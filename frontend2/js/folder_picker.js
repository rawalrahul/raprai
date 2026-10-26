// The web UI's main script, part 2 of 8. index.html loads the parts in order.
// --- Folder picker ---------------------------------------------------------------------------------------
// Places (recent projects, Home, Desktop, Documents, Downloads, drives) on the left;
// the current folder's subfolders on the right with a filter; clickable path
// segments, or type/paste a path. Click a folder to open it; "Use" on a row, or
// the footer button, picks it. Keys: ↑/↓ move, Enter opens, Backspace goes up.
let _browsePath = '', _browseTarget = 'cwd'; // 'cwd' or the id of a form field to fill
let _browseData = null, _browseFocus = -1;
let _browseShowHidden = false;
try { _browseShowHidden = localStorage.getItem('raprBrowseHidden') === '1'; } catch(e) {}

const _FP_ICON = {
  folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  home: '<path d="M3 11 12 4l9 7"/><path d="M5 10v10h14V10"/>',
  desktop: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
  documents: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h5"/>',
  downloads: '<path d="M12 3v12M7 10l5 5 5-5M5 21h14"/>',
  drive: '<rect x="3" y="13" width="18" height="7" rx="2"/><path d="M5 13 7 5h10l2 8M7 17h.01"/>',
  recent: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/>',
};
const _fpSvg = k => `<svg viewBox="0 0 24 24" aria-hidden="true">${_FP_ICON[k] || _FP_ICON.folder}</svg>`;
const _fpSame = (a, b) => (a || '').replace(/[\\/]+$/, '').toLowerCase() === (b || '').replace(/[\\/]+$/, '').toLowerCase();

async function openBrowse(target){
  _browseTarget = target || 'cwd';
  const project = _browseTarget === 'cwd';
  document.getElementById('browse-modal-title').textContent = project ? 'Choose your project' : 'Choose a folder';
  document.getElementById('browse-hint').textContent = project
    ? 'Your AI works inside this folder.'
    : 'Pick the folder to use.';
  document.getElementById('browse-select-btn').textContent = project ? 'Use this project' : 'Use this folder';
  document.getElementById('fp-show-hidden').checked = _browseShowHidden;
  const cur = document.getElementById('cwd-display').textContent;
  _browsePath = project ? cur : (document.getElementById(_browseTarget)?.value || cur);
  if(_browsePath === '—') _browsePath = '';
  document.getElementById('browse-modal').classList.add('open');
  await loadBrowse(_browsePath, true);
  document.getElementById('fp-filter').focus();
}

async function loadBrowse(path, withPlaces){
  let data;
  try {
    const res = await fetch('/browse?path=' + encodeURIComponent(path || '') + (withPlaces ? '&places=1' : ''));
    if(!res.ok) throw new Error('HTTP ' + res.status);
    data = await res.json();
  } catch(e){
    _fpError('Could not reach RAPR to list folders.');
    return;
  }
  // A typed path that doesn't exist: stay where we are and say so.
  if(data.error && path && _browseData && !withPlaces && !_fpSame(data.path, path)){
    _fpError(data.error);
    _renderBrowseCrumbs();
    return;
  }
  if(withPlaces || !_browseData) _browseData = Object.assign({}, data);
  else Object.assign(_browseData, data, {places: _browseData.places, recent: _browseData.recent});
  _browsePath = data.path;
  _fpError(data.error);
  document.getElementById('fp-filter').value = '';
  _browseFocus = -1;
  _renderBrowseCrumbs();
  _renderBrowsePlaces();
  _renderBrowseList();
  document.getElementById('fp-up').disabled = !data.parent;
  const sel = document.getElementById('fp-selected');
  const name = data.path.replace(/[\\/]+$/, '').split(/[\\/]/).pop() || data.path;
  sel.innerHTML = 'Selected: <b>' + escHtml(name) + '</b>';
  sel.title = data.path;
}

function _fpError(msg){
  const el = document.getElementById('fp-error');
  el.textContent = msg || '';
  el.hidden = !msg;
}

