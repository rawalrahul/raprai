/**
 * Kelvin, the RAPR AI penguin.
 *
 * Kelvin.mount(el, opts)  draws an animated Kelvin into el and returns { setState, destroy }.
 * KelvinUI                maps live WebSocket events to Kelvin's mood and drives every
 *                         Kelvin on the page. complete.js forwards events via KelvinUI.onWs().
 *
 * Pure SVG + spring physics, no dependencies. Kelvin's face only changes on real
 * agent events, so what users see is what their AI is actually doing.
 */
(function () {
  'use strict';

  var STATES = {
    idle:      { label: 'Idle',           open: 1,    happy: 0,    slant: 0,     mOpen: 0,    tilt: 0,  perk: 0,    eyeScale: 1 },
    listening: { label: 'Listening',      open: 1.08, happy: 0.15, slant: 0,     mOpen: 0.15, tilt: 7,  perk: 1,    eyeScale: 1.1 },
    thinking:  { label: 'Thinking',       open: 0.82, happy: 0,    slant: -0.05, mOpen: 0,    tilt: -4, perk: 0.3,  eyeScale: 1,    gaze: [0.7, -0.9] },
    working:   { label: 'Working',        open: 0.62, happy: 0,    slant: 0.35,  mOpen: 0,    tilt: 0,  perk: 0.2,  eyeScale: 0.95 },
    approval:  { label: 'Needs approval', open: 1.05, happy: 0,    slant: -0.12, mOpen: 0.1,  tilt: -6, perk: 0.6,  eyeScale: 1.08, gaze: [0, 0.15] },
    done:      { label: 'Done',           open: 1,    happy: 1,    slant: 0,     mOpen: 0.7,  tilt: 0,  perk: 1,    eyeScale: 1 },
    error:     { label: 'Something went wrong', open: 0.78, happy: 0, slant: -0.4, mOpen: 0.05, tilt: 5, perk: -0.6, eyeScale: 0.95, gaze: [-0.2, 0.6] },
    sleeping:  { label: 'Sleeping',       open: 0,    happy: 0,    slant: 0,     mOpen: 0.1,  tilt: 3,  perk: -0.4, eyeScale: 1 },
  };

  var C = {
    amber: '#f2b33d', amberDark: '#d48a1c', rib: '#b8781a', cream: '#f6efe3', creamLine: '#e3d6c1',
    ink: '#1b1712', blush: '#ff8fa0', navy: '#283244', navyLine: '#3a4760', wing: '#1d2532',
    card: '#1f1a14', sweat: '#8fd0ff',
  };
  var HEAD = { top: -172, left: -64, right: 62 };

  // Each AI's Kelvin wears its own beanie so duplicates are easy to tell apart.
  // [knit, band, ribs]. RAPR amber is the default (and Claude's).
  var HATS = {
    rapr:       [C.amber, C.amberDark, C.rib],
    claude:     [C.amber, C.amberDark, C.rib],
    gemini:     ['#6aa6f8', '#3f7fd8', '#2f66b5'],
    codex:      ['#4fd1a1', '#2fae80', '#238a65'],
    openai:     ['#4fd1a1', '#2fae80', '#238a65'],
    ollama:     ['#e9e6df', '#c4bfb4', '#a39d90'],
    openrouter: ['#b993f5', '#9064e0', '#7448c4'],
    cursor:     ['#ff8a65', '#e0603a', '#bf4a27'],
    shell:      ['#a3aab8', '#7e8696', '#646b7a'],
  };
  function hatFor(ai) {
    if (!ai) return HATS.rapr;
    if (HATS[ai]) return HATS[ai];
    // Unknown/custom AIs get a stable colour from their name.
    var keys = ['gemini', 'codex', 'openrouter', 'cursor', 'ollama'], h = 0;
    for (var i = 0; i < ai.length; i++) h = (h * 31 + ai.charCodeAt(i)) >>> 0;
    return HATS[keys[h % keys.length]];
  }

  function eye(side, x, y, id) {
    var rx = 8, ry = 10, clip = id + '-' + side;
    return '<g data-eye="' + side + '" data-x="' + x + '" data-y="' + y + '" transform="translate(' + x + ' ' + y + ')">' +
      '<clipPath id="' + clip + '"><ellipse rx="' + rx * 1.04 + '" ry="' + ry * 1.04 + '"/></clipPath>' +
      '<ellipse rx="' + rx + '" ry="' + ry + '" fill="' + C.ink + '"/>' +
      '<circle cx="' + rx * 0.32 + '" cy="' + -ry * 0.38 + '" r="' + rx * 0.36 + '" fill="#fff"/>' +
      '<circle cx="' + -rx * 0.3 + '" cy="' + ry * 0.35 + '" r="' + rx * 0.15 + '" fill="#fff" opacity=".7"/>' +
      '<g clip-path="url(#' + clip + ')">' +
        '<rect data-lid="top" data-ry="' + ry + '" x="' + -rx * 2 + '" y="' + -ry * 3 + '" width="' + rx * 4 + '" height="0" fill="' + C.cream + '"/>' +
        '<ellipse data-lid="bot" data-ry="' + ry + '" cx="0" cy="' + ry * 2.5 + '" rx="' + rx * 1.7 + '" ry="' + ry * 1.3 + '" fill="' + C.cream + '"/>' +
      '</g></g>';
  }

  function body(id, hat) {
    hat = hat || HATS.rapr;
    var ribs = '';
    for (var i = 0; i < 12; i++) {
      var x = -46 + i * 8.4;
      ribs += '<line x1="' + x + '" y1="-117" x2="' + x + '" y2="-108" stroke="' + hat[2] + '" stroke-width="2" stroke-linecap="round"/>';
    }
    return '' +
      '<ellipse cx="-24" cy="-3" rx="14" ry="6" fill="' + C.amber + '"/><ellipse cx="24" cy="-3" rx="14" ry="6" fill="' + C.amber + '"/>' +
      '<g data-perk data-px="-54" data-py="-74" data-amt="-30"><ellipse cx="-61" cy="-56" rx="11" ry="25" transform="rotate(22 -61 -56)" fill="' + C.wing + '"/></g>' +
      '<g data-perk data-px="54" data-py="-74" data-amt="30"><ellipse cx="61" cy="-56" rx="11" ry="25" transform="rotate(-22 61 -56)" fill="' + C.wing + '"/></g>' +
      '<ellipse cx="0" cy="-63" rx="63" ry="63" fill="' + C.navy + '" stroke="' + C.navyLine + '" stroke-width="2.5"/>' +
      '<ellipse cx="0" cy="-50" rx="45" ry="44" fill="' + C.cream + '"/>' +
      '<circle cx="-20" cy="-88" r="27" fill="' + C.cream + '"/><circle cx="20" cy="-88" r="27" fill="' + C.cream + '"/>' +
      '<circle cx="-36" cy="-74" r="6" fill="' + C.blush + '" opacity=".45"/><circle cx="36" cy="-74" r="6" fill="' + C.blush + '" opacity=".45"/>' +
      eye('L', -19, -88, id) + eye('R', 19, -88, id) +
      '<path d="M-10 -77 Q0 -73 10 -77 L0 -67 Z" fill="' + C.amber + '" stroke="' + C.amberDark + '" stroke-width="1.5" stroke-linejoin="round"/>' +
      '<path data-beak d="M-7 -70 L7 -70 L0 -63 Z" fill="' + C.amberDark + '"/>' +
      '<path d="M-47 -112 Q-46 -150 0 -152 Q46 -150 47 -112 Z" fill="' + hat[0] + '"/>' +
      '<path d="M-24 -146 Q-30 -130 -30 -114 M0 -152 L0 -114 M24 -146 Q30 -130 30 -114" stroke="' + hat[1] + '" stroke-width="2" fill="none" opacity=".55"/>' +
      '<rect x="-53" y="-120" width="106" height="15" rx="7.5" fill="' + hat[1] + '"/>' + ribs +
      '<g data-perk data-px="0" data-py="-150" data-amt="16"><circle cx="0" cy="-158" r="10" fill="' + C.cream + '" stroke="' + C.creamLine + '" stroke-width="2"/></g>';
  }

  function star(x, y, r) {
    return 'M' + x + ' ' + (y - r) + ' Q' + x + ' ' + y + ' ' + (x + r) + ' ' + y + ' Q' + x + ' ' + y + ' ' + x + ' ' + (y + r) +
      ' Q' + x + ' ' + y + ' ' + (x - r) + ' ' + y + ' Q' + x + ' ' + y + ' ' + x + ' ' + (y - r) + ' Z';
  }

  function overlays() {
    var h = HEAD, font = 'font-family="inherit"';
    return '' +
      '<g class="kv-ov" data-ov="listening" opacity="0">' +
        '<path class="kv-wave" d="M' + (h.left - 8) + ' -110 q-9 12 0 24" stroke="' + C.amber + '" stroke-width="3" fill="none" stroke-linecap="round"/>' +
        '<path class="kv-wave kv-d2" d="M' + (h.left - 18) + ' -116 q-13 18 0 36" stroke="' + C.amber + '" stroke-width="3" fill="none" stroke-linecap="round"/></g>' +
      '<g class="kv-ov" data-ov="thinking" opacity="0">' +
        '<circle class="kv-bob" cx="' + (h.right + 2) + '" cy="' + (h.top + 18) + '" r="4" fill="' + C.cream + '"/>' +
        '<circle class="kv-bob kv-d1" cx="' + (h.right + 14) + '" cy="' + (h.top + 4) + '" r="5.5" fill="' + C.cream + '"/>' +
        '<circle class="kv-bob kv-d2" cx="' + (h.right + 28) + '" cy="' + (h.top - 12) + '" r="7" fill="' + C.cream + '"/></g>' +
      '<g class="kv-ov" data-ov="working" opacity="0"><g transform="translate(' + (h.right + 14) + ' ' + (h.top + 14) + ')"><g class="kv-spin">' +
        '<circle r="11" fill="none" stroke="' + C.amber + '" stroke-width="6" stroke-dasharray="4.3 4.3"/>' +
        '<circle r="7.5" fill="none" stroke="' + C.amber + '" stroke-width="3.5"/></g></g></g>' +
      '<g class="kv-ov" data-ov="approval" opacity="0"><g class="kv-pulse" ' + font + '>' +
        '<rect x="-50" y="-26" width="100" height="40" rx="10" fill="' + C.card + '" stroke="' + C.amber + '" stroke-width="2"/>' +
        '<text x="0" y="-10" text-anchor="middle" font-size="11" font-weight="700" fill="' + C.cream + '">may I?</text>' +
        '<rect x="-40" y="-4" width="36" height="13" rx="6.5" fill="' + C.amber + '"/><text x="-22" y="5.5" text-anchor="middle" font-size="9" font-weight="800" fill="' + C.card + '">yes</text>' +
        '<rect x="4" y="-4" width="36" height="13" rx="6.5" fill="none" stroke="#6b6359" stroke-width="1.5"/><text x="22" y="5.5" text-anchor="middle" font-size="9" font-weight="700" fill="#cfc6b8">no</text></g></g>' +
      '<g class="kv-ov" data-ov="done" opacity="0">' +
        '<path class="kv-twinkle" d="' + star(h.left - 6, h.top + 30, 9) + '" fill="' + C.amber + '"/>' +
        '<path class="kv-twinkle kv-d2" d="' + star(h.right + 8, h.top + 6, 12) + '" fill="' + C.amber + '"/>' +
        '<path class="kv-twinkle kv-d3" d="' + star(h.right + 2, h.top + 52, 7) + '" fill="' + C.amber + '"/></g>' +
      '<g class="kv-ov" data-ov="error" opacity="0"><path class="kv-drip" d="M' + (h.right - 4) + ' ' + (h.top + 24) + ' q-7 10 0 14 q7 -4 0 -14 Z" fill="' + C.sweat + '"/></g>' +
      '<g class="kv-ov" data-ov="sleeping" opacity="0" ' + font + ' font-weight="800" fill="' + C.cream + '">' +
        '<text class="kv-zz" x="' + (h.right + 2) + '" y="' + (h.top + 22) + '" font-size="14">z</text>' +
        '<text class="kv-zz kv-d4" x="' + (h.right + 2) + '" y="' + (h.top + 22) + '" font-size="16">z</text>' +
        '<text class="kv-zz kv-d5" x="' + (h.right + 2) + '" y="' + (h.top + 22) + '" font-size="18">z</text></g>';
  }

  // ---------------------------------------------------------------------------
  // Rig + shared animation loop
  // ---------------------------------------------------------------------------

  var KEYS = ['hop', 'stretch', 'tilt', 'open', 'happy', 'slant', 'mOpen', 'perk', 'gx', 'gy', 'eyeScale'];
  var instances = [];
  var uid = 0;
  var pointer = [0, 0, false];
  var still = false;
  var reduceMq = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  var rafId = 0;
  var last = 0;

  function isStill() { return still || (reduceMq && reduceMq.matches); }

  function mount(host, opts) {
    opts = opts || {};
    var id = 'kv' + (uid++);
    var withOv = opts.overlays !== false;
    host.innerHTML =
      '<svg viewBox="' + (opts.viewBox || (withOv ? '-100 -190 200 212' : '-76 -170 152 174')) + '" class="kelvin-svg" role="img" aria-label="' + (opts.label || 'Kelvin, the RAPR AI penguin') + '" overflow="visible">' +
      (withOv ? '<ellipse data-shadow cx="0" cy="2" rx="52" ry="7" fill="#000" opacity=".25"/>' : '') +
      '<g data-rig>' + body(id, hatFor(opts.ai)) + '</g>' + (withOv ? overlays() : '') + '</svg>';
    var svg = host.firstChild;
    var q = function (s) { return Array.prototype.slice.call(svg.querySelectorAll(s)); };
    var inst = {
      host: host, svg: svg, state: opts.state || 'idle', poke: 0,
      blinkAt: performance.now() + 1500 + Math.random() * 2500,
      rig: svg.querySelector('[data-rig]'), shadow: svg.querySelector('[data-shadow]'), beak: svg.querySelector('[data-beak]'),
      eyes: q('[data-eye]').map(function (g) {
        var top = g.querySelector('[data-lid="top"]');
        return { g: g, x: +g.getAttribute('data-x'), y: +g.getAttribute('data-y'), side: g.getAttribute('data-eye'),
                 top: top, bot: g.querySelector('[data-lid="bot"]'), ry: +top.getAttribute('data-ry') };
      }),
      perks: q('[data-perk]').map(function (g) {
        return { g: g, px: +g.getAttribute('data-px'), py: +g.getAttribute('data-py'), amt: +g.getAttribute('data-amt') };
      }),
      ovs: q('[data-ov]'),
      track: opts.track !== false,
      sp: {},
    };
    KEYS.forEach(function (k) { inst.sp[k] = { x: 0, v: 0 }; });
    inst.sp.open.x = 1; inst.sp.eyeScale.x = 1;
    if (opts.pokeable !== false) {
      svg.style.cursor = 'pointer';
      svg.addEventListener('click', function () { inst.poke = performance.now(); });
    }
    instances.push(inst);
    start();
    return {
      setState: function (s) { if (STATES[s]) inst.state = s; },
      destroy: function () { instances = instances.filter(function (i) { return i !== inst; }); host.innerHTML = ''; },
    };
  }

  function step(inst, now, dt) {
    var st = inst.state, P = STATES[st], t = now / 1000, sp = inst.sp, calm = isStill();
    var poked = now - inst.poke < 700;
    var T = { hop: 0, stretch: 0, tilt: P.tilt, open: P.open, happy: P.happy, slant: P.slant, mOpen: P.mOpen, perk: P.perk, eyeScale: P.eyeScale, gx: 0, gy: 0 };
    if (!calm) {
      T.stretch = st === 'sleeping' ? Math.sin(t * 1.6) * 0.035 : Math.sin(t * 2.4) * 0.02;
      if (st === 'working') { T.hop = -Math.abs(Math.sin(t * 6)) * 3; T.stretch += Math.sin(t * 12) * 0.015; }
      if (st === 'done') {
        var ph = (t * 1.25) % 1;
        T.hop = ph < 0.45 ? -Math.sin(ph / 0.45 * Math.PI) * 16 : 0;
        T.stretch += (ph < 0.06 || (ph > 0.42 && ph < 0.5)) ? -0.08 : 0.02;
        T.perk = 0.4 + Math.sin(t * 9) * 0.7;
      }
      if (st === 'error') T.stretch -= 0.05;
      if (st === 'listening') T.tilt = P.tilt + Math.sin(t * 2) * 1.5;
    }
    if (poked) {
      T.happy = 1; T.mOpen = 0.6; T.perk = 1;
      T.hop = calm ? 0 : -Math.sin((now - inst.poke) / 700 * Math.PI) * 18;
    }
    var g = P.gaze;
    if (!g && inst.track && pointer[2]) {
      var b = inst.svg.getBoundingClientRect();
      var dx = (pointer[0] - (b.left + b.width / 2)) / (window.innerWidth * 0.5);
      var dy = (pointer[1] - (b.top + b.height * 0.45)) / (window.innerHeight * 0.5);
      g = [Math.max(-1, Math.min(1, dx * 1.6)), Math.max(-1, Math.min(1, dy * 1.6))];
    }
    if (g) { T.gx = g[0]; T.gy = g[1]; }
    if (st === 'sleeping') { T.gx = 0; T.gy = 0.3; }
    if (P.open > 0.3 && !poked && now > inst.blinkAt) {
      if (now < inst.blinkAt + 130) T.open = 0;
      else inst.blinkAt = now + 2200 + Math.random() * 3200;
    }

    KEYS.forEach(function (k) {
      var s = sp[k], target = T[k];
      if (calm) { s.x = target; s.v = 0; return; }
      var stiff = k === 'open' ? 900 : k === 'hop' ? 520 : (k === 'gx' || k === 'gy') ? 140 : 220;
      var damp = 2 * Math.sqrt(stiff) * (k === 'perk' ? 0.45 : 0.85);
      s.v += (stiff * (target - s.x) - damp * s.v) * dt;
      s.x += s.v * dt;
    });
    var v = function (k) { return sp[k].x; };

    inst.rig.setAttribute('transform', 'translate(0 ' + v('hop').toFixed(2) + ') rotate(' + v('tilt').toFixed(2) + ') scale(' +
      (1 - v('stretch') * 0.6).toFixed(3) + ' ' + (1 + v('stretch')).toFixed(3) + ')');
    if (inst.shadow) inst.shadow.setAttribute('rx', (52 * (1 + v('hop') / 60)).toFixed(1));
    var open = Math.max(0, Math.min(1.15, v('open')));
    var happy = Math.max(0, Math.min(1, v('happy')));
    inst.eyes.forEach(function (e) {
      e.g.setAttribute('transform', 'translate(' + (e.x + v('gx') * 5).toFixed(2) + ' ' + (e.y + v('gy') * 4).toFixed(2) + ') scale(' + v('eyeScale').toFixed(3) + ')');
      var lidY = -e.ry + (1 - Math.min(open, 1)) * 2.1 * e.ry;
      e.top.setAttribute('height', Math.max(0, lidY + e.ry * 3).toFixed(2));
      e.top.setAttribute('transform', 'rotate(' + (v('slant') * 24 * (e.side === 'L' ? 1 : -1)).toFixed(2) + ')');
      e.bot.setAttribute('cy', (e.ry * (1.3 + (1 - happy) * 1.25)).toFixed(2));
    });
    if (inst.beak) inst.beak.setAttribute('transform', 'translate(0 ' + (Math.max(0, v('mOpen')) * 7).toFixed(2) + ')');
    inst.perks.forEach(function (p) { p.g.setAttribute('transform', 'rotate(' + (v('perk') * p.amt).toFixed(2) + ' ' + p.px + ' ' + p.py + ')'); });
    inst.ovs.forEach(function (o) { o.setAttribute('opacity', o.getAttribute('data-ov') === st ? '1' : '0'); });
  }

  function frame(now) {
    var dt = Math.min(0.033, (now - last) / 1000);
    last = now;
    var anyVisible = false;
    instances.forEach(function (inst) {
      // Skip hidden instances (display:none ancestors) to save CPU.
      if (!inst.svg.isConnected || inst.host.offsetParent === null) return;
      anyVisible = true;
      step(inst, now, dt);
    });
    rafId = instances.length ? requestAnimationFrame(frame) : 0;
    if (!anyVisible && document.hidden) { cancelAnimationFrame(rafId); rafId = 0; }
  }

  function start() {
    if (rafId) return;
    last = performance.now();
    rafId = requestAnimationFrame(frame);
  }

  window.addEventListener('pointermove', function (e) { pointer = [e.clientX, e.clientY, true]; }, { passive: true });
  document.addEventListener('visibilitychange', function () { if (!document.hidden && instances.length) start(); });

  window.Kelvin = { mount: mount, STATES: STATES };

  // ---------------------------------------------------------------------------
  // KelvinUI: turns RAPR's live events into one mood for the focused session
  // ---------------------------------------------------------------------------

  var MODE_KEY = 'raprKelvin'; // 'animated' | 'still' | 'hidden'
  var SLEEP_AFTER_MS = 10 * 60 * 1000;
  var ui = {
    mode: 'animated', focusedId: null, thinking: {}, activity: false, approval: false,
    doneUntil: 0, listenUntil: 0, errorUntil: 0, lastEvent: Date.now(), current: null, views: [],
    sessions: [], pipeline: null, pipelineEndedAt: 0, dismissedPipeline: null, stepDoneAt: {},
    groups: {},   // group chats answering right now: id -> {name, members, speaking, replied}
  };

  function readMode() {
    try { return localStorage.getItem(MODE_KEY) || 'animated'; } catch (e) { return 'animated'; }
  }

  function computeState() {
    var now = Date.now();
    var thinking = !!(ui.thinking[ui.focusedId] || ui.thinking._);
    if (ui.approval) return 'approval';
    if (now < ui.errorUntil) return 'error';
    if (ui.activity) return 'working';
    if (Object.keys(ui.groups).length) return 'working';
    if (thinking) return 'thinking';
    if (now < ui.doneUntil) return 'done';
    if (now < ui.listenUntil) return 'listening';
    if (now - ui.lastEvent > SLEEP_AFTER_MS) return 'sleeping';
    return 'idle';
  }

  var expiryTimer = 0;
  function render() {
    // Re-render exactly when the next short-lived mood (done, listening, error) runs out.
    clearTimeout(expiryTimer);
    var now = Date.now();
    var timers = [ui.doneUntil, ui.listenUntil, ui.errorUntil, ui.pipelineEndedAt + CREW_LINGER_MS];
    Object.keys(ui.stepDoneAt).forEach(function (id) { timers.push(ui.stepDoneAt[id] + STEP_CELEBRATE_MS); });
    var next = timers.filter(function (t) { return t > now; });
    if (next.length) expiryTimer = setTimeout(render, Math.min.apply(null, next) - now + 20);
    renderCrew();
    var s = computeState();
    if (s === ui.current) return;
    ui.current = s;
    ui.views.forEach(function (v) { v.k.setState(v.fixed || s); });
    var head = document.getElementById('kelvin-header');
    if (head) head.title = 'Kelvin: ' + STATES[s].label;
  }

  function applyMode(mode) {
    ui.mode = mode === 'still' || mode === 'hidden' ? mode : 'animated';
    still = ui.mode === 'still';
    document.documentElement.setAttribute('data-kelvin', ui.mode);
    var sel = document.getElementById('st-kelvin');
    if (sel) sel.value = ui.mode;
  }

  function slot(id, opts, fixed) {
    var el = document.getElementById(id);
    if (!el) return;
    ui.views.push({ k: mount(el, opts), fixed: fixed });
  }

  // ---------------------------------------------------------------------------
  // Kelvin crew: one Kelvin per busy session and per pipeline step
  // ---------------------------------------------------------------------------

  var CREW_LINGER_MS = 8000;      // keep a finished pipeline's crew on screen briefly
  var STEP_CELEBRATE_MS = 3000;   // a finished step hops, then rests
  var crew = { sig: '', members: {} };

  function esc(t) {
    return String(t == null ? '' : t).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function aiName(ai) {
    var names = { claude: 'Claude', gemini: 'Gemini', codex: 'Codex', openai: 'OpenAI', ollama: 'Ollama',
                  openrouter: 'OpenRouter', cursor: 'Cursor', shell: 'Shell' };
    return names[ai] || (ai ? ai.charAt(0).toUpperCase() + ai.slice(1) : 'AI');
  }

  /** Group steps into waves: steps in the same wave can run side by side. */
  function waves(steps) {
    var byId = {}, level = {};
    steps.forEach(function (st) { byId[st.id] = st; });
    function lv(st, seen) {
      if (level[st.id] !== undefined) return level[st.id];
      if (seen[st.id]) return 0; // cycle guard; the backend validates the DAG anyway
      seen[st.id] = true;
      var deps = (st.depends_on || []).filter(function (d) { return byId[d]; });
      var l = deps.length ? 1 + Math.max.apply(null, deps.map(function (d) { return lv(byId[d], seen); })) : 0;
      level[st.id] = l;
      return l;
    }
    var out = [];
    steps.forEach(function (st) { var l = lv(st, {}); (out[l] = out[l] || []).push(st); });
    return out.filter(Boolean);
  }

  function stepMood(st, now) {
    if (st.status === 'running') return 'working';
    if (st.status === 'failed') return 'error';
    if (st.status === 'skipped') return 'sleeping';
    if (st.status === 'completed') return now - (ui.stepDoneAt[st.id] || 0) < STEP_CELEBRATE_MS ? 'done' : 'idle';
    return 'idle';
  }

  function leadMood(pl) {
    return { planning: 'thinking', awaiting_approval: 'approval', running: 'working', completed: 'done',
             failed: 'error', cancelled: 'error' }[pl.status] || 'idle';
  }

  var TAGS = { pending: 'waiting', running: 'working', completed: 'done', failed: 'failed', skipped: 'skipped' };

  /** Work out who should be in the crew right now. */
  function crewPlan() {
    var now = Date.now(), groups = [];

    var busy = ui.sessions.filter(function (se) { return ui.thinking[se.id]; });
    if (busy.length >= 2) {
      groups.push({
        kind: 'sessions',
        title: busy.length + ' sessions working at once',
        sub: 'Each Kelvin is a separate AI session. Click one to open it.',
        // Sessions are independent, so each gets its own lane with no hand-off arrows.
        lanes: busy.map(function (se) {
          return [{ key: 's:' + se.id, ai: se.ai, mood: 'thinking', name: (se.emoji ? se.emoji + ' ' : '') + se.name,
                    tag: aiName(se.ai), sessionId: se.id, focused: se.id === ui.focusedId }];
        }),
      });
    }

    // Group chats: one Kelvin per member, in that AI's beanie. The member speaking
    // works, members who already replied this turn look pleased, the rest wait.
    Object.keys(ui.groups).forEach(function (gid) {
      var g = ui.groups[gid];
      var speaker = (g.members || []).filter(function (m) { return m.id === g.speaking; })[0];
      var replied = Object.keys(g.replied).length;
      groups.push({
        kind: 'group', id: gid,
        title: '👥 ' + g.name,
        sub: (speaker ? speaker.name + ' is replying…' : 'The group is thinking…') +
             (replied ? ' · ' + replied + ' repl' + (replied === 1 ? 'y' : 'ies') + ' so far' : ''),
        lanes: [(g.members || []).map(function (m) {
          var talking = m.id === g.speaking, done = !!g.replied[m.id];
          return { key: 'g:' + gid + ':' + m.id, ai: m.ai, groupId: gid,
                   mood: talking ? 'working' : done ? 'done' : 'idle',
                   name: (m.emoji ? m.emoji + ' ' : '') + m.name,
                   tag: talking ? 'replying' : done ? 'replied' : 'waiting' };
        })],
      });
    });

    var pl = ui.pipeline;
    var ended = pl && /^(completed|failed|cancelled)$/.test(pl.status);
    if (pl && pl.id !== ui.dismissedPipeline && (!ended || now - ui.pipelineEndedAt < CREW_LINGER_MS)) {
      var steps = pl.steps || [];
      var p = pl.progress || {};
      var running = steps.filter(function (st) { return st.status === 'running'; }).length;
      var done = steps.filter(function (st) { return st.status === 'completed'; }).length;
      var failed = steps.filter(function (st) { return st.status === 'failed'; }).length;
      var sub = pl.status === 'awaiting_approval' ? 'Plan ready. Approve it to start the crew.'
        : pl.status === 'planning' ? 'Lead Kelvin is splitting up the task…'
        : ended ? (pl.status === 'completed' ? 'All done. The crew finished together.' : 'The crew hit a problem. Check the failed step.')
        : failed ? failed + ' step' + (failed === 1 ? '' : 's') + ' failed · ' + done + ' of ' + steps.length + ' done'
        : running + ' working in parallel · ' + done + ' of ' + steps.length + ' done';
      var lanes = [[{ key: 'p:' + pl.id + ':lead', ai: pl.planner_ai, mood: leadMood(pl), name: 'Lead', tag: aiName(pl.planner_ai) + ' · plans', lead: true }]];
      waves(steps).forEach(function (wave) {
        lanes.push(wave.map(function (st) {
          return { key: 'p:' + pl.id + ':' + st.id, ai: st.assigned_ai, mood: stepMood(st, now), name: st.title,
                   tag: aiName(st.assigned_ai) + ' · ' + (TAGS[st.status] || st.status), status: st.status,
                   title: st.title + ' (' + aiName(st.assigned_ai) + ', ' + (TAGS[st.status] || st.status) + ')' + (st.error ? '\n' + st.error : '') };
        }));
      });
      groups.push({ kind: 'pipeline', id: pl.id, title: 'Kelvin crew · ' + steps.length + ' step' + (steps.length === 1 ? '' : 's'),
                    sub: sub, lanes: lanes, progress: p.percent });
    }
    return groups;
  }

  function onActivate(node, fn) {
    node.addEventListener('click', fn);
    node.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fn(); }
    });
  }

  function renderCrew() {
    var el = document.getElementById('kelvin-crew');
    if (!el) return;
    var groups = crewPlan();
    var sig = JSON.stringify(groups.map(function (g) {
      return [g.kind, g.id, g.lanes.map(function (l) { return l.map(function (m) { return m.key + '|' + m.ai; }); })];
    }));

    if (sig !== crew.sig) {
      // Membership changed: rebuild. Kelvins are cheap to mount.
      Object.keys(crew.members).forEach(function (k) { crew.members[k].k.destroy(); });
      crew.members = {};
      crew.sig = sig;
      el.innerHTML = groups.map(function (g, gi) {
        var lanesHtml = g.lanes.map(function (lane, li) {
          return (li && g.kind === 'pipeline' ? '<span class="kc-handoff" aria-hidden="true">→</span>' : '') +
            '<div class="kc-wave' + (lane.length > 1 ? ' kc-parallel' : '') + '">' +
            lane.map(function (m) {
              // Divs with role=button: the app's global button styles (!important) would break this layout.
              var clickable = m.sessionId || m.groupId;
              return '<div class="kc-m' + (m.lead ? ' kc-lead' : '') + (clickable ? ' kc-click' : '') + '" data-key="' + esc(m.key) + '"' +
                (clickable ? ' role="button" tabindex="0"' : '') + '>' +
                '<span class="kelvin-slot kc-art"></span><span class="kc-name"></span><span class="kc-tag"></span></div>';
            }).join('') + '</div>';
        }).join('');
        return '<section class="kc-group" data-group="' + gi + '">' +
          '<div class="kc-head"><span class="kc-title"></span><span class="kc-sub"></span>' +
          (g.kind === 'pipeline' ? '<span class="kc-close" role="button" tabindex="0" aria-label="Hide crew">✕</span>' : '') +
          '</div><div class="kc-row">' + lanesHtml + '</div></section>';
      }).join('');
      groups.forEach(function (g) {
        g.lanes.forEach(function (lane) {
          lane.forEach(function (m) {
            var node = el.querySelector('[data-key="' + m.key.replace(/"/g, '\\"') + '"]');
            if (!node) return;
            crew.members[m.key] = { node: node, k: mount(node.querySelector('.kc-art'), {
              overlays: false, track: false, pokeable: false, ai: m.ai, label: 'Kelvin: ' + m.name } ) };
            if (m.sessionId) onActivate(node, function () { if (typeof window.cmd === 'function') window.cmd('focus:' + m.sessionId); });
            if (m.groupId) onActivate(node, function () {
              if (typeof window.openGroupSection === 'function') { window.openGroupSection(); window.openGroup(m.groupId); }
            });
          });
        });
        var close = el.querySelector('[data-group="' + groups.indexOf(g) + '"] .kc-close');
        if (close) onActivate(close, function () { ui.dismissedPipeline = g.id; renderCrew(); });
      });
    }

    // Update moods and labels in place.
    groups.forEach(function (g, gi) {
      var sec = el.querySelector('[data-group="' + gi + '"]');
      if (!sec) return;
      sec.querySelector('.kc-title').textContent = g.title;
      sec.querySelector('.kc-sub').textContent = g.sub;
      g.lanes.forEach(function (lane) {
        lane.forEach(function (m) {
          var mem = crew.members[m.key];
          if (!mem) return;
          mem.k.setState(m.mood);
          mem.node.querySelector('.kc-name').textContent = m.name;
          mem.node.querySelector('.kc-tag').textContent = m.tag;
          mem.node.title = m.title || (m.name + ' · ' + m.tag);
          mem.node.setAttribute('data-status', m.status || m.mood);
          mem.node.classList.toggle('kc-focused', !!m.focused);
        });
      });
    });
    el.hidden = groups.length === 0;
  }

  /** Offer to hand a big task to the crew (backend sent crew_suggest). */
  function showCrewSuggest() {
    var wrap = document.getElementById('messages');
    if (!wrap) return;
    var old = document.getElementById('kelvin-crew-offer');
    if (old) old.remove();
    var card = document.createElement('div');
    card.id = 'kelvin-crew-offer';
    card.className = 'kelvin-crew-offer';
    card.innerHTML =
      '<div class="kco-art" aria-hidden="true"><span class="kelvin-slot"></span><span class="kelvin-slot"></span><span class="kelvin-slot"></span></div>' +
      '<div class="kco-text"><b>Big task?</b> Split it across several AIs and run the parts in parallel.</div>' +
      '<button type="button" class="kco-btn">🐧 Call the Kelvin crew</button>';
    wrap.appendChild(card);
    wrap.classList.add('has-messages');
    var arts = card.querySelectorAll('.kco-art .kelvin-slot');
    ['gemini', 'claude', 'codex'].forEach(function (ai, i) {
      var k = mount(arts[i], { overlays: false, track: false, pokeable: false, ai: ai, label: 'Kelvin crew member' });
      k.setState(i === 1 ? 'listening' : 'idle');
    });
    var btn = card.querySelector('.kco-btn');
    btn.addEventListener('click', function () {
      if (typeof window.cmd !== 'function') return;
      window.cmd('crew');
      btn.disabled = true;
      btn.textContent = 'Crew called';
    });
    if (typeof window.scroll === 'function') window.scroll();
  }

  var KelvinUI = {
    init: function () {
      applyMode(readMode());
      slot('kelvin-header', { overlays: false, label: 'Kelvin, the RAPR AI penguin' });
      slot('kelvin-thinking', { overlays: false, track: false, pokeable: false, label: 'Kelvin is busy' });
      slot('kelvin-approval', { overlays: false, track: false, pokeable: false, label: 'Kelvin is asking for approval' }, 'approval');
      slot('kelvin-hello-art', { label: 'Kelvin says hello' });
      render();
      setInterval(render, 1000);
    },

    setMode: function (mode) {
      try { localStorage.setItem(MODE_KEY, mode); } catch (e) { /* storage blocked: keep for this page only */ }
      applyMode(mode);
    },

    /** Feed every WebSocket payload here. focusedId is the session the user is looking at. */
    onWs: function (d, focusedId) {
      if (!d || !d.type) return;
      var now = Date.now();
      ui.lastEvent = now;
      if (focusedId !== undefined) ui.focusedId = focusedId;
      var mine = !d.session_id || !ui.focusedId || d.session_id === ui.focusedId;

      switch (d.type) {
        case 'thinking':
          ui.thinking[d.session_id || '_'] = !!d.active;
          break;
        case 'activity':
          if (!mine) break;
          if (d.phase === 'done') { ui.activity = false; ui.doneUntil = now + 2500; }
          else ui.activity = true;
          break;
        case 'approval_request':
          ui.approval = true;
          break;
        case 'approval_resolved':
          ui.approval = false;
          break;
        case 'agent_error':
          if (!mine) break;
          ui.activity = false;
          ui.errorUntil = now + 6000;
          break;
        case 'message':
          if (!mine) break;
          if (d.role === 'user') ui.listenUntil = now + 1500;
          else if (d.role === 'assistant') { ui.activity = false; ui.doneUntil = now + 2500; ui.errorUntil = 0; }
          break;
        case 'state':
          if (d.focused_id !== undefined) ui.focusedId = d.focused_id;
          if (Array.isArray(d.sessions)) ui.sessions = d.sessions;
          break;
        case 'group_status':
          if (d.status === 'running') {
            var prevG = ui.groups[d.group_id];
            ui.groups[d.group_id] = { name: d.name || 'Group chat', members: d.members || (prevG && prevG.members) || [],
                                      speaking: d.speaking, replied: prevG ? prevG.replied : {} };
          } else if (ui.groups[d.group_id]) {
            delete ui.groups[d.group_id];
            ui.doneUntil = now + 2500;
          }
          break;
        case 'group_message':
          if (d.message && d.message.role === 'member' && ui.groups[d.group_id]) ui.groups[d.group_id].replied[d.message.author] = true;
          else if (d.message && d.message.role === 'user' && ui.groups[d.group_id]) ui.groups[d.group_id].replied = {};
          break;
        case 'crew_suggest':
          if (mine) showCrewSuggest();
          break;
        case 'pipeline_update':
          if (!d.pipeline) break;
          var prev = ui.pipeline && ui.pipeline.id === d.pipeline.id ? ui.pipeline : null;
          (d.pipeline.steps || []).forEach(function (st) {
            var was = prev && (prev.steps || []).filter(function (x) { return x.id === st.id; })[0];
            if (st.status === 'completed' && (!was || was.status !== 'completed')) ui.stepDoneAt[st.id] = now;
          });
          if (/^(completed|failed|cancelled)$/.test(d.pipeline.status) && (!prev || prev.status !== d.pipeline.status)) ui.pipelineEndedAt = now;
          if (!prev && ui.dismissedPipeline !== d.pipeline.id) ui.dismissedPipeline = null;
          ui.pipeline = d.pipeline;
          break;
      }
      render();
    },

    get state() { return ui.current; },
  };

  window.KelvinUI = KelvinUI;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', KelvinUI.init);
  else KelvinUI.init();
})();
