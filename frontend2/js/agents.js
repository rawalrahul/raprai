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
let _runWindows = {}; // run_id → window reference for runs opened in separate windows
let _agGenRunning = false;
let _bPan = {x:60, y:60};
let _bPanning = false, _bPanStart = {x:0,y:0}, _bPanOrigin = {x:0,y:0};
let _rPan = {x:60, y:60};
let _rPanning = false, _rPanStart = {x:0,y:0}, _rPanOrigin = {x:0,y:0};
let _edgeDrag = null;
let _editingNodeId = null;
let _nodeDrag = null;
let _tempEdgeLine = null;
let _builderChatHistory = [];
let _builderChatSending = false;
let _builderChatDesc = '';

const PORT_COLORS = ['#f0a500','#4caf50','#a855f7'];
const PORT_LABELS = ['Out 1','Out 2','Out 3'];
const AG_NODE_CONFIG_KEYS = [
  'timeout','http_method','http_url','http_headers','http_body',
  'file_op','file_path','deliver_channel','deliver_to','deliver_subject',
  'input_timeout','loop_max','retry_max',
  'transform_op','transform_key','transform_pattern','transform_length',
  'env_vars',
  'manager_max_iter',
  'join_separator',
];

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
  const tb=_iconBtn('⚗','Test Run (dry)','#8b5cf6');tb.onclick=()=>runAgentNow(ag.id,true);
  const eb=_iconBtn('✎','Edit','var(--dim)');eb.onclick=()=>openAgentBuilderWindow(ag.id);
  const vb=_iconBtn('⏱','Versions','#c8844a');vb.onclick=()=>_openVersionsModal(ag.id);
  const xb=_iconBtn('↓','Export JSON','var(--dim)');xb.onclick=()=>_exportAgent(ag.id,ag.name);
  const db=_iconBtn('✕','Delete','#e06c75');db.onclick=()=>deleteAgent(ag.id);
  row2.appendChild(rb);row2.appendChild(tb);row2.appendChild(eb);row2.appendChild(vb);row2.appendChild(xb);row2.appendChild(db);wrap.appendChild(row2);return wrap;
}

function _badge(text,bg,color){const s=document.createElement('span');s.style.cssText=`font-size:9px;padding:1px 5px;border-radius:8px;background:${bg};color:${color}`;s.textContent=text;return s;}
function _iconBtn(icon,title,color){const b=document.createElement('button');b.style.cssText=`font-size:10px;padding:2px 6px;border-radius:3px;background:var(--inp);border:1px solid var(--border);color:${color};cursor:pointer`;b.title=title;b.textContent=icon;return b;}

function _openAgentRunWindow(run){
  if(!run||!run.id) return;
  const url='/agent-run/'+encodeURIComponent(run.id);
  const win=window.open(url,'agent-run-'+run.id,'width=1280,height=760');
  if(!win){
    openAgentRunOverlay(run);
    return;
  }
  _runWindows[run.id]=win;
  _flashStatus('Agent run opened in a separate window','#4caf50');
}

function _runHasInputNode(run){
  return !!(run&&Array.isArray(run.nodes)&&run.nodes.some(n=>(n.type||'ai')==='input'));
}

function _builderManagerTitle(){
  const nameInp=document.getElementById('agent-name-inp');
  const name=(nameInp&&nameInp.value||'').trim();
  return name||'Manager Review';
}

function _workflowRootNodes(nodes){
  const childIds=new Set();
  (nodes||[]).forEach(n=>{
    if((n.type||'ai')==='manager') return;
    (n.children||[]).forEach(id=>childIds.add(id));
  });
  return (nodes||[]).filter(n=>(n.type||'ai')!=='manager'&&!childIds.has(n.id));
}

