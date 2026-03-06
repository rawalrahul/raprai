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
    from helm.paths import PROJECT_ROOT, user_data_dir
    here   = user_data_dir()  # writable root (exe dir when bundled)
    search = here
    # Also check the bundle root (for skills shipped with the installer)
    _add((PROJECT_ROOT / ".skills" / "skills").resolve())
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
    # Scans up to 2 levels deep and supports TWO layouts:
    #   A) skills_base/skill-name/SKILL.md          (directory-based)
    #   B) skills_base/category/some-skill.md        (standalone .md files with frontmatter)
    # Also: skills_base/category/skill-name/SKILL.md  (grouped directory-based)
    new_registry: dict[str, dict] = {}
    total_found = 0

    def _register_skill_file(skill_file: pathlib.Path, skills_base: pathlib.Path,
                             fallback_name: str = "") -> bool:
        """Register a single skill from a .md file. Returns True on success."""
        nonlocal total_found
        if not skill_file.exists():
            return False
        try:
            raw  = skill_file.read_text(encoding="utf-8", errors="replace")
            meta, body = _parse_frontmatter(raw)
            if not meta:
                # No valid frontmatter — not a skill file, skip silently
                return False
            name = meta.get("name", fallback_name or skill_file.stem)

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
                "path":        str(skill_file),
                "source_dir":  str(skills_base),
            }
            total_found += 1
            return True
        except Exception as exc:
            logger.warning("skills.py: failed to load %s — %s", skill_file, exc)
            return False

    def _load_skill_dir(skill_dir: pathlib.Path, skills_base: pathlib.Path) -> bool:
        """Try to register a skill from a SKILL.md inside skill_dir."""
        return _register_skill_file(skill_dir / "SKILL.md", skills_base,
                                    fallback_name=skill_dir.name)

    for skills_base in _skills_dirs:
        dir_found = 0
        for entry in sorted(skills_base.iterdir()):
            if not entry.is_dir():
                continue
            # Level 1: skills_base/foo/SKILL.md  (directory-based skill)
            _load_skill_dir(entry, skills_base)

            # Level 2: always scan inside for both layouts:
            #   - skills_base/category/bar/SKILL.md   (sub-directory skill)
            #   - skills_base/category/bar.md          (standalone .md with frontmatter)
            # Cap at 200 entries to avoid scanning huge dirs.
            try:
                count = 0
                for sub_entry in sorted(entry.iterdir()):
                    count += 1
                    if count > 200:
                        logger.debug("Skills: level-2 scan of %s capped at 200",
                                     entry.name)
                        break
                    if sub_entry.is_dir():
                        _load_skill_dir(sub_entry, skills_base)
                    elif (sub_entry.suffix == ".md"
                          and sub_entry.name not in ("README.md", "SKILL.md",
                                                     "SKILLS_SUMMARY.txt")):
                        # Standalone .md file with frontmatter
                        _register_skill_file(sub_entry, skills_base)
            except PermissionError:
                pass

        dir_found = sum(1 for n, i in new_registry.items()
                        if i["source_dir"] == str(skills_base))

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
    # ── Document generation ────────────────────────────────────────────────
    "docx":              ["word doc", "word document", "report", "memo",
                          "letter", "manuscript", "essay", ".docx", "docx",
                          "document", "write a report", "formal letter"],
    "pdf":               [".pdf", "portable document", "fillable form", "ocr",
                          "pdf report", "merge pdf", "split pdf", "extract pdf"],
    "pptx":              ["powerpoint", "slides", "slide deck", "pitch deck",
                          "presentation", "deck", ".pptx", "ppt", "keynote"],
    "xlsx":              ["excel", "spreadsheet", "xls", "csv", "tabular",
                          ".xlsx", "budget", "financial model", "data table",
                          "pivot table", "chart", "workbook"],
    # ── Content & writing ──────────────────────────────────────────────────
    "humanizer":         ["write", "draft", "rewrite", "improve", "polish",
                          "humanize", "tone", "blog post", "email", "linkedin"],
    "content-research-writer": ["research", "article", "blog", "write about",
                          "content", "long form", "seo", "topic research",
                          "blog post", "write a post", "write an article"],
    # ── Scheduling & automation ────────────────────────────────────────────
    "schedule":          ["scheduled task", "recurring", "automation", "cron",
                          "run daily", "run weekly", "automate", "periodic",
                          "schedule this", "timer", "interval"],
    # ── Design & visual ────────────────────────────────────────────────────
    "canvas-design":     ["poster", "artwork", "flyer", "banner",
                          "illustration", "visual design", "graphic design"],
    "image-enhancer":    ["enhance image", "upscale", "improve image",
                          "photo edit", "resize image", "compress image"],
    "brand-guidelines":  ["brand guide", "brand kit", "brand identity",
                          "logo usage", "brand colors", "style guide"],
    "theme-factory":     ["theme", "colour scheme", "color scheme", "styling",
                          "dark mode", "light mode", "ui theme"],
    # ── Web & code ─────────────────────────────────────────────────────────
    "artifacts-builder": ["react", "html artifact", "ui component", "shadcn",
                          "web app", "frontend", "interactive", "dashboard",
                          "web component", "single page"],
    "webapp-testing":    ["test website", "qa", "selenium", "playwright",
                          "end to end test", "e2e test", "browser test"],
    "mcp-builder":       ["mcp server", "model context protocol", "mcp tool"],
    # ── Communication ────────────────────────────────────────────────────
    "email-composer":    ["email", "write an email", "draft email", "compose email",
                          "send email", "email template", "follow up email"],
    "blog-post-writer":  ["blog", "blog post", "write a blog", "write a post",
                          "article", "content writing"],
    "resume-cover-letter": ["resume", "cv", "cover letter", "job application",
                          "curriculum vitae", "write a resume"],
    "invoice-generator": ["invoice", "create invoice", "create an invoice",
                          "generate invoice", "bill", "billing statement",
                          "send invoice", "invoice template"],
    "feedback-giver":    ["feedback", "give feedback", "performance review",
                          "peer review", "constructive feedback"],
    # ── Business & productivity ────────────────────────────────────────────
    "invoice-organizer": ["invoice", "receipt", "billing", "expense",
                          "payment", "accounts payable"],
    "file-organizer":    ["organize files", "sort files", "clean up folder",
                          "rename files", "file management", "declutter"],
    "meeting-insights-analyzer": ["meeting notes", "meeting summary", "action items",
                          "meeting transcript", "standup", "retrospective"],
    "changelog-generator": ["changelog", "release notes", "what changed",
                          "version history", "git log summary"],
    "lead-research-assistant": ["lead research", "prospect", "company research",
                          "sales research", "linkedin research"],
    "competitive-ads-extractor": ["competitor ads", "ad copy", "competitor analysis",
                          "marketing analysis", "ad research"],
    "developer-growth-analysis": ["developer metrics", "github stats",
                          "code review", "team velocity", "dev productivity",
                          "developer team", "dev team", "engineering metrics"],
    # ── Media ──────────────────────────────────────────────────────────────
    "slack-gif-creator": ["gif", "animated gif", "slack gif", "create gif",
                          "make a gif", "gif from", "screen gif"],
    "video-downloader":  ["download video", "youtube download", "save video",
                          "video url", "extract video", "youtube", "video from"],
    # ── Resume & career ────────────────────────────────────────────────────
    "tailored-resume-generator": ["resume", "cv", "cover letter", "job application",
                          "tailor resume", "career"],
    "domain-name-brainstormer":  ["domain name", "website name", "url ideas",
                          "domain brainstorm", "name generator"],
    # ── Skill management ───────────────────────────────────────────────────
    "skill-creator":     ["create skill", "new skill", "edit skill",
                          "skill template", "build a skill"],
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
    name_parts = [p for p in name.lower().split("-") if len(p) >= 3 and p not in _STOP_WORDS]
    for part in name_parts:
        keywords.append(part)

    # 2b. Generate multi-word phrases from consecutive name parts
    #     e.g. "blog-post-writer" → "blog post", "post writer"
    #     These are high-value signals when matched in the prompt.
    for i in range(len(name_parts) - 1):
        keywords.append(f"{name_parts[i]} {name_parts[i+1]}")

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


