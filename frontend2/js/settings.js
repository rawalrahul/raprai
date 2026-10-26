// The web UI's main script, part 6 of 8. index.html loads the parts in order.
// --- Settings panel --------------------------------------------------------------------------------------------

function openAiCatalog(){
  openSettings();
  setTimeout(() => {
    const el = document.getElementById('ai-int-list');
    if(el) el.scrollIntoView({behavior:'smooth', block:'start'});
  }, 150);
}

function openSettings(){
  const m = document.getElementById('settings-modal');
  m.style.display = 'flex';
  // Render context window inputs immediately — no fetch needed
  const ctxContainer = document.getElementById('ctx-window-inputs');
  if(ctxContainer && !ctxContainer.querySelector('input')){
    while(ctxContainer.firstChild) ctxContainer.removeChild(ctxContainer.firstChild);
    for(const key of Object.keys(_CTX_DEFAULTS)){
      _appendCtxRow(ctxContainer, key, _CTX_LABELS[key]||key, _CTX_EMOJI[key]||'🤖', null);
    }
  }
  loadSettings();
  loadIntegrationStatus();
  loadCustomAIs();
  loadBudget();
  loadDefaultModels();
  loadPersonalization();
  if(typeof loadBackupConfig === 'function') loadBackupConfig();
}

function closeSettings(){
  document.getElementById('settings-modal').style.display = 'none';
  // collapse PIN sub-form
  document.getElementById('st-pin-sub').classList.remove('open');
  document.getElementById('st-pin-new').value = '';
  document.getElementById('st-pin-confirm').value = '';
  document.getElementById('st-pin-err').style.display = 'none';
}

const _PROVIDER_API_KEY_SETTINGS = ['GROQ_API_KEY', 'OPENROUTER_API_KEY', 'GITHUB_TOKEN'];

function _setProviderApiKeyStatus(key, item){
  const statusEl = document.getElementById('st-' + key + '-status');
  const inputEl = document.getElementById('st-' + key);
  if(inputEl) inputEl.value = '';
  if(!statusEl) return;
  if(item && item.configured){
    statusEl.textContent = 'Saved securely' + (item.preview ? ` (${item.preview})` : '');
    statusEl.style.color = 'var(--accent)';
  } else {
    statusEl.textContent = 'Not configured';
    statusEl.style.color = 'var(--muted)';
  }
}

function loadProviderApiKeyStatus(){
  return fetch('/settings/api-keys')
    .then(r=>r.json())
    .then(d=>{
      _PROVIDER_API_KEY_SETTINGS.forEach(k=>_setProviderApiKeyStatus(k, d[k]));
    })
    .catch(()=>{});
}

function saveProviderApiKeys(){
  const saves = [];
  _PROVIDER_API_KEY_SETTINGS.forEach(k=>{
    const el = document.getElementById('st-' + k);
    const value = el ? el.value.trim() : '';
    if(!value) return;
    saves.push(
      fetch('/settings/api-keys', {
        method: 'POST',
        headers: {'Content-Type':'application/json','x-csrf-token':_csrfToken()},
        body: JSON.stringify({env_key: k, value})
      }).then(r=>{
        if(!r.ok) throw new Error('Failed to save ' + k);
        return r.json();
      })
    );
  });
  return Promise.all(saves);
}

// Known context window defaults per AI key (tokens)
const _CTX_DEFAULTS = {
  claude: 1000000, gemini: 1000000, antigravity: 1000000, codex: 1000000, openai: 1000000,
  openclaw: 1000000, opencode: 1000000,
  ollama: 128000, openrouter: 128000, groq: 131072, local_ai: 128000
};

// Display names/emojis for known AIs (used when integrations haven't loaded yet)
const _CTX_LABELS = {
  claude:'Claude Code', gemini:'Gemini', antigravity:'Antigravity', codex:'Codex', openai:'OpenAI / GPT',
  openclaw:'OpenClaw', opencode:'OpenCode',
  ollama:'Ollama (local)', openrouter:'OpenRouter', groq:'Groq', local_ai:'Local AI'
};
const _CTX_EMOJI = {
  claude:'🤖', gemini:'✨', antigravity:'🪐', codex:'💻', openai:'🧠', openclaw:'🦞', opencode:'🖥️',
  ollama:'🦙', openrouter:'🔀', groq:'⚡', local_ai:'🏠'
};

function _fmtTokens(n){
  if(n >= 1000000) return (n/1000000).toFixed(n%1000000===0?0:1)+'M';
  if(n >= 1000) return Math.round(n/1000)+'K';
  return String(n);
}

