"""
helm/whatsapp_bridge.py — Control RAPR AI from WhatsApp (free, no Business API).

Uses neonize (https://github.com/krypton-byte/neonize), a Python wrapper around
whatsmeow: RAPR joins your WhatsApp as a *linked device*, the same way WhatsApp
Web does. Link it once by scanning a QR code in the web UI (Settings →
WhatsApp). No Meta developer account, no per-message fees.

Who RAPR listens to:
  • your own "Message yourself" chat, always;
  • any number in WHATSAPP_ALLOWED_NUMBERS (comma-separated, digits only),
    useful when RAPR is linked to a spare number and you write to it.
Everything else (your friends, groups, status updates) is ignored, and RAPR's
own replies are never taken as commands.

What you can do from WhatsApp:
  plain text            → the focused session, or the group chat you're in
  /sessions             → numbered list of sessions
  /use 2                → focus session 2
  /new claude           → start a session (any AI key: gemini, codex, ollama…)
  /group …              → group chats (same commands as Telegram, see
                          helm/groupchat_channels.py)
  /status, /help
"""

from __future__ import annotations

import asyncio
import base64
import io
import os
import re
import time
from collections import deque
from typing import Optional

import helm.state as _st
from helm.config import logger

CHANNEL = "whatsapp"
MAX_CHUNK = 3500

HELP = (
    "🐧 RAPR AI on WhatsApp\n"
    "Just type to talk to your focused session.\n"
    "/sessions — list sessions\n"
    "/use <number> — switch session\n"
    "/new <ai> — start a session (claude, gemini, codex, ollama…)\n"
    "/group — group chats with several AIs (/group help)\n"
    "/status — what's running\n"
    "/kelvin — is RAPR on? Kelvin's report, same as on Telegram\n"
    "/approvals — actions waiting for your OK; /approve <id> or /deny <id>\n"
    "/help — this message"
)

# Runtime state, shown in the web UI.
state: dict = {
    "status": "off",        # off | starting | qr | connected | error
    "qr": None,             # data:image/png;base64,… while waiting for a scan
    "me": None,             # linked phone number
    "error": None,
    "available": None,      # False when neonize can't be imported on this machine
}

_client = None
_me_users: set[str] = set()          # our own JID/LID users: the "Message yourself" chat
_sent_ids: deque = deque(maxlen=200)  # ids of messages RAPR sent, never treated as input
_sent_texts: deque = deque(maxlen=50)  # (time, text) of recent sends: echo guard for the self-chat
_reply_to = None                      # JID of the chat we last heard from


# ---------------------------------------------------------------------------
# Paths & settings
# ---------------------------------------------------------------------------

def _dir():
    from helm.paths import user_data_dir
    d = user_data_dir() / "whatsapp"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _db_path() -> str:
    return str(_dir() / "whatsapp_session.db")


def is_linked() -> bool:
    """True when a WhatsApp session has been saved (QR scanned before)."""
    try:
        return os.path.exists(_db_path()) and (_dir() / "linked").exists()
    except Exception:
        return False


def allowed_numbers() -> set[str]:
    raw = os.environ.get("WHATSAPP_ALLOWED_NUMBERS", "")
    return {re.sub(r"\D", "", n) for n in raw.split(",") if re.sub(r"\D", "", n)}


def public_state() -> dict:
    return {**state, "linked": is_linked(), "allowed_numbers": sorted(allowed_numbers())}


async def _push_state() -> None:
    try:
        from helm.broadcast import broadcast
        await broadcast({"type": "whatsapp_status", **public_state()})
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Pure logic (tested without WhatsApp)
# ---------------------------------------------------------------------------

def is_authorized(chat_user: str, sender_users: list[str], from_me: bool,
                  is_group: bool, me_users: set[str], allowed: set[str]) -> bool:
    """Should RAPR act on this message?"""
    if is_group:
        return False
    if from_me:
        # Only your own "Message yourself" chat, never what you write to friends.
        return chat_user in me_users
    return any(u and re.sub(r"\D", "", u) in allowed for u in sender_users)


def is_echo(text: str, now: Optional[float] = None) -> bool:
    """True when text is something RAPR itself sent in the last 10 minutes."""
    now = now or time.time()
    t = (text or "").strip()
    return any(t == sent and now - at < 600 for at, sent in _sent_texts)


def chunks(text: str, size: int = MAX_CHUNK) -> list[str]:
    text = text or ""
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]


