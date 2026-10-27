// packages_install.js — Installing, updating, uploading and removing packages, and custom MCP servers.

// ═══════════════════════════════════════════════════════════════════════════════
// INSTALL WITH SETUP — install, then show setup if needed
// ═══════════════════════════════════════════════════════════════════════════════

function rpInstallWithSetup(pkgId, btn){
  if(btn){ btn.disabled = true; btn.classList.add('rp-installing'); btn.textContent = ''; }

  const card = btn ? btn.closest('.rp-card') : null;
  let progressEl = null;
  if(card){
    progressEl = document.createElement('div');
    progressEl.className = 'rp-install-progress';
    progressEl.innerHTML = '<div class="rp-progress-bar"><div class="rp-progress-fill" style="width:0%"></div></div><div class="rp-progress-label">Starting install...</div>';
    card.appendChild(progressEl);
  }
  fetch('/packages/install', {
    method: 'POST',
    headers: _rpHeaders(),
    body: JSON.stringify({package_id: pkgId, force: false})
  }).then(r=>r.json()).then(d=>{
    if(d.task_id){
      _pollInstallProgress(d.task_id, pkgId, btn, progressEl);
    } else if(d.requires_manual_setup){
      if(btn){ btn.disabled = false; btn.classList.remove('rp-installing'); btn.textContent = 'Install'; }
      if(progressEl) progressEl.remove();
      const card = btn ? btn.closest('.rp-card') : null;
      const manualSteps = [];
      if(d.setup && d.setup.install_steps){
        d.setup.install_steps.forEach(s => manualSteps.push({label: s.label || String(s), detail: s.cmd || s.detail || ''}));
      }
      if(!manualSteps.length){
        manualSteps.push({label: d.detail || 'Manual installation required'});
      }
      _showInstallResultPanel(card, [], manualSteps);
    } else if(d.ok !== false && !d.detail){
      _onInstallComplete(pkgId, btn, progressEl);
    } else {
      if(btn){ btn.disabled = false; btn.classList.remove('rp-installing'); btn.textContent = 'Install'; }
      const card = btn ? btn.closest('.rp-card') : null;
      _showInstallResultPanel(card, [{label: 'Installation failed', detail: d.detail || d.error || 'Unknown error'}], []);
      if(progressEl) progressEl.remove();
    }
  }).catch(e=>{
    if(btn){ btn.disabled = false; btn.classList.remove('rp-installing'); btn.textContent = 'Install'; }
    const card = btn ? btn.closest('.rp-card') : null;
    _showInstallResultPanel(card, [{label: 'Install failed', detail: e.message}], []);
    if(progressEl) progressEl.remove();
  });
}

// ─── Install / Uninstall (legacy) ────────────────────────────────────────────

function _pollInstallProgress(taskId, pkgId, btn, progressEl){
  const poll = () => {
    fetch('/packages/install/status/' + taskId)
      .then(r => r.json())
      .then(task => {
        if(progressEl){
          const fill = progressEl.querySelector('.rp-progress-fill');
          const label = progressEl.querySelector('.rp-progress-label');
          if(fill) fill.style.width = (task.progress || 0) + '%';
          if(label) label.textContent = task.current_step || 'Installing...';
          _renderInstallSteps(progressEl, task.steps || []);
        }
        if(btn) btn.textContent = (task.progress || 0) + '%';

        if(task.status === 'done'){
          _onInstallComplete(pkgId, btn, progressEl, task);
        } else if(task.status === 'failed'){
          if(btn){ btn.disabled = false; btn.classList.remove('rp-installing'); btn.textContent = 'Install'; }
          const failedSteps = (task.steps||[]).filter(s => s.status === 'failed');
          const errDetail = task.error || (failedSteps.length ? failedSteps[0].detail : 'Unknown error');
          const card = progressEl ? progressEl.closest('.rp-card') : null;
          _showInstallResultPanel(card, [{label: 'Installation failed', detail: errDetail}], []);
          if(progressEl) progressEl.remove();
        } else {
          setTimeout(poll, 1000);
        }
      })
      .catch(() => {
        setTimeout(poll, 2000);
      });
  };
  setTimeout(poll, 500);
}

