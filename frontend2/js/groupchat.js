/**
 * Group Chats — several AIs and you in one conversation.
 * Talk to all of them, or @mention who should answer. Members see each other's
 * replies and can build on them. Uses DOM APIs (no innerHTML with user data).
 */

const groupState = {
  groups: [],          // summaries (no messages)
  activeId: null,
  active: null,        // full group with messages
  loaded: false,
};

function _g(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

function _gToast(kind, msg) {
  if (typeof Toast !== 'undefined' && Toast[kind]) Toast[kind](msg);
}

async function _gFetch(url, opts) {
  const o = Object.assign({ headers: { 'Content-Type': 'application/json' } }, opts || {});
  const r = await fetch(url, o);
  let d = {};
  try { d = await r.json(); } catch (_) {}
  if (!r.ok || d.error) throw new Error(d.error || ('HTTP ' + r.status));
  return d;
}

function _gMember(group, id) {
  return (group?.members || []).find(m => m.id === id) || null;
}

function _gTime(ts) {
  if (!ts) return '';
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// ── Data ────────────────────────────────────────────────────────────────────

async function loadGroups() {
  try {
    const d = await _gFetch('/api/groups');
    groupState.groups = d.groups || [];
    groupState.loaded = true;
  } catch (err) {
    _gToast('error', 'Could not load group chats: ' + err.message);
  }
  renderGroupList();
  renderGroupSidebar();
}

async function openGroup(id) {
  groupState.activeId = id;
  try {
    const d = await _gFetch('/api/groups/' + encodeURIComponent(id));
    groupState.active = d.group;
  } catch (err) {
    _gToast('error', err.message);
    groupState.active = null;
  }
  renderGroupList();
  renderGroupConversation(true);
}

function _upsertSummary(group) {
  const last = group.messages && group.messages.length ? group.messages[group.messages.length - 1] : null;
  const s = Object.assign({}, group);
  delete s.messages;
  if (last) {
    const who = last.role === 'user' ? 'You' : (last.author_name || '');
    s.last_message = (who ? who + ': ' : '') + (last.content || '').slice(0, 120);
  }
  const i = groupState.groups.findIndex(g => g.id === group.id);
  if (i >= 0) groupState.groups[i] = Object.assign(groupState.groups[i], s);
  else groupState.groups.unshift(s);
}

// ── WebSocket handlers ──────────────────────────────────────────────────────

function groupOnUpdated(d) {
  if (!d.group) return;
  _upsertSummary(d.group);
  if (groupState.activeId === d.group.id) {
    groupState.active = d.group;
    renderGroupConversation(false);
  }
  renderGroupList();
  renderGroupSidebar();
}

function groupOnDeleted(d) {
  groupState.groups = groupState.groups.filter(g => g.id !== d.group_id);
  if (groupState.activeId === d.group_id) { groupState.activeId = null; groupState.active = null; }
  renderGroupList();
  renderGroupConversation(true);
  renderGroupSidebar();
}

function groupOnMessage(d) {
  const s = groupState.groups.find(g => g.id === d.group_id);
  const m = d.message;
  if (s && m) {
    const who = m.role === 'user' ? 'You' : (m.author_name || '');
    s.last_message = (who ? who + ': ' : '') + (m.content || '').slice(0, 120);
    s.updated_at = m.timestamp;
  }
  if (groupState.active && groupState.active.id === d.group_id && m) {
    if (!groupState.active.messages.some(x => x.id === m.id)) {
      groupState.active.messages.push(m);
      const list = document.getElementById('group-messages');
      if (list) {
        const empty = list.querySelector('.group-empty-chat');
        if (empty) empty.remove();
        list.appendChild(_buildGroupMessage(groupState.active, m));
        _scrollGroup(m.role === 'user');
      }
    }
  } else if (m && m.role === 'member' && typeof Toast !== 'undefined' && !_groupPanelOpen()) {
    Toast.info((m.author_name || 'AI') + ' replied in ' + (s ? s.name : 'a group chat'));
  }
  renderGroupList();
  renderGroupSidebar();
}

function groupOnStatus(d) {
  const s = groupState.groups.find(g => g.id === d.group_id);
  if (s) { s.status = d.status; s.speaking = d.speaking; }
  if (groupState.active && groupState.active.id === d.group_id) {
    groupState.active.status = d.status;
    groupState.active.speaking = d.speaking;
    _renderTyping();
    _renderGroupHeaderState();
  }
  renderGroupList();
}

// ── Rendering: sidebar section ──────────────────────────────────────────────

function renderGroupSidebar() {
  const body = document.getElementById('sb-panel-groups');
  if (!body) return;
  while (body.firstChild) body.removeChild(body.firstChild);
  if (!groupState.groups.length) {
    body.appendChild(_g('div', 'sb-empty', 'No group chats yet'));
    return;
  }
  groupState.groups.slice(0, 8).forEach(g => {
    const row = _g('div', 'group-sb-row');
    row.setAttribute('role', 'button');
    row.tabIndex = 0;
    row.title = g.name;
    row.appendChild(_g('span', 'group-sb-icon', '👥'));
    row.appendChild(_g('span', 'group-sb-name', g.name));
    row.addEventListener('click', () => { openGroupSection(); openGroup(g.id); });
    row.addEventListener('keydown', e => { if (e.key === 'Enter') { openGroupSection(); openGroup(g.id); } });
    body.appendChild(row);
  });
}

// ── Rendering: group list ───────────────────────────────────────────────────

function _avatarStack(members) {
  const stack = _g('span', 'group-avatars');
  (members || []).slice(0, 4).forEach(m => {
    const a = _g('span', 'group-avatar', m.emoji || '🤖');
    a.style.borderColor = m.color || '#6b7280';
    a.title = m.name;
    stack.appendChild(a);
  });
  return stack;
}

function renderGroupList() {
  const list = document.getElementById('group-list');
  if (!list) return;
  while (list.firstChild) list.removeChild(list.firstChild);
  if (!groupState.groups.length) {
    list.appendChild(_g('div', 'group-list-empty', groupState.loaded ? 'No groups yet' : 'Loading…'));
    return;
  }
  groupState.groups.forEach(g => {
    const row = _g('button', 'group-row' + (g.id === groupState.activeId ? ' active' : ''));
    row.type = 'button';
    const top = _g('div', 'group-row-top');
    top.appendChild(_avatarStack(g.members));
    top.appendChild(_g('span', 'group-row-name', g.name));
    if (g.status === 'running') top.appendChild(_g('span', 'group-row-live', '●'));
    row.appendChild(top);
    row.appendChild(_g('div', 'group-row-last', g.last_message || (g.members || []).map(m => m.name).join(', ')));
    row.addEventListener('click', () => openGroup(g.id));
    list.appendChild(row);
  });
}

// ── Rendering: conversation ─────────────────────────────────────────────────

function _scrollGroup(force) {
  const list = document.getElementById('group-messages');
  if (!list) return;
  const dist = list.scrollHeight - list.scrollTop - list.clientHeight;
  if (force || dist < 200) setTimeout(() => { list.scrollTop = list.scrollHeight; }, 0);
}

function _buildGroupMessage(group, m) {
  if (m.role === 'user') {
    const wrap = _g('div', 'group-msg group-msg-user');
    const bubble = _g('div', 'group-bubble group-bubble-user');
    bubble.appendChild(_mentionText(m.content || '', group));
    wrap.appendChild(bubble);
    wrap.appendChild(_g('div', 'group-msg-time', _gTime(m.timestamp)));
    return wrap;
  }
  if (m.role === 'system') return _g('div', 'group-msg-system', m.content || '');

  const member = _gMember(group, m.author);
  const color = (member && member.color) || m.author_color || '#6b7280';
  const wrap = _g('div', 'group-msg group-msg-member');
  const av = _g('span', 'group-msg-avatar', (member && member.emoji) || m.author_emoji || '🤖');
  av.style.borderColor = color;
  const col = _g('div', 'group-msg-col');
  const head = _g('div', 'group-msg-head');
  const name = _g('span', 'group-msg-name', (member && member.name) || m.author_name || 'AI');
  name.style.color = color;
  head.appendChild(name);
  if (m.author_ai) head.appendChild(_g('span', 'group-msg-ai', m.author_ai));
  head.appendChild(_g('span', 'group-msg-time', _gTime(m.timestamp)));
  const bubble = _g('div', 'group-bubble');
  bubble.style.borderLeftColor = color;
  bubble.appendChild(_mentionText(m.content || '', group));
  const copy = _g('button', 'group-msg-copy', 'Copy');
  copy.type = 'button';
  copy.addEventListener('click', () => {
    navigator.clipboard?.writeText(m.content || '').then(() => _gToast('success', 'Copied'));
  });
  head.appendChild(copy);
  col.appendChild(head);
  col.appendChild(bubble);
  wrap.appendChild(av);
  wrap.appendChild(col);
  return wrap;
}

/** Text node(s) with @mentions of members highlighted. */
function _mentionText(text, group) {
  const frag = document.createDocumentFragment();
  const re = /(?<!\w)@[\w#-]+/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) frag.appendChild(document.createTextNode(text.slice(last, m.index)));
    const span = _g('span', 'group-mention', m[0]);
    const word = m[0].slice(1).toLowerCase();
    const hit = (group?.members || []).find(x => {
      const n = (x.name || '').toLowerCase();
      return n.replace(/\s+/g, '') === word || n.split(/\s+/)[0] === word;
    });
    if (hit) span.style.color = hit.color;
    frag.appendChild(span);
    last = m.index + m[0].length;
  }
  if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
  return frag;
}

function _renderTyping() {
  const el = document.getElementById('group-typing');
  const g = groupState.active;
  if (!el) return;
  while (el.firstChild) el.removeChild(el.firstChild);
  if (!g || g.status !== 'running') { el.style.display = 'none'; return; }
  const m = _gMember(g, g.speaking);
  el.style.display = '';
  el.appendChild(_g('span', 'group-typing-dots', '•••'));
  el.appendChild(document.createTextNode(' ' + (m ? m.name + ' is replying…' : 'The group is thinking…')));
}

function _renderGroupHeaderState() {
  const stop = document.getElementById('group-stop-btn');
  // `hidden`, not style.display: a global rule forces display on every button.
  if (stop) stop.hidden = !(groupState.active && groupState.active.status === 'running');
}

function renderGroupConversation(scrollToEnd) {
  const pane = document.getElementById('group-conversation');
  if (!pane) return;
  const prevInput = document.getElementById('group-input');
  const draft = prevInput ? prevInput.value : '';
  const hadFocus = prevInput && document.activeElement === prevInput;
  const prevList = document.getElementById('group-messages');
  const prevScroll = prevList ? prevList.scrollTop : 0;
  while (pane.firstChild) pane.removeChild(pane.firstChild);

  const g = groupState.active;
  if (!g) {
    const empty = _g('div', 'group-empty');
    empty.appendChild(_g('div', 'group-empty-icon', '👥'));
    empty.appendChild(_g('div', 'group-empty-title', 'Group Chats'));
    empty.appendChild(_g('div', 'group-empty-desc',
      'Put several AIs in one chat. Ask once and they all answer, reading and building on each other\'s replies. ' +
      '@mention a member to choose who answers.'));
    const btn = _g('button', 'council-btn-primary', 'New Group Chat');
    btn.addEventListener('click', () => openGroupModal(null));
    empty.appendChild(btn);
    pane.appendChild(empty);
    return;
  }

  // Header
  const header = _g('div', 'group-conv-header');
  const left = _g('div', 'group-conv-title');
  left.appendChild(_g('span', 'group-conv-name', g.name));
  const sub = _g('span', 'group-conv-sub', (g.members || []).map(m => m.name).join(' · '));
  left.appendChild(sub);
  header.appendChild(left);
  const actions = _g('div', 'group-conv-actions');
  const stop = _g('button', 'council-btn-stop', 'Stop');
  stop.id = 'group-stop-btn';
  stop.addEventListener('click', () => stopGroup(g.id));
  actions.appendChild(stop);
  const edit = _g('button', 'council-btn-secondary', 'Edit');
  edit.addEventListener('click', () => openGroupModal(g));
  actions.appendChild(edit);
  const exp = _g('button', 'council-btn-secondary', 'Export');
  exp.addEventListener('click', () => _exportGroup(g));
  actions.appendChild(exp);
  const clr = _g('button', 'council-btn-secondary', 'Clear');
  clr.addEventListener('click', () => clearGroup(g.id));
  actions.appendChild(clr);
  const del = _g('button', 'council-btn-secondary group-danger', 'Delete');
  del.addEventListener('click', () => deleteGroup(g.id));
  actions.appendChild(del);
  header.appendChild(actions);
  pane.appendChild(header);
  if (g.about) pane.appendChild(_g('div', 'group-about', g.about));

  // Messages
  const list = _g('div', 'group-messages');
  list.id = 'group-messages';
  list.setAttribute('role', 'log');
  list.setAttribute('aria-live', 'polite');
  if (!g.messages.length) {
    list.appendChild(_g('div', 'group-empty-chat',
      'Say hi to the group. Everyone answers, or start with @' +
      ((g.members[0]?.name || 'Name').split(/\s+/)[0]) + ' to ask one member.'));
  }
  g.messages.forEach(m => list.appendChild(_buildGroupMessage(g, m)));
  pane.appendChild(list);

  const typing = _g('div', 'group-typing');
  typing.id = 'group-typing';
  pane.appendChild(typing);

  // Composer
  const composer = _g('div', 'group-composer');
  const chips = _g('div', 'group-chips');
  const addChip = (label, insert, color) => {
    const c = _g('button', 'group-chip', label);
    c.type = 'button';
    if (color) c.style.borderColor = color;
    c.addEventListener('click', () => {
      const inp = document.getElementById('group-input');
      if (!inp) return;
      const pre = inp.value && !/\s$/.test(inp.value) ? ' ' : '';
      inp.value += pre + insert + ' ';
      inp.focus();
    });
    chips.appendChild(c);
  };
  (g.members || []).forEach(m => addChip('@' + m.name, '@' + m.name.replace(/\s+/g, ''), m.color));
  if ((g.members || []).length > 1) addChip('@all', '@all');
  composer.appendChild(chips);

  const row = _g('div', 'group-input-row');
  const ta = document.createElement('textarea');
  ta.id = 'group-input';
  ta.className = 'group-input';
  ta.rows = 2;
  ta.placeholder = 'Message ' + g.name + '…  (Enter to send, Shift+Enter for a new line)';
  ta.value = draft;
  ta.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); sendGroupMessage(); }
  });
  const send = _g('button', 'council-btn-primary group-send', 'Send');
  send.addEventListener('click', sendGroupMessage);
  row.appendChild(ta);
  row.appendChild(send);
  composer.appendChild(row);
  pane.appendChild(composer);

  _renderTyping();
  _renderGroupHeaderState();
  if (scrollToEnd) _scrollGroup(true);
  else list.scrollTop = prevScroll;
  if (hadFocus || scrollToEnd) ta.focus();
}

