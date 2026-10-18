from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy.ndimage import median_filter


def noise_residual(gray):
    """Noise = image minus its denoised (median-filtered) version."""
    return gray - median_filter(gray, size=3)


def block_noise_map(residual, block=32):
    h, w = residual.shape
    h, w = h - h % block, w - w % block
    blocks = residual[:h, :w].reshape(h // block, block, w // block, block)
    return blocks.std(axis=(1, 3))


def jpeg_quality_estimate(path):
    """Rough JPEG quality from the luminance quantization table."""
    with Image.open(path) as img:
        q = getattr(img, "quantization", None)
    if not q:
        return None, None
    table = np.array(q[0])
    avg = float(table.mean())
    # Standard table averages ~57.7 at quality 50; scale from there.
    quality = 100 - avg * 50 / 57.7 if avg < 57.7 else 5000 / (avg / 57.7 * 100)
    return round(float(np.clip(quality, 1, 100)), 1), table.tolist()


def analyze(path, out_dir="outputs"):
    gray = np.asarray(Image.open(path).convert("L")).astype(np.float32)
    residual = noise_residual(gray)
    nmap = block_noise_map(residual)

    # Robust outlier test: median absolute deviation (not fooled by the outliers)
    med = np.median(nmap)
    mad = np.median(np.abs(nmap - med)) or 1e-6
    z = 0.6745 * (nmap - med) / mad
    outlier_pct = float((np.abs(z) > 3.5).mean() * 100)

    quality, _ = jpeg_quality_estimate(path)

    out = Path(out_dir)
    out.mkdir(exist_ok=True)
    stem = Path(path).stem
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].imshow(gray, cmap="gray")
    axes[0].set_title("Grayscale")
    im = axes[1].imshow(nmap, cmap="inferno")
    axes[1].set_title("Block noise level (32x32)")
    fig.colorbar(im, ax=axes[1], fraction=0.046)
    for ax in axes:
        ax.axis("off")
    fig_path = out / f"{stem}_noise.png"
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return {
        "median_noise": round(float(med), 3),
        "noise_outlier_pct": round(outlier_pct, 2),
        "jpeg_quality_est": quality,
        "noise_map": str(fig_path),
    }