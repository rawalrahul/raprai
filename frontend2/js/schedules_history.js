// The web UI's main script, part 4 of 8. index.html loads the parts in order.
// --- History modal ------------------------------------------------------------------------------------------
// --- Schedules modal ---------------------------------------------------------------------------------------
let _schedTasks = [];

function openSchedules(){
  document.getElementById('sched-modal').style.display = 'flex';
  cmd('schedule_list');  // request fresh list from server
}
function closeSchedules(){
  document.getElementById('sched-modal').style.display = 'none';
}

function renderSchedules(tasks){
  _schedTasks = tasks || [];
  // Update sidebar scheduled tasks
  updateSbScheduled(_schedTasks);
  const el = document.getElementById('sched-list');
  if(!_schedTasks.length){
    el.innerHTML = '<div class="modal-empty">No scheduled tasks yet.<br>Use the form below to add one.</div>';
    return;
  }
  el.innerHTML = _schedTasks.map(t => {
    const ico = t.enabled ? '✅' : '⏸';
    const ai  = t.ai || 'shell';
    return `<div class="sched-row">
      <div class="sched-meta">
        ${ico} <strong>${escHtml(t.name)}</strong>
        <code style="margin-left:6px;font-size:11px">${escHtml(t.cron)}</code>
        <span class="sched-ai-badge ${ai}">${ai}</span>
      </div>
      <div class="sched-prompt">${escHtml(t.prompt.length>80 ? t.prompt.slice(0,80)+'...' : t.prompt)}</div>
      <div class="sched-times">Next: ${escHtml(t.next_run_fmt)} &nbsp;·&nbsp; Last: ${escHtml(t.last_run_fmt)} &nbsp;·&nbsp; Runs: ${t.run_count||0}</div>
      <div class="sched-actions">
        <button onclick="cmd('schedule_run:${t.id}')" title="Run now">â–¶</button>
        <button onclick="cmd('schedule_toggle:${t.id}')" title="${t.enabled?'Pause':'Enable'}">${t.enabled?'⏸':'â–¶ï¸'}</button>
        <button onclick="if(confirm('Delete ${escHtml(t.name)}?'))cmd('schedule_delete:${t.id}')" title="Delete" style="color:#f87171">🗑️</button>
      </div>
    </div>`;
  }).join('');
}

// --- Shared schedule builder from friendly picker ---------------------------------------------------
function _buildCronFromPicker(pfx){
  // pfx = '' for modal, 'sb-' for sidebar
  const freq = document.getElementById(pfx+'sched-freq').value;
  let hour = parseInt(document.getElementById(pfx+'sched-hour').value, 10);
  const min  = parseInt(document.getElementById(pfx+'sched-min').value, 10);
  const ampm = document.getElementById(pfx+'sched-ampm').value;
  if(ampm === 'pm' && hour !== 12) hour += 12;
  if(ampm === 'am' && hour === 12) hour = 0;
  if(freq === 'daily')   return `${min} ${hour} * * *`;
  if(freq === 'weekly'){
    const checks = document.querySelectorAll(`input[name="${pfx}sched-wd"]:checked`);
    const days = [...checks].map(c => c.value).join(',');
    return `${min} ${hour} * * ${days || '*'}`;
  }
  if(freq === 'monthly') return `${min} ${hour} ${document.getElementById(pfx+'sched-monthday').value} * *`;
  return '';
}
function _schedFreqToggle(pfx){
  const freq = document.getElementById(pfx+'sched-freq').value;
  document.getElementById(pfx+'sched-weekday-row').style.display  = freq==='weekly'  ? '' : 'none';
  document.getElementById(pfx+'sched-monthday-row').style.display = freq==='monthly' ? '' : 'none';
  document.getElementById(pfx+'sched-time-row').style.display     = '';
}
function schedFreqChange()   { _schedFreqToggle(''); }
function sbSchedFreqChange() { _schedFreqToggle('sb-'); }
function _initSchedPicker(pfx){
  // Populate hours 1-12
  const hSel = document.getElementById(pfx+'sched-hour');
  if(hSel && !hSel.options.length){
    for(let h=1;h<=12;h++){
      const o = document.createElement('option'); o.value=h; o.textContent=h; hSel.appendChild(o);
    }
    hSel.value = 9; // default 9
  }
  // Populate month days 1-28
  const mSel = document.getElementById(pfx+'sched-monthday');
  if(mSel && !mSel.options.length){
    for(let d=1;d<=28;d++){
      const o = document.createElement('option'); o.value=d;
      o.textContent = d + (d===1?'st':d===2?'nd':d===3?'rd':'th');
      mSel.appendChild(o);
    }
  }
}

