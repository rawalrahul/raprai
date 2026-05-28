"""
helm/learning/injector.py

Builds learned-context blocks to prepend to AI prompts.
Reads playbooks and antipatterns directly from disk — does NOT import playbook.py.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_LEARNING_DIR = Path(__file__).parent
_PLAYBOOKS_DIR = _LEARNING_DIR / "playbooks"
_ANTIPATTERNS_DIR = _LEARNING_DIR / "antipatterns"
_TEMPLATES_DIR = _LEARNING_DIR / "prompt_templates"
_ERROR_LOG = _LEARNING_DIR / "telemetry_errors.log"

# ---------------------------------------------------------------------------
# In-memory cache: key -> (content, expires_at)
# ---------------------------------------------------------------------------
_cache: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 60.0

# ---------------------------------------------------------------------------
# Task types that never get context injected
# ---------------------------------------------------------------------------
_SKIP_TYPES = {"chat", "unknown"}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _log_error(msg: str) -> None:
    """Append error message to telemetry_errors.log. Best-effort."""
    try:
        with _ERROR_LOG.open("a", encoding="utf-8") as fh:
            fh.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] injector: {msg}\n")
    except Exception:
        pass


def _count_tokens(text: str) -> int:
    """Approximate token count: len(text) // 4."""
    return len(text) // 4


def _cache_get(key: str) -> Optional[str]:
    entry = _cache.get(key)
    if entry is None:
        return None
    content, expires_at = entry
    if time.monotonic() > expires_at:
        del _cache[key]
        return None
    return content


def _cache_set(key: str, content: str) -> None:
    _cache[key] = (content, time.monotonic() + _CACHE_TTL)


def _load_best_playbook(task_type: str, fingerprint: Optional[str]) -> Optional[str]:
    """
    Scan helm/learning/playbooks/{task_type}/ for subdirs.
    Each subdir must have meta.json (status=="active") and current.md.
    If fingerprint given, prefer exact match on meta["fingerprint"].
    Otherwise return content of highest success_rate active playbook.
    Returns markdown string or None.
    """
    cache_key = f"playbook:{task_type}:{fingerprint or ''}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached or None  # "" stored means "not found"

    try:
        task_dir = _PLAYBOOKS_DIR / task_type
        if not task_dir.is_dir():
            _cache_set(cache_key, "")
            return None

        best_content: Optional[str] = None
        best_rate: float = -1.0
        fingerprint_match: Optional[str] = None

        for subdir in task_dir.iterdir():
            if not subdir.is_dir():
                continue
            meta_path = subdir / "meta.json"
            content_path = subdir / "current.md"
            if not meta_path.exists() or not content_path.exists():
                continue
            try:
                with meta_path.open("r", encoding="utf-8") as mf:
                    meta = json.load(mf)
            except Exception as exc:
                _log_error(f"meta.json read failed ({meta_path}): {exc}")
                continue

            if meta.get("status") != "active":
                continue

            try:
                with content_path.open("r", encoding="utf-8") as cf:
                    content = cf.read()
            except Exception as exc:
                _log_error(f"current.md read failed ({content_path}): {exc}")
                continue

            # Exact fingerprint match — highest priority
            if fingerprint and meta.get("fingerprint") == fingerprint:
                fingerprint_match = content
                break  # no need to keep scanning

            rate = float(meta.get("success_rate", 0.0))
            if rate > best_rate:
                best_rate = rate
                best_content = content

        result = fingerprint_match if fingerprint_match is not None else best_content
        _cache_set(cache_key, result if result is not None else "")
        return result

    except Exception as exc:
        _log_error(f"_load_best_playbook({task_type}): {exc}")
        return None


def _load_prompt_template(task_type: str) -> Optional[str]:
    """
    Load prompt template for task_type from prompt_templates/.
    "code.debug" -> code_debug.txt, fallback to task_type.txt directly.
    """
    cache_key = f"template:{task_type}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached or None

    try:
        candidates = [
            _TEMPLATES_DIR / (task_type.replace(".", "_") + ".txt"),
            _TEMPLATES_DIR / (task_type + ".txt"),
        ]
        for path in candidates:
            if path.exists():
                content = path.read_text(encoding="utf-8").strip()
                _cache_set(cache_key, content)
                return content
        _cache_set(cache_key, "")
        return None
    except Exception as exc:
        _log_error(f"_load_prompt_template({task_type}): {exc}")
        return None