function _onInstallComplete(pkgId, btn, progressEl, task){
  const failed = task && task.steps ? task.steps.filter(s => s.status === 'failed') : [];
  const manual = task && task.steps ? task.steps.filter(s => s.status === 'manual') : [];

  if(progressEl){
    const fill = progressEl.querySelector('.rp-progress-fill');
    const label = progressEl.querySelector('.rp-progress-label');
    if(fill) fill.style.width = '100%';
    if(label) label.textContent = manual.length
      ? 'Installed - manual setup remains'
      : failed.length
        ? 'Installed - dependency warnings'
        : 'Installation complete!';
    if(task && task.steps) _renderInstallSteps(progressEl, task.steps);
    if(!manual.length && !failed.length) setTimeout(() => progressEl.remove(), 3000);
  }

  // Show inline result panel instead of alert
  if(failed.length || manual.length){
    const card = btn ? btn.closest('.rp-card') : (progressEl ? progressEl.closest('.rp-card') : null);
    _showInstallResultPanel(card, failed, manual);
  }

  // Verify skill detected on disk before showing installed
  _verifyAndShowInstalled(pkgId, btn);

  fetch('/packages/setup/' + pkgId)
    .then(r => r.json())
    .then(setupData => {
      if(setupData.ok && setupData.setup && setupData.setup.type !== 'none'){
        setTimeout(() => _rpRenderSetupModal(pkgId, setupData.setup), 500);
      }
    })
    .catch(() => {});

  setTimeout(()=>{ loadPackageCatalog(); loadInstalledPackages(); }, 500);
}

function _renderInstallSteps(progressEl, steps){
  if(!progressEl) return;
  let stepsEl = progressEl.querySelector('.rp-progress-steps');
  if(!steps || !steps.length){
    if(stepsEl) stepsEl.remove();
    return;
  }
  if(!stepsEl){
    stepsEl = document.createElement('div');
    stepsEl.className = 'rp-progress-steps';
    progressEl.appendChild(stepsEl);
  }
  stepsEl.innerHTML = steps.map(step => {
    const status = step.status || 'pending';
    const detail = step.detail ? `<div class="rp-progress-step-detail">${escHtml(step.detail)}</div>` : '';
    return `<div class="rp-progress-step rp-progress-step-${escHtml(status)}">
      <span class="rp-progress-step-status">${escHtml(status)}</span>
      <span class="rp-progress-step-label">${escHtml(step.label || 'Install step')}</span>
      ${detail}
    </div>`;
  }).join('');
}

function rpInstall(pkgId, btn){
  rpInstallWithSetup(pkgId, btn);
}

function rpUninstall(pkgId, btn){
  if(!confirm('Uninstall package "' + pkgId + '"?')) return;
  if(btn){ btn.disabled = true; btn.textContent = 'Removing...'; }
  fetch('/packages/uninstall', {
    method: 'POST',
    headers: _rpHeaders(),
    body: JSON.stringify({package_id: pkgId})
  }).then(r=>r.json()).then(d=>{
    if(d.ok !== false && !d.detail){
      loadInstalledPackages();
    } else {
      alert('Uninstall failed: ' + (d.detail || d.error || 'Unknown error'));
      if(btn){ btn.disabled = false; btn.textContent = 'Uninstall'; }
    }
  }).catch(e=>{
    alert('Uninstall failed: ' + e.message);
    if(btn){ btn.disabled = false; btn.textContent = 'Uninstall'; }
  });
}

// ─── Update All ──────────────────────────────────────────────────────────────

function rpUpdateAll(){
  if(!_rpUpdates.length) return;
  if(!confirm(`Update ${_rpUpdates.length} package(s)?`)) return;

  const banner = document.querySelector('.rp-update-banner');
  if(banner) banner.innerHTML = '<span>Updating...</span>';

  // Install each update sequentially
  let chain = Promise.resolve();
  _rpUpdates.forEach(u => {
    chain = chain.then(() =>
      fetch('/packages/install', {
        method: 'POST',
        headers: _rpHeaders(),
        body: JSON.stringify({ package_id: u.id, force: true })
      }).then(r => r.json())
    );
  });

  chain.then(() => {
    _rpUpdates = [];
    _rpRenderUpdateBadge();
    loadInstalledPackages();
  }).catch(() => {
    alert('Some updates failed. Please try refreshing.');
    loadInstalledPackages();
  });
}

// ─── Upload .raprpkg file ────────────────────────────────────────────────────

function rpUploadInstall(){
  const fileInput = document.getElementById('rp-upload-file');
  if(!fileInput || !fileInput.files.length){
    alert('Select a .raprpkg file first');
    return;
  }
  const file = fileInput.files[0];
  if(!file.name.endsWith('.raprpkg')){
    alert('File must have .raprpkg extension');
    return;
  }

  const form = new FormData();
  form.append('file', file);

  fetch('/packages/install/upload', {
    method: 'POST',
    headers: {'x-csrf-token': _rpCsrfToken()},
    body: form
  }).then(r=>r.json()).then(d=>{
    if(d.ok !== false && !d.detail){
      alert('Package installed successfully!');
      fileInput.value = '';
      loadInstalledPackages();
    } else {
      alert('Upload install failed: ' + (d.detail || d.error || 'Unknown error'));
    }
  }).catch(e=>{
    alert('Upload install failed: ' + e.message);
  });
}

