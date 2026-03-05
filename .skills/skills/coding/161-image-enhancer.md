---
name: image-enhancer
description: "Enhance image quality using Python (Pillow, OpenCV) with sharpening, noise reduction, color correction, and upscaling"
category: coding
difficulty: intermediate
model_boost: "Weak models don't diagnose image problems first, apply generic filters, miss format-specific optimization, and produce over-sharpened or over-saturated results"
---

# Image Enhancer

## Purpose
Diagnose and enhance image quality across multiple dimensions: resolution, sharpness, clarity, color accuracy, and noise. This skill analyzes source images, applies targeted enhancements, and exports optimized outputs for specific use cases (web, print, archive). All techniques use parameter values tested for quality outputs.

## When to Use
- Improving photograph quality (exposure, color, sharpness)
- Enhancing scanned documents (clarity, contrast, noise removal)
- Upscaling low-resolution images while preserving detail
- Batch processing multiple images with consistent improvements
- Optimizing format and compression for specific platforms

## Do NOT Use When
- Creating AI-generated images (use generative models instead)
- Dramatically changing composition or removing/adding objects (use image editing tools)
- Restoring severely damaged or corrupted images (use specialized restoration software)

## Instructions

### Step 1: Image Diagnosis System
```python
import cv2
import numpy as np
from PIL import Image
import math

class ImageAnalyzer:
    def __init__(self, image_path):
        self.img_cv = cv2.imread(image_path)
        self.img_pil = Image.open(image_path)
        self.h, self.w = self.img_cv.shape[:2]
        self.diagnosis = {}

    def detect_blur(self):
        """Estimate blur using Laplacian variance (lower = more blur)"""
        gray = cv2.cvtColor(self.img_cv, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        if laplacian_var < 100:
            severity = "heavy"
        elif laplacian_var < 500:
            severity = "moderate"
        elif laplacian_var < 1000:
            severity = "mild"
        else:
            severity = "none"

        self.diagnosis['blur'] = {
            'laplacian_variance': round(laplacian_var, 2),
            'severity': severity
        }
        return self.diagnosis['blur']

    def detect_noise(self):
        """Estimate noise level (higher = more noise)"""
        gray = cv2.cvtColor(self.img_cv, cv2.COLOR_BGR2GRAY)

        # Use Laplacian as noise detector
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        noise_level = np.std(laplacian)

        if noise_level > 200:
            severity = "heavy"
        elif noise_level > 100:
            severity = "moderate"
        elif noise_level > 30:
            severity = "mild"
        else:
            severity = "none"

        self.diagnosis['noise'] = {
            'noise_level': round(noise_level, 2),
            'severity': severity
        }
        return self.diagnosis['noise']

    def detect_exposure(self):
        """Analyze exposure levels (brightness)"""
        gray = cv2.cvtColor(self.img_cv, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)

        if mean_brightness < 50:
            condition = "underexposed"
        elif mean_brightness > 200:
            condition = "overexposed"
        else:
            condition = "correct"

        self.diagnosis['exposure'] = {
            'mean_brightness': round(mean_brightness, 2),
            'condition': condition
        }
        return self.diagnosis['exposure']

    def detect_color_cast(self):
        """Detect color cast (red/green/blue dominance)"""
        img = cv2.cvtColor(self.img_cv, cv2.COLOR_BGR2RGB)

        b_mean = np.mean(self.img_cv[:, :, 0])
        g_mean = np.mean(self.img_cv[:, :, 1])
        r_mean = np.mean(self.img_cv[:, :, 2])

        means = {'blue': b_mean, 'green': g_mean, 'red': r_mean}
        dominant = max(means, key=means.get)

        self.diagnosis['color_cast'] = {
            'dominant_channel': dominant,
            'values': {k: round(v, 2) for k, v in means.items()}
        }
        return self.diagnosis['color_cast']

    def get_resolution(self):
        """Current resolution and suggested upscale factor"""
        pixels = self.w * self.h

        if pixels < 1_000_000:  # < 1 MP
            upscale = 4
            quality = "very_low"
        elif pixels < 2_000_000:  # < 2 MP
            upscale = 3
            quality = "low"
        elif pixels < 5_000_000:  # < 5 MP
            upscale = 2
            quality = "medium"
        else:
            upscale = 1
            quality = "high"

        self.diagnosis['resolution'] = {
            'width': self.w,
            'height': self.h,
            'megapixels': round(pixels / 1_000_000, 2),
            'quality_level': quality,
            'suggested_upscale': upscale
        }
        return self.diagnosis['resolution']

    def full_diagnosis(self):
        """Run complete analysis"""
        self.detect_blur()
        self.detect_noise()
        self.detect_exposure()
        self.detect_color_cast()
        self.get_resolution()
        return self.diagnosis
```