function _renderBrowseCrumbs(){
  const path = _browsePath;
  const sep = _browseData.sep || (path.includes('\\') ? '\\' : '/');
  const parts = [];
  let acc = '';
  // "C:\Users\me" -> C:\ , Users, me   |   "/home/me" -> /, home, me
  const segs = path.split(/[\\/]+/).filter(Boolean);
  if(path.startsWith('/')){ acc = '/'; parts.push({label: '/', path: '/'}); }
  segs.forEach((seg, i) => {
    if(i === 0 && /^[A-Za-z]:$/.test(seg)){ acc = seg + sep; parts.push({label: seg + sep, path: acc}); return; }
    acc = acc && !acc.endsWith(sep) ? acc + sep + seg : acc + seg;
    parts.push({label: seg, path: acc});
  });
  const el = document.getElementById('browse-crumb');
  el.innerHTML = parts.map((p, i) =>
    (i ? '<span class="fp-crumb-sep" aria-hidden="true">›</span>' : '') +
    `<button type="button" class="fp-crumb${i === parts.length - 1 ? ' is-current' : ''}" data-path="${escHtml(p.path)}">${escHtml(p.label)}</button>`
  ).join('');
  el.scrollLeft = el.scrollWidth;
  el.hidden = false;
  document.getElementById('fp-path-input').hidden = true;
}

function _renderBrowsePlaces(){
  const d = _browseData;
  const item = (p, icon) => `<button type="button" class="fp-place${_fpSame(p.path, _browsePath) ? ' is-current' : ''}" data-path="${escHtml(p.path)}" title="${escHtml(p.path)}">${_fpSvg(icon)}<span>${escHtml(p.name)}</span></button>`;
  let html = '';
  if(d.recent && d.recent.length){
    html += '<div class="fp-places-label">Recent projects</div>' + d.recent.map(p => item(p, 'recent')).join('');
  }
  if(d.places && d.places.length){
    html += '<div class="fp-places-label">Places</div>' + d.places.map(p => item(p, p.kind)).join('');
  }
  if(d.drives && d.drives.length){
    html += '<div class="fp-places-label">Drives</div>' + d.drives.map(x => item({name: x.replace(/\\$/, ''), path: x}, 'drive')).join('');
  }
  document.getElementById('fp-places').innerHTML = html;
}

function _browseVisibleDirs(){
  const d = _browseData;
  const q = document.getElementById('fp-filter').value.trim().toLowerCase();
  const hidden = new Set(d.hidden || []);
  return d.dirs.filter(n => (_browseShowHidden || !hidden.has(n)) && (!q || n.toLowerCase().includes(q)));
}

function _renderBrowseList(){
  const d = _browseData;
  const dirs = _browseVisibleDirs();
  const hiddenCount = (d.hidden || []).length;
  document.getElementById('fp-hidden-count').textContent = hiddenCount ? `(${hiddenCount})` : '';
  const q = document.getElementById('fp-filter').value.trim();
  const list = document.getElementById('browse-list');
  if(!dirs.length){
    list.innerHTML = `<div class="fp-empty">${q ? 'No folders match “' + escHtml(q) + '”.' : d.dirs.length ? 'Only hidden folders here.' : 'No folders inside this one.'}<br><span>You can use this folder, or create one with New folder.</span></div>`;
    return;
  }
  const sep = d.sep || (d.path.includes('\\') ? '\\' : '/');
  const base = d.path.replace(/[\\/]+$/, '');
  const hidden = new Set(d.hidden || []);
  list.innerHTML = dirs.map((n, i) => {
    const full = base + sep + n;
    return `<div class="fp-row${hidden.has(n) ? ' is-hidden' : ''}${i === _browseFocus ? ' is-focus' : ''}" role="option" data-i="${i}" data-path="${escHtml(full)}" aria-selected="${i === _browseFocus}">
      ${_fpSvg('folder')}<span class="fp-row-name">${escHtml(n)}</span>
      <button type="button" class="fp-use" data-use="${escHtml(full)}" title="Use ${escHtml(n)}">Use</button>
      <svg class="fp-chev" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 6 6 6-6 6"/></svg>
    </div>`;
  }).join('');
  list.querySelector('.is-focus')?.scrollIntoView({block: 'nearest'});
}