def _load_antipatterns(task_type: str) -> Optional[str]:
    """
    Load antipatterns for task_type.
    "code.debug" -> antipatterns/code_debug.md
    Reads first 1500 chars only.
    """
    cache_key = f"antipatterns:{task_type}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached or None

    try:
        filename = task_type.replace(".", "_") + ".md"
        ap_path = _ANTIPATTERNS_DIR / filename
        if not ap_path.exists():
            _cache_set(cache_key, "")
            return None

        with ap_path.open("r", encoding="utf-8") as fh:
            content = fh.read(1500)

        _cache_set(cache_key, content)
        return content

    except Exception as exc:
        _log_error(f"_load_antipatterns({task_type}): {exc}")
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_context(
    task_type: str,
    fingerprint: Optional[str] = None,
    ai: str = "claude",
    max_tokens: int = 800,
) -> str:
    """
    Build learned context block for injection into AI prompt.
    Returns empty string if nothing relevant or on any error.
    Never raises.
    """
    try:
        # Kill switch — return empty if learning is disabled
        try:
            from helm.learning import is_learning_enabled
            if not is_learning_enabled():
                return ""
        except Exception:
            pass

        # Guard: skip non-actionable task types
        if not task_type or task_type.strip() in _SKIP_TYPES:
            return ""

        task_type = task_type.strip()
        budget = max_tokens  # tokens remaining
        parts: list[str] = []

        # --- 0: Prompt template for this task type ---
        template = _load_prompt_template(task_type)
        if template:
            tokens_needed = _count_tokens(template)
            if tokens_needed <= budget:
                parts.append(template)
                budget -= tokens_needed

        # --- 1 & 2: Best playbook (fingerprint-exact first, then best rate) ---
        playbook_content = _load_best_playbook(task_type, fingerprint)
        if playbook_content:
            tokens_needed = _count_tokens(playbook_content)
            if tokens_needed <= budget:
                parts.append(playbook_content)
                budget -= tokens_needed
            else:
                # Truncate to fit
                char_budget = budget * 4
                parts.append(playbook_content[:char_budget])
                budget = 0

        # --- 3: Antipatterns for task_type ---
        if budget > 0:
            ap_content = _load_antipatterns(task_type)
            if ap_content:
                tokens_needed = _count_tokens(ap_content)
                if tokens_needed <= budget:
                    parts.append(ap_content)
                    budget -= tokens_needed
                else:
                    char_budget = budget * 4
                    parts.append(ap_content[:char_budget])
                    budget = 0

        # --- 4: Generic computer_use antipatterns (always for computer_use tasks) ---
        if budget > 0 and task_type == "computer_use":
            # Already loaded above if task_type is computer_use — skip double load
            pass
        elif budget > 0 and task_type.startswith("computer_use"):
            generic_ap = _load_antipatterns("computer_use")
            if generic_ap and generic_ap not in parts:
                tokens_needed = _count_tokens(generic_ap)
                if tokens_needed <= budget:
                    parts.append(generic_ap)
                    budget -= tokens_needed
                else:
                    char_budget = budget * 4
                    parts.append(generic_ap[:char_budget])

        # --- 5: Cross-AI performance hints ---
        if budget > 0:
            try:
                from helm.learning.cross_ai import get_hints as _get_cross_hints
                cross_hints = _get_cross_hints(ai, task_type, fingerprint)
                if cross_hints:
                    tokens_needed = _count_tokens(cross_hints)
                    if tokens_needed <= budget:
                        parts.append(cross_hints)
                        budget -= tokens_needed
                    else:
                        char_budget = budget * 4
                        parts.append(cross_hints[:char_budget])
                        budget = 0
            except Exception:
                pass

        # --- 6: User environment context (screen/browser/OS) ---
        if budget > 0:
            try:
                from helm.learning.user_context import get_context_block
                env_block = get_context_block()
                if env_block:
                    tokens_needed = _count_tokens(env_block)
                    if tokens_needed <= budget:
                        parts.append(env_block)
                        budget -= tokens_needed
            except Exception:
                pass

        # If nothing was collected, return empty
        if not parts:
            return ""

        body = "\n\n".join(parts)
        return f"[LEARNED CONTEXT — {task_type}]\n{body}\n[END LEARNED CONTEXT]\n\n"

    except Exception as exc:
        _log_error(f"build_context({task_type}): {exc}")
        return ""
