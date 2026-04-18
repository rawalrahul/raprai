"""Shell/CLI node executor."""

import asyncio
import os
import re
import subprocess
import sys


async def execute_shell_node(node: dict, context: str, cwd: str = ".") -> str:
    """Run node['task'] as a shell command and return stdout/stderr."""
    command = node.get("task", "").strip()
    if not command:
        return "Error: shell node has no command"

    timeout = node.get("timeout", 60)

    # Build env: inherit current env + node-specific vars
    env = os.environ.copy()
    node_env = node.get("env_vars") or {}
    env.update({str(k): str(v) for k, v in node_env.items()})

    if sys.platform == "win32":
        return await _execute_windows_shell(command, timeout=timeout, cwd=cwd, env=env)

    proc = None
    try:
        kwargs = {
            "stdout": asyncio.subprocess.PIPE,
            "stderr": asyncio.subprocess.PIPE,
            "cwd": cwd,
            "env": env,
            "start_new_session": True,  # B11: own process group for group-kill
        }
        if sys.platform != "win32":
            kwargs["executable"] = "/bin/bash"
        proc = await asyncio.create_subprocess_shell(command, **kwargs)

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            _kill_proc_tree(proc)
            try:
                await asyncio.wait_for(proc.communicate(), timeout=2)
            except Exception:
                pass
            return f"Error: command timed out after {timeout}s\nCommand: {command}"

        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()
        parts = []
        if out:
            parts.append(out)
        if err:
            parts.append(f"[stderr]\n{err}")
        return "\n".join(parts) if parts else "(no output)"
    except asyncio.CancelledError:
        # B11: ensure child process does not outlive the cancelled node.
        if proc and proc.returncode is None:
            _kill_proc_tree(proc)
            try:
                await asyncio.wait_for(proc.communicate(), timeout=2)
            except Exception:
                pass
        raise
    except Exception as exc:
        return f"Error executing shell command: {exc}\nCommand: {command}"


async def _execute_windows_shell(command: str, timeout: float, cwd: str, env: dict) -> str:
    """Run a Windows shell command without asyncio's overlapped pipe path."""
    command = _cmd_env_refs_to_powershell(command)
    executable = (
        os.environ.get("POWERSHELL_EXE")
        or r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
    )
    args = [executable, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command]
    proc = None
    started = asyncio.get_running_loop().time()
    # B11: CREATE_NEW_PROCESS_GROUP lets taskkill /T target the whole tree.
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    try:
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=env,
            creationflags=creationflags,
        )
        while proc.poll() is None:
            if timeout and timeout > 0 and asyncio.get_running_loop().time() - started > timeout:
                _kill_windows_tree(proc)
                return f"Error: command timed out after {timeout}s\nCommand: {command}"
            await asyncio.sleep(0.05)
        stdout, stderr = proc.communicate()
        return _format_shell_output(stdout, stderr)
    except asyncio.CancelledError:
        if proc and proc.poll() is None:
            _kill_windows_tree(proc)
        raise
    except Exception as exc:
        return f"Error executing shell command: {exc}\nCommand: {command}"


def _kill_windows_tree(proc: "subprocess.Popen") -> None:
    """Terminate a Windows Popen + any child processes."""
    if not proc or proc.poll() is not None:
        return
    try:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3,
        )
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    try:
        proc.wait(timeout=1)
    except subprocess.TimeoutExpired:
        pass


def _kill_proc_tree(proc) -> None:
    """Kill an asyncio subprocess's process group where supported."""
    if proc is None or proc.returncode is not None:
        return
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
            )
            return
        except Exception:
            pass
    try:
        import os as _os
        import signal as _signal
        _os.killpg(_os.getpgid(proc.pid), _signal.SIGKILL)
        return
    except Exception:
        pass
    try:
        proc.kill()
    except Exception:
        pass


def _cmd_env_refs_to_powershell(command: str) -> str:
    """Support common %VAR% references when executing via PowerShell."""
    return re.sub(r"%([A-Za-z_][A-Za-z0-9_]*)%", r"$env:\1", command)


def _format_shell_output(stdout: bytes, stderr: bytes) -> str:
    out = stdout.decode("utf-8", errors="replace").strip()
    err = stderr.decode("utf-8", errors="replace").strip()
    parts = []
    if out:
        parts.append(out)
    if err:
        parts.append(f"[stderr]\n{err}")
    return "\n".join(parts) if parts else "(no output)"
