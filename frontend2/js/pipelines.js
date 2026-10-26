// The web UI's main script, part 7 of 8. index.html loads the parts in order.
// --- Pipeline UI --------------------------------------------------------------------------------------------

let _pipelines = {};       // pipeline_id -> pipeline state
let _activePipelineId = null;  // currently viewing

const _PL_STATUS_ICON = {
  pending:'⏳', running:'⚡', completed:'✅', failed:'❌', skipped:'⏭️',
  paused:'⏸️', cancelled:'🚫', planning:'🧠', awaiting_approval:'📋'
};
const _PL_STATUS_COLOR = {
  pending:'var(--muted)', running:'var(--claude)', completed:'#22c55e',
  failed:'#ef4444', skipped:'var(--dim)', paused:'#f59e0b'
};

function handlePipelineUpdate(pl){
  if(!pl || !pl.id) return;
  _pipelines[pl.id] = pl;
  // If this is awaiting_approval, show the approval modal
  if(pl.status === 'awaiting_approval'){
    _activePipelineId = pl.id;
    showPipelineApprovalModal(pl);
  }
  // Update the inline graph if it exists in chat
  updatePipelineGraph(pl);
  // Update sidebar list if visible
  const panel = document.getElementById('sb-panel-pipelines');
  if(panel && panel.classList.contains('active')) loadPipelines();
}

function loadPipelines(){
  const el = document.getElementById('pipelines-list');
  if(!el) return;
  fetch('/api/pipelines').then(r=>r.json()).then(data=>{
    const pls = data.pipelines || [];
    if(!pls.length){
      el.innerHTML = '<div class="sb-empty">No pipelines yet.</div>';
      return;
    }
    // Templates link
    let tplHtml = '<div class="pl-sb-tpl-link" onclick="loadTemplates()">📋 Saved Templates</div>';
    el.innerHTML = tplHtml + '<div id="pipeline-templates-list"></div>' + pls.map(p=>{
      const icon = _PL_STATUS_ICON[p.status] || '❓';
      const prog = p.progress || {};
      const progText = prog.total ? `${prog.completed||0}/${prog.total} done` : '';
      return `<div class="pl-sb-card" onclick="viewPipeline('${p.id}')">
        <div class="pl-sb-header">
          <span>${icon} ${escHtml(p.original_prompt.slice(0,60))}${p.original_prompt.length>60?'…':''}</span>
        </div>
        <div class="pl-sb-meta">
          <span class="pl-sb-status">${p.status}</span>
          <span>${progText}</span>
          <span>${p.planner_ai}</span>
        </div>
      </div>`;
    }).join('');
  }).catch(()=>{
    el.innerHTML = '<div class="sb-empty">Failed to load pipelines</div>';
  });
}

function sbPipelineCreate(){
  const ta = document.getElementById('sb-pipeline-prompt');
  const prompt = (ta.value || '').trim();
  if(!prompt){ ta.focus(); return; }
  const btn = ta.nextElementSibling;
  btn.disabled = true; btn.textContent = 'Planning…';
  fetch('/api/pipeline/plan', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({prompt})
  }).then(r=>r.json()).then(data=>{
    btn.disabled = false; btn.textContent = 'Create Pipeline';
    if(data.error){ alert(data.error); return; }
    ta.value = '';
    ta.closest('details').removeAttribute('open');
    loadPipelines();
  }).catch(()=>{
    btn.disabled = false; btn.textContent = 'Create Pipeline';
    alert('Failed to create pipeline');
  });
}

function viewPipeline(plId){
  fetch('/api/pipeline/'+plId).then(r=>r.json()).then(data=>{
    if(data.pipeline){
      _pipelines[plId] = data.pipeline;
      _activePipelineId = plId;
      if(data.pipeline.status === 'awaiting_approval'){
        showPipelineApprovalModal(data.pipeline);
      } else {
        injectPipelineGraph(data.pipeline);
      }
    }
  });
}

// --- Pipeline Approval Modal ---

