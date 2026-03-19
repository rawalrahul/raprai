const AI_LABEL = {claude:'Claude Code',shell:'Shell'};
let ws = null, activeAi = null, _viewingHistory = false, _liveHistory = [], _pendingContext = '';
let _sessNames = {};
// Multi-session state
let _sessions = [], _focusedId = null, _focusedAi = null;
// Sidebar state
let _sbHistSessions = [], _sbSchedTasks = [], _sessionTimers = {}, _integrationKeys = {};
let _sbTemplates = [];
let _activeHistoryId = null, _viewedHistoryId = null;
const AI_COLOR = {claude:'var(--claude)',gemini:'var(--gemini)',codex:'var(--codex)',shell:'var(--shell)'};

// ─── CSRF helper (reads hq_csrf cookie set by server) ──────────────────────
function _csrfToken(){
  const m = document.cookie.match(/(?:^|;\s*)hq_csrf=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : '';
}

// Notification setup
let _notificationsEnabled = localStorage.getItem('helmNotify') === '1';
const _notificationAudio = new Audio('data:audio/wav;base64,UklGRiYAAABXQVZFZm10IBAAAAABAAEAQB8AAAB9AAACABAAZGF0YQIAAAAAAA==');

// Load integrations from server and inject menu items + CSS vars dynamically
async function loadIntegrations(){
  try {
    const res = await fetch('/integrations');
    if(!res.ok) return;
    const integrations = await res.json();
    if(!integrations.length) return;
    const root = document.documentElement;
    let css = '';
    const shellBtn = document.getElementById('shell-mode-btn');
    for(const {key, name, emoji, color, ready, setup_hint} of integrations){
      // Register CSS variable
      root.style.setProperty('--'+key, color);
      // Parse hex -> r,g,b for rgba()
      const r = parseInt(color.slice(1,3),16);
      const g = parseInt(color.slice(3,5),16);
      const b = parseInt(color.slice(5,7),16);
      css += `.dot.${key}{background:var(--${key})}`;
      css += `.who.${key}{color:var(--${key})}`;
      css += `.ai-picker.active-${key}{border-color:rgba(${r},${g},${b},.35);background:rgba(${r},${g},${b},.05)}`;
      css += `.ai-picker.active-${key} #ai-label{color:var(--${key})}`;
      // Update label map + integration registry
      AI_LABEL[key] = name;
      _integrationKeys[key] = name;
      AI_COLOR[key] = 'var(--' + key + ')';
      // Inject "New Session: ..." button before Shell mode
      const btn = document.createElement('button');
      btn.className = 'ai-menu-item';
      btn.dataset.newAi = key;
      const warnIcon = ready ? '' : ' <span title="'+escHtml(setup_hint)+'" style="color:#f59e0b;font-size:11px">⚠️ Not set up</span>';
      btn.innerHTML = `<span class="menu-dot ${key}"></span>New: ${escHtml(name)}${warnIcon}`;
      // Always create session directly with default model — use Switch Model to change
      btn.onclick = () => { cmd('new_session:'+key); closeAiMenu(); };
      shellBtn.parentNode.insertBefore(btn, shellBtn);
    }
    const styleEl = document.createElement('style');
    styleEl.textContent = css;
    document.head.appendChild(styleEl);
    _sbSchedPopulateAi();
  } catch(e){ console.warn('loadIntegrations failed', e); }
}

// ─────────────────────────────────────────────────────────────────────────────

// Check Claude CLI auth status (OAuth, not API key) and warn if not logged in
async function checkClaudeAuth(){
  try {
    const res = await fetch('/integrations/claude/status');
    if(!res.ok) return;
    const {ready, setup_hint} = await res.json();
    if(!ready && setup_hint){
      const btn = document.getElementById('claude-menu-btn');
      if(btn){
        const warn = document.createElement('span');
        warn.title = setup_hint;
        warn.style.cssText = 'color:#f59e0b;font-size:11px;margin-left:4px';
        warn.textContent = '⚠️ Not set up';
        btn.appendChild(warn);
      }
    }
  } catch(e){ console.warn('checkClaudeAuth failed', e); }
}
function escHtml(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

function connect(){
  const wsProto = location.protocol === 'https:' ? 'wss' : 'ws';
  const url = `${wsProto}://${location.host}/ws`;
  console.log('[RAPR AI] Connecting WS:', url);
  ws = new WebSocket(url);
  ws.onopen = () => {
    console.log('[RAPR AI] WS connected');
    document.getElementById('conn').className = 'ok';
    // Hide connection error banner on successful reconnect
    const banner = document.getElementById('conn-banner');
    if(banner) banner.style.display = 'none';
    // Apply theme from localStorage (or default to dark)
    const savedTheme = localStorage.getItem('helmTheme') || 'dark';
    document.documentElement.dataset.theme = savedTheme;
    const themeBtn = document.getElementById('theme-toggle-btn');
    if(themeBtn) themeBtn.textContent = savedTheme === 'light' ? '☀️' : '🌙';
    // Show notification button if Notification API is supported
    const notifyBtn = document.getElementById('notify-toggle-btn');
    if(notifyBtn && typeof Notification !== 'undefined'){
      notifyBtn.style.display = 'inline-block';
      notifyBtn.textContent = _notificationsEnabled ? '🔔' : '🔕';
    }
    try { initOnboarding(); } catch(e){ console.warn('initOnboarding err', e); }
    try { cmd('schedule_list'); } catch(e){ console.warn('schedule_list err', e); }
    try { loadSbHistory(); } catch(e){ console.warn('loadSbHistory err', e); }
    try { loadSbTemplates(); } catch(e){ console.warn('loadSbTemplates err', e); }
    try { _sbSchedPopulateAi(); } catch(e){ console.warn('_sbSchedPopulateAi err', e); }
    try { _initSchedPicker(''); _initSchedPicker('sb-'); } catch(e){ console.warn('initSchedPicker err', e); }
  };
  ws.onclose = (ev) => {
    console.warn('[RAPR AI] WS closed', ev.code, ev.reason);
    document.getElementById('conn').className = '';
    const banner = document.getElementById('conn-banner');
    const bannerMsg = document.getElementById('conn-banner-msg');
    const bannerIcon = document.getElementById('conn-banner-icon');
    const bannerAction = document.getElementById('conn-banner-action');
    if(banner){
      if(ev.code === 4401 || ev.reason === 'auth_required'){
        // Auth failure — PIN is set but cookie is missing/expired
        banner.className = 'conn-banner';
        bannerIcon.textContent = '🔒';
        bannerMsg.textContent = 'Session expired — please re-login to reconnect';
        bannerAction.style.display = 'inline-block';
        bannerAction.textContent = 'Re-login';
        bannerAction.onclick = () => { location.href = '/login'; };
        banner.style.display = 'flex';
        // Don't auto-retry — user needs to re-login
        return;
      } else if(ev.code === 1006){
        // Abnormal close — server probably down
        banner.className = 'conn-banner warn';
        bannerIcon.textContent = '⚠️';
        bannerMsg.textContent = 'Connection lost — retrying…';
        bannerAction.style.display = 'none';
        banner.style.display = 'flex';
      }
      // Normal close / other — hide banner on reconnect
    }
    setTimeout(connect, 2500);
  };
  ws.onerror = (ev) => { console.error('[RAPR AI] WS error', ev); };
  ws.onmessage = e => {
    const d = JSON.parse(e.data);
    if(d.type==='message'){
      _liveHistory.push(d);
      if(!_viewingHistory && (!d.session_id || d.session_id === _focusedId)){
        renderMsg(d);
      }
      // Send desktop notification if user is not focused and this is from assistant
      if(d.role === 'assistant' && document.hidden && _notificationsEnabled){
        sendNotification(d);
      }
    }
    else if(d.type==='state') applyState(d);
    else if(d.type==='thinking') setThinking(d.active, d.ai, d.session_id);
    else if(d.type==='cwd') applyCwd(d.path);
    else if(d.type==='schedule_list') renderSchedules(d.tasks);
    else if(d.type==='pipeline_update') handlePipelineUpdate(d.pipeline);
    else if(d.type==='pipeline_step_stream') handleStepStream(d.pipeline_id, d.step_id, d.chunk);
    else if(d.type==='approval_request') showApprovalBanner(d.approval);
    else if(d.type==='approval_resolved') hideApprovalBanner();
  };
}

async function sendNotification(msg){
  // Request permission if needed
  if(Notification.permission === 'default'){
    await Notification.requestPermission();
  }
  if(Notification.permission === 'granted'){
    const title = (_sessions.find(s => s.id === msg.session_id)?.name) || msg.ai || 'RAPR AI';
    const body = (msg.content || '').substring(0, 100);
    new Notification(title, {body: body, icon: '/static/logo.png'});
    try {
      _notificationAudio.currentTime = 0;
      _notificationAudio.play().catch(() => {});
    } catch(e) {}
  }
}

function toggleNotifications(){
  _notificationsEnabled = !_notificationsEnabled;
  localStorage.setItem('helmNotify', _notificationsEnabled ? '1' : '0');
  const btn = document.getElementById('notify-toggle-btn');
  if(btn) btn.textContent = _notificationsEnabled ? '🔔' : '🔕';
  if(_notificationsEnabled && Notification.permission === 'default'){
    Notification.requestPermission();
  }
}

function toggleTheme(){
  const curr = document.documentElement.dataset.theme || 'dark';
  const next = curr === 'light' ? 'dark' : 'light';
  document.documentElement.dataset.theme = next;
  localStorage.setItem('helmTheme', next);
  const btn = document.getElementById('theme-toggle-btn');
  if(btn) btn.textContent = next === 'light' ? '☀️' : '🌙';
}

let _onboardingStep = 0;
const _onboardingSteps = [
  {title: 'Welcome to RAPR AI!', content: 'Your personal AI assistant with multi-session support, integrated terminal, and chat history.'},
  {title: '📂 History Panel', content: 'Click the menu icon (☰) on the left to see your past sessions and scheduled tasks.'},
  {title: '⚙️ Settings', content: 'Customize timeouts, model defaults, security settings, and more. Click the gear icon.'},
  {title: '💬 Start Chatting', content: 'Pick an AI from the dropdown, type your message, and press Enter or click Send.'},
  {title: 'All Set! 🚀', content: 'You\'re ready to go! Type a message to begin, or explore the settings.'}
];

function initOnboarding(){
  if(localStorage.getItem('helmOnboarded') === '1') return;
  fetch('/prefs').then(r=>r.json()).then(prefs=>{
    if(prefs.onboarded){ localStorage.setItem('helmOnboarded','1'); return; }
    showOnboardingStep(0);
  }).catch(()=>{ showOnboardingStep(0); });
}

function showOnboardingStep(step){
  _onboardingStep = step;
  if(step >= _onboardingSteps.length){
    closeOnboarding();
    return;
  }
  const data = _onboardingSteps[step];
  document.getElementById('onboarding-title').textContent = data.title;
  document.getElementById('onboarding-content').textContent = data.content;

  const dotsContainer = document.getElementById('onboarding-dots');
  dotsContainer.innerHTML = _onboardingSteps.map((_, i) =>
    `<div class="onboarding-dot${i === step ? ' active' : ''}" onclick="showOnboardingStep(${i})"></div>`
  ).join('');

  const overlay = document.getElementById('onboarding-overlay');
  if(overlay) overlay.classList.add('show');
}

function nextOnboarding(){
  if(_onboardingStep < _onboardingSteps.length - 1){
    showOnboardingStep(_onboardingStep + 1);
  } else {
    closeOnboarding();
  }
}

function skipOnboarding(){
  closeOnboarding();
}

function closeOnboarding(){
  const overlay = document.getElementById('onboarding-overlay');
  if(overlay) overlay.classList.remove('show');
  localStorage.setItem('helmOnboarded', '1');
  fetch('/prefs',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({onboarded:true})}).catch(()=>{});
}

function showHelpTour(){
  localStorage.removeItem('helmOnboarded');
  initOnboarding();
}

function applyState(s){
  // Clear "Connecting to server..." placeholder once we get real state
  const _ph = document.querySelector('#messages .grp.system .bubble');
  if(_ph && _ph.textContent === 'Connecting to server...') _ph.closest('.grp').remove();
  // Multi-session state format: { sessions, focused_id, focused_ai, focused_cwd, focused_status }
  // Also support legacy format: { active_ai, cwd }
  if(s.sessions !== undefined){
    const oldFocusedId = _focusedId;
    _sessions = s.sessions || [];
    _focusedId = s.focused_id || null;
    _focusedAi = s.focused_ai || null;
    activeAi = _focusedAi;
    
    // Re-render center panel if focus changed and not viewing history
    if(!_viewingHistory && oldFocusedId !== _focusedId){
      _clearMessages();
      _liveHistory.forEach(m => {
        if(!m.session_id || m.session_id === _focusedId) renderMsg(m);
      });
      scroll();
    }
    
    // Update sessions list in the dropdown
    const sessContainer = document.getElementById('ai-menu-sessions');
    if(sessContainer){
      if(!_sessions.length){
        sessContainer.innerHTML = '<div style="padding:7px 13px;font-size:12px;color:var(--muted)">No active sessions</div>';
      } else {
        sessContainer.innerHTML = _sessions.map(sess => {
          const isFocused = sess.id === _focusedId;
          const icon = sess.status === 'stopped' ? '🔴' : sess.busy ? '🟡' : '🟢';
          const busyTag = sess.busy
            ? `<span class="sess-busy-dot" title="Working..."></span>`
            : '';
          const folder = sess.cwd ? sess.cwd.split(/[/\\]/).pop() || sess.cwd : '';
          return `<button class="ai-menu-item${isFocused ? ' session-focused' : ''}${sess.busy ? ' session-busy' : ''}"
            onclick="cmd('focus:${sess.id}');closeAiMenu()"
            style="${isFocused ? 'color:var(--text);background:var(--surface2);' : ''}">
            ${icon} ${escHtml(sess.name)}${isFocused ? ' ✓' : ''}${busyTag}
            <span style="margin-left:auto;font-size:10px;color:var(--muted)">${escHtml(folder)}</span>
          </button>`;
        }).join('');
      }
    }
    // Update the focused session display
    const focusedSess = _sessions.find(s => s.id === _focusedId);
    const picker = document.getElementById('ai-picker');
    const badge = document.getElementById('session-badge');
    if(focusedSess){
      const aiKey = focusedSess.ai || 'shell';
      document.getElementById('dot').className = 'dot ' + aiKey;
      // Show session name
      const labelEl = document.getElementById('ai-label');
      labelEl.textContent = focusedSess.emoji + ' ' + focusedSess.name;
      picker.className = 'ai-picker' + (focusedSess.ai ? ' active-' + aiKey : '');
      if(badge){
        const busyCount = _sessions.filter(s => s.busy).length;
        if(_sessions.length > 1 && busyCount > 0)
          badge.textContent = `${busyCount}/${_sessions.length} running · `;
        else if(_sessions.length > 1)
          badge.textContent = `${_sessions.length} sessions · `;
        else
          badge.textContent = '';
      }
    } else {
      document.getElementById('dot').className = 'dot';
      document.getElementById('ai-label').textContent = 'No session';
      picker.className = 'ai-picker';
      if(badge) badge.textContent = '';
    }
    if(s.focused_cwd) applyCwd(s.focused_cwd);
    // After focus may have changed, update the thinking indicator so it always
    // reflects the currently focused session (not whatever was thinking before).
    _refreshThinkingUI();
    // Update right sidebar session dashboard
    updateRightSidebar(_sessions, _focusedId);
    // Update context window bar
    updateContextBar(focusedSess);
    const focusedHistoryId = focusedSess && focusedSess.history_id ? focusedSess.history_id : null;
    _activeHistoryId = _viewingHistory ? _viewedHistoryId : focusedHistoryId;
    
    if(_sbSearchQ.length >= 2) renderSbHistorySearch(_sbSearchHits, _sbSearchQ);
    else if(_sbHistSessions.length) renderSbHistory(_sbHistSessions);
    // Keep left sidebar history in sync when sessions/folders change.
    const newHistSig = (_sessions || [])
      .map(sess => `${sess.id}:${sess.cwd || ''}`)
      .sort()
      .join('|');
    if(newHistSig !== _sbStateSig){
      _sbStateSig = newHistSig;
      if(_sbHistLoading) _sbPendingForceRefresh = true;
      else loadSbHistory(true);
    }
  } else {
    // Legacy format
    activeAi = s.active_ai;
    const key = activeAi || 'shell';
    const picker = document.getElementById('ai-picker');
    document.getElementById('dot').className = 'dot ' + key;
    document.getElementById('ai-label').textContent = AI_LABEL[key] || key;
    picker.className = 'ai-picker' + (activeAi ? ' active-' + activeAi : '');
    if(s.cwd) applyCwd(s.cwd);
  }
}

function applyCwd(path){
  const el = document.getElementById('cwd-display');
  el.textContent = path;
  el.title = 'Working directory: ' + path + '\nClick to change';
}

// --- AI Menu ---------------------------------------------------------------------------------------------------
function toggleAiMenu(e){
  e.stopPropagation();
  const menu = document.getElementById('ai-menu');
  const picker = document.getElementById('ai-picker');
  const isOpen = menu.classList.contains('open');
  if(isOpen){ closeAiMenu(); } else {
    menu.classList.add('open');
    picker.classList.add('menu-open');
  }
}
function closeAiMenu(){
  document.getElementById('ai-menu').classList.remove('open');
  document.getElementById('ai-picker').classList.remove('menu-open');
}
document.addEventListener('click', e => {
  if(!document.getElementById('ai-picker').contains(e.target) &&
     !document.getElementById('ai-menu').contains(e.target)){
    closeAiMenu();
  }
});

// --- Dir bar ---------------------------------------------------------------------------------------------------
function startCwdEdit(){
  const display = document.getElementById('cwd-display');
  const input   = document.getElementById('cwd-input');
  input.value = display.textContent === '—' ? '' : display.textContent;
  display.style.display = 'none';
  input.style.display   = 'block';
  input.focus();
  input.select();
}
function cancelCwdEdit(){
  document.getElementById('cwd-display').style.display = '';
  document.getElementById('cwd-input').style.display   = 'none';
}
function applyCwdEdit(forcedPath){
  const path = forcedPath !== undefined ? forcedPath : document.getElementById('cwd-input').value.trim();
  cancelCwdEdit();
  if(!path || !ws || ws.readyState !== 1) return;
  ws.send(JSON.stringify({type:'command', command:'cwd', path:path}));
}
function cwdKey(e){
  if(e.key === 'Enter')  { e.preventDefault(); applyCwdEdit(); }
  if(e.key === 'Escape') { cancelCwdEdit(); }
}

// --- Browse directory modal ------------------------------------------------------------------------------
let _browsePath = '', _browseTarget = 'cwd'; // 'cwd' or 'sched-cwd' or 'sb-sched-cwd'
async function openBrowse(target){
  _browseTarget = target || 'cwd';
  // Try the native Windows folder-picker first (only works on the server machine)
  try {
    const res = await fetch('/browse/native');
    if(res.ok){
      const data = await res.json();
      if(data.path){
        // User picked a folder — apply it directly, no modal needed
        if(_browseTarget === 'cwd') applyCwdEdit(data.path);
        else document.getElementById(_browseTarget).value = data.path;
        return;
      }
    }
  } catch(e){ /* ignore — fall through to modal */ }

  // Fall back to the in-browser folder browser modal
  if(_browseTarget === 'cwd'){
    _browsePath = document.getElementById('cwd-display').textContent;
  } else {
    _browsePath = document.getElementById(_browseTarget).value || _session_cwd();
  }
  if(_browsePath === '—') _browsePath = '';
  await loadBrowse(_browsePath);
  document.getElementById('browse-modal').classList.add('open');
}
async function loadBrowse(path){
  const res = await fetch('/browse?path=' + encodeURIComponent(path || ''));
  if(!res.ok) return;
  const data = await res.json();
  _browsePath = data.path;
  document.getElementById('browse-crumb').textContent = data.path;
  let html = '';
  if(data.drives && data.drives.length){
    html += '<div class="browse-drives">' +
      data.drives.map(d => `<span class="drive-chip" onclick="loadBrowse('${esc(d)}')">${escHtml(d)}</span>`).join('') +
      '</div>';
  }
  if(data.parent)
    html += `<div class="browse-item up" onclick="loadBrowse('${esc(data.parent)}')">⬆ ..</div>`;
  if(!data.dirs.length)
    html += '<div class="browse-empty">No subfolders in this directory</div>';
  const sep = data.path.includes('\\') ? '\\' : '/';
  data.dirs.forEach(d => {
    const full = data.path.replace(/[/\\]+$/, '') + sep + d;
    html += `<div class="browse-item" onclick="loadBrowse('${esc(full)}')">📂 ${escHtml(d)}</div>`;
  });
  document.getElementById('browse-list').innerHTML = html;
}
function selectBrowsePath(){
  if(_browsePath){
    if(_browseTarget === 'cwd') applyCwdEdit(_browsePath);
    else {
      const el = document.getElementById(_browseTarget);
      if(el) el.value = _browsePath;
    }
  }
  closeBrowseModal();
}
function closeBrowseModal(){ document.getElementById('browse-modal').classList.remove('open'); }
function closeBrowse(e){ if(e.target.id === 'browse-modal') closeBrowseModal(); }
function esc(s){ return s.replace(/\\/g,'\\\\').replace(/'/g,"\\'"); }

// --- Thinking (per-session) ------------------------------------------------------------------------------
// Track which sessions are currently "thinking" so we can show/hide the
// indicator correctly when sessions run in parallel or the user switches focus.
const _thinkingState = {};   // { session_id: { active: bool, ai: string } }

function setThinking(active, ai, session_id){
  // Update per-session tracking
  if(session_id){
    if(active) _thinkingState[session_id] = { active: true, ai: ai };
    else        delete _thinkingState[session_id];
  }
  // Show the indicator only for the focused session
  _refreshThinkingUI();
}

function _refreshThinkingUI(){
  const el      = document.getElementById('thinking');
  const focused = _thinkingState[_focusedId];
  if(focused && focused.active){
    el.className = 'on';
    const k     = focused.ai || _focusedAi || activeAi || '';
    const sess  = _sessions.find(s => s.id === _focusedId);
    const label = sess ? (sess.emoji + ' ' + sess.name) : (AI_LABEL[k] || 'AI');
    document.getElementById('thlabel').textContent = label + '...';
    scroll();
  } else {
    el.className = '';
  }
}

// --- Logo watermark helpers ------------------------------------------------------------------------------
function _clearMessages(){
  // Remove all message groups but keep #chat-logo-bg intact
  const wrap = document.getElementById('messages');
  [...wrap.children].forEach(el => { if(el.id !== 'chat-logo-bg') el.remove(); });
  wrap.classList.remove('has-messages');
}
function _updateLogoState(){
  const wrap = document.getElementById('messages');
  // Count real message groups (exclude the logo bg div itself)
  const msgCount = wrap.querySelectorAll('.grp:not(.system), .grp.user, .grp.assistant').length;
  // Also count system bubbles that aren't the connecting placeholder
  const sysBubbles = [...wrap.querySelectorAll('.grp.system .bubble')]
    .filter(b => b.textContent !== 'Connecting to server...');
  const hasAny = msgCount > 0 || sysBubbles.length > 0;
  wrap.classList.toggle('has-messages', hasAny);
}

// --- Messages ------------------------------------------------------------------------------------------------
/** Strip fenced code blocks (```...```) from AI output so users see only the result */
function stripCodeBlocks(text){
  if(!text) return text;
  // Remove fenced code blocks: ```lang\n...\n``` (with optional language tag)
  let cleaned = text.replace(/```[\s\S]*?```/g, '');
  // Collapse multiple blank lines left behind into a single blank line
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n').trim();
  return cleaned || text; // fallback to original if everything was code
}
function renderMsg(m){
  const wrap = document.getElementById('messages');
  const placeholder = wrap.querySelector('.grp.system .bubble');
  if(placeholder && placeholder.textContent === 'Connecting to server...'){
    placeholder.closest('.grp').remove();
  }
  const grp = document.createElement('div');
  grp.className = 'grp ' + m.role;
  if(m.role !== 'system'){
    const meta = document.createElement('div');
    meta.className = 'meta';
    if(m.role==='user'){
      const via = m.source==='telegram' ? '<span class="via">via Telegram · </span>' : '';
      // Show session label on user messages when multiple sessions exist
      const sessTag = (m.session_name && _sessions.length > 1)
        ? `<span class="via">[${escHtml(m.session_emoji||'')} ${escHtml(m.session_name)}] </span>`
        : '';
      meta.innerHTML = sessTag + via + 'You';
    } else {
      const k = m.ai || '';
      const aiName = AI_LABEL[k] || k || 'AI';
      // Show session name badge if multiple sessions or session is identified
      const sessLabel = (m.session_name && _sessions.length > 1)
        ? ` <span style="font-size:10px;color:var(--muted);font-weight:normal">${escHtml(m.session_emoji||'')} ${escHtml(m.session_name)}</span>`
        : '';
      meta.innerHTML = `<span class="who ${k}">${escHtml(aiName)}</span>${sessLabel}`;
    }
    grp.appendChild(meta);
  }
  const bub = document.createElement('div');
  bub.className = 'bubble';
  bub.textContent = m.role === 'assistant' ? stripCodeBlocks(m.content) : m.content;
  grp.appendChild(bub);
  wrap.appendChild(grp);
  _updateLogoState();
  scroll();
}
function scroll(){ const m = document.getElementById('messages'); m.scrollTop = m.scrollHeight; }

// --- Send ------------------------------------------------------------------------------------------------------
function send(){
  const inp = document.getElementById('inp');
  const txt = inp.value.trim();
  if(!txt) return;
  if(!ws || ws.readyState !== 1){
    const banner = document.getElementById('conn-banner');
    if(banner && banner.style.display === 'none'){
      const bannerMsg = document.getElementById('conn-banner-msg');
      const bannerIcon = document.getElementById('conn-banner-icon');
      if(bannerMsg) bannerMsg.textContent = 'Cannot send — not connected to server';
      if(bannerIcon) bannerIcon.textContent = '⚠️';
      banner.className = 'conn-banner warn';
      banner.style.display = 'flex';
    }
    return;
  }
  let content = txt;
  if(_pendingContext){
    content = _pendingContext + txt;
    _pendingContext = '';
  }
  if(_viewingHistory) returnToLive();
  ws.send(JSON.stringify({type:'message', content:content}));
  inp.value = '';
  inp.style.height = 'auto';
}
// --- File Upload ------------------------------------------------------------------------------------------------
let _uploadedFiles = [];

async function handleFileUpload(inputEl){
  const files = inputEl.files;
  if(!files || files.length === 0) return;
  const btn = document.getElementById('clip-btn');
  btn.classList.add('uploading');
  const names = [];
  for(const file of files){
    const form = new FormData();
    form.append('file', file);
    try {
      const resp = await fetch('/upload', {method:'POST', headers:{'x-csrf-token':_csrfToken()}, body:form});
      const data = await resp.json();
      if(data.filename) names.push(data.filename);
    } catch(err) {
      console.error('Upload failed:', err);
    }
  }
  btn.classList.remove('uploading');
  inputEl.value = '';
  if(names.length > 0){
    _uploadedFiles = _uploadedFiles.concat(names);
    const inp = document.getElementById('inp');
    const tag = names.map(n => `[📎 ${n}]`).join(' ');
    inp.value = (inp.value ? inp.value + ' ' : '') + tag + ' ';
    inp.focus();
    inp.dispatchEvent(new Event('input'));
  }
}

// --- Voice Recording --------------------------------------------------------------------------------------------
let _mediaRec = null;
let _audioChunks = [];
let _isRecording = false;
let _voiceTargetSession = null; // session that was focused when recording started

function toggleVoiceRec(){
  if(_isRecording) stopVoiceRec();
  else startVoiceRec();
}

async function startVoiceRec(){
  const btn = document.getElementById('mic-btn');
  // Capture the focused session at recording start so the message
  // goes to the right session even if user switches during transcription
  _voiceTargetSession = _focusedId || null;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({audio:true});
    _mediaRec = new MediaRecorder(stream, {mimeType: getSupportedMime()});
    _audioChunks = [];
    _mediaRec.ondataavailable = e => { if(e.data.size>0) _audioChunks.push(e.data); };
    _mediaRec.onstop = async () => {
      stream.getTracks().forEach(t=>t.stop());
      if(_audioChunks.length === 0) return;
      const blob = new Blob(_audioChunks, {type: _mediaRec.mimeType});
      await transcribeAndInsert(blob);
    };
    _mediaRec.start();
    _isRecording = true;
    btn.classList.add('recording');
    btn.title = 'Click to stop recording';
  } catch(err) {
    console.error('Microphone access denied:', err);
    alert('Microphone access denied. Please allow microphone in your browser settings.');
  }
}

function stopVoiceRec(){
  const btn = document.getElementById('mic-btn');
  if(_mediaRec && _mediaRec.state !== 'inactive') _mediaRec.stop();
  _isRecording = false;
  btn.classList.remove('recording');
  btn.title = 'Click to record voice message';
}

function getSupportedMime(){
  const types = ['audio/webm;codecs=opus','audio/webm','audio/ogg;codecs=opus','audio/mp4'];
  for(const t of types){ if(MediaRecorder.isTypeSupported(t)) return t; }
  return '';
}

async function transcribeAndInsert(blob){
  const btn = document.getElementById('mic-btn');
  const inp = document.getElementById('inp');
  btn.classList.add('transcribing');
  btn.textContent = '⏳';
  try {
    const form = new FormData();
    form.append('file', blob, 'recording.webm');
    const resp = await fetch('/transcribe', {method:'POST', headers:{'x-csrf-token':_csrfToken()}, body:form});
    const data = await resp.json();
    if(data.error){ alert('Transcription failed: ' + data.error); return; }
    if(data.text){
      // Auto-send the transcribed voice message to the session
      // that was focused when the user started recording
      if(ws && ws.readyState === 1){
        const msg = {type:'message', content: data.text};
        if(_voiceTargetSession) msg.session_id = _voiceTargetSession;
        ws.send(JSON.stringify(msg));
        // Show the sent text in the input briefly then clear
        inp.value = '';
        inp.style.height = 'auto';
      } else {
        // Fallback: put text in input for manual send if WS disconnected
        inp.value = (inp.value ? inp.value + ' ' : '') + data.text;
        inp.dispatchEvent(new Event('input'));
        inp.focus();
      }
      _voiceTargetSession = null;
    }
  } catch(err) {
    console.error('Transcription request failed:', err);
    alert('Could not reach transcription server.');
  } finally {
    btn.textContent = '🎙️';
    btn.classList.remove('transcribing');
  }
}

function cmd(c){
  if(!ws || ws.readyState !== 1){
    // WS not connected — show banner if hidden
    const banner = document.getElementById('conn-banner');
    if(banner && banner.style.display === 'none'){
      const bannerMsg = document.getElementById('conn-banner-msg');
      const bannerIcon = document.getElementById('conn-banner-icon');
      if(bannerMsg) bannerMsg.textContent = 'Not connected to server — commands cannot be sent';
      if(bannerIcon) bannerIcon.textContent = '⚠️';
      banner.className = 'conn-banner warn';
      banner.style.display = 'flex';
    }
    return;
  }
  // If creating a new session, inject CWD into the 2nd segment if it is empty.
  // Format: new_session:ai[|cwd[|model]]
  // When called from model picker: new_session:ollama||mymodel — CWD slot is empty.
  if(c.startsWith('new_session:')){
    const payload = c.slice('new_session:'.length);
    const segs = payload.split('|');    // segs[0]=ai, segs[1]=cwd, segs[2]=model
    if(!segs[1] || !segs[1].trim()){
      const cwd = document.getElementById('cwd-display').textContent;
      if(cwd && cwd !== '—') segs[1] = cwd;
      c = 'new_session:' + segs.join('|');
    }
    if(_viewingHistory) returnToLive();
  }
  ws.send(JSON.stringify({type:'command', command:c}));
}
const inp = document.getElementById('inp');
inp.addEventListener('input', () => {
  inp.style.height = 'auto';
  inp.style.height = Math.min(inp.scrollHeight, 120) + 'px';
});
inp.addEventListener('keydown', e => {
  if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); send(); }
});

