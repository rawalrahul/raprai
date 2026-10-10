/**
 * Settings → Cloud server: run RAPR on a server you own.
 * DOM APIs only. Passwords and keys are sent once and cleared from the form.
 */

const _COPY_KEYS = ['GEMINI_API_KEY', 'OPENAI_API_KEY', 'OPENROUTER_API_KEY', 'GROQ_API_KEY', 'GITHUB_TOKEN',
  'ELEVENLABS_API_KEY', 'LOCAL_AI_URL', 'LOCAL_AI_MODEL', 'TELEGRAM_BOT_TOKEN', 'ALLOWED_USER_IDS',
  'DISCORD_BOT_TOKEN', 'DISCORD_ALLOWED_USER_IDS', 'SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN', 'SLACK_ALLOWED_USER_IDS',
  'WHATSAPP_ALLOWED_NUMBERS', 'KELVIN_DAILY_CHECKIN', 'TELEGRAM_KELVIN_STICKERS'];

let _cloudJobTimer = null;

async function _cloudApi(url, body) {
  const r = await fetch(url, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : undefined);
  let d = {};
  try { d = await r.json(); } catch (_) {}
  if (!r.ok || d.error) throw new Error(d.error || ('HTTP ' + r.status));
  return d;
}

function _cloudForm() {
  const v = id => (document.getElementById(id)?.value || '').trim();
  return {
    host: v('cloud-host'), user: v('cloud-user') || 'ubuntu', port: parseInt(v('cloud-port') || '22', 10),
    name: v('cloud-name') || 'rapr', password: document.getElementById('cloud-password')?.value || '',
    private_key: document.getElementById('cloud-key')?.value || '',
  };
}

function _clearSecrets() {
  ['cloud-password', 'cloud-key', 'cloud-pin'].forEach(id => { const e = document.getElementById(id); if (e) e.value = ''; });
}

async function renderCloudSettings() {
  const box = document.getElementById('cloud-copy');
  if (box && !box.childElementCount) {
    _COPY_KEYS.forEach(k => {
      const lbl = document.createElement('label');
      lbl.style.cssText = 'display:flex;gap:6px;align-items:center;font-size:11px';
      const cb = document.createElement('input');
      cb.type = 'checkbox'; cb.name = 'cloud-copy-key'; cb.value = k; cb.checked = true;
      lbl.append(cb, document.createTextNode(k));
      box.appendChild(lbl);
    });
  }
  try {
    const saved = (await _cloudApi('/api/cloud')).server || {};
    if (saved.host) document.getElementById('cloud-host').value = saved.host;
    if (saved.user) document.getElementById('cloud-user').value = saved.user;
    if (saved.port) document.getElementById('cloud-port').value = saved.port;
    if (saved.name) document.getElementById('cloud-name').value = saved.name;
    if (saved.url) _showCloudUrl(saved.url);
  } catch (_) {}
}

function _showCloudUrl(url) {
  const out = document.getElementById('cloud-url');
  if (!out) return;
  out.textContent = '';
  const a = document.createElement('a');
  a.href = url; a.target = '_blank'; a.rel = 'noopener noreferrer'; a.textContent = url;
  out.append('Open RAPR on your server: ', a);
  out.append(document.createElement('br'));
  out.append('This address changes if the server restarts; come back here to see the new one.');
}

async function startCloudDeploy() {
  const form = _cloudForm();
  const pin = document.getElementById('cloud-pin')?.value || '';
  const copy = [...document.querySelectorAll('input[name="cloud-copy-key"]:checked')].map(c => c.value);
  const log = document.getElementById('cloud-log');
  log.textContent = '';
  try {
    const job = await _cloudApi('/api/cloud/deploy', { ...form, pin, copy_settings: copy });
    _clearSecrets();
    _watchCloudJob(job.id);
  } catch (err) {
    _clearSecrets();
    log.textContent = err.message;
  }
}

function _watchCloudJob(id) {
  clearInterval(_cloudJobTimer);
  const log = document.getElementById('cloud-log');
  const draw = async () => {
    let j;
    try { j = await _cloudApi('/api/cloud/job/' + encodeURIComponent(id)); } catch (err) { log.textContent = err.message; clearInterval(_cloudJobTimer); return; }
    log.textContent = '';
    j.steps.forEach(s => {
      const line = document.createElement('div');
      const mark = s.state === 'ok' ? '✅' : s.state === 'fail' ? '❌' : '⏳';
      line.textContent = mark + ' ' + s.step + (s.detail ? ' — ' + s.detail : '');
      log.appendChild(line);
    });
    if (j.status === 'running') {
      const busy = document.createElement('div'); busy.textContent = '⏳ working…';
      log.appendChild(busy);
    }
    if (j.status === 'done') {
      clearInterval(_cloudJobTimer);
      if (j.url) _showCloudUrl(j.url);
      else _cloudNote('Deployed, but no public address yet. Press Refresh status in a minute.');
    }
    if (j.status === 'failed') clearInterval(_cloudJobTimer);
  };
  draw();
  _cloudJobTimer = setInterval(draw, 2000);
}

function _cloudNote(text) {
  const log = document.getElementById('cloud-log');
  if (log) { const d = document.createElement('div'); d.textContent = text; log.appendChild(d); }
}

async function cloudAction(what) {
  const out = document.getElementById('cloud-log');
  if (what === 'remove' && !confirm('Remove RAPR from this server? Its data volume is deleted too.')) return;
  out.textContent = '⏳ ' + what + '…';
  try {
    const body = { ..._cloudForm(), what };
    const d = await _cloudApi('/api/cloud/action', body);
    _clearSecrets();
    if (what === 'status') {
      out.textContent = d.containers.length ? d.containers.join('\n') : 'Nothing is running on the server.';
      if (d.url) _showCloudUrl(d.url);
    } else {
      out.textContent = d.output || 'Done.';
    }
  } catch (err) {
    _clearSecrets();
    out.textContent = err.message;
  }
}

(function () {
  const orig = window.openSettings;
  if (typeof orig === 'function') {
    window.openSettings = function () { const r = orig.apply(this, arguments); renderCloudSettings(); return r; };
  }
})();
