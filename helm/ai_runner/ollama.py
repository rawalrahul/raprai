"""
helm/ai_runner/ollama.py — Ollama REST API agent and tool execution.

Covers: ollama_model_supports_tools, _OLLAMA_TOOLS, _execute_ollama_tool,
        _parse_content_tool_calls, _ollama_system_prompt, _run_ollama_agent.
"""

import asyncio
import json
import os
import pathlib
import re
import subprocess
import urllib.error

from helm.subprocess_utils import hidden_kwargs
import urllib.request

import helm.state as _st
from helm.broadcast import push_message
from helm.config import logger
from helm.skills import inject_skill_prefix, detect_skill

from .ollama_tools import (
    _build_ollama_tools, _execute_ollama_tool, _get_mcp_manager,
    _parse_content_tool_calls,
)


_OLLAMA_URL = "http://localhost:11434/api/chat"


# Both helpers block (a local model can take minutes to answer): call them with
# asyncio.to_thread so the wait doesn't freeze RAPR's event loop, and with it
# the web UI, chat apps and every other session.

def installed_models() -> list[str]:
    """Names of the models Ollama has installed (``ollama list``); [] if none or no Ollama."""
    try:
        r = subprocess.run(["ollama", "list"], capture_output=True, text=True,
                           timeout=5, **hidden_kwargs())
    except (OSError, subprocess.SubprocessError, ValueError):   # ValueError: odd output bytes
        return []
    return [line.split()[0] for line in r.stdout.strip().splitlines()[1:] if line.split()]


def _chat(payload: dict, timeout: int) -> dict:
    """POST *payload* to Ollama's chat API and return its decoded reply."""
    req = urllib.request.Request(
        _OLLAMA_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())

_OLLAMA_TOOL_SUPPORT: dict[str, bool] = {
    "qwen2.5":          True,
    "qwen3":            True,
    "llama3.1":         True,
    "llama3.2":         True,
    "llama3.3":         True,
    "mistral-nemo":     True,
    "mistral-small3.1": True,   # vision + tools (good for computer use)
    "mistral-small3.2": True,   # vision + tools (good for computer use)
    "mistral":          True,
    "command-r":        True,
    "granite3":         True,
    "firefunction":     True,
    "smollm2":          True,
    # Vision-first models below carry NO `tools` capability tag in Ollama —
    # /api/chat rejects requests with a `tools` key ("does not support tools").
    # They must be False so the agent loop never passes tools to them.
    "llama3.2-vision":  False,
    "qwen2-vl":         False,
    "qwen2.5vl":        False,
    "minicpm-v":        False,
    "deepseek-r1":      False,
    "deepseek-v":       False,
    "llama2":           False,
    "phi3":             False,
    "gemma":            False,
    "gemma2":           False,
    "gemma3":           False,
    "codellama":        False,
    "starcoder":        False,
    "flux":             False,
    "stable-diffusion": False,
    "llava":            False,
    "llava-llama3":     False,
    "llava-phi3":       False,
    "bakllava":         False,
    "moondream":        False,
}

# Vision-capable models — can receive base64 images in messages
_OLLAMA_VISION_SUPPORT: dict[str, bool] = {
    "llama3.2-vision":  True,
    "mistral-small3.1": True,   # vision + tools — preferred for computer use
    "mistral-small3.2": True,   # vision + tools — preferred for computer use
    "qwen2-vl":         True,
    "qwen2.5vl":        True,
    "minicpm-v":        True,
    "llava":            True,
    "llava-llama3":     True,
    "llava-phi3":       True,
    "bakllava":         True,
    "moondream":        True,
    "gemma3":           True,
}


def _longest_prefix_match(m: str, table: dict[str, bool]) -> bool | None:
    """Return the value for the LONGEST matching prefix, or None if none match.

    Longest-match matters: 'llama3.2-vision' starts with both 'llama3.2' and
    'llama3.2-vision'. First-match would wrongly inherit the 'llama3.2' value;
    the more specific 'llama3.2-vision' entry must win.
    """
    best: bool | None = None
    best_len = -1
    for prefix, supported in table.items():
        if m.startswith(prefix) and len(prefix) > best_len:
            best, best_len = supported, len(prefix)
    return best


