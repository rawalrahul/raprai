// agent_builder.js — Agent builder: canvas, nodes, edges, node settings, save, triggers, generate.
// Shared state and _esc() live in agents.js, which loads first.

// ---------------------------------------------------------------------------
// Builder open / close
// ---------------------------------------------------------------------------

function openAgentBuilder(agentId, template){
  _clearBlockingUiForAgentBuilder();
  _builderAgentId=agentId;
  const wrap=document.getElementById('agent-builder-wrapper');
  if(wrap) wrap.classList.add('open');
  const nameInp=document.getElementById('agent-name-inp');
  const descInp=document.getElementById('agent-desc-inp');
  if(template){
    _builderAgentId=null;
    if(nameInp) nameInp.value=template.name||'';
    if(descInp) descInp.value=template.description||'';
    _builderNodes=JSON.parse(JSON.stringify(template.nodes||[])).map(n=>({
      ...n,status:'pending',output:null,output_summary:null,error:null,stream_buffer:'',
      session_id:null,started_at:null,completed_at:null,elapsed_seconds:0
    }));
    _builderTrigger=JSON.parse(JSON.stringify(template.trigger||_defaultTrigger()));
  }else if(agentId&&_agents[agentId]){
    const ag=_agents[agentId];
    if(nameInp) nameInp.value=ag.name||'';
    if(descInp) descInp.value=ag.description||'';
    _builderNodes=JSON.parse(JSON.stringify(ag.nodes||[]));
    _builderTrigger=JSON.parse(JSON.stringify(ag.trigger||_defaultTrigger()));
  }else{
    if(nameInp) nameInp.value='';
    if(descInp) descInp.value='';
    _builderNodes=[];_builderTrigger=_defaultTrigger();
  }
  _bPan={x:60,y:60};
  _builderChatHistory=[];
  _builderChatSending=false;
  _builderChatDesc=(document.getElementById('agent-desc-inp')||{}).value||'';
  _closeBuilderChat();
  _fixCanvasBg();
  _renderBuilderCanvas();
  _setupBuilderPan();
  _ensureBuilderManagerNode();
  _renderBuilderCanvas();
}

function closeAgentBuilder(){
  const wrap=document.getElementById('agent-builder-wrapper');
  if(wrap) wrap.classList.remove('open');
  _builderAgentId=null;_builderNodes=[];
}

function _clearBlockingUiForAgentBuilder(){
  const onboarding=document.getElementById('onboarding-overlay');
  if(onboarding) onboarding.classList.remove('show');
  const sidebarOverlay=document.getElementById('sb-overlay');
  if(sidebarOverlay) sidebarOverlay.classList.remove('open');
  const leftSidebar=document.getElementById('left-sidebar');
  if(leftSidebar) leftSidebar.classList.remove('open');
  const rightSidebar=document.getElementById('right-sidebar');
  if(rightSidebar) rightSidebar.classList.remove('open');
}

function _defaultTrigger(){return{telegram:true,schedule:{enabled:false,expression:'',cron:'',next_run:null,input_data:null},webhook:{enabled:false,token:''}};}

// ---------------------------------------------------------------------------
// Canvas rendering
// ---------------------------------------------------------------------------

function _renderBuilderCanvas(){
  const canvas=document.getElementById('agent-canvas');
  if(!canvas) return;
  canvas.querySelectorAll('.ag-node,.ag-hint').forEach(el=>el.remove());
  if(_builderNodes.length===0){
    // Empty state hint
    const hint=document.createElement('div');
    hint.className='ag-hint';
    hint.style.cssText='position:absolute;left:50%;top:50%;transform:translate(-50%,-60%);text-align:center;pointer-events:none;z-index:5';
    hint.appendChild(_hintLine('Start building your agent workflow','font-size:15px;font-weight:600;color:var(--text-dim);margin-bottom:10px'));
    hint.appendChild(_hintLine('Click  ✦ Generate  to create steps from a description','font-size:12px;color:var(--text-muted);margin-bottom:6px'));
    hint.appendChild(_hintLine('— or —','font-size:11px;color:var(--text-dim);margin-bottom:6px'));
    hint.appendChild(_hintLine('Click  + Node  in the toolbar to add a step manually','font-size:12px;color:var(--text-muted)'));
    canvas.appendChild(hint);
  }
  _builderNodes.forEach(node=>canvas.appendChild(_makeNodeEl(node,false)));
  _applyPan('agent-canvas',_bPan);
  _drawEdges('agent-edges-svg',_builderNodes,false,_bPan);
  _drawGrid('agent-grid-svg');
  _updateCanvasHint();
}

function _hintLine(text,css){const d=document.createElement('div');d.style.cssText=css;d.textContent=text;return d;}

