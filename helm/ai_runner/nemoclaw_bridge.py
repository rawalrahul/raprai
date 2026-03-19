"""
helm/ai_runner/nemoclaw_bridge.py — NemoClaw WSL bridge for RAPR AI.

Manages the full NemoClaw lifecycle automatically:
  - Detect if NemoClaw is installed in WSL
  - Auto-launch Docker Desktop if not running
  - Wait for Docker to become ready
  - Start the OpenShell gateway automatically
  - Check sandbox health
  - Provide status info for the UI

Called from web_app.py at startup and from the integration when needed.
The goal: user launches RAPR AI → everything else happens automatically.
"""

import glob
import logging
import os
import subprocess
import sys
import time
from typing import Optional

from helm.config import logger

# ── File-based debug logger ──────────────────────────────────────────────────
_nc_log = logging.getLogger("nemoclaw_bridge")
_nc_log.setLevel(logging.DEBUG)

try:
    from helm.paths import user_data_dir
    _log_path = user_data_dir() / "nemoclaw_debug.log"
except Exception:
    _log_path = "nemoclaw_debug.log"

try:
    _fh = logging.FileHandler(str(_log_path), encoding="utf-8")
    _fh.setLevel(logging.DEBUG)
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(funcName)s: %(message)s"))
    _nc_log.addHandler(_fh)
except Exception:
    pass

# Cache availability so we don't shell out to WSL on every message
_nemoclaw_available: Optional[bool] = None
_gateway_started: bool = False

# All WSL commands get PATH prepended so nemoclaw/openshell are found
_WSL_PATH_PREFIX = 'export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:$PATH" && '


def _wsl_exe() -> str:
    """Return the full path to wsl.exe, falling back to bare 'wsl' if not found."""
    import pathlib as _pl
    default = r"C:\Windows\System32\wsl.exe"
    return default if _pl.Path(default).exists() else "wsl"


def _run_wsl(cmd: str, timeout: int = 15) -> tuple[int, str, str]:
    """Run a command inside WSL and return (returncode, stdout, stderr)."""
    full_cmd = _WSL_PATH_PREFIX + cmd
    _nc_log.debug("_run_wsl: %s (timeout=%ds)", cmd, timeout)
    try:
        r = subprocess.run(
            [_wsl_exe(), "-e", "bash", "-lc", full_cmd],
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        _nc_log.debug("_run_wsl result: rc=%d stdout=%r stderr=%r",
                       r.returncode, r.stdout.strip()[:200], r.stderr.strip()[:200])
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        _nc_log.warning("_run_wsl timeout: %s", cmd)
        return -1, "", "timeout"
    except FileNotFoundError:
        _nc_log.warning("_run_wsl: wsl not found")
        return -1, "", "wsl not found"
    except Exception as e:
        _nc_log.error("_run_wsl exception: %s", e)
        return -1, "", str(e)


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def check_wsl_available() -> bool:
    """Check if WSL is available on this Windows machine."""
    if sys.platform != "win32":
        logger.debug("NemoClaw: not on Windows, skipping")
        return False
    try:
        r = subprocess.run(
            [_wsl_exe(), "--status"],
            capture_output=True, text=True, timeout=10,
        )
        return r.returncode == 0
    except Exception:
        return False


def check_nemoclaw_installed() -> bool:
    """Check if nemoclaw CLI exists inside WSL."""
    rc, out, _ = _run_wsl("which nemoclaw 2>/dev/null")
    return rc == 0 and out != ""


def check_openshell_installed() -> bool:
    """Check if openshell CLI exists inside WSL."""
    rc, out, _ = _run_wsl("which openshell 2>/dev/null")
    return rc == 0 and out != ""


def check_docker_running() -> bool:
    """Check if Docker is accessible from WSL."""
    rc, _, _ = _run_wsl("docker info >/dev/null 2>&1")
    return rc == 0


# ---------------------------------------------------------------------------
# Docker Desktop auto-launch
# ---------------------------------------------------------------------------

_DOCKER_DESKTOP_PATHS = [
    os.path.expandvars(r"%ProgramFiles%\Docker\Docker\Docker Desktop.exe"),
    os.path.expandvars(r"%ProgramFiles(x86)%\Docker\Docker\Docker Desktop.exe"),
    os.path.expandvars(r"%LocalAppData%\Docker\Docker Desktop.exe"),
    os.path.expandvars(r"%APPDATA%\Docker\Docker Desktop.exe"),
]


def _find_docker_desktop() -> Optional[str]:
    """Find the Docker Desktop executable on Windows."""
    for path in _DOCKER_DESKTOP_PATHS:
        if os.path.isfile(path):
            return path
    # Fallback: search common install locations with glob
    for pattern in [
        r"C:\Program Files\Docker\Docker\Docker Desktop.exe",
        r"C:\Program Files (x86)\Docker\Docker\Docker Desktop.exe",
    ]:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
    return None


def _is_docker_desktop_process_running() -> bool:
    """Check if Docker Desktop process is running on Windows (fast, no WSL needed)."""
    try:
        r = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Docker Desktop.exe", "/NH"],
            capture_output=True, text=True, timeout=10,
        )
        return "Docker Desktop.exe" in r.stdout
    except Exception:
        return False