function showPipelineApprovalModal(pl){
  const modal = document.getElementById('pipeline-modal');
  const promptEl = document.getElementById('pipeline-modal-prompt');
  const stepsEl = document.getElementById('pipeline-modal-steps');
  if(!modal || !stepsEl) return;

  // Show prompt + cost estimate
  let promptText = pl.original_prompt || '';
  if(pl.estimated_total_cost > 0){
    promptText += `\n\n💰 Estimated total cost: $${pl.estimated_total_cost.toFixed(4)}`;
  }
  promptEl.textContent = promptText;

  const aiOptions = ['claude','antigravity','codex','ollama'].map(a =>
    `<option value="${a}">${a}</option>`
  ).join('');

  stepsEl.innerHTML = pl.steps.map((s,i) => {
    const costHint = s.estimated_cost_usd > 0 ? `<span class="pl-step-cost">~$${s.estimated_cost_usd.toFixed(4)}</span>` : '';
    const condHint = s.condition ? `<span class="pl-step-cond">⚡ Conditional</span>` : '';
    const fbHint = s.fallback_ais && s.fallback_ais.length
      ? `<span class="pl-step-fb">↩ Fallback: ${s.fallback_ais.join(', ')}</span>` : '';
    return `
    <div class="pl-approval-step" data-step-id="${s.id}">
      <div class="pl-approval-step-header">
        <span class="pl-step-num">${i+1}</span>
        <input class="pl-step-title-input" value="${escHtml(s.title)}" data-field="title">
        <select class="pl-step-ai-select" data-field="assigned_ai">
          ${aiOptions.replace('value="'+s.assigned_ai+'"','value="'+s.assigned_ai+'" selected')}
        </select>
        ${costHint}
      </div>
      <textarea class="pl-step-desc-input" rows="2" data-field="description">${escHtml(s.description)}</textarea>
      <div class="pl-step-deps">
        ${s.depends_on.length ? 'Depends on: '+s.depends_on.join(', ') : 'No dependencies (can run in parallel)'}
        ${condHint} ${fbHint}
      </div>
    </div>`;
  }).join('');

  modal.style.display = 'flex';
}

function closePipelineModal(){
  document.getElementById('pipeline-modal').style.display = 'none';
}

function approvePipeline(){
  if(!_activePipelineId) return;
  const stepsEl = document.getElementById('pipeline-modal-steps');
  const stepEdits = [];
  stepsEl.querySelectorAll('.pl-approval-step').forEach(el => {
    const sid = el.dataset.stepId;
    const title = el.querySelector('[data-field="title"]').value;
    const ai = el.querySelector('[data-field="assigned_ai"]').value;
    const desc = el.querySelector('[data-field="description"]').value;
    stepEdits.push({id: sid, title, assigned_ai: ai, description: desc});
  });

  fetch('/api/pipeline/'+_activePipelineId+'/approve', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({steps: stepEdits})
  }).then(r=>r.json()).then(()=>{
    closePipelineModal();
  }).catch(err => console.error('Pipeline approve failed:', err));
}

// --- Live Pipeline Graph (inline in chat) ---

function injectPipelineGraph(pl){
  // Find or create the pipeline graph element in #messages
  let graphEl = document.getElementById('pl-graph-'+pl.id);
  if(!graphEl){
    const wrap = document.getElementById('messages');
    graphEl = document.createElement('div');
    graphEl.id = 'pl-graph-'+pl.id;
    graphEl.className = 'pl-graph-container';
    wrap.appendChild(graphEl);
    scroll();
  }
  renderPipelineGraphContent(graphEl, pl);
}

function updatePipelineGraph(pl){
  const graphEl = document.getElementById('pl-graph-'+pl.id);
  if(graphEl) renderPipelineGraphContent(graphEl, pl);
}

