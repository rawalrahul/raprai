"""
helm/skills.py — Shared Skill Library for AI-agnostic skill injection.

Scans one or more .skills/skills/ directories for SKILL.md files, builds a
merged registry (user skills take priority over system skills), detects which
skill is relevant to a given prompt, and injects the skill's best-practice
instructions as a context prefix before dispatching to any non-Claude AI
(Ollama, Gemini, Codex, or custom CLIs).

How it works
────────────
1.  scan_skills() is called once at server startup.
    It walks every configured skills directory, parses YAML frontmatter,
    and indexes each skill's name, description, keywords, and content.
    Earlier (higher-priority) paths win when two directories define the
    same skill name.

2.  When a user sends a task to Ollama (or any non-Claude integration),
    ai_runner.process_message() calls inject_skill_prefix(prompt) first.
    The function detects the best-matching skill from the registry and
    prepends a condensed version of its instructions to the prompt.

3.  The AI receives the enriched prompt and follows the skill's
    best-practice guidance without any user intervention.

4.  When the AI handles a task for which no skill exists, auto_create_skill_template()
    generates a new SKILL.md in the primary writable skills directory and
    hot-reloads the registry so subsequent identical tasks are enriched.

Path resolution order (highest → lowest priority)
──────────────────────────────────────────────────
  1. SKILLS_DIR env var  (colon-separated list of absolute paths)
  2. Auto-discovered user workspace .skills/skills/
     (walks up to 4 levels from project root, first match wins for user dir)
  3. Auto-discovered system .skills/skills/
     (continues upward past the user dir hit to catch the system skills too)

Public API
──────────
    scan_skills(skills_bases=None)          → dict   populate registry
    detect_skill(prompt)                    → str|None
    inject_skill_prefix(prompt, ai)         → str    (main entry point)
    list_skills()                           → list[dict]   for Settings UI
    get_skills_dir()                        → str|None     primary dir
    get_user_skills_dir()                   → str|None     writable primary dir
    create_skill(name, description, content)→ bool   create + hot-reload
    auto_create_skill_template(prompt, ai, output) → str|None  (skill name created)
    skill_enabled(skill, ai)               → bool
    set_skill_enabled(skill, ai, val)      → None
"""

import os
import pathlib
import re
import textwrap
from typing import Optional

from helm.config import logger

# ---------------------------------------------------------------------------
# Registry (populated at startup by scan_skills())
# ---------------------------------------------------------------------------

# { "docx": { "name", "description", "keywords", "content", "path" }, … }
_registry: dict[str, dict] = {}

# Ordered list of all resolved skill directories (for display + debugging)
_skills_dirs: list[pathlib.Path] = []

# The primary *writable* directory where new skills are created.
# Set to the first directory the process can write to.
_primary_skills_dir: Optional[pathlib.Path] = None

# Per-(skill, ai) enable flags.  Defaults to True (all skills on for all AIs).
# Key: "docx::ollama", value: bool
_enabled: dict[str, bool] = {}

# How many lines of skill content to inject — avoids flooding small context windows.
# Ollama skills can be code-heavy, so we allow a generous limit.
_MAX_SKILL_LINES = 250


# ---------------------------------------------------------------------------
# Startup scanner
# ---------------------------------------------------------------------------

def _candidate_paths() -> list[pathlib.Path]:
    """
    Build an ordered, deduplicated list of skills directories to scan.

    Priority order (index 0 = highest priority):
      1. Paths from SKILLS_DIR env var (colon-separated)
      2. Auto-discovered: walk upward from project root collecting every
         '.skills/skills' directory found (up to 6 levels).
    """
    seen: set[pathlib.Path] = set()
    candidates: list[pathlib.Path] = []

    def _add(p: pathlib.Path) -> None:
        p = p.resolve()
        if p not in seen:
            seen.add(p)
            candidates.append(p)

    # 1. Explicit env-var override
    env_val = os.environ.get("SKILLS_DIR", "").strip()
    if env_val:
        for part in env_val.split(":"):
            part = part.strip()
            if part:
                _add(pathlib.Path(part))

    # 2. Auto-discover: walk upward collecting ALL .skills/skills directories
    here   = pathlib.Path(__file__).parent.parent  # helm/ → project root
    search = here
    for _ in range(6):
        probe = search / ".skills" / "skills"
        if probe.exists():
            _add(probe)
        search = search.parent

    return candidates