// --- Paste / Drop images & files into chat ------------------------------------------------------------------

async function _uploadBlob(blob, filename){
  const form = new FormData();
  form.append('file', blob, filename);
  try {
    const resp = await fetch('/upload', {method:'POST', headers:{'x-csrf-token':_csrfToken()}, body:form});
    const data = await resp.json();
    if(data.filename){
      _uploadedFiles.push(data.filename);
      const tag = `[📎 ${data.filename}]`;
      inp.value = (inp.value ? inp.value + ' ' : '') + tag + ' ';
      inp.focus();
      inp.dispatchEvent(new Event('input'));
    }
  } catch(err){
    console.error('Paste/drop upload failed:', err);
  }
}

async function _handlePastedFiles(files){
  const btn = document.getElementById('clip-btn');
  btn.classList.add('uploading');
  for(const file of files){
    await _uploadBlob(file, file.name || `pasted_${Date.now()}.png`);
  }
  btn.classList.remove('uploading');
}

// Clipboard paste (Ctrl+V / Cmd+V) — images and files
document.addEventListener('paste', async (e) => {
  const items = e.clipboardData?.items;
  if(!items) return;

  const files = [];
  for(const item of items){
    // Skip plain text — let the browser handle normal text paste
    if(item.kind === 'string') continue;
    if(item.kind === 'file'){
      const file = item.getAsFile();
      if(file) files.push(file);
    }
  }
  if(files.length > 0){
    e.preventDefault();
    await _handlePastedFiles(files);
  }
});

