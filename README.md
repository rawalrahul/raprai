<div align="center">

<img src="frontend2/assets/kelvin/avatar.png" width="96" alt="Kelvin, the RAPR AI penguin">

# RAPR AI

**Run Claude Code, Codex, Antigravity, Ollama and more side by side, let them work together in group chats, and control them from your browser, Telegram or WhatsApp.**

[![Latest release](https://img.shields.io/github/v/release/rawalrahul/rapr-releases?label=release)](https://github.com/rawalrahul/rapr-releases/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
![Windows | macOS | Linux server](https://img.shields.io/badge/platforms-Windows%20%7C%20macOS%20%7C%20Linux%20server-blue)
[![GitHub stars](https://img.shields.io/github/stars/rawalrahul/raprai?style=social)](https://github.com/rawalrahul/raprai/stargazers)

[Website](https://raprai.com) · [Install](#install) · [Features](#what-you-can-do) · [Full guide](docs/guide.md) · [Contributing](CONTRIBUTING.md)

<img src="docs/assets/demo-group-chat.gif" width="860" alt="A group chat in RAPR AI: Claude builds a /health endpoint, Antigravity reviews it, Codex updates the tests">

<sub>A group chat: Claude builds it, Antigravity reviews it, Codex updates the tests. (Demo recorded with scripted replies.)</sub>

</div>

---

## Why RAPR AI

You probably already pay for one or two AI coding agents, and each lives in its own terminal. RAPR AI puts them all in one place:

- **Use them together, not one at a time.** Put Claude Code, Codex and Antigravity in one group chat. Ask once; they answer, review each other's work and hand off with `@mentions`.
- **Leave your desk.** Every session is reachable from your phone through Telegram or WhatsApp, and you get a notification when an AI needs your approval.
- **Bring the AIs you already have.** RAPR runs the official command-line tools with your own sign-ins, so your existing plans and limits just work. There's nothing to sign up for.
- **Free and open source** under the MIT license. Everything runs on your computer (or your own server).

## What you can do

| | |
|---|---|
| 💬 **Group chats** | Several AIs in one conversation. `@mention` who should answer, or `@all`. Ready-made **crews** give each AI a job: code review, research, launch, debate. |
| 🧪 **Bake-off** | Give the same task to several AIs. Each works in its own copy of your project; compare the diffs, test results and time, then merge the winner. |
| 🧭 **Smart routing** | Choose "Auto" and RAPR picks the AI for each task: free local models for easy work, the strongest coding agent for hard work, skipping any AI that's over budget. |
| 📱 **Phone control** | Telegram bot and WhatsApp (scan a QR code, no Business API). Start sessions, send tasks, approve actions, get files back. |
| 🖥️ **Parallel sessions** | Many sessions at once, each with its own AI, folder and history. Resume any past conversation. |
| 🛡️ **Your rules** | Decide what always needs a yes, what is never allowed and what can run on its own. Every decision is logged. |
| 🧠 **Shared memory & playbooks** | What one AI learns is available to the others. RAPR keeps how-to notes from past tasks. |
| ☁️ **Your own server** | One command installs RAPR on any Linux server (Oracle's free tier works) with a free public address, so it runs while your laptop is off. |

## Works with

**Coding agents** (they use your own sign-in): Claude Code · Codex · Antigravity · Copilot CLI · Cursor · OpenCode · Droid · Qwen Code · Kiro (Amazon Q) · Aider · Goose · Kilo Code · OpenClaw · Open Interpreter

**Free and local:** Claude Code and Codex on a local model through Ollama, plus Ollama on its own

**Models through an API key:** Groq · OpenRouter · GitHub Models · LM Studio and any OpenAI-compatible server

**Anything else:** add any agent that speaks the [Agent Client Protocol](https://agentclientprotocol.com) in Settings → Agents over ACP, or any command-line AI in Settings → AI Integrations.

Install the tools you want, and RAPR finds them. **Settings → AI Integrations** lists every supported AI with its install command.

## Install

**Windows:** download the installer from [raprai.com](https://raprai.com) or the [latest release](https://github.com/rawalrahul/rapr-releases/releases/latest), run it, and follow the setup page that opens.
> Windows SmartScreen may warn because the installer isn't code-signed yet: click **More info → Run anyway**.

**macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/rawalrahul/raprai/main/scripts/install-mac.sh | bash
```
This adds a **RAPR AI** app to your Applications and a `rapr` command.

**Linux server** (Ubuntu/Debian, x86 or ARM):
```bash
curl -fsSL https://raw.githubusercontent.com/rawalrahul/raprai/main/scripts/install-server.sh | bash
```
RAPR runs in Docker and prints a public address to open. `rapr url`, `rapr logs` and `rapr update` manage it. See [docs/cloud-setup.md](docs/cloud-setup.md).

**From source:** see the [full guide](docs/guide.md#prerequisites).

On first launch, a short setup page asks for a PIN and (optionally) a Telegram bot. Then pick an AI and start a session.

## How it works

```
 Browser  ─┐                                     ┌─ Claude Code  (~/projects/web)
 Telegram ─┼─▶  RAPR AI  (one Python process) ──┼─ Codex        (~/projects/web)
 WhatsApp ─┘    sessions · group chats · rules   ├─ Antigravity  (~/projects/api)
                                                 └─ Ollama       (offline)
```

RAPR starts each AI's own command-line tool in the folder you choose and streams its replies to every channel. Your chats, settings and keys stay in RAPR's data folder on your machine; keys are encrypted.

## Documentation

- [Full guide](docs/guide.md): Telegram setup, every command, sessions, history, files, memory, packages and backups
- [Run it on your own server](docs/cloud-setup.md)
- [Release notes](release-notes/)

## Contributing

Ideas, bug reports and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md), and look for issues labelled **good first issue**. If RAPR AI is useful to you, a ⭐ helps other people find it.

## License

[MIT](LICENSE): use it, fork it, build on it.
