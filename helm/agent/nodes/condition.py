"""Condition node executor."""


async def evaluate_condition(question: str, context: str) -> bool:
    """Evaluate a yes/no condition against context."""
    question_l = question.lower()
    context_l = context.lower()
    if "mention" in question_l or "contains" in question_l:
        for marker in ("mention ", "mentions ", "contains "):
            if marker in question_l:
                term = question_l.split(marker, 1)[1].strip(" ?'\".")
                if term:
                    return term in context_l

    try:
        from helm.ai_runner.core import process_message
        from helm.session_mgr import make_session
        prompt = (
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Answer with exactly one word: YES or NO."
        )
        sess = make_session("claude")
        answer = await process_message(prompt, source="agent", session_id=sess["id"])
        return "yes" in answer.strip().lower()
    except Exception:
        return False


async def execute_condition_node(node: dict, context: str) -> str:
    """Return 'true' or 'false' for a condition node."""
    question = node.get("task", "").strip()
    if not question:
        return "false"
    return "true" if await evaluate_condition(question, context) else "false"
