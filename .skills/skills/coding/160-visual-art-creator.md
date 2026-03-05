---
name: visual-art-creator
description: "Create publication-quality visual designs, posters, and infographics using Python with sophisticated design principles"
category: coding
difficulty: advanced
model_boost: "Weak models forget whitespace, use default fonts, skip kerning, apply flat colors instead of gradients, and ignore composition grids"
---

# Visual Art Creator

## Purpose
Generate museum-quality visual designs, posters, and infographics using Python. This skill focuses on professional design output using composition rules, color theory, typography hierarchy, and visual hierarchy principles. Output is production-ready for print or digital media at any resolution.

## When to Use
- Creating branded marketing materials, posters, event graphics
- Generating infographics with aesthetic visual hierarchy
- Building social media graphics with consistent design language
- Producing presentation backdrops and slide backgrounds
- Creating cover art or book illustrations

## Do NOT Use When
- Creating data visualization charts (use specialized charting libraries instead)
- Making quick mockups or wireframes (use design tools instead)
- Generating photographs or realistic imagery (use image synthesis models)

## Instructions

### Step 1: Set Up Environment and Define Color Palettes
```python
from PIL import Image, ImageDraw, ImageFont
import math
from enum import Enum

# Three sophisticated color palettes (hex values)
PALETTES = {
    "ocean_depths": {
        "primary": "#0A3D62",      # Deep navy
        "secondary": "#1B5E8C",    # Ocean blue
        "accent": "#48B0F7",       # Bright cyan
        "background": "#F0F4F8",   # Almost white
        "surface": "#FFFFFF",      # Pure white
        "text_dark": "#0A1128",    # Near black
        "text_light": "#F8FAFC",   # Near white
    },
    "sunset_boulevard": {
        "primary": "#D4522B",      # Deep rust
        "secondary": "#E67E3C",    # Warm orange
        "accent": "#FDBF60",       # Golden yellow
        "background": "#FFF7E6",   # Cream
        "surface": "#FFFFFF",      # Pure white
        "text_dark": "#3D1F0F",    # Dark brown
        "text_light": "#FFFBF5",   # Off-white
    },
    "forest_canopy": {
        "primary": "#2D5016",      # Deep forest
        "secondary": "#5A8C3C",    # Leaf green
        "accent": "#A8D96E",       # Light lime
        "background": "#F1F5E8",   # Off-white green
        "surface": "#FFFFFF",      # Pure white
        "text_dark": "#1A2F0A",    # Dark green black
        "text_light": "#F9FBF6",   # Almost white
    }
}

class DesignSystem:
    def __init__(self, palette_name="ocean_depths"):
        self.palette = PALETTES[palette_name]
        self.font_sizes = {
            "h1": 72,
            "h2": 54,
            "h3": 36,
            "body": 18,
            "caption": 12
        }
        # Font pairs (heading, body)
        self.font_pairs = {
            "modern": ("arial.ttf", "arial.ttf"),
            "elegant": ("georgia.ttf", "georgia.ttf"),
            "sans_serif": ("helvetica.ttf", "helvetica.ttf"),
        }
```

### Step 2: Implement Composition Grid System
```python
class CompositionGrid:
    """Rule of thirds + golden ratio layout system"""

    def __init__(self, width, height):
        self.width = width
        self.height = height

    def thirds(self):
        """Return rule of thirds intersection points"""
        return [
            (self.width // 3, self.height // 3),
            (2 * self.width // 3, self.height // 3),
            (self.width // 3, 2 * self.height // 3),
            (2 * self.width // 3, 2 * self.height // 3),
        ]

    def golden_ratio_areas(self):
        """Return safe areas based on golden ratio (1.618)"""
        phi = 1.618
        margin_x = self.width // (phi + 2)
        margin_y = self.height // (phi + 2)

        return {
            "main": (margin_x, margin_y,
                    self.width - margin_x, self.height - margin_y),
            "safe": (margin_x * 1.5, margin_y * 1.5,
                    self.width - margin_x * 1.5, self.height - margin_y * 1.5)
        }

    def grid_cells(self, cols=3, rows=3):
        """Generate grid cells for layout spacing"""
        cell_w = self.width / cols
        cell_h = self.height / rows
        cells = []
        for r in range(rows):
            for c in range(cols):
                cells.append({
                    "row": r, "col": c,
                    "x1": int(c * cell_w),
                    "y1": int(r * cell_h),
                    "x2": int((c + 1) * cell_w),
                    "y2": int((r + 1) * cell_h),
                })
        return cells
```