// ── Actions ─────────────────────────────────────────────────────────────────

async function sendGroupMessage() {
  const g = groupState.active;
  const inp = document.getElementById('group-input');
  if (!g || !inp) return;
  const text = inp.value.trim();
  if (!text) return;
  inp.value = '';
  try {
    await _gFetch('/api/groups/' + encodeURIComponent(g.id) + '/send', {
      method: 'POST', body: JSON.stringify({ text }),
    });
  } catch (err) {
    inp.value = text;
    _gToast('error', 'Could not send: ' + err.message);
  }
}

async function stopGroup(id) {
  try { await _gFetch('/api/groups/' + encodeURIComponent(id) + '/stop', { method: 'POST' }); }
  catch (err) { _gToast('error', err.message); }
}

async function clearGroup(id) {
  if (!confirm('Clear all messages in this group chat?')) return;
  try { await _gFetch('/api/groups/' + encodeURIComponent(id) + '/messages', { method: 'DELETE' }); }
  catch (err) { _gToast('error', err.message); }
}

async function deleteGroup(id) {
  if (!confirm('Delete this group chat? Its sessions stay open.')) return;
  try { await _gFetch('/api/groups/' + encodeURIComponent(id), { method: 'DELETE' }); }
  catch (err) { _gToast('error', err.message); }
}

