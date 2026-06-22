"""
helm/terminal.py — TerminalSession (persistent shell wrapper) and ANSI output cleaner.

Cross-platform: wraps cmd.exe on Windows and the user's login shell
($SHELL, falling back to /bin/bash then /bin/sh) on macOS/Linux.
"""

import os
import queue
import signal
import subprocess
import sys
import threading

from helm.config import ANSI_ESCAPE, IDLE_TIMEOUT, MAX_WAIT, NO_OUTPUT_TIMEOUT

IS_WINDOWS = sys.platform == "win32"


def _shell_command() -> list[str]:
    """Return the argv for an interactive shell on this platform."""
    if IS_WINDOWS:
        return ["cmd.exe"]
    # POSIX: prefer the user's login shell, then bash, then sh.
    shell = os.environ.get("SHELL")
    for candidate in (shell, "/bin/bash", "/bin/sh"):
        if candidate and os.path.exists(candidate):
            return [candidate, "-i"]
    return ["/bin/sh", "-i"]


def _spawn_kwargs() -> dict:
    """Platform-specific Popen kwargs for a controllable shell process group.

    Windows: hide the console window and put the child in its own process
    group so we can send CTRL_C_EVENT.
    POSIX: start a new session (setsid) so we can signal the whole group.
    """
    if IS_WINDOWS:
        return {
            "creationflags": (subprocess.CREATE_NO_WINDOW
                              | subprocess.CREATE_NEW_PROCESS_GROUP),
        }
    return {"start_new_session": True}


# ---------------------------------------------------------------------------
# ANSI output cleaner
# ---------------------------------------------------------------------------

def clean_output(raw: str) -> str:
    """Strip ANSI escape codes and collapse carriage-return overwriting."""
    text = ANSI_ESCAPE.sub("", raw)
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        parts = line.split("\r")
        result = ""
        for part in parts:
            if part:
                result = part
        cleaned.append(result)
    return "\n".join(cleaned)


# Keep the original private name as an alias so any code that still calls
# the old name continues to work during the transition.
_clean_output = clean_output


# ---------------------------------------------------------------------------
# TerminalSession
# ---------------------------------------------------------------------------

class TerminalSession:
    """Wraps a persistent shell subprocess with a non-blocking output queue.

    Uses cmd.exe on Windows and the login shell on macOS/Linux.
    """

    def __init__(self):
        self._proc: subprocess.Popen | None = None
        self._q: queue.Queue = queue.Queue()
        self._reader_thread: threading.Thread | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_loop(self):
        try:
            for line in self._proc.stdout:
                self._q.put(line)
        except Exception:
            pass
        self._q.put(None)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def launch(self):
        with self._lock:
            if self._proc and self._proc.poll() is None:
                raise RuntimeError("Session already running (PID %d)" % self._proc.pid)
            self._q = queue.Queue()
            self._proc = subprocess.Popen(
                _shell_command(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=0,
                **_spawn_kwargs(),
            )
            self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._reader_thread.start()

    def is_alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def pid(self) -> int | None:
        return self._proc.pid if self._proc else None

    def write(self, text: str):
        if not self.is_alive():
            raise RuntimeError("No active session. Use /launch first.")
        self._proc.stdin.write(text + "\n")
        self._proc.stdin.flush()

    def drain(
        self,
        idle_timeout: float = IDLE_TIMEOUT,
        max_wait: float = MAX_WAIT,
        no_output_timeout: float = NO_OUTPUT_TIMEOUT,
    ) -> str:
        import time
        chunks: list[str] = []
        start = time.monotonic()
        got_first = False

        while True:
            elapsed = time.monotonic() - start
            if elapsed >= max_wait:
                break
            if got_first:
                timeout = idle_timeout
            else:
                remaining = no_output_timeout - elapsed
                if remaining <= 0:
                    break
                timeout = min(remaining, no_output_timeout)
            try:
                item = self._q.get(timeout=timeout)
            except queue.Empty:
                break
            if item is None:
                break
            chunks.append(item)
            got_first = True

        raw = "".join(chunks)
        return clean_output(raw)

    def send_interrupt(self):
        if not self.is_alive():
            raise RuntimeError("No active session.")
        if IS_WINDOWS:
            # Child is in its own process group (CREATE_NEW_PROCESS_GROUP).
            os.kill(self._proc.pid, signal.CTRL_C_EVENT)
        else:
            # Child started a new session (setsid); signal its whole group.
            try:
                os.killpg(os.getpgid(self._proc.pid), signal.SIGINT)
            except (ProcessLookupError, PermissionError):
                self._proc.send_signal(signal.SIGINT)

    def stop(self):
        if self._proc:
            try:
                self._proc.kill()
            except Exception:
                pass
            self._proc = None
