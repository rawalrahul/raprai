---
name: python-docx-engine
description: "Programmatic Word document creation with styling, tables, and professional layouts using python-docx"
category: office
difficulty: intermediate
model_boost: "Weak models confuse spacing (use space_after not blank paragraphs), hardcode styles instead of defining them, ignore cell padding, and create flat unstyled tables. This engine pattern prevents all of those."
---

# Python-DOCX Document Generation Engine

## Purpose
Generate professional Word documents (.docx) programmatically with consistent styling, proper typography, sophisticated table layouts, and adherence to document standards. This engine handles heading hierarchies, spacing rules, color-coded elements, and formatting that remains editable in Microsoft Word.

## When to Use
- Generating reports, proposals, or technical documentation from templates
- Creating styled documents with dynamic content (databases, APIs, user input)
- Building multi-section documents with tables of contents and headers/footers
- **Do NOT use when**: Creating pixel-perfect layouts requiring absolute positioning (use ReportLab), designing presentation decks (use python-pptx), or building interactive forms

## Instructions

### Step 1: Install and Import
```bash
pip install python-docx
```

```python
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_STYLE
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
```

### Step 2: Define Color Palette
Create a professional color palette at module level for consistency:

```python
# Professional Dark Blue/Teal Palette
COLORS = {
    'primary_dark': RGBColor(25, 55, 95),      # Dark blue #193F5F
    'primary_light': RGBColor(100, 180, 210),  # Light teal #64B4D2
    'accent': RGBColor(200, 50, 50),           # Red accent #C83232
    'text_dark': RGBColor(45, 45, 45),         # Near black #2D2D2D
    'text_light': RGBColor(120, 120, 120),     # Gray #787878
    'bg_light': RGBColor(240, 245, 250),       # Very light blue #F0F5FA
    'bg_callout': RGBColor(220, 240, 250),     # Light blue callout #DCF0FA
}
```

### Step 3: Create Helper Function - Shading
Add background color to paragraphs and table cells:

```python
def shade_cell(cell, color):
    """Add background color to table cell."""
    shading_elm = OxmlElement('w:shd')
    shading_elm.set(qn('w:fill'), color)
    cell._element.get_or_add_tcPr().append(shading_elm)

def shade_paragraph(paragraph, color):
    """Add background shading to paragraph."""
    shading_elm = OxmlElement('w:shd')
    shading_elm.set(qn('w:fill'), color)
    paragraph._element.get_or_add_pPr().append(shading_elm)
```

### Step 4: Create Helper Function - Horizontal Rule
Insert visual dividers between sections:

```python
def add_horizontal_rule(doc, color=COLORS['primary_dark'], thickness_pt=1):
    """Add a horizontal rule (line) to document."""
    p = doc.add_paragraph()
    pPr = p._element.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), str(int(thickness_pt * 8)))  # eighths of a point
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), color.rgb if hasattr(color, 'rgb') else color)
    pBdr.append(bottom)
    pPr.append(pBdr)
    p.space_after = Pt(12)
```

### Step 5: Set Document Margins
Control page layout from the start:

```python
def set_margins(doc, top=1, bottom=1, left=1, right=1):
    """Set document margins in inches."""
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(top)
        section.bottom_margin = Inches(bottom)
        section.left_margin = Inches(left)
        section.right_margin = Inches(right)
```

### Step 6: Define Paragraph Styles
Create reusable, consistent text styles:

