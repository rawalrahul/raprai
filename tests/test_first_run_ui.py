"""First-run fixes in the web UI that have no browser test yet: checks on the
files themselves, so they can't quietly come back."""
import pathlib
import re

FRONT = pathlib.Path(__file__).resolve().parents[1] / "frontend2"


def test_a_first_message_without_an_ai_starts_a_chat():
    """It used to be dropped with "No active session"."""
    js = (FRONT / "js" / "chat.js").read_text(encoding="utf-8")
    send = js[js.index("function send(){"):js.index("function _hasLiveSession")]
    assert "_startSessionThenSend(content)" in send
    assert "/api/routing/decide" in js


def test_sidebars_are_closed_drawers_on_phones():
    """overhaul.css forces #left-sidebar to display:flex !important; sidebar.css
    (loaded last) must hide it again below 900px unless it's opened."""
    css = (FRONT / "css" / "sidebar.css").read_text(encoding="utf-8")
    assert re.search(r"@media \(max-width: 900px\)\s*\{\s*html #left-sidebar:not\(\.open\)", css)
    html = (FRONT / "index.html").read_text(encoding="utf-8")
    assert html.index("css/sidebar.css") > html.index("css/overhaul.css")


def test_the_setup_wizard_never_sends_people_to_edit_env_or_relaunch():
    from helm.setup_wizard import _SETUP_HTML
    visible = re.sub(r"<script>.*?</script>", "", _SETUP_HTML, flags=re.S)
    assert "relaunch" not in visible.lower()
    assert "<code>.env</code>" not in visible
    assert "SETUP_DONE" in _SETUP_HTML      # skipping every step still finishes setup
