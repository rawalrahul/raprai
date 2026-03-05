---
name: python-pptx-engine
description: "Professional PowerPoint generation with custom slide templates, accent shapes, color systems, and extreme typography contrast using python-pptx"
category: office
difficulty: intermediate
model_boost: "Weak models use white backgrounds (amateur), don't implement accent shapes, hardcode font sizes without contrast hierarchy, and ignore blank layouts. This engine provides dark color systems, accent bars, proper sizing (72pt titles, 11pt body), and reusable slide templates."
---

# Python-PPTX Presentation Generation Engine

## Purpose
Generate professional PowerPoint presentations (.pptx) programmatically with dark color schemes, accent shapes (left-edge bars, bottom strips), typography contrast (72pt headlines vs 11pt body), and slide templates. Create slide decks with consistent branding, proper visual hierarchy, and aesthetic accent patterns that align with modern design standards.

## When to Use
- Building automated presentation decks from data or templates
- Creating branded slides with consistent color schemes and layouts
- Generating multi-template presentations (title, content, data highlight, section dividers)
- **Do NOT use when**: Editing existing presentations interactively (use PowerPoint app), creating pixel-perfect layouts (use ReportLab PDF), or designing animated transitions (use Keynote/Adobe)

## Instructions

### Step 1: Install and Import
```bash
pip install python-pptx
```

```python
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.dml import MSO_THEME_COLOR
```

### Step 2: Define Color Palettes
Create two professional dark palettes:

```python
# Palette 1: Dark Navy + Teal (Corporate)
PALETTE_NAVY = {
    'primary': RGBColor(25, 55, 95),       # Dark navy #193F5F
    'secondary': RGBColor(100, 180, 210),  # Light teal #64B4D2
    'accent': RGBColor(200, 50, 50),       # Red #C83232
    'text_dark': RGBColor(45, 45, 45),     # Near black #2D2D2D
    'text_light': RGBColor(200, 200, 200), # Light gray #C8C8C8
    'bg_dark': RGBColor(20, 20, 20),       # Almost black #141414
    'bg_accent': RGBColor(35, 85, 135),    # Darker navy #355587
}

# Palette 2: Dark Charcoal + Gold (Premium)
PALETTE_GOLD = {
    'primary': RGBColor(50, 50, 50),       # Dark charcoal #323232
    'secondary': RGBColor(212, 175, 55),   # Gold #D4AF37
    'accent': RGBColor(220, 80, 80),       # Rose #DC5050
    'text_dark': RGBColor(30, 30, 30),     # Near black #1E1E1E
    'text_light': RGBColor(220, 220, 220), # Light gray #DCDCDC
    'bg_dark': RGBColor(25, 25, 25),       # Very dark #191919
    'bg_accent': RGBColor(70, 70, 70),     # Lighter gray #464646
}

# Set default palette
PALETTE = PALETTE_NAVY
```

### Step 3: Presentation Setup
Initialize a presentation with blank layout:

```python
def setup_presentation(palette=PALETTE_NAVY):
    """
    Create presentation with blank layouts.
    IMPORTANT: Always use blank layout (slide_layouts[6]) to avoid white defaults.
    """
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    # Set slide dimensions to 16:9
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    return prs
```

### Step 4: Helper Function - Solid Fill
Set background color on shapes:

```python
def solid_fill(shape, color):
    """Apply solid fill color to shape."""
    fill = shape.fill
    fill.solid()
    fill.fore_color.rgb = color
```

### Step 5: Helper Function - Add Rectangle Shape
Create accent rectangles:

```python
def add_rectangle(slide, left, top, width, height, fill_color, line_color=None):
    """
    Add a filled rectangle to slide.

    Returns: shape object
    """
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(left),
        Inches(top),
        Inches(width),
        Inches(height)
    )
    solid_fill(shape, fill_color)

    if line_color:
        shape.line.color.rgb = line_color
    else:
        shape.line.color.rgb = fill_color

    return shape
```

### Step 6: Helper Function - Add Text Box
Insert and format text:

```python
def add_textbox(slide, left, top, width, height, text='', font_size=11, color=RGBColor(255, 255, 255), bold=False, alignment=PP_ALIGN.LEFT):
    """
    Add a text box to slide.

    Returns: text_frame object
    """
    textbox = slide.shapes.add_textbox(
        Inches(left),
        Inches(top),
        Inches(width),
        Inches(height)
    )
    text_frame = textbox.text_frame
    text_frame.word_wrap = True
    text_frame.margin_top = Inches(0.1)
    text_frame.margin_left = Inches(0.1)
    text_frame.margin_right = Inches(0.1)

    p = text_frame.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.alignment = alignment

    return text_frame
```

