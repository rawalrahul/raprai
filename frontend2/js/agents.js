// ============================================================================
// agents.js — Agent workflow builder + runner UI
// All user-supplied content is escaped via _esc() before DOM insertion.
// ============================================================================

let _agents = {};
let _availableAis = null; // cached from /integrations
let _builderAgentId = null;
let _builderNodes = [];
let _builderTrigger = null;
let _activeRunId = null;
let _activeRunAgentId = null;
let _runNodes = [];
let _agGenRunning = false;
let _bPan = {x:60, y:60};
let _bPanning = false, _bPanStart = {x:0,y:0}, _bPanOrigin = {x:0,y:0};
let _rPan = {x:60, y:60};
let _rPanning = false, _rPanStart = {x:0,y:0}, _rPanOrigin = {x:0,y:0};
let _edgeDrag = null;
let _editingNodeId = null;
let _nodeDrag = null;
let _tempEdgeLine = null;

const PORT_COLORS = ['#f0a500','#4caf50','#a855f7'];
const PORT_LABELS = ['Out 1','Out 2','Out 3'];

function _esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');}
function _setText(el,t){if(el)el.textContent=String(t==null?'':t);}

// ---------------------------------------------------------------------------
// Sidebar
// ---------------------------------------------------------------------------

function _loadAvailableAis(cb){
  if(_availableAis){if(cb) cb();return;}
  fetch('/integrations').then(r=>r.json()).then(list=>{
    // Start with claude (always built-in)
    _availableAis=[{key:'claude',name:'Claude Code'}];
    (list||[]).forEach(i=>{_availableAis.push({key:i.key,name:i.name});});
    if(cb) cb();
  }).catch(()=>{
    _availableAis=[{key:'claude',name:'Claude Code'},{key:'gemini',name:'Gemini'},{key:'ollama',name:'Ollama'}];
    if(cb) cb();
  });
}

function loadAgentsPanel(){
  _loadAvailableAis();
  fetch('/api/agents').then(r=>r.json()).then(data=>{
    _agents={};
    (data.agents||[]).forEach(a=>{_agents[a.id]=a;});
    _renderAgentsList();
    const cnt=document.getElementById('sb-count-agents');
    if(cnt) _setText(cnt, Object.keys(_agents).length||'');
  }).catch(()=>{
    const el=document.getElementById('agents-list');
    if(el){el.textContent='';const d=document.createElement('div');d.className='sb-empty';d.textContent='Failed to load';el.appendChild(d);}
  });
}

function _renderAgentsList(){
  const el=document.getElementById('agents-list');
  if(!el) return;
  el.textContent='';
  const list=Object.values(_agents).sort((a,b)=>(b.created_at||0)-(a.created_at||0));
  if(!list.length){
    const d=document.createElement('div');d.className='sb-empty';d.textContent='No agents yet.';el.appendChild(d);return;
  }
  list.forEach(ag=>el.appendChild(_buildAgentCard(ag)));
}

function _buildAgentCard(ag){
  const wrap=document.createElement('div');wrap.className='sb-item';wrap.style.cssText='padding:6px 8px';
  const row1=document.createElement('div');row1.style.cssText='display:flex;align-items:center;gap:4px;min-width:0';
  const nm=document.createElement('span');nm.style.cssText='flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px';_setText(nm,ag.name);row1.appendChild(nm);
  const tc=ag.trigger||{};
  if(tc.telegram) row1.appendChild(_badge('TG','#2a3a2a','#5a9a5a'));
  if((tc.schedule||{}).enabled) row1.appendChild(_badge('⏰','#3a2a1a','#c8844a'));
  if((tc.webhook||{}).enabled) row1.appendChild(_badge('⊙','#1a2a3a','#4a8ac8'));
  wrap.appendChild(row1);
  const row2=document.createElement('div');row2.style.cssText='display:flex;align-items:center;gap:4px;margin-top:3px';
  const meta=document.createElement('span');meta.style.cssText='font-size:10px;color:var(--dim)';
  const lr=ag.last_run_at?new Date(ag.last_run_at*1000).toLocaleDateString():'never';
  _setText(meta,`${ag.node_count} steps · ${ag.run_count} runs · ${lr}`);
  row2.appendChild(meta);const sp=document.createElement('div');sp.style.flex='1';row2.appendChild(sp);
  const rb=_iconBtn('▶','Run','var(--acc)');rb.onclick=()=>runAgentNow(ag.id);
  const eb=_iconBtn('✎','Edit','var(--dim)');eb.onclick=()=>openAgentBuilder(ag.id);
  const db=_iconBtn('✕','Delete','#e06c75');db.onclick=()=>deleteAgent(ag.id);
  row2.appendChild(rb);row2.appendChild(eb);row2.appendChild(db);wrap.appendChild(row2);return wrap;
}

