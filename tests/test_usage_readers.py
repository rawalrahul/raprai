"""Each AI's real usage, read from the AI's own service (helm/usage_readers.py)."""
import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from helm import mcp_usage
from helm import usage_readers as ur

LATER = "2099-01-01T00:00:00Z"


@pytest.fixture
def claude_home(tmp_path, monkeypatch):
    d = tmp_path / "claude"
    d.mkdir()
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(d))
    for k in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", *mcp_usage.CLAUDE_API_ENV):
        monkeypatch.delenv(k, raising=False)
    return d


def _signed_in(d, expires_ms=None, plan="max"):
    (d / ".credentials.json").write_text(json.dumps({"claudeAiOauth": {
        "accessToken": "tok", "expiresAt": expires_ms or (time.time() + 3600) * 1000, "subscriptionType": plan}}))


def test_claude_reads_the_same_windows_as_its_usage_page(claude_home):
    _signed_in(claude_home)
    asked = {}

    def fetch(url, headers):
        asked.update(url=url, headers=headers)
        return {"five_hour": {"utilization": 22.0, "resets_at": LATER},
                "seven_day": {"utilization": 51.0, "resets_at": LATER},
                "seven_day_opus": {"utilization": 7.0, "resets_at": None}, "seven_day_sonnet": None}
    r = ur.read_claude(fetch)
    assert asked["url"] == ur.CLAUDE_USAGE_URL and asked["headers"]["Authorization"] == "Bearer tok"
    assert r.mode == ur.PLAN and r.plan == "Max"
    assert [(w["label"], w["pct"]) for w in r.windows] == [("5h", 22.0), ("week", 51.0), ("week Opus", 7.0)]
    assert r.windows[0]["resets_at"] == 4070908800


def test_an_expired_claude_sign_in_is_not_refreshed_or_used(claude_home):
    _signed_in(claude_home, expires_ms=1000)
    r = ur.read_claude(lambda *a: pytest.fail("asked with an expired sign-in"))
    assert r.mode == ur.PLAN and not r.windows and "renews it" in r.note


