/**
 * Kelvin, the RAPR AI penguin.
 *
 * Kelvin.mount(el, opts)  draws an animated Kelvin into el and returns { setState, destroy }.
 * KelvinUI (kelvin_ui.js) maps live events to Kelvin's mood.
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
    antigravity: ['#6aa6f8', '#3f7fd8', '#2f66b5'],   // Google blue, like Gemini
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
      '<g data-foot="L"><ellipse cx="-24" cy="-3" rx="14" ry="6" fill="' + C.amber + '"/></g>' +
      '<g data-foot="R"><ellipse cx="24" cy="-3" rx="14" ry="6" fill="' + C.amber + '"/></g>' +
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
  // Scenes: props for the big Kelvins (greeting, Desktop Kelvin). Each mood has
  // three; the small Kelvins (header, group chats) keep simple moves instead.
  // Every animation cycles in 1.2 s (or a divisor) so Desktop Kelvin's strips loop.
  // ---------------------------------------------------------------------------

  var SCENES = {
    working:  ['laptop', 'run', 'hammer'],
    thinking: ['bubble', 'bulb', 'pace'],
    done:     ['jump', 'cloud', 'party'],
    idle:     ['breathe', 'relax', 'shades'],
  };
  // Scenes that bring their own props hide the mood's usual overlay (gear, thought dots).
  var OWN_OVERLAY = { laptop: 1, run: 1, hammer: 1, bulb: 1, pace: 1 };

  function prop(name, inner) { return '<g data-prop="' + name + '" class="kv-prop" display="none">' + inner + '</g>'; }

  /** Props behind Kelvin, on the ground. */
  function propsBack() {
    return prop('run',
        '<g stroke="#cfd6e2" stroke-width="3" stroke-linecap="round" opacity=".75">' +
          '<line class="kv-speed" x1="-70" y1="-128" x2="-96" y2="-128"/>' +
          '<line class="kv-speed kv-s2" x1="-74" y1="-92" x2="-98" y2="-92"/>' +
          '<line class="kv-speed kv-s3" x1="-70" y1="-52" x2="-94" y2="-52"/></g>' +
        '<circle class="kv-dust" cx="-34" cy="-5" r="6" fill="#cfc6b8"/>' +
        '<circle class="kv-dust kv-s2" cx="-46" cy="-9" r="4" fill="#cfc6b8"/>') +
      prop('relax',
        '<rect x="-96" y="-9" width="192" height="13" rx="4" fill="#5b9cf5"/>' +
        '<rect x="-96" y="-5" width="192" height="4" fill="' + C.cream + '" opacity=".85"/>' +
        '<g transform="translate(-78 -164)"><g class="kv-sun">' +
          [0, 45, 90, 135].map(function (a) {
            return '<rect x="-2" y="-19" width="4" height="38" rx="2" fill="#ffd34d" transform="rotate(' + a + ')"/>';
          }).join('') + '</g><circle r="10" fill="#ffd34d"/></g>');
  }

  /** Props in front of Kelvin. */
  function propsFront() {
    var confetti = '', cols = [C.amber, '#6aa6f8', '#4fd1a1', C.blush, '#b993f5'];
    for (var i = 0; i < 10; i++) {
      confetti += '<rect class="kv-fall" style="animation-delay:-' + (i * 0.12).toFixed(2) + 's" x="' + (-90 + i * 19) +
        '" y="-190" width="6" height="10" rx="1.5" fill="' + cols[i % cols.length] + '"/>';
    }
    var code = function (x, txt, cls) {
      return '<text class="kv-code ' + cls + '" x="' + x + '" y="-62" font-size="12" font-weight="700" fill="#8fd0ff" text-anchor="middle" font-family="monospace">' + txt + '</text>';
    };
    return prop('laptop',
        code(-24, '&lt;/&gt;', '') + code(4, '{ }', 'kv-c2') + code(28, '01', 'kv-c3') +
        '<rect x="-48" y="-13" width="96" height="10" rx="3" fill="#9aa3b2"/>' +
        '<path d="M-41 -13 L-35 -58 L35 -58 L41 -13 Z" fill="#cdd4df" stroke="#8e97a6" stroke-width="2" stroke-linejoin="round"/>' +
        '<path d="M-35 -58 L35 -58" stroke="#8fd0ff" stroke-width="2.5"/>' +
        '<ellipse cx="-3" cy="-36" rx="9" ry="6" fill="' + C.amber + '"/><path d="M5 -36 l8 -6 v12 Z" fill="' + C.amber + '"/>' +
        '<circle cx="-7" cy="-37" r="1.6" fill="' + C.ink + '"/>') +
      prop('hammer',
        '<rect x="68" y="-34" width="26" height="13" rx="2" fill="#c0603a"/><rect x="68" y="-20" width="26" height="13" rx="2" fill="#a64f2f"/>' +
        '<g data-bang><path d="' + star(80, -46, 8) + '" fill="#ffd34d"/><path d="' + star(94, -52, 5) + '" fill="#ffd34d"/>' +
          '<text x="62" y="-122" font-size="15" font-weight="900" fill="#ffd34d" text-anchor="middle">BANG!</text></g>') +
      prop('pace',
        '<text class="kv-q" x="-80" y="-148" font-size="24" font-weight="800" fill="' + C.cream + '">?</text>' +
        '<text class="kv-q kv-c2" x="74" y="-124" font-size="18" font-weight="800" fill="' + C.cream + '">?</text>') +
      prop('party', confetti) +
      prop('shades',
        '<text class="kv-note" x="-84" y="-118" font-size="20" fill="' + C.cream + '">\u266A</text>' +
        '<text class="kv-note kv-c2" x="70" y="-140" font-size="18" fill="' + C.cream + '">\u266B</text>') +
      prop('relax',
        '<text class="kv-note" x="30" y="-150" font-size="15" font-weight="700" fill="' + C.cream + '">ahh~</text>');
  }

  /** Props that move with Kelvin: behind the body (cloud) and in front of it. */
  function propsRigBack() {
    return prop('cloud',
      '<g fill="#eef3fb"><circle cx="-34" cy="4" r="14"/><circle cx="-12" cy="-2" r="18"/><circle cx="14" cy="-1" r="17"/>' +
      '<circle cx="36" cy="5" r="13"/><rect x="-48" y="2" width="96" height="16" rx="8"/></g>' +
      '<text x="0" y="15" text-anchor="middle" font-size="14" font-weight="900" fill="#5b9cf5">9</text>');
  }
  function propsRigFront() {
    return prop('hammer',
        '<g data-hammer><rect x="45" y="-95" width="6" height="37" rx="3" fill="#8b5a2b"/>' +
        '<rect x="36" y="-106" width="24" height="13" rx="3" fill="#9aa3b2" stroke="#6b7280" stroke-width="1.5"/></g>') +
      prop('bulb',
        '<circle class="kv-bulb" cx="74" cy="-160" r="21" fill="#ffd34d"/>' +
        '<circle cx="74" cy="-160" r="11" fill="#fff3b0" stroke="#e0b030" stroke-width="2"/>' +
        '<rect x="69" y="-150" width="10" height="7" rx="2" fill="#9aa3b2"/>' +
        '<text class="kv-q" x="-80" y="-140" font-size="22" font-weight="800" fill="' + C.cream + '">?</text>') +
      prop('shades',
        '<rect x="-34" y="-98" width="28" height="18" rx="7" fill="#111"/><rect x="6" y="-98" width="28" height="18" rx="7" fill="#111"/>' +
        '<path d="M-6 -91 h12" stroke="#111" stroke-width="3"/>' +
        '<path d="M-29 -94 l7 0 M11 -94 l7 0" stroke="#fff" stroke-width="2" stroke-linecap="round" opacity=".7"/>' +
        '<rect x="60" y="-54" width="17" height="21" rx="3" fill="' + C.cream + '"/>' +
        '<path d="M77 -48 q8 0 8 6 q0 6 -8 6" stroke="' + C.cream + '" stroke-width="3" fill="none"/>' +
        '<path class="kv-note" d="M64 -60 q-3 -6 0 -10 M71 -60 q3 -6 0 -10" stroke="#cfd6e2" stroke-width="2" fill="none"/>');
  }

  // ---------------------------------------------------------------------------
  // Rig + shared animation loop
  // ---------------------------------------------------------------------------

  var KEYS = ['hop', 'stretch', 'tilt', 'open', 'happy', 'slant', 'mOpen', 'perk', 'gx', 'gy', 'eyeScale', 'dx', 'dy'];
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
      (withOv ? '<ellipse data-shadow cx="0" cy="2" rx="52" ry="7" fill="#000" opacity=".25"/>' + propsBack() : '') +
      '<g data-rig>' + (withOv ? propsRigBack() : '') + body(id, hatFor(opts.ai)) + (withOv ? propsRigFront() : '') + '</g>' +
      (withOv ? propsFront() + overlays() : '') + '</svg>';
    var svg = host.firstChild;
    var q = function (s) { return Array.prototype.slice.call(svg.querySelectorAll(s)); };
    var inst = {
      host: host, svg: svg, state: opts.state || 'idle', poke: 0,
      phase: Math.random() * 10,
      // Each mood has a few moves; a Kelvin switches move every few seconds.
      // opts.variant pins one move (used to record Desktop Kelvin's strips).
      variant: opts.variant || 0, pinned: opts.variant !== undefined, variantUntil: 0,
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
      props: q('[data-prop]'), feet: q('[data-foot]'), hammer: svg.querySelector('[data-hammer]'), bang: svg.querySelector('[data-bang]'),
      big: withOv, scene: null,   // only the big Kelvins act out scenes with props
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
      setState: function (s) {
        if (!STATES[s] || s === inst.state) return;
        inst.state = s;
        if (!inst.pinned) { inst.variant = Math.floor(Math.random() * MOVES); inst.variantUntil = 0; }
      },
      destroy: function () { instances = instances.filter(function (i) { return i !== inst; }); host.innerHTML = ''; },
    };
  }

  var MOVES = 3;                    // moves per mood (see step)
  var W = 2 * Math.PI / 1.2;        // one cycle per 1.2 s, so Desktop Kelvin's 16-frame strips loop cleanly

  function step(inst, now, dt) {
    var st = inst.state, P = STATES[st], t = now / 1000 + inst.phase, sp = inst.sp, calm = isStill();
    if (!inst.pinned && now > inst.variantUntil) {
      // Time for a different move (never the same one twice in a row).
      if (inst.variantUntil) inst.variant = (inst.variant + 1 + Math.floor(Math.random() * (MOVES - 1))) % MOVES;
      inst.variantUntil = now + 6000 + Math.random() * 3000;
    }
    var mv = inst.variant;
    var poked = now - inst.poke < 700;
    var T = { hop: 0, stretch: 0, tilt: P.tilt, open: P.open, happy: P.happy, slant: P.slant, mOpen: P.mOpen, perk: P.perk, eyeScale: P.eyeScale, gx: 0, gy: 0, dx: 0, dy: 0 };
    var scene = inst.big && SCENES[st] ? SCENES[st][mv % SCENES[st].length] : null;
    var sceneGaze = null, hammerAt = 10, bangOn = false, feetL = 0, feetR = 0;
    if (scene === 'laptop') {                 // typing away on a laptop
      sceneGaze = [0, 0.85]; T.slant = 0.25; T.open = 0.85;
      if (!calm) { T.perk = 0.25 + Math.sin(t * W * 4) * 0.45; T.hop = -Math.abs(Math.sin(t * W * 2)) * 1; }
    } else if (scene === 'run') {             // running flat out
      T.tilt = 8; T.slant = 0.3; T.mOpen = 0.25; sceneGaze = [0.9, 0];
      if (!calm) {
        var r = Math.sin(t * W * 2);
        T.hop = -Math.abs(r) * 7; T.stretch = Math.sin(t * W * 4) * 0.03; T.perk = r * 1.2;
        feetL = -Math.max(0, r) * 9; feetR = -Math.max(0, -r) * 9;
      }
    } else if (scene === 'hammer') {          // building it, one brick at a time
      T.slant = 0.3; sceneGaze = [0.7, 0.4];
      if (!calm) {
        var hp = (t / 0.6) % 1;               // strike, lift slowly, strike again
        hammerAt = hp < 0.6 ? 120 - (hp / 0.6) * 110 : 10 + Math.pow((hp - 0.6) / 0.4, 2) * 110;
        bangOn = hp < 0.18;
        T.hop = hp < 0.1 ? -3 : 0;
      }
    } else if (scene === 'bulb') {            // lightbulb moment
      T.tilt = -6; sceneGaze = [0.8, -0.9]; T.perk = 0.4;
      if (!calm) T.tilt = -6 + Math.sin(t * W) * 2;
    } else if (scene === 'pace') {            // pacing back and forth
      sceneGaze = [0, -0.4];
      if (!calm) { T.dx = Math.sin(t * W) * 22; T.tilt = Math.cos(t * W) * 5; T.hop = -Math.abs(Math.sin(t * W * 2)) * 2; }
    } else if (scene === 'cloud') {           // on cloud 9
      T.dy = -18; T.happy = 1; T.perk = 0.9; T.mOpen = 0.5;
      if (!calm) { T.dy = -18 + Math.sin(t * W) * 4; T.tilt = Math.sin(t * W) * 3; }
    } else if (scene === 'party') {           // confetti party
      T.happy = 1; T.mOpen = 0.7;
      if (!calm) { T.tilt = Math.sin(t * W * 2) * 9; T.perk = 0.6 + Math.sin(t * W * 2) * 0.6; T.hop = -Math.abs(Math.sin(t * W)) * 5; }
    } else if (scene === 'relax') {           // lying on a beach towel in the sun
      T.tilt = -90; T.dx = 85; T.dy = -66; T.open = 0.35; T.happy = 0.7; sceneGaze = [0.3, -0.2];
      if (!calm) T.stretch = Math.sin(t * W) * 0.03;
    } else if (scene === 'shades') {          // sunglasses, coffee and a tune
      T.happy = 0.5; T.perk = 0.3;
      if (!calm) { T.tilt = Math.sin(t * W) * 5; T.hop = -Math.abs(Math.sin(t * W * 2)) * 2; }
    }
    var acting = scene && scene !== 'bubble' && scene !== 'jump' && scene !== 'breathe';
    if (!calm && !acting) {
      T.stretch = st === 'sleeping' ? Math.sin(t * 1.6) * 0.035 : Math.sin(t * 2.4) * 0.02;
      if (st === 'working') {
        if (mv === 1) {                      // waddle side to side
          T.tilt = Math.sin(t * W) * 7; T.hop = -Math.abs(Math.sin(t * W)) * 2.5;
        } else if (mv === 2) {               // typing with both flippers
          T.perk = 0.2 + Math.sin(t * W * 2) * 1.4; T.hop = -Math.abs(Math.sin(t * W * 2)) * 3; T.tilt = Math.sin(t * W * 2) * 2;
        } else {                             // busy little hops
          T.hop = -Math.abs(Math.sin(t * W)) * 3.5; T.stretch += Math.sin(t * W * 2) * 0.015;
        }
      }
      if (st === 'done') {
        if (mv === 1) {                      // happy wiggle
          T.tilt = Math.sin(t * W * 2) * 9; T.perk = 0.6 + Math.sin(t * W * 2) * 0.5;
        } else if (mv === 2) {               // flipper cheer
          T.perk = 0.8 + Math.sin(t * W * 2) * 1.6; T.hop = -Math.abs(Math.sin(t * W)) * 12; T.stretch += Math.sin(t * W * 2) * 0.04;
        } else {                             // jump for joy
          var ph = (t / 1.2) % 1;
          T.hop = ph < 0.45 ? -Math.sin(ph / 0.45 * Math.PI) * 16 : 0;
          T.stretch += (ph < 0.06 || (ph > 0.42 && ph < 0.5)) ? -0.08 : 0.02;
          T.perk = 0.4 + Math.sin(t * W) * 0.7;
        }
      }
      if (st === 'thinking') {
        if (mv === 1) T.tilt = P.tilt + Math.sin(t * W) * 6;                    // ponder, head swaying
        else if (mv === 2) {                                                     // hmm… little bounces
          T.hop = -Math.abs(Math.sin(t * W)) * 5; T.perk = 0.3 + Math.sin(t * W) * 0.8; T.tilt = P.tilt + 4;
        }
      }
      if (st === 'idle') {
        if (mv === 1) T.hop = -Math.abs(Math.sin(t * W)) * 3;                   // gentle bob
        else if (mv === 2) T.tilt = Math.sin(t * W) * 5;                         // easy sway
      }
      if (st === 'error') T.stretch -= 0.05;
      if (st === 'listening') T.tilt = P.tilt + Math.sin(t * 2) * 1.5;
    }
    if (poked) {
      T.happy = 1; T.mOpen = 0.6; T.perk = 1;
      T.hop = calm ? 0 : -Math.sin((now - inst.poke) / 700 * Math.PI) * 18;
    }
    var g = sceneGaze || P.gaze;
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

    inst.rig.setAttribute('transform', 'translate(' + v('dx').toFixed(2) + ' ' + (v('hop') + v('dy')).toFixed(2) + ') rotate(' + v('tilt').toFixed(2) + ') scale(' +
      (1 - v('stretch') * 0.6).toFixed(3) + ' ' + (1 + v('stretch')).toFixed(3) + ')');
    if (inst.shadow) inst.shadow.setAttribute('rx', (scene === 'relax' ? 92 : Math.max(12, 52 * (1 + (v('hop') + v('dy')) / 60))).toFixed(1));
    if (scene !== inst.scene) {
      inst.scene = scene;
      inst.props.forEach(function (el) { el.setAttribute('display', el.getAttribute('data-prop') === scene ? 'inline' : 'none'); });
    }
    if (inst.feet.length) {
      inst.feet[0].setAttribute('transform', 'translate(0 ' + feetL.toFixed(2) + ')');
      inst.feet[1].setAttribute('transform', 'translate(0 ' + feetR.toFixed(2) + ')');
    }
    if (inst.hammer) inst.hammer.setAttribute('transform', 'rotate(' + hammerAt.toFixed(1) + ' 48 -60)');
    if (inst.bang) inst.bang.setAttribute('opacity', bangOn ? '1' : '0');
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
    inst.ovs.forEach(function (o) { o.setAttribute('opacity', o.getAttribute('data-ov') === st && !OWN_OVERLAY[scene] ? '1' : '0'); });
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

  // setStill: kelvin_ui.js switches every Kelvin between animated and still.
  window.Kelvin = { mount: mount, STATES: STATES, setStill: function (v) { still = !!v; } };
})();
