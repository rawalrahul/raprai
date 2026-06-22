// ─────────────────────────────────────────────────────────────────────────────
// Shared AI Memory UI — sidebar panel + CRUD
// ─────────────────────────────────────────────────────────────────────────────

let _memCatFilter = '';
let _memData = [];

// ─── Load / refresh ──────────────────────────────────────────────────────────

function loadMemoryPanel(){
  const container = document.getElementById('mem-list');
  if(!container) return;
  const params = new URLSearchParams();
  if(_memCatFilter) params.set('category', _memCatFilter);
  params.set('limit', '100');
  fetch('/memory?' + params.toString()).then(r=>r.json()).then(data=>{
    if(!data.ok) return;
    _memData = data.memories || [];
    _renderMemories(container);
    _updateMemCount();
  }).catch(()=>{
    container.innerHTML = '<div class="sb-empty">Failed to load memories</div>';
  });
}

function _updateMemCount(){
  const el = document.getElementById('sb-count-memory');
  if(el) el.textContent = _memData.length ? `(${_memData.length})` : '';
}

// ─── Render ──────────────────────────────────────────────────────────────────

function _renderMemories(container){
  if(!_memData.length){
    container.innerHTML = '<div class="sb-empty">No memories yet — use <code>/remember</code> in chat</div>';
    return;
  }
  container.innerHTML = _memData.map(m => {
    const pinCls = m.pinned ? ' mem-pinned' : '';
    const pinIcon = m.pinned ? '📌' : '';
    const catBadge = `<span class="mem-cat-badge mem-cat-${escHtml(m.category)}">${escHtml(m.category)}</span>`;
    const srcBadge = m.source_ai ? `<span class="mem-src">${escHtml(m.source_ai)}</span>` : '';

    return `
    <div class="mem-entry${pinCls}" data-mem-id="${m.id}">
      <div class="mem-entry-header">
        ${pinIcon}${catBadge}${srcBadge}
        <div class="mem-entry-actions">
          <button onclick="memTogglePin(${m.id},${m.pinned?0:1})" title="${m.pinned?'Unpin':'Pin'}">${m.pinned?'📌':'📍'}</button>
          <button onclick="memEdit(${m.id})" title="Edit">✎</button>
          <button onclick="memArchive(${m.id})" title="Archive">📦</button>
          <button onclick="memDelete(${m.id})" title="Delete">✕</button>
        </div>
      </div>
      <div class="mem-entry-content">${escHtml(m.content)}</div>
      ${m.use_count > 0 ? `<div class="mem-entry-uses">Used ${m.use_count}×</div>` : ''}
    </div>`;
  }).join('');
}

// ─── Category filter ─────────────────────────────────────────────────────────

function memFilterCat(btn, cat){
  _memCatFilter = cat;
  document.querySelectorAll('.mem-cat-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  loadMemoryPanel();
}

// ─── Quick add ───────────────────────────────────────────────────────────────

function memQuickAdd(){
  const inp = document.getElementById('mem-add-input');
  if(!inp) return;
  let text = inp.value.trim();
  if(!text) return;

  // Strip /remember prefix if user typed it
  if(text.toLowerCase().startsWith('/remember ')) text = text.substring(10).trim();
  if(!text) return;

  // Check if first word is a category
  const categories = ['preference','fact','project','person','decision','instruction'];
  const words = text.split(/\s+/);
  let category = 'fact';
  let content = text;
  if(words.length >= 2 && categories.includes(words[0].toLowerCase().replace(':',''))){
    category = words[0].toLowerCase().replace(':','');
    content = words.slice(1).join(' ');
  }

  fetch('/memory', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({content, category})
  }).then(r=>r.json()).then(d=>{
    if(d.ok){
      inp.value = '';
      loadMemoryPanel();
    } else {
      alert(d.error || 'Failed to save memory');
    }
  }).catch(()=> alert('Failed to save memory'));
}

// ─── Actions ─────────────────────────────────────────────────────────────────

function memTogglePin(id, pinned){
  fetch('/memory/' + id + '/pin', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({pinned: !!pinned})
  }).then(r=>r.json()).then(d=>{
    if(d.ok) loadMemoryPanel();
  });
}

function memEdit(id){
  const m = _memData.find(x => x.id === id);
  if(!m) return;
  const content = prompt('Edit memory:', m.content);
  if(content === null) return;               // cancelled
  const trimmed = content.trim();
  if(!trimmed || trimmed === m.content) return;
  fetch('/memory/' + id, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({content: trimmed})
  }).then(r=>r.json()).then(d=>{
    if(d.ok) loadMemoryPanel();
    else alert('Failed to update memory');
  }).catch(()=> alert('Failed to update memory'));
}

