/**
 * Needs you (left sidebar) and Settings → Your brief.
 *
 * Needs you lists everything waiting for you in one place: approvals, the open
 * items of your latest brief, and what your scheduled tasks answered. Each brief
 * item has a button that hands it to the AI that has the app (helm/brief.py).
 * Text from emails and chats is shown with textContent only, never as HTML.
 */

function _el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}

function _needsSay(msg, kind) {
  if (typeof Toast !== 'undefined' && Toast[kind || 'info']) Toast[kind || 'info'](msg);
  const m = document.getElementById('brief-msg');
  if (m) { m.textContent = msg; setTimeout(() => { if (m.textContent === msg) m.textContent = ''; }, 4000); }
}

let _needsAIs = {};          // key → name, from /integrations
async function _loadAIs() {
  try {
    const list = await (await fetch('/integrations')).json();
    _needsAIs = {};
    (list || []).forEach(i => { if (i && i.key) _needsAIs[i.key] = i.name || i.key; });
  } catch (_) {}
}

function _aiName(ai) {
  if (!ai || ai === 'claude') return 'Claude';
  return _needsAIs[ai] || ai.charAt(0).toUpperCase() + ai.slice(1);
}

function _btn(label, cls, onClick, title) {
  const b = _el('button', 'needs-btn ' + (cls || ''), label);
  b.type = 'button';
  if (title) b.title = title;
  b.addEventListener('click', ev => { ev.stopPropagation(); onClick(b); });
  return b;
}

let _needsCount = 0;
function _setNeedsCount(n) {
  _needsCount = n;
  const c = document.getElementById('sb-count-needs');
  if (c) c.textContent = n ? String(n) : '';
  const rail = document.querySelector('#sb-rail-items .sb-rail-btn[data-section="needs"]');
  if (rail) { if (n) rail.dataset.count = n > 9 ? '9+' : String(n); else delete rail.dataset.count; }
}

// The sidebar redraws its rail (layout, order, reorder by drag); put the count back each time.
(function () {
  const rail = document.getElementById('sb-rail-items');
  if (rail && window.MutationObserver) {
    new MutationObserver(() => {
      const btn = rail.querySelector('.sb-rail-btn[data-section="needs"]');
      const want = _needsCount ? (_needsCount > 9 ? '9+' : String(_needsCount)) : null;
      if (btn && (btn.dataset.count || null) !== want) _setNeedsCount(_needsCount);
    }).observe(rail, {childList: true});
  }
})();

let _needsLoading = null;
async function loadNeeds() {
  const panel = document.getElementById('sb-panel-needs');
  if (!panel) return;
  if (_needsLoading) return _needsLoading;
  _needsLoading = (async () => {
    let d;
    try {
      const r = await fetch('/api/needs');
      if (!r.ok) { setTimeout(loadNeeds, 3000); return; }   // busy or rate-limited: keep what's shown
      d = await r.json();
    }
    catch (_) { return; }
    finally { setTimeout(() => { _needsLoading = null; }, 0); }
    _renderNeeds(panel, d);
  })();
  return _needsLoading;
}