function _ensureBuilderManagerNode(){
  if(!_builderNodes||!_builderNodes.length) return;
  const title=_builderManagerTitle();
  const managers=_builderNodes.filter(n=>(n.type||'ai')==='manager');
  let manager=managers[0];
  if(!manager){
    const nonManagers=_builderNodes.filter(n=>(n.type||'ai')!=='manager');
    const minX=nonManagers.length?Math.min(...nonManagers.map(n=>Number(n.x)||100)):100;
    const maxX=nonManagers.length?Math.max(...nonManagers.map(n=>Number(n.x)||100)):100;
    const minY=nonManagers.length?Math.min(...nonManagers.map(n=>Number(n.y)||100)):100;
    manager={
      id:_randomHex(10),
      title,
      type:'manager',
      ai:'claude',
      task:'Review the full workflow result with the user. Ask if they are happy with the output. If not, collect the issue, identify the node most responsible, improve that node, and rerun the workflow.',
      children:[],
      x:(minX+maxX)/2,
      y:Math.max(20,minY-170),
      manager_max_iter:3,
      input_timeout:3600,
      deliver_channel:'ui',
      status:'pending',output:null,output_summary:null,error:null,stream_buffer:'',
      session_id:null,started_at:null,completed_at:null,elapsed_seconds:0
    };
    _builderNodes.push(manager);
  }
  managers.slice(1).forEach(extra=>{
    _builderNodes=_builderNodes.filter(n=>n.id!==extra.id);
  });
  manager.title=title;
  manager.type='manager';
  manager.ai=manager.ai||'claude';
  manager.children=[];
  manager.manager_max_iter=manager.manager_max_iter||3;
  manager.input_timeout=manager.input_timeout||3600;
  manager.deliver_channel=manager.deliver_channel||'ui';

  const managerId=manager.id;
  const nonManagers=_builderNodes.filter(n=>n.id!==managerId);
  nonManagers.forEach(n=>{
    n.children=(n.children||[]).filter(id=>id!==managerId);
  });
  if(nonManagers.length){
    const minX=Math.min(...nonManagers.map(n=>Number(n.x)||100));
    const maxX=Math.max(...nonManagers.map(n=>Number(n.x)||100));
    const minY=Math.min(...nonManagers.map(n=>Number(n.y)||100));
    manager.x=(minX+maxX)/2;
    manager.y=Math.max(20,minY-170);
  }
  const roots=_workflowRootNodes(_builderNodes);
  manager.children=(roots.length?roots:nonManagers.slice(0,1)).map(n=>n.id);
}

function openAgentBuilderWindow(agentId){
  if(!agentId){
    openAgentBuilder(null);
    return;
  }
  const params=new URLSearchParams();
  params.set('agent_builder',agentId?'edit':'new');
  if(agentId) params.set('agent_id',agentId);
  const url='/?'+params.toString();
  const win=window.open(url,'agent-builder-'+(agentId||'new'),'width=1440,height=860');
  if(!win){
    openAgentBuilder(agentId||null);
    return;
  }
  _flashStatus('Agent builder opened in a separate window','#4caf50');
}

async function runAgentNow(agentId, dryRun=false){
  try{
    const body=dryRun?{dry_run:true}:{};
    const opts={method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)};
    let data=await fetch('/api/agents/'+agentId+'/run',opts).then(r=>r.json());
    if(data.needs_input){
      const input=await _safeCollectAgentInput(data.question||'This agent needs input to start. Please provide it:');
      if(input===null) return;
      data=await fetch('/api/agents/'+agentId+'/run',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({input_data:input,dry_run:dryRun})
      }).then(r=>r.json());
    }
    if(data.run){
      if(_runHasInputNode(data.run)) openAgentRunOverlay(data.run);
      else _openAgentRunWindow(data.run);
    }
    else if(data.error) alert(data.error);
  }catch(err){alert('Failed to start: '+err);}
}

function deleteAgent(agentId){
  if(!confirm('Delete this agent and all its run history?')) return;
  fetch('/api/agents/'+agentId,{method:'DELETE'}).then(()=>{delete _agents[agentId];_renderAgentsList();});
}

// ---------------------------------------------------------------------------
// Export / Import (frontend2 — same API as helm/frontend/agents.js)
// ---------------------------------------------------------------------------

function _exportAgent(agentId, agentName){
  fetch('/api/agents/'+agentId+'/export')
    .then(r=>r.blob())
    .then(blob=>{
      const url=URL.createObjectURL(blob);
      const a=document.createElement('a');
      a.href=url;
      const safe=(agentName||'agent').replace(/[^a-zA-Z0-9_\- ]/g,'_');
      a.download=safe+'.json';
      document.body.appendChild(a);a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    });
}

function _importAgentFromFile(){
  const inp=document.createElement('input');
  inp.type='file';inp.accept='.json,application/json';
  inp.style.display='none';
  inp.addEventListener('cancel',()=>inp.remove());
  inp.onchange=async()=>{
    const file=inp.files[0];if(!file) return;
    try{
      const text=await file.text();
      const data=JSON.parse(text);
      const res=await fetch('/api/agents/import',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify(data),
      }).then(r=>r.json());
      if(res.error){alert('Import failed: '+res.error);return;}
      const list=await fetch('/api/agents').then(r=>r.json());
      (list.agents||[]).forEach(a=>{_agents[a.id]=a;});
      _renderAgentsList();
      alert('Imported: '+res.name);
    }catch(e){alert('Import failed: '+e);}
    finally{inp.remove();}
  };
  document.body.appendChild(inp);
  inp.click();
}

