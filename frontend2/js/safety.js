/**
 * Auto (smart routing), approval rules and the audit log, in the app.
 * Rules and the log live on the server; this file only shows and edits them.
 */

// ── Auto: pick an AI for a task, then start it ───────────────────────────────

async function autoNewSession() {
  const task = (window.prompt('What do you want to do? RAPR will pick the AI.') || '').trim();
  if (!task) return;
  let decision;
  try {
    const r = await fetch('/api/routing/decide', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: task }),
    });
    decision = await r.json();
  } catch (err) {
    if (typeof Toast !== 'undefined') Toast.error('Auto could not decide: ' + err.message);
    return;
  }
  if (!decision.ai) {
    if (typeof Toast !== 'undefined') Toast.warning('Auto: ' + decision.reason);
    return;
  }
  if (typeof Toast !== 'undefined') Toast.info('Auto → ' + decision.ai + ': ' + decision.reason);
  cmd('new_session:' + decision.ai);
  // The session is created asynchronously and becomes the focused one; then send the task.
  setTimeout(() => {
    const inp = document.getElementById('inp');
    if (inp) { inp.value = task; send(); }
  }, 900);
}

// ── Approval rules ───────────────────────────────────────────────────────────

const _ruleActions = ['ask', 'deny', 'allow'];

function _ruleRow(rule) {
  const row = document.createElement('div');
  row.className = 'rule-row';
  row.style.cssText = 'display:grid;grid-template-columns:auto 1fr 90px 1fr auto;gap:6px;align-items:center';

  const on = document.createElement('input');
  on.type = 'checkbox'; on.className = 'rule-enabled'; on.checked = rule.enabled !== false;
  on.title = 'On';

  const match = document.createElement('input');
  match.type = 'text'; match.className = 'settings-input rule-match wide';
  match.placeholder = 'e.g. git push.*main'; match.value = rule.match || '';

  const action = document.createElement('select');
  action.className = 'settings-input rule-action';
  _ruleActions.forEach(a => {
    const o = document.createElement('option');
    o.value = a; o.textContent = a; if (rule.action === a) o.selected = true;
    action.appendChild(o);
  });

  const desc = document.createElement('input');
  desc.type = 'text'; desc.className = 'settings-input rule-desc wide';
  desc.placeholder = 'What this means (optional)'; desc.value = rule.description || '';

  const del = document.createElement('button');
  del.className = 'settings-save-btn'; del.textContent = '✕';
  del.style.cssText = 'font-size:11px;padding:4px 8px';
  del.title = 'Remove rule';
  del.addEventListener('click', () => row.remove());

  row.append(on, match, action, desc, del);
  row._rule = () => ({ id: rule.id || ('r-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 5)),
                       enabled: on.checked, match: match.value.trim(), action: action.value,
                       description: desc.value.trim() });
  return row;
}

function addRuleRow(rule) {
  document.getElementById('rules-list').appendChild(_ruleRow(rule || { action: 'ask' }));
}

async function loadRules() {
  const list = document.getElementById('rules-list');
  if (!list) return;
  let rules = [];
  try { rules = (await (await fetch('/api/approval-rules')).json()).rules || []; } catch (_) {}
  // Replace the list only once the server answered, so rows you just added aren't lost.
  list.textContent = '';
  rules.forEach(r => list.appendChild(_ruleRow(r)));
}

async function saveRules() {
  const msg = document.getElementById('rules-msg');
  const rows = [...document.querySelectorAll('#rules-list .rule-row')];
  const rules = rows.map(r => r._rule()).filter(r => r.match);
  rules.forEach((r, i) => { if (rules.findIndex(x => x.id === r.id) !== i) r.id += '-' + i; });
  try {
    const r = await fetch('/api/approval-rules', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ rules }),
    });
    const d = await r.json();
    if (!r.ok) { msg.textContent = d.error || 'Could not save'; return; }
    msg.textContent = 'Saved';
    setTimeout(() => { if (msg.textContent === 'Saved') msg.textContent = ''; }, 2000);
    loadRules();
  } catch (err) {
    msg.textContent = 'Could not save: ' + err.message;
  }
}

// ── Audit log (latest entries) ───────────────────────────────────────────────

async function loadAudit() {
  const list = document.getElementById('audit-list');
  if (!list) return;
  list.textContent = '';
  try {
    const d = await (await fetch('/api/audit?limit=30')).json();
    if (!d.entries || !d.entries.length) {
      const none = document.createElement('div'); none.textContent = 'Nothing recorded yet.';
      list.appendChild(none); return;
    }
    d.entries.forEach(e => {
      const line = document.createElement('div');
      const when = new Date(e.ts * 1000).toLocaleString();
      let what = e.event.replace(/_/g, ' ');
      if (e.action) what += ': ' + e.action;
      if (e.source) what += ' (' + e.source + ')';
      if (e.rule) what += ' [rule ' + e.rule + ']';
      line.textContent = when + '  ' + what + (e.description ? ' — ' + e.description : '');
      list.appendChild(line);
    });
  } catch (_) {}
}

