/**
 * Settings → WhatsApp: link RAPR to WhatsApp by scanning a QR code.
 * Status updates arrive live as `whatsapp_status` WebSocket events.
 */

function waRender(st) {
  if (!st) return;
  const status = document.getElementById('wa-status');
  const qrWrap = document.getElementById('wa-qr-wrap');
  const qr = document.getElementById('wa-qr');
  const connect = document.getElementById('wa-connect-btn');
  const unlink = document.getElementById('wa-unlink-btn');
  const allowed = document.getElementById('wa-allowed');
  if (!status) return;

  const labels = {
    off: st.linked ? 'Linked · disconnected' : 'Not linked',
    starting: 'Connecting…',
    qr: 'Scan the QR code',
    connected: '🟢 Connected' + (st.me ? ' as +' + st.me : ''),
    error: 'Error',
  };
  status.textContent = labels[st.status] || st.status;
  status.style.color = st.status === 'connected' ? 'var(--ok, #34d399)' : st.status === 'error' ? 'var(--color-danger, #f87171)' : 'var(--muted)';
  if (qrWrap) qrWrap.style.display = st.status === 'qr' && st.qr ? '' : 'none';
  if (qr && st.qr) qr.src = st.qr;
  // `hidden`, not style.display: a global rule forces display on every button.
  if (connect) {
    connect.hidden = st.status === 'connected' || st.status === 'qr' || st.status === 'starting';
    connect.textContent = st.linked ? 'Reconnect' : 'Link WhatsApp';
  }
  if (unlink) unlink.hidden = !(st.linked || st.status === 'connected' || st.status === 'qr' || st.status === 'starting');
  if (allowed && document.activeElement !== allowed) allowed.value = (st.allowed_numbers || []).join(', ');
  const msg = document.getElementById('wa-msg');
  if (msg && msg.textContent !== 'Saved') msg.textContent = st.error || '';
}

async function _waPost(path, body) {
  const r = await fetch('/api/whatsapp/' + path, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  return r.json();
}

async function waRefresh() {
  try { waRender(await (await fetch('/api/whatsapp/status')).json()); } catch (_) {}
}

async function waConnect() {
  const msg = document.getElementById('wa-msg');
  if (msg) msg.textContent = 'Starting…';
  try { waRender(await _waPost('connect')); } catch (e) { if (msg) msg.textContent = 'Failed: ' + e.message; }
}

async function waUnlink() {
  if (!confirm('Unlink RAPR from WhatsApp? You can link it again any time.')) return;
  try { waRender(await _waPost('disconnect')); } catch (e) { /* status event will follow */ }
}

async function waSaveAllowed() {
  const v = document.getElementById('wa-allowed')?.value || '';
  try {
    waRender(await _waPost('settings', { allowed_numbers: v }));
    const msg = document.getElementById('wa-msg');
    if (msg) { msg.textContent = 'Saved'; setTimeout(() => { if (msg.textContent === 'Saved') msg.textContent = ''; }, 2000); }
  } catch (_) {}
}

// Refresh whenever the Settings modal opens.
(function () {
  const orig = window.openSettings;
  if (typeof orig === 'function') {
    window.openSettings = function () { const r = orig.apply(this, arguments); waRefresh(); return r; };
  }
})();
