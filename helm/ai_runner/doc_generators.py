"""
helm/ai_runner/doc_generators.py — Document generation code generators.

Covers: _generate_pptx_code, _generate_pdf_code, _generate_docx_code.
These functions generate complete Python code strings that can be executed
to create PowerPoint presentations, PDF documents, and Word documents.

Enhanced with multiple themes, varied slide types, and professional output
so that even small AI models (7B Ollama) produce polished results.
"""


# ---------------------------------------------------------------------------
# Theme definitions (shared across generators)
# ---------------------------------------------------------------------------

PPTX_THEMES = {
    "dark": {
        "bg": (0x0D, 0x1B, 0x2A),
        "bg_alt": (0x0A, 0x14, 0x22),
        "accent1": (0x00, 0xC9, 0xFF),
        "accent2": (0xFF, 0x6B, 0x35),
        "title_c": (0xFF, 0xFF, 0xFF),
        "body_c": (0xCC, 0xDD, 0xEE),
        "muted_c": (0x77, 0x99, 0xAA),
        "card_bg": (0x00, 0x30, 0x50),
        "card_bg2": (0x00, 0x40, 0x60),
        "divider": (0x1A, 0x3A, 0x5A),
    },
    "corporate": {
        "bg": (0x1F, 0x35, 0x64),
        "bg_alt": (0x16, 0x28, 0x4A),
        "accent1": (0x00, 0xB0, 0xF0),
        "accent2": (0xF0, 0xA5, 0x00),
        "title_c": (0xFF, 0xFF, 0xFF),
        "body_c": (0xE0, 0xE8, 0xF0),
        "muted_c": (0x90, 0xA0, 0xBB),
        "card_bg": (0x2E, 0x4A, 0x7A),
        "card_bg2": (0x38, 0x56, 0x88),
        "divider": (0x3A, 0x55, 0x80),
    },
    "light": {
        "bg": (0xF8, 0xF9, 0xFC),
        "bg_alt": (0xEE, 0xF1, 0xF6),
        "accent1": (0x2E, 0x74, 0xB5),
        "accent2": (0xE0, 0x5A, 0x2D),
        "title_c": (0x1A, 0x1A, 0x2E),
        "body_c": (0x33, 0x40, 0x55),
        "muted_c": (0x88, 0x90, 0xA0),
        "card_bg": (0xFF, 0xFF, 0xFF),
        "card_bg2": (0xE8, 0xEC, 0xF2),
        "divider": (0xD0, 0xD8, 0xE4),
    },
    "forest": {
        "bg": (0x14, 0x20, 0x18),
        "bg_alt": (0x0E, 0x18, 0x12),
        "accent1": (0x4A, 0xBB, 0x6A),
        "accent2": (0xF0, 0xC0, 0x40),
        "title_c": (0xF0, 0xF5, 0xF0),
        "body_c": (0xC0, 0xDD, 0xC8),
        "muted_c": (0x70, 0x99, 0x78),
        "card_bg": (0x1E, 0x36, 0x28),
        "card_bg2": (0x28, 0x44, 0x32),
        "divider": (0x2A, 0x50, 0x38),
    },
}


def _get_theme(theme_name: str) -> dict:
    """Return theme dict, falling back to 'dark'."""
    return PPTX_THEMES.get(theme_name, PPTX_THEMES["dark"])


# ---------------------------------------------------------------------------
# PPTX Generator — Enhanced
# ---------------------------------------------------------------------------

