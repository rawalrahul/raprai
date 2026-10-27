// agent_run.js — Live run overlay, run updates, and questions a running agent asks you.

// ---------------------------------------------------------------------------
// Live run overlay
// ---------------------------------------------------------------------------

let _runPollTimer = null;
let _pendingRunInput = null;
let _agentInputModalOpenFor = null;

function openAgentRunOverlay(run){
  _activeRunId=run.id;_activeRunAgentId=run.agent_id;_runNodes=run.nodes||[];
  const t=document.getElementById('agent-run-title');
  if(t) _setText(t,run.agent_name+' — Run '+run.id.slice(0,8));
  _updateRunOverlayStatus(run);
  const wrap=document.getElementById('agent-run-wrapper');
  if(wrap) wrap.classList.add('open');
  _rPan={x:60,y:60};_renderRunCanvas();_setupRunPan();
  _syncRunInputState(run);
  _startRunPoll(run.id);
}

function closeAgentRunOverlay(){
  const wrap=document.getElementById('agent-run-wrapper');
  if(wrap) wrap.classList.remove('open');
  _activeRunId=null;_runNodes=[];
  _pendingRunInput=null;
  _hideAgentInputBanner();
  _stopRunPoll();
}

async function cancelAgentRun(){
  if(!_activeRunId) return;
  // Find agent_id from current run data
  const run=_runNodes.length?{agent_id:_activeRunAgentId}:null;
  const agentId=_activeRunAgentId;
  if(!agentId){alert('Cannot cancel — agent ID unknown.');return;}
  const btn=document.getElementById('agent-run-cancel-btn');
  if(btn){btn.disabled=true;btn.textContent='Stopping…';}
  try{
    const data=await fetch('/api/agents/'+agentId+'/runs/'+_activeRunId+'/cancel',{method:'POST'}).then(r=>r.json());
    if(data.error){alert('Cancel failed: '+data.error);if(btn){btn.disabled=false;btn.textContent='Stop';}}
  }catch(e){alert('Cancel request failed: '+e);if(btn){btn.disabled=false;btn.textContent='Stop';}}
}

function _startRunPoll(runId){
  _stopRunPoll();
  let missed=0;
  _runPollTimer=setInterval(async()=>{
    if(!_activeRunId){_stopRunPoll();return;}
    try{
      const data=await fetch('/api/agents/runs/'+runId).then(r=>r.json());
      if(data.run){
        missed=0;
        // Always update — catches WS gaps
        _runNodes=data.run.nodes||[];
        _updateRunOverlayStatus(data.run);
        _renderRunCanvas();
        _syncRunInputState(data.run);
        if(_isTerminalRunStatus(data.run.status)) _stopRunPoll();
      }
    }catch(e){missed++;if(missed>5) _stopRunPoll();}
  },2000);
}

function _stopRunPoll(){
  if(_runPollTimer){clearInterval(_runPollTimer);_runPollTimer=null;}
}

function _updateRunOverlayStatus(run){
  const prog=run.progress||{};
  const badge=document.getElementById('agent-run-status-badge');
  const progEl=document.getElementById('agent-run-progress');
  const cancelBtn=document.getElementById('agent-run-cancel-btn');
  if(badge){
    const colors={running:'#4a9eff',waiting_input:'#f0a500',completed:'#4caf50',failed:'#e06c75',cancelled:'#888'};
    const c=colors[run.status]||'#888';
    badge.style.background=c+'22';badge.style.color=c;badge.textContent=run.status;
  }
  if(cancelBtn){
    cancelBtn.style.display=_isTerminalRunStatus(run.status)?'none':'inline-block';
    cancelBtn.disabled=false;cancelBtn.textContent='Stop';
  }
  if(run.status==='waiting_input'){
    _showRunInputHeaderButton(_pendingRunInput||_runInputPayloadFromNode(null));
  }else{
    _hideRunInputHeaderButton();
  }
  if(progEl){
    const total=prog.total||_runNodes.length;
    const done=(prog.completed||0)+(prog.failed||0)+(prog.skipped||0);
    const running=(prog.running||0)||_runNodes.filter(n=>n.status==='running').length;
    const waiting=run.status==='waiting_input'||_runNodes.some(n=>['input','manager'].includes(n.type||'ai')&&n.status==='running');
    const label=waiting?`Step ${done+1}/${total} waiting for input`:(running>0?`Step ${done+1}/${total} running`:done+'/'+total+' steps');
    _setText(progEl,label);
  }
}

function _renderRunCanvas(){
  const canvas=document.getElementById('agent-run-canvas');
  if(!canvas) return;
  canvas.querySelectorAll('.ag-node').forEach(el=>el.remove());
  _runNodes.forEach(node=>canvas.appendChild(_makeNodeEl(node,true)));
  _applyPan('agent-run-canvas',_rPan);
  _drawEdges('agent-run-edges-svg',_runNodes,true,_rPan);
  _drawGrid('agent-run-grid-svg');
}

