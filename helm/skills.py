"""
helm/skills.py — Shared Skill Library for AI-agnostic skill injection.

Scans the .skills/skills/ directory for SKILL.md files, builds a registry,
detects which skill is relevant to a given prompt, and injects the skill's
best-practice instructions as a context prefix before dispatching to any
non-Claude AI (Ollama, Gemini, Codex, or custom CLIs).

How it works
────────────
1.  scan_skills() is called once at server startup.
    It walks .skills/skills/<name>/SKILL.md, parses the YAML frontmatter,
    and indexes each skill's name, description, keywords, and content.

2.  When a user sends a task to Ollama (or any non-Claude integration),
    ai_runner.process_message() calls inject_skill_prefix(prompt) first.
    The function detects the best-matching skill from the registry and
    prepends a condensed version of its instructions to the prompt.

3.  The AI receives the enriched prompt and follows the skill's
    best-practice guidance without any user intervention.

Public API
──────────
    scan_skills(skills_base=None)       → dict   populate registry
    detect_skill(prompt)                → str|None
    inject_skill_prefix(prompt)         → str    (main entry point)
    list_skills()                       → list[dict]   for Settings UI
    get_skills_dir()                    → str|None
    skill_enabled(skill, ai)            → bool
    set_skill_enabled(skill, ai, val)   → None
"""

import pathlib
import re
from typing import Optional

from helm.config import logger

# ---------------------------------------------------------------------------
# Registry (populated at startup by scan_skills())
# ---------------------------------------------------------------------------

# { "docx": { "name", "description", "keywords", "content", "path" }, … }
_registry: dict[str, dict] = {}

_skills_dir: Optional[pathlib.Path] = None

# Per-(skill, ai) enable flags.  Defaults to True (all skills on for all AIs).
# Key: "docx::ollama", value: bool
_enabled: dict[str, bool] = {}

# How many lines of skill content to inject — avoids flooding small context windows.
_MAX_SKILL_LINES = 90


# ---------------------------------------------------------------------------
# Startup scanner
# ---------------------------------------------------------------------------

