/**
 * Talk to RAPR hands-free (the composer's voice button).
 *
 * Local (free, the default):
 *   you speak → the browser's speech recognition (or Whisper on this PC, for
 *   privacy or browsers without it) → your session. The reply is read out a
 *   sentence at a time in a natural voice made on this PC (Kokoro), so it starts
 *   talking right away. Talk over it to interrupt.
 *
 * Live (needs an OpenAI or Gemini API key):
 *   a phone-call-like conversation with Kelvin. The provider's speech model
 *   hears you as you speak, answers in about half a second and stops when you
 *   interrupt. Real work goes to your RAPR sessions (run_task) and Kelvin reads
 *   you the result.
 *
 * Settings → Voices → "Hands-free voice" picks the mode.
 */
(function () {
  const MODE_KEY = 'rapr_voice_mode';   // local | local-private | live | live-openai | live-gemini
  let _mode = 'local';
  try { _mode = localStorage.getItem(MODE_KEY) || 'local'; } catch (_) {}
  let _ttsBackend = 'offline';
  let _status = null;
  let _session = null;        // the running hands-free session (local or live)

  window._handsFree = false;

  const csrf = () => (typeof _csrfToken === 'function' ? _csrfToken() : '');
  const toast = (kind, msg) => { if (typeof _toast === 'function') _toast(kind, msg); };

  async function refreshStatus() {
    try {
      const r = await fetch('/tts/status');
      _status = await r.json();
      _ttsBackend = _status.backend || 'offline';
    } catch (_) {}
    _renderModeStatus();
    return _status;
  }

  // ── Caption pill: what Kelvin is doing right now ─────────────────────────────
  function caption(text) {
    let el = document.getElementById('talk-caption');
    if (!text) { if (el) el.remove(); return; }
    if (!el) {
      el = document.createElement('div');
      el.id = 'talk-caption';
      el.setAttribute('role', 'status');
      el.style.cssText = 'position:fixed;left:50%;bottom:96px;transform:translateX(-50%);z-index:9999;' +
        'max-width:min(560px,calc(100vw - 32px));padding:8px 14px;border-radius:18px;font-size:13px;' +
        'background:var(--bg-elevated,#1e1e24);color:var(--text,#eee);box-shadow:0 4px 18px rgba(0,0,0,.35);' +
        'cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis';
      el.title = 'Click to stop hands-free';
      el.onclick = () => stopHandsFree();
      document.body.appendChild(el);
    }
    el.textContent = text;
  }

  // ── Text → sentences that sound right ────────────────────────────────────────
  function speakableText(t) {
    return String(t || '')
      .replace(/```[\s\S]*?(```|$)/g, ' (code is in the chat) ')
      .replace(/`([^`]*)`/g, '$1')
      .replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1')
      .replace(/https?:\/\/\S+/g, 'a link')
      .replace(/^\s{0,3}(#{1,6}|>|[-*+]|\d+\.)\s+/gm, '')
      .replace(/(\*\*|__|\*|_|~~)(.+?)\1/g, '$2')
      .replace(/^\s*\|.*\|\s*$/gm, '')
      .replace(/[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}\u{200D}]/gu, '')
      .replace(/[ \t]+/g, ' ')
      .trim();
  }

  /** Short first chunk (so speech starts fast), then chunks of a sentence or two. */
  function sentences(text, maxChars = 2400) {
    let t = speakableText(text);
    let tail = '';
    if (t.length > maxChars) { t = t.slice(0, maxChars).replace(/\s+\S*$/, ''); tail = 'The rest is in the chat.'; }
    const raw = t.match(/[^.!?\n]+(?:[.!?]+["')\]]*|\n|$)/g) || [];
    const out = [];
    for (let s of raw) {
      s = s.replace(/\s+/g, ' ').trim();
      if (!s) continue;
      const last = out[out.length - 1];
      if (out.length > 1 && last && (last.length + s.length) < 180) out[out.length - 1] = last + ' ' + s;
      else out.push(s);
    }
    if (tail) out.push(tail);
    return out;
  }

  // ── Speaker: plays replies sentence by sentence; stop() for barge-in ────────
  const Speaker = {
    gen: 0, speaking: false, recent: '', playing: null,

    speak(ai, text) {
      this.stop();
      const parts = sentences(text);
      if (!parts.length) return;
      const g = ++this.gen;
      this.speaking = true;
      if (_ttsBackend === 'offline') refreshStatus();     // the natural voice may be ready by the next reply
      if (_session && _session.onSpeak) _session.onSpeak(true);
      this._run(g, ai, parts);
    },

    async _run(g, ai, parts) {
      const server = _ttsBackend === 'kokoro' || _ttsBackend === 'elevenlabs';
      let next = server ? this._fetch(parts[0], ai) : null;
      for (let i = 0; i < parts.length; i++) {
        if (g !== this.gen) return;
        this.recent = (parts[i - 1] || '') + ' ' + parts[i];
        caption('🔊 ' + parts[i]);
        if (server) {
          const cur = next;
          next = i + 1 < parts.length ? this._fetch(parts[i + 1], ai) : null;
          const blob = await cur;
          if (g !== this.gen) return;
          if (blob) await this._play(blob); else await this._browser(parts[i], ai);
        } else {
          await this._browser(parts[i], ai);
        }
      }
      if (g === this.gen) this._done();
    },

    _fetch(text, ai) {
      return fetch('/tts', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'x-csrf-token': csrf()},
        body: JSON.stringify({text, ai: ai || 'kelvin'}),
      }).then(r => (r.ok ? r.blob() : null)).catch(() => null);
    },

    _play(blob) {
      return new Promise(resolve => {
        const url = URL.createObjectURL(blob);
        const a = new Audio(url);
        const done = () => { URL.revokeObjectURL(url); if (this.playing === a) this.playing = null; resolve(); };
        a._done = done;
        a.onended = done; a.onerror = done;
        this.playing = a;
        a.play().catch(done);
      });
    },

    _browser(text, ai) {
      return new Promise(resolve => {
        if (!window.speechSynthesis) return resolve();
        const u = new SpeechSynthesisUtterance(text);
        const v = typeof voiceFor === 'function' ? voiceFor(ai) : null;
        if (v) { u.voice = v; u.lang = v.lang; }
        u.rate = 1.05;
        u.onend = resolve; u.onerror = resolve;
        speechSynthesis.speak(u);
      });
    },

    _done() {
      if (!this.speaking) return;
      this.speaking = false;
      this.recent = '';
      if (_session && _session.onSpeak) _session.onSpeak(false);
    },

    stop() {
      this.gen++;
      const a = this.playing;
      if (a) { this.playing = null; try { a.pause(); } catch (_) {} a._done && a._done(); }
      if (window.speechSynthesis) try { speechSynthesis.cancel(); } catch (_) {}
      this._done();
    },
  };

  /** Is what the mic heard just our own voice coming back from the speakers? */
  function isEcho(heard) {
    if (!Speaker.speaking || !Speaker.recent) return false;
    const words = s => String(s).toLowerCase().match(/[a-z0-9']+/g) || [];
    const said = new Set(words(Speaker.recent));
    const w = words(heard);
    if (!w.length) return true;
    return w.filter(x => said.has(x)).length / w.length >= 0.6;
  }

  function submit(text) {
    text = (text || '').trim();
    if (text.length < 2) return;
    const inp = document.getElementById('inp');
    if (!inp || typeof send !== 'function') return;
    inp.value = text;
    send();
    caption('⏳ ' + text);
  }

  // ── Microphone as PCM frames (used by Whisper mode and Gemini Live) ─────────

  async function openMic(onFrames) {
    const stream = await navigator.mediaDevices.getUserMedia(
      {audio: {echoCancellation: true, noiseSuppression: true, autoGainControl: true}});
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const src = ctx.createMediaStreamSource(stream);
    let node;
    try {
      // AudioWorklet runs off the main thread; if it can't load, use the older ScriptProcessor.
      await Promise.race([ctx.audioWorklet.addModule('/js/talk_worklet.js?v=1'),
        new Promise((_, reject) => setTimeout(() => reject(new Error('worklet timeout')), 3000))]);
      node = new AudioWorkletNode(ctx, 'rapr-capture');
      node.port.onmessage = e => onFrames(e.data, ctx.sampleRate);
      src.connect(node);
    } catch (_) {
      node = ctx.createScriptProcessor(2048, 1, 1);
      node.onaudioprocess = e => onFrames(e.inputBuffer.getChannelData(0).slice(0), ctx.sampleRate);
      const mute = ctx.createGain(); mute.gain.value = 0;
      src.connect(node); node.connect(mute); mute.connect(ctx.destination);
    }
    return {stream, ctx, close() { try { node.disconnect(); src.disconnect(); } catch (_) {} stream.getTracks().forEach(t => t.stop()); ctx.close().catch(() => {}); }};
  }

  function downsample(frames, rate, target = 16000) {
    if (rate === target) return frames;
    const ratio = rate / target, n = Math.floor(frames.length / ratio), out = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const a = Math.floor(i * ratio), b = Math.min(frames.length, Math.floor((i + 1) * ratio));
      let s = 0; for (let j = a; j < b; j++) s += frames[j];
      out[i] = s / Math.max(1, b - a);
    }
    return out;
  }

  function toInt16(f32) {
    const out = new Int16Array(f32.length);
    for (let i = 0; i < f32.length; i++) { const s = Math.max(-1, Math.min(1, f32[i])); out[i] = s < 0 ? s * 0x8000 : s * 0x7fff; }
    return out;
  }

  function wav16k(f32) {
    const pcm = toInt16(f32), buf = new ArrayBuffer(44 + pcm.length * 2), v = new DataView(buf);
    const w = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
    w(0, 'RIFF'); v.setUint32(4, 36 + pcm.length * 2, true); w(8, 'WAVEfmt ');
    v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
    v.setUint32(24, 16000, true); v.setUint32(28, 32000, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
    w(36, 'data'); v.setUint32(40, pcm.length * 2, true);
    new Int16Array(buf, 44).set(pcm);
    return new Blob([buf], {type: 'audio/wav'});
  }

  function b64(int16) {
    const bytes = new Uint8Array(int16.buffer);
    let s = '';
    for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    return btoa(s);
  }

  // ── Local mode, browser speech recognition (fastest) ────────────────────────
  function startBrowserListening() {
    const C = window.SpeechRecognition || window.webkitSpeechRecognition;
    const r = new C();
    r.lang = navigator.language || 'en-US';
    r.continuous = true;
    r.interimResults = true;
    let alive = true;
    r.onresult = e => {
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const res = e.results[i], text = (res[0] && res[0].transcript || '').trim();
        if (!text) continue;
        if (Speaker.speaking) {
          if (isEcho(text)) continue;
          if (text.split(/\s+/).length >= 2 || res.isFinal) Speaker.stop();      // you talked over it
        }
        if (res.isFinal) submit(text);
        else caption('🎙 ' + text);
      }
    };
    r.onend = () => { if (alive && window._handsFree) try { r.start(); } catch (_) {} };
    r.onerror = e => {
      if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
        toast('error', 'Microphone access was refused.'); stopHandsFree();
      }
    };
    try { r.start(); } catch (_) {}
    caption('🎙 Listening… just talk');
    return {stop() { alive = false; try { r.stop(); } catch (_) {} }};
  }

  // ── Local mode, Whisper on this PC (private; any browser) ───────────────────
  async function startWhisperListening() {
    const PRE = 0.3, END_SILENCE = 0.7, MIN_SPEECH = 0.25, MAX_LEN = 30;
    let floor = 0.01, voiced = 0, silent = 0, inSpeech = false, rate = 48000;
    let pre = [], utter = [], busy = false;
    const mic = await openMic((frames, sr) => {
      rate = sr;
      let e = 0; for (let i = 0; i < frames.length; i++) e += frames[i] * frames[i];
      const rms = Math.sqrt(e / frames.length), dt = frames.length / sr;
      const loud = rms > Math.max(floor * 3, 0.015) * (Speaker.speaking ? 1.8 : 1);
      if (!inSpeech) floor = floor * 0.995 + rms * 0.005;
      if (loud) { voiced += dt; silent = 0; } else { silent += dt; if (!inSpeech) voiced = Math.max(0, voiced - dt); }
      if (!inSpeech) {
        pre.push(frames);
        while (pre.length * dt > PRE) pre.shift();
        if (voiced >= MIN_SPEECH) {
          inSpeech = true; utter = pre.slice(); pre = [];
          if (Speaker.speaking) Speaker.stop();
          caption('🎙 Listening…');
        }
        return;
      }
      utter.push(frames);
      const len = utter.length * dt;
      if (silent >= END_SILENCE || len >= MAX_LEN) {
        inSpeech = false; voiced = 0; silent = 0;
        const all = new Float32Array(utter.reduce((n, f) => n + f.length, 0));
        let o = 0; utter.forEach(f => { all.set(f, o); o += f.length; });
        utter = [];
        transcribe(downsample(all, rate));
      }
    });

    async function transcribe(f32) {
      if (busy) return;
      busy = true;
      caption('✍️ Transcribing…');
      try {
        const form = new FormData();
        form.append('file', wav16k(f32), 'speech.wav');
        const r = await fetch('/transcribe', {method: 'POST', headers: {'x-csrf-token': csrf()}, body: form});
        const d = await r.json();
        if (d.text) submit(d.text); else caption('🎙 Listening… just talk');
      } catch (_) {
        caption('🎙 Listening… just talk');
      } finally { busy = false; }
    }
    caption('🎙 Listening (Whisper on this PC)… just talk');
    return {stop() { mic.close(); }};
  }

  // ── Live: OpenAI Realtime over WebRTC ───────────────────────────────────────
  async function startOpenAI(sess) {
    const pc = new RTCPeerConnection();
    const audio = new Audio(); audio.autoplay = true;
    pc.ontrack = e => { audio.srcObject = e.streams[0]; };
    const mic = await navigator.mediaDevices.getUserMedia(
      {audio: {echoCancellation: true, noiseSuppression: true, autoGainControl: true}});
    pc.addTrack(mic.getTracks()[0], mic);
    const dc = pc.createDataChannel('oai-events');
    const sendEv = ev => { if (dc.readyState === 'open') dc.send(JSON.stringify(ev)); };
    let said = '';
    dc.onmessage = e => {
      let ev; try { ev = JSON.parse(e.data); } catch (_) { return; }
      if (ev.type === 'input_audio_buffer.speech_started') caption('🎙 Listening…');
      else if (ev.type === 'response.output_audio_transcript.delta') { said += ev.delta || ''; caption('🐧 ' + said); }
      else if (ev.type === 'response.done') said = '';
      else if (ev.type === 'response.function_call_arguments.done' && ev.name === 'run_task') {
        let args = {}; try { args = JSON.parse(ev.arguments || '{}'); } catch (_) {}
        sendEv({type: 'conversation.item.create', item: {type: 'function_call_output', call_id: ev.call_id,
          output: JSON.stringify({status: 'started; the result will follow'})}});
        sendEv({type: 'response.create'});
        runTask(args, result => {
          sendEv({type: 'conversation.item.create', item: {type: 'message', role: 'user',
            content: [{type: 'input_text', text: result}]}});
          sendEv({type: 'response.create'});
        });
      } else if (ev.type === 'error') {
        toast('error', 'Live voice: ' + ((ev.error && ev.error.message) || 'error'));
      }
    };
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    const r = await fetch(sess.calls_url, {method: 'POST', body: offer.sdp,
      headers: {Authorization: 'Bearer ' + sess.token, 'Content-Type': 'application/sdp'}});
    if (!r.ok) { pc.close(); mic.getTracks().forEach(t => t.stop()); throw new Error('OpenAI ' + r.status + ': ' + (await r.text()).slice(0, 160)); }
    await pc.setRemoteDescription({type: 'answer', sdp: await r.text()});
    caption('🐧 Live with Kelvin (OpenAI). Just talk.');
    return {stop() { try { dc.close(); } catch (_) {} pc.close(); mic.getTracks().forEach(t => t.stop()); audio.srcObject = null; }};
  }

  // ── Live: Gemini Live over WebSocket ────────────────────────────────────────
  async function startGemini(sess) {
    const ws = new WebSocket(sess.ws_url);
    const out = new (window.AudioContext || window.webkitAudioContext)({sampleRate: 24000});
    let playAt = 0, sources = [], mic = null, said = '', heard = '';
    const sendJ = o => { if (ws.readyState === 1) ws.send(JSON.stringify(o)); };
    const flush = () => { sources.forEach(s => { try { s.stop(); } catch (_) {} }); sources = []; playAt = 0; };
    const play = data => {
      const bin = atob(data), n = bin.length >> 1, f = new Float32Array(n);
      for (let i = 0; i < n; i++) { let v = bin.charCodeAt(2 * i) | (bin.charCodeAt(2 * i + 1) << 8); if (v >= 0x8000) v -= 0x10000; f[i] = v / 0x8000; }
      const buf = out.createBuffer(1, n, 24000); buf.copyToChannel(f, 0);
      const s = out.createBufferSource(); s.buffer = buf; s.connect(out.destination);
      playAt = Math.max(playAt, out.currentTime + 0.03);
      s.start(playAt); playAt += buf.duration;
      s.onended = () => { sources = sources.filter(x => x !== s); };
      sources.push(s);
    };

    await new Promise((resolve, reject) => {
      const t = setTimeout(() => reject(new Error('Gemini did not answer')), 15000);
      ws.onerror = () => { clearTimeout(t); reject(new Error('Could not connect to Gemini Live')); };
      ws.onopen = () => sendJ(sess.setup);
      ws.onclose = e => { clearTimeout(t); if (window._handsFree && _session && _session.provider === 'gemini') { toast('warning', 'Gemini Live ended' + (e.reason ? ': ' + e.reason : '') + '.'); stopHandsFree(); } reject(new Error(e.reason || 'Gemini closed the connection')); };
      ws.onmessage = async e => {
        let m; try { m = JSON.parse(typeof e.data === 'string' ? e.data : await e.data.text()); } catch (_) { return; }
        if (m.setupComplete) { clearTimeout(t); resolve(); return; }
        const sc = m.serverContent;
        if (sc) {
          if (sc.interrupted) { flush(); said = ''; }
          ((sc.modelTurn && sc.modelTurn.parts) || []).forEach(p => { if (p.inlineData && p.inlineData.data) play(p.inlineData.data); });
          if (sc.inputTranscription && sc.inputTranscription.text) { heard += sc.inputTranscription.text; caption('🎙 ' + heard); }
          if (sc.outputTranscription && sc.outputTranscription.text) { said += sc.outputTranscription.text; heard = ''; caption('🐧 ' + said); }
          if (sc.turnComplete) said = '';
        }
        ((m.toolCall && m.toolCall.functionCalls) || []).forEach(fc => {
          sendJ({toolResponse: {functionResponses: [{id: fc.id, name: fc.name, response: {result: 'started; the result will follow'}}]}});
          if (fc.name === 'run_task') runTask(fc.args || {}, result => sendJ({realtimeInput: {text: result}}));
        });
      };
    });

    let pending = [], pendingLen = 0;
    mic = await openMic((frames, sr) => {
      const f = downsample(frames, sr);
      pending.push(f); pendingLen += f.length;
      if (pendingLen < 1600) return;                     // ~100 ms per message
      const all = new Float32Array(pendingLen); let o = 0;
      pending.forEach(x => { all.set(x, o); o += x.length; });
      pending = []; pendingLen = 0;
      sendJ({realtimeInput: {audio: {data: b64(toInt16(all)), mimeType: 'audio/pcm;rate=16000'}}});
    });
    caption('🐧 Live with Kelvin (Gemini). Just talk.');
    return {provider: 'gemini', stop() { mic && mic.close(); flush(); try { ws.close(); } catch (_) {} out.close().catch(() => {}); }};
  }

  /** Live voice handed Kelvin a task: run it in RAPR, give the reply back to Kelvin. */
  async function runTask(args, deliver) {
    const task = (args.task || '').trim();
    if (!task) return;
    caption('🛠 ' + task);
    let reply = '';
    try {
      const r = await fetch('/voice/live/task', {method: 'POST',
        headers: {'Content-Type': 'application/json', 'x-csrf-token': csrf()},
        body: JSON.stringify({task, ai: args.ai || ''})});
      const d = await r.json();
      reply = d.reply || d.error || '(no output)';
    } catch (e) { reply = 'The task could not be sent: ' + e.message; }
    if (!window._handsFree || !_session || !_session.live) return;
    deliver('[Result from RAPR for "' + task.slice(0, 200) + '"]\n' + reply.slice(0, 6000) +
      '\n\n(Tell me the gist out loud in one to three sentences. The full reply is in the chat.)');
  }

  // ── Start / stop ────────────────────────────────────────────────────────────
  function _voiceAvailable() {
    return !!(window.SpeechRecognition || window.webkitSpeechRecognition ||
      (navigator.mediaDevices && navigator.mediaDevices.getUserMedia && (window.AudioContext || window.webkitAudioContext)));
  }

  async function startLive(st) {
    const provider = _mode === 'live-openai' ? 'openai' : _mode === 'live-gemini' ? 'gemini' : '';
    const r = await fetch('/voice/live/session', {method: 'POST',
      headers: {'Content-Type': 'application/json', 'x-csrf-token': csrf()}, body: JSON.stringify({provider})});
    const sess = await r.json();
    if (!r.ok) throw new Error(sess.error || 'Live voice is unavailable');
    const s = sess.provider === 'openai' ? await startOpenAI(sess) : await startGemini(sess);
    s.live = true; s.provider = sess.provider;
    return s;
  }

  async function startLocal(st) {
    fetch('/tts/prepare', {method: 'POST', headers: {'x-csrf-token': csrf()}}).catch(() => {});
    const browser = window.SpeechRecognition || window.webkitSpeechRecognition;
    const s = (_mode === 'local-private' || !browser) ? await startWhisperListening() : startBrowserListening();
    s.onSpeak = on => { if (!on) caption('🎙 Listening… just talk'); };
    return s;
  }

  async function toggleHandsFree() {
    if (window._handsFree) { stopHandsFree(); return; }
    if (!_voiceAvailable()) { toast('warning', 'This browser cannot use the microphone for hands-free voice.'); return; }
    window._handsFree = true;
    _markHandsFree();
    caption('… starting voice');
    const st = await refreshStatus();
    try {
      if (_mode.startsWith('live')) {
        try { _session = await startLive(st); }
        catch (e) {
          if (!window._handsFree) return;
          toast('warning', e.message + ' Using local voice instead.');
          _session = await startLocal(st);
        }
      } else {
        _session = await startLocal(st);
      }
      if (!window._handsFree) { _session && _session.stop(); _session = null; }
    } catch (e) {
      toast('error', 'Hands-free voice could not start: ' + (e.message || e));
      stopHandsFree();
    }
  }

  function stopHandsFree() {
    window._handsFree = false;
    Speaker.stop();
    if (_session) { try { _session.stop(); } catch (_) {} _session = null; }
    caption('');
    _markHandsFree();
  }

  function _markHandsFree() {
    const b = document.getElementById('handsfree-btn');
    if (b) { b.classList.toggle('active', window._handsFree); b.title = window._handsFree ? 'Hands-free is on (click to stop)' : 'Hands-free: talk instead of typing'; }
    if (typeof _updateComposer === 'function') _updateComposer();
  }

  /** A reply arrived while hands-free is on: read it out (local mode; Live speaks for itself). */
  function speakReplyHandsFree(ai, text) {
    if (!window._handsFree || !text || (_session && _session.live)) return;
    Speaker.speak(ai, text);
  }

  // ── Settings → Voices ───────────────────────────────────────────────────────
  function setVoiceMode(mode) {
    _mode = mode || 'local';
    try { localStorage.setItem(MODE_KEY, _mode); } catch (_) {}
    if (window._handsFree) { stopHandsFree(); toggleHandsFree(); }
    _renderModeStatus();
  }

  function _renderModeStatus() {
    const sel = document.getElementById('st-voice-mode');
    if (sel && sel.value !== _mode) sel.value = _mode;
    const el = document.getElementById('voice-mode-status');
    if (!el || !_status) return;
    const local = _status.local || {}, live = _status.live || {};
    const voice = _status.backend === 'kokoro' ? 'natural voice ready (Kokoro, on this PC)'
      : _status.backend === 'elevenlabs' ? 'ElevenLabs voice'
      : local.status === 'preparing' ? 'downloading the natural voice (~120 MB, one time)…'
      : local.status === 'error' ? 'natural voice unavailable (' + (local.error || 'error') + '); using the browser voice'
      : 'natural voice downloads the first time you use hands-free';
    const keys = [live.gemini && 'Gemini', live.openai && 'OpenAI'].filter(Boolean);
    el.textContent = 'Local: ' + voice + '. Live: ' + (keys.length ? keys.join(' and ') + ' key set.' : 'add an OpenAI or Gemini API key to use it.');
  }

  window.toggleHandsFree = toggleHandsFree;
  window.stopHandsFree = stopHandsFree;
  window.speakReplyHandsFree = speakReplyHandsFree;
  window.setVoiceMode = setVoiceMode;
  window.refreshVoiceStatus = refreshStatus;
  window._voiceAvailable = _voiceAvailable;
  window._talk = {sentences, speakableText, isEcho, Speaker};   // for tests and the console

  const orig = window.openSettings;
  if (typeof orig === 'function') {
    window.openSettings = function () { const r = orig.apply(this, arguments); refreshStatus(); return r; };
  }
})();
