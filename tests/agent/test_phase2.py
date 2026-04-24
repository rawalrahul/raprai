import sys, os, asyncio, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
import helm.state as _st
from helm.agent.models import make_agent, make_node, make_run
from helm.agent.executor import execute_agent_run

def test_run_timeout_marks_run_failed():
    node = make_node("Slow", "sleep 10", node_type="shell")
    node["timeout"] = 30
    agent = make_agent("Timeout Test", nodes=[node])
    agent["run_timeout"] = 0.1
    agent["id"] = "ag-timeout-test"
    _st.agents[agent["id"]] = agent

    run = make_run(agent, trigger="ui")
    _st.agent_runs[run["id"]] = run

    asyncio.run(execute_agent_run(run["id"]))
    assert run["status"] == "failed"
    assert run.get("timed_out") is True


from helm.agent.context import substitute_vars, extract_var_assignments

def test_substitute_vars_replaces_placeholder():
    run = {"vars": {"city": "Delhi", "role": "Python Dev"}}
    prompt = "Find {{var:role}} jobs in {{var:city}}"
    result = substitute_vars(prompt, run)
    assert result == "Find Python Dev jobs in Delhi"

def test_substitute_vars_missing_key_leaves_placeholder():
    run = {"vars": {}}
    prompt = "Hello {{var:name}}"
    result = substitute_vars(prompt, run)
    assert "{{var:name}}" in result

def test_extract_var_assignments():
    output = "I found 5 jobs.\nSET_VAR: count = 5\nSET_VAR: city = Mumbai"
    assignments = extract_var_assignments(output)
    assert assignments == {"count": "5", "city": "Mumbai"}

def test_extract_var_assignments_none():
    output = "Nothing special here"
    assert extract_var_assignments(output) == {}


from helm.agent.nodes.transform import execute_transform_node

def test_transform_json_extract():
    node = make_node("Extract", "", node_type="transform")
    node["transform_op"] = "json_extract"
    node["transform_key"] = "name"
    result = asyncio.run(
        execute_transform_node(node, context='{"name": "Rahul", "age": 30}')
    )
    assert result == "Rahul"

def test_transform_regex_extract():
    node = make_node("Regex", "", node_type="transform")
    node["transform_op"] = "regex_extract"
    node["transform_pattern"] = r"\d+"
    result = asyncio.run(
        execute_transform_node(node, context="There are 42 results found")
    )
    assert result == "42"

def test_transform_template():
    node = make_node("Template", "Hello {{input}}, welcome", node_type="transform")
    node["transform_op"] = "template"
    result = asyncio.run(
        execute_transform_node(node, context="Rahul")
    )
    assert "Hello Rahul" in result

def test_transform_truncate():
    node = make_node("Truncate", "", node_type="transform")
    node["transform_op"] = "truncate"
    node["transform_length"] = 10
    result = asyncio.run(
        execute_transform_node(node, context="Hello World this is long")
    )
    assert len(result) <= 10

def test_transform_missing_op():
    node = make_node("Bad", "", node_type="transform")
    result = asyncio.run(
        execute_transform_node(node, context="anything")
    )
    assert "error" in result.lower()

def test_shell_node_var_substitution():
    """Var substitution should work in shell node task text."""
    from helm.agent.context import substitute_vars
    run = {"vars": {"output_dir": "/tmp/results"}}
    task = "mkdir -p {{var:output_dir}}"
    result = substitute_vars(task, run)
    assert result == "mkdir -p /tmp/results"


from helm.agent.nodes.input_node import extract_file_text_from_telegram

def test_extract_file_text_returns_none_for_no_file():
    result = asyncio.run(
        extract_file_text_from_telegram(file_id=None, mime_type=None, bot=None)
    )
    assert result is None

def test_extract_file_text_unsupported_mime():
    result = asyncio.run(
        extract_file_text_from_telegram(file_id="abc", mime_type="image/png", bot=None)
    )
    assert result is None


from helm.agent.executor import _build_failure_summary