function memArchive(id){
  fetch('/memory/' + id + '/archive', {method: 'POST'})
    .then(r=>r.json()).then(d=>{
      if(d.ok) loadMemoryPanel();
    });
}

// ─── Obsidian-style Markdown vault export ────────────────────────────────────

function memExportVault(){
  // GET /memory/export returns a .zip (Content-Disposition: attachment).
  const a = document.createElement('a');
  a.href = '/memory/export';
  a.download = '';
  document.body.appendChild(a);
  a.click();
  a.remove();
}

function memDelete(id){
  if(!confirm('Delete this memory permanently?')) return;
  fetch('/memory/' + id, {method: 'DELETE'})
    .then(r=>r.json()).then(d=>{
      if(d.ok) loadMemoryPanel();
    });
}

// ─── Knowledge Transfer ─────────────────────────────────────────────────────

function openKnowledgeTransfer(){
  const modal = document.getElementById('kt-modal');
  if(!modal) return;
  modal.style.display = 'flex';
  // Reset state
  document.getElementById('kt-import-text').value = '';
  document.getElementById('kt-import-msg').textContent = '';
  document.getElementById('kt-results').style.display = 'none';
  // Load the export prompt
  const ta = document.getElementById('kt-export-prompt');
  ta.value = 'Loading prompt...';
  fetch('/memory/transfer/export-prompt').then(r=>r.json()).then(d=>{
    if(d.ok) ta.value = d.prompt;
    else ta.value = 'Failed to generate prompt.';
  }).catch(()=>{ ta.value = 'Failed to load — check server connection.'; });
}

function closeKnowledgeTransfer(){
  document.getElementById('kt-modal').style.display = 'none';
}

function ktCopyPrompt(){
  const ta = document.getElementById('kt-export-prompt');
  const btn = document.getElementById('kt-copy-btn');
  navigator.clipboard.writeText(ta.value).then(()=>{
    btn.textContent = 'Copied!';
    setTimeout(()=> btn.textContent = 'Copy', 2000);
  }).catch(()=>{
    // Fallback for older browsers
    ta.select();
    document.execCommand('copy');
    btn.textContent = 'Copied!';
    setTimeout(()=> btn.textContent = 'Copy', 2000);
  });
}

function ktImport(){
  const text = document.getElementById('kt-import-text').value.trim();
  const source = document.getElementById('kt-source').value;
  const msg = document.getElementById('kt-import-msg');
  const results = document.getElementById('kt-results');
  const resultsBody = document.getElementById('kt-results-body');

  if(!text){
    msg.textContent = 'Please paste the AI response first.';
    msg.style.color = 'var(--warn)';
    return;
  }

  // Quick sanity check — look for at least one [category] line
  if(!text.match(/\[\w+\]/)){
    msg.textContent = 'No [category] tags found. Make sure the AI formatted its response correctly.';
    msg.style.color = 'var(--warn)';
    return;
  }

  msg.textContent = 'Importing...';
  msg.style.color = 'var(--dim)';

  fetch('/memory/transfer/import', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({response: text, source: source})
  }).then(r=>r.json()).then(d=>{
    if(d.ok){
      msg.textContent = '';
      results.style.display = 'block';
      let html = `<div style="color:var(--ok);font-weight:600;margin-bottom:6px">✓ ${d.message}</div>`;
      if(d.skipped > 0){
        html += `<div style="color:var(--muted)">${d.skipped} lines skipped (no category tag or too short)</div>`;
      }
      if(d.errors && d.errors.length > 0){
        html += `<div style="color:var(--warn);margin-top:6px">Issues:</div>`;
        d.errors.forEach(e => { html += `<div style="color:var(--muted);font-size:11px">• ${escHtml(e)}</div>`; });
      }
      html += `<div style="margin-top:10px;color:var(--dim)">All your AI providers now have access to this knowledge.</div>`;
      resultsBody.innerHTML = html;
      // Refresh memory panel in the sidebar
      loadMemoryPanel();
    } else {
      msg.textContent = d.error || 'Import failed';
      msg.style.color = 'var(--err)';
    }
  }).catch(()=>{
    msg.textContent = 'Network error — could not import.';
    msg.style.color = 'var(--err)';
  });
}
