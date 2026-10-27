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
  if(el) toggleSbSection(el.querySelector('.sb-section-header'));
}

function loadPackagesSection(){
  if(_rpTab === 'installed') loadInstalledPackages();
  else loadPackageCatalog();
  // Check for updates in background
  if(!_rpUpdateCheckDone) rpCheckUpdates();
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