def _generate_pptx_code(filename: str, title: str, subtitle: str,
                        slides: list, theme: str = "dark") -> str:
    """Generate complete Python code for a professional PPTX."""
    t = _get_theme(theme)

    # Build slide calls
    slide_calls = []
    for s in slides:
        stype = s.get("type", "content")
        if stype == "content":
            slide_calls.append(
                f"content_slide({repr(s.get('title',''))}, {repr(s.get('bullets',[]))})"
            )
        elif stype == "two_column":
            slide_calls.append(
                f"two_col_slide({repr(s.get('title',''))}, "
                f"{repr(s.get('left_title',''))}, {repr(s.get('left_items',[]))}, "
                f"{repr(s.get('right_title',''))}, {repr(s.get('right_items',[]))})"
            )
        elif stype == "stat":
            slide_calls.append(
                f"stat_slide({repr(s.get('stat_value',''))}, "
                f"{repr(s.get('stat_label',''))}, {repr(s.get('context',''))})"
            )
        elif stype == "section":
            slide_calls.append(
                f"section_slide({s.get('number', 1)}, {repr(s.get('title',''))})"
            )
        elif stype == "timeline":
            slide_calls.append(
                f"timeline_slide({repr(s.get('title',''))}, {repr(s.get('steps',[]))})"
            )
        elif stype == "comparison":
            slide_calls.append(
                f"comparison_slide({repr(s.get('title',''))}, "
                f"{repr(s.get('option_a',''))}, {repr(s.get('option_a_points',[]))}, "
                f"{repr(s.get('option_b',''))}, {repr(s.get('option_b_points',[]))})"
            )
        elif stype == "quote":
            slide_calls.append(
                f"quote_slide({repr(s.get('quote',''))}, {repr(s.get('author',''))})"
            )
        elif stype == "cards":
            slide_calls.append(
                f"cards_slide({repr(s.get('title',''))}, {repr(s.get('cards',[]))})"
            )
        elif stype == "table":
            slide_calls.append(
                f"table_slide({repr(s.get('title',''))}, "
                f"{repr(s.get('headers',[]))}, {repr(s.get('rows',[]))})"
            )
        elif stype == "closing":
            slide_calls.append(
                f"closing_slide({repr(s.get('title','Thank You'))}, {repr(s.get('subtitle',''))})"
            )

    slide_code = "\n".join(slide_calls)

    # RGB tuple helpers
    def rgb_tuple(key):
        c = t[key]
        return f"RGBColor({c[0]:#04x}, {c[1]:#04x}, {c[2]:#04x})"

    return f'''\
import subprocess, sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "python-pptx", "-q"])

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

prs = Presentation()
prs.slide_width  = Inches(13.33)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]

# ── Theme Colors ──
BG      = {rgb_tuple("bg")}
BG_ALT  = {rgb_tuple("bg_alt")}
ACCENT1 = {rgb_tuple("accent1")}
ACCENT2 = {rgb_tuple("accent2")}
TITLE_C = {rgb_tuple("title_c")}
BODY_C  = {rgb_tuple("body_c")}
MUTED_C = {rgb_tuple("muted_c")}
CARD_BG = {rgb_tuple("card_bg")}
CARD_BG2= {rgb_tuple("card_bg2")}
DIVIDER = {rgb_tuple("divider")}

SW = prs.slide_width
SH = prs.slide_height

# ── Utilities ──

def solid(shape, color):
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()

def rect(slide, x, y, w, h, color):
    s = slide.shapes.add_shape(1, Inches(x), Inches(y), Inches(w), Inches(h))
    solid(s, color)
    return s

def rounded_rect(slide, x, y, w, h, color, radius=0.15):
    from pptx.enum.shapes import MSO_SHAPE
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h))
    solid(s, color)
    s.adjustments[0] = radius / max(w, h)
    return s

def txt(slide, text, x, y, w, h, size=24, color=None, bold=False,
        align=PP_ALIGN.LEFT, italic=False, font="Calibri"):
    if color is None:
        color = TITLE_C
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tb.line.fill.background()
    tf = tb.text_frame
    tf.word_wrap = True
    p  = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = str(text)
    run.font.size  = Pt(size)
    run.font.color.rgb = color
    run.font.bold  = bold
    run.font.italic = italic
    run.font.name = font
    return tb

def multi_txt(slide, lines, x, y, w, h, size=18, color=None, bold=False, line_spacing=1.3):
    """Add multiple lines in one textbox with proper spacing."""
    if color is None:
        color = BODY_C
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tb.line.fill.background()
    tf = tb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.space_after = Pt(int(size * (line_spacing - 1) + 2))
        run = p.add_run()
        run.text = str(line)
        run.font.size = Pt(size)
        run.font.color.rgb = color
        run.font.bold = bold
        run.font.name = "Calibri"
    return tb

def bg(slide, color=None):
    if color is None:
        color = BG
    r = rect(slide, 0, 0, SW.inches, SH.inches, color)
    slide.shapes._spTree.remove(r._element)
    slide.shapes._spTree.insert(2, r._element)
    return r

def accent_bar(slide, bar_color=None, x=0, y=0, w=0.06, h=None):
    if bar_color is None:
        bar_color = ACCENT1
    if h is None:
        h = SH.inches
    rect(slide, x, y, w, h, bar_color)

def bottom_strip(slide, color=None, height=0.06):
    if color is None:
        color = ACCENT1
    rect(slide, 0, SH.inches - height, SW.inches, height, color)

def header_bar(slide, title_text, height=1.1):
    rect(slide, 0, 0, SW.inches, height, BG_ALT)
    accent_bar(slide, ACCENT1, x=0, y=0, w=0.06, h=SH.inches)
    txt(slide, title_text, x=0.25, y=0.12, w=12.5, h=height - 0.2,
        size=30, color=TITLE_C, bold=True)
    rect(slide, 0.25, height, 12.8, 0.04, ACCENT1)

def slide_number(slide, num):
    txt(slide, str(num), x=SW.inches - 0.8, y=SH.inches - 0.45,
        w=0.6, h=0.35, size=10, color=MUTED_C, align=PP_ALIGN.RIGHT)

_slide_num = 0

def next_num():
    global _slide_num
    _slide_num += 1
    return _slide_num

# ── Slide Types ──

def title_slide(title_text, subtitle_text=""):
    slide = prs.slides.add_slide(BLANK)
    bg(slide)
    # Geometric accent block
    rect(slide, 8.5, 0, 4.83, 3.5, CARD_BG2)
    rect(slide, 9.5, 3.5, 3.83, 4.0, CARD_BG)
    accent_bar(slide, ACCENT1, x=0, y=0, w=0.08, h=SH.inches)
    txt(slide, title_text, x=0.5, y=2.0, w=8.5, h=2.0,
        size=48, color=TITLE_C, bold=True, font="Calibri")
    if subtitle_text:
        txt(slide, subtitle_text, x=0.5, y=4.2, w=8.0, h=0.8,
            size=20, color=ACCENT1, font="Calibri")
    # Thin separator
    rect(slide, 0.5, 3.95, 5.0, 0.04, ACCENT1)
    bottom_strip(slide)
    return slide

def content_slide(title_text, bullets):
    slide = prs.slides.add_slide(BLANK)
    bg(slide)
    header_bar(slide, title_text)
    n = next_num()
    y_pos = 1.45
    spacing = min(0.7, 5.5 / max(len(bullets), 1))
    for i, bullet in enumerate(bullets):
        # Numbered circle marker
        circle_x, circle_y = 0.4, y_pos + 0.02
        rounded_rect(slide, circle_x, circle_y, 0.32, 0.32, ACCENT1, radius=0.16)
        txt(slide, str(i + 1), x=circle_x, y=circle_y, w=0.32, h=0.32,
            size=12, color=BG, bold=True, align=PP_ALIGN.CENTER)
        txt(slide, bullet, x=0.85, y=y_pos, w=11.8, h=0.55,
            size=18, color=BODY_C)
        y_pos += spacing
    bottom_strip(slide)
    slide_number(slide, n)
    return slide

def two_col_slide(title_text, left_title, left_items, right_title, right_items):
    slide = prs.slides.add_slide(BLANK)
    bg(slide)
    header_bar(slide, title_text)
    n = next_num()
    # Left card
    rounded_rect(slide, 0.3, 1.35, 6.1, 5.5, CARD_BG, radius=0.12)
    rect(slide, 0.3, 1.35, 0.08, 5.5, ACCENT1)
    txt(slide, left_title, x=0.6, y=1.5, w=5.5, h=0.5,
        size=18, color=ACCENT1, bold=True)
    y = 2.15
    for item in left_items:
        txt(slide, "\\u2022  " + item, x=0.7, y=y, w=5.4, h=0.5,
            size=16, color=BODY_C)
        y += 0.55
    # Right card
    rounded_rect(slide, 6.8, 1.35, 6.2, 5.5, CARD_BG, radius=0.12)
    rect(slide, 6.8, 1.35, 0.08, 5.5, ACCENT2)
    txt(slide, right_title, x=7.1, y=1.5, w=5.6, h=0.5,
        size=18, color=ACCENT2, bold=True)
    y = 2.15
    for item in right_items:
        txt(slide, "\\u2022  " + item, x=7.2, y=y, w=5.4, h=0.5,
            size=16, color=BODY_C)
        y += 0.55
    bottom_strip(slide)
    slide_number(slide, n)
    return slide

def stat_slide(stat_value, stat_label, context_text=""):
    slide = prs.slides.add_slide(BLANK)
    bg(slide)
    n = next_num()
    # Centered stat card
    rounded_rect(slide, 2.0, 1.0, 9.3, 4.0, CARD_BG, radius=0.15)
    rect(slide, 2.0, 1.0, 0.12, 4.0, ACCENT1)
    txt(slide, str(stat_value), x=2.5, y=1.3, w=8.3, h=2.0,
        size=80, color=ACCENT1, bold=True, align=PP_ALIGN.CENTER)
    txt(slide, stat_label, x=2.5, y=3.2, w=8.3, h=0.8,
        size=22, color=TITLE_C, align=PP_ALIGN.CENTER)
    if context_text:
        txt(slide, context_text, x=2.0, y=5.3, w=9.3, h=0.6,
            size=15, color=MUTED_C, align=PP_ALIGN.CENTER, italic=True)
    bottom_strip(slide)
    slide_number(slide, n)
    return slide

def section_slide(section_number, section_title):
    slide = prs.slides.add_slide(BLANK)
    bg(slide)
    next_num()
    # Large number block on left
    rect(slide, 0, 0, 4.8, SH.inches, CARD_BG)
    rect(slide, 4.8, 0, 0.06, SH.inches, ACCENT1)
    txt(slide, str(section_number).zfill(2), x=0.5, y=1.5, w=3.8, h=3.0,
        size=120, color=ACCENT1, bold=True, align=PP_ALIGN.CENTER)
    txt(slide, section_title, x=5.5, y=2.5, w=7.3, h=1.8,
        size=38, color=TITLE_C, bold=True)
    rect(slide, 5.5, 4.3, 4.0, 0.06, ACCENT1)
    bottom_strip(slide)
    return slide

def timeline_slide(title_text, steps):
    slide = prs.slides.add_slide(BLANK)
    bg(slide)
    header_bar(slide, title_text)
    n = next_num()
    num_steps = len(steps)
    if num_steps == 0:
        bottom_strip(slide)
        return slide
    usable_w = 12.0
    step_w = usable_w / num_steps
    start_x = 0.65
    # Connecting line
    line_y = 2.6
    rect(slide, start_x + 0.2, line_y + 0.13, usable_w - 0.4, 0.04, DIVIDER)
    for i, step in enumerate(steps):
        cx = start_x + i * step_w + step_w / 2
        # Circle node
        node_size = 0.5
        rounded_rect(slide, cx - node_size/2, line_y - 0.02,
                      node_size, node_size, ACCENT1, radius=0.25)
        txt(slide, str(i + 1), x=cx - node_size/2, y=line_y - 0.02,
            w=node_size, h=node_size, size=16, color=BG, bold=True,
            align=PP_ALIGN.CENTER)
        # Step title
        step_title = step if isinstance(step, str) else step.get("title", "")
        step_desc = "" if isinstance(step, str) else step.get("description", "")
        txt(slide, step_title, x=cx - step_w/2 + 0.1, y=3.3,
            w=step_w - 0.2, h=0.6, size=14, color=TITLE_C, bold=True,
            align=PP_ALIGN.CENTER)
        if step_desc:
            txt(slide, step_desc, x=cx - step_w/2 + 0.1, y=3.9,
                w=step_w - 0.2, h=1.5, size=12, color=MUTED_C,
                align=PP_ALIGN.CENTER)
    bottom_strip(slide)
    slide_number(slide, n)
    return slide

def comparison_slide(title_text, option_a, option_a_points, option_b, option_b_points):
    slide = prs.slides.add_slide(BLANK)
    bg(slide)
    header_bar(slide, title_text)
    n = next_num()
    # VS divider
    txt(slide, "VS", x=6.1, y=3.5, w=1.1, h=0.6,
        size=20, color=MUTED_C, bold=True, align=PP_ALIGN.CENTER)
    # Option A card
    rounded_rect(slide, 0.3, 1.35, 5.6, 5.5, CARD_BG, radius=0.12)
    rect(slide, 0.3, 1.35, 5.6, 0.7, ACCENT1)
    txt(slide, option_a, x=0.5, y=1.42, w=5.2, h=0.55,
        size=18, color=BG, bold=True, align=PP_ALIGN.CENTER)
    y = 2.3
    for pt in option_a_points:
        txt(slide, "\\u2713  " + pt, x=0.6, y=y, w=5.0, h=0.5,
            size=15, color=BODY_C)
        y += 0.55
    # Option B card
    rounded_rect(slide, 7.4, 1.35, 5.6, 5.5, CARD_BG, radius=0.12)
    rect(slide, 7.4, 1.35, 5.6, 0.7, ACCENT2)
    txt(slide, option_b, x=7.6, y=1.42, w=5.2, h=0.55,
        size=18, color=BG, bold=True, align=PP_ALIGN.CENTER)
    y = 2.3
    for pt in option_b_points:
        txt(slide, "\\u2713  " + pt, x=7.7, y=y, w=5.0, h=0.5,
            size=15, color=BODY_C)
        y += 0.55
    bottom_strip(slide)
    slide_number(slide, n)
    return slide

def quote_slide(quote_text, author=""):
    slide = prs.slides.add_slide(BLANK)
    bg(slide)
    n = next_num()
    # Large quotation mark
    txt(slide, "\\u201C", x=1.5, y=0.8, w=2.0, h=2.5,
        size=150, color=ACCENT1, bold=True)
    # Quote text
    txt(slide, quote_text, x=2.5, y=2.2, w=8.5, h=2.5,
        size=26, color=TITLE_C, italic=True, align=PP_ALIGN.LEFT)
    # Author
    if author:
        rect(slide, 2.5, 4.8, 3.0, 0.04, ACCENT1)
        txt(slide, "\\u2014 " + author, x=2.5, y=5.0, w=8.0, h=0.6,
            size=18, color=ACCENT1, bold=True)
    bottom_strip(slide)
    slide_number(slide, n)
    return slide

def cards_slide(title_text, cards):
    slide = prs.slides.add_slide(BLANK)
    bg(slide)
    header_bar(slide, title_text)
    n = next_num()
    num_cards = min(len(cards), 4)
    if num_cards == 0:
        bottom_strip(slide)
        return slide
    usable_w = 12.4
    card_w = (usable_w - (num_cards - 1) * 0.3) / num_cards
    start_x = 0.45
    for i, card in enumerate(cards[:4]):
        cx = start_x + i * (card_w + 0.3)
        c_title = card if isinstance(card, str) else card.get("title", "")
        c_desc = "" if isinstance(card, str) else card.get("description", "")
        # Card background
        rounded_rect(slide, cx, 1.4, card_w, 5.3, CARD_BG, radius=0.1)
        # Accent top bar
        rect(slide, cx, 1.4, card_w, 0.06, ACCENT1 if i % 2 == 0 else ACCENT2)
        # Number badge
        badge_x = cx + card_w / 2 - 0.22
        rounded_rect(slide, badge_x, 1.7, 0.44, 0.44,
                      ACCENT1 if i % 2 == 0 else ACCENT2, radius=0.22)
        txt(slide, str(i + 1), x=badge_x, y=1.7, w=0.44, h=0.44,
            size=14, color=BG, bold=True, align=PP_ALIGN.CENTER)
        # Card title
        txt(slide, c_title, x=cx + 0.15, y=2.35, w=card_w - 0.3, h=0.7,
            size=15, color=TITLE_C, bold=True, align=PP_ALIGN.CENTER)
        # Card description
        if c_desc:
            txt(slide, c_desc, x=cx + 0.15, y=3.1, w=card_w - 0.3, h=3.3,
                size=13, color=MUTED_C, align=PP_ALIGN.CENTER)
    bottom_strip(slide)
    slide_number(slide, n)
    return slide

def table_slide(title_text, headers, rows):
    slide = prs.slides.add_slide(BLANK)
    bg(slide)
    header_bar(slide, title_text)
    n = next_num()
    if not headers or not rows:
        bottom_strip(slide)
        return slide
    num_cols = len(headers)
    num_rows = len(rows) + 1
    t_w = min(12.0, num_cols * 2.5)
    t_x = (SW.inches - t_w) / 2
    from pptx.util import Inches as I, Pt as P, Emu
    table_shape = slide.shapes.add_table(num_rows, num_cols,
        I(t_x), I(1.5), I(t_w), I(min(5.0, num_rows * 0.6)))
    table = table_shape.table
    # Style header row
    for ci, h in enumerate(headers):
        cell = table.cell(0, ci)
        cell.text = str(h)
        cell.fill.solid()
        cell.fill.fore_color.rgb = ACCENT1
        for p in cell.text_frame.paragraphs:
            p.alignment = PP_ALIGN.CENTER
            for run in p.runs:
                run.font.bold = True
                run.font.size = P(14)
                run.font.color.rgb = BG
                run.font.name = "Calibri"
    # Style data rows
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = table.cell(ri + 1, ci)
            cell.text = str(val)
            cell.fill.solid()
            cell.fill.fore_color.rgb = CARD_BG if ri % 2 == 0 else BG
            for p in cell.text_frame.paragraphs:
                for run in p.runs:
                    run.font.size = P(13)
                    run.font.color.rgb = BODY_C
                    run.font.name = "Calibri"
    bottom_strip(slide)
    slide_number(slide, n)
    return slide

def closing_slide(title_text="Thank You", subtitle_text=""):
    slide = prs.slides.add_slide(BLANK)
    bg(slide)
    # Geometric accents
    rect(slide, 0, 0, 0.08, SH.inches, ACCENT1)
    rect(slide, 0, SH.inches - 1.5, SW.inches, 1.5, CARD_BG)
    txt(slide, title_text, x=0.5, y=2.0, w=12.3, h=2.0,
        size=52, color=TITLE_C, bold=True, align=PP_ALIGN.CENTER)
    if subtitle_text:
        txt(slide, subtitle_text, x=0.5, y=4.0, w=12.3, h=0.8,
            size=20, color=ACCENT1, align=PP_ALIGN.CENTER)
    rect(slide, 4.5, 3.8, 4.3, 0.05, ACCENT1)
    bottom_strip(slide)
    return slide

# ── Build Presentation ──
title_slide({repr(title)}, {repr(subtitle or '')})
{slide_code}
prs.save({repr(filename)})
print("Created " + {repr(filename)})
'''