def sessions_text() -> str:
    items = sorted(_st.sessions.values(), key=lambda s: s.get("created", 0))
    if not items:
        return "No sessions yet. Start one with /new claude (or gemini, codex, ollama…)."
    lines = ["Sessions:"]
    for i, s in enumerate(items, 1):
        mark = "  ← focused" if s["id"] == _st.focused_id else ""
        busy = " (working…)" if s.get("busy") else ""
        lines.append(f"{i}. {s.get('emoji', '🤖')} {s['name']}{busy}{mark}")
    lines.append("\nSwitch with /use <number>")
    return "\n".join(lines)


def status_text() -> str:
    from helm.kelvin_report import kelvin_report
    try:
        return kelvin_report()
    except Exception:
        return sessions_text()


async def handle_text(text: str) -> list[str]:
    """Process one WhatsApp message (the shared commands live in chat_router)."""
    from helm.chat_router import handle
    return await handle(CHANNEL, text)


# ---------------------------------------------------------------------------
# neonize adapter
# ---------------------------------------------------------------------------

def _ensure_magic() -> None:
    """neonize imports python-magic, which needs the libmagic library. Windows
    rarely has it, and RAPR only sends text (magic is used for media mime
    types), so fall back to a stand-in instead of failing the import."""
    import sys
    try:
        import magic  # noqa: F401
    except Exception:
        import types
        stub = types.ModuleType("magic")
        stub.from_buffer = lambda buf, mime=False: "application/octet-stream" if mime else "data"
        stub.from_file = lambda path, mime=False: "application/octet-stream" if mime else "data"
        sys.modules["magic"] = stub


_PROTO_ALIAS_PREFIXES = ("wa", "instamadillo", "Neonize_pb2")


class _NeonizeProtoAliases:
    """neonize adds its proto folder to sys.path and imports those packages by
    short names ("waCommon", "waE2E.WAWebProtobufsE2E_pb2"), and elsewhere by
    their full names ("neonize.proto.waE2E..."). In the compiled Windows app
    there are no files on that path, only the compiled neonize.proto.* modules,
    so the short names fail ("No module named 'waAICommon'"). This finder,
    placed last so normal installs never reach it, answers a short name with
    the same compiled module under its full name (one module, not two copies,
    so protobuf registers each file once)."""

    def find_spec(self, fullname, path=None, target=None):
        import importlib.util
        if not fullname.startswith(_PROTO_ALIAS_PREFIXES):
            return None
        real = "neonize.proto." + fullname
        try:
            if importlib.util.find_spec(real) is None:
                return None
        except (ImportError, ValueError):
            return None
        return importlib.util.spec_from_loader(fullname, _ProtoAliasLoader(real))


class _ProtoAliasLoader:
    def __init__(self, real: str):
        self.real = real

    def create_module(self, spec):
        import importlib
        module = importlib.import_module(self.real)
        self._spec = module.__spec__   # Python overwrites it with the alias's spec
        return module

    def exec_module(self, module):
        module.__spec__ = self._spec   # already executed under its full name


def _ensure_proto_aliases() -> None:
    import sys
    if not any(isinstance(f, _NeonizeProtoAliases) for f in sys.meta_path):
        sys.meta_path.append(_NeonizeProtoAliases())


def approval_text(req: dict) -> str:
    details = "".join(f"\n  • {str(d)[:100]}" for d in (req.get("details") or [])[:5])
    return (f"⚠️ Approval needed\n{req.get('description', '')}{details}\n\n"
            f"Reply /approve {req['id']} or /deny {req['id']}")


async def notify_approval(req: dict) -> None:
    """Tell the WhatsApp chat that an action is waiting for approval."""
    if state["status"] != "connected":
        return
    await send_text(approval_text(req))


def _qr_data_uri(data: bytes) -> str:
    import segno
    buf = io.BytesIO()
    segno.make(data.decode() if isinstance(data, bytes) else data).save(buf, kind="png", scale=6, border=2)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _message_text(m) -> str:
    try:
        if m.conversation:
            return m.conversation
        if m.HasField("extendedTextMessage"):
            return m.extendedTextMessage.text
    except Exception:
        pass
    return ""


async def send_text(text: str, to=None) -> None:
    """Send text to WhatsApp (to the chat we last heard from by default)."""
    target = to or _reply_to
    if not (_client and target is not None and state["status"] == "connected"):
        return
    for part in chunks(text):
        _sent_texts.append((time.time(), part.strip()))
        try:
            resp = await _client.send_message(target, part)
            if getattr(resp, "ID", None):
                _sent_ids.append(resp.ID)
        except Exception as exc:
            logger.warning("WhatsApp send failed: %s", exc)
            return


async def _send_group_text(_group: dict, text: str) -> None:
    await send_text(text)


