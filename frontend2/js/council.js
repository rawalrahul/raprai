/**
 * AI Council — debate panel UI + WebSocket event handlers
 * Uses DOM APIs (no innerHTML with user data) for XSS safety.
 */

const councilState = {
  activeCouncil: null,
  streamingParticipant: null,
  streamBuffer: "",
  expandedMessages: new Set(),
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
  // Don't scroll if user is typing in the inject bar
  const input = document.getElementById('council-inject-input');
  if (input && document.activeElement === input) return;

  const section = document.getElementById('council-section');
  if (!section) return;

  // Don't scroll if user has scrolled up to read (>150px from bottom)
  const distFromBottom = section.scrollHeight - section.scrollTop - section.clientHeight;
  if (distFromBottom > 150) return;

  setTimeout(() => { section.scrollTop = section.scrollHeight; }, 0);
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
  const content = msg.content || '';

  if (!streaming && content.length > 320) {
    const msgId = msg.id || '';
    const startExpanded = msgId && councilState.expandedMessages.has(msgId);

    const preview = _el('span');
    preview.textContent = content.slice(0, 320) + '…';
    preview.style.display = startExpanded ? 'none' : '';

    const full = _el('span');
    full.textContent = content;
    full.style.display = startExpanded ? '' : 'none';

    const toggle = _el('button', 'council-expand-btn', startExpanded ? 'Show less' : 'Show more');
    toggle.addEventListener('click', () => {
      const open = full.style.display !== 'none';
      full.style.display = open ? 'none' : '';
      preview.style.display = open ? '' : 'none';
      toggle.textContent = open ? 'Show more' : 'Show less';
      if (msgId) {
        if (open) councilState.expandedMessages.delete(msgId);
        else councilState.expandedMessages.add(msgId);
      }
    });
    body.appendChild(preview);
    body.appendChild(full);
    body.appendChild(toggle);
  } else {
    body.textContent = content;
  }

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

  // Preserve state that re-render would destroy
  const prevInput = document.getElementById('council-inject-input');
  const savedText = prevInput ? prevInput.value : '';
  const wasFocused = prevInput && document.activeElement === prevInput;
  const savedSelStart = wasFocused ? prevInput.selectionStart : null;
  const savedSelEnd = wasFocused ? prevInput.selectionEnd : null;
  const savedScroll = section.scrollTop;

  // Clear panel
  while (section.firstChild) section.removeChild(section.firstChild);

  const council = councilState.activeCouncil;

  if (!council) {
    const empty = _el('div', 'council-empty');

    const icon = _el('div', 'council-empty-icon'); icon.textContent = '⚖';
    const title = _el('div', 'council-empty-title', 'AI Council');
    const desc = _el('div', 'council-empty-desc', 'Pick a topic, assign participants and a moderator, let your AIs debate.');
    const btn = _el('button', 'council-btn-primary', 'Start Council');
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

  const headerRight = _el('div');
  headerRight.style.cssText = 'display:flex;align-items:center;gap:6px';

  if (council.status === 'running') {
    const stopBtn = _el('button', 'council-btn-stop', 'Stop');
    stopBtn.addEventListener('click', () => stopCouncil(council.id));
    headerRight.appendChild(stopBtn);
  } else {
    const exportBtn = _el('button', 'council-btn-secondary', 'Export');
    exportBtn.addEventListener('click', () => _exportCouncilMarkdown(council));
    headerRight.appendChild(exportBtn);
    const newBtn = _el('button', 'council-btn-secondary', 'New');
    newBtn.addEventListener('click', openCouncilModal);
    headerRight.appendChild(newBtn);
  }
  header.appendChild(headerRight);
  section.appendChild(header);

  // Topic
  section.appendChild(_el('div', 'council-topic', council.topic));

  // Participants row + scoreboard
  const pRow = _el('div', 'council-participants-row');
  (council.participants || []).forEach(p => {
    const chip = _el('span', 'council-participant-dot');
    chip.title = p.ai;
    const swatch = _el('span', 'council-participant-dot-swatch');
    swatch.style.background = p.color || '#6b7280';
    chip.appendChild(swatch);
    chip.appendChild(document.createTextNode(p.name || p.ai));
    pRow.appendChild(chip);
  });
  const roundBadge = _el('span', 'council-round-badge',
    'Round ' + council.rounds + ' / ' + council.max_rounds);
  pRow.appendChild(roundBadge);
  section.appendChild(pRow);

  // Scoreboard
  if (council.scores && Object.keys(council.scores).length > 0) {
    const sb = _el('div', 'council-scoreboard');
    sb.id = 'council-scoreboard';
    const maxScore = Math.max(0, ...Object.values(council.scores).map(Number));
    (council.participants || []).forEach(p => {
      const score = (council.scores || {})[p.ai] || 0;
      const chip = _el('span', 'council-score-chip' + (score >= maxScore && maxScore > 0 ? ' leader' : ''));
      const swatch = _el('span', 'council-participant-dot-swatch');
      swatch.style.cssText = `background:${p.color||'#6b7280'};display:inline-block;margin-right:5px;vertical-align:middle`;
      chip.appendChild(swatch);
      chip.appendChild(document.createTextNode(`${p.name}: ${score}`));
      sb.appendChild(chip);
    });
    section.appendChild(sb);
  }

  // Overall winner banner
  if (council.overall_winner) {
    const w = council.overall_winner;
    const winBanner = _el('div', 'council-overall-winner');
    winBanner.appendChild(_el('div', 'council-overall-winner-label', 'Debate Complete'));
    winBanner.appendChild(_el('div', 'council-overall-winner-name',
      `${w.name}  ·  ${w.score} / ${w.total_rounds} rounds`));
    if (w.verdict) {
      winBanner.appendChild(_el('div', 'council-overall-winner-verdict', w.verdict));
    }
    section.appendChild(winBanner);
  }

  // Messages with round dividers
  const msgContainer = _el('div', 'council-messages');
  msgContainer.id = 'council-messages';
  const nP = (council.participants || []).length;
  let pCount = 0;
  let rNum = 0;
  (council.messages || []).forEach(msg => {
    if (msg.role === 'participant' && nP > 0) {
      if (pCount % nP === 0) {
        rNum++;
        const div = _el('div', 'council-round-divider');
        div.appendChild(_el('span', null, `Round ${rNum}`));
        msgContainer.appendChild(div);
      }
      pCount++;
    }
    const node = _buildMessageNode(msg);
    if (node) msgContainer.appendChild(node);
  });
  section.appendChild(msgContainer);

  // Consensus box
  if (council.consensus_summary) {
    const box = _el('div', 'council-consensus-box');
    box.appendChild(_el('div', 'council-consensus-title', 'Consensus Reached'));
    if (council.early_consensus) {
      const note = _el('div', 'council-early-consensus-note',
        `Concluded after ${council.rounds} of ${council.max_rounds} rounds — participants reached consensus early.`);
      box.appendChild(note);
    }
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

  // Restore inject input text, cursor, focus and scroll position
  section.scrollTop = savedScroll;
  if (savedText || wasFocused) {
    const newInput = document.getElementById('council-inject-input');
    if (newInput) {
      newInput.value = savedText;
      if (wasFocused) {
        newInput.focus();
        if (savedSelStart !== null) newInput.setSelectionRange(savedSelStart, savedSelEnd);
      }
    }
  }
}

// ── WS event handlers ─────────────────────────────────────────────────────────

function councilOnCreated(data) {
  councilState.activeCouncil = data.council || data;
  councilState.streamingParticipant = null;
  councilState.streamBuffer = '';
  openCouncilSection();
  const id = (data.council || data).id;
  if (id) _startCouncilPoll(id);
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

function councilOnRoundResult(data) {
  if (!councilState.activeCouncil) return;
  if (data.council_id !== councilState.activeCouncil.id) return;
  if (data.scores) councilState.activeCouncil.scores = data.scores;
  if (data.result) {
    councilState.activeCouncil.round_results = councilState.activeCouncil.round_results || [];
    councilState.activeCouncil.round_results.push(data.result);
  }
  _updateScoreboard();
  const container = document.getElementById('council-messages');
  if (container && data.result) {
    const r = data.result;
    const banner = _el('div', 'council-round-winner-banner');
    const label = _el('div', 'council-round-winner-label', `Round ${r.round} verdict`);
    const body = _el('div');
    const nameSpan = _el('span', 'council-round-winner-name', r.winner_name);
    body.appendChild(nameSpan);
    body.appendChild(document.createTextNode(' — ' + r.reasoning));
    banner.appendChild(label);
    banner.appendChild(body);
    container.appendChild(banner);

    // Divider for next round if debate continues
    const nextRound = data.result.round + 1;
    if (nextRound <= (councilState.activeCouncil?.max_rounds || 0)) {
      const divider = _el('div', 'council-round-divider');
      divider.appendChild(_el('span', null, `Round ${nextRound}`));
      container.appendChild(divider);
    }

    _scrollCouncilMessages();
  }
}

function _updateScoreboard() {
  const sb = document.getElementById('council-scoreboard');
  if (!sb || !councilState.activeCouncil?.scores) return;
  while (sb.firstChild) sb.removeChild(sb.firstChild);
  const c = councilState.activeCouncil;
  const maxScore = Math.max(0, ...Object.values(c.scores).map(Number));
  (c.participants || []).forEach(p => {
    const score = c.scores[p.ai] || 0;
    const chip = _el('span', 'council-score-chip' + (score >= maxScore && maxScore > 0 ? ' leader' : ''));
    const swatch = _el('span', 'council-participant-dot-swatch');
    swatch.style.cssText = `background:${p.color||'#6b7280'};display:inline-block;margin-right:5px;vertical-align:middle`;
    chip.appendChild(swatch);
    chip.appendChild(document.createTextNode(`${p.name}: ${score}`));
    sb.appendChild(chip);
  });
}

function councilOnCompleted(data) {
  councilState.activeCouncil = data.council || data;
  _stopCouncilPoll();
  renderCouncilPanel();
}

function councilOnStopped(data) {
  if (councilState.activeCouncil && data.council_id === councilState.activeCouncil.id) {
    if (data.council) councilState.activeCouncil = data.council;
    else councilState.activeCouncil.status = 'stopped';
    _stopCouncilPoll();
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

async function openCouncilModal() {
  const existing = document.getElementById('council-modal');
  if (existing) existing.remove();

  let sessions = (typeof State !== 'undefined' ? State.sessions : []) || [];
  if (sessions.length === 0) {
    try {
      const r = await fetch('/api/sessions');
      const d = await r.json();
      sessions = d.sessions || [];
    } catch (_) {}
  }

  const overlay = _el('div', 'modal-overlay open');
  overlay.id = 'council-modal';
  overlay.style.zIndex = '1300';
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
      dot.style.background = s.color || s.ai_color || '#6b7280';
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
      if (data.council) councilOnCreated(data);
    }
  } catch (err) {
    if (typeof Toast !== 'undefined') Toast.error('Failed to start council: ' + err.message);
  }
}

// ── Council poll (fallback for missed WS events) ──────────────────────────────

let _councilPollTimer = null;

function _startCouncilPoll(councilId) {
  _stopCouncilPoll();
  _councilPollTimer = setInterval(async () => {
    const c = councilState.activeCouncil;
    if (!c || (c.status !== 'pending' && c.status !== 'running')) {
      _stopCouncilPoll();
      return;
    }
    try {
      const r = await fetch('/api/council/list');
      const d = await r.json();
      const all = [...(d.active || []), ...(d.history || [])];
      const updated = all.find(x => x.id === councilId);
      if (updated) {
        councilState.activeCouncil = updated;
        renderCouncilPanel();
        if (updated.status !== 'pending' && updated.status !== 'running') _stopCouncilPoll();
      }
    } catch (_) {}
  }, 3000);
}

function _stopCouncilPoll() {
  if (_councilPollTimer) { clearInterval(_councilPollTimer); _councilPollTimer = null; }
}

// ── Export ────────────────────────────────────────────────────────────────────

function _exportCouncilMarkdown(council) {
  const lines = [
    `# AI Council Debate`,
    ``,
    `**Topic:** ${council.topic}`,
    `**Participants:** ${(council.participants || []).map(p => p.name).join(', ')}`,
    `**Rounds:** ${council.rounds} / ${council.max_rounds}`,
    ``,
  ];

  if (council.scores) {
    lines.push('## Scores', '');
    (council.participants || []).forEach(p => {
      lines.push(`- ${p.name}: ${council.scores[p.ai] || 0}`);
    });
    lines.push('');
  }

  lines.push('## Transcript', '');
  (council.messages || []).forEach(msg => {
    if (msg.role === 'moderator') {
      lines.push(`**Moderator:** ${msg.content}`, '');
    } else if (msg.role === 'participant') {
      lines.push(`**${msg.participant_name} (${msg.participant_ai}):**`, '', msg.content, '');
    } else if (msg.role === 'system') {
      lines.push(`---`, `*${msg.content}*`, '');
    }
  });

  if (council.overall_winner) {
    const w = council.overall_winner;
    lines.push('## Final Verdict', '', `**Winner:** ${w.name} (${w.score}/${w.total_rounds} rounds)`, '', w.verdict || '');
  }

  const blob = new Blob([lines.join('\n')], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `council-${(council.id || 'debate').slice(0, 8)}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Resize handle ─────────────────────────────────────────────────────────────

let _councilResizeInited = false;

function _initCouncilResize() {
  if (_councilResizeInited) return;
  const handle = document.getElementById('council-resize-handle');
  const overlay = document.getElementById('council-overlay');
  if (!handle || !overlay) return;
  _councilResizeInited = true;

  const saved = localStorage.getItem('council-panel-width');
  if (saved) overlay.style.width = saved + 'px';

  let startX, startW;
  handle.addEventListener('mousedown', e => {
    e.preventDefault();
    startX = e.clientX;
    startW = overlay.offsetWidth;
    handle.classList.add('dragging');
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'ew-resize';

    const onMove = ev => {
      const dx = startX - ev.clientX;
      const w = Math.max(380, Math.min(window.innerWidth - 80, startW + dx));
      overlay.style.width = w + 'px';
    };
    const onUp = () => {
      handle.classList.remove('dragging');
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
      localStorage.setItem('council-panel-width', String(overlay.offsetWidth));
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  });
}

// ── Section visibility ────────────────────────────────────────────────────────

function openCouncilSection() {
  const wrapper = document.getElementById('council-wrapper');
  if (wrapper) wrapper.classList.add('open');
  _initCouncilResize();
  renderCouncilPanel();
}

function closeCouncilSection() {
  const wrapper = document.getElementById('council-wrapper');
  if (wrapper) wrapper.classList.remove('open');
}