def ollama_model_supports_tools(model: str) -> bool | None:
    """
    Return True if the model is known to support tool calling,
    False if known not to, or None if unknown.
    """
    m = model.lower().split(":")[0]
    return _longest_prefix_match(m, _OLLAMA_TOOL_SUPPORT)


def ollama_model_supports_vision(model: str) -> bool:
    """Return True if the model can process images (multimodal)."""
    m = model.lower().split(":")[0]
    return _longest_prefix_match(m, _OLLAMA_VISION_SUPPORT) is True


# ---------------------------------------------------------------------------
# MCP tools (dynamically added from all running MCP servers)
# ---------------------------------------------------------------------------


def _ollama_system_prompt(cwd: str, skill_content: str = "", user_prompt: str = "",
                          model: str = "") -> str:
    """Build the Ollama system prompt."""
    base = (
        f"You are a capable AI assistant with tools to create and manage files.\n"
        f"Working directory: {cwd}\n\n"
        "CRITICAL: You MUST use tool calls to take action. DO NOT just describe or explain "
        "commands — actually CALL the tools to execute them.\n"
        "- To run ANY shell/terminal/CLI command: call `execute_shell` with the command string.\n"
        "- To run Python code: call `execute_python` with the code string.\n"
        "- To create/write files: call `write_file` with filepath and content.\n"
        "- To read files: call `read_file` with the filepath.\n\n"
        "NEVER output a command in a code block without calling the tool. "
        "If the user asks you to DO something, USE the tools — don't just explain how.\n"
        "After each tool call, read the result and continue with the NEXT step "
        "until the ENTIRE task is complete. Do NOT stop after one step.\n"
        "Be EFFICIENT — complete tasks in as few tool calls as possible. "
        "Do not retry the same command more than twice if it fails.\n"
        "MULTI-STEP TASKS: When a task has multiple parts (e.g. 'go to X, search Y, "
        "screenshot Z'), you MUST complete ALL parts. Plan the steps first, then "
        "execute them one by one using tool calls. Do NOT stop until every part is done.\n"
        "Produce detailed, professional content. Never produce stubs or placeholders.\n"
        "IMPORTANT: This is a WINDOWS system. Use Windows commands "
        "(dir, type, copy, move, del, powershell) — NOT Linux commands "
        "(ls, cat, cp, mv, rm). For PowerShell, prefix with 'powershell -Command'.\n"
    )

    # Computer Use capability hint — peer of scripting, not a fallback.
    try:
        from helm.builtin_tools import is_computer_use_enabled
        if is_computer_use_enabled():
            _vision = ollama_model_supports_vision(model) if model else False
            base += (
                "\nDESKTOP CONTROL is available via computer_* tools (mouse, "
                "keyboard, screenshots, window manipulation, app launch, "
                "semantic pywinauto control). Treat them as a peer of "
                "scripting. Prefer them when scripts cannot reach the task. Broad classes:\n"
                "  - Any web app the user is already signed into — act in "
                "their real browser session, no API keys, no OAuth dance, "
                "no bot detection (social, email, banking, SaaS, internal "
                "tools, gov portals, etc.).\n"
                "  - Native desktop apps without a public scripting API.\n"
                "  - Anti-bot / captcha-walled web flows.\n"
                "  - Cross-app orchestration (drag/drop, OS dialogs, file "
                "pickers, print dialogs, clipboard hand-offs).\n"
                "  - Visual verification a script cannot do.\n"
                "Prefer computer_click_control / computer_type_in_control "
                "(semantic, no vision needed) over pixel coordinates for "
                "native Windows apps. Take computer_screenshot before "
                "clicking by pixel.\n"
            )
            if _vision:
                base += (
                    "VISION ACTIVE: You can see screenshots. After calling "
                    "computer_screenshot the image is attached automatically — "
                    "examine it to identify UI elements, read text, and verify "
                    "results before proceeding. WORKFLOW:\n"
                    "  1. computer_screenshot → see current state\n"
                    "  2. Identify target element by position/text in image\n"
                    "  3. computer_click at correct pixel coords (or use "
                    "computer_click_control for Win32 apps)\n"
                    "  4. computer_screenshot again to confirm result\n"
                    "Repeat see→act→verify until task is complete.\n"
                )
            else:
                base += (
                    "NOTE: Your model does not support vision. For computer use, "
                    "prefer semantic tools (computer_get_window_tree, "
                    "computer_click_control, computer_type_in_control) which work "
                    "without seeing the screen. Use computer_screenshot only when "
                    "you need to extract text (OCR will be attempted automatically).\n"
                    "For full Computer Use (vision + tool calling in one model), use "
                    "mistral-small3.1 — most other Ollama vision models (llama3.2-vision, "
                    "qwen2.5vl) cannot call tools.\n"
                )
    except Exception:
        logger.debug("Couldn't add the desktop-control note to the prompt", exc_info=True)

    if skill_content:
        base += (
            "\nThe following skill guide applies to this task:\n\n"
            f"{skill_content}\n"
        )
        # If the skill contains bash/shell commands, guide the model to use execute_shell
        if "```bash" in skill_content or "npx " in skill_content or "npm " in skill_content:
            base += (
                "\n[IMPORTANT — USE execute_shell FOR CLI COMMANDS]\n"
                "The skill guide above contains shell/terminal commands (e.g. npx, npm, CLI tools). "
                "Use the `execute_shell` tool to run these commands directly — do NOT wrap them "
                "in Python code or use execute_python for shell commands. "
                "Run each command step by step using execute_shell and read the output before proceeding.\n"
            )
            # Extra guidance for Playwright CLI multi-step workflows
            if "playwright" in skill_content.lower():
                base += (
                    "\nPLAYWRIGHT CLI WORKFLOW — follow these steps IN ORDER:\n"
                    "1. execute_shell: npx @playwright/cli open <url>\n"
                    "2. execute_shell: npx @playwright/cli snapshot  (to get element refs)\n"
                    "3. execute_shell: npx @playwright/cli fill <ref> \"<text>\"  (for search/input)\n"
                    "4. execute_shell: npx @playwright/cli press Enter  (to submit)\n"
                    "5. execute_shell: npx @playwright/cli snapshot  (to see results)\n"
                    "6. execute_shell: npx @playwright/cli screenshot  (to capture)\n"
                    "You MUST do snapshot BEFORE interacting — you need ref IDs from the snapshot.\n"
                    "Do NOT skip steps. Complete the ENTIRE workflow.\n"
                )
            base += "[END INSTRUCTIONS]\n"

    # Add MCP server info if any servers are running
    mgr = _get_mcp_manager()
    if mgr and mgr.has_running_servers():
        mcp_summary = mgr.get_system_prompt_summary()
        if mcp_summary:
            base += f"\n{mcp_summary}\n"

    # Inject shared AI memory (pass prompt for relevance scoring)
    try:
        from helm.memory import get_memory_block
        mem_block = get_memory_block(prompt=user_prompt)
        if mem_block:
            base += f"\n{mem_block}"
    except Exception:
        logger.debug("Couldn't add shared memory to the prompt", exc_info=True)

    # Inject user personalization and custom instructions
    try:
        from helm.personalization import get_personalization_block
        pblock = get_personalization_block()
        if pblock:
            base += f"\n{pblock}"
    except Exception:
        logger.debug("Couldn't add personalization to the prompt", exc_info=True)

    return base


