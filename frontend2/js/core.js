// The web UI's main script, part 1 of 8 (was complete.js). index.html loads the parts in order.
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
    document.querySelectorAll('.ai-menu-item[data-new-ai]').forEach(btn=>btn.remove());
    const oldStyle = document.getElementById('dynamic-integration-styles');
    if(oldStyle) oldStyle.remove();
    Object.keys(_integrationKeys || {}).forEach(key=>{
      delete AI_LABEL[key];
      delete AI_COLOR[key];
    });
    _integrationKeys = {};
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
      // Only AIs that are set up go in the menu; the rest are in the catalog below.
      if(!ready) continue;
      // Inject "New Session: ..." button before Shell mode
      const btn = document.createElement('button');
      btn.className = 'ai-menu-item';
      btn.dataset.newAi = key;
      const warnIcon = ready ? '' : ' <span title="'+escHtml(setup_hint)+'" style="color:#f59e0b;font-size:11px">⚠️ Not set up</span>';
      btn.innerHTML = `<span class="menu-dot ${key}"></span>${escHtml(name)}${warnIcon}`;
      // Always create session directly with default model — use Switch Model to change
      btn.onclick = () => { cmd('new_session:'+key); closeAiMenu(); };
      shellBtn.parentNode.insertBefore(btn, shellBtn);
    }
    // "Add more AIs" opens the catalog (Settings → AI Integrations).
    const more = document.createElement('button');
    more.className = 'ai-menu-item';
    more.dataset.newAi = '__catalog';
    more.innerHTML = '<span class="menu-dot" style="background:transparent">➕</span>Add more AIs…';
    more.onclick = () => { closeAiMenu(); openAiCatalog(); };
    shellBtn.parentNode.insertBefore(more, shellBtn);
    const styleEl = document.createElement('style');
    styleEl.id = 'dynamic-integration-styles';
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

