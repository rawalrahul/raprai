/**
 * Settings → raprai.com account: optional linking. RAPR works without it.
 * Linked apps sync connections set up on raprai.com and send usage counts
 * (which features are used, never chat content).
 */

async function renderAccountLink() {
  const box = document.getElementById('account-link-status');
  if (!box) return;
  let st = {};
  try { st = await fetch('/device/status').then(r => r.json()); } catch (_) {}
  const linked = !!st.linked;
  box.textContent = linked
    ? 'Linked to raprai.com. Connections from raprai.com sync here, and usage counts are sent.'
    : 'Not linked. Nothing is sent to raprai.com.';
  document.getElementById('account-link-form').hidden = linked;
  document.getElementById('account-unlink-btn').hidden = !linked;
  document.getElementById('account-link-msg').textContent = '';
}

async function linkAccount() {
  const input = document.getElementById('account-link-code');
  const msg = document.getElementById('account-link-msg');
  const code = (input.value || '').trim();
  if (!code) { msg.textContent = 'Enter the code from raprai.com/activate.'; return; }
  msg.textContent = 'Linking...';
  try {
    const r = await fetch('/device/activate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code }),
    });
    const d = await r.json();
    if (!d.ok) {
      const offline = /connection error|max retries|timed out/i.test(d.error || '');
      throw new Error(offline ? "Couldn't reach raprai.com. Check your internet connection and try again."
                              : (d.error || 'Linking failed. Check the code and try again.'));
    }
    input.value = '';
    await renderAccountLink();
  } catch (err) {
    msg.textContent = err.message;
  }
}

async function unlinkAccount() {
  if (!confirm('Unlink from raprai.com? Connections from raprai.com stop syncing and no usage counts are sent.')) return;
  try {
    await fetch('/device/unlink', { method: 'POST' });
  } catch (_) {}
  await renderAccountLink();
}

(function () {
  const orig = window.openSettings;
  if (typeof orig === 'function') {
    window.openSettings = function () { const r = orig.apply(this, arguments); renderAccountLink(); return r; };
  }
})();
