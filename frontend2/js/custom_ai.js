// ─────────────────────────────────────────────────────────────────────────────
// Custom AI Integration Management (Settings UI)
// ─────────────────────────────────────────────────────────────────────────────

function loadCustomAIs(){
  const container = document.getElementById('custom-ai-list');
  if(!container) return;
  fetch('/integrations/custom').then(r=>r.json()).then(data=>{
    if(!data.ok) return;
    const entries = data.integrations || [];
    if(!entries.length){
      container.innerHTML = '';
      return;
    }
    container.innerHTML = '<div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-bottom:4px">Custom AIs</div>' +
      entries.map(e => {
        return `<div class="ai-int-row" style="position:relative">
          <span style="width:8px;height:8px;border-radius:50%;background:${escHtml(e.color)};flex-shrink:0"></span>
          <span class="ai-int-name">${escHtml(e.emoji)} ${escHtml(e.name)}</span>
          <span style="font-size:10px;color:var(--dim);font-family:monospace">${escHtml(e.key)}</span>
          <div style="display:flex;gap:4px;margin-left:auto">
            <button class="ai-int-rescan-btn" onclick="removeCustomAI('${escHtml(e.key)}')" style="color:#ef4444;border-color:#ef4444" title="Remove">✕</button>
          </div>
        </div>`;
      }).join('');
  }).catch(()=>{});
}

function addCustomAI(){
  const key = (document.getElementById('cai-key')?.value || '').trim().toLowerCase();
  const name = (document.getElementById('cai-name')?.value || '').trim();
  const emoji = (document.getElementById('cai-emoji')?.value || '🤖').trim();
  const color = (document.getElementById('cai-color')?.value || '#6b7280').trim();
  const command = (document.getElementById('cai-cmd')?.value || '').trim();
  const envVarsStr = (document.getElementById('cai-envvars')?.value || '').trim();
  const hint = (document.getElementById('cai-hint')?.value || '').trim();
  const stdin = document.getElementById('cai-stdin')?.checked || false;

  if(!key || !name || !command){
    alert('Key, Name, and Command are required');
    return;
  }

  const envVars = envVarsStr ? envVarsStr.split(',').map(s => s.trim()).filter(Boolean) : [];

  fetch('/integrations/custom', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      key, name, emoji, color, command,
      env_vars: envVars,
      setup_hint: hint,
      stdin_prompt: stdin,
    })
  }).then(r=>r.json()).then(d=>{
    if(d.ok){
      // Clear form
      ['cai-key','cai-name','cai-cmd','cai-envvars','cai-hint'].forEach(id=>{
        const el = document.getElementById(id);
        if(el) el.value = '';
      });
      document.getElementById('cai-emoji').value = '🤖';
      document.getElementById('cai-stdin').checked = false;
      // Refresh lists
      loadCustomAIs();
      loadIntegrations(); // Refresh AI menu
      loadIntegrationStatus(); // Refresh detection list
    } else {
      alert(d.error || 'Failed to add integration');
    }
  }).catch(e => alert('Failed: ' + e.message));
}

function removeCustomAI(key){
  if(!confirm('Remove custom AI "' + key + '"? This will remove it from the UI.')) return;
  fetch('/integrations/custom/' + key, {method: 'DELETE'})
    .then(r=>r.json()).then(d=>{
      if(d.ok){
        loadCustomAIs();
        // Note: removed integration stays in AI menu until page refresh
        // since dynamic button injection is additive. That's fine.
      } else {
        alert('Failed to remove');
      }
    }).catch(e => alert('Failed: ' + e.message));
}