function _appendCtxRow(container, aiKey, label, emoji, settingsData){
  const def = _CTX_DEFAULTS[aiKey] || 128000;
  const safeKey = aiKey.replace(/[^a-zA-Z0-9_]/g,'').toUpperCase();
  const envKey = 'CONTEXT_WINDOW_' + safeKey;
  if(document.getElementById('st-'+envKey)) return; // already rendered

  const row = document.createElement('div');
  row.className = 'settings-row';

  const lbl = document.createElement('label');
  lbl.textContent = (emoji||'🤖') + ' ' + label;
  const small = document.createElement('small');
  small.textContent = 'Default: ' + _fmtTokens(def);
  lbl.appendChild(small);

  const inp = document.createElement('input');
  inp.className = 'settings-input';
  inp.id = 'st-' + envKey;
  inp.type = 'number';
  inp.min = '1000';
  inp.step = '1000';
  inp.placeholder = String(def);
  inp.style.width = '120px';

  row.appendChild(lbl);
  row.appendChild(inp);
  container.appendChild(row);

  const savedVal = settingsData && settingsData[envKey];
  if(savedVal) inp.value = savedVal;
}

function loadSettings(){
  fetch('/settings').then(r=>r.json()).then(d=>{
    const keys = ['OUTPUT_IDLE_TIMEOUT','OUTPUT_MAX_WAIT','OUTPUT_NO_RESPONSE',
                  'CLAUDE_TIMEOUT','SESSION_DAYS','WEB_PORT','WEB_HOST',
                  'HEARTBEAT_ENABLED','HEARTBEAT_AI',
                  'AI_MAX_RETRIES','AI_AUTO_SWITCH',
                  'PIPELINE_PLANNER_AI','PIPELINE_MAX_PARALLEL','PIPELINE_AUTO_SUGGEST','PIPELINE_CONTEXT_THRESHOLD','TELEGRAM_KELVIN_STICKERS','CHAT_APPS_SYNC','KELVIN_KEEP_AWAKE','KELVIN_DESKTOP_PET','KELVIN_DESKTOP_SIZE','KELVIN_DAILY_CHECKIN','OUTWARD_ACTIONS','OUTWARD_WAIT_MINUTES',
                  'LOCAL_AI_URL','LOCAL_AI_MODEL',
                  'COMPUTER_USE','COMPUTER_USE_TIER2','OMNIPARSER_ENABLED'];
    keys.forEach(k=>{
      const el = document.getElementById('st-'+k);
      if(el && d[k] !== undefined && d[k] !== '') el.value = d[k];
    });
    // Heartbeat interval: stored as seconds, displayed as hours or minutes
    const hbVal = document.getElementById('st-HEARTBEAT_INTERVAL_VAL');
    const hbUnit = document.getElementById('st-HEARTBEAT_INTERVAL_UNIT');
    if(hbVal && hbUnit && d['HEARTBEAT_INTERVAL']){
      const secs = parseFloat(d['HEARTBEAT_INTERVAL']);
      if(secs < 3600){
        hbVal.value = Math.round(secs / 60);
        hbUnit.value = 'minutes';
      } else {
        hbVal.value = Math.round(secs / 3600);
        hbUnit.value = 'hours';
      }
    }
    const pinStatus = document.getElementById('st-pin-status');
    if(pinStatus) pinStatus.textContent = d.pin_is_set ? 'PIN is set' : 'No PIN configured';

    // Fill in any saved context-window overrides (rows already rendered by openSettings)
    const container = document.getElementById('ctx-window-inputs');
    if(container){
      for(const [k, v] of Object.entries(d)){
        if(!k.startsWith('CONTEXT_WINDOW_') || !v) continue;
        const inp = document.getElementById('st-'+k);
        if(inp) inp.value = v;
      }
    }

    // AI dropdowns (heartbeat + pipeline) — async, needs /integrations
    _populateAiDropdowns(d);
    loadProviderApiKeyStatus();
  }).catch(()=>{});
}

function _populateAiDropdowns(settingsData){
  fetch('/integrations').then(r=>r.json()).catch(()=>[]).then(intList=>{
    if(!Array.isArray(intList)) intList = [];   // e.g. a rate-limit error object
    // Build full AI list: claude built-in + all integrations
    const allAis = [{key:'claude', name:'Claude Code', emoji:'🤖'}];
    const seen = new Set(['claude']);
    for(const int of (intList||[])){
      if(int.key && !seen.has(int.key)){
        allAis.push({key:int.key, name:int.name||int.key, emoji:int.emoji||'🤖'});
        seen.add(int.key);
      }
    }

    // Populate any <select> that should show all AIs
    const dropdownIds = ['st-HEARTBEAT_AI','st-PIPELINE_PLANNER_AI'];
    for(const id of dropdownIds){
      const sel = document.getElementById(id);
      if(!sel) continue;
      const curVal = sel.value;
      sel.innerHTML = '';
      for(const ai of allAis){
        const opt = document.createElement('option');
        opt.value = ai.key;
        opt.textContent = ai.emoji + ' ' + ai.name;
        sel.appendChild(opt);
      }
      const savedKey = id.replace('st-','');
      const saved = settingsData[savedKey] || curVal;
      if(saved) sel.value = saved;
    }

    // Append any extra AIs from integrations not already rendered in ctx-window-inputs
    const container = document.getElementById('ctx-window-inputs');
    if(container){
      for(const ai of allAis){
        if(!_CTX_DEFAULTS[ai.key]){
          _appendCtxRow(container, ai.key, ai.name, ai.emoji, settingsData);
        }
      }
    }
  });
}