function _updateCanvasHint(){
  // Show a persistent "how to connect" tip when there are nodes but no edges yet
  const wrap=document.getElementById('agent-canvas-wrap');
  if(!wrap) return;
  let tip=wrap.querySelector('.ag-connect-tip');
  const hasEdges=_builderNodes.some(n=>(n.children||[]).length>0);
  const hasNodes=_builderNodes.length>0;
  if(hasNodes&&!hasEdges){
    if(!tip){
      tip=document.createElement('div');
      tip.className='ag-connect-tip';
      tip.style.cssText='position:absolute;bottom:14px;left:50%;transform:translateX(-50%);background:var(--bg-elevated);color:var(--text-muted);font-size:11px;padding:6px 14px;border-radius:20px;pointer-events:none;z-index:20;white-space:nowrap;border:1px solid var(--border-default);box-shadow:var(--shadow-md)';
      tip.textContent='Click a node to configure it · Drag from a colored dot to connect nodes';
      wrap.appendChild(tip);
    }
  }else if(tip){
    tip.remove();
  }
}

function _makeNodeEl(node,isRun){
  const el=document.createElement('div');
  el.className='ag-node';
  el.id='node-'+node.id;

  const sc=isRun?_nodeStatusColor(node.status):'#3a3a3a';
  const hasTask=node.task&&node.task.trim().length>0;
  const isRunning=isRun&&node.status==='running';

  el.style.cssText=[
    'position:absolute',
    `left:${node.x}px`,
    `top:${node.y}px`,
    'width:200px',
    isRunning?'background:var(--bg-active)':'background:var(--bg-surface)',
    `border:${isRunning?'2px':'1.5px'} solid ${sc}`,
    'border-radius:8px',
    'z-index:10',
    'user-select:none',
    `box-shadow:${isRunning?`0 0 0 3px ${sc}33, 0 3px 16px rgba(0,0,0,0.6)`:'0 3px 12px rgba(0,0,0,0.5)'}`,
    'font-family:inherit',
    isRunning?'animation:ag-node-pulse 1.8s ease-in-out infinite':'',
  ].join(';');

  // ── Header ──
  const hdr=document.createElement('div');
  hdr.style.cssText=[
    'padding:8px 10px 6px',
    'cursor:'+(isRun?'default':'pointer'),
    'border-radius:7px 7px 0 0',
    isRun?`background:${sc}22`:'',
  ].join(';');

  // AI chip + title row
  const titleRow=document.createElement('div');
  titleRow.style.cssText='display:flex;align-items:center;gap:6px;margin-bottom:'+(isRun?'0':'4px');

  const aiChip=document.createElement('span');
  aiChip.style.cssText='font-size:9px;padding:1px 5px;border-radius:4px;background:var(--bg-elevated);color:var(--text-muted);flex-shrink:0;text-transform:uppercase;letter-spacing:.4px';
  aiChip.textContent=node.ai||'claude';
  const typeChip=document.createElement('span');
  typeChip.style.cssText='font-size:9px;padding:1px 5px;border-radius:4px;background:var(--accent-subtle);color:var(--accent);flex-shrink:0;text-transform:uppercase;letter-spacing:.4px';
  typeChip.textContent=node.type||'ai';

  if ((node.type || 'ai') === 'manager') {
    el.style.border = '1px solid #9b59b6';
    el.style.zIndex = '14';
    typeChip.style.background = '#2d1b4e';
    typeChip.style.color = '#c39bd3';
  }

  const titleSpan=document.createElement('span');
  titleSpan.style.cssText='font-size:12px;font-weight:600;color:var(--text-main);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap';
  if(isRun){
    const icon=_nodeStatusIcon(node.status);
    if(icon){
      const iconEl=document.createElement('span');
      iconEl.style.cssText=`margin-right:4px;font-size:11px;${node.status==='running'?'animation:ag-spin 1s linear infinite;display:inline-block':''}`;
      iconEl.textContent=icon;
      titleSpan.appendChild(iconEl);
    }
    const textNode=document.createTextNode(node.title||'');
    titleSpan.appendChild(textNode);
  }else{
    titleSpan.textContent=node.title||'New Step';
  }

  if((node.type||'ai')==='ai') titleRow.appendChild(aiChip);
  titleRow.appendChild(typeChip);
  titleRow.appendChild(titleSpan);
  hdr.appendChild(titleRow);

  if(!isRun){
    // Task preview or "click to configure" hint
    const preview=document.createElement('div');
    if(hasTask){
      preview.style.cssText='font-size:10px;color:var(--text-muted);line-height:1.4;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;margin-top:2px';
      preview.textContent=node.task.slice(0,120);
    }else{
      preview.style.cssText='font-size:10px;color:var(--text-dim);font-style:italic;margin-top:2px';
      preview.textContent='Click to add instructions…';
    }
    hdr.appendChild(preview);
  }

  if(isRun&&node.status==='running'){
    const buf=document.createElement('div');buf.className='ag-stream-buf';
    buf.style.cssText='font-size:9px;color:var(--text-muted);margin-top:4px;max-height:36px;overflow:hidden;font-family:monospace;line-height:1.3';
    buf.textContent=(node.stream_buffer||'').slice(-200);
    hdr.appendChild(buf);
  }
  if(isRun&&node.status==='failed'&&node.error){
    const errDiv=document.createElement('div');
    errDiv.style.cssText='font-size:10px;color:#e06c75;margin-top:3px';
    errDiv.textContent=(node.error||'').slice(0,80);
    hdr.appendChild(errDiv);
  }
  if(isRun&&node.status==='completed'){
    const elapsed=document.createElement('div');
    elapsed.style.cssText='font-size:9px;color:#4caf50;margin-top:3px';
    elapsed.textContent=node.elapsed_seconds?`✓ ${node.elapsed_seconds.toFixed(1)}s`:'✓ done';
    hdr.appendChild(elapsed);
  }
  if(isRun&&['input','manager'].includes(node.type||'ai')&&node.status==='running'){
    const promptHint=document.createElement('div');
    promptHint.style.cssText='font-size:10px;color:#f0c36a;margin-top:4px';
    promptHint.textContent='Waiting for your input. Click here to continue.';
    hdr.style.cursor='pointer';
    hdr.title='Provide input or upload a file';
    hdr.appendChild(promptHint);
  }
  el.appendChild(hdr);

  if(!isRun){
    // ── Output ports row ──
    const portsWrap=document.createElement('div');
    portsWrap.style.cssText='border-top:1px solid var(--border-dim);padding:5px 10px 6px;display:flex;justify-content:space-between;align-items:center';

    const portsLabel=document.createElement('span');
    portsLabel.style.cssText='font-size:9px;color:var(--text-dim)';
    const isManager=(node.type||'ai')==='manager';
    portsLabel.textContent=isManager?'supervises workflow':'outputs →';
    portsWrap.appendChild(portsLabel);

    const portsDots=document.createElement('div');
    portsDots.style.cssText='display:flex;gap:10px;align-items:center';

    if(isManager){
      const badge=document.createElement('span');
      badge.style.cssText='font-size:9px;color:#c39bd3;background:#2d1b4e;border-radius:4px;padding:1px 5px';
      badge.textContent=(node.children||[]).length+' roots';
      portsDots.appendChild(badge);
    }else PORT_COLORS.forEach((c,i)=>{
      const wrapper=document.createElement('div');
      wrapper.style.cssText='display:flex;flex-direction:column;align-items:center;gap:2px';
      const p=document.createElement('div');
      p.className='ag-port';
      p.dataset.node=node.id;
      p.dataset.port=i;
      // Check if this port is already connected
      const connected=(node.children||[])[i];
      p.style.cssText=[
        'width:12px','height:12px','border-radius:50%',
        `background:${c}`,
        'cursor:crosshair',
        connected?'box-shadow:0 0 0 2px rgba(255,255,255,0.2)':'opacity:0.5',
      ].join(';');
      p.title=connected?`Port ${i+1} — connected (drag to reconnect)`:`Port ${i+1} — drag to connect to another step`;
      p.addEventListener('mousedown',e=>{e.stopPropagation();_startEdgeDrag(e,node.id,i);});
      wrapper.appendChild(p);
      portsDots.appendChild(wrapper);
    });

    portsWrap.appendChild(portsDots);
    el.appendChild(portsWrap);

    hdr.addEventListener('click',()=>openNodeModal(node.id));
    el.addEventListener('mousedown',e=>{if(!e.target.classList.contains('ag-port'))_startNodeDrag(e,node.id);});
  }else if(['input','manager'].includes(node.type||'ai')&&node.status==='running'){
    hdr.addEventListener('click',e=>{
      e.stopPropagation();
      const payload=_pendingRunInput||_runInputPayloadFromNode(node);
      _openAgentInputFromBanner(payload);
    });
  }else if(isRun&&['completed','failed','skipped'].includes(node.status)){
    hdr.style.cursor='pointer';
    hdr.title='Click to inspect node output';
    hdr.addEventListener('click',e=>{e.stopPropagation();_openNodeInspector(node);});
  }
  return el;
}

