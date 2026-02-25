# Claude Remote — Multi-Session AI Control via Web UI + Telegram

Run Claude Code, Gemini, Codex, and your shell as **parallel independent sessions** — controlled from a local web UI in your browser and/or Telegram on your phone. Both channels stay in sync. Every session gets its own terminal, its own working directory, and its own conversation history.

---

## How it works

```
Browser (http://localhost:8000)  ←── WebSocket ──┐
                                                  ├── Session Manager ── Session 1: Claude Code  (C:\projects\webapp)
Telegram App (your phone)        ←── Bot API  ────┘                  ├── Session 2: Gemini       (C:\projects\data)
                                        ↑                            └── Session 3: Shell         (C:\scripts)
                                  web_app.py
                             (single Python process)
```

- **Multi-session** — run Claude Code, Gemini, Codex, and a raw shell at the same time, each with its own directory and history
- **Focused session** — Telegram always routes to the session you last tapped. Switch focus with one button tap
- **Web UI** — chat bubbles, session picker chip, directory bar, per-session badges, thinking indicator
- **Full sync** — web messages forwarded to Telegram, Telegram messages shown in browser, both always in sync
- **File auto-send** — any AI-generated file (PDF, image, video, code) sent to Telegram as a proper attachment the moment it's created
- **Chat history** — every session auto-saved; browse, view, resume with context, rename, or delete from web UI or Telegram

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Windows 10/11 | Uses Windows-specific subprocess flags |
| Python 3.10+ | [python.org](https://www.python.org/downloads/) — tick "Add to PATH" during install |
| A Telegram account | To create the bot and receive messages |
| Claude Code installed | `claude` must be on your PATH (or whichever AI CLIs you want to use) |

---

## Step 1 — Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a name (e.g. `My Claude Remote`)
4. Choose a username ending in `bot` (e.g. `my_claude_remote_bot`)
5. BotFather replies with a token:
   ```
   123456789:ABCDefgh-XXXXXXXXXXXXXXXXXXXXXXX
   ```
   Copy it — you'll need it in Step 3.

---

## Step 2 — Find your Telegram User ID

1. Open Telegram and search for **@userinfobot**
2. Send `/start`
3. It replies with your numeric user ID (e.g. `987654321`)

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
| `SESSION_CWD` | — | Default working directory when a new session is created (defaults to the folder where you run the script) |
| `OUTPUT_IDLE_TIMEOUT` | — | Seconds of silence before assuming output is done (default: `1.5`) |
| `OUTPUT_MAX_WAIT` | — | Hard cap in seconds before returning whatever was received (default: `60`) |
| `OUTPUT_NO_RESPONSE` | — | Seconds to wait if no output arrives at all (default: `5`) |
| `WEB_PORT` | — | Port for the web UI (default: `8000`) |
| `WEB_HOST` | — | Host to bind the web server to (default: `127.0.0.1`) |
| `CLAUDE_TIMEOUT` | — | Max seconds to wait for any AI response (default: `600`). Increase for long tasks. |

---

## Step 5 — Run

Double-click **`launch.bat`**, or run it from the command line:

```bat
:: Start with the default working directory (from .env or the script folder)
launch.bat

:: Start in a specific project folder
launch.bat C:\projects\myapp
launch.bat "C:\My Projects\website"
```

Your browser opens automatically at **http://localhost:8000**. The Telegram bot is active at the same time.

> **Tip — per-project shortcuts:** Right-click `launch.bat` → *Create shortcut*, open the shortcut properties, and append your project path to the **Target** field:
> ```
> C:\...\claude-remote\launch.bat  C:\projects\website
> ```
> Give each shortcut a different name and pin them to your taskbar.

---

## Sessions — the core concept

Claude Remote is built around sessions. Each session is an independent process with its own AI, working directory, and conversation history. You can run as many as you like simultaneously.

**Focused session** — only one session is "focused" at a time. All typing (in Telegram or the web UI) goes to the focused session. You can switch focus at any moment.

**Session states:**
- 🟢 Running (shell, no AI active)
- 🟡 Running with an AI (Claude / Gemini / Codex)
- 🔴 Stopped

**Resuming a stopped session** — you can restart any stopped session. You can also switch it to a different AI when you resume — e.g. start a session with Claude Code, stop it, resume it under Gemini.

---

## Web UI

```
┌──────────────────────────────────────────────────────────────┐
│  ◈ Claude Remote                                   ≡  ●      │  ← header (history / connection)
│──────────────────────────────────────────────────────────────│
│  📁  2 sessions ·  C:\projects\webapp              [🔍]      │  ← dir bar (focused session CWD)
│──────────────────────────────────────────────────────────────│
│                                                              │
│                                 You   [🤖 Claude #1]  12:34 │
│                    ┌──────────────────────────────────┐      │
│                    │  refactor the auth module        │      │
│                    └──────────────────────────────────┘      │
│                                                              │
│  Claude Code  🤖 Claude #1                          12:34   │
│  ┌──────────────────────────────────────────────────┐        │
│  │  I'll start by reading the current auth files…   │        │
│  └──────────────────────────────────────────────────┘        │
│                                                              │
│  🤖 Claude #1…  ● ● ●                                        │  ← per-session thinking indicator
│                                                              │
│──────────────────────────────────────────────────────────────│
│  [🤖 Claude #1 ▾]  Type a message…                  [Send]  │  ← session picker + input
└──────────────────────────────────────────────────────────────┘
```

### Session picker chip (bottom-left)

Click the chip (shows the focused session's emoji and name) to open the sessions menu:

- **Active sessions** — all running/stopped sessions listed. Tick marks the focused one. Tap any to switch focus.
- **New Session** — create a new session with Claude Code, any loaded integration, or a raw shell.
- **Focused Session controls** — interrupt, stop, or clear history for the current session.

### Changing the working directory

Click the path in the directory bar, type a new path, and press **Enter**. This changes the CWD for the focused session only. Other sessions keep their own directories.

---

## Telegram — how multi-session works

Telegram stays simple. There is always one focused session. All your messages go there.

**To switch which session you're talking to:**
Tap the **📋 Sessions** button (or send `/status`) → tap any session from the list.

**To create a new session:**
Tap **➕ New Session** → pick an AI.

**Session controls keyboard** — appears below most session-related replies:

| Button | What it does |
|--------|-------------|
| **📋 All Sessions** | Lists all sessions; tap one to focus it |
| **📁 Change Dir** | Opens the folder browser for the focused session |
| **🔀 Switch AI** | Changes the AI of the focused session (restarts terminal) |
| **⏸ Interrupt** | Sends Ctrl+C to the focused session |
| **⏹ Stop Session** | Stops the focused session (keeps history) |
| **🗑 End & Delete** | Stops and permanently removes the focused session |

---

## Commands

### Telegram commands

**Session management**

| Command | What it does |
|---------|-------------|
| `/launch` | Creates a new raw shell session |
| `/claude` | Creates a new Claude Code session |
| `/gemini` | Creates a new Gemini session |
| `/codex` | Creates a new Codex session |
| `/status` | Lists all sessions with status, AI, and directory |
| `/stop` | Stops the focused session |
| `/interrupt` | Sends Ctrl+C to the focused session |
| `/stop_ai` | Removes the AI from the focused session (keeps terminal running as shell) |
| `/clear` | Clears the Claude conversation history for the focused session |

**Directory control**

| Command | What it does |
|---------|-------------|
| `/cwd` | Shows the focused session's current working directory |
| `/cwd <path>` | Changes the focused session's working directory |
| `/browse` | Opens the interactive folder browser |

**Utility**

| Command | What it does |
|---------|-------------|
| `/cmd <text>` | Runs a shell command in the focused session |
| `/timeout` | Shows the current AI response timeout |
| `/timeout <seconds>` | Sets the AI response timeout |
| `/start` | Shows help text |

**Chat history**

| Command | What it does |
|---------|-------------|
| `/history` | Shows your last 5 saved messages |
| `/history <n>` | Shows last n messages, max 20 |
| `/resume` | Creates a new session with context from your most recent saved session |
| `/resume <date>` | Creates a new session with context from a specific date |
| `/clear_context` | Discards any pending resume context |

### Natural language shortcuts

You don't need to memorise commands. These plain-text phrases work too:

| Type this | What happens |
|-----------|-------------|
| `menu` / `help` / `?` | Opens the main menu |
| `sessions` / `list sessions` | Shows all sessions |
| `new claude` / `start claude` | Creates a new Claude Code session |
| `new gemini` / `start gemini` | Creates a new Gemini session |
| `stop` / `kill` / `quit` | Stops the focused session |
| `interrupt` / `cancel` / `ctrl+c` | Sends Ctrl+C |
| `resume` / `continue` | Resumes the most recent saved session |
| `folder` / `cwd` / `directory` | Shows the current directory |
| `status` / `session status` | Lists all sessions |

---

## Working with multiple sessions

The real power is running sessions in parallel. A typical multi-session workflow:

```
1. Create a Claude Code session in C:\projects\webapp
   → Ask Claude to plan a refactor

2. Without stopping Claude, create a Gemini session in C:\projects\data
   → Ask Gemini to analyse the database schema in parallel

3. Claude finishes → switch back to it, review the plan
   → Files appear in Telegram from both sessions independently

4. Stop the Gemini session
   → Claude session keeps running, history preserved

5. Resume the Gemini session later with a different working directory
   → Pick Codex as the AI this time
```

Each session's files, CWD, and conversation history are completely independent. Stopping one never affects another.

---

## File Auto-Send

When an AI creates a file in the session's working directory, Claude Remote detects it and sends it to Telegram automatically. The message includes which session produced the file.

| File type | Extensions | Telegram action |
|-----------|-----------|----------------|
| Photo | `.png` `.jpg` `.jpeg` `.gif` `.webp` `.bmp` | Sent as photo |
| Animated GIF | `.gif` | Sent as animation |
| Video | `.mp4` `.mov` `.avi` `.mkv` `.webm` | Sent as video |
| Document | `.pdf` `.pptx` `.ppt` `.docx` `.doc` `.xlsx` `.xls` `.csv` `.html` `.htm` `.zip` `.tar` `.gz` `.txt` `.md` | Sent as document |

Files up to **50 MB** are supported. The web UI also shows a clickable link at `http://localhost:8000/files/<filename>`.

---

## Chat History

Every session is auto-saved to daily log files in `chat_logs/`. Nothing to configure.

### Web UI — 📂 History button

Click the history icon in the header to open the modal. Each saved session shows its name (or date) and message count.

Click a session row to expand it:

| Button | What it does |
|--------|-------------|
| **👁 View** | Replays the session in the chat window (read-only). Click **↩ Back to Live** to return. |
| **▶ Resume with context** | Creates a new session with the last 10 exchanges injected as context. |
| **✎ Rename** | Sets a custom name (e.g. *"Portfolio site project"*). Press **Enter** to save. |
| **🗑** | Permanently deletes that day's log file. |

### Telegram

```
You:  /resume
Bot:  ✅ Resumed: "Portfolio site project" (10 exchanges loaded)
      📁 Directory restored: C:\projects\myapp
      🤖 Claude Code re-activated — just type to continue.

You:  now add dark mode to the navbar
Bot:  📎 Context injected. Thinking…
      (Claude responds with full context of the previous session)
```

### Notes

- History is not AI memory — each CLI is stateless. Resume works by prepending a condensed transcript to your next message.
- Log files are stored as `chat_logs/YYYY-MM-DD.jsonl` (one file per day).
- Custom names are stored in `chat_logs/chat_names.json`.
- Both files are plain text — safe to back up or delete.

---

## Adding AI integrations

Claude Remote loads integrations from an `integrations/` folder at startup. Drop in a new `.json` file and restart — no code changes needed.

Each integration file defines the CLI command, display name, emoji, and colour. See the existing files in `integrations/` for the format.

---

## Running on startup (optional)

To start automatically when you log into Windows:

1. Press `Win + R`, type `shell:startup`, press Enter
2. Create a shortcut pointing to:
   ```
   pythonw "C:\path\to\claude-remote\web_app.py"
   ```
   (`pythonw` runs Python without a visible console window.)

---

## Project files

```
claude-remote/
├── web_app.py            # Main entry point (Web UI + Telegram bot + session manager)
├── requirements.txt      # Python dependencies
├── .env                  # Your config (never share this)
├── .env.example          # Config template
├── setup.bat             # One-time setup (install deps, create .env)
├── launch.bat            # Daily launcher — accepts optional path argument
├── integrations/         # AI plugin definitions (one .json per AI)
│   ├── gemini.json
│   └── codex.json
├── README.md             # This file
└── chat_logs/            # Auto-created; stores chat history
    ├── 2026-02-25.jsonl  # One file per day
    ├── last_state.json   # Saved session state (restored on restart)
    └── chat_names.json   # Custom session names
```

---

## Troubleshooting

**Bot doesn't respond**
- Check the console for errors
- Make sure `TELEGRAM_BOT_TOKEN` is correct in `.env`
- Only user IDs listed in `ALLOWED_USER_IDS` can use the bot

**Web UI not opening**
- Make sure port 8000 is free (`WEB_PORT` in `.env` to change it)
- Navigate to `http://localhost:8000` manually if the browser didn't open

**Session says "stopped" when I try to type**
- Tap the session in the list → choose **Resume** and pick an AI to restart it

**Files not being sent to Telegram**
- The file must be created inside the session's working directory
- Files over 50 MB cannot be sent via Telegram Bot API
- Send any message to the bot first if you've only been using the web UI — the bot needs to know your chat ID

**Output is cut off**
- Long output is split into multiple messages automatically (3,800 chars each)
- Increase `OUTPUT_MAX_WAIT` in `.env` if responses are being truncated

**Claude/Codex/Gemini not found**
- Make sure the CLI is installed and on your system PATH
- Test by opening `cmd.exe` manually and typing `claude` (or `codex`/`gemini`)

**Working directory change not taking effect**
- Make sure the path exists before switching
- Use full absolute paths (e.g. `C:\Users\me\projects`) not relative ones
- Each session has its own CWD — changing it in one session doesn't affect others

**Switching AI on a session clears the conversation history**
- This is intentional. A new AI needs a clean slate; the old history is still in the daily log file.
