# Claude Remote — Telegram Bot for Remote CLI Control

Control Claude Code (and other AI CLIs) on your Windows PC from anywhere via Telegram.

---

## How it works

```
Your Phone (Telegram)          Your PC (this script)
──────────────────────         ─────────────────────────────
You type a message    →  Bot receives it via polling
                         Writes it to cmd.exe stdin
                    ←    Reads stdout, sends output back
```

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Windows 10/11 | Script uses Windows-specific process flags |
| Python 3.10+ | [python.org](https://www.python.org/downloads/) — tick "Add to PATH" during install |
| A Telegram account | To create the bot and to send messages |
| Claude Code installed | `claude` must be available on your PATH |

---

## Step 1 — Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a name (e.g. `My Claude Remote`)
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
- Install the two Python dependencies
- Copy `.env.example` → `.env`

---

## Step 4 — Configure `.env`

Open `.env` in any text editor and fill in the two required values:

```env
TELEGRAM_BOT_TOKEN=123456789:ABCDefgh-XXXXXXXXXXXXXXXXXXXXXXX
ALLOWED_USER_IDS=987654321
```

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather (Step 1) |
| `ALLOWED_USER_IDS` | Your user ID from @userinfobot (Step 2). Comma-separate multiple IDs. |
| `OUTPUT_IDLE_TIMEOUT` | Seconds of silence before assuming output is done (default: `1.5`) |
| `OUTPUT_MAX_WAIT` | Hard cap in seconds before returning whatever was received (default: `60`) |
| `OUTPUT_NO_RESPONSE` | Seconds to wait if no output arrives at all (default: `5`) |

---

## Step 5 — Run the bot

```bat
python telegram_claude_bot.py
```

You should see:
```
INFO - Bot started. Polling for updates...
```

Keep this window open (or run it minimized). The bot is now live.

---

## Using the bot

Open your Telegram bot and use these commands:

| Command | What it does |
|---------|-------------|
| `/launch` | Starts a new `cmd.exe` terminal session |
| `/claude` | Types `claude` into the terminal, waits for startup |
| `/codex` | Types `codex` into the terminal, waits for startup |
| `/gemini` | Types `gemini` into the terminal, waits for startup |
| `/cmd <text>` | Runs any shell command (e.g. `/cmd dir`) |
| `/status` | Shows whether a session is running and its PID |
| `/interrupt` | Sends Ctrl+C to the terminal (stops running command) |
| `/stop` | Kills the current terminal session |
| `/start` | Shows help text |
| _(any text)_ | Forwarded directly to the active terminal |

### Typical session

```
You:  /launch
Bot:  Microsoft Windows [Version ...]
      C:\Users\...>

You:  /claude
Bot:  Claude Code v... ready

You:  hello
Bot:  Hi! How can I help you today?

You:  /stop
Bot:  Session stopped.

You:  /launch
Bot:  (fresh terminal)

You:  /codex
Bot:  Codex started...
```

---

## Running on startup (optional)

To have the bot start automatically when you log into Windows:

1. Press `Win + R`, type `shell:startup`, press Enter
2. Create a shortcut to the following command in that folder:
   ```
   pythonw "C:\Users\91982\Downloads\claude-remote\telegram_claude_bot.py"
   ```
   (`pythonw` runs Python without a visible console window)

---

## Project files

```
claude-remote/
├── telegram_claude_bot.py   # Main bot script
├── requirements.txt         # Python dependencies
├── .env                     # Your config (never share this)
├── .env.example             # Config template
├── setup.bat                # One-time setup script
└── README.md                # This file
```

---

## Troubleshooting

**Bot doesn't respond**
- Check the console for errors
- Make sure `TELEGRAM_BOT_TOKEN` is correct in `.env`
- Only the user IDs listed in `ALLOWED_USER_IDS` can use the bot

**`/launch` says "Session already running"**
- Send `/stop` first, then `/launch`

**Output is cut off**
- Long output is split into multiple messages automatically (3800 chars each)
- Increase `OUTPUT_MAX_WAIT` in `.env` if responses are being cut short

**Claude/Codex/Gemini not found**
- Make sure the CLI is installed and available on your system PATH
- Test by opening `cmd.exe` manually and typing `claude` (or `codex`/`gemini`)
