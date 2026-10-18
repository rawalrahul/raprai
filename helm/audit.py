"""
helm/audit.py — A record of what RAPR asked, what you decided, and why.

One JSON line per event in user data/audit.jsonl:
  approval_requested, approval_resolved (approved | denied | timeout),
  rule_applied (a rule decided without asking).
Nothing leaves your machine; the file is yours to read, export or delete.

Tamper evidence: each line carries `prev` (the previous line's `h`) and
`h = HMAC-SHA256(key, prev + line)`, with the key in user data/.audit_key.
verify() walks the chain, so editing, inserting, reordering or removing a line
in the middle shows up. Lines written before the chain existed are counted as
`legacy`, not checked.

Anchor: once a day, when the log has grown, anchor_loop() saves the entry count
and latest `h` in user data/audit_anchor.json, and sends them to every linked
chat app (Telegram, WhatsApp, Discord, Slack). None need be linked. verify()
checks the file still reaches that point, which catches lines cut from the end
and a log re-signed with a stolen key. The local copy only helps if it wasn't
edited too; a chat message is a copy that can't be changed from this computer.
"""

from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import os
import secrets
import threading
import time
from typing import Optional

from helm.config import logger

_lock = threading.Lock()
_head: dict = {}   # path -> (file size, last h) so record() needn't re-read the file


def _path():
    from helm.paths import user_data_dir
    return user_data_dir() / "audit.jsonl"