function schedAdd(){
  _initSchedPicker('');
  const freq   = document.getElementById('sched-freq').value;
  const cron   = _buildCronFromPicker('');
  const ai     = document.getElementById('sched-ai').value;
  const prompt = document.getElementById('sched-prompt').value.trim();
  const cwd    = document.getElementById('sched-cwd').value.trim();
  if(!cron || !prompt){ alert('Please fill in schedule and prompt.'); return; }
  if(freq === 'weekly' && !document.querySelector('input[name="sched-wd"]:checked')){
    alert('Please select at least one day of the week.'); return;
  }
  cmd(`schedule_add:${cron}|${ai}|${cwd}|${prompt}`);
  document.getElementById('sched-prompt').value = '';
  document.getElementById('sched-cwd').value = '';
  document.getElementById('sched-add-details').open = false;
}

// Populate the AI dropdown in schedules modal with loaded integrations
function _schedPopulateAiSelect(){
  const sel = document.getElementById('sched-ai');
  if(!sel) return;
  // Remove existing integration options (keep claude + shell)
  [...sel.options].filter(o => o.dataset.integration).forEach(o => o.remove());
  Object.entries(_integrationKeys||{}).forEach(([key, name]) => {
    const opt = document.createElement('option');
    opt.value = key; opt.textContent = name; opt.dataset.integration = '1';
    sel.insertBefore(opt, sel.options[sel.options.length-1]);
  });
}

// --- History modal ------------------------------------------------------------------------------------------
let _histSessions = [];   // full session list loaded from /history
// AI_COLOR already declared above — reuse it for session cards
const AI_DISPLAY = {claude:'Claude Code', gemini:'Gemini', antigravity:'Antigravity', codex:'Codex', shell:'Shell'};

function _fmtDate(dateStr, ts){
  // dateStr = YYYY-MM-DD; ts = unix timestamp of last message (optional)
  try {
    if(!ts && (!dateStr || !/^\d{4}-\d{2}-\d{2}$/.test(dateStr))) return dateStr || "";
    const d = ts ? new Date(ts * 1000) : new Date(dateStr + 'T12:00:00');
    if(isNaN(d.getTime())) return dateStr || "";
    const now = new Date();
    const diffDays = Math.floor((now - d) / 86400000);
    if(diffDays === 0) return 'Today';
    if(diffDays === 1) return 'Yesterday';
    if(diffDays < 7)  return d.toLocaleDateString(undefined,{weekday:'long'});
    return d.toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'});
  } catch(e){ return dateStr || ""; }
}

function _renderHistoryList(sessions){
  const list = document.getElementById('hist-list');
  if(!sessions.length){
    list.innerHTML = `<div class="modal-empty">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>
      No saved sessions yet.<br>Sessions are saved automatically as you chat.
    </div>`;
    return;
  }
  list.innerHTML = sessions.map(s => {
    const displayName = s.name || _fmtDate(s.date, s.ts);
    const subline     = (s.name ? _fmtDate(s.date, s.ts) + ' · ' : '') +
                        s.count + ' message' + (s.count !== 1 ? 's' : '');
    const accentColor = AI_COLOR[s.ai] || '#4b5563';
    const aiBadge     = s.ai ? `<span class="hcard-ai-badge">${escHtml(AI_DISPLAY[s.ai] || s.ai)}</span>` : '';
    const preview     = s.preview
      ? `<div class="hcard-preview">${escHtml(s.preview)}</div>` : '';
    return `
    <div class="hcard" id="hcard-${s.date}">
      <div class="hcard-accent" style="background:${accentColor}"></div>
      <div class="hcard-body" onclick="toggleHistCard('${s.date}')">
        <div class="hcard-top">
          <div class="hcard-name" id="hcard-name-${s.date}">${escHtml(displayName)}</div>
          ${aiBadge}
        </div>
        <div class="hcard-meta">${escHtml(subline)}</div>
        ${preview}
      </div>
      <button class="hcard-del" title="Delete session" onclick="delSession(event,'${s.date}')">✖</button>
    </div>
    <div class="hcard-actions" id="hcard-act-${s.date}">
      <button class="hact primary" onclick="loadSession('${s.date}')">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
          <circle cx="12" cy="12" r="3"/>
        </svg>View
      </button>
      <button class="hact resume" onclick="resumeSession('${s.date}')">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <polygon points="5 3 19 12 5 21 5 3"/>
        </svg>Resume
      </button>
      <button class="hact" onclick="startRename(event,'${s.date}')">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
          <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
        </svg>Rename
      </button>
    </div>`;
  }).join('');
}

