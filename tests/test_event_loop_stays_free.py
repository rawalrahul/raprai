"""Slow work runs off the event loop, so RAPR keeps answering meanwhile.

RAPR is one asyncio process: a blocking call inside an async function freezes
the web UI, the chat apps and every other session until it returns. Local
Ollama replies (up to 10 minutes), cloud backup uploads and the pipeline
planner all used to block it.
"""
import asyncio
import os
import stat
import subprocess
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


async def _ticks_while(coro) -> tuple[object, int]:
    """Run *coro* and count how often another task got to run meanwhile."""
    ticks = 0
    done = asyncio.Event()

    async def ticker():
        nonlocal ticks
        while not done.is_set():
            ticks += 1
            await asyncio.sleep(0.01)

    t = asyncio.create_task(ticker())
    try:
        return await coro, ticks
    finally:
        done.set()
        await t


def test_backup_provider_calls_run_off_the_loop():
    from helm.cloud_backup.providers import off_loop

    class SlowProvider:
        async def upload(self, path, folder, name):
            time.sleep(0.5)          # what the providers' urllib calls do
            return {"ok": True, "remote_id": f"{folder}/{name}"}

    result, ticks = asyncio.run(_ticks_while(off_loop(SlowProvider().upload, "p", "/f", "b.zip")))
    assert result == {"ok": True, "remote_id": "/f/b.zip"}
    assert ticks >= 10, "the event loop was blocked during the upload"


def test_installed_models_parses_ollama_list(monkeypatch):
    from helm.ai_runner import ollama
    out = ("NAME          ID            SIZE    MODIFIED\n"
           "qwen3:4b      abc123        2.5 GB  2 days ago\n"
           "llama3.2:3b   def456        2.0 GB  3 weeks ago\n")
    monkeypatch.setattr(ollama.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 0, out, ""))
    assert ollama.installed_models() == ["qwen3:4b", "llama3.2:3b"]


def test_installed_models_without_ollama(monkeypatch):
    from helm.ai_runner import ollama

    def missing(*a, **k):
        raise FileNotFoundError("ollama")
    monkeypatch.setattr(ollama.subprocess, "run", missing)
    assert ollama.installed_models() == []


@pytest.mark.skipif(sys.platform == "win32", reason="uses a POSIX shell script as a stand-in")
def test_windows_shell_step_returns_large_output(tmp_path, monkeypatch):
    """It waited for PowerShell to exit before reading its output, so a command
    printing more than the pipe holds hung until the timeout."""
    from helm.agent.nodes import shell
    fake = tmp_path / "powershell"
    fake.write_text("#!/bin/sh\nhead -c 300000 /dev/zero | tr '\\0' x\n")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("POWERSHELL_EXE", str(fake))
    out = asyncio.run(shell._execute_windows_shell("dir", timeout=10, cwd=str(tmp_path),
                                                   env=dict(os.environ)))
    assert out == "x" * 300000


@pytest.mark.skipif(sys.platform == "win32", reason="uses a POSIX shell script as a stand-in")
def test_windows_shell_step_times_out(tmp_path, monkeypatch):
    from helm.agent.nodes import shell
    fake = tmp_path / "powershell"
    fake.write_text("#!/bin/sh\nexec sleep 30\n")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("POWERSHELL_EXE", str(fake))
    started = time.monotonic()
    out = asyncio.run(shell._execute_windows_shell("x", timeout=0.5, cwd=str(tmp_path),
                                                   env=dict(os.environ)))
    assert out.startswith("Error: command timed out") and time.monotonic() - started < 10