function saveSettings(){
  const keys = ['OUTPUT_IDLE_TIMEOUT','OUTPUT_MAX_WAIT','OUTPUT_NO_RESPONSE',
                'CLAUDE_TIMEOUT','SESSION_DAYS','WEB_PORT','WEB_HOST',
                'HEARTBEAT_ENABLED','HEARTBEAT_AI',
                'AI_MAX_RETRIES','AI_AUTO_SWITCH',
                'PIPELINE_PLANNER_AI','PIPELINE_MAX_PARALLEL','PIPELINE_AUTO_SUGGEST','PIPELINE_CONTEXT_THRESHOLD','TELEGRAM_KELVIN_STICKERS','CHAT_APPS_SYNC','KELVIN_KEEP_AWAKE','KELVIN_DESKTOP_PET','KELVIN_DESKTOP_SIZE','KELVIN_DAILY_CHECKIN','OUTWARD_ACTIONS','OUTWARD_WAIT_MINUTES',
                'LOCAL_AI_URL','LOCAL_AI_MODEL',
                'COMPUTER_USE','COMPUTER_USE_TIER2','OMNIPARSER_ENABLED'];
  const body = {};
  keys.forEach(k=>{
    const el = document.getElementById('st-'+k);
    if(el && el.value.trim() !== '') body[k] = el.value.trim();
  });
  // Convert heartbeat value + unit → seconds for storage
  const hbVal = document.getElementById('st-HEARTBEAT_INTERVAL_VAL');
  const hbUnit = document.getElementById('st-HEARTBEAT_INTERVAL_UNIT');
  if(hbVal && hbVal.value.trim() !== ''){
    const multiplier = (hbUnit && hbUnit.value === 'minutes') ? 60 : 3600;
    body['HEARTBEAT_INTERVAL'] = String(parseFloat(hbVal.value) * multiplier);
  }
  // Collect all dynamically-rendered CONTEXT_WINDOW_* inputs
  document.querySelectorAll('[id^="st-CONTEXT_WINDOW_"]').forEach(el=>{
    if(el.value.trim()) body[el.id.replace('st-','')] = el.value.trim();
  });
  fetch('/settings',{method:'POST',headers:{'Content-Type':'application/json','x-csrf-token':_csrfToken()},body:JSON.stringify(body)})
    .then(r=>r.json())
    .then(()=>saveProviderApiKeys())
    .then(()=>{
      loadProviderApiKeyStatus();
      loadIntegrationStatus();
      loadDefaultModels();
      const msg = document.getElementById('st-msg');
      msg.textContent = 'Saved ✓';
      msg.classList.add('show');
      setTimeout(()=>msg.classList.remove('show'),2500);
    }).catch(()=>alert('Failed to save settings'));
}

// --- Default Models per AI -------------------------------------------------------------------------------------

const _CLI_ONLY_AIS = new Set(['claude','gemini','antigravity','codex']);