### Step 3: Create Gradient and Texture Backgrounds
```python
class BackgroundGenerator:
    @staticmethod
    def linear_gradient(image, start_color, end_color, direction="vertical"):
        """Create smooth linear gradient (90% visual impact)"""
        draw = ImageDraw.Draw(image)
        w, h = image.size

        # Parse hex colors to RGB
        start_rgb = tuple(int(start_color.lstrip('#')[i:i+2], 16)
                         for i in (0, 2, 4))
        end_rgb = tuple(int(end_color.lstrip('#')[i:i+2], 16)
                       for i in (0, 2, 4))

        if direction == "vertical":
            for y in range(h):
                ratio = y / h
                r = int(start_rgb[0] * (1 - ratio) + end_rgb[0] * ratio)
                g = int(start_rgb[1] * (1 - ratio) + end_rgb[1] * ratio)
                b = int(start_rgb[2] * (1 - ratio) + end_rgb[2] * ratio)
                draw.line([(0, y), (w, y)], fill=(r, g, b))

        elif direction == "horizontal":
            for x in range(w):
                ratio = x / w
                r = int(start_rgb[0] * (1 - ratio) + end_rgb[0] * ratio)
                g = int(start_rgb[1] * (1 - ratio) + end_rgb[1] * ratio)
                b = int(start_rgb[2] * (1 - ratio) + end_rgb[2] * ratio)
                draw.line([(x, 0), (x, h)], fill=(r, g, b))

        return image

    @staticmethod
    def geometric_pattern(image, color1, color2, pattern_type="diagonal_lines"):
        """Add sophisticated geometric patterns"""
        draw = ImageDraw.Draw(image)
        w, h = image.size

        if pattern_type == "diagonal_lines":
            spacing = 20
            for i in range(0, w + h, spacing):
                draw.line([(i, 0), (i - h, h)], fill=color2, width=1)

        elif pattern_type == "dots":
            spacing = 30
            radius = 3
            for x in range(0, w, spacing):
                for y in range(0, h, spacing):
                    draw.ellipse([x-radius, y-radius, x+radius, y+radius],
                                fill=color2)

        return image
```

### Step 4: Typography with Proper Kerning and Alignment
```python
class TypographyEngine:
    def __init__(self, design_system):
        self.design = design_system
        self.line_spacing_ratio = 1.4  # Professional leading
        self.letter_spacing = 0  # Will adjust per element

    def render_text(self, image, text, position, font_size,
                   color, alignment="left", font_file="arial.ttf"):
        """Render text with professional typography"""
        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.truetype(font_file, font_size)
        except:
            font = ImageFont.load_default()

        # Get text bounding box for proper alignment
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x, y = position

        if alignment == "center":
            x = x - text_width // 2
        elif alignment == "right":
            x = x - text_width

        draw.text((x, y), text, fill=color, font=font)
        return image

    def render_heading(self, image, text, position, color,
                      alignment="left", level=1):
        """Render heading with hierarchy"""
        size = self.design.font_sizes.get(f"h{level}", 48)
        return self.render_text(image, text, position, size, color, alignment)

    def render_paragraph(self, image, text, position, color, max_width):
        """Render multi-line paragraph with proper leading"""
        draw = ImageDraw.Draw(image)
        x, y = position

        try:
            font = ImageFont.truetype("arial.ttf", self.design.font_sizes["body"])
        except:
            font = ImageFont.load_default()

        words = text.split()
        line = ""

        for word in words:
            test_line = f"{line} {word}".strip()
            bbox = draw.textbbox((0, 0), test_line, font=font)

            if bbox[2] - bbox[0] > max_width:
                draw.text((x, y), line, fill=color, font=font)
                y += int(self.design.font_sizes["body"] * self.line_spacing_ratio)
                line = word
            else:
                line = test_line

        if line:
            draw.text((x, y), line, fill=color, font=font)

        return image
```

### Step 5: Geometric Shapes and Decorative Elements
```python
class DecorativeElements:
    @staticmethod
    def draw_rounded_rectangle(draw, bbox, radius, fill=None, outline=None, width=1):
        """Draw rounded corner rectangle"""
        x1, y1, x2, y2 = bbox

        # Draw corners
        draw.arc([x1, y1, x1 + 2*radius, y1 + 2*radius], 180, 270,
                fill=outline, width=width)
        draw.arc([x2 - 2*radius, y1, x2, y1 + 2*radius], 270, 360,
                fill=outline, width=width)
        draw.arc([x1, y2 - 2*radius, x1 + 2*radius, y2], 90, 180,
                fill=outline, width=width)
        draw.arc([x2 - 2*radius, y2 - 2*radius, x2, y2], 0, 90,
                fill=outline, width=width)

        # Draw lines
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)

    @staticmethod
    def draw_circle_accent(draw, center, radius, color, width=2):
        """Draw circular accent elements"""
        x, y = center
        draw.ellipse([x - radius, y - radius, x + radius, y + radius],
                    outline=color, width=width)

    @staticmethod
    def draw_bar_accent(draw, position, length, direction, color, width=3):
        """Draw accent bars for emphasis"""
        x, y = position
        if direction == "horizontal":
            draw.line([(x, y), (x + length, y)], fill=color, width=width)
        elif direction == "vertical":
            draw.line([(x, y), (x, y + length)], fill=color, width=width)
```

