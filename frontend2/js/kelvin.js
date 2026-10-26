/**
 * Kelvin, the RAPR AI penguin.
 *
 * Kelvin.mount(el, opts)  draws an animated Kelvin into el and returns { setState, destroy }.
 * KelvinUI                maps live WebSocket events to Kelvin's mood and drives every
 *                         Kelvin on the page. core.js forwards events via KelvinUI.onWs().
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
    Object.keys(groupDone).forEach(function (gid) {
      Object.keys(groupDone[gid]).forEach(function (id) { timers.push(groupDone[gid][id] + TEAM_DONE_MS); });
    });
    var next = timers.filter(function (t) { return t > now; });
    if (next.length) expiryTimer = setTimeout(render, Math.min.apply(null, next) - now + 20);
    renderCrew();
    renderTeam();
    renderFloat();
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
    var names = { claude: 'Claude', gemini: 'Gemini', antigravity: 'Antigravity', codex: 'Codex', openai: 'OpenAI', ollama: 'Ollama',
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

    // Group chats get their own stage (the open group chat, or the floating stage), not a lane here.

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
    ['antigravity', 'claude', 'codex'].forEach(function (ai, i) {
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

  // ---------------------------------------------------------------------------
  // Group chat stage: one big Kelvin per member (in that AI's beanie) acting out
  // the collaboration. Shown inside the open group chat, and as a floating stage
  // while a group works and its chat isn't on screen.
  // ---------------------------------------------------------------------------

  var TEAM_DONE_MS = 4000;
  var BATON_MS = 1600;
  var BIT_MS = 7000;
  var BITS = ['toss', 'tower', 'board', 'plane', 'cheer', 'coffee'];
  var groupDone = {};      // group id -> { member id: when it last replied }

  function first(name) { return String(name || 'AI').split(/\s+/)[0]; }

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  /** A stage in host. Returns { update(group), destroy() }. */
  function createStage(host, size) {
    var st = { actors: {}, order: [], bit: null, bitUntil: 0, prevSpeaker: null, baton: null, five: null, fxKey: '', sig: '' };
    host.textContent = '';
    var stage = el('div', 'kv-stage kv-stage-' + size);
    var fx = el('div', 'kv-fx');
    var row = el('div', 'kv-actors');
    var caption = el('div', 'kv-caption');
    stage.appendChild(fx); stage.appendChild(row); stage.appendChild(caption);
    host.appendChild(stage);

    function build(members) {
      Object.keys(st.actors).forEach(function (id) { st.actors[id].k.destroy(); });
      st.actors = {}; st.order = []; row.textContent = '';
      members.forEach(function (m) {
        var node = el('div', 'kv-actor');
        var art = el('span', 'kelvin-slot kv-actor-art');
        var name = el('span', 'kv-actor-name', m.name);
        if (m.color) name.style.color = m.color;
        var tag = el('span', 'kv-actor-tag');
        node.appendChild(art); node.appendChild(name); node.appendChild(tag);
        row.appendChild(node);
        st.actors[m.id] = { m: m, node: node, tag: tag,
                            k: mount(art, { track: false, pokeable: false, ai: m.ai, label: 'Kelvin: ' + m.name }) };
        st.order.push(m.id);
      });
    }

    function x(id) {   // centre of an actor, relative to the stage
      var a = st.actors[id];
      return a ? a.node.offsetLeft + a.node.offsetWidth / 2 : 0;
    }

    function update(g) {
      var members = g.members || [];
      var sig = members.map(function (m) { return m.id + ':' + m.ai; }).join(',');
      if (sig !== st.sig) { build(members); st.sig = sig; st.fxKey = ''; }
      var now = Date.now(), live = g.live, done = groupDone[g.id] || {};
      var speaker = live ? live.speaking : null;

      // Turn changes: the baton flies from the last speaker to the new one.
      if (speaker !== st.prevSpeaker) {
        if (st.prevSpeaker && speaker && st.actors[st.prevSpeaker] && st.actors[speaker]) {
          st.baton = { from: st.prevSpeaker, to: speaker, until: now + BATON_MS };
        }
        st.prevSpeaker = speaker;
      }
      // A fresh reply: a high five.
      Object.keys(done).forEach(function (id) {
        if (now - done[id] < 1500 && (!st.five || st.five.at !== done[id])) st.five = { id: id, at: done[id] };
      });

      st.order.forEach(function (id) {
        var a = st.actors[id], mood;
        if (live && id === speaker) mood = 'working';
        else if (now - (done[id] || 0) < TEAM_DONE_MS) mood = 'done';
        else if (live) mood = 'listening';
        else mood = now - ui.lastEvent > SLEEP_AFTER_MS ? 'sleeping' : 'idle';
        a.k.setState(mood);
        a.node.setAttribute('data-mood', mood);
        a.tag.textContent = { working: 'replying', done: 'replied', listening: 'with the team', sleeping: 'napping' }[mood] ||
                            (a.m.role || aiName(a.m.ai));
      });

      // A new collaboration bit every few seconds while the group works.
      if (!live) { st.bit = null; }
      else if (!st.bit || now > st.bitUntil) {
        var pool = BITS.filter(function (b) { return b !== st.bit && (st.order.length > 1 || b === 'board' || b === 'tower'); });
        st.bit = pool[Math.floor(Math.random() * pool.length)];
        st.bitUntil = now + BIT_MS;
      }
      renderFx(g, live, speaker, now);
    }

    function renderFx(g, live, speaker, now) {
      var baton = st.baton && now < st.baton.until ? st.baton : null;
      var five = st.five && now - st.five.at < 1500 ? st.five : null;
      var others = st.order.filter(function (id) { return id !== speaker; });
      var buddy = others.length ? others[Math.floor(now / BIT_MS) % others.length] : null;
      var key = [live ? 1 : 0, st.bit, speaker, buddy, baton && baton.to, five && five.at, row.offsetWidth].join('|');
      if (key === st.fxKey) return;
      st.fxKey = key;
      fx.textContent = '';
      var name = function (id) { return st.actors[id] ? first(st.actors[id].m.name) : 'AI'; };
      var put = function (cls, text, left, vars) {
        var n = el('span', 'kvx ' + cls, text);
        n.style.left = Math.round(left) + 'px';
        Object.keys(vars || {}).forEach(function (k) { n.style.setProperty(k, Math.round(vars[k]) + 'px'); });
        fx.appendChild(n);
        return n;
      };
      var line = '';
      if (five) {
        put('kvx-five', '🙌', x(five.id) + 18);
        line = name(five.id) + ' nailed their part. High five! 🙌';
      }
      if (baton) {
        put('kvx-baton', '📜', x(baton.from), { '--dx': x(baton.to) - x(baton.from) });
        line = name(baton.from) + ' passes the baton to ' + name(baton.to) + ' 📜';
      } else if (live && speaker && st.actors[speaker]) {
        var xs = x(speaker), xb = buddy ? x(buddy) : xs + 60, mid = (xs + xb) / 2;
        if (st.bit === 'toss') {
          put('kvx-toss', '💡', xs, { '--dx': xb - xs });
          line = line || name(buddy) + ' and ' + name(speaker) + ' toss ideas around 💡';
        } else if (st.bit === 'tower') {
          var n = Math.min(6, 1 + Object.keys((ui.groups[g.id] || {}).replied || {}).length);
          for (var i = 0; i < n; i++) {
            var b = put('kvx-brick', '🧱', mid - 9);
            b.style.bottom = (52 + i * 15) + 'px';   // stacked on the floor, above the name tags
            b.style.animationDelay = (i * 0.12) + 's';
          }
          line = line || 'Building it together, one brick per reply 🧱';
        } else if (st.bit === 'board') {
          put('kvx-board', '📋', buddy ? mid - 14 : xs + 44);
          put('kvx-pen', '✏️', (buddy ? mid : xs + 58));
          line = line || 'Huddle at the whiteboard: ' + name(speaker) + ' sketches the plan';
        } else if (st.bit === 'plane') {
          put('kvx-plane', '✈️', xb, { '--dx': xs - xb });
          line = line || name(buddy) + ' sends ' + name(speaker) + ' a note: "looks good!" ✈️';
        } else if (st.bit === 'cheer') {
          others.forEach(function (id) { put('kvx-sign', '📣', x(id) + 16); });
          line = line || 'The team cheers: "Go ' + name(speaker) + '!" 📣';
        } else if (st.bit === 'coffee') {
          put('kvx-coffee', '☕', xb, { '--dx': xs - xb });
          line = line || name(buddy) + ' brings ' + name(speaker) + ' a coffee (fish-flavoured) ☕';
        }
      }
      if (!live && !five) line = '';
      caption.textContent = line;
      caption.hidden = !line;
    }

    return {
      update: update,
      destroy: function () {
        Object.keys(st.actors).forEach(function (id) { st.actors[id].k.destroy(); });
        st.actors = {};
        host.textContent = '';
      },
    };
  }

  /** The group as the stage sees it: roster plus live status (if it's answering now). */
  function stageGroup(gid, fallback) {
    var live = ui.groups[gid] || null;
    var members = (fallback && fallback.members) || (live && live.members) || [];
    return { id: gid, name: (live && live.name) || (fallback && fallback.name) || 'Group chat', members: members, live: live };
  }

  // Inside the open group chat.
  var team = { host: null, gid: null, group: null, stage: null };

  function renderTeam() {
    if (!team.stage || !team.host || !team.host.isConnected) return;
    team.stage.update(stageGroup(team.gid, team.group));
  }

  /** Show an open group chat's members on a stage (host null = closed). */
  function mountGroupTeam(host, group) {
    if (!host || !group) {
      if (team.stage) team.stage.destroy();
      team.stage = team.host = team.gid = team.group = null;
      renderFloat();
      return;
    }
    if (team.host !== host || team.gid !== group.id) {
      if (team.stage) team.stage.destroy();
      team.stage = createStage(host, 'panel');
    }
    team.host = host; team.gid = group.id; team.group = group;
    if (group.status === 'running' && !ui.groups[group.id]) {
      ui.groups[group.id] = { name: group.name, members: group.members || [], speaking: group.speaking, replied: {} };
    }
    renderTeam();
    renderFloat();
  }

  // Floating stage: a group is working but its chat isn't on screen.
  var float = { el: null, stage: null, gid: null, dismissed: {} };

  function groupOnScreen(gid) {
    var wrap = document.getElementById('group-wrapper');
    return !!(wrap && wrap.classList.contains('open') && team.gid === gid && team.host && team.host.isConnected);
  }

  function renderFloat() {
    var gid = Object.keys(ui.groups).filter(function (id) { return !groupOnScreen(id) && !float.dismissed[id]; })[0] || null;
    Object.keys(float.dismissed).forEach(function (id) { if (!ui.groups[id]) delete float.dismissed[id]; });
    if (!gid) {
      if (float.el) float.el.hidden = true;
      if (float.stage) { float.stage.destroy(); float.stage = null; float.gid = null; }
      return;
    }
    if (!float.el) {
      float.el = el('div', 'kv-float');
      float.el.id = 'kelvin-stage-float';
      var head = el('div', 'kv-float-head');
      float.title = el('span', 'kv-float-title');
      var open = el('span', 'kv-float-btn', 'Open');
      var close = el('span', 'kv-float-btn kv-float-x', '✕');
      open.setAttribute('role', 'button'); close.setAttribute('role', 'button');
      close.setAttribute('aria-label', 'Hide');
      onActivate(open, function () {
        // Remember the group first: opening the panel hides this floating stage.
        var gid = float.gid;
        if (typeof window.openGroupSection === 'function' && gid) { window.openGroupSection(); window.openGroup(gid); }
      });
      onActivate(close, function () { if (float.gid) float.dismissed[float.gid] = true; renderFloat(); });
      open.tabIndex = 0; close.tabIndex = 0;
      head.appendChild(float.title); head.appendChild(open); head.appendChild(close);
      float.body = el('div', 'kv-float-body');
      float.el.appendChild(head); float.el.appendChild(float.body);
      document.body.appendChild(float.el);
    }
    if (float.gid !== gid) {
      if (float.stage) float.stage.destroy();
      float.stage = createStage(float.body, 'float');
      float.gid = gid;
    }
    float.el.hidden = false;
    var g = stageGroup(gid, null);
    float.title.textContent = '👥 ' + g.name + ' is working together';
    float.stage.update(g);
  }

  var KelvinUI = {
    mountGroupTeam: mountGroupTeam,

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
          if (d.message && d.message.role === 'member') (groupDone[d.group_id] = groupDone[d.group_id] || {})[d.message.author] = now;
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
