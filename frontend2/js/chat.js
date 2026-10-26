// The web UI's main script, part 3 of 8. index.html loads the parts in order.
// --- Thinking (per-session) ------------------------------------------------------------------------------
// Track which sessions are currently "thinking" so we can show/hide the
// indicator correctly when sessions run in parallel or the user switches focus.
const _thinkingState = {};   // { session_id: { active: bool, ai: string } }
let _thinkingTimer = null;
let _thinkingMsgIdx = 0;

// Fun one-liners + feature discovery tips (prefixed with 💡)
const _thinkingMessages = [
  // ── Kelvin, the RAPR penguin ──
  "Kelvin is typing with both flippers...",
  "Kelvin is sliding through your code belly-first...",
  "Kelvin is checking under the iceberg...",
  "Fish break later, answer first...",
  "Kelvin is waddling between files...",
  // ── Fun one-liners ──
  "Crunching the numbers...",
  "Consulting the digital oracle...",
  "Teaching electrons to think...",
  "Brewing some fresh ideas...",
  "Asking the rubber duck...",
  "Warming up the brain cells...",
  "Untangling the spaghetti code...",
  "Downloading more RAM...",
  "Feeding the hamster that powers this...",
  "Polishing the pixels...",
  "Summoning the code wizards...",
  "Rearranging the bits and bytes...",
  "Making the magic happen...",
  "Calibrating the flux capacitor...",
  "Consulting Stack Overflow... just kidding",
  "Thinking at the speed of light... almost",
  "Rolling up the sleeves...",
  "Channeling inner genius...",
  "Converting caffeine to code...",
  "Assembling the answer...",
  "Running on pure vibes...",
  "Almost there... probably...",
  "Convincing the AI hamsters to run faster...",
  "Sprinkling some AI magic...",
  "Loading awesome sauce...",
  "Doing complicated math in my head...",
  "Please hold, your call is important to us...",
  // ── Feature tips ──
  "💡 New: Watch AI work live — each file read and command shows up as a step in chat",
  "💡 New: Type /model to list available models live and switch any CLI's model",
  "💡 Tip: Build custom Agents — chain steps visually in the Agent Builder",
  "💡 Tip: Import and export Agents as JSON to share them",
  "💡 Tip: Check Agent run statistics from the Agents panel",
  "💡 New: Group Chats 👥 — put several AIs in one chat and @mention who should answer",
  "💡 Tip: Open AI Council ⚖️ — multiple AIs debate your question and agree on an answer",
  "💡 Tip: Click the mic 🎤 to send a voice message instead of typing",
  "💡 Tip: Upload a video demo — AI analyzes it and replicates the workflow",
  "💡 Tip: AI can control your browser through the Chrome extension",
  "💡 Tip: Risky commands pause for your approval — watch for the approval banner",
  "💡 Tip: Add any CLI tool as a custom AI in Settings",
  "💡 Tip: Vector memory finds related facts even when the wording differs",
  "💡 Tip: The learning system improves AI from your past runs — auto-enabled",
  "💡 Tip: Protect access with a PIN — set it in Settings → Security",
  "💡 Tip: Install RAPR AI as a desktop app — use your browser's Install button",
  "💡 Tip: Toggle light/dark theme with the 🌙 button in the toolbar",
  "💡 Tip: Use /remember to save facts AI will recall later",
  "💡 Tip: Schedule tasks — say \"every morning at 9am, summarize my emails\"",
  "💡 Tip: Heartbeat monitors your pending tasks and reminds you via Telegram",
  "💡 Tip: Transfer knowledge from ChatGPT/Gemini — click 🔄 Transfer in Memory",
  "💡 Tip: Set Custom Instructions in Settings — all AIs will follow them",
  "💡 Tip: Name your AI in Settings → Personalization",
  "💡 Tip: Run 4+ sessions in parallel — each with its own AI and project folder",
  "💡 Tip: Control RAPR AI from your phone with the Telegram bot",
  "💡 Tip: Use Pipelines to chain multiple AI steps into one workflow",
  "💡 Tip: Install plugins from the marketplace — GitHub is live!",
  "💡 Tip: MCP servers give AI live access to your repos and databases",
  "💡 Tip: Set daily budget caps in Settings to control AI usage costs",
  "💡 Tip: All your API keys and tokens are encrypted with Fernet at rest",
  "💡 Tip: Back up your data — go to Settings → Cloud Backup",
  "💡 Tip: Pin important memories so AI always sees them in every prompt",
  "💡 Tip: Use templates to save and reuse session configurations",
  "💡 Tip: Drag & drop files into the chat to share them with AI",
  "💡 Tip: AI auto-retries on failure and can switch to a fallback model",
  "💡 Tip: Search your entire chat history with the search bar",
  "💡 Tip: Switch AI mid-conversation — click the AI chip at the top",
  // ── Prompting tips ──
  "✏️ Be specific — \"refactor auth.py to use async\" beats \"fix my code\"",
  "✏️ Give context — mention the language, framework, and what you've tried",
  "✏️ One task at a time — split complex requests into focused prompts",
  "✏️ Ask for alternatives — \"give me 3 approaches\" surfaces better options",
  "✏️ Include examples — show what input/output you expect",
  "✏️ Say \"explain your reasoning\" to catch logic mistakes early",
  "✏️ Specify the format — \"respond in bullet points\" or \"give me a table\"",
  "✏️ Mention constraints — \"keep it under 50 lines\" or \"use no dependencies\"",
  "✏️ Don't be afraid to say \"try again\" — AI gets better with feedback",
  "✏️ Start with \"you are a [role]\" to set the right expertise level",
  // ── Skills tips ──
  "🛠️ 75 skills built in — AI auto-picks the right one for your task",
  "🛠️ Skill: Playwright — automate browsers, fill forms, take screenshots",
  "🛠️ Skill: Docker CLI — manage containers and compose stacks via chat",
  "🛠️ Skill: AWS CLI — manage S3, Lambda, EC2, DynamoDB from right here",
  "🛠️ Skill: GitHub CLI — create PRs, manage issues, trigger Actions",
  "🛠️ Skill: Terraform — deploy infrastructure as code via natural language",
  "🛠️ Skill: Firebase — manage Firestore, Hosting, Functions, Auth",
  "🛠️ Skill: Kubernetes — manage pods, deployments, services via kubectl",
  "🛠️ Skill: Supabase — manage Postgres, Auth, Storage, Edge Functions",
  "🛠️ Skill: Stripe CLI — test webhooks, manage payments and subscriptions",
  "🛠️ Skill: Redis — cache operations, pub/sub, key management",
  "🛠️ Skill: MongoDB — database queries, aggregations, index management",
  "🛠️ Skill: Vercel — deploy and manage Next.js apps",
  "🛠️ Skill: Cloudflare — Workers, Pages, R2 storage, KV, DNS",
  "🛠️ Skill: FireCrawl — scrape websites and extract clean markdown",
  "🛠️ Skill: Web Search — search DuckDuckGo, Google, Brave from chat",
  "🛠️ Skill: File Organizer — batch sort, rename, detect duplicate files",
  "🛠️ Skill: Webapp Testing — automated testing with Playwright",
  "🛠️ Skill: Prisma — database ORM, migrations, and schema management",
  "🛠️ Skill: Azure CLI — App Service, Functions, CosmosDB, AKS",
  "🛠️ Skill: Google Cloud — Compute, Cloud Run, BigQuery, GCS",
  "🛠️ Skill: Twilio — send SMS, voice calls, messaging via chat",
  "🛠️ Skill: Skill Creator — create your own custom skills!",
  "🛠️ Browse the marketplace for more skills — click RAPR Packages",
  "🛠️ Skills auto-inject best practices — your AI becomes an expert instantly",
];