def _screenshot_path_from_result(tool_result: str) -> str | None:
    """Extract file path from computer_screenshot tool result string."""
    m = re.search(r'Screenshot saved:\s*(.+?)\s+\(', tool_result)
    if m:
        p = m.group(1).strip()
        if pathlib.Path(p).exists():
            return p
    return None


def _screenshot_to_base64(tool_result: str) -> str | None:
    """Read screenshot PNG and return base64 string, or None on failure."""
    import base64
    p = _screenshot_path_from_result(tool_result)
    if not p:
        return None
    try:
        return base64.b64encode(pathlib.Path(p).read_bytes()).decode()
    except Exception:
        return None


def _screenshot_to_markitdown(tool_result: str) -> str | None:
    """Run markitdown on screenshot for non-vision model fallback (OCR/text extraction)."""
    import shutil
    p = _screenshot_path_from_result(tool_result)
    if not p:
        return None
    md_bin = shutil.which("markitdown")
    if not md_bin:
        return None
    try:
        result = subprocess.run(
            [md_bin, p],
            capture_output=True, text=True, timeout=30,
            **hidden_kwargs(),
        )
        if result.returncode == 0 and result.stdout.strip():
            return f"[Screenshot OCR via markitdown]\n{result.stdout.strip()[:3000]}"
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _append_screenshot_result(sess: dict, tool_result: str, model: str) -> None:
    """
    Append a screenshot tool result to ollama_messages.
    Vision models: keep minimal tool message + inject image as user message.
    Non-vision models: attempt markitdown OCR fallback, else plain text.
    """
    if ollama_model_supports_vision(model):
        b64 = _screenshot_to_base64(tool_result)
        if b64:
            sess["ollama_messages"].append({
                "role": "tool",
                "content": "Screenshot captured. Image follows.",
            })
            sess["ollama_messages"].append({
                "role": "user",
                "content": "[screenshot]",
                "images": [b64],
            })
            return
    # Non-vision or base64 failed — try markitdown OCR
    md_text = _screenshot_to_markitdown(tool_result)
    sess["ollama_messages"].append({
        "role": "tool",
        "content": md_text or tool_result,
    })


