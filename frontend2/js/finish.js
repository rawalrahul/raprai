/**
 * Bake-off board, ACP agents, and hands-free voice.
 * DOM APIs only (no innerHTML with user data).
 */

function _el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}
async function _api(url, opts) {
  const o = Object.assign({ headers: { 'Content-Type': 'application/json' } }, opts || {});
  const r = await fetch(url, o);
  let d = {};
  try { d = await r.json(); } catch (_) {}
  if (!r.ok || d.error) throw new Error(d.error || ('HTTP ' + r.status));
  return d;
}
function _toast(kind, msg) { if (typeof Toast !== 'undefined' && Toast[kind]) Toast[kind](msg); }

// ── Bake-off ──────────────────────────────────────────────────────────────────

let _bakeTimer = null;

async function openBakeoffModal() {
  document.getElementById('bakeoff-modal')?.remove();
  const ais = (typeof availableAis === 'function' ? await availableAis() : []).map(a => a.key);
  const overlay = _el('div', 'modal-overlay open');
  overlay.id = 'bakeoff-modal';
  overlay.style.zIndex = '1300';
  overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
  const content = _el('div', 'modal-content');
  content.style.maxWidth = '560px';
  const head = _el('div', 'modal-header');
  head.appendChild(_el('h3', null, 'Bake-off: same task, several AIs'));
  const x = _el('button', 'modal-close', '✕');
  x.addEventListener('click', () => overlay.remove());
  head.appendChild(x);
  content.appendChild(head);

  const body = _el('div', 'modal-body');
  body.style.cssText = 'display:flex;flex-direction:column;gap:12px';
  const field = (label, el) => { const w = _el('div'); w.appendChild(_el('label', 'council-modal-label', label)); w.appendChild(el); body.appendChild(w); };

  const repo = document.createElement('input');
  repo.className = 'council-modal-select'; repo.id = 'bake-repo';
  repo.placeholder = 'Project folder, e.g. C:\\projects\\app';
  const shownCwd = (document.getElementById('cwd-display')?.textContent || '').trim();
  repo.value = shownCwd && shownCwd !== '—' ? shownCwd : '';
  field('Project folder', repo);

  const task = document.createElement('textarea');
  task.className = 'council-modal-textarea'; task.id = 'bake-task'; task.rows = 3;
  task.placeholder = 'What should each AI do?';
  field('Task', task);

  const list = _el('div', 'council-modal-sessions');
  if (ais.length < 2) list.appendChild(_el('div', null, 'A bake-off needs at least two AIs installed (Claude Code, Gemini CLI, Codex, Ollama…).'));
  ais.forEach(ai => {
    const lbl = _el('label', 'council-modal-session-label');
    const cb = document.createElement('input');
    cb.type = 'checkbox'; cb.name = 'bake-ai'; cb.value = ai;
    cb.checked = ais.length <= 3;
    lbl.append(cb, document.createTextNode(' ' + ai));
    list.appendChild(lbl);
  });
  field('AIs (2 to 4)', list);

  const test = document.createElement('input');
  test.className = 'council-modal-select'; test.id = 'bake-test';
  test.placeholder = 'Optional test command, e.g. pytest -q';
  field('Test command (optional)', test);

  const go = _el('button', 'council-btn-primary', 'Start bake-off');
  go.style.width = '100%';
  go.addEventListener('click', () => startBakeoff(overlay));
  body.appendChild(go);

  content.appendChild(body);
  overlay.appendChild(content);
  document.body.appendChild(overlay);
}

async function startBakeoff(overlay) {
  const ais = [...document.querySelectorAll('input[name="bake-ai"]:checked')].map(c => c.value);
  if (ais.length < 2 || ais.length > 4) { _toast('warning', 'Pick 2 to 4 AIs'); return; }
  const payload = {
    repo: document.getElementById('bake-repo').value.trim(),
    task: document.getElementById('bake-task').value.trim(),
    ais,
    test_command: document.getElementById('bake-test').value.trim() || null,
  };
  if (!payload.repo || !payload.task) { _toast('warning', 'Add a folder and a task'); return; }
  try {
    const d = await _api('/api/bakeoff', { method: 'POST', body: JSON.stringify(payload) });
    overlay.remove();
    showBakeoffBoard(d.id);
  } catch (err) { _toast('error', 'Bake-off: ' + err.message); }
}