function loadDefaultModels(){
  const container = document.getElementById('default-models-container');
  if(!container) return;

  // Fetch both default models and available integrations in parallel
  Promise.all([
    fetch('/settings/default-models').then(r=>r.json()),
    fetch('/integrations').then(r=>r.json()),
    fetch('/integrations/models').then(r=>r.json()).catch(()=>({models:{}})),
  ]).then(([dmData, integrations, modelsData])=>{
    const defaults = dmData.default_models || {};
    const models = modelsData.models || {};

    // Build list of REST-API AIs (exclude CLI-only)
    const restAis = [];
    // Always include ollama
    restAis.push({key:'ollama', name:'Ollama', emoji:'🦙'});
    // Add any integration that isn't CLI-only
    integrations.forEach(intg=>{
      if(!_CLI_ONLY_AIS.has(intg.key) && intg.key !== 'ollama'){
        restAis.push({key:intg.key, name:intg.name, emoji:intg.emoji});
      }
    });

    if(restAis.length === 0){
      container.innerHTML = '<span style="color:var(--muted);font-size:11px">No REST-API AIs configured</span>';
      return;
    }

    let html = '';
    restAis.forEach(ai=>{
      const currentDefault = defaults[ai.key] || '';
      const aiModels = models[ai.key] || [];

      html += `<div class="settings-row" style="margin-bottom:6px">
        <label>${ai.emoji} ${ai.name} default model
          <small>Auto-loaded when starting a new ${ai.name} session</small>
        </label>
        <div style="display:flex;gap:4px;align-items:center;margin-top:4px">
          <input class="settings-input wide dm-model-input" type="text"
                 id="dm-${ai.key}" value="${currentDefault}"
                 placeholder="None (use AI default)" style="flex:1">`;

      // If we have available models, show a dropdown picker
      if(aiModels.length > 0){
        html += `<select class="settings-input dm-model-select" style="width:auto;max-width:180px"
                         onchange="document.getElementById('dm-${ai.key}').value=this.value">
          <option value="">— pick —</option>`;
        aiModels.forEach(m=>{
          const sel = m === currentDefault ? ' selected' : '';
          html += `<option value="${m}"${sel}>${m}</option>`;
        });
        html += `</select>`;
      }

      html += `</div></div>`;
    });

    html += `<div style="margin-top:8px">
      <button class="settings-pin-btn" onclick="saveDefaultModels()" style="padding:5px 14px">
        Save Default Models
      </button>
      <span id="dm-save-msg" style="color:#22c55e;font-size:11px;margin-left:8px;opacity:0;transition:opacity .3s"></span>
    </div>`;

    container.innerHTML = html;
  }).catch(()=>{
    container.innerHTML = '<span style="color:#ef4444;font-size:11px">Failed to load default models</span>';
  });
}

function saveDefaultModels(){
  const inputs = document.querySelectorAll('.dm-model-input');
  const body = {};
  inputs.forEach(el=>{
    const aiKey = el.id.replace('dm-','');
    body[aiKey] = el.value.trim();
  });

  fetch('/settings/default-models',{
    method:'POST',
    headers:{'Content-Type':'application/json','x-csrf-token':_csrfToken()},
    body:JSON.stringify(body),
  }).then(r=>r.json()).then(()=>{
    const msg = document.getElementById('dm-save-msg');
    if(msg){
      msg.textContent = 'Saved ✓';
      msg.style.opacity = '1';
      setTimeout(()=>{msg.style.opacity='0'},2500);
    }
  }).catch(()=>alert('Failed to save default models'));
}

// --- Approval banner (destructive action approvals via UI + Telegram) ---

let _currentApprovalId = null;  // tracks the active approval request shown in the banner

function showApprovalBanner(approval){
  _currentApprovalId = approval.id;
  const banner = document.getElementById('approval-banner');
  const msg = document.getElementById('approval-banner-msg');
  if(!banner||!msg) return;
  msg.textContent = approval.description || 'An action requires your approval';
  banner.style.display = 'flex';
}

function hideApprovalBanner(){
  const banner = document.getElementById('approval-banner');
  if(banner) banner.style.display = 'none';
  _currentApprovalId = null;
}

function resolveApproval(status){
  if(!_currentApprovalId) return;
  const reqId = _currentApprovalId;
  fetch(`/approval/${reqId}`,{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({status})
  }).then(r=>r.json()).then(d=>{
    if(d.ok) hideApprovalBanner();
  }).catch(()=>alert('Failed to resolve approval'));
}

function togglePinSub(){
  document.getElementById('st-pin-sub').classList.toggle('open');
}

// --- AI Integration status in Settings -----------------------------------------------------------------------

const _AI_INT_META = {
  claude: { name:'Claude Code', emoji:'🤖', hint:'Install: npm install -g @anthropic-ai/claude-code' },
  antigravity: { name:'Antigravity', emoji:'🪐', hint:'Install Antigravity CLI: see antigravity.google/docs/cli-using' },
  codex:  { name:'Codex CLI',   emoji:'🧠', hint:'Install: npm install -g @openai/codex' },
  ollama: { name:'Ollama',      emoji:'🦙', hint:'Download from https://ollama.com/download' },
};