function setThinking(active, ai, session_id){
  // Update per-session tracking
  if(session_id){
    if(active) _thinkingState[session_id] = { active: true, ai: ai };
    else        delete _thinkingState[session_id];
  }
  // Show the indicator only for the focused session
  _refreshThinkingUI();
}

function _refreshThinkingUI(){
  const el      = document.getElementById('thinking');
  const focused = _thinkingState[_focusedId];
  if(focused && focused.active){
    el.className = 'on';
    // Show the first label immediately (session name + thinking)
    const k     = focused.ai || _focusedAi || activeAi || '';
    const sess  = _sessions.find(s => s.id === _focusedId);
    const label = sess ? (sess.emoji + ' ' + sess.name) : (AI_LABEL[k] || 'AI');
    const thlabel = document.getElementById('thlabel');
    if(!_thinkingTimer){
      thlabel.textContent = label + ' is thinking...';
      // After 3s, start rotating fun messages
      _thinkingMsgIdx = Math.floor(Math.random() * _thinkingMessages.length);
      _thinkingTimer = setInterval(() => {
        thlabel.textContent = _thinkingMessages[_thinkingMsgIdx % _thinkingMessages.length];
        _thinkingMsgIdx++;
      }, 3000);
    }
    scroll();
  } else {
    el.className = '';
    if(_thinkingTimer){ clearInterval(_thinkingTimer); _thinkingTimer = null; }
  }
  _updateComposer();
}

