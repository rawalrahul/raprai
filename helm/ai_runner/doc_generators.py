"""
helm/ai_runner/doc_generators.py — Document generation code generators.

Covers: _generate_pptx_code, _generate_pdf_code, _generate_docx_code.
These functions generate complete Python code strings that can be executed
to create PowerPoint presentations, PDF documents, and Word documents.
"""


def _generate_pptx_code(filename: str, title: str, subtitle: str, slides: list) -> str:
    """Generate complete Python code from the ollama-pptx skill template."""
    slide_calls = []
    for s in slides:
        stype = s.get("type", "content")
        if stype == "content":
            t = repr(s.get("title", ""))
            b = repr(s.get("bullets", []))
            slide_calls.append(f"content_slide({t}, {b})")
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

    slide_code = "\n".join(slide_calls)

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

BG      = RGBColor(0x0D, 0x1B, 0x2A)
ACCENT1 = RGBColor(0x00, 0xC9, 0xFF)
ACCENT2 = RGBColor(0xFF, 0x6B, 0x35)
TITLE_C = RGBColor(0xFF, 0xFF, 0xFF)
BODY_C  = RGBColor(0xCC, 0xDD, 0xEE)
MUTED_C = RGBColor(0x77, 0x99, 0xAA)
BAR_C   = ACCENT1

SW = prs.slide_width
SH = prs.slide_height

def solid(shape, color):
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()

def rect(slide, x, y, w, h, color):
    s = slide.shapes.add_shape(1, Inches(x), Inches(y), Inches(w), Inches(h))
    solid(s, color)
    return s

def txt(slide, text, x, y, w, h, size=24, color=None, bold=False, align=PP_ALIGN.LEFT, italic=False):
    if color is None:
        color = TITLE_C
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tb.line.fill.background()
    tf = tb.text_frame
    tf.word_wrap = True
    p  = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size  = Pt(size)
    run.font.color.rgb = color
    run.font.bold  = bold
    run.font.italic = italic
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
        bar_color = BAR_C
    if h is None:
        h = SH.inches
    rect(slide, x, y, w, h, bar_color)

def bottom_strip(slide, color=None, height=0.08):
    if color is None:
        color = ACCENT1
    rect(slide, 0, SH.inches - height, SW.inches, height, color)

def title_slide(title_text, subtitle_text=""):
    slide = prs.slides.add_slide(BLANK)
    bg(slide)
    rect(slide, 7.8, 0, 5.53, 3.2, RGBColor(0x00, 0x40, 0x60))
    accent_bar(slide, ACCENT1, x=0, y=0, w=0.08, h=SH.inches)
    txt(slide, title_text, x=0.5, y=2.2, w=8.5, h=1.8, size=52, color=TITLE_C, bold=True)
    if subtitle_text:
        txt(slide, subtitle_text, x=0.5, y=4.2, w=8.0, h=0.8, size=22, color=ACCENT1)
    bottom_strip(slide)
    return slide

def content_slide(title_text, bullets):
    slide = prs.slides.add_slide(BLANK)
    bg(slide)
    rect(slide, 0, 0, SW.inches, 1.2, RGBColor(0x0A, 0x14, 0x22))
    accent_bar(slide, ACCENT1, x=0, y=0, w=0.06, h=SH.inches)
    txt(slide, title_text, x=0.25, y=0.15, w=12.5, h=0.9, size=30, color=TITLE_C, bold=True)
    rect(slide, 0.25, 1.2, 12.8, 0.04, ACCENT1)
    y_pos = 1.5
    for bullet in bullets:
        rect(slide, 0.35, y_pos + 0.07, 0.12, 0.12, ACCENT1)
        txt(slide, bullet, x=0.6, y=y_pos, w=12.1, h=0.55, size=20, color=BODY_C)
        y_pos += 0.65
    bottom_strip(slide)
    return slide

def two_col_slide(title_text, left_title, left_items, right_title, right_items):
    slide = prs.slides.add_slide(BLANK)
    bg(slide)
    rect(slide, 0, 0, SW.inches, 1.1, RGBColor(0x0A, 0x14, 0x22))
    accent_bar(slide, ACCENT1, x=0, y=0, w=0.06, h=SH.inches)
    txt(slide, title_text, x=0.25, y=0.12, w=12.5, h=0.85, size=28, color=TITLE_C, bold=True)
    rect(slide, 6.6, 1.2, 0.04, 5.9, RGBColor(0x1A, 0x3A, 0x5A))
    txt(slide, left_title, x=0.4, y=1.3, w=5.8, h=0.6, size=18, color=ACCENT1, bold=True)
    y = 2.0
    for item in left_items:
        rect(slide, 0.4, y + 0.08, 0.1, 0.1, ACCENT1)
        txt(slide, item, x=0.6, y=y, w=5.6, h=0.5, size=17, color=BODY_C)
        y += 0.6
    txt(slide, right_title, x=6.9, y=1.3, w=6.0, h=0.6, size=18, color=ACCENT2, bold=True)
    y = 2.0
    for item in right_items:
        rect(slide, 6.9, y + 0.08, 0.1, 0.1, ACCENT2)
        txt(slide, item, x=7.1, y=y, w=5.8, h=0.5, size=17, color=BODY_C)
        y += 0.6
    bottom_strip(slide)
    return slide