def scan_skills(skills_base: Optional[str] = None) -> dict[str, dict]:
    """Scan the skills directory and populate the registry.  Call once at startup."""
    global _registry, _skills_dir

    if skills_base is None:
        # Walk upward from the project root until we find a .skills/skills
        # directory.  This handles the common case where Helm HQ lives inside
        # a workspace folder and .skills sits one level above it.
        here = pathlib.Path(__file__).parent.parent  # helm/ → project root
        candidate = None
        search = here
        for _ in range(4):  # look up at most 4 levels
            probe = search / ".skills" / "skills"
            if probe.exists():
                candidate = probe
                break
            search = search.parent
        skills_base = candidate or (here / ".skills" / "skills")

    skills_base = pathlib.Path(skills_base)
    _skills_dir = skills_base

    _registry = {}

    if not skills_base.exists():
        logger.info("Skills directory not found at %s — skill injection disabled.", skills_base)
        return _registry

    found = 0
    for skill_dir in sorted(skills_base.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        try:
            raw = skill_md.read_text(encoding="utf-8", errors="replace")
            meta, body = _parse_frontmatter(raw)
            name = meta.get("name", skill_dir.name)
            description = meta.get("description", "")
            keywords = _extract_keywords(name, description)
            _registry[name] = {
                "name":        name,
                "description": description,
                "keywords":    keywords,
                "content":     body,
                "path":        str(skill_md),
            }
            found += 1
        except Exception as exc:
            logger.warning("skills.py: failed to load %s — %s", skill_md, exc)

    logger.info("Skill registry: %d skill(s) loaded from %s", found, skills_base)
    return _registry


# ---------------------------------------------------------------------------
# Frontmatter parser
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split YAML frontmatter from body.  Returns (meta_dict, body_str)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm_block = text[3:end].strip()
    body = text[end + 4:].lstrip("\n")
    meta: dict = {}
    for line in fm_block.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, body


# ---------------------------------------------------------------------------
# Keyword extractor
# ---------------------------------------------------------------------------

# Hand-curated extra keywords that aren't always obvious from the description
_EXTRA_KEYWORDS: dict[str, list[str]] = {
    "docx":              ["word doc", "word document", "report", "memo",
                          "letter", "manuscript", "essay", ".docx"],
    "pdf":               [".pdf", "portable document", "fillable form", "ocr"],
    "pptx":              ["powerpoint", "slides", "slide deck", "pitch deck",
                          "presentation", "deck", ".pptx"],
    "xlsx":              ["excel", "spreadsheet", "xls", "csv", "tabular",
                          ".xlsx", "budget", "financial model"],
    "humanizer":         ["write", "draft", "rewrite", "improve", "polish",
                          "humanize", "tone", "blog post", "email", "linkedin"],
    "canvas-design":     ["poster", "artwork", "flyer", "banner",
                          "illustration", "visual design", "graphic design"],
    "mcp-builder":       ["mcp server", "model context protocol", "mcp tool"],
    "pptx":              ["presentation", "slides", "deck", "powerpoint", ".pptx"],
    "slack-gif-creator": ["gif", "animated gif", "slack gif"],
    "theme-factory":     ["theme", "colour scheme", "color scheme", "styling"],
    "web-artifacts-builder": ["react", "html artifact", "ui component", "shadcn"],
}


def _extract_keywords(name: str, description: str) -> list[str]:
    """Build a deduplicated keyword list for prompt matching."""
    keywords: list[str] = [name.lower()]

    # File extensions mentioned in description — skip for visual/design skills
    # where file extensions describe output format rather than skill triggers.
    _skip_ext_for = {"canvas-design", "slack-gif-creator", "theme-factory"}
    if name not in _skip_ext_for:
        for ext in re.findall(r'\.[a-z]{2,5}\b', description.lower()):
            keywords.append(ext)           # ".docx"
            keywords.append(ext.lstrip("."))  # "docx"

    # Extra curated keywords
    for kw in _EXTRA_KEYWORDS.get(name, []):
        keywords.append(kw.lower())

    # Deduplicate preserving insertion order
    seen: set[str] = set()
    result: list[str] = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            result.append(kw)
    return result


# ---------------------------------------------------------------------------
# Enable / disable flags
# ---------------------------------------------------------------------------

def _flag_key(skill: str, ai: str) -> str:
    return f"{skill}::{ai}"


def skill_enabled(skill: str, ai: str) -> bool:
    """Return True (default) if skill injection is enabled for this skill+AI pair."""
    return _enabled.get(_flag_key(skill, ai), True)


def set_skill_enabled(skill: str, ai: str, enabled: bool) -> None:
    """Toggle skill injection for a specific skill+AI pair from the Settings UI."""
    _enabled[_flag_key(skill, ai)] = enabled
    logger.info("Skill injection %s: skill=%s ai=%s",
                "enabled" if enabled else "disabled", skill, ai)


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def detect_skill(prompt: str) -> Optional[str]:
    """
    Return the name of the best-matching skill for the prompt, or None.

    Scoring: each keyword that appears in the lowercased prompt adds 1 point.
    The skill with the highest score wins.  Ties resolved alphabetically.
    """
    if not _registry:
        return None

    pl = prompt.lower()
    best_name: Optional[str] = None
    best_score = 0

    for name, info in _registry.items():
        score = sum(1 for kw in info["keywords"] if kw in pl)
        # Bonus: skill name itself appearing in the prompt is a strong signal
        if name.lower() in pl or name.lower().replace("-", " ") in pl:
            score += 2
        if score > best_score:
            best_score = score
            best_name = name

    return best_name if best_score > 0 else None


# ---------------------------------------------------------------------------
# Skill prefix builder
# ---------------------------------------------------------------------------

def _build_prefix(skill_name: str) -> str:
    """
    Build the context-prefix block injected before the user prompt.
    Takes up to _MAX_SKILL_LINES lines of content, breaking at a clean
    section boundary (## heading or --- divider) where possible.
    """
    info = _registry.get(skill_name)
    if not info:
        return ""

    lines = info["content"].splitlines()
    total = len(lines)

    # Find a clean break point at or before the line limit
    cutoff = min(_MAX_SKILL_LINES, total)
    for i in range(cutoff - 1, max(0, cutoff - 20), -1):
        ln = lines[i].strip()
        if ln.startswith("##") or ln == "---":
            cutoff = i  # stop just before the next major section
            break

    snippet = "\n".join(lines[:cutoff]).rstrip()

    return (
        f"[HELM HQ SKILL: {skill_name}]\n"
        f"The following best-practice guide applies to this task. "
        f"Follow it carefully to produce high-quality output.\n\n"
        f"{snippet}\n\n"
        f"[END SKILL — now complete the user's task below]\n\n"
    )


# ---------------------------------------------------------------------------
# Public injection entry point
# ---------------------------------------------------------------------------

def inject_skill_prefix(prompt: str, ai: str = "") -> str:
    """
    Detect the best skill for `prompt`, check it is enabled for `ai`,
    build the prefix, and return the augmented prompt.

    Returns the original prompt unchanged if:
    - The registry is empty (skills directory not found)
    - No skill matches the prompt
    - The matched skill is disabled for this AI
    """
    skill_name = detect_skill(prompt)
    if not skill_name:
        return prompt

    if ai and not skill_enabled(skill_name, ai):
        return prompt

    prefix = _build_prefix(skill_name)
    if not prefix:
        return prompt

    logger.info("Skill injection: skill=%s ai=%s prompt_chars=%d",
                skill_name, ai or "unknown", len(prompt))
    return prefix + prompt


# ---------------------------------------------------------------------------
# Settings UI helpers
# ---------------------------------------------------------------------------

def list_skills() -> list[dict]:
    """Return a summary list suitable for the Settings panel."""
    return [
        {
            "name":        info["name"],
            "description": info["description"][:160] + ("…" if len(info["description"]) > 160 else ""),
            "keywords":    info["keywords"][:8],
            "path":        info["path"],
        }
        for info in _registry.values()
    ]


def get_skills_dir() -> Optional[str]:
    """Return the discovered skills directory path (for display in Settings)."""
    return str(_skills_dir) if _skills_dir else None
