// packages_installed.js — The Installed tab: plugins, MCP servers, skills and packages in one list.
// Shared state lives in packages.js, which loads first.

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
      if(q && !(s.id||'').toLowerCase().includes(q) && !(s.label||'').toLowerCase().includes(q)) return;
      items.push({_source:'mcp', _data:s, name:s.label || s.id.replace(/_/g,' '), id:s.id, type:'mcp',
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

  _rpScheduleCustomPoll();

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

    // Added by the user (any MCP server): sign-in state, reconnect, remove.
    if(s.custom){
      let cStatus, cCls = statusCls;
      if(s.running) cStatus = 'Running';
      else if(s.connecting) cStatus = s.auth_url ? 'Sign in' : 'Connecting...';
      else if(!s.enabled) cStatus = 'Disabled';
      else { cStatus = 'Not connected'; cCls = 'stopped'; }
      const where = s.transport === 'local' ? escHtml(s.command || 'local command') : escHtml(s.host || 'remote server');
      const authTxt = {oauth:'account sign-in', device:'sign-in code', bearer:'API key', headers:'custom headers', none:'no sign-in'}[s.auth] || '';
      const signin = (s.connecting && s.auth_url)
        ? `<a class="plg-header-connect" href="${escHtml(s.auth_url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()" title="${s.auth_code ? 'Code: '+escHtml(s.auth_code) : 'Open sign-in page'}">Sign in</a>`
        : '';
      const reconnectLbl = (s.auth === 'oauth' || s.auth === 'device') ? 'Sign in again' : 'Reconnect';
      return `
      <div class="plg-accordion" data-mcp-id="${id}">
        <div class="plg-accordion-header" onclick="togglePluginAccordion(this)">
          <span class="plg-accordion-arrow">▶</span>
          <span class="plg-emoji">🔌</span>
          <span class="plg-title">${name}</span>
          <span class="mcp-status ${cCls}">${cStatus}</span> ${typeBadge}
          <div class="plg-header-right">${signin} ${toggle}</div>
        </div>
        <div class="plg-accordion-body">
          <div class="plg-body-desc">${where}${authTxt ? ' · '+authTxt : ''}${s.running ? '<br>'+escHtml(s.summary||'') : ''}</div>
          ${s.auth_code && s.connecting ? `<div class="plg-body-desc">Sign-in code: <b>${escHtml(s.auth_code)}</b></div>` : ''}
          ${s.error ? `<div class="plg-body-desc" style="color:var(--red,#f87171);white-space:pre-wrap">${escHtml(s.error)}</div>` : ''}
          <div class="plg-body-meta">
            <span class="mcp-tool-count">${s.running ? (s.tool_count||0)+' tools' : ''}</span>
            <button class="plg-reconnect-btn" onclick="event.stopPropagation();reconnectCustomMcp('${id}')">${reconnectLbl}</button>
            <button class="plg-disconnect-btn" onclick="event.stopPropagation();removeCustomMcp('${id}')">Remove</button>
          </div>
        </div>
      </div>`;
    }

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