// Drag-and-drop onto the input area or chat
const _dropZone = document.querySelector('.input-bar') || document.body;

_dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  e.stopPropagation();
  _dropZone.classList.add('drag-over');
});

_dropZone.addEventListener('dragleave', (e) => {
  e.preventDefault();
  e.stopPropagation();
  _dropZone.classList.remove('drag-over');
});

_dropZone.addEventListener('drop', async (e) => {
  e.preventDefault();
  e.stopPropagation();
  _dropZone.classList.remove('drag-over');

  const files = [];
  if(e.dataTransfer?.files){
    for(const f of e.dataTransfer.files) files.push(f);
  }
  if(files.length > 0){
    await _handlePastedFiles(files);
  }
});

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
const AI_DISPLAY = {claude:'Claude Code', gemini:'Gemini', codex:'Codex', shell:'Shell'};

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

async function resumeSession(date){
  closeHistory();
  const res = await fetch('/history/' + date + '/resume');
  const data = await res.json();
  _pendingContext = data.context || '';
  _viewingHistory = false;
  _viewedHistoryId = null;
  const focusedSess = (_sessions || []).find(s => s.id === _focusedId);
  if(focusedSess && focusedSess.cwd) applyCwd(focusedSess.cwd);
  _activeHistoryId = focusedSess && focusedSess.history_id ? focusedSess.history_id : null;
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

// --- Right Sidebar: Session Dashboard ---------------------------------------------------------------
function _fmtElapsed(ts){
  if(!ts) return '';
  const sec = Math.floor((Date.now() - ts) / 1000);
  if(sec < 60) return sec + 's';
  const m = Math.floor(sec / 60);
  if(m < 60) return m + 'm ' + (sec % 60) + 's';
  return Math.floor(m / 60) + 'h ' + (m % 60) + 'm';
}
function _fmtResetIn(sec){
  const s = Math.max(0, Math.floor(sec || 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return `${h}h ${m}m`;
}
function updateRightSidebar(sessions, focusedId){
  const el = document.getElementById('rs-list');
  const countEl = document.getElementById('rs-count');
  if(!el) return;
  if(!sessions.length){
    el.innerHTML = '<div class="rs-empty">No sessions yet.<br>Create one below.</div>';
    if(countEl) countEl.textContent = '';
    return;
  }
  const busy = sessions.filter(s => s.busy).length;
  if(countEl) countEl.textContent = busy > 0 ? busy + ' running' : sessions.length + ' total';
  el.innerHTML = sessions.map(sess => {
    const f = sess.id === focusedId;
    let dot = 'idle';
    if(sess.status === 'stopped') dot = 'stopped';
    else if(sess.busy) dot = 'busy';
    const aiKey = sess.ai || 'shell';
    const color = AI_COLOR[aiKey] || 'var(--shell)';
    const folder = sess.cwd ? sess.cwd.split(/[/\\]/).pop() || '' : '';
    const timer = sess.busy && sess.task_start ? _fmtElapsed(sess.task_start) : '';
    const u = sess.usage || {};
    const pct = u.pct == null ? null : Math.max(0, Math.min(100, Number(u.pct)));
    const usageText = pct == null
      ? `${(u.used_min || 0).toFixed(1)}m used`
      : `${pct.toFixed(1)}% used`;
    const usageSrc = (u.source || '').endsWith('_cli') ? 'CLI' : 'EST';
    const resetText = _fmtResetIn(u.reset_in_sec || 0);
    const fillWidth = pct == null ? '0%' : `${pct}%`;
    return `<div class="rs-item${f ? ' focused' : ''}" data-sid="${sess.id}" onclick="cmd('focus:${sess.id}')">
      <div class="rs-dot ${dot}"></div>
      <div class="rs-info">
        <div class="rs-name">${escHtml(sess.name)}</div>
        <div class="rs-meta">
          <div class="rs-ai-dot" style="background:${color}"></div>
          <span>${aiKey}</span>
          ${sess.model ? `<span class="rs-model-badge">${escHtml(sess.model)}</span>` : ''}
          ${timer ? `<span class="rs-timer">${timer}</span>` : ''}
          ${folder ? `<span style="opacity:.5">${escHtml(folder)}</span>` : ''}
        </div>
        <div class="rs-usage">
          <div class="rs-usage-line">
            <span>${usageText}</span>
            <span>${usageSrc} · reset ${resetText}</span>
          </div>
          <div class="rs-usage-bar"><div class="rs-usage-fill" style="width:${fillWidth}"></div></div>
        </div>
      </div>
      <div class="rs-actions">
        <button class="rs-act" onclick="event.stopPropagation();cmd('interrupt')" title="Cancel running task">⏸</button>
        <button class="rs-act" onclick="event.stopPropagation();if(confirm('Delete this session?'))cmd('delete_session')" title="Delete session">🗑️</button>
      </div>
    </div>`;
  }).join('');
  // Manage elapsed timers
  Object.keys(_sessionTimers).forEach(id => {
    if(!sessions.find(s => s.id === id && s.busy && s.task_start)){
      clearInterval(_sessionTimers[id]);
      delete _sessionTimers[id];
    }
  });
  sessions.forEach(sess => {
    if(sess.busy && sess.task_start && !_sessionTimers[sess.id]){
      _sessionTimers[sess.id] = setInterval(() => {
        const te = document.querySelector(`.rs-item[data-sid="${sess.id}"] .rs-timer`);
        if(te) te.textContent = _fmtElapsed(sess.task_start);
      }, 1000);
    }
  });
}

// --- Left Sidebar: Tab Switching ---------------------------------------------------------------------
// Legacy switchSbTab kept for any references, now delegates to section toggle
function switchSbTab(tab, btn){
  const section = document.querySelector(`.sb-section[data-section="${tab}"]`);
  if(section && !section.classList.contains('open')){
    toggleSbSection(section.querySelector('.sb-section-header'));
  }
}

function toggleSbSection(headerEl){
  const section = headerEl.closest('.sb-section');
  if(!section) return;
  const isOpen = section.classList.contains('open');
  section.classList.toggle('open');

  // Load data when opening
  if(!isOpen){
    const tab = section.dataset.section;
    if(tab === 'history') loadSbHistory();
    if(tab === 'scheduled') cmd('schedule_list');
    // files section removed
    if(tab === 'usage') loadUsageDashboard();
    if(tab === 'pipelines') loadPipelines();
    if(tab === 'memory') loadMemoryPanel();
  }
}

// --- Left Sidebar: History ------------------------------------------------------------------------------
let _sbHistLoading = false, _sbPendingForceRefresh = false, _sbStateSig = '';
function loadSbHistory(force){
  const mustForce = !!force;
  if(_sbHistLoading) return;
  const el = document.getElementById('sb-panel-history');
  if(!_sbHistSessions.length){
    el.innerHTML = '<div class="sb-empty" style="opacity:.5">Loading...</div>';
  }
  _sbHistLoading = true;
  fetch('/history' + (mustForce ? '?force=1' : '')).then(r => r.json()).then(sessions => {
    _sbHistLoading = false;
    if(_sbPendingForceRefresh && !mustForce){
      _sbPendingForceRefresh = false;
      loadSbHistory(true);
      return;
    }
    if(sessions.length){
      _sbHistSessions = sessions;
      renderSbHistory(sessions);
    } else if(!_sbHistSessions.length){
      // Cache might still be warming — retry once after 2s
      setTimeout(() => {
        fetch('/history' + (mustForce ? '?force=1' : '')).then(r => r.json()).then(s2 => {
          _sbHistSessions = s2;
          renderSbHistory(s2);
        }).catch(() => {});
      }, 2000);
    }
  }).catch(() => {
    _sbHistLoading = false;
    if(!_sbHistSessions.length) el.innerHTML = '<div class="sb-empty">No saved sessions</div>';
  });
}
function renderSbHistory(sessions){
  const el = document.getElementById('sb-panel-history');
  if(!sessions.length){
    el.innerHTML = '<div class="sb-empty">No saved sessions yet</div>';
    return;
  }
  el.innerHTML = sessions.map(s => {
    const dateDisp = _fmtDate(s.date, s.ts);
    const name = s.name || dateDisp || s.date;
    const ai = s.ai || '';
    const color = AI_COLOR[ai] || '';
    const isActive = s.date === _activeHistoryId && _activeHistoryId !== null;
    return `<div class="sb-hcard${isActive ? ' active' : ''}" onclick="loadSession('${s.date}')" title="Click to view session">
      <div style="display:flex;align-items:center;gap:6px">
        <div class="sb-hcard-name" id="sb-hcard-name-${s.date}" style="flex:1">${escHtml(name)}</div>
        ${isActive ? '<span class="sb-active-pill">Active</span>' : ''}
        ${ai ? `<span class="sb-hcard-ai" style="${color ? 'border-color:' + color + ';color:' + color : ''}">${ai}</span>` : ''}
        <button class="sb-rename-btn" title="Rename" onclick="sbStartRename(event,'${s.date}')">&#9998;</button>
        <button class="sb-export-btn" title="Export chat" onclick="sbExportSession(event,'${s.date}')">&#11015;</button>
        <button class="sb-del-btn" title="Delete" onclick="sbDeleteSession(event,'${s.date}')">&#10005;</button>
      </div>
      <div class="sb-hcard-meta">
        <span>${dateDisp}</span>
        <span>${s.count || 0} msg${(s.count||0) !== 1 ? 's' : ''}</span>
      </div>
    </div>`;
  }).join('');
}
function sbStartRename(e, date){
  e.stopPropagation();
  const nameEl = document.getElementById('sb-hcard-name-' + date);
  if(!nameEl) return;
  const cur = nameEl.textContent;
  nameEl.innerHTML = `<input class="sess-rename-input" value="${escHtml(cur)}"
    onkeydown="sbFinishRename(event,'${date}')" onblur="sbFinishRename(event,'${date}',true)"
    onclick="event.stopPropagation()">`;
  const inp = nameEl.querySelector('input');
  inp.focus(); inp.select();
}
async function sbFinishRename(e, date, blur){
  if(!blur && e.key !== 'Enter' && e.key !== 'Escape') return;
  const nameEl = document.getElementById('sb-hcard-name-' + date);
  if(!nameEl) return;
  const inp = nameEl.querySelector('input');
  if(!inp) return;
  const newName = (e.key === 'Escape') ? '' : inp.value.trim();
  if(newName){
    await fetch('/history/' + date + '/rename', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'x-csrf-token': _csrfToken()},
      body: JSON.stringify({name: newName})
    });
    // Update both sidebar and modal caches
    const sb = _sbHistSessions.find(s => s.date === date);
    if(sb) sb.name = newName;
    const hm = _histSessions ? _histSessions.find(s => s.date === date) : null;
    if(hm) hm.name = newName;
  }
  // Re-render name text
  const s = _sbHistSessions.find(s => s.date === date);
  nameEl.textContent = (s && s.name) ? s.name : date;
}
// --- Sidebar history search (full-text via API) ------------------------------------------------
async function sbDeleteSession(e, date){
  e.stopPropagation();
  const label = _sessNames[date] || (_sbHistSessions.find(s => s.date === date)?.name) || date;
  if(!confirm('Delete session "' + label + '"? This cannot be undone.')) return;
  await fetch('/history/' + date, {method: 'DELETE', headers:{'x-csrf-token':_csrfToken()}});
  _sbHistSessions = _sbHistSessions.filter(s => s.date !== date);
  _histSessions = (_histSessions || []).filter(s => s.date !== date);
  delete _sessNames[date];
  _sbSearchHits = (_sbSearchHits || []).filter(s => s.date !== date);
  if(_activeHistoryId === date){
    _activeHistoryId = null;
    _viewedHistoryId = null;
  }
  if(_sbSearchQ.length >= 2) renderSbHistorySearch(_sbSearchHits, _sbSearchQ);
  else renderSbHistory(_sbHistSessions);
  loadSbHistory(true);
}
function sbExportSession(e, date){
  e.stopPropagation();
  window.open('/history/' + date + '/export?format=md', '_blank');
}
let _sbSearchTimer = null;
let _sbSearchQ = '';
let _sbSearchHits = [];

function filterSidebarHistory(q){
  _sbSearchQ = q.trim();
  clearTimeout(_sbSearchTimer);
  const el = document.getElementById('sb-panel-history');

  if(_sbSearchQ.length < 2){
    // Fewer than 2 chars -> restore full list immediately
    _sbSearchHits = [];
    renderSbHistory(_sbHistSessions);
    return;
  }

  // Show a subtle loading state while debouncing
  el.innerHTML = '<div class="sb-empty" style="opacity:.5">Searching...</div>';

  _sbSearchTimer = setTimeout(async () => {
    if(_sbSearchQ.length < 2){ renderSbHistory(_sbHistSessions); return; }
    try {
      const res  = await fetch('/history/search?q=' + encodeURIComponent(_sbSearchQ));
      const hits = await res.json();
      // Only apply if the query hasn't changed while we were fetching
      if(_sbSearchQ !== q.trim()) return;
      _sbSearchHits = hits;
      renderSbHistorySearch(hits, _sbSearchQ);
    } catch(e){
      el.innerHTML = '<div class="sb-empty">Search failed</div>';
    }
  }, 280);
}

function _highlightMatch(text, q){
  if(!q || !text) return escHtml(text || '');
  const idx = text.toLowerCase().indexOf(q.toLowerCase());
  if(idx === -1) return escHtml(text);
  return escHtml(text.slice(0, idx))
    + '<mark class="sb-hl">' + escHtml(text.slice(idx, idx + q.length)) + '</mark>'
    + escHtml(text.slice(idx + q.length));
}

function renderSbHistorySearch(hits, q){
  const el = document.getElementById('sb-panel-history');
  if(!hits.length){
    el.innerHTML = '<div class="sb-empty">No sessions match <em>' + escHtml(q) + '</em></div>';
    return;
  }
  el.innerHTML = hits.map(s => {
    const name  = s.name || s.date;
    const ai    = s.ai || '';
    const color = AI_COLOR[ai] || '';
    const count = s.match_count === 1 ? '1 match' : s.match_count + ' matches';
    const isActive = s.date === _activeHistoryId;
    return `<div class="sb-hcard sb-hcard-search${isActive ? ' active' : ''}" onclick="loadSession('${s.date}')" title="Click to view session">
      <div style="display:flex;align-items:center;gap:6px">
        <div class="sb-hcard-name" id="sb-hcard-name-${s.date}" style="flex:1">${_highlightMatch(name, q)}</div>
        ${isActive ? '<span class="sb-active-pill">Active</span>' : ''}
        ${ai ? `<span class="sb-hcard-ai" style="${color ? 'border-color:' + color + ';color:' + color : ''}">${ai}</span>` : ''}
        <button class="sb-rename-btn" title="Rename" onclick="sbStartRename(event,'${s.date}')">&#9998;</button>
        <button class="sb-del-btn" title="Delete" onclick="sbDeleteSession(event,'${s.date}')">&#10005;</button>
      </div>
      <div class="sb-hcard-snippet">${_highlightMatch(s.snippet, q)}</div>
      <div class="sb-hcard-meta"><span>${s.date}</span><span class="sb-match-count">${count}</span></div>
    </div>`;
  }).join('');
}

// --- Left Sidebar: Scheduled Tasks ------------------------------------------------------------------
function updateSbScheduled(tasks){
  const el = document.getElementById('sb-sched-list');
  if(!el) return;
  if(!tasks.length){
    el.innerHTML = '<div class="sb-empty">No scheduled tasks</div>';
    return;
  }
  el.innerHTML = tasks.map(t => {
    const ico = t.enabled ? '✅' : '⏸';
    const ai = t.ai || 'shell';
    return `<div class="sb-sched-item">
      <div class="sb-sched-top">
        <span>${ico}</span>
        <span class="sb-sched-name">${escHtml(t.name)}</span>
        <span class="sb-hcard-ai">${ai}</span>
      </div>
      <div class="sb-sched-prompt">${escHtml(t.prompt.length > 60 ? t.prompt.slice(0,60) + '...' : t.prompt)}</div>
      <div class="sb-sched-meta"><code style="font-size:10px">${escHtml(t.cron)}</code> · Next: ${escHtml(t.next_run_fmt)}</div>
      <div class="sb-sched-btns">
        <button onclick="cmd('schedule_run:${t.id}')" title="Run now">â–¶ Run</button>
        <button onclick="cmd('schedule_toggle:${t.id}')">${t.enabled ? '⏸' : 'â–¶'}</button>
        <button onclick="if(confirm('Delete?'))cmd('schedule_delete:${t.id}')" style="color:#f87171">✖</button>
      </div>
    </div>`;
  }).join('');
}
function sbSchedAdd(){
  _initSchedPicker('sb-');
  const freq   = document.getElementById('sb-sched-freq').value;
  const cron   = _buildCronFromPicker('sb-');
  const ai     = document.getElementById('sb-sched-ai').value;
  const prompt = document.getElementById('sb-sched-prompt').value.trim();
  const cwd    = document.getElementById('sb-sched-cwd').value.trim();
  if(!cron || !prompt){ alert('Please fill in schedule and prompt.'); return; }
  if(freq === 'weekly' && !document.querySelector('input[name="sb-sched-wd"]:checked')){
    alert('Please select at least one day of the week.'); return;
  }
  cmd(`schedule_add:${cron}|${ai}|${cwd}|${prompt}`);
  document.getElementById('sb-sched-prompt').value = '';
  document.getElementById('sb-sched-cwd').value = '';
}

// Also populate sidebar AI dropdown with integrations
function _sbSchedPopulateAi(){
  const sel = document.getElementById('sb-sched-ai');
  if(!sel) return;
  [...sel.options].filter(o => o.dataset.integration).forEach(o => o.remove());
  Object.entries(_integrationKeys||{}).forEach(([key, name]) => {
    const opt = document.createElement('option');
    opt.value = key; opt.textContent = name; opt.dataset.integration = '1';
    sel.insertBefore(opt, sel.options[sel.options.length - 1]);
  });
}

// --- Session Templates in sidebar ---------------------------------------------------------------
async function loadSbTemplates(){
  try {
    const res = await fetch('/templates');
    _sbTemplates = await res.json();
    renderSbTemplates();
  } catch(e){
    console.warn('loadSbTemplates error:', e);
  }
}

function renderSbTemplates(){
  const el = document.getElementById('sb-templates-list');
  if(!el) return;
  if(!_sbTemplates || !_sbTemplates.length){
    el.innerHTML = '<div class="sb-empty">No templates yet</div>';
    return;
  }
  el.innerHTML = _sbTemplates.map(t => {
    const ai = t.ai || 'shell';
    return `<div class="sb-hcard">
      <div style="display:flex;align-items:center;gap:6px">
        <div class="sb-hcard-name" style="flex:1">${escHtml(t.name)}</div>
        ${t.ai ? `<span class="sb-hcard-ai">${ai}</span>` : ''}
        <button class="sb-rename-btn" title="Launch template" onclick="sbLaunchTemplate(event,'${escHtml(t.name)}')">▶</button>
        <button class="sb-del-btn" title="Delete" onclick="sbDeleteTemplate(event,'${escHtml(t.name)}')">✖</button>
      </div>
      <div class="sb-hcard-meta" style="font-size:10px;color:var(--muted)">
        ${t.cwd ? escHtml(t.cwd.split(/[\\/]/).pop()) : 'default'}
      </div>
    </div>`;
  }).join('');
}

async function sbLaunchTemplate(e, name){
  e.stopPropagation();
  const t = _sbTemplates.find(x => x.name === name);
  if(!t) return;
  const payload = t.ai ? t.ai : '';
  const cwd = t.cwd && t.cwd.trim() ? t.cwd.trim() : '';
  cmd(`new_session:${payload}${cwd ? '|' + cwd : ''}`);
  if(t.prompt && t.prompt.trim()){
    setTimeout(() => {
      const inp = document.getElementById('msg-input');
      if(inp) inp.value = t.prompt.trim();
    }, 500);
  }
}

async function sbDeleteTemplate(e, name){
  e.stopPropagation();
  if(!confirm(`Delete template "${name}"?`)) return;
  try {
    await fetch('/templates/' + encodeURIComponent(name), {method: 'DELETE'});
    await loadSbTemplates();
  } catch(e){ console.warn('sbDeleteTemplate error:', e); }
}

async function sbSaveTemplate(){
  const name = document.getElementById('sb-templ-name').value.trim();
  const ai = document.getElementById('sb-templ-ai').value;
  const cwd = document.getElementById('sb-templ-cwd').value.trim();
  const prompt = document.getElementById('sb-templ-prompt').value.trim();
  if(!name) { alert('Please enter a template name'); return; }
  try {
    const res = await fetch('/templates', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name, ai, cwd, prompt})
    });
    if(!res.ok) { alert('Failed to save template'); return; }
    document.getElementById('sb-templ-name').value = '';
    document.getElementById('sb-templ-ai').value = '';
    document.getElementById('sb-templ-cwd').value = '';
    document.getElementById('sb-templ-prompt').value = '';
    await loadSbTemplates();
  } catch(e){ alert('Error: ' + e); }
}