function _setupRunPan(){
  const overlay=document.getElementById('agent-run-overlay');
  if(!overlay||overlay._agRunPanSetup) return;
  overlay._agRunPanSetup=true;
  overlay.addEventListener('mousedown',e=>{
    if(!e.target.closest('.ag-node')){_rPanning=true;_rPanStart={x:e.clientX,y:e.clientY};_rPanOrigin={..._rPan};overlay.style.cursor='grabbing';}
  });
  window.addEventListener('mousemove',e=>{
    if(!_rPanning) return;
    _rPan.x=_rPanOrigin.x+(e.clientX-_rPanStart.x);_rPan.y=_rPanOrigin.y+(e.clientY-_rPanStart.y);
    _applyPan('agent-run-canvas',_rPan);
  });
  window.addEventListener('mouseup',()=>{if(_rPanning){_rPanning=false;overlay.style.cursor='';}});
}

// ---------------------------------------------------------------------------
// WebSocket handlers
// ---------------------------------------------------------------------------

function handleAgentRunUpdate(run){
  if(run.agent_id&&_agents[run.agent_id]&&run.status!=='running'){
    _agents[run.agent_id].last_run_at=run.completed_at||run.started_at;
    _agents[run.agent_id].run_count=(_agents[run.agent_id].run_count||0)+1;
  }
  if(_activeRunId===run.id){
    _runNodes=run.nodes||[];_updateRunOverlayStatus(run);_renderRunCanvas();_syncRunInputState(run);
  }
}

function handleAgentRunStream(runId,nodeId,chunk){
  if(_activeRunId!==runId) return;
  const node=_runNodes.find(n=>n.id===nodeId);
  if(node){
    node.stream_buffer=((node.stream_buffer||'')+chunk).slice(-500);
    const el=document.getElementById('node-'+nodeId);
    if(el){const b=el.querySelector('.ag-stream-buf');if(b) b.textContent=node.stream_buffer.slice(-200);}
  }
}

// ---------------------------------------------------------------------------
// Canvas background colour — force dark regardless of page theme
// ---------------------------------------------------------------------------

async function handleAgentRunWaitingInput(payload){
  // If this run is already in a separate browser window, focus that window instead
  // of opening a second overlay+modal in the main window.
  const runWin=payload.run_id&&_runWindows[payload.run_id];
  if(runWin&&!runWin.closed){
    try{runWin.focus();}catch(e){}
    if(typeof _flashStatus==='function') _flashStatus('Agent waiting for input — see run window','#f0a500');
    return;
  }
  if(payload.run_id&&!_activeRunId){
    try{
      const data=await fetch('/api/agents/runs/'+payload.run_id).then(r=>r.json());
      if(data.run) openAgentRunOverlay(data.run);
      else openAgentRunOverlay({id:payload.run_id,agent_name:'Agent',nodes:[],status:'waiting_input'});
    }catch(e){
      openAgentRunOverlay({id:payload.run_id,agent_name:'Agent',nodes:[],status:'waiting_input'});
    }
  }
  _pendingRunInput=payload;
  _showAgentInputBanner(payload);
  _openAgentInputFromBanner(payload);
}

function _isTerminalRunStatus(status){
  return status==='completed'||status==='failed'||status==='cancelled';
}

function _runInputPayloadFromNode(node){
  const isManager=node&&(node.type||'ai')==='manager';
  return {
    run_id:_activeRunId,
    node_id:node&&node.id,
    kind:isManager?'feedback':'input',
    question:(node&&node.task)||(isManager
      ? 'Review the workflow output. Reply YES if you are happy with it, or describe what should be fixed.'
      : 'This step needs input. Upload a file or paste text to continue.')
  };
}

function _syncRunInputState(run){
  if(!run||run.id!==_activeRunId) return;
  const waitingNode=(run.nodes||[]).find(n=>{
    const t=n.type||'ai';
    return (t==='input'||t==='manager')&&n.status==='running';
  });
  if(run.status==='waiting_input'||waitingNode){
    const alreadyPending=_pendingRunInput&&_pendingRunInput.run_id===run.id;
    const payload=alreadyPending
      ? _pendingRunInput
      : _runInputPayloadFromNode(waitingNode);
    _pendingRunInput=payload;
    _showAgentInputBanner(payload);
    // Auto-open on first detection only (not on every poll cycle)
    if(!alreadyPending&&!_agentInputModalOpenFor) _openAgentInputFromBanner(payload);
  }else if(_pendingRunInput&&_pendingRunInput.run_id===run.id){
    _pendingRunInput=null;
    _hideAgentInputBanner();
  }
}

