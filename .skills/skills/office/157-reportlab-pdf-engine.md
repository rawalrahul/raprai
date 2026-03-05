---
name: reportlab-pdf-engine
description: "Professional PDF creation with custom styles, tables, headers/footers, and multi-layout support using ReportLab"
category: office
difficulty: intermediate
model_boost: "Weak models forget style definitions and hardcode formatting on every element, don't implement proper header/footer callbacks, miss table styling hooks, and ignore Spacer elements. This engine pattern ensures scalable, reusable, consistent PDF generation."
---

# ReportLab PDF Generation Engine

## Purpose
Generate pixel-perfect, professional PDFs programmatically with complete control over typography, colors, spacing, tables, and multi-page layouts. ReportLab creates PDFs that render identically across all viewers and support headers, footers, page numbers, and complex table styling using the Platypus flowable architecture.

## When to Use
- Generating branded reports with headers/footers and consistent styling
- Creating multi-page documents with dynamic content from databases or APIs
- Building styled tables with merged cells, colored backgrounds, and custom padding
- **Do NOT use when**: Creating editable documents (use python-docx), building presentations (use python-pptx), or designing interactive forms (use acrobat APIs)

## Instructions

### Step 1: Install and Import
```bash
pip install reportlab
```

```python
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm, pt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Image
from reportlab.pdfgen import canvas
from datetime import datetime
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
```

### Step 2: Define Color Palette
Create professional color constants for consistent branding:

```python
# Professional Dark Blue/Teal Palette
PALETTE = {
    'primary_dark': colors.HexColor('#193F5F'),      # Dark blue
    'primary_light': colors.HexColor('#64B4D2'),     # Light teal
    'accent': colors.HexColor('#C83232'),            # Red accent
    'text_dark': colors.HexColor('#2D2D2D'),         # Near black
    'text_light': colors.HexColor('#787878'),        # Gray
    'bg_light': colors.HexColor('#F0F5FA'),          # Very light blue
    'bg_callout': colors.HexColor('#DCF0FA'),        # Light blue callout
    'border': colors.HexColor('#B0B0B0'),            # Light gray border
    'white': colors.whitesmoke,
}
```

### Step 3: Create Custom Paragraph Styles
Define all text styles for reuse throughout document:

```python
def create_styles():
    """Return dictionary of all custom paragraph styles."""
    styles_dict = {}

    # Heading 1 - Section titles
    styles_dict['Heading1'] = ParagraphStyle(
        name='Heading1',
        parent=getSampleStyleSheet()['Heading1'],
        fontSize=28,
        textColor=PALETTE['primary_dark'],
        spaceAfter=12,
        spaceBefore=18,
        leading=32,
        fontName='Helvetica-Bold',
        alignment=TA_LEFT,
    )

    # Heading 2 - Subsection titles
    styles_dict['Heading2'] = ParagraphStyle(
        name='Heading2',
        parent=getSampleStyleSheet()['Heading2'],
        fontSize=18,
        textColor=PALETTE['primary_light'],
        spaceAfter=8,
        spaceBefore=12,
        leading=22,
        fontName='Helvetica-Bold',
    )

    # Heading 3 - Sub-subsection
    styles_dict['Heading3'] = ParagraphStyle(
        name='Heading3',
        fontSize=14,
        textColor=PALETTE['text_dark'],
        spaceAfter=6,
        spaceBefore=10,
        leading=17,
        fontName='Helvetica-Bold',
    )

    # Body text - Default paragraph style
    styles_dict['BodyText'] = ParagraphStyle(
        name='BodyText',
        fontSize=11,
        textColor=PALETTE['text_dark'],
        spaceAfter=6,
        leading=15,
        alignment=TA_JUSTIFY,
        fontName='Helvetica',
    )

    # Bullet list style
    styles_dict['BulletList'] = ParagraphStyle(
        name='BulletList',
        fontSize=11,
        textColor=PALETTE['text_dark'],
        spaceAfter=4,
        leading=14,
        leftIndent=20,
        fontName='Helvetica',
    )

    # Caption style for images
    styles_dict['Caption'] = ParagraphStyle(
        name='Caption',
        fontSize=9,
        textColor=PALETTE['text_light'],
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique',
    )

    # Callout box style
    styles_dict['Callout'] = ParagraphStyle(
        name='Callout',
        fontSize=11,
        textColor=PALETTE['text_dark'],
        spaceAfter=12,
        spaceBefore=12,
        leading=14,
        leftIndent=12,
        rightIndent=12,
        fontName='Helvetica',
    )

    return styles_dict

# Create global styles dictionary
STYLES = create_styles()
```

