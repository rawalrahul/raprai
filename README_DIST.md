# RAPR AI — Getting Started

Welcome to RAPR AI, your personal AI command center. This guide will get you up and running in a few minutes.

---

## What's Included

Everything you need to run RAPR AI is already bundled in this folder — no Python installation required. Just run the setup script to install a few optional external tools, then launch the app.

| File / Folder | Purpose |
|---|---|
| `web_app.exe` | The main RAPR AI application |
| `setup_dist.bat` | One-time setup script for external tools |
| `helm/frontend/` | Web UI assets (CSS, HTML, JS) |

---

## Quick Start

### Step 1 — Run Setup (one time only)

Double-click **`setup_dist.bat`**. It will check for and install the external tools listed below. You only need to do this once.

### Step 2 — Launch RAPR AI

Double-click **`web_app.exe`**. A terminal window will open showing the server log. After a few seconds, open your browser and go to:

```
http://localhost:8000
```

On first launch, a **Setup Wizard** will walk you through configuring your API keys, Telegram bot (optional), and a PIN to protect the web UI.

### Step 3 — You're Done

RAPR AI is now running. Leave the terminal window open — closing it stops the server.

---

## Prerequisites

RAPR AI has **no hard prerequisites** — it will run on its own. However, certain features depend on external tools. The setup script handles all of these automatically via `winget`, but you can also install them manually if needed.

### Required for full functionality

| Tool | What it enables | Install |
|---|---|---|
| **Node.js** (LTS) | Word (.docx) and PowerPoint (.pptx) file creation | [nodejs.org/en/download](https://nodejs.org/en/download/) |
| **docx** (npm) | Word document generation | Installed automatically by setup script |
| **pptxgenjs** (npm) | PowerPoint slide generation | Installed automatically by setup script |

### Optional tools

| Tool | What it enables | Install |
|---|---|---|
| **Pandoc** | Reading and converting existing .docx files | [pandoc.org/installing](https://pandoc.org/installing.html) |
| **FFmpeg** | Voice message transcription (Telegram) | [ffmpeg.org/download](https://ffmpeg.org/download.html) |
| **Tesseract OCR** | Text extraction from scanned PDFs | [github.com/UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki) |

> **Note:** RAPR AI will run fine without any of these. Features that depend on a missing tool will show a helpful message telling you what to install.

---

## System Requirements

- **OS:** Windows 10 or later (64-bit)
- **RAM:** 4 GB minimum, 8 GB recommended
- **Disk:** ~500 MB for the application folder
- **Browser:** Any modern browser (Chrome, Edge, Firefox)
- **Network:** Internet connection required for AI providers (Gemini, Claude, OpenAI). Ollama works fully offline.

---

## Configuration

All configuration is stored in a `.env` file that RAPR AI creates automatically on first launch. You can configure everything through the web UI:

- **Settings panel** — API keys, model selection, Telegram bot token
- **Settings → WhatsApp** — link RAPR to WhatsApp by scanning a QR code, then talk to it from your "Message yourself" chat
- **👥 Group Chats** (header button) — put several AIs in one chat; also from Telegram with `/group`
- **Setup Wizard** — runs automatically on first launch to walk you through initial setup
- **PIN protection** — optional login PIN to secure the web UI

---

## Troubleshooting

**The terminal window opens and closes immediately**
Right-click `web_app.exe` → Open in Terminal (or run it from an existing Command Prompt) to see the error message.

**"Missing CSRF token" error**
Clear your browser cookies for `localhost:8000` and refresh the page.

**Setup wizard keeps looping back to step 1**
Delete the `.env` file in the application folder and relaunch — the wizard will start fresh.

**Node.js features not working after install**
Close and reopen your terminal, then relaunch `web_app.exe` so it picks up the updated PATH.

**Port 8000 already in use**
Another application is using port 8000. Close it first, or set a custom port by adding `WEB_PORT=9000` to your `.env` file.

---

## Updating

When a new version of RAPR AI is available, simply replace the contents of this folder with the new release. Your `.env` file and any data will be preserved.

---

## Support

If you run into issues, reach out to the RAPR AI team with:

1. The error message (screenshot or copy-paste from the terminal)
2. Your Windows version (`Settings → System → About`)
3. Whether you ran `setup_dist.bat` successfully
