---
name: theme-system
description: "Reusable theming system with 10 professional color and font themes for any document, presentation, or web artifact"
category: coding
difficulty: intermediate
model_boost: "Weak models skip contrast verification, create themes without dark/light variants, pick unmatched font pairs, and don't consider accessibility"
---

# Theme System

## Purpose
Create and apply professional design themes across any digital artifact (HTML, CSS, presentations, Python documents). Each theme includes carefully chosen color palettes (primary, secondary, accent, background, surface, text colors) and typography pairs. All themes meet WCAG AA contrast standards, include dark/light variants, and can generate custom themes from brand colors.

## When to Use
- Establishing consistent visual identity across multiple documents
- Rapid theming of dashboards, presentations, web layouts
- Creating branded templates for organizational use
- Applying dark/light mode variants to existing designs
- Extracting custom themes from brand colors

## Do NOT Use When
- Building bespoke custom color systems (too specific)
- Creating complex design systems with spacing, shadows, borders (use CSS frameworks)
- Designing for specialized accessibility needs beyond WCAG AA

## Instructions

### Step 1: Theme Structure Definition
```python
from dataclasses import dataclass, asdict
from typing import Dict, Tuple
import colorsys

@dataclass
class ThemeColor:
    """Color definition with validation"""
    hex_value: str

    def __post_init__(self):
        # Validate hex format
        if not self.hex_value.startswith('#') or len(self.hex_value) != 7:
            raise ValueError(f"Invalid hex color: {self.hex_value}")

    def to_rgb(self) -> Tuple[int, int, int]:
        """Convert hex to RGB"""
        hex_val = self.hex_value.lstrip('#')
        return tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))

    def to_hsl(self) -> Tuple[float, float, float]:
        """Convert hex to HSL"""
        r, g, b = self.to_rgb()
        r, g, b = r / 255, g / 255, b / 255

        max_c = max(r, g, b)
        min_c = min(r, g, b)
        l = (max_c + min_c) / 2

        if max_c == min_c:
            h = s = 0
        else:
            d = max_c - min_c
            s = d / (2 - max_c - min_c) if l > 0.5 else d / (max_c + min_c)

            if max_c == r:
                h = (60 * ((g - b) / d) + 360) % 360
            elif max_c == g:
                h = (60 * ((b - r) / d) + 120) % 360
            else:
                h = (60 * ((r - g) / d) + 240) % 360

        return (h, s, l)

@dataclass
class FontPair:
    """Typography pair: heading and body fonts"""
    heading_font: str
    body_font: str
    heading_weight: str = "bold"
    body_weight: str = "regular"

    def to_css(self) -> str:
        """Generate CSS font definitions"""
        return f"""
        --heading-font: '{self.heading_font}', sans-serif;
        --heading-weight: {self._weight_to_num(self.heading_weight)};
        --body-font: '{self.body_font}', sans-serif;
        --body-weight: {self._weight_to_num(self.body_weight)};
        """

    @staticmethod
    def _weight_to_num(weight: str) -> int:
        weights = {
            'thin': 100, 'light': 300, 'regular': 400,
            'medium': 500, 'semibold': 600, 'bold': 700, 'black': 900
        }
        return weights.get(weight, 400)

@dataclass
class Theme:
    """Complete theme definition"""
    name: str
    primary: str       # Brand primary color
    secondary: str     # Brand secondary color
    accent: str        # Highlight/CTA color
    background: str    # Page background
    surface: str       # Card/panel background
    text_dark: str     # Dark mode text
    text_light: str    # Light mode text
    border: str        # Border color
    font_pair: FontPair

    def validate_contrast(self) -> Dict[str, float]:
        """Verify WCAG AA compliance (minimum 4.5:1 for text)"""
        results = {}

        # Check text on background
        ratio = Theme.contrast_ratio(self.text_dark, self.background)
        results['text_on_background'] = ratio
        results['text_on_background_compliant'] = ratio >= 4.5

        # Check text on surface
        ratio = Theme.contrast_ratio(self.text_dark, self.surface)
        results['text_on_surface'] = ratio
        results['text_on_surface_compliant'] = ratio >= 4.5

        return results

    @staticmethod
    def contrast_ratio(color1: str, color2: str) -> float:
        """Calculate WCAG contrast ratio"""
        def luminance(hex_color):
            r, g, b = Theme._hex_to_rgb(hex_color)
            r, g, b = r / 255, g / 255, b / 255

            r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
            g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
            b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4

            return 0.2126 * r + 0.7152 * g + 0.0722 * b

        l1 = luminance(color1)
        l2 = luminance(color2)

        lighter = max(l1, l2)
        darker = min(l1, l2)

        return (lighter + 0.05) / (darker + 0.05)

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Convert hex to RGB"""
        hex_val = hex_color.lstrip('#')
        return tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))

    def to_css(self, mode='light') -> str:
        """Generate CSS variables"""
        if mode == 'light':
            text_color = self.text_dark
            bg_color = self.background
            surface_color = self.surface
        else:  # dark
            text_color = self.text_light
            bg_color = self._invert_color(self.background)
            surface_color = self._invert_color(self.surface)

        return f"""
        :root {{
            --primary: {self.primary};
            --secondary: {self.secondary};
            --accent: {self.accent};
            --background: {bg_color};
            --surface: {surface_color};
            --text: {text_color};
            --border: {self.border};
            {self.font_pair.to_css()}
        }}
        """

    def to_hex_dict(self) -> Dict[str, str]:
        """Export all colors as dictionary"""
        return {
            'primary': self.primary,
            'secondary': self.secondary,
            'accent': self.accent,
            'background': self.background,
            'surface': self.surface,
            'text_dark': self.text_dark,
            'text_light': self.text_light,
            'border': self.border,
        }

    @staticmethod
    def _invert_color(hex_color: str) -> str:
        """Invert color for dark mode"""
        r, g, b = Theme._hex_to_rgb(hex_color)
        r, g, b = 255 - r, 255 - g, 255 - b
        return f"#{r:02x}{g:02x}{b:02x}"
```

