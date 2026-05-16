/**
 * AI Council — debate panel UI + WebSocket event handlers
 * Uses DOM APIs (no innerHTML with user data) for XSS safety.
 */

const councilState = {
  activeCouncil: null,
  streamingParticipant: null,
  streamBuffer: "",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function _el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

function _getParticipantColor(aiName) {
  const p = (councilState.activeCouncil?.participants || []).find(x => x.ai === aiName);
  return p ? (p.color || '#6b7280') : '#6b7280';
}

function _scrollCouncilMessages() {
  const el = document.getElementById('council-messages');
  if (el) setTimeout(() => { el.scrollTop = el.scrollHeight; }, 0);
}

// ── Message DOM builders ──────────────────────────────────────────────────────

function _buildModeratorBubble(content, nextParticipant) {
  const wrap = _el('div', 'council-msg-moderator');
  const label = _el('div', 'council-msg-moderator-label');
  label.textContent = nextParticipant ? 'Moderator → ' + nextParticipant : 'Moderator';
  const body = _el('div', 'council-msg-moderator-body', content);
  wrap.appendChild(label);
  wrap.appendChild(body);
  return wrap;
}

function _buildParticipantBubble(msg, streaming) {
  const color = _getParticipantColor(msg.participant_ai);
  const wrap = _el('div', 'council-msg-participant' + (streaming ? ' streaming' : ''));
  if (msg.id) wrap.id = 'cmsg-' + msg.id;
  if (streaming) wrap.id = 'council-streaming-bubble';

  const header = _el('div', 'council-msg-participant-header');
  header.style.color = color;
  header.textContent = msg.participant_name || msg.participant_ai || 'AI';

  const badge = _el('span', 'council-msg-ai-badge');
  badge.style.background = color;
  badge.textContent = msg.participant_ai || '';
  header.appendChild(badge);

  const body = _el('div', 'council-msg-participant-body');
  body.id = streaming ? 'council-streaming-body' : '';
  body.textContent = msg.content || '';

  wrap.appendChild(header);
  wrap.appendChild(body);
  return wrap;
}

function _buildUserBubble(content) {
  const wrap = _el('div', 'council-msg-user');
  const label = _el('span', 'council-msg-user-label', 'You: ');
  wrap.appendChild(label);
  wrap.appendChild(document.createTextNode(content));
  return wrap;
}

function _buildSystemBubble(content) {
  return _el('div', 'council-msg-system', content);
}

function _buildMessageNode(msg) {
  if (msg.role === 'moderator')   return _buildModeratorBubble(msg.content || '', null);
  if (msg.role === 'participant') return _buildParticipantBubble(msg, false);
  if (msg.role === 'user')        return _buildUserBubble(msg.content || '');
  if (msg.role === 'system')      return _buildSystemBubble(msg.content || '');
  return null;
}

// ── Panel render ──────────────────────────────────────────────────────────────

function renderCouncilPanel() {
  const section = document.getElementById('council-section');
  if (!section) return;

  // Clear panel
  while (section.firstChild) section.removeChild(section.firstChild);

  const council = councilState.activeCouncil;

  if (!council) {
    const empty = _el('div', 'council-empty');

    const icon = _el('div'); icon.textContent = '🏛️';
    icon.style.cssText = 'font-size:2em;margin-bottom:12px';

    const title = _el('div'); title.textContent = 'AI Council';
    title.style.cssText = 'font-size:1.1em;font-weight:600;margin-bottom:8px';

    const desc = _el('div');
    desc.textContent = 'Let your AIs debate a topic and reach consensus.';
    desc.style.cssText = 'color:var(--muted);margin-bottom:20px';

    const btn = _el('button', 'council-btn-primary', 'Start New Council');
    btn.addEventListener('click', openCouncilModal);

    empty.appendChild(icon);
    empty.appendChild(title);
    empty.appendChild(desc);
    empty.appendChild(btn);
    section.appendChild(empty);
    return;
  }

  // Header
  const header = _el('div', 'council-header');
  const headerLeft = _el('div', 'council-header-left');
  headerLeft.appendChild(_el('span', 'council-title', 'AI Council'));

  const statusMap = { completed: '✓ Consensus', stopped: '■ Stopped', running: '● Running' };
  const statusEl = _el('span', 'council-status ' + council.status, statusMap[council.status] || council.status);
  headerLeft.appendChild(statusEl);
  header.appendChild(headerLeft);

  if (council.status === 'running') {
    const stopBtn = _el('button', 'council-btn-stop', 'Stop');
    stopBtn.addEventListener('click', () => stopCouncil(council.id));
    header.appendChild(stopBtn);
  } else {
    const newBtn = _el('button', 'council-btn-secondary', 'New Council');
    newBtn.addEventListener('click', openCouncilModal);
    header.appendChild(newBtn);
  }
  section.appendChild(header);

  // Topic
  section.appendChild(_el('div', 'council-topic', council.topic));

  // Participants row
  const pRow = _el('div', 'council-participants-row');
  (council.participants || []).forEach(p => {
    const dot = _el('span', 'council-participant-dot');
    dot.style.background = p.color || '#6b7280';
    dot.title = p.name || p.ai;
    dot.textContent = p.emoji || '🤖';
    pRow.appendChild(dot);
  });
  const roundBadge = _el('span', 'council-round-badge',
    'Round ' + council.rounds + ' / ' + council.max_rounds);
  pRow.appendChild(roundBadge);
  section.appendChild(pRow);

  // Messages
  const msgContainer = _el('div', 'council-messages');
  msgContainer.id = 'council-messages';
  (council.messages || []).forEach(msg => {
    const node = _buildMessageNode(msg);
    if (node) msgContainer.appendChild(node);
  });
  section.appendChild(msgContainer);

  // Consensus box
  if (council.consensus_summary) {
    const box = _el('div', 'council-consensus-box');
    box.appendChild(_el('div', 'council-consensus-title', 'Consensus Reached'));
    box.appendChild(_el('div', 'council-consensus-body', council.consensus_summary));

    const btnRow = _el('div'); btnRow.style.cssText = 'display:flex;gap:8px;margin-top:12px';
    const copyBtn = _el('button', 'council-btn-secondary', 'Copy Summary');
    copyBtn.addEventListener('click', copyCouncilSummary);
    const newBtn2 = _el('button', 'council-btn-primary', 'Start New Council');
    newBtn2.addEventListener('click', openCouncilModal);
    btnRow.appendChild(copyBtn);
    btnRow.appendChild(newBtn2);
    box.appendChild(btnRow);
    section.appendChild(box);
  }

  // Stopped banner
  if (council.status === 'stopped' && !council.consensus_summary) {
    const banner = _el('div', 'council-stopped-banner', 'Council stopped. ');
    const restartBtn = _el('button', 'council-btn-secondary', 'Start New Council');
    restartBtn.addEventListener('click', openCouncilModal);
    banner.appendChild(restartBtn);
    section.appendChild(banner);
  }

  // Inject bar
  if (council.status === 'running') {
    const bar = _el('div', 'council-inject-bar');
    const input = _el('input', 'council-inject-input');
    input.id = 'council-inject-input';
    input.placeholder = 'Inject message into debate...';
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter') injectCouncilMessage(council.id);
    });
    const sendBtn = _el('button', 'council-btn-primary', 'Send');
    sendBtn.addEventListener('click', () => injectCouncilMessage(council.id));
    bar.appendChild(input);
    bar.appendChild(sendBtn);
    section.appendChild(bar);
  }
}

