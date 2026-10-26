"""What happens to a message you send an AI: helm/ai_runner/core.py process_message.

These pin down today's behaviour before that code is split up
(docs/code-health-plan.md, step C1). They watch RAPR from the outside
(tests/core_harness.py), so moving the code shouldn't break them.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest  # noqa: E402

import helm.state as st  # noqa: E402
from helm.ai_runner.core import _SAFETY_PREAMBLE  # noqa: E402
from helm.session_mgr import record_usage_task  # noqa: E402


# ── Before anything runs ──────────────────────────────────────────────────

def test_without_a_session_nothing_runs(rapr):
    out = rapr.send("hello")
    assert out == "No active session. Create or resume a session first."
    assert rapr.messages() == [("system", out)]
    assert rapr.calls() == []


def test_a_stopped_session_doesnt_run(rapr):
    sess = rapr.session("codex")
    sess["status"] = "stopped"
    out = rapr.send("hello", sess)
    assert out.startswith("No active session")
    assert rapr.calls() == []


def test_a_busy_session_says_wait(rapr):
    sess = rapr.session("codex")

    async def while_busy():
        sess["_lock"] = asyncio.Lock()
        await sess["_lock"].acquire()
        from helm.ai_runner.core import process_message
        return await process_message("hello", session_id=sess["id"])

    out = asyncio.run(while_busy())
    assert "is already processing a task" in out
    assert rapr.calls() == []


def test_over_budget_the_ai_isnt_asked(rapr, monkeypatch):
    monkeypatch.setenv("BUDGET_DAILY_CODEX", "1")            # one minute a day
    sess = rapr.session("codex")
    record_usage_task("codex", 120.0)                         # two minutes used
    out = rapr.send("hello", sess)
    assert out.startswith("🚫 **Budget limit reached**")
    assert rapr.calls() == []


def test_near_budget_it_warns_and_runs(rapr, monkeypatch):
    monkeypatch.setenv("BUDGET_DAILY_CODEX", "10")
    sess = rapr.session("codex")
    record_usage_task("codex", 9 * 60.0)                      # 90% used
    rapr.reply("codex", "Done.")
    out = rapr.send("hello", sess)
    assert out == "Done."
    assert any("%" in c for r, c in rapr.messages("system"))
    assert len(rapr.calls("codex")) == 1


# ── A normal message ──────────────────────────────────────────────────────

def test_the_message_reaches_the_ai_with_the_file_safety_rule(rapr):
    sess = rapr.session("codex")
    rapr.reply("codex", "Done.")
    out = rapr.send("PINEAPPLE", sess)
    assert out == "Done."
    [call] = rapr.calls("codex")
    prompt = rapr.prompt(call)
    assert prompt.endswith(_SAFETY_PREAMBLE + "PINEAPPLE")
    assert call["cwd"] == sess["cwd"] and call["session"] == sess["id"]
    assert rapr.messages() == [("user", "PINEAPPLE"), ("assistant", "Done.")]


def test_after_a_message_the_session_is_idle_and_counted(rapr):
    sess = rapr.session("codex")
    rapr.send("hello", sess)
    rapr.send("again", sess)
    assert sess["busy"] is False and sess["task_start"] is None
    assert sess["task_count"] == 2
    assert sess["total_task_seconds"] > 0
    assert st.usage_stats["codex"]["seconds"] > 0
    states = rapr.events("state")
    assert any(s["sessions"] and s["sessions"][0].get("busy") for s in states)
    assert not states[-1]["sessions"][0].get("busy")


def test_the_session_is_freed_even_if_something_breaks(rapr, monkeypatch):
    import helm.file_tracker as ft

    def broken(*a, **k):
        raise RuntimeError("disk on fire")
    monkeypatch.setattr(ft, "snapshot_dir", broken)
    sess = rapr.session("codex")
    sess["_lock"] = asyncio.Lock()
    with pytest.raises(RuntimeError):
        rapr.send("hello", sess)
    assert sess["busy"] is False
    assert not sess["_lock"].locked()


# ── /model ────────────────────────────────────────────────────────────────

def test_model_switch_is_remembered_and_passed_to_the_cli(rapr):
    from helm.model_prefs import get_model_pref
    sess = rapr.session("codex")
    out = rapr.send("/model gpt-test-1", sess)
    assert out == "✅ Codex model switched to `gpt-test-1`."
    assert sess["model"] == "gpt-test-1" and get_model_pref("codex") == "gpt-test-1"
    assert rapr.calls() == []                                 # a command, not a prompt
    rapr.send("hello", sess)
    argv = rapr.calls("codex")[0]["argv"]
    assert argv[argv.index("--model") + 1] == "gpt-test-1"
    out = rapr.send("/model default", sess)
    assert out == "✅ Model reset to default for Codex."
    assert sess["model"] is None and not get_model_pref("codex")


def test_model_list_shows_the_live_models(rapr, monkeypatch):
    import helm.web_routes.helpers as helpers
    monkeypatch.setattr(helpers, "_fetch_openai_models", lambda: ["gpt-a", "gpt-b"])
    sess = rapr.session("codex", model="gpt-b")
    out = rapr.send("/model", sess)
    assert "**Current model:** `gpt-b`" in out
    assert "  • `gpt-a`\n  • `gpt-b` ✅" in out


def test_model_list_when_it_cant_be_fetched(rapr, monkeypatch):
    import helm.web_routes.helpers as helpers

    def offline():
        raise OSError("offline")
    monkeypatch.setattr(helpers, "_fetch_openai_models", offline)
    out = rapr.send("/model list", rapr.session("codex"))
    assert "Could not fetch a live model list" in out


def test_model_isnt_switchable_for_the_shell(rapr):
    out = rapr.send("/model x", rapr.session("shell"))
    assert out.startswith("ℹ️ **Model switching is not available for Shell.**")


def test_ollama_model_switch_warns_when_not_installed(rapr, monkeypatch):
    import helm.ai_runner.ollama as ollama
    import helm.web_routes.helpers as helpers
    monkeypatch.setattr(ollama, "installed_models", lambda: ["qwen3:4b"])
    monkeypatch.setattr(helpers, "_fetch_ollama_models", lambda: ["qwen3:4b"])
    sess = rapr.session("ollama")
    out = rapr.send("/model llama9", sess)
    assert out == "✅ Model switched to `llama9`." and sess["model"] == "llama9"
    assert any("is not installed locally" in c for _, c in rapr.messages("system"))
    out = rapr.send("/model", sess)
    assert "**Current model:** `llama9`" in out and "  • `qwen3:4b`" in out
    out = rapr.send("/model default", sess)
    assert out.startswith("✅ Model reset to default") and sess["model"] is None


# ── /remember ─────────────────────────────────────────────────────────────

def test_remember_saves_a_memory_with_an_optional_category(rapr):
    sess = rapr.session("codex")
    assert rapr.send("/remember the build uses uv", sess) == "🧠 Remembered: **[fact]** the build uses uv"
    assert rapr.send("/remember preference: dark mode", sess) == \
        "🧠 Remembered: **[preference]** dark mode"
    listing = rapr.send("/remember list", sess)
    assert "**[fact]** the build uses uv" in listing and "**[preference]** dark mode" in listing
    assert rapr.calls() == []


def test_remember_with_nothing_saved_and_help(rapr):
    sess = rapr.session("codex")
    assert rapr.send("/remember", sess).startswith("🧠 No memories saved yet.")
    assert rapr.send("/remember help", sess).startswith("🧠 **Memory Commands:**")


def test_a_memory_is_given_to_the_ai(rapr):
    sess = rapr.session("codex")
    rapr.send("/remember MANGO is the project codename", sess)
    rapr.send("what is the codename?", sess)
    assert "MANGO is the project codename" in rapr.prompt(rapr.calls("codex")[0])


# ── /pipeline and the crew suggestion ─────────────────────────────────────

def test_pipeline_without_a_task_explains_itself(rapr):
    out = rapr.send("/pipeline", rapr.session("codex"))
    assert out.startswith("📋 **Pipeline Mode**")


def test_pipeline_plans_the_task(rapr, monkeypatch):
    import helm.pipeline.planner as planner
    seen = {}

    async def plan(prompt, session_id, cwd, planner_ai):
        seen.update(prompt=prompt, planner_ai=planner_ai)
        return {"id": "p1", "steps": [
            {"title": "Research", "assigned_ai": "gemini", "depends_on": []},
            {"title": "Write", "assigned_ai": "claude", "depends_on": ["s1"]},
        ]}
    monkeypatch.setattr(planner, "plan_pipeline", plan)
    out = rapr.send("/pipeline research and write", rapr.session("codex"))
    assert seen == {"prompt": "research and write", "planner_ai": "claude"}
    assert out.startswith("📋 **Pipeline plan ready** — 2 steps")
    assert "  1. **Research** → gemini\n  2. **Write** → claude (after s1)" in out
    assert "p1" in st.pipelines


def test_pipeline_planning_failure_is_explained(rapr, monkeypatch):
    import helm.pipeline.planner as planner

    async def plan(**kw):
        raise RuntimeError("planner down")
    monkeypatch.setattr(planner, "plan_pipeline", plan)
    out = rapr.send("/pipeline do things", rapr.session("codex"))
    assert out.startswith("❌ **Pipeline planning failed**") and "planner down" in out


def test_a_big_task_suggests_the_crew_and_still_runs(rapr, monkeypatch):
    import helm.pipeline.planner as planner
    monkeypatch.setenv("PIPELINE_AUTO_SUGGEST", "1")
    monkeypatch.setattr(planner, "looks_complex", lambda text: True)
    sess = rapr.session("codex")
    rapr.send("research, build and ship it", sess)
    assert sess["crew_prompt"] == "research, build and ship it"
    assert rapr.events("crew_suggest") == [{"type": "crew_suggest", "session_id": sess["id"]}]
    assert len(rapr.calls("codex")) == 1


# ── Skill guides and background looks ─────────────────────────────────────

SKILL_TASK = "organize files in my downloads folder"


def test_a_matching_skill_guide_is_added(rapr):
    import helm.skills as sk
    sk.reload_registry()
    if "file-organizer" not in sk._registry:
        pytest.skip("bundled skills not found")
    sess = rapr.session("codex")
    rapr.send(SKILL_TASK, sess)
    assert "HQ SKILL: file-organizer" in rapr.prompt(rapr.calls("codex")[0])


def test_a_background_look_gets_no_skill_guide(rapr):
    import helm.skills as sk
    sk.reload_registry()
    sess = rapr.session("codex")
    sess["read_only"] = True
    rapr.send(SKILL_TASK, sess)
    assert "HQ SKILL" not in rapr.prompt(rapr.calls("codex")[0])