function showBakeoffBoard(bid) {
  document.getElementById('bakeoff-board')?.remove();
  clearInterval(_bakeTimer);
  const overlay = _el('div', 'modal-overlay open');
  overlay.id = 'bakeoff-board';
  overlay.style.zIndex = '1300';
  const content = _el('div', 'modal-content');
  content.style.maxWidth = '960px';
  content.style.width = '96vw';
  const head = _el('div', 'modal-header');
  const title = _el('h3', null, 'Bake-off');
  head.appendChild(title);
  const x = _el('button', 'modal-close', '✕');
  x.addEventListener('click', () => { clearInterval(_bakeTimer); overlay.remove(); });
  head.appendChild(x);
  content.appendChild(head);
  const body = _el('div', 'modal-body');
  body.id = 'bakeoff-body';
  body.style.cssText = 'display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;max-height:70vh;overflow:auto';
  content.appendChild(body);
  overlay.appendChild(content);
  document.body.appendChild(overlay);

  const draw = async () => {
    let d;
    try { d = await _api('/api/bakeoff/' + encodeURIComponent(bid)); } catch (err) { body.textContent = err.message; clearInterval(_bakeTimer); return; }
    title.textContent = 'Bake-off · ' + (d.status === 'done' ? 'pick a result' : d.status === 'merged' ? 'merged' : d.status === 'discarded' ? 'discarded' : 'running…');
    body.textContent = '';
    d.attempts.forEach((a, i) => body.appendChild(_attemptCard(bid, i, a, d.status)));
    if (d.status !== 'running' && d.status !== 'created') clearInterval(_bakeTimer);
  };
  draw();
  _bakeTimer = setInterval(draw, 2000);
}

function _attemptCard(bid, index, a, status) {
  const card = _el('div', 'bake-card');
  card.style.cssText = 'border:1px solid var(--border-dim);border-radius:10px;padding:10px;display:flex;flex-direction:column;gap:6px';
  card.appendChild(_el('strong', null, a.ai));
  const stats = [
    a.error ? 'failed' : (a.seconds ? a.seconds.toFixed(0) + 's' : 'working…'),
    a.files_changed + ' file' + (a.files_changed === 1 ? '' : 's') + ' changed',
    a.tests_passed === true ? '✅ tests pass' : a.tests_passed === false ? '❌ tests fail' : '',
  ].filter(Boolean).join(' · ');
  card.appendChild(_el('div', null, stats));
  if (a.error) card.appendChild(_el('div', null, a.error));
  if (a.output) {
    const out = _el('pre', null, a.output.slice(0, 1200));
    out.style.cssText = 'white-space:pre-wrap;font-size:11px;max-height:140px;overflow:auto;margin:0';
    card.appendChild(out);
  }
  if (a.diff) {
    const det = document.createElement('details');
    const sum = _el('summary', null, 'Changes');
    const diff = _el('pre', null, a.diff.slice(0, 8000));
    diff.style.cssText = 'white-space:pre;font-size:11px;max-height:260px;overflow:auto';
    det.append(sum, diff);
    card.appendChild(det);
  }
  if (status === 'done') {
    const row = _el('div');
    row.style.cssText = 'display:flex;gap:6px;margin-top:auto';
    const merge = _el('button', 'council-btn-primary', 'Merge this one');
    merge.addEventListener('click', async () => {
      try {
        const r = await _api('/api/bakeoff/' + encodeURIComponent(bid) + '/merge', { method: 'POST', body: JSON.stringify({ attempt: index }) });
        _toast('success', 'Merged ' + r.files_changed + ' file(s) from ' + a.ai);
        document.getElementById('bakeoff-board')?.remove(); clearInterval(_bakeTimer);
      } catch (err) { _toast('error', err.message); }
    });
    const discard = _el('button', 'council-btn-secondary', 'Discard all');
    discard.addEventListener('click', async () => {
      try { await _api('/api/bakeoff/' + encodeURIComponent(bid) + '/discard', { method: 'POST' }); } catch (_) {}
      document.getElementById('bakeoff-board')?.remove(); clearInterval(_bakeTimer);
    });
    row.append(merge, discard);
    card.appendChild(row);
  }
  return card;
}

// ── ACP agents (Settings) ─────────────────────────────────────────────────────

function _acpRow(agent) {
  const row = _el('div', 'acp-row');
  row.style.cssText = 'display:grid;grid-template-columns:110px 1fr 1fr auto;gap:6px;align-items:center';
  const id = document.createElement('input'); id.className = 'settings-input acp-id'; id.placeholder = 'id'; id.value = agent.id || '';
  const name = document.createElement('input'); name.className = 'settings-input acp-name'; name.placeholder = 'Name'; name.value = agent.name || '';
  const cmd = document.createElement('input'); cmd.className = 'settings-input acp-cmd'; cmd.placeholder = 'command, e.g. gemini --acp';
  cmd.value = Array.isArray(agent.command) ? agent.command.join(' ') : (agent.command || '');
  const del = _el('button', 'settings-save-btn', '✕'); del.style.cssText = 'font-size:11px;padding:4px 8px';
  del.addEventListener('click', () => row.remove());
  row.append(id, name, cmd, del);
  row._agent = () => ({ id: id.value.trim(), name: name.value.trim(), command: cmd.value.trim() });
  return row;
}

