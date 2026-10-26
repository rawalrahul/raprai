"""Every frontend file is used, and the service worker caches what the page loads.

About 6,100 lines of JS and CSS sat in frontend2/ that no page loaded (an
unfinished rewrite), and the service worker cached those instead of most of the
files the page does load.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from helm.paths import PROJECT_ROOT

FRONTEND = PROJECT_ROOT / "frontend2"
# Loaded by other scripts rather than by a <script> tag
LOADED_BY_SCRIPTS = {"/js/talk_worklet.js"}


def _page_loads() -> list[str]:
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    return re.findall(r'(?:href|src)="(/(?:css|js)/[^"?]+)', html)


def test_page_loads_only_files_that_exist():
    for path in _page_loads():
        assert (FRONTEND / path.lstrip("/")).is_file(), path


def test_every_js_and_css_file_is_used():
    used = set(_page_loads()) | LOADED_BY_SCRIPTS
    on_disk = {f"/{p.parent.name}/{p.name}" for sub in ("js", "css")
               for p in (FRONTEND / sub).glob(f"*.{sub}")}
    assert on_disk - used == set(), "unused frontend files; delete them or load them"


def test_service_worker_caches_what_the_page_loads():
    sw = (FRONTEND / "sw.js").read_text(encoding="utf-8")
    block = sw[sw.index("cache.addAll(["):sw.index("])")]
    cached = re.findall(r"'([^']+)'", block)
    assert [p for p in cached if p.startswith(("/css/", "/js/"))] == _page_loads()
    for path in cached:
        if path.startswith("/static/"):
            from helm.web_routes.app import PUBLIC_ASSETS
            assert path.removeprefix("/static/") in PUBLIC_ASSETS, path


def test_ui_files_dont_use_up_the_rate_limit(monkeypatch):
    """A page load fetches about 40 JS and CSS files. Counted against the API
    limit (120 a minute), a few quick reloads made the UI's own calls fail."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from helm import security

    monkeypatch.setattr(security, "_rate_limiter", security.RateLimiter())
    app = FastAPI()
    app.add_middleware(security.RateLimitMiddleware)
    app.get("/js/{name}")(lambda name: "file")
    app.get("/css/{name}")(lambda name: "file")
    app.get("/history")(lambda: "ok")
    c = TestClient(app)
    for i in range(100):
        assert c.get(f"/js/f{i}.js").status_code == 200
        assert c.get(f"/css/f{i}.css").status_code == 200
    assert c.get("/history").status_code == 200
    # API calls are still limited
    codes = [c.get("/history").status_code for _ in range(130)]
    assert 429 in codes