def stat_slide(stat_value, stat_label, context_text=""):
    slide = prs.slides.add_slide(BLANK)
    bg(slide)
    rect(slide, 1.5, 1.2, 10.3, 3.2, RGBColor(0x00, 0x30, 0x50))
    rect(slide, 1.5, 1.2, 0.15, 3.2, ACCENT1)
    txt(slide, stat_value, x=2.0, y=1.4, w=9.0, h=1.8, size=80, color=ACCENT1, bold=True, align=PP_ALIGN.CENTER)
    txt(slide, stat_label, x=2.0, y=3.1, w=9.0, h=0.8, size=22, color=TITLE_C, align=PP_ALIGN.CENTER)
    if context_text:
        txt(slide, context_text, x=1.5, y=4.8, w=10.3, h=0.6, size=16, color=MUTED_C, align=PP_ALIGN.CENTER, italic=True)
    bottom_strip(slide)
    return slide

def section_slide(section_number, section_title):
    slide = prs.slides.add_slide(BLANK)
    bg(slide)
    rect(slide, 0, 0, 4.5, SH.inches, RGBColor(0x00, 0x35, 0x55))
    txt(slide, str(section_number), x=0.5, y=1.8, w=3.5, h=2.5, size=120, color=ACCENT1, bold=True, align=PP_ALIGN.CENTER)
    txt(slide, section_title, x=5.0, y=2.8, w=7.8, h=1.5, size=36, color=TITLE_C, bold=True)
    rect(slide, 5.0, 2.65, 7.8, 0.06, ACCENT1)
    bottom_strip(slide)
    return slide

title_slide({repr(title)}, {repr(subtitle or '')})
{slide_code}
prs.save({repr(filename)})
print("Created " + {repr(filename)})
'''


def _generate_pdf_code(filename: str, title: str, subtitle: str, sections: list) -> str:
    """Generate complete Python code from the ollama-pdf skill template."""
    section_code_parts = []
    for s in sections:
        h = s.get("heading", "")
        section_code_parts.append(f"story.append(Paragraph({repr(h)}, H2))")
        for p in s.get("paragraphs", []):
            section_code_parts.append(f"story.append(Paragraph({repr(p)}, BODY))")
        if s.get("bullets"):
            items_repr = repr(s["bullets"])
            section_code_parts.append(f"story.extend(bullets({items_repr}))")
        if s.get("callout"):
            section_code_parts.append(f"story.append(callout_box({repr(s['callout'])}))")
        if s.get("table_headers") and s.get("table_rows"):
            section_code_parts.append(
                f"story.append(styled_table({repr(s['table_headers'])}, {repr(s['table_rows'])}))"
            )
        if s.get("page_break"):
            section_code_parts.append("story.append(PageBreak())")
        section_code_parts.append("story.append(divider())")

    sections_code = "\n".join(section_code_parts)

    return f'''\
import subprocess, sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab", "-q"])
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak, KeepTogether
PAGE_W, PAGE_H = A4
MARGIN = 2.2 * cm
C_DARK_BLUE  = colors.HexColor('#1F3564')
C_MID_BLUE   = colors.HexColor('#2E74B5')
C_TEAL       = colors.HexColor('#0070C0')
C_ACCENT     = colors.HexColor('#00B0F0')
C_ORANGE     = colors.HexColor('#FF6B35')
C_LIGHT_GREY = colors.HexColor('#F2F4F8')
C_WHITE      = colors.white
C_TEXT       = colors.HexColor('#1A1A2E')
C_MUTED      = colors.HexColor('#666680')
_base = getSampleStyleSheet()
H1 = ParagraphStyle('H1', parent=_base['Heading1'], fontName='Helvetica-Bold', fontSize=22, textColor=C_DARK_BLUE, spaceBefore=18, spaceAfter=8, leading=26)
H2 = ParagraphStyle('H2', parent=_base['Heading2'], fontName='Helvetica-Bold', fontSize=15, textColor=C_MID_BLUE, spaceBefore=14, spaceAfter=5, leading=19)
BODY = ParagraphStyle('Body', parent=_base['Normal'], fontName='Helvetica', fontSize=10.5, textColor=C_TEXT, leading=16, spaceAfter=7, alignment=TA_JUSTIFY)
BULLET_STYLE = ParagraphStyle('Bullet', parent=BODY, leftIndent=14, firstLineIndent=-10, spaceAfter=4)
CAPTION = ParagraphStyle('Caption', parent=BODY, fontSize=8.5, textColor=C_MUTED, alignment=TA_CENTER, spaceAfter=6)
CALLOUT = ParagraphStyle('Callout', parent=BODY, fontName='Helvetica', fontSize=10, textColor=C_TEXT, backColor=C_LIGHT_GREY, leftIndent=12, rightIndent=12, spaceBefore=8, spaceAfter=8, borderPadding=(8,10,8,10), leading=15)