### Step 2: Sharpening Techniques
```python
class SharpeningEngine:
    @staticmethod
    def unsharp_mask(img_cv, radius=1.0, strength=1.5):
        """Unsharp mask: high-quality sharpening (default for photos)"""
        gaussian = cv2.GaussianBlur(img_cv, (0, 0), radius)
        sharpened = cv2.addWeighted(img_cv, 1.0 + strength, gaussian, -strength, 0)
        return np.clip(sharpened, 0, 255).astype(np.uint8)

    @staticmethod
    def laplacian_sharpen(img_cv, strength=0.5):
        """Laplacian sharpening: aggressive edge enhancement"""
        laplacian = cv2.Laplacian(img_cv, cv2.CV_64F)
        sharpened = cv2.convertScaleAbs(img_cv + laplacian * strength)
        return sharpened

    @staticmethod
    def high_pass_sharpen(img_cv, radius=5, strength=0.7):
        """High-pass filter sharpening: subtle but effective"""
        gaussian = cv2.GaussianBlur(img_cv, (0, 0), radius)
        high_pass = cv2.subtract(img_cv.astype(np.float32),
                                gaussian.astype(np.float32)) + 128
        sharpened = cv2.addWeighted(img_cv.astype(np.float32), 1.0,
                                   (high_pass - 128), strength, 0)
        return np.clip(sharpened, 0, 255).astype(np.uint8)

    # Recommended parameters by use case:
    # Photos: unsharp_mask(radius=1.0, strength=1.5)
    # Screenshots: unsharp_mask(radius=0.5, strength=2.0)
    # Documents: laplacian_sharpen(strength=1.0)
```

### Step 3: Noise Reduction Techniques
```python
class NoiseReductionEngine:
    @staticmethod
    def bilateral_filter(img_cv, diameter=9, sigma_color=75, sigma_space=75):
        """Bilateral filter: preserves edges while reducing noise (BEST for photos)"""
        denoised = cv2.bilateralFilter(img_cv, diameter, sigma_color, sigma_space)
        return denoised

    @staticmethod
    def non_local_means(img_cv, h=10, template_window=7, search_window=21):
        """Non-local means: excellent for detailed noise reduction"""
        denoised = cv2.fastNlMeansDenoisingColored(
            img_cv,
            None,
            h=h,  # Filter strength (higher = more smoothing)
            templateWindowSize=template_window,
            searchWindowSize=search_window
        )
        return denoised

    @staticmethod
    def morphological_denoise(img_cv, kernel_size=5):
        """Morphological operations: removes small noise"""
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        denoised = cv2.morphologyEx(img_cv, cv2.MORPH_OPEN, kernel)
        return denoised

    # Recommended parameters by use case:
    # Light noise: bilateral_filter(diameter=9, sigma_color=75, sigma_space=75)
    # Heavy noise: non_local_means(h=10, template_window=7, search_window=21)
    # Screenshots: morphological_denoise(kernel_size=3)
```