async function _openVersionsModal(agentId){
  let modal=document.getElementById('ag-versions-modal');
  if(!modal){
    modal=document.createElement('div');
    modal.id='ag-versions-modal';
    modal.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:9999;display:flex;align-items:center;justify-content:center';
    modal.addEventListener('click',e=>{if(e.target===modal) modal.style.display='none';});
    const box=document.createElement('div');
    box.style.cssText='background:var(--bg-surface);border:1px solid var(--border-default);border-radius:8px;width:480px;max-width:95vw;max-height:70vh;display:flex;flex-direction:column;overflow:hidden';
    const hdr=document.createElement('div');
    hdr.style.cssText='display:flex;align-items:center;justify-content:space-between;padding:10px 14px;border-bottom:1px solid var(--border-subtle)';
    const title=document.createElement('span');title.id='ag-ver-title';title.style.cssText='font-size:13px;font-weight:600;color:var(--text-main)';
    const cls=document.createElement('button');cls.textContent='✕';cls.style.cssText='background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:14px';cls.onclick=()=>modal.style.display='none';
    hdr.appendChild(title);hdr.appendChild(cls);
    const list=document.createElement('div');list.id='ag-ver-list';list.style.cssText='padding:8px 14px;overflow-y:auto;flex:1';
    box.appendChild(hdr);box.appendChild(list);modal.appendChild(box);document.body.appendChild(modal);
  }
  modal.style.display='flex';
  const agName=(_agents[agentId]||{}).name||agentId;
  document.getElementById('ag-ver-title').textContent='Versions — '+agName;
  const list=document.getElementById('ag-ver-list');
  while(list.firstChild) list.removeChild(list.firstChild);
  const loading=document.createElement('div');loading.style.cssText='color:var(--text-dim);font-size:11px;padding:8px 0';loading.textContent='Loading…';list.appendChild(loading);
  try{
    const data=await fetch('/api/agents/'+agentId+'/versions').then(r=>r.json());
    while(list.firstChild) list.removeChild(list.firstChild);
    const versions=data.versions||[];
    if(!versions.length){const em=document.createElement('div');em.style.cssText='color:var(--text-dim);font-size:11px;padding:8px 0';em.textContent='No versions yet.';list.appendChild(em);return;}
    versions.forEach((v,idx)=>{
      const row=document.createElement('div');row.style.cssText='display:flex;align-items:center;justify-content:space-between;padding:7px 0;border-bottom:1px solid var(--border-subtle)';
      const label=document.createElement('span');label.style.cssText='font-size:11px;color:var(--text-muted)';label.textContent=`v${v.version_num} — ${v.saved_at?new Date(v.saved_at*1000).toLocaleString():'?'}`;
      if(idx===0){const cur=document.createElement('span');cur.style.cssText='font-size:9px;color:#4caf50;margin-left:6px';cur.textContent='current';label.appendChild(cur);}
      row.appendChild(label);
      if(idx>0){
        const btn=document.createElement('button');btn.textContent='Restore';btn.style.cssText='font-size:10px;padding:2px 8px;border-radius:3px;background:var(--bg-elevated);border:1px solid #c8844a;color:#c8844a;cursor:pointer';
        btn.onclick=async()=>{
          if(!confirm('Restore to v'+v.version_num+'?')) return;
          const res=await fetch('/api/agents/'+agentId+'/versions/'+v.id+'/restore',{method:'POST'}).then(r=>r.json());
          if(res.error){alert('Restore failed: '+res.error);return;}
          if(res.agent) _agents[agentId]=res.agent;
          modal.style.display='none';_renderAgentsList();alert('Restored to v'+v.version_num);
        };
        row.appendChild(btn);
      }
      list.appendChild(row);
    });
  }catch(e){while(list.firstChild) list.removeChild(list.firstChild);const err=document.createElement('div');err.style.cssText='color:#e06c75;font-size:11px';err.textContent='Error: '+e;list.appendChild(err);}
}