// ── Create / edit modal ─────────────────────────────────────────────────────

async function openGroupModal(group) {
  document.getElementById('group-modal')?.remove();
  let sessions = (typeof State !== 'undefined' ? State.sessions : []) || [];
  if (!sessions.length) {
    try { sessions = (await _gFetch('/api/sessions')).sessions || []; } catch (_) {}
  }
  const aiSessions = sessions.filter(s => s.ai);
  const memberSids = new Set((group?.members || []).map(m => m.session_id));

  const overlay = _g('div', 'modal-overlay open');
  overlay.id = 'group-modal';
  overlay.style.zIndex = '1300';
  overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
  const content = _g('div', 'modal-content');
  content.style.maxWidth = '480px';

  const head = _g('div', 'modal-header');
  head.appendChild(_g('h3', null, group ? 'Edit Group Chat' : 'New Group Chat'));
  const x = _g('button', 'modal-close', '✕');
  x.addEventListener('click', () => overlay.remove());
  head.appendChild(x);
  content.appendChild(head);

  const body = _g('div', 'modal-body');
  body.style.cssText = 'display:flex;flex-direction:column;gap:14px';

  const nameWrap = _g('div');
  nameWrap.appendChild(_g('label', 'council-modal-label', 'Name'));
  const name = document.createElement('input');
  name.className = 'council-modal-select';
  name.id = 'group-name';
  name.placeholder = 'e.g. Launch team';
  name.value = group?.name || '';
  nameWrap.appendChild(name);
  body.appendChild(nameWrap);

  const aboutWrap = _g('div');
  aboutWrap.appendChild(_g('label', 'council-modal-label', 'What is this group for? (optional)'));
  const about = _g('textarea', 'council-modal-textarea');
  about.id = 'group-about';
  about.rows = 2;
  about.placeholder = 'e.g. Plan and review the new pricing page together';
  about.value = group?.about || '';
  aboutWrap.appendChild(about);
  body.appendChild(aboutWrap);

  // New group only: start from a ready-made crew (each AI gets a role).
  let crewSel = null;
  if (!group) {
    const crewWrap = _g('div');
    crewWrap.appendChild(_g('label', 'council-modal-label', 'Start from a crew (optional)'));
    crewSel = document.createElement('select');
    crewSel.id = 'group-crew';
    crewSel.className = 'council-modal-select';
    const none = document.createElement('option');
    none.value = ''; none.textContent = 'No crew: a plain group';
    crewSel.appendChild(none);
    try {
      window._crewCache = (await _gFetch('/api/crews')).crews;
      window._crewCache.forEach(c => {
        const o = document.createElement('option');
        o.value = c.id;
        o.textContent = c.name + ' — ' + c.roles.map(r => r.name).join(', ');
        crewSel.appendChild(o);
      });
    } catch (_) {}
    crewSel.addEventListener('change', () => {
      document.getElementById('group-about').value = '';
      if (crewSel.value) {
        const c = (window._crewCache || []).find(x => x.id === crewSel.value);
        if (c) document.getElementById('group-about').value = c.about;
      }
    });
    crewWrap.appendChild(crewSel);
    body.appendChild(crewWrap);
  }

  const memWrap = _g('div');
  memWrap.appendChild(_g('label', 'council-modal-label', 'Members (your open AI sessions)'));
  const list = _g('div', 'council-modal-sessions');
  // Members whose session is closed stay selectable so editing doesn't drop them.
  const rows = aiSessions.map(s => ({ id: s.id, name: s.name || s.id, ai: s.ai_name || s.ai, color: s.color }));
  (group?.members || []).forEach(m => {
    if (!rows.some(r => r.id === m.session_id)) {
      rows.push({ id: m.session_id, name: m.name, ai: m.ai + ', session closed', color: m.color });
    }
  });
  if (!rows.length) {
    const none = _g('div', null, 'No AI sessions open. Start a Claude, Gemini, Codex, Ollama… session first.');
    none.style.cssText = 'color:var(--muted);font-size:12px';
    list.appendChild(none);
  }
  rows.forEach(r => {
    const lbl = _g('label', 'council-modal-session-label');
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.name = 'group-member';
    cb.value = r.id;
    cb.checked = memberSids.has(r.id);
    const dot = _g('span', 'council-dot');
    dot.style.background = r.color || '#6b7280';
    const nm = _g('span');
    nm.appendChild(document.createTextNode(' ' + r.name + ' '));
    const small = _g('small', null, '(' + r.ai + ')');
    small.style.color = 'var(--muted)';
    nm.appendChild(small);
    lbl.appendChild(cb); lbl.appendChild(dot); lbl.appendChild(nm);
    list.appendChild(lbl);
  });
  memWrap.appendChild(list);
  body.appendChild(memWrap);

  const submit = _g('button', 'council-btn-primary', group ? 'Save' : 'Create Group');
  submit.style.width = '100%';
  submit.addEventListener('click', () => submitGroupModal(group));
  body.appendChild(submit);

  content.appendChild(body);
  overlay.appendChild(content);
  document.body.appendChild(overlay);
  name.focus();
}

