import io
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # save to file, no pop-up window
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageChops


def run_ela(path, quality=90):
    """Re-save as JPEG and return the (amplified) difference image + raw array."""
    original = Image.open(path).convert("RGB")

    buffer = io.BytesIO()
    original.save(buffer, "JPEG", quality=quality)
    buffer.seek(0)
    resaved = Image.open(buffer).convert("RGB")

    diff = np.asarray(ImageChops.difference(original, resaved)).astype(np.float32)

    # Scale so the brightest 0.5% of pixels hit white (robust to outliers)
    top = np.percentile(diff, 99.5)
    scale = 255.0 / top if top > 0 else 1.0
    ela_img = Image.fromarray(np.clip(diff * scale, 0, 255).astype(np.uint8))
    return original, ela_img, diff


def block_statistics(diff, block=16):
    """Average error level per block; blocks far above the rest are suspicious."""
    gray = diff.mean(axis=2)
    h, w = gray.shape
    h, w = h - h % block, w - w % block
    blocks = gray[:h, :w].reshape(h // block, block, w // block, block).mean(axis=(1, 3))
    threshold = blocks.mean() + 3 * blocks.std()
    return {
        "mean_error": round(float(gray.mean()), 3),
        "max_block_error": round(float(blocks.max()), 3),
        "suspicious_block_pct": round(float((blocks > threshold).mean() * 100), 2),
    }


def analyze(path, quality=90, out_dir="outputs"):
    original, ela_img, diff = run_ela(path, quality)
    stats = block_statistics(diff)

    out = Path(out_dir)
    out.mkdir(exist_ok=True)
    stem = Path(path).stem
    ela_path = out / f"{stem}_ela.png"
    ela_img.save(ela_path)

    # Side-by-side figure for the report
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].imshow(original)
    axes[0].set_title("Original")
    axes[1].imshow(ela_img)
    axes[1].set_title(f"ELA (quality={quality})")
    for ax in axes:
        ax.axis("off")
    fig_path = out / f"{stem}_ela_comparison.png"
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return {**stats, "ela_image": str(ela_path), "comparison": str(fig_path)}