// ── WS event handlers ─────────────────────────────────────────────────────────

function councilOnCreated(data) {
  councilState.activeCouncil = data.council || data;
  councilState.streamingParticipant = null;
  councilState.streamBuffer = '';
  openCouncilSection();
}

function councilOnModerator(data) {
  if (!councilState.activeCouncil) return;
  if (data.council_id !== councilState.activeCouncil.id) return;
  if (!data.moderator_prompt) return;

  const container = document.getElementById('council-messages');
  if (container) {
    container.appendChild(_buildModeratorBubble(data.moderator_prompt, data.next_participant));
    _scrollCouncilMessages();
  }
}

function councilOnStream(data) {
  if (!councilState.activeCouncil) return;
  if (data.council_id !== councilState.activeCouncil.id) return;

  const container = document.getElementById('council-messages');
  if (!container) return;

  if (councilState.streamingParticipant !== data.participant_ai) {
    councilState.streamingParticipant = data.participant_ai;
    councilState.streamBuffer = '';
    const bubble = _buildParticipantBubble(
      { participant_ai: data.participant_ai, participant_name: data.participant_ai, content: '' },
      true
    );
    container.appendChild(bubble);
  }

  councilState.streamBuffer += data.chunk || '';
  const body = document.getElementById('council-streaming-body');
  if (body) body.textContent = councilState.streamBuffer;
  _scrollCouncilMessages();
}

