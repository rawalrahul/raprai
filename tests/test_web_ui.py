"""The web UI works in a real browser (headless Chromium, through Playwright).

The safety net for splitting frontend2/js/complete.js (docs/code-health-plan.md,
step B1): a function that moves to the wrong file or loads too late shows up
here as a page error, a missing handler or a chat that stops working.

Runs in CI's "ui" job. Skipped where Playwright isn't installed.
"""
import os
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


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
           "OUTPUT_IDLE_TIMEOUT": "0.5",            # a shell reply is done after 0.5s of quiet
           "RAPR_RATE_LIMIT": "2000"}               # every test loads the page (~25 API calls)
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


def test_the_page_loads_without_errors(page):
    page.wait_for_timeout(1000)                     # late scripts and the first state message
    assert page.problems == []


def test_the_fonts_ship_with_rapr(page):
    """Inter and JetBrains Mono load from RAPR itself, not Google Fonts."""
    loaded = page.evaluate("""async () => [
        (await document.fonts.load('16px Inter')).length,
        (await document.fonts.load('16px "JetBrains Mono"')).length]""")
    assert loaded == [1, 1]
    assert page.problems == []


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
    assert page.problems == []


def test_the_agent_builder_opens_and_adds_a_step(page):
    """The builder's code is spread over agents.js and the agent_*.js files it loads."""
    page.evaluate("openAgentBuilder(null)")
    page.wait_for_selector("#agent-builder-wrapper.open", timeout=5000)
    workers = "_builderNodes.filter(n => (n.type || 'ai') !== 'manager').length"
    before = page.evaluate(workers)
    page.evaluate("agentAddNode()")                 # the first step also adds the manager step
    assert page.evaluate(workers) == before + 1
    page.wait_for_selector(".agent-mic-btn", state="attached", timeout=5000)
    page.evaluate("closeAgentBuilder()")
    assert page.problems == []


def test_kelvin_draws_and_switches_to_still(page):
    """Kelvin's drawing is in kelvin.js and his moods in kelvin_ui.js; the still
    switch has to reach the drawing code."""
    assert page.locator("#kelvin-header svg").count() == 1
    page.evaluate("""() => {
        window.__still = [];
        const real = Kelvin.setStill;
        Kelvin.setStill = v => { window.__still.push(v); real(v); };
    }""")
    page.evaluate("KelvinUI.setMode('still')")
    assert page.evaluate("document.documentElement.dataset.kelvin") == "still"
    page.evaluate("KelvinUI.setMode('animated')")
    assert page.evaluate("window.__still") == [True, False]
    assert page.problems == []


def test_the_packages_panel_lists_and_switches_tabs(page):
    """The panel's code is spread over packages.js and the packages_*.js files."""
    page.evaluate("togglePackagesPanel()")
    page.wait_for_selector("button.rp-tab:has-text('Browse')", state="visible", timeout=5000)
    page.evaluate("loadPackagesSection()")
    page.wait_for_function("() => !document.querySelector('#rp-list .rp-loading')", timeout=10000)
    page.click("button.rp-tab:has-text('Browse')")
    page.wait_for_function("() => _rpTab === 'browse'", timeout=5000)
    page.wait_for_timeout(1000)
    page.click("button.rp-tab:has-text('Installed')")
    page.wait_for_timeout(1000)
    assert page.problems == []



def test_page_reloads_itself_when_its_files_failed_to_load(browser, rapr_url):
    """RAPR still starting (e.g. after an update) can leave the page loaded without its
    CSS and JS: a bare page stuck on "Loading…". It must reload until they arrive."""
    ctx = browser.new_context(service_workers="block")
    page = ctx.new_page()
    failed = set()

    def fail_first_time(route):                   # the first load misses a CSS and a JS file
        name = route.request.url.split("?")[0].rsplit("/", 1)[-1]
        if name in failed:
            route.continue_()
        else:
            failed.add(name)
            route.abort()

    page.route("**/css/design-system.css*", fail_first_time)
    page.route("**/js/core.js*", fail_first_time)
    try:
        page.goto(rapr_url, wait_until="load")
        ready = "() => getComputedStyle(document.documentElement).getPropertyValue('--font-sans') !== ''" \
                " && typeof connect === 'function'"
        for _ in range(30):                       # the page's CSP blocks wait_for_function's eval
            try:
                if page.evaluate(ready):
                    break
            except sync_api.Error:                # evaluated mid-reload
                pass
            page.wait_for_timeout(500)
        else:
            pytest.fail("the page never reloaded with its CSS and JS")
    finally:
        ctx.close()


def test_settings_shows_the_telegram_status(page):
    """No bot set up in the test server: Settings says so, and how to fix it."""
    page.evaluate("() => openSettings()")
    status = page.locator("#tg-status")
    sync_api.expect(status).to_have_text("Not set up", timeout=5000)
    sync_api.expect(page.locator("#tg-msg")).to_contain_text("/setup")
