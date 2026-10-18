/**
 * Share cards: a bake-off result (with optional publishing to RAPR Arena) and
 * the monthly recap. Cards are drawn on a canvas in the browser, so nothing is
 * uploaded unless you press Publish. Uses _el/_api/_toast from finish.js.
 * DOM APIs only (no innerHTML with user data).
 */

const SHARE_W = 1200, SHARE_H = 630;
const SHARE_C = {
  bg1: '#0c1022', bg2: '#1b2152', text: '#f4f5fb', dim: '#a3a9cf', faint: 'rgba(255,255,255,.08)',
  accent: '#8b97ff', gold: '#f5c451', good: '#4ade80', bad: '#f87171',
};
const AI_COLORS = {
  claude: '#d97757', codex: '#10a37f', antigravity: '#4f8cff', gemini: '#4f8cff', ollama: '#e5e7eb',
  copilot: '#8b5cf6', cursor: '#f4f4f5', opencode: '#f59e0b', qwen_code: '#6366f1', groq: '#f55036',
  openrouter: '#94a3b8', aider: '#22c55e', goose: '#eab308',
};
function aiColor(ai) {
  if (AI_COLORS[ai]) return AI_COLORS[ai];
  let h = 0;
  for (const ch of String(ai)) h = (h * 31 + ch.charCodeAt(0)) % 360;
  return `hsl(${h} 70% 62%)`;
}

let _kelvinImg = null;
function _kelvin() {
  if (_kelvinImg) return _kelvinImg;
  _kelvinImg = new Promise(res => {
    const img = new Image();
    img.onload = () => res(img);
    img.onerror = () => res(null);
    img.src = '/assets/kelvin/avatar.png';
  });
  return _kelvinImg;
}

function _font(px, weight) { return `${weight || 500} ${px}px Inter, "Segoe UI", system-ui, -apple-system, sans-serif`; }

function _fit(ctx, text, maxW) {
  if (ctx.measureText(text).width <= maxW) return text;
  let t = text;
  while (t.length > 1 && ctx.measureText(t + '…').width > maxW) t = t.slice(0, -1);
  return t + '…';
}

function _wrap(ctx, text, maxW, maxLines) {
  const words = String(text).split(/\s+/).filter(Boolean);
  const lines = [];
  let line = '';
  for (const w of words) {
    const next = line ? line + ' ' + w : w;
    if (ctx.measureText(next).width > maxW && line) { lines.push(line); line = w; } else line = next;
  }
  if (line) lines.push(line);
  if (lines.length > maxLines) {
    const kept = lines.slice(0, maxLines);
    kept[maxLines - 1] = _fit(ctx, kept[maxLines - 1] + ' ' + lines[maxLines], maxW);
    return kept;
  }
  return lines;
}

function _roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

/** Background, brand line and footer shared by every card. Returns the 2D context. */
async function _cardBase(canvas, kicker) {
  canvas.width = SHARE_W; canvas.height = SHARE_H;
  const ctx = canvas.getContext('2d');
  const g = ctx.createLinearGradient(0, 0, SHARE_W, SHARE_H);
  g.addColorStop(0, SHARE_C.bg1); g.addColorStop(1, SHARE_C.bg2);
  ctx.fillStyle = g; ctx.fillRect(0, 0, SHARE_W, SHARE_H);
  const glow = ctx.createRadialGradient(SHARE_W - 160, 80, 10, SHARE_W - 160, 80, 420);
  glow.addColorStop(0, 'rgba(139,151,255,.28)'); glow.addColorStop(1, 'rgba(139,151,255,0)');
  ctx.fillStyle = glow; ctx.fillRect(0, 0, SHARE_W, SHARE_H);

  const k = await _kelvin();
  if (k) ctx.drawImage(k, 56, 44, 52, 52);
  ctx.fillStyle = SHARE_C.text; ctx.font = _font(26, 700); ctx.textBaseline = 'middle';
  ctx.fillText('RAPR AI', k ? 122 : 56, 70);
  ctx.fillStyle = SHARE_C.dim; ctx.font = _font(22, 500); ctx.textAlign = 'right';
  ctx.fillText(kicker, SHARE_W - 56, 70);
  ctx.textAlign = 'left';

  ctx.fillStyle = SHARE_C.faint; ctx.fillRect(56, SHARE_H - 76, SHARE_W - 112, 1);
  ctx.fillStyle = SHARE_C.dim; ctx.font = _font(20, 500);
  ctx.fillText('Run your AI agents side by side, free and open source', 56, SHARE_H - 42);
  ctx.fillStyle = SHARE_C.accent; ctx.font = _font(20, 700); ctx.textAlign = 'right';
  ctx.fillText('raprai.com', SHARE_W - 56, SHARE_H - 42);
  ctx.textAlign = 'left';
  return ctx;
}

