"""
NVIDIA NemoClaw integration — sandboxed AI agent via WSL + OpenShell.

NemoClaw wraps OpenClaw inside a secure sandbox (Landlock + seccomp + netns)
with NVIDIA cloud inference (Nemotron 3 Super 120B via build.nvidia.com).

Setup:
  1. Install WSL2 + Ubuntu: wsl --install (then restart PC)
  2. Install Docker Desktop with WSL2 integration enabled
  3. Follow the NemoClaw setup guide at https://your-site.com/nemoclaw-setup
  4. Set NEMOCLAW_SANDBOX=mynemo in .env (or whatever sandbox name you chose)
  5. Restart RAPR AI — NemoClaw appears in the AI selector automatically.

Free to use — only requires a free NVIDIA API key from build.nvidia.com.
"""

import logging
import os
import sys

# ── Identity ─────────────────────────────────────────────────────────────────

KEY   = "nemoclaw"
NAME  = "NemoClaw"
EMOJI = "🐲"
COLOR = "#76b900"   # NVIDIA green

# ── Logging (to file for debugging) ──────────────────────────────────────────

_nc_log = logging.getLogger("nemoclaw_integration")
_nc_log.setLevel(logging.DEBUG)

# File handler — logs to nemoclaw_debug.log next to the app
try:
    from helm.paths import user_data_dir
    _log_path = user_data_dir() / "nemoclaw_debug.log"
except Exception:
    _log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nemoclaw_debug.log")

try:
    _fh = logging.FileHandler(str(_log_path), encoding="utf-8")
    _fh.setLevel(logging.DEBUG)
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _nc_log.addHandler(_fh)
except Exception:
    pass


# ── Helpers ──────────────────────────────────────────────────────────────────

def _sandbox_name() -> str:
    """Return the configured sandbox name."""
    try:
        import helm.state as _st
        dm = _st.default_models.get("nemoclaw", "")
        if dm:
            return dm
    except Exception:
        pass
    return os.environ.get("NEMOCLAW_SANDBOX", "mynemo").strip()


# ── Command builder ──────────────────────────────────────────────────────────

def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    """
    Build a WSL command that SSHs into the NemoClaw sandbox and runs
    openclaw agent with the prompt.

    Requires Windows with WSL2. Prompt piped via stdin (STDIN_PROMPT = True)
    to avoid the 32 KB CreateProcess command-line limit.
    Uses openshell ssh-proxy to run commands non-interactively inside the sandbox.
    """
    if sys.platform != "win32":
        raise RuntimeError(
            "NemoClaw requires Windows with WSL2. "
            "Not supported on this platform."
        )

    sandbox = _sandbox_name()

    # The WSL script:
    # 1. Reads the prompt from stdin (piped by run_ai_popen)
    # 2. SSHs into the sandbox using openshell's ssh-proxy
    # 3. Runs openclaw agent with --agent main through the managed gateway route
    # 4. Returns the response through stdout
    gateway_name = os.environ.get("OPENSHELL_GATEWAY", "nemoclaw")
    openshell_bin = "$HOME/.local/bin/openshell"

    # OPENCLAW_AGENT_CMD lets users patch the inner command without a recompile
    # if openclaw changes its flag syntax (e.g. --local removed, subcommand renamed).
    inner_cmd = os.environ.get("OPENCLAW_AGENT_CMD", "openclaw agent --agent main")

    # Capture stderr separately so Node.js warnings (UNDICI-EHPA etc.)
    # don't pollute stdout.  On failure (rc!=0) the stderr is appended
    # so real error messages are still visible.
    wsl_script = (
        f'export PATH="$HOME/.local/bin:$PATH" && '
        f'B64=$(cat | base64 -w0) && '
        f'_NC_ERR=$(mktemp) && '
        f'_NC_OUT=$( ssh -o StrictHostKeyChecking=no '
        f'-o UserKnownHostsFile=/dev/null '
        f'-o LogLevel=ERROR '
        f'-o "ProxyCommand={openshell_bin} ssh-proxy '
        f'--gateway-name {gateway_name} --name {sandbox}" '
        f'sandbox@openshell-{sandbox} '
        f'"{inner_cmd} '
        f'--message \\"\\$(echo $B64 | base64 -d)\\"" '
        f'2>"$_NC_ERR" ) ; _NC_RC=$? ; '
        f'echo "$_NC_OUT" ; '
        f'[ $_NC_RC -ne 0 ] && cat "$_NC_ERR" ; '
        f'rm -f "$_NC_ERR" ; exit $_NC_RC'
    )

    _nc_log.info("build_command called | sandbox=%s | prompt_len=%d", sandbox, len(prompt))
    _nc_log.debug("WSL script: %s", wsl_script)

    # Use wsl.exe (with .exe extension) for reliable Windows resolution.
    _ext = ".exe" if sys.platform == "win32" else ""
    return [f"wsl{_ext}", "-e", "bash", "-lc", wsl_script]


# Prompt is piped via stdin — NOT embedded in the command line.
# This is critical on Windows where CreateProcess has a 32 KB limit.
STDIN_PROMPT = True

# ── Metadata ─────────────────────────────────────────────────────────────────

ENV_VARS: list[str] = ["NEMOCLAW_SANDBOX", "OPENSHELL_GATEWAY", "OPENCLAW_AGENT_CMD"]

SETUP_HINT: str = (
    "NemoClaw requires WSL2 + Docker Desktop + OpenShell.  |  "
    "Follow the setup guide at your RAPR AI setup page.  |  "
    "Get a free NVIDIA API key from https://build.nvidia.com  |  "
    "Set NEMOCLAW_SANDBOX=your-sandbox-name in .env"
)