### Step 2: Define 10 Professional Themes
```python
class ThemeLibrary:
    """Pre-built professional themes"""

    @staticmethod
    def ocean_depths() -> Theme:
        """Deep, calming ocean-inspired theme"""
        return Theme(
            name="Ocean Depths",
            primary="#0A3D62",      # Deep navy
            secondary="#1B5E8C",    # Ocean blue
            accent="#48B0F7",       # Bright cyan
            background="#F0F4F8",   # Almost white
            surface="#FFFFFF",      # Pure white
            text_dark="#0A1128",    # Near black
            text_light="#F8FAFC",   # Near white
            border="#D4D8E2",       # Light gray-blue
            font_pair=FontPair("Playfair Display", "Open Sans")
        )

    @staticmethod
    def sunset_boulevard() -> Theme:
        """Warm, energetic sunset theme"""
        return Theme(
            name="Sunset Boulevard",
            primary="#D4522B",      # Deep rust
            secondary="#E67E3C",    # Warm orange
            accent="#FDBF60",       # Golden yellow
            background="#FFF7E6",   # Cream
            surface="#FFFFFF",      # Pure white
            text_dark="#3D1F0F",    # Dark brown
            text_light="#FFFBF5",   # Off-white
            border="#E8D4C0",       # Beige
            font_pair=FontPair("Merriweather", "Lato")
        )

    @staticmethod
    def forest_canopy() -> Theme:
        """Natural, organic forest theme"""
        return Theme(
            name="Forest Canopy",
            primary="#2D5016",      # Deep forest
            secondary="#5A8C3C",    # Leaf green
            accent="#A8D96E",       # Light lime
            background="#F1F5E8",   # Off-white green
            surface="#FFFFFF",      # Pure white
            text_dark="#1A2F0A",    # Dark green-black
            text_light="#F9FBF6",   # Almost white
            border="#D8E5C8",       # Pale green
            font_pair=FontPair("Lora", "Source Sans Pro")
        )

    @staticmethod
    def modern_minimalist() -> Theme:
        """Clean, contemporary minimalist theme"""
        return Theme(
            name="Modern Minimalist",
            primary="#1A1A1A",      # True black
            secondary="#4A4A4A",    # Dark gray
            accent="#00D4FF",       # Neon cyan
            background="#F8F9FA",   # Off-white
            surface="#FFFFFF",      # Pure white
            text_dark="#1A1A1A",    # True black
            text_light="#F8F9FA",   # Off-white
            border="#E0E0E0",       # Light gray
            font_pair=FontPair("Inter", "Inter")
        )

    @staticmethod
    def golden_hour() -> Theme:
        """Luxurious, golden-toned theme"""
        return Theme(
            name="Golden Hour",
            primary="#8B6F47",      # Warm brown
            secondary="#D4A574",    # Tan
            accent="#FFD700",       # Gold
            background="#FAF8F3",   # Cream
            surface="#FFFFFF",      # Pure white
            text_dark="#3D2817",    # Dark brown
            text_light="#FBF9F4",   # Almost white
            border="#E8DCC8",       # Tan beige
            font_pair=FontPair("EB Garamond", "Poppins")
        )

    @staticmethod
    def arctic_frost() -> Theme:
        """Cool, crisp ice-inspired theme"""
        return Theme(
            name="Arctic Frost",
            primary="#1E4D7B",      # Ice blue
            secondary="#3A7CA5",    # Powder blue
            accent="#B0E0E6",       # Pale blue
            background="#F0F7FF",   # Off-white blue
            surface="#FFFFFF",      # Pure white
            text_dark="#1B3A52",    # Dark blue
            text_light="#F5FAFF",   # Almost white
            border="#D0E8F2",       # Ice blue
            font_pair=FontPair("Montserrat", "Roboto")
        )

    @staticmethod
    def desert_rose() -> Theme:
        """Warm, romantic desert theme"""
        return Theme(
            name="Desert Rose",
            primary="#C2185B",      # Rose pink
            secondary="#E91E63",    # Hot pink
            accent="#F48FB1",       # Light pink
            background="#FCE4EC",   # Pale pink
            surface="#FFFFFF",      # Pure white
            text_dark="#5D1F3F",    # Dark plum
            text_light="#FEF8F8",   # Almost white
            border="#F1C4D4",       # Light pink
            font_pair=FontPair("Cormorant Garamond", "Mulish")
        )

    @staticmethod
    def tech_innovation() -> Theme:
        """Modern, tech-forward theme"""
        return Theme(
            name="Tech Innovation",
            primary="#0066CC",      # Bright blue
            secondary="#0052A3",    # Dark blue
            accent="#FF6B35",       # Bright orange
            background="#F5F7FA",   # Light gray
            surface="#FFFFFF",      # Pure white
            text_dark="#1A1A2E",    # Dark blue-black
            text_light="#F5F7FA",   # Light gray
            border="#D0D8E8",       # Blue-gray
            font_pair=FontPair("Space Mono", "Work Sans")
        )

    @staticmethod
    def botanical_garden() -> Theme:
        """Organic, botanical-inspired theme"""
        return Theme(
            name="Botanical Garden",
            primary="#4A6741",      # Sage green
            secondary="#7CB342",    # Leaf green
            accent="#AED581",       # Light sage
            background="#F6F8F4",   # Off-white green
            surface="#FFFFFF",      # Pure white
            text_dark="#2D4A2B",    # Very dark green
            text_light="#F9FBF7",   # Almost white
            border="#E0E8DC",       # Pale sage
            font_pair=FontPair("Crimson Text", "Nunito")
        )

    @staticmethod
    def midnight_galaxy() -> Theme:
        """Deep, cosmic dark theme"""
        return Theme(
            name="Midnight Galaxy",
            primary="#0F0E1A",      # Deep purple-black
            secondary="#2D2A45",    # Dark purple
            accent="#7C3AED",       # Violet
            background="#15131B",   # Almost black
            surface="#1F1D2B",      # Dark gray-purple
            text_dark="#E5E0FF",    # Light purple
            text_light="#F0EDFF",   # Very light purple
            border="#3F3A55",       # Dark purple-gray
            font_pair=FontPair("IBM Plex Mono", "IBM Plex Sans")
        )

    @staticmethod
    def get_theme(name: str) -> Theme:
        """Get theme by name"""
        themes = {
            'ocean_depths': ThemeLibrary.ocean_depths,
            'sunset_boulevard': ThemeLibrary.sunset_boulevard,
            'forest_canopy': ThemeLibrary.forest_canopy,
            'modern_minimalist': ThemeLibrary.modern_minimalist,
            'golden_hour': ThemeLibrary.golden_hour,
            'arctic_frost': ThemeLibrary.arctic_frost,
            'desert_rose': ThemeLibrary.desert_rose,
            'tech_innovation': ThemeLibrary.tech_innovation,
            'botanical_garden': ThemeLibrary.botanical_garden,
            'midnight_galaxy': ThemeLibrary.midnight_galaxy,
        }
        theme_fn = themes.get(name.lower().replace(' ', '_'))
        if not theme_fn:
            raise ValueError(f"Unknown theme: {name}")
        return theme_fn()

    @staticmethod
    def list_themes() -> list:
        """List all available themes"""
        return [
            'Ocean Depths',
            'Sunset Boulevard',
            'Forest Canopy',
            'Modern Minimalist',
            'Golden Hour',
            'Arctic Frost',
            'Desert Rose',
            'Tech Innovation',
            'Botanical Garden',
            'Midnight Galaxy',
        ]
```