async function _openMonitorDashboard(){
  let modal=document.getElementById('ag-monitor-modal');
  if(!modal){
    modal=document.createElement('div');modal.id='ag-monitor-modal';modal.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:9999;display:flex;align-items:center;justify-content:center';
    modal.addEventListener('click',e=>{if(e.target===modal) modal.style.display='none';});
    const box=document.createElement('div');box.style.cssText='background:var(--bg-surface);border:1px solid var(--border-default);border-radius:8px;width:800px;max-width:97vw;max-height:80vh;display:flex;flex-direction:column;overflow:hidden';
    const hdr=document.createElement('div');hdr.style.cssText='display:flex;align-items:center;justify-content:space-between;padding:10px 16px;border-bottom:1px solid var(--border-subtle)';
    const title=document.createElement('span');title.style.cssText='font-size:14px;font-weight:700;color:var(--text-main)';title.textContent='Agent Monitor';
    const cls=document.createElement('button');cls.textContent='✕';cls.style.cssText='background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:14px';cls.onclick=()=>modal.style.display='none';
    hdr.appendChild(title);hdr.appendChild(cls);
    const body=document.createElement('div');body.id='ag-monitor-body';body.style.cssText='padding:14px 16px;overflow-y:auto;flex:1';
    box.appendChild(hdr);box.appendChild(body);modal.appendChild(box);document.body.appendChild(modal);
  }
  modal.style.display='flex';
  const body=document.getElementById('ag-monitor-body');while(body.firstChild) body.removeChild(body.firstChild);
  const loading=document.createElement('div');loading.style.cssText='color:var(--text-dim);font-size:11px';loading.textContent='Loading…';body.appendChild(loading);
  try{
    const data=await fetch('/api/agents/stats').then(r=>r.json());
    while(body.firstChild) body.removeChild(body.firstChild);
    const t=data.totals||{};
    const banner=document.createElement('div');banner.style.cssText='display:flex;gap:20px;margin-bottom:16px;flex-wrap:wrap';
    const stat=(label,val,color)=>{const d=document.createElement('div');d.style.cssText='text-align:center;min-width:80px';const v=document.createElement('div');v.style.cssText=`font-size:22px;font-weight:700;color:${color||'var(--text-main)'}`;v.textContent=val==null?'—':val;const l=document.createElement('div');l.style.cssText='font-size:10px;color:var(--text-dim);margin-top:2px';l.textContent=label;d.appendChild(v);d.appendChild(l);return d;};
    banner.appendChild(stat('Total Runs',t.total_runs,'#4a9eff'));banner.appendChild(stat('Successful',t.ok_runs,'#4caf50'));banner.appendChild(stat('Failed',t.fail_runs,'#e06c75'));banner.appendChild(stat('Success Rate',t.success_rate!=null?(t.success_rate*100).toFixed(1)+'%':null,'#f5a623'));
    body.appendChild(banner);
    const table=document.createElement('table');table.style.cssText='width:100%;border-collapse:collapse;font-size:11px';
    const thead=document.createElement('thead');const hr=document.createElement('tr');
    ['Agent','Runs','OK','Fail','Rate','Avg (s)','Last Run','Status'].forEach(h=>{const th=document.createElement('th');th.style.cssText='text-align:left;padding:5px 8px;color:var(--text-dim);border-bottom:1px solid var(--border-subtle);font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:.4px';th.textContent=h;hr.appendChild(th);});
    thead.appendChild(hr);table.appendChild(thead);
    const tbody=document.createElement('tbody');
    (data.agents||[]).forEach((ag,i)=>{
      const tr=document.createElement('tr');tr.style.background=i%2===0?'var(--bg-deep)':'var(--bg-surface)';
      const cell=(val,color)=>{const td=document.createElement('td');td.style.cssText=`padding:6px 8px;color:${color||'var(--text-muted)'};`;td.textContent=val==null?'—':val;return td;};
      const statusColor={'completed':'#4caf50','failed':'#e06c75','running':'#4a9eff'}[ag.last_status]||'#888';
      const rate=ag.success_rate!=null?(ag.success_rate*100).toFixed(0)+'%':null;
      const rateColor=ag.success_rate!=null?(ag.success_rate>=0.9?'#4caf50':ag.success_rate>=0.7?'#f5a623':'#e06c75'):'#888';
      tr.appendChild(cell(ag.name));tr.appendChild(cell(ag.total_runs,'var(--text-main)'));tr.appendChild(cell(ag.ok_runs,'#4caf50'));tr.appendChild(cell(ag.fail_runs,ag.fail_runs>0?'#e06c75':'#4caf50'));tr.appendChild(cell(rate,rateColor));tr.appendChild(cell(ag.avg_duration,'var(--text-main)'));tr.appendChild(cell(ag.last_run_at?new Date(ag.last_run_at*1000).toLocaleDateString():'never','var(--text-dim)'));tr.appendChild(cell(ag.last_status||'—',statusColor));tbody.appendChild(tr);
    });
    table.appendChild(tbody);body.appendChild(table);
  }catch(e){while(body.firstChild) body.removeChild(body.firstChild);const err=document.createElement('div');err.style.cssText='color:#e06c75;font-size:11px';err.textContent='Error: '+e;body.appendChild(err);}
}

