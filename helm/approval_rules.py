"""
helm/approval_rules.py — Your own rules for what needs a yes.

Built-in checks (delete, remove, drop table…) still ask. These rules add your
own, in Settings or in the file user data/approval_rules.json:

  {"id": "no-main-push", "match": "git push.*(origin )?main", "action": "deny",
   "description": "Never push to main from RAPR", "enabled": true}

action:
  ask    — always ask you (even if a built-in check wouldn't)
  deny   — refuse without asking
  allow  — approve without asking (use with care)

match is a case-insensitive regular expression, checked against the approval's
description and details. The first enabled rule that matches decides.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from helm.config import logger

ACTIONS = ("ask", "deny", "allow")


def _path():
    from helm.paths import user_data_dir
    return user_data_dir() / "approval_rules.json"


def load_rules() -> list[dict]:
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
        return [r for r in data.get("rules", []) if isinstance(r, dict)]
    except FileNotFoundError:
        return []
    except Exception as exc:
        logger.warning("Approval rules unreadable, ignoring them: %s", exc)
        return []


def save_rules(rules: list[dict]) -> None:
    clean = [validate(r) for r in rules]
    _path().write_text(json.dumps({"rules": clean}, indent=2, ensure_ascii=False), encoding="utf-8")


def validate(rule: dict) -> dict:
    """Return a clean rule, or raise ValueError describing what's wrong."""
    rid = str(rule.get("id", "")).strip()
    match = str(rule.get("match", "")).strip()
    action = str(rule.get("action", "ask")).strip().lower()
    if not rid:
        raise ValueError("every rule needs an id")
    if not match:
        raise ValueError(f"rule {rid}: match can't be empty")
    if action not in ACTIONS:
        raise ValueError(f"rule {rid}: action must be one of {', '.join(ACTIONS)}")
    try:
        re.compile(match)
    except re.error as exc:
        raise ValueError(f"rule {rid}: bad pattern ({exc})") from exc
    return {"id": rid, "match": match, "action": action,
            "description": str(rule.get("description", ""))[:200],
            "enabled": bool(rule.get("enabled", True))}


def evaluate(text: str, rules: Optional[list[dict]] = None) -> Optional[dict]:
    """The first enabled rule whose pattern matches `text`, or None."""
    for rule in (load_rules() if rules is None else rules):
        if not rule.get("enabled", True):
            continue
        try:
            if re.search(rule["match"], text, re.IGNORECASE):
                return rule
        except (re.error, KeyError):
            continue
    return None
