// --- Usage ribbon --------------------------------------------------------------------------------------------
// A thin strip above the message box: how much the AI you're talking to has used this period
// (time against its cap, tasks, tokens, cost, when it resets), plus what AIs run from your
// editors through `rapr mcp` did today. Click it for every AI; × hides it (Usage panel brings it back).
// Data: /api/usage (helm/web_routes/usage_routes.py), refreshed every 30 s and after each reply.

let _ribbonData = null, _ribbonTimer = null, _ribbonOpen = false;
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

function _ribbonLevel(pct, budget){
  if(budget && budget.allowed === false) return 'over';
  if(budget && budget.warn) return 'warn';
  if(pct == null) return '';
  return pct >= 90 ? 'over' : pct >= 70 ? 'warn' : '';
}

// One AI as "Codex 4% · 12m/300m · 8 tasks · ~32k tok · $0.12"
function _ribbonAiParts(a){
  const parts = [];
  const planned = (a.limits || []).length;
  parts.push(a.cap_min && !planned ? `${_ribbonFmtMin(a.used_min)} / ${_ribbonFmtMin(a.cap_min)}` : _ribbonFmtMin(a.used_min));
  parts.push(`${a.tasks} task${a.tasks === 1 ? '' : 's'}`);
  parts.push(`${a.tokens_source === 'actual' ? '' : '~'}${_ribbonFmtTok(a.total_tokens)} tok`);
  if(a.cost_usd >= 0.005) parts.push('$' + a.cost_usd.toFixed(2));
  return parts;
}

function _ribbonMeter(pct, level){
  const w = pct == null ? 0 : Math.max(2, Math.min(100, pct));
  return `<span class="ur-meter ${level}" aria-hidden="true"><span style="width:${w}%"></span></span>`;
}

function _ribbonResetText(at){
  if(!at) return '';
  const s = Math.max(0, at - Date.now() / 1000);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
  const when = new Date(at * 1000).toLocaleString([], {weekday: 'short', hour: 'numeric', minute: '2-digit'});
  return `resets in ${h >= 24 ? Math.floor(h / 24) + 'd ' + (h % 24) + 'h' : h + 'h ' + m + 'm'} (${when})`;
}

// The share used: the plan's own windows when the AI reported them (Claude's 5h and week,
// Codex's), else RAPR's estimate against the cap in .env.
function _ribbonGauge(a){
  const wins = a.limits || [];
  if(wins.length){
    return wins.map(w => {
      const level = w.pct >= 90 ? 'over' : w.pct >= 70 ? 'warn' : '';
      const tip = `${a.label} ${w.label}: ${w.pct.toFixed(0)}% of your plan used, as ${a.label} reports it. ${_ribbonResetText(w.resets_at)}`;
      return `<span class="ur-win" title="${escHtml(tip)}"><span class="ur-wl">${escHtml(w.label)}</span>` +
        _ribbonMeter(w.pct, level) + `<span class="ur-pct ${level}">${w.pct.toFixed(0)}%</span></span>`;
    }).join('');
  }
  const pct = a.pct_used, level = _ribbonLevel(pct, a.budget);
  const tip = pct == null ? 'No cap set' : `Estimated: time used against the cap in .env (USAGE_CAP_MIN_${String(a.label).toUpperCase()})`;
  return _ribbonMeter(pct, level) +
    `<span class="ur-pct ${level}" title="${escHtml(tip)}">${pct == null ? 'no cap' : '≈' + pct.toFixed(0) + '%'}</span>`;
}