function _nodeStatusColor(st){return{running:'var(--accent)',completed:'#4caf50',failed:'#e06c75',skipped:'var(--text-dim)',pending:'var(--border-strong)'}[st]||'var(--border-strong)';}
function _nodeStatusIcon(st){return{running:'⟳',completed:'✓',failed:'✗',skipped:'⊘',pending:''}[st]||'';}

// ---------------------------------------------------------------------------
// SVG helpers
// ---------------------------------------------------------------------------

function _drawEdges(svgId,nodes,isRun,pan){
  const svg=document.getElementById(svgId);
  if(!svg) return;
  while(svg.firstChild) svg.removeChild(svg.firstChild);
  const px=(pan||{x:0}).x, py=(pan||{x:0,y:0}).y;
  const map={};nodes.forEach(n=>map[n.id]=n);
  nodes.forEach(parent=>{
    (parent.children||[]).forEach((childId,portIdx)=>{
      const child=map[childId];if(!child) return;
      const c=PORT_COLORS[portIdx%PORT_COLORS.length];
      const isManager=(parent.type||'ai')==='manager';
      // Translate canvas coords → SVG/wrapper coords by adding pan offset
      const x1=isManager?parent.x+px+100:(isRun?parent.x+px+200:parent.x+px+184);
      const y1=isManager?parent.y+py+74:(isRun?parent.y+py+22:parent.y+py+74);
      const x2=isRun?child.x+px:child.x+px+100;
      const y2=isRun?child.y+py+22:child.y+py;
      const dx=Math.abs(x2-x1);
      const path=document.createElementNS('http://www.w3.org/2000/svg','path');
      if(isManager){
        const midY=y1+Math.max((y2-y1)*0.5,50);
        path.setAttribute('d',`M ${x1} ${y1} C ${x1} ${midY}, ${x2} ${midY}, ${x2} ${y2}`);
      }else{
        path.setAttribute('d',`M ${x1} ${y1} C ${x1+Math.max(dx*0.5,60)} ${y1}, ${x2-Math.max(dx*0.5,60)} ${y2}, ${x2} ${y2}`);
      }
      path.setAttribute('fill','none');
      path.setAttribute('stroke',isManager?'var(--text-muted)':c);
      path.setAttribute('stroke-width',isManager?'1.5':'2');
      path.setAttribute('opacity',isManager?'0.45':'0.8');
      if(isManager) path.setAttribute('stroke-dasharray','6,4');
      else if(isRun&&map[childId]?.status==='pending') path.setAttribute('stroke-dasharray','5,4');
      svg.appendChild(path);
      // Arrowhead dot
      const arrow=document.createElementNS('http://www.w3.org/2000/svg','circle');
      arrow.setAttribute('cx',x2);arrow.setAttribute('cy',y2);arrow.setAttribute('r','3');
      arrow.setAttribute('fill',c);
      svg.appendChild(arrow);
    });
  });
}