### Step 4: Contrast and Exposure Enhancement
```python
class ContrastEngine:
    @staticmethod
    def clahe(img_cv, clip_limit=2.0, tile_size=8):
        """CLAHE (Contrast Limited Adaptive Histogram Equalization)
        Best for maintaining local contrast without washing out"""

        if len(img_cv.shape) == 3:  # Color image
            lab = cv2.cvtColor(img_cv, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)

            clahe = cv2.createCLAHE(clipLimit=clip_limit,
                                   tileGridSize=(tile_size, tile_size))
            l_clahe = clahe.apply(l)

            enhanced = cv2.merge([l_clahe, a, b])
            return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        else:  # Grayscale
            clahe = cv2.createCLAHE(clipLimit=clip_limit,
                                   tileGridSize=(tile_size, tile_size))
            return clahe.apply(img_cv)

    @staticmethod
    def histogram_equalization(img_cv, strength=1.0):
        """Global histogram equalization (good for scanned documents)"""
        if len(img_cv.shape) == 3:  # Color
            hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
            h, s, v = cv2.split(hsv)
            v_eq = cv2.equalizeHist(v)
            enhanced = cv2.merge([h, s, v_eq])
            return cv2.cvtColor(enhanced, cv2.COLOR_HSV2BGR)
        else:  # Grayscale
            return cv2.equalizeHist(img_cv)

    @staticmethod
    def exposure_adjustment(img_cv, brightness_delta=0, contrast_factor=1.0):
        """Manual brightness and contrast adjustment"""
        adjusted = cv2.convertScaleAbs(img_cv.astype(np.float32) * contrast_factor
                                      + brightness_delta)
        return np.clip(adjusted, 0, 255).astype(np.uint8)

    # Recommended parameters by use case:
    # Photos: clahe(clip_limit=2.0, tile_size=8)
    # Documents: histogram_equalization(strength=1.0)
    # Underexposed: exposure_adjustment(brightness_delta=30, contrast_factor=1.2)
```

### Step 5: Color Correction
```python
class ColorCorrectionEngine:
    @staticmethod
    def white_balance(img_cv, method="gray_world"):
        """Correct color cast"""
        if method == "gray_world":
            # Gray world assumption
            result = cv2.cvtColor(img_cv, cv2.COLOR_BGR2LAB)
            avg_a = np.mean(result[:, :, 1])
            avg_b = np.mean(result[:, :, 2])
            result[:, :, 1] -= (avg_a - 128)
            result[:, :, 2] -= (avg_b - 128)
            return cv2.cvtColor(result, cv2.COLOR_LAB2BGR)

        elif method == "simplest_cb":
            # Simplest Color Balance
            h, w = img_cv.shape[:2]
            sample_size = int(h * w * 0.001)  # 0.1% of pixels

            bgr_planes = cv2.split(img_cv.astype(np.float32))
            white_level = max([np.percentile(p.flatten(), 99) for p in bgr_planes])
            result = np.zeros_like(img_cv, dtype=np.float32)

            for i in range(3):
                result[:, :, i] = bgr_planes[i] * (255 / white_level)

            return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def saturation_adjustment(img_cv, factor=1.0):
        """Adjust color saturation (1.0 = original, >1.0 = more vibrant)"""
        hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] *= factor
        hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
        return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    @staticmethod
    def temperature_adjustment(img_cv, kelvin_shift=0):
        """Adjust color temperature (-1000K = warmer/orange, +1000K = cooler/blue)"""
        if kelvin_shift > 0:  # Cooler (add blue)
            img_cv[:, :, 2] = np.clip(img_cv[:, :, 2] + kelvin_shift // 100, 0, 255)
        else:  # Warmer (add red)
            img_cv[:, :, 0] = np.clip(img_cv[:, :, 0] - kelvin_shift // 100, 0, 255)
        return img_cv
```