function renderUsageRibbon(){
  const el = document.getElementById('usage-ribbon');
  if(!el) return;
  const hidden = localStorage.getItem(_RIBBON_HIDDEN_KEY) === '1';
  const d = _ribbonData;
  if(hidden || !d){ el.hidden = true; return; }

  const ais = d.ais || {};
  const used = Object.keys(ais).filter(k => (ais[k].tasks || 0) > 0 || (ais[k].limits || []).length);
  const mcp = d.mcp || {};
  const mcpToday = (mcp.today || {});
  if(!used.length && !(mcpToday.calls > 0) && !_focusedAi){ el.hidden = true; return; }

  // The AI of the session you're in; else the busiest one.
  let key = _focusedAi && ais[_focusedAi] ? _focusedAi : null;
  if(!key && used.length) key = used.sort((x, y) => ais[y].used_min - ais[x].used_min)[0];
  const a = key ? ais[key] : null;

  let main = '';
  if(a){
    main = `<span class="ur-ai">${escHtml(a.label)}</span>` + _ribbonGauge(a) +
      _ribbonAiParts(a).map(p => `<span class="ur-sep">·</span><span>${escHtml(p)}</span>`).join('') +
      (a.budget && a.budget.allowed === false ? '<span class="ur-flag over">budget reached</span>' : '');
  } else {
    main = '<span class="ur-dim">No AI used yet this period</span>';
  }
  const mcpPart = mcpToday.calls > 0
    ? `<span class="ur-mcp" title="AIs RAPR ran for Claude Code, Codex, Cursor… through rapr mcp, today">` +
      `editors: ${mcpToday.calls} call${mcpToday.calls === 1 ? '' : 's'} · ${_ribbonFmtMin((mcpToday.seconds || 0) / 60)}</span>`
    : '';

  let details = '';
  if(_ribbonOpen){
    const rows = used.sort((x, y) => ais[y].used_min - ais[x].used_min).map(k => {
      const x = ais[k];
      return `<div class="ur-row"><span class="ur-ai">${escHtml(x.label)}</span>${_ribbonGauge(x)}` +
        `<span class="ur-dim">${escHtml(_ribbonAiParts(x).join(' · '))}</span></div>`;
    });
    const mcpAgents = Object.entries(mcpToday.agents || {}).sort((x, y) => (y[1].seconds || 0) - (x[1].seconds || 0));
    mcpAgents.forEach(([k, x]) => {
      rows.push(`<div class="ur-row"><span class="ur-ai">${escHtml(x.name || k)}</span><span class="ur-tag">editor</span>` +
        `<span class="ur-dim">${x.calls} call${x.calls === 1 ? '' : 's'} · ${_ribbonFmtMin((x.seconds || 0) / 60)} · ${x.estimated ? '~' : ''}${_ribbonFmtTok(x.tokens)} tok` +
        `${x.cost_usd >= 0.005 ? ' · $' + x.cost_usd.toFixed(2) : ''}` +
        `${x.failed ? ' · ' + x.failed + ' failed' : ''}</span></div>`);
    });
    details = `<div class="ur-details">${rows.join('') || '<div class="ur-dim">Nothing yet</div>'}` +
      `<div class="ur-foot ur-dim">5h / week: your plan, as each AI reports it · ≈ estimated against your cap · ~ tokens estimated from text length · RAPR's own counters reset in ${escHtml(d.reset_eta || '?')}</div></div>`;
  }

  el.innerHTML =
    `<div class="ur-line" role="button" tabindex="0" onclick="toggleUsageRibbon()" onkeydown="if(event.key==='Enter')toggleUsageRibbon()"` +
    ` title="${_ribbonOpen ? 'Hide' : 'Show'} every AI's usage · resets in ${escHtml(d.reset_eta || '?')}" aria-expanded="${_ribbonOpen}">` +
    `<span class="ur-main">${main}</span>${mcpPart}` +
    `<span class="ur-chev">${_ribbonOpen ? '▾' : '▸'}</span>` +
    `<button class="ur-close" onclick="event.stopPropagation();hideUsageRibbon()" title="Hide the usage ribbon (bring it back from the Usage panel)" aria-label="Hide usage ribbon">×</button>` +
    `</div>${details}`;
  el.hidden = false;
}

function refreshUsageRibbon(){
  if(localStorage.getItem(_RIBBON_HIDDEN_KEY) === '1') return renderUsageRibbon();
  fetch('/api/usage').then(r => r.ok ? r.json() : null).then(d => {
    if(d){ _ribbonData = d; renderUsageRibbon(); }
  }).catch(() => {});
}

function toggleUsageRibbon(){ _ribbonOpen = !_ribbonOpen; renderUsageRibbon(); }

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
      if(!active) setTimeout(refreshUsageRibbon, 500);
    };
  }
  if(typeof applyState === 'function'){
    const origApply = applyState;
    applyState = function(s){
      const before = _focusedAi;
      origApply.apply(this, arguments);
      if(_focusedAi !== before) renderUsageRibbon();
    };
  }
  refreshUsageRibbon();
  _ribbonTimer = setInterval(() => { if(!document.hidden) refreshUsageRibbon(); }, 30000);
})();
