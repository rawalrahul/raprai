"""Bake-off: same task, several AIs, each in its own copy; merge the winner."""
import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.bakeoff as bo


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "proj"
    r.mkdir()
    git(r, "init", "-q")
    git(r, "config", "user.email", "t@example.com")
    git(r, "config", "user.name", "t")
    (r / "app.py").write_text("def add(a, b):\n    return a - b\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "init")
    return r


def fake_runner(plan):
    """plan: ai -> (file, content). Each fake AI writes one file in its own copy."""
    async def run(ai, prompt, cwd):
        fname, content = plan[ai]
        Path(cwd, fname).write_text(content)
        return f"{ai} done: {prompt[:20]}"
    return run


def test_creates_one_copy_per_ai(repo, tmp_path):
    b = bo.create(str(repo), "fix add", ["claude", "codex"], root=str(tmp_path / "work"))
    assert b.is_git and len(b.attempts) == 2
    for a in b.attempts:
        assert Path(a.path, "app.py").exists()
    bo.discard(b)
    assert not Path(b.attempts[0].path).exists()
    assert "bakeoff/" not in subprocess.run(["git", "branch"], cwd=repo, capture_output=True, text=True).stdout


def test_each_attempt_is_compared(repo, tmp_path):
    b = bo.create(str(repo), "fix add", ["claude", "codex"], test_command="python -c 'import app; assert app.add(1,2)==3'",
                  root=str(tmp_path / "work"))
    fixed = "def add(a, b):\n    return a + b\n"
    plan = {"claude": ("app.py", fixed), "codex": ("notes.txt", "I looked at it")}
    asyncio.run(bo.run(b, fake_runner(plan)))
    by_ai = {a.ai: a for a in b.attempts}
    assert by_ai["claude"].files_changed == 1 and "return a + b" in by_ai["claude"].diff
    assert by_ai["codex"].files_changed == 1 and "notes.txt" in by_ai["codex"].diff
    assert by_ai["claude"].tests_passed is True
    assert by_ai["codex"].tests_passed is False
    assert b.status == "done"
    bo.discard(b)


def test_merge_applies_only_the_chosen_attempt(repo, tmp_path):
    b = bo.create(str(repo), "fix add", ["claude", "codex"], root=str(tmp_path / "work"))
    fixed = "def add(a, b):\n    return a + b\n"
    asyncio.run(bo.run(b, fake_runner({"claude": ("app.py", fixed), "codex": ("extra.txt", "x")})))
    idx = [a.ai for a in b.attempts].index("claude")
    bo.merge(b, idx)
    assert (repo / "app.py").read_text() == fixed
    assert not (repo / "extra.txt").exists()
    assert b.status == "merged"
    assert not Path(b.attempts[0].path).exists()


def test_plain_folder_without_git(tmp_path):
    proj = tmp_path / "plain"
    proj.mkdir()
    (proj / "a.txt").write_text("one")
    b = bo.create(str(proj), "change a", ["gemini", "ollama"], root=str(tmp_path / "work"))
    assert not b.is_git
    asyncio.run(bo.run(b, fake_runner({"gemini": ("a.txt", "two"), "ollama": ("b.txt", "new")})))
    g = next(a for a in b.attempts if a.ai == "gemini")
    assert g.files_changed == 1
    bo.merge(b, [a.ai for a in b.attempts].index("gemini"))
    assert (proj / "a.txt").read_text() == "two"
    assert not (proj / "b.txt").exists()


def test_an_ai_that_fails_is_reported(repo, tmp_path):
    b = bo.create(str(repo), "x", ["claude", "codex"], root=str(tmp_path / "work"))

    async def runner(ai, prompt, cwd):
        if ai == "codex":
            raise RuntimeError("quota exceeded")
        Path(cwd, "app.py").write_text("ok\n")
        return "ok"
    asyncio.run(bo.run(b, runner))
    codex = next(a for a in b.attempts if a.ai == "codex")
    assert "quota exceeded" in codex.error
    bo.discard(b)


def test_validation(repo, tmp_path):
    with pytest.raises(ValueError):
        bo.create(str(repo), "x", ["claude"], root=str(tmp_path))
    with pytest.raises(ValueError):
        bo.create(str(tmp_path / "missing"), "x", ["claude", "codex"], root=str(tmp_path))


def test_api_round_trip(repo, tmp_path, monkeypatch):
    import time
    from fastapi.testclient import TestClient
    from helm.web_routes import app as webapp
    import helm.web_routes.bakeoff_routes as routes

    async def runner(ai, prompt, cwd):
        Path(cwd, "app.py").write_text(f"# {ai}\n")
        return "ok"
    monkeypatch.setattr(routes, "_runner", lambda: runner)
    real_create = bo.create
    monkeypatch.setattr(bo, "create", lambda repo, task, ais, test_command=None: real_create(repo, task, ais, test_command=test_command, root=str(tmp_path / "w")))
    client = TestClient(webapp)
    r = client.post("/api/bakeoff", json={"repo": str(repo), "task": "fix", "ais": ["claude", "codex"]})
    assert r.status_code == 200, r.text
    bid = r.json()["id"]
    for _ in range(50):
        d = client.get(f"/api/bakeoff/{bid}").json()
        if d["status"] == "done":
            break
        time.sleep(0.1)
    assert d["status"] == "done" and len(d["attempts"]) == 2
    assert client.post(f"/api/bakeoff/{bid}/merge", json={"attempt": 0}).json()["ok"]
    assert (repo / "app.py").read_text() == "# claude\n"
    assert client.post("/api/bakeoff", json={"repo": str(repo), "task": "x", "ais": ["one"]}).status_code == 400