async def _run_ollama_agent(sess: dict, text: str, source: str, sid: str) -> str:
    """
    Ollama agentic loop via /api/chat with tool calling.

    Sends the user message together with tool definitions, executes any
    tool_calls the model returns, feeds results back, and repeats until the
    model gives a plain-text answer.  Falls back to the regular subprocess
    (ollama run) when the REST API is unreachable or the model does not
    support tools.
    """
    from helm.file_tracker import snapshot_dir, handle_diff
    from .core import run_ai_popen  # lazy to avoid circular import

    cwd   = sess["cwd"]
    model = sess.get("model") or _st.default_models.get("ollama", "") or os.environ.get("OLLAMA_MODEL", "")
    if not model:
        model = next(iter(await asyncio.to_thread(installed_models)), "")
    if not model:
        model = "qwen3:4b"

    tool_support = ollama_model_supports_tools(model)
    from helm.builtin_tools import is_computer_use_enabled
    _cu_on = is_computer_use_enabled()
    if tool_support is False:
        if _cu_on:
            # Computer Use needs BOTH vision + tools. On Ollama only the
            # mistral-small3.x family carries both tags; the popular vision
            # models (llama3.2-vision, qwen2.5vl, minicpm-v) are vision-only
            # and Ollama's /api/chat rejects any request that includes tools.
            await push_message(
                "system",
                f"⚠️ **{model}** is vision-capable but does NOT support tool calling on Ollama, "
                f"so Computer Use (and all file tools) cannot work with it.\n"
                f"Computer Use needs a model with BOTH vision **and** tools. "
                f"Switch via `/model` to **`mistral-small3.1`** (or `mistral-small3.2`), "
                f"then `ollama pull mistral-small3.1`.",
                source=source, session_id=sid,
            )
        else:
            await push_message(
                "system",
                f"⚠️ **{model}** does not support tool calling — file creation tools are disabled.\n"
                f"Switch to a compatible model (e.g. `qwen2.5-coder:7b`, `qwen3:4b`, `llama3.1:8b`) "
                f"via `/model` to enable tools.",
                source=source, session_id=sid,
            )
    elif tool_support is None:
        await push_message(
            "system",
            f"ℹ️ **{model}** — tool calling support unknown. "
            f"If file creation doesn't work, switch to `qwen2.5-coder:7b` or `llama3.1:8b`.",
            source=source, session_id=sid,
        )

    from helm.skills import _registry
    skill_name = detect_skill(text)
    skill_content = ""
    if skill_name:
        ai_specific = f"{sess['ai']}-{skill_name}" if sess.get("ai") else ""
        if ai_specific and ai_specific in _registry:
            skill_name = ai_specific
        skill_content = _registry.get(skill_name, {}).get("content", "")
        logger.info("Ollama skill injection (system prompt): skill=%s chars=%d",
                     skill_name, len(skill_content))

    system_content = _ollama_system_prompt(cwd, skill_content=skill_content,
                                            user_prompt=text, model=model)
    if not sess.get("ollama_messages"):
        sess["ollama_messages"] = [{"role": "system", "content": system_content}]
    else:
        if sess["ollama_messages"][0].get("role") == "system":
            sess["ollama_messages"][0]["content"] = system_content

    # ── Context window management ──
    # Trim old tool results to prevent context overflow on smaller models.
    # Keep the system prompt + last 6 messages intact; compress everything
    # in between by replacing long tool results with short summaries.
    _MAX_TOOL_RESULT_CHARS = 500
    _KEEP_RECENT = 6  # keep last N messages untouched
    msgs = sess["ollama_messages"]
    if len(msgs) > _KEEP_RECENT + 1:  # +1 for system prompt
        for i in range(1, len(msgs) - _KEEP_RECENT):
            msg = msgs[i]
            if msg.get("role") == "tool" and len(msg.get("content", "")) > _MAX_TOOL_RESULT_CHARS:
                # Summarise long tool results to save context space
                original = msg["content"]
                msgs[i] = {
                    "role": "tool",
                    "content": original[:200] + "\n...(truncated)...\n" + original[-200:],
                }
            elif msg.get("role") == "assistant" and len(msg.get("content", "")) > _MAX_TOOL_RESULT_CHARS:
                original = msg["content"]
                msgs[i] = {
                    "role": "assistant",
                    "content": original[:200] + "\n...(truncated)...\n" + original[-200:],
                }

    sess["ollama_messages"].append({"role": "user", "content": text})

    before       = await asyncio.to_thread(snapshot_dir, cwd)
    final_output = ""

    # Token tracking — accumulate across all iterations of the agent loop
    _total_prompt_tokens = 0
    _total_eval_tokens   = 0

    # Safety limit prevents runaway loops from smaller models that keep
    # retrying failed commands or taking unnecessary steps.
    _SAFETY_LIMIT = 30
    for _iteration in range(_SAFETY_LIMIT):
        active_tools = _build_ollama_tools()
        payload = {
            "model":   model,
            "messages": sess["ollama_messages"],
            "tools":   active_tools,
            "stream":  False,
        }

        try:
            data = await asyncio.to_thread(_chat, payload, 600)

        except urllib.error.URLError as exc:
            logger.warning("Ollama REST API unreachable (%s) — falling back to CLI", exc)
            cli_text = inject_skill_prefix(text, ai=sess.get("ai", "ollama"))
            cmd = _st.integrations["ollama"]["build_command"](
                cli_text, model=sess.get("model")
            )
            final_output = await asyncio.to_thread(
                run_ai_popen, cmd, cwd, "ollama", sess
            )
            break

        except Exception as exc:
            final_output = f"Ollama error: {exc}"
            logger.error(final_output)
            break

        api_error = data.get("error", "")
        if api_error:
            logger.warning(
                "Ollama API returned error (%s) — falling back to CLI", api_error
            )
            # "does not support tools" while Computer Use is on means the bare
            # CLI fallback has no computer/file tools — it would silently do
            # nothing useful. Tell the user to switch to a vision+tools model.
            if _cu_on and "does not support tools" in api_error.lower():
                await push_message(
                    "system",
                    f"⚠️ **{model}** rejected tool calls (`{api_error.strip()}`), so Computer Use "
                    f"cannot run. Switch via `/model` to **`mistral-small3.1`** "
                    f"(vision + tools) and `ollama pull mistral-small3.1`.",
                    source=source, session_id=sid,
                )
                final_output = (
                    f"Computer Use is unavailable: **{model}** does not support tool calling "
                    f"on Ollama. Use a vision+tools model like `mistral-small3.1`."
                )
                break
            cli_text = inject_skill_prefix(text, ai=sess.get("ai", "ollama"))
            cmd = _st.integrations["ollama"]["build_command"](
                cli_text, model=sess.get("model")
            )
            final_output = await asyncio.to_thread(
                run_ai_popen, cmd, cwd, "ollama", sess
            )
            break

        # Extract token counts from Ollama response
        _total_prompt_tokens += int(data.get("prompt_eval_count", 0))
        _total_eval_tokens   += int(data.get("eval_count", 0))

        msg        = data.get("message", {})
        tool_calls = msg.get("tool_calls") or []
        content    = (msg.get("content") or "").strip()

        if not tool_calls and content:
            tool_calls = _parse_content_tool_calls(content)
            if tool_calls:
                logger.info(
                    "Ollama: parsed %d tool call(s) from content text (model=%s)",
                    len(tool_calls), model,
                )
                content = ""

        sess["ollama_messages"].append(msg)

        if not tool_calls:
            final_output = content or "(no response)"
            break

        for tc in tool_calls:
            fn        = tc.get("function", {})
            tool_name = fn.get("name", "")
            tool_args = fn.get("arguments", {})

            if isinstance(tool_args, str):
                try:
                    tool_args = json.loads(tool_args)
                except Exception:
                    tool_args = {}

            await push_message(
                "system", f"🔧 `{tool_name}` — running…",
                source=source, session_id=sid,
            )

            tool_result = await _execute_ollama_tool(tool_name, tool_args, cwd)

            if tool_name == "computer_screenshot" and not tool_result.startswith("Error"):
                _append_screenshot_result(sess, tool_result, model)
            else:
                sess["ollama_messages"].append({
                    "role":    "tool",
                    "content": tool_result,
                })

            # Show success or error to the user based on actual result
            if tool_result.startswith("Error") or tool_result.startswith("Exit "):
                await push_message(
                    "system", f"❌ `{tool_name}` — failed",
                    source=source, session_id=sid,
                )
            else:
                await push_message(
                    "system", f"✅ `{tool_name}` — done",
                    source=source, session_id=sid,
                )

    else:
        # Loop exhausted — force a final summary by calling the model
        # one more time WITHOUT tools so it must produce a text response.
        logger.warning("Ollama agent loop hit %d-iteration safety limit — forcing summary",
                       _SAFETY_LIMIT)
        sess["ollama_messages"].append({
            "role": "user",
            "content": (
                "You have completed all the tool calls. Now provide a brief, "
                "friendly summary of everything you did and any files you created. "
                "Do NOT call any more tools — just reply with text."
            ),
        })
        try:
            _summary_payload = {
                "model":    model,
                "messages": sess["ollama_messages"],
                "stream":   False,
                # No "tools" key — forces text-only response
            }
            _summary_data = await asyncio.to_thread(_chat, _summary_payload, 120)
            _total_prompt_tokens += int(_summary_data.get("prompt_eval_count", 0))
            _total_eval_tokens   += int(_summary_data.get("eval_count", 0))
            _summary_msg = _summary_data.get("message", {})
            final_output = (_summary_msg.get("content") or "").strip()
            if _summary_msg:
                sess["ollama_messages"].append(_summary_msg)
        except Exception as exc:
            logger.error("Ollama summary call failed: %s", exc)

        if not final_output:
            # Absolute last resort — build a summary from the tool results
            _tool_names = [
                m.get("content", "")[:80]
                for m in sess.get("ollama_messages", [])
                if m.get("role") == "system" and "done" in m.get("content", "")
            ]
            final_output = "✅ All tasks completed successfully."

    after = await asyncio.to_thread(snapshot_dir, cwd)
    await handle_diff(before, after, source, cwd, session_id=sid)

    # Store actual token counts in session for record_usage_task to pick up
    if _total_prompt_tokens > 0 or _total_eval_tokens > 0:
        sess["_last_tokens"] = {
            "input": _total_prompt_tokens,
            "output": _total_eval_tokens,
        }
        logger.info("Ollama tokens: %d in + %d out = %d total",
                     _total_prompt_tokens, _total_eval_tokens,
                     _total_prompt_tokens + _total_eval_tokens)

    return final_output


async def run_ollama(ai: str, sess: dict, text: str, safe_text: str,
                     source: str, sid: str) -> str:
    """Run one message through the local Ollama agent and show its answer."""
    from helm.broadcast import push_thinking
    from helm.skill_creation import auto_create_skill_template
    from .core import _is_coherent_task, _is_failure, _self_heal_with_skill

    await push_thinking(True, ai, session_id=sid)
    skill_matched = detect_skill(text)
    output = await _run_ollama_agent(sess, safe_text, source, sid)
    await push_thinking(False, session_id=sid)
    if not _is_failure(output):
        await push_message("assistant", output, ai=ai, source=source, session_id=sid)
        if not skill_matched and _is_coherent_task(text):
            asyncio.create_task(
                asyncio.to_thread(auto_create_skill_template, text, "ollama", output)
            )
    else:
        # Clear conversation history after a failed turn so the next
        # request starts fresh — stale error context confuses the model.
        sess.pop("ollama_messages", None)
        # Self-healing: AI failed and no skill existed → ask Claude to create one
        if not skill_matched:
            healed = await _self_heal_with_skill(ai, sess, text, safe_text,
                                                 source, sid, output)
            if healed:
                return healed
    return output
