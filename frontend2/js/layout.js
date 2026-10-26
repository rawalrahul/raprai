// The web UI's main script, part 8 of 8. index.html loads the parts in order.
// --- Diagnostics export ---------------------------------------------------------------------------------------
function exportDiagnostics(){
  const a = document.createElement('a');
  a.href = '/diagnostics';
  a.download = 'helm_diagnostics.json';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

// --- Panel toggle & resize -------------------------------------------------------------------------------------

// Restore persisted panel widths & collapsed state
(function restorePanelState(){
  const lw = localStorage.getItem('helmLeftW');
  const rw = localStorage.getItem('helmRightW');
  const lc = localStorage.getItem('helmLeftCollapsed') === '1';
  const rc = localStorage.getItem('helmRightCollapsed') === '1';
  const left  = document.getElementById('left-sidebar');
  const right = document.getElementById('right-sidebar');
  if(lw && !lc) left.style.width = lw + 'px';
  if(rw && !rc) right.style.width = rw + 'px';
  if(lc){ left.classList.add('collapsed'); updateToggleBtn('left', true); }
  if(rc){ right.classList.add('collapsed'); updateToggleBtn('right', true); }
})();

function updateToggleBtn(side, collapsed){
  // Keep the SVG icon; show state through the title and aria-pressed (styled in header.css).
  const btn = document.getElementById(side === 'left' ? 'toggle-left-panel' : 'toggle-right-panel');
  if(!btn) return;
  btn.title = side === 'left' ? (collapsed ? 'Show sidebar' : 'Hide sidebar')
                              : (collapsed ? 'Show sessions panel' : 'Hide sessions panel');
  btn.setAttribute('aria-pressed', collapsed ? 'false' : 'true');
}

function toggleLeftPanel(){
  const el = document.getElementById('left-sidebar');
  const collapsed = el.classList.toggle('collapsed');
  localStorage.setItem('helmLeftCollapsed', collapsed ? '1' : '0');
  updateToggleBtn('left', collapsed);
  // Restore width if un-collapsing
  if(!collapsed){
    const saved = localStorage.getItem('helmLeftW');
    if(saved) el.style.width = saved + 'px';
  }
}

function toggleRightPanel(){
  const el = document.getElementById('right-sidebar');
  const collapsed = el.classList.toggle('collapsed');
  localStorage.setItem('helmRightCollapsed', collapsed ? '1' : '0');
  updateToggleBtn('right', collapsed);
  if(!collapsed){
    const saved = localStorage.getItem('helmRightW');
    if(saved) el.style.width = saved + 'px';
  }
}

// --- Resize drag logic ---
(function initResizeHandles(){
  const leftHandle  = document.getElementById('resize-left');
  const rightHandle = document.getElementById('resize-right');
  if(!leftHandle && !rightHandle) return;

  let dragging = null; // 'left' or 'right'
  let startX = 0, startW = 0;

  function onMouseDown(side, e){
    e.preventDefault();
    const panel = document.getElementById(side === 'left' ? 'left-sidebar' : 'right-sidebar');
    if(panel.classList.contains('collapsed')) return;
    dragging = side;
    startX = e.clientX;
    startW = panel.getBoundingClientRect().width;
    e.target.classList.add('active');
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }

  function onMouseMove(e){
    if(!dragging) return;
    const panel = document.getElementById(dragging === 'left' ? 'left-sidebar' : 'right-sidebar');
    let delta = e.clientX - startX;
    if(dragging === 'right') delta = -delta; // right sidebar grows leftward
    let newW = Math.max(140, Math.min(600, startW + delta));
    panel.style.width = newW + 'px';
  }

  function onMouseUp(){
    if(!dragging) return;
    const panel = document.getElementById(dragging === 'left' ? 'left-sidebar' : 'right-sidebar');
    localStorage.setItem(dragging === 'left' ? 'helmLeftW' : 'helmRightW',
                         Math.round(panel.getBoundingClientRect().width));
    document.querySelectorAll('.resize-handle').forEach(h => h.classList.remove('active'));
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    dragging = null;
  }

  if(leftHandle)  leftHandle.addEventListener('mousedown',  e => onMouseDown('left', e));
  if(rightHandle) rightHandle.addEventListener('mousedown', e => onMouseDown('right', e));
  document.addEventListener('mousemove', onMouseMove);
  document.addEventListener('mouseup', onMouseUp);
})();

// --- Init ------------------------------------------------------------------------------------------------------
connect();
// Load integrations immediately (shows AI buttons)
loadIntegrations();
checkClaudeAuth();