function _renderNeeds(panel, d) {
  panel.textContent = '';
  const approvals = d.approvals || [];
  const items = (d.brief && d.brief.items) || [];
  const results = d.results || [];
  _setNeedsCount(approvals.length + items.length);

  const head = _el('div', 'needs-head');
  const when = d.brief
    ? 'Brief · ' + new Date(d.brief.created * 1000).toLocaleString([], {weekday: 'short', hour: '2-digit', minute: '2-digit'})
    : 'No brief yet';
  head.appendChild(_el('span', 'needs-when', d.running ? 'Putting your brief together…' : when));
  head.appendChild(_btn('Brief me now', 'needs-run', () => briefRunNow(), 'Ask your AIs to look now'));
  panel.appendChild(head);
  if (d.brief && (d.brief.checked || []).length) {
    const checked = d.brief.checked.map(c => _aiName(c.ai) + (c.problem ? ' ⚠️' : '')).join(', ');
    const line = _el('div', 'needs-checked', 'Looked through: ' + checked);
    line.title = d.brief.checked.map(c => _aiName(c.ai) + ': ' + c.look_at + (c.problem ? ' — ' + c.problem : '')).join('\n');
    panel.appendChild(line);
  }

  if (approvals.length) {
    panel.appendChild(_el('div', 'needs-group', 'Waiting for your OK'));
    approvals.forEach(a => {
      const row = _el('div', 'needs-item needs-approval');
      row.appendChild(_el('div', 'needs-title', a.description || 'An action needs your OK'));
      (a.details || []).slice(0, 3).forEach(t => row.appendChild(_el('div', 'needs-why', t)));
      const acts = _el('div', 'needs-actions');
      acts.appendChild(_btn('Approve', 'ok', () => _needsResolve(a.id, 'approved')));
      acts.appendChild(_btn('Deny', 'no', () => _needsResolve(a.id, 'denied')));
      row.appendChild(acts);
      panel.appendChild(row);
    });
  }

  if (items.length) {
    panel.appendChild(_el('div', 'needs-group', 'From your brief'));
    items.forEach(it => {
      const row = _el('div', 'needs-item urg-' + (it.urgency || 'normal'));
      const title = _el('div', 'needs-title');
      title.appendChild(_el('span', 'needs-dot'));
      title.appendChild(document.createTextNode(it.title));
      if (it.app && it.app !== 'RAPR') title.appendChild(_el('span', 'needs-app', it.app));
      row.appendChild(title);
      if (it.why) row.appendChild(_el('div', 'needs-why', it.why));
      if (it.link) {
        const a = _el('a', 'needs-link', 'Open');
        a.href = it.link; a.target = '_blank'; a.rel = 'noopener noreferrer';
        row.appendChild(a);
      }
      const acts = _el('div', 'needs-actions');
      if (it.action) acts.appendChild(_btn('▶ Hand to ' + _aiName(it.ai), 'do', b => _needsDo(it.n, b), it.action));
      acts.appendChild(_btn('✕', 'skip', () => _needsSkip(it.n), 'Drop it'));
      row.appendChild(acts);
      panel.appendChild(row);
    });
  }

  if (results.length) {
    panel.appendChild(_el('div', 'needs-group', 'Scheduled results'));
    results.forEach(r => {
      const det = _el('details', 'needs-item needs-result' + (r.failed ? ' failed' : ''));
      const sum = _el('summary', 'needs-title');
      sum.textContent = (r.failed ? '⚠️ ' : '✓ ') + r.name + ' · ' +
        new Date(r.ts * 1000).toLocaleString([], {weekday: 'short', hour: '2-digit', minute: '2-digit'});
      det.appendChild(sum);
      det.appendChild(_el('pre', 'needs-result-text', r.result || '(no output)'));
      panel.appendChild(det);
    });
  }

  if (!approvals.length && !items.length && !results.length) {
    const empty = _el('div', 'sb-empty', 'Nothing needs you right now.');
    const set = _el('a', 'needs-link', 'Set up your brief');
    set.href = '#';
    set.addEventListener('click', ev => { ev.preventDefault(); openBriefSettings(); });
    empty.appendChild(document.createElement('br'));
    empty.appendChild(set);
    panel.appendChild(empty);
  }
}

async function _needsResolve(id, status) {
  try {
    await fetch('/approval/' + encodeURIComponent(id), {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({status}),
    });
  } catch (_) {}
  loadNeeds();
}

async function _needsDo(n, btn) {
  if (btn) { btn.disabled = true; btn.textContent = 'Starting…'; }
  try {
    const r = await fetch('/api/brief/item/' + n + '/do', {method: 'POST'});
    const d = await r.json();
    if (!r.ok) { _needsSay(d.error || 'Could not start it', 'error'); loadNeeds(); return; }
    if (typeof cmd === 'function' && d.session_id) cmd('focus:' + d.session_id);
    _needsSay('Started. Anything it wants to send or change will ask you first.', 'success');
  } catch (err) { _needsSay(err.message, 'error'); }
  loadNeeds();
}

async function _needsSkip(n) {
  try { await fetch('/api/brief/item/' + n + '/skip', {method: 'POST'}); } catch (_) {}
  loadNeeds();
}

async function briefRunNow() {
  try {
    const d = await (await fetch('/api/brief/run', {method: 'POST'})).json();
    _needsSay(d.already ? 'Already putting one together.' : 'Putting your brief together. It shows up under Needs you and on your phone.');
  } catch (err) { _needsSay(err.message, 'error'); }
  setTimeout(loadNeeds, 800);
}

// ── Settings → Your brief ────────────────────────────────────────────────────

function _aiChoices() {
  return [['claude', 'Claude Code'], ...Object.entries(_needsAIs)];
}

function _sourceRow(src) {
  const row = _el('div', 'brief-source');
  const on = document.createElement('input');
  on.type = 'checkbox'; on.checked = src.enabled !== false; on.title = 'On';
  const ai = document.createElement('select');
  ai.className = 'settings-input';
  const choices = _aiChoices();
  if (src.ai && !choices.some(c => c[0] === src.ai)) choices.push([src.ai, src.ai]);
  choices.forEach(([k, name]) => {
    const o = document.createElement('option');
    o.value = k; o.textContent = name; if (k === (src.ai || 'claude')) o.selected = true;
    ai.appendChild(o);
  });
  const look = document.createElement('input');
  look.type = 'text'; look.className = 'settings-input wide';
  look.placeholder = 'What to look at, e.g. my Gmail, calendar and Slack';
  look.value = src.look_at || '';
  const folder = document.createElement('input');
  folder.type = 'text'; folder.className = 'settings-input';
  folder.placeholder = 'Folder (optional)'; folder.value = src.folder || '';
  folder.title = 'Run it in this folder, e.g. a project, so it can check that repository';
  const del = _btn('✕', 'skip', () => row.remove(), 'Remove');
  row.append(on, ai, look, folder, del);
  row._source = () => ({id: src.id, enabled: on.checked, ai: ai.value, look_at: look.value.trim(), folder: folder.value.trim()});
  return row;
}

