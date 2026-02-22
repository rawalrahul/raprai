# My Personal Assistant — Web UI + Telegram Bot for Remote AI Control

Control Claude Code, Gemini, Codex, and your shell from **anywhere** — through a local web chat UI in your browser and/or Telegram on your phone. Both channels are always in sync.

---

## How it works

```
Browser (http://localhost:8000)  ←── WebSocket ──┐
                                                  ├── Shared State ── AI CLIs / shell subprocess
Telegram App (your phone)        ←── Bot API  ────┘
                                        ↑
                                  web_app.py
                             (single Python process)
```

- **Web UI** — chat bubbles, active AI badge, mode buttons, directory bar, thinking indicator
- **Telegram** — full mirroring: web messages forwarded to Telegram, Telegram messages shown in browser
- **File auto-send** — if the AI creates a PDF, image, video, or any file, it is automatically sent to Telegram as a proper attachment

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Windows 10/11 | Uses Windows-specific subprocess flags |
| Python 3.10+ | [python.org](https://www.python.org/downloads/) — tick "Add to PATH" during install |
| A Telegram account | To create the bot and to send messages |
| Claude Code installed | `claude` must be on your PATH (or whichever AI CLIs you want to use) |

---

## Step 1 — Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a name (e.g. `My My Personal Assistant`)
4. Choose a username ending in `bot` (e.g. `my_claude_remote_bot`)
5. BotFather replies with a **token** that looks like:
   ```
   123456789:ABCDefgh-XXXXXXXXXXXXXXXXXXXXXXX
   ```
   Copy it — you'll need it in Step 3.

---

## Step 2 — Find your Telegram User ID

1. Open Telegram and search for **@userinfobot**
2. Send `/start`
3. It replies with your **numeric user ID** (e.g. `987654321`)

   Copy it — this whitelists only you to control the bot.

---

## Step 3 — Set up the project

Open a Command Prompt in the project folder and run:

```bat
setup.bat
```

This will:
- Check that Python is installed
- Install all Python dependencies (`python-telegram-bot`, `fastapi`, `uvicorn`, `python-dotenv`)
- Copy `.env.example` → `.env`

---

## Step 4 — Configure `.env`

Open `.env` in any text editor and fill in the required values:

```env
TELEGRAM_BOT_TOKEN=123456789:ABCDefgh-XXXXXXXXXXXXXXXXXXXXXXX
ALLOWED_USER_IDS=987654321
```

All available settings:

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Token from @BotFather (Step 1) |
| `ALLOWED_USER_IDS` | ✅ | Your user ID from @userinfobot (Step 2). Comma-separate for multiple users. |
| `SESSION_CWD` | — | Default working directory for AI sessions (defaults to the folder where you run the script) |
| `OUTPUT_IDLE_TIMEOUT` | — | Seconds of silence before assuming output is done (default: `1.5`) |
| `OUTPUT_MAX_WAIT` | — | Hard cap in seconds before returning whatever was received (default: `60`) |
| `OUTPUT_NO_RESPONSE` | — | Seconds to wait if no output arrives at all (default: `5`) |
| `WEB_PORT` | — | Port for the web UI (default: `8000`) |
| `WEB_HOST` | — | Host to bind the web server to (default: `127.0.0.1`) |

---

## Step 5 — Run

```bat
python web_app.py
```

You should see:
```
INFO:     Started server process
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO - Bot started. Polling for updates...
```

Your browser will open automatically at **http://localhost:8000**. The Telegram bot is also active at the same time.

---

## Web UI

```
┌─────────────────────────────────────────────────────┐
│  ◈ My Personal Assistant                    ● Claude Code   │  ← header with active AI badge
│─────────────────────────────────────────────────────│
│  📁 C:\Users\me\projects\myapp          [✎ edit]   │  ← working directory bar
│─────────────────────────────────────────────────────│
│  [Claude Code] [Gemini] [Codex] [Shell]  [⚡ Launch]│  ← mode bar
│─────────────────────────────────────────────────────│
│                                                     │
│                           You                 12:34 │
│                 ┌──────────────────────┐            │
│                 │  hello, how are you? │            │
│                 └──────────────────────┘            │
│                                                     │
│  Claude Code                          12:34         │
│  ┌──────────────────────────────────┐              │
│  │  I'm doing well! How can I help? │              │
│  └──────────────────────────────────┘              │
│                                                     │
│  ● Thinking...                                      │  ← typing indicator
│                                                     │
│─────────────────────────────────────────────────────│
│  Type a message...                           [Send] │  ← input bar
└─────────────────────────────────────────────────────┘
```

### Changing the working directory from the browser

Click the **✎ edit** pencil next to the directory path, type a new path, and press **Enter** (or click **Apply**). The change takes effect immediately for the next AI call.

---

## Commands

### Telegram commands

| Command | What it does |
|---------|-------------|
| `/launch` | Starts a new terminal session |
| `/claude` | Launches Claude Code in the session |
| `/gemini` | Launches Gemini CLI in the session |
| `/codex` | Launches Codex CLI in the session |
| `/cmd <text>` | Runs any shell command (e.g. `/cmd dir`) |
| `/cwd` | Shows the current working directory |
| `/cwd <path>` | Changes the working directory (e.g. `/cwd C:\projects\myapp`) |
| `/status` | Shows whether a session is running and its PID |
| `/interrupt` | Sends Ctrl+C to the terminal |
| `/stop` | Kills the current terminal session |
| `/start` | Shows help text |
| _(any text)_ | Forwarded directly to the active terminal / AI |

### Web UI buttons

| Button | What it does |
|--------|-------------|
| **Claude Code** | Launches Claude Code (equivalent to `/claude`) |
| **Gemini** | Launches Gemini CLI (equivalent to `/gemini`) |
| **Codex** | Launches Codex CLI (equivalent to `/codex`) |
| **Shell** | Sends raw shell commands |
| **⚡ Launch** | Starts a fresh terminal session |

---

## File Auto-Send

When an AI creates a file in the working directory, My Personal Assistant automatically detects it and sends it to Telegram:

| File type | Extensions | Telegram action |
|-----------|-----------|----------------|
| Photo | `.png` `.jpg` `.jpeg` `.gif` `.webp` `.bmp` | Sent as photo |
| Animated GIF | `.gif` | Sent as animation |
| Video | `.mp4` `.mov` `.avi` `.mkv` `.webm` | Sent as video |
| Document | `.pdf` `.pptx` `.docx` `.xlsx` `.zip` `.py` `.html` `.css` `.js` `.txt` and any other | Sent as document |

Files up to **50 MB** are supported. You also get a message in the web chat with a clickable link to view/download the file from the local server at `http://localhost:8000/files/<filename>`.

---

## Working Directory Workflow

You can use different directories for different AI tasks in the same session:

```
1. Start web_app.py → session starts in default directory (SESSION_CWD or script folder)

2. /cwd C:\projects\website     ← switch to website project
   [Claude Code]                 ← launch Claude Code there
   "build me a landing page"     ← Claude creates files in that folder
   → files auto-sent to Telegram

3. /stop                         ← stop Claude Code

4. /cwd C:\projects\datawork     ← switch to data project
   [Gemini]                      ← launch Gemini there
   "analyse sales.csv"           ← Gemini works in that folder
```

No restart needed between directory changes.

---

## Typical session

### From Telegram:
```
You:  /launch
Bot:  Microsoft Windows [Version ...]
      C:\Users\me>

You:  /cwd C:\projects\myapp
Bot:  📁 Working directory set to C:\projects\myapp

You:  /claude
Bot:  Claude Code ready

You:  build me a one-page portfolio site
Bot:  (Claude creates index.html, style.css...)
Bot:  📎 [sends index.html as document]
Bot:  📸 [sends screenshot.png as photo]
```

### From browser:
Same conversation — all messages and files appear in both the web UI and Telegram simultaneously.

---

## Running on startup (optional)

To have it start automatically when you log into Windows:

1. Press `Win + R`, type `shell:startup`, press Enter
2. Create a shortcut pointing to:
   ```
   pythonw "C:\path\to\claude-remote\web_app.py"
   ```
   (`pythonw` runs Python without a visible console window — the web UI is your interface)

---

## Project files

```
claude-remote/
├── web_app.py               # Main entry point (Web UI + Telegram bot)
├── telegram_claude_bot.py   # Original Telegram-only bot (kept as fallback)
├── requirements.txt         # Python dependencies
├── .env                     # Your config (never share this)
├── .env.example             # Config template
├── setup.bat                # One-time setup script
├── PLAN.md                  # Architecture and design notes
└── README.md                # This file
```

---

## Troubleshooting

**Bot doesn't respond**
- Check the console for errors
- Make sure `TELEGRAM_BOT_TOKEN` is correct in `.env`
- Only the user IDs in `ALLOWED_USER_IDS` can use the bot

**Web UI not opening**
- Make sure port 8000 is free (or set `WEB_PORT` in `.env` to another port)
- Navigate to `http://localhost:8000` manually if the browser didn't open automatically

**`/launch` says "Session already running"**
- Send `/stop` first, then `/launch`

**Files not being sent to Telegram**
- Make sure the file is created inside the current working directory
- Files over 50 MB cannot be sent via Telegram Bot API
- Check that `_telegram_chat_id` is set — send any message to the bot first if you only used the web UI

**Output is cut off**
- Long output is split into multiple messages automatically (3800 chars each)
- Increase `OUTPUT_MAX_WAIT` in `.env` if responses are being cut short

**Claude/Codex/Gemini not found**
- Make sure the CLI is installed and available on your system PATH
- Test by opening `cmd.exe` manually and typing `claude` (or `codex`/`gemini`)

**Working directory change not taking effect**
- Make sure the path exists on disk before switching
- Use full absolute paths (e.g. `C:\Users\me\projects`) not relative ones
