// agent_builder_chat.js — Builder chat panel and the manager-node guard.

function _fixCanvasBg(){
  ['agent-builder-overlay','agent-run-overlay','agent-canvas-wrap'].forEach(id=>{
    const el=document.getElementById(id);
    if(el) el.style.background='var(--bg-deep)';
  });
  const canvas=document.getElementById('agent-canvas');
  if(canvas) canvas.style.background='var(--bg-deep)';
  const runCanvas=document.getElementById('agent-run-canvas');
  if(runCanvas) runCanvas.style.background='var(--bg-deep)';
}

// ---------------------------------------------------------------------------
// Utility
// ---------------------------------------------------------------------------

function _randomHex(n){
  return Array.from(crypto.getRandomValues(new Uint8Array(n))).map(b=>b.toString(16).padStart(2,'0')).join('').slice(0,n);
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Builder Chat Panel
// ---------------------------------------------------------------------------

function toggleBuilderChat(){
  const panel=document.getElementById('builder-chat-panel');
  if(!panel) return;
  if(panel.style.display==='none'||!panel.style.display){_openBuilderChat();}else{_closeBuilderChat();}
}

function _openBuilderChat(){
  const panel=document.getElementById('builder-chat-panel');
  if(panel) panel.style.display='flex';
}

function _closeBuilderChat(){
  const panel=document.getElementById('builder-chat-panel');
  if(panel) panel.style.display='none';
}

function _addBuilderChatBubble(role, text){
  const msgs=document.getElementById('builder-chat-messages');
  if(!msgs) return;
  const wrap=document.createElement('div');
  wrap.style.cssText='display:flex;flex-direction:column;align-items:'+(role==='user'?'flex-end':'flex-start')+';margin-bottom:8px';
  const bubble=document.createElement('div');
  bubble.style.cssText='max-width:90%;padding:7px 11px;border-radius:12px;font-size:12px;line-height:1.5;word-break:break-word;'+(role==='user'?'background:var(--bg-elevated);color:var(--text-main)':'background:var(--accent-subtle);color:var(--accent);border:1px solid var(--accent-border)');
  bubble.textContent=text;
  wrap.appendChild(bubble);
  msgs.appendChild(wrap);
  msgs.scrollTop=msgs.scrollHeight;
  _builderChatHistory.push({role,content:text});
}

function _addBuilderChatThinking(){
  const msgs=document.getElementById('builder-chat-messages');
  if(!msgs) return;
  const wrap=document.createElement('div');
  wrap.id='builder-chat-thinking';
  wrap.style.cssText='display:flex;align-items:flex-start;margin-bottom:8px';
  const bubble=document.createElement('div');
  bubble.style.cssText='background:var(--accent-subtle);color:var(--accent);border:1px solid var(--accent-border);padding:7px 11px;border-radius:12px;font-size:12px';
  bubble.textContent='Thinking…';
  wrap.appendChild(bubble);
  msgs.appendChild(wrap);
  msgs.scrollTop=msgs.scrollHeight;
}

function _removeBuilderChatThinking(){
  const el=document.getElementById('builder-chat-thinking');
  if(el) el.remove();
}

async function sendBuilderChat(){
  if(_builderChatSending) return;
  const inp=document.getElementById('builder-chat-inp');
  if(!inp) return;
  const msg=inp.value.trim();
  if(!msg) return;

  // Manager guard — intercept locally
  const lc=msg.toLowerCase();
  if((lc.includes('remov')||lc.includes('delet'))&&(lc.includes('manager')||lc.includes('supervisor')||lc.includes('review'))){
    inp.value='';
    _addBuilderChatBubble('user',msg);
    _builderChatHistory.pop(); // don't keep user msg in history for local intercept
    const guardMsg="I can't remove the Manager node — it's what makes your agent self-healing. When a node fails or the output isn't what you expected, the Manager reviews the result, identifies the failing node, fixes its task, and reruns automatically. Without it, a single failure stops the whole workflow. You can set Max Iterations to 1 (auto-approve after one review) if you want less interaction.";
    _addBuilderChatBubble('assistant',guardMsg);
    return;
  }

  inp.value='';
  _addBuilderChatBubble('user',msg);
  _builderChatSending=true;
  _addBuilderChatThinking();

  const sendBtn=document.getElementById('builder-chat-send-btn');
  if(sendBtn) sendBtn.disabled=true;

  try{
    const body={
      description:_builderChatDesc||'',
      nodes:JSON.parse(JSON.stringify(_builderNodes)),
      history:_builderChatHistory.slice(-20),
      message:msg
    };
    const data=await fetch('/api/agents/builder-chat',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(body)
    }).then(r=>r.json());

    _removeBuilderChatThinking();
    if(data.error){
      _addBuilderChatBubble('assistant','Error: '+data.error);
    }else{
      _addBuilderChatBubble('assistant',data.reply||'Done.');
      if(data.nodes&&data.nodes.length>=1){
        _applyBuilderChatNodes(data.nodes);
      }
    }
  }catch(err){
    _removeBuilderChatThinking();
    _addBuilderChatBubble('assistant','Network error — please try again.');
  }finally{
    _builderChatSending=false;
    if(sendBtn) sendBtn.disabled=false;
    if(inp) inp.focus();

  }
}