// --- Logo watermark helpers ------------------------------------------------------------------------------
function _clearMessages(){
  // Remove all message groups but keep #chat-logo-bg and Kelvin's greeting intact
  const wrap = document.getElementById('messages');
  [...wrap.children].forEach(el => { if(el.id !== 'chat-logo-bg' && el.id !== 'kelvin-hello') el.remove(); });
  wrap.classList.remove('has-messages');
}
function _updateLogoState(){
  const wrap = document.getElementById('messages');
  // Count real message groups (exclude the logo bg div itself)
  const msgCount = wrap.querySelectorAll('.grp:not(.system), .grp.user, .grp.assistant').length;
  // Also count system bubbles that aren't the connecting placeholder
  const sysBubbles = [...wrap.querySelectorAll('.grp.system .bubble')]
    .filter(b => b.textContent !== 'Connecting to server...');
  const hasAny = msgCount > 0 || sysBubbles.length > 0;
  wrap.classList.toggle('has-messages', hasAny);
}

// --- Messages ------------------------------------------------------------------------------------------------
/** Strip fenced code blocks (```...```) from AI output so users see only the result */
function stripCodeBlocks(text){
  if(!text) return text;
  // Remove fenced code blocks: ```lang\n...\n``` (with optional language tag)
  let cleaned = text.replace(/```[\s\S]*?```/g, '');
  // Collapse multiple blank lines left behind into a single blank line
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n').trim();
  return cleaned || text; // fallback to original if everything was code
}
function renderMsg(m){
  if(m.role === 'assistant') _finishActivity();  // freeze live activity card when the reply lands
  const wrap = document.getElementById('messages');
  const placeholder = wrap.querySelector('.grp.system .bubble');
  if(placeholder && placeholder.textContent === 'Connecting to server...'){
    placeholder.closest('.grp').remove();
  }
  const grp = document.createElement('div');
  grp.className = 'grp ' + m.role;
  if(m.role !== 'system'){
    const meta = document.createElement('div');
    meta.className = 'meta';
    if(m.role==='user'){
      const via = m.source==='telegram' ? '<span class="via">via Telegram · </span>' : '';
      // Show session label on user messages when multiple sessions exist
      const sessTag = (m.session_name && _sessions.length > 1)
        ? `<span class="via">[${escHtml(m.session_emoji||'')} ${escHtml(m.session_name)}] </span>`
        : '';
      meta.innerHTML = sessTag + via + 'You';
    } else {
      const k = m.ai || '';
      const aiName = AI_LABEL[k] || k || 'AI';
      // Show session name badge if multiple sessions or session is identified
      const sessLabel = (m.session_name && _sessions.length > 1)
        ? ` <span style="font-size:10px;color:var(--muted);font-weight:normal">${escHtml(m.session_emoji||'')} ${escHtml(m.session_name)}</span>`
        : '';
      meta.innerHTML = `<span class="who ${k}">${escHtml(aiName)}</span>${sessLabel}`;
    }
    grp.appendChild(meta);
  }
  const bub = document.createElement('div');
  bub.className = 'bubble';
  bub.textContent = m.role === 'assistant' ? stripCodeBlocks(m.content) : m.content;
  grp.appendChild(bub);

  // Voice out: speaker button on assistant replies (+ optional auto-speak).
  if(m.role === 'assistant'){
    const speakable = (bub.textContent || '').trim();
    if(speakable){
      const spk = document.createElement('button');
      spk.className = 'msg-speak-btn';
      spk.title = 'Read aloud';
      spk.setAttribute('aria-label', 'Read message aloud');
      spk.textContent = '🔊';
      spk.onclick = () => speakText(speakable, spk);
      grp.appendChild(spk);
      if(window._autoSpeak) speakText(speakable, spk);
    }
  }

  wrap.appendChild(grp);
  _updateLogoState();
  scroll();
}