### Step 7: Helper Function - Set Background
Apply dark background to entire slide:

```python
def set_background(slide, color):
    """Set slide background to solid color."""
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = color
```

### Step 8: Helper Function - Add Accent Bar (Left Edge)
Create left-edge accent bar:

```python
def add_accent_bar(slide, color=None, width=0.15):
    """Add a thick vertical bar on the left edge of slide."""
    if color is None:
        color = PALETTE['secondary']

    # Slide dimensions: 13.333 x 7.5 inches (16:9)
    add_rectangle(slide, 0, 0, width, 7.5, color)
```

### Step 9: Helper Function - Add Bottom Strip
Create bottom accent strip:

```python
def add_bottom_strip(slide, color=None, height=0.3):
    """Add a horizontal accent strip at bottom of slide."""
    if color is None:
        color = PALETTE['secondary']

    add_rectangle(slide, 0, 7.5 - height, 13.333, height, color)
```

### Step 10: Slide Template 1 - Title Slide
Create opening slide:

```python
def create_title_slide(prs, title='', subtitle='', palette=PALETTE):
    """
    Create title slide with accent bar and centered text.

    Title: 72pt bold, light color
    Subtitle: 32pt, secondary color
    """
    blank_slide_layout = prs.slide_layouts[6]  # Blank layout
    slide = prs.slides.add_slide(blank_slide_layout)

    # Dark background
    set_background(slide, palette['bg_dark'])

    # Left accent bar
    add_accent_bar(slide, palette['secondary'], width=0.2)

    # Title (centered, massive)
    title_box = add_textbox(slide, 1, 2.5, 11.333, 2, title, font_size=72, color=palette['text_light'], bold=True, alignment=PP_ALIGN.CENTER)
    title_box.paragraphs[0].alignment = PP_ALIGN.CENTER

    # Subtitle
    subtitle_box = add_textbox(slide, 1, 4.8, 11.333, 1.5, subtitle, font_size=32, color=palette['secondary'], alignment=PP_ALIGN.CENTER)
    subtitle_box.paragraphs[0].alignment = PP_ALIGN.CENTER

    # Bottom accent strip
    add_bottom_strip(slide, palette['accent'], height=0.25)

    return slide
```

### Step 11: Slide Template 2 - Content Slide
Create standard content slide:

```python
def create_content_slide(prs, title='', bullets=None, palette=PALETTE):
    """
    Create content slide with bullet points.

    Title: 48pt, light color, top-left
    Bullets: 18pt, body text
    """
    if bullets is None:
        bullets = []

    blank_slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_slide_layout)

    # Dark background
    set_background(slide, palette['bg_dark'])

    # Left accent bar
    add_accent_bar(slide, palette['secondary'])

    # Title
    title_box = add_textbox(slide, 0.5, 0.4, 12.333, 1, title, font_size=48, color=palette['secondary'], bold=True)

    # Title underline
    add_rectangle(slide, 0.5, 1.5, 3, 0.05, palette['accent'])

    # Bullet points
    bullets_text = '\n\n'.join(f'• {bullet}' for bullet in bullets)
    bullets_box = add_textbox(slide, 1.2, 2.2, 11, 5, bullets_text, font_size=20, color=palette['text_light'])
    bullets_box.paragraphs[0].level = 0

    return slide
```

### Step 12: Slide Template 3 - Two-Column Layout
Create side-by-side content:

```python
def create_two_column_slide(prs, title='', left_content='', right_content='', palette=PALETTE):
    """
    Create two-column slide.

    Title: 48pt across top
    Columns: 24pt body text, separated by divider
    """
    blank_slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_slide_layout)

    # Dark background
    set_background(slide, palette['bg_dark'])

    # Left accent bar
    add_accent_bar(slide, palette['secondary'])

    # Title
    title_box = add_textbox(slide, 0.5, 0.4, 12.333, 0.8, title, font_size=48, color=palette['secondary'], bold=True)

    # Vertical divider
    add_rectangle(slide, 6.5, 1.5, 0.05, 5.5, palette['accent'])

    # Left column
    left_box = add_textbox(slide, 0.7, 1.7, 5.5, 5.3, left_content, font_size=18, color=palette['text_light'])

    # Right column
    right_box = add_textbox(slide, 6.8, 1.7, 5.5, 5.3, right_content, font_size=18, color=palette['text_light'])

    return slide
```

### Step 13: Slide Template 4 - Stat Highlight
Create data-focused slide:

