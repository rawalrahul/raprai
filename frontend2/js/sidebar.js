// --- Left sidebar: icon rail, section order, visibility and layout ----------------------------
// Two layouts, chosen in Customize:
//   rail  - an icon rail on the left; the chosen section fills the panel (one at a time).
//           Collapsing the sidebar leaves just the rail.
//   stack - the classic list of collapsible sections.
// Order, hidden sections, layout and the last section used come from RaprUI (js/customize.js).

(function(){
  const DEFS = {
    history:   {label: 'History'},
    templates: {label: 'Templates'},
    scheduled: {label: 'Scheduled'},
    usage:     {label: 'Usage'},
    pipelines: {label: 'Pipelines'},
    agents:    {label: 'Agents'},
    memory:    {label: 'Memory'},
    groups:    {label: 'Group Chats'},
    council:   {label: 'AI Council', launcher: true},
    demos:     {label: 'Demos'},
    packages:  {label: 'Packages'},
  };

  const sidebar = document.getElementById('left-sidebar');
  const list = document.getElementById('sb-sections');
  const rail = document.getElementById('sb-rail-items');
  if(!sidebar || !list || !rail || !window.RaprUI) return;

  const sectionEl = id => list.querySelector(`.sb-section[data-section="${id}"]`);
  const sb = () => RaprUI.get().sidebar;
  const isRail = () => sb().layout === 'rail';
  const visibleIds = () => sb().order.filter(id => !sb().hidden.includes(id) && sectionEl(id));
  const narrow = () => window.matchMedia('(max-width: 900px)').matches;

  function setOpen(id, open){
    const el = sectionEl(id);
    if(!el) return;
    el.classList.toggle('open', open);
    el.querySelector('.sb-section-header')?.setAttribute('aria-expanded', open ? 'true' : 'false');
  }

  function renderRail(){
    const active = sb().active;
    rail.innerHTML = '';
    visibleIds().forEach(id => {
      const d = DEFS[id] || {label: id};
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'sb-rail-btn' + (d.launcher ? ' is-launcher' : '');
      b.dataset.section = id;
      b.draggable = true;
      b.title = d.launcher ? `${d.label} (opens its own panel)` : d.label;
      b.setAttribute('aria-label', d.label);
      if(!d.launcher){
        b.setAttribute('role', 'tab');
        b.setAttribute('aria-selected', String(id === active));
        b.setAttribute('aria-controls', sectionEl(id)?.id || '');
      }
      b.tabIndex = id === active ? 0 : -1;
      b.innerHTML = `<svg class="ico" aria-hidden="true"><use href="#i-${id}"/></svg><span class="sb-rail-label">${d.label}</span>`;
      rail.appendChild(b);
    });
    if(!rail.querySelector('[tabindex="0"]') && rail.firstElementChild) rail.firstElementChild.tabIndex = 0;
  }

  function apply(){
    const s = sb();
    // Order and visibility
    s.order.forEach(id => { const el = sectionEl(id); if(el) list.appendChild(el); });
    list.querySelectorAll('.sb-section').forEach(el => { el.hidden = s.hidden.includes(el.dataset.section); });

    const wasRail = sidebar.classList.contains('sb-layout-rail');
    sidebar.classList.toggle('sb-layout-rail', s.layout === 'rail');
    sidebar.classList.toggle('sb-layout-stack', s.layout === 'stack');
    sidebar.classList.toggle('sb-rail-labels', s.layout === 'rail' && s.labels);

    if(s.layout === 'rail'){
      let active = s.active;
      if(!visibleIds().includes(active) || DEFS[active]?.launcher){
        active = visibleIds().find(id => !DEFS[id]?.launcher) || 'history';
      }
      const changed = !sectionEl(active)?.classList.contains('open');
      list.querySelectorAll('.sb-section').forEach(el => setOpen(el.dataset.section, el.dataset.section === active));
      if(active !== s.active) RaprUI.setSidebar({active});   // re-enters apply() once
      else {
        renderRail();
        if(changed && typeof window.sbLoadSection === 'function') window.sbLoadSection(active);
      }
    } else {
      if(wasRail){
        // Coming from the rail: keep only the section that was showing open.
        list.querySelectorAll('.sb-section').forEach(el => setOpen(el.dataset.section, el.dataset.section === s.active));
      }
      rail.innerHTML = '';
    }
  }

  function setCollapsed(collapsed){
    if(sidebar.classList.contains('collapsed') !== collapsed && typeof window.toggleLeftPanel === 'function') window.toggleLeftPanel();
  }

  /** Show a section. In rail layout it replaces whatever is showing. */
  function activate(id, opts){
    opts = opts || {};
    const d = DEFS[id];
    if(!d) return;
    if(d.launcher){
      if(id === 'council' && typeof window.openCouncilSection === 'function') window.openCouncilSection();
      if(narrow() && typeof window.closeSidebars === 'function') window.closeSidebars();
      return;
    }
    if(sb().hidden.includes(id)) RaprUI.setSidebar({hidden: sb().hidden.filter(x => x !== id)});
    if(!isRail()){
      const el = sectionEl(id);
      if(el && !el.classList.contains('open')){
        setOpen(id, true);
        if(typeof window.sbLoadSection === 'function') window.sbLoadSection(id);
      }
      RaprUI.setSidebar({active: id});
      return;
    }
    if(!narrow()){
      const collapsed = sidebar.classList.contains('collapsed');
      // Clicking the section that's already showing tucks the panel away, like VS Code.
      if(opts.fromRail && !collapsed && sb().active === id){ setCollapsed(true); return; }
      if(collapsed) setCollapsed(false);
    }
    const wasOpen = sectionEl(id)?.classList.contains('open');
    list.querySelectorAll('.sb-section').forEach(el => setOpen(el.dataset.section, el.dataset.section === id));
    if(sb().active !== id) RaprUI.setSidebar({active: id});
    else renderRail();
    if(!wasOpen && typeof window.sbLoadSection === 'function') window.sbLoadSection(id);
    if(opts.fromRail) rail.querySelector(`[data-section="${id}"]`)?.focus();
  }

  // ---- rail interactions ----
  rail.addEventListener('click', e => {
    const b = e.target.closest('.sb-rail-btn');
    if(b) activate(b.dataset.section, {fromRail: true});
  });

  rail.addEventListener('contextmenu', e => {
    if(!e.target.closest('.sb-rail-btn')) return;
    e.preventDefault();
    if(typeof window.openCustomize === 'function') window.openCustomize('sidebar');
  });

  // Arrow keys move between rail buttons (roving tabindex)
  document.getElementById('sb-rail')?.addEventListener('keydown', e => {
    const keys = ['ArrowDown', 'ArrowUp', 'Home', 'End'];
    if(!keys.includes(e.key)) return;
    const btns = [...document.querySelectorAll('#sb-rail .sb-rail-btn')];
    const i = btns.indexOf(document.activeElement);
    if(i < 0) return;
    e.preventDefault();
    let j = i;
    if(e.key === 'ArrowDown') j = (i + 1) % btns.length;
    if(e.key === 'ArrowUp') j = (i - 1 + btns.length) % btns.length;
    if(e.key === 'Home') j = 0;
    if(e.key === 'End') j = btns.length - 1;
    btns.forEach(b => { if(b.closest('#sb-rail-items')) b.tabIndex = -1; });
    btns[j].tabIndex = 0;
    btns[j].focus();
  });

  // Drag rail icons to reorder
  let dragId = null;
  rail.addEventListener('dragstart', e => {
    const b = e.target.closest('.sb-rail-btn'); if(!b) return;
    dragId = b.dataset.section;
    b.classList.add('is-dragging');
    e.dataTransfer.effectAllowed = 'move';
    try { e.dataTransfer.setData('text/plain', dragId); } catch(_) {}
  });
  rail.addEventListener('dragover', e => {
    const b = e.target.closest('.sb-rail-btn'); if(!b || !dragId) return;
    e.preventDefault();
    const r = b.getBoundingClientRect();
    rail.querySelectorAll('.sb-rail-btn').forEach(x => x.classList.remove('drop-before', 'drop-after'));
    if(b.dataset.section !== dragId) b.classList.add(e.clientY > r.top + r.height / 2 ? 'drop-after' : 'drop-before');
  });
  rail.addEventListener('drop', e => {
    const b = e.target.closest('.sb-rail-btn'); if(!b || !dragId || b.dataset.section === dragId) return;
    e.preventDefault();
    const after = b.classList.contains('drop-after');
    const order = sb().order.filter(id => id !== dragId);
    let idx = order.indexOf(b.dataset.section);
    if(after) idx++;
    order.splice(idx, 0, dragId);
    dragId = null;
    RaprUI.setSidebar({order});
  });
  rail.addEventListener('dragend', () => {
    dragId = null;
    rail.querySelectorAll('.sb-rail-btn').forEach(x => x.classList.remove('is-dragging', 'drop-before', 'drop-after'));
  });

  window.Sidebar = {defs: DEFS, isRail, activate, apply};
  RaprUI.onChange(apply);
  apply();
})();