// --- Text-to-speech (voice out) -------------------------------------------------------------
let _ttsAudio = null;   // currently-playing HTMLAudioElement
function speakText(text, btn){
  if(!text) return;
  // Toggle: clicking again while playing stops it.
  if(_ttsAudio){
    try{ _ttsAudio.pause(); }catch(e){}
    if(_ttsAudio._url) URL.revokeObjectURL(_ttsAudio._url);
    _ttsAudio = null;
    if(btn) btn.textContent = '🔊';
    return;
  }
  if(btn) btn.textContent = '⏳';
  fetch('/tts', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({text})
  }).then(r => { if(!r.ok) throw new Error('tts failed'); return r.blob(); })
    .then(blob => {
      const url = URL.createObjectURL(blob);
      const a = new Audio(url);
      a._url = url;
      _ttsAudio = a;
      if(btn) btn.textContent = '⏸';
      a.onended = () => { URL.revokeObjectURL(url); _ttsAudio = null; if(btn) btn.textContent = '🔊'; };
      a.onerror = () => { URL.revokeObjectURL(url); _ttsAudio = null; if(btn) btn.textContent = '🔊'; };
      a.play();
    })
    .catch(() => { _ttsAudio = null; if(btn) btn.textContent = '🔊'; });
}
function toggleAutoSpeak(on){
  window._autoSpeak = !!on;
  try{ localStorage.setItem('rapr_auto_speak', on ? '1' : '0'); }catch(e){}
}
try{ window._autoSpeak = localStorage.getItem('rapr_auto_speak') === '1'; }catch(e){}
function scroll(){ const m = document.getElementById('messages'); m.scrollTop = m.scrollHeight; }