function councilOnMessage(data) {
  if (!councilState.activeCouncil) return;
  if (data.council_id !== councilState.activeCouncil.id) return;

  const streaming = document.getElementById('council-streaming-bubble');
  if (streaming) streaming.remove();
  councilState.streamingParticipant = null;
  councilState.streamBuffer = '';

  const msg = data.message;
  if (!msg) return;

  councilState.activeCouncil.messages = councilState.activeCouncil.messages || [];
  councilState.activeCouncil.messages.push(msg);
  councilState.activeCouncil.rounds = (councilState.activeCouncil.rounds || 0) + 1;

  const container = document.getElementById('council-messages');
  if (container) {
    const node = _buildMessageNode(msg);
    if (node) { container.appendChild(node); _scrollCouncilMessages(); }
  }

  const badge = document.querySelector('.council-round-badge');
  if (badge && councilState.activeCouncil) {
    badge.textContent = 'Round ' + councilState.activeCouncil.rounds + ' / ' + councilState.activeCouncil.max_rounds;
  }
}

function councilOnCompleted(data) {
  councilState.activeCouncil = data.council || data;
  renderCouncilPanel();
}

function councilOnStopped(data) {
  if (councilState.activeCouncil && data.council_id === councilState.activeCouncil.id) {
    councilState.activeCouncil.status = 'stopped';
    renderCouncilPanel();
  }
}

// ── Actions ───────────────────────────────────────────────────────────────────

async function stopCouncil(councilId) {
  try {
    await fetch('/api/council/' + councilId + '/stop', { method: 'DELETE' });
  } catch (err) {
    if (typeof Toast !== 'undefined') Toast.error('Failed to stop council: ' + err.message);
  }
}

async function injectCouncilMessage(councilId) {
  const input = document.getElementById('council-inject-input');
  if (!input) return;
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';
  try {
    await fetch('/api/council/' + councilId + '/inject', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg }),
    });
  } catch (err) {
    if (typeof Toast !== 'undefined') Toast.error('Failed to inject message: ' + err.message);
  }
}

function copyCouncilSummary() {
  const summary = councilState.activeCouncil?.consensus_summary;
  if (!summary) return;
  navigator.clipboard.writeText(summary).then(() => {
    if (typeof Toast !== 'undefined') Toast.success('Summary copied');
  });
}

// ── Start New Council Modal ───────────────────────────────────────────────────