// --- Mobile sidebar toggles ---------------------------------------------------------------------------
function toggleLeft(){
  const el = document.getElementById('left-sidebar');
  const ov = document.getElementById('sb-overlay');
  const isOpen = el.classList.contains('open');
  closeSidebars();
  if(!isOpen){ el.classList.add('open'); ov.classList.add('open'); }
}
function toggleRight(){
  const el = document.getElementById('right-sidebar');
  const ov = document.getElementById('sb-overlay');
  const isOpen = el.classList.contains('open');
  closeSidebars();
  if(!isOpen){ el.classList.add('open'); ov.classList.add('open'); }
}
function closeSidebars(){
  document.getElementById('left-sidebar').classList.remove('open');
  document.getElementById('right-sidebar').classList.remove('open');
  document.getElementById('sb-overlay').classList.remove('open');
}

// --- Redirect old modal openers to sidebars (on desktop) / toggle (mobile) ------
function openSbSection(name){
  const section = document.querySelector(`.sb-section[data-section="${name}"]`);
  if(section && !section.classList.contains('open')){
    toggleSbSection(section.querySelector('.sb-section-header'));
  }
}
const _origOpenHistory = openHistory;
openHistory = function(){
  if(window.innerWidth <= 900) toggleLeft();
  openSbSection('history');
  loadSbHistory();
};
const _origOpenSchedules = openSchedules;
openSchedules = function(){
  if(window.innerWidth <= 900) toggleLeft();
  openSbSection('scheduled');
  cmd('schedule_list');
};

