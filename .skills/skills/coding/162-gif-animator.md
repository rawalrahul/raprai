---
name: gif-animator
description: "Create optimized animated GIFs with easing functions, animation primitives, and platform-specific constraints"
category: coding
difficulty: advanced
model_boost: "Weak models don't consider file size limits, skip easing functions (linear is boring), don't optimize frame palettes, and produce large unoptimized GIFs"
---

# GIF Animator

## Purpose
Generate professional animated GIFs with smooth motion, precise timing control, and file size optimization for specific platforms. This skill covers frame generation, easing functions, animation primitives (bounce, fade, slide, spin), color quantization, and platform constraints (Slack: 128x128/64KB, Twitter: 15MB, Discord: 8MB).

## When to Use
- Creating animated GIF reactions or emojis for messaging platforms
- Building loading spinners, progress indicators, animated backgrounds
- Generating social media content with text animation
- Creating pixel art animations or simple motion graphics
- Producing animated illustrations or character animations

## Do NOT Use When
- Creating videos (use MP4/WebM instead)
- Building complex interactive animations (use CSS/JavaScript)
- Generating high-frame-rate cinematic content (use video formats)

## Instructions

### Step 1: Set Up GIF Builder with Frame Management
```python
from PIL import Image, ImageDraw
import math
import struct
import io
from pathlib import Path

class GIFBuilder:
    def __init__(self, width, height, duration_ms=50, loop=0):
        """
        Initialize GIF builder
        duration_ms: milliseconds per frame (50ms = 20 fps, 100ms = 10 fps)
        loop: 0 = infinite loop, N = repeat N times
        """
        self.width = width
        self.height = height
        self.duration = duration_ms
        self.loop = loop
        self.frames = []
        self.durations = []

    def add_frame(self, image, duration=None):
        """Add PIL Image as frame"""
        if image.size != (self.width, self.height):
            image = image.resize((self.width, self.height), Image.Resampling.LANCZOS)

        self.frames.append(image)
        self.durations.append(duration or self.duration)

    def add_solid_frame(self, color, duration=None):
        """Add solid color frame"""
        frame = Image.new('RGB', (self.width, self.height), color)
        self.add_frame(frame, duration)

    def create_background(self, bg_color='white', gradient_color=None):
        """Create background layer"""
        img = Image.new('RGB', (self.width, self.height), bg_color)

        if gradient_color:
            draw = ImageDraw.Draw(img, 'RGBA')
            for y in range(self.height):
                ratio = y / self.height
                r = int(self.hex_to_rgb(bg_color)[0] * (1 - ratio) +
                       self.hex_to_rgb(gradient_color)[0] * ratio)
                g = int(self.hex_to_rgb(bg_color)[1] * (1 - ratio) +
                       self.hex_to_rgb(gradient_color)[1] * ratio)
                b = int(self.hex_to_rgb(bg_color)[2] * (1 - ratio) +
                       self.hex_to_rgb(gradient_color)[2] * ratio)
                draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        return img

    @staticmethod
    def hex_to_rgb(hex_color):
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def save(self, filepath, optimize=True, quality=85):
        """Save as optimized GIF"""
        if not self.frames:
            raise ValueError("No frames added")

        # Convert to palette mode for optimization
        quantized_frames = []
        for frame in self.frames:
            # Quantize to 256 colors (standard GIF palette)
            if frame.mode != 'P':
                frame = frame.quantize(colors=256)
            quantized_frames.append(frame)

        quantized_frames[0].save(
            filepath,
            save_all=True,
            append_images=quantized_frames[1:],
            duration=self.durations,
            loop=self.loop,
            optimize=optimize
        )

        # Get file size
        file_size_mb = Path(filepath).stat().st_size / (1024 * 1024)
        return file_size_mb
```