function _drawGrid(svgId){
  const svg=document.getElementById(svgId);
  if(!svg) return;
  while(svg.firstChild) svg.removeChild(svg.firstChild);
  const ns='http://www.w3.org/2000/svg';
  const defs=document.createElementNS(ns,'defs');
  const pat=document.createElementNS(ns,'pattern');
  pat.setAttribute('id','ag-dot-pat');pat.setAttribute('x','0');pat.setAttribute('y','0');
  pat.setAttribute('width','28');pat.setAttribute('height','28');pat.setAttribute('patternUnits','userSpaceOnUse');
  const circ=document.createElementNS(ns,'circle');
  circ.setAttribute('cx','1');circ.setAttribute('cy','1');circ.setAttribute('r','1');
  circ.setAttribute('fill','var(--border-strong)');
  pat.appendChild(circ);defs.appendChild(pat);svg.appendChild(defs);
  const rect=document.createElementNS(ns,'rect');
  rect.setAttribute('width','100%');rect.setAttribute('height','100%');rect.setAttribute('fill','url(#ag-dot-pat)');
  svg.appendChild(rect);
}

function _applyPan(canvasId,pan){
  const c=document.getElementById(canvasId);
  if(c) c.style.transform=`translate(${pan.x}px,${pan.y}px)`;
}

// ---------------------------------------------------------------------------
// Pan (builder)
// ---------------------------------------------------------------------------

function _setupBuilderPan(){
  const wrap=document.getElementById('agent-canvas-wrap');
  if(!wrap||wrap._agPanSetup) return;
  wrap._agPanSetup=true;
  wrap.addEventListener('mousedown',e=>{
    if(e.target===wrap||e.target.id==='agent-canvas'||e.target.id==='agent-grid-svg'){
      _bPanning=true;_bPanStart={x:e.clientX,y:e.clientY};_bPanOrigin={..._bPan};wrap.style.cursor='grabbing';
    }
  });
  window.addEventListener('mousemove',e=>{
    if(_bPanning){_bPan.x=_bPanOrigin.x+(e.clientX-_bPanStart.x);_bPan.y=_bPanOrigin.y+(e.clientY-_bPanStart.y);_applyPan('agent-canvas',_bPan);}
    if(_edgeDrag) _updateEdgeDragLine(e);
  });
  window.addEventListener('mouseup',e=>{
    if(_bPanning){_bPanning=false;wrap.style.cursor='grab';}
    if(_edgeDrag) _finishEdgeDrag(e);
  });
}