### Step 3: Generate Custom Themes from Brand Color
```python
class CustomThemeGenerator:
    @staticmethod
    def from_brand_color(brand_hex: str, intensity='balanced') -> Theme:
        """Generate complete theme from single brand color"""

        # Parse brand color
        r, g, b = Theme._hex_to_rgb(brand_hex)
        h, s, l = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)

        # Generate palette variations
        primary = brand_hex
        secondary = CustomThemeGenerator._adjust_hue(h, s, l, -30, 0.9)  # Darker variant
        accent = CustomThemeGenerator._adjust_hue(h, s, l, 120, 1.0)     # Complementary

        # Generate backgrounds
        if intensity == 'balanced':
            background = CustomThemeGenerator._lighten(primary, 0.90)
            surface = "#FFFFFF"
        elif intensity == 'bold':
            background = CustomThemeGenerator._lighten(primary, 0.85)
            surface = CustomThemeGenerator._lighten(primary, 0.95)
        else:  # subtle
            background = CustomThemeGenerator._lighten(primary, 0.95)
            surface = "#FFFFFF"

        # Text colors
        text_dark = CustomThemeGenerator._darken(primary, 0.3)
        text_light = "#F8FAFC"
        border = CustomThemeGenerator._lighten(primary, 0.80)

        return Theme(
            name=f"Custom - {brand_hex}",
            primary=primary,
            secondary=secondary,
            accent=accent,
            background=background,
            surface=surface,
            text_dark=text_dark,
            text_light=text_light,
            border=border,
            font_pair=FontPair("Inter", "Inter")
        )

    @staticmethod
    def _adjust_hue(h: float, s: float, l: float,
                   hue_shift: float, saturation_mult: float) -> str:
        """Adjust HSL values and convert back to hex"""
        h = (h * 360 + hue_shift) % 360
        s = min(1.0, s * saturation_mult)
        r, g, b = colorsys.hls_to_rgb(h / 360, l, s)
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

    @staticmethod
    def _lighten(hex_color: str, factor: float) -> str:
        """Lighten color by blending with white"""
        r, g, b = Theme._hex_to_rgb(hex_color)
        r = int(r + (255 - r) * (1 - factor))
        g = int(g + (255 - g) * (1 - factor))
        b = int(b + (255 - b) * (1 - factor))
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _darken(hex_color: str, factor: float) -> str:
        """Darken color by blending with black"""
        r, g, b = Theme._hex_to_rgb(hex_color)
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)
        return f"#{r:02x}{g:02x}{b:02x}"
```