def _key() -> bytes:
    kp = _path().with_name(".audit_key")
    try:
        return bytes.fromhex(kp.read_text().strip())
    except FileNotFoundError:
        pass
    key = secrets.token_bytes(32)
    kp.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(kp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(key.hex())
    return key


def _canonical(entry: dict) -> str:
    return json.dumps({k: v for k, v in entry.items() if k != "h"},
                      ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sign(key: bytes, entry: dict) -> str:
    return hmac.new(key, _canonical(entry).encode("utf-8"), hashlib.sha256).hexdigest()


def _last_hash(path) -> str:
    """`h` of the file's last line ("" for a new file or a legacy last line)."""
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        return ""
    cached = _head.get(str(path))
    if cached and cached[0] == size:
        return cached[1]
    with open(path, "rb") as f:
        f.seek(max(0, size - 65536))
        tail = f.read().decode("utf-8", errors="replace").splitlines()
    for raw in reversed(tail):
        if raw.strip():
            try:
                return json.loads(raw).get("h", "")
            except (json.JSONDecodeError, AttributeError):
                return ""
    return ""


def record(event: str, **fields) -> None:
    line = {"ts": round(time.time(), 3), "event": event, **{k: v for k, v in fields.items() if v is not None}}
    try:
        line = json.loads(json.dumps(line, ensure_ascii=False, default=str))  # hash what read() will see
        path = _path()
        with _lock:
            line["prev"] = _last_hash(path)
            line["h"] = _sign(_key(), line)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")
            _head[str(path)] = (path.stat().st_size, line["h"])
    except Exception as exc:
        logger.debug("audit write failed: %s", exc)


def verify() -> dict:
    """Check the chain. Returns {ok, entries, legacy, head, problem, anchor};
    problem is {line, reason} for the first break (1-based line number), else
    None; anchor is the last daily check this was compared with, if any."""
    result = {"ok": True, "entries": 0, "legacy": 0, "head": "", "problem": None, "anchor": None}

    def broken(n: int, reason: str) -> dict:
        result.update(ok=False, problem={"line": n, "reason": reason})
        return result

    try:
        lines = _path().read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        lines = []
    with _lock:
        key = _key()
    anchor = last_anchor()
    if anchor and anchor["entries"]:
        result["anchor"] = {"entries": anchor["entries"], "day": _day(anchor.get("ts", 0)),
                            "sent_to": anchor.get("sent_to") or []}
    else:
        anchor = None
    prev = None   # None until the first chained line
    for n, raw in enumerate(lines, 1):
        if not raw.strip():
            continue
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            return broken(n, "not a valid entry")
        if not isinstance(entry, dict):
            return broken(n, "not a valid entry")
        if "h" not in entry:
            if prev is not None:
                return broken(n, "unsigned entry after signing began")
            result["legacy"] += 1
            continue
        if entry.get("prev", "") != (prev or ""):
            return broken(n, "entry before this one is missing or changed")
        if not hmac.compare_digest(str(entry["h"]), _sign(key, entry)):
            return broken(n, "entry was edited")
        prev = entry["h"]
        result["entries"] += 1
        if anchor and result["entries"] == anchor["entries"] and prev != anchor["head"]:
            return broken(n, f"log was rewritten after the check on {_day(anchor['ts'])}")
    result["head"] = prev or ""
    if anchor and result["entries"] < anchor["entries"]:
        missing = anchor["entries"] - result["entries"]
        return broken(len(lines) + 1, f"{missing} entries removed from the end since the check on {_day(anchor['ts'])}")
    return result


# ---------------------------------------------------------------------------
# Daily anchor
# ---------------------------------------------------------------------------

_ANCHOR_EVERY = 86400


def _anchor_path():
    return _path().with_name("audit_anchor.json")


def _day(ts: float) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(ts))


def last_anchor() -> Optional[dict]:
    try:
        a = json.loads(_anchor_path().read_text(encoding="utf-8"))
        return a if isinstance(a.get("entries"), int) and isinstance(a.get("head"), str) else None
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        return None


def anchor_message(v: dict) -> str:
    if not v["ok"]:
        p = v["problem"]
        return (f"⚠️ RAPR audit log check failed: {p['reason']} (line {p['line']}). "
                "Something changed it outside RAPR. Open Settings → Approvals & audit → Verify.")
    return (f"🔏 RAPR audit log: {v['entries']} signed entries, intact.\n"
            f"Latest: {v['head']}\n"
            "Keep this message: Verify in Settings should never show fewer entries or a different hash here.")


def _sending_on() -> bool:
    return os.environ.get("AUDIT_ANCHOR", "1").strip().lower() not in ("0", "false", "no", "off")


async def send_to_chat_apps(text: str) -> list[str]:
    """Send to every linked chat app. Returns the ones that were linked."""
    import helm.state as _st
    sent = []
    if _st.telegram_app and _st.telegram_chat_id:
        try:
            await _st.telegram_app.bot.send_message(chat_id=_st.telegram_chat_id, text=text)
            sent.append("Telegram")
        except Exception as exc:
            logger.warning("audit anchor to Telegram failed: %s", exc)
    try:
        import helm.whatsapp_bridge as wa
        if wa.state.get("status") == "connected":
            await wa.send_text(text)
            sent.append("WhatsApp")
    except Exception as exc:
        logger.debug("audit anchor to WhatsApp skipped: %s", exc)
    try:
        import helm.groupchat as gc
        for name in ("discord", "slack"):   # they can only post to a chat you've used since start
            send = gc._channel_senders.get(name)
            if send and getattr(getattr(send, "__self__", None), "last_chat", None):
                await send({}, text)
                sent.append(name.capitalize())
    except Exception as exc:
        logger.debug("audit anchor to Discord/Slack skipped: %s", exc)
    return sent


async def anchor_now(send=None) -> Optional[str]:
    """Verify; if the log grew since the last anchor (or is broken), save the new
    anchor and, when `send` is given, send the result with it (`send(text)`
    returns the apps it reached). Returns the text, or None if nothing changed."""
    import asyncio
    v = await asyncio.to_thread(verify)
    last = last_anchor()
    if v["ok"] and (not v["entries"] or (last and last["entries"] == v["entries"])):
        return None
    text = anchor_message(v)
    sent_to = (await send(text) or []) if send else []
    # A broken log keeps the last good anchor, so the warning repeats daily, not hourly.
    keep = {"entries": v["entries"], "head": v["head"]} if v["ok"] else \
        {k: (last or {"entries": 0, "head": ""}).get(k) for k in ("entries", "head")}
    _anchor_path().write_text(json.dumps({**keep, "ts": time.time(), "sent_to": list(sent_to)}),
                              encoding="utf-8")
    return text


async def anchor_loop() -> None:
    """Background task: anchor once a day. Works with no chat app linked; then
    the anchor is only kept on this computer. AUDIT_ANCHOR=0 stops the sending."""
    import asyncio
    await asyncio.sleep(120)
    while True:
        try:
            last = last_anchor()
            if not last or time.time() - float(last.get("ts", 0)) >= _ANCHOR_EVERY:
                await anchor_now(send_to_chat_apps if _sending_on() else None)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("audit anchor failed: %s", exc)
        await asyncio.sleep(3600)


def read(since: float = 0.0, event: Optional[str] = None, query: str = "", limit: int = 500) -> list[dict]:
    try:
        lines = _path().read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    q = query.lower()
    out = []
    for raw in reversed(lines):
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if entry.get("ts", 0) < since:
            break
        if event and entry.get("event") != event:
            continue
        if q and q not in json.dumps({k: v for k, v in entry.items() if k not in ("h", "prev")},
                                     ensure_ascii=False).lower():
            continue
        out.append(entry)
        if len(out) >= limit:
            break
    return out


def to_csv(entries: list[dict]) -> str:
    cols = ["ts", "event", "id", "action", "description", "status", "source", "rule", "session_id"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for e in entries:
        w.writerow({c: e.get(c, "") for c in cols})
    return buf.getvalue()