def test_build_failure_summary_lists_failed_nodes():
    nodes = [
        {"title": "Step 1", "status": "completed", "error": None},
        {"title": "Step 2", "status": "failed", "error": "HTTP 500"},
        {"title": "Step 3", "status": "skipped", "error": None},
    ]
    summary = _build_failure_summary(nodes)
    assert "Step 2" in summary
    assert "HTTP 500" in summary
    assert "Step 1" not in summary

def test_build_failure_summary_no_failures():
    nodes = [{"title": "Step 1", "status": "completed", "error": None}]
    summary = _build_failure_summary(nodes)
    assert summary == ""


from helm.agent.nodes.shell import execute_shell_node

def test_shell_node_env_var_injection():
    cmd = "echo %MY_SECRET_KEY%" if sys.platform == "win32" else "echo $MY_SECRET_KEY"
    node = make_node("Env Test", cmd, node_type="shell")
    node["env_vars"] = {"MY_SECRET_KEY": "super_secret_123"}
    result = asyncio.run(
        execute_shell_node(node, context="", cwd=".")
    )
    assert "super_secret_123" in result

def test_shell_node_env_var_not_in_task():
    """Env vars must not appear in task text — they're injected separately."""
    cmd = "echo %MY_KEY%" if sys.platform == "win32" else "echo $MY_KEY"
    node = make_node("Safe", cmd, node_type="shell")
    node["env_vars"] = {"MY_KEY": "abc"}
    assert "abc" not in node["task"]


from helm.agent.nodes.join import execute_join_node

def test_join_node_merges_parent_outputs():
    parent_a = make_node("Branch A", "result A", node_id="pa")
    parent_a["output"] = "Result from Branch A"
    parent_b = make_node("Branch B", "result B", node_id="pb")
    parent_b["output"] = "Result from Branch B"
    join = make_node("Join", "", node_type="join", node_id="jn")
    join["children"] = []
    parent_a["children"] = ["jn"]
    parent_b["children"] = ["jn"]

    # In actual run, build_node_context would be called.
    # We simulate the merged context here.
    context = "Result from Branch A\n\nResult from Branch B"
    result = asyncio.run(
        execute_join_node(join, context=context)
    )
    assert "Result from Branch A" in result
    assert "Result from Branch B" in result


from helm.agent.runner import trigger_agent_run
from unittest.mock import patch, AsyncMock

def test_schedule_trigger_uses_static_input():
    node = make_node("Step", "analyze")
    agent = make_agent("Sched Agent", nodes=[node])
    agent["id"] = "ag-sched-test"
    agent["trigger"]["schedule"]["input_data"] = "My saved resume text"
    _st.agents[agent["id"]] = agent

    with patch("helm.agent.executor.execute_agent_run", new_callable=AsyncMock):
        run = asyncio.run(
            trigger_agent_run(agent["id"], trigger="schedule")
        )
    assert run["input_data"] == "My saved resume text"


from helm.agent.executor import _expand_loop_children

def test_expand_loop_children_creates_clones():
    """After loop node completes with 3 items, 3 child clones should exist."""
    loop_node = make_node("Loop", "", node_type="loop", node_id="loop1")
    child = make_node("Process Item", "analyze {{loop_item}}", node_id="child1")
    loop_node["children"] = ["child1"]
    loop_node["output"] = "1. Python Developer\n2. Data Scientist\n3. ML Engineer"
    loop_node["status"] = "completed"

    nodes = [loop_node, child]
    new_nodes = _expand_loop_children(loop_node, nodes)

    # Original child replaced by 3 clones
    clone_ids = [n["id"] for n in new_nodes if n["id"] != "loop1"]
    assert len(clone_ids) == 3
    # Each clone has _loop_item set
    clones = [n for n in new_nodes if n.get("_loop_item")]
    assert len(clones) == 3
    items = [n["_loop_item"] for n in clones]
    assert "Python Developer" in items


from helm.agent.executor import _is_final_worker_node

def test_final_worker_node_detects_only_non_manager_leaf_nodes():
    first = make_node("First", "do first", node_id="first")
    final = make_node("Final", "write report", node_id="final")
    manager = make_node("Manager", "review", node_type="manager", node_id="manager")
    first["children"] = ["final"]
    final["children"] = []
    manager["children"] = ["first", "final"]
    run = {"nodes": [first, final, manager]}
    assert _is_final_worker_node(run, first) is False
    assert _is_final_worker_node(run, final) is True
    assert _is_final_worker_node(run, manager) is False