```python
def create_stat_highlight_slide(prs, stat='', stat_label='', supporting_text='', palette=PALETTE):
    """
    Create stat highlight slide with massive number.

    Stat: 120pt, accent color, centered
    Label: 32pt, secondary color
    Supporting: 16pt, body text
    """
    blank_slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_slide_layout)

    # Dark background
    set_background(slide, palette['bg_dark'])

    # Left accent bar
    add_accent_bar(slide, palette['secondary'])

    # Stat value (extreme size contrast)
    stat_box = add_textbox(slide, 2, 1.8, 9.333, 2, stat, font_size=120, color=palette['accent'], bold=True, alignment=PP_ALIGN.CENTER)
    stat_box.paragraphs[0].alignment = PP_ALIGN.CENTER

    # Stat label
    label_box = add_textbox(slide, 2, 4, 9.333, 0.8, stat_label, font_size=32, color=palette['secondary'], alignment=PP_ALIGN.CENTER)
    label_box.paragraphs[0].alignment = PP_ALIGN.CENTER

    # Supporting text
    support_box = add_textbox(slide, 1.5, 5.2, 10.333, 1.8, supporting_text, font_size=16, color=palette['text_light'], alignment=PP_ALIGN.CENTER)
    support_box.paragraphs[0].alignment = PP_ALIGN.CENTER

    return slide
```

### Step 14: Slide Template 5 - Section Divider
Create section break slide:

```python
def create_section_divider_slide(prs, section_title='', subtitle='', palette=PALETTE):
    """
    Create section divider slide with minimal design.

    Title: 64pt, light color, centered
    Subtitle: 28pt, secondary color
    """
    blank_slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_slide_layout)

    # Background with accent tint
    set_background(slide, palette['bg_accent'])

    # Large left accent bar (full height)
    add_accent_bar(slide, palette['secondary'], width=0.3)

    # Section title (centered)
    title_box = add_textbox(slide, 1, 2.5, 11.333, 2, section_title, font_size=64, color=palette['text_light'], bold=True, alignment=PP_ALIGN.CENTER)
    title_box.paragraphs[0].alignment = PP_ALIGN.CENTER

    # Subtitle
    if subtitle:
        subtitle_box = add_textbox(slide, 1, 5, 11.333, 1, subtitle, font_size=28, color=palette['secondary'], alignment=PP_ALIGN.CENTER)
        subtitle_box.paragraphs[0].alignment = PP_ALIGN.CENTER

    # Bottom accent strip (prominent)
    add_bottom_strip(slide, palette['accent'], height=0.4)

    return slide
```

## Complete Working Boilerplate

```python
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

PALETTE = {
    'primary': RGBColor(25, 55, 95),
    'secondary': RGBColor(100, 180, 210),
    'accent': RGBColor(200, 50, 50),
    'text_light': RGBColor(200, 200, 200),
    'bg_dark': RGBColor(20, 20, 20),
}

def solid_fill(shape, color):
    fill = shape.fill
    fill.solid()
    fill.fore_color.rgb = color

def add_rectangle(slide, left, top, width, height, fill_color):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    solid_fill(shape, fill_color)
    shape.line.color.rgb = fill_color
    return shape

def add_textbox(slide, left, top, width, height, text='', font_size=11, color=RGBColor(255, 255, 255), bold=False):
    textbox = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    text_frame = textbox.text_frame
    p = text_frame.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = color
    p.font.bold = bold
    return text_frame

def set_background(slide, color):
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = color

def add_accent_bar(slide, color, width=0.15):
    add_rectangle(slide, 0, 0, width, 7.5, color)

def create_title_slide(prs, title='', subtitle=''):
    blank = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank)
    set_background(slide, PALETTE['bg_dark'])
    add_accent_bar(slide, PALETTE['secondary'])
    add_textbox(slide, 1, 2.5, 11.333, 2, title, 72, PALETTE['text_light'], True)
    add_textbox(slide, 1, 4.8, 11.333, 1.5, subtitle, 32, PALETTE['secondary'])
    add_rectangle(slide, 0, 7.2, 13.333, 0.3, PALETTE['accent'])
    return slide

def create_content_slide(prs, title='', bullets=None):
    if bullets is None:
        bullets = []
    blank = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank)
    set_background(slide, PALETTE['bg_dark'])
    add_accent_bar(slide, PALETTE['secondary'])
    add_textbox(slide, 0.5, 0.4, 12.333, 1, title, 48, PALETTE['secondary'], True)
    add_rectangle(slide, 0.5, 1.5, 3, 0.05, PALETTE['accent'])
    bullets_text = '\n\n'.join(f'• {b}' for b in bullets)
    add_textbox(slide, 1.2, 2.2, 11, 5, bullets_text, 20, PALETTE['text_light'])
    return slide

# Build presentation
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

create_title_slide(prs, 'Professional Deck', 'Powered by Python-PPTX')
create_content_slide(prs, 'Key Points', ['First bullet point', 'Second bullet point', 'Third bullet point'])

prs.save('presentation.pptx')
print('Presentation created: presentation.pptx')
```