// --- Live activity timeline -----------------------------------------------------------------
// Rendered from 'activity' WS events emitted while a CLI agent (Claude/Codex/Gemini) works:
//   {phase:'step', n, label} per tool call · {phase:'note', label} for text · {phase:'done'}
function _ensureActivityStyle(){
  if(document.getElementById('activity-style')) return;
  const st = document.createElement('style');
  st.id = 'activity-style';
  st.textContent =
    '.activity-card{align-self:flex-start;max-width:74ch;width:fit-content;min-width:260px;margin:2px 0 4px;'
    + 'padding:10px 14px;background:var(--bg-surface,#16161d);border:1px solid var(--border-subtle,rgba(255,255,255,.09));'
    + 'border-radius:12px;animation:msgIn .22s ease;}'
    + '.activity-card.done{opacity:.75;}'
    + '.activity-card.done .activity-spinner{display:none;}'
    + '.activity-head{display:flex;align-items:center;gap:8px;}'
    + '.activity-title{font-size:12px;font-weight:600;color:var(--text-muted,#9aa0ab);'
    + 'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:60ch;}'
    + '.activity-spinner{width:11px;height:11px;flex-shrink:0;border-radius:50%;'
    + 'border:2px solid oklch(from var(--accent, #7c77dd) l c h / 0.25);border-top-color:var(--accent,#7c77dd);'
    + 'animation:activity-spin .8s linear infinite;}'
    + '.activity-steps{display:flex;flex-direction:column;gap:3px;margin-top:6px;}'
    + '.activity-steps:empty{margin-top:0;}'
    + '.activity-step{display:flex;align-items:center;gap:8px;font-size:12px;line-height:1.5;'
    + 'color:var(--text-muted,#aab);font-family:"JetBrains Mono",ui-monospace,monospace;}'
    + '.activity-tick{width:5px;height:5px;flex-shrink:0;border-radius:50%;background:var(--ok,#3fb950);}'
    + '.activity-label{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}'
    + '@keyframes activity-spin{to{transform:rotate(360deg)}}';
  document.head.appendChild(st);
}

function _activityCard(){
  const wrap = document.getElementById('messages');
  if(!wrap) return null;
  _ensureActivityStyle();
  let card = document.getElementById('activity-card');
  if(!card){
    card = document.createElement('div');
    card.id = 'activity-card';
    card.className = 'activity-card';
    card.innerHTML =
      '<div class="activity-head"><span class="activity-spinner"></span>'
      + '<span class="activity-title">Working…</span></div>'
      + '<div class="activity-steps"></div>';
    wrap.appendChild(card);
    wrap.classList.add('has-messages');
    scroll();
  }
  return card;
}

/** Freeze the live card: stop spinner, keep the step history in the transcript. */
function _finishActivity(){
  const card = document.getElementById('activity-card');
  if(!card) return;
  card.classList.add('done');
  const t = card.querySelector('.activity-title');
  if(t){
    const n = card.querySelectorAll('.activity-step').length;
    t.textContent = n ? `Done — ${n} step${n>1?'s':''}` : 'Done';
  }
  card.removeAttribute('id');  // next run gets a fresh card
}

function onActivity(d){
  if(!d || _viewingHistory) return;
  if(d.session_id && _focusedId && d.session_id !== _focusedId) return;
  if(d.phase === 'done'){ _finishActivity(); return; }
  const card = _activityCard();
  if(!card) return;
  if(d.phase === 'step'){
    const steps = card.querySelector('.activity-steps');
    const row  = document.createElement('div'); row.className = 'activity-step';
    const tick = document.createElement('span'); tick.className = 'activity-tick';
    const lab  = document.createElement('span'); lab.className = 'activity-label';
    lab.textContent = d.label || 'Working';
    row.appendChild(tick); row.appendChild(lab);
    steps.appendChild(row);
  } else if(d.phase === 'note'){
    const t = card.querySelector('.activity-title');
    if(t && d.label) t.textContent = d.label;
  }
  scroll();
}

// --- Send ------------------------------------------------------------------------------------------------------
function send(){
  const inp = document.getElementById('inp');
  const txt = inp.value.trim();
  if(!txt) return;
  if(!ws || ws.readyState !== 1){
    const banner = document.getElementById('conn-banner');
    if(banner && banner.style.display === 'none'){
      const bannerMsg = document.getElementById('conn-banner-msg');
      const bannerIcon = document.getElementById('conn-banner-icon');
      if(bannerMsg) bannerMsg.textContent = 'Cannot send — not connected to server';
      if(bannerIcon) bannerIcon.textContent = '⚠️';
      banner.className = 'conn-banner warn';
      banner.style.display = 'flex';
    }
    return;
  }
  let content = txt;
  if(_pendingContext){
    content = _pendingContext + txt;
    _pendingContext = '';
  }
  if(_viewingHistory) returnToLive();
  ws.send(JSON.stringify({type:'message', content:content}));
  inp.value = '';
  inp.style.height = 'auto';
  _updateComposer();
}