def test_telegram_final_output_sends_only_leaf_node():
    from helm.agent.executor import _send_final_node_output_to_telegram

    class FakeBot:
        def __init__(self):
            self.messages = []

        async def send_message(self, **kwargs):
            self.messages.append(kwargs)

    class FakeApp:
        def __init__(self):
            self.bot = FakeBot()

    old_app = _st.telegram_app
    old_chat_id = _st.telegram_chat_id
    app = FakeApp()
    try:
        _st.telegram_app = app
        _st.telegram_chat_id = 12345

        first = make_node("First", "do first", node_id="first")
        final = make_node("Final", "write report", node_id="final")
        manager = make_node("Manager", "review", node_type="manager", node_id="manager")
        first["children"] = ["final"]
        first["output"] = "intermediate output"
        final["output"] = "final output"
        manager["children"] = ["first", "final"]
        run = {"trigger": "ui", "nodes": [first, final, manager]}

        asyncio.run(_send_final_node_output_to_telegram(run, first))
        asyncio.run(_send_final_node_output_to_telegram(run, final))
    finally:
        _st.telegram_app = old_app
        _st.telegram_chat_id = old_chat_id

    assert len(app.bot.messages) == 1
    assert app.bot.messages[0]["chat_id"] == 12345
    assert "Final output - Final" in app.bot.messages[0]["text"]
    assert "final output" in app.bot.messages[0]["text"]
    assert "intermediate output" not in app.bot.messages[0]["text"]


def test_telegram_final_output_skips_telegram_deliver_node_to_avoid_duplicate():
    from helm.agent.executor import _send_final_node_output_to_telegram

    class FakeBot:
        def __init__(self):
            self.messages = []

        async def send_message(self, **kwargs):
            self.messages.append(kwargs)

    class FakeApp:
        def __init__(self):
            self.bot = FakeBot()

    old_app = _st.telegram_app
    old_chat_id = _st.telegram_chat_id
    app = FakeApp()
    try:
        _st.telegram_app = app
        _st.telegram_chat_id = 12345

        deliver = make_node("Deliver", "", node_type="deliver", node_id="deliver")
        deliver["deliver_channel"] = "telegram"
        deliver["output"] = "OK: delivered 12 chars to Telegram chat 12345"
        run = {"trigger": "telegram", "nodes": [deliver]}

        asyncio.run(_send_final_node_output_to_telegram(run, deliver))
    finally:
        _st.telegram_app = old_app
        _st.telegram_chat_id = old_chat_id

    assert app.bot.messages == []


def test_telegram_final_output_sends_final_file_artifact():
    from helm.agent.executor import _send_final_node_output_to_telegram
    import pathlib
    import shutil

    class FakeBot:
        def __init__(self):
            self.messages = []
            self.documents = []

        async def send_message(self, **kwargs):
            self.messages.append(kwargs)

        async def send_document(self, **kwargs):
            self.documents.append({
                "chat_id": kwargs["chat_id"],
                "name": pathlib.Path(kwargs["document"].name).name,
                "caption": kwargs.get("caption", ""),
            })

    class FakeApp:
        def __init__(self):
            self.bot = FakeBot()

    tmp_path = pathlib.Path(os.getcwd()) / f"pytest-agent-telegram-file-{time.time_ns()}"
    tmp_path.mkdir()
    final_file = tmp_path / "final_post.html"
    old_app = _st.telegram_app
    old_chat_id = _st.telegram_chat_id
    app = FakeApp()
    try:
        final_file.write_text("<h1>Final post</h1>", encoding="utf-8")
        _st.telegram_app = app
        _st.telegram_chat_id = 12345

        final = make_node("Final", "create html", node_id="final")
        final["status"] = "completed"
        final["output"] = "Created final_post.html"
        run = {
            "trigger": "ui",
            "nodes": [final],
            "_generated_files": [str(final_file)],
            "_generated_files_by_node": {"final": [str(final_file)]},
        }

        asyncio.run(_send_final_node_output_to_telegram(run, final))
    finally:
        _st.telegram_app = old_app
        _st.telegram_chat_id = old_chat_id
        shutil.rmtree(tmp_path, ignore_errors=True)

    assert len(app.bot.messages) == 1
    assert len(app.bot.documents) == 1
    assert app.bot.documents[0]["chat_id"] == 12345
    assert app.bot.documents[0]["name"] == "final_post.html"
    assert "final_post.html" in app.bot.documents[0]["caption"]