// ─── API helpers (kept for backward compat, called from installed cards) ─────

function togglePlugin(id, enable, connectable, connected){
  if(enable && connectable && !connected){
    connectPlugin(id);
    return;
  }
  fetch('/plugins/'+id+'/toggle',{
    method:'POST',
    headers: _rpHeaders(),
    body:JSON.stringify({enabled:enable})
  }).then(r=>r.json()).then(d=>{
    if(d.ok) loadInstalledPackages();
    else if(d.error) alert('Toggle failed: '+d.error);
  }).catch(()=>alert('Failed to toggle plugin'));
}

function connectPlugin(id){
  const url = '/plugins/'+id+'/connect';
  const w = 500, h = 600;
  const left = (screen.width - w) / 2, top = (screen.height - h) / 2;
  window.open(url, 'rapr-connect', `width=${w},height=${h},left=${left},top=${top},toolbar=no,menubar=no`);
}

function disconnectPlugin(id){
  if(!confirm('Disconnect this plugin? Stored tokens will be cleared.')) return;
  fetch('/plugins/'+id+'/disconnect',{method:'POST', headers:{'x-csrf-token':_rpCsrfToken()}})
    .then(r=>r.json()).then(d=>{
      if(d.ok) loadInstalledPackages();
    }).catch(()=>alert('Failed to disconnect plugin'));
}

function connectZapier(){
  const w = 540, h = 640;
  const left = (screen.width - w) / 2, top = (screen.height - h) / 2;
  window.open('/mcp/zapier/connect', 'rapr-connect',
    `width=${w},height=${h},left=${left},top=${top},toolbar=no,menubar=no`);
}

function disconnectZapier(){
  if(!confirm('Disconnect Zapier? Your stored MCP URL will be cleared and the server stopped.')) return;
  fetch('/mcp/zapier/disconnect',{method:'POST', headers:_rpHeaders()})
    .then(r=>r.json()).then(d=>{ if(d.ok) loadInstalledPackages(); })
    .catch(()=>alert('Failed to disconnect Zapier'));
}

function connectComposio(){
  const w = 540, h = 640;
  const left = (screen.width - w) / 2, top = (screen.height - h) / 2;
  window.open('/mcp/composio/connect', 'rapr-connect',
    `width=${w},height=${h},left=${left},top=${top},toolbar=no,menubar=no`);
}

function disconnectComposio(){
  if(!confirm('Disconnect Composio? Your stored MCP URL will be cleared and the server stopped.')) return;
  fetch('/mcp/composio/disconnect',{method:'POST', headers:_rpHeaders()})
    .then(r=>r.json()).then(d=>{ if(d.ok) loadInstalledPackages(); })
    .catch(()=>alert('Failed to disconnect Composio'));
}

// ─── Custom MCP servers ("Add any MCP") ─────────────────────────────────────

function openAddMcp(){
  const w = 600, h = 760;
  const left = (screen.width - w) / 2, top = (screen.height - h) / 2;
  window.open('/mcp/custom/add', 'rapr-add-mcp',
    `width=${w},height=${h},left=${left},top=${top},toolbar=no,menubar=no`);
}

function reconnectCustomMcp(id){
  fetch('/mcp/custom/'+encodeURIComponent(id)+'/connect',{method:'POST', headers:_rpHeaders()})
    .then(r=>r.json()).then(d=>{
      if(!d.ok && d.error) alert(d.error);
      loadInstalledPackages();
    }).catch(()=>alert('Failed to reconnect'));
}

function removeCustomMcp(id){
  if(!confirm('Remove this MCP server? Its saved keys are deleted and no AI will see its tools any more.')) return;
  fetch('/mcp/custom/'+encodeURIComponent(id),{method:'DELETE', headers:_rpHeaders()})
    .then(r=>r.json()).then(()=>loadInstalledPackages())
    .catch(()=>alert('Failed to remove the server'));
}

// While a custom server is connecting (or waiting on a sign-in), refresh the
// list so its status and sign-in link stay current.
let _rpCustomPoll = null;
function _rpScheduleCustomPoll(){
  clearTimeout(_rpCustomPoll);
  if(_rpTab !== 'installed' || !_rpMcpServers.some(s => s.custom && s.connecting)) return;
  _rpCustomPoll = setTimeout(()=>{
    fetch('/mcp/servers').then(r=>r.json()).then(d=>{
      _rpMcpServers = d.servers || [];
      renderInstalledPackages();
    }).catch(()=>{});
  }, 3000);
}