function briefAddSource(src) {
  const list = document.getElementById('brief-sources');
  if (list) list.appendChild(_sourceRow(src || {ai: 'claude'}));
}

async function loadBriefSettings() {
  const list = document.getElementById('brief-sources');
  if (!list) return;
  let s;
  try { s = await (await fetch('/api/brief/settings')).json(); } catch (_) { return; }
  document.getElementById('brief-enabled').checked = !!s.enabled;
  document.getElementById('brief-time').value = s.time || '08:00';
  document.getElementById('brief-every').value = String(s.every_hours || 0);
  list.textContent = '';
  (s.sources || []).forEach(src => list.appendChild(_sourceRow(src)));
}

async function briefSaveSettings() {
  const rows = [...document.querySelectorAll('#brief-sources .brief-source')];
  const body = {
    enabled: document.getElementById('brief-enabled').checked,
    time: document.getElementById('brief-time').value || '08:00',
    every_hours: parseInt(document.getElementById('brief-every').value, 10) || 0,
    sources: rows.map(r => r._source()).filter(s => s.look_at),
  };
  try {
    const r = await fetch('/api/brief/settings', {
      method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body),
    });
    const d = await r.json();
    if (!r.ok) { _needsSay(d.error || 'Could not save', 'error'); return; }
    _needsSay('Saved');
    loadBriefSettings();
  } catch (err) { _needsSay('Could not save: ' + err.message, 'error'); }
}

async function loadReach(refresh) {
  const box = document.getElementById('reach-list');
  const sugg = document.getElementById('brief-suggestions');
  if (!box) return;
  box.textContent = refresh ? 'Asking your AIs which apps they have…' : 'Checking…';
  let d;
  try { d = await (await fetch('/api/reach' + (refresh ? '?refresh=1' : ''))).json(); }
  catch (err) { box.textContent = 'Could not check: ' + err.message; return; }
  box.textContent = '';
  const sum = d.summary || {};
  box.appendChild(_el('div', 'reach-sum',
    (sum.apps || 0) + ' connected app' + (sum.apps === 1 ? '' : 's') + ' across ' + (sum.ais || 0) +
    ' AI' + (sum.ais === 1 ? '' : 's') + ' and RAPR'));
  const groups = (d.agents || []).map(a => ({name: a.name, apps: a.apps, error: a.error}));
  groups.push({name: 'RAPR (Packages)', apps: d.rapr || [], error: ''});
  groups.forEach(g => {
    const row = _el('div', 'reach-row');
    row.appendChild(_el('span', 'reach-ai', g.name));
    const apps = _el('span', 'reach-apps');
    if (g.error) apps.textContent = '⚠️ ' + g.error;
    else if (!g.apps.length) apps.textContent = 'none yet';
    g.apps.forEach(a => {
      const chip = _el('span', 'reach-chip ' + (a.status === 'connected' ? 'on' : 'off'), a.name);
      chip.title = (a.via ? 'via ' + a.via + ' · ' : '') + a.status;
      apps.appendChild(chip);
    });
    row.appendChild(apps);
    box.appendChild(row);
  });
  if (sugg) {
    sugg.textContent = '';
    const have = new Set([...document.querySelectorAll('#brief-sources .brief-source')]
      .map(r => r._source()).map(s => s.ai + '|' + s.look_at));
    (d.suggestions || []).filter(s => !have.has(s.ai + '|' + s.look_at)).forEach(s => {
      const b = _btn('+ ' + _aiName(s.ai) + ': ' + s.look_at, 'suggest', btn => { briefAddSource(s); btn.remove(); },
                     'Add this, then Save');
      sugg.appendChild(b);
    });
  }
}

function openBriefSettings() {
  if (typeof openSettings === 'function') openSettings();
  setTimeout(() => document.getElementById('brief-section')?.scrollIntoView({behavior: 'smooth', block: 'start'}), 150);
}

(function () {
  const orig = window.openSettings;
  if (typeof orig === 'function') {
    window.openSettings = function () {
      const r = orig.apply(this, arguments);
      _loadAIs().then(loadBriefSettings).then(() => loadReach(false));
      return r;
    };
  }
  if (location.hash === '#needs' || location.hash === '#approvals') {
    setTimeout(() => document.getElementById('sb-section-needs')?.scrollIntoView({block: 'start'}), 500);
  }
  // After the sidebar has drawn its rail, so the count badge has a place to go.
  setTimeout(() => _loadAIs().then(loadNeeds), 300);
  setInterval(loadNeeds, 5 * 60 * 1000);
})();
