// The web UI's main script, part 5 of 8. index.html loads the parts in order.
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
        <button class="rs-act" onclick="event.stopPropagation();cmd('interrupt:${sess.id}')" title="Cancel running task">⏸</button>
        <button class="rs-act" onclick="event.stopPropagation();if(confirm('Delete this session?'))cmd('delete_session:${sess.id}')" title="Delete session">🗑️</button>
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
  // Rail layout shows one section at a time (js/sidebar.js); Stacked layout toggles in place.
  if(window.Sidebar && Sidebar.isRail()){ Sidebar.activate(section.dataset.section); return; }
  const isOpen = section.classList.contains('open');
  section.classList.toggle('open');
  headerEl.setAttribute('aria-expanded', isOpen ? 'false' : 'true');
  if(!isOpen){
    sbLoadSection(section.dataset.section);
    if(window.RaprUI) RaprUI.setSidebar({active: section.dataset.section});
  }
}

// Load a sidebar section's data when it is shown
function sbLoadSection(tab){
  if(tab === 'history') loadSbHistory();
  if(tab === 'scheduled') cmd('schedule_list');
  if(tab === 'usage') loadUsageDashboard();
  if(tab === 'pipelines') loadPipelines();
  if(tab === 'memory') loadMemoryPanel();
  if(tab === 'agents') loadAgentsPanel();
  if(tab === 'demos') loadDemosPanel();
  if(tab === 'packages' && typeof loadPackagesSection === 'function') loadPackagesSection();
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