## Output Template
```
Expected .pptx file with:
- Dark backgrounds (20, 20, 20) on all slides—no white
- Left accent bars (0.15" width, light teal) on content slides
- Extreme typography contrast: 72pt titles, 48pt subtitles, 20pt bullets, 11pt body
- Accent shapes: bottom strips (0.25" height, red), vertical dividers (0.05" width)
- Consistent color palette (navy/teal or charcoal/gold)
- Professional margins: 0.5" from edges
- Proper text alignment: titles left-aligned or centered, bullets left, stats centered
- Slide dimensions: 16:9 (13.333 x 7.5 inches)
- Editable in PowerPoint with all shapes and text selectable
```

## Quality Gates
1. **Dark Background Verification**: Confirm slide background is dark (RGB 20, 20, 20), not white or light gray
2. **Accent Shape Placement**: Check left bar is 0.15" wide, bottom strip is 0.25-0.4" tall, centered vertically
3. **Typography Hierarchy**: Measure title font sizes (72pt > 48pt > 32pt > 20pt > 11pt); verify extreme contrast
4. **Color Consistency**: Ensure all text colors come from PALETTE dict; no hardcoded random colors
5. **Shape Properties**: Confirm rectangles use `solid_fill()` and have matching stroke/fill colors
6. **Slide Layout**: Verify all slides use blank layout (slide_layouts[6]), never default layouts with placeholders
7. **Text Box Spacing**: Check text boxes have proper left/right padding (Inches(0.1)) to avoid edge-touching text

## Examples

### Good Example
```python
# Use helper functions and palette
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# Title slide with accent bar and bottom strip
create_title_slide(prs, 'Project Overview', 'Q1 2026')

# Content with bullet points
bullets = ['Initiative A drives growth', 'Initiative B reduces costs', 'Initiative C improves quality']
create_content_slide(prs, 'Strategic Initiatives', bullets)

# Data highlight with extreme contrast
create_stat_highlight_slide(prs, '245%', 'Year-over-Year Growth', 'Fastest growth in company history')

# Save
prs.save('strategic_deck.pptx')
```

### Bad Example
```python
prs = Presentation()
# Using default slide layouts with placeholders
blank = prs.slide_layouts[5]  # Title and Content (white background)
slide = prs.slides.add_slide(blank)

# Hardcoding colors and sizes
shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(1), Inches(7.5))
shape.fill.solid()
shape.fill.fore_color.rgb = RGBColor(100, 180, 210)  # No palette reference

# Inline text formatting
title = slide.shapes.title
title.text = 'Title'
title.text_frame.paragraphs[0].font.size = Pt(44)  # Not 72pt for title
title.text_frame.paragraphs[0].font.color.rgb = RGBColor(0, 0, 0)  # Black text on white

# No accent shapes, no consistency
prs.save('deck.pptx')
```

## Common Mistakes

1. **Using Default Slide Layouts**: Calling `slide_layouts[1]` or `slide_layouts[5]` includes white backgrounds and placeholder shapes. Always use `slide_layouts[6]` (blank) and set dark background explicitly.

2. **Not Implementing Accent Shapes**: Creating slides with just text and dark background looks flat and amateurish. Add left accent bar, bottom strip, or vertical divider using helper functions.

3. **Ignoring Typography Contrast**: Setting all text to 18pt or 24pt eliminates visual hierarchy. Use extreme contrast: 72pt for titles, 11pt for body (6.5x multiplier).

4. **Hardcoding Colors**: Using `RGBColor(100, 180, 210)` inline instead of `PALETTE['secondary']` makes rebranding impossible and creates inconsistency. Always abstract to palette dict.

5. **Text Touching Edges**: Not setting text box margins means text runs to cell edges. Always use `text_frame.margin_left = Inches(0.1)` and similar on all sides.

## Anti-Patterns

1. **White or Light Backgrounds**: Using `RGBColor(255, 255, 255)` backgrounds signals amateur design. Always use dark (20-70 RGB) to make accent colors pop and reduce eye strain.

2. **No Color System**: Each slide picks different colors instead of using consistent PALETTE. Unprofessional and confusing. Define palette once, reference everywhere.

3. **Uniform Font Sizes**: Making titles and body the same size (or only 2-3pt difference) eliminates hierarchy. Use 3-6x multiplier between sizes.

4. **Text Box Overflow**: Not setting `word_wrap = True` or providing adequate height causes text to overflow or clip. Always test text fitting in your dimensions.

5. **Accent Shapes Without Purpose**: Adding random colored rectangles that don't frame or highlight content. Accent shapes should always support visual hierarchy (frame title, separate sections, highlight data).