// ---------------------------------------------------------------------------
// Node drag
// ---------------------------------------------------------------------------

function _startNodeDrag(e,nodeId){
  e.preventDefault();
  const node=_builderNodes.find(n=>n.id===nodeId);if(!node) return;
  _nodeDrag={nodeId,startX:e.clientX,startY:e.clientY,origX:node.x,origY:node.y};
  const onMove=ev=>{
    if(!_nodeDrag) return;
    node.x=Math.max(0,_nodeDrag.origX+(ev.clientX-_nodeDrag.startX));
    node.y=Math.max(0,_nodeDrag.origY+(ev.clientY-_nodeDrag.startY));
    const el=document.getElementById('node-'+nodeId);
    if(el){el.style.left=node.x+'px';el.style.top=node.y+'px';}
    _drawEdges('agent-edges-svg',_builderNodes,false,_bPan);
  };
  const onUp=()=>{_nodeDrag=null;window.removeEventListener('mousemove',onMove);window.removeEventListener('mouseup',onUp);};
  window.addEventListener('mousemove',onMove);window.addEventListener('mouseup',onUp);
}

// ---------------------------------------------------------------------------
// Edge drag
// ---------------------------------------------------------------------------

function _startEdgeDrag(e,fromNodeId,portIdx){
  e.preventDefault();
  _edgeDrag={fromNodeId,portIdx};
  const svg=document.getElementById('agent-edges-svg');
  if(svg){
    _tempEdgeLine=document.createElementNS('http://www.w3.org/2000/svg','line');
    _tempEdgeLine.setAttribute('stroke',PORT_COLORS[portIdx]);
    _tempEdgeLine.setAttribute('stroke-width','2');
    _tempEdgeLine.setAttribute('stroke-dasharray','5,4');
    _tempEdgeLine.setAttribute('opacity','0.9');
    svg.appendChild(_tempEdgeLine);
  }
}

function _updateEdgeDragLine(e){
  if(!_edgeDrag||!_tempEdgeLine) return;
  const from=_builderNodes.find(n=>n.id===_edgeDrag.fromNodeId);if(!from) return;
  const x1=from.x+_bPan.x+184,y1=from.y+_bPan.y+34;
  _tempEdgeLine.setAttribute('x1',x1);_tempEdgeLine.setAttribute('y1',y1);
  _tempEdgeLine.setAttribute('x2',e.clientX);_tempEdgeLine.setAttribute('y2',e.clientY);
}

function _finishEdgeDrag(e){
  if(!_edgeDrag) return;
  const els=document.elementsFromPoint(e.clientX,e.clientY);
  let targetId=null;
  for(const el of els){const n=el.closest('.ag-node');if(n&&n.id.startsWith('node-')){targetId=n.id.replace('node-','');break;}}
  if(_tempEdgeLine){_tempEdgeLine.remove();_tempEdgeLine=null;}
  const drag=_edgeDrag;_edgeDrag=null;
  if(targetId&&targetId!==drag.fromNodeId){
    const from=_builderNodes.find(n=>n.id===drag.fromNodeId);
    if(from&&!from.children.includes(targetId)&&from.children.length<3){
      from.children[drag.portIdx]=targetId;
      _renderBuilderCanvas();
    }
  }
}

// ---------------------------------------------------------------------------
// Add / delete nodes
// ---------------------------------------------------------------------------

function agentAddNode(){
  const id=_randomHex(5);
  const workerCount=_builderNodes.filter(n=>(n.type||'ai')!=='manager').length;
  const col=workerCount%4;
  const row=Math.floor(workerCount/4);
  const x=60+(col*240);
  const y=220+(row*180);
  _builderNodes.push({id,title:'New Step',task:'',type:'ai',ai:'claude',children:[],x,y,
    status:'pending',output:null,output_summary:null,error:null,stream_buffer:'',
    session_id:null,started_at:null,completed_at:null,elapsed_seconds:0});
  _ensureBuilderManagerNode();
  _renderBuilderCanvas();
  // Auto-open config for the new node
  setTimeout(()=>openNodeModal(id),50);
}