function openCouncilModal() {
  const existing = document.getElementById('council-modal');
  if (existing) existing.remove();

  const sessions = (typeof State !== 'undefined' ? State.sessions : []) || [];

  const overlay = _el('div', 'modal-overlay visible');
  overlay.id = 'council-modal';
  overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });

  const content = _el('div', 'modal-content');
  content.style.maxWidth = '480px';

  // Header
  const mHeader = _el('div', 'modal-header');
  mHeader.appendChild(_el('h3', null, 'Start New Council'));
  const closeBtn = _el('button', 'modal-close', '✕');
  closeBtn.addEventListener('click', () => overlay.remove());
  mHeader.appendChild(closeBtn);
  content.appendChild(mHeader);

  // Body
  const body = _el('div', 'modal-body');
  body.style.cssText = 'display:flex;flex-direction:column;gap:14px';

  // Topic
  const topicWrap = _el('div');
  topicWrap.appendChild(_el('label', 'council-modal-label', 'Topic'));
  const topicTA = _el('textarea', 'council-modal-textarea');
  topicTA.id = 'council-topic';
  topicTA.rows = 3;
  topicTA.placeholder = 'What should the AIs debate?';
  topicWrap.appendChild(topicTA);
  body.appendChild(topicWrap);

  // Participants
  const partWrap = _el('div');
  partWrap.appendChild(_el('label', 'council-modal-label', 'Participants (select sessions)'));
  const partList = _el('div', 'council-modal-sessions');
  if (sessions.length === 0) {
    partList.appendChild(_el('div', null, 'No active sessions. Start some sessions first.'));
    partList.firstChild.style.cssText = 'color:var(--muted);font-size:12px';
  } else {
    sessions.forEach(s => {
      const lbl = _el('label', 'council-modal-session-label');
      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.name = 'council-participant';
      cb.value = s.id;
      const dot = _el('span', 'council-dot');
      dot.style.background = s.ai_color || '#6b7280';
      const nameSpan = _el('span');
      nameSpan.appendChild(document.createTextNode(' ' + (s.name || s.id) + ' '));
      const small = _el('small');
      small.textContent = '(' + (s.ai_name || s.ai || 'shell') + ')';
      small.style.color = 'var(--muted)';
      nameSpan.appendChild(small);
      lbl.appendChild(cb);
      lbl.appendChild(dot);
      lbl.appendChild(nameSpan);
      partList.appendChild(lbl);
    });
  }
  partWrap.appendChild(partList);
  body.appendChild(partWrap);

  // Moderator
  const modWrap = _el('div');
  modWrap.appendChild(_el('label', 'council-modal-label', 'Moderator'));
  const modSel = document.createElement('select');
  modSel.id = 'council-moderator';
  modSel.className = 'council-modal-select';
  sessions.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s.id;
    opt.textContent = s.name || s.id;
    modSel.appendChild(opt);
  });
  modWrap.appendChild(modSel);
  body.appendChild(modWrap);

  // Max rounds
  const roundWrap = _el('div');
  const roundLabelText = _el('span', 'council-modal-label', 'Max Rounds: ');
  const roundVal = _el('span'); roundVal.id = 'council-rounds-val'; roundVal.textContent = '10';
  roundLabelText.appendChild(roundVal);
  roundWrap.appendChild(roundLabelText);
  const roundSlider = document.createElement('input');
  roundSlider.type = 'range'; roundSlider.id = 'council-rounds';
  roundSlider.min = '3'; roundSlider.max = '20'; roundSlider.value = '10';
  roundSlider.style.width = '100%';
  roundSlider.addEventListener('input', () => { roundVal.textContent = roundSlider.value; });
  roundWrap.appendChild(roundSlider);
  body.appendChild(roundWrap);

  // Submit
  const submitBtn = _el('button', 'council-btn-primary', 'Start Council');
  submitBtn.style.width = '100%';
  submitBtn.addEventListener('click', submitCouncilStart);
  body.appendChild(submitBtn);

  content.appendChild(body);
  overlay.appendChild(content);
  document.body.appendChild(overlay);
}

async function submitCouncilStart() {
  const topic = (document.getElementById('council-topic')?.value || '').trim();
  if (!topic) { if (typeof Toast !== 'undefined') Toast.warning('Enter a topic'); return; }

  const checked = [...document.querySelectorAll('input[name="council-participant"]:checked')];
  const participantIds = checked.map(cb => cb.value);
  if (participantIds.length < 2) {
    if (typeof Toast !== 'undefined') Toast.warning('Select at least 2 participants');
    return;
  }

  const moderatorId = document.getElementById('council-moderator')?.value;
  if (!moderatorId) { if (typeof Toast !== 'undefined') Toast.warning('Select a moderator'); return; }

  const maxRounds = parseInt(document.getElementById('council-rounds')?.value || '10', 10);

  document.getElementById('council-modal')?.remove();

  try {
    const resp = await fetch('/api/council/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        topic,
        participant_session_ids: participantIds,
        moderator_session_id: moderatorId,
        max_rounds: maxRounds,
      }),
    });
    const data = await resp.json();
    if (data.error) {
      if (typeof Toast !== 'undefined') Toast.error('Council error: ' + data.error);
    } else {
      if (typeof Toast !== 'undefined') Toast.info('Council started');
    }
  } catch (err) {
    if (typeof Toast !== 'undefined') Toast.error('Failed to start council: ' + err.message);
  }
}

// ── Section visibility ────────────────────────────────────────────────────────

function openCouncilSection() {
  const wrapper = document.getElementById('council-wrapper');
  if (wrapper) wrapper.classList.add('open');
  renderCouncilPanel();
}

function closeCouncilSection() {
  const wrapper = document.getElementById('council-wrapper');
  if (wrapper) wrapper.classList.remove('open');
}