def scan_skills(skills_bases=None) -> dict[str, dict]:
    """
    Scan all skills directories and populate the merged registry.
    Call once at startup; safe to call again to hot-reload.

    Parameters
    ----------
    skills_bases : str | list[str] | pathlib.Path | None
        Override the directories to scan.  None = auto-discover.
    """
    global _registry, _skills_dirs, _primary_skills_dir

    # ── Resolve the list of paths to scan ───────────────────────────────────
    if skills_bases is None:
        paths = _candidate_paths()
    elif isinstance(skills_bases, (str, pathlib.Path)):
        paths = [pathlib.Path(skills_bases)]
    else:
        paths = [pathlib.Path(p) for p in skills_bases]

    _skills_dirs = [p for p in paths if p.exists()]

    # Determine the primary writable dir (for creating new skills)
    _primary_skills_dir = None
    for p in _skills_dirs:
        if os.access(p, os.W_OK):
            _primary_skills_dir = p
            break

    # ── Load skills; first occurrence wins (higher-priority path) ───────────
    # Scans up to 2 levels deep: skills_base/*/SKILL.md  AND
    # skills_base/*/*/SKILL.md  (covers grouped skills like document-skills/pptx/).
    new_registry: dict[str, dict] = {}
    total_found = 0

    def _load_skill(skill_dir: pathlib.Path, skills_base: pathlib.Path) -> bool:
        """Try to register the skill in skill_dir. Returns True on success."""
        nonlocal total_found
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            return False
        try:
            raw  = skill_md.read_text(encoding="utf-8", errors="replace")
            meta, body = _parse_frontmatter(raw)
            name = meta.get("name", skill_dir.name)

            if name in new_registry:
                # Already loaded from a higher-priority directory — skip.
                return False

            description = meta.get("description", "")
            keywords    = _extract_keywords(name, description)
            new_registry[name] = {
                "name":        name,
                "description": description,
                "keywords":    keywords,
                "content":     body,
                "path":        str(skill_md),
                "source_dir":  str(skills_base),
            }
            total_found += 1
            return True
        except Exception as exc:
            logger.warning("skills.py: failed to load %s — %s", skill_md, exc)
            return False

    for skills_base in _skills_dirs:
        dir_found = 0
        for skill_dir in sorted(skills_base.iterdir()):
            if not skill_dir.is_dir():
                continue
            # Level 1: skills_base/foo/SKILL.md
            if _load_skill(skill_dir, skills_base):
                dir_found += 1
            else:
                # Level 2: skills_base/foo/bar/SKILL.md
                # (covers grouped directories like document-skills/pptx/)
                # Cap at 50 entries to avoid scanning huge dirs like composio-skills (800+).
                try:
                    count = 0
                    for sub_dir in skill_dir.iterdir():
                        count += 1
                        if count > 50:
                            logger.debug("Skills: level-2 scan of %s capped at 50",
                                         skill_dir.name)
                            break
                        if sub_dir.is_dir() and _load_skill(sub_dir, skills_base):
                            dir_found += 1
                except PermissionError:
                    pass

        logger.info("Skills: loaded %d skill(s) from %s", dir_found, skills_base)

    if not _skills_dirs:
        logger.info("Skills: no skills directory found — skill injection disabled.")

    logger.info("Skills: %d skill(s) total across %d director(y/ies)", total_found, len(_skills_dirs))
    if _primary_skills_dir:
        logger.info("Skills: primary writable dir = %s", _primary_skills_dir)

    _registry = new_registry
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

