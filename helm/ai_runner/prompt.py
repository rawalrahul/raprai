"""
helm/ai_runner/prompt.py — what RAPR adds to a message before an AI sees it.
"""

from helm.config import logger
from helm.plugins import inject_plugin_context
from helm.skills import inject_skill_prefix


_SAFETY_PREAMBLE = (
    "\n[SAFETY RULE — FILE DELETION]\n"
    "You MUST NEVER delete, remove, or overwrite any file or directory without "
    "explicitly asking the user for permission first and receiving confirmation. "
    "This applies to ALL destructive operations: rm, del, rmdir, shutil.rmtree, "
    "os.remove, os.unlink, pathlib.Path.unlink, rimraf, Remove-Item, etc. "
    "Always list the exact files/folders you intend to delete and wait for the "
    "user to say 'yes' before proceeding. If in doubt, DO NOT delete.\n\n"
)


def base_prompt(text: str, ai: str, clf: dict, background: bool = False) -> str:
    """The safety rule, then *text*; learned playbooks and antipatterns go first,
    except for background looks (your brief)."""
    prompt = _SAFETY_PREAMBLE + text
    if background:
        return prompt
    try:
        from helm.learning.injector import build_context
        learned = build_context(task_type=clf.get("task_type", "unknown"),
                                fingerprint=clf.get("task_fingerprint"), ai=ai)
        if learned:
            prompt = learned + prompt
    except Exception:
        logger.debug("Couldn't add learned context to the prompt", exc_info=True)
    return prompt


def enrich_prompt(safe_text: str, text: str, ai: str, sess: dict) -> str:
    """Add the matching skill guide (not for read-only looks), plugin context,
    shared memory and your personalization to *safe_text*."""
    enriched_text = safe_text if sess.get("read_only") else \
        inject_skill_prefix(safe_text, ai=ai, match_text=text)
    enriched_text = inject_plugin_context(enriched_text)

    # Inject shared AI memory into prompt
    try:
        from helm.memory import get_memory_block
        _mem = get_memory_block(prompt=safe_text)
        if _mem:
            enriched_text = _mem + enriched_text
    except Exception:
        logger.debug("Couldn't add shared memory to the prompt", exc_info=True)

    # Inject user personalization and custom instructions
    try:
        from helm.personalization import get_personalization_block
        _pblock = get_personalization_block()
        if _pblock:
            enriched_text = _pblock + enriched_text
    except Exception:
        logger.debug("Couldn't add personalization to the prompt", exc_info=True)
    return enriched_text