# ---------------------------------------------------------------------------
# PDF Generator — Enhanced
# ---------------------------------------------------------------------------

def _generate_pdf_code(filename: str, title: str, subtitle: str,
                       sections: list) -> str:
    """Generate complete Python code for a professional PDF."""
    section_code_parts = []
    for s in sections:
        h = s.get("heading", "")
        section_code_parts.append(f"story.append(Paragraph({repr(h)}, H2))")
        for p in s.get("paragraphs", []):
            section_code_parts.append(f"story.append(Paragraph({repr(p)}, BODY))")
        if s.get("bullets"):
            items_repr = repr(s["bullets"])
            section_code_parts.append(f"story.extend(bullets({items_repr}))")
        if s.get("numbered_items"):
            items_repr = repr(s["numbered_items"])
            section_code_parts.append(f"story.extend(numbered_list({items_repr}))")
        if s.get("callout"):
            section_code_parts.append(
                f"story.append(callout_box({repr(s['callout'])}, "
                f"{repr(s.get('callout_label', 'Note'))}))"
            )
        if s.get("key_value_pairs"):
            section_code_parts.append(
                f"story.append(key_value_table({repr(s['key_value_pairs'])}))"
            )
        if s.get("table_headers") and s.get("table_rows"):
            section_code_parts.append(
                f"story.append(styled_table({repr(s['table_headers'])}, "
                f"{repr(s['table_rows'])}))"
            )
        if s.get("page_break"):
            section_code_parts.append("story.append(PageBreak())")
        section_code_parts.append("story.append(Spacer(1, 0.3*cm))")

    sections_code = "\n".join(section_code_parts)

    return f'''\
import subprocess, sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab", "-q"])
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, PageBreak, KeepTogether)

PAGE_W, PAGE_H = A4
MARGIN = 2.2 * cm

# ── Colors ──
C_PRIMARY    = colors.HexColor('#1F3564')
C_SECONDARY  = colors.HexColor('#2E74B5')
C_ACCENT     = colors.HexColor('#00B0F0')
C_ACCENT2    = colors.HexColor('#FF6B35')
C_LIGHT_BG   = colors.HexColor('#F2F4F8')
C_WHITE      = colors.white
C_TEXT        = colors.HexColor('#1A1A2E')
C_MUTED      = colors.HexColor('#666680')
C_BORDER     = colors.HexColor('#C8D0DC')

# ── Styles ──
_base = getSampleStyleSheet()
H1 = ParagraphStyle('H1', parent=_base['Heading1'], fontName='Helvetica-Bold',
    fontSize=24, textColor=C_PRIMARY, spaceBefore=20, spaceAfter=10, leading=28)
H2 = ParagraphStyle('H2', parent=_base['Heading2'], fontName='Helvetica-Bold',
    fontSize=16, textColor=C_SECONDARY, spaceBefore=16, spaceAfter=6, leading=20)
BODY = ParagraphStyle('Body', parent=_base['Normal'], fontName='Helvetica',
    fontSize=10.5, textColor=C_TEXT, leading=16, spaceAfter=7, alignment=TA_JUSTIFY)
BULLET_STYLE = ParagraphStyle('Bullet', parent=BODY,
    leftIndent=18, firstLineIndent=-12, spaceAfter=4)
NUM_STYLE = ParagraphStyle('Numbered', parent=BODY,
    leftIndent=18, firstLineIndent=-14, spaceAfter=4)
CAPTION = ParagraphStyle('Caption', parent=BODY,
    fontSize=9, textColor=C_MUTED, alignment=TA_CENTER, spaceAfter=6)
CALLOUT = ParagraphStyle('Callout', parent=BODY, fontName='Helvetica',
    fontSize=10, textColor=C_TEXT, backColor=C_LIGHT_BG,
    leftIndent=12, rightIndent=12, spaceBefore=8, spaceAfter=8,
    borderPadding=(8,10,8,10), leading=15)
KV_KEY = ParagraphStyle('KVKey', parent=BODY, fontName='Helvetica-Bold',
    fontSize=10, textColor=C_PRIMARY)
KV_VAL = ParagraphStyle('KVVal', parent=BODY, fontSize=10, textColor=C_TEXT)

def divider(color=C_SECONDARY, thickness=1.5):
    return HRFlowable(width='100%', thickness=thickness, color=color,
        spaceAfter=8, spaceBefore=8)

def bullets(items):
    return [Paragraph('\\u2022  ' + str(item), BULLET_STYLE) for item in items]

def numbered_list(items):
    return [Paragraph(f'{{i+1}}.  {{item}}', NUM_STYLE)
            for i, item in enumerate(items)]

def callout_box(text, label="Note"):
    label_html = f'<font color="#2E74B5" name="Helvetica-Bold">{{label}}:  </font>'
    return Paragraph(label_html + str(text), CALLOUT)

def key_value_table(pairs):
    data = [[Paragraph(str(k), KV_KEY), Paragraph(str(v), KV_VAL)]
            for k, v in pairs]
    avail = PAGE_W - 2 * MARGIN
    t = Table(data, colWidths=[avail * 0.3, avail * 0.7])
    t.setStyle(TableStyle([
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [C_WHITE, C_LIGHT_BG]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, C_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    return t

def styled_table(headers, rows, col_widths=None):
    all_rows = [headers] + rows
    header_style = ParagraphStyle('th', parent=BODY,
        fontName='Helvetica-Bold', textColor=C_WHITE, fontSize=10)
    cell_style = ParagraphStyle('td', parent=BODY, fontSize=10)
    all_data = [[Paragraph(str(v), header_style if ri==0 else cell_style)
                 for v in row] for ri, row in enumerate(all_rows)]
    if col_widths is None:
        avail = PAGE_W - 2 * MARGIN
        col_widths = [avail / len(headers)] * len(headers)
    t = Table(all_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_PRIMARY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_WHITE, C_LIGHT_BG]),
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    return t

_DOC_TITLE = {repr(title)}

def _header_footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    # Header
    canvas.setFillColor(C_PRIMARY)
    canvas.rect(0, h - 1.2*cm, w, 1.2*cm, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont('Helvetica-Bold', 10)
    canvas.drawString(MARGIN, h - 0.8*cm, _DOC_TITLE)
    # Accent line under header
    canvas.setFillColor(C_ACCENT)
    canvas.rect(0, h - 1.25*cm, w, 0.05*cm, fill=1, stroke=0)
    # Footer
    canvas.setFillColor(C_LIGHT_BG)
    canvas.rect(0, 0, w, 1.0*cm, fill=1, stroke=0)
    canvas.setFillColor(C_MUTED)
    canvas.setFont('Helvetica', 8)
    canvas.drawString(MARGIN, 0.35*cm, 'Generated by RAPR AI')
    canvas.drawRightString(w - MARGIN, 0.35*cm, f'Page {{doc.page}}')
    canvas.restoreState()

doc = SimpleDocTemplate({repr(filename)}, pagesize=A4,
    leftMargin=MARGIN, rightMargin=MARGIN,
    topMargin=MARGIN + 1.5*cm, bottomMargin=MARGIN + 0.8*cm)
story = []
story.append(Spacer(1, 1.5*cm))
story.append(Paragraph({repr(title)}, H1))
story.append(Paragraph({repr(subtitle or '')}, CAPTION))
story.append(divider(C_ACCENT, thickness=2))
story.append(Spacer(1, 0.4*cm))
{sections_code}
doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
print("Created " + {repr(filename)})
'''


