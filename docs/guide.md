# RAPR AI — full guide

This is the detailed guide: running from source, Telegram setup, every command, and how each feature works.
For the quick install, see the [README](../README.md#install).

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Windows 10/11, macOS, or Linux | The Windows installer and the Mac / server one-liners in the [README](../README.md#install) set all of this up for you. These steps are for running from source. |
| Python 3.10+ | [python.org](https://www.python.org/downloads/) — tick "Add to PATH" during install |
| A Telegram account | To create the bot and receive messages |
| Claude Code installed | `claude` must be on your PATH (or whichever AI CLIs you want to use) |

---

## Step 1 — Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a name (e.g. `My RAPR AI`)
4. Choose a username ending in `bot` (e.g. `my_raprai_bot`)
5. BotFather replies with a token:
   ```
   123456789:ABCDefgh-XXXXXXXXXXXXXXXXXXXXXXX
   ```
   Copy it — you'll need it in Step 3.

6. *(Optional)* Give your bot Kelvin's face: send `/setuserpic` to **@BotFather**, pick your bot, and upload `frontend2/assets/kelvin/avatar.png`.

> **Desktop Kelvin.** On Windows a small Kelvin sits on your desktop. Drag him anywhere, scroll the mouse wheel over him to resize (small, medium, large), hover and click ✕ to hide him, or right-click for *Hide for 1 hour* and *Show → Only while AI works* (he then appears only when an AI is working or needs your approval). The same choices are in the tray menu (**Kelvin on desktop**) and **Settings → Personalization**.

> **Kelvin stickers.** Kelvin, the RAPR AI penguin, can also send a sticker when a long task or pipeline finishes, when a run fails, and alongside approval requests. It's off by default: turn on **Settings → Personalization → Kelvin stickers on Telegram**.

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

Open `.env` in any text editor and fill in the required values (or use the setup wizard at `http://localhost:8000/setup` on first run):

```env
TELEGRAM_BOT_TOKEN=123456789:ABCDefgh-XXXXXXXXXXXXXXXXXXXXXXX
ALLOWED_USER_IDS=987654321
```

> **Note:** API keys and tokens are automatically migrated to an encrypted vault on first run. After migration, `.env` entries show `vault-managed` as a placeholder — the real values are Fernet-encrypted in SQLite.

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
> C:\...\raprai\launch.bat  C:\projects\website
> ```
> Give each shortcut a different name and pin them to your taskbar.

---

## Sessions — the core concept

RAPR AI is built around sessions. Each session is an independent process with its own AI, working directory, and conversation history. You can run as many as you like simultaneously.

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
│  ◈ RAPR AI                                   ≡  ●      │  ← header (history / connection)
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
| `/kelvin` | Is RAPR on? Uptime, what's running, approvals waiting, next schedule, keep-awake. No reply means RAPR is off or the PC is asleep |
| `/brief` | Your latest brief, with a button per item: ▶ hands it to its AI, ✕ drops it, ✅/❌ answers an approval. `/brief now` puts a fresh one together |
| `/stop` | Stops the focused session |
| `/interrupt` | Sends Ctrl+C to the focused session |
| `/stop_ai` | Removes the AI from the focused session (keeps terminal running as shell) |
| `/clear` | Clears the Claude conversation history for the focused session |

**Group chats**

| Command | What it does |
|---------|-------------|
| `/group` | Lists your group chats as buttons; tap one to enter it, or ➕ New group to tick AI sessions and create one |
| `/group <number>` | Enters that group: your messages (typed or voice) now go to every member, and each reply comes back signed by the AI that wrote it |
| `/group new <name>: 1 3` | Creates a group from AI sessions 1 and 3 (`/group new` lists them) |
| `/group who` / `/group stop` / `/group leave` | Members, stop the replies in progress, back to a single session (tapping a session also leaves) |

Inside a group, start a message with `@Name` (or `@all`) to choose who answers.

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

## Your brief and Needs you

Every morning RAPR puts one short list of what needs you in front of you, the way an assistant would, but built from **all** the AIs you already use.

**Where it looks**

- **Inside RAPR**, at no cost: approvals waiting for you, sessions you left unfinished, and what your scheduled tasks answered (failures first).
- **Through your AIs' own apps.** Each AI keeps its own connections: Claude Code has your claude.ai connectors (Gmail, Google Calendar, Slack, Drive…) and the MCP servers you added to it; Codex and Gemini have theirs. RAPR doesn't need a second copy of any of them, or of their sign-ins: it asks the AI that has the app to look. Pick several AIs, or the same AI twice, and the brief covers several accounts (a work Gmail through Claude, a personal one through Codex) and more apps than any one AI reaches.

**Set it up:** **Settings → Your brief**.

1. **Send my brief** at a time you choose (08:00 by default), and optionally **Check in again** every 2, 3 or 4 hours until 9 pm. A check-in only arrives when something new needs you.
2. **Ask these AIs to look**: each line is one AI and what it should look at, in plain words, for example *Claude Code: my Gmail, calendar and Slack* or *Codex: GitHub, with the gh command: pull requests waiting for my review and failing checks*. Add a folder to run it inside a project, so it checks that repository. Under the list, RAPR suggests lines from the apps each AI already has.
3. **What your AIs can reach** lists every AI's connected apps, and RAPR's own (Packages). **Check again** asks the AIs afresh.

**How it arrives:** on Telegram, with a button per item; on WhatsApp, Discord and Slack as a numbered list; as a phone notification; and in the app under **Needs you**, the first section of the sidebar. The bell's badge counts what's waiting.

**One tap to hand it off.** Each item can carry a next step (draft the reply, fix the failing test, review the pull request). **▶ Hand to Claude** (or Codex, or whichever AI found it) starts a session with that AI, with the item and its link as the task. On WhatsApp, Discord or Slack reply `/do 2`; `/skip 2` drops an item, `/brief` shows the latest brief and `/brief now` puts a fresh one together. Approvals in the brief can be answered right there.

**What it costs and what it can do:** the looks run on your own AI plans and count toward their usage, like any other task; inside-RAPR items cost nothing. The looks only read: if an AI tries to send or change something during one, RAPR refuses it and tells the AI to list it as a suggestion. When you hand an item off, anything that AI then wants to send or change asks you first (below). While the brief is on, the old Heartbeat check-in stays quiet so you don't get both. Turn the brief off in the same place.

## Ask before an AI acts in your apps

When an AI wants to **send an email, post a message, comment, merge, pay, sign or delete** something in a connected app, it asks you first, like a risky command does: in the app (the banner and **Needs you**), on Telegram, WhatsApp and your phone (on Discord and Slack, `/approvals` lists them). You see which AI, which app, and the details (recipient, subject, channel, pull request…). Reading never asks. With no answer within 10 minutes (**Wait for my answer**), the action is skipped and the AI is told it's waiting for your OK, so it can carry on with the rest.

This covers:

- **Claude Code**, through a hook RAPR adds when it starts Claude: RAPR's own MCP servers, the MCP servers you added to Claude Code, and your claude.ai connectors.
- **Any AI calling tools through RAPR itself**: RAPR's tool loop and its local tool endpoint.
- **ACP agents** already ask through their own permission requests.

Codex and Gemini call the apps in their own settings directly, including RAPR's apps (RAPR copies them there), so those calls follow Codex's and Gemini's own approval settings.

**Your rules decide first.** **Settings → Approvals & audit** rules now apply to every tool call: `allow` + `slack.*post` lets Slack posts through without asking, `deny` + `merge` never lets an AI merge, `ask` + `postgres.*query` asks even for a tool that only reads. The description a rule matches names the AI, the action and the app, e.g. *Claude wants to send email in Gmail*. Every decision is in the audit log. To stop asking altogether, set **Ask before acting in your apps** to *Don't ask (only my rules)*.

## Group chats

Open **👥 Group Chats** in the header (or the sidebar section), pick any of your open AI sessions, and chat with all of them at once.

- Each message gets up to 3 rounds and 10 replies. Members answer one at a time and see the whole conversation, so they build on each other instead of repeating.
- `@Name` (full name, name without spaces, or first word) or `@all` picks who answers; a member can pull another in the same way. A member with nothing to add replies `(pass)` and stays quiet.
- A new message or **Stop** ends the replies in progress. Groups are saved, and a member keeps answering from its saved AI/model/folder even after its session is closed.
- The same group can be used from the web UI, Telegram and WhatsApp at once; every app that's in the group sees every message.
- Kelvin shows a crew for the group while it answers: one Kelvin per member in its AI's beanie, working, done or waiting. It also counts as work for the tray, keep-awake, `/kelvin` and the "done" sticker.

---

## Bake-offs and RAPR Arena

Pick **🧪 Bake-off (compare AIs)** in the AI menu, choose a project folder, a task, 2 to 4 AIs and (optionally) a test command. Each AI works in its own copy of the project; the board shows each attempt's time, files and lines changed, test result and diff. **Merge this one** applies the winner to your project; **Discard all** throws every copy away.

Once you've merged a winner (or discarded them all), **🏆 Share result** opens a card you can share:

- **Copy text**, **Download image** or **Post on X**. These stay on your computer until you post them.
- **Publish to RAPR Arena** adds the result to the public leaderboard at [raprai.com/arena](https://www.raprai.com/arena), where everyone's bake-offs show which AI wins which kind of task, and gives you a link to a page for your result.
  - What's sent: the AIs and models, how long each took, files and lines changed, whether your tests passed, which one you merged, the kind of task (which you can change), the main language and RAPR's version. **Exactly what gets sent** in the dialog shows the request before you press Publish.
  - Never sent: your code, file names, folder paths or what the AIs said. The task text is only included if you tick the box, and you can edit it first.
  - Nothing is sent until you press **Publish**. `ARENA_URL` in `.env` points RAPR at a different Arena server.

Finished bake-offs are kept (the numbers only, not the code), so they count toward your monthly recap.

## Use RAPR from Claude Code, Cursor or Codex (MCP)

RAPR is also an MCP server, so the AI you're coding with can call the others. The `rapr mcp` command comes with the Windows and Mac installs; from a source checkout, use `python /path/to/raprai/rapr_mcp.py` wherever you see `rapr mcp` below.

### Claude Code

```
claude mcp add --scope user rapr -- rapr mcp
```

On Windows: `claude mcp add --scope user rapr -- cmd /c rapr mcp`. `--scope user` makes RAPR available in every project; leave it out to add RAPR to the current project only. Check it with `claude mcp list` (it should say *Connected*), or `/mcp` inside Claude Code.

### Codex

```
codex mcp add rapr -- rapr mcp
```

On Windows: `codex mcp add rapr -- cmd /c rapr mcp`. Then give RAPR more time: Codex stops waiting for a tool after 60 seconds, and another AI's review usually takes longer. Open `~/.codex/config.toml` (on Windows `%USERPROFILE%\.codex\config.toml`) and add the `tool_timeout_sec` line to the `[mcp_servers.rapr]` section the command wrote:

```toml
[mcp_servers.rapr]
command = "rapr"
args = ["mcp"]
tool_timeout_sec = 600
```

Check it with `codex mcp list`, or `/mcp` inside Codex.

### Cursor, Windsurf and other MCP clients

Add a server with the command `rapr` and the argument `mcp` (on Windows: command `cmd`, arguments `/c rapr mcp`). For example, in Cursor's `~/.cursor/mcp.json`:

```json
{ "mcpServers": { "rapr": { "command": "rapr", "args": ["mcp"] } } }
```

### Using it

Ask in plain words: *"get a second opinion from Codex on my changes"*, *"ask Antigravity how it would structure this"*, *"run a bake-off between Claude and Codex on this task, with pytest -q"*. From Codex, ask for Claude's opinion the same way.

| Tool | What it does |
|---|---|
| `second_opinion` | Another AI reviews your uncommitted changes (or the last commit, or changes since a branch you name) and reports bugs and risks, most serious first. |
| `ask_agent` | Sends any question or task to another AI and returns its reply. |
| `start_bakeoff`, `bakeoff_status`, `merge_bakeoff`, `discard_bakeoff` | The same bake-off as in the app: 2 to 4 AIs, each in its own copy of the project. Merge the one you like (staged, not committed). |
| `list_agents` | The AIs that are installed and set up on this computer. |
| `latest_brief` | What needs you, from your latest brief in the RAPR app: approvals, unfinished work, scheduled results and what your AIs found in their apps. |

- **It runs on your computer.** Your MCP client starts `rapr mcp` itself and talks to it over stdin/stdout. Nothing is hosted, and the RAPR app doesn't need to be open. The AIs run through their own command-line tools with your sign-ins, as in a bake-off.
- **Your files are safe by default.** `second_opinion` and `ask_agent` run the other AI in a temporary copy of the project, including your uncommitted changes. If it edits anything, you get the diff back; your files don't change. Pass `allow_edits` to `ask_agent` to let it work in the real folder.
- Each call takes as long as the other AI does, usually a minute or a few. Bake-offs run in the background: `start_bakeoff` returns an id, and `bakeoff_status` waits up to 50 seconds per call (inside Codex's time limit, even without `tool_timeout_sec`), so your AI calls it again until the results are in. Bake-offs from MCP are kept like the app's, so they count in your monthly recap.


**🐧 Your month with RAPR** (top of the **Usage** panel, or in the AI menu) turns a month of work into a card: tasks sent, AI replies, active days and longest streak, your AI crew and its MVP, bake-offs judged, tasks sent from your phone, and a title for the month ("The Conductor", "Night Owl", "Local Hero"…). Use **‹ Previous** to look back. At the start of each month RAPR offers last month's recap once.

- It's worked out on your computer from your chat history, group chats and bake-offs. Nothing is uploaded; the image only leaves your computer if you post it.
- Dollar figures are estimates from the text you saw (about 4 characters per token, at API list prices). "Saved" is local AI work (Ollama and other local models) priced as if Claude's API had done it. AIs also read files and run tools you don't see, so real figures are higher; the card says "at least".

---

## WhatsApp

Free WhatsApp control through [neonize](https://github.com/krypton-byte/neonize) (whatsmeow): RAPR joins your WhatsApp as a linked device, the same way WhatsApp Web does. No Meta developer account, no per-message fees.

1. **Settings → WhatsApp → Link WhatsApp**.
2. On your phone: WhatsApp → Settings → **Linked devices** → **Link a device**, and scan the QR code.
3. Open your **"Message yourself"** chat and type. Your message goes to the focused session (or the group chat you're in) and the reply comes back there.

| Message | What it does |
|---------|-------------|
| any text | Sent to the focused session, or to your group chat |
| `/sessions`, `/use 2` | List sessions, switch to session 2 |
| `/new claude` | Start a session (any AI: `gemini`, `codex`, `ollama`, …) |
| `/group …` | Group chats, same commands as on Telegram |
| `/brief`, `/brief now` | Your latest brief, or a fresh one |
| `/do 2`, `/skip 2` | Hand brief item 2 to its AI, or drop it |
| `/approvals`, `/approve <id>`, `/deny <id>` | Actions waiting for your OK |
| `/status`, `/help` | What's running; the command list |

RAPR only acts on your "Message yourself" chat and on numbers you add under **Also accept messages from** (for when RAPR is linked to a spare number). Chats with other people, groups and statuses are ignored. **Unlink** in Settings, or removing the device on your phone, disconnects it. WhatsApp's terms don't cover unofficial clients, so a dedicated or spare number is the safest choice.

---

## File Auto-Send

When an AI creates a file in the session's working directory, RAPR AI detects it and sends it to Telegram automatically. The message includes which session produced the file.

| File type | Extensions | Telegram action |
|-----------|-----------|----------------|
| Photo | `.png` `.jpg` `.jpeg` `.gif` `.webp` `.bmp` | Sent as photo |
| Animated GIF | `.gif` | Sent as animation |
| Video | `.mp4` `.mov` `.avi` `.mkv` `.webm` | Sent as video |
| Document | `.pdf` `.pptx` `.ppt` `.docx` `.doc` `.xlsx` `.xls` `.csv` `.html` `.htm` `.zip` `.tar` `.gz` `.txt` `.md` | Sent as document |

Files up to **50 MB** are supported. The web UI also shows a clickable link at `http://localhost:8000/files/<filename>`.

---

## Chat History

Every session is auto-saved to the SQLite database (`raprai.db`). Nothing to configure.

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

- History is not AI memory — each CLI is stateless. Resume works by loading conversation summaries and recent messages as context for your next session.
- All data is stored in `raprai.db` (SQLite with WAL mode). Legacy `chat_logs/` files are auto-migrated on first run.
- Custom session names are stored in the database alongside chat history.
- Use the Cloud Backup feature (Settings → Cloud Backup) to back up the database to OneDrive, Google Drive, Dropbox, or a local folder.

---

## Adding AI integrations

RAPR AI supports two ways to add new AI integrations:

### From the Settings UI (recommended)

Open Settings (gear icon) → scroll to "Add Custom AI Integration" → fill in the key, name, command template, and optional fields → click Add. The new AI appears immediately in the session picker — no restart needed.

Command templates support `{prompt}` and `{model}` placeholders. Enable "Pipe prompt via stdin" if your CLI reads from stdin instead of command-line arguments.

### From the integrations/ folder

Drop a `.py` file into the `integrations/` folder and restart. Each file defines KEY, NAME, EMOJI, COLOR, and a `build_command(prompt)` function. See `integrations/_template.py` for the format.

---

## Shared AI Memory

RAPR AI maintains a persistent memory store that all AI sessions share. Knowledge learned in one AI session is available to all others.

**How it works:** Relevant memories are automatically injected into AI prompts based on keyword matching. Memories can be added manually or extracted automatically at session end.

**Adding memories:**
- Type `/remember <fact>` in any chat session
- Use the Memory panel in the sidebar to quick-add entries
- When a session ends, an AI reads what you typed (never the AI's replies) next to the memories that look related, and adds new lasting facts, updates ones that changed, or archives ones that are no longer true. One-off requests like "fix this bug" are skipped, and pinned memories are never touched. It uses Ollama if it's running on your computer; otherwise, for a Claude session, Claude's small Haiku model (your messages already went to Anthropic). Anything else falls back to simple phrase matching ("remember: …", "my name is …"). A conversation is never sent somewhere it didn't already go. Choose with `MEMORY_EXTRACTOR` in `.env`: `auto` (default), `ollama`, `claude`, `regex` or `off`.

**Memory categories:** preference, fact, project, person, decision, instruction

**Memory panel:** Open from the sidebar to browse, search, pin, archive, or delete memories. Pinned memories are always injected into AI prompts.

---

## RAPR Packages

Browse, search, and one-click install packages (MCP servers, skills, plugins) from the unified RAPR Packages sidebar panel. The Installed tab shows all detected skills, plugins, and MCP servers in one view. The Browse tab lets you discover and install new packages from the catalog.

Upload `.raprpkg` files to install from local packages. Each `.raprpkg` is a ZIP with a `manifest.json` describing the package type, dependencies, and metadata. Installs are atomic with automatic rollback on failure.

### Add any MCP server

Any app that has an MCP server can be connected without waiting for RAPR to support it. In the RAPR Packages panel, click **+ Add MCP server** and pick one of:

- **Server URL**: paste the app's hosted MCP URL (usually ending in `/mcp` or `/sse`) and choose how to sign in:
  - *Sign in with my account*: a sign-in page for the app opens; approve access and you're done.
  - *API key or token*: sent as `Authorization: Bearer <key>`.
  - *Custom headers*: for apps that want something like `X-API-Key`.
  - *Sign in with a code*: for a RAPR running on a server with no browser (the app must support the OAuth device flow).
  - *No sign-in needed*.
- **Command**: a server RAPR starts on this computer (for example `npx -y @modelcontextprotocol/server-github`), with environment variables for its API keys.
- **Paste JSON**: the `mcpServers` snippet apps publish for Claude Desktop, Cursor or VS Code. Every server in it is added.

Once a server is connected, every AI in RAPR can use its tools: Claude Code gets it through `--mcp-config`, Codex and Gemini through their own config files, and Ollama and the API AIs (Groq, OpenRouter...) through RAPR's tool calling. Each server's card shows its status, the reason if it couldn't connect, and **Reconnect** / **Sign in again** and **Remove** buttons.

Remote servers are bridged with [`mcp-remote`](https://www.npmjs.com/package/mcp-remote), so they need Node.js. Keys, tokens and URLs are stored encrypted in RAPR's vault; the server list is kept in RAPR's data folder (`custom_mcp_servers.json`), so updates don't remove it.

---

## Cloud Backup

Back up the full RAPR AI database to cloud storage or a local folder. Configure from Settings → Cloud Backup.

Supported providers: OneDrive, Google Drive, Dropbox, and local/network folder. Each provider uses OAuth 2.0 for authentication (tokens stored in the encrypted vault). The local provider requires no authentication — just set a folder path.

No OAuth apps are bundled: to use OneDrive, Google Drive or Dropbox, register your own app with the provider and set its credentials in `.env` (`BACKUP_GDRIVE_CLIENT_ID`, `BACKUP_GDRIVE_CLIENT_SECRET`, etc. — see `.env.example`) or in Settings → Cloud Backup.

Schedule automatic backups (daily or weekly at a chosen time), or trigger a manual backup with the "Backup Now" button. Each backup is a ZIP containing the SQLite database, a SHA-256 checksum, and a manifest with table row counts. Job history shows status, size, and timestamps for recent backups.

---

## Running on startup (optional)

To start automatically when you log into Windows:

1. Press `Win + R`, type `shell:startup`, press Enter
2. Create a shortcut pointing to:
   ```
   pythonw "C:\path\to\raprai\web_app.py"
   ```
   (`pythonw` runs Python without a visible console window.)

---

## Project files

```
RAPR-AI/
├── web_app.py            # Main entry point (Web UI + Telegram bot + session manager)
├── requirements.txt      # Python dependencies
├── .env                  # Your config (secrets auto-migrated to encrypted vault)
├── .env.example          # Config template
├── setup.bat             # One-time setup (install deps, create .env)
├── launch.bat            # Daily launcher — accepts optional path argument
├── helm/                 # Core application package
│   ├── ai_runner/        # AI session management (core.py, ollama.py)
│   ├── frontend/         # Modular web UI (template.html, styles.css, JS modules)
│   ├── packages/         # RAPR Packages system (installer, catalog)
│   ├── mcp/              # MCP server management
│   ├── web_routes/       # FastAPI route modules
│   ├── db.py             # SQLite database (WAL mode, FTS5)
│   ├── cloud_backup/     # Cloud backup system (OneDrive, GDrive, Dropbox, local)
│   ├── db_migrate.py     # Schema migrations (currently v8)
│   ├── integrations.py   # AI integration loader (file-based + custom JSON)
│   ├── memory.py         # Shared AI memory system (encrypted at rest)
│   ├── token_vault.py    # Fernet-encrypted credential vault
│   ├── security.py       # Security constants and helpers
│   ├── plugins.py        # Plugin system
│   └── skills.py         # Skill registry
├── integrations/         # AI plugin definitions (one .py per AI)
│   ├── _template.py      # Template for new integrations
│   ├── gemini.py
│   └── codex.py
├── raprai.db             # SQLite database (auto-created)
├── README.md             # This file
└── chat_logs/            # Legacy (migrated to SQLite)
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

---