// Refresh the installed list when a connect popup reports success.
window.addEventListener('message', (e)=>{
  if(e.data && e.data.type === 'plugin-oauth-done' && e.data.success){
    setTimeout(()=>loadInstalledPackages(), 500);
  }
});

function toggleMcpServer(id, enable){
  fetch('/mcp/servers/'+id+'/toggle',{
    method:'POST',
    headers: _rpHeaders(),
    body:JSON.stringify({enabled:enable})
  }).then(r=>r.json()).then(d=>{
    if(d.ok) loadInstalledPackages();
    else if(d.error) alert('MCP error: '+d.error);
  }).catch(()=>alert('Failed to toggle MCP server'));
}

function togglePluginAccordion(headerEl){
  headerEl.parentElement.classList.toggle('open');
}

function expandAllPackages(){
  document.querySelectorAll('#rp-list .plg-accordion').forEach(el => el.classList.add('open'));
}

function collapseAllPackages(){
  document.querySelectorAll('#rp-list .plg-accordion').forEach(el => el.classList.remove('open'));
}

// ─── Auto-check updates on page load ─────────────────────────────────────────

setTimeout(()=> rpCheckUpdates(), 5000);

// ─── Install helpers ─────────────────────────────────────────────────────────

function _verifyAndShowInstalled(pkgId, btn){
  // Keep spinner while confirming skill was detected, then flip to installed
  if(btn){ btn.classList.add('rp-installing'); btn.textContent = 'Verifying...'; }
  fetch('/skills/rescan')
    .then(() => fetch('/packages/installed'))
    .then(r => r.json())
    .then(data => {
      const found = (data.packages || []).some(p => p.id === pkgId);
      if(btn){
        btn.classList.remove('rp-installing');
        if(found){
          btn.textContent = '✓ Installed';
          btn.classList.add('rp-done');
          btn.disabled = true;
        } else {
          btn.textContent = 'Install';
          btn.disabled = false;
        }
      }
    })
    .catch(() => {
      if(btn){
        btn.classList.remove('rp-installing');
        btn.textContent = '✓ Installed';
        btn.classList.add('rp-done');
        btn.disabled = true;
      }
    });
}

function _showInstallResultPanel(card, failed, manual){
  if(!card) return;
  if(!failed.length && !manual.length) return;
  const old = card.querySelector('.rp-install-result-panel');
  if(old) old.remove();

  const isError = failed.length > 0;
  const panel = document.createElement('div');
  panel.className = 'rp-install-result-panel ' + (isError ? 'rp-panel-error' : 'rp-panel-manual');

  function addSection(steps, titleText, extraMargin){
    const title = document.createElement('div');
    title.className = 'rp-panel-title';
    title.textContent = titleText;
    if(extraMargin) title.style.marginTop = '8px';
    panel.appendChild(title);
    steps.forEach(s => {
      const step = document.createElement('div');
      step.className = 'rp-panel-step';
      const lbl = document.createElement('div');
      lbl.className = 'rp-panel-step-label';
      lbl.textContent = s.label || '';
      step.appendChild(lbl);
      if(s.detail){
        const wrap = document.createElement('div');
        wrap.className = 'rp-copy-cmd-wrap';
        const code = document.createElement('code');
        code.className = 'rp-copy-cmd';
        code.textContent = s.detail;
        const copyBtn = document.createElement('button');
        copyBtn.className = 'rp-copy-btn';
        copyBtn.textContent = 'Copy';
        const detail = s.detail;
        copyBtn.onclick = () => _rpCopy(copyBtn, detail);
        wrap.appendChild(code);
        wrap.appendChild(copyBtn);
        step.appendChild(wrap);
      }
      panel.appendChild(step);
    });
  }

  if(isError) addSection(failed, 'Some steps failed — run these manually:');
  if(manual.length) addSection(manual, 'Manual steps required:', isError);

  const closeBtn = document.createElement('button');
  closeBtn.className = 'rp-panel-close';
  closeBtn.textContent = 'Dismiss';
  closeBtn.onclick = () => panel.remove();
  panel.appendChild(closeBtn);
  card.appendChild(panel);
}

function _rpCopy(btn, text){
  navigator.clipboard.writeText(text || '').then(() => {
    btn.textContent = 'Copied!';
    setTimeout(() => { btn.textContent = 'Copy'; }, 2000);
  }).catch(() => {
    btn.textContent = 'Failed';
    setTimeout(() => { btn.textContent = 'Copy'; }, 2000);
  });
}
