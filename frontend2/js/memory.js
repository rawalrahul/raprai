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

function memArchive(id){
  fetch('/memory/' + id + '/archive', {method: 'POST'})
    .then(r=>r.json()).then(d=>{
      if(d.ok) loadMemoryPanel();
    });
}

function memDelete(id){
  if(!confirm('Delete this memory permanently?')) return;
  fetch('/memory/' + id, {method: 'DELETE'})
    .then(r=>r.json()).then(d=>{
      if(d.ok) loadMemoryPanel();
    });
}