// --- Settings panel --------------------------------------------------------------------------------------------

function openSettings(){
  const m = document.getElementById('settings-modal');
  m.style.display = 'flex';
  loadSettings();
  loadIntegrationStatus();
  loadCustomAIs();
  loadBudget();
  loadDefaultModels();
  if(typeof loadBackupConfig === 'function') loadBackupConfig();
}

function closeSettings(){
  document.getElementById('settings-modal').style.display = 'none';
  // collapse PIN sub-form
  document.getElementById('st-pin-sub').classList.remove('open');
  document.getElementById('st-pin-new').value = '';
  document.getElementById('st-pin-confirm').value = '';
  document.getElementById('st-pin-err').style.display = 'none';
}

function loadSettings(){
  fetch('/settings').then(r=>r.json()).then(d=>{
    const keys = ['OUTPUT_IDLE_TIMEOUT','OUTPUT_MAX_WAIT','OUTPUT_NO_RESPONSE',
                  'CLAUDE_TIMEOUT','SESSION_DAYS','WEB_PORT','WEB_HOST',
                  'HEARTBEAT_ENABLED','HEARTBEAT_AI',
                  'AI_MAX_RETRIES','AI_AUTO_SWITCH',
                  'PIPELINE_PLANNER_AI','PIPELINE_MAX_PARALLEL','PIPELINE_AUTO_SUGGEST','PIPELINE_CONTEXT_THRESHOLD'];
    keys.forEach(k=>{
      const el = document.getElementById('st-'+k);
      if(el && d[k] !== undefined && d[k] !== '') el.value = d[k];
    });
    // Heartbeat interval: stored as seconds, displayed as hours or minutes
    const hbVal = document.getElementById('st-HEARTBEAT_INTERVAL_VAL');
    const hbUnit = document.getElementById('st-HEARTBEAT_INTERVAL_UNIT');
    if(hbVal && hbUnit && d['HEARTBEAT_INTERVAL']){
      const secs = parseFloat(d['HEARTBEAT_INTERVAL']);
      if(secs < 3600){
        hbVal.value = Math.round(secs / 60);
        hbUnit.value = 'minutes';
      } else {
        hbVal.value = Math.round(secs / 3600);
        hbUnit.value = 'hours';
      }
    }
    const pinStatus = document.getElementById('st-pin-status');
    if(pinStatus) pinStatus.textContent = d.pin_is_set ? 'PIN is set' : 'No PIN configured';

    // Dynamically populate AI dropdowns (heartbeat + pipeline planner)
    _populateAiDropdowns(d);
  }).catch(()=>{});
}

function _populateAiDropdowns(settingsData){
  fetch('/integrations').then(r=>r.json()).catch(()=>[]).then(intList=>{
    // Build full AI list: claude built-in + all integrations
    const allAis = [{key:'claude', name:'Claude Code', emoji:'🤖'}];
    const seen = new Set(['claude']);
    for(const int of (intList||[])){
      if(int.key && !seen.has(int.key)){
        allAis.push({key:int.key, name:int.name||int.key, emoji:int.emoji||'🤖'});
        seen.add(int.key);
      }
    }
    // Populate any <select> that should show all AIs
    const dropdownIds = ['st-HEARTBEAT_AI','st-PIPELINE_PLANNER_AI'];
    for(const id of dropdownIds){
      const sel = document.getElementById(id);
      if(!sel) continue;
      const curVal = sel.value;
      sel.innerHTML = '';
      for(const ai of allAis){
        const opt = document.createElement('option');
        opt.value = ai.key;
        opt.textContent = `${ai.emoji} ${ai.name}`;
        sel.appendChild(opt);
      }
      // Restore saved value
      const savedKey = id.replace('st-','');
      const saved = settingsData[savedKey] || curVal;
      if(saved) sel.value = saved;
    }
  });
}

function saveSettings(){
  const keys = ['OUTPUT_IDLE_TIMEOUT','OUTPUT_MAX_WAIT','OUTPUT_NO_RESPONSE',
                'CLAUDE_TIMEOUT','SESSION_DAYS','WEB_PORT','WEB_HOST',
                'HEARTBEAT_ENABLED','HEARTBEAT_AI',
                'AI_MAX_RETRIES','AI_AUTO_SWITCH',
                'PIPELINE_PLANNER_AI','PIPELINE_MAX_PARALLEL','PIPELINE_AUTO_SUGGEST','PIPELINE_CONTEXT_THRESHOLD'];
  const body = {};
  keys.forEach(k=>{
    const el = document.getElementById('st-'+k);
    if(el && el.value.trim() !== '') body[k] = el.value.trim();
  });
  // Convert heartbeat value + unit → seconds for storage
  const hbVal = document.getElementById('st-HEARTBEAT_INTERVAL_VAL');
  const hbUnit = document.getElementById('st-HEARTBEAT_INTERVAL_UNIT');
  if(hbVal && hbVal.value.trim() !== ''){
    const multiplier = (hbUnit && hbUnit.value === 'minutes') ? 60 : 3600;
    body['HEARTBEAT_INTERVAL'] = String(parseFloat(hbVal.value) * multiplier);
  }
  fetch('/settings',{method:'POST',headers:{'Content-Type':'application/json','x-csrf-token':_csrfToken()},body:JSON.stringify(body)})
    .then(r=>r.json())
    .then(()=>{
      const msg = document.getElementById('st-msg');
      msg.textContent = 'Saved ✓';
      msg.classList.add('show');
      setTimeout(()=>msg.classList.remove('show'),2500);
    }).catch(()=>alert('Failed to save settings'));
}

// --- Default Models per AI -------------------------------------------------------------------------------------

const _CLI_ONLY_AIS = new Set(['claude','gemini','codex']);

function loadDefaultModels(){
  const container = document.getElementById('default-models-container');
  if(!container) return;

  // Fetch both default models and available integrations in parallel
  Promise.all([
    fetch('/settings/default-models').then(r=>r.json()),
    fetch('/integrations').then(r=>r.json()),
    fetch('/integrations/models').then(r=>r.json()).catch(()=>({models:{}})),
  ]).then(([dmData, integrations, modelsData])=>{
    const defaults = dmData.default_models || {};
    const models = modelsData.models || {};

    // Build list of REST-API AIs (exclude CLI-only)
    const restAis = [];
    // Always include ollama
    restAis.push({key:'ollama', name:'Ollama', emoji:'🦙'});
    // Add any integration that isn't CLI-only
    integrations.forEach(intg=>{
      if(!_CLI_ONLY_AIS.has(intg.key) && intg.key !== 'ollama'){
        restAis.push({key:intg.key, name:intg.name, emoji:intg.emoji});
      }
    });

    if(restAis.length === 0){
      container.innerHTML = '<span style="color:var(--muted);font-size:11px">No REST-API AIs configured</span>';
      return;
    }

    let html = '';
    restAis.forEach(ai=>{
      const currentDefault = defaults[ai.key] || '';
      const aiModels = models[ai.key] || [];

      html += `<div class="settings-row" style="margin-bottom:6px">
        <label>${ai.emoji} ${ai.name} default model
          <small>Auto-loaded when starting a new ${ai.name} session</small>
        </label>
        <div style="display:flex;gap:4px;align-items:center;margin-top:4px">
          <input class="settings-input wide dm-model-input" type="text"
                 id="dm-${ai.key}" value="${currentDefault}"
                 placeholder="None (use AI default)" style="flex:1">`;

      // If we have available models, show a dropdown picker
      if(aiModels.length > 0){
        html += `<select class="settings-input dm-model-select" style="width:auto;max-width:180px"
                         onchange="document.getElementById('dm-${ai.key}').value=this.value">
          <option value="">— pick —</option>`;
        aiModels.forEach(m=>{
          const sel = m === currentDefault ? ' selected' : '';
          html += `<option value="${m}"${sel}>${m}</option>`;
        });
        html += `</select>`;
      }

      html += `</div></div>`;
    });

    html += `<div style="margin-top:8px">
      <button class="settings-pin-btn" onclick="saveDefaultModels()" style="padding:5px 14px">
        Save Default Models
      </button>
      <span id="dm-save-msg" style="color:#22c55e;font-size:11px;margin-left:8px;opacity:0;transition:opacity .3s"></span>
    </div>`;

    container.innerHTML = html;
  }).catch(()=>{
    container.innerHTML = '<span style="color:#ef4444;font-size:11px">Failed to load default models</span>';
  });
}

function saveDefaultModels(){
  const inputs = document.querySelectorAll('.dm-model-input');
  const body = {};
  inputs.forEach(el=>{
    const aiKey = el.id.replace('dm-','');
    body[aiKey] = el.value.trim();
  });

  fetch('/settings/default-models',{
    method:'POST',
    headers:{'Content-Type':'application/json','x-csrf-token':_csrfToken()},
    body:JSON.stringify(body),
  }).then(r=>r.json()).then(()=>{
    const msg = document.getElementById('dm-save-msg');
    if(msg){
      msg.textContent = 'Saved ✓';
      msg.style.opacity = '1';
      setTimeout(()=>{msg.style.opacity='0'},2500);
    }
  }).catch(()=>alert('Failed to save default models'));
}

// --- Approval banner (destructive action approvals via UI + Telegram) ---

let _currentApprovalId = null;  // tracks the active approval request shown in the banner

