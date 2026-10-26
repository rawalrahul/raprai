"""The left sidebar's sections, the Customize section list and the icon sprite stay in step."""
import re
from pathlib import Path

FRONT = Path(__file__).resolve().parent.parent / "frontend2"


def _html():
    return (FRONT / "index.html").read_text(encoding="utf-8")


def _section_ids_in_html():
    return re.findall(r'class="sb-section[^"]*" data-section="([a-z]+)"', _html())


def test_every_sidebar_section_is_known_to_customize_and_the_rail():
    html_ids = _section_ids_in_html()
    customize = (FRONT / "js" / "customize.js").read_text(encoding="utf-8")
    sidebar = (FRONT / "js" / "sidebar.js").read_text(encoding="utf-8")
    listed = re.search(r"SECTION_IDS = \[([^\]]+)\]", customize).group(1)
    customize_ids = re.findall(r"'([a-z]+)'", listed)
    assert sorted(html_ids) == sorted(customize_ids)
    for sid in html_ids:
        assert re.search(rf"\b{sid}:\s*\{{label:", sidebar), f"{sid} missing from sidebar.js DEFS"


def test_every_section_has_an_icon_in_the_sprite():
    html = _html()
    symbols = set(re.findall(r'<symbol id="i-([a-z-]+)"', html))
    for sid in _section_ids_in_html():
        assert sid in symbols, f"no #i-{sid} icon"
    for used in set(re.findall(r'href="#i-([a-z-]+)"', html)):
        assert used in symbols, f"#i-{used} is used but not defined"


def test_customize_loads_before_paint_and_sidebar_after_the_app():
    html = _html()
    head = html.split("</head>")[0]
    assert "/js/customize.js" in head
    assert html.index("/js/sidebar.js") > html.index("/js/layout.js")         # the main script's last part
    assert html.index("/js/sidebar.js") > html.index("/js/packages.js")
