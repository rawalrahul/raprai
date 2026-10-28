"""The MCP server installed on its own (pyproject.toml): it must work with python-dotenv as
its only package, so `uvx --from git+… rapr-mcp` stays a small, quick install.

The server runs as a real process with every other installed package made unimportable,
and drives a (fake) Claude Code through a whole relay and an ask_agent."""
import json
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Run the standalone entry point with only the standard library and python-dotenv importable.
LAUNCH = textwrap.dedent("""\
    import importlib.abc, importlib.metadata, sys
    allowed = {{"dotenv", "helm", "integrations"}}
    blocked = {{name for name in importlib.metadata.packages_distributions() if name not in allowed}}

    class Block(importlib.abc.MetaPathFinder):
        def find_spec(self, name, path=None, target=None):
            if name.split(".")[0] in blocked:
                raise ModuleNotFoundError(f"No module named {{name!r}} (not installed with rapr-mcp)")
            return None

    sys.meta_path.insert(0, Block())
    sys.path.insert(0, {root!r})
    from helm.mcp_server import standalone
    standalone()
""")

FAKE_CLAUDE = textwrap.dedent("""\
    #!{py}
    import json, sys
    prompt = sys.argv[sys.argv.index("-p") + 1]
    if "You are the planner" in prompt:
        out = "Make add() return a + b."
    elif "You are the reviewer" in prompt:
        out = "Fine.\\nVERDICT: APPROVED"
    elif "--permission-mode" in sys.argv:          # allowed to edit
        open("app.py", "w").write("def add(a, b):\\n    return a + b\\n")
        out = "Fixed it."
    else:
        out = "Read only."
    print(json.dumps({{"result": out}}))
""")


@pytest.mark.skipif(sys.platform == "win32", reason="uses a shebang script as a fake CLI")
def test_tools_work_with_only_python_dotenv(tmp_path):
    repo = tmp_path / "proj"
    repo.mkdir()
    for args in (["init", "-q"], ["config", "user.email", "t@example.com"], ["config", "user.name", "t"]):
        subprocess.run(["git", *args], cwd=repo, check=True)
    (repo / "app.py").write_text("def add(a, b):\n    return a - b\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "claude").write_text(FAKE_CLAUDE.format(py=sys.executable))
    (bindir / "claude").chmod(0o755)

    env = {k: v for k, v in os.environ.items() if k != "RAPR_DATA_DIR"}
    env.update(PATH=f"{bindir}{os.pathsep}{env['PATH']}", HOME=str(tmp_path / "home"),
               XDG_DATA_HOME=str(tmp_path / "xdg"))
    proc = subprocess.Popen([sys.executable, "-c", LAUNCH.format(root=str(ROOT))], cwd=repo, env=env,
                            text=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ids = iter(range(1, 1000))

    def call(name, **args):
        mid = next(ids)
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": mid, "method": "tools/call",
                                     "params": {"name": name, "arguments": args}}) + "\n")
        proc.stdin.flush()
        line = proc.stdout.readline()
        assert line, proc.stderr.read()
        msg = json.loads(line)
        assert msg["id"] == mid
        result = msg["result"]
        assert not result.get("isError"), result
        return result["content"][0]["text"]

    try:
        assert "claude (Claude Code)" in call("list_agents")
        reply = call("ask_agent", agent="claude", prompt="hi")
        assert "Fixed it." in reply and "temporary copy" in reply      # it could edit, in a copy
        assert (repo / "app.py").read_text().endswith("a - b\n")
        assert "Briefs are made by the RAPR app" in call("latest_brief")
        started = call("start_relay", task="add() subtracts", planner="claude", executor="claude")
        rid = started.split("relay ", 1)[1].split()[0]
        deadline = time.time() + 60
        report = ""
        while time.time() < deadline:
            report = call("relay_status", id=rid, wait_seconds=2)
            if "Still running" not in report:
                break
        assert f"Relay {rid}: done" in report and "approved" in report, report
        assert "Make add() return a + b." in report
        assert "applied" in call("merge_relay", id=rid).lower()
        assert (repo / "app.py").read_text().endswith("a + b\n")
    finally:
        proc.stdin.close()
        proc.wait(timeout=10)
    # The standalone server keeps its data where the RAPR app would (helm/mcp_server.py: default_data_dir).
    if sys.platform.startswith("linux"):
        assert (tmp_path / "xdg" / "RAPR AI").is_dir()
