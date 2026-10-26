"""
helm/ai_runner/prompt.py — what RAPR adds to a message before an AI sees it.
"""

from helm.config import logger
from helm.plugins import inject_plugin_context
from helm.skills import inject_skill_prefix


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