def test_cleanup_intermediate_generated_files_preserves_final_leaf_output():
    from helm.agent.executor import _cleanup_intermediate_generated_files
    import pathlib
    import shutil

    tmp_path = pathlib.Path(os.getcwd()) / f"pytest-agent-cleanup-{time.time_ns()}"
    tmp_path.mkdir()
    intermediate = tmp_path / "scratch.py"
    final_output = tmp_path / "Final_Report.md"
    preexisting = tmp_path / "keep_existing.txt"
    try:
        intermediate.write_text("temporary script", encoding="utf-8")
        final_output.write_text("final report", encoding="utf-8")
        preexisting.write_text("not generated by workflow", encoding="utf-8")

        first = make_node("Scratch", "make scratch", node_id="first")
        first["status"] = "completed"
        final = make_node("Final", "make final", node_id="final")
        final["status"] = "completed"
        first["children"] = ["final"]
        run = {
            "id": "run-cleanup-leaf",
            "nodes": [first, final],
            "_workflow_cwds": [str(tmp_path)],
            "_generated_files": [str(intermediate), str(final_output)],
            "_final_output_files": [str(final_output)],
            "_generated_files_by_node": {
                "first": [str(intermediate)],
                "final": [str(final_output)],
            },
        }

        deleted = asyncio.run(_cleanup_intermediate_generated_files(run))

        assert str(intermediate.resolve()) in deleted
        assert not intermediate.exists()
        assert final_output.exists()
        assert preexisting.exists()
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_cleanup_preserves_final_leaf_generated_script_when_expected_output():
    from helm.agent.executor import _cleanup_intermediate_generated_files
    import pathlib
    import shutil

    tmp_path = pathlib.Path(os.getcwd()) / f"pytest-agent-cleanup-{time.time_ns()}"
    tmp_path.mkdir()
    scratch = tmp_path / "scratch.json"
    final_script = tmp_path / "deliverable_script.py"
    try:
        scratch.write_text("scratch", encoding="utf-8")
        final_script.write_text("print('deliverable')", encoding="utf-8")

        first = make_node("Scratch", "make scratch", node_id="first")
        first["status"] = "completed"
        final = make_node("Final Script", "create final script", node_id="final")
        final["status"] = "completed"
        first["children"] = ["final"]
        run = {
            "id": "run-cleanup-script",
            "nodes": [first, final],
            "_workflow_cwds": [str(tmp_path)],
            "_generated_files": [str(scratch), str(final_script)],
            "_generated_files_by_node": {
                "first": [str(scratch)],
                "final": [str(final_script)],
            },
        }

        deleted = asyncio.run(_cleanup_intermediate_generated_files(run))

        assert str(scratch.resolve()) in deleted
        assert not scratch.exists()
        assert final_script.exists()
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_persist_final_text_output_creates_output_file_and_cleanup_removes_script():
    from helm.agent.executor import _cleanup_intermediate_generated_files, _persist_final_text_output
    import pathlib
    import shutil

    tmp_path = pathlib.Path(os.getcwd()) / f"pytest-agent-cleanup-{time.time_ns()}"
    tmp_path.mkdir()
    script = tmp_path / "searchnews.py"
    try:
        script.write_text("print('helper')", encoding="utf-8")

        draft = make_node("Draft LinkedIn Post", "draft", node_id="draft")
        draft["status"] = "completed"
        deliver = make_node("Final Delivery", "", node_type="deliver", node_id="deliver")
        deliver["status"] = "completed"
        deliver["deliver_channel"] = "terminal"
        draft["children"] = ["deliver"]

        run = {
            "id": "run-linkedin-test",
            "agent_name": "LinkedIn Content Generator",
            "nodes": [draft, deliver],
            "_workflow_cwds": [str(tmp_path)],
            "_generated_files": [str(script)],
            "_generated_files_by_node": {"draft": [str(script)]},
        }

        output_path = asyncio.run(
            _persist_final_text_output(
                run,
                deliver,
                str(tmp_path),
                "Here is the final LinkedIn post.",
            )
        )
        deleted = asyncio.run(_cleanup_intermediate_generated_files(run))

        assert output_path
        final_file = pathlib.Path(output_path)
        assert final_file.exists()
        assert "Here is the final LinkedIn post." in final_file.read_text(encoding="utf-8")
        assert str(script.resolve()) in deleted
        assert not script.exists()
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_cleanup_runs_after_workflow_output_before_manager_review():
    from helm.agent.executor import _cleanup_after_workflow_outputs
    import pathlib
    import shutil

    tmp_path = pathlib.Path(os.getcwd()) / f"pytest-agent-cleanup-{time.time_ns()}"
    tmp_path.mkdir()
    script = tmp_path / "generate_news_report.py"
    data = tmp_path / "trending_ai_news_2026.json"
    final_output = tmp_path / "linkedin_content_generator_final_delivery.txt"
    try:
        script.write_text("print('helper')", encoding="utf-8")
        data.write_text('{"items": []}', encoding="utf-8")
        final_output.write_text("final LinkedIn post", encoding="utf-8")

        topic = make_node("Topic Selection", "topic", node_id="topic")
        topic["status"] = "completed"
        draft = make_node("Draft LinkedIn Post", "draft", node_id="draft")
        draft["status"] = "completed"
        deliver = make_node("Final Delivery", "", node_type="deliver", node_id="deliver")
        deliver["status"] = "completed"
        deliver["deliver_channel"] = "ui"
        manager = make_node("Manager Review", "review", node_type="manager", node_id="manager")
        manager["status"] = "pending"
        topic["children"] = ["draft"]
        draft["children"] = ["deliver"]
        manager["children"] = ["topic", "draft", "deliver"]
        run = {
            "id": "run-cleanup-before-manager",
            "nodes": [topic, draft, deliver, manager],
            "_workflow_cwds": [str(tmp_path)],
            "_generated_files": [str(script), str(data), str(final_output)],
            "_final_output_files": [str(final_output)],
            "_generated_files_by_node": {
                "topic": [str(data)],
                "draft": [str(script)],
                "deliver": [str(final_output)],
            },
        }

        asyncio.run(_cleanup_after_workflow_outputs(run))

        assert not script.exists()
        assert not data.exists()
        assert final_output.exists()
        assert run["_workflow_output_cleanup_done"] is True
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_cleanup_intermediate_generated_files_preserves_delivered_parent_output():
    from helm.agent.executor import _cleanup_intermediate_generated_files
    import pathlib
    import shutil

    tmp_path = pathlib.Path(os.getcwd()) / f"pytest-agent-cleanup-{time.time_ns()}"
    tmp_path.mkdir()
    scratch = tmp_path / "scratch.json"
    final_output = tmp_path / "final.md"
    try:
        scratch.write_text("scratch", encoding="utf-8")
        final_output.write_text("final", encoding="utf-8")

        first = make_node("Scratch", "make scratch", node_id="first")
        first["status"] = "completed"
        final_file = make_node("Final File", "make final", node_type="file", node_id="final_file")
        final_file["status"] = "completed"
        final_file["file_op"] = "write"
        final_file["file_path"] = str(final_output)
        deliver = make_node("Deliver", "", node_type="deliver", node_id="deliver")
        deliver["status"] = "completed"
        first["children"] = ["final_file"]
        final_file["children"] = ["deliver"]

        run = {
            "id": "run-cleanup-deliver",
            "nodes": [first, final_file, deliver],
            "_workflow_cwds": [str(tmp_path)],
            "_generated_files": [str(scratch), str(final_output)],
            "_generated_files_by_node": {
                "first": [str(scratch)],
                "final_file": [str(final_output)],
            },
        }

        deleted = asyncio.run(_cleanup_intermediate_generated_files(run))

        assert str(scratch.resolve()) in deleted
        assert not scratch.exists()
        assert final_output.exists()
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