function browseUp(){ if(_browseData && _browseData.parent) loadBrowse(_browseData.parent); }

function browseEditPath(){
  const inp = document.getElementById('fp-path-input');
  document.getElementById('browse-crumb').hidden = true;
  inp.hidden = false;
  inp.value = _browsePath;
  inp.focus();
  inp.select();
}

async function browseNewFolder(){
  const name = (prompt('Name of the new folder:') || '').trim();
  if(!name) return;
  try {
    const res = await fetch('/browse/mkdir', {method: 'POST', headers: {'Content-Type': 'application/json', 'x-csrf-token': _csrfToken()},
      body: JSON.stringify({path: _browsePath, name})});
    const data = await res.json();
    if(data.error){ _fpError(data.error); return; }
    await loadBrowse(data.path);
  } catch(e){ _fpError('Could not create the folder.'); }
}

function _browsePick(path){
  if(!path) return;
  if(_browseTarget === 'cwd') applyCwdEdit(path);
  else { const el = document.getElementById(_browseTarget); if(el) el.value = path; }
  closeBrowseModal();
}
function selectBrowsePath(){ _browsePick(_browsePath); }
function closeBrowseModal(){ document.getElementById('browse-modal').classList.remove('open'); }
function closeBrowse(e){ if(e.target.id === 'browse-modal') closeBrowseModal(); }

(function _wireBrowse(){
  const modal = document.getElementById('browse-modal');
  if(!modal) return;
  modal.addEventListener('click', e => {
    const use = e.target.closest('[data-use]');
    if(use){ e.stopPropagation(); _browsePick(use.dataset.use); return; }
    const nav = e.target.closest('.fp-row, .fp-place, .fp-crumb');
    if(nav && nav.dataset.path) loadBrowse(nav.dataset.path);
  });
  modal.addEventListener('dblclick', e => {
    // Double-clicking a place picks it straight away (recent projects especially)
    const place = e.target.closest('.fp-place');
    if(place) _browsePick(place.dataset.path);
  });
  const filter = document.getElementById('fp-filter');
  filter.addEventListener('input', () => { _browseFocus = _browseVisibleDirs().length ? 0 : -1; _renderBrowseList(); });
  document.getElementById('fp-show-hidden').addEventListener('change', e => {
    _browseShowHidden = e.target.checked;
    try { localStorage.setItem('raprBrowseHidden', _browseShowHidden ? '1' : '0'); } catch(_) {}
    _renderBrowseList();
  });
  const pathInp = document.getElementById('fp-path-input');
  pathInp.addEventListener('keydown', e => {
    if(e.key === 'Enter'){ e.preventDefault(); e.stopPropagation(); loadBrowse(pathInp.value.trim()); }
    if(e.key === 'Escape'){ e.preventDefault(); e.stopPropagation(); _renderBrowseCrumbs(); }
  });
  pathInp.addEventListener('blur', () => setTimeout(() => { if(!pathInp.hidden) _renderBrowseCrumbs(); }, 150));
  modal.addEventListener('keydown', e => {
    if(!modal.classList.contains('open') || e.target === pathInp) return;
    const dirs = _browseVisibleDirs();
    const inFilter = e.target === filter;
    if(e.key === 'Escape'){ e.preventDefault(); closeBrowseModal(); return; }
    if(e.key === 'ArrowDown' || e.key === 'ArrowUp'){
      if(!dirs.length) return;
      e.preventDefault();
      _browseFocus = e.key === 'ArrowDown' ? Math.min(dirs.length - 1, _browseFocus + 1) : Math.max(0, _browseFocus - 1);
      _renderBrowseList();
      return;
    }
    if(e.key === 'Enter' && (inFilter || e.target.id === 'browse-list')){
      e.preventDefault();
      const row = document.querySelector(`#browse-list .fp-row[data-i="${_browseFocus}"]`);
      if(row) loadBrowse(row.dataset.path);
      return;
    }
    if(e.key === 'Backspace' && (!inFilter || !filter.value)){ e.preventDefault(); browseUp(); }
  });
})();

function esc(s){ return s.replace(/\\/g,'\\\\').replace(/'/g,"\\'"); }

