/**
 * KelvinUI maps live WebSocket events to Kelvin's mood and drives every Kelvin on
 * the page: the header, the crew strip, group-chat stages. core.js forwards events
 * via KelvinUI.onWs(). Kelvin himself (drawing, physics) is in kelvin.js, which
 * loads first.
 */
(function () {
  'use strict';

  var mount = Kelvin.mount;
  var STATES = Kelvin.STATES;

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
    Kelvin.setStill(ui.mode === 'still');
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