function _badge(text,bg,color){const s=document.createElement('span');s.style.cssText=`font-size:9px;padding:1px 5px;border-radius:8px;background:${bg};color:${color}`;s.textContent=text;return s;}
function _iconBtn(icon,title,color){const b=document.createElement('button');b.style.cssText=`font-size:10px;padding:2px 6px;border-radius:3px;background:var(--inp);border:1px solid var(--border);color:${color};cursor:pointer`;b.title=title;b.textContent=icon;return b;}

function runAgentNow(agentId){
  fetch('/api/agents/'+agentId+'/run',{method:'POST'}).then(r=>r.json()).then(data=>{
    if(data.run) openAgentRunOverlay(data.run);
  }).catch(err=>alert('Failed to start: '+err));
}

function deleteAgent(agentId){
  if(!confirm('Delete this agent and all its run history?')) return;
  fetch('/api/agents/'+agentId,{method:'DELETE'}).then(()=>{delete _agents[agentId];_renderAgentsList();});
}

// ---------------------------------------------------------------------------
// Builder open / close
// ---------------------------------------------------------------------------

function openAgentBuilder(agentId){
  _builderAgentId=agentId;
  const overlay=document.getElementById('agent-builder-overlay');
  overlay.style.display='flex';
  const nameInp=document.getElementById('agent-name-inp');
  const descInp=document.getElementById('agent-desc-inp');
  if(agentId&&_agents[agentId]){
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
  _renderBuilderCanvas();
  _setupBuilderPan();
}

function closeAgentBuilder(){
  document.getElementById('agent-builder-overlay').style.display='none';
  _builderAgentId=null;_builderNodes=[];
}

function _defaultTrigger(){return{telegram:true,schedule:{enabled:false,expression:'',cron:'',next_run:null},webhook:{enabled:false,token:''}};}

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
    hint.appendChild(_hintLine('Start building your agent workflow','font-size:15px;font-weight:600;color:#555;margin-bottom:10px'));
    hint.appendChild(_hintLine('Click  ✦ Generate  to create steps from a description','font-size:12px;color:#666;margin-bottom:6px'));
    hint.appendChild(_hintLine('— or —','font-size:11px;color:#444;margin-bottom:6px'));
    hint.appendChild(_hintLine('Click  + Node  in the toolbar to add a step manually','font-size:12px;color:#666'));
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
      tip.style.cssText='position:absolute;bottom:14px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.75);color:#aaa;font-size:11px;padding:6px 14px;border-radius:20px;pointer-events:none;z-index:20;white-space:nowrap';
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
    isRunning?'background:#0d1b2a':'background:#1c1c1c',
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
  aiChip.style.cssText='font-size:9px;padding:1px 5px;border-radius:4px;background:#2a2a2a;color:#888;flex-shrink:0;text-transform:uppercase;letter-spacing:.4px';
  aiChip.textContent=node.ai||'claude';

  const titleSpan=document.createElement('span');
  titleSpan.style.cssText='font-size:12px;font-weight:600;color:#e0e0e0;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap';
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

  titleRow.appendChild(aiChip);
  titleRow.appendChild(titleSpan);
  hdr.appendChild(titleRow);

  if(!isRun){
    // Task preview or "click to configure" hint
    const preview=document.createElement('div');
    if(hasTask){
      preview.style.cssText='font-size:10px;color:#777;line-height:1.4;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;margin-top:2px';
      preview.textContent=node.task.slice(0,120);
    }else{
      preview.style.cssText='font-size:10px;color:#555;font-style:italic;margin-top:2px';
      preview.textContent='Click to add instructions…';
    }
    hdr.appendChild(preview);
  }

  if(isRun&&node.status==='running'){
    const buf=document.createElement('div');buf.className='ag-stream-buf';
    buf.style.cssText='font-size:9px;color:#666;margin-top:4px;max-height:36px;overflow:hidden;font-family:monospace;line-height:1.3';
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
  el.appendChild(hdr);

  if(!isRun){
    // ── Output ports row ──
    const portsWrap=document.createElement('div');
    portsWrap.style.cssText='border-top:1px solid #252525;padding:5px 10px 6px;display:flex;justify-content:space-between;align-items:center';

    const portsLabel=document.createElement('span');
    portsLabel.style.cssText='font-size:9px;color:#444';
    portsLabel.textContent='outputs →';
    portsWrap.appendChild(portsLabel);

    const portsDots=document.createElement('div');
    portsDots.style.cssText='display:flex;gap:10px;align-items:center';

    PORT_COLORS.forEach((c,i)=>{
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
  }
  return el;
}

function _nodeStatusColor(st){return{running:'#4a9eff',completed:'#4caf50',failed:'#e06c75',skipped:'#555',pending:'#3a3a3a'}[st]||'#3a3a3a';}
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
      // Translate canvas coords → SVG/wrapper coords by adding pan offset
      const x1=parent.x+px+184, y1=parent.y+py+74; // right side of port row (port dots center)
      const x2=child.x+px+100,  y2=child.y+py;      // top-center of child node
      const dx=Math.abs(x2-x1);
      const path=document.createElementNS('http://www.w3.org/2000/svg','path');
      path.setAttribute('d',`M ${x1} ${y1} C ${x1+Math.max(dx*0.5,60)} ${y1}, ${x2-Math.max(dx*0.5,60)} ${y2}, ${x2} ${y2}`);
      path.setAttribute('fill','none');
      path.setAttribute('stroke',c);
      path.setAttribute('stroke-width','2');
      path.setAttribute('opacity','0.8');
      if(isRun&&map[childId]?.status==='pending') path.setAttribute('stroke-dasharray','5,4');
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
  circ.setAttribute('fill','#333');
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
  const col=_builderNodes.length%4;
  const row=Math.floor(_builderNodes.length/4);
  const x=60+(col*240);
  const y=60+(row*180);
  _builderNodes.push({id,title:'New Step',task:'',ai:'claude',children:[],x,y,
    status:'pending',output:null,output_summary:null,error:null,stream_buffer:'',
    session_id:null,started_at:null,completed_at:null,elapsed_seconds:0});
  _renderBuilderCanvas();
  // Auto-open config for the new node
  setTimeout(()=>openNodeModal(id),50);
}

function deleteAgentNode(){
  if(!_editingNodeId) return;
  const id=_editingNodeId;
  _builderNodes=_builderNodes.filter(n=>n.id!==id);
  _builderNodes.forEach(n=>{n.children=n.children.filter(c=>c!==id);});
  closeNodeModal();_renderBuilderCanvas();
}

// ---------------------------------------------------------------------------
// Node config modal
// ---------------------------------------------------------------------------

function openNodeModal(nodeId){
  const node=_builderNodes.find(n=>n.id===nodeId);if(!node) return;
  _editingNodeId=nodeId;
  const ti=document.getElementById('node-title-inp');if(ti) ti.value=node.title||'';
  const ai=document.getElementById('node-ai-sel');if(ai){_populateNodeAiSelect();ai.value=node.ai||'claude';}
  const tk=document.getElementById('node-task-inp');if(tk) tk.value=node.task||'';
  // Update modal title
  const mt=document.querySelector('#agent-node-modal .modal-title');
  if(mt) mt.textContent='Configure Step';
  document.getElementById('agent-node-modal').style.display='flex';
  // Focus the title if empty
  if(ti&&!ti.value) ti.focus();
  else if(tk) tk.focus();
}

function _populateNodeAiSelect(){
  const sel=document.getElementById('node-ai-sel');if(!sel) return;
  const cur=sel.value;
  const _fill=()=>{
    while(sel.firstChild) sel.removeChild(sel.firstChild);
    const add=(v,t)=>{const o=document.createElement('option');o.value=v;o.textContent=t;sel.appendChild(o);};
    (_availableAis||[{key:'claude',name:'Claude Code'}]).forEach(a=>add(a.key,a.name));
    sel.value=cur||'claude';
  };
  if(_availableAis){_fill();}else{_loadAvailableAis(_fill);}
}

function closeNodeModal(){_editingNodeId=null;document.getElementById('agent-node-modal').style.display='none';}

function saveNodeModal(){
  const node=_builderNodes.find(n=>n.id===_editingNodeId);if(!node) return;
  const ti=document.getElementById('node-title-inp');if(ti) node.title=ti.value.trim()||'Step';
  const ai=document.getElementById('node-ai-sel');if(ai) node.ai=ai.value||'claude';
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
  _flashStatus('Saving…','#888');
  const body={name,description,
    nodes:_builderNodes.map(n=>({id:n.id,title:n.title,task:n.task,ai:n.ai,children:n.children,x:n.x,y:n.y})),
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
    }else{
      _flashStatus('✗ '+(res.error||'save failed'),'#e06c75');
    }
  }catch(err){_flashStatus('✗ Network error','#e06c75');}
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
  const wEn=document.getElementById('trig-webhook-enabled');if(wEn) wEn.checked=!!(t.webhook||{}).enabled;
  const token=(t.webhook||{}).token||'';
  const urlEl=document.getElementById('trig-webhook-url');
  if(urlEl) urlEl.textContent=token?('POST '+window.location.origin+'/api/agents/webhook/'+token):'Webhook URL will appear after first save.';
  document.getElementById('agent-triggers-modal').style.display='flex';
}

function toggleScheduleFields(){
  const en=document.getElementById('trig-schedule-enabled');
  const ex=document.getElementById('trig-schedule-expr');
  if(en&&ex) ex.disabled=!en.checked;
}

function closeAgentTriggers(){document.getElementById('agent-triggers-modal').style.display='none';}

function saveAgentTriggers(){
  if(!_builderTrigger) _builderTrigger=_defaultTrigger();
  const tgCb=document.getElementById('trig-telegram');_builderTrigger.telegram=tgCb?tgCb.checked:true;
  const sEn=document.getElementById('trig-schedule-enabled');
  const sEx=document.getElementById('trig-schedule-expr');
  _builderTrigger.schedule={enabled:sEn?sEn.checked:false,expression:sEx?sEx.value.trim():'',cron:_builderTrigger.schedule?.cron||'',next_run:_builderTrigger.schedule?.next_run||null};
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
      closeGenerateDialog();_renderBuilderCanvas();
      _flashStatus(`✓ Generated ${_builderNodes.length} steps — click nodes to review`,'#4caf50');
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

// ---------------------------------------------------------------------------
// Live run overlay
// ---------------------------------------------------------------------------

let _runPollTimer = null;

function openAgentRunOverlay(run){
  _activeRunId=run.id;_activeRunAgentId=run.agent_id;_runNodes=run.nodes||[];
  const t=document.getElementById('agent-run-title');
  if(t) _setText(t,run.agent_name+' — Run '+run.id.slice(0,8));
  _updateRunOverlayStatus(run);
  document.getElementById('agent-run-overlay').style.display='flex';
  _rPan={x:60,y:60};_renderRunCanvas();_setupRunPan();
  _startRunPoll(run.id);
}

function closeAgentRunOverlay(){
  document.getElementById('agent-run-overlay').style.display='none';
  _activeRunId=null;_runNodes=[];
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
        if(data.run.status!=='running') _stopRunPoll();
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
    const colors={running:'#4a9eff',completed:'#4caf50',failed:'#e06c75',cancelled:'#888'};
    const c=colors[run.status]||'#888';
    badge.style.background=c+'22';badge.style.color=c;badge.textContent=run.status;
  }
  if(cancelBtn){
    cancelBtn.style.display=run.status==='running'?'':'none';
    cancelBtn.disabled=false;cancelBtn.textContent='Stop';
  }
  if(progEl){
    const total=prog.total||_runNodes.length;
    const done=(prog.completed||0)+(prog.failed||0)+(prog.skipped||0);
    const running=(prog.running||0)||_runNodes.filter(n=>n.status==='running').length;
    const label=running>0?`Step ${done+1}/${total} running`:done+'/'+total+' steps';
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
    _runNodes=run.nodes||[];_updateRunOverlayStatus(run);_renderRunCanvas();
  }
  if(run.status==='running'&&!_activeRunId) openAgentRunOverlay(run);
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

function _fixCanvasBg(){
  ['agent-builder-overlay','agent-run-overlay','agent-canvas-wrap'].forEach(id=>{
    const el=document.getElementById(id);
    if(el) el.style.background='#111';
  });
  const canvas=document.getElementById('agent-canvas');
  if(canvas) canvas.style.background='#111';
  const runCanvas=document.getElementById('agent-run-canvas');
  if(runCanvas) runCanvas.style.background='#111';
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

(function _agentsInit(){
  function _hookAgentsSection(){
    const section=document.querySelector('[data-section="agents"]');
    if(!section) return;
    const obs=new MutationObserver(()=>{
      if(section.classList.contains('open')&&!section.dataset.agLoaded){
        section.dataset.agLoaded='1';loadAgentsPanel();
      }
    });
    obs.observe(section,{attributes:true});
    if(section.classList.contains('open')) loadAgentsPanel();
  }
  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',_hookAgentsSection);
  }else{
    _hookAgentsSection();
  }

  // Fix canvas background on builder open
  const origOpen=window.openAgentBuilder;
  // Patch after DOM ready so the overlay elements exist
  document.addEventListener('DOMContentLoaded',()=>{
    const overlay=document.getElementById('agent-builder-overlay');
    if(overlay){
      const obs2=new MutationObserver(()=>{
        if(overlay.style.display!=='none') _fixCanvasBg();
      });
      obs2.observe(overlay,{attributes:true,attributeFilter:['style']});
    }
  });
})();
