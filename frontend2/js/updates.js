// --- Updates: tell the user when RAPR has a newer version, and update in one click ----------------
// The server checks in the background (helm/updater.py); this page shows the result:
//   - a dot on the Settings button and, once per new version, a small "update available" bar
//   - an Updates section at the top of Settings: version, what's new, Check now, Update now,
//     and the automatic-check switch
//   - "Update now": source installs rerun their installer in the background (RAPR stops,
//     updates and starts again). This page waits and reloads itself when RAPR is back.

(function(){
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const csrf = () => (typeof _csrfToken === 'function' ? _csrfToken() : '');
  const post = (url, body) => fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json', 'x-csrf-token': csrf()},
                                          body: JSON.stringify(body || {})}).then(r => r.json());
  const KIND_LABEL = {
    'source-windows': 'installed with the Windows installer script',
    'source-mac': 'installed with the Mac installer script',
    'docker': 'cloud server (Docker)',
    'dev': 'running from a source checkout',
  };
  let status = null;
  let checking = false;

  function updateId(u){ return u && (u.latest_commit || u.latest_version) || ''; }
  function hasUpdate(){ return !!(status && status.update && status.update.update_available); }

  async function loadStatus(force){
    try {
      if(force){
        checking = true; render();
        await fetch('/update/check?force=1').then(r => r.json());
      }
      status = await fetch('/update/status').then(r => r.json());
    } catch(e){ /* offline or RAPR restarting */ }
    checking = false;
    render();
    markSettings();
    maybeShowBar();
  }

  // ---- dot on the Settings buttons ----
  function markSettings(){
    const on = hasUpdate();
    document.querySelectorAll('#sb-rail-settings, #sb-settings-footer button[onclick*="openSettings"]').forEach(b => {
      b.classList.toggle('has-update', on);
      if(on) b.title = 'Settings · an update is available';
      else b.title = 'Settings';
    });
  }

  // ---- once-per-version bar ----
  function maybeShowBar(){
    if(!hasUpdate() || document.getElementById('upd-bar')) return;
    const id = updateId(status.update);
    let dismissed = '';
    try { dismissed = localStorage.getItem('raprUpdateDismissed') || ''; } catch(e) {}
    if(id && dismissed === id) return;
    const bar = document.createElement('div');
    bar.id = 'upd-bar';
    bar.setAttribute('role', 'status');
    const n = status.update.behind_by;
    bar.innerHTML = `<span>${n ? `RAPR update available: ${n} new change${n === 1 ? '' : 's'}.` : 'A RAPR update is available.'}</span>
      <button type="button" class="upd-bar-link" data-act="open">What's new</button>
      ${status.install && status.install.self_update ? '<button type="button" class="upd-bar-go" data-act="update">Update now</button>' : ''}
      <button type="button" class="upd-bar-x" data-act="dismiss" aria-label="Not now" title="Not now">×</button>`;
    bar.addEventListener('click', e => {
      const act = e.target.closest('[data-act]')?.dataset.act;
      if(act === 'open'){ openUpdates(); }
      if(act === 'update'){ updateNow(); }
      if(act === 'dismiss' || act === 'open'){
        try { localStorage.setItem('raprUpdateDismissed', id); } catch(_) {}
        bar.remove();
      }
    });
    document.body.appendChild(bar);
  }

  function openUpdates(){
    if(typeof openSettings === 'function') openSettings();
    loadStatus(false);
    setTimeout(() => document.getElementById('updates-section')?.scrollIntoView({block: 'start'}), 50);
  }

  // ---- Settings section ----
  function render(){
    const el = document.getElementById('upd-panel');
    if(!el) return;
    if(!status){ el.innerHTML = '<small>Checking…</small>'; return; }
    const inst = status.install || {};
    const u = status.update || null;
    const short = c => c ? c.slice(0, 7) : '';
    let line = `RAPR ${esc(status.current_version)}`;
    if(inst.commit) line += ` · <code>${esc(short(inst.commit))}</code>`;
    if(inst.ref) line += ` · follows <code>${esc(inst.ref)}</code>`;
    let state, cls = '';
    if(checking) state = 'Checking for updates…';
    else if(!u) state = status.auto_check ? 'Not checked yet.' : 'Automatic checks are off.';
    else if(u.error){ state = esc(u.error); cls = 'is-warn'; }
    else if(u.update_available === true){
      state = u.behind_by ? `<b>Update available:</b> ${u.behind_by} new change${u.behind_by === 1 ? '' : 's'}` +
                            (u.latest_date ? ` (latest ${esc(u.latest_date)})` : '') + '.'
                          : `<b>Update available:</b> version ${esc(u.latest_version)}.`;
      cls = 'is-new';
    }
    else if(u.update_available === null){ state = 'RAPR can\'t tell which version this is (installed before update checks existed). Update now to get the latest and turn checks on.'; cls = 'is-new'; }
    else state = 'You have the latest version.';

    let changes = '';
    if(u && u.changes && u.changes.length){
      changes = '<div class="upd-changes-title">What\'s new</div><ul class="upd-changes">' +
        u.changes.map(c => `<li><span>${esc(c.title)}</span>${c.date ? `<time>${esc(c.date)}</time>` : ''}</li>`).join('') +
        (u.behind_by > u.changes.length ? `<li class="upd-more">…and ${u.behind_by - u.changes.length} more</li>` : '') + '</ul>';
    } else if(u && u.release_notes){
      changes = `<div class="upd-changes-title">What's new</div><div class="upd-notes">${esc(u.release_notes).slice(0, 1500)}</div>`;
    }

    const canUpdate = inst.self_update && u && (u.update_available === true || u.update_available === null);
    let how = '';
    if(u && u.update_available !== false && !inst.self_update){
      if(inst.kind === 'docker') how = 'To update this server, open RAPR on the computer that set it up and use <b>Settings → Cloud server → Update</b> (or run <code>docker compose pull && docker compose up -d</code> on the server).';
      else if(inst.kind === 'dev') how = 'This is a source checkout: update it with <code>git pull</code>, then restart RAPR.';
    }
    el.innerHTML = `
      <div class="upd-line">${line} <small>(${esc(KIND_LABEL[inst.kind] || inst.kind || '')})</small></div>
      <div class="upd-state ${cls}">${state}</div>
      ${changes}
      ${how ? `<div class="upd-how">${how}</div>` : ''}
      <div class="upd-actions">
        <button type="button" class="settings-save-btn upd-check" ${checking ? 'disabled' : ''}>Check now</button>
        ${canUpdate ? '<button type="button" class="settings-save-btn upd-go">Update now</button>' : ''}
      </div>
      <label class="upd-auto"><input type="checkbox" class="upd-auto-box" ${status.auto_check ? 'checked' : ''}>
        Check for updates automatically
        <small>Every hour RAPR asks GitHub whether there's a newer version (an ordinary web request that includes RAPR's version number). Nothing else is sent. Offline, it just skips.</small></label>`;
    el.querySelector('.upd-check').onclick = () => loadStatus(true);
    const go = el.querySelector('.upd-go'); if(go) go.onclick = updateNow;
    el.querySelector('.upd-auto-box').onchange = e => {
      post('/update/settings', {auto_check: e.target.checked}).then(() => loadStatus(false)).catch(() => {});
    };
  }

  // ---- Update now ----
  let overlay = null;
  function showOverlay(title, body){
    if(!overlay){
      overlay = document.createElement('div');
      overlay.id = 'upd-overlay';
      overlay.setAttribute('role', 'alertdialog');
      overlay.setAttribute('aria-live', 'polite');
      document.body.appendChild(overlay);
    }
    overlay.innerHTML = `<div class="upd-card"><div class="upd-spin" aria-hidden="true"></div>
      <div class="upd-card-title">${title}</div><div class="upd-card-body">${body}</div></div>`;
  }
  function failOverlay(msg, log){
    try { sessionStorage.removeItem('raprUpdating'); } catch(e) {}
    showOverlay('The update didn\'t finish', `${esc(msg)}${log ? `<pre class="upd-log">${esc(log)}</pre>` : ''}
      <button type="button" class="settings-save-btn" onclick="document.getElementById('upd-overlay').remove()">Close</button>`);
    overlay.querySelector('.upd-spin')?.remove();
    overlay = null;
  }

  async function updateNow(){
    if(!confirm('Update RAPR now?\n\nRAPR stops, updates and starts again by itself, usually in a minute or two. Anything an AI is doing right now is interrupted.')) return;
    if(typeof closeSettings === 'function') try { closeSettings(); } catch(e) {}
    document.getElementById('upd-bar')?.remove();
    try { sessionStorage.setItem('raprUpdating', String(Date.now())); } catch(e) {}

    const r = await post('/update/now').catch(() => ({ok: false, error: 'Could not reach RAPR.'}));
    if(!r.ok){ failOverlay(r.error || 'The update could not start.'); return; }
    showOverlay('Updating RAPR…', 'RAPR stops, updates and starts again by itself. This page reloads when it\'s back.');
    watchUpdate(Date.now());
  }

  // While updating: RAPR goes away (the installer stops it) and comes back. Once it's
  // back without the installer reporting a failure, reload to get the new page.
  async function watchUpdate(started){
    let wentDown = false;
    while(Date.now() - started < 10 * 60 * 1000){
      await new Promise(res => setTimeout(res, 3000));
      let log = null;
      try { log = await fetch('/update/log', {cache: 'no-store'}).then(r => r.ok ? r.json() : null); }
      catch(e){ wentDown = true; continue; }
      if(log && log.failed){ failOverlay('RAPR is still running the version you had. Here is what the installer said:', log.log); return; }
      if(wentDown && log){ location.reload(); return; }
    }
    failOverlay('RAPR hasn\'t come back after 10 minutes. Try reloading this page; if RAPR isn\'t running, start it from the Start menu (or run "rapr start") and check "rapr logs".');
  }

  // Back after an update?
  function afterReload(){
    let t = null;
    try { t = sessionStorage.getItem('raprUpdating'); sessionStorage.removeItem('raprUpdating'); } catch(e) {}
    if(!t) return;
    const bar = document.createElement('div');
    bar.id = 'upd-bar';
    bar.setAttribute('role', 'status');
    bar.innerHTML = '<span>RAPR is updated.</span><button type="button" class="upd-bar-x" aria-label="Close">×</button>';
    bar.querySelector('button').onclick = () => bar.remove();
    document.body.appendChild(bar);
    setTimeout(() => bar.remove(), 8000);
  }

  window.openUpdates = openUpdates;
  window.raprUpdateNow = updateNow;

  // Refresh the Updates section whenever Settings opens, asking GitHub again when
  // the last check is more than 10 minutes old.
  function stale(){ return !status || !status.last_check_at || Date.now() / 1000 - status.last_check_at > 10 * 60; }
  const origOpen = window.openSettings;
  if(typeof origOpen === 'function'){
    window.openSettings = function(){ const r = origOpen.apply(this, arguments); loadStatus(stale()); return r; };
  }

  afterReload();
  setTimeout(() => loadStatus(false), 4000);
  setInterval(() => loadStatus(false), 15 * 60 * 1000);   // pick up the server's hourly check
})();