### Step 4: Helper Function - Horizontal Rule
Create visual dividers:

```python
def divider(color=PALETTE['primary_dark'], width=6.5*inch, height=1*pt):
    """Create a horizontal rule flowable."""
    return HRFlowable(width=width, height=height, color=color, spaceBefore=12, spaceAfter=12)
```

### Step 5: Helper Function - Bullet Points
Format bulleted lists:

```python
def bullet_list(items, style=None):
    """Convert list of strings to Paragraph bullets."""
    if style is None:
        style = STYLES['BulletList']

    flowables = []
    for item in items:
        p = Paragraph(f"• {item}", style)
        flowables.append(p)
    return flowables
```

### Step 6: Helper Function - Callout Box
Create highlighted information sections:

```python
def callout_box(text, box_type='info'):
    """Create a colored callout box with border."""
    bg_color_map = {
        'info': PALETTE['bg_callout'],
        'warning': colors.HexColor('#FFFFF3CD'),
        'error': colors.HexColor('#FFFFE0E0'),
    }

    bg = bg_color_map.get(box_type, PALETTE['bg_callout'])

    # Create table to manage background
    data = [[Paragraph(text, STYLES['Callout'])]]
    table = Table(data, colWidths=[6*inch])

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg),
        ('BORDER', (0, 0), (-1, -1), 2, PALETTE['accent']),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    return table
```

### Step 7: Helper Function - Styled Tables
Create professional tables with colors and formatting:

```python
def styled_table(data, header_row=True, col_widths=None):
    """
    Create a styled table.
    data: list of lists
    header_row: bool - color first row as header
    col_widths: list of widths or None for auto
    """
    if col_widths is None:
        col_widths = [6.5 * inch / len(data[0])] * len(data[0])

    table = Table(data, colWidths=col_widths)

    style = [
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 11) if header_row else (),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, PALETTE['border']),
    ]

    # Header styling
    if header_row:
        style.extend([
            ('BACKGROUND', (0, 0), (-1, 0), PALETTE['primary_dark']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ])
        # Alternating row colors for data rows
        for i in range(1, len(data)):
            if i % 2 == 0:
                style.append(('BACKGROUND', (0, i), (-1, i), PALETTE['bg_light']))

    table.setStyle(TableStyle(style))
    return table
```

### Step 8: Header/Footer with Page Numbers
Create callbacks for page-level elements:

```python
def header_footer_callback(canvas, doc, header_text='', footer_text='', logo_path=None):
    """
    Create a callback function for headers and footers.
    Returns function for SimpleDocTemplate's onFirstPage and onLaterPages.
    """
    def on_page(canvas, doc):
        canvas.saveState()

        # Header
        if header_text:
            canvas.setFont('Helvetica', 9)
            canvas.setFillColor(PALETTE['text_light'])
            canvas.drawString(0.5*inch, 10.5*inch, header_text)

            # Draw header line
            canvas.setStrokeColor(PALETTE['border'])
            canvas.line(0.5*inch, 10.45*inch, 7.5*inch, 10.45*inch)

        # Footer with page number
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(PALETTE['text_light'])

        if footer_text:
            canvas.drawString(0.5*inch, 0.5*inch, footer_text)

        # Page number
        page_num = f'Page {doc.page}'
        canvas.drawString(7*inch, 0.5*inch, page_num)

        canvas.restoreState()

    return on_page
```

### Step 9: Document Setup Function
Initialize a document with proper configuration:

```python
def setup_document(filename, title='', author='', page_size=letter):
    """
    Create and configure a SimpleDocTemplate.

    Returns:
        doc: SimpleDocTemplate instance
        story: empty list for flowables
    """
    # Calculate margins
    left_margin = 0.75 * inch
    right_margin = 0.75 * inch
    top_margin = 1 * inch
    bottom_margin = 0.75 * inch

    doc = SimpleDocTemplate(
        filename,
        pagesize=page_size,
        leftMargin=left_margin,
        rightMargin=right_margin,
        topMargin=top_margin,
        bottomMargin=bottom_margin,
        title=title,
        author=author,
    )

    story = []
    return doc, story
```

### Step 10: Multi-Column Layout
Create parallel content columns:

```python
def two_column_layout(left_content, right_content, widths=None):
    """
    Create a two-column table layout.

    left_content: list of flowables
    right_content: list of flowables
    widths: [left_width, right_width] or None for equal
    """
    if widths is None:
        widths = [3.25*inch, 3.25*inch]

    # Wrap content in cells
    left_cell = [[item] for item in left_content]
    right_cell = [[item] for item in right_content]

    data = [
        [Paragraph('<b>Left Column</b>', STYLES['Heading3']),
         Paragraph('<b>Right Column</b>', STYLES['Heading3'])],
        [left_cell, right_cell]
    ]

    table = Table(data, colWidths=widths)
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BORDER', (0, 0), (-1, -1), 1, PALETTE['border']),
    ]))

    return table
```

### Step 11: Build and Output
Generate final PDF:

```python
def build_pdf(doc, story, on_page_callback=None):
    """
    Build the PDF document.

    doc: SimpleDocTemplate instance
    story: list of flowables
    on_page_callback: function(canvas, doc) for custom page handling
    """
    if on_page_callback:
        doc.build(story, onFirstPage=on_page_callback, onLaterPages=on_page_callback)
    else:
        doc.build(story)
```

## Complete Working Boilerplate

```python
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch, pt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from datetime import datetime

PALETTE = {
    'primary_dark': colors.HexColor('#193F5F'),
    'primary_light': colors.HexColor('#64B4D2'),
    'accent': colors.HexColor('#C83232'),
    'text_dark': colors.HexColor('#2D2D2D'),
    'text_light': colors.HexColor('#787878'),
    'bg_light': colors.HexColor('#F0F5FA'),
    'border': colors.HexColor('#B0B0B0'),
    'white': colors.whitesmoke,
}

def create_styles():
    return {
        'Heading1': ParagraphStyle(name='Heading1', fontSize=28, textColor=PALETTE['primary_dark'],
                                   spaceAfter=12, spaceBefore=18, fontName='Helvetica-Bold'),
        'Heading2': ParagraphStyle(name='Heading2', fontSize=18, textColor=PALETTE['primary_light'],
                                   spaceAfter=8, spaceBefore=12, fontName='Helvetica-Bold'),
        'BodyText': ParagraphStyle(name='BodyText', fontSize=11, textColor=PALETTE['text_dark'],
                                   spaceAfter=6, leading=15, alignment=TA_JUSTIFY),
        'Caption': ParagraphStyle(name='Caption', fontSize=9, textColor=PALETTE['text_light'],
                                  spaceAfter=12, alignment=TA_CENTER, fontName='Helvetica-Oblique'),
    }

STYLES = create_styles()

def divider(color=PALETTE['primary_dark']):
    return HRFlowable(width=6.5*inch, height=1*pt, color=color, spaceBefore=12, spaceAfter=12)

def styled_table(data, header_row=True):
    table = Table(data, colWidths=[6.5*inch/len(data[0])]*len(data[0]))
    style = [
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, PALETTE['border']),
    ]
    if header_row:
        style.extend([
            ('BACKGROUND', (0, 0), (-1, 0), PALETTE['primary_dark']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 11),
        ])
        for i in range(1, len(data)):
            if i % 2 == 0:
                style.append(('BACKGROUND', (0, i), (-1, i), PALETTE['bg_light']))

    table.setStyle(TableStyle(style))
    return table

def header_footer_callback(header_text='', footer_text=''):
    def on_page(canvas, doc):
        canvas.saveState()
        if header_text:
            canvas.setFont('Helvetica', 9)
            canvas.setFillColor(PALETTE['text_light'])
            canvas.drawString(0.5*inch, 10.5*inch, header_text)
            canvas.setStrokeColor(PALETTE['border'])
            canvas.line(0.5*inch, 10.45*inch, 7.5*inch, 10.45*inch)
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(PALETTE['text_light'])
        canvas.drawString(0.5*inch, 0.5*inch, footer_text or '')
        canvas.drawString(7*inch, 0.5*inch, f'Page {doc.page}')
        canvas.restoreState()
    return on_page

# Build document
doc = SimpleDocTemplate('professional_report.pdf', pagesize=letter,
                        leftMargin=0.75*inch, rightMargin=0.75*inch)
story = []

story.append(Paragraph('Executive Report', STYLES['Heading1']))
story.append(Spacer(1, 0.2*inch))
story.append(Paragraph('This is a professional PDF generated with ReportLab.', STYLES['BodyText']))
story.append(divider())

story.append(Paragraph('Key Metrics', STYLES['Heading2']))
data = [['Metric', 'Value'], ['Revenue', '$1.2M'], ['Growth', '+15%']]
story.append(styled_table(data, header_row=True))
story.append(Spacer(1, 0.2*inch))

story.append(PageBreak())
story.append(Paragraph('Summary', STYLES['Heading2']))
story.append(Paragraph('Document complete.', STYLES['BodyText']))

on_page = header_footer_callback(header_text='Confidential Report', footer_text='')
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print('PDF created: professional_report.pdf')
```