# Common English stop-words to exclude from description-based keyword extraction.
_STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "for", "to", "of", "in", "on",
    "at", "by", "is", "are", "was", "were", "be", "been", "being", "have",
    "has", "had", "do", "does", "did", "will", "would", "could", "should",
    "may", "might", "shall", "can", "not", "no", "with", "from", "into",
    "about", "as", "up", "that", "this", "it", "its", "than", "then", "so",
    "if", "when", "where", "which", "who", "what", "how", "all", "also",
    "any", "both", "each", "few", "more", "most", "other", "some", "such",
    "very", "just", "even", "across", "multiple", "without", "every",
    "between", "through", "their", "they", "them", "use", "used", "using",
    "make", "makes", "making", "like", "new", "turn", "turns", "help",
    "your", "our", "you", "your", "into", "over", "under", "after",
    # Generic quality adjectives — too common to be useful keyword signals
    "beautiful", "professional", "comprehensive", "powerful",
    "advanced", "detailed", "styled", "modern", "great",
    # Generic action verbs — present in almost every skill description
    "create", "creates", "creating", "build", "builds", "building",
    "generate", "generates", "generating", "produce", "produces",
    "perform", "performs", "apply", "applies",
}

# Hand-curated extra keywords that aren't always obvious from the description
_EXTRA_KEYWORDS: dict[str, list[str]] = {
    "docx":              ["word doc", "word document", "report", "memo",
                          "letter", "manuscript", "essay", ".docx", "docx",
                          "document"],
    "pdf":               [".pdf", "portable document", "fillable form", "ocr"],
    "pptx":              ["powerpoint", "slides", "slide deck", "pitch deck",
                          "presentation", "deck", ".pptx", "ppt"],
    "xlsx":              ["excel", "spreadsheet", "xls", "csv", "tabular",
                          ".xlsx", "budget", "financial model"],
    "humanizer":         ["write", "draft", "rewrite", "improve", "polish",
                          "humanize", "tone", "blog post", "email", "linkedin"],
    "canvas-design":     ["poster", "artwork", "flyer", "banner",
                          "illustration", "visual design", "graphic design"],
    "mcp-builder":       ["mcp server", "model context protocol", "mcp tool"],
    "slack-gif-creator": ["gif", "animated gif", "slack gif"],
    "theme-factory":     ["theme", "colour scheme", "color scheme", "styling"],
    "web-artifacts-builder": ["react", "html artifact", "ui component", "shadcn"],
}


def _extract_keywords(name: str, description: str) -> list[str]:
    """Build a deduplicated keyword list for prompt matching.

    Sources (in priority order):
      1. Full skill name (e.g. "invoice-organizer")
      2. Individual hyphen-split parts (e.g. "invoice", "organizer")
      3. File extensions found in description  (e.g. ".docx", "docx")
      4. Significant words from description  (stop-words & short words removed)
      5. Hand-curated extras from _EXTRA_KEYWORDS
    """
    keywords: list[str] = [name.lower()]

    # 2. Split name on hyphens and add each meaningful part
    for part in name.lower().split("-"):
        if len(part) >= 3 and part not in _STOP_WORDS:
            keywords.append(part)

    # 3. File extensions mentioned in description — skip for visual/design skills.
    #    Require at least 3 chars after the dot to avoid false positives like ".io".
    _skip_ext_for = {"canvas-design", "slack-gif-creator", "theme-factory"}
    if name not in _skip_ext_for:
        for ext in re.findall(r'\.[a-z]{3,5}\b', description.lower()):
            keywords.append(ext)              # ".docx"
            keywords.append(ext.lstrip("."))  # "docx"

    # 4. Significant words from description (length >= 4, not a stop-word)
    for word in re.findall(r'\b[a-z]{4,}\b', description.lower()):
        if word not in _STOP_WORDS:
            keywords.append(word)

    # 5. Extra curated keywords
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

# AI-prefixed skill names are reserved for AI-specific overrides.
# detect_skill() skips them so they never win over base skills for non-matching AIs.
# inject_skill_prefix() resolves them via direct lookup after detecting the base skill.
_AI_PREFIXES = ("ollama-", "gemini-", "codex-", "claude-", "openai-")