function showApprovalBanner(approval){
  _currentApprovalId = approval.id;
  const banner = document.getElementById('approval-banner');
  const msg = document.getElementById('approval-banner-msg');
  if(!banner||!msg) return;
  msg.textContent = approval.description || 'An action requires your approval';
  banner.style.display = 'flex';
}

function hideApprovalBanner(){
  const banner = document.getElementById('approval-banner');
  if(banner) banner.style.display = 'none';
  _currentApprovalId = null;
}

function resolveApproval(status){
  if(!_currentApprovalId) return;
  const reqId = _currentApprovalId;
  fetch(`/approval/${reqId}`,{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({status})
  }).then(r=>r.json()).then(d=>{
    if(d.ok) hideApprovalBanner();
  }).catch(()=>alert('Failed to resolve approval'));
}

function togglePinSub(){
  document.getElementById('st-pin-sub').classList.toggle('open');
}

// --- AI Integration status in Settings -----------------------------------------------------------------------

const _AI_INT_META = {
  claude: { name:'Claude Code', emoji:'🤖', hint:'Install: npm install -g @anthropic-ai/claude-code' },
  gemini: { name:'Gemini CLI',  emoji:'✨', hint:'Install: npm install -g @google/gemini-cli' },
  codex:  { name:'Codex CLI',   emoji:'🧠', hint:'Install: npm install -g @openai/codex' },
  ollama: { name:'Ollama',      emoji:'🦙', hint:'Download from https://ollama.com/download' },
};

function _renderIntegrationList(data){
  const list = document.getElementById('ai-int-list');
  if(!list) return;
  const items = data._items || Object.entries(_AI_INT_META).map(([key, meta]) => ({
    key, name: meta.name, emoji: meta.emoji,
    found: !!data[key],
    hint: !data[key] ? meta.hint : '',
    models: key === 'ollama' && Array.isArray(data.ollama_models) ? data.ollama_models : [],
  }));
  const rows = items.map(item => {
    const found = item.found;
    const dotCls = found ? 'ok' : 'miss';
    let hint = '';
    if(!found && item.hint) hint = `<span class="ai-int-hint" title="${escHtml(item.hint)}">${escHtml(item.hint)}</span>`;
    else if(found && Array.isArray(item.models) && item.models.length){
      hint = `<span class="ai-int-hint" style="color:var(--dim)">${item.models.join(', ')}</span>`;
    }
    return `<div class="ai-int-row">
      <span class="ai-int-dot ${dotCls}"></span>
      <span class="ai-int-name">${escHtml((item.emoji||'🤖')+' '+item.name)}</span>
      ${hint}
      <span style="font-size:11px;color:${found?'#22c55e':'#6b7280'};white-space:nowrap">
        ${found ? '✓ Detected' : '✗ Not found'}
      </span>
    </div>`;
  });
  list.innerHTML = rows.join('');
}

function loadIntegrationStatus(){
  const list = document.getElementById('ai-int-list');
  if(list) list.innerHTML = '<div style="font-size:12px;color:var(--muted);padding:4px 0">Scanning…</div>';
  fetch('/integrations/rescan').then(r=>r.json()).then(d=>{
    _renderIntegrationList(d);
  }).catch(()=>{
    if(list) list.innerHTML = '<div style="font-size:12px;color:#f87171;padding:4px 0">Failed to scan</div>';
  });
}

function rescanIntegrations(){
  const btn = document.getElementById('ai-int-rescan-btn');
  if(btn){ btn.disabled=true; btn.textContent='Scanning…'; }
  fetch('/integrations/rescan').then(r=>r.json()).then(d=>{
    _renderIntegrationList(d);
    if(btn){ btn.disabled=false; btn.textContent='⟳ Re-scan'; }
    // Also refresh the AI dropdown so newly-detected tools appear
    loadIntegrations();
  }).catch(()=>{
    if(btn){ btn.disabled=false; btn.textContent='⟳ Re-scan'; }
  });
}

function debugCli(name){
  // Show a modal with raw detection diagnostics so we can see exactly why
  // a CLI is not being found (which PATH step fails, what subprocess returns).
  fetch('/integrations/debug/' + name).then(r=>r.json()).then(d=>{
    const cands = Object.entries(d.candidates||{})
      .map(([k,v])=>`  ${v.exists?'✓':'✗'} ${k}: ${v.path}`)
      .join('\n');
    const probe = d.subprocess_probe || {};
    const probeText = probe.timed_out
      ? '  TIMED OUT (process is running — binary exists!)'
      : probe.error
        ? '  ERROR: ' + probe.error
        : `  returncode: ${probe.returncode}\n  stdout: ${probe.stdout||'(empty)'}\n  stderr: ${probe.stderr||'(empty)'}`;
    const msg =
`=== Detection report for: ${name} ===

STEP 1 — shutil.which:
  plain: ${d.which_plain||'null'}
  .cmd:  ${d.which_cmd||'null'}
  .exe:  ${d.which_exe||'null'}

STEP 2 — File-system candidates:
${cands}

STEP 3 — Subprocess probe (shell=True):
${probeText}

FINAL RESULT: ${d._find_cli_result ? '✓ FOUND' : '✗ NOT FOUND'}`;
    // Show in a styled overlay
    let ov = document.getElementById('debug-overlay');
    if(!ov){
      ov = document.createElement('div');
      ov.id = 'debug-overlay';
      ov.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:9999;display:flex;align-items:center;justify-content:center';
      ov.onclick = e => { if(e.target===ov) ov.remove(); };
      document.body.appendChild(ov);
    }
    ov.innerHTML = `<div style="background:#1a1a1a;border:1px solid #3a3a3a;border-radius:12px;padding:20px 24px;max-width:640px;width:92vw;max-height:80vh;overflow-y:auto">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
        <span style="font-size:14px;font-weight:600;color:#e5e7eb">🔍 Claude Detection Diagnostics</span>
        <button onclick="document.getElementById('debug-overlay').remove()" style="background:none;border:none;color:#9ca3af;font-size:18px;cursor:pointer">✖</button>
      </div>
      <pre style="font-size:11px;color:#d1d5db;white-space:pre-wrap;word-break:break-all;line-height:1.6;background:#111;border-radius:8px;padding:12px">${escHtml(msg)}</pre>
      <p style="font-size:11px;color:#6b7280;margin-top:10px">Copy this output and share it if you need help diagnosing the issue.</p>
    </div>`;
  }).catch(err=>{
    alert('Debug fetch failed: ' + err);
  });
}

// --- Plugin Management (Standalone section above Settings) --------------------

// Listen for OAuth callback messages from popup window
window.addEventListener('message', function(e){
  if(e.data && e.data.type === 'plugin-oauth-done') loadInstalledPackages();
});

// NOTE: Plugin/MCP panel functions (togglePlugin, connectPlugin, disconnectPlugin,
// toggleMcpServer, togglePluginAccordion, etc.) are now in packages.js
// as part of the unified RAPR Packages panel.

// --- Context Window Management -----------------------------------------------

function updateContextBar(sess){
  const bar = document.getElementById('context-bar');
  if(!bar) return;
  if(!sess || !sess.context || !sess.ai || sess.ai === 'shell'){
    bar.classList.add('hidden');
    return;
  }
  const ctx = sess.context;
  // Only show bar if there's meaningful context usage (>1%)
  if(ctx.pct < 1){
    bar.classList.add('hidden');
    return;
  }
  bar.classList.remove('hidden');
  const fill = document.getElementById('context-fill');
  const pctEl = document.getElementById('context-pct');
  const compactBtn = document.getElementById('context-compact-btn');
  fill.style.width = Math.min(100, ctx.pct) + '%';
  fill.className = 'context-progress-fill ' + ctx.status;
  pctEl.textContent = ctx.pct.toFixed(0) + '%';
  pctEl.className = 'context-pct ' + ctx.status;
  // Show compact button only when usage is notable (>30%)
  if(compactBtn){
    compactBtn.style.display = ctx.pct > 30 ? '' : 'none';
  }
}

function compactContext(){
  if(!_focusedId) return;
  const btn = document.getElementById('context-compact-btn');
  if(btn){btn.textContent = 'Compacting...';btn.disabled = true;}
  fetch('/context/' + _focusedId + '/compact', {method:'POST'})
    .then(r => r.json())
    .then(d => {
      if(btn){btn.textContent = 'Compact';btn.disabled = false;}
      // The state update from WebSocket will refresh the bar
    })
    .catch(() => {
      if(btn){btn.textContent = 'Compact';btn.disabled = false;}
    });
}

// --- PIN Management ----------------------------------------------------------

function saveNewPin(){
  const np = document.getElementById('st-pin-new').value;
  const cp = document.getElementById('st-pin-confirm').value;
  const errEl = document.getElementById('st-pin-err');
  errEl.style.display = 'none';
  if(!np){errEl.textContent='Enter a new PIN.';errEl.style.display='block';return;}
  if(np !== cp){errEl.textContent='PINs do not match.';errEl.style.display='block';return;}
  fetch('/auth/set-pin',{method:'POST',headers:{'Content-Type':'application/json','x-csrf-token':_csrfToken()},body:JSON.stringify({pin:np})})
    .then(r=>r.json())
    .then(d=>{
      if(d.ok){
        document.getElementById('st-pin-sub').classList.remove('open');
        document.getElementById('st-pin-new').value='';
        document.getElementById('st-pin-confirm').value='';
        document.getElementById('st-pin-status').textContent='PIN is set';
        const msg = document.getElementById('st-msg');
        msg.textContent = 'PIN updated ✓';
        msg.classList.add('show');
        setTimeout(()=>msg.classList.remove('show'),2500);
      } else {
        errEl.textContent = d.detail || 'Failed to set PIN.';
        errEl.style.display = 'block';
      }
    }).catch(()=>{errEl.textContent='Network error.';errEl.style.display='block';});
}

function confirmLogout(){
  if(!confirm('Log out of RAPR AI?')) return;
  fetch('/logout',{method:'POST',headers:{'x-csrf-token':_csrfToken()}}).then(()=>{ window.location.href='/login'; });
}

// --- Generated Files panel ------------------------------------------------------------------------------------
function loadGeneratedFiles(){
  const el = document.getElementById('gf-list');
  el.innerHTML = '<div class="sb-empty" style="opacity:.5">Loading...</div>';
  fetch('/generated-files').then(r=>r.json()).then(files=>{
    if(!files.length){ el.innerHTML='<div class="sb-empty">No generated files yet</div>'; return; }
    el.innerHTML='';
    const extIcons = {'.pdf':'📄','.pptx':'📊','.ppt':'📊','.docx':'📝','.doc':'📝',
      '.xlsx':'📈','.xls':'📈','.csv':'📈','.png':'🖼','.jpg':'🖼','.jpeg':'🖼','.webp':'🖼',
      '.mp4':'🎬','.mov':'🎬','.gif':'🎞','.html':'🌐','.htm':'🌐','.zip':'📦','.tar':'📦',
      '.gz':'📦','.txt':'📃','.md':'📃','.bmp':'🖼'};
    files.forEach(f=>{
      const icon = extIcons[f.ext] || '📎';
      const sizeKb = f.size ? Math.round(f.size/1024) : 0;
      const age = f.age < 60 ? 'just now' : f.age < 3600 ? Math.round(f.age/60)+'m ago' :
                  f.age < 86400 ? Math.round(f.age/3600)+'h ago' : Math.round(f.age/86400)+'d ago';
      const card = document.createElement('div');
      card.className = 'gf-card' + (f.exists ? '' : ' gf-missing');
      card.innerHTML = `<span class="gf-icon">${icon}</span>`+
        `<div class="gf-info">`+
          `<div class="gf-name" title="${f.path}">${f.name}</div>`+
          `<div class="gf-meta">`+
            `<span>${sizeKb} KB</span>`+
            `<span>${age}</span>`+
            (f.ai ? `<span class="gf-ai-badge">${f.ai}</span>` : '')+
            (f.session_name ? `<span>${f.session_name}</span>` : '')+
            (!f.exists ? '<span style="color:#f87171">deleted</span>' : '')+
          `</div>`+
        `</div>`+
        (f.exists ? `<a class="gf-dl" href="/files/${encodeURIComponent(f.name)}" target="_blank" title="Open / download">↓</a>` : '');
      el.appendChild(card);
    });
  }).catch(()=>{ el.innerHTML='<div class="sb-empty">Failed to load files</div>'; });
}

// --- Token Usage Dashboard ------------------------------------------------------------------------------------