// --- After an update: the open tab is still the old page --------------------------------------
// The server fingerprints the UI files (<meta name="rapr-build"> and /health). When RAPR
// comes back after an update with a different fingerprint, reload: straight away if
// nobody is looking at this tab, otherwise offer a Reload button so nothing typed is lost.
const _pageBuild = document.querySelector('meta[name="rapr-build"]')?.content || '';
let _newVersionShown = false;
function _checkForNewVersion(){
  if(!_pageBuild || _newVersionShown) return;
  fetch('/health', {cache: 'no-store'}).then(r => r.json()).then(d => {
    if(!d.build || d.build === _pageBuild) return;
    // Hidden tab, or the user clicked Update now (js/updates.js): just reload.
    let updating = false;
    try { updating = !!sessionStorage.getItem('raprUpdating'); } catch(e) {}
    if(document.hidden || updating){ location.reload(); return; }
    _newVersionShown = true;
    const bar = document.createElement('div');
    bar.id = 'update-ready-bar';
    bar.setAttribute('role', 'status');
    bar.innerHTML = '<span>RAPR was updated.</span><button type="button">Reload</button>';
    bar.querySelector('button').onclick = () => location.reload();
    document.body.appendChild(bar);
  }).catch(() => {});
}
document.addEventListener('visibilitychange', () => { if(!document.hidden) _checkForNewVersion(); });

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
    renderHeaderIcons();
    try { initOnboarding(); } catch(e){ console.warn('initOnboarding err', e); }
    try { cmd('schedule_list'); } catch(e){ console.warn('schedule_list err', e); }
    _checkForNewVersion();
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
    if(window.KelvinUI) KelvinUI.onWs(d, _focusedId);
    if(d.type==='message'){
      _liveHistory.push(d);
      if(!_viewingHistory && (!d.session_id || d.session_id === _focusedId)){
        renderMsg(d);
      }
      // Send desktop notification if user is not focused and this is from assistant
      // Hands-free: speak the reply in its AI's voice.
      if(d.role === 'assistant' && window._handsFree && (!d.session_id || d.session_id === _focusedId) && typeof speakReplyHandsFree === 'function'){
        speakReplyHandsFree(d.ai, d.content || '');
      }
      if(d.role === 'assistant' && document.hidden && _notificationsEnabled){
        sendNotification(d);
      }
    }
    else if(d.type==='state') applyState(d);
    else if(d.type==='activity') onActivity(d);
    else if(d.type==='thinking') setThinking(d.active, d.ai, d.session_id);
    else if(d.type==='cwd') applyCwd(d.path);
    else if(d.type==='schedule_list') renderSchedules(d.tasks);
    else if(d.type==='pipeline_update') handlePipelineUpdate(d.pipeline);
    else if(d.type==='pipeline_step_stream') handleStepStream(d.pipeline_id, d.step_id, d.chunk);
    else if(d.type==='approval_request') { showApprovalBanner(d.approval); if(typeof loadNeeds==='function') loadNeeds(); }
    else if(d.type==='approval_resolved') { hideApprovalBanner(); if(typeof loadNeeds==='function') loadNeeds(); }
    else if((d.type==='brief' || d.type==='needs_changed') && typeof loadNeeds==='function') loadNeeds();
    else if(d.type==='agent_run_update' && typeof handleAgentRunUpdate==='function') handleAgentRunUpdate(d.run);
    else if(d.type==='agent_run_stream' && typeof handleAgentRunStream==='function') handleAgentRunStream(d.run_id, d.node_id, d.chunk);
    else if(d.type==='agent_run_waiting_input' && typeof handleAgentRunWaitingInput==='function') handleAgentRunWaitingInput(d);
    else if(d.type==='group_message' && typeof groupOnMessage==='function') groupOnMessage(d);
    else if(d.type==='group_status' && typeof groupOnStatus==='function') groupOnStatus(d);
    else if(d.type==='group_updated' && typeof groupOnUpdated==='function') groupOnUpdated(d);
    else if(d.type==='group_deleted' && typeof groupOnDeleted==='function') groupOnDeleted(d);
    else if(d.type==='group_open' && typeof groupOpenFromServer==='function') groupOpenFromServer(d);
    else if(d.type==='whatsapp_status' && typeof waRender==='function') waRender(d);
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
    new Notification(title, {body: body, icon: '/static/rapr-logo.png'});
    try {
      _notificationAudio.currentTime = 0;
      _notificationAudio.play().catch(() => {});
    } catch(e) {}
  }
}

function toggleNotifications(){
  _notificationsEnabled = !_notificationsEnabled;
  localStorage.setItem('helmNotify', _notificationsEnabled ? '1' : '0');
  renderHeaderIcons();
  if(_notificationsEnabled && Notification.permission === 'default'){
    Notification.requestPermission();
  }
}

function toggleTheme(){
  const curr = document.documentElement.dataset.theme || 'dark';
  const next = curr === 'light' ? 'dark' : 'light';
  document.documentElement.dataset.theme = next;
  localStorage.setItem('helmTheme', next);
  renderHeaderIcons();
}

// Header icons are SVG (not emoji) so they match; the icon shows the current state.
const _HDR_ICONS = {
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>',
  moon: '<path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>',
  bell: '<path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/>',
  bellOff: '<path d="M13.73 21a2 2 0 01-3.46 0M18.63 13A17.89 17.89 0 0118 8M6.26 6.26A5.86 5.86 0 006 8c0 7-3 9-3 9h14M18 8a6 6 0 00-9.33-5M1 1l22 22"/>',
};
function _hdrSvg(name){
  return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + _HDR_ICONS[name] + '</svg>';
}
function renderHeaderIcons(){
  const light = (document.documentElement.dataset.theme || 'dark') === 'light';
  const theme = document.getElementById('theme-toggle-btn');
  if(theme){
    theme.innerHTML = _hdrSvg(light ? 'moon' : 'sun');
    theme.title = light ? 'Switch to dark theme' : 'Switch to light theme';
  }
  const notify = document.getElementById('notify-toggle-btn');
  if(notify){
    notify.hidden = typeof Notification === 'undefined';
    notify.innerHTML = _hdrSvg(_notificationsEnabled ? 'bell' : 'bellOff');
    notify.title = _notificationsEnabled ? 'Desktop notifications are on (click to turn off)' : 'Desktop notifications are off (click to turn on)';
    notify.setAttribute('aria-pressed', _notificationsEnabled ? 'true' : 'false');
  }
}