### Step 2: Easing Functions for Smooth Motion
```python
class Easing:
    @staticmethod
    def linear(t):
        """Linear: constant speed"""
        return t

    @staticmethod
    def ease_in_quad(t):
        """Ease in: slow start"""
        return t * t

    @staticmethod
    def ease_out_quad(t):
        """Ease out: slow end"""
        return 1 - (1 - t) ** 2

    @staticmethod
    def ease_in_out_quad(t):
        """Ease in-out: slow start and end (MOST NATURAL)"""
        return 2 * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 2 / 2

    @staticmethod
    def ease_in_cubic(t):
        """Ease in cubic: aggressive slow start"""
        return t ** 3

    @staticmethod
    def ease_out_cubic(t):
        """Ease out cubic: aggressive slow end"""
        return 1 - (1 - t) ** 3

    @staticmethod
    def ease_out_bounce(t):
        """Bounce out: bouncy elastic ending"""
        n1 = 7.5625
        d1 = 2.75

        if t < 1 / d1:
            return n1 * t * t
        elif t < 2 / d1:
            t -= 1.5 / d1
            return n1 * t * t + 0.75
        elif t < 2.5 / d1:
            t -= 2.25 / d1
            return n1 * t * t + 0.9375
        else:
            t -= 2.625 / d1
            return n1 * t * t + 0.984375

    @staticmethod
    def ease_out_elastic(t):
        """Elastic out: springy ending"""
        if t == 0:
            return 0
        if t == 1:
            return 1

        c5 = (2 * math.pi) / 4.5
        return pow(2, -10 * t) * math.sin((t * 10 - 0.75) * c5) + 1

    @staticmethod
    def ease_in_out_cubic(t):
        """Ease in-out cubic: smooth professional motion"""
        return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2

    # Recommended easing by animation:
    # Fade: ease_in_out_quad (natural opacity change)
    # Slide: ease_out_cubic (snappy entrance)
    # Bounce: ease_out_bounce (playful effect)
    # Spin: ease_in_out_cubic (smooth rotation)
    # General: ease_in_out_quad (safest default)
```