function _renderIntegrationList(data){
  const list = document.getElementById('ai-int-list');
  if(!list) return;
  const items = data._items || Object.entries(_AI_INT_META).map(([key, meta]) => ({
    key, name: meta.name, emoji: meta.emoji,
    found: !!data[key],
    hint: !data[key] ? meta.hint : '',
    models: key === 'ollama' && Array.isArray(data.ollama_models) ? data.ollama_models : [],
  }));
  // Catalog: installed AIs first, each with what it is, how to install it and a way to start it.
  const sorted = items.slice().sort((x, y) => (y.found === true) - (x.found === true));
  const rows = sorted.map(item => {
    const found = item.found;
    const key = escHtml(item.key);
    const status = `<span class="ai-cat-status ${found ? 'ok' : ''}">${found ? '✓ Ready' : 'Not set up'}</span>`;
    const about = item.about ? `<div class="ai-cat-about">${escHtml(item.about)}</div>` : '';
    const acts = [];
    if(found && item.startable){
      acts.push(`<button class="ai-cat-btn primary" onclick="cmd('new_session:${key}');if(typeof closeSettings==='function')closeSettings()">▶ Start session</button>`);
    }
    if(found && Array.isArray(item.models) && item.models.length){
      acts.push(`<span class="ai-cat-note">${escHtml(item.models.join(', '))}</span>`);
    }
    if(!found && item.install){
      acts.push(`<code class="ai-cat-cmd">${escHtml(item.install)}</code><button class="ai-cat-btn" onclick="navigator.clipboard&&navigator.clipboard.writeText(this.previousElementSibling.textContent);this.textContent='Copied'">Copy</button>`);
    } else if(!found && item.hint && !item.docs){
      acts.push(`<span class="ai-cat-note">${escHtml(item.hint)}</span>`);
    }
    if(item.docs){
      acts.push(`<a class="ai-cat-link" href="${escHtml(item.docs)}" target="_blank" rel="noopener">${found ? 'Docs' : 'How to install'} ↗</a>`);
    }
    return `<div class="ai-int-row ai-cat-row">
      <span class="ai-int-dot ${found ? 'ok' : 'miss'}"></span>
      <div class="ai-cat-main">
        <div class="ai-cat-head"><span class="ai-int-name">${escHtml((item.emoji||'🤖')+' '+item.name)}</span>${status}</div>
        ${about}
        ${acts.length ? `<div class="ai-cat-actions">${acts.join('')}</div>` : ''}
      </div>
    </div>`;
  });
  list.innerHTML = rows.join('');
}

function loadIntegrationStatus(){
  const list = document.getElementById('ai-int-list');
  if(list) list.innerHTML = '<div style="font-size:12px;color:var(--muted);padding:4px 0">Scanning…</div>';
  fetch('/integrations/rescan').then(r=>r.json()).then(d=>{
    _renderIntegrationList(d);
  }).catch(()=>{
    if(list) list.innerHTML = '<div style="font-size:12px;color:#f87171;padding:4px 0">Failed to scan</div>';
  });
}

function rescanIntegrations(){
  const btn = document.getElementById('ai-int-rescan-btn');
  if(btn){ btn.disabled=true; btn.textContent='Scanning…'; }
  fetch('/integrations/rescan').then(r=>r.json()).then(d=>{
    _renderIntegrationList(d);
    if(btn){ btn.disabled=false; btn.textContent='⟳ Re-scan'; }
    // Also refresh the AI dropdown so newly-detected tools appear
    loadIntegrations();
  }).catch(()=>{
    if(btn){ btn.disabled=false; btn.textContent='⟳ Re-scan'; }
  });
}

function debugCli(name){
  // Show a modal with raw detection diagnostics so we can see exactly why
  // a CLI is not being found (which PATH step fails, what subprocess returns).
  fetch('/integrations/debug/' + name).then(r=>r.json()).then(d=>{
    const cands = Object.entries(d.candidates||{})
      .map(([k,v])=>`  ${v.exists?'✓':'✗'} ${k}: ${v.path}`)
      .join('\n');
    const probe = d.subprocess_probe || {};
    const probeText = probe.timed_out
      ? '  TIMED OUT (process is running — binary exists!)'
      : probe.error
        ? '  ERROR: ' + probe.error
        : `  returncode: ${probe.returncode}\n  stdout: ${probe.stdout||'(empty)'}\n  stderr: ${probe.stderr||'(empty)'}`;
    const msg =
`=== Detection report for: ${name} ===

STEP 1 — shutil.which:
  plain: ${d.which_plain||'null'}
  .cmd:  ${d.which_cmd||'null'}
  .exe:  ${d.which_exe||'null'}

STEP 2 — File-system candidates:
${cands}

STEP 3 — Subprocess probe (shell=True):
${probeText}

FINAL RESULT: ${d._find_cli_result ? '✓ FOUND' : '✗ NOT FOUND'}`;
    // Show in a styled overlay
    let ov = document.getElementById('debug-overlay');
    if(!ov){
      ov = document.createElement('div');
      ov.id = 'debug-overlay';
      ov.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:9999;display:flex;align-items:center;justify-content:center';
      ov.onclick = e => { if(e.target===ov) ov.remove(); };
      document.body.appendChild(ov);
    }
    ov.innerHTML = `<div style="background:#1a1a1a;border:1px solid #3a3a3a;border-radius:12px;padding:20px 24px;max-width:640px;width:92vw;max-height:80vh;overflow-y:auto">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
        <span style="font-size:14px;font-weight:600;color:#e5e7eb">🔍 Claude Detection Diagnostics</span>
        <button onclick="document.getElementById('debug-overlay').remove()" style="background:none;border:none;color:#9ca3af;font-size:18px;cursor:pointer">✖</button>
      </div>
      <pre style="font-size:11px;color:#d1d5db;white-space:pre-wrap;word-break:break-all;line-height:1.6;background:#111;border-radius:8px;padding:12px">${escHtml(msg)}</pre>
      <p style="font-size:11px;color:#6b7280;margin-top:10px">Copy this output and share it if you need help diagnosing the issue.</p>
    </div>`;
  }).catch(err=>{
    alert('Debug fetch failed: ' + err);
  });
}

