/**
 * One list of AIs for every screen (group chats, crews, bake-off, voices).
 *
 * liveSessions(): the sessions the app shows right now (complete.js keeps them in
 *   `_sessions`; the older State store is used only if that's missing).
 * availableAis(): every AI you can use: Claude plus each installed integration
 *   that's ready, plus any AI that already has an open session. Each entry says
 *   which open session it would use, if any.
 */

function liveSessions() {
  if (typeof _sessions !== 'undefined' && Array.isArray(_sessions) && _sessions.length) return _sessions;
  if (typeof State !== 'undefined' && Array.isArray(State.sessions) && State.sessions.length) return State.sessions;
  return [];
}

async function liveSessionsFresh() {
  const s = liveSessions();
  if (s.length) return s;
  try { return (await (await fetch('/api/sessions')).json()).sessions || []; } catch (_) { return []; }
}

let _aiListCache = null, _aiListAt = 0;

async function availableAis() {
  const sessions = (await liveSessionsFresh()).filter(s => s.ai && s.status !== 'stopped');
  if (!_aiListCache || Date.now() - _aiListAt > 30000) {
    let integrations = [];
    try {
      const r = await fetch('/integrations');
      const d = await r.json();
      integrations = Array.isArray(d) ? d : [];
    } catch (_) {}
    _aiListCache = [{ key: 'claude', name: 'Claude Code', emoji: '🤖', color: '#f59e0b', ready: true }]
      .concat(integrations.map(i => ({ key: i.key, name: i.name, emoji: i.emoji, color: i.color, ready: !!i.ready, hint: i.setup_hint || '' })));
    _aiListAt = Date.now();
  }
  const byKey = new Map(_aiListCache.map(a => [a.key, Object.assign({}, a)]));
  sessions.forEach(s => {
    if (!byKey.has(s.ai)) byKey.set(s.ai, { key: s.ai, name: s.ai, emoji: s.emoji || '🤖', color: s.color || '#6b7280', ready: true });
    const a = byKey.get(s.ai);
    if (!a.session) a.session = s.name;
    a.ready = true;           // it has a session, so it's usable
  });
  return [...byKey.values()].filter(a => a.ready);
}
