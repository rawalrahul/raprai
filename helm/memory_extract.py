"""
helm/memory_extract.py — Decide what to remember from a session, with an AI.

The approach Mem0 popularised, in one call per session: what the user said
since the last extraction, plus the stored memories that look related, go to a
small model. It answers with operations, not just facts:
  add      a new lasting fact, preference, decision...
  update   an existing memory changed ("we moved from SQLite to Postgres")
  archive  an existing memory is now wrong (archived, not deleted)
so memory stays consistent instead of piling up contradictions. Pinned
memories are never changed.

Only the user's own messages are read, never AI replies or tool output, so a
web page or file an AI looked at can't plant memories.

Which AI does it (MEMORY_EXTRACTOR in .env):
  auto    (default) local Ollama if it's running; else Claude (Haiku) for a
          Claude session, whose messages already went to Anthropic; else the
          pattern matcher. A conversation is never sent to a provider it
          didn't already go to.
  ollama | claude   always that one (pattern matcher if it fails)
  regex   the pattern matcher only
  off     nothing is extracted
MEMORY_EXTRACTOR_MODEL overrides the model (Ollama model name or Claude alias).
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import tempfile
import urllib.request
from typing import Optional

from helm.config import logger
from helm import memory as mem

_OLLAMA = "http://localhost:11434"
_MAX_OPS = 10
_MAX_CONTENT = 300
_MAX_INPUT_CHARS = 8000

_PROMPT = """You maintain long-term memory for a user of AI coding assistants. \
Memories are injected into every future AI conversation, so keep only what will \
still matter weeks from now: the user's lasting preferences, facts about them, \
their projects and team, decisions they made, and standing instructions.

Do NOT save: one-off task requests ("fix this bug"), questions, things about \
this conversation only, secrets (passwords, API keys, tokens), or anything the \
user didn't state themselves.

Compare with the existing memories. If a message changes one, update it; if a \
message shows one is no longer true, archive it; if it's already known, skip it.

Existing memories (id: [category] text):
{existing}

New messages from the user:
{messages}

Reply with JSON only, no other text:
{{"ops": [
  {{"op": "add", "category": "preference|fact|project|person|decision|instruction", "content": "short standalone sentence"}},
  {{"op": "update", "id": 12, "content": "the corrected memory"}},
  {{"op": "archive", "id": 7}}
]}}
Use {{"ops": []}} when nothing is worth remembering."""


# ---------------------------------------------------------------------------
# Choosing the AI
# ---------------------------------------------------------------------------

def _setting() -> str:
    return (os.environ.get("MEMORY_EXTRACTOR") or "auto").strip().lower()


def _ollama_up() -> bool:
    try:
        with urllib.request.urlopen(_OLLAMA + "/api/tags", timeout=1.5) as r:
            return r.status == 200
    except Exception:
        return False


def _claude_installed() -> bool:
    import shutil
    return shutil.which("claude") is not None


def pick_extractor(sess: dict) -> str:
    """ollama | claude | regex | off for this session."""
    choice = _setting()
    if choice in ("off", "regex", "ollama", "claude"):
        return choice
    if _ollama_up():
        return "ollama"
    if sess.get("ai") == "claude" and _claude_installed():
        return "claude"
    return "regex"


# ---------------------------------------------------------------------------
# Calling it
# ---------------------------------------------------------------------------

def _ask_ollama(prompt: str) -> str:
    import helm.state as _st
    model = (os.environ.get("MEMORY_EXTRACTOR_MODEL") or _st.default_models.get("ollama")
             or os.environ.get("OLLAMA_MODEL") or "qwen3:4b")
    body = {"model": model, "stream": False, "format": "json", "options": {"temperature": 0},
            "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(_OLLAMA + "/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return (json.loads(r.read()).get("message") or {}).get("content", "")


def _ask_claude(prompt: str) -> str:
    from helm.ai_runner.claude import parse_claude_json_output
    from helm.ai_runner.core import run_ai_popen
    model = os.environ.get("MEMORY_EXTRACTOR_MODEL") or "haiku"
    # No tools, an empty folder, nothing saved: this call only reads the prompt.
    cmd = ["claude", "-p", "--tools", "", "--model", model,
           "--no-session-persistence", "--output-format", "json"]
    with tempfile.TemporaryDirectory(prefix="rapr_mem_") as cwd:
        raw = run_ai_popen(cmd, cwd, "claude", {}, 120, prompt)
    return parse_claude_json_output(raw).get("text", "")


def parse_ops(raw: str) -> Optional[list[dict]]:
    """The ops list from a model reply, or None if it isn't usable JSON."""
    text = re.sub(r"<think>.*?</think>", "", raw or "", flags=re.S).strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except (json.JSONDecodeError, ValueError):
        return None
    ops = data.get("ops") if isinstance(data, dict) else None
    return [o for o in ops if isinstance(o, dict)] if isinstance(ops, list) else None