function _secs(s) {
  s = Math.round(s || 0);
  return s >= 60 ? `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, '0')}s` : `${s}s`;
}
function _money(n) { return '$' + (n >= 100 ? Math.round(n).toLocaleString() : n.toFixed(2)); }

/** Draw a bake-off result. r: the result from /api/bakeoff/{id}/share; task: shown only if given. */
async function drawBakeoffCard(canvas, r, task) {
  const ctx = await _cardBase(canvas, ['AI bake-off', r.category, r.language].filter(Boolean).join(' · '));
  let y = 150;
  const winner = r.attempts.find(a => a.winner);
  ctx.fillStyle = SHARE_C.text; ctx.font = _font(54, 800); ctx.textBaseline = 'alphabetic';
  ctx.fillText(winner ? `🏆 ${winner.ai} wins` : 'No clear winner', 56, y + 20);
  y += 50;
  if (task) {
    ctx.fillStyle = SHARE_C.dim; ctx.font = _font(26, 500);
    _wrap(ctx, '“' + task + '”', SHARE_W - 112, 2).forEach(l => { y += 34; ctx.fillText(l, 56, y); });
  }
  y += 34;

  const rows = [...r.attempts].sort((a, b) => (b.winner - a.winner) || (a.failed - b.failed) || (a.seconds - b.seconds));
  const maxS = Math.max(1, ...rows.map(a => a.seconds || 0));
  const rowH = Math.min(78, (SHARE_H - 110 - y) / rows.length);
  rows.forEach((a, i) => {
    const top = y + i * rowH;
    _roundRect(ctx, 56, top, SHARE_W - 112, rowH - 12, 14);
    ctx.fillStyle = a.winner ? 'rgba(245,196,81,.12)' : 'rgba(255,255,255,.05)'; ctx.fill();
    if (a.winner) { ctx.strokeStyle = 'rgba(245,196,81,.55)'; ctx.lineWidth = 2; ctx.stroke(); }
    const mid = top + (rowH - 12) / 2;
    ctx.textBaseline = 'middle';
    ctx.fillStyle = aiColor(a.ai); ctx.beginPath(); ctx.arc(84, mid, 9, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = SHARE_C.text; ctx.font = _font(28, 700);
    ctx.fillText(_fit(ctx, a.ai, 230), 106, mid);

    // time bar
    const bx = 360, bw = 300;
    ctx.fillStyle = SHARE_C.faint; _roundRect(ctx, bx, mid - 6, bw, 12, 6); ctx.fill();
    if (!a.failed) {
      ctx.fillStyle = a.winner ? SHARE_C.gold : SHARE_C.accent;
      _roundRect(ctx, bx, mid - 6, Math.max(12, bw * (a.seconds || 0) / maxS), 12, 6); ctx.fill();
    }
    ctx.fillStyle = SHARE_C.text; ctx.font = _font(24, 600);
    ctx.fillText(a.failed ? 'failed' : _secs(a.seconds), bx + bw + 18, mid);

    ctx.textAlign = 'right'; ctx.fillStyle = SHARE_C.dim; ctx.font = _font(22, 500);
    const bits = a.failed ? [] : [`${a.files_changed} file${a.files_changed === 1 ? '' : 's'}`, `+${a.lines_added} −${a.lines_removed}`];
    if (a.tests_passed === true) bits.push('tests ✅');
    if (a.tests_passed === false) bits.push('tests ❌');
    ctx.fillText(bits.join('   '), SHARE_W - 84, mid);
    ctx.textAlign = 'left';
  });
}

/** Draw the monthly recap. s: the result of /api/recap. */
async function drawRecapCard(canvas, s) {
  const ctx = await _cardBase(canvas, 'My ' + s.month_label);
  ctx.textBaseline = 'alphabetic';
  ctx.fillStyle = SHARE_C.dim; ctx.font = _font(24, 600);
  ctx.fillText('THIS MONTH I WAS', 56, 160);
  ctx.fillStyle = SHARE_C.text; ctx.font = _font(68, 800);
  ctx.fillText(s.persona, 56, 230);
  ctx.fillStyle = SHARE_C.dim; ctx.font = _font(26, 500);
  ctx.fillText(_fit(ctx, s.persona_line, 600), 56, 272);

  const tiles = [
    [s.messages_sent.toLocaleString(), 'tasks sent'],
    [s.replies.toLocaleString(), 'AI replies'],
    [String(s.active_days), 'active days'],
    [String(s.longest_streak), 'day streak'],
  ];
  tiles.forEach(([v, l], i) => {
    const x = 56 + i * 150;
    ctx.fillStyle = SHARE_C.text; ctx.font = _font(44, 800); ctx.fillText(v, x, 360);
    ctx.fillStyle = SHARE_C.dim; ctx.font = _font(20, 500); ctx.fillText(l, x, 392);
  });

  const money = [];
  if (s.saved_usd >= 0.01) money.push(`${_money(s.saved_usd)} saved by running AIs locally`);
  if (s.api_value_usd >= 0.01) money.push(`at least ${_money(s.api_value_usd)} of AI work at API prices`);
  if (s.bakeoffs) money.push(`${s.bakeoffs} bake-off${s.bakeoffs === 1 ? '' : 's'} judged`);
  if (s.from_chat_apps) money.push(`${s.from_chat_apps} task${s.from_chat_apps === 1 ? '' : 's'} sent from my phone`);
  ctx.font = _font(24, 600);
  money.slice(0, 3).forEach((m, i) => {
    ctx.fillStyle = SHARE_C.accent; ctx.fillText('●', 56, 450 + i * 38);
    ctx.fillStyle = SHARE_C.text; ctx.fillText(_fit(ctx, m, 560), 84, 450 + i * 38);
  });

  // My crew: share of replies per AI
  const px = 720, pw = SHARE_W - 56 - px;
  const crew = s.ais.slice(0, 5);
  _roundRect(ctx, px, 130, pw, 96 + Math.max(1, crew.length) * 60, 18); ctx.fillStyle = 'rgba(255,255,255,.05)'; ctx.fill();
  ctx.fillStyle = SHARE_C.dim; ctx.font = _font(20, 600);
  ctx.fillText('MY AI CREW', px + 28, 172);
  crew.forEach((a, i) => {
    const y = 214 + i * 60;
    ctx.fillStyle = SHARE_C.text; ctx.font = _font(24, i === 0 ? 800 : 600);
    ctx.fillText(_fit(ctx, (i === 0 ? '👑 ' : '') + a.label, pw - 140), px + 28, y);
    ctx.textAlign = 'right'; ctx.fillStyle = SHARE_C.dim; ctx.font = _font(20, 500);
    ctx.fillText(Math.round(a.share * 100) + '%', px + pw - 28, y);
    ctx.textAlign = 'left';
    ctx.fillStyle = SHARE_C.faint; _roundRect(ctx, px + 28, y + 14, pw - 56, 10, 5); ctx.fill();
    ctx.fillStyle = aiColor(a.ai); _roundRect(ctx, px + 28, y + 14, Math.max(10, (pw - 56) * a.share), 10, 5); ctx.fill();
  });
  if (!crew.length) { ctx.fillStyle = SHARE_C.dim; ctx.font = _font(22, 500); ctx.fillText('No AI replies yet', px + 28, 214); }
}

// ── Shared dialog bits ───────────────────────────────────────────────────────

function _shareModal(id, title) {
  document.getElementById(id)?.remove();
  const overlay = _el('div', 'modal-overlay open');
  overlay.id = id;
  overlay.style.zIndex = '1310';
  overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
  const content = _el('div', 'modal-content');
  content.style.cssText = 'max-width:720px;width:96vw';
  const head = _el('div', 'modal-header');
  const h = _el('h3', null, title);
  head.appendChild(h);
  const x = _el('button', 'modal-close', '✕');
  x.setAttribute('aria-label', 'Close');
  x.addEventListener('click', () => overlay.remove());
  head.appendChild(x);
  const body = _el('div', 'modal-body');
  body.style.cssText = 'display:flex;flex-direction:column;gap:12px;max-height:80vh;overflow:auto';
  content.append(head, body);
  overlay.appendChild(content);
  document.body.appendChild(overlay);
  return { overlay, body, title: h };
}

function _cardPreview() {
  const canvas = document.createElement('canvas');
  canvas.style.cssText = 'width:100%;height:auto;border-radius:12px;border:1px solid var(--border-dim);display:block';
  canvas.setAttribute('role', 'img');
  return canvas;
}

async function _copy(text, what) {
  try { await navigator.clipboard.writeText(text); _toast('success', (what || 'Text') + ' copied'); }
  catch (_) { _toast('error', 'Could not copy. Select the text and copy it instead.'); }
}

function _download(canvas, name) {
  canvas.toBlob(blob => {
    if (!blob) return;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }, 'image/png');
}

function _xIntent(text) {
  return 'https://x.com/intent/post?text=' + encodeURIComponent(text);
}

function _btn(label, cls, onClick) {
  const b = _el('button', cls || 'council-btn-secondary', label);
  b.addEventListener('click', onClick);
  return b;
}

function _row() {
  const r = _el('div');
  r.style.cssText = 'display:flex;gap:8px;flex-wrap:wrap;align-items:center';
  return r;
}

// ── Bake-off: share and publish ──────────────────────────────────────────────

async function openBakeoffShare(bid) {
  const { body } = _shareModal('bakeoff-share', 'Share this bake-off');
  body.appendChild(_el('div', null, 'Loading…'));
  let d;
  try { d = await _api('/api/bakeoff/' + encodeURIComponent(bid) + '/share'); }
  catch (err) { body.textContent = err.message; return; }
  body.textContent = '';

  const state = { include: false, task: d.result.task || '', category: d.result.category, url: d.arena_url };
  const canvas = _cardPreview();
  canvas.setAttribute('aria-label', 'Bake-off result card');
  body.appendChild(canvas);

  const text = document.createElement('textarea');
  text.className = 'council-modal-textarea'; text.rows = 5; text.readOnly = true;
  text.setAttribute('aria-label', 'Text to post');
  body.appendChild(text);

  const actions = _row();
  actions.append(
    _btn('Copy text', null, () => _copy(text.value)),
    _btn('Download image', null, () => _download(canvas, `rapr-bakeoff-${bid}.png`)),
    _btn('Post on X', null, () => window.open(_xIntent(text.value), '_blank', 'noopener')),
  );
  body.appendChild(actions);

  // Arena
  const arena = _el('div');
  arena.style.cssText = 'border-top:1px solid var(--border-dim);padding-top:12px;display:flex;flex-direction:column;gap:10px';
  arena.appendChild(_el('strong', null, 'Publish to RAPR Arena'));
  const host = d.arena.replace(/^https?:\/\//, '');
  arena.appendChild(_el('div', null,
    `Add this result to the public leaderboard at ${host}/arena, where everyone's bake-offs show which AI wins which kind of task, and get a link to share.`));

  const catRow = _row();
  const catLbl = _el('label', 'council-modal-label', 'Kind of task');
  const cat = document.createElement('select');
  cat.className = 'council-modal-select'; cat.style.width = 'auto';
  d.categories.forEach(c => { const o = _el('option', null, c); o.value = c; o.selected = c === state.category; cat.appendChild(o); });
  catLbl.htmlFor = cat.id = 'bake-share-cat';
  catRow.append(catLbl, cat);
  arena.appendChild(catRow);

  const incLbl = _el('label');
  incLbl.style.cssText = 'display:flex;gap:8px;align-items:center';
  const inc = document.createElement('input'); inc.type = 'checkbox';
  incLbl.append(inc, document.createTextNode('Include the task (it will be public)'));
  arena.appendChild(incLbl);
  const taskIn = document.createElement('input');
  taskIn.className = 'council-modal-select'; taskIn.maxLength = 280; taskIn.value = state.task;
  taskIn.setAttribute('aria-label', 'Task as it will be shown');
  taskIn.style.display = 'none';
  arena.appendChild(taskIn);

  const det = document.createElement('details');
  det.appendChild(_el('summary', null, 'Exactly what gets sent'));
  det.appendChild(_el('div', null, 'No code, file names, folder paths or AI replies are ever sent.'));
  const pre = _el('pre');
  pre.style.cssText = 'white-space:pre-wrap;font-size:11px;max-height:220px;overflow:auto;margin:6px 0 0';
  det.appendChild(pre);
  arena.appendChild(det);

  const pubRow = _row();
  const pub = _btn('Publish', 'council-btn-primary', () => publish());
  pubRow.appendChild(pub);
  arena.appendChild(pubRow);
  if (!d.can_publish) {
    pub.disabled = true;
    pubRow.appendChild(_el('span', null, 'Merge a winner (or discard them all) first.'));
  }
  body.appendChild(arena);

  const showLink = (url) => {
    pubRow.textContent = '';
    const link = _el('a', null, url);
    link.href = url; link.target = '_blank'; link.rel = 'noopener';
    pubRow.append(_el('span', null, '✅ Published:'), link, _btn('Copy link', null, () => _copy(url, 'Link')));
    [catRow, incLbl, taskIn, det].forEach(n => { n.style.display = 'none'; });
  };

  let seq = 0;
  const refresh = async () => {
    const my = ++seq;
    const q = new URLSearchParams({ include_task: state.include ? '1' : '0', task: state.task, category: state.category });
    let s;
    try { s = await _api('/api/bakeoff/' + encodeURIComponent(bid) + '/share?' + q); } catch (_) { return; }
    if (my !== seq) return;
    text.value = s.text;
    pre.textContent = JSON.stringify(s.payload, null, 2);
    await drawBakeoffCard(canvas, { ...s.result, category: s.payload.category }, s.payload.task);
  };
  let timer = null;
  const later = () => { clearTimeout(timer); timer = setTimeout(refresh, 250); };
  cat.addEventListener('change', () => { state.category = cat.value; refresh(); });
  inc.addEventListener('change', () => { state.include = inc.checked; taskIn.style.display = inc.checked ? '' : 'none'; refresh(); });
  taskIn.addEventListener('input', () => { state.task = taskIn.value; later(); });

  async function publish() {
    pub.disabled = true; pub.textContent = 'Publishing…';
    try {
      const r = await _api('/api/bakeoff/' + encodeURIComponent(bid) + '/publish', {
        method: 'POST', body: JSON.stringify({ include_task: state.include, task: state.task, category: state.category }),
      });
      if (r.text) text.value = r.text;
      showLink(r.url);
      _toast('success', 'Published to RAPR Arena');
    } catch (err) {
      pub.disabled = false; pub.textContent = 'Publish';
      _toast('error', 'Arena: ' + err.message);
    }
  }

  await refresh();
  if (state.url) showLink(state.url);
}

// ── Monthly recap ────────────────────────────────────────────────────────────

function _monthShift(month, by) {
  const [y, m] = month.split('-').map(Number);
  const d = new Date(y, m - 1 + by, 1);
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
}
function _thisMonth() { const d = new Date(); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0'); }

async function openRecap(month) {
  const { body, title } = _shareModal('recap-modal', 'Your month with RAPR');
  month = month || _thisMonth();

  const nav = _row();
  nav.style.justifyContent = 'space-between';
  const prev = _btn('‹ Previous', null, () => go(-1));
  const label = _el('strong');
  const next = _btn('Next ›', null, () => go(1));
  nav.append(prev, label, next);
  body.appendChild(nav);

  const canvas = _cardPreview();
  canvas.setAttribute('aria-label', 'Monthly recap card');
  body.appendChild(canvas);
  const empty = _el('div', 'sb-empty', '');
  body.appendChild(empty);

  const text = document.createElement('textarea');
  text.className = 'council-modal-textarea'; text.rows = 6; text.readOnly = true;
  text.setAttribute('aria-label', 'Text to post');
  body.appendChild(text);

  const actions = _row();
  actions.append(
    _btn('Copy text', null, () => _copy(text.value)),
    _btn('Download image', null, () => _download(canvas, `rapr-recap-${month}.png`)),
    _btn('Post on X', null, () => window.open(_xIntent(text.value), '_blank', 'noopener')),
  );
  body.appendChild(actions);
  body.appendChild(_el('div', null,
    'Worked out on your computer from your chat history; nothing is uploaded. Dollar figures are estimates from the text you saw, at API list prices.'));

  let first = null;
  async function load() {
    label.textContent = '…';
    let s;
    try { s = await _api('/api/recap?month=' + encodeURIComponent(month)); }
    catch (err) { empty.textContent = err.message; return; }
    first = s.first_month;
    label.textContent = s.month_label;
    title.textContent = 'Your ' + s.month_label + ' with RAPR';
    prev.disabled = !first || month <= first;
    next.disabled = month >= _thisMonth();
    const hasData = !s.empty;
    canvas.style.display = actions.style.display = text.style.display = hasData ? '' : 'none';
    empty.style.display = hasData ? 'none' : '';
    empty.textContent = hasData ? '' : 'Nothing happened this month yet. Come back after a few chats.';
    if (!hasData) return;
    await drawRecapCard(canvas, s);
    const top = s.mvp ? `MVP: ${s.mvp.label}` : '';
    const lines = [
      `My ${s.month_label} with RAPR AI: ${s.persona} 🐧`,
      `${s.messages_sent} tasks · ${s.replies} AI replies · ${s.active_days} active days${top ? ' · ' + top : ''}`,
    ];
    if (s.saved_usd >= 0.01) lines.push(`${_money(s.saved_usd)} saved running AIs locally`);
    if (s.bakeoffs) lines.push(`${s.bakeoffs} AI bake-off${s.bakeoffs === 1 ? '' : 's'} judged`);
    lines.push('https://raprai.com');
    text.value = lines.join('\n');
  }
  function go(by) { month = _monthShift(month, by); load(); }
  await load();
}

/** Once a month, offer last month's recap (only if there was anything in it). */
async function maybeOfferRecap() {
  const last = _monthShift(_thisMonth(), -1);
  let seen = null;
  try { seen = localStorage.getItem('rapr-recap-offered'); } catch (_) {}
  if (seen === last) return;
  try {
    const s = await _api('/api/recap?month=' + last);
    try { localStorage.setItem('rapr-recap-offered', last); } catch (_) {}
    if (s.empty) return;
    if (typeof Toast === 'undefined' || !Toast.info) return;
    const id = Toast.info(`🐧 Your ${s.month_label} recap is ready: you were "${s.persona}". Click to see it.`, 12000);
    const el = document.getElementById('toast-' + id);
    if (el) {
      el.style.cursor = 'pointer';
      el.addEventListener('click', e => { if (e.target.tagName !== 'BUTTON') openRecap(last); });
    }
  } catch (_) {}
}
setTimeout(maybeOfferRecap, 8000);