function _applyBuilderChatNodes(newNodes){
  const oldIds=new Set(_builderNodes.map(n=>n.id));
  const newIds=new Set(newNodes.map(n=>n.id));
  const addedIds=newNodes.filter(n=>!oldIds.has(n.id)).map(n=>n.id);
  const removedIds=[..._builderNodes.filter(n=>!newIds.has(n.id)).map(n=>n.id)];
  const changedIds=newNodes.filter(n=>{
    const old=_builderNodes.find(o=>o.id===n.id);
    return old&&(old.task!==n.task||JSON.stringify(old.children)!==JSON.stringify(n.children));
  }).map(n=>n.id);

  _builderNodes=newNodes.map(n=>({
    ...n,
    status:n.status||'pending',output:n.output||null,output_summary:n.output_summary||null,
    error:n.error||null,stream_buffer:n.stream_buffer||'',
    session_id:n.session_id||null,started_at:n.started_at||null,
    completed_at:n.completed_at||null,elapsed_seconds:n.elapsed_seconds||0
  }));
  _renderBuilderCanvas();

  // Flash changed/added nodes
  const toFlash=[...addedIds,...changedIds];
  toFlash.forEach(id=>{
    const el=document.getElementById('node-'+id);
    if(!el) return;
    el.style.transition='box-shadow 0.2s';
    el.style.boxShadow='0 0 0 3px #f0a50088, 0 3px 16px rgba(0,0,0,0.6)';
    setTimeout(()=>{el.style.boxShadow='';},800);
  });
}

function _showManagerGuard(){
  const existing=document.getElementById('manager-guard-panel');
  if(existing){existing.remove();return;}

  const panel=document.createElement('div');
  panel.id='manager-guard-panel';
  panel.style.cssText='position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:var(--bg-surface);border:1.5px solid #f0a500;border-radius:10px;padding:20px 24px;z-index:9999;max-width:400px;width:90%;box-shadow:0 8px 32px rgba(0,0,0,0.7)';

  const title=document.createElement('div');
  title.style.cssText='font-size:14px;font-weight:700;color:#f0a500;margin-bottom:10px';
  title.textContent='Keep the Manager node';
  panel.appendChild(title);

  const lines=[
    "It's what makes your agent self-healing.",
    "When a node fails or the output isn't what you expected, the Manager reviews the result with you, figures out which node needs fixing, updates its task, and reruns automatically.",
    "Without it, a single failure stops the whole workflow.",
    "If you want less interaction, lower its Max Iterations to 1 (auto-approve after one review)."
  ];
  lines.forEach(txt=>{
    const p=document.createElement('p');
    p.style.cssText='font-size:12px;color:var(--text-muted);margin:6px 0;line-height:1.5';
    p.textContent=txt;
    panel.appendChild(p);
  });

  const btnRow=document.createElement('div');
  btnRow.style.cssText='display:flex;gap:10px;margin-top:16px;justify-content:flex-end';

  const autoBtn=document.createElement('button');
  autoBtn.style.cssText='padding:6px 14px;border-radius:6px;background:var(--accent-subtle);border:1px solid var(--accent);color:var(--accent);font-size:12px;cursor:pointer';
  autoBtn.textContent='Set to auto-approve';
  autoBtn.addEventListener('click',()=>{_setManagerAutoApprove();panel.remove();});

  const okBtn=document.createElement('button');
  okBtn.style.cssText='padding:6px 14px;border-radius:6px;background:var(--bg-elevated);border:1px solid var(--border-default);color:var(--text-main);font-size:12px;cursor:pointer';
  okBtn.textContent='Got it';
  okBtn.addEventListener('click',()=>panel.remove());

  btnRow.appendChild(autoBtn);
  btnRow.appendChild(okBtn);
  panel.appendChild(btnRow);

  document.body.appendChild(panel);
  closeNodeModal();
}

function _setManagerAutoApprove(){
  const mgr=_builderNodes.find(n=>(n.type||'ai')==='manager');
  if(mgr) mgr.manager_max_iter=1;
  _renderBuilderCanvas();
}

// Builder chat keyboard shortcut
