"""Custom MCP servers: the user adds any MCP server (URL or command), signs in,
and every AI in RAPR gets its tools."""

import asyncio
import json
import sys
import textwrap

import pytest

from helm.mcp import custom_mcp
from helm.mcp.manager import MCPManager


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Isolated data folder, an in-memory vault and a fresh manager."""
    monkeypatch.setenv("RAPR_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    vault: dict[str, str] = {}

    import helm.token_vault as tv

    def store(k, v):
        vault[k] = v
        monkeypatch.setenv(k, v)

    def delete(k):
        vault.pop(k, None)

    monkeypatch.setattr(tv, "store_token", store)
    monkeypatch.setattr(tv, "load_token", lambda k: vault.get(k, ""))
    monkeypatch.setattr(tv, "delete_token", delete)

    mgr = MCPManager()
    import helm.mcp.manager as mm
    monkeypatch.setattr(mm, "get_manager", lambda: mgr)
    custom_mcp._connect_tasks.clear()
    custom_mcp._last_error.clear()
    return {"vault": vault, "mgr": mgr, "tmp": tmp_path}


def test_remote_api_key_stays_out_of_files_and_args(env):
    res = custom_mcp.add_server({"name": "Buffer", "transport": "remote",
                                 "url": "https://mcp.buffer.example/mcp",
                                 "auth": "bearer", "token": "Bearer sk-123"})
    assert res["ok"] and res["id"] == "buffer"

    cfg = custom_mcp.runtime_configs()["buffer"]
    assert cfg["command"][:4] == ["npx", "-y", "mcp-remote", "https://mcp.buffer.example/mcp"]
    i = cfg["command"].index("--header")
    assert cfg["command"][i + 1] == "Authorization:${RAPR_MCP_HEADER_0}"
    assert cfg["env"] == {"RAPR_MCP_HEADER_0": "Bearer sk-123"}   # "Bearer " not doubled
    assert cfg["enabled"] and not cfg["needs_config"]

    stored = (env["tmp"] / "data" / "custom_mcp_servers.json").read_text()
    assert "sk-123" not in stored and "https://" not in stored


def test_oauth_and_device_flags(env):
    custom_mcp.add_server({"name": "Linear", "transport": "remote",
                           "url": "https://mcp.linear.app/mcp", "auth": "oauth"})
    custom_mcp.add_server({"name": "Srv", "transport": "remote",
                           "url": "https://x.example/mcp", "auth": "device"})
    custom_mcp.add_server({"name": "Dev", "transport": "remote",
                           "url": "http://localhost:9000/mcp", "auth": "none"})
    cfgs = custom_mcp.runtime_configs()
    assert "--header" not in cfgs["linear"]["command"]
    assert "--device-code" in cfgs["srv"]["command"]
    assert "--allow-http" in cfgs["dev"]["command"]


@pytest.mark.parametrize("url", ["", "ftp://x/mcp", "http://evil.example/mcp", "not a url"])
def test_bad_urls_rejected(env, url):
    assert not custom_mcp.add_server({"name": "x", "transport": "remote", "url": url})["ok"]


def test_ids_never_shadow_builtins_or_each_other(env):
    a = custom_mcp.add_server({"name": "Zapier", "transport": "remote", "url": "https://a.example/mcp"})
    b = custom_mcp.add_server({"name": "Zapier", "transport": "remote", "url": "https://b.example/mcp"})
    assert a["id"] != "zapier" and b["id"] != a["id"]


def test_local_command_with_env(env):
    res = custom_mcp.add_server({"name": "GitHub", "transport": "local",
                                 "command": "npx -y @modelcontextprotocol/server-github",
                                 "env": [{"name": "GITHUB_PERSONAL_ACCESS_TOKEN", "value": "ghp_x"}]})
    cfg = custom_mcp.runtime_configs()[res["id"]]
    assert cfg["command"] == ["npx", "-y", "@modelcontextprotocol/server-github"]
    assert cfg["env"] == {"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_x"}
    assert not custom_mcp.add_server({"name": "y", "transport": "local", "command": "x",
                                      "env": [{"name": "BAD NAME", "value": "1"}]})["ok"]


def test_import_claude_desktop_json(env):
    snippet = {"mcpServers": {
        "notion": {"url": "https://mcp.notion.com/mcp"},
        "keyed": {"url": "https://k.example/mcp", "headers": {"X-API-Key": "abc"}},
        "fs": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/my docs"]},
        "wrapped": {"command": "npx", "args": ["mcp-remote", "https://w.example/sse",
                                               "--header", "Authorization:${AUTH}"],
                    "env": {"AUTH": "Bearer t0k"}},
    }}
    res = custom_mcp.import_json(json.dumps(snippet))
    assert res["ok"] and set(res["ids"]) == {"notion", "keyed", "fs", "wrapped"}
    cfgs = custom_mcp.runtime_configs()
    servers = {s["id"]: s for s in custom_mcp.list_servers()}
    assert servers["notion"]["auth"] == "oauth"
    assert cfgs["keyed"]["env"] == {"RAPR_MCP_HEADER_0": "abc"}
    assert cfgs["fs"]["command"][-1] == "/my docs"              # spaces survive
    assert cfgs["wrapped"]["command"][3] == "https://w.example/sse"
    assert cfgs["wrapped"]["env"] == {"RAPR_MCP_HEADER_0": "Bearer t0k"}

    assert not custom_mcp.import_json("{nope")["ok"]


def test_load_config_includes_custom_servers(env):
    from helm.mcp.config import load_config
    res = custom_mcp.add_server({"name": "Mine", "transport": "local", "command": "uvx my-mcp"})
    cfg = load_config()
    assert cfg[res["id"]]["custom"] and cfg[res["id"]]["command"] == ["uvx", "my-mcp"]


# ── End to end with a real stdio server ──────────────────────────────────────

_FAKE_SERVER = textwrap.dedent('''
    import json, sys
    for line in sys.stdin:
        msg = json.loads(line)
        if "id" not in msg:
            continue
        m = msg["method"]
        if m == "initialize":
            res = {"serverInfo": {"name": "fake", "version": "1"}, "capabilities": {}}
        elif m == "tools/list":
            res = {"tools": [{"name": "post_update", "description": "Queue a social post",
                              "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}},
                                              "required": ["text"]}}]}
        elif m == "tools/call":
            res = {"content": [{"type": "text", "text": "queued: " + msg["params"]["arguments"]["text"]}]}
        else:
            res = {}
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": res}) + "\\n")
        sys.stdout.flush()
''')

_SIGNIN_SERVER = textwrap.dedent('''
    import sys, time
    sys.stderr.write("Please authorize this client by visiting:\\nhttps://auth.example/authorize?x=1\\n")
    sys.stderr.flush()
    time.sleep(60)
''')


async def _wait(pred, timeout=10):
    for _ in range(int(timeout / 0.1)):
        if pred():
            return True
        await asyncio.sleep(0.1)
    return False


def test_connect_call_and_remove(env, tmp_path):
    script = tmp_path / "fake_mcp.py"
    script.write_text(_FAKE_SERVER)
    (tmp_path / ".codex").mkdir()
    codex = tmp_path / ".codex" / "config.toml"
    codex.write_text('model = "x"\n\n[mcp_servers.mine]\ncommand = "keep-me"\n')

    async def run():
        res = custom_mcp.add_server({"name": "Social", "transport": "local",
                                     "command": f'"{sys.executable}" "{script}"'})
        sid = res["id"]
        assert (await custom_mcp.connect(sid))["ok"]
        assert await _wait(lambda: custom_mcp.status(sid)["running"])
        await asyncio.sleep(0.1)                      # let the resync run
        mgr = env["mgr"]
        assert mgr.is_mcp_tool("social_post_update")
        assert await mgr.call_tool("social_post_update", {"text": "hi"}) == "queued: hi"
        assert "social_post_update" in mgr.get_text_tool_descriptions()
        assert "[mcp_servers.social]" in codex.read_text()

        assert (await custom_mcp.remove_server(sid))["ok"]
        assert not mgr.is_mcp_tool("social_post_update")
        assert custom_mcp.list_servers() == []
        assert "[mcp_servers.social]" not in codex.read_text()
        assert not any(k.startswith("RAPR_MCP_SOCIAL") for k in env["vault"])

    asyncio.run(run())


def test_signin_link_is_surfaced_and_remove_cancels(env, tmp_path):
    script = tmp_path / "signin.py"
    script.write_text(_SIGNIN_SERVER)

    async def run():
        res = custom_mcp.add_server({"name": "NeedsLogin", "transport": "local",
                                     "command": f'"{sys.executable}" "{script}"'})
        sid = res["id"]
        await custom_mcp.connect(sid)
        assert await _wait(lambda: custom_mcp.status(sid)["auth_url"])
        st = custom_mcp.status(sid)
        assert st["connecting"] and st["auth_url"] == "https://auth.example/authorize?x=1"
        # Removing mid sign-in must not wait for the handshake timeout.
        await asyncio.wait_for(custom_mcp.remove_server(sid), timeout=5)

    asyncio.run(run())


def test_failed_server_reports_its_error(env, tmp_path):
    script = tmp_path / "boom.py"
    script.write_text("import sys; sys.stderr.write('invalid api key\\n'); sys.exit(1)")

    async def run():
        sid = custom_mcp.add_server({"name": "Broken", "transport": "local",
                                     "command": f'"{sys.executable}" "{script}"'})["id"]
        await custom_mcp.connect(sid)
        assert await _wait(lambda: custom_mcp.status(sid)["error"])
        assert "invalid api key" in custom_mcp.status(sid)["error"]

    asyncio.run(run())


def test_errors_are_explained():
    tail = ("[2718] Connecting to remote server: https://x/mcp\n"
            "[2718] Fatal error: RegistrationRejectedError: Dynamic Client Registration "
            "rejected (HTTP 401): {\"error\":\"unauthorized\"}\n}")
    msg = custom_mcp._explain(tail, {"auth": "bearer", "host": "mcp.buffer.com"})
    assert msg.startswith("mcp.buffer.com rejected the key")
    assert "RegistrationRejectedError" in msg
    assert "Couldn't find" in custom_mcp._explain("Error: getaddrinfo ENOTFOUND x", {"host": "x"})