### Step 3: Animation Primitives
```python
class AnimationPrimitives:
    def __init__(self, builder):
        self.builder = builder
        self.w = builder.width
        self.h = builder.height

    def fade(self, color='white', frames=20, easing_func=Easing.ease_in_out_quad,
            direction='in'):
        """Fade in or out"""
        for i in range(frames):
            t = i / frames
            eased = easing_func(t)

            if direction == 'in':
                alpha = int(255 * eased)
            else:  # out
                alpha = int(255 * (1 - eased))

            frame = Image.new('RGBA', (self.w, self.h), color + (alpha,))
            self.builder.add_frame(frame.convert('RGB'))

    def slide(self, image, frames=30, easing_func=Easing.ease_out_cubic,
             direction='left', distance=None):
        """Slide image in/out"""
        if distance is None:
            distance = self.w

        for i in range(frames):
            t = i / frames
            eased = easing_func(t)

            frame = self.builder.create_background()
            draw = ImageDraw.Draw(frame)

            if direction == 'left':
                x = int(-distance + eased * distance)
            elif direction == 'right':
                x = int(self.w - eased * distance)
            elif direction == 'down':
                x = 0
                y = int(-distance + eased * distance)
            elif direction == 'up':
                x = 0
                y = int(self.h - eased * distance)

            frame.paste(image, (x, y) if direction in ['left', 'right'] else (0, y))
            self.builder.add_frame(frame)

    def spin(self, image, frames=30, easing_func=Easing.ease_in_out_cubic,
            rotations=1, clockwise=True):
        """Spin image"""
        for i in range(frames):
            t = i / frames
            eased = easing_func(t)

            angle = eased * 360 * rotations
            if not clockwise:
                angle = -angle

            rotated = image.rotate(angle, expand=False)

            # Center on canvas
            x = (self.w - rotated.width) // 2
            y = (self.h - rotated.height) // 2

            frame = self.builder.create_background()
            frame.paste(rotated, (x, y), rotated if rotated.mode == 'RGBA' else None)
            self.builder.add_frame(frame)

    def bounce(self, image, frames=40, easing_func=Easing.ease_out_bounce,
              amplitude=50, y_base=None):
        """Bounce up and down"""
        if y_base is None:
            y_base = self.h // 2

        for i in range(frames):
            t = (i % frames) / frames
            eased = easing_func(t)

            y = int(y_base - eased * amplitude)
            x = (self.w - image.width) // 2

            frame = self.builder.create_background()
            frame.paste(image, (x, y), image if image.mode == 'RGBA' else None)
            self.builder.add_frame(frame)

    def pulse(self, image, frames=30, easing_func=Easing.ease_in_out_quad,
             scale_range=(0.8, 1.2)):
        """Pulse (grow/shrink)"""
        min_scale, max_scale = scale_range

        for i in range(frames):
            t = i / frames
            eased = easing_func(t)

            scale = min_scale + (max_scale - min_scale) * eased
            new_size = (int(image.width * scale), int(image.height * scale))
            scaled = image.resize(new_size, Image.Resampling.LANCZOS)

            x = (self.w - scaled.width) // 2
            y = (self.h - scaled.height) // 2

            frame = self.builder.create_background()
            frame.paste(scaled, (x, y), scaled if scaled.mode == 'RGBA' else None)
            self.builder.add_frame(frame)

    def shake(self, image, frames=20, intensity=5):
        """Shake/vibrate effect"""
        x_center = (self.w - image.width) // 2
        y_center = (self.h - image.height) // 2

        for i in range(frames):
            offset_x = int(math.cos(i * 0.8) * intensity)
            offset_y = int(math.sin(i * 0.6) * intensity)

            x = x_center + offset_x
            y = y_center + offset_y

            frame = self.builder.create_background()
            frame.paste(image, (x, y), image if image.mode == 'RGBA' else None)
            self.builder.add_frame(frame)

    def wiggle(self, image, frames=30, amplitude=10):
        """Side-to-side wiggle"""
        x_center = (self.w - image.width) // 2
        y_center = (self.h - image.height) // 2

        for i in range(frames):
            t = i / frames
            # Sine wave for smooth wiggle
            offset = int(math.sin(t * 2 * math.pi) * amplitude)

            frame = self.builder.create_background()
            frame.paste(image, (x_center + offset, y_center),
                       image if image.mode == 'RGBA' else None)
            self.builder.add_frame(frame)

    def zoom(self, image, frames=30, easing_func=Easing.ease_out_cubic,
            zoom_range=(0.5, 1.0)):
        """Zoom in or out"""
        min_zoom, max_zoom = zoom_range

        for i in range(frames):
            t = i / frames
            eased = easing_func(t)

            zoom = min_zoom + (max_zoom - min_zoom) * eased
            new_size = (int(image.width * zoom), int(image.height * zoom))
            zoomed = image.resize(new_size, Image.Resampling.LANCZOS)

            x = (self.w - zoomed.width) // 2
            y = (self.h - zoomed.height) // 2

            frame = self.builder.create_background()
            frame.paste(zoomed, (x, y), zoomed if zoomed.mode == 'RGBA' else None)
            self.builder.add_frame(frame)
```

### Step 4: Text Animation
```python
class TextAnimation:
    def __init__(self, builder, font_size=24, font_color='black'):
        self.builder = builder
        self.font_size = font_size
        self.font_color = font_color

    def typewriter(self, text, frames=60, easing_func=Easing.linear):
        """Typewriter effect: characters appear one by one"""
        chars_per_frame = max(1, len(text) / frames)

        for i in range(frames + 1):
            char_count = int(i * chars_per_frame)
            displayed_text = text[:char_count]

            frame = self.builder.create_background()
            draw = ImageDraw.Draw(frame)

            draw.text((50, self.builder.h // 2), displayed_text,
                     fill=self.font_color)

            self.builder.add_frame(frame)

    def fade_in_text(self, text, frames=30, easing_func=Easing.ease_in_out_quad):
        """Text fades in"""
        for i in range(frames):
            t = i / frames
            eased = easing_func(t)

            # Create transparent text image
            text_img = Image.new('RGBA', (self.builder.w, self.builder.h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(text_img)

            alpha = int(255 * eased)
            r, g, b = self.builder.hex_to_rgb(self.font_color)
            draw.text((50, self.builder.h // 2), text,
                     fill=(r, g, b, alpha))

            frame = self.builder.create_background()
            frame.paste(text_img, (0, 0), text_img)
            self.builder.add_frame(frame.convert('RGB'))

    def slide_in_text(self, text, frames=30, direction='left'):
        """Text slides in from edge"""
        for i in range(frames):
            t = i / frames

            frame = self.builder.create_background()
            draw = ImageDraw.Draw(frame)

            if direction == 'left':
                x = int(-100 + t * 150)
            elif direction == 'right':
                x = int(self.builder.w - t * 150)

            draw.text((x, self.builder.h // 2), text,
                     fill=self.font_color)

            self.builder.add_frame(frame)
```

