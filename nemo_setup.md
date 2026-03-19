# NemoClaw Setup Architecture

## How NemoClaw Works

NemoClaw is a security layer built by NVIDIA that wraps **OpenClaw** AI agents inside sandboxed containers managed by **OpenShell**. The architecture has four layers:

```
Windows Host
  └── WSL2 (Ubuntu)
        ├── OpenShell Gateway (Docker container on https://127.0.0.1:8080)
        │     └── Sandbox "mynemo" (Landlock + seccomp + netns isolation)
        │           └── OpenClaw Agent (uses Nemotron 3 Super 120B via NVIDIA Cloud API)
        └── NemoClaw CLI (orchestrates all of the above)
```

## Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **Docker Desktop** | Windows | Provides container runtime, WSL2 backend |
| **WSL2 + Ubuntu** | Windows feature | Linux environment where everything runs |
| **Node.js 22** | WSL (`/usr/bin/node`) | Required by NemoClaw and OpenClaw (v20+ needed) |
| **OpenShell CLI** | WSL (`~/.local/bin/openshell`) | NVIDIA's sandbox runtime — creates/manages secure containers |
| **NemoClaw CLI** | WSL (`/usr/bin/nemoclaw`) | Security orchestrator — wraps OpenClaw in sandboxed environments |
| **OpenClaw** | Inside sandbox (`/usr/local/bin/openclaw`) | The AI agent itself — chat interface to Nemotron 3 Super 120B |

## How RAPR AI Integrates

RAPR AI runs on Windows and communicates with NemoClaw through this chain:

```
RAPR AI (Windows Python)
  → wsl.exe -e bash -lc "..."       # Enter WSL from Windows
    → ssh (via openshell ssh-proxy)  # SSH into the sandbox
      → openclaw agent --agent main --message "..." --local
        → Nemotron 3 Super 120B (NVIDIA Cloud API)
      ← Response text
    ← SSH stdout
  ← WSL stdout
← Python subprocess.Popen stdout
```

Key design decisions:
- **STDIN_PROMPT = True**: The prompt is piped via stdin (not command-line) to avoid Windows' 32KB CreateProcess limit
- **SSH via openshell proxy**: `openshell sandbox connect` doesn't support non-interactive command execution, so we use SSH with `openshell ssh-proxy` as the ProxyCommand
- **--agent main --local**: Uses the embedded agent locally (no gateway routing needed for single-shot commands)

## File Locations

| File | Path | Purpose |
|------|------|---------|
| Integration module | `integrations/nemoclaw.py` | Builds the WSL→SSH→openclaw command |
| Bridge (detection) | `helm/ai_runner/nemoclaw_bridge.py` | Detects NemoClaw at startup, checks availability |
| Environment config | `.env` | `NEMOCLAW_SANDBOX`, `NEMOCLAW_AUTO_START`, `OPENSHELL_GATEWAY_ENDPOINT` |

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `NEMOCLAW_SANDBOX` | `mynemo` | Name of the OpenShell sandbox to connect to |
| `NEMOCLAW_AUTO_START` | `1` | Set to `0` if you manage the gateway manually |
| `OPENSHELL_GATEWAY_ENDPOINT` | *(none)* | Gateway URL (e.g., `https://127.0.0.1:8080`) |
| `OPENSHELL_GATEWAY` | `nemoclaw` | Gateway name for ssh-proxy routing |

## Verified Working Commands

From **inside the sandbox** (after `nemoclaw mynemo connect`):
```bash
openclaw tui                                          # Interactive chat
openclaw agent --agent main --message "hello" --local # One-shot command
```

From **Ubuntu host** (non-interactive, used by RAPR AI):
```bash
ssh -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    -o LogLevel=ERROR \
    -o "ProxyCommand=$HOME/.local/bin/openshell ssh-proxy --gateway-name nemoclaw --name mynemo" \
    sandbox@openshell-mynemo \
    'openclaw agent --agent main --message "hello" --local'
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `openclaw: command not found` | Not inside sandbox, or sandbox needs re-onboarding | Run `cd ~/NemoClaw && ./fix-and-onboard.sh` |
| `openshell gateway create` error | Wrong subcommand | Use `openshell gateway start` |
| `openshell sandbox exec` error | Subcommand doesn't exist | Use SSH via openshell proxy instead |
| `wsl.exe not found in PATH` | Windows 32KB command-line limit exceeded | Use `STDIN_PROMPT = True` |
| `Connection closed by UNKNOWN` | Sandbox SSH not ready | Destroy and recreate: `nemoclaw mynemo destroy` then re-onboard |
| Gateway detection fails in app | `_find_cli("nemoclaw")` looks on Windows PATH | App uses bridge's `is_available()` for NemoClaw detection |