function renderPipelineGraphContent(el, pl){
  const prog = pl.progress || {};
  const statusIcon = _PL_STATUS_ICON[pl.status] || '';
  const prompt = (pl.original_prompt||'').slice(0,80);

  // Determine graph layers (topological sort for visual layout)
  const layers = computeGraphLayers(pl.steps);

  let layersHtml = layers.map(layer =>
    `<div class="pl-graph-layer">` +
    layer.map(s => {
      const color = _PL_STATUS_COLOR[s.status] || 'var(--muted)';
      const icon = _PL_STATUS_ICON[s.status] || '❓';
      const aiColor = `var(--${s.assigned_ai||'shell'})`;
      const elapsed = s.elapsed_seconds ? `${s.elapsed_seconds.toFixed(1)}s` : '';
      const costTag = s.actual_cost_usd > 0 ? ` · $${s.actual_cost_usd.toFixed(4)}`
                   : s.estimated_cost_usd > 0 ? ` · ~$${s.estimated_cost_usd.toFixed(4)}` : '';
      const condTag = s.condition ? '<span class="pl-cond-badge">⚡</span>' : '';
      const fbTag = s.fallback_ais && s.fallback_ais.length ? `<span class="pl-fb-badge">↩${s.fallback_index||0}/${s.fallback_ais.length}</span>` : '';
      const streamHtml = s.status === 'running' && s.stream_buffer
        ? `<pre class="pl-stream-live" id="pl-stream-${pl.id}-${s.id}">${escHtml(s.stream_buffer.slice(-200))}</pre>` : '';
      return `<div class="pl-graph-node" data-status="${s.status}" style="border-color:${color}"
                   onclick="toggleStepDetail('${pl.id}','${s.id}')">
        <div class="pl-node-icon">${icon} ${condTag}${fbTag}</div>
        <div class="pl-node-title">${escHtml(s.title)}</div>
        <div class="pl-node-ai" style="color:${aiColor}">${s.assigned_ai}${elapsed?' · '+elapsed:''}${costTag}</div>
        ${streamHtml}
        <div class="pl-node-detail" id="pl-detail-${pl.id}-${s.id}" style="display:none"></div>
      </div>`;
    }).join('<div class="pl-graph-arrow">→</div>') +
    `</div>`
  ).join('');

  // Controls bar
  let controls = '';
  if(pl.status === 'running'){
    controls = `<button class="pl-ctrl-btn" onclick="plAction('${pl.id}','pause')">⏸ Pause</button>
                <button class="pl-ctrl-btn pl-danger" onclick="plAction('${pl.id}','cancel')">✖ Cancel</button>`;
  } else if(pl.status === 'paused'){
    controls = `<button class="pl-ctrl-btn" onclick="plAction('${pl.id}','resume')">▶ Resume</button>
                <button class="pl-ctrl-btn pl-danger" onclick="plAction('${pl.id}','cancel')">✖ Cancel</button>`;
  } else if(pl.status === 'failed'){
    controls = `<button class="pl-ctrl-btn" onclick="plAction('${pl.id}','resume')">🔄 Retry Failed</button>`;
  } else if(pl.status === 'completed'){
    controls = `<button class="pl-ctrl-btn" onclick="saveAsTemplate('${pl.id}')">💾 Save as Template</button>`;
  }

  const costStr = pl.actual_total_cost > 0 ? ` · $${pl.actual_total_cost.toFixed(4)}`
                : pl.estimated_total_cost > 0 ? ` · ~$${pl.estimated_total_cost.toFixed(4)}` : '';

  el.innerHTML = `
    <div class="pl-graph-header">
      <span>${statusIcon} Pipeline: ${escHtml(prompt)}${prompt.length<(pl.original_prompt||'').length?'…':''}</span>
      <span class="pl-graph-progress">${prog.completed||0}/${prog.total||0} steps${costStr}</span>
    </div>
    <div class="pl-graph-body">${layersHtml}</div>
    ${controls ? `<div class="pl-graph-controls">${controls}</div>` : ''}
  `;
}

function computeGraphLayers(steps){
  // Simple topological layering: steps with no deps go in layer 0, etc.
  if(!steps || !steps.length) return [];
  const stepMap = {};
  steps.forEach(s => stepMap[s.id] = s);
  const layers = [];
  const placed = new Set();

  for(let i = 0; i < steps.length + 1; i++){
    const layer = [];
    steps.forEach(s => {
      if(placed.has(s.id)) return;
      const deps = (s.depends_on||[]).filter(d => !placed.has(d));
      if(deps.length === 0) layer.push(s);
    });
    if(!layer.length) break;
    layer.forEach(s => placed.add(s.id));
    layers.push(layer);
  }
  // Add any remaining (circular dep edge case)
  const remaining = steps.filter(s => !placed.has(s.id));
  if(remaining.length) layers.push(remaining);
  return layers;
}

