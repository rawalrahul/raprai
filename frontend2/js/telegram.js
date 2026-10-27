/**
 * Settings → Telegram: is the bot connected, and if not, why (not set up, can't reach
 * Telegram, another copy using the bot, token rejected). Refreshed while Settings is open.
 */

async function tgRefresh() {
  const status = document.getElementById('tg-status');
  const msg = document.getElementById('tg-msg');
  if (!status) return;
  let st;
  try {
    const r = await fetch('/api/telegram/status', {cache: 'no-store'});
    if (!r.ok) return;                       // keep showing the last answer
    st = await r.json();
  } catch (_) { return; }
  const labels = {
    off: 'Not set up',
    connecting: 'Connecting…',
    connected: '🟢 Connected',
    conflict: 'In use elsewhere',
    error: 'Token rejected',
  };
  status.textContent = labels[st.status] || st.status;
  status.style.color = st.status === 'connected' ? 'var(--ok, #34d399)'
    : st.status === 'error' || st.status === 'conflict' ? 'var(--color-danger, #f87171)' : 'var(--muted)';
  if (msg) msg.textContent = st.status === 'off'
    ? 'Add a bot token and your Telegram user ID in setup (/setup) to control RAPR from Telegram.'
    : st.error || '';
}

// Refresh when Settings opens, and every 10 s while it stays open.
(function () {
  const orig = window.openSettings;
  if (typeof orig !== 'function') return;
  let timer = null;
  window.openSettings = function () {
    const r = orig.apply(this, arguments);
    tgRefresh();
    clearInterval(timer);
    timer = setInterval(() => {
      if (!document.getElementById('tg-status')?.offsetParent) { clearInterval(timer); return; }
      tgRefresh();
    }, 10000);
    return r;
  };
})();
