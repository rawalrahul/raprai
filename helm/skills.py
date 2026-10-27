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
    skill_enabled(skill, ai)               → bool
    set_skill_enabled(skill, ai, val)      → None

Writing new skills (create_skill, generate_skill, auto_create_skill_template)
is in helm/skill_creation.py.
"""

import os
import pathlib
import re
from typing import Optional

from helm.config import logger

# ---------------------------------------------------------------------------
# Stop words excluded from skill name generation (common English words)
# ---------------------------------------------------------------------------

_STOP_WORDS = frozenset({
    "about", "after", "also", "back", "been", "before", "being", "between",
    "both", "came", "come", "could", "each", "from", "have", "here", "into",
    "just", "like", "make", "many", "more", "most", "much", "must", "need",
    "only", "other", "over", "said", "same", "should", "show", "some",
    "such", "take", "than", "that", "their", "them", "then", "there",
    "these", "they", "this", "through", "time", "very", "want", "well",
    "were", "what", "when", "where", "which", "while", "will", "with",
    "would", "your", "able", "does", "done", "every", "good", "great",
    "help", "keep", "know", "look", "part", "please", "right", "tell",
    "thing", "think", "those", "using", "work", "write", "create", "update",
    "generate", "build", "implement", "develop", "design",
})

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

# ---------------------------------------------------------------------------
# Skill line-limit logic (Option C: model-aware + user-overridable)
# ---------------------------------------------------------------------------

# Cloud AIs (Claude, Gemini, Codex, etc.) — effectively no cap.
_MAX_LINES_CLOUD = 2000

# Ollama with a large model (≥30B) — treat like cloud.
_MAX_LINES_OLLAMA_LARGE = 2000

# Ollama with an unknown-size model — safe middle ground.
_MAX_LINES_OLLAMA_UNKNOWN = 600

# Ollama with a small model (<14B) — conservative.
_MAX_LINES_OLLAMA_SMALL = 250

# Size thresholds extracted from model name (e.g. "llama3:70b" → 70).
_OLLAMA_LARGE_B  = 30   # ≥ 30B → large
_OLLAMA_SMALL_B  = 14   # < 14B → small


def _ollama_model_size_b() -> Optional[int]:
    """
    Parse the active Ollama model name for a parameter-count hint (in billions).
    Returns None if the model name contains no recognisable size token.
    Reads OLLAMA_MODEL or DEFAULT_MODEL_OLLAMA env vars (same as ai_runner).
    """
    model = (
        os.environ.get("OLLAMA_MODEL", "")
        or os.environ.get("DEFAULT_MODEL_OLLAMA", "")
    ).lower()
    # Match patterns like "70b", "72b", "3.8b", "0.5b"
    m = re.search(r"(\d+(?:\.\d+)?)b", model)
    if m:
        try:
            return int(float(m.group(1)))
        except ValueError:
            pass
    return None


def _get_max_skill_lines(ai: str) -> int:
    """
    Return the effective skill-line cap for the given AI provider.

    Priority:
      1. MAX_SKILL_LINES env var (user override — always wins)
      2. Ollama: model-size heuristic (large/unknown/small)
      3. All other AIs: _MAX_LINES_CLOUD
    """
    override = os.environ.get("MAX_SKILL_LINES", "").strip()
    if override:
        try:
            return max(1, int(override))
        except ValueError:
            pass

    if ai == "ollama":
        size = _ollama_model_size_b()
        if size is None:
            return _MAX_LINES_OLLAMA_UNKNOWN
        if size >= _OLLAMA_LARGE_B:
            return _MAX_LINES_OLLAMA_LARGE
        if size < _OLLAMA_SMALL_B:
            return _MAX_LINES_OLLAMA_SMALL
        return _MAX_LINES_OLLAMA_UNKNOWN  # 14–29B: middle ground

    return _MAX_LINES_CLOUD


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


def reload_registry() -> None:
    """Convenience wrapper for hot-reload after helmpack install/uninstall."""
    scan_skills()


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

    # Skills that should never appear (auto-generated leftovers, etc.)
    _SKILL_BLOCKLIST = {
        "general-know-name-tell",
        "general-else-chrome",
        "general-gemini-hear",
        "general-mynemo-remeber",
    }

    def _register_skill_file(skill_file: pathlib.Path, skills_base: pathlib.Path,
                             fallback_name: str = "") -> bool:
        """Register a single skill from a .md file. Returns True on success."""
        nonlocal total_found
        if not skill_file.exists():
            return False

        # Check directory name against blocklist
        dir_name = skill_file.parent.name.lower()
        if dir_name in _SKILL_BLOCKLIST:
            return False

        try:
            raw  = skill_file.read_text(encoding="utf-8", errors="replace")
            meta, body = _parse_frontmatter(raw)
            if not meta:
                # No valid frontmatter — not a skill file, skip silently
                return False
            name = meta.get("name", fallback_name or skill_file.stem)

            # Also check name against blocklist
            if name.lower() in _SKILL_BLOCKLIST:
                return False

            if name in new_registry:
                # Already loaded from a higher-priority directory — skip.
                return False

            description = meta.get("description", "")
            explicit_kw = meta.get("keywords", "")
            keywords    = _extract_keywords(name, description, explicit_kw)
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
    "your", "our", "you", "over", "under", "after",
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
    "webapp-testing":    ["test website", "qa", "selenium",
                          "end to end test", "e2e test", "browser test"],
    "playwright-cli":    ["playwright", "browser automation", "open browser",
                          "open the browser", "browse website", "browse the web",
                          "web scraping", "scrape website", "scrape the website",
                          "fill form", "fill out form", "fill the form",
                          "fill out the form", "click button", "click the button",
                          "take screenshot of website", "screenshot of the page",
                          "automate browser", "visit website", "visit the website",
                          "go to website", "go to the website", "go to google",
                          "navigate to website", "navigate to the page",
                          "web page", "login to website", "login to the site",
                          "open url", "open a url", "open this url",
                          "browser task", "webpage", "website interaction",
                          "scrape the page", "scrape data from",
                          "automate login", "automate the login",
                          "open the site", "open the page",
                          "browse to", "go to .com", "go to .org",
                          "submit the form", "click on the website",
                          "interact with website", "interact with the page"],
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


def _extract_keywords(name: str, description: str,
                       explicit_keywords: str = "") -> list[str]:
    """Build a deduplicated keyword list for prompt matching.

    Sources (in priority order):
      0. Explicit keywords from frontmatter `keywords:` field (comma-separated)
      1. Full skill name (e.g. "invoice-organizer")
      2. Individual hyphen-split parts (e.g. "invoice", "organizer")
      3. File extensions found in description  (e.g. ".docx", "docx")
      4. Significant words from description  (stop-words & short words removed)
      5. Hand-curated extras from _EXTRA_KEYWORDS
    """
    keywords: list[str] = [name.lower()]

    # 0. Explicit keywords from frontmatter — highest signal
    if explicit_keywords:
        for kw in re.split(r'[,\s]+', explicit_keywords.strip()):
            kw = kw.strip().lower()
            if kw and len(kw) >= 2:
                keywords.append(kw)

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
    Takes up to _get_max_skill_lines(ai) lines of content, breaking at a clean
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
    cutoff = min(_get_max_skill_lines(ai), total)
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
        has_bash = "```bash" in snippet
        has_code = "```python" in snippet or has_bash
        if has_code:
            # CLI-first priority: if skill provides CLI commands, prefer those
            # over MCP tools for the same service (CLI is faster & more capable)
            cli_priority_note = ""
            if has_bash:
                cli_priority_note = (
                    "• PREFER the CLI commands in this skill over MCP tools for the "
                    "same service. The CLI is faster and more capable. Only fall back "
                    "to MCP tools if the CLI is not installed or the command fails.\n"
                )

            # Skill has code templates → instruct AI to write & execute code
            cli_preamble = (
                "\n[IMPORTANT — EXECUTION INSTRUCTIONS]\n"
                "You MUST write and execute a complete, self-contained Python script "
                "to complete this task. Copy the code templates above, adapt them for "
                "the user's specific request, and RUN the script.\n"
                f"{cli_priority_note}"
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

def inject_skill_prefix(prompt: str, ai: str = "", match_text: Optional[str] = None) -> str:
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

    match_text: what to pick the skill from, when `prompt` carries more than the
    user's own words (RAPR's file-safety rule mentions files and folders, which
    made every message look like a file-organizing task).
    """
    skill_name = detect_skill(prompt if match_text is None else match_text)
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
# Settings UI helpers
# ---------------------------------------------------------------------------

