// frontend2/js/demos.js — Demos sidebar section

(function () {
  if (!document.getElementById('demos-styles')) {
    const s = document.createElement('style');
    s.id = 'demos-styles';
    s.textContent = `
.demos-card{border-bottom:1px solid var(--border,#333);padding:4px 10px}
.demos-card-header{display:flex;align-items:center;gap:6px;cursor:pointer;padding:2px 0}
.demos-title{flex:1;font-size:.85em;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.demos-badge{font-size:.72em;border-radius:10px;padding:1px 6px;white-space:nowrap}
.demos-badge-ready{background:#2d5a3d;color:#7affaa}
.demos-badge-analyzing,.demos-badge-uploading{background:#3d3d2d;color:#ffd07a}
.demos-badge-error{background:#5a2d2d;color:#ff7a7a}
.demos-dur{font-size:.72em;color:var(--text-muted,#888)}
.demos-card-actions{display:flex;gap:4px;margin:2px 0 4px}
.demos-btn{padding:2px 8px;border-radius:4px;border:1px solid var(--border,#333);background:var(--surface2,#1e1e2e);cursor:pointer;font-size:.75em;color:var(--text,#ccc)}
.demos-btn:hover:not(:disabled){opacity:.8}
.demos-btn:disabled{opacity:.4;cursor:default}
.demos-btn-del:hover:not(:disabled){background:#5a2d2d;border-color:#9a4a4a}
.demos-actions-container{padding:4px 0}
.demos-action-row{display:grid;grid-template-columns:22px 42px 90px 1fr;gap:3px;padding:2px 2px;font-size:.76em;border-bottom:1px solid var(--border,#333)}
.demos-action-step{color:var(--text-muted,#888);text-align:right}
.demos-action-ts{color:var(--text-muted,#888)}
.demos-action-type{color:var(--accent,#7c6af7);font-weight:500}
.demos-action-target{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
`;
    document.head.appendChild(s);
  }

  let _expandedId = null;
  let _pollTimer = null;

  window.loadDemosPanel = function () {
    _fetchAndRender();
  };

  async function _fetchAndRender() {
    const panel = document.getElementById('sb-panel-demos');
    if (!panel) return;
    try {
      const r = await fetch('/api/demos/');
      const data = await r.json();
      const demos = data.demos || [];
      _render(panel, demos);
      _managePoll(demos);
    } catch (e) {
      panel.innerHTML = '<div class="sb-empty">Failed to load demos.</div>';
    }
  }

  function _render(panel, demos) {
    if (!demos.length) {
      panel.innerHTML = '<div class="sb-empty">No demos yet.</div>';
      return;
    }
    panel.innerHTML = demos.map(_card).join('');
    if (_expandedId) {
      const card = panel.querySelector(`[data-demo-id="${_expandedId}"]`);
      if (card) _loadActionsInto(card, _expandedId);
    }
  }

  function _card(d) {
    const badge = {uploading:'⟳ uploading',analyzing:'⟳ analyzing',ready:'● ready',error:'✕ error'}[d.status] || _esc(d.status);
    const dur = d.duration_s ? `${Math.round(d.duration_s)}s` : '';
    const busy = d.status === 'analyzing' || d.status === 'uploading';
    return `<div class="demos-card" data-demo-id="${_esc(d.demo_id)}">
  <div class="demos-card-header" data-action="toggle">
    <span class="demos-title">${_esc(d.title)}</span>
    <span class="demos-badge demos-badge-${_esc(d.status)}">${badge}</span>
    <span class="demos-dur">${_esc(dur)}</span>
  </div>
  <div class="demos-card-actions">
    ${d.status==='ready' ? `<button class="demos-btn" data-action="run">Run</button>` : ''}
    <button class="demos-btn" data-action="regenerate" ${busy?'disabled':''}>Regenerate</button>
    <button class="demos-btn demos-btn-del" data-action="delete" ${busy?'disabled':''}>Delete</button>
  </div>
</div>`;
  }

  document.addEventListener('click', function (e) {
    const card = e.target.closest('[data-demo-id]');
    if (!card) return;
    const demoId = card.dataset.demoId;
    const action = e.target.closest('[data-action]')?.dataset?.action;
    if (!action) return;
    e.stopPropagation();
    if (action === 'toggle') { _toggle(demoId); return; }
    if (action === 'run')   { _run(demoId); return; }
    if (action === 'regenerate') { _regenerate(demoId); return; }
    if (action === 'delete') { _delete(demoId); return; }
  });

  function _toggle(demoId) {
    if (_expandedId === demoId) { _expandedId = null; _fetchAndRender(); return; }
    _expandedId = demoId;
    const card = document.querySelector(`[data-demo-id="${demoId}"]`);
    if (card) _loadActionsInto(card, demoId);
  }

  async function _run(demoId) {
    try {
      const r = await fetch(`/api/demos/${encodeURIComponent(demoId)}/run`, { method: 'POST' });
      const data = await r.json();
      if (!data.ok) {
        alert('Run failed: ' + (data.error || 'unknown error'));
        return;
      }
      const prog = document.getElementById('demos-upload-progress');
      if (prog) {
        prog.style.display = 'block';
        prog.textContent = 'Playbook dispatched to active session.';
        setTimeout(() => { prog.style.display = 'none'; }, 4000);
      }
    } catch (e) {
      alert('Run failed: ' + e.message);
    }
  }

  async function _regenerate(demoId) {
    try {
      await fetch(`/api/demos/${encodeURIComponent(demoId)}/regenerate`, { method: 'POST' });
    } catch (e) { /* best effort */ }
    _fetchAndRender();
  }

  async function _delete(demoId) {
    if (!confirm('Delete this demo?')) return;
    if (_expandedId === demoId) _expandedId = null;
    try {
      const r = await fetch(`/api/demos/${encodeURIComponent(demoId)}`, { method: 'DELETE' });
      const data = await r.json().catch(() => ({}));
      if (!r.ok || data.ok === false) {
        alert('Delete failed: ' + (data.error || `HTTP ${r.status}`));
        return;
      }
    } catch (e) {
      alert('Delete failed: ' + e.message);
      return;
    }
    _fetchAndRender();
  }

  async function _loadActionsInto(card, demoId) {
    let container = card.querySelector('.demos-actions-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'demos-actions-container';
      card.appendChild(container);
    }
    container.innerHTML = '<div class="sb-empty">Loading…</div>';
    try {
      const r = await fetch(`/api/demos/${encodeURIComponent(demoId)}`);
      const data = await r.json();
      const actions = data.actions || [];
      if (!actions.length) { container.innerHTML = '<div class="sb-empty">No actions yet.</div>'; return; }
      container.innerHTML = actions.map(a =>
        `<div class="demos-action-row">
          <span class="demos-action-step">${_esc(String(a.step))}</span>
          <span class="demos-action-ts">${_esc(a.timestamp)}</span>
          <span class="demos-action-type">${_esc(a.action)}</span>
          <span class="demos-action-target" title="${_esc(a.intent)}">${_esc(a.target)}${a.content ? ` — <code>${_esc(a.content)}</code>` : ''}</span>
        </div>`
      ).join('');
    } catch (e) {
      container.innerHTML = '<div class="sb-empty">Failed to load actions.</div>';
    }
  }

  window.demosUpload = function () {
    const inp = document.createElement('input');
    inp.type = 'file';
    inp.accept = 'video/*';
    inp.onchange = async () => {
      const file = inp.files[0];
      if (!file) return;
      const prog = document.getElementById('demos-upload-progress');
      if (prog) { prog.style.display = 'block'; prog.textContent = 'Uploading…'; }
      const fd = new FormData();
      fd.append('file', file);
      try {
        const r = await fetch('/api/demos/upload', { method: 'POST', body: fd });
        const data = await r.json();
        if (!data.ok) throw new Error(data.error || 'Upload failed');
        if (prog) prog.textContent = 'Analyzing… (may take a minute)';
        _fetchAndRender();
        _startPoll();
      } catch (e) {
        if (prog) prog.textContent = 'Error: ' + e.message;
      }
    };
    inp.click();
  };

  function _managePoll(demos) {
    const hasPending = demos.some(d => d.status === 'analyzing' || d.status === 'uploading');
    if (hasPending) { _startPoll(); }
    else {
      _stopPoll();
      const prog = document.getElementById('demos-upload-progress');
      if (prog) prog.style.display = 'none';
    }
  }

  function _startPoll() {
    if (_pollTimer) return;
    _pollTimer = setInterval(_fetchAndRender, 3000);
  }

  function _stopPoll() {
    if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }
  }

  function _esc(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }
})();
