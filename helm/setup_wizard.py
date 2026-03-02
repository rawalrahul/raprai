"""
helm/setup_wizard.py — Embedded HTML for the first-run setup wizard.

Flow:
  Step 0 — Gemini CLI (optional, free)
  Step 1 — Telegram Bot (optional)
  Step 2 — Claude + Codex (optional)
  Step 3 — Done / summary
"""

_SETUP_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Helm HQ — Setup</title>
<link rel="icon" href="/static/logo.png" type="image/png">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0d0d0d;--surface:#141414;--surface2:#1c1c1c;--border:#242424;
  --text:#e2e2e2;--muted:#555;--dim:#888;
  --accent:#3b82f6;--ok:#22c55e;--warn:#f59e0b;--err:#ef4444;
}
html,body{height:100%;background:var(--bg);color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:14px;line-height:1.5}

.wizard{display:flex;min-height:100vh;align-items:center;justify-content:center;padding:24px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;
  width:100%;max-width:580px;overflow:hidden;box-shadow:0 8px 40px rgba(0,0,0,.5)}

.card-header{padding:22px 28px 18px;border-bottom:1px solid var(--border)}
.logo-row{display:flex;align-items:center;gap:10px;margin-bottom:14px}
.logo-row img{width:26px;height:26px;border-radius:5px;object-fit:contain}
.logo-row .app-name{font-size:15px;font-weight:700;color:var(--text)}
.logo-row .tag{color:var(--muted);font-size:12px;margin-left:4px}

.step-bar{display:flex;gap:5px}
.step-dot{height:3px;border-radius:2px;flex:1;background:var(--border);transition:background .3s}
.step-dot.done{background:var(--ok)}
.step-dot.active{background:var(--accent)}