def list_skills() -> list[dict]:
    """Return a summary list suitable for the Settings panel."""
    import pathlib as _pl
    result = []
    for info in _registry.values():
        skill_path = _pl.Path(info["path"])
        # A skill is enabled if its SKILL.md exists (not renamed to .disabled)
        enabled = skill_path.exists() and skill_path.name == "SKILL.md"
        result.append({
            "name":        info["name"],
            "description": info["description"][:160] + ("…" if len(info["description"]) > 160 else ""),
            "keywords":    info["keywords"][:8],
            "path":        info["path"],
            "source_dir":  info.get("source_dir", ""),
            "enabled":     enabled,
        })
    return result


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


def get_pending_proposal_count() -> int:
    """Return count of pending skill proposals. 0 if learning disabled or no proposals."""
    try:
        from helm.learning.skill_proposals import list_proposals
        proposals = list_proposals(status_filter="pending_review")
        return len(proposals)
    except Exception:
        return 0


def list_skills_with_proposals() -> list[dict]:
    """list_skills() enriched with pending proposal count per skill."""
    skills = list_skills()
    try:
        from helm.learning.skill_proposals import list_proposals
        proposals = list_proposals(status_filter="pending_review")
        # Index proposals by target_skill name
        pending: dict[str, int] = {}
        for p in proposals:
            target = p.get("target_skill", "")
            # target_skill may be a path — extract skill name from it
            skill_name = pathlib.Path(target).parent.name if "/" in target or "\\" in target else target
            pending[skill_name] = pending.get(skill_name, 0) + 1
        for skill in skills:
            skill["pending_proposals"] = pending.get(skill["name"], 0)
    except Exception:
        for skill in skills:
            skill["pending_proposals"] = 0
    return skills