async function submitGroupModal(group) {
  const ids = [...document.querySelectorAll('input[name="group-member"]:checked')].map(c => c.value);
  if (!ids.length) { _gToast('warning', 'Pick at least one AI session'); return; }
  const payload = {
    name: (document.getElementById('group-name')?.value || '').trim(),
    about: (document.getElementById('group-about')?.value || '').trim(),
    member_session_ids: ids,
  };
  const crewId = document.getElementById('group-crew')?.value || '';
  try {
    let d;
    if (group) {
      d = await _gFetch('/api/groups/' + encodeURIComponent(group.id), { method: 'PATCH', body: JSON.stringify(payload) });
    } else if (crewId) {
      d = await _gFetch('/api/groups/from-crew', { method: 'POST', body: JSON.stringify({ crew_id: crewId, session_ids: ids, name: payload.name }) });
    } else {
      d = await _gFetch('/api/groups', { method: 'POST', body: JSON.stringify(payload) });
    }
    document.getElementById('group-modal')?.remove();
    _upsertSummary(d.group);
    groupState.activeId = d.group.id;
    groupState.active = d.group;
    renderGroupList();
    renderGroupSidebar();
    renderGroupConversation(true);
  } catch (err) {
    _gToast('error', err.message);
  }
}

// ── Export ──────────────────────────────────────────────────────────────────