### Step 5: Platform-Specific Optimization
```python
class PlatformOptimizer:
    PLATFORMS = {
        'slack_emoji': {'width': 128, 'height': 128, 'max_size_mb': 0.064},
        'slack_message': {'width': 480, 'height': 480, 'max_size_mb': 2.0},
        'discord': {'width': 512, 'height': 512, 'max_size_mb': 8.0},
        'twitter': {'width': 1200, 'height': 675, 'max_size_mb': 15.0},
        'web': {'width': 800, 'height': 600, 'max_size_mb': 5.0},
    }

    @staticmethod
    def optimize_for_platform(gif_path, platform='slack_emoji'):
        """Optimize GIF for specific platform constraints"""
        if platform not in PlatformOptimizer.PLATFORMS:
            raise ValueError(f"Unknown platform: {platform}")

        constraints = PlatformOptimizer.PLATFORMS[platform]
        max_size_bytes = constraints['max_size_mb'] * 1024 * 1024

        # Check current size
        current_size = Path(gif_path).stat().st_size

        if current_size <= max_size_bytes:
            return gif_path  # Already within limits

        # Optimize by reducing colors
        img = Image.open(gif_path)
        optimized_frames = []

        for frame_idx in range(getattr(img, 'n_frames', 1)):
            img.seek(frame_idx)
            # Reduce to 128 colors for smaller file size
            frame = img.quantize(colors=128)
            optimized_frames.append(frame)

        # Re-save optimized
        optimized_frames[0].save(
            gif_path,
            save_all=True,
            append_images=optimized_frames[1:],
            duration=getattr(img, 'info', {}).get('duration', 50),
            loop=0,
            optimize=True
        )

        return gif_path

    @staticmethod
    def get_constraints(platform):
        """Get dimension and size constraints"""
        return PlatformOptimizer.PLATFORMS.get(platform, {})
```

### Step 6: Color Quantization for Size Optimization
```python
class ColorQuantization:
    @staticmethod
    def reduce_palette(gif_path, color_count=128):
        """Reduce color palette to reduce file size"""
        img = Image.open(gif_path)
        optimized = []

        for frame_idx in range(getattr(img, 'n_frames', 1)):
            img.seek(frame_idx)
            quantized = img.quantize(colors=color_count)
            optimized.append(quantized)

        optimized[0].save(
            gif_path,
            save_all=True,
            append_images=optimized[1:],
            duration=getattr(img, 'info', {}).get('duration', 50),
            loop=0
        )

        return Path(gif_path).stat().st_size / (1024 * 1024)

    @staticmethod
    def remove_duplicate_frames(gif_path, threshold=0.95):
        """Remove frames that are >95% similar to reduce file size"""
        import numpy as np

        img = Image.open(gif_path)
        frames = []
        prev_hash = None

        for frame_idx in range(getattr(img, 'n_frames', 1)):
            img.seek(frame_idx)
            # Simple hash: convert to numpy and get mean of differences
            frame_array = np.array(img.resize((64, 64)))
            current_hash = frame_array.tobytes()

            # Keep frame if different enough from previous
            frames.append(img.copy())

            prev_hash = current_hash

        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=50,
            loop=0,
            optimize=True
        )

        return len(frames)
```