function deleteAgentNode(){
  if(!_editingNodeId) return;
  const id=_editingNodeId;
  const node=_builderNodes.find(n=>n.id===id);
  if(node&&(node.type||'ai')==='manager'){_showManagerGuard();return;}
  _builderNodes=_builderNodes.filter(n=>n.id!==id);
  _builderNodes.forEach(n=>{n.children=n.children.filter(c=>c!==id);});
  _ensureBuilderManagerNode();
  closeNodeModal();_renderBuilderCanvas();
}

// ---------------------------------------------------------------------------
// Node config modal
// ---------------------------------------------------------------------------

function openNodeModal(nodeId){
  const node=_builderNodes.find(n=>n.id===nodeId);if(!node) return;
  _editingNodeId=nodeId;
  const ti=document.getElementById('node-title-inp');if(ti) ti.value=node.title||'';
  const ty=_ensureNodeTypeSelect();if(ty) ty.value=node.type||'ai';
  // Handle openrouter/model split: node.ai may be "openrouter/anthropic/claude-sonnet-4-5"
  const aiSpec=node.ai||'claude';
  const isOr=aiSpec.startsWith('openrouter/');
  const aiKey=isOr?'openrouter':aiSpec;
  const orModel=isOr?aiSpec.slice('openrouter/'.length):'';
  const ai=document.getElementById('node-ai-sel');
  if(ai){
    _populateNodeAiSelect(()=>{
      ai.value=aiKey;
      _toggleOpenRouterInput(aiKey);
      const mi=document.getElementById('node-or-model-inp');if(mi) mi.value=orModel;
    });
  }
  const tk=document.getElementById('node-task-inp');if(tk) tk.value=node.task||'';
  const mt=document.querySelector('#agent-node-modal .modal-title');
  if(mt) mt.textContent='Configure Step';
  document.getElementById('agent-node-modal').style.display='flex';
  if(ti&&!ti.value) ti.focus();
  else if(tk) tk.focus();
}

function _toggleOpenRouterInput(aiVal){
  const wrap=document.getElementById('node-or-model-wrap');
  if(!wrap) return;
  wrap.style.display=(aiVal==='openrouter')?'block':'none';
}

function _ensureOpenRouterModelInput(){
  if(document.getElementById('node-or-model-wrap')) return;
  const ai=document.getElementById('node-ai-sel');
  if(!ai||!ai.parentElement) return;
  const wrap=document.createElement('div');
  wrap.id='node-or-model-wrap';
  wrap.style.cssText='margin-bottom:8px;display:none';
  const label=document.createElement('label');
  label.textContent='OpenRouter Model';
  label.style.cssText='display:block;font-size:11px;color:var(--text-dim);margin-bottom:4px';
  const inp=document.createElement('input');
  inp.type='text';
  inp.id='node-or-model-inp';
  inp.placeholder='e.g. anthropic/claude-sonnet-4.6  or  openrouter/free';
  inp.style.cssText='width:100%;box-sizing:border-box;background:var(--bg-deep);color:var(--text-main);border:1px solid var(--border-default);border-radius:4px;padding:5px 8px;font-size:12px';
  const hint=document.createElement('div');
  hint.style.cssText='font-size:10px;color:var(--text-dim);margin-top:3px';
  hint.textContent='Full model list: openrouter.ai/models';
  wrap.appendChild(label);wrap.appendChild(inp);wrap.appendChild(hint);
  ai.parentElement.insertBefore(wrap,ai.nextSibling);
}

function _populateNodeAiSelect(cb){
  const sel=document.getElementById('node-ai-sel');if(!sel) return;
  const cur=sel.value;
  const _fill=()=>{
    while(sel.firstChild) sel.removeChild(sel.firstChild);
    const add=(v,t)=>{const o=document.createElement('option');o.value=v;o.textContent=t;sel.appendChild(o);};
    (_availableAis||[{key:'claude',name:'Claude Code'}]).forEach(a=>add(a.key,a.name));
    sel.value=cur||'claude';
    _ensureOpenRouterModelInput();
    if(!sel._orListenerAdded){
      sel.addEventListener('change',()=>_toggleOpenRouterInput(sel.value));
      sel._orListenerAdded=true;
    }
    if(cb) cb();
  };
  if(_availableAis){_fill();}else{_loadAvailableAis(_fill);}
}