# ---------------------------------------------------------------------------
# DOCX Generator — Enhanced
# ---------------------------------------------------------------------------

def _generate_docx_code(filename: str, title: str, sections: list) -> str:
    """Generate complete Python code for a professional DOCX."""
    section_code_parts = []
    for s in sections:
        h = s.get("heading", "")
        section_code_parts.append(f"heading({repr(h)}, level=2)")
        for p in s.get("paragraphs", []):
            section_code_parts.append(f"body({repr(p)})")
        for b in s.get("bullets", []):
            section_code_parts.append(f"bullet({repr(b)})")
        if s.get("numbered_items"):
            for i, item in enumerate(s["numbered_items"]):
                section_code_parts.append(f"numbered({repr(item)})")
        if s.get("callout"):
            section_code_parts.append(f"callout({repr(s['callout'])})")
        if s.get("key_value_pairs"):
            section_code_parts.append(
                f"kv_table({repr(s['key_value_pairs'])})"
            )
        if s.get("table_headers") and s.get("table_rows"):
            section_code_parts.append(
                f"add_table({repr(s['table_headers'])}, {repr(s['table_rows'])})"
            )
        # Add spacing between sections
        section_code_parts.append("doc.add_paragraph()")

    sections_code = "\n".join(section_code_parts)

    return f'''\
import subprocess, sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "python-docx", "-q"])
from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

doc = Document()

# ── Page Setup ──
for section in doc.sections:
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.8)
    section.right_margin = Cm(2.5)

# ── Base Style ──
style = doc.styles['Normal']
style.font.name = 'Calibri'
style.font.size = Pt(11)
style.paragraph_format.space_after = Pt(6)
style.paragraph_format.line_spacing = Pt(15)

# ── Colors ──
PRIMARY  = RGBColor(0x1F, 0x35, 0x64)
SECONDARY = RGBColor(0x2E, 0x74, 0xB5)
ACCENT   = RGBColor(0x00, 0xB0, 0xF0)
TEXT_C   = RGBColor(0x1A, 0x1A, 0x1A)
MUTED    = RGBColor(0x66, 0x66, 0x80)

def heading(text, level=1):
    p = doc.add_heading(text, level=level)
    run = p.runs[0] if p.runs else p.add_run(text)
    run.font.color.rgb = PRIMARY if level == 1 else SECONDARY
    run.font.bold = True
    run.font.name = "Calibri"
    sizes = {{1: 22, 2: 16, 3: 13}}
    run.font.size = Pt(sizes.get(level, 12))
    if level == 2:
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(6)
        # Add colored bottom border
        pPr = p._p.get_or_add_pPr()
        pBdr = pPr.makeelement(qn('w:pBdr'), {{}})
        bottom = pBdr.makeelement(qn('w:bottom'), {{
            qn('w:val'): 'single', qn('w:sz'): '6',
            qn('w:space'): '1', qn('w:color'): '2E74B5'
        }})
        pBdr.append(bottom)
        pPr.append(pBdr)
    return p

def body(text):
    p = doc.add_paragraph(text)
    p.paragraph_format.space_after = Pt(8)
    for run in p.runs:
        run.font.color.rgb = TEXT_C
        run.font.name = "Calibri"
    return p

def bullet(text):
    p = doc.add_paragraph(text, style='List Bullet')
    p.paragraph_format.space_after = Pt(3)
    for run in p.runs:
        run.font.name = "Calibri"
    return p

def numbered(text):
    p = doc.add_paragraph(text, style='List Number')
    p.paragraph_format.space_after = Pt(3)
    for run in p.runs:
        run.font.name = "Calibri"
    return p

def callout(text):
    """Indented callout block with accent styling."""
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(1.0)
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(8)
    # Add colored left border via XML
    pPr = p._p.get_or_add_pPr()
    pBdr = pPr.makeelement(qn('w:pBdr'), {{}})
    left = pBdr.makeelement(qn('w:left'), {{
        qn('w:val'): 'single', qn('w:sz'): '18',
        qn('w:space'): '8', qn('w:color'): '2E74B5'
    }})
    pBdr.append(left)
    pPr.append(pBdr)
    # Shading
    shd = pPr.makeelement(qn('w:shd'), {{
        qn('w:val'): 'clear', qn('w:fill'): 'F2F4F8'
    }})
    pPr.append(shd)
    run = p.add_run(text)
    run.font.color.rgb = TEXT_C
    run.font.size = Pt(10)
    run.font.italic = True
    run.font.name = "Calibri"
    return p

def kv_table(pairs):
    """Key-value info table — for metadata, specs, etc."""
    table = doc.add_table(rows=len(pairs), cols=2)
    table.style = 'Light Grid Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (k, v) in enumerate(pairs):
        kc = table.rows[i].cells[0]
        vc = table.rows[i].cells[1]
        kr = kc.paragraphs[0].add_run(str(k))
        kr.bold = True
        kr.font.size = Pt(10)
        kr.font.name = "Calibri"
        vr = vc.paragraphs[0].add_run(str(v))
        vr.font.size = Pt(10)
        vr.font.name = "Calibri"

def add_table(headers, rows):
    table = doc.add_table(rows=1+len(rows), cols=len(headers))
    table.style = 'Light Grid Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        run = cell.paragraphs[0].add_run(str(h))
        run.bold = True
        run.font.size = Pt(10)
        run.font.name = "Calibri"
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = table.rows[ri+1].cells[ci]
            run = cell.paragraphs[0].add_run(str(val))
            run.font.size = Pt(10)
            run.font.name = "Calibri"

# ── Build Document ──

# Title
heading({repr(title)}, level=1)

# Thin accent line under title
p = doc.add_paragraph()
pPr = p._p.get_or_add_pPr()
pBdr = pPr.makeelement(qn('w:pBdr'), {{}})
bottom = pBdr.makeelement(qn('w:bottom'), {{
    qn('w:val'): 'single', qn('w:sz'): '12',
    qn('w:space'): '1', qn('w:color'): '00B0F0'
}})
pBdr.append(bottom)
pPr.append(pBdr)

{sections_code}

# Footer with generation note
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(24)
run = p.add_run("Generated by RAPR AI")
run.font.size = Pt(8)
run.font.color.rgb = MUTED
run.font.italic = True
run.font.name = "Calibri"

doc.save({repr(filename)})
print("Created " + {repr(filename)})
'''