// --- Plugin Management (Standalone section above Settings) --------------------

// Listen for OAuth callback messages from popup window
window.addEventListener('message', function(e){
  if(e.data && e.data.type === 'plugin-oauth-done') loadInstalledPackages();
});

// NOTE: Plugin/MCP panel functions (togglePlugin, connectPlugin, disconnectPlugin,
// toggleMcpServer, togglePluginAccordion, etc.) are now in packages.js
// as part of the unified RAPR Packages panel.

// --- Context Window Management -----------------------------------------------

function updateContextBar(sess){
  const bar = document.getElementById('context-bar');
  if(!bar) return;
  if(!sess || !sess.context || !sess.ai || sess.ai === 'shell'){
    bar.classList.add('hidden');
    return;
  }
  const ctx = sess.context;
  // Only show bar if there's meaningful context usage (>1%)
  if(ctx.pct < 1){
    bar.classList.add('hidden');
    return;
  }
  bar.classList.remove('hidden');
  const fill = document.getElementById('context-fill');
  const pctEl = document.getElementById('context-pct');
  const compactBtn = document.getElementById('context-compact-btn');
  fill.style.width = Math.min(100, ctx.pct) + '%';
  fill.className = 'context-progress-fill ' + ctx.status;
  pctEl.textContent = ctx.pct.toFixed(0) + '%';
  pctEl.className = 'context-pct ' + ctx.status;
  // Show compact button only when usage is notable (>30%)
  if(compactBtn){
    compactBtn.style.display = ctx.pct > 30 ? '' : 'none';
  }
}

function compactContext(){
  if(!_focusedId) return;
  const btn = document.getElementById('context-compact-btn');
  if(btn){btn.textContent = 'Compacting...';btn.disabled = true;}
  fetch('/context/' + _focusedId + '/compact', {method:'POST'})
    .then(r => r.json())
    .then(d => {
      if(btn){btn.textContent = 'Compact';btn.disabled = false;}
      // The state update from WebSocket will refresh the bar
    })
    .catch(() => {
      if(btn){btn.textContent = 'Compact';btn.disabled = false;}
    });
}

// --- PIN Management ----------------------------------------------------------

function saveNewPin(){
  const np = document.getElementById('st-pin-new').value;
  const cp = document.getElementById('st-pin-confirm').value;
  const errEl = document.getElementById('st-pin-err');
  errEl.style.display = 'none';
  if(!np){errEl.textContent='Enter a new PIN.';errEl.style.display='block';return;}
  if(np !== cp){errEl.textContent='PINs do not match.';errEl.style.display='block';return;}
  fetch('/auth/set-pin',{method:'POST',headers:{'Content-Type':'application/json','x-csrf-token':_csrfToken()},body:JSON.stringify({pin:np})})
    .then(r=>r.json())
    .then(d=>{
      if(d.ok){
        document.getElementById('st-pin-sub').classList.remove('open');
        document.getElementById('st-pin-new').value='';
        document.getElementById('st-pin-confirm').value='';
        document.getElementById('st-pin-status').textContent='PIN is set';
        const msg = document.getElementById('st-msg');
        msg.textContent = 'PIN updated ✓';
        msg.classList.add('show');
        setTimeout(()=>msg.classList.remove('show'),2500);
      } else {
        errEl.textContent = d.detail || 'Failed to set PIN.';
        errEl.style.display = 'block';
      }
    }).catch(()=>{errEl.textContent='Network error.';errEl.style.display='block';});
}

function confirmLogout(){
  if(!confirm('Log out of RAPR AI?')) return;
  fetch('/logout',{method:'POST',headers:{'x-csrf-token':_csrfToken()}}).then(()=>{ window.location.href='/login'; });
}

