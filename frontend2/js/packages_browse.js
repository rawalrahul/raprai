// packages_browse.js — The Browse tab (marketplace catalog) and the setup wizard for API keys and sign-ins.

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