### Step 4: Theme Application for HTML/CSS
```python
class HTMLThemeApplier:
    @staticmethod
    def generate_css_file(theme: Theme, filepath: str, include_dark_variant=True):
        """Generate complete CSS file with theme and dark mode"""

        css_content = f"""
/* Generated Theme: {theme.name} */

/* Light Mode (Default) */
{theme.to_css(mode='light')}

/* Theme-specific styles */
body {{
    background-color: var(--background);
    color: var(--text);
    font-family: var(--body-font);
    font-weight: var(--body-weight);
}}

h1, h2, h3, h4, h5, h6 {{
    font-family: var(--heading-font);
    font-weight: var(--heading-weight);
    color: var(--text);
}}

a {{
    color: var(--accent);
    text-decoration: none;
}}

a:hover {{
    opacity: 0.8;
}}

button, .btn {{
    background-color: var(--primary);
    color: var(--text-light);
    border: none;
    border-radius: 4px;
    padding: 10px 20px;
    font-family: var(--body-font);
    cursor: pointer;
}}

button:hover {{
    background-color: var(--secondary);
}}

.card, .surface {{
    background-color: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
}}

/* Dark Mode Variant */
"""

        if include_dark_variant:
            css_content += f"""
@media (prefers-color-scheme: dark) {{
    {theme.to_css(mode='dark')}

    body {{
        background-color: var(--background);
        color: var(--text);
    }}
}}
"""

        with open(filepath, 'w') as f:
            f.write(css_content)

        return filepath

    @staticmethod
    def generate_html_template(theme: Theme, title: str) -> str:
        """Generate HTML template with theme applied"""

        colors = theme.to_hex_dict()

        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --primary: {colors['primary']};
            --secondary: {colors['secondary']};
            --accent: {colors['accent']};
            --background: {colors['background']};
            --surface: {colors['surface']};
            --text: {colors['text_dark']};
            --border: {colors['border']};
            --heading-font: '{theme.font_pair.heading_font}', sans-serif;
            --body-font: '{theme.font_pair.body_font}', sans-serif;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            background-color: var(--background);
            color: var(--text);
            font-family: var(--body-font);
            line-height: 1.6;
        }}

        h1, h2, h3 {{
            font-family: var(--heading-font);
            color: var(--text);
            margin-top: 20px;
            margin-bottom: 10px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}

        .card {{
            background-color: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }}

        .btn {{
            background-color: var(--primary);
            color: var(--surface);
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-family: var(--body-font);
        }}

        .btn:hover {{
            background-color: var(--secondary);
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <p>Theme: {theme.name}</p>

        <div class="card">
            <h2>Sample Card</h2>
            <p>This card uses the {theme.name} theme colors and typography.</p>
            <button class="btn">Click Me</button>
        </div>
    </div>
</body>
</html>
"""
```

