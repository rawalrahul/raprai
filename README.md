<div align="center">

<img src="frontend2/assets/kelvin/avatar.png" width="96" alt="Kelvin, the RAPR AI penguin">

# RAPR AI

**Every AI you already pay for, working as one team. They reach every app any of them is connected to, brief you each morning on what needs you, and ask before they act. From your browser, your phone, or inside Claude Code.**

[![Version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Frawalrahul%2Fraprai%2Fmain%2F.codex-plugin%2Fplugin.json&query=%24.version&label=version)](release-notes/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
![Windows | macOS | Linux server](https://img.shields.io/badge/platforms-Windows%20%7C%20macOS%20%7C%20Linux%20server-blue)
[![Listed in awesome-ai-plugins](https://img.shields.io/badge/listed%20in-awesome--ai--plugins-fc60a8)](https://github.com/hashgraph-online/awesome-ai-plugins#tools--integrations)
[![HOL Guard](https://img.shields.io/endpoint?url=https%3A%2F%2Fhol.org%2Fapi%2Fregistry%2Fbadges%2Fplugin%3Fslug%3Drawalrahul%252Fraprai%26metric%3Dtrust)](https://hol.org/registry/plugins/rawalrahul%2Fraprai)
[![GitHub stars](https://img.shields.io/github/stars/rawalrahul/raprai?style=social)](https://github.com/rawalrahul/raprai/stargazers)

[Website](https://raprai.com) · [Install](#install) · [Features](#what-you-can-do) · [Full guide](docs/guide.md) · [Contributing](CONTRIBUTING.md)

<img src="docs/assets/demo-group-chat.gif" width="860" alt="A group chat in RAPR AI: Claude builds a /health endpoint, Antigravity reviews it, Codex updates the tests">

<sub>A group chat: Claude builds it, Antigravity reviews it, Codex updates the tests. (Demo recorded with scripted replies.)</sub>

</div>

---

## Why RAPR AI

You probably already pay for one or two AIs, and each lives in its own app or terminal with its own connected apps. RAPR AI puts them all in one place, and the whole is bigger than any one of them:

- **More reach than any single AI.** Claude Code has your claude.ai connectors (Gmail, Calendar, Slack, Drive…) and its MCP servers; Codex and Gemini have theirs; RAPR adds its own (any MCP server, Zapier, Composio). RAPR uses each app through the AI that already has it, with that AI's sign-in, so nothing is set up twice. Different accounts can live in different AIs: a work Gmail through Claude, a personal one through Codex.
- **It comes to you.** Each morning your **brief** lists what needs you, from all of those apps at once plus your approvals, unfinished sessions and scheduled tasks, with one tap to hand each item to the AI that has the app. Schedules and check-ins run as often as you like, on your computer or your own server.
- **It asks before it acts.** When an AI wants to send an email, post, merge, pay or delete in a connected app, it waits for your OK on your phone or in the app. That covers everything Claude Code can reach (its MCP servers, your claude.ai connectors and RAPR's apps) and tools any AI calls through RAPR, under one set of your rules and a tamper-evident audit log.
- **Use them together, not one at a time.** Group chats, bake-offs, second opinions and relays: Claude plans it, Codex builds it, Claude reviews it, the best answer wins.
- **Everywhere you are.** Browser, Telegram, WhatsApp, Discord, Slack, phone notifications, and inside Claude Code, Codex, Antigravity, Grok, Cursor or Windsurf as an MCP server, which also installs on its own without the app.
- **Bring the AIs you already have.** RAPR runs the official command-line tools with your own sign-ins, so your existing plans and limits just work. Nothing to sign up for. **Free and open source** (MIT); everything runs on your computer or your own server.

## What only RAPR does

An assistant from one AI company sees that company's connectors, runs that company's model, and lives in that company's app. RAPR sits above all of them:

| | One AI's own assistant | RAPR AI |
|---|---|---|
| **Apps it can see** | That AI's connectors | Every connected app of every AI you use, plus any MCP server, Zapier or Composio |
| **Accounts** | Usually one per app | Several: each AI can hold a different account of the same app |
| **Who does the work** | Its own model | Claude Code, Codex, Antigravity, Copilot, Cursor, Ollama and more; pick one, let **Auto** choose, or make them compete |
| **Schedules and briefs** | What that product offers | As many as you want, on your computer or server, running on your AI plans |
| **Where you use it** | Its own apps | Browser, Telegram, WhatsApp, Discord, Slack, and inside Claude Code, Codex, Antigravity, Grok, Cursor and Windsurf (MCP) |
| **Before it acts** | Its own rules | Your rules and one audit log over everything Claude Code reaches and every tool call through RAPR |
| **Price** | A subscription | Free (MIT), on the plans you already have |

## What you can do

| | |
|---|---|
| ☀️ **Your brief** | Each morning (and check-ins if you like) one list of what needs you: approvals, unfinished sessions, scheduled results, and what each AI you pick finds in its own connected apps. Arrives on Telegram, WhatsApp, Discord, Slack, your phone and under **Needs you**; one tap hands an item to the AI that has the app. |
| 🛡️ **Asks before acting** | An AI that wants to send, post, comment, merge, pay or delete in a connected app waits for your OK first, including Claude Code's own MCP servers and claude.ai connectors. Your rules can always allow, always ask or never allow; every decision is logged. |
| 💬 **Group chats** | Several AIs in one conversation. `@mention` who should answer, or `@all`. Ready-made **crews** give each AI a job: code review, research, launch, debate. |
| 🧪 **Bake-off** | Give the same task to several AIs. Each works in its own copy of your project; compare the diffs, test results and time, then merge the winner. Share the result as a card, or publish it to the public [RAPR Arena](https://www.raprai.com/arena) leaderboard. |
| 🔌 **RAPR inside your editor** | RAPR is an MCP server: from Claude Code, Codex, Antigravity, Grok, Cursor or Windsurf, ask another AI to review your changes, answer a question or join a bake-off, run a **relay** (one AI plans, another builds, another reviews and gets it fixed), or ask "what needs me today?" for your brief. Runs on your computer, with or without the app installed; your files stay untouched until you allow edits or merge. [Set it up](#use-rapr-inside-your-coding-agent-mcp) |
| 🐧 **Monthly recap** | Your month as a shareable card: your AI crew and its MVP, streaks, bake-offs, and what running AIs locally saved you. Worked out on your computer. |
| 🧭 **Smart routing** | Choose "Auto" and RAPR picks the AI for each task: free local models for easy work, the strongest coding agent for hard work, skipping any AI that's over budget. |
| 📱 **Phone control** | Telegram bot, WhatsApp (scan a QR code, no Business API), Discord and Slack. Start sessions, send tasks, approve actions, get your brief and hand items off with `/do`, get files back. |
| 🖥️ **Parallel sessions** | Many sessions at once, each with its own AI, folder and history. Resume any past conversation. |
| 🧠 **Shared memory & playbooks** | What one AI learns is available to the others. RAPR keeps how-to notes from past tasks. |
| ☁️ **Your own server** | One command installs RAPR on any Linux server (Oracle's free tier works) with a free public address, so it runs while your laptop is off. |

## Works with

**Coding agents** (they use your own sign-in): Claude Code · Codex · Antigravity · Grok · Copilot CLI · Cursor · OpenCode · Droid · Qwen Code · Kiro (Amazon Q) · Aider · Goose · Kilo Code · OpenClaw · Open Interpreter

**Free and local:** Claude Code and Codex on a local model through Ollama, plus Ollama on its own

**Models through an API key:** Groq · OpenRouter · GitHub Models · LM Studio and any OpenAI-compatible server

**Anything else:** add any agent that speaks the [Agent Client Protocol](https://agentclientprotocol.com) in Settings → Agents over ACP, or any command-line AI in Settings → AI Integrations.

**Any app with an MCP server:** click **+ Add MCP server** in RAPR Packages, paste its URL (or command, or the JSON snippet from its docs) and sign in. Every AI in RAPR can then use its tools.

Install the tools you want, and RAPR finds them. **Settings → AI Integrations** lists every supported AI with its install command.

## Install

One command on each platform. It installs the latest version, and the same command updates it later.

**Windows 10/11** (in PowerShell):
```powershell
irm https://raw.githubusercontent.com/rawalrahul/raprai/main/scripts/install-windows.ps1 | iex
```
Adds **RAPR AI** to your Start menu and desktop, plus a `rapr` command. Python 3.12 is installed for you if it's missing.

**macOS 12+** (in Terminal):
```bash
curl -fsSL https://raw.githubusercontent.com/rawalrahul/raprai/main/scripts/install-mac.sh | bash
```
Adds a **RAPR AI** app to your Applications, plus a `rapr` command.

**Linux server** (Ubuntu/Debian, x86 or ARM, over SSH):
```bash
curl -fsSL https://raw.githubusercontent.com/rawalrahul/raprai/main/scripts/install-server.sh | bash
```
RAPR runs in Docker and prints a free public address to open. See [docs/cloud-setup.md](docs/cloud-setup.md).

On first launch, a short setup page asks for a PIN and, optionally, a Telegram bot. Then pick an AI and start a session.

### Update and uninstall

| | Windows / macOS | Linux server |
|---|---|---|
| **Update** | **Settings → Updates → Update now**, or `rapr update` (or run the install command again) | `rapr update` |
| **Uninstall** | `rapr uninstall`: type `yes` to keep your chats and settings, `all` to delete them | `rapr remove` |
| **Start / stop** | `rapr start` / `rapr stop` (or the RAPR AI app) | `rapr restart` |
| **Status and logs** | `rapr status`, `rapr logs` | `rapr status`, `rapr logs`, `rapr url` |

**How RAPR knows about updates:** every hour it asks GitHub whether the branch it was installed from (`main` by default) has new commits. That's an ordinary web request carrying RAPR's version number; nothing else is sent. When there's something new, a dot appears on Settings, and **Settings → Updates** lists what changed. Offline, the check just skips. Turn it off in the same place (or set `UPDATE_CHECK=0` in `.env`); **Check now** still works.

Your chats and settings live in `%LOCALAPPDATA%\RAPR AI` (Windows) or `~/Library/Application Support/RAPR AI` (Mac), so updating keeps them. Used the old Windows `.exe` installer? Run the Windows command: it uses the same folder, so everything carries over. Then remove the old app in Windows Settings → Apps.

**From source:** see the [full guide](docs/guide.md#prerequisites).

**Only want RAPR inside your coding agent?** You don't need the app: see [Just the MCP server](#use-rapr-inside-your-coding-agent-mcp).

## Use RAPR inside your coding agent (MCP)

RAPR is an MCP server, so the AI you're already coding with (Claude Code, Codex, Antigravity, Grok, Cursor…) can ask the others for help. After installing RAPR, add it once:

```bash
claude mcp add --scope user rapr -- rapr mcp     # Claude Code
codex mcp add rapr -- rapr mcp                   # Codex
```

On Windows, end both with `-- cmd /c rapr mcp`. For Codex, also add `tool_timeout_sec = 600` under `[mcp_servers.rapr]` in `~/.codex/config.toml`: Codex gives up on a tool after 60 seconds, and a review usually takes a few minutes. Grok: `grok mcp add rapr -- rapr mcp`. Antigravity, Cursor, Windsurf and other clients: add a server with the command `rapr` and the argument `mcp` ([how, for each](docs/guide.md#use-rapr-from-your-coding-agent-mcp)).

**Just the MCP server, without the app:** if you have [uv](https://docs.astral.sh/uv/), use `uvx --from git+https://github.com/rawalrahul/raprai rapr-mcp` in place of `rapr mcp` (other ways, and how to update each: [Update, reset or remove](#update-reset-or-remove-the-mcp-server)):

```bash
claude mcp add --scope user rapr -- uvx --from git+https://github.com/rawalrahul/raprai rapr-mcp
```

Then ask in plain words: *"get a second opinion from Codex on my changes"*, *"plan this with Claude, have Codex build it and Claude review it"*, *"give part 1 of the plan to Claude and part 2 to Codex, I'll do part 3"*, *"run a bake-off between Claude and Codex on this task, with pytest -q"*, *"what needs me today?"*.

| Tool | What it does |
|---|---|
| `second_opinion` | Another AI reviews your uncommitted changes (or the last commit, or changes since a branch you name) and reports bugs, most serious first. |
| `ask_agent` | Puts any question or task to another AI and returns its reply. |
| `start_relay`, `relay_status`, `merge_relay`, `discard_relay` | Plan, build, review, fix: pick any AI for each role (say Claude plans, Codex builds, Claude reviews and Codex fixes what it found), all in a copy of the project until you merge. |
| `start_team`, `team_status`, `merge_team`, `discard_team` | Split a plan into parts: say Claude does the API and Codex the UI at the same time, each in its own copy, while you do your own part; then merge them all into the project. |
| `start_bakeoff`, `bakeoff_status`, `merge_bakeoff`, `discard_bakeoff` | A bake-off from your editor: 2 to 4 AIs, each in its own copy of the project; merge the one you like. |
| `list_agents` | The AIs installed and signed in on this computer. |
| `latest_brief` | What needs you, from your latest brief in the RAPR app (needs the app). |

The other AI works in a temporary copy of your project, so your files only change if you allow edits or merge a relay or bake-off. Nothing is hosted, and the RAPR app doesn't need to be open, or even installed. More in the [full guide](docs/guide.md#use-rapr-from-your-coding-agent-mcp).

RAPR only offers the AIs you can actually use: their command-line tool is installed (or came with their VS Code, Cursor or Windsurf extension), you're signed in where RAPR can check (Claude Code, Codex, Grok, Kiro), and a local model server like Ollama or LM Studio is running. Ask for `list_agents` to see them; it also says which installed AI still needs signing in, and how.

### GitHub Copilot

In **VS Code**, run **MCP: Open User Configuration** from the Command Palette and add:

```json
{
  "servers": {
    "rapr": { "type": "stdio", "command": "uvx",
              "args": ["--from", "git+https://github.com/rawalrahul/raprai", "rapr-mcp"] }
  }
}
```

Then switch Copilot Chat to **Agent** mode and turn on RAPR's tools. In **Copilot CLI**, add the same server with `/mcp add`, or in `~/.copilot/mcp-config.json` under `"mcpServers"`, with `"type": "local"` and `"tools": ["*"]`. With the app installed, use `"command": "rapr", "args": ["mcp"]` instead (on Windows, if `rapr` isn't found: `"command": "cmd", "args": ["/c", "rapr", "mcp"]`).

### Update, reset or remove the MCP server

There are three ways to run RAPR's MCP server, and each updates differently, so first find out which one you have.

| | **uvx** (recommended without the app) | **uv tool install** | **The app** |
|---|---|---|---|
| Set up with | Nothing to install: your client runs `uvx --from git+https://github.com/rawalrahul/raprai rapr-mcp` | `uv tool install git+https://github.com/rawalrahul/raprai` once, then your client runs `rapr-mcp` | The [app installer](#install), then your client runs `rapr mcp` |
| Your MCP config's command | `uvx` | `rapr-mcp` | `rapr` (or `cmd` with `/c rapr mcp` on Windows) |
| **To update** | `uv cache clean rapr-mcp` | `uv tool upgrade rapr-mcp` | `rapr update`, or **Settings → Updates** |
| **To remove the server** | `uv cache clean rapr-mcp` | `uv tool uninstall rapr-mcp` | `rapr uninstall` (see [Update and uninstall](#update-and-uninstall)) |

**Which to use.** Already using the app? Use `rapr mcp`; it updates with the app. Otherwise **uvx** is the simplest: nothing is installed, and `uv` keeps a copy in its cache. Pick **uv tool install** if you'd rather have a real `rapr-mcp` command that starts a little faster and is the same for every client. If `rapr-mcp` isn't found afterwards, run `uv tool update-shell` and open a new terminal. Use one of them, not several; if you switch, remove the old one as in the table.

**Which one you have.**

1. Look at RAPR's entry in your MCP client. In VS Code and Copilot CLI, open the MCP config (VS Code: **MCP: Open User Configuration**; Copilot CLI: `~/.copilot/mcp-config.json`). In Claude Code or Codex, run `claude mcp list` or `codex mcp list`. Its **command** tells you which: `uvx`, `rapr-mcp` or `rapr`, as in the table.
2. `uv tool list` lists `rapr-mcp` only if you used **uv tool install**.

**Why the update commands differ.** `uvx` runs the server from `uv`'s cache and keeps using the copy it downloaded first, without checking for a newer one. Clearing the cache makes the next start download the latest `main`. If `uv cache clean rapr-mcp` reports that it removed nothing, run `uv cache clean`; that clears everything `uv` downloaded, so other tools re-download once. To always start the latest instead, put `--refresh` before `--from` in your config; each start then checks GitHub and is a little slower. **uv tool install** puts a permanent copy outside the cache, so clearing the cache doesn't touch it, and `uv tool upgrade rapr-mcp` fetches the latest `main`.

**After updating,** restart your MCP client so it starts the new version (in VS Code, restart the `rapr` server or VS Code itself). Then ask for `list_agents` and look for the new tools in your client's tool list to check it worked.

**Something stuck?** Close your MCP client, run the update command for your setup from the table, and open the client again.

**Leftover copies.** RAPR works in copies of your project. Relay, team and `ask_agent` copies are removed when they finish or your client closes; if it crashed, delete the `rapr-mcp-*` folders in your system's temp folder. Bake-off copies stay in `~/.rapr-bakeoff` until you merge or discard the bake-off. After deleting any of these by hand, run `git worktree prune` in your project so git forgets them too, and delete the `bakeoff/…` branches if you don't want them.

**Remove it completely.**

1. Take RAPR out of your MCP client: `claude mcp remove rapr --scope user` (or without `--scope user` if you added it to one project), `codex mcp remove rapr`; in VS Code, Copilot CLI, Antigravity, Cursor, Windsurf and the rest, delete the `rapr` entry from their MCP settings.
2. Remove the server itself with the command in the table for your setup.
3. Optional, deletes your bake-off history and settings: the `RAPR AI` folder in `%LOCALAPPDATA%` (Windows), `~/Library/Application Support` (Mac) or `~/.local/share` (Linux). The app keeps its data there too, so leave it if you use the app.

## How it works

```
 Browser   ─┐                                    ┌─ Claude Code ─ Gmail, Calendar, Slack (claude.ai), GitHub
 Telegram  ─┤                                    ├─ Codex ─────── Linear, a second Gmail
 WhatsApp  ─┼─▶  RAPR AI  (one Python process) ──┼─ Antigravity
 Discord   ─┤    sessions · brief · group chats  ├─ Ollama        (offline)
 Slack     ─┤    approvals · rules · audit       └─ RAPR's own MCP servers, Zapier, Composio
 Your editor (Claude Code, Codex, Antigravity, Grok, Cursor: MCP)
```

RAPR starts each AI's own command-line tool in the folder you choose and streams its replies to every channel. Each AI keeps its own connected apps (Claude Code's claude.ai connectors and MCP servers, Codex's, Gemini's); RAPR reaches them by asking that AI, and adds a hook so Claude Code asks you before it acts in one. Your chats, settings and keys stay in RAPR's data folder on your machine; keys are encrypted.

## Documentation

- [Full guide](docs/guide.md): Telegram setup, every command, sessions, history, files, memory, packages and backups
- [Run it on your own server](docs/cloud-setup.md)
- [Release notes](release-notes/)

## Contributing

Ideas, bug reports and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md), and look for issues labelled **good first issue**. If RAPR AI is useful to you, a ⭐ helps other people find it.

## License

[MIT](LICENSE): use it, fork it, build on it.