function _showAgentInputBanner(payload){
  const overlay=document.getElementById('agent-run-overlay');
  if(!overlay) return;
  _showRunInputHeaderButton(payload);
  const manager=_isManagerInputPayload(payload);
  let banner=document.getElementById('agent-input-banner');
  if(!banner){
    banner=document.createElement('div');
    banner.id='agent-input-banner';
    banner.style.cssText='position:absolute;left:50%;top:76px;transform:translateX(-50%);z-index:80;width:min(760px,calc(100vw - 36px));background:#211a08;border:1px solid #9b6b13;border-radius:8px;color:#f5d38a;padding:10px 12px;box-shadow:0 8px 28px rgba(0,0,0,.45);display:flex;align-items:center;gap:12px';
    const text=document.createElement('div');
    text.className='agent-input-banner-text';
    text.style.cssText='flex:1;min-width:0;font-size:12px;line-height:1.35';
    banner.appendChild(text);
    const btn=document.createElement('button');
    btn.className='agent-input-banner-btn';
    btn.style.cssText='flex-shrink:0;padding:7px 10px;border-radius:6px;border:1px solid #d8a33a;background:#33240d;color:#ffd887;cursor:pointer;font-size:12px';
    btn.onclick=()=>_openAgentInputFromBanner(_pendingRunInput||payload);
    banner.appendChild(btn);
    overlay.appendChild(banner);
  }
  const text=banner.querySelector('.agent-input-banner-text');
  const btn=banner.querySelector('.agent-input-banner-btn');
  if(btn) btn.textContent=manager?'Chat with manager':'Provide input / upload file';
  if(text) text.textContent=(manager
    ? (payload.kind==='input'?'Manager is asking for input: ':'Manager is waiting for feedback: ')
    : 'Waiting for input: ')+(payload.question||'Upload a file or paste text to continue.');
  banner.style.display='flex';
}

function _hideAgentInputBanner(){
  const banner=document.getElementById('agent-input-banner');
  if(banner) banner.style.display='none';
  _hideRunInputHeaderButton();
}

function _showRunInputHeaderButton(payload){
  const progEl=document.getElementById('agent-run-progress');
  if(!progEl||!progEl.parentElement) return;
  let btn=document.getElementById('agent-run-input-btn');
  if(!btn){
    btn=document.createElement('button');
    btn.id='agent-run-input-btn';
    btn.style.cssText='background:#f0a50022;border:1px solid #f0a500;color:#f0c36a;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:12px';
    progEl.parentElement.insertBefore(btn, document.getElementById('agent-run-cancel-btn'));
  }
  btn.textContent=_isManagerInputPayload(payload)?'Chat with manager':'Upload / provide input';
  btn.style.display='inline-block';
  btn.onclick=()=>_openAgentInputFromBanner(_pendingRunInput||payload||_runInputPayloadFromNode(null));
}

function _hideRunInputHeaderButton(){
  const btn=document.getElementById('agent-run-input-btn');
  if(btn) btn.style.display='none';
}

async function _openAgentInputFromBanner(payload){
  if(!payload||!payload.run_id) return;
  if(_agentInputModalOpenFor===payload.run_id) return;
  _agentInputModalOpenFor=payload.run_id;
  const manager=_isManagerInputPayload(payload);
  const managerInput=manager&&payload.kind==='input';
  const input=await _safeCollectAgentInput(
    payload.question||'Please provide input to continue.',
    manager?'Chat with manager':'Agent input required',
    manager
      ? (managerInput?'Reply with the information this step needs.':'Reply YES if you are happy with the result, or describe what should be fixed.')
      : 'Paste resume text, preferences, approval, or any other required input here...'
  );
  _agentInputModalOpenFor=null;
  if(input===null) return;
  try{
    const res=await fetch('/api/agents/runs/'+payload.run_id+'/resume',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({input})
    }).then(r=>r.json());
    if(res.error) alert(res.error);
    else{
      _pendingRunInput=null;
      _hideAgentInputBanner();
      try{
        const data=await fetch('/api/agents/runs/'+payload.run_id).then(r=>r.json());
        if(data.run){
          _runNodes=data.run.nodes||[];
          _updateRunOverlayStatus(data.run);
          _renderRunCanvas();
          _syncRunInputState(data.run);
        }
      }catch(e){}
    }
  }catch(err){alert('Failed to resume agent: '+err);}
}

async function _safeCollectAgentInput(question,titleText,placeholderText){
  try{
    if(typeof _collectAgentInput==='function') return await _collectAgentInput(question,titleText,placeholderText);
  }catch(err){
    console.error('Agent input modal failed:',err);
  }
  return prompt(question||'Please provide input to continue.');
}

