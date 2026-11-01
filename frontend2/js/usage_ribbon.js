// --- Usage ribbon --------------------------------------------------------------------------------------------
// A thin strip above the message box, shown once you're in a session: the real usage of the AI
// you're talking to, as that AI's own service reports it (helm/usage_readers.py):
//   - a plan (Claude Pro/Max, ChatGPT, Google sign-in): its windows, e.g. 5h 61% · week 88%
//   - an API key: no windows, just what you've spent through RAPR
//   - a local model: nothing to limit
//   - nothing reported: why (not signed in...)
// Click it for every AI set up here, read live from each AI's service. × hides it (the Usage
// panel brings it back). Data: /api/usage (helm/web_routes/usage_routes.py).

let _ribbonData = null, _ribbonTimer = null, _ribbonOpen = false, _ribbonAsking = false;
const _RIBBON_HIDDEN_KEY = 'raprUsageRibbonHidden';

function _ribbonFmtMin(m){
  m = Math.max(0, m || 0);
  if(m < 1) return Math.round(m * 60) + 's';
  if(m < 60) return m.toFixed(m < 10 ? 1 : 0) + 'm';
  return Math.floor(m / 60) + 'h ' + String(Math.round(m % 60)).padStart(2, '0') + 'm';
}

function _ribbonFmtTok(n){
  n = n || 0;
  if(n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if(n >= 1e3) return (n / 1e3).toFixed(1) + 'k';
  return String(n);
}

function _ribbonAgo(at){
  if(!at) return '';
  const s = Math.max(0, Date.now() / 1000 - at);
  if(s < 90) return 'just now';
  if(s < 3600) return Math.round(s / 60) + 'm ago';
  return Math.round(s / 3600) + 'h ago';
}

function _ribbonResetText(at){
  if(!at) return '';
  const s = Math.max(0, at - Date.now() / 1000);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
  const when = new Date(at * 1000).toLocaleString([], {weekday: 'short', hour: 'numeric', minute: '2-digit'});
  return `resets in ${h >= 24 ? Math.floor(h / 24) + 'd ' + (h % 24) + 'h' : h + 'h ' + m + 'm'} (${when})`;
}

function _ribbonMeter(pct, level){
  const w = pct == null ? 0 : Math.max(2, Math.min(100, pct));
  return `<span class="ur-meter ${level}" aria-hidden="true"><span style="width:${w}%"></span></span>`;
}

const _ribbonLevelOf = pct => pct >= 90 ? 'over' : pct >= 70 ? 'warn' : '';

// RAPR's own counters for an AI: tasks, tokens, and money where it's really spent.
function _ribbonCounters(a){
  const parts = [];
  if(a.tasks) parts.push(`${a.tasks} task${a.tasks === 1 ? '' : 's'} · ${_ribbonFmtMin(a.used_min)}`);
  if(a.total_tokens) parts.push(`${a.tokens_source === 'actual' ? '' : '~'}${_ribbonFmtTok(a.total_tokens)} tok`);
  return parts;
}

// What the AI's own service says about it: plan windows, API key, local, or why there's nothing.
function _ribbonUsage(a, withResets){
  const wins = a.limits || [];
  if(wins.length){
    const asOf = a.as_of ? ` (as of ${_ribbonAgo(a.as_of)})` : '';
    return wins.map(w => {
      const level = _ribbonLevelOf(w.pct);
      const reset = _ribbonResetText(w.resets_at);
      const tip = `${a.label} ${w.label}: ${w.pct.toFixed(0)}% used, as ${a.label} reports it${asOf}. ${reset}`;
      return `<span class="ur-win" title="${escHtml(tip)}"><span class="ur-wl">${escHtml(w.label)}</span>` +
        _ribbonMeter(w.pct, level) + `<span class="ur-pct ${level}">${w.pct.toFixed(0)}%</span>` +
        (withResets && reset ? `<span class="ur-dim ur-reset-at">${escHtml(reset.replace(/ \(.*\)$/, ''))}</span>` : '') +
        `</span>`;
    }).join('');
  }
  if(a.billing === 'api'){
    return `<span class="ur-tag" title="${escHtml(a.label)} uses an API key: billed per token, with no 5-hour or weekly limit">API key</span>` +
      (a.cost_usd >= 0.005 ? `<span>$${a.cost_usd.toFixed(2)} spent</span>` : '<span class="ur-dim">nothing spent through RAPR yet</span>');
  }
  if(a.local) return '<span class="ur-tag">local</span><span class="ur-dim">no limit</span>';
  if(a.cap_min){
    const level = _ribbonLevelOf(a.pct_used);
    return _ribbonMeter(a.pct_used, level) +
      `<span class="ur-pct ${level}" title="Time used against the cap you set (USAGE_CAP_MIN_${escHtml(String(a.label).toUpperCase())})">` +
      `${_ribbonFmtMin(a.used_min)} of your ${_ribbonFmtMin(a.cap_min)} cap</span>`;
  }
  return `<span class="ur-dim">${escHtml(a.note || a.label + " doesn't report its usage")}</span>`;
}

function _ribbonPlanTag(a){
  return a.plan ? `<span class="ur-tag">${escHtml(a.plan)}</span>` : '';
}

// Every AI set up here: those with something to show first, busiest first.
function _ribbonOrder(ais){
  const rank = a => (a.limits || []).length ? 0 : a.billing === 'api' ? 1 : a.tasks ? 2 : a.local ? 4 : 3;
  return Object.keys(ais).sort((x, y) => rank(ais[x]) - rank(ais[y]) || (ais[y].used_min || 0) - (ais[x].used_min || 0)
                                           || String(ais[x].label).localeCompare(String(ais[y].label)));
}

function renderUsageRibbon(){
  const el = document.getElementById('usage-ribbon');
  if(!el) return;
  const d = _ribbonData;
  const sess = (typeof _sessions !== 'undefined' ? _sessions : []).find(s => s.id === _focusedId);
  // Nothing to say until you're in a session with an AI (a shell has no usage).
  if(usageRibbonHidden() || !d || !sess || !_focusedAi || _focusedAi === 'shell'){ el.hidden = true; return; }

  const ais = d.ais || {};
  const a = ais[_focusedAi] || {label: (typeof AI_LABEL !== 'undefined' && AI_LABEL[_focusedAi]) || _focusedAi,
                                tasks: 0, used_min: 0, limits: [], note: ''};
  const counters = _ribbonCounters(a);
  const mcpToday = ((d.mcp || {}).today) || {};
  const mcpPart = mcpToday.calls > 0
    ? `<span class="ur-mcp" title="AIs RAPR ran for Claude Code, Codex, Cursor… through rapr mcp, today">` +
      `editors: ${mcpToday.calls} call${mcpToday.calls === 1 ? '' : 's'}</span>`
    : '';
  const main = `<span class="ur-ai">${escHtml(a.label)}</span>${_ribbonPlanTag(a)}${_ribbonUsage(a, false)}` +
    counters.map(p => `<span class="ur-sep">·</span><span class="ur-dim">${escHtml(p)}</span>`).join('');

  let details = '';
  if(_ribbonOpen){
    // A row for each AI with something to show; the rest folded into one line each.
    const quiet = [], local = [];
    const rows = [];
    _ribbonOrder(ais).forEach(k => {
      const x = ais[k];
      const c = _ribbonCounters(x);
      const shows = (x.limits || []).length || x.billing === 'api' || x.cap_min || c.length || k === _focusedAi
                    || (x.note && !x.local);
      if(!shows && x.local){ local.push(x.label); return; }
      if(!shows && !x.note){ quiet.push(x.label); return; }
      rows.push(`<div class="ur-row${k === _focusedAi ? ' ur-current' : ''}"><span class="ur-ai">${escHtml(x.label)}</span>` +
        `<span class="ur-row-usage">${_ribbonPlanTag(x)}${_ribbonUsage(x, true)}</span>` +
        (c.length ? `<span class="ur-dim ur-row-counters">${escHtml(c.join(' · '))}</span>` : '') + `</div>`);
    });
    if(local.length) rows.push(`<div class="ur-row ur-dim"><span class="ur-tag">local</span>no limit: ${escHtml(local.join(', '))}</div>`);
    if(quiet.length) rows.push(`<div class="ur-row ur-dim" title="These AIs have no usage service RAPR can ask">Don't report usage: ${escHtml(quiet.join(', '))}</div>`);
    Object.entries(mcpToday.agents || {}).sort((x, y) => (y[1].seconds || 0) - (x[1].seconds || 0)).forEach(([k, x]) => {
      rows.push(`<div class="ur-row"><span class="ur-ai">${escHtml(x.name || k)}</span><span class="ur-tag">from editors</span>` +
        `<span class="ur-dim">${x.calls} call${x.calls === 1 ? '' : 's'} · ${_ribbonFmtMin((x.seconds || 0) / 60)} · ` +
        `${x.estimated ? '~' : ''}${_ribbonFmtTok(x.tokens)} tok${x.cost_usd >= 0.005 ? ' · $' + x.cost_usd.toFixed(2) + ' spent' : ''}` +
        `${x.failed ? ' · ' + x.failed + ' failed' : ''}</span></div>`);
    });
    details = `<div class="ur-details">` +
      (_ribbonAsking ? '<div class="ur-dim">Asking each AI for its usage…</div>' : '') +
      (rows.join('') || '<div class="ur-dim">No AI set up yet</div>') +
      `<div class="ur-foot ur-dim">Plan usage comes from each AI's own service (the numbers on its usage page). ` +
      `An API key has no 5-hour or weekly limit: its row shows money spent. ~ tokens estimated from text length.` +
      ` <a href="#" onclick="event.preventDefault();event.stopPropagation();askUsageNow()">Ask again</a></div></div>`;
  }

  el.innerHTML =
    `<div class="ur-line" role="button" tabindex="0" onclick="toggleUsageRibbon()" onkeydown="if(event.key==='Enter')toggleUsageRibbon()"` +
    ` title="${_ribbonOpen ? 'Hide' : 'Show'} every AI's usage" aria-expanded="${_ribbonOpen}">` +
    `<span class="ur-main">${main}</span>${mcpPart}` +
    `<span class="ur-chev">${_ribbonOpen ? '▾' : '▸'}</span>` +
    `<button class="ur-close" onclick="event.stopPropagation();hideUsageRibbon()" title="Hide the usage ribbon (bring it back from the Usage panel)" aria-label="Hide usage ribbon">×</button>` +
    `</div>${details}`;
  el.hidden = false;
}

function refreshUsageRibbon(live){
  if(usageRibbonHidden() && !live){ renderUsageRibbon(); return Promise.resolve(); }
  return fetch('/api/usage' + (live ? '?live=1' : '')).then(r => r.ok ? r.json() : null).then(d => {
    if(d){ _ribbonData = d; renderUsageRibbon(); }
  }).catch(() => {});
}

// Opened, or "Ask again": ask every AI's service now rather than use the last answer.
function askUsageNow(){
  _ribbonAsking = true; renderUsageRibbon();
  refreshUsageRibbon(true).finally(() => { _ribbonAsking = false; renderUsageRibbon(); });
}

function toggleUsageRibbon(){
  _ribbonOpen = !_ribbonOpen;
  if(_ribbonOpen) askUsageNow(); else renderUsageRibbon();
}

function hideUsageRibbon(){
  localStorage.setItem(_RIBBON_HIDDEN_KEY, '1');
  renderUsageRibbon();
}

function showUsageRibbon(){
  localStorage.removeItem(_RIBBON_HIDDEN_KEY);
  refreshUsageRibbon();
}

function usageRibbonHidden(){ return localStorage.getItem(_RIBBON_HIDDEN_KEY) === '1'; }

(function initUsageRibbon(){
  // After each reply (setThinking(false…)) and when you switch sessions, show fresh numbers.
  if(typeof setThinking === 'function'){
    const orig = setThinking;
    setThinking = function(active, ai, session_id){
      orig.apply(this, arguments);
      if(!active) setTimeout(() => refreshUsageRibbon(), 500);
    };
  }
  if(typeof applyState === 'function'){
    const origApply = applyState;
    applyState = function(s){
      const before = _focusedAi + '|' + _focusedId;
      origApply.apply(this, arguments);
      if(_focusedAi + '|' + _focusedId !== before) renderUsageRibbon();
    };
  }
  refreshUsageRibbon();
  _ribbonTimer = setInterval(() => { if(!document.hidden) refreshUsageRibbon(); }, 60000);
})();