function _ensureNodeTypeSelect(){
  let sel=document.getElementById('node-type-sel');
  if(sel) return sel;
  const ai=document.getElementById('node-ai-sel');
  if(!ai||!ai.parentElement) return null;
  const row=document.createElement('div');
  row.style.cssText='margin-bottom:8px';
  const label=document.createElement('label');
  label.textContent='Node Type';
  label.style.cssText='display:block;font-size:11px;color:var(--text-dim);margin-bottom:4px';
  sel=document.createElement('select');
  sel.id='node-type-sel';
  sel.style.cssText='width:100%;background:var(--bg-deep);color:var(--text-main);border:1px solid var(--border-default);border-radius:4px;padding:4px';
  ['ai','shell','http','file','deliver','input','condition','loop','transform','join','manager'].forEach(t=>{
    const opt=document.createElement('option');
    opt.value=t;opt.textContent=t;
    sel.appendChild(opt);
  });
  row.appendChild(label);
  row.appendChild(sel);
  ai.parentElement.insertBefore(row,ai.parentElement.firstChild);
  return sel;
}

function closeNodeModal(){_editingNodeId=null;document.getElementById('agent-node-modal').style.display='none';}

function saveNodeModal(){
  const node=_builderNodes.find(n=>n.id===_editingNodeId);if(!node) return;
  const ti=document.getElementById('node-title-inp');if(ti) node.title=ti.value.trim()||'Step';
  const ty=document.getElementById('node-type-sel');if(ty) node.type=ty.value||'ai';
  const ai=document.getElementById('node-ai-sel');
  if(ai){
    const aiVal=ai.value||'claude';
    if(aiVal==='openrouter'){
      const mi=document.getElementById('node-or-model-inp');
      const model=(mi&&mi.value.trim())||'openrouter/free';
      node.ai='openrouter/'+model;
    } else {
      node.ai=aiVal;
    }
  }
  const tk=document.getElementById('node-task-inp');if(tk) node.task=tk.value;
  closeNodeModal();_renderBuilderCanvas();
}

// ---------------------------------------------------------------------------
// Save agent
// ---------------------------------------------------------------------------