function toggleStepDetail(plId, stepId){
  const el = document.getElementById('pl-detail-'+plId+'-'+stepId);
  if(!el) return;
  if(el.style.display !== 'none'){
    el.style.display = 'none';
    return;
  }
  // Fetch full step detail
  fetch(`/api/pipeline/${plId}/step/${stepId}`).then(r=>r.json()).then(data=>{
    const s = data.step;
    if(!s) return;
    let html = `<div class="pl-detail-desc">${escHtml(s.description).slice(0,300)}</div>`;
    if(s.condition){
      html += `<div class="pl-detail-cond">⚡ Condition: if ${s.condition.check}.${s.condition.field} ${s.condition.equals?'==':'contains'} "${escHtml(s.condition.equals||s.condition.contains||'')}"</div>`;
    }
    if(s.fallback_ais && s.fallback_ais.length){
      html += `<div class="pl-detail-fb">↩ Fallback AIs: ${s.fallback_ais.join(' → ')} (used ${s.fallback_index||0})</div>`;
    }
    if(s.output){
      html += `<div class="pl-detail-output">${escHtml(s.output).slice(0,500)}${s.output.length>500?'…':''}</div>`;
    }
    if(s.stream_buffer){
      html += `<pre class="pl-detail-stream">Live: ${escHtml(s.stream_buffer.slice(-300))}</pre>`;
    }
    if(s.error){
      html += `<div class="pl-detail-error">Error: ${escHtml(s.error)}</div>`;
    }
    // Artifact files (structured)
    if(s.artifact_files && s.artifact_files.length){
      html += `<div class="pl-detail-files">📁 Files:<br>${s.artifact_files.map(f =>
        `  ${f.name} (${(f.size/1024).toFixed(1)}KB, .${f.type})`
      ).join('<br>')}</div>`;
    } else if(s.artifacts && s.artifacts.length){
      html += `<div class="pl-detail-files">📁 ${s.artifacts.join(', ')}</div>`;
    }
    // Cost
    if(s.actual_cost_usd > 0){
      html += `<div class="pl-detail-cost">💰 Actual: $${s.actual_cost_usd.toFixed(4)} (${s.actual_tokens} tokens)</div>`;
    } else if(s.estimated_cost_usd > 0){
      html += `<div class="pl-detail-cost">💰 Est: ~$${s.estimated_cost_usd.toFixed(4)} (~${s.estimated_tokens} tokens)</div>`;
    }
    // Action buttons
    if(s.status === 'failed'){
      html += `<div class="pl-detail-actions">
        <button class="pl-ctrl-btn" onclick="plStepAction('${plId}','${stepId}','retry')">🔄 Retry</button>
        <button class="pl-ctrl-btn" onclick="plStepAction('${plId}','${stepId}','skip')">⏭️ Skip</button>
      </div>`;
    }
    el.innerHTML = html;
    el.style.display = 'block';
  });
}

// --- Step-level streaming handler ---
function handleStepStream(plId, stepId, chunk){
  const el = document.getElementById('pl-stream-'+plId+'-'+stepId);
  if(el){
    el.textContent = (el.textContent + chunk).slice(-500);
    el.scrollTop = el.scrollHeight;
  }
}

// --- Pipeline Templates ---
function loadTemplates(){
  fetch('/api/pipeline/templates').then(r=>r.json()).then(data=>{
    const tpls = data.templates || [];
    const el = document.getElementById('pipeline-templates-list');
    if(!el) return;
    if(!tpls.length){
      el.innerHTML = '<div class="pl-tpl-empty">No saved templates yet. Complete a pipeline to save it as a template.</div>';
      return;
    }
    el.innerHTML = tpls.map(t => `
      <div class="pl-tpl-card">
        <div class="pl-tpl-name">${escHtml(t.name)}</div>
        <div class="pl-tpl-meta">${t.step_count} steps · ${t.planner_ai} · used ${t.use_count}x</div>
        <div class="pl-tpl-actions">
          <button class="pl-ctrl-btn" onclick="useTemplate('${t.id}')">▶ Use</button>
          <button class="pl-ctrl-btn pl-danger" onclick="deleteTemplate('${t.id}')">🗑️</button>
        </div>
      </div>
    `).join('');
  });
}

function saveAsTemplate(plId){
  const name = prompt('Template name:');
  if(!name) return;
  fetch(`/api/pipeline/${plId}/save-template`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({name})
  }).then(r=>r.json()).then(data=>{
    if(data.ok) alert('Template saved: ' + data.template.name);
    loadTemplates();
  });
}

function useTemplate(tplId){
  const userPrompt = prompt('What should this pipeline do? (or leave blank for default):') || '';
  fetch('/api/pipeline/from-template', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({template_id: tplId, prompt: userPrompt})
  }).then(r=>r.json()).then(data=>{
    if(data.pipeline){
      _pipelines[data.pipeline.id] = data.pipeline;
      _activePipelineId = data.pipeline.id;
      showPipelineApprovalModal(data.pipeline);
    }
  });
}

function deleteTemplate(tplId){
  if(!confirm('Delete this template?')) return;
  fetch(`/api/pipeline/template/${tplId}`, {method:'DELETE'}).then(()=> loadTemplates());
}

function plAction(plId, action){
  fetch(`/api/pipeline/${plId}/${action}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'})
    .then(r=>r.json()).catch(err => console.error('Pipeline action failed:', err));
}

function plStepAction(plId, stepId, action){
  fetch(`/api/pipeline/${plId}/step/${stepId}/${action}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'})
    .then(r=>r.json()).catch(err => console.error('Step action failed:', err));
}

