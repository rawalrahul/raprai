"""A throwaway group-chat world for the group-chat tests: fake AI CLIs, a
temporary store, and no real Claude (so summaries come from the fake AIs)."""
import os
import sys
import textwrap

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.groupchat as gc  # noqa: E402
import helm.state as _st  # noqa: E402
from helm.groupchat_context import budget, summariser  # noqa: E402

# `python fake_ai.py <behaviour> <prompt>` (or the prompt on stdin) prints a reply.
FAKE_AI = textwrap.dedent('''
    import sys, time
    mode = sys.argv[1]
    prompt = sys.argv[2] if len(sys.argv) > 2 else sys.stdin.read()
    head = prompt.split("Write your next")[0]
    if mode == "pass":
        print("(pass)")
    elif mode == "slow":
        time.sleep(30)
        print("too late")
    elif mode == "pinger":
        print("(pass)" if "Alpha asks @Beta" in head else "Alpha asks @Beta to check")
    elif mode == "echo-last":
        convo = head.strip().splitlines()
        last = [l for l in convo if l.strip() and not l.startswith("---")][-1]
        print("Beta saw -> " + last)
    elif mode == "writer":
        # The summariser: echoes the first message it was given, keeps facts.
        if "Merge these consecutive summaries" in prompt:
            print("TOPIC: merged part\\nSUMMARY:\\n- merged summary\\nFACTS:\\n- Budget is $500")
        else:
            first = [l for l in prompt.splitlines() if l.startswith(("User:", "Alpha:", "Beta:"))][0]
            print("TOPIC: early talk\\nSUMMARY:\\n- " + first[:40] + "\\nFACTS:\\n- Budget is $500\\n- Alpha: write the tests")
    elif mode == "recaller":
        # Asks for b1 once; then reports what it was shown.
        if "Details you asked for" in prompt:
            print("got it: " + ("SECRET-42" if "SECRET-42" in prompt else "nothing"))
        else:
            print("(recall b1)")
    elif mode == "nested-recall":
        print("(recall b1)")
    else:
        print(mode + " says hi")
''')


@pytest.fixture
def env(tmp_path, monkeypatch):
    script = tmp_path / "fake_ai.py"
    script.write_text(FAKE_AI)

    def integration(mode, stdin=False):
        if stdin:
            build = lambda prompt, model=None: [sys.executable, str(script), mode]  # noqa: E731
        else:
            build = lambda prompt, model=None: [sys.executable, str(script), mode, prompt]  # noqa: E731
        return {"name": mode, "emoji": "🤖", "color": "#123456", "build_command": build,
                "stdin_prompt": stdin}

    monkeypatch.setattr(_st, "integrations", {}, raising=False)
    monkeypatch.setattr(_st, "sessions", {}, raising=False)
    monkeypatch.setattr(gc, "groups", {})
    monkeypatch.setattr(gc, "_loaded", True)
    monkeypatch.setattr(gc, "_store_path", lambda: tmp_path / "group_chats.json")
    monkeypatch.setattr(summariser, "claude_installed", lambda: False)
    for var in ("GROUP_SUMMARISER", "GROUP_CONTEXT_TOKENS", "GROUP_CONTEXT_OFFLINE_SHARE"):
        monkeypatch.delenv(var, raising=False)
    for var in [k for k in os.environ if k.startswith("CONTEXT_WINDOW_")]:
        monkeypatch.delenv(var, raising=False)
    # Same prompt budget on every OS (Windows' command line is much shorter).
    monkeypatch.setattr(budget, "ARGV_MAX_CHARS_WINDOWS", budget.ARGV_MAX_CHARS_POSIX)
    events = []

    async def fake_broadcast(ev):
        events.append(ev)
    monkeypatch.setattr(gc, "_broadcast", fake_broadcast)

    def add_session(sid, name, mode, stdin=False, ai=None):
        key = ai or mode
        _st.integrations[key] = integration(mode, stdin)
        _st.sessions[sid] = {"id": sid, "ai": key, "name": name, "cwd": str(tmp_path),
                             "model": None, "emoji": "🤖", "color": "#123456"}
        return _st.sessions[sid]

    return {"add": add_session, "events": events, "tmp": tmp_path, "integration": integration}


def chat(g, n, size=10, start=0, text="msg"):
    """n alternating user / last-member messages: "msg<i> xxxx…"."""
    for i in range(start, start + n):
        who = None if i % 2 == 0 else g["members"][-1]
        role = "user" if who is None else "member"
        gc.append_message(g, gc.make_message(role, f"{text}{i} " + "x" * size, who))