def launch_docker_desktop(max_wait: int = 90) -> bool:
    """
    Launch Docker Desktop if not running, wait for it to be ready.

    Returns True if Docker is accessible from WSL after launch.
    Waits up to max_wait seconds for Docker engine to become ready.
    """
    # Already running and accessible?
    if check_docker_running():
        logger.info("NemoClaw: Docker already running and accessible from WSL")
        return True

    # Check if the process is at least running (might still be starting up)
    if _is_docker_desktop_process_running():
        logger.info("NemoClaw: Docker Desktop process found, waiting for engine...")
    else:
        # Need to actually launch Docker Desktop
        docker_path = _find_docker_desktop()
        if not docker_path:
            logger.warning("NemoClaw: Docker Desktop not found on this machine")
            return False

        logger.info("NemoClaw: launching Docker Desktop from %s", docker_path)
        try:
            # Launch detached — Docker Desktop is a GUI app that manages itself
            subprocess.Popen(
                [docker_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.DETACHED_PROCESS
                | subprocess.CREATE_NO_WINDOW
                if sys.platform == "win32" else 0,
            )
        except Exception as exc:
            logger.warning("NemoClaw: failed to launch Docker Desktop: %s", exc)
            return False

    # Wait for Docker engine to become ready (accessible from WSL)
    logger.info("NemoClaw: waiting for Docker engine (up to %ds)...", max_wait)
    start = time.time()
    poll_interval = 5  # seconds between checks

    while time.time() - start < max_wait:
        if check_docker_running():
            elapsed = int(time.time() - start)
            logger.info("NemoClaw: Docker engine ready (took %ds)", elapsed)
            return True
        time.sleep(poll_interval)

    logger.warning("NemoClaw: Docker engine not ready after %ds", max_wait)
    return False


# ---------------------------------------------------------------------------
# Full detection (with optional auto-launch)
# ---------------------------------------------------------------------------

def detect_nemoclaw(auto_launch_docker: bool = False) -> dict:
    """
    Full availability check. Returns a status dict:
    {
        "available": bool,
        "wsl": bool,
        "docker": bool,
        "openshell": bool,
        "nemoclaw": bool,
        "docker_launched": bool,   # True if we had to launch Docker
        "message": str,
    }
    """
    global _nemoclaw_available

    _nc_log.info("=== detect_nemoclaw started (auto_launch_docker=%s) ===", auto_launch_docker)

    result = {
        "available": False,
        "wsl": False,
        "docker": False,
        "openshell": False,
        "nemoclaw": False,
        "docker_launched": False,
        "message": "",
    }

    if sys.platform != "win32":
        result["message"] = "NemoClaw requires Windows with WSL2"
        _nemoclaw_available = False
        _nc_log.info("Not on Windows — skipping")
        return result

    # Step 1: WSL
    result["wsl"] = check_wsl_available()
    _nc_log.info("WSL available: %s", result["wsl"])
    if not result["wsl"]:
        result["message"] = "WSL2 is not installed or not running"
        _nemoclaw_available = False
        return result

    # Step 2: Check if NemoClaw + OpenShell are installed BEFORE dealing with Docker
    # (no point launching Docker if NemoClaw isn't even installed)
    result["openshell"] = check_openshell_installed()
    _nc_log.info("OpenShell installed: %s", result["openshell"])
    if not result["openshell"]:
        result["message"] = "OpenShell CLI not found in WSL — follow the NemoClaw setup guide"
        _nemoclaw_available = False
        return result

    result["nemoclaw"] = check_nemoclaw_installed()
    _nc_log.info("NemoClaw installed: %s", result["nemoclaw"])
    if not result["nemoclaw"]:
        result["message"] = "NemoClaw not found in WSL — follow the NemoClaw setup guide"
        _nemoclaw_available = False
        return result

    # Step 3: Docker (auto-launch if configured)
    result["docker"] = check_docker_running()
    _nc_log.info("Docker running: %s", result["docker"])
    if not result["docker"]:
        if auto_launch_docker:
            _nc_log.info("Docker not running, attempting auto-launch...")
            logger.info("NemoClaw: Docker not running, attempting auto-launch...")
            docker_ready = launch_docker_desktop()
            if docker_ready:
                result["docker"] = True
                result["docker_launched"] = True
                _nc_log.info("Docker auto-launched successfully")
            else:
                result["message"] = (
                    "Docker Desktop could not be started automatically. "
                    "Please start Docker Desktop manually."
                )
                _nemoclaw_available = False
                _nc_log.warning("Docker auto-launch failed")
                return result
        else:
            result["message"] = "Docker Desktop is not running"
            _nemoclaw_available = False
            return result

    result["available"] = True
    result["message"] = "NemoClaw is ready"
    _nemoclaw_available = True
    _nc_log.info("=== detect_nemoclaw complete: AVAILABLE ===")
    return result


def is_available() -> bool:
    """Quick cached check — returns True if NemoClaw was detected at startup."""
    global _nemoclaw_available
    if _nemoclaw_available is None:
        detect_nemoclaw()
    return bool(_nemoclaw_available)


# ---------------------------------------------------------------------------
# Gateway lifecycle
# ---------------------------------------------------------------------------

def is_gateway_running() -> bool:
    """Check if the OpenShell gateway named 'nemoclaw' is running."""
    rc, out, _ = _run_wsl("openshell gateway list 2>/dev/null", timeout=20)
    if rc != 0:
        return False
    return "nemoclaw" in out


def start_gateway() -> bool:
    """Start the OpenShell gateway if not already running. Returns True if ready."""
    global _gateway_started

    if is_gateway_running():
        _gateway_started = True
        logger.info("NemoClaw: gateway already running")
        _nc_log.info("Gateway already running")
        return True

    logger.info("NemoClaw: starting OpenShell gateway...")
    _nc_log.info("Starting OpenShell gateway...")
    rc, out, err = _run_wsl(
        "openshell gateway start --name nemoclaw 2>&1",
        timeout=120,
    )

    _nc_log.info("Gateway create result: rc=%d out=%r err=%r", rc, out[:300], err[:300])

    if rc == 0:
        _gateway_started = True
        logger.info("NemoClaw: gateway started successfully")
        _nc_log.info("Gateway started successfully")
        return True
    else:
        logger.warning("NemoClaw: gateway start failed: %s %s", out, err)
        _nc_log.warning("Gateway start FAILED: %s %s", out, err)
        return False


def stop_gateway() -> bool:
    """Stop the OpenShell gateway."""
    global _gateway_started
    rc, _, _ = _run_wsl("openshell gateway destroy --name nemoclaw 2>&1", timeout=30)
    _gateway_started = False
    return rc == 0


# ---------------------------------------------------------------------------
# Sandbox status
# ---------------------------------------------------------------------------

def get_sandbox_status(sandbox_name: str = "") -> dict:
    """Get the status of a NemoClaw sandbox."""
    name = sandbox_name or os.environ.get("NEMOCLAW_SANDBOX", "mynemo")
    rc, out, err = _run_wsl(f"nemoclaw {name} status 2>&1", timeout=20)

    return {
        "sandbox": name,
        "running": rc == 0,
        "output": out or err,
    }


# ---------------------------------------------------------------------------
# Startup routine (called from web_app.py)
# ---------------------------------------------------------------------------

def startup_check() -> None:
    """
    Run at app startup — full automated NemoClaw bootstrap:

    1. Check if NemoClaw + OpenShell are installed in WSL
    2. If Docker isn't running → auto-launch Docker Desktop
    3. Wait for Docker engine to become ready
    4. Start the OpenShell gateway
    5. Verify sandbox is accessible

    This is failure-safe — if anything goes wrong, NemoClaw simply
    shows as unavailable in the UI. Nothing blocks the main app.
    """
    global _nemoclaw_available, _gateway_started

    auto_start = os.environ.get("NEMOCLAW_AUTO_START", "1").strip().lower()
    should_auto_start = auto_start in ("1", "true", "yes")

    # Run detection with Docker auto-launch enabled
    status = detect_nemoclaw(auto_launch_docker=should_auto_start)

    if not status["available"]:
        logger.info("NemoClaw: not available — %s", status["message"])
        return

    if status.get("docker_launched"):
        logger.info("NemoClaw: Docker Desktop was auto-launched")

    logger.info("NemoClaw: detected (WSL + Docker + OpenShell + NemoClaw all present)")

    # Auto-start gateway
    if should_auto_start:
        try:
            if start_gateway():
                logger.info("NemoClaw: gateway ready, sandbox integration active")
            else:
                logger.warning(
                    "NemoClaw: gateway failed to start — "
                    "integration available but may not work until gateway is running"
                )
        except Exception as exc:
            logger.warning("NemoClaw: gateway auto-start error: %s", exc)
    else:
        logger.info("NemoClaw: auto-start disabled (NEMOCLAW_AUTO_START=0)")