async function loadAcpAgents() {
  const list = document.getElementById('acp-list');
  if (!list) return;
  let agents = [];
  try { agents = (await _api('/api/acp-agents')).agents || []; } catch (_) {}
  list.textContent = '';
  agents.forEach(a => list.appendChild(_acpRow(a)));
  _renderAcpMenu(agents);
}

function addAcpRow() { document.getElementById('acp-list').appendChild(_acpRow({})); }

async function saveAcpAgents() {
  const msg = document.getElementById('acp-msg');
  const agents = [...document.querySelectorAll('#acp-list .acp-row')].map(r => r._agent()).filter(a => a.id || a.name || a.command);
  try {
    await _api('/api/acp-agents', { method: 'PUT', body: JSON.stringify({ agents }) });
    if (msg) msg.textContent = 'Saved';
    loadAcpAgents();
  } catch (err) { if (msg) msg.textContent = err.message; }
}

function _renderAcpMenu(agents) {
  document.querySelectorAll('.acp-menu-item').forEach(n => n.remove());
  const anchor = document.getElementById('auto-menu-btn');
  if (!anchor) return;
  agents.forEach(a => {
    const b = _el('button', 'ai-menu-item acp-menu-item', 'New: ' + a.name + ' (ACP)');
    b.setAttribute('role', 'menuitem');
    b.addEventListener('click', () => { cmd('new_session:acp:' + a.id); closeAiMenu(); });
    anchor.parentNode.insertBefore(b, anchor.nextSibling);
  });
}

// ── Hands-free voice ─────────────────────────────────────────────────────────────

let _recog = null;
window._handsFree = false;

function _recogniser() {
  const C = window.SpeechRecognition || window.webkitSpeechRecognition;
  return C ? new C() : null;
}

function toggleHandsFree() {
  if (window._handsFree) { stopHandsFree(); return; }
  const r = _recogniser();
  if (!r) { _toast('warning', 'Hands-free needs a browser with speech recognition (Chrome or Edge).'); return; }
  r.lang = navigator.language || 'en-US';
  r.continuous = false;
  r.interimResults = false;
  r.onresult = e => {
    const text = (e.results[0] && e.results[0][0] && e.results[0][0].transcript || '').trim();
    if (!text) return;
    const inp = document.getElementById('inp');
    if (inp) { inp.value = text; if (typeof send === 'function') send(); }
  };
  r.onend = () => { if (window._handsFree && !window._speakingReply) try { r.start(); } catch (_) {} };
  r.onerror = e => { if (e.error === 'not-allowed') { _toast('error', 'Microphone access was refused.'); stopHandsFree(); } };
  _recog = r;
  window._handsFree = true;
  try { r.start(); } catch (_) {}
  _markHandsFree();
}

function stopHandsFree() {
  window._handsFree = false;
  try { _recog && _recog.stop(); } catch (_) {}
  _recog = null;
  _markHandsFree();
}

function _markHandsFree() {
  const b = document.getElementById('handsfree-btn');
  if (b) { b.classList.toggle('active', window._handsFree); b.title = window._handsFree ? 'Hands-free is on (click to stop)' : 'Hands-free: talk instead of typing'; }
}

/** Speak an assistant reply with its AI's voice, pausing the microphone so it doesn't hear itself. */
function speakReplyHandsFree(ai, text) {
  if (!window._handsFree || !window.speechSynthesis || !text) return;
  window._speakingReply = true;
  try { _recog && _recog.stop(); } catch (_) {}
  const u = new SpeechSynthesisUtterance(text.slice(0, 1500));
  const v = typeof voiceFor === 'function' ? voiceFor(ai) : null;
  if (v) { u.voice = v; u.lang = v.lang; }
  const resume = () => {
    window._speakingReply = false;
    if (window._handsFree && _recog) try { _recog.start(); } catch (_) {}
  };
  u.onend = resume; u.onerror = resume;
  speechSynthesis.speak(u);
}

// Load the ACP list when Settings opens.
(function () {
  const orig = window.openSettings;
  if (typeof orig === 'function') {
    window.openSettings = function () { const r = orig.apply(this, arguments); loadAcpAgents(); return r; };
  }
})();