def detect_skill(prompt: str) -> Optional[str]:
    """
    Return the name of the best-matching *base* skill for the prompt, or None.

    Scoring: each keyword that appears in the lowercased prompt adds 1 point.
    The skill with the highest score wins.  Ties resolved alphabetically.

    AI-prefixed variants (e.g. "ollama-pptx") are excluded from scoring here;
    they are resolved in inject_skill_prefix() after the base skill is found.
    """
    if not _registry:
        return None

    pl = prompt.lower()
    best_name: Optional[str] = None
    best_score = 0

    for name, info in _registry.items():
        # Skip AI-specific variants — resolved by inject_skill_prefix() instead
        if any(name.startswith(pfx) for pfx in _AI_PREFIXES):
            continue
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

    AI-specific override: if a skill named "{ai}-{skill_name}" exists in the
    registry (e.g. "ollama-pptx" for ai="ollama", skill="pptx"), that variant
    is used instead of the generic skill.  This lets each AI integration have
    tailored instructions (e.g. python-pptx code for Ollama vs JS for Claude).

    Returns the original prompt unchanged if:
    - The registry is empty (skills directory not found)
    - No skill matches the prompt
    - The matched skill is disabled for this AI
    """
    skill_name = detect_skill(prompt)
    if not skill_name:
        return prompt

    # Prefer an AI-specific variant if one exists (e.g. "ollama-pptx")
    if ai:
        ai_specific = f"{ai}-{skill_name}"
        if ai_specific in _registry:
            logger.debug("Skill injection: using AI-specific variant '%s' (base='%s')",
                         ai_specific, skill_name)
            skill_name = ai_specific

    if ai and not skill_enabled(skill_name, ai):
        return prompt

    prefix = _build_prefix(skill_name)
    if not prefix:
        return prompt

    logger.info("Skill injection: skill=%s ai=%s prompt_chars=%d",
                skill_name, ai or "unknown", len(prompt))
    return prefix + prompt


# ---------------------------------------------------------------------------
# Skill creation helpers
# ---------------------------------------------------------------------------

_TASK_HINTS: list[tuple[list[str], str]] = [
    # (trigger keywords, task_label)
    (["word", "docx", "document", "report", "memo", "letter"],          "document_creation"),
    (["excel", "xlsx", "spreadsheet", "csv", "table", "budget"],        "spreadsheet"),
    (["powerpoint", "pptx", "slides", "presentation", "deck"],          "presentation"),
    (["pdf"],                                                             "pdf"),
    (["image", "photo", "png", "jpg", "jpeg", "diagram", "chart"],      "image_generation"),
    (["email", "draft", "write", "blog", "post", "linkedin"],           "writing"),
    (["web", "html", "react", "css", "component", "ui"],                "web_development"),
    (["python", "script", "code", "function", "class", "module"],       "python_scripting"),
    (["git", "commit", "push", "branch", "merge"],                      "git_operations"),
    (["api", "request", "json", "fetch", "endpoint"],                   "api_integration"),
    (["summarize", "summary", "analyse", "analyze", "review"],          "analysis"),
    (["translate", "translation"],                                        "translation"),
]


def _detect_task_type(prompt: str) -> str:
    """Return a short task-type label for the prompt (best effort)."""
    pl = prompt.lower()
    best_label = "general"
    best_score = 0
    for keywords, label in _TASK_HINTS:
        score = sum(1 for kw in keywords if kw in pl)
        if score > best_score:
            best_score = score
            best_label = label
    return best_label


def _skill_name_from_prompt(prompt: str) -> str:
    """
    Derive a short kebab-case skill name from the prompt / task type.
    e.g. "document_creation" → "document-creation"
    """
    task_type = _detect_task_type(prompt)
    return task_type.replace("_", "-")


def _generate_skill_content(task_type: str, ai: str, prompt: str, output: str) -> str:
    """
    Generate a SKILL.md body appropriate for the AI type and task.

    Ollama skills include Python code patterns (since Ollama uses execute_python).
    Gemini/Codex skills include natural-language prompt strategies.
    Generic skills contain general best-practice guidance.
    """
    display_task = task_type.replace("_", " ").title()
    ai_upper = (ai or "unknown").upper()

    # ── Common header ─────────────────────────────────────────────────────
    header = textwrap.dedent(f"""\
        # {display_task} Skill
        > Auto-generated by Helm HQ for {ai_upper} on first encounter.
        > Edit this file to improve guidance for future tasks.

        ## What this skill covers
        Tasks involving {display_task.lower()}.

        ## Key objectives
        - Produce accurate, complete, and well-structured output
        - Confirm what was created or modified at the end
        - Handle errors gracefully and report them clearly
    """)

    # ── AI-specific body ──────────────────────────────────────────────────
    if ai == "ollama":
        body = _ollama_skill_body(task_type)
    elif ai in ("gemini", "codex"):
        body = _cli_skill_body(task_type, ai)
    else:
        body = _generic_skill_body(task_type)

    return header + "\n" + body


def _ollama_skill_body(task_type: str) -> str:
    """Skill body for Ollama — focuses on tool usage and Python code patterns."""
    bodies: dict[str, str] = {
        "document_creation": textwrap.dedent("""\
            ## Approach (Ollama with tools)
            Use `execute_python` to create Word documents via `python-docx`.

            ```python
            import subprocess, sys
            subprocess.check_call([sys.executable, "-m", "pip", "install",
                                   "python-docx", "-q"])
            from docx import Document
            from docx.shared import Pt, RGBColor
            doc = Document()
            doc.add_heading("Title", 0)
            doc.add_paragraph("Body text here.")
            doc.save("output.docx")
            print("✓ Created output.docx")
            ```

            ## Tips
            - Always install packages silently with `-q`
            - Use `doc.add_heading(text, level)` for structure
            - Save with a descriptive filename matching the user's request
        """),
        "spreadsheet": textwrap.dedent("""\
            ## Approach (Ollama with tools)
            Use `execute_python` with `openpyxl` for Excel files.

            ```python
            import subprocess, sys
            subprocess.check_call([sys.executable, "-m", "pip", "install",
                                   "openpyxl", "-q"])
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Sheet1"
            ws.append(["Column A", "Column B"])
            ws.append([1, 2])
            wb.save("output.xlsx")
            print("✓ Created output.xlsx")
            ```
        """),
        "presentation": textwrap.dedent("""\
            ## Approach (Ollama with tools)
            Use `execute_python` with `python-pptx` for PowerPoint files.

            ```python
            import subprocess, sys
            subprocess.check_call([sys.executable, "-m", "pip", "install",
                                   "python-pptx", "-q"])
            from pptx import Presentation
            from pptx.util import Inches, Pt
            prs = Presentation()
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = "Slide Title"
            slide.placeholders[1].text = "Slide content here."
            prs.save("output.pptx")
            print("✓ Created output.pptx")
            ```
        """),
        "pdf": textwrap.dedent("""\
            ## Approach (Ollama with tools)
            Use `execute_python` with `reportlab` for PDF creation.

            ```python
            import subprocess, sys
            subprocess.check_call([sys.executable, "-m", "pip", "install",
                                   "reportlab", "-q"])
            from reportlab.pdfgen import canvas as rl_canvas
            c = rl_canvas.Canvas("output.pdf")
            c.drawString(72, 750, "Hello PDF World")
            c.save()
            print("✓ Created output.pdf")
            ```
        """),
    }
    default = textwrap.dedent("""\
        ## Approach (Ollama with tools)
        - Use `execute_python` for any binary file formats
        - Use `write_file` for plain text, Markdown, JSON, CSV
        - Use `list_directory` to inspect the workspace before editing
        - Always print a confirmation message at the end

        ## Error handling
        Wrap all file operations in try/except and report errors clearly.
    """)
    return bodies.get(task_type, default)


def _cli_skill_body(task_type: str, ai: str) -> str:
    """Skill body for CLI AIs (Gemini, Codex) — natural language instructions."""
    ai_name = ai.title()
    return textwrap.dedent(f"""\
        ## Approach ({ai_name})
        When handling {task_type.replace("_", " ")} tasks:

        1. **Plan first** — outline what you will create before writing code.
        2. **Self-contained scripts** — every script should run without external
           setup beyond standard pip-installable libraries.
        3. **Install dependencies inline** — use subprocess to pip-install if needed.
        4. **Confirm at the end** — print the exact filename(s) created.
        5. **Error handling** — catch exceptions and report them clearly.

        ## Quality checklist
        - Output file exists and is non-empty
        - File format is correct (not corrupted)
        - Filename matches user's request or is descriptively named
    """)


def _generic_skill_body(task_type: str) -> str:
    return textwrap.dedent(f"""\
        ## Approach
        When handling {task_type.replace("_", " ")} tasks:

        1. Understand the user's intent fully before starting.
        2. Produce complete, accurate output.
        3. Confirm what was created at the end.
        4. Handle errors gracefully.
    """)


def create_skill(name: str, description: str, content: str) -> bool:
    """
    Write a new SKILL.md to the primary writable skills directory and
    hot-reload the registry.

    Parameters
    ----------
    name        Kebab-case skill name (e.g. "document-creation")
    description One-line description (used as registry description + YAML)
    content     Full Markdown body of the skill (without frontmatter)

    Returns True on success, False if no writable skills dir is configured.
    """
    global _primary_skills_dir

    if _primary_skills_dir is None:
        # Try to find/create a default path
        here = pathlib.Path(__file__).parent.parent
        fallback = here / ".skills" / "skills"
        try:
            fallback.mkdir(parents=True, exist_ok=True)
            _primary_skills_dir = fallback
        except Exception as exc:
            logger.error("create_skill: no writable skills dir and could not create fallback: %s", exc)
            return False

    skill_dir = _primary_skills_dir / name
    skill_md  = skill_dir / "SKILL.md"

    try:
        skill_dir.mkdir(parents=True, exist_ok=True)
        safe_desc = description.replace('"', "'")
        frontmatter = f'---\nname: "{name}"\ndescription: "{safe_desc}"\n---\n\n'
        skill_md.write_text(frontmatter + content, encoding="utf-8")
        logger.info("create_skill: wrote %s", skill_md)
    except Exception as exc:
        logger.error("create_skill: failed to write %s — %s", skill_md, exc)
        return False

    # Hot-reload the registry so the new skill is immediately available
    scan_skills()
    return True


def auto_create_skill_template(prompt: str, ai: str, output: str = "") -> Optional[str]:
    """
    Auto-generate and save a SKILL.md for the detected task type.

    Called after a task completes when no skill was matched, so that future
    identical tasks receive guidance.  Returns the skill name created, or None
    if creation failed or was skipped.

    Skips creation if:
    - No primary writable skills directory is available
    - The detected skill name already exists in the registry
    - The prompt is very short (< 10 chars) — likely not meaningful
    """
    if len(prompt.strip()) < 10:
        return None

    skill_name = _skill_name_from_prompt(prompt)

    # Don't overwrite an existing skill
    if skill_name in _registry:
        return None

    task_type   = _detect_task_type(prompt)
    description = f"Best practices for {task_type.replace('_', ' ')} tasks with {ai or 'AI'}."
    content     = _generate_skill_content(task_type, ai or "", prompt, output)

    success = create_skill(skill_name, description, content)
    if success:
        logger.info("auto_create_skill_template: created skill '%s' for ai=%s", skill_name, ai)
        return skill_name
    return None


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
            "source_dir":  info.get("source_dir", ""),
        }
        for info in _registry.values()
    ]


def get_skills_dir() -> Optional[str]:
    """Return the primary discovered skills directory path (for display in Settings)."""
    if _skills_dirs:
        return str(_skills_dirs[0])
    return None


def get_user_skills_dir() -> Optional[str]:
    """Return the primary *writable* skills directory (where new skills are saved)."""
    return str(_primary_skills_dir) if _primary_skills_dir else None


def get_all_skills_dirs() -> list[str]:
    """Return all loaded skills directories (for display in Settings)."""
    return [str(p) for p in _skills_dirs]