### Step 6: Upscaling Techniques
```python
class UpscalingEngine:
    @staticmethod
    def lanczos_upscale(img_pil, factor=2):
        """Lanczos interpolation: best quality for 2-4x upscaling"""
        new_size = (int(img_pil.width * factor),
                   int(img_pil.height * factor))
        return img_pil.resize(new_size, Image.Resampling.LANCZOS)

    @staticmethod
    def cubic_upscale(img_pil, factor=2):
        """Cubic interpolation: good balance of speed and quality"""
        new_size = (int(img_pil.width * factor),
                   int(img_pil.height * factor))
        return img_pil.resize(new_size, Image.Resampling.BICUBIC)

    @staticmethod
    def edge_enhanced_upscale(img_cv, factor=2):
        """Upscale with edge enhancement to maintain sharpness"""
        h, w = img_cv.shape[:2]
        new_h, new_w = int(h * factor), int(w * factor)

        # Upscale using Lanczos via OpenCV
        upscaled = cv2.resize(img_cv, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

        # Apply light sharpening to enhance edges
        sharpened = SharpeningEngine.unsharp_mask(upscaled, radius=1.0, strength=0.8)
        return sharpened

    # Recommended parameters by use case:
    # Photos: lanczos_upscale(factor=2) for 2x, avoid 4x+ upscaling
    # Screenshots: cubic_upscale(factor=2-3)
    # Maximum quality: edge_enhanced_upscale(factor=2)
```

### Step 7: Batch Processing
```python
class BatchProcessor:
    def __init__(self, input_folder, output_folder):
        self.input_folder = input_folder
        self.output_folder = output_folder

    def process_folder(self, enhancement_preset="balanced"):
        """Apply consistent enhancements to all images in folder"""
        import os
        from pathlib import Path

        os.makedirs(self.output_folder, exist_ok=True)
        results = []

        for filename in os.listdir(self.input_folder):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                img_path = os.path.join(self.input_folder, filename)
                output_path = os.path.join(self.output_folder, filename)

                try:
                    analyzer = ImageAnalyzer(img_path)
                    diagnosis = analyzer.full_diagnosis()

                    img_cv = cv2.imread(img_path)
                    enhanced = self._apply_preset(img_cv, enhancement_preset, diagnosis)

                    cv2.imwrite(output_path, enhanced)
                    results.append({'file': filename, 'status': 'success'})
                except Exception as e:
                    results.append({'file': filename, 'status': 'error', 'error': str(e)})

        return results

    def _apply_preset(self, img_cv, preset, diagnosis):
        """Apply enhancement preset based on diagnosis"""
        if preset == "balanced":
            img = NoiseReductionEngine.bilateral_filter(img_cv, diameter=9)
            img = SharpeningEngine.unsharp_mask(img, radius=1.0, strength=1.5)
            img = ContrastEngine.clahe(img, clip_limit=2.0)
            return img

        elif preset == "document":
            img = NoiseReductionEngine.non_local_means(img_cv)
            img = ContrastEngine.histogram_equalization(img)
            img = SharpeningEngine.laplacian_sharpen(img, strength=1.0)
            return img

        elif preset == "aggressive":
            img = NoiseReductionEngine.non_local_means(img_cv, h=12)
            img = SharpeningEngine.high_pass_sharpen(img, radius=5, strength=1.0)
            img = ContrastEngine.clahe(img, clip_limit=3.0)
            return img

        return img_cv
```

### Step 8: Format Conversion and Compression
```python
class ExportOptimizer:
    @staticmethod
    def to_png(img_pil, filepath, compress_level=9):
        """Export as PNG with optimization"""
        img_pil.save(filepath, 'PNG', optimize=True, compress_level=compress_level)

    @staticmethod
    def to_jpg(img_pil, filepath, quality=85):
        """Export as JPG with quality control
        quality=85: Good balance (use for photos)
        quality=90: High quality (use for prints)
        quality=75: Web-optimized (use for web)"""

        rgb_image = img_pil.convert('RGB')
        rgb_image.save(filepath, 'JPEG', quality=quality, optimize=True)

    @staticmethod
    def to_webp(img_pil, filepath, quality=80):
        """Export as WebP (smallest file size)"""
        img_pil.save(filepath, 'WebP', quality=quality, method=6)

    @staticmethod
    def estimate_file_size(img_pil, format_type, quality):
        """Estimate file size before export"""
        from io import BytesIO

        buffer = BytesIO()
        if format_type.upper() == 'PNG':
            img_pil.save(buffer, 'PNG', optimize=True)
        elif format_type.upper() == 'JPG':
            img_pil.convert('RGB').save(buffer, 'JPEG', quality=quality, optimize=True)
        elif format_type.upper() == 'WEBP':
            img_pil.save(buffer, 'WebP', quality=quality, method=6)

        return buffer.tell() / (1024 * 1024)  # MB
```