## Output Template
```
Expected PDF file with:
- Heading 1: 28pt, dark blue, 18pt space before, 12pt after
- Heading 2: 18pt, teal, 12pt space before, 8pt after
- Body text: 11pt, justified, 1.15 line spacing
- Tables: colored headers with white text, alternating row backgrounds
- Horizontal rules: 1pt dark blue dividers with 12pt spacing
- Headers: Document title, gray, 0.25" from top
- Footers: Page numbers, gray, right-aligned
- Professional margins: 0.75" left/right, 1" top
- Consistent pixel-perfect rendering across PDF viewers
```

## Quality Gates
1. **Style Consistency**: Verify all headings use correct STYLES dict (not hardcoded); check font size progression (H1 > H2 > H3)
2. **Table Formatting**: Confirm header row has dark blue background with white bold text; verify alternating row colors (bg_light)
3. **Spacing Rules**: Check spaceAfter on all Paragraphs; verify Spacer(1, 0.2*inch) used between sections
4. **Color Palette**: Ensure all colors reference PALETTE dict (no hardcoded RGB); verify consistent accent color usage
5. **Header/Footer**: Confirm header_footer_callback function receives and renders both header text and page numbers
6. **PDF Rendering**: Open in multiple PDF viewers (Adobe, Preview, browser); confirm pixel-perfect consistency and no encoding issues

## Examples

### Good Example
```python
# Define style once, reuse everywhere
story.append(Paragraph('Section Title', STYLES['Heading2']))
story.append(Spacer(1, 0.1*inch))

# Use helper functions
data = [['Name', 'Value'], ['Item1', '100'], ['Item2', '200']]
story.append(styled_table(data, header_row=True))

# Professional spacing
story.append(divider())
story.append(Spacer(1, 0.2*inch))

# Reusable header/footer
on_page = header_footer_callback('Professional Document', '')
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
```

### Bad Example
```python
# Hardcoding styles throughout
story.append(Paragraph('<font size=18 color=blue>Title</font>', ...))
story.append(Paragraph('<font size=18 color=blue>Another Title</font>', ...))

# Table without proper styling
table = Table(data)
# Missing TableStyle, header not colored, no padding

# Using blank Spacer for spacing
story.append(Spacer(1, 0.05*inch))
story.append(Spacer(1, 0.05*inch))
story.append(Spacer(1, 0.05*inch))
# Fragile, inconsistent spacing

# No header/footer callback
doc.build(story)
# Missing professional page numbers and headers
```

## Common Mistakes

1. **Hardcoding Colors Inline**: Using `colors.HexColor('#193F5F')` repeatedly instead of referencing PALETTE dict. Makes rebranding impossible and creates visual inconsistency. Always use `PALETTE['primary_dark']`.

2. **Forgetting Spacer Between Elements**: Placing flowables directly adjacent creates visually cramped output. Insert `Spacer(1, 0.1*inch)` between logical sections for breathing room.

3. **Not Using Style Dictionary**: Creating ParagraphStyle inline for each heading instead of defining once in `create_styles()`. This violates DRY, makes global changes difficult, and increases file size.

4. **Missing TableStyle Application**: Creating a Table but not calling `setStyle(TableStyle([...]))` results in unstyled, hard-to-read tables. Always apply a style with borders, padding, and alignment.

5. **Ignoring Page Numbers**: Not implementing `header_footer_callback()` means no page numbers or headers, making multi-page documents unprofessional and hard to reference.

## Anti-Patterns

1. **Embedding HTML Tags for Styling**: Using `<font>`, `<b>`, `<i>` tags in Paragraph text instead of ParagraphStyle. While functional, it's fragile and impossible to update globally. Use styles instead.

2. **Raw Table Without Helper Function**: Calling `Table(data)` directly without wrapping in `styled_table()` creates inconsistent tables. Always use helper functions for repeatability.

3. **Spacer for Layout Control**: Using `Spacer(1, 0.3*inch)` to control section spacing instead of `spaceAfter` on styles. Spacers are fragile and don't compose well; prefer paragraph spacing attributes.

4. **No Palette Abstraction**: Defining colors as inline `colors.HexColor()` calls throughout document generation code. Impossible to rebrand. Always abstract to PALETTE dict.

5. **Single-Pass Document Building**: Not separating document setup, content generation, and building phases. Makes testing and reuse difficult. Always follow: setup → populate story → build with callbacks.
