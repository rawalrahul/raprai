/* What the AIs in a group chat see: the per-member context meter details,
   room facts, pins and the summaries of older messages (each can be opened to
   read the messages it covers). Server side: helm/groupchat_context/.
   Uses _g, _gFetch and _gToast from groupchat.js. */

function _gcNum(n) { return (n || 0).toLocaleString(); }

function _gcMemberRow(m) {
  const row = _g('div', 'gc-member');
  const pct = Math.max(0, Math.min(100, m.pct || 0));
  row.appendChild(_g('span', 'gc-member-name', (m.name || m.ai || 'AI') + (m.offline ? ' · offline' : '')));
  const bar = _g('span', 'group-context-bar');
  const fill = _g('span', 'group-context-fill');
  fill.style.width = pct + '%';
  if (pct >= 90) fill.classList.add('hot');
  else if (pct >= 70) fill.classList.add('warm');
  bar.appendChild(fill);
  row.appendChild(bar);
  const bits = [_gcNum(m.tokens) + ' / ' + _gcNum(m.budget) + ' tokens'];
  if (m.summaries) bits.push(m.summaries + ' summaries');
  if (m.expanded) bits.push(m.expanded + ' opened word for word');
  if (m.hidden) bits.push(m.hidden + ' not shown');
  row.appendChild(_g('span', 'gc-member-text', bits.join(' · ')));
  return row;
}

function _gcSummaryCard(groupId, s) {
  const card = _g('div', 'group-context-summary gc-summary');
  const head = _g('div', 'gc-summary-head');
  head.appendChild(_g('span', 'gc-summary-id', s.id + ' · level ' + s.level));
  head.appendChild(_g('span', 'gc-summary-topic',
    (s.topic ? s.topic + ' · ' : '') + (s.messages ? s.messages + ' messages' : 'older messages')));
  card.appendChild(head);
  card.appendChild(_g('div', 'gc-summary-text', s.summary || ''));
  if (!s.legacy && s.messages) {
    const btn = _g('button', 'gc-summary-open', 'Show messages');
    const box = _g('div', 'gc-summary-msgs');
    box.hidden = true;
    btn.addEventListener('click', async () => {
      if (!box.hidden) { box.hidden = true; btn.textContent = 'Show messages'; return; }
      if (!box.childNodes.length) {
        try {
          const d = await _gFetch('/api/groups/' + encodeURIComponent(groupId) +
            '/summaries/' + encodeURIComponent(s.id));
          (d.messages || []).forEach(m => box.appendChild(_g('div', 'gc-summary-msg',
            (m.role === 'user' ? 'User' : (m.author_name || 'AI')) + ': ' + (m.content || ''))));
          if (d.missing) box.appendChild(_g('div', 'group-context-empty', d.missing + ' messages are no longer stored.'));
        } catch (err) { _gToast('error', err.message); return; }
      }
      box.hidden = false;
      btn.textContent = 'Hide messages';
    });
    card.appendChild(btn);
    card.appendChild(box);
  }
  return card;
}

async function openGroupContext(id) {
  let d;
  try { d = await _gFetch('/api/groups/' + encodeURIComponent(id) + '/context'); }
  catch (err) { _gToast('error', err.message); return; }
  document.getElementById('group-context-modal')?.remove();
  const overlay = _g('div', 'modal-overlay open');
  overlay.id = 'group-context-modal';
  overlay.style.zIndex = '1300';
  overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
  const content = _g('div', 'modal-content');
  content.style.maxWidth = '600px';
  const head = _g('div', 'modal-header');
  head.appendChild(_g('h3', null, 'What the AIs see'));
  const x = _g('button', 'modal-close', '✕');
  x.addEventListener('click', () => overlay.remove());
  head.appendChild(x);
  content.appendChild(head);

  const body = _g('div', 'modal-body group-context-body');
  const c = d.context || {};
  body.appendChild(_g('p', 'group-context-note',
    'Each AI gets its own view of the chat, sized to its context window: online AIs see up to ' +
    '200K tokens or more, offline models a share of theirs. Older messages are summarised; an AI ' +
    'with room to spare reads them word for word instead, and any AI can ask for the messages ' +
    'behind a summary.' + (c.summarising ? ' Summarising now…' : '')));

  body.appendChild(_g('label', 'council-modal-label', 'Each AI'));
  (c.members || []).forEach(m => body.appendChild(_gcMemberRow(m)));

  const facts = d.facts || [];
  body.appendChild(_g('label', 'council-modal-label', 'Room facts (' + facts.length + ')'));
  if (!facts.length) body.appendChild(_g('div', 'group-context-empty', 'None yet. They are kept with the summaries.'));
  else body.appendChild(_g('div', 'group-context-summary', facts.map(f => '• ' + f).join('\n')));

  const pins = d.pinned || [];
  body.appendChild(_g('label', 'council-modal-label', 'Pinned (' + pins.length + ')'));
  if (!pins.length) body.appendChild(_g('div', 'group-context-empty', 'Nothing pinned. Use “Pin” on a message to keep it in view.'));
  pins.forEach(p => body.appendChild(_g('div', 'group-context-pin', (p.who ? p.who + ': ' : '') + (p.content || ''))));

  const sums = d.summaries || [];
  body.appendChild(_g('label', 'council-modal-label', 'Summaries of older messages (' + sums.length + ')'));
  if (!sums.length) body.appendChild(_g('div', 'group-context-empty', 'No summaries yet. Older messages are summarised once the chat gets long.'));
  sums.forEach(s => body.appendChild(_gcSummaryCard(id, s)));

  content.appendChild(body);
  overlay.appendChild(content);
  document.body.appendChild(overlay);
}