// --- Composer primary button -----------------------------------------------------------------------------------
// One button, like Claude and ChatGPT: Send when there's text, Stop while the AI
// is working and the box is empty, otherwise hands-free voice (talk.js; when the
// browser has no microphone access, a disabled Send).
const _COMPOSER_MODES = {
  send:  {title: 'Send (Enter)', label: 'Send message'},
  stop:  {title: 'Stop the AI', label: 'Stop the running task'},
  voice: {title: 'Talk hands-free: speak, and RAPR replies out loud', label: 'Start hands-free voice'},
  'voice-on': {title: 'Hands-free is on (click to stop)', label: 'Stop hands-free voice'},
};
function _composerMode(){
  const el = document.getElementById('inp');
  if(el && el.value.trim()) return 'send';
  if(_thinkingState[_focusedId] && _thinkingState[_focusedId].active) return 'stop';
  if(window._handsFree) return 'voice-on';
  if(typeof _voiceAvailable === 'function' ? _voiceAvailable() : (window.SpeechRecognition || window.webkitSpeechRecognition)) return 'voice';
  return 'send';
}
function _updateComposer(){
  const btn = document.getElementById('send');
  if(!btn) return;
  const mode = _composerMode();
  const el = document.getElementById('inp');
  btn.dataset.mode = mode;
  btn.title = _COMPOSER_MODES[mode].title;
  btn.setAttribute('aria-label', _COMPOSER_MODES[mode].label);
  btn.disabled = mode === 'send' && !(el && el.value.trim());
}
function composerPrimary(){
  const mode = _composerMode();
  if(mode === 'send') send();
  else if(mode === 'stop') cmd('interrupt');
  else if(typeof toggleHandsFree === 'function') toggleHandsFree();
  _updateComposer();
}
// --- File Upload ------------------------------------------------------------------------------------------------
let _uploadedFiles = [];

function _isAudioFile(file){
  const t = (file.type || '').toLowerCase();
  if(t.startsWith('audio/')) return true;
  const name = (file.name || '').toLowerCase();
  return /\.(mp3|wav|m4a|ogg|oga|opus|webm|flac|aac|amr)$/.test(name);
}

async function handleFileUpload(inputEl){
  const files = inputEl.files;
  if(!files || files.length === 0) return;
  const btn = document.getElementById('clip-btn');
  btn.classList.add('uploading');
  const names = [];
  const transcripts = [];
  for(const file of files){
    if(_isAudioFile(file)){
      // Audio uploads bypass /upload and go straight through Whisper,
      // so they can resolve a waiting Agent Builder input node as text.
      const form = new FormData();
      form.append('file', file, file.name || 'recording.webm');
      try {
        const resp = await fetch('/transcribe', {method:'POST', headers:{'x-csrf-token':_csrfToken()}, body:form});
        const data = await resp.json();
        if(data.error){
          alert('Transcription failed: ' + data.error);
        } else if(data.text){
          transcripts.push(data.text);
        }
      } catch(err) {
        console.error('Audio transcription failed:', err);
      }
      continue;
    }
    const form = new FormData();
    form.append('file', file);
    try {
      const resp = await fetch('/upload', {method:'POST', headers:{'x-csrf-token':_csrfToken()}, body:form});
      const data = await resp.json();
      if(data.filename) names.push(data.filename);
    } catch(err) {
      console.error('Upload failed:', err);
    }
  }
  btn.classList.remove('uploading');
  inputEl.value = '';
  const inp = document.getElementById('inp');
  if(names.length > 0){
    _uploadedFiles = _uploadedFiles.concat(names);
    const tag = names.map(n => `[📎 ${n}]`).join(' ');
    inp.value = (inp.value ? inp.value + ' ' : '') + tag + ' ';
  }
  if(transcripts.length > 0){
    inp.value = (inp.value ? inp.value + ' ' : '') + transcripts.join(' ') + ' ';
  }
  if(names.length > 0 || transcripts.length > 0){
    inp.focus();
    inp.dispatchEvent(new Event('input'));
  }
}

