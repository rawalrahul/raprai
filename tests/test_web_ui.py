"""The web UI works in a real browser (headless Chromium, through Playwright).

The safety net for splitting frontend2/js/complete.js (docs/code-health-plan.md,
step B1): a function that moves to the wrong file or loads too late shows up
here as a page error, a missing handler or a chat that stops working.

Runs in CI's "ui" job. Skipped where Playwright isn't installed.
"""
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# shortcut: the UI asks Google Fonts for its fonts and RAPR's CSP blocks that
# (plan step E1); drop this once the fonts ship with RAPR.
KNOWN_NOISE = re.compile(r"fonts\.googleapis\.com")


@pytest.fixture(scope="module")
def rapr_url(tmp_path_factory):
    data = tmp_path_factory.mktemp("data")
    (data / ".env").write_text("RAPR_HEADLESS=1\n")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    # No PIN: some tests set PIN_* in os.environ, and a PIN would send the page to /login.
    env = {**{k: v for k, v in os.environ.items() if not k.startswith("PIN_")},
           "RAPR_HEADLESS": "1", "RAPR_DATA_DIR": str(data),
           "WEB_HOST": "127.0.0.1", "WEB_PORT": str(port),
           "OUTPUT_IDLE_TIMEOUT": "0.5"}            # a shell reply is done after 0.5s of quiet
    log = open(data / "server.log", "w")
    proc = subprocess.Popen([sys.executable, "web_app.py"], cwd=ROOT, env=env,
                            stdout=log, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(120):
            try:
                urllib.request.urlopen(url + "/health", timeout=1)
                break
            except OSError:
                if proc.poll() is not None:
                    break
                time.sleep(0.5)
        else:
            pytest.fail("RAPR didn't start: " + (data / "server.log").read_text()[-2000:])
        if proc.poll() is not None:
            pytest.fail("RAPR exited: " + (data / "server.log").read_text()[-2000:])
        yield url
    finally:
        proc.terminate()
        proc.wait(timeout=10)
        log.close()


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def page(browser, rapr_url):
    """The UI, loaded, with every page error and failed request collected."""
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.problems = []
    page.on("pageerror", lambda e: page.problems.append(f"page error: {e}"))
    page.on("console", lambda m: m.type == "error" and page.problems.append(f"console: {m.text}"))
    page.on("response", lambda r: r.status >= 400 and page.problems.append(f"{r.status} {r.url}"))
    page.goto(rapr_url, wait_until="networkidle")
    yield page
    page.close()


def _problems(page):
    return [p for p in page.problems if not KNOWN_NOISE.search(p)]


def test_the_page_loads_without_errors(page):
    page.wait_for_timeout(1000)                     # late scripts and the first state message
    assert _problems(page) == []


def test_every_button_calls_a_function_that_exists(page):
    missing = page.evaluate(r"""() => {
        const names = new Set();
        for (const el of document.querySelectorAll('[onclick],[onchange],[oninput],[onkeydown],[onsubmit]'))
            for (const a of ['onclick', 'onchange', 'oninput', 'onkeydown', 'onsubmit']) {
                const code = el.getAttribute(a) || '';
                for (const m of code.matchAll(/(?:^|[;\s(!&|])([A-Za-z_$][\w$]*)\s*\(/g)) names.add(m[1]);
            }
        const builtins = ['if', 'event', 'return', 'function', 'alert', 'confirm', 'setTimeout', 'fetch'];
        return [...names].filter(n => !builtins.includes(n) && typeof window[n] !== 'function').sort();
    }""")
    assert missing == []


def test_a_message_goes_to_the_session_and_its_reply_shows(page):
    page.evaluate("cmd('new_session:shell')")
    page.wait_for_function("() => _focusedId !== null", timeout=10000)
    page.fill("#inp", "echo PONYTAIL-$((40+2))")
    page.press("#inp", "Enter")
    page.wait_for_selector("text=PONYTAIL-42", timeout=20000)
    assert _problems(page) == []