function _isManagerInputPayload(payload){
  if(!payload) return false;
  const node=_runNodes.find(n=>n.id===payload.node_id);
  if(node&&(node.type||'ai')==='manager') return true;
  const managerNode=_runNodes.find(n=>(n.type||'ai')==='manager');
  return !!(payload.session_id&&managerNode&&managerNode.session_id===payload.session_id);
}

function _collectAgentInput(question,titleText,placeholderText){
  return new Promise(resolve=>{
    const existing=document.getElementById('agent-input-modal');
    if(existing) existing.remove();
    const overlay=document.createElement('div');
    overlay.id='agent-input-modal';
    overlay.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.72);z-index:10000;display:flex;align-items:center;justify-content:center;padding:20px';
    const box=document.createElement('div');
    box.style.cssText='width:min(720px,96vw);background:var(--bg-surface);border:1px solid var(--border-default);border-radius:8px;padding:16px;color:var(--text-main);box-shadow:0 12px 40px rgba(0,0,0,.55)';
    const title=document.createElement('div');
    title.style.cssText='font-size:15px;font-weight:600;margin-bottom:8px';
    title.textContent=titleText||'Agent input required';
    const q=document.createElement('div');
    q.style.cssText='font-size:12px;color:var(--text-muted);line-height:1.45;margin-bottom:10px;white-space:pre-wrap';
    q.textContent=question;
    const ta=document.createElement('textarea');
    ta.style.cssText='width:100%;height:180px;resize:vertical;background:var(--bg-deep);color:var(--text-main);border:1px solid var(--border-default);border-radius:6px;padding:10px;font-family:inherit;font-size:12px;box-sizing:border-box';
    ta.placeholder=placeholderText||'Paste resume text, preferences, approval, or any other required input here...';
    const fileRow=document.createElement('div');
    fileRow.style.cssText='display:flex;align-items:center;gap:8px;margin-top:10px;flex-wrap:wrap';
    const file=document.createElement('input');
    file.type='file';
    file.accept='.pdf,.docx,.txt,.md,.csv,.json,.mp3,.wav,.m4a,.ogg,.opus,.webm,.flac,.aac,.amr,audio/*';
    file.style.cssText='font-size:12px;color:var(--text-muted)';
    const uploadStatus=document.createElement('span');
    uploadStatus.style.cssText='font-size:11px;color:var(--text-dim)';
    uploadStatus.textContent='Optional: upload a document or voice recording';
    fileRow.appendChild(file);
    fileRow.appendChild(uploadStatus);
    file.onchange=async()=>{
      if(!file.files||!file.files.length) return;
      const form=new FormData();
      form.append('file',file.files[0]);
      uploadStatus.textContent='Uploading and extracting...';
      try{
        const headers={};
        if(typeof _csrfToken==='function') headers['x-csrf-token']=_csrfToken();
        const data=await fetch('/api/agents/input-file',{method:'POST',headers,body:form}).then(r=>r.json());
        if(data.error){uploadStatus.textContent=data.error;uploadStatus.style.color='#e06c75';return;}
        const prefix=ta.value.trim()?ta.value.trim()+'\n\n':'';
        ta.value=prefix+(data.input_text||`Uploaded file: ${data.filename}\nSaved path: ${data.path}`);
        uploadStatus.textContent='Added '+(data.filename||'file')+' to input';
        uploadStatus.style.color='#4caf50';
      }catch(err){
        uploadStatus.textContent='Upload failed: '+err;
        uploadStatus.style.color='#e06c75';
      }
    };
    const actions=document.createElement('div');
    actions.style.cssText='display:flex;justify-content:flex-end;gap:8px;margin-top:14px';
    const cancel=document.createElement('button');
    cancel.textContent='Cancel';
    cancel.style.cssText='padding:7px 12px;border-radius:6px;border:1px solid var(--border-default);background:var(--bg-elevated);color:var(--text-muted);cursor:pointer';
    const submit=document.createElement('button');
    submit.textContent='Continue';
    submit.style.cssText='padding:7px 12px;border-radius:6px;border:1px solid #4a8;background:#1d3a2a;color:#9fdaaa;cursor:pointer';
    actions.appendChild(cancel);
    actions.appendChild(submit);
    cancel.onclick=()=>{overlay.remove();resolve(null);};
    submit.onclick=()=>{
      const val=ta.value.trim();
      if(!val){ta.focus();uploadStatus.textContent='Paste text or upload a file first.';uploadStatus.style.color='#e06c75';return;}
      overlay.remove();resolve(val);
    };
    box.appendChild(title);
    box.appendChild(q);
    box.appendChild(ta);
    box.appendChild(fileRow);
    box.appendChild(actions);
    overlay.appendChild(box);
    document.body.appendChild(overlay);
    ta.focus();
  });
}