```python
def setup_styles(doc):
    """Define all custom paragraph and character styles."""
    styles = doc.styles

    # Heading 1 - Section titles
    h1 = styles['Heading 1']
    h1.font.size = Pt(28)
    h1.font.bold = True
    h1.font.color.rgb = COLORS['primary_dark']
    h1.space_before = Pt(18)
    h1.space_after = Pt(12)
    h1.paragraph_format.line_spacing = 1.15

    # Heading 2 - Subsection titles
    h2 = styles['Heading 2']
    h2.font.size = Pt(18)
    h2.font.bold = True
    h2.font.color.rgb = COLORS['primary_light']
    h2.space_before = Pt(12)
    h2.space_after = Pt(8)

    # Heading 3 - Sub-subsection titles
    h3 = styles['Heading 3']
    h3.font.size = Pt(14)
    h3.font.bold = True
    h3.font.color.rgb = COLORS['text_dark']
    h3.space_before = Pt(10)
    h3.space_after = Pt(6)

    # Normal body text
    body = styles['Normal']
    body.font.size = Pt(11)
    body.font.color.rgb = COLORS['text_dark']
    body.space_after = Pt(6)
    body.paragraph_format.line_spacing = 1.15

    # List Bullet
    bullet = styles['List Bullet']
    bullet.font.size = Pt(11)
    bullet.space_after = Pt(4)

    # List Number
    number = styles['List Number']
    number.font.size = Pt(11)
    number.space_after = Pt(4)
```

### Step 7: Add Styled Heading
Insert headings with automatic styling:

```python
def add_heading(doc, text, level=1):
    """Add a heading with proper styling (level 1-3)."""
    h = doc.add_heading(text, level=level)
    if level == 1:
        h.space_before = Pt(18)
        h.space_after = Pt(12)
    return h
```

### Step 8: Create Professional Tables with Styling
Build tables with proper formatting, padding, and alternating rows:

```python
def add_styled_table(doc, data, header_row=True, color_header=True):
    """
    Add a table with professional styling.
    data: list of lists (rows)
    header_row: bool - first row is header
    color_header: bool - use color for header
    """
    rows = len(data)
    cols = len(data[0])
    table = doc.add_table(rows=rows, cols=cols)
    table.style = 'Light Grid Accent 1'

    # Fill in data
    for i, row_data in enumerate(data):
        row = table.rows[i]
        for j, cell_data in enumerate(row_data):
            cell = row.cells[j]
            cell.text = str(cell_data)

            # Format header row
            if header_row and i == 0:
                if color_header:
                    shade_cell(cell, 'FF' + COLORS['primary_dark'].rgb[1:])

                # Header text formatting
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.bold = True
                        run.font.color.rgb = RGBColor(255, 255, 255)
                        run.font.size = Pt(11)
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                # Alternate row colors
                if i % 2 == 1:
                    shade_cell(cell, 'FFF0F5FA')

                # Cell padding
                tcPr = cell._element.get_or_add_tcPr()
                tcMar = OxmlElement('w:tcMar')
                for margin_name in ['top', 'left', 'bottom', 'right']:
                    margin_el = OxmlElement(f'w:{margin_name}')
                    margin_el.set(qn('w:w'), '100')
                    margin_el.set(qn('w:type'), 'dxa')
                    tcMar.append(margin_el)
                tcPr.append(tcMar)

    return table
```

### Step 9: Add Callout Boxes
Create highlighted information boxes:

```python
def add_callout_box(doc, text, box_type='info'):
    """
    Add a colored callout box.
    box_type: 'info' (blue), 'warning' (yellow), 'error' (red)
    """
    color_map = {
        'info': 'FFDCF0FA',
        'warning': 'FFFFF3CD',
        'error': 'FFFFE0E0',
    }

    p = doc.add_paragraph(text, style='Normal')
    shade_paragraph(p, color_map.get(box_type, color_map['info']))

    # Add left border
    pPr = p._element.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    left = OxmlElement('w:left')
    left.set(qn('w:val'), 'single')
    left.set(qn('w:sz'), '24')  # 3pt border
    left.set(qn('w:space'), '0')
    left.set(qn('w:color'), COLORS['accent'].rgb[1:])
    pBdr.append(left)
    pPr.append(pBdr)

    # Padding
    p.paragraph_format.left_indent = Inches(0.2)
    p.space_before = Pt(6)
    p.space_after = Pt(6)
```

### Step 10: Add Images and Page Breaks
Insert images with captions and manage page flow:

```python
def add_image_with_caption(doc, image_path, width=Inches(5), caption=''):
    """Add image with optional caption."""
    doc.add_picture(image_path, width=width)
    last_paragraph = doc.paragraphs[-1]
    last_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

    if caption:
        cap = doc.add_paragraph(caption)
        cap.style = 'Normal'
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in cap.runs:
            run.font.italic = True
            run.font.size = Pt(9)
            run.font.color.rgb = COLORS['text_light']

def add_page_break(doc):
    """Insert a page break."""
    doc.add_page_break()

def add_section_break(doc):
    """Insert a section break with space."""
    add_horizontal_rule(doc)
    doc.add_paragraph()  # Spacing
```

### Step 11: Header and Footer
Add running headers/footers with page numbers:

```python
def add_header_footer(doc, header_text='', footer_text=''):
    """Add header and footer to document."""
    sections = doc.sections
    for section in sections:
        # Header
        if header_text:
            header = section.header
            h_para = header.paragraphs[0]
            h_para.text = header_text
            h_para.style = 'Normal'
            for run in h_para.runs:
                run.font.size = Pt(9)
                run.font.color.rgb = COLORS['text_light']

        # Footer with page numbers
        footer = section.footer
        f_para = footer.paragraphs[0]
        if footer_text:
            f_para.text = footer_text
        else:
            f_para.text = 'Page '

        # Add page number field
        if not footer_text:
            run = f_para.add_run()
            fldChar1 = OxmlElement('w:fldChar')
            fldChar1.set(qn('w:fldCharType'), 'begin')
            run._r.append(fldChar1)
            run = f_para.add_run()
            instrText = OxmlElement('w:instrText')
            instrText.set(qn('xml:space'), 'preserve')
            instrText.text = 'PAGE'
            run._r.append(instrText)
            run = f_para.add_run()
            fldChar2 = OxmlElement('w:fldChar')
            fldChar2.set(qn('w:fldCharType'), 'end')
            run._r.append(fldChar2)

        f_para.style = 'Normal'
        for run in f_para.runs:
            run.font.size = Pt(9)
```

## Complete Working Boilerplate

```python
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

COLORS = {
    'primary_dark': RGBColor(25, 55, 95),
    'primary_light': RGBColor(100, 180, 210),
    'accent': RGBColor(200, 50, 50),
    'text_dark': RGBColor(45, 45, 45),
    'text_light': RGBColor(120, 120, 120),
    'bg_light': RGBColor(240, 245, 250),
    'bg_callout': RGBColor(220, 240, 250),
}

def shade_cell(cell, color):
    shading_elm = OxmlElement('w:shd')
    shading_elm.set(qn('w:fill'), color)
    cell._element.get_or_add_tcPr().append(shading_elm)

def add_horizontal_rule(doc, color_hex='193F5F', thickness_pt=1):
    p = doc.add_paragraph()
    pPr = p._element.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), str(int(thickness_pt * 8)))
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), color_hex)
    pBdr.append(bottom)
    pPr.append(pBdr)
    p.space_after = Pt(12)

def setup_styles(doc):
    styles = doc.styles
    h1 = styles['Heading 1']
    h1.font.size = Pt(28)
    h1.font.bold = True
    h1.font.color.rgb = COLORS['primary_dark']
    h1.space_before = Pt(18)
    h1.space_after = Pt(12)

    h2 = styles['Heading 2']
    h2.font.size = Pt(18)
    h2.font.bold = True
    h2.font.color.rgb = COLORS['primary_light']
    h2.space_before = Pt(12)
    h2.space_after = Pt(8)

def add_styled_table(doc, data, header_row=True):
    rows, cols = len(data), len(data[0])
    table = doc.add_table(rows=rows, cols=cols)
    table.style = 'Light Grid Accent 1'

    for i, row_data in enumerate(data):
        for j, cell_data in enumerate(row_data):
            cell = table.rows[i].cells[j]
            cell.text = str(cell_data)
            if header_row and i == 0:
                shade_cell(cell, 'FF193F5F')
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.bold = True
                        run.font.color.rgb = RGBColor(255, 255, 255)
    return table

# Main document creation
doc = Document()
set_margins_simple(doc)
setup_styles(doc)
add_header_footer(doc, header_text='Professional Document', footer_text='Confidential')

doc.add_heading('Executive Summary', level=1)
doc.add_paragraph('This document demonstrates professional Word generation.')
add_horizontal_rule(doc)

doc.add_heading('Key Data', level=2)
data = [['Name', 'Value', 'Status'], ['Project A', '$50,000', 'Complete'], ['Project B', '$75,000', 'In Progress']]
add_styled_table(doc, data)

doc.save('professional_document.docx')
```

