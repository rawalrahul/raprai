// ─────────────────────────────────────────────────────────────────────────────
// RAPR Packages — unified panel for Plugins, MCP Servers, and Marketplace
// ─────────────────────────────────────────────────────────────────────────────

let _rpTab = 'installed';    // 'installed' | 'browse'
let _rpType = '';             // '' | 'skill' | 'mcp' | 'plugin'
let _rpQuery = '';
let _rpDebounce = null;
let _rpCatalog = [];          // cached catalog results
let _rpInstalled = [];        // cached installed package list
let _rpPlugins = [];          // cached plugins list
let _rpMcpServers = [];       // cached MCP servers list
let _rpSkills = [];           // cached detected skills list
let _rpUpdates = [];          // cached available updates
let _rpUpdateCheckDone = false;

// ─── CSRF helper ────────────────────────────────────────────────────────────

function _rpCsrfToken(){
  const m = document.cookie.match(/(?:^|;\s*)hq_csrf=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : '';
}

function _rpHeaders(extra){
  const h = {'Content-Type':'application/json', 'x-csrf-token': _rpCsrfToken()};
  return extra ? Object.assign(h, extra) : h;
}

// ─── Panel toggle ────────────────────────────────────────────────────────────

function togglePackagesPanel(){
  const el = document.getElementById('sb-packages-section');
  if(!el) return;
  const wasOpen = el.classList.contains('open');
  el.classList.toggle('open');
  if(!wasOpen){
    if(_rpTab === 'installed') loadInstalledPackages();
    else loadPackageCatalog();
    // Check for updates in background
    if(!_rpUpdateCheckDone) rpCheckUpdates();
  }
}

// ─── Refresh ────────────────────────────────────────────────────────────────

function rpRefresh(){
  if(_rpTab === 'installed'){
    // Trigger a rescan of the skills directory first, then reload
    fetch('/skills/rescan').catch(()=>{}).finally(()=> loadInstalledPackages());
  } else {
    loadPackageCatalog(true);
  }
  // Also refresh updates
  rpCheckUpdates(true);
}

// ─── Tab switching ───────────────────────────────────────────────────────────

function rpSwitchTab(btn, tab){
  _rpTab = tab;
  document.querySelectorAll('.rp-tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  if(tab === 'installed') loadInstalledPackages();
  else loadPackageCatalog();
}

// ─── Type filter ─────────────────────────────────────────────────────────────

function rpSetType(btn, type){
  _rpType = type;
  document.querySelectorAll('.rp-type-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  if(_rpTab === 'installed') renderInstalledPackages();
  else loadPackageCatalog();
}

// ─── Search debounce ─────────────────────────────────────────────────────────

function rpSearchDebounce(){
  clearTimeout(_rpDebounce);
  _rpDebounce = setTimeout(()=>{
    _rpQuery = (document.getElementById('rp-search')?.value || '').trim();
    if(_rpTab === 'installed') renderInstalledPackages();
    else loadPackageCatalog();
  }, 300);
}

// ─── Update checking ─────────────────────────────────────────────────────────

function rpCheckUpdates(force){
  fetch('/packages/updates' + (force ? '?force=true' : ''))
    .then(r=>r.json())
    .then(data=>{
      _rpUpdates = data.updates || [];
      _rpUpdateCheckDone = true;
      _rpRenderUpdateBadge();
    })
    .catch(()=>{});
}

function _rpRenderUpdateBadge(){
  // Update the sidebar badge
  const badge = document.getElementById('rp-update-badge');
  if(badge){
    if(_rpUpdates.length > 0){
      badge.textContent = _rpUpdates.length;
      badge.style.display = 'inline-flex';
    } else {
      badge.style.display = 'none';
    }
  }
  // If installed tab is showing, re-render to show update indicators
  if(_rpTab === 'installed' && _rpUpdates.length > 0){
    renderInstalledPackages();
  }
}

function _rpGetUpdate(pkgId){
  // Check if there's an update for this package
  return _rpUpdates.find(u => u.id === pkgId || u.id === pkgId.replace(/_/g, '-'));
}

// ═══════════════════════════════════════════════════════════════════════════════
// INSTALLED TAB — merges Plugins + MCP Servers + Detected Skills + Marketplace Packages
// ═══════════════════════════════════════════════════════════════════════════════

function loadInstalledPackages(){
  const container = document.getElementById('rp-list');
  if(!container) return;
  container.innerHTML = '<div class="sb-empty rp-loading">Loading...</div>';

  // Fetch all four sources in parallel
  Promise.all([
    fetch('/plugins').then(r=>r.json()).catch(()=>({plugins:[]})),
    fetch('/mcp/servers').then(r=>r.json()).catch(()=>({servers:[]})),
    fetch('/packages/installed').then(r=>r.json()).catch(()=>({ok:true,packages:[]})),
    fetch('/skills').then(r=>r.json()).catch(()=>({skills:[]}))
  ]).then(([pluginData, mcpData, pkgData, skillsData])=>{
    _rpPlugins = pluginData.plugins || [];
    _rpMcpServers = mcpData.servers || [];
    _rpInstalled = (pkgData.packages || []);
    _rpSkills = skillsData.skills || [];
    renderInstalledPackages();
  }).catch(()=>{
    container.innerHTML = '<div class="sb-empty">Failed to load packages</div>';
  });
}

function renderInstalledPackages(){
  const container = document.getElementById('rp-list');
  if(!container) return;

  let items = [];
  const q = _rpQuery.toLowerCase();

  // Show update banner if there are updates
  let updateBannerHtml = '';
  if(_rpUpdates.length > 0 && !_rpQuery && !_rpType){
    updateBannerHtml = `
    <div class="rp-update-banner">
      <span class="rp-update-icon">↑</span>
      <span>${_rpUpdates.length} update${_rpUpdates.length>1?'s':''} available</span>
      <button class="rp-update-all-btn" onclick="rpUpdateAll()">Update All</button>
    </div>`;
  }

  // Plugins → unified items
  if(!_rpType || _rpType === 'plugin'){
    _rpPlugins.forEach(p => {
      if(q && !(p.name||'').toLowerCase().includes(q) && !(p.id||'').toLowerCase().includes(q)) return;
      items.push({_source:'plugin', _data:p, name:p.name, id:p.id, type:'plugin',
        emoji:p.emoji||'🧩', description:p.description||'', enabled:p.enabled,
        connected:p.connected, connectable:p.connectable, category:p.category});
    });
  }

  // MCP Servers → unified items
  if(!_rpType || _rpType === 'mcp'){
    _rpMcpServers.forEach(s => {
      if(q && !(s.id||'').toLowerCase().includes(q)) return;
      items.push({_source:'mcp', _data:s, name:s.id.replace(/_/g,' '), id:s.id, type:'mcp',
        emoji: s.running ? '🟢' : (s.enabled ? '🟡' : '⚪'),
        description: s.running ? (s.summary||'Running') : 'Server not running',
        enabled:s.enabled, running:s.running, tool_count:s.tool_count||0,
        connector:s.connector, connected:s.connected});
    });
  }

  // Detected skills (from .skills/ folder)
  if(!_rpType || _rpType === 'skill'){
    _rpSkills.forEach(s => {
      if(q && !(s.name||'').toLowerCase().includes(q)
           && !(s.description||'').toLowerCase().includes(q)
           && !(s.keywords||[]).some(k=>k.toLowerCase().includes(q))) return;
      items.push({_source:'skill', _data:s, name:s.name, id:s.name, type:'skill',
        emoji:'📜', description:s.description||'', keywords:s.keywords||[]});
    });
  }

  // Installed packages (from marketplace)
  if(!_rpType || !['plugin','mcp','skill'].includes(_rpType)){
    _rpInstalled.forEach(p => {
      if(_rpType && (p.type||'').toLowerCase() !== _rpType) return;
      if(q && !(p.name||'').toLowerCase().includes(q) && !(p.id||'').toLowerCase().includes(q)) return;
      items.push({_source:'package', _data:p, name:p.name, id:p.id, type:p.type||'skill',
        emoji: (p.type==='mcp'?'🔌':p.type==='plugin'?'🧩':'📦'),
        description:p.description||'', version:p.version||'', author:p.author||''});
    });
  }

  if(!items.length){
    container.innerHTML = updateBannerHtml + (_rpQuery || _rpType
      ? '<div class="sb-empty">No packages match your search</div>'
      : '<div class="sb-empty">No packages installed yet</div>');
    return;
  }

  container.innerHTML = updateBannerHtml + items.map(item => _renderInstalledCard(item)).join('');
}

function _renderInstalledCard(item){
  const id = escHtml(item.id);
  const name = escHtml(item.name);
  const type = item.type;
  const typeEmoji = type === 'mcp' ? '🔌' : type === 'plugin' ? '🧩' : '📦';
  const typeBadge = `<span class="rp-type-badge rp-type-${type}">${typeEmoji} ${type}</span>`;

  // Check for available update
  const update = _rpGetUpdate(item.id);
  const updateBadge = update
    ? `<span class="rp-update-badge-inline" title="Update available: v${escHtml(update.latest_version)}">↑ v${escHtml(update.latest_version)}</span>`
    : '';

  if(item._source === 'plugin'){
    const p = item._data;
    const connectable = p.connectable;
    const connected = p.connected;
    const isLocal = !connectable && connected;
    const statusDot = connected
      ? '<span class="plg-dot connected" title="Connected"></span>'
      : (p.enabled ? '<span class="plg-dot enabled" title="Enabled"></span>' : '');

    let headerAction = '';
    if(connectable && !connected){
      headerAction = `<button class="plg-header-connect" onclick="event.stopPropagation();connectPlugin('${id}')" title="Connect">Connect</button>`;
    } else if(connectable && connected){
      headerAction = `<span class="plg-header-connected">Connected</span>`;
    } else if(isLocal){
      headerAction = `<span class="plg-header-connected local">Ready</span>`;
    }

    const toggle = `<button class="toggle-switch ${p.enabled?'on':''}"
      onclick="event.stopPropagation();togglePlugin('${id}',${!p.enabled},${connectable},${connected})"
      title="${p.enabled?'Disable':'Enable'}"></button>`;

    return `
    <div class="plg-accordion" data-plugin-id="${id}">
      <div class="plg-accordion-header" onclick="togglePluginAccordion(this)">
        <span class="plg-accordion-arrow">▶</span>
        <span class="plg-emoji">${p.emoji||'🧩'}</span>
        <span class="plg-title">${name}</span>
        ${statusDot} ${typeBadge} ${updateBadge}
        <div class="plg-header-right">${headerAction} ${toggle}</div>
      </div>
      <div class="plg-accordion-body">
        <div class="plg-body-desc">${escHtml(p.description)}</div>
        <div class="plg-body-meta">
          <span class="plugin-cat">${escHtml(p.category||'general')}</span>
          ${connectable && connected ? `<button class="plg-disconnect-btn" onclick="event.stopPropagation();disconnectPlugin('${id}')" title="Disconnect">Disconnect</button>` : ''}
          ${connectable && !connected ? `<button class="plg-reconnect-btn" onclick="event.stopPropagation();connectPlugin('${id}')" title="Connect">Connect</button>` : ''}
        </div>
      </div>
    </div>`;
  }

  if(item._source === 'mcp'){
    const s = item._data;
    const statusCls = s.running ? 'running' : 'stopped';
    const statusTxt = s.running ? 'Running' : (s.enabled ? 'Starting...' : 'Disabled');

    // Zapier: universal connector — connect via pasted MCP URL, not a toggle.
    if(s.connector === 'zapier'){
      const connected = !!s.connected;
      const headerAction = connected
        ? `<span class="plg-header-connected">Connected</span>`
        : `<button class="plg-header-connect" onclick="event.stopPropagation();connectZapier()" title="Connect">Connect</button>`;
      const zStatus = s.running ? 'Running' : (connected ? 'Starting...' : 'Not connected');
      return `
      <div class="plg-accordion" data-mcp-id="${id}">
        <div class="plg-accordion-header" onclick="togglePluginAccordion(this)">
          <span class="plg-accordion-arrow">▶</span>
          <span class="plg-emoji">⚡</span>
          <span class="plg-title">Zapier</span>
          <span class="mcp-status ${statusCls}">${zStatus}</span> ${typeBadge}
          <div class="plg-header-right">${headerAction}</div>
        </div>
        <div class="plg-accordion-body">
          <div class="plg-body-desc">Universal connector — one link unlocks 8,000+ apps via Zapier MCP.</div>
          <div class="plg-body-meta">
            <span class="mcp-tool-count">${s.running ? (s.tool_count||0)+' tools' : (connected ? 'Waiting...' : 'Paste your Zapier MCP URL')}</span>
            ${connected ? `<button class="plg-disconnect-btn" onclick="event.stopPropagation();disconnectZapier()" title="Disconnect">Disconnect</button>` : ''}
          </div>
        </div>
      </div>`;
    }

    // Composio: universal connector — connect via pasted MCP URL, not a toggle.
    if(s.connector === 'composio'){
      const connected = !!s.connected;
      const headerAction = connected
        ? `<span class="plg-header-connected">Connected</span>`
        : `<button class="plg-header-connect" onclick="event.stopPropagation();connectComposio()" title="Connect">Connect</button>`;
      const cStatus = s.running ? 'Running' : (connected ? 'Starting...' : 'Not connected');
      return `
      <div class="plg-accordion" data-mcp-id="${id}">
        <div class="plg-accordion-header" onclick="togglePluginAccordion(this)">
          <span class="plg-accordion-arrow">▶</span>
          <span class="plg-emoji">🔗</span>
          <span class="plg-title">Composio</span>
          <span class="mcp-status ${statusCls}">${cStatus}</span> ${typeBadge}
          <div class="plg-header-right">${headerAction}</div>
        </div>
        <div class="plg-accordion-body">
          <div class="plg-body-desc">Universal connector — one link unlocks 100+ apps with managed OAuth via Composio MCP.</div>
          <div class="plg-body-meta">
            <span class="mcp-tool-count">${s.running ? (s.tool_count||0)+' tools' : (connected ? 'Waiting...' : 'Paste your Composio MCP URL')}</span>
            ${connected ? `<button class="plg-disconnect-btn" onclick="event.stopPropagation();disconnectComposio()" title="Disconnect">Disconnect</button>` : ''}
          </div>
        </div>
      </div>`;
    }

    const toggle = `<button class="toggle-switch ${s.enabled?'on':''}"
      onclick="event.stopPropagation();toggleMcpServer('${id}',${!s.enabled})"
      title="${s.enabled?'Disable':'Enable'}"></button>`;

    // Setup button for MCP servers that need configuration
    let setupBtn = '';
    if(!s.running && s.enabled){
      setupBtn = `<button class="rp-setup-btn" onclick="event.stopPropagation();rpShowSetup('${id}')" title="Configure">⚙</button>`;
    }

    return `
    <div class="plg-accordion" data-mcp-id="${id}">
      <div class="plg-accordion-header" onclick="togglePluginAccordion(this)">
        <span class="plg-accordion-arrow">▶</span>
        <span class="plg-emoji">${item.emoji}</span>
        <span class="plg-title">${name}</span>
        <span class="mcp-status ${statusCls}">${statusTxt}</span> ${typeBadge} ${updateBadge}
        <div class="plg-header-right">${setupBtn} ${toggle}</div>
      </div>
      <div class="plg-accordion-body">
        <div class="plg-body-desc">${escHtml(item.description)}</div>
        <div class="plg-body-meta">
          <span class="mcp-tool-count">${s.running ? (s.tool_count||0)+' tools' : (s.enabled ? 'Waiting...' : 'Toggle to enable')}</span>
        </div>
      </div>
    </div>`;
  }

  // Detected skill (from .skills/ folder)
  if(item._source === 'skill'){
    const s = item._data;
    const kwHtml = (item.keywords || []).slice(0, 5).map(k =>
      `<span class="rp-keyword">${escHtml(k)}</span>`
    ).join('');
    return `
    <div class="rp-card" data-skill-name="${id}">
      <div class="rp-card-header">
        <div class="rp-card-info">
          <span class="rp-card-name">📜 ${name}</span>
          ${typeBadge}
        </div>
        <div class="rp-card-action">
          <span class="rp-installed-badge">✓ Detected</span>
        </div>
      </div>
      ${item.description ? `<div class="rp-card-desc">${escHtml(item.description.substring(0,140))}</div>` : ''}
      <div class="rp-card-footer">
        <div class="rp-keywords">${kwHtml}</div>
      </div>
    </div>`;
  }

  // Installed marketplace package
  const p = item._data;
  return `
  <div class="rp-card" data-pkg-id="${id}">
    <div class="rp-card-header">
      <div class="rp-card-info">
        <span class="rp-card-name">${name}</span>
        ${typeBadge}
        ${item.version ? `<span class="rp-version">v${escHtml(item.version)}</span>` : ''}
        ${updateBadge}
      </div>
      <div class="rp-card-action">
        <button class="rp-uninstall-btn" onclick="event.stopPropagation();rpUninstall('${id}',this)">Uninstall</button>
      </div>
    </div>
    ${item.description ? `<div class="rp-card-desc">${escHtml(item.description.substring(0,120))}</div>` : ''}
    <div class="rp-card-footer">
      ${item.author ? `<span class="rp-author">by ${escHtml(item.author)}</span>` : ''}
    </div>
  </div>`;
}

// ═══════════════════════════════════════════════════════════════════════════════
// BROWSE TAB — marketplace catalog
// ═══════════════════════════════════════════════════════════════════════════════

function loadPackageCatalog(forceRefresh){
  const container = document.getElementById('rp-list');
  if(!container) return;
  container.innerHTML = '<div class="sb-empty rp-loading">Loading catalog...</div>';

  const params = new URLSearchParams();
  if(_rpQuery) params.set('q', _rpQuery);
  if(_rpType) params.set('type', _rpType);
  params.set('limit', '50');

  let url = '/packages/catalog?' + params.toString();
  if(forceRefresh){
    fetch('/packages/catalog/refresh', {method:'POST', headers:{'x-csrf-token':_rpCsrfToken()}})
      .finally(()=> _fetchCatalog(url, container));
  } else {
    _fetchCatalog(url, container);
  }
}

function _fetchCatalog(url, container){
  fetch(url).then(r=>r.json()).then(data=>{
    if(!data.ok){
      container.innerHTML = '<div class="sb-empty">Failed to load catalog</div>';
      return;
    }
    _rpCatalog = data.packages || [];
    renderCatalog(container);
  }).catch(()=>{
    container.innerHTML = '<div class="sb-empty">Catalog unavailable (offline?)</div>';
  });
}

function renderCatalog(container){
  if(!container) container = document.getElementById('rp-list');
  if(!container) return;

  const pkgs = _rpCatalog;
  if(!pkgs.length){
    container.innerHTML = _rpQuery || _rpType
      ? '<div class="sb-empty">No packages match your search</div>'
      : '<div class="sb-empty">Catalog is empty — add packages or connect a source</div>';
    return;
  }

  container.innerHTML = pkgs.map(p => _renderBrowseCard(p)).join('');
}

function _renderBrowseCard(pkg){
  const id = escHtml(pkg.id || '');
  const name = escHtml(pkg.name || pkg.id || 'Untitled');
  const desc = escHtml((pkg.description || '').substring(0, 120));
  const type = (pkg.type || 'skill').toLowerCase();
  const version = escHtml(pkg.version || '');
  const author = escHtml(pkg.author || '');
  const installed = pkg.installed;
  const hasSetup = pkg.setup && pkg.setup.type && pkg.setup.type !== 'none';

  const typeEmoji = type === 'mcp' ? '🔌' : type === 'plugin' ? '🧩' : '📦';
  const typeBadge = `<span class="rp-type-badge rp-type-${type}">${typeEmoji} ${type}</span>`;

  let action = '';
  if(installed){
    action = `<span class="rp-installed-badge">✓ Installed</span>`;
    if(hasSetup){
      action += ` <button class="rp-setup-btn-sm" onclick="event.stopPropagation();rpShowSetup('${id}')" title="Configure">⚙</button>`;
    }
  } else {
    action = `<button class="rp-install-btn" onclick="event.stopPropagation();rpInstallWithSetup('${id}',this)">Install</button>`;
  }

  // Setup indicator
  const setupHint = hasSetup ? `<span class="rp-setup-hint">${pkg.setup.type === 'api_key' ? '🔑 API key required' : pkg.setup.type === 'oauth' ? '🔐 OAuth login required' : pkg.setup.type === 'extension' ? '🧩 Extension required' : ''}</span>` : '';

  const kwHtml = (pkg.keywords || []).slice(0, 4).map(k =>
    `<span class="rp-keyword">${escHtml(k)}</span>`
  ).join('');

  return `
  <div class="rp-card" data-pkg-id="${id}">
    <div class="rp-card-header">
      <div class="rp-card-info">
        <span class="rp-card-name">${name}</span>
        ${typeBadge}
        ${version ? `<span class="rp-version">v${version}</span>` : ''}
      </div>
      <div class="rp-card-action">${action}</div>
    </div>
    ${desc ? `<div class="rp-card-desc">${desc}</div>` : ''}
    <div class="rp-card-footer">
      ${author ? `<span class="rp-author">by ${author}</span>` : ''}
      ${setupHint}
      <div class="rp-keywords">${kwHtml}</div>
    </div>
  </div>`;
}

// ═══════════════════════════════════════════════════════════════════════════════
// SETUP WIZARD — configure API keys, OAuth, etc.
// ═══════════════════════════════════════════════════════════════════════════════

function rpShowSetup(pkgId){
  fetch('/packages/setup/' + pkgId)
    .then(r => r.json())
    .then(data => {
      if(!data.ok || !data.setup){
        alert('No setup required for this package.');
        return;
      }
      _rpRenderSetupModal(pkgId, data.setup);
    })
    .catch(() => {
      alert('Could not load setup info.');
    });
}

function _rpRenderSetupModal(pkgId, setup){
  // Remove existing modal
  const old = document.getElementById('rp-setup-modal');
  if(old) old.remove();

  let bodyHtml = '';

  if(setup.type === 'api_key' && setup.env_vars){
    bodyHtml = setup.env_vars.map(ev => `
      <div class="rp-setup-field">
        <label>${escHtml(ev.label || ev.key)}</label>
        ${ev.help_url ? `<a href="${escHtml(ev.help_url)}" target="_blank" class="rp-setup-help">Get your key →</a>` : ''}
        <input type="text" class="rp-setup-input" data-key="${escHtml(ev.key)}"
               placeholder="${escHtml(ev.placeholder || '')}" autocomplete="off" spellcheck="false">
      </div>
    `).join('');
  } else if(setup.type === 'oauth'){
    bodyHtml = `
      <div class="rp-setup-oauth">
        <p>${escHtml(setup.instructions || 'OAuth login is required for this package.')}</p>
        <button class="rp-setup-oauth-btn" onclick="rpStartOAuth('${escHtml(pkgId)}')">Sign In</button>
      </div>
    `;
  } else if(setup.type === 'extension'){
    bodyHtml = `
      <div class="rp-setup-ext">
        <p>${escHtml(setup.instructions || 'This package requires a browser extension.')}</p>
      </div>
    `;
  } else {
    bodyHtml = '<p>No additional configuration needed.</p>';
  }

  const modal = document.createElement('div');
  modal.id = 'rp-setup-modal';
  modal.className = 'rp-modal-overlay';
  modal.innerHTML = `
    <div class="rp-modal">
      <div class="rp-modal-header">
        <h3>Configure: ${escHtml(pkgId)}</h3>
        <button class="rp-modal-close" onclick="rpCloseSetup()">×</button>
      </div>
      <div class="rp-modal-body">
        ${bodyHtml}
      </div>
      ${setup.type === 'api_key' ? `
      <div class="rp-modal-footer">
        <button class="rp-modal-save" onclick="rpSaveSetup('${escHtml(pkgId)}')">Save & Restart</button>
      </div>` : ''}
    </div>
  `;

  document.body.appendChild(modal);

  // Close on background click
  modal.addEventListener('click', (e) => {
    if(e.target === modal) rpCloseSetup();
  });
}

function rpCloseSetup(){
  const modal = document.getElementById('rp-setup-modal');
  if(modal) modal.remove();
}

function rpSaveSetup(pkgId){
  const inputs = document.querySelectorAll('#rp-setup-modal .rp-setup-input');
  const env_vars = {};
  inputs.forEach(inp => {
    const key = inp.dataset.key;
    const val = inp.value.trim();
    if(key && val) env_vars[key] = val;
  });

  if(!Object.keys(env_vars).length){
    alert('Please fill in at least one field.');
    return;
  }

  const btn = document.querySelector('#rp-setup-modal .rp-modal-save');
  if(btn){ btn.disabled = true; btn.textContent = 'Saving...'; }

  fetch('/packages/configure', {
    method: 'POST',
    headers: _rpHeaders(),
    body: JSON.stringify({ package_id: pkgId, env_vars })
  }).then(r => r.json()).then(d => {
    if(d.ok !== false && !d.detail){
      rpCloseSetup();
      // Refresh installed list to show new status
      setTimeout(() => loadInstalledPackages(), 1500);
    } else {
      alert('Failed: ' + (d.detail || 'Unknown error'));
      if(btn){ btn.disabled = false; btn.textContent = 'Save & Restart'; }
    }
  }).catch(e => {
    alert('Failed: ' + e.message);
    if(btn){ btn.disabled = false; btn.textContent = 'Save & Restart'; }
  });
}

function rpStartOAuth(pkgId){
  // Open OAuth connect window (reuses plugin connect flow)
  const w = 500, h = 600;
  const left = (screen.width - w) / 2, top = (screen.height - h) / 2;
  window.open('/plugins/' + pkgId + '/connect', 'rapr-connect',
    `width=${w},height=${h},left=${left},top=${top},toolbar=no,menubar=no`);
}

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
