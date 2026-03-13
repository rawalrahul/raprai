// ─────────────────────────────────────────────────────────────────────────────
// Cloud Backup — Settings UI logic
// ─────────────────────────────────────────────────────────────────────────────

let _backupConfig = {};

// Listen for OAuth callback from popup
window.addEventListener('message', function(e){
  if(e.data && e.data.type === 'backup-oauth-done'){
    loadBackupConfig();
  }
});

function loadBackupConfig(){
  fetch('/backups/config').then(r=>r.json()).then(cfg=>{
    _backupConfig = cfg;

    // Update each provider card
    ['onedrive','gdrive','dropbox','local'].forEach(p=>{
      const pc = cfg[p] || {};
      const enableEl = document.getElementById('bk-'+p+'-enabled');
      if(enableEl) enableEl.checked = !!pc.enabled;

      const folderEl = document.getElementById('bk-'+p+'-folder');
      if(folderEl) folderEl.value = pc.remote_folder || '';

      const statusEl = document.getElementById('bk-'+p+'-status');
      if(statusEl){
        if(pc.last_backup_at){
          statusEl.textContent = 'Last backup: ' + new Date(pc.last_backup_at).toLocaleString();
        } else {
          statusEl.textContent = 'No backups yet';
        }
      }

      // Update connect button
      const connectBtn = document.getElementById('bk-'+p+'-connect');
      if(connectBtn){
        if(pc.connected){
          connectBtn.textContent = 'Disconnect';
          connectBtn.onclick = function(){ disconnectBackupProvider(p); };
          connectBtn.classList.add('connected');
        } else {
          connectBtn.textContent = 'Connect';
          connectBtn.onclick = function(){ connectBackupProvider(p); };
          connectBtn.classList.remove('connected');
        }
      }

      // Show/hide fields
      _toggleBackupFields(p);
    });

    // Schedule settings
    const freqEl = document.getElementById('bk-frequency');
    // Use first enabled provider's frequency, or default
    for(const p of ['onedrive','gdrive','dropbox','local']){
      if(cfg[p] && cfg[p].frequency){
        if(freqEl) freqEl.value = cfg[p].frequency;
        const hourEl = document.getElementById('bk-hour');
        if(hourEl) hourEl.value = cfg[p].scheduled_hour || 2;
        break;
      }
    }

    loadBackupJobs();
  }).catch(()=>{});
}

function _toggleBackupFields(provider){
  const enableEl = document.getElementById('bk-'+provider+'-enabled');
  const fieldsEl = document.getElementById('bk-'+provider+'-fields');
  if(fieldsEl && enableEl){
    fieldsEl.style.display = enableEl.checked ? 'block' : 'none';
  }
}

function toggleBackupProvider(provider){
  _toggleBackupFields(provider);
}

function connectBackupProvider(provider){
  const url = '/backups/providers/'+provider+'/connect';
  const w = 550, h = 650;
  const left = (screen.width - w) / 2, top = (screen.height - h) / 2;
  window.open(url, 'rapr-backup-connect',
    'width='+w+',height='+h+',left='+left+',top='+top+',toolbar=no,menubar=no');
}

function disconnectBackupProvider(provider){
  if(!confirm('Disconnect '+provider+'? Stored tokens will be removed.')) return;
  fetch('/backups/providers/'+provider+'/disconnect',{method:'POST'})
    .then(r=>r.json()).then(d=>{
      if(d.ok) loadBackupConfig();
      else alert('Error: '+(d.error||'Unknown'));
    }).catch(e=>alert('Failed: '+e.message));
}

function saveBackupConfig(){
  const freq = document.getElementById('bk-frequency')?.value || 'daily';
  const hour = parseInt(document.getElementById('bk-hour')?.value || '2', 10);

  const promises = ['onedrive','gdrive','dropbox','local'].map(p=>{
    const enabled = document.getElementById('bk-'+p+'-enabled')?.checked || false;
    const folder = document.getElementById('bk-'+p+'-folder')?.value || '';

    return fetch('/backups/config/'+p, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        enabled: enabled,
        frequency: freq,
        scheduled_hour: hour,
        remote_folder: folder
      })
    });
  });

  Promise.all(promises).then(()=>{
    const msg = document.getElementById('bk-save-msg');
    if(msg){ msg.textContent = 'Saved!'; setTimeout(()=>{msg.textContent='';}, 2000); }
  }).catch(()=> alert('Failed to save backup config'));
}

async function triggerBackupNow(){
  const btn = document.getElementById('bk-now-btn');
  if(btn){ btn.disabled = true; btn.textContent = 'Backing up...'; }

  try {
    const res = await fetch('/backups/now', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({})
    });
    const data = await res.json();
    if(data.ok){
      const results = (data.results||[]).map(r=>
        r.provider + ': ' + (r.ok ? 'Success' : r.error)
      ).join('\n');
      alert('Backup complete!\n\n' + results);
      setTimeout(loadBackupJobs, 500);
    } else {
      alert('Backup failed: ' + (data.error || 'Unknown error'));
    }
  } catch(e){
    alert('Backup failed: ' + e.message);
  } finally {
    if(btn){ btn.disabled = false; btn.textContent = 'Backup Now'; }
  }
}

function loadBackupJobs(){
  fetch('/backups/jobs?limit=10').then(r=>r.json()).then(data=>{
    const list = document.getElementById('bk-jobs-list');
    if(!list) return;
    const jobs = data.jobs || [];
    if(!jobs.length){
      list.innerHTML = '<div style="color:var(--muted);font-style:italic">No backups yet</div>';
      return;
    }
    list.innerHTML = jobs.map(j=>{
      const icon = j.status === 'completed' ? '✓' : j.status === 'failed' ? '✗' : '⏳';
      const cls = j.status === 'completed' ? 'bk-job-ok' : j.status === 'failed' ? 'bk-job-fail' : 'bk-job-pending';
      const date = new Date(j.completed_at || j.started_at).toLocaleString();
      const size = j.backup_size ? (j.backup_size / 1048576).toFixed(1) + ' MB' : '—';
      const type = j.job_type === 'auto' ? '⏰' : '👤';
      return '<div class="bk-job '+cls+'">'
        + '<span>'+icon+' '+type+' '+escHtml(j.provider)+' — '+date+'</span>'
        + '<span>'+size+'</span>'
        + (j.error_message ? '<div class="bk-job-err">'+escHtml(j.error_message)+'</div>' : '')
        + '</div>';
    }).join('');
  }).catch(()=>{});
}