### Step 5: Theme Application for Presentations
```python
class PresentationThemeApplier:
    @staticmethod
    def generate_powerpoint_colors(theme: Theme) -> Dict:
        """Generate PowerPoint color scheme from theme"""
        colors = theme.to_hex_dict()

        return {
            'primary': colors['primary'],
            'secondary': colors['secondary'],
            'accent': colors['accent'],
            'background': colors['background'],
            'text': colors['text_dark'],
        }

    @staticmethod
    def generate_markdown_css(theme: Theme) -> str:
        """Generate CSS for Markdown presentations (Marp, Reveal.js)"""
        colors = theme.to_hex_dict()

        return f"""
/* {theme.name} Theme */
section {{
    background-color: {colors['background']};
    color: {colors['text_dark']};
    font-family: '{theme.font_pair.body_font}', sans-serif;
}}

h1, h2, h3 {{
    font-family: '{theme.font_pair.heading_font}', sans-serif;
    color: {colors['primary']};
}}

a {{
    color: {colors['accent']};
}}

code {{
    background-color: {colors['surface']};
    color: {colors['primary']};
    padding: 2px 6px;
    border-radius: 3px;
}}

pre {{
    background-color: {colors['surface']};
    border-left: 4px solid {colors['primary']};
    padding: 10px;
}}
"""
```

### Step 6: Verification and Reporting
```python
class ThemeValidator:
    @staticmethod
    def full_audit(theme: Theme) -> Dict:
        """Complete theme validation report"""
        contrast_results = theme.validate_contrast()

        return {
            'theme_name': theme.name,
            'contrast_compliance': contrast_results,
            'font_pairing': {
                'heading': theme.font_pair.heading_font,
                'body': theme.font_pair.body_font,
            },
            'colors': theme.to_hex_dict(),
            'wcag_aa_compliant': (
                contrast_results.get('text_on_background_compliant', False) and
                contrast_results.get('text_on_surface_compliant', False)
            )
        }

    @staticmethod
    def print_audit_report(theme: Theme):
        """Print formatted audit report"""
        audit = ThemeValidator.full_audit(theme)

        print(f"""
╔════════════════════════════════════════════════════════════╗
║  THEME AUDIT REPORT: {audit['theme_name']}
╠════════════════════════════════════════════════════════════╣

Typography:
  Heading Font: {audit['font_pairing']['heading']}
  Body Font:    {audit['font_pairing']['body']}

Colors:
  Primary:      {audit['colors']['primary']}
  Secondary:    {audit['colors']['secondary']}
  Accent:       {audit['colors']['accent']}
  Background:   {audit['colors']['background']}
  Surface:      {audit['colors']['surface']}
  Text (Dark):  {audit['colors']['text_dark']}
  Text (Light): {audit['colors']['text_light']}
  Border:       {audit['colors']['border']}

WCAG AA Contrast Compliance:
  Text on Background: {audit['contrast_compliance']['text_on_background']:.2f}:1 {'✓' if audit['contrast_compliance']['text_on_background_compliant'] else '✗'}
  Text on Surface:    {audit['contrast_compliance']['text_on_surface']:.2f}:1 {'✓' if audit['contrast_compliance']['text_on_surface_compliant'] else '✗'}

Overall Status: {'COMPLIANT' if audit['wcag_aa_compliant'] else 'NON-COMPLIANT'}
╚════════════════════════════════════════════════════════════╝
        """)
```