function _exportGroup(g) {
  const lines = [`# ${g.name}`, '', `**Members:** ${(g.members || []).map(m => `${m.name} (${m.ai})`).join(', ')}`, ''];
  if (g.about) lines.push(`**About:** ${g.about}`, '');
  (g.messages || []).forEach(m => {
    const who = m.role === 'user' ? 'You' : (m.author_name || 'AI');
    lines.push(`**${who}:**`, '', m.content || '', '');
  });
  const blob = new Blob([lines.join('\n')], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = (g.name || 'group-chat').replace(/[^\w-]+/g, '-').slice(0, 40) + '.md';
  a.click();
  URL.revokeObjectURL(url);
}

// ── Section visibility ──────────────────────────────────────────────────────

function _groupPanelOpen() {
  return !!document.getElementById('group-wrapper')?.classList.contains('open');
}

function openGroupSection() {
  document.getElementById('group-wrapper')?.classList.add('open');
  if (!groupState.loaded) loadGroups();
  renderGroupList();
  renderGroupConversation(true);
}

function closeGroupSection() {
  document.getElementById('group-wrapper')?.classList.remove('open');
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && _groupPanelOpen() && !document.getElementById('group-modal')) closeGroupSection();
});

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', loadGroups);
else loadGroups();

// Catch up on anything missed while the tab was hidden or the socket reconnected.
document.addEventListener('visibilitychange', () => {
  if (document.hidden || !_groupPanelOpen()) return;
  loadGroups();
  if (groupState.activeId) openGroup(groupState.activeId);
});