// --- Voice Recording --------------------------------------------------------------------------------------------
let _mediaRec = null;
let _audioChunks = [];
let _isRecording = false;
let _voiceTargetSession = null; // session that was focused when recording started

function toggleVoiceRec(){
  if(_isRecording) stopVoiceRec();
  else startVoiceRec();
}

async function startVoiceRec(){
  const btn = document.getElementById('mic-btn');
  // Capture the focused session at recording start so the message
  // goes to the right session even if user switches during transcription
  _voiceTargetSession = _focusedId || null;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({audio:true});
    _mediaRec = new MediaRecorder(stream, {mimeType: getSupportedMime()});
    _audioChunks = [];
    _mediaRec.ondataavailable = e => { if(e.data.size>0) _audioChunks.push(e.data); };
    _mediaRec.onstop = async () => {
      stream.getTracks().forEach(t=>t.stop());
      if(_audioChunks.length === 0) return;
      const blob = new Blob(_audioChunks, {type: _mediaRec.mimeType});
      await transcribeAndInsert(blob);
    };
    _mediaRec.start();
    _isRecording = true;
    btn.classList.add('recording');
    btn.title = 'Click to stop recording';
  } catch(err) {
    console.error('Microphone access denied:', err);
    alert('Microphone access denied. Please allow microphone in your browser settings.');
  }
}

function stopVoiceRec(){
  const btn = document.getElementById('mic-btn');
  if(_mediaRec && _mediaRec.state !== 'inactive') _mediaRec.stop();
  _isRecording = false;
  btn.classList.remove('recording');
  btn.title = 'Click to record voice message';
}

function getSupportedMime(){
  const types = ['audio/webm;codecs=opus','audio/webm','audio/ogg;codecs=opus','audio/mp4'];
  for(const t of types){ if(MediaRecorder.isTypeSupported(t)) return t; }
  return '';
}

async function transcribeAndInsert(blob){
  const btn = document.getElementById('mic-btn');
  const inp = document.getElementById('inp');
  // Indicate transcribing via CSS class only — do not destroy the SVG with
  // textContent/innerHTML, otherwise the mic icon never restores.
  btn.classList.add('transcribing');
  try {
    const form = new FormData();
    form.append('file', blob, 'recording.webm');
    const resp = await fetch('/transcribe', {method:'POST', headers:{'x-csrf-token':_csrfToken()}, body:form});
    const data = await resp.json();
    if(data.error){ alert('Transcription failed: ' + data.error); return; }
    if(data.text){
      // Auto-send the transcribed voice message to the session
      // that was focused when the user started recording
      if(ws && ws.readyState === 1){
        const msg = {type:'message', content: data.text};
        if(_voiceTargetSession) msg.session_id = _voiceTargetSession;
        ws.send(JSON.stringify(msg));
        // Show the sent text in the input briefly then clear
        inp.value = '';
        inp.style.height = 'auto';
      } else {
        // Fallback: put text in input for manual send if WS disconnected
        inp.value = (inp.value ? inp.value + ' ' : '') + data.text;
        inp.dispatchEvent(new Event('input'));
        inp.focus();
      }
      _voiceTargetSession = null;
    }
  } catch(err) {
    console.error('Transcription request failed:', err);
    alert('Could not reach transcription server.');
  } finally {
    btn.classList.remove('transcribing');
  }
}