// --- Generated Files panel ------------------------------------------------------------------------------------
function loadGeneratedFiles(){
  const el = document.getElementById('gf-list');
  el.innerHTML = '<div class="sb-empty" style="opacity:.5">Loading...</div>';
  fetch('/generated-files').then(r=>r.json()).then(files=>{
    if(!files.length){ el.innerHTML='<div class="sb-empty">No generated files yet</div>'; return; }
    el.innerHTML='';
    const extIcons = {'.pdf':'📄','.pptx':'📊','.ppt':'📊','.docx':'📝','.doc':'📝',
      '.xlsx':'📈','.xls':'📈','.csv':'📈','.png':'🖼','.jpg':'🖼','.jpeg':'🖼','.webp':'🖼',
      '.mp4':'🎬','.mov':'🎬','.gif':'🎞','.html':'🌐','.htm':'🌐','.zip':'📦','.tar':'📦',
      '.gz':'📦','.txt':'📃','.md':'📃','.bmp':'🖼'};
    files.forEach(f=>{
      const icon = extIcons[f.ext] || '📎';
      const sizeKb = f.size ? Math.round(f.size/1024) : 0;
      const age = f.age < 60 ? 'just now' : f.age < 3600 ? Math.round(f.age/60)+'m ago' :
                  f.age < 86400 ? Math.round(f.age/3600)+'h ago' : Math.round(f.age/86400)+'d ago';
      const card = document.createElement('div');
      card.className = 'gf-card' + (f.exists ? '' : ' gf-missing');
      card.innerHTML = `<span class="gf-icon">${icon}</span>`+
        `<div class="gf-info">`+
          `<div class="gf-name" title="${f.path}">${f.name}</div>`+
          `<div class="gf-meta">`+
            `<span>${sizeKb} KB</span>`+
            `<span>${age}</span>`+
            (f.ai ? `<span class="gf-ai-badge">${f.ai}</span>` : '')+
            (f.session_name ? `<span>${f.session_name}</span>` : '')+
            (!f.exists ? '<span style="color:#f87171">deleted</span>' : '')+
          `</div>`+
        `</div>`+
        (f.exists ? `<a class="gf-dl" href="/files/${encodeURIComponent(f.name)}" target="_blank" title="Open / download">↓</a>` : '');
      el.appendChild(card);
    });
  }).catch(()=>{ el.innerHTML='<div class="sb-empty">Failed to load files</div>'; });
}

// --- Token Usage Dashboard ------------------------------------------------------------------------------------

function loadUsageDashboard(){
  const el = document.getElementById('usage-dashboard');
  if(!el) return;
  el.innerHTML = '<div class="sb-empty" style="opacity:.5">Loading...</div>';
  fetch('/api/usage').then(r=>r.json()).then(data=>{
    let html = '';
    // Period info
    html += `<div class="usage-period">Reset in: <strong>${data.reset_eta || '?'}</strong></div>`;
    // Per-AI cards
    const ais = data.ais || {};
    const aiKeys = Object.keys(ais);
    if(!aiKeys.length){
      html += '<div class="sb-empty">No usage recorded yet</div>';
    } else {
      aiKeys.forEach(key=>{
        const a = ais[key];
        const pct = a.pct_used != null ? a.pct_used : 0;
        const capText = a.cap_min ? `/ ${a.cap_min}m` : '';
        const src = (a.source||'').endsWith('_cli') ? 'CLI' : 'EST';
        const budgetOk = a.budget && a.budget.allowed !== false;
        const budgetWarn = a.budget && a.budget.warn;
        const barColor = !budgetOk ? '#ef4444' : budgetWarn ? '#f59e0b' : '';
        // Token display: prefer actual counts, fall back to estimate
        const tokSource = a.tokens_source || 'estimate';
        const isActual = tokSource === 'actual';
        const tokBadge = isActual ? 'ACTUAL' : 'EST';
        const tokBadgeClass = isActual ? 'usage-actual-badge' : 'usage-est-badge';
        const tokIn = a.tokens_in || 0;
        const tokOut = a.tokens_out || 0;
        const tokTotal = isActual ? (tokIn + tokOut) : (a.total_tokens || a.est_tokens || 0);
        const tokDetail = isActual
          ? `${tokIn.toLocaleString()} in / ${tokOut.toLocaleString()} out`
          : `~${tokTotal.toLocaleString()} (char÷4)`;
        html += `<div class="usage-ai-card${!budgetOk ? ' usage-blocked' : ''}">
          <div class="usage-ai-header">
            <span class="usage-ai-name">${a.label}</span>
            <span class="usage-ai-src">${src}</span>
          </div>
          <div class="usage-ai-stats">
            <span>${a.used_min.toFixed(1)}m ${capText}</span>
            <span>${a.tasks} task${a.tasks!==1?'s':''}</span>
          </div>
          <div class="usage-token-line">
            <span class="${tokBadgeClass}">${tokBadge}</span>
            <span>${tokTotal.toLocaleString()} tok</span>
            <span class="usage-tok-detail">${tokDetail}</span>
          </div>
          <div class="usage-bar-wrap">
            <div class="usage-bar-fill" style="width:${Math.min(100,pct)}%${barColor?';background:'+barColor:''}"></div>
          </div>
          <div class="usage-pct-line">
            <span>${a.pct_used != null ? a.pct_used.toFixed(1)+'%' : 'No cap'}</span>
            ${!budgetOk ? '<span class="usage-blocked-badge">BLOCKED</span>' : ''}
            ${budgetWarn && budgetOk ? '<span class="usage-warn-badge">WARNING</span>' : ''}
          </div>
        </div>`;
      });
    }
    // Per-session breakdown
    const sess = data.sessions || [];
    if(sess.length){
      html += '<div class="usage-section-title">Per-Session Breakdown</div>';
      sess.forEach(s=>{
        html += `<div class="usage-sess-row">
          <span class="usage-sess-name">${escHtml(s.name)}</span>
          <span>${s.task_count} tasks</span>
          <span>${s.total_min.toFixed(1)}m</span>
        </div>`;
      });
    }
    el.innerHTML = html;
  }).catch(()=>{ el.innerHTML='<div class="sb-empty">Failed to load usage data</div>'; });
}