// ── What RAPR has learned (playbooks) ───────────────────────────────────────

async function loadPlaybooks() {
  const list = document.getElementById('playbook-list');
  if (!list) return;
  let items = [];
  try { items = (await (await fetch('/api/playbooks/library')).json()).playbooks || []; } catch (_) {}
  list.textContent = '';
  if (!items.length) { list.textContent = 'Nothing learned yet.'; return; }
  items.forEach(pb => {
    const row = document.createElement('div');
    row.style.cssText = 'display:grid;grid-template-columns:1fr auto auto;gap:6px;align-items:center;font-size:12px';
    const name = document.createElement('span');
    const rate = pb.success_rate != null ? Math.round(pb.success_rate * 100) + '%' : '—';
    name.textContent = pb.name.replace(/_/g, ' ') + '  · ' + pb.task_type + ' · ' + rate + ' · ' + pb.sample_count + ' uses';
    const sel = document.createElement('select');
    sel.className = 'settings-input';
    ['active', 'draft', 'disabled'].forEach(st => {
      const o = document.createElement('option');
      o.value = st; o.textContent = st; if (pb.status === st) o.selected = true;
      sel.appendChild(o);
    });
    sel.addEventListener('change', async () => {
      await fetch('/api/playbooks/library/' + encodeURIComponent(pb.task_type) + '/' + encodeURIComponent(pb.name) + '/status', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: sel.value }),
      });
    });
    const view = document.createElement('button');
    view.className = 'settings-save-btn'; view.textContent = 'View';
    view.style.cssText = 'font-size:11px;padding:3px 8px';
    view.addEventListener('click', async () => {
      const out = document.getElementById('playbook-view');
      try {
        const d = await (await fetch('/api/playbooks/library/' + encodeURIComponent(pb.task_type) + '/' + encodeURIComponent(pb.name))).json();
        out.textContent = d.content || d.error || '';
        out.style.display = 'block';
      } catch (_) {}
    });
    row.append(name, sel, view);
    list.appendChild(row);
  });
}

// Load when Settings opens.
(function () {
  const orig = window.openSettings;
  if (typeof orig === 'function') {
    window.openSettings = function () {
      const r = orig.apply(this, arguments);
      loadRules(); loadAudit(); loadPlaybooks();
      const gs = document.getElementById('st-group-speak');
      if (gs) gs.value = window._groupSpeak ? '1' : '0';
      if (typeof renderVoiceSettings === 'function') renderVoiceSettings();
      return r;
    };
  }
})();

// ── Phone notifications ──────────────────────────────────────────────────────

function _b64urlToBytes(b64) {
  const pad = '='.repeat((4 - (b64.length % 4)) % 4);
  const raw = atob((b64 + pad).replace(/-/g, '+').replace(/_/g, '/'));
  return Uint8Array.from(raw, c => c.charCodeAt(0));
}

async function enablePhoneNotifications() {
  const msg = document.getElementById('phone-msg');
  const say = t => { if (msg) msg.textContent = t; };
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    say('This browser can\'t do phone notifications. Use the installed app on Chrome, Edge or Safari (iOS 16.4+).');
    return;
  }
  try {
    const perm = await Notification.requestPermission();
    if (perm !== 'granted') { say('Notifications are blocked. Allow them in the browser settings.'); return; }
    const reg = await navigator.serviceWorker.ready;
    const { publicKey } = await (await fetch('/api/push/key')).json();
    const sub = (await reg.pushManager.getSubscription()) || await reg.pushManager.subscribe({
      userVisibleOnly: true, applicationServerKey: _b64urlToBytes(publicKey),
    });
    const r = await fetch('/api/push/subscribe', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(sub.toJSON()),
    });
    const d = await r.json();
    if (!r.ok) { say(d.error || 'Could not turn on notifications'); return; }
    say('On for this device. Use "Send test" to check.');
  } catch (err) {
    say('Could not turn on notifications: ' + err.message);
  }
}

async function sendTestPush() {
  const msg = document.getElementById('phone-msg');
  try {
    const d = await (await fetch('/api/push/test', { method: 'POST' })).json();
    if (msg) msg.textContent = d.sent ? 'Test sent to ' + d.sent + ' device(s).' : 'No device is turned on yet.';
  } catch (err) { if (msg) msg.textContent = err.message; }
}