### Step 6: Image Compositing
```python
def composite_layers(bg_image, elements):
    """Composite multiple design elements"""
    canvas = bg_image.convert('RGBA')

    for element in elements:
        if isinstance(element, Image.Image):
            # Paste with alpha blending
            canvas.paste(element, element.getbbox(), element)
        elif isinstance(element, dict) and element.get('type') == 'color_overlay':
            overlay = Image.new('RGBA', canvas.size,
                              element['color'] + (element.get('alpha', 128),))
            canvas = Image.alpha_composite(canvas, overlay)

    return canvas
```

### Step 7: Export with Quality Control
```python
def export_design(image, filepath, format="PNG", quality=95):
    """Export with format-specific optimization"""

    if format.upper() == "PNG":
        image.save(filepath, "PNG", optimize=True)

    elif format.upper() == "JPG":
        rgb_image = image.convert('RGB')
        rgb_image.save(filepath, "JPEG", quality=quality, optimize=True)

    elif format.upper() == "PDF":
        rgb_image = image.convert('RGB')
        rgb_image.save(filepath, "PDF", optimize=True)

    elif format.upper() == "SVG":
        # For SVG export, you'd use a library like svgwrite
        pass

    return filepath
```

## Output Template
```
Design Output Checklist:
✓ Background: [Gradient/Pattern/Solid with specific colors]
✓ Composition: [Grid system used, focal points placed]
✓ Typography: [Hierarchy clear, font pairs matched, leading = 1.4x]
✓ Color Contrast: [WCAG AA compliant, min 4.5:1 for text]
✓ Visual Elements: [Geometric accents, decorative elements placed]
✓ Whitespace: [40%+ negative space for breathing room]
✓ Export: [Format, resolution, file size optimized]
```

## Quality Gates

1. **Whitespace Rule**: Minimum 40% of canvas should be empty. Avoid cramped designs.
2. **Color Contrast**: All text must meet WCAG AA standards (minimum 4.5:1 contrast ratio).
3. **Typography Hierarchy**: Use only 2-3 font sizes maximum; heading:body ratio ≥2:1.
4. **Composition**: Primary focal point must land on rule of thirds intersection or golden ratio zone.
5. **Consistency**: Font pairs matched properly; color palette limited to 5 colors max.
6. **Resolution**: Minimum 1920x1080 for digital, 300 DPI for print.
7. **File Size**: PNG ≤5MB, JPG ≤2MB for web delivery.

## Examples

### Good Design
```
- Ocean Depths palette with linear gradient background (navy → cyan)
- Large heading (72pt) centered on upper third intersection
- Body text (18pt, 1.4 line spacing) in 2-column layout
- Circular accent elements in accent color (#48B0F7)
- 45% whitespace; crisp 1200x800px export
```

### Bad Design
```
✗ Using all 7 colors from palette instead of 5
✗ Text placed over low-contrast background (3:1 ratio)
✗ Mixed serif and sans-serif fonts without hierarchy
✗ No whitespace; elements touch canvas edges
✗ Different heading sizes (48pt, 62pt, 71pt) - looks random
```

## Common Mistakes

1. **Ignoring Whitespace**: Cramming elements creates amateur feel. Whitespace = sophistication.
2. **Wrong Color Combinations**: Using complementary colors without testing contrast ratios first.
3. **Font Overload**: Mixing 4+ different fonts. Stick to 2-font pairs maximum.
4. **Poor Leading/Line Spacing**: Using default spacing creates cramped text. Use 1.4x multiplier minimum.
5. **Ignoring Grid System**: Placing elements randomly. Always snap to composition grid.

## Anti-Patterns

1. **Flat Design Without Depth**: Avoid single-color blocks. Use gradients and layering for sophistication.
2. **Inconsistent Font Sizing**: Don't use arbitrary sizes. Define scale and stick to it.
3. **Centered Everything**: Over-centering creates static, boring layouts. Use asymmetrical balance instead.
4. **Neon Color Palettes**: Avoid eye-watering colors. Professional palettes are muted, sophisticated.
5. **Missing Visual Hierarchy**: Every element same visual weight means nothing stands out. Use size, color, and position to guide eye.