def divider(color=C_MID_BLUE, thickness=1.5):
    return HRFlowable(width='100%', thickness=thickness, color=color, spaceAfter=8, spaceBefore=8)

def bullets(items):
    flowables = []
    for item in items:
        flowables.append(Paragraph(f'\\u2022 ' + item, BULLET_STYLE))
    return flowables

def callout_box(text, label="Note"):
    label_html = '<font color="#2E74B5" name="Helvetica-Bold">' + label + '  </font>'
    return Paragraph(label_html + text, CALLOUT)

def styled_table(headers, rows, col_widths=None):
    all_rows = [headers] + rows
    header_style = ParagraphStyle('th', parent=BODY, fontName='Helvetica-Bold', textColor=C_WHITE, fontSize=10)
    cell_style = ParagraphStyle('td', parent=BODY, fontSize=10)
    all_data = []
    for ri, row in enumerate(all_rows):
        styled = [Paragraph(str(v), header_style if ri==0 else cell_style) for v in row]
        all_data.append(styled)
    if col_widths is None:
        avail = PAGE_W - 2 * MARGIN
        col_widths = [avail / len(headers)] * len(headers)
    t = Table(all_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_DARK_BLUE),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_WHITE, C_LIGHT_GREY]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#C8D0DC')),
        ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8), ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    return t

_DOC_TITLE = {repr(title)}
def _header_footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(C_DARK_BLUE)
    canvas.rect(0, h - 1.2*cm, w, 1.2*cm, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont('Helvetica-Bold', 10)
    canvas.drawString(MARGIN, h - 0.8*cm, _DOC_TITLE)
    canvas.setFillColor(C_LIGHT_GREY)
    canvas.rect(0, 0, w, 1.0*cm, fill=1, stroke=0)
    canvas.setFillColor(C_MUTED)
    canvas.setFont('Helvetica', 8)
    canvas.drawString(MARGIN, 0.35*cm, 'Generated Document')
    canvas.drawRightString(w - MARGIN, 0.35*cm, f'Page {{doc.page}}')
    canvas.restoreState()

doc = SimpleDocTemplate({repr(filename)}, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN+1.5*cm, bottomMargin=MARGIN+0.8*cm)
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


def _generate_docx_code(filename: str, title: str, sections: list) -> str:
    """Generate complete Python code from the ollama-docx skill template."""
    section_code_parts = []
    for s in sections:
        h = s.get("heading", "")
        section_code_parts.append(f"heading({repr(h)}, level=2)")
        for p in s.get("paragraphs", []):
            section_code_parts.append(f"body({repr(p)})")
        for b in s.get("bullets", []):
            section_code_parts.append(f"bullet({repr(b)})")
        if s.get("table_headers") and s.get("table_rows"):
            section_code_parts.append(
                f"add_table({repr(s['table_headers'])}, {repr(s['table_rows'])})"
            )

    sections_code = "\n".join(section_code_parts)

    return f'''\
import subprocess, sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "python-docx", "-q"])
from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()
for section in doc.sections:
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(3.0)
    section.right_margin = Cm(2.5)
style = doc.styles['Normal']
style.font.name = 'Calibri'
style.font.size = Pt(11)
style.paragraph_format.space_after = Pt(6)
style.paragraph_format.line_spacing = Pt(14)
DARK_BLUE = RGBColor(0x1F, 0x35, 0x64)
MID_BLUE = RGBColor(0x2E, 0x74, 0xB5)
TEXT = RGBColor(0x1A, 0x1A, 0x1A)

def heading(text, level=1):
    p = doc.add_heading(text, level=level)
    run = p.runs[0] if p.runs else p.add_run(text)
    run.font.color.rgb = DARK_BLUE if level == 1 else MID_BLUE
    run.font.bold = True
    if level == 1:
        run.font.size = Pt(18)
    elif level == 2:
        run.font.size = Pt(14)
    else:
        run.font.size = Pt(12)
    return p

def body(text):
    p = doc.add_paragraph(text)
    for run in p.runs:
        run.font.color.rgb = TEXT
    return p

def bullet(text):
    p = doc.add_paragraph(text, style='List Bullet')
    p.paragraph_format.space_after = Pt(3)
    return p

def add_table(headers, rows):
    table = doc.add_table(rows=1+len(rows), cols=len(headers))
    table.style = 'Light Grid Accent 1'
    for i, h in enumerate(headers):
        table.rows[0].cells[i].text = h
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            table.rows[ri+1].cells[ci].text = str(val)

heading({repr(title)}, level=1)
{sections_code}
doc.save({repr(filename)})
print("Created " + {repr(filename)})
'''