## Output Template
```
Enhancement Report:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOURCE DIAGNOSIS:
  Blur Severity: [none/mild/moderate/heavy]
  Noise Level: [Laplacian σ value]
  Exposure: [underexposed/correct/overexposed]
  Color Cast: [dominant channel]
  Resolution: [W×H, megapixels, quality tier]

ENHANCEMENTS APPLIED:
  ✓ Noise Reduction: [bilateral_filter/non_local_means/morphological]
  ✓ Sharpening: [unsharp_mask/laplacian/high_pass] (strength: X)
  ✓ Contrast: [clahe/histogram_eq] (clip_limit/strength: X)
  ✓ Color: [white_balance method, saturation adjustment]
  ✓ Upscaling: [none/Lanczos 2x/Lanczos 4x]

EXPORT:
  Format: [PNG/JPG/WebP]
  Quality: [score 0-100]
  File Size: [estimated MB]
  Dimensions: [W×H pixels]
```

## Quality Gates

1. **No Over-Processing**: Enhancements should look natural, not artificial or hyper-saturated.
2. **Edge Preservation**: Sharpening must not create halos around objects.
3. **Noise vs Smoothness**: Noise reduction should not blur fine details.
4. **Color Accuracy**: Adjusted colors should appear natural, not shifted.
5. **Resolution Integrity**: Upscaling should use Lanczos minimum; no visible artifacts.
6. **Contrast Visibility**: Enhanced contrast must aid readability without crushing blacks/whites.
7. **File Size Optimization**: Final export optimized for use case (web: <500KB, print: >2MB).

## Examples

### Good Enhancement
```
Original: 1200×800px, underexposed (brightness=95), heavy noise (σ=150)
Process:
  1. Diagnosis confirms: underexposure + noise
  2. Apply: bilateral_filter (diameter=9, σ=75)
  3. Apply: exposure_adjustment(brightness_delta=+30)
  4. Apply: unsharp_mask(radius=1.0, strength=1.5)
  5. Apply: clahe(clip_limit=2.0)
Result: Clear, vibrant, sharp without artifacts
```

### Bad Enhancement
```
✗ Over-sharpened (creates halos around edges)
✗ Color saturation turned to 200% (unrealistic skin tones)
✗ Applied 4x upscaling without edge enhancement (blocky)
✗ Noise reduction too aggressive (loses fine details)
✗ Histogram equalization without CLAHE (destroys local contrast)
```

## Common Mistakes

1. **Over-Sharpening**: Using strength > 2.0 creates halo artifacts. Keep to 0.8-1.5 range.
2. **Wrong Noise Algorithm**: Using morphological denoise for all cases; bilateral filter is better for photos, non-local means for heavy noise.
3. **Skipping Diagnosis**: Applying same enhancement to underexposed and overexposed images. Diagnose first.
4. **Upscaling Too Much**: 4x+ upscaling degrades quality. Use 2x Lanczos for best results.
5. **Ignoring Format**: Exporting all images as JPG destroys transparency; use PNG when needed.

## Anti-Patterns

1. **Aggressive Noise + Aggressive Sharpening**: Contradictory; creates artificial look.
2. **Histogram Equalization Globally**: Destroys natural tones. Use CLAHE instead.
3. **Color Saturation Without White Balance**: Creates weird color casts. Balance first, saturate second.
4. **Excessive Contrast Before Sharpening**: Pre-sharpening blur causes artifacts. Sharpen last.
5. **JPG Recompression**: Never load JPG, enhance, save as JPG again. Use PNG intermediate format.
