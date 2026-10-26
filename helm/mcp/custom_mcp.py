"""
helm/mcp/custom_mcp.py — Servers the user adds themselves ("Add any MCP").

Instead of shipping one hard-coded connector per service, the user can add any
MCP server from the Packages panel, sign in to it, and every AI in RAPR gets
its tools: Ollama and the API AIs through RAPR's own tool calling, Claude
through --mcp-config, and Gemini / Codex through their native config files
(see MCPManager.sync_native_mcp_configs).

Two kinds of server:

  remote  A hosted MCP URL (streamable HTTP or SSE). Bridged to stdio with the
          `mcp-remote` npm proxy, which also handles sign-in:
            none     no auth
            oauth    sign in through the browser (mcp-remote does the OAuth
                     dance and caches tokens in ~/.mcp-auth, which every CLI
                     that later runs the same bridge shares)
            device   OAuth device code, for a RAPR on a server with no browser
            bearer   an API key sent as "Authorization: Bearer <key>"
            headers  any custom headers (e.g. X-API-Key)
  local   A command RAPR starts itself (npx / uvx / docker / a binary), with
          optional environment variables such as API tokens.

Where things live:
  - The server list is kept in the user data folder (custom_mcp_servers.json),
    not in the app folder, so it survives updates (an update replaces the app
    folder and its mcp_servers.json).
  - Every secret (URL, API key, header values, env values) goes in the
    encrypted token vault under RAPR_MCP_<ID>_*; the list only names the keys.
    Header values reach mcp-remote as ${VAR} placeholders it fills from its
    environment, so secrets never appear on a command line.

Public API:
    list_servers()                 -> list[dict]   public view (no secrets)
    runtime_configs()              -> dict         load_config()-format entries
    add_server(spec)               -> dict
    import_json(text)              -> dict         Claude Desktop / Cursor style JSON
    remove_server(id)              -> awaitable[dict]
    set_enabled(id, enabled)       -> None
    connect(id)                    -> awaitable[dict]  starts in the background
    status(id)                     -> dict
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shlex
from urllib.parse import urlparse

from helm.config import logger


_ID_RE = re.compile(r"[^a-z0-9_]+")
_HEADER_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

AUTH_MODES = ("none", "oauth", "device", "bearer", "headers")

# Ids the built-in servers already use; a custom server may not shadow them.
_RESERVED_IDS = {"chrome", "zapier", "composio"}

# How long a sign-in may take before we give up on the connect attempt.
_OAUTH_TIMEOUT = 300.0
_DEFAULT_TIMEOUT = 45.0     # npx may need to download mcp-remote the first time

# Background connect tasks, so a slow sign-in never blocks a request.
_connect_tasks: dict[str, asyncio.Task] = {}
_last_error: dict[str, str] = {}


# ── Storage ──────────────────────────────────────────────────────────────────

def _store_path() -> str:
    from helm.paths import user_data_dir
    return os.path.join(user_data_dir(), "custom_mcp_servers.json")


def _load() -> dict:
    path = _store_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.warning("custom_mcp: could not read %s: %s", path, exc)
        return {}


def _save(data: dict) -> None:
    path = _store_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def _secret_key(server_id: str, suffix: str) -> str:
    return f"RAPR_MCP_{server_id.upper()}_{suffix}"


def _put_secret(key: str, value: str) -> None:
    from helm.token_vault import store_token
    store_token(key, value)                 # also sets os.environ


def _get_secret(key: str) -> str:
    val = os.environ.get(key, "")
    if val:
        return val
    try:
        from helm.token_vault import load_token
        return load_token(key) or ""
    except Exception:
        return ""


def _drop_secrets(entry: dict) -> None:
    from helm.token_vault import delete_token
    for key in entry.get("secret_keys", []):
        try:
            delete_token(key)
        except Exception:
            logger.warning("Couldn't delete the secret %s from the vault", key, exc_info=True)
        os.environ.pop(key, None)


# ── Validation helpers ───────────────────────────────────────────────────────

def make_id(name: str) -> str:
    """Turn a display name into a server id (also the tool-name prefix)."""
    sid = _ID_RE.sub("_", (name or "").strip().lower()).strip("_")
    return sid[:32].strip("_")


def _unique_id(base: str, taken: set[str]) -> str:
    sid, n = base, 2
    while sid in taken or sid in _RESERVED_IDS:
        sid = f"{base[:28]}_{n}"
        n += 1
    return sid


def _taken_ids() -> set[str]:
    """Ids already used by built-in (mcp_servers.json) or custom servers."""
    taken = set(_load().keys()) | _RESERVED_IDS
    try:
        from helm.paths import PROJECT_ROOT
        with open(PROJECT_ROOT / "mcp_servers.json", "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            taken |= set(raw.keys())
    except (OSError, ValueError):
        pass
    return taken


def _check_url(url: str) -> str | None:
    if not url:
        return "Enter the server URL."
    try:
        parsed = urlparse(url)
    except Exception:
        return "That URL could not be read."
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in ("https", "http") or not host:
        return "The URL must start with https://"
    if parsed.scheme == "http" and host not in ("localhost", "127.0.0.1", "::1"):
        return "Use https:// (plain http:// is only allowed for localhost)."
    return None


def _clean_pairs(pairs, name_re: re.Pattern, what: str) -> tuple[list[tuple[str, str]], str | None]:
    """Normalise [{name, value}] / {name: value} into a list, validating names."""
    if isinstance(pairs, dict):
        pairs = [{"name": k, "value": v} for k, v in pairs.items()]
    out = []
    for p in pairs or []:
        if not isinstance(p, dict):
            continue
        name = str(p.get("name", "")).strip()
        value = str(p.get("value", ""))
        if not name and not value.strip():
            continue
        if not name_re.match(name):
            return [], f"'{name}' is not a valid {what} name."
        out.append((name, value))
    return out, None


# ── Add / import / remove ────────────────────────────────────────────────────

def add_server(spec: dict) -> dict:
    """Add a server from the Add-MCP form.

    spec (remote): {"name", "transport": "remote", "url", "auth",
                    "token"?, "headers"?: [{name, value}]}
    spec (local):  {"name", "transport": "local", "command",
                    "env"?: [{name, value}]}
    """
    name = str(spec.get("name", "")).strip()
    transport = spec.get("transport", "remote")
    if transport not in ("remote", "local"):
        return {"ok": False, "error": "Unknown server type."}

    if transport == "remote":
        fallback = urlparse(str(spec.get("url", ""))).hostname or ""
    else:
        fallback = (str(spec.get("command", "")).split() or [""])[-1]
    base = make_id(name) or make_id(fallback)
    if not base:
        return {"ok": False, "error": "Give the server a name."}
    sid = _unique_id(base, _taken_ids())
    label = name or sid.replace("_", " ")

    entry: dict = {"label": label, "transport": transport, "enabled": True,
                   "secret_keys": []}
    secrets: dict[str, str] = {}

    if transport == "remote":
        url = str(spec.get("url", "")).strip()
        err = _check_url(url)
        if err:
            return {"ok": False, "error": err}
        auth = spec.get("auth", "none")
        if auth not in AUTH_MODES:
            return {"ok": False, "error": "Unknown sign-in method."}
        entry["auth"] = auth
        entry["host"] = urlparse(url).hostname or ""
        secrets[_secret_key(sid, "URL")] = url

        headers: list[tuple[str, str]] = []
        if auth == "bearer":
            token = str(spec.get("token", "")).strip()
            if not token:
                return {"ok": False, "error": "Paste the API key or token."}
            if token.lower().startswith("bearer "):
                token = token[7:].strip()
            headers.append(("Authorization", f"Bearer {token}"))
        elif auth == "headers":
            headers, err = _clean_pairs(spec.get("headers"), _HEADER_NAME_RE, "header")
            if err:
                return {"ok": False, "error": err}
            if not headers:
                return {"ok": False, "error": "Add at least one header."}
        entry["headers"] = []
        for i, (hname, hval) in enumerate(headers):
            key = _secret_key(sid, f"H{i}")
            secrets[key] = hval
            entry["headers"].append({"name": hname, "key": key})
    else:
        command = str(spec.get("command", "")).strip()
        try:
            argv = shlex.split(command, posix=(os.name != "nt"))
            # Windows-style splitting keeps the quotes around "C:\Program Files\..."
            argv = [a[1:-1] if len(a) >= 2 and a[0] == a[-1] and a[0] in "\"'" else a
                    for a in argv]
        except ValueError as exc:
            return {"ok": False, "error": f"Could not read the command: {exc}"}
        if not argv:
            return {"ok": False, "error": "Enter the command that starts the server."}
        entry["command"] = argv
        env, err = _clean_pairs(spec.get("env"), _ENV_NAME_RE, "variable")
        if err:
            return {"ok": False, "error": err}
        entry["env"] = []
        for i, (ename, evalue) in enumerate(env):
            key = _secret_key(sid, f"E{i}")
            secrets[key] = evalue
            entry["env"].append({"name": ename, "key": key})

    for key, value in secrets.items():
        _put_secret(key, value)
    entry["secret_keys"] = list(secrets)

    data = _load()
    data[sid] = entry
    _save(data)
    logger.info("custom_mcp: added '%s' (%s%s)", sid, transport,
                f", auth={entry.get('auth')}" if transport == "remote" else "")
    return {"ok": True, "id": sid, "server": _public(sid, entry)}


def import_json(text: str) -> dict:
    """Add every server from a pasted MCP config snippet.

    Accepts the format most MCP docs hand out (Claude Desktop, Cursor, VS Code):
        {"mcpServers": {"name": {"command": "npx", "args": [...], "env": {...}}}}
        {"mcpServers": {"name": {"url": "https://...", "headers": {...}}}}
    A bare {"name": {...}} map, or a single server object, works too.
    """
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"That isn't valid JSON: {exc.msg} (line {exc.lineno})."}
    if not isinstance(raw, dict):
        return {"ok": False, "error": "Expected a JSON object."}

    servers = raw.get("mcpServers") or raw.get("servers") or raw
    if any(k in servers for k in ("command", "url", "serverUrl")):
        servers = {"server": servers}

    added, errors = [], []
    for name, cfg in servers.items():
        if not isinstance(cfg, dict):
            continue
        url = cfg.get("url") or cfg.get("serverUrl")
        args = [str(a) for a in cfg.get("args") or []]
        # A config that already wraps mcp-remote: unwrap it to the URL.
        if not url and args and any(a.startswith("mcp-remote") for a in args[:2]):
            rest = args[[i for i, a in enumerate(args) if a.startswith("mcp-remote")][0] + 1:]
            url = rest[0] if rest else ""
            hdrs = {}
            for i, a in enumerate(rest):
                if a == "--header" and i + 1 < len(rest) and ":" in rest[i + 1]:
                    hname, hval = rest[i + 1].split(":", 1)
                    hdrs[hname] = _fill_env(hval.strip(), cfg.get("env") or {})
            cfg = {"headers": hdrs}
        if url:
            headers = cfg.get("headers") or {}
            spec = {"name": name, "transport": "remote", "url": url,
                    "auth": "headers" if headers else "oauth",
                    "headers": headers}
        elif cfg.get("command"):
            cmd = [str(cfg["command"])] + args
            spec = {"name": name, "transport": "local",
                    "command": " ".join(_quote(a) for a in cmd),
                    "env": cfg.get("env") or {}}
        else:
            errors.append(f"{name}: no command or url")
            continue
        res = add_server(spec)
        if res.get("ok"):
            added.append(res["id"])
        else:
            errors.append(f"{name}: {res.get('error')}")

    if not added:
        return {"ok": False, "error": "; ".join(errors) or "No servers found in that JSON."}
    return {"ok": True, "ids": added, "errors": errors}


def _fill_env(value: str, env: dict) -> str:
    return re.sub(r"\$\{([^}]+)}", lambda m: str(env.get(m.group(1), m.group(0))), value)


def _quote(arg: str) -> str:
    if os.name == "nt":
        return f'"{arg}"' if (" " in arg or not arg) else arg
    return shlex.quote(arg)


async def remove_server(server_id: str) -> dict:
    data = _load()
    entry = data.pop(server_id, None)
    if entry is None:
        return {"ok": False, "error": f"No custom server '{server_id}'."}
    await _stop(server_id)
    _drop_secrets(entry)
    _save(data)
    _last_error.pop(server_id, None)
    _resync(removed=[server_id])
    logger.info("custom_mcp: removed '%s'", server_id)
    return {"ok": True}


def set_enabled(server_id: str, enabled: bool) -> bool:
    data = _load()
    if server_id not in data:
        return False
    data[server_id]["enabled"] = bool(enabled)
    _save(data)
    return True


def is_custom(server_id: str) -> bool:
    return server_id in _load()


# ── Runtime config ───────────────────────────────────────────────────────────

def _runtime(server_id: str, entry: dict) -> dict:
    """Build the load_config()-format entry for one custom server."""
    missing: list[str] = []
    env: dict[str, str] = {}

    if entry.get("transport") == "remote":
        url = _get_secret(_secret_key(server_id, "URL"))
        if not url:
            missing.append(_secret_key(server_id, "URL"))
        command = ["npx", "-y", "mcp-remote", url]
        if url.startswith("http://"):
            command.append("--allow-http")
        if entry.get("auth") == "device":
            command.append("--device-code")
        for i, h in enumerate(entry.get("headers", [])):
            value = _get_secret(h["key"])
            if not value:
                missing.append(h["key"])
            # mcp-remote fills ${VAR} in header values from its environment,
            # which keeps the secret off the command line.
            var = f"RAPR_MCP_HEADER_{i}"
            env[var] = value
            command += ["--header", f"{h['name']}:${{{var}}}"]
    else:
        command = list(entry.get("command", []))
        for e in entry.get("env", []):
            value = _get_secret(e["key"])
            if value:
                env[e["name"]] = value

    return {
        "type": "subprocess",
        "command": command,
        "env": env,
        "enabled": bool(entry.get("enabled", True)) and not missing,
        "needs_config": bool(missing),
        "missing_env": missing,
        "custom": True,
        # Startup and reloads use the short timeout so a server whose sign-in
        # expired can't hold everything up; connect() allows time to sign in.
        "init_timeout": _DEFAULT_TIMEOUT,
    }


def runtime_configs() -> dict:
    """All custom servers in load_config() format, keyed by id."""
    return {sid: _runtime(sid, entry) for sid, entry in _load().items()}


def _public(server_id: str, entry: dict) -> dict:
    return {
        "id": server_id,
        "label": entry.get("label", server_id),
        "transport": entry.get("transport", "remote"),
        "auth": entry.get("auth", ""),
        "host": entry.get("host", ""),
        "command": " ".join(entry.get("command", [])[:3]) if entry.get("transport") == "local" else "",
        "enabled": bool(entry.get("enabled", True)),
    }


def list_servers() -> list[dict]:
    return [{**_public(sid, e), **status(sid)} for sid, e in _load().items()]


# ── Connect / status ─────────────────────────────────────────────────────────

def _mgr():
    from helm.mcp.manager import get_manager
    return get_manager()


async def _stop(server_id: str) -> None:
    task = _connect_tasks.pop(server_id, None)
    mgr = _mgr()
    client = mgr.get_client(server_id)
    if client:
        client.cancel()                 # unblocks a start() waiting on sign-in
    if task and not task.done():
        task.cancel()
    await mgr.stop_server(server_id)


def _resync(removed: list[str] | None = None) -> None:
    try:
        _mgr().sync_native_mcp_configs(removed=removed)
    except Exception as exc:
        logger.warning("custom_mcp: native config sync failed: %s", exc)


async def connect(server_id: str) -> dict:
    """Start (or restart) a custom server in the background.

    Returns at once; poll status() to follow it. For OAuth servers the status
    carries the sign-in link mcp-remote asks the user to open.
    """
    data = _load()
    entry = data.get(server_id)
    if entry is None:
        return {"ok": False, "error": f"No custom server '{server_id}'."}
    if not entry.get("enabled", True):
        entry["enabled"] = True
        _save(data)

    cfg = _runtime(server_id, entry)
    if entry.get("auth") in ("oauth", "device"):
        cfg["init_timeout"] = _OAUTH_TIMEOUT
    if cfg["needs_config"]:
        return {"ok": False, "error": "Some saved details are missing. Remove the server and add it again."}

    await _stop(server_id)
    _last_error.pop(server_id, None)

    async def _run():
        mgr = _mgr()
        ok = await mgr.start_server(server_id, cfg)
        if ok:
            _resync()
            return
        client = mgr.get_client(server_id)
        tail = client.get_stderr_tail(40) if client else ""
        if entry.get("transport") == "remote" and not _which("npx"):
            _last_error[server_id] = ("Node.js is needed to connect remote MCP servers "
                                      "(RAPR uses npx mcp-remote). Install Node.js and try again.")
        elif client and client.auth_url:
            _last_error[server_id] = "The sign-in wasn't finished in time. Use Sign in again to retry."
        else:
            _last_error[server_id] = _explain(tail, entry)

    _connect_tasks[server_id] = asyncio.create_task(_run())
    return {"ok": True, "connecting": True, **status(server_id)}


_PID_PREFIX_RE = re.compile(r"^\[\d+\]\s*")
_ERROR_LINE_RE = re.compile(r"(fatal error|connection error|error)[:\s]", re.I)


def _explain(tail: str, entry: dict) -> str:
    """Turn a server's stderr into one readable reason it didn't connect."""
    lines = [_PID_PREFIX_RE.sub("", ln).strip() for ln in tail.splitlines()]
    lines = [ln for ln in lines if ln and not ln.startswith(("}", "{", "at "))]
    errors = [ln for ln in lines if _ERROR_LINE_RE.search(ln)]
    detail = (errors or lines or [""])[-1][:300]
    low = tail.lower()
    host = entry.get("host") or "the server"
    if re.search(r"\b(401|403)\b|unauthori[sz]ed|forbidden", low):
        if entry.get("auth") in ("bearer", "headers"):
            reason = f"{host} rejected the key. Check the API key or headers."
        elif entry.get("auth") == "none":
            reason = f"{host} needs a sign-in. Remove it and add it again with a sign-in method."
        else:
            reason = f"{host} refused the sign-in."
    elif "enotfound" in low or "getaddrinfo" in low:
        reason = f"Couldn't find {host}. Check the URL and your internet connection."
    elif "econnrefused" in low:
        reason = f"Nothing answered at {host}. Is the server running?"
    elif "timed out" in low or "no response for 'initialize'" in low:
        reason = "The server didn't answer in time (or the sign-in wasn't finished)."
    else:
        reason = "Could not connect."
    return reason + (f"\n{detail}" if detail and detail not in reason else "")


def _which(cmd: str) -> bool:
    import shutil
    return bool(shutil.which(cmd))


def status(server_id: str) -> dict:
    client = _mgr().get_client(server_id)
    task = _connect_tasks.get(server_id)
    running = bool(client and client.is_running())
    connecting = bool(task and not task.done())
    return {
        "running": running,
        "connecting": connecting and not running,
        "tool_count": client.get_tool_count() if running else 0,
        "summary": client.get_tool_summary_short() if running else "",
        "auth_url": client.auth_url if (client and connecting) else "",
        "auth_code": client.auth_code if (client and connecting) else "",
        "error": "" if (running or connecting) else _error_for(server_id, client),
    }


def _error_for(server_id: str, client) -> str:
    """Why a server isn't running: the last connect attempt's reason, or, for
    one that failed at startup, whatever it wrote to stderr."""
    if server_id in _last_error:
        return _last_error[server_id]
    tail = client.get_stderr_tail(40) if client else ""
    if not tail:
        return ""
    return _explain(tail, _load().get(server_id, {}))