def _kw_matches(keyword: str, prompt_lower: str) -> bool:
    """Check if a keyword matches in the prompt using word-boundary-aware matching.

    Multi-word keywords (e.g. 'blog post') use substring matching.
    Single-word keywords use word-boundary matching to avoid false positives
    like 'voice' matching 'invoice' or 'post' matching 'compost'.
    """
    if " " in keyword:
        # Multi-word phrase — substring match is appropriate
        return keyword in prompt_lower
    # Single word — require word boundary (letter/digit boundary)
    pattern = r'(?<![a-z0-9])' + re.escape(keyword) + r'(?![a-z0-9])'
    return bool(re.search(pattern, prompt_lower))


def detect_skill(prompt: str) -> Optional[str]:
    """
    Return the name of the best-matching *base* skill for the prompt, or None.

    Scoring: each keyword that appears in the prompt adds 1 point.
    Multi-word keywords get +1 bonus (more specific = more valuable).
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
        score = 0
        for kw in info["keywords"]:
            if _kw_matches(kw, pl):
                score += 1
                # Multi-word keywords are more specific — bonus point
                if " " in kw:
                    score += 1
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

def _build_prefix(skill_name: str, ai: str = "") -> str:
    """
    Build the context-prefix block injected before the user prompt.
    Takes up to _MAX_SKILL_LINES lines of content, breaking at a clean
    section boundary (## heading or --- divider) where possible.

    For CLI-based AIs (claude, gemini, codex), appends an execution preamble
    instructing the AI to write and run Python code from the skill templates.
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

    # CLI execution preamble for non-Ollama AIs
    # (Ollama has its own tool-calling system prompt that handles this)
    cli_preamble = ""
    if ai and ai != "ollama":
        has_code = "```python" in snippet or "```bash" in snippet
        if has_code:
            # Skill has code templates → instruct AI to write & execute code
            cli_preamble = (
                "\n[IMPORTANT — EXECUTION INSTRUCTIONS]\n"
                "You MUST write and execute a complete, self-contained Python script "
                "to complete this task. Copy the code templates above, adapt them for "
                "the user's specific request, and RUN the script.\n"
                "• Install packages silently: subprocess.check_call([sys.executable, "
                '"-m", "pip", "install", "package-name", "-q"])\n'
                "• Save output files to the current working directory.\n"
                "• Print the exact filename(s) created when done.\n"
                "• Do NOT just explain the code — actually execute it.\n"
                "[END INSTRUCTIONS]\n\n"
            )
        else:
            # Skill has guidance/instructions only → just ask AI to follow them
            cli_preamble = (
                "\n[IMPORTANT — FOLLOW THE SKILL GUIDE ABOVE]\n"
                "Apply the best practices and instructions from the skill guide above "
                "to complete the user's task. If you need to create files, write and "
                "execute code to do so. Confirm what you created or accomplished.\n"
                "[END INSTRUCTIONS]\n\n"
            )

    return (
        f"[HELM HQ SKILL: {skill_name}]\n"
        f"The following best-practice guide applies to this task. "
        f"Follow it carefully to produce high-quality output.\n\n"
        f"{snippet}\n\n"
        f"[END SKILL]{cli_preamble}"
        f"Now complete the user's task below:\n\n"
    )


# ---------------------------------------------------------------------------
# Public injection entry point
# ---------------------------------------------------------------------------

def inject_skill_prefix(prompt: str, ai: str = "") -> str:
    """
    Detect the best skill for `prompt`, check it is enabled for `ai`,
    build the prefix, and return the augmented prompt.

    AI-specific override order:
      1. "{ai}-{skill}" variant  (e.g. "gemini-pptx")
      2. "ollama-{skill}" as universal code-generation fallback
         (ollama skills have Python code templates usable by ANY coding CLI)
      3. Base skill (e.g. "pptx")

    Returns the original prompt unchanged if:
    - The registry is empty (skills directory not found)
    - No skill matches the prompt
    - The matched skill is disabled for this AI
    """
    skill_name = detect_skill(prompt)
    if not skill_name:
        return prompt

    resolved = skill_name  # will be updated if an AI variant is found

    if ai:
        # 1. Prefer an AI-specific variant (e.g. "gemini-pptx")
        ai_specific = f"{ai}-{skill_name}"
        if ai_specific in _registry:
            logger.debug("Skill injection: using AI-specific variant '%s' (base='%s')",
                         ai_specific, skill_name)
            resolved = ai_specific
        # 2. Fallback: use ollama variant for ANY CLI AI (has Python code templates)
        elif ai != "ollama":
            ollama_variant = f"ollama-{skill_name}"
            if ollama_variant in _registry:
                logger.debug("Skill injection: using ollama variant '%s' as universal "
                             "code-gen fallback for ai='%s' (base='%s')",
                             ollama_variant, ai, skill_name)
                resolved = ollama_variant

    if ai and not skill_enabled(resolved, ai):
        return prompt

    prefix = _build_prefix(resolved, ai=ai)
    if not prefix:
        return prompt

    logger.info("Skill injection: skill=%s (resolved=%s) ai=%s prompt_chars=%d",
                skill_name, resolved, ai or "unknown", len(prompt))
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
        > Auto-generated by RAPR AI for {ai_upper} on first encounter.
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
        from helm.paths import user_data_dir
        fallback = user_data_dir() / ".skills" / "skills"
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


def claude_generate_skill(prompt: str, ai: str, error_output: str = "") -> Optional[str]:
    """
    Invoke Claude CLI to generate a high-quality SKILL.md for a task the AI failed.

    This is the "self-healing" path: when a non-Claude AI encounters a task it
    cannot handle and no skill exists, Claude is asked to create a reusable skill
    so the original AI can retry (and future tasks succeed immediately).

    Returns the skill name on success, None on failure or if Claude CLI unavailable.
    """
    import shutil
    import subprocess as sp

    if not shutil.which("claude"):
        logger.warning("claude_generate_skill: 'claude' CLI not found — skipping")
        return None

    skill_name = _skill_name_from_prompt(prompt)
    task_type = _detect_task_type(prompt)

    # Don't overwrite existing skills
    if skill_name in _registry:
        logger.info("claude_generate_skill: skill '%s' already exists — skipping", skill_name)
        return skill_name

    display_task = task_type.replace("_", " ").title()

    claude_prompt = textwrap.dedent(f"""\
        You are a skill author for RAPR AI, a multi-AI orchestration platform.
        An AI ({ai}) failed the following user task. Create a reusable SKILL.md
        that will help ANY AI model (including small local models like qwen2.5-coder:7b)
        succeed at this type of task in the future.

        ## Failed task
        {prompt[:1500]}

        ## Error output
        {error_output[:1000] if error_output else "(no error output)"}

        ## Task type detected
        {display_task}

        ## Requirements for the SKILL.md
        - Write clear, step-by-step instructions the AI should follow
        - Include complete Python code templates with all imports
        - Code must be self-contained (install deps inline with pip)
        - Include error handling patterns
        - Include quality checklist at the end
        - Target AI: {ai} (but make it usable by any AI)
        - Keep it under 200 lines
        - Do NOT include YAML frontmatter — just the Markdown body

        Output ONLY the Markdown content for the SKILL.md file. No preamble, no explanation.
    """)

    try:
        result = sp.run(
            ["claude", "-p", claude_prompt, "--output-format", "text"],
            capture_output=True, text=True, timeout=120,
            env={**os.environ, "CLAUDE_AUTO_APPROVE": "1"},
        )
        if result.returncode != 0 or not result.stdout.strip():
            logger.warning("claude_generate_skill: Claude returned code=%d, output=%d chars",
                           result.returncode, len(result.stdout or ""))
            return None

        content = result.stdout.strip()
        description = f"AI-generated skill for {display_task.lower()} tasks (created by Claude for {ai})."
        success = create_skill(skill_name, description, content)
        if success:
            logger.info("claude_generate_skill: created high-quality skill '%s' via Claude CLI",
                        skill_name)
            return skill_name
        return None

    except sp.TimeoutExpired:
        logger.warning("claude_generate_skill: Claude CLI timed out (120s)")
        return None
    except Exception as exc:
        logger.warning("claude_generate_skill: unexpected error — %s", exc)
        return None


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