def test_claude_on_an_api_key_has_no_windows(claude_home, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    r = ur.read_claude(lambda *a: pytest.fail("no plan to ask about"))
    assert r.mode == ur.API and not r.windows


def _codex(monkeypatch, answers):
    monkeypatch.setattr(ur, "codex_executable", lambda: "codex")
    return ur.read_codex(lambda exe: answers)


def test_codex_reads_its_plan_windows_from_its_app_server(monkeypatch):
    r = _codex(monkeypatch, {
        2: {"result": {"account": {"type": "chatgpt", "email": "a@b.c", "planType": "plus"}}},
        3: {"result": {"rateLimits": {
            "primary": {"usedPercent": 12, "windowDurationMins": 300, "resetsAt": 4102444800},
            "secondary": {"usedPercent": 41, "windowDurationMins": 10080, "resetsAt": 4102444800}}}}})
    assert r.mode == ur.PLAN and r.plan == "Plus"
    assert [(w["label"], w["pct"]) for w in r.windows] == [("5h", 12.0), ("week", 41.0)]


def test_codex_on_an_api_key_or_signed_out_shows_no_windows(monkeypatch):
    api = _codex(monkeypatch, {2: {"result": {"account": {"type": "apiKey"}}}, 3: {"error": {"message": "x"}}})
    assert api.mode == ur.API and not api.windows
    out = _codex(monkeypatch, {2: {"result": {"account": None, "requiresOpenaiAuth": True}}, 3: {"error": {}}})
    assert out.mode is None and "codex login" in out.note


def test_codex_app_server_is_really_asked(monkeypatch, tmp_path):
    """The real protocol, against a fake `codex app-server` that answers like Codex 0.166."""
    fake = tmp_path / "codex"
    fake.write_text("#!" + sys.executable + "\n" + '''import json, sys
for line in sys.stdin:
    m = json.loads(line)
    if m.get("method") == "account/read":
        print(json.dumps({"id": m["id"], "result": {"account": {"type": "chatgpt", "planType": "pro", "email": None}}}), flush=True)
    elif m.get("method") == "account/rateLimits/read":
        print(json.dumps({"id": m["id"], "result": {"rateLimits": {"primary": {"usedPercent": 3, "windowDurationMins": 300}}}}), flush=True)
''')
    fake.chmod(0o755)
    if os.name == "nt":
        pytest.skip("a shebang script")
    answers = ur.codex_app_server(str(fake), timeout=10)
    assert answers[2]["result"]["account"]["planType"] == "pro" and answers[3]["result"]["rateLimits"]["primary"]["usedPercent"] == 3


def test_gemini_reads_its_daily_quota_per_model(monkeypatch, tmp_path):
    monkeypatch.setattr(ur, "gemini_dir", lambda: tmp_path)
    monkeypatch.setattr(ur.shutil, "which", lambda name: "/bin/" + name if name == "gemini" else None)
    (tmp_path / "settings.json").write_text(json.dumps({"security": {"auth": {"selectedType": "oauth-personal"}}}))
    (tmp_path / "oauth_creds.json").write_text(json.dumps({"access_token": "t", "expiry_date": (time.time() + 600) * 1000}))

    def fetch(url, headers, body):
        if url.endswith(":loadCodeAssist"):
            return {"cloudaicompanionProject": "proj-1", "currentTier": {"name": "Gemini Code Assist for individuals"}}
        assert body == {"project": "proj-1"}
        return {"buckets": [{"modelId": "gemini-2.5-pro", "remainingFraction": 0.75, "resetTime": LATER, "tokenType": "REQUESTS"}]}
    r = ur.read_gemini(fetch)
    assert r.mode == ur.PLAN and r.windows == [{"key": "gemini-2.5-pro", "label": "2.5 Pro today", "pct": 25.0,
                                                 "resets_at": 4070908800}]


def test_a_reading_replaces_what_was_kept_before():
    mcp_usage.set_limits("codex", "Codex", [{"key": "primary", "label": "5h", "pct": 99.0, "resets_at": 4102444800}], "old file")
    mcp_usage.store_readings({"codex": ur.Reading("codex", "Codex", mode=ur.PLAN, plan="Plus",
                                                  windows=[{"key": "primary", "label": "5h", "pct": 12.0, "resets_at": 4102444800}])})
    assert mcp_usage.limits()["codex"]["windows"][0]["pct"] == 12.0 and mcp_usage.limits()["codex"]["plan"] == "Plus"
    mcp_usage.store_readings({"codex": ur.Reading("codex", "Codex", note="Not signed in to Codex (run `codex login`).")})
    assert "codex" not in mcp_usage.limits() and mcp_usage.billing("codex") is None
    assert "codex login" in mcp_usage.readings()["codex"]["note"]


def test_the_app_shows_no_made_up_cap(monkeypatch):
    import asyncio
    from helm.web_routes import usage_routes
    monkeypatch.delenv("USAGE_CAP_MIN_CLAUDE", raising=False)
    monkeypatch.delenv("USAGE_CAP_MIN_DEFAULT", raising=False)
    mcp_usage.store_readings({"claude": ur.Reading("claude", "Claude", note="Not signed in to claude.ai")})
    c = json.loads(asyncio.run(usage_routes.get_usage()).body)["ais"]["claude"]
    assert c["cap_min"] is None and c["pct_used"] is None and c["limits"] == [] and "Not signed in" in c["note"]
    monkeypatch.setenv("USAGE_CAP_MIN_CLAUDE", "120")
    c = json.loads(asyncio.run(usage_routes.get_usage()).body)["ais"]["claude"]
    assert c["cap_min"] == 120 and c["source"] == "cap"