### Step 7: Complete Animation Builder Example
```python
def create_animated_spinner():
    """Example: Create loading spinner for Slack"""
    builder = GIFBuilder(width=128, height=128, duration_ms=50, loop=0)

    # Create animation
    anim = AnimationPrimitives(builder)

    # White background
    bg = builder.create_background(bg_color='#FFFFFF')

    # Draw spinner circle
    spinner = Image.new('RGBA', (100, 100), (255, 255, 255, 0))
    draw = ImageDraw.Draw(spinner)
    draw.arc([(10, 10), (90, 90)], 0, 270, fill='#0A3D62', width=8)

    # Animate rotation
    for i in range(12):
        angle = (i / 12) * 360
        rotated = spinner.rotate(angle)
        x = (128 - rotated.width) // 2
        y = (128 - rotated.height) // 2

        frame = bg.copy()
        frame.paste(rotated, (x, y), rotated)
        builder.add_frame(frame)

    # Save and optimize for Slack
    builder.save('spinner.gif', optimize=True)
    return 'spinner.gif'
```

## Output Template
```
GIF Animation Report:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SPECIFICATIONS:
  Dimensions: [W×H pixels]
  Frame Count: [N frames]
  Duration: [X ms per frame = Y fps]
  Loop: [infinite/N repeats]

ANIMATIONS APPLIED:
  ✓ [Animation 1]: [easing function, duration]
  ✓ [Animation 2]: [easing function, duration]
  ✓ [Animation N]: [easing function, duration]

COLOR OPTIMIZATION:
  Palette: [256/128/64 colors]
  Quantization: [enabled/disabled]
  Frame Diffing: [enabled/disabled]

PLATFORM COMPLIANCE:
  Target: [Platform]
  Max Size: [X MB]
  Current Size: [Y MB]
  Status: [COMPLIANT/NEEDS OPTIMIZATION]

FINAL OUTPUT:
  File: [filename]
  Size: [X MB]
  Quality: [high/medium/optimized]
```

## Quality Gates

1. **Smooth Motion**: Easing functions must be applied; linear motion only for simple effects.
2. **Frame Rate**: Minimum 15 FPS (67ms per frame), maximum 30 FPS (33ms per frame) for smooth appearance.
3. **Color Fidelity**: Palette reduction should not create visible banding or posterization.
4. **Platform Compliance**: File size must be within platform limits; optimize if exceeded.
5. **No Artifacts**: Rotation, scaling, and compositing must be smooth without visible seams.
6. **Timing Consistency**: All frames must have consistent duration unless intentionally varied.
7. **File Size**: Optimized frames should reduce size by 30-50% with no perceptible quality loss.

## Examples

### Good Animation
```
Platform: Slack Emoji (128×128, max 64KB)
Animation: Spinning circle with easing_in_out_cubic rotation
  - 12 frames, 50ms each = 0.6 second spin
  - 256-color quantized palette
  - Final size: 45KB (within limits)
  - Result: Smooth professional spinner
```

### Bad Animation
```
✗ Linear spinning (jerky, feels cheap)
✗ 60 frames at 30ms (file size 200KB, exceeds Slack limit)
✗ No easing functions (motion looks mechanical)
✗ Unoptimized palette (uses all 256 colors unnecessarily)
✗ Inconsistent frame durations (jumpy, unprofessional)
```

## Common Mistakes

1. **No Easing Functions**: Linear motion feels cheap and mechanical. Always use ease_in_out_quad minimum.
2. **Too Many Frames**: 60+ frames for simple animations wastes file size. 12-30 frames usually sufficient.
3. **Ignoring Platform Limits**: Creating 15MB GIFs for Slack (max 64KB). Test platform constraints first.
4. **Poor Color Quantization**: Using 256 colors for simple animations. Reduce to 128 or 64 colors.
5. **Lack of Timing Control**: Not varying frame duration; all frames same speed feels robotic.

## Anti-Patterns

1. **Mixing Multiple Complex Animations**: Bounce + Spin + Fade simultaneously looks chaotic. Sequence them instead.
2. **Animation Duration Too Long**: 3+ second animations for simple effects frustrate users. Keep to <2 seconds.
3. **No Background Consideration**: Animating without testing on actual background colors; might be invisible.
4. **Over-Optimization**: Reducing to 16 colors creates visible banding. 128-256 colors is sweet spot.
5. **Ignoring Easing Direction**: Using ease_out for entrance (backwards); should be ease_in. Match easing to animation phase.
