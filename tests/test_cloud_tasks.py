"""Cloud tasks: /cloud claude|codex from a chat app, with the tools faked."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

import helm.cloud_tasks as ct

CLAUDE_OUT = ("\x1b[32m✔\x1b[0m Created cloud session: Add a /health endpoint\n"
              "View: https://claude.ai/code/session_01AbCdEf\n"
              "Resume with: claude --teleport session_01AbCdEf\n")
CODEX_OUT = "Submitted task_e_68ab12cd. https://chatgpt.com/codex/tasks/task_e_68ab12cd\n"


@pytest.fixture
def cloud(tmp_path, monkeypatch):
    """Tools 'installed', a git folder for Claude, a Codex env, and a recorder for commands."""
    monkeypatch.setenv("RAPR_DATA_DIR", str(tmp_path / "data"))
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    monkeypatch.setenv("CLOUD_CLAUDE_FOLDER", str(repo))
    monkeypatch.setenv("CODEX_CLOUD_ENV", "env_123")
    monkeypatch.delenv("CODEX_CLOUD_BRANCH", raising=False)
    monkeypatch.setattr(ct, "_exe", lambda name: f"/bin/{name}")
    calls = []
    answers = {"claude": (0, CLAUDE_OUT), "exec": (0, CODEX_OUT),
               "status": (0, "Status: running"), "diff": (0, "+ added line")}

    async def fake_run(cmd, cwd=None, timeout=0):
        calls.append((cmd, cwd))
        if cmd[0].endswith("claude"):
            return answers["claude"] if "-p" not in cmd else (0, "Sent to cloud session.")
        return answers[cmd[2]]
    monkeypatch.setattr(ct, "run", fake_run)
    monkeypatch.setattr(ct, "watch", lambda task: None)
    return {"calls": calls, "answers": answers, "repo": str(repo)}


def test_reads_the_session_and_task_ids():
    c = ct.parse_started("claude", CLAUDE_OUT)
    assert c == {"id": "session_01AbCdEf", "url": "https://claude.ai/code/session_01AbCdEf",
                 "title": "Add a /health endpoint"}
    x = ct.parse_started("codex", CODEX_OUT)
    assert x["id"] == "task_e_68ab12cd" and x["url"].endswith("task_e_68ab12cd")
    # Only a link printed: the id comes from it.
    assert ct.parse_started("claude", "View: https://claude.ai/code/session_9Zz")["id"] == "session_9Zz"


def test_status_words():
    assert ct.status_word("Status: READY\nattempts: 1") == "done"
    assert ct.status_word("status: in progress") == "running"
    assert ct.status_word("Status: failed (setup error)") == "failed"
    assert ct.status_word("something else") == ""


def test_commands_match_the_tools():
    os.environ.pop("CODEX_CLOUD_BRANCH", None)
    assert ct.claude_start_cmd("fix it")[1:] == ["--cloud", "fix it"]
    assert ct.claude_reply_cmd("session_1", "and tests")[1:] == ["-p", "--cloud", "session_1", "and tests"]
    assert ct.codex_start_cmd("fix it", "env_1", "dev")[1:] == [
        "cloud", "exec", "--env", "env_1", "--branch", "dev", "fix it"]
    assert len(ct.claude_start_cmd("x" * 10000)[-1]) < 6100


def test_claude_task_starts_in_the_repo_and_is_listed(cloud):
    reply = asyncio.run(ct.handle("whatsapp", "claude add a /health endpoint"))
    cmd, cwd = cloud["calls"][0]
    assert cmd[1:] == ["--cloud", "add a /health endpoint"] and cwd == cloud["repo"]
    assert "#1 started" in reply and "https://claude.ai/code/session_01AbCdEf" in reply
    assert "can't ask you before it acts" in reply
    assert "add a /health endpoint" in ct.list_text()

    out = asyncio.run(ct.handle("whatsapp", "reply 1 also add a test"))
    assert cloud["calls"][-1][0][1:] == ["-p", "--cloud", "session_01AbCdEf", "also add a test"]
    assert "Sent to Claude cloud session #1" in out


def test_codex_task_status_and_diff(cloud):
    reply = asyncio.run(ct.handle("slack", "codex bump the version"))
    assert cloud["calls"][0][0][1:] == ["cloud", "exec", "--env", "env_123", "bump the version"]
    assert "#1 started" in reply and "tell you here when it finishes" in reply
    assert "Status: running" in asyncio.run(ct.handle("slack", "status 1"))
    cloud["answers"]["status"] = (0, "Status: ready")
    asyncio.run(ct.handle("slack", "status 1"))
    assert ct.find("1")["state"] == "done"
    assert asyncio.run(ct.handle("slack", "diff 1")) == "+ added line"
    assert "don't take follow-ups" in asyncio.run(ct.handle("slack", "reply 1 more"))


def test_not_ready_says_what_is_missing(cloud, monkeypatch):
    monkeypatch.delenv("CODEX_CLOUD_ENV")
    reply = asyncio.run(ct.handle("whatsapp", "codex do it"))
    assert "CODEX_CLOUD_ENV" in reply and not cloud["calls"]
    monkeypatch.setenv("CLOUD_CLAUDE_FOLDER", os.path.dirname(cloud["repo"]))   # not a repo
    assert "isn't a git repository" in asyncio.run(ct.handle("whatsapp", "claude do it"))
    assert "not ready" in ct.setup_text()


def test_only_claude_and_codex(cloud):
    assert "Claude and Codex only" in asyncio.run(ct.handle("whatsapp", "gemini do it"))
    assert not cloud["calls"]


def test_a_failed_start_shows_the_tool_output(cloud):
    cloud["answers"]["claude"] = (1, "No cloud session started: this machine isn't signed in to claude.ai.")
    reply = asyncio.run(ct.handle("whatsapp", "claude do it"))
    assert "didn't start" in reply and "isn't signed in" in reply
    assert ct.tasks() == []


def test_chat_router_sends_cloud_commands_here(cloud):
    import helm.chat_router as router
    replies = asyncio.run(router.handle("whatsapp", "/cloud codex fix the typo"))
    assert "Codex cloud task #1 started" in replies[0]
    assert "/cloud" in router.HELP


def test_watcher_reports_when_codex_finishes(cloud, monkeypatch):
    sent = []

    async def fake_send(channel, text):
        sent.append((channel, text))
    monkeypatch.setattr(ct, "_send", fake_send)
    monkeypatch.setattr(ct, "WATCH_EVERY", 0)
    cloud["answers"]["status"] = (0, "Status: ready")
    task = ct._add({"ai": "codex", "id": "task_e_1", "url": "", "prompt": "fix", "channel": "whatsapp",
                    "created": 0, "state": "running"})
    asyncio.run(ct._watch(task))
    assert sent and sent[0][0] == "whatsapp" and "finished" in sent[0][1]
    assert ct.find("task_e_1")["state"] == "done"