function cmd(c){
  if(!ws || ws.readyState !== 1){
    // WS not connected — show banner if hidden
    const banner = document.getElementById('conn-banner');
    if(banner && banner.style.display === 'none'){
      const bannerMsg = document.getElementById('conn-banner-msg');
      const bannerIcon = document.getElementById('conn-banner-icon');
      if(bannerMsg) bannerMsg.textContent = 'Not connected to server — commands cannot be sent';
      if(bannerIcon) bannerIcon.textContent = '⚠️';
      banner.className = 'conn-banner warn';
      banner.style.display = 'flex';
    }
    return;
  }
  // If creating a new session, inject CWD into the 2nd segment if it is empty.
  // Format: new_session:ai[|cwd[|model]]
  // When called from model picker: new_session:ollama||mymodel — CWD slot is empty.
  if(c.startsWith('new_session:')){
    const payload = c.slice('new_session:'.length);
    const segs = payload.split('|');    // segs[0]=ai, segs[1]=cwd, segs[2]=model
    if(!segs[1] || !segs[1].trim()){
      const cwd = document.getElementById('cwd-display').textContent;
      if(cwd && cwd !== '—') segs[1] = cwd;
      c = 'new_session:' + segs.join('|');
    }
    if(_viewingHistory) returnToLive();
  }
  ws.send(JSON.stringify({type:'command', command:c}));
}
const inp = document.getElementById('inp');
inp.addEventListener('input', () => {
  inp.style.height = 'auto';
  inp.style.height = Math.min(inp.scrollHeight, 200) + 'px';
  _updateComposer();
});
_updateComposer();
inp.addEventListener('keydown', e => {
  if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); send(); }
});

// --- Paste / Drop images & files into chat ------------------------------------------------------------------

async function _uploadBlob(blob, filename){
  const form = new FormData();
  form.append('file', blob, filename);
  try {
    const resp = await fetch('/upload', {method:'POST', headers:{'x-csrf-token':_csrfToken()}, body:form});
    const data = await resp.json();
    if(data.filename){
      _uploadedFiles.push(data.filename);
      const tag = `[📎 ${data.filename}]`;
      inp.value = (inp.value ? inp.value + ' ' : '') + tag + ' ';
      inp.focus();
      inp.dispatchEvent(new Event('input'));
    }
  } catch(err){
    console.error('Paste/drop upload failed:', err);
  }
}

async function _handlePastedFiles(files){
  const btn = document.getElementById('clip-btn');
  btn.classList.add('uploading');
  for(const file of files){
    await _uploadBlob(file, file.name || `pasted_${Date.now()}.png`);
  }
  btn.classList.remove('uploading');
}

// Clipboard paste (Ctrl+V / Cmd+V) — images and files
document.addEventListener('paste', async (e) => {
  const items = e.clipboardData?.items;
  if(!items) return;

  const files = [];
  for(const item of items){
    // Skip plain text — let the browser handle normal text paste
    if(item.kind === 'string') continue;
    if(item.kind === 'file'){
      const file = item.getAsFile();
      if(file) files.push(file);
    }
  }
  if(files.length > 0){
    e.preventDefault();
    await _handlePastedFiles(files);
  }
});

// Drag-and-drop onto the input area or chat
const _dropZone = document.querySelector('.input-bar') || document.body;

_dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  e.stopPropagation();
  _dropZone.classList.add('drag-over');
});

_dropZone.addEventListener('dragleave', (e) => {
  e.preventDefault();
  e.stopPropagation();
  _dropZone.classList.remove('drag-over');
});

_dropZone.addEventListener('drop', async (e) => {
  e.preventDefault();
  e.stopPropagation();
  _dropZone.classList.remove('drag-over');

  const files = [];
  if(e.dataTransfer?.files){
    for(const f of e.dataTransfer.files) files.push(f);
  }
  if(files.length > 0){
    await _handlePastedFiles(files);
  }
});