function _openNodeInspector(node){
  let modal=document.getElementById('ag-inspector-modal');
  if(!modal){
    modal=document.createElement('div');modal.id='ag-inspector-modal';modal.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:9999;display:flex;align-items:center;justify-content:center';
    modal.addEventListener('click',e=>{if(e.target===modal) modal.style.display='none';});
    const box=document.createElement('div');box.style.cssText='background:var(--bg-surface);border:1px solid var(--border-default);border-radius:8px;width:680px;max-width:95vw;max-height:80vh;display:flex;flex-direction:column;overflow:hidden';
    const hdr=document.createElement('div');hdr.style.cssText='display:flex;align-items:center;justify-content:space-between;padding:10px 14px;border-bottom:1px solid var(--border-subtle)';
    const title=document.createElement('span');title.id='ag-insp-title';title.style.cssText='font-size:13px;font-weight:600;color:var(--text-main)';
    const cls=document.createElement('button');cls.textContent='✕';cls.style.cssText='background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:14px';cls.onclick=()=>modal.style.display='none';
    hdr.appendChild(title);hdr.appendChild(cls);
    const body=document.createElement('div');body.id='ag-insp-body';body.style.cssText='padding:12px 14px;overflow-y:auto;flex:1;font-size:11px;color:var(--text-muted);line-height:1.5';
    box.appendChild(hdr);box.appendChild(body);modal.appendChild(box);document.body.appendChild(modal);
  }
  modal.style.display='flex';
  document.getElementById('ag-insp-title').textContent=`${node.title||'Node'} — ${node.status}`;
  const body=document.getElementById('ag-insp-body');while(body.firstChild) body.removeChild(body.firstChild);
  const section=(label,value,color)=>{
    if(!value&&value!==0) return;
    const h=document.createElement('div');h.style.cssText='font-size:10px;color:var(--text-dim);margin-top:10px;margin-bottom:3px;text-transform:uppercase;letter-spacing:.5px';h.textContent=label;
    const v=document.createElement('pre');v.style.cssText=`white-space:pre-wrap;word-break:break-word;background:var(--bg-deep);border:1px solid var(--border-subtle);border-radius:4px;padding:8px;font-size:11px;color:${color||'var(--text-main)'};max-height:200px;overflow-y:auto;margin:0`;
    v.textContent=typeof value==='string'?value:JSON.stringify(value,null,2);
    body.appendChild(h);body.appendChild(v);
  };
  const timingDiv=document.createElement('div');timingDiv.style.cssText='display:flex;gap:16px;flex-wrap:wrap;margin-bottom:6px';
  const pill=(label,val)=>{const s=document.createElement('span');s.style.cssText='font-size:10px;padding:2px 8px;border-radius:4px;background:var(--bg-elevated);color:var(--text-muted);border:1px solid var(--border-dim)';s.textContent=`${label}: ${val}`;return s;};
  timingDiv.appendChild(pill('Type',node.type||'ai'));timingDiv.appendChild(pill('AI',node.ai||'claude'));timingDiv.appendChild(pill('Status',node.status));
  if(node.elapsed_seconds!=null) timingDiv.appendChild(pill('Duration',node.elapsed_seconds.toFixed(2)+'s'));
  if(node.started_at) timingDiv.appendChild(pill('Started',new Date(node.started_at*1000).toLocaleTimeString()));
  body.appendChild(timingDiv);
  section('Task / Instructions',node.task||'(none)','var(--text-main)');
  if(node.status==='completed') section('Output',node.output||'(empty)','#4caf50');
  if(node.output_summary) section('Summary',node.output_summary,'var(--text-dim)');
  if(node.error) section('Error',node.error,'#e06c75');
}