function loadUsageDashboard(){
  const el = document.getElementById('usage-dashboard');
  if(!el) return;
  el.innerHTML = '<div class="sb-empty" style="opacity:.5">Loading...</div>';
  fetch('/api/usage').then(r=>r.json()).then(data=>{
    let html = '';
    // Period info
    html += `<div class="usage-period">Reset in: <strong>${data.reset_eta || '?'}</strong></div>`;
    // Per-AI cards
    const ais = data.ais || {};
    const aiKeys = Object.keys(ais);
    if(!aiKeys.length){
      html += '<div class="sb-empty">No usage recorded yet</div>';
    } else {
      aiKeys.forEach(key=>{
        const a = ais[key];
        const pct = a.pct_used != null ? a.pct_used : 0;
        const capText = a.cap_min ? `/ ${a.cap_min}m` : '';
        const src = (a.source||'').endsWith('_cli') ? 'CLI' : 'EST';
        const budgetOk = a.budget && a.budget.allowed !== false;
        const budgetWarn = a.budget && a.budget.warn;
        const barColor = !budgetOk ? '#ef4444' : budgetWarn ? '#f59e0b' : '';
        // Token display: prefer actual counts, fall back to estimate
        const tokSource = a.tokens_source || 'estimate';
        const isActual = tokSource === 'actual';
        const tokBadge = isActual ? 'ACTUAL' : 'EST';
        const tokBadgeClass = isActual ? 'usage-actual-badge' : 'usage-est-badge';
        const tokIn = a.tokens_in || 0;
        const tokOut = a.tokens_out || 0;
        const tokTotal = isActual ? (tokIn + tokOut) : (a.total_tokens || a.est_tokens || 0);
        const tokDetail = isActual
          ? `${tokIn.toLocaleString()} in / ${tokOut.toLocaleString()} out`
          : `~${tokTotal.toLocaleString()} (char÷4)`;
        html += `<div class="usage-ai-card${!budgetOk ? ' usage-blocked' : ''}">
          <div class="usage-ai-header">
            <span class="usage-ai-name">${a.label}</span>
            <span class="usage-ai-src">${src}</span>
          </div>
          <div class="usage-ai-stats">
            <span>${a.used_min.toFixed(1)}m ${capText}</span>
            <span>${a.tasks} task${a.tasks!==1?'s':''}</span>
          </div>
          <div class="usage-token-line">
            <span class="${tokBadgeClass}">${tokBadge}</span>
            <span>${tokTotal.toLocaleString()} tok</span>
            <span class="usage-tok-detail">${tokDetail}</span>
          </div>
          <div class="usage-bar-wrap">
            <div class="usage-bar-fill" style="width:${Math.min(100,pct)}%${barColor?';background:'+barColor:''}"></div>
          </div>
          <div class="usage-pct-line">
            <span>${a.pct_used != null ? a.pct_used.toFixed(1)+'%' : 'No cap'}</span>
            ${!budgetOk ? '<span class="usage-blocked-badge">BLOCKED</span>' : ''}
            ${budgetWarn && budgetOk ? '<span class="usage-warn-badge">WARNING</span>' : ''}
          </div>
        </div>`;
      });
    }
    // Per-session breakdown
    const sess = data.sessions || [];
    if(sess.length){
      html += '<div class="usage-section-title">Per-Session Breakdown</div>';
      sess.forEach(s=>{
        html += `<div class="usage-sess-row">
          <span class="usage-sess-name">${escHtml(s.name)}</span>
          <span>${s.task_count} tasks</span>
          <span>${s.total_min.toFixed(1)}m</span>
        </div>`;
      });
    }
    el.innerHTML = html;
  }).catch(()=>{ el.innerHTML='<div class="sb-empty">Failed to load usage data</div>'; });
}

// --- Budget controls ------------------------------------------------------------------------------------------

function loadBudget(){
  fetch('/api/budget').then(r=>r.json()).then(cfg=>{
    const en = document.getElementById('budget-enabled');
    if(en) en.value = cfg.enabled ? '1' : '0';
    ['claude','gemini','codex','ollama'].forEach(ai=>{
      const inp = document.getElementById('budget-'+ai);
      if(inp && cfg[ai] && cfg[ai].daily_cap_min != null) inp.value = cfg[ai].daily_cap_min;
    });
    const wp = document.getElementById('budget-warn-pct');
    if(wp && cfg.claude && cfg.claude.warn_pct) wp.value = cfg.claude.warn_pct;
  }).catch(()=>{});
}

function saveBudget(){
  const body = {};
  const en = document.getElementById('budget-enabled');
  body.enabled = en && en.value === '1';
  const warnPct = parseFloat((document.getElementById('budget-warn-pct')||{}).value) || 80;
  ['claude','gemini','codex','ollama'].forEach(ai=>{
    const inp = document.getElementById('budget-'+ai);
    const val = inp ? inp.value.trim() : '';
    body[ai] = {
      daily_cap_min: val ? parseFloat(val) : null,
      warn_pct: warnPct,
    };
  });
  fetch('/api/budget',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
    .then(r=>r.json())
    .then(()=>{
      const msg = document.getElementById('budget-msg');
      if(msg){ msg.textContent='Saved ✓'; setTimeout(()=>msg.textContent='',2000); }
    })
    .catch(()=>{
      const msg = document.getElementById('budget-msg');
      if(msg) msg.textContent='Error saving';
    });
}

// --- Pipeline UI --------------------------------------------------------------------------------------------

let _pipelines = {};       // pipeline_id -> pipeline state
let _activePipelineId = null;  // currently viewing

const _PL_STATUS_ICON = {
  pending:'⏳', running:'⚡', completed:'✅', failed:'❌', skipped:'⏭️',
  paused:'⏸️', cancelled:'🚫', planning:'🧠', awaiting_approval:'📋'
};
const _PL_STATUS_COLOR = {
  pending:'var(--muted)', running:'var(--claude)', completed:'#22c55e',
  failed:'#ef4444', skipped:'var(--dim)', paused:'#f59e0b'
};

function handlePipelineUpdate(pl){
  if(!pl || !pl.id) return;
  _pipelines[pl.id] = pl;
  // If this is awaiting_approval, show the approval modal
  if(pl.status === 'awaiting_approval'){
    _activePipelineId = pl.id;
    showPipelineApprovalModal(pl);
  }
  // Update the inline graph if it exists in chat
  updatePipelineGraph(pl);
  // Update sidebar list if visible
  const panel = document.getElementById('sb-panel-pipelines');
  if(panel && panel.classList.contains('active')) loadPipelines();
}

function loadPipelines(){
  const el = document.getElementById('pipelines-list');
  if(!el) return;
  fetch('/api/pipelines').then(r=>r.json()).then(data=>{
    const pls = data.pipelines || [];
    if(!pls.length){
      el.innerHTML = '<div class="sb-empty">No pipelines yet.</div>';
      return;
    }
    // Templates link
    let tplHtml = '<div class="pl-sb-tpl-link" onclick="loadTemplates()">📋 Saved Templates</div>';
    el.innerHTML = tplHtml + '<div id="pipeline-templates-list"></div>' + pls.map(p=>{
      const icon = _PL_STATUS_ICON[p.status] || '❓';
      const prog = p.progress || {};
      const progText = prog.total ? `${prog.completed||0}/${prog.total} done` : '';
      return `<div class="pl-sb-card" onclick="viewPipeline('${p.id}')">
        <div class="pl-sb-header">
          <span>${icon} ${escHtml(p.original_prompt.slice(0,60))}${p.original_prompt.length>60?'…':''}</span>
        </div>
        <div class="pl-sb-meta">
          <span class="pl-sb-status">${p.status}</span>
          <span>${progText}</span>
          <span>${p.planner_ai}</span>
        </div>
      </div>`;
    }).join('');
  }).catch(()=>{
    el.innerHTML = '<div class="sb-empty">Failed to load pipelines</div>';
  });
}

function sbPipelineCreate(){
  const ta = document.getElementById('sb-pipeline-prompt');
  const prompt = (ta.value || '').trim();
  if(!prompt){ ta.focus(); return; }
  const btn = ta.nextElementSibling;
  btn.disabled = true; btn.textContent = 'Planning…';
  fetch('/api/pipeline/plan', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({prompt})
  }).then(r=>r.json()).then(data=>{
    btn.disabled = false; btn.textContent = 'Create Pipeline';
    if(data.error){ alert(data.error); return; }
    ta.value = '';
    ta.closest('details').removeAttribute('open');
    loadPipelines();
  }).catch(()=>{
    btn.disabled = false; btn.textContent = 'Create Pipeline';
    alert('Failed to create pipeline');
  });
}

function viewPipeline(plId){
  fetch('/api/pipeline/'+plId).then(r=>r.json()).then(data=>{
    if(data.pipeline){
      _pipelines[plId] = data.pipeline;
      _activePipelineId = plId;
      if(data.pipeline.status === 'awaiting_approval'){
        showPipelineApprovalModal(data.pipeline);
      } else {
        injectPipelineGraph(data.pipeline);
      }
    }
  });
}

// --- Pipeline Approval Modal ---

function showPipelineApprovalModal(pl){
  const modal = document.getElementById('pipeline-modal');
  const promptEl = document.getElementById('pipeline-modal-prompt');
  const stepsEl = document.getElementById('pipeline-modal-steps');
  if(!modal || !stepsEl) return;

  // Show prompt + cost estimate
  let promptText = pl.original_prompt || '';
  if(pl.estimated_total_cost > 0){
    promptText += `\n\n💰 Estimated total cost: $${pl.estimated_total_cost.toFixed(4)}`;
  }
  promptEl.textContent = promptText;

  const aiOptions = ['claude','gemini','codex','ollama'].map(a =>
    `<option value="${a}">${a}</option>`
  ).join('');

  stepsEl.innerHTML = pl.steps.map((s,i) => {
    const costHint = s.estimated_cost_usd > 0 ? `<span class="pl-step-cost">~$${s.estimated_cost_usd.toFixed(4)}</span>` : '';
    const condHint = s.condition ? `<span class="pl-step-cond">⚡ Conditional</span>` : '';
    const fbHint = s.fallback_ais && s.fallback_ais.length
      ? `<span class="pl-step-fb">↩ Fallback: ${s.fallback_ais.join(', ')}</span>` : '';
    return `
    <div class="pl-approval-step" data-step-id="${s.id}">
      <div class="pl-approval-step-header">
        <span class="pl-step-num">${i+1}</span>
        <input class="pl-step-title-input" value="${escHtml(s.title)}" data-field="title">
        <select class="pl-step-ai-select" data-field="assigned_ai">
          ${aiOptions.replace('value="'+s.assigned_ai+'"','value="'+s.assigned_ai+'" selected')}
        </select>
        ${costHint}
      </div>
      <textarea class="pl-step-desc-input" rows="2" data-field="description">${escHtml(s.description)}</textarea>
      <div class="pl-step-deps">
        ${s.depends_on.length ? 'Depends on: '+s.depends_on.join(', ') : 'No dependencies (can run in parallel)'}
        ${condHint} ${fbHint}
      </div>
    </div>`;
  }).join('');

  modal.style.display = 'flex';
}

function closePipelineModal(){
  document.getElementById('pipeline-modal').style.display = 'none';
}

function approvePipeline(){
  if(!_activePipelineId) return;
  const stepsEl = document.getElementById('pipeline-modal-steps');
  const stepEdits = [];
  stepsEl.querySelectorAll('.pl-approval-step').forEach(el => {
    const sid = el.dataset.stepId;
    const title = el.querySelector('[data-field="title"]').value;
    const ai = el.querySelector('[data-field="assigned_ai"]').value;
    const desc = el.querySelector('[data-field="description"]').value;
    stepEdits.push({id: sid, title, assigned_ai: ai, description: desc});
  });

  fetch('/api/pipeline/'+_activePipelineId+'/approve', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({steps: stepEdits})
  }).then(r=>r.json()).then(()=>{
    closePipelineModal();
  }).catch(err => console.error('Pipeline approve failed:', err));
}

// --- Live Pipeline Graph (inline in chat) ---

function injectPipelineGraph(pl){
  // Find or create the pipeline graph element in #messages
  let graphEl = document.getElementById('pl-graph-'+pl.id);
  if(!graphEl){
    const wrap = document.getElementById('messages');
    graphEl = document.createElement('div');
    graphEl.id = 'pl-graph-'+pl.id;
    graphEl.className = 'pl-graph-container';
    wrap.appendChild(graphEl);
    scroll();
  }
  renderPipelineGraphContent(graphEl, pl);
}

function updatePipelineGraph(pl){
  const graphEl = document.getElementById('pl-graph-'+pl.id);
  if(graphEl) renderPipelineGraphContent(graphEl, pl);
}