# ---------------------------------------------------------------------------
# Building the prompt and applying the answer
# ---------------------------------------------------------------------------

def _related(texts: list[str]) -> dict[int, dict]:
    found: dict[int, dict] = {}
    for t in texts:
        for m in mem.search_memories(t[:500], limit=5):
            found.setdefault(m["id"], m)
        if len(found) >= 25:
            break
    return found


def build_prompt(texts: list[str], related: dict[int, dict]) -> str:
    existing = "\n".join(f"{i}: [{m['category']}] {m['content']}" for i, m in related.items()) or "(none)"
    msgs, used = [], 0
    for t in reversed(texts):   # newest first wins the space
        t = t.strip()[:1500]
        if used + len(t) > _MAX_INPUT_CHARS:
            break
        msgs.insert(0, "- " + t.replace("\n", " "))
        used += len(t)
    return _PROMPT.format(existing=existing, messages="\n".join(msgs))


def apply_ops(ops: list[dict], related: dict[int, dict], sess: dict) -> int:
    """Carry out the model's ops. Only ids it was shown, never pinned ones."""
    changed = 0
    for op in ops[:_MAX_OPS]:
        kind = str(op.get("op", "")).lower()
        content = str(op.get("content") or "").strip()[:_MAX_CONTENT]
        try:
            mid = int(op.get("id")) if op.get("id") is not None else None
        except (TypeError, ValueError):
            mid = None
        target = related.get(mid) if mid is not None else None
        try:
            if kind == "add" and len(content) >= 5:
                category = str(op.get("category") or "").lower()
                mem.add_memory(content, category if category in mem.VALID_CATEGORIES else mem.DEFAULT_CATEGORY,
                               source_ai=sess.get("ai") or "", session_id=sess.get("id", ""))
                changed += 1
            elif kind == "update" and target and not target.get("pinned") and len(content) >= 5:
                changed += mem.edit_memory(mid, content=content)
            elif kind in ("archive", "delete") and target and not target.get("pinned"):
                changed += mem.archive_memory(mid)
        except Exception as exc:
            logger.warning("memory: could not apply %s: %s", kind, exc)
    return changed


async def extract_and_save(sess: dict) -> int:
    """Remember what's worth remembering from the session's new messages.
    Returns how many memories were added, updated or archived."""
    how = await asyncio.to_thread(pick_extractor, sess)
    if how == "off":
        return 0
    if how == "regex":
        return await asyncio.to_thread(mem.save_extracted_memories, sess)

    texts, cursor = mem.new_user_texts(sess)
    if not texts:
        return 0
    related = await asyncio.to_thread(_related, texts)
    prompt = build_prompt(texts, related)
    try:
        raw = await asyncio.to_thread(_ask_ollama if how == "ollama" else _ask_claude, prompt)
        ops = parse_ops(raw)
    except Exception as exc:
        logger.info("memory: %s extraction failed (%s); using patterns", how, exc)
        ops = None
    if ops is None:
        return await asyncio.to_thread(mem.save_extracted_memories, sess)
    changed = await asyncio.to_thread(apply_ops, ops, related, sess)
    sess["_memory_cursor"] = cursor
    if changed:
        logger.info("memory: %s made %d change(s) from session %s", how, changed, sess.get("id", "?"))
    return changed
