// --- Customize: appearance and layout preferences ---------------------------------------------
// Loaded in <head> so saved preferences apply before the first paint. Everything here is saved on
// this device only (localStorage 'raprUI'). The Customize drawer is built the first time it opens.
// js/sidebar.js reads the `sidebar` part of these preferences.

(function(){
  const KEY = 'raprUI';

  const SECTION_IDS = ['history','templates','scheduled','usage','pipelines','agents','memory','groups','council','demos','packages'];

  const DEFAULTS = {
    theme: 'dark',          // dark | light | system
    accent: '',             // '' = built-in indigo, otherwise #rrggbb
    font: 'inter',          // inter | system | mono | serif
    scale: 100,             // interface size, percent
    radius: 'soft',         // sharp | soft | round
    density: 'cozy',        // compact | cozy | roomy
    motion: 'full',         // full | reduced
    chatWidth: 'normal',    // narrow | normal | wide | full
    chatText: 'normal',     // small | normal | large
    sidebar: {
      layout: 'rail',       // rail | stack
      labels: false,        // labels under rail icons
      order: SECTION_IDS.slice(),
      hidden: [],
      active: 'history',
    },
  };

  const ACCENTS = [
    {name: 'Default blue', value: ''},
    {name: 'Indigo',  value: '#6366f1'},
    {name: 'Violet',  value: '#8b5cf6'},
    {name: 'Pink',    value: '#ec4899'},
    {name: 'Red',     value: '#ef4444'},
    {name: 'Orange',  value: '#f97316'},
    {name: 'Amber',   value: '#f59e0b'},
    {name: 'Green',   value: '#22c55e'},
    {name: 'Teal',    value: '#14b8a6'},
    {name: 'Cyan',    value: '#06b6d4'},
    {name: 'Slate',   value: '#64748b'},
  ];

  const FONTS = {
    inter:  "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif",
    system: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Ubuntu, system-ui, sans-serif",
    mono:   "'JetBrains Mono', 'SF Mono', 'Cascadia Code', Consolas, monospace",
    serif:  "'Iowan Old Style', 'Palatino Linotype', Palatino, Georgia, serif",
  };
  const RADII = {
    sharp: {sm: 2, md: 3, lg: 4, xl: 6},
    soft:  null,                              // stylesheet defaults
    round: {sm: 8, md: 12, lg: 16, xl: 22},
  };
  const CHAT_WIDTH = {narrow: '640px', normal: null, wide: '1100px', full: '100%'};
  const CHAT_TEXT = {small: 13.5, normal: null, large: 17};

  // ---- storage ----
  function clone(o){ return JSON.parse(JSON.stringify(o)); }

  function normalize(p){
    const out = clone(DEFAULTS);
    if(!p || typeof p !== 'object') return out;
    const pick = (k, ok) => { if(ok(p[k])) out[k] = p[k]; };
    pick('theme', v => ['dark','light','system'].includes(v));
    pick('accent', v => v === '' || /^#[0-9a-f]{6}$/i.test(v || ''));
    pick('font', v => v in FONTS);
    pick('scale', v => typeof v === 'number' && v >= 80 && v <= 130);
    pick('radius', v => v in RADII);
    pick('density', v => ['compact','cozy','roomy'].includes(v));
    pick('motion', v => ['full','reduced'].includes(v));
    pick('chatWidth', v => v in CHAT_WIDTH);
    pick('chatText', v => v in CHAT_TEXT);
    const s = p.sidebar;
    if(s && typeof s === 'object'){
      if(['rail','stack'].includes(s.layout)) out.sidebar.layout = s.layout;
      out.sidebar.labels = !!s.labels;
      if(Array.isArray(s.order)){
        const known = s.order.filter(id => SECTION_IDS.includes(id));
        out.sidebar.order = [...new Set(known.concat(SECTION_IDS))];
      }
      if(Array.isArray(s.hidden)) out.sidebar.hidden = s.hidden.filter(id => SECTION_IDS.includes(id));
      if(SECTION_IDS.includes(s.active)) out.sidebar.active = s.active;
    }
    return out;
  }

  function load(){
    let raw = null;
    try { raw = JSON.parse(localStorage.getItem(KEY) || 'null'); } catch(e) { /* storage blocked or corrupt */ }
    const p = normalize(raw);
    // First run: adopt the theme the header toggle saved before this feature existed.
    if(!raw){
      try { const t = localStorage.getItem('helmTheme'); if(t === 'light' || t === 'dark') p.theme = t; } catch(e) {}
    }
    return p;
  }

  let prefs = load();
  const listeners = [];

  function save(){
    try { localStorage.setItem(KEY, JSON.stringify(prefs)); } catch(e) { /* keep for this page only */ }
  }

  // ---- applying ----
  const mql = window.matchMedia ? window.matchMedia('(prefers-color-scheme: light)') : null;

  function resolvedTheme(){
    if(prefs.theme === 'system') return mql && mql.matches ? 'light' : 'dark';
    return prefs.theme;
  }

  function applyTheme(){
    const t = resolvedTheme();
    document.documentElement.dataset.theme = t;
    // complete.js re-applies helmTheme on every reconnect; keep it in step.
    try { localStorage.setItem('helmTheme', t); } catch(e) {}
    if(typeof window.renderHeaderIcons === 'function') try { window.renderHeaderIcons(); } catch(e) {}
  }

  function buildCss(){
    const css = [];
    const root = [];
    if(prefs.accent){
      const a = prefs.accent;
      root.push(
        `--accent:${a}`, `--accent-hover:color-mix(in oklch, ${a} 85%, white)`,
        `--accent-subtle:color-mix(in oklch, ${a} 12%, transparent)`,
        `--accent-glow:color-mix(in oklch, ${a} 40%, transparent)`,
        `--color-primary:${a}`, `--color-primary-hover:color-mix(in oklch, ${a} 85%, white)`,
        `--color-primary-subtle:color-mix(in oklch, ${a} 12%, transparent)`,
        `--border-focus:color-mix(in oklch, ${a} 50%, transparent)`,
        `--shadow-glow:0 0 0 3px color-mix(in oklch, ${a} 18%, transparent)`,
        `--bg-selected:color-mix(in oklch, ${a} 12%, transparent)`
      );
    }
    if(prefs.font !== 'inter') root.push(`--font-sans:${FONTS[prefs.font]}`);
    const r = RADII[prefs.radius];
    if(r){
      root.push(`--radius-sm:${r.sm}px`, `--radius-md:${r.md}px`, `--radius-lg:${r.lg}px`, `--radius-xl:${r.xl}px`,
                `--rad-sm:${r.sm}px`, `--rad-md:${r.md}px`, `--rad-lg:${r.lg}px`);
    }
    if(root.length) css.push(`html:root{${root.join(';')}}`);

    if(prefs.font !== 'inter'){
      // The theme layers name 'Inter' in dozens of rules; override everything except code and terminals.
      css.push(`html body, html body *:not(:is(code, pre, kbd, samp, svg, svg *, .xterm, .xterm *, [class*="mono"], [class*="code"], [class*="term"])){font-family:${FONTS[prefs.font]} !important}`);
    }
    if(prefs.scale !== 100){
      // CSS zoom also scales vh, so size the app to the zoomed viewport.
      const z = prefs.scale / 100;
      css.push(`html{zoom:${z}}`, `html body, html #app{height:calc(100vh / ${z}) !important}`);
    }
    const w = CHAT_WIDTH[prefs.chatWidth];
    if(w) css.push(`html #messages .grp, html #messages .grp.assistant{max-width:${w} !important}`, `html #messages .grp.user{max-width:min(${w}, 80%) !important}`);
    const t = CHAT_TEXT[prefs.chatText];
    if(t) css.push(`html #messages .grp .bubble, html #messages .grp.assistant .bubble, html #messages .grp.user .bubble{font-size:${t}px !important}`);
    if(prefs.motion === 'reduced'){
      css.push(`html *, html *::before, html *::after{animation-duration:.001ms !important;animation-iteration-count:1 !important;transition-duration:.001ms !important;scroll-behavior:auto !important}`);
    }
    return css.join('\n');
  }

  function applyAll(){
    const el = document.documentElement;
    applyTheme();
    el.dataset.density = prefs.density;
    el.dataset.radius = prefs.radius;
    let style = document.getElementById('rapr-ui-style');
    if(!style){
      style = document.createElement('style');
      style.id = 'rapr-ui-style';
    }
    style.textContent = buildCss();
    // Keep it last in <head> so it wins over the theme stylesheets.
    (document.head || el).appendChild(style);
    listeners.forEach(fn => { try { fn(prefs); } catch(e) { console.warn('[customize] listener', e); } });
  }

  if(mql){
    const onChange = () => { if(prefs.theme === 'system') applyTheme(); };
    if(mql.addEventListener) mql.addEventListener('change', onChange); else if(mql.addListener) mql.addListener(onChange);
  }

  // ---- public API ----
  const RaprUI = {
    get: () => prefs,
    defaults: () => clone(DEFAULTS),
    sectionIds: SECTION_IDS,
    set(patch){
      prefs = normalize(Object.assign({}, prefs, patch));
      save(); applyAll();
    },
    setSidebar(patch){
      prefs = normalize(Object.assign({}, prefs, {sidebar: Object.assign({}, prefs.sidebar, patch)}));
      save(); applyAll();
    },
    replace(p){ prefs = normalize(p); save(); applyAll(); },
    reset(){ prefs = clone(DEFAULTS); save(); applyAll(); },
    onChange(fn){ listeners.push(fn); },
  };
  window.RaprUI = RaprUI;

  applyAll();

  // ---- Customize drawer ----
  const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const icon = id => `<svg class="ico" aria-hidden="true"><use href="#i-${id}"/></svg>`;

  function seg(name, options, current){
    return `<div class="cz-seg" role="radiogroup" data-pref="${name}">` + options.map(([v, label]) =>
      `<button type="button" role="radio" aria-checked="${String(v) === String(current)}" data-value="${esc(v)}">${esc(label)}</button>`
    ).join('') + `</div>`;
  }

  function toggle(name, on, label){
    return `<label class="cz-switch"><input type="checkbox" data-pref="${name}" ${on ? 'checked' : ''}><span class="cz-switch-track" aria-hidden="true"></span><span>${esc(label)}</span></label>`;
  }

  function sectionRows(){
    const s = prefs.sidebar;
    const defs = (window.Sidebar && Sidebar.defs) || {};
    return s.order.map((id, i) => {
      const d = defs[id] || {label: id};
      const hidden = s.hidden.includes(id);
      return `<li class="cz-sec${hidden ? ' is-hidden' : ''}" draggable="true" data-id="${id}">
        <span class="cz-grip" aria-hidden="true">${icon('grip')}</span>
        ${icon(id)}
        <span class="cz-sec-label">${esc(d.label)}</span>
        <button type="button" class="cz-mini" data-move="-1" ${i === 0 ? 'disabled' : ''} title="Move up" aria-label="Move ${esc(d.label)} up">${icon('up')}</button>
        <button type="button" class="cz-mini" data-move="1" ${i === s.order.length - 1 ? 'disabled' : ''} title="Move down" aria-label="Move ${esc(d.label)} down">${icon('down')}</button>
        <button type="button" class="cz-mini" data-hide aria-pressed="${!hidden}" title="${hidden ? 'Show' : 'Hide'}" aria-label="${hidden ? 'Show' : 'Hide'} ${esc(d.label)}">${icon(hidden ? 'eye-off' : 'eye')}</button>
      </li>`;
    }).join('');
  }

  function render(){
    const p = prefs;
    const swatches = ACCENTS.map(a => {
      const on = (a.value || '') === p.accent;
      const bg = a.value || 'oklch(62% 0.18 260)';
      return `<button type="button" class="cz-swatch" role="radio" aria-checked="${on}" data-accent="${a.value}" title="${a.name}" aria-label="${a.name}" style="--sw:${bg}"></button>`;
    }).join('');
    const custom = p.accent && !ACCENTS.some(a => a.value === p.accent);
    const rightCollapsed = !!document.getElementById('right-sidebar')?.classList.contains('collapsed');
    let kelvin = 'animated';
    try { kelvin = localStorage.getItem('raprKelvin') || 'animated'; } catch(e) {}

    return `
      <div class="cz-head">
        <div>
          <div class="cz-title" id="cz-title">Customize</div>
          <div class="cz-sub">Changes apply right away and are saved on this device.</div>
        </div>
        <button type="button" class="cz-close" onclick="closeCustomize()" aria-label="Close">${icon('close')}</button>
      </div>
      <div class="cz-tabs" role="tablist">
        <button type="button" role="tab" data-tab="look" aria-selected="${czTab === 'look'}">Appearance</button>
        <button type="button" role="tab" data-tab="sidebar" aria-selected="${czTab === 'sidebar'}">Sidebar</button>
        <button type="button" role="tab" data-tab="layout" aria-selected="${czTab === 'layout'}">Chat &amp; layout</button>
      </div>
      <div class="cz-body">
        <section class="cz-pane" data-pane="look" ${czTab === 'look' ? '' : 'hidden'}>
          <div class="cz-group"><div class="cz-label">Theme</div>
            ${seg('theme', [['dark','Dark'],['light','Light'],['system','Match system']], p.theme)}</div>
          <div class="cz-group"><div class="cz-label">Accent colour</div>
            <div class="cz-swatches" role="radiogroup">${swatches}
              <label class="cz-swatch cz-swatch-custom${custom ? ' is-on' : ''}" title="Custom colour" style="--sw:${custom ? p.accent : 'transparent'}">
                <input type="color" data-accent-custom value="${p.accent || '#6366f1'}" aria-label="Custom accent colour">${icon('plus')}
              </label>
            </div></div>
          <div class="cz-group"><div class="cz-label">Font</div>
            ${seg('font', [['inter','Inter'],['system','System'],['serif','Serif'],['mono','Mono']], p.font)}</div>
          <div class="cz-group"><div class="cz-label">Interface size <span class="cz-val" id="cz-scale-val">${p.scale}%</span></div>
            <input type="range" class="cz-range" data-pref="scale" min="80" max="130" step="5" value="${p.scale}" aria-label="Interface size">
            <div class="cz-range-ticks" aria-hidden="true"><span>80%</span><span>100%</span><span>130%</span></div></div>
          <div class="cz-group"><div class="cz-label">Corners</div>
            ${seg('radius', [['sharp','Sharp'],['soft','Soft'],['round','Round']], p.radius)}</div>
          <div class="cz-group"><div class="cz-label">Density</div>
            ${seg('density', [['compact','Compact'],['cozy','Cozy'],['roomy','Roomy']], p.density)}</div>
          <div class="cz-group">${toggle('motion', p.motion === 'reduced', 'Reduce motion')}</div>
        </section>

        <section class="cz-pane" data-pane="sidebar" ${czTab === 'sidebar' ? '' : 'hidden'}>
          <div class="cz-group"><div class="cz-label">Layout</div>
            <div class="cz-cards" role="radiogroup" data-pref="layout">
              <button type="button" class="cz-card" role="radio" aria-checked="${p.sidebar.layout === 'rail'}" data-value="rail">
                <span class="cz-card-art cz-art-rail" aria-hidden="true"><i></i><i></i><i></i><b></b></span>
                <span class="cz-card-name">Icon rail</span><span class="cz-card-desc">One section at a time, full height</span>
              </button>
              <button type="button" class="cz-card" role="radio" aria-checked="${p.sidebar.layout === 'stack'}" data-value="stack">
                <span class="cz-card-art cz-art-stack" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
                <span class="cz-card-name">Stacked</span><span class="cz-card-desc">Collapsible list, several open at once</span>
              </button>
            </div></div>
          <div class="cz-group" ${p.sidebar.layout === 'rail' ? '' : 'hidden'}>${toggle('labels', p.sidebar.labels, 'Show names under rail icons')}</div>
          <div class="cz-group"><div class="cz-label">Sections <span class="cz-hint">Drag to reorder. Hidden sections stay one click away here.</span></div>
            <ul class="cz-secs" id="cz-secs">${sectionRows()}</ul>
            <button type="button" class="cz-link" data-action="reset-sidebar">Reset sections</button></div>
        </section>

        <section class="cz-pane" data-pane="layout" ${czTab === 'layout' ? '' : 'hidden'}>
          <div class="cz-group"><div class="cz-label">Chat width</div>
            ${seg('chatWidth', [['narrow','Narrow'],['normal','Normal'],['wide','Wide'],['full','Full']], p.chatWidth)}</div>
          <div class="cz-group"><div class="cz-label">Chat text size</div>
            ${seg('chatText', [['small','Small'],['normal','Normal'],['large','Large']], p.chatText)}</div>
          <div class="cz-group">${toggle('rightPanel', !rightCollapsed, 'Show the sessions panel')}</div>
          <div class="cz-group"><div class="cz-label">Kelvin the penguin</div>
            ${seg('kelvin', [['animated','Animated'],['still','Still'],['hidden','Hidden']], kelvin)}</div>
        </section>
      </div>
      <div class="cz-foot">
        <button type="button" class="cz-link" data-action="export">${icon('download')}Export</button>
        <label class="cz-link">${icon('upload')}Import<input type="file" accept="application/json,.json" data-action="import" hidden></label>
        <button type="button" class="cz-link cz-danger" data-action="reset-all">Reset everything</button>
      </div>`;
  }

  let czTab = 'look';
  let drawer = null;
  let lastFocus = null;

  function rerender(){
    if(!drawer) return;
    const body = drawer.querySelector('.cz-body');
    const top = body ? body.scrollTop : 0;
    drawer.querySelector('.cz-panel').innerHTML = render();
    const nb = drawer.querySelector('.cz-body');
    if(nb) nb.scrollTop = top;
  }

  function onSeg(name, value){
    switch(name){
      case 'layout': RaprUI.setSidebar({layout: value}); break;
      case 'kelvin':
        if(window.KelvinUI && KelvinUI.setMode) KelvinUI.setMode(value);
        { const st = document.getElementById('st-kelvin'); if(st) st.value = value; }
        break;
      default: RaprUI.set({[name]: value});
    }
    rerender();
  }

  function moveSection(id, delta){
    const order = prefs.sidebar.order.slice();
    const i = order.indexOf(id), j = i + delta;
    if(i < 0 || j < 0 || j >= order.length) return;
    [order[i], order[j]] = [order[j], order[i]];
    RaprUI.setSidebar({order});
    rerender();
    drawer.querySelector(`.cz-sec[data-id="${id}"] [data-move="${delta}"]:not([disabled])`)?.focus();
  }

  function wire(){
    const panel = drawer.querySelector('.cz-panel');

    panel.addEventListener('click', e => {
      const tab = e.target.closest('[data-tab]');
      if(tab){ czTab = tab.dataset.tab; rerender(); return; }
      const sb = e.target.closest('.cz-seg [data-value], .cz-cards [data-value]');
      if(sb){ onSeg(sb.parentElement.dataset.pref, sb.dataset.value); return; }
      const sw = e.target.closest('[data-accent]');
      if(sw){ RaprUI.set({accent: sw.dataset.accent}); rerender(); return; }
      const mv = e.target.closest('[data-move]');
      if(mv){ moveSection(mv.closest('.cz-sec').dataset.id, Number(mv.dataset.move)); return; }
      const hd = e.target.closest('[data-hide]');
      if(hd){
        const id = hd.closest('.cz-sec').dataset.id;
        const hidden = new Set(prefs.sidebar.hidden);
        hidden.has(id) ? hidden.delete(id) : hidden.add(id);
        if(hidden.size >= SECTION_IDS.length) return;  // keep at least one
        RaprUI.setSidebar({hidden: [...hidden]});
        rerender();
        drawer.querySelector(`.cz-sec[data-id="${id}"] [data-hide]`)?.focus();
        return;
      }
      const act = e.target.closest('button[data-action]');
      if(!act) return;
      if(act.dataset.action === 'reset-sidebar'){
        const d = DEFAULTS.sidebar;
        RaprUI.setSidebar({order: d.order.slice(), hidden: []});
        rerender();
      } else if(act.dataset.action === 'reset-all'){
        if(!confirm('Reset all appearance and sidebar settings to their defaults?')) return;
        RaprUI.reset(); rerender();
      } else if(act.dataset.action === 'export'){
        const blob = new Blob([JSON.stringify(prefs, null, 2)], {type: 'application/json'});
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'rapr-ui.json';
        document.body.appendChild(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 1000);
      }
    });

    panel.addEventListener('input', e => {
      const t = e.target;
      if(t.matches('[data-pref="scale"]')){
        const v = Number(t.value);
        const lbl = drawer.querySelector('#cz-scale-val'); if(lbl) lbl.textContent = v + '%';
      }
      if(t.matches('[data-accent-custom]')){
        RaprUI.set({accent: t.value.toLowerCase()});
        const lbl = t.closest('.cz-swatch'); if(lbl){ lbl.style.setProperty('--sw', t.value); lbl.classList.add('is-on'); }
        drawer.querySelectorAll('.cz-swatch[data-accent]').forEach(b => b.setAttribute('aria-checked', 'false'));
      }
    });

    panel.addEventListener('change', e => {
      const t = e.target;
      // Apply size on release so the drawer doesn't jump under the pointer while dragging.
      if(t.matches('[data-pref="scale"]')) RaprUI.set({scale: Number(t.value)});
      else if(t.matches('[data-pref="motion"]')) RaprUI.set({motion: t.checked ? 'reduced' : 'full'});
      else if(t.matches('[data-pref="labels"]')) RaprUI.setSidebar({labels: t.checked});
      else if(t.matches('[data-pref="rightPanel"]')){
        const right = document.getElementById('right-sidebar');
        if(right && right.classList.contains('collapsed') === t.checked && typeof window.toggleRightPanel === 'function') window.toggleRightPanel();
      }
      else if(t.matches('[data-action="import"]') && t.files && t.files[0]){
        t.files[0].text().then(txt => {
          try { RaprUI.replace(JSON.parse(txt)); rerender(); }
          catch(err){ alert('That file is not a RAPR customization export.'); }
        });
      }
    });

    // Drag-to-reorder the section list
    let dragId = null;
    panel.addEventListener('dragstart', e => {
      const li = e.target.closest('.cz-sec'); if(!li) return;
      dragId = li.dataset.id; li.classList.add('is-dragging');
      e.dataTransfer.effectAllowed = 'move';
      try { e.dataTransfer.setData('text/plain', dragId); } catch(_) {}
    });
    panel.addEventListener('dragover', e => {
      const li = e.target.closest('.cz-sec'); if(!li || !dragId) return;
      e.preventDefault();
      const r = li.getBoundingClientRect();
      const after = e.clientY > r.top + r.height / 2;
      panel.querySelectorAll('.cz-sec').forEach(x => x.classList.remove('drop-before', 'drop-after'));
      if(li.dataset.id !== dragId) li.classList.add(after ? 'drop-after' : 'drop-before');
    });
    panel.addEventListener('drop', e => {
      const li = e.target.closest('.cz-sec'); if(!li || !dragId) return;
      e.preventDefault();
      const after = li.classList.contains('drop-after');
      const order = prefs.sidebar.order.filter(id => id !== dragId);
      let idx = order.indexOf(li.dataset.id);
      if(after) idx++;
      if(li.dataset.id === dragId) return;
      order.splice(idx, 0, dragId);
      dragId = null;
      RaprUI.setSidebar({order});
      rerender();
    });
    panel.addEventListener('dragend', () => {
      dragId = null;
      panel.querySelectorAll('.cz-sec').forEach(x => x.classList.remove('is-dragging', 'drop-before', 'drop-after'));
    });

    drawer.addEventListener('keydown', e => {
      if(e.key === 'Escape'){ e.stopPropagation(); closeCustomize(); }
      if(e.key === 'Tab'){
        const f = [...drawer.querySelectorAll('button:not([disabled]), input:not([hidden]), [tabindex]:not([tabindex="-1"])')].filter(x => x.offsetParent !== null);
        if(!f.length) return;
        if(e.shiftKey && document.activeElement === f[0]){ e.preventDefault(); f[f.length - 1].focus(); }
        else if(!e.shiftKey && document.activeElement === f[f.length - 1]){ e.preventDefault(); f[0].focus(); }
      }
    });
  }

  window.openCustomize = function(tab){
    if(tab) czTab = tab;
    if(!drawer){
      drawer = document.createElement('div');
      drawer.id = 'customize-drawer';
      drawer.innerHTML = `<div class="cz-scrim" onclick="closeCustomize()"></div>
        <aside class="cz-panel" tabindex="-1" role="dialog" aria-modal="true" aria-labelledby="cz-title"></aside>`;
      document.body.appendChild(drawer);
      wire();
    }
    const sm = document.getElementById('settings-modal');
    if(sm && sm.style.display === 'flex' && typeof window.closeSettings === 'function') window.closeSettings();
    lastFocus = document.activeElement;
    rerender();
    drawer.classList.add('open');
    requestAnimationFrame(() => drawer.querySelector('.cz-panel').focus());
  };

  window.closeCustomize = function(){
    if(!drawer) return;
    drawer.classList.remove('open');
    if(lastFocus && lastFocus.focus) try { lastFocus.focus(); } catch(e) {}
  };

  // The header theme button flips light/dark; remember that choice here too.
  document.addEventListener('DOMContentLoaded', () => {
    const orig = window.toggleTheme;
    if(typeof orig === 'function'){
      window.toggleTheme = function(){
        orig.apply(this, arguments);
        const t = document.documentElement.dataset.theme === 'light' ? 'light' : 'dark';
        RaprUI.set({theme: t});
        if(drawer && drawer.classList.contains('open')) rerender();
      };
    }
  });
})();