function renderPipelineGraphContent(el, pl){
  const prog = pl.progress || {};
  const statusIcon = _PL_STATUS_ICON[pl.status] || '';
  const prompt = (pl.original_prompt||'').slice(0,80);

  // Determine graph layers (topological sort for visual layout)
  const layers = computeGraphLayers(pl.steps);

  let layersHtml = layers.map(layer =>
    `<div class="pl-graph-layer">` +
    layer.map(s => {
      const color = _PL_STATUS_COLOR[s.status] || 'var(--muted)';
      const icon = _PL_STATUS_ICON[s.status] || '❓';
      const aiColor = `var(--${s.assigned_ai||'shell'})`;
      const elapsed = s.elapsed_seconds ? `${s.elapsed_seconds.toFixed(1)}s` : '';
      const costTag = s.actual_cost_usd > 0 ? ` · $${s.actual_cost_usd.toFixed(4)}`
                   : s.estimated_cost_usd > 0 ? ` · ~$${s.estimated_cost_usd.toFixed(4)}` : '';
      const condTag = s.condition ? '<span class="pl-cond-badge">⚡</span>' : '';
      const fbTag = s.fallback_ais && s.fallback_ais.length ? `<span class="pl-fb-badge">↩${s.fallback_index||0}/${s.fallback_ais.length}</span>` : '';
      const streamHtml = s.status === 'running' && s.stream_buffer
        ? `<pre class="pl-stream-live" id="pl-stream-${pl.id}-${s.id}">${escHtml(s.stream_buffer.slice(-200))}</pre>` : '';
      return `<div class="pl-graph-node" data-status="${s.status}" style="border-color:${color}"
                   onclick="toggleStepDetail('${pl.id}','${s.id}')">
        <div class="pl-node-icon">${icon} ${condTag}${fbTag}</div>
        <div class="pl-node-title">${escHtml(s.title)}</div>
        <div class="pl-node-ai" style="color:${aiColor}">${s.assigned_ai}${elapsed?' · '+elapsed:''}${costTag}</div>
        ${streamHtml}
        <div class="pl-node-detail" id="pl-detail-${pl.id}-${s.id}" style="display:none"></div>
      </div>`;
    }).join('<div class="pl-graph-arrow">→</div>') +
    `</div>`
  ).join('');

  // Controls bar
  let controls = '';
  if(pl.status === 'running'){
    controls = `<button class="pl-ctrl-btn" onclick="plAction('${pl.id}','pause')">⏸ Pause</button>
                <button class="pl-ctrl-btn pl-danger" onclick="plAction('${pl.id}','cancel')">✖ Cancel</button>`;
  } else if(pl.status === 'paused'){
    controls = `<button class="pl-ctrl-btn" onclick="plAction('${pl.id}','resume')">▶ Resume</button>
                <button class="pl-ctrl-btn pl-danger" onclick="plAction('${pl.id}','cancel')">✖ Cancel</button>`;
  } else if(pl.status === 'failed'){
    controls = `<button class="pl-ctrl-btn" onclick="plAction('${pl.id}','resume')">🔄 Retry Failed</button>`;
  } else if(pl.status === 'completed'){
    controls = `<button class="pl-ctrl-btn" onclick="saveAsTemplate('${pl.id}')">💾 Save as Template</button>`;
  }

  const costStr = pl.actual_total_cost > 0 ? ` · $${pl.actual_total_cost.toFixed(4)}`
                : pl.estimated_total_cost > 0 ? ` · ~$${pl.estimated_total_cost.toFixed(4)}` : '';

  el.innerHTML = `
    <div class="pl-graph-header">
      <span>${statusIcon} Pipeline: ${escHtml(prompt)}${prompt.length<(pl.original_prompt||'').length?'…':''}</span>
      <span class="pl-graph-progress">${prog.completed||0}/${prog.total||0} steps${costStr}</span>
    </div>
    <div class="pl-graph-body">${layersHtml}</div>
    ${controls ? `<div class="pl-graph-controls">${controls}</div>` : ''}
  `;
}

function computeGraphLayers(steps){
  // Simple topological layering: steps with no deps go in layer 0, etc.
  if(!steps || !steps.length) return [];
  const stepMap = {};
  steps.forEach(s => stepMap[s.id] = s);
  const layers = [];
  const placed = new Set();

  for(let i = 0; i < steps.length + 1; i++){
    const layer = [];
    steps.forEach(s => {
      if(placed.has(s.id)) return;
      const deps = (s.depends_on||[]).filter(d => !placed.has(d));
      if(deps.length === 0) layer.push(s);
    });
    if(!layer.length) break;
    layer.forEach(s => placed.add(s.id));
    layers.push(layer);
  }
  // Add any remaining (circular dep edge case)
  const remaining = steps.filter(s => !placed.has(s.id));
  if(remaining.length) layers.push(remaining);
  return layers;
}

function toggleStepDetail(plId, stepId){
  const el = document.getElementById('pl-detail-'+plId+'-'+stepId);
  if(!el) return;
  if(el.style.display !== 'none'){
    el.style.display = 'none';
    return;
  }
  // Fetch full step detail
  fetch(`/api/pipeline/${plId}/step/${stepId}`).then(r=>r.json()).then(data=>{
    const s = data.step;
    if(!s) return;
    let html = `<div class="pl-detail-desc">${escHtml(s.description).slice(0,300)}</div>`;
    if(s.condition){
      html += `<div class="pl-detail-cond">⚡ Condition: if ${s.condition.check}.${s.condition.field} ${s.condition.equals?'==':'contains'} "${escHtml(s.condition.equals||s.condition.contains||'')}"</div>`;
    }
    if(s.fallback_ais && s.fallback_ais.length){
      html += `<div class="pl-detail-fb">↩ Fallback AIs: ${s.fallback_ais.join(' → ')} (used ${s.fallback_index||0})</div>`;
    }
    if(s.output){
      html += `<div class="pl-detail-output">${escHtml(s.output).slice(0,500)}${s.output.length>500?'…':''}</div>`;
    }
    if(s.stream_buffer){
      html += `<pre class="pl-detail-stream">Live: ${escHtml(s.stream_buffer.slice(-300))}</pre>`;
    }
    if(s.error){
      html += `<div class="pl-detail-error">Error: ${escHtml(s.error)}</div>`;
    }
    // Artifact files (structured)
    if(s.artifact_files && s.artifact_files.length){
      html += `<div class="pl-detail-files">📁 Files:<br>${s.artifact_files.map(f =>
        `  ${f.name} (${(f.size/1024).toFixed(1)}KB, .${f.type})`
      ).join('<br>')}</div>`;
    } else if(s.artifacts && s.artifacts.length){
      html += `<div class="pl-detail-files">📁 ${s.artifacts.join(', ')}</div>`;
    }
    // Cost
    if(s.actual_cost_usd > 0){
      html += `<div class="pl-detail-cost">💰 Actual: $${s.actual_cost_usd.toFixed(4)} (${s.actual_tokens} tokens)</div>`;
    } else if(s.estimated_cost_usd > 0){
      html += `<div class="pl-detail-cost">💰 Est: ~$${s.estimated_cost_usd.toFixed(4)} (~${s.estimated_tokens} tokens)</div>`;
    }
    // Action buttons
    if(s.status === 'failed'){
      html += `<div class="pl-detail-actions">
        <button class="pl-ctrl-btn" onclick="plStepAction('${plId}','${stepId}','retry')">🔄 Retry</button>
        <button class="pl-ctrl-btn" onclick="plStepAction('${plId}','${stepId}','skip')">⏭️ Skip</button>
      </div>`;
    }
    el.innerHTML = html;
    el.style.display = 'block';
  });
}

// --- Step-level streaming handler ---
function handleStepStream(plId, stepId, chunk){
  const el = document.getElementById('pl-stream-'+plId+'-'+stepId);
  if(el){
    el.textContent = (el.textContent + chunk).slice(-500);
    el.scrollTop = el.scrollHeight;
  }
}

// --- Pipeline Templates ---
function loadTemplates(){
  fetch('/api/pipeline/templates').then(r=>r.json()).then(data=>{
    const tpls = data.templates || [];
    const el = document.getElementById('pipeline-templates-list');
    if(!el) return;
    if(!tpls.length){
      el.innerHTML = '<div class="pl-tpl-empty">No saved templates yet. Complete a pipeline to save it as a template.</div>';
      return;
    }
    el.innerHTML = tpls.map(t => `
      <div class="pl-tpl-card">
        <div class="pl-tpl-name">${escHtml(t.name)}</div>
        <div class="pl-tpl-meta">${t.step_count} steps · ${t.planner_ai} · used ${t.use_count}x</div>
        <div class="pl-tpl-actions">
          <button class="pl-ctrl-btn" onclick="useTemplate('${t.id}')">▶ Use</button>
          <button class="pl-ctrl-btn pl-danger" onclick="deleteTemplate('${t.id}')">🗑️</button>
        </div>
      </div>
    `).join('');
  });
}

function saveAsTemplate(plId){
  const name = prompt('Template name:');
  if(!name) return;
  fetch(`/api/pipeline/${plId}/save-template`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({name})
  }).then(r=>r.json()).then(data=>{
    if(data.ok) alert('Template saved: ' + data.template.name);
    loadTemplates();
  });
}

function useTemplate(tplId){
  const userPrompt = prompt('What should this pipeline do? (or leave blank for default):') || '';
  fetch('/api/pipeline/from-template', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({template_id: tplId, prompt: userPrompt})
  }).then(r=>r.json()).then(data=>{
    if(data.pipeline){
      _pipelines[data.pipeline.id] = data.pipeline;
      _activePipelineId = data.pipeline.id;
      showPipelineApprovalModal(data.pipeline);
    }
  });
}

function deleteTemplate(tplId){
  if(!confirm('Delete this template?')) return;
  fetch(`/api/pipeline/template/${tplId}`, {method:'DELETE'}).then(()=> loadTemplates());
}

function plAction(plId, action){
  fetch(`/api/pipeline/${plId}/${action}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'})
    .then(r=>r.json()).catch(err => console.error('Pipeline action failed:', err));
}

function plStepAction(plId, stepId, action){
  fetch(`/api/pipeline/${plId}/step/${stepId}/${action}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'})
    .then(r=>r.json()).catch(err => console.error('Step action failed:', err));
}

// --- Diagnostics export ---------------------------------------------------------------------------------------
function exportDiagnostics(){
  const a = document.createElement('a');
  a.href = '/diagnostics';
  a.download = 'helm_diagnostics.json';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

// --- Panel toggle & resize -------------------------------------------------------------------------------------

// Restore persisted panel widths & collapsed state
(function restorePanelState(){
  const lw = localStorage.getItem('helmLeftW');
  const rw = localStorage.getItem('helmRightW');
  const lc = localStorage.getItem('helmLeftCollapsed') === '1';
  const rc = localStorage.getItem('helmRightCollapsed') === '1';
  const left  = document.getElementById('left-sidebar');
  const right = document.getElementById('right-sidebar');
  if(lw && !lc) left.style.width = lw + 'px';
  if(rw && !rc) right.style.width = rw + 'px';
  if(lc){ left.classList.add('collapsed'); updateToggleBtn('left', true); }
  if(rc){ right.classList.add('collapsed'); updateToggleBtn('right', true); }
})();

function updateToggleBtn(side, collapsed){
  if(side === 'left'){
    const btn = document.getElementById('toggle-left-panel');
    if(btn) btn.textContent = collapsed ? '▸' : '☰';
    if(btn) btn.title = collapsed ? 'Show left sidebar' : 'Hide left sidebar';
  } else {
    const btn = document.getElementById('toggle-right-panel');
    if(btn) btn.textContent = collapsed ? '◂' : '▸';
    if(btn) btn.title = collapsed ? 'Show sessions panel' : 'Hide sessions panel';
  }
}

function toggleLeftPanel(){
  const el = document.getElementById('left-sidebar');
  const collapsed = el.classList.toggle('collapsed');
  localStorage.setItem('helmLeftCollapsed', collapsed ? '1' : '0');
  updateToggleBtn('left', collapsed);
  // Restore width if un-collapsing
  if(!collapsed){
    const saved = localStorage.getItem('helmLeftW');
    if(saved) el.style.width = saved + 'px';
  }
}

function toggleRightPanel(){
  const el = document.getElementById('right-sidebar');
  const collapsed = el.classList.toggle('collapsed');
  localStorage.setItem('helmRightCollapsed', collapsed ? '1' : '0');
  updateToggleBtn('right', collapsed);
  if(!collapsed){
    const saved = localStorage.getItem('helmRightW');
    if(saved) el.style.width = saved + 'px';
  }
}

// --- Resize drag logic ---
(function initResizeHandles(){
  const leftHandle  = document.getElementById('resize-left');
  const rightHandle = document.getElementById('resize-right');
  if(!leftHandle && !rightHandle) return;

  let dragging = null; // 'left' or 'right'
  let startX = 0, startW = 0;

  function onMouseDown(side, e){
    e.preventDefault();
    const panel = document.getElementById(side === 'left' ? 'left-sidebar' : 'right-sidebar');
    if(panel.classList.contains('collapsed')) return;
    dragging = side;
    startX = e.clientX;
    startW = panel.getBoundingClientRect().width;
    e.target.classList.add('active');
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }

  function onMouseMove(e){
    if(!dragging) return;
    const panel = document.getElementById(dragging === 'left' ? 'left-sidebar' : 'right-sidebar');
    let delta = e.clientX - startX;
    if(dragging === 'right') delta = -delta; // right sidebar grows leftward
    let newW = Math.max(140, Math.min(600, startW + delta));
    panel.style.width = newW + 'px';
  }

  function onMouseUp(){
    if(!dragging) return;
    const panel = document.getElementById(dragging === 'left' ? 'left-sidebar' : 'right-sidebar');
    localStorage.setItem(dragging === 'left' ? 'helmLeftW' : 'helmRightW',
                         Math.round(panel.getBoundingClientRect().width));
    document.querySelectorAll('.resize-handle').forEach(h => h.classList.remove('active'));
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    dragging = null;
  }

  if(leftHandle)  leftHandle.addEventListener('mousedown',  e => onMouseDown('left', e));
  if(rightHandle) rightHandle.addEventListener('mousedown', e => onMouseDown('right', e));
  document.addEventListener('mousemove', onMouseMove);
  document.addEventListener('mouseup', onMouseUp);
})();

// --- Init ------------------------------------------------------------------------------------------------------
connect();
// Load integrations immediately (shows AI buttons)
loadIntegrations();
checkClaudeAuth();