async function saveAgent(){
  const nameInp=document.getElementById('agent-name-inp');
  const name=(nameInp?nameInp.value:'').trim();
  if(!name){nameInp&&nameInp.focus();_flashStatus('Please enter an agent name ↑','#e06c75');return;}
  const descInp=document.getElementById('agent-desc-inp');
  const description=(descInp?descInp.value:'').trim();
  _ensureBuilderManagerNode();
  _renderBuilderCanvas();
  _flashStatus('Saving…','#888');
  const serializeNode=n=>{
    const out={id:n.id,title:n.title,type:n.type||'ai',task:n.task,ai:n.ai,children:n.children,x:n.x,y:n.y};
    AG_NODE_CONFIG_KEYS.forEach(k=>{if(Object.prototype.hasOwnProperty.call(n,k)) out[k]=n[k];});
    return out;
  };
  const body={name,description,
    nodes:_builderNodes.map(serializeNode),
    trigger:_builderTrigger};
  try{
    let res;
    if(_builderAgentId){
      res=await fetch('/api/agents/'+_builderAgentId,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(r=>r.json());
    }else{
      res=await fetch('/api/agents',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(r=>r.json());
    }
    if(res.agent){
      _builderAgentId=res.agent.id;_agents[res.agent.id]=res.agent;_renderAgentsList();
      _flashStatus('✓ Saved','#4caf50');
      _notifyAgentBuilderSaved(res.agent);
    }else{
      _flashStatus('✗ '+(res.error||'save failed'),'#e06c75');
    }
  }catch(err){_flashStatus('✗ Network error','#e06c75');}
}

function _notifyAgentBuilderSaved(agent){
  try{
    if(window.opener && !window.opener.closed && typeof window.opener.loadAgentsPanel==='function'){
      window.opener.loadAgentsPanel();
    }
  }catch(e){}
}

function _flashStatus(msg,color){
  const el=document.getElementById('agent-save-status');
  if(!el) return;
  el.style.color=color;_setText(el,msg);
  setTimeout(()=>_setText(el,''),2500);
}

// ---------------------------------------------------------------------------
// Triggers modal
// ---------------------------------------------------------------------------

function openAgentTriggers(){
  const t=_builderTrigger||_defaultTrigger();
  const tgCb=document.getElementById('trig-telegram');if(tgCb) tgCb.checked=t.telegram!==false;
  const sEn=document.getElementById('trig-schedule-enabled');if(sEn) sEn.checked=!!(t.schedule||{}).enabled;
  const sEx=document.getElementById('trig-schedule-expr');if(sEx){sEx.value=(t.schedule||{}).expression||'';sEx.disabled=!(t.schedule||{}).enabled;}
  const sIn=document.getElementById('trig-schedule-input');if(sIn){sIn.value=(t.schedule||{}).input_data||'';sIn.disabled=!(t.schedule||{}).enabled;}
  const wEn=document.getElementById('trig-webhook-enabled');if(wEn) wEn.checked=!!(t.webhook||{}).enabled;
  const token=(t.webhook||{}).token||'';
  const urlEl=document.getElementById('trig-webhook-url');
  if(urlEl) urlEl.textContent=token?('POST '+window.location.origin+'/api/agents/webhook/'+token):'Webhook URL will appear after first save.';
  document.getElementById('agent-triggers-modal').style.display='flex';
}

function toggleScheduleFields(){
  const en=document.getElementById('trig-schedule-enabled');
  const ex=document.getElementById('trig-schedule-expr');
  const inp=document.getElementById('trig-schedule-input');
  if(en && ex) ex.disabled=!en.checked;
  if(en && inp) inp.disabled=!en.checked;
}

function closeAgentTriggers(){document.getElementById('agent-triggers-modal').style.display='none';}

function saveAgentTriggers(){
  if(!_builderTrigger) _builderTrigger=_defaultTrigger();
  const tgCb=document.getElementById('trig-telegram');_builderTrigger.telegram=tgCb?tgCb.checked:true;
  const sEn=document.getElementById('trig-schedule-enabled');
  const sEx=document.getElementById('trig-schedule-expr');
  const sIn=document.getElementById('trig-schedule-input');
  _builderTrigger.schedule={
    enabled:sEn?sEn.checked:false,
    expression:sEx?sEx.value.trim():'',
    input_data:sIn?sIn.value.trim():null,
    cron:_builderTrigger.schedule?.cron||'',
    next_run:_builderTrigger.schedule?.next_run||null
  };
  const wEn=document.getElementById('trig-webhook-enabled');
  _builderTrigger.webhook={enabled:wEn?wEn.checked:false,token:_builderTrigger.webhook?.token||''};
  closeAgentTriggers();_flashStatus('Triggers saved','#4caf50');
}

// ---------------------------------------------------------------------------
// Generate from description
// ---------------------------------------------------------------------------

function openGenerateDialog(){
  const d=document.getElementById('agent-gen-desc');if(d){d.value='';d.style.display='';}
  const s=document.getElementById('agent-gen-status');if(s){s.textContent='';s.style.color='';}
  const l=document.getElementById('agent-gen-loading');if(l) l.style.display='none';
  const btn=document.getElementById('agent-gen-btn');if(btn) btn.disabled=false;
  const cb=document.getElementById('agent-gen-cancel-btn');if(cb) cb.disabled=false;
  document.getElementById('agent-generate-modal').style.display='flex';
  if(d) d.focus();
}

function closeGenerateDialog(){document.getElementById('agent-generate-modal').style.display='none';}

async function runAgentGenerate(){
  const d=document.getElementById('agent-gen-desc');
  const desc=d?d.value.trim():'';
  if(!desc){if(d) d.focus();return;}
  const btn=document.getElementById('agent-gen-btn');
  const cancelBtn=document.getElementById('agent-gen-cancel-btn');
  const statusEl=document.getElementById('agent-gen-status');
  const loadingEl=document.getElementById('agent-gen-loading');
  _agGenRunning=true;
  if(btn) btn.disabled=true;
  if(cancelBtn) cancelBtn.disabled=true;
  if(d) d.style.display='none';
  if(loadingEl) loadingEl.style.display='block';
  if(statusEl){statusEl.style.color='#888';statusEl.textContent='';}
  try{
    const data=await fetch('/api/agents/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({description:desc})}).then(r=>r.json());
    if(data.nodes&&data.nodes.length){
      _builderNodes=data.nodes.map(n=>({...n,status:'pending',output:null,output_summary:null,error:null,stream_buffer:'',session_id:null,started_at:null,completed_at:null,elapsed_seconds:0}));
      _ensureBuilderManagerNode();
      _builderChatDesc=desc;
      _builderChatHistory=[];
      closeGenerateDialog();_renderBuilderCanvas();
      _flashStatus(`✓ Generated ${_builderNodes.length} steps — click nodes to review`,'#4caf50');
      _openBuilderChat();
      _addBuilderChatBubble('assistant',`I've generated ${_builderNodes.length} nodes for your workflow. Tell me what to change, or click Save if it looks good.`);
    }else{
      if(d) d.style.display='';
      if(loadingEl) loadingEl.style.display='none';
      if(statusEl){statusEl.style.color='#e06c75';statusEl.textContent='✗ '+(data.error||'No steps returned');}
    }
  }catch(err){
    if(d) d.style.display='';
    if(loadingEl) loadingEl.style.display='none';
    if(statusEl){statusEl.style.color='#e06c75';statusEl.textContent='✗ Network error';}
  }
  finally{
    _agGenRunning=false;
    if(btn) btn.disabled=false;
    if(cancelBtn) cancelBtn.disabled=false;
  }
}