from helm.agent.nodes.manager import focus_manager_session, parse_manager_reply, is_approval

def test_is_approval_yes():
    assert is_approval("yes") is True
    assert is_approval("YES") is True
    assert is_approval("looks good") is True
    assert is_approval("approved") is True
    assert is_approval("lgtm") is True

def test_is_approval_negative():
    assert is_approval("no, the jobs are too senior") is False
    assert is_approval("the results are wrong") is False
    assert is_approval("missing salary info") is False

def test_parse_manager_reply_returns_feedback():
    reply = "The job titles are too senior, I need junior roles"
    feedback = parse_manager_reply(reply)
    assert feedback["approved"] is False
    assert "junior" in feedback["feedback"].lower()


def test_focus_manager_session_sets_focused_waiting_session():
    from helm.agent.nodes import input_node

    old_sessions = dict(_st.sessions)
    old_focused = _st.focused_id
    old_pending = dict(input_node._pending_input_sessions)
    try:
        _st.sessions.clear()
        _st.focused_id = None
        input_node._pending_input_sessions.clear()
        run = {
            "id": "run-manager-focus",
            "agent_id": "ag-manager-focus",
            "agent_name": "Manager Focus Test",
            "session_id": None,
        }
        node = make_node("Manager Review", "Review output", node_type="manager")

        sess = asyncio.run(focus_manager_session(node, run, summary="Step output"))

        assert _st.focused_id == sess["id"]
        assert sess["name"] == "Manager Focus Test"
        assert node["session_id"] == sess["id"]
        assert run["manager_session_id"] == sess["id"]
        assert sess["agent_manager"] is True
        assert sess["agent_manager_waiting_run_id"] == run["id"]
        assert input_node._pending_input_sessions[sess["id"]] == (run["id"], node["id"])
    finally:
        _st.sessions.clear()
        _st.sessions.update(old_sessions)
        _st.focused_id = old_focused
        input_node._pending_input_sessions.clear()
        input_node._pending_input_sessions.update(old_pending)