async function openHistory(){
  // Reset search
  const sinp = document.getElementById('hist-search-inp');
  if(sinp) sinp.value = '';

  const list = document.getElementById('hist-list');
  list.innerHTML = '<div class="modal-empty" style="padding:32px 0"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="opacity:.3;animation:spin 1s linear infinite"><path d="M21 12a9 9 0 11-18 0"/></svg></div>';
  document.getElementById('hist-modal').classList.add('open');

  try {
    const res = await fetch('/history');
    _histSessions = await res.json();
    _sessNames = {};
    _histSessions.forEach(s => { if(s.name) _sessNames[s.date] = s.name; });
    _renderHistoryList(_histSessions);
  } catch(e){
    list.innerHTML = '<div class="modal-empty">Failed to load sessions.</div>';
  }
}

function filterHistory(q){
  const lq = q.toLowerCase().trim();
  if(!lq){ _renderHistoryList(_histSessions); return; }
  const filtered = _histSessions.filter(s =>
    (s.name || s.date).toLowerCase().includes(lq) ||
    (s.preview || '').toLowerCase().includes(lq) ||
    (s.ai || '').toLowerCase().includes(lq)
  );
  _renderHistoryList(filtered);
}

function closeHistory(){
  document.getElementById('hist-modal').classList.remove('open');
}

function toggleHistCard(date){
  const act = document.getElementById('hcard-act-' + date);
  const isOpen = act.classList.contains('open');
  document.querySelectorAll('.hcard-actions.open').forEach(el => el.classList.remove('open'));
  if(!isOpen) act.classList.add('open');
}

async function loadSession(date){
  closeHistory();

  // If there's a live session matching this history entry, focus it instead of
  // just viewing read-only history.  This restores the correct AI + CWD.
  const liveMatch = (_sessions || []).find(s => s.history_id === date);
  if(liveMatch && liveMatch.id !== _focusedId){
    cmd('focus:' + liveMatch.id);
    // Brief delay for the focus state to arrive via WS, then show its messages
    await new Promise(r => setTimeout(r, 150));
  }

  const res = await fetch('/history/' + date);
  const data = await res.json();
  const msgs = data.messages || data;
  if(data.cwd) applyCwd(data.cwd);
  _viewingHistory = true;
  _viewedHistoryId = date;
  _activeHistoryId = date;
  const name = _sessNames[date] || _fmtDate(date);
  const banner = document.getElementById('hist-banner');

  if(liveMatch){
    // This is a live session — show "Active" banner with option to return to live input
    banner.className = 'on resume';
    document.getElementById('hist-banner-icon').textContent = '▶';
    document.getElementById('hist-banner-date').textContent = 'Restored: ' + name + ' (' + (liveMatch.ai || 'shell') + ')';
  } else {
    // No live session — read-only view
    banner.className = 'on view';
    document.getElementById('hist-banner-icon').textContent = '📖';
    document.getElementById('hist-banner-date').textContent = 'Viewing: ' + name;
  }
  _clearMessages();
  msgs.forEach(renderMsg);
  if(_sbSearchQ.length >= 2) renderSbHistorySearch(_sbSearchHits, _sbSearchQ);
  else renderSbHistory(_sbHistSessions);
  scroll();
}