async def _on_message(client, ev) -> None:
    global _reply_to
    try:
        info = ev.Info
        src = info.MessageSource
        if info.ID in _sent_ids:
            return
        if src.Chat.Server in ("broadcast", "newsletter"):
            return
        senders = [src.Sender.User, src.SenderAlt.User if src.HasField("SenderAlt") else ""]
        if not is_authorized(src.Chat.User, senders, src.IsFromMe, src.IsGroup,
                             _me_users, allowed_numbers()):
            return
        text = _message_text(ev.Message)
        if not text:
            return
        if src.IsFromMe and is_echo(text):
            return
        _reply_to = src.Chat
        for reply in await handle_text(text):
            await send_text(reply, to=src.Chat)
    except Exception as exc:
        logger.warning("WhatsApp message handling failed: %s", exc, exc_info=True)


async def start() -> dict:
    """Connect (showing a QR code in the web UI if not linked yet)."""
    global _client
    if _client and state["status"] in ("starting", "qr", "connected"):
        return public_state()
    try:
        _ensure_magic()
        _ensure_proto_aliases()
        from neonize.aioze.client import NewAClient
        from neonize.aioze.events import ConnectedEv, MessageEv, LoggedOutEv, PairStatusEv
    except Exception as exc:  # missing wheel / libmagic on this machine
        state.update(status="error", available=False,
                     error=f"WhatsApp support isn't available on this install: {exc}")
        await _push_state()
        return public_state()

    state.update(status="starting", available=True, error=None, qr=None)
    await _push_state()
    client = NewAClient(_db_path())

    async def on_qr(_c, data: bytes):
        state.update(status="qr", qr=_qr_data_uri(data))
        await _push_state()

    client.event.qr(on_qr)

    @client.event(ConnectedEv)
    async def _on_connected(c, _ev):
        global _reply_to
        _me_users.clear()
        try:
            me = await c.get_me()
            for jid in (me.JID, me.LID):
                if jid.User:
                    _me_users.add(jid.User)
            state["me"] = me.JID.User or None
            if _reply_to is None and me.JID.User:
                from neonize.utils.jid import build_jid
                _reply_to = build_jid(me.JID.User)
        except Exception as exc:
            logger.warning("WhatsApp get_me failed: %s", exc)
        (_dir() / "linked").write_text(str(time.time()))
        state.update(status="connected", qr=None, error=None)
        logger.info("WhatsApp connected as %s", state["me"])
        await _push_state()

    @client.event(PairStatusEv)
    async def _on_pair(_c, _ev):
        state.update(qr=None)
        await _push_state()

    @client.event(LoggedOutEv)
    async def _on_logged_out(_c, _ev):
        logger.info("WhatsApp: logged out from the phone")
        await _forget()

    client.event(MessageEv)(_on_message)

    import helm.groupchat as gc
    gc.register_channel(CHANNEL, _send_group_text)
    _client = client
    try:
        await client.connect()
    except Exception as exc:
        state.update(status="error", error=str(exc))
        _client = None
        await _push_state()
        return public_state()
    asyncio.get_running_loop().create_task(_watch_start(client))
    return public_state()


async def _watch_start(client, timeout: float = 45.0) -> None:
    """Tell the user when WhatsApp can't be reached (it keeps retrying)."""
    await asyncio.sleep(timeout)
    if _client is client and state["status"] == "starting":
        state["error"] = ("Can't reach WhatsApp yet. Check this PC's internet connection "
                          "or firewall; RAPR keeps trying.")
        await _push_state()


async def _forget() -> None:
    """Drop the saved session so the next connect shows a fresh QR."""
    global _client, _reply_to
    _client = None
    _reply_to = None
    _me_users.clear()
    for name in ("linked", "whatsapp_session.db", "whatsapp_session.db-wal", "whatsapp_session.db-shm"):
        try:
            (_dir() / name).unlink()
        except FileNotFoundError:
            pass
        except Exception as exc:
            logger.warning("WhatsApp: could not remove %s: %s", name, exc)
    import helm.groupchat as gc
    if gc.active_groups.get(CHANNEL):
        gc.set_active_group(CHANNEL, None)
    state.update(status="off", qr=None, me=None, error=None)
    await _push_state()


async def stop(logout: bool = False) -> dict:
    """Disconnect; with logout=True also unlink RAPR from the phone."""
    client = _client
    if client:
        try:
            if logout:
                await client.logout()
            else:
                await client.disconnect()
        except Exception as exc:
            logger.warning("WhatsApp disconnect: %s", exc)
    if logout:
        await _forget()
    else:
        globals()["_client"] = None
        state.update(status="off", qr=None)
        await _push_state()
    return public_state()


async def autostart() -> None:
    """Reconnect at launch when WhatsApp was linked before."""
    if is_linked():
        await asyncio.sleep(2)
        await start()