// --- Budget controls ------------------------------------------------------------------------------------------

function loadBudget(){
  fetch('/api/budget').then(r=>r.json()).then(cfg=>{
    const en = document.getElementById('budget-enabled');
    if(en) en.value = cfg.enabled ? '1' : '0';
    ['claude','antigravity','codex','ollama'].forEach(ai=>{
      const inp = document.getElementById('budget-'+ai);
      if(inp && cfg[ai] && cfg[ai].daily_cap_min != null) inp.value = cfg[ai].daily_cap_min;
    });
    const wp = document.getElementById('budget-warn-pct');
    if(wp && cfg.claude && cfg.claude.warn_pct) wp.value = cfg.claude.warn_pct;
  }).catch(()=>{});
}

function saveBudget(){
  const body = {};
  const en = document.getElementById('budget-enabled');
  body.enabled = en && en.value === '1';
  const warnPct = parseFloat((document.getElementById('budget-warn-pct')||{}).value) || 80;
  ['claude','antigravity','codex','ollama'].forEach(ai=>{
    const inp = document.getElementById('budget-'+ai);
    const val = inp ? inp.value.trim() : '';
    body[ai] = {
      daily_cap_min: val ? parseFloat(val) : null,
      warn_pct: warnPct,
    };
  });
  fetch('/api/budget',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
    .then(r=>r.json())
    .then(()=>{
      const msg = document.getElementById('budget-msg');
      if(msg){ msg.textContent='Saved ✓'; setTimeout(()=>msg.textContent='',2000); }
    })
    .catch(()=>{
      const msg = document.getElementById('budget-msg');
      if(msg) msg.textContent='Error saving';
    });
}

// --- Personalization & Custom Instructions -------------------------------------------------------------------

function loadPersonalization(){
  fetch('/prefs').then(r=>r.json()).then(p=>{
    const un = document.getElementById('st-user-name');
    const an = document.getElementById('st-ai-name');
    const ci = document.getElementById('st-custom-instructions');
    if(un && p.user_name) un.value = p.user_name;
    if(an && p.ai_name)   an.value = p.ai_name;
    if(ci && p.custom_instructions) ci.value = p.custom_instructions;
  }).catch(()=>{});
}

function savePersonalization(){
  const userName = (document.getElementById('st-user-name')||{}).value || '';
  const aiName   = (document.getElementById('st-ai-name')||{}).value || '';
  const msg = document.getElementById('personalization-msg');
  fetch('/prefs',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({user_name: userName.trim(), ai_name: aiName.trim()})})
    .then(r=>r.json())
    .then(()=>{ if(msg){ msg.textContent='Saved ✓'; setTimeout(()=>msg.textContent='',2000); } })
    .catch(()=>{ if(msg) msg.textContent='Error saving'; });
}

function saveCustomInstructions(){
  const ci = (document.getElementById('st-custom-instructions')||{}).value || '';
  const msg = document.getElementById('custom-instr-msg');
  fetch('/prefs',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({custom_instructions: ci})})
    .then(r=>r.json())
    .then(()=>{ if(msg){ msg.textContent='Saved ✓'; setTimeout(()=>msg.textContent='',2000); } })
    .catch(()=>{ if(msg) msg.textContent='Error saving'; });
}