## Output Template
```
Expected .docx file with:
- Proper heading hierarchy (H1 28pt dark blue, H2 18pt teal, H3 14pt dark)
- Consistent body spacing (6pt after paragraphs, 1.15 line spacing)
- Tables with colored headers, alternating row colors, and proper cell padding
- Callout boxes with left border accent
- Professional margins (1" all sides)
- Editable in Microsoft Word with all formatting preserved
- Headers/footers with page numbers
```

## Quality Gates
1. **Spacing Verification**: Measure that space_after is used instead of blank paragraphs; verify 1.15 line spacing on body text
2. **Color Consistency**: Confirm header colors match palette (primary_dark, primary_light); verify no random colors in table cells
3. **Table Structure**: Check header row has bold white text on colored background; verify alternating rows use bg_light color
4. **Typography Hierarchy**: Verify H1=28pt bold, H2=18pt bold, H3=14pt bold with proper vertical spacing
5. **Cell Padding**: Inspect table cells have left/right padding; verify no text touching cell borders
6. **Editability**: Open generated .docx in Microsoft Word; confirm all formatting is preserved and document is fully editable

## Examples

### Good Example
```python
doc = Document()
set_margins(doc, top=1, bottom=1, left=1, right=1)
setup_styles(doc)

# Use space_after on paragraphs
p = doc.add_paragraph('Body text here')
p.space_after = Pt(6)

# Use colors from palette
table_data = [['Col1', 'Col2'], ['Data1', 'Data2']]
add_styled_table(doc, table_data, header_row=True)

# Professional spacing between sections
add_horizontal_rule(doc)
doc.add_heading('New Section', level=1)
```

### Bad Example
```python
doc = Document()
# Missing margin setup
# Missing style initialization

# Creates flat unstyled table
table = doc.add_table(rows=2, cols=2)
for cell in table.rows[0].cells:
    cell.text = 'Header'
# No color, no formatting, no padding

# Improper spacing using blank paragraphs
doc.add_paragraph('')
doc.add_paragraph('')
doc.add_paragraph('Next content')
# Hard to control, inconsistent
```

## Common Mistakes

1. **Using Blank Paragraphs for Spacing**: `doc.add_paragraph('')` creates unpredictable gaps. Instead, use `p.space_after = Pt(6)` on the paragraph before.

2. **Ignoring Cell Padding in Tables**: Text runs edge-to-edge against cell borders, looking cramped. Always apply tcMar (table cell margins) with 100 twips (≈7pt) on all sides.

3. **Hardcoding Style Properties**: Repeating `run.font.size = Pt(11)` throughout code. Instead, define styles once in `setup_styles()` and apply via `style='Normal'`.

4. **Forgetting Margin Setup**: Documents default to 1.25" margins; explicitly call `set_margins()` at the start of every document for consistency.

5. **Not Using Palette Colors**: Hardcoding RGB values like `RGBColor(255, 0, 0)` creates inconsistent branding. Define COLORS dict and reference consistently.

## Anti-Patterns

1. **Creating Tables Without Headers**: Tables without colored, bold headers look amateurish. Always use first row as header with distinct styling.

2. **Mixing Heading Levels Randomly**: Jumping from H1 to H3 without H2 breaks document structure and confuses table-of-contents generation. Use hierarchical: H1 → H2 → H3.

3. **Applying Direct Formatting Over Styles**: `run.font.size = Pt(14)` instead of using styles makes global changes impossible. Always leverage style system.

4. **Setting Line Spacing on Every Paragraph**: Each paragraph manually set to 1.15 spacing is redundant. Define once in style setup, apply via `style='Normal'`.

5. **Not Controlling Section Spacing**: Random space_before/space_after creates "floating" sections. Use consistent before/after rules: H1 gets 18pt before, 12pt after; body gets 6pt after.