def test_input_node_wait_uses_run_session_not_manager_session():
    from unittest.mock import AsyncMock, patch
    from helm.agent.nodes import input_node
    from helm.agent.nodes.input_node import execute_input_node, resume_run

    old_sessions = dict(_st.sessions)
    old_focused = _st.focused_id
    old_pending = dict(input_node._pending_input_sessions)
    try:
        _st.sessions.clear()
        _st.focused_id = "main-session"
        _st.sessions["main-session"] = {
            "id": "main-session",
            "name": "Main",
            "cwd": ".",
            "ai": "claude",
            "status": "idle",
            "last_used": 0,
        }
        run = {
            "id": "run-input-direct",
            "agent_id": "ag-input-direct",
            "agent_name": "Input Direct Test",
            "session_id": "main-session",
            "nodes": [
                make_node("Needs Input", "Please provide details", node_type="input", node_id="input"),
                make_node("Manager", "Review", node_type="manager", node_id="manager"),
            ],
        }
        node = run["nodes"][0]

        async def _exercise():
            task = asyncio.create_task(execute_input_node(node, run, context=""))
            await asyncio.sleep(0)
            assert input_node._pending_input_sessions["main-session"] == (run["id"], node["id"])
            assert run.get("manager_session_id") is None
            assert _st.focused_id == "main-session"
            assert resume_run(run["id"], "resume text") is True
            return await task

        with patch("helm.broadcast.broadcast", new_callable=AsyncMock), patch(
            "helm.broadcast.push_message", new_callable=AsyncMock
        ):
            result = asyncio.run(_exercise())
        assert result == "resume text"
    finally:
        _st.sessions.clear()
        _st.sessions.update(old_sessions)
        _st.focused_id = old_focused
        input_node._pending_input_sessions.clear()
        input_node._pending_input_sessions.update(old_pending)