.card-body{padding:28px}
.step{display:none}.step.active{display:block}
.step-title{font-size:17px;font-weight:700;margin-bottom:6px;color:var(--text)}
.step-desc{color:var(--dim);font-size:13px;margin-bottom:20px;line-height:1.65}
.step-desc code{background:var(--surface2);padding:1px 5px;border-radius:3px;font-size:12px;color:#9ca3af}
.step-desc a{color:var(--accent);text-decoration:none}.step-desc a:hover{text-decoration:underline}

.free-tag{background:rgba(34,197,94,.15);color:var(--ok);font-size:11px;font-weight:700;
  padding:2px 8px;border-radius:4px;vertical-align:middle;margin-left:6px;letter-spacing:.03em}

.status-badge{
  display:inline-flex;align-items:center;gap:7px;
  padding:7px 12px;border-radius:7px;font-size:12px;font-weight:600;margin-bottom:16px}
.status-badge.checking{background:rgba(107,114,128,.12);color:#9ca3af}
.status-badge.ok{background:rgba(34,197,94,.1);color:var(--ok)}
.status-badge.warn{background:rgba(245,158,11,.1);color:var(--warn)}
.status-badge.err{background:rgba(239,68,68,.1);color:var(--err)}

.code-block{
  background:var(--surface2);border:1px solid var(--border);border-radius:6px;
  padding:10px 36px 10px 14px;font-family:'Courier New',monospace;font-size:12px;color:#9ca3af;
  margin-bottom:12px;position:relative;word-break:break-all}
.code-copy{
  position:absolute;right:8px;top:7px;background:var(--border);border:none;
  border-radius:4px;color:var(--dim);font-size:10px;padding:3px 7px;cursor:pointer;font-family:inherit}
.code-copy:hover{color:var(--text);background:#2a2a2a}

.alert{padding:10px 14px;border-radius:7px;font-size:12px;margin-bottom:14px;line-height:1.65}
.alert-warn{background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.18);color:#fbbf24}
.alert-ok{background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.18);color:#4ade80}
.alert-info{background:rgba(96,165,250,.08);border:1px solid rgba(96,165,250,.18);color:#93c5fd}

.field{margin-bottom:14px}
.field label{display:block;font-size:11px;font-weight:600;color:var(--dim);
  text-transform:uppercase;letter-spacing:.05em;margin-bottom:5px}
.field input{
  width:100%;background:var(--surface2);border:1px solid var(--border);
  border-radius:6px;padding:9px 12px;font-size:13px;color:var(--text);
  outline:none;font-family:inherit;transition:border-color .15s}
.field input:focus{border-color:#3a3a3a}
.field small{font-size:11px;color:var(--muted);margin-top:5px;display:block;line-height:1.5}
.field small a{color:var(--accent);text-decoration:none}.field small a:hover{text-decoration:underline}

.btn-row{display:flex;gap:10px;margin-top:24px;align-items:center}
.btn{padding:9px 18px;border-radius:6px;font-size:13px;font-weight:600;
  cursor:pointer;border:none;transition:opacity .15s;font-family:inherit}
.btn:disabled{opacity:.4;cursor:not-allowed}
.btn-primary{background:var(--accent);color:#fff}
.btn-primary:hover:not(:disabled){opacity:.85}
.btn-secondary{background:var(--surface2);border:1px solid var(--border);color:var(--dim)}
.btn-secondary:hover:not(:disabled){color:var(--text);border-color:#3a3a3a}
.btn-skip{background:none;border:none;color:var(--muted);font-size:12px;
  cursor:pointer;text-decoration:underline;margin-left:auto;font-family:inherit;padding:4px}
.btn-skip:hover{color:var(--dim)}

.integ-card{border:1px solid var(--border);border-radius:8px;padding:16px;margin-bottom:12px}
.integ-header{display:flex;align-items:center;gap:8px;margin-bottom:10px}
.integ-emoji{font-size:16px}
.integ-name{font-weight:600;font-size:13px}
.integ-badge{margin-left:auto;font-size:11px;padding:2px 8px;border-radius:4px;font-weight:600}
.integ-badge.ok{background:rgba(34,197,94,.12);color:var(--ok)}
.integ-badge.off{background:var(--surface2);color:var(--muted)}

.summary-item{
  display:flex;align-items:center;gap:10px;padding:10px 0;
  border-bottom:1px solid var(--border);font-size:13px}
.summary-item:last-child{border-bottom:none}
.sum-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.sum-dot.ok{background:var(--ok)}
.sum-dot.off{background:var(--border)}
</style>
</head>
<body>
<div class="wizard">
<div class="card">

  <div class="card-header">
    <div class="logo-row">
      <img src="/static/logo.png" alt="Helm HQ">
      <span class="app-name">Helm HQ</span>
      <span class="tag">— First-run Setup</span>
    </div>
    <div class="step-bar">
      <div class="step-dot active" id="dot0"></div>
      <div class="step-dot" id="dot1"></div>
      <div class="step-dot" id="dot2"></div>
      <div class="step-dot" id="dot3"></div>
      <div class="step-dot" id="dot4"></div>
    </div>
  </div>

  <div class="card-body">

    <!-- ─── STEP 0: Gemini (Required) ─── -->
    <div class="step active" id="step0">
      <div class="step-title">Gemini <span class="free-tag">FREE</span> <span style="color:var(--muted);font-size:12px;font-weight:400">(optional)</span></div>
      <div class="step-desc">
        <strong style="color:var(--text)">Google Gemini CLI</strong> is a free AI backend for Helm HQ.
        No paid subscription required — just a free API key from Google AI Studio.
        You can skip this if you're using Claude or another AI instead.
      </div>

      <div id="gemini-badge" class="status-badge checking">⟳ Checking...</div>
      <div id="gemini-details"></div>

      <div class="field">
        <label>GEMINI_API_KEY</label>
        <input id="gemini-key-0" type="password" placeholder="AIzaSy..." autocomplete="off">
        <small>Get a free key at <a href="https://aistudio.google.com/app/apikey" target="_blank">aistudio.google.com/app/apikey</a></small>
      </div>
      <div id="gemini-msg"></div>

      <div class="btn-row">
        <button class="btn btn-secondary" onclick="checkGemini()">Re-check</button>
        <button class="btn btn-primary" onclick="saveGeminiAndContinue()">Save & Continue →</button>
        <button class="btn-skip" onclick="goStep(1)">Skip for now</button>
      </div>
    </div>

    <!-- ─── STEP 1: Telegram (optional) ─── -->
    <div class="step" id="step1">
      <div class="step-title">Telegram Bot <span style="color:var(--muted);font-size:12px;font-weight:400">(optional)</span></div>
      <div class="step-desc">
        Connect a Telegram bot to control Helm HQ remotely from your phone — launch sessions,
        send prompts, and get AI responses via chat. You can skip this and configure it later
        by editing your <code>.env</code> file.
      </div>
      <div class="field">
        <label>Bot Token</label>
        <input id="tg-token" type="password" placeholder="123456789:ABCDEFGhijklmnopqrstuvwxyz" autocomplete="off">
        <small>Create a bot and get your token from <a href="https://t.me/botfather" target="_blank">@BotFather</a></small>
      </div>
      <div class="field">
        <label>Allowed User IDs</label>
        <input id="tg-users" type="text" placeholder="123456789, 987654321" autocomplete="off">
        <small>Your Telegram numeric ID(s), comma-separated. Find yours via <a href="https://t.me/userinfobot" target="_blank">@userinfobot</a></small>
      </div>
      <div id="tg-msg"></div>
      <div class="btn-row">
        <button class="btn btn-secondary" onclick="goStep(0)">← Back</button>
        <button class="btn btn-primary" onclick="saveTelegram()">Save & Continue →</button>
        <button class="btn-skip" onclick="goStep(2)">Skip for now</button>
      </div>
    </div>

    <!-- ─── STEP 2: Claude + Codex (optional) ─── -->
    <div class="step" id="step2">
      <div class="step-title">More AI Integrations <span style="color:var(--muted);font-size:12px;font-weight:400">(optional)</span></div>
      <div class="step-desc">
        Add Claude and Codex as extra AI backends alongside Gemini. Both need their own CLI
        tools and credentials. You can skip this entirely and add them later via your <code>.env</code> file.
      </div>

      <div class="integ-card">
        <div class="integ-header">
          <span class="integ-emoji">🤖</span>
          <span class="integ-name">Claude (Anthropic)</span>
          <span class="integ-badge off" id="claude-badge-2">not configured</span>
        </div>
        <div style="font-size:12px;color:var(--muted);margin-bottom:6px">Install CLI:</div>
        <div class="code-block">npm install -g @anthropic-ai/claude-code<button class="code-copy" onclick="copyCode(this)">copy</button></div>
        <div style="font-size:12px;color:var(--muted);margin-bottom:6px">Then authenticate:</div>
        <div class="code-block">claude login<button class="code-copy" onclick="copyCode(this)">copy</button></div>
        <div style="font-size:11px;color:var(--muted)">Click <strong>Re-check</strong> after logging in.</div>
      </div>

      <div class="integ-card">
        <div class="integ-header">
          <span class="integ-emoji">💻</span>
          <span class="integ-name">OpenAI Codex</span>
          <span class="integ-badge off" id="codex-badge-2">not configured</span>
        </div>
        <div style="font-size:12px;color:var(--muted);margin-bottom:6px">Install CLI:</div>
        <div class="code-block">npm install -g @openai/codex<button class="code-copy" onclick="copyCode(this)">copy</button></div>
        <div class="field" style="margin-top:8px;margin-bottom:0">
          <label>OPENAI_API_KEY</label>
          <input id="codex-key" type="password" placeholder="sk-..." autocomplete="off">
          <small>Get one at <a href="https://platform.openai.com/api-keys" target="_blank">platform.openai.com/api-keys</a></small>
        </div>
      </div>

      <div class="integ-card">
        <div class="integ-header">
          <span class="integ-emoji">🦙</span>
          <span class="integ-name">Ollama <span style="font-size:10px;color:var(--ok);font-weight:700;margin-left:4px">OFFLINE</span></span>
          <span class="integ-badge off" id="ollama-badge-2">checking...</span>
        </div>
        <div style="font-size:12px;color:var(--muted);margin-bottom:8px">
          Run any AI model locally — no API key, no internet required after download.
        </div>
        <div id="ollama-models-row" style="display:none;margin-bottom:10px">
          <div style="font-size:11px;color:var(--muted);margin-bottom:5px">Active model (OLLAMA_MODEL):</div>
          <select id="ollama-model-select" style="
            width:100%;background:var(--surface2);border:1px solid var(--border);
            border-radius:6px;padding:8px 10px;font-size:13px;color:var(--text);
            outline:none;font-family:inherit">
          </select>
        </div>
        <div id="ollama-install-hint" style="display:none">
          <div style="font-size:12px;color:var(--muted);margin-bottom:6px">Install Ollama:</div>
          <div class="code-block">winget install Ollama.Ollama<button class="code-copy" onclick="copyCode(this)">copy</button></div>
          <div style="font-size:12px;color:var(--muted);margin:8px 0 4px">Then pull a model:</div>
          <div class="code-block">ollama pull qwen3:4b<button class="code-copy" onclick="copyCode(this)">copy</button></div>
        </div>
      </div>

      <div id="optional-msg"></div>
      <div class="btn-row">
        <button class="btn btn-secondary" onclick="goStep(1)">← Back</button>
        <button class="btn btn-secondary" onclick="checkOptionalIntegrations()">Re-check</button>
        <button class="btn btn-primary" onclick="saveOptional()">Save & Continue →</button>
        <button class="btn-skip" onclick="goStep(3)">Skip for now →</button>
      </div>
    </div>

    <!-- ─── STEP 3: PIN Protection ─── -->
    <div class="step" id="step3">
      <div class="step-title">Set a PIN 🔒</div>
      <div class="step-desc">
        Helm HQ is accessible from any browser that can reach your machine.
        Set a PIN so only you can log in — it will be required every time the
        app is opened in a new browser session.
      </div>
      <div id="pin-already-set" class="alert alert-ok" style="display:none">
        ✓ A PIN is already configured. You can set a new one below to replace it.
      </div>
      <div id="pin-msg"></div>
      <div class="field">
        <label for="wiz-pin">New PIN (min 4 characters)</label>
        <input id="wiz-pin" type="password" inputmode="numeric"
               autocomplete="new-password" placeholder="Choose a PIN">
      </div>
      <div class="field">
        <label for="wiz-pin2">Confirm PIN</label>
        <input id="wiz-pin2" type="password" inputmode="numeric"
               autocomplete="new-password" placeholder="Repeat PIN">
      </div>
      <div class="btn-row">
        <button class="btn btn-primary" onclick="savePin()">Set PIN &amp; Continue</button>
        <button class="btn-skip" onclick="goStep(4)">Skip for now</button>
      </div>
    </div>

    <!-- ─── STEP 4: Done ─── -->
    <div class="step" id="step4">
      <div class="step-title">You're all set! 🎉</div>
      <div class="step-desc">
        Here's a summary of what's configured. You can always update settings later by editing
        your <code>.env</code> file in the Helm HQ folder.
      </div>
      <div id="summary"></div>
      <div class="btn-row" style="margin-top:28px">
        <button class="btn btn-primary" style="width:100%;text-align:center;padding:11px" onclick="launch()">
          Launch Helm HQ →
        </button>
      </div>
    </div>

  </div><!-- card-body -->
</div><!-- card -->
</div><!-- wizard -->

<script>
let _geminiStatus = {};
let _saved = {gemini: false, tg: false, claude: false, codex: false, ollama: false};

// ── Gemini check ──────────────────────────────────────────────
async function checkGemini() {
  const badge   = document.getElementById('gemini-badge');
  const details = document.getElementById('gemini-details');
  badge.className   = 'status-badge checking';
  badge.textContent = '⟳ Checking...';
  details.innerHTML = '';

  try {
    const r = await fetch('/integrations/gemini/status');
    _geminiStatus = await r.json();
  } catch (e) {
    _geminiStatus = {ready: false, cli_installed: false, api_key_set: false};
  }

  if (_geminiStatus.cli_installed) {
    // CLI present = ready; API key is optional (CLI handles its own auth)
    badge.className   = 'status-badge ok';
    badge.textContent = '✓ Gemini CLI ready';
    _saved.gemini = true;
  } else {
    badge.className   = 'status-badge err';
    badge.textContent = '✗ Gemini CLI not found';
    details.innerHTML = `
      <div class="alert alert-warn">
        Install the Gemini CLI, then click <strong>Re-check</strong>.
      </div>
      <div style="font-size:12px;color:var(--muted);margin-bottom:6px">Run in your terminal:</div>
      <div class="code-block">npm install -g @google/gemini-cli<button class="code-copy" onclick="copyCode(this)">copy</button></div>`;
  }
  return _geminiStatus;
}

async function saveGeminiAndContinue() {
  const key = document.getElementById('gemini-key-0').value.trim();
  const msg = document.getElementById('gemini-msg');
  msg.innerHTML = '';

  if (key) {
    try {
      await apiSave({GEMINI_API_KEY: key});
    } catch (e) {
      msg.innerHTML = '<div class="alert alert-warn">⚠ Could not save — check file permissions.</div>';
      return;
    }
  }

  const st = await checkGemini();
  if (st.cli_installed) {
    // CLI installed = ready (API key is optional)
    _saved.gemini = true;
    goStep(1);
  } else if (key) {
    // Key provided but no CLI yet
    msg.innerHTML = '<div class="alert alert-warn">⚠ API key saved, but Gemini CLI is not installed. You can install it later.</div>';
    setTimeout(() => goStep(1), 1200);
  } else {
    msg.innerHTML = '<div class="alert alert-warn">⚠ Gemini CLI not found — you can skip this and use Claude or another AI instead.</div>';
    setTimeout(() => goStep(1), 1500);
  }
}

// ── Optional integrations check (step 2) ─────────────────────
async function checkOptionalIntegrations() {
  try {
    const [cr, ir, ollamaR] = await Promise.all([
      fetch('/integrations/claude/status').then(r => r.json()),
      fetch('/integrations').then(r => r.json()),
      fetch('/integrations/ollama/status').then(r => r.json()),
    ]);
    if (cr.ready) {
      const el = document.getElementById('claude-badge-2');
      if (el) { el.textContent = '✓ ready'; el.className = 'integ-badge ok'; }
      _saved.claude = true;
    }
    for (const integ of ir) {
      if (integ.key === 'codex' && integ.ready) {
        const el = document.getElementById('codex-badge-2');
        if (el) { el.textContent = '✓ ready'; el.className = 'integ-badge ok'; }
        _saved.codex = true;
      }
    }
    // Ollama card
    const badge   = document.getElementById('ollama-badge-2');
    const modRow  = document.getElementById('ollama-models-row');
    const instHint= document.getElementById('ollama-install-hint');
    if (ollamaR.cli_installed && ollamaR.models && ollamaR.models.length) {
      // Populate model selector
      const sel = document.getElementById('ollama-model-select');
      if (sel) {
        sel.innerHTML = ollamaR.models.map(m =>
          `<option value="${m}" ${m === ollamaR.current_model ? 'selected' : ''}>${m}</option>`
        ).join('');
      }
      if (modRow)  modRow.style.display  = 'block';
      if (instHint) instHint.style.display = 'none';
      if (badge) {
        if (ollamaR.ready) {
          badge.textContent = '✓ ready'; badge.className = 'integ-badge ok';
          _saved.ollama = true;
        } else {
          badge.textContent = '⚠ model not set'; badge.className = 'integ-badge warn';
        }
      }
    } else {
      if (badge)   { badge.textContent = '✗ not installed'; badge.className = 'integ-badge err'; }
      if (modRow)  modRow.style.display  = 'none';
      if (instHint) instHint.style.display = 'block';
    }
  } catch (e) {}
}

// ── Save helpers ──────────────────────────────────────────────
async function apiSave(payload) {
  const r = await fetch('/setup/save', {
    method:  'POST',
    headers: {'Content-Type': 'application/json'},
    body:    JSON.stringify(payload),
  });
  return r.json();
}

async function saveTelegram() {
  const token = document.getElementById('tg-token').value.trim();
  const users = document.getElementById('tg-users').value.trim();
  const msg   = document.getElementById('tg-msg');
  msg.innerHTML = '';

  if (token || users) {
    try {
      await apiSave({TELEGRAM_BOT_TOKEN: token, ALLOWED_USER_IDS: users});
      _saved.tg = !!token;
      msg.innerHTML = '<div class="alert alert-ok">✓ Saved to .env</div>';
    } catch (e) {
      msg.innerHTML = '<div class="alert alert-warn">⚠ Could not save — check file permissions.</div>';
    }
  }
  setTimeout(() => goStep(2), token || users ? 600 : 0);
}

async function saveOptional() {
  const codexKey   = document.getElementById('codex-key').value.trim();
  const ollamaSel  = document.getElementById('ollama-model-select');
  const ollamaModel = ollamaSel ? ollamaSel.value.trim() : '';
  const msg        = document.getElementById('optional-msg');
  msg.innerHTML    = '';

  const payload = {};
  if (codexKey)    { payload.OPENAI_API_KEY = codexKey;    _saved.codex  = true; }
  if (ollamaModel) { payload.OLLAMA_MODEL   = ollamaModel; _saved.ollama = true; }

  if (Object.keys(payload).length) {
    try {
      await apiSave(payload);
      msg.innerHTML = '<div class="alert alert-ok">✓ Saved to .env</div>';
    } catch (e) {
      msg.innerHTML = '<div class="alert alert-warn">⚠ Could not save — check file permissions.</div>';
    }
  }
  setTimeout(() => goStep(3), Object.keys(payload).length ? 600 : 0);  // → PIN step
}

// ── Step navigation ───────────────────────────────────────────
function goStep(n) {
  document.querySelectorAll('.step').forEach((s, i) => s.classList.toggle('active', i === n));
  document.querySelectorAll('.step-dot').forEach((d, i) => {
    d.className = 'step-dot' + (i < n ? ' done' : i === n ? ' active' : '');
  });
  if (n === 2) checkOptionalIntegrations();
  if (n === 3) checkPinStatus();
  if (n === 4) buildSummary();
}

// ── PIN step ──────────────────────────────────────────────────
async function checkPinStatus() {
  try {
    const st = await fetch('/auth/status').then(r => r.json());
    const el = document.getElementById('pin-already-set');
    if (el) el.style.display = st.pin_set ? 'block' : 'none';
  } catch(e) {}
}

async function savePin() {
  const pin  = document.getElementById('wiz-pin').value;
  const pin2 = document.getElementById('wiz-pin2').value;
  const msg  = document.getElementById('pin-msg');
  msg.innerHTML = '';

  if (pin.length < 4) {
    msg.innerHTML = '<div class="alert alert-warn">⚠ PIN must be at least 4 characters.</div>';
    return;
  }
  if (pin !== pin2) {
    msg.innerHTML = '<div class="alert alert-warn">⚠ PINs do not match.</div>';
    return;
  }
  try {
    const r = await fetch('/auth/set-pin', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({pin}),
    });
    const data = await r.json();
    if (!r.ok || data.error) {
      msg.innerHTML = `<div class="alert alert-warn">⚠ ${data.error || 'Failed to set PIN.'}</div>`;
      return;
    }
    msg.innerHTML = '<div class="alert alert-ok">✓ PIN set successfully!</div>';
    setTimeout(() => goStep(4), 800);
  } catch(e) {
    msg.innerHTML = '<div class="alert alert-warn">⚠ Network error — could not save PIN.</div>';
  }
}

async function buildSummary() {
  // Start with whatever was saved during this wizard session
  let pinSet      = false;
  let geminiReady = _saved.gemini;
  let tgReady     = _saved.tg;
  let claudeReady = _saved.claude;
  let codexReady  = _saved.codex;
  let ollamaReady = _saved.ollama;

  // Merge with actual server-side config (catches pre-existing .env values)
  try {
    const [authSt, setupSt] = await Promise.all([
      fetch('/auth/status').then(r => r.json()),
      fetch('/setup/status').then(r => r.json()),
    ]);
    pinSet      = authSt.pin_set;
    if (setupSt.has_bot_token) tgReady     = true;
    if (setupSt.gemini_ready)  geminiReady = true;
    if (setupSt.claude_ready)  claudeReady = true;
    if (setupSt.codex_ready)   codexReady  = true;
    if (setupSt.ollama_ready)  ollamaReady = true;
  } catch(e) {}

  const items = [
    {label: 'PIN Protection', ok: pinSet,       note: pinSet       ? 'Enabled — login required'         : 'Not set (recommended)'},
    {label: 'Google Gemini',  ok: geminiReady,  note: geminiReady  ? 'CLI ready'                        : 'Not configured (optional)'},
    {label: 'Telegram Bot',   ok: tgReady,      note: tgReady      ? 'Configured'                       : 'Not set up (optional)'},
    {label: 'Claude',         ok: claudeReady,  note: claudeReady  ? 'CLI installed & authenticated'    : 'Not configured (optional)'},
    {label: 'OpenAI Codex',   ok: codexReady,   note: codexReady   ? 'CLI ready'                        : 'Not configured (optional)'},
    {label: 'Ollama (local)', ok: ollamaReady,  note: ollamaReady  ? 'Model selected, offline AI ready' : 'Not configured (optional)'},
  ];
  document.getElementById('summary').innerHTML = items.map(i => `
    <div class="summary-item">
      <div class="sum-dot ${i.ok ? 'ok' : 'off'}"></div>
      <span style="flex:1;font-weight:600">${i.label}</span>
      <span style="color:var(--muted);font-size:12px">${i.note}</span>
    </div>`).join('');
}

function launch() { window.location.href = '/'; }

function copyCode(btn) {
  const text = btn.parentElement.childNodes[0].textContent.trim();
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = 'copied!';
    setTimeout(() => btn.textContent = 'copy', 1500);
  }).catch(() => {});
}

// ── Init ──────────────────────────────────────────────────────
(async function init() {
  try {
    const st = await fetch('/setup/status').then(r => r.json());
    // Pre-populate _saved with anything already in .env so the summary is accurate
    if (st.has_bot_token)  _saved.tg     = true;
    if (st.gemini_ready)   _saved.gemini = true;
    if (st.claude_ready)   _saved.claude = true;
    if (st.codex_ready)    _saved.codex  = true;
    if (st.ollama_ready)   _saved.ollama = true;

    if (!st.env_exists || !st.has_bot_token) {
      // Fresh install or missing Telegram credentials — jump straight to Telegram step
      goStep(1);
      return;
    }
  } catch (e) { /* fallthrough */ }
  // .env exists and has a bot token — start at Gemini check
  checkGemini();
})();
</script>
</body>
</html>"""