## Output Template
```
Theme Application Report:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THEME SELECTED: [Theme Name]

COLOR PALETTE:
  Primary:      [hex] (used for headings, emphasis)
  Secondary:    [hex] (used for secondary elements)
  Accent:       [hex] (used for CTAs, highlights)
  Background:   [hex] (page/document background)
  Surface:      [hex] (cards, panels, containers)
  Text (Dark):  [hex] (dark mode text)
  Text (Light): [hex] (light mode text)

TYPOGRAPHY:
  Headings:     [Font Name]
  Body Text:    [Font Name]

WCAG AA COMPLIANCE:
  Text Contrast: [ratio]:1 [PASS/FAIL]

APPLICATIONS:
  ✓ HTML/CSS file generated
  ✓ Dark mode variant included
  ✓ All hex values exported
  ✓ Font pairing validated

DELIVERABLES:
  CSS File: [path]
  HTML Template: [path]
  Preview: [available/pending]
```

## Quality Gates

1. **Contrast Compliance**: All text colors must achieve minimum 4.5:1 contrast ratio against backgrounds (WCAG AA).
2. **Font Harmony**: Heading and body fonts must be compatible and readable at intended sizes.
3. **Color Cohesion**: All colors must work together without visual conflict; accent color must pop without clashing.
4. **Accessibility**: Theme must be usable in both light and dark modes without color-only information.
5. **Consistency**: Theme should be applicable across HTML, CSS, presentations, and documents without modification.
6. **Dark Mode**: Dark variant must be readable and maintainable; avoid simple color inversion.
7. **Professional Appearance**: Theme colors must evoke intended tone (warm, cool, minimal, organic, etc.).

## Examples

### Good Theme Application
```
Theme: Ocean Depths
  - Primary (#0A3D62) on Background (#F0F4F8): 12.5:1 contrast ✓
  - Professional serif+sans pairing (Playfair + Open Sans)
  - Consistent application: HTML, CSS, Markdown, PowerPoint
  - Dark variant uses adjusted palette (#15131B background)
  - All colors harmonize; accent doesn't clash
```

### Bad Theme Application
```
✗ Theme colors picked without contrast testing
✗ Text on background has 2:1 contrast (WCAG AAA fails)
✗ Serif heading + serif body (monotonous)
✗ Accent color too similar to primary (can't distinguish)
✗ Dark mode is simple color inversion (unreadable)
✗ Theme inconsistently applied (works in HTML, breaks in Markdown)
```

## Common Mistakes

1. **Ignoring Contrast Requirements**: Choosing colors that look pretty but fail accessibility. Always verify 4.5:1 minimum.
2. **Poor Font Pairing**: Using two serif fonts or two sans-serif fonts without intention. Mix serif+sans for hierarchy.
3. **No Dark Variant**: Light-only themes don't work for dark mode users. Always create inverted variant.
4. **Monochromatic Accent**: Using accent color too similar to primary makes CTAs invisible. Must have sufficient difference.
5. **Overcomplicated Palettes**: Using 10+ colors confuses usage. Stick to 8 maximum.

## Anti-Patterns

1. **Rainbow Themes**: Too many distinct colors looks chaotic. Professional themes use 3-4 core colors maximum.
2. **Extreme Saturation**: Neon colors look cheap and cause eye strain. Use muted, sophisticated colors.
3. **White Text on Light Background**: Unreadable; always verify contrast ratios. No exceptions.
4. **Font Overload**: Using 3+ different fonts breaks cohesion. Stick to single font pair.
5. **Inconsistent Application**: Using theme in HTML but ignoring it in CSS or presentations. Consistency = professionalism.