// One button per side: on wide screens it collapses the sidebar, on narrow ones it opens the drawer.
const _narrowLayout = () => window.matchMedia('(max-width: 900px)').matches;
function toggleSidebarLeft(){ _narrowLayout() ? toggleLeft() : toggleLeftPanel(); }
function toggleSidebarRight(){ _narrowLayout() ? toggleRight() : toggleRightPanel(); }
renderHeaderIcons();

let _onboardingStep = 0;
const _onboardingSteps = [
  {title: 'Welcome to RAPR AI!', content: 'Your personal AI assistant with multi-session support, integrated terminal, and chat history.'},
  {title: '📂 History Panel', content: 'Click the menu icon (☰) on the left to see your past sessions and scheduled tasks.'},
  {title: '⚙️ Settings', content: 'Customize timeouts, model defaults, security settings, and more. Click the gear icon.'},
  {title: '💬 Start Chatting', content: 'Pick an AI from the dropdown, type your message, and press Enter or click Send.'},
  {title: 'All Set! 🚀', content: 'You\'re ready to go! Type a message to begin, or explore the settings.'}
];

function initOnboarding(){
  // Primary guard: localStorage persists across sessions
  if(localStorage.getItem('helmOnboarded') === '1') return;
  // Secondary guard: server-side prefs survive localStorage clears
  fetch('/prefs').then(r=>r.json()).then(prefs=>{
    if(prefs.onboarded){
      // Server says already onboarded — sync localStorage and skip
      localStorage.setItem('helmOnboarded','1');
      return;
    }
    showOnboardingStep(0);
  }).catch(()=>{
    // Network/fetch error — do NOT show onboarding on failure.
    // If the user truly never onboarded, it will show on next successful load.
    // This prevents random re-triggering when /prefs is temporarily unreachable.
  });
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
      document.getElementById('ai-label').textContent = 'Pick an AI';
      picker.className = 'ai-picker';
      if(badge) badge.textContent = '';
    }
    // Sync header context strip (Phase F)
    const hDot  = document.getElementById('hctx-dot');
    const hName = document.getElementById('hctx-name');
    if(hDot && hName){
      if(focusedSess){
        hDot.className = 'hctx-dot ' + (focusedSess.ai || 'shell');
        hName.textContent = focusedSess.name || AI_LABEL[focusedSess.ai] || 'Session';
      } else {
        hDot.className = 'hctx-dot';
        hName.textContent = 'No session';
      }
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
    const hDot2  = document.getElementById('hctx-dot');
    const hName2 = document.getElementById('hctx-name');
    if(hDot2 && hName2){ hDot2.className = 'hctx-dot ' + key; hName2.textContent = AI_LABEL[key] || key; }
    if(s.cwd) applyCwd(s.cwd);
  }
}

function applyCwd(path){
  const el = document.getElementById('cwd-display');
  el.textContent = path;
  el.title = 'Project folder: ' + path + '\nYour AI works inside this folder. Click to type a different path.';
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
    picker.setAttribute('aria-expanded', 'true');
  }
}
function closeAiMenu(){
  document.getElementById('ai-menu').classList.remove('open');
  const picker = document.getElementById('ai-picker');
  picker.classList.remove('menu-open');
  picker.setAttribute('aria-expanded', 'false');
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