function returnToLive(){
  _viewingHistory = false;
  _viewedHistoryId = null;
  const focusedSess = (_sessions || []).find(s => s.id === _focusedId);
  if(focusedSess && focusedSess.cwd) applyCwd(focusedSess.cwd);
  else if(_DEFAULT_CWD) applyCwd(_DEFAULT_CWD);
  _activeHistoryId = focusedSess && focusedSess.history_id ? focusedSess.history_id : null;
  const banner = document.getElementById('hist-banner');
  banner.className = '';
  _clearMessages();
  _liveHistory.forEach(m => {
    if(!m.session_id || m.session_id === _focusedId) renderMsg(m);
  });
  if(_sbSearchQ.length >= 2) renderSbHistorySearch(_sbSearchHits, _sbSearchQ);
  else renderSbHistory(_sbHistSessions);
  scroll();
}

// Resume starts its own session (the AI and folder that conversation used), so it never
// waits behind, or mixes into, whatever the current session is doing.
async function resumeSession(date){
  closeHistory();
  const [data, hist] = await Promise.all([
    fetch('/history/' + date + '/resume').then(r => r.json()),
    fetch('/history/' + date).then(r => r.json()).catch(() => ({})),
  ]);
  _pendingContext = data.context || '';
  _viewingHistory = false;
  _viewedHistoryId = null;
  const focusedSess = (_sessions || []).find(s => s.id === _focusedId);
  const known = k => k && (k === 'claude' || k.startsWith('acp:') || k in (_integrationKeys || {}));
  const ai = known(hist.ai) ? hist.ai : (focusedSess && focusedSess.ai) || 'claude';
  const cwd = hist.cwd || (focusedSess && focusedSess.cwd) || '';
  if(cwd) applyCwd(cwd);
  cmd('new_session:' + ai + (cwd ? '|' + cwd : ''));
  _activeHistoryId = null;
  const name = _sessNames[date] || _fmtDate(date);
  const banner = document.getElementById('hist-banner');
  banner.className = 'on resume';
  document.getElementById('hist-banner-icon').textContent = '▶';
  document.getElementById('hist-banner-date').textContent = 'Context from: ' + name + ' — type your message to continue';
  if(_sbSearchQ.length >= 2) renderSbHistorySearch(_sbSearchHits, _sbSearchQ);
  else renderSbHistory(_sbHistSessions);
  document.getElementById('inp').focus();
}

async function delSession(e, date){
  e.stopPropagation();
  if(!confirm('Delete session "' + (_sessNames[date] || date) + '"?')) return;
  await fetch('/history/' + date, {method: 'DELETE', headers:{'x-csrf-token':_csrfToken()}});
  // Remove from local list and re-render
  _histSessions = _histSessions.filter(s => s.date !== date);
  _renderHistoryList(_histSessions);
}

function startRename(e, date){
  e.stopPropagation();
  const nameEl = document.getElementById('hcard-name-' + date);
  const cur = nameEl.textContent;
  nameEl.innerHTML = `<input class="sess-rename-input" value="${escHtml(cur)}"
    onkeydown="finishRename(event,'${date}')" onblur="finishRename(event,'${date}',true)">`;
  const inp = nameEl.querySelector('input');
  inp.focus(); inp.select();
}

async function finishRename(e, date, blur){
  if(!blur && e.key !== 'Enter' && e.key !== 'Escape') return;
  const nameEl = document.getElementById('hcard-name-' + date);
  if(!nameEl) return;
  const inp = nameEl.querySelector('input');
  if(!inp) return;
  const newName = (e.key === 'Escape') ? '' : inp.value.trim();
  if(newName && newName !== date){
    await fetch('/history/' + date + '/rename', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'x-csrf-token': _csrfToken()},
      body: JSON.stringify({name: newName})
    });
    _sessNames[date] = newName;
    // Update local cache
    const s = _histSessions.find(s => s.date === date);
    if(s) s.name = newName;
  }
  // Re-render just this card's name
  const s = _histSessions.find(s => s.date === date);
  if(nameEl && s){
    nameEl.textContent = s.name || _fmtDate(s.date, s.ts);
  }
}

