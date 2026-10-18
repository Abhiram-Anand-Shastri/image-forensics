from pathlib import Path

import cv2
import numpy as np

from modules import hashing, metadata, noise_analysis

META_FIELDS = ["format", "dimensions", "make", "model", "software",
               "datetime_original", "datetime_digitized", "datetime_modified", "gps"]


def interpret_phash(d):
    if d == 0:
        return "Visually identical"
    if d <= 10:
        return "Very similar (same picture, minor changes)"
    if d <= 20:
        return "Similar but clearly modified (derivative image)"
    return "Probably different images"


def metadata_diff(orig_path, susp_path):
    a = metadata.extract_metadata(orig_path)
    b = metadata.extract_metadata(susp_path)
    return [{"field": f, "original": str(a[f]), "suspect": str(b[f]),
             "changed": "YES" if a[f] != b[f] else ""} for f in META_FIELDS]


def pixel_difference(orig_path, susp_path, out_dir="outputs",
                     thresh=25, min_area=200):
    """Highlight where the suspect differs from the original.
    If sizes differ, only the overlapping top-left area is compared."""
    a = cv2.imread(str(orig_path))
    b = cv2.imread(str(susp_path))
    size_mismatch = a.shape != b.shape
    h = min(a.shape[0], b.shape[0])
    w = min(a.shape[1], b.shape[1])
    a, b = a[:h, :w], b[:h, :w]

    gray = cv2.cvtColor(cv2.absdiff(a, b), cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # Threshold ignores the small differences caused by JPEG re-saving
    mask = (gray > thresh).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    regions = [cv2.boundingRect(c) for c in contours if cv2.contourArea(c) >= min_area]

    boxes = b.copy()
    for x, y, rw, rh in regions:
        cv2.rectangle(boxes, (x, y), (x + rw, y + rh), (0, 0, 255), 2)
    heat = cv2.applyColorMap(np.clip(gray.astype(np.float32) * 4, 0, 255).astype(np.uint8),
                             cv2.COLORMAP_JET)

    out = Path(out_dir)
    out.mkdir(exist_ok=True)
    stem = Path(susp_path).stem
    heat_path = out / f"{stem}_diff_heatmap.png"
    box_path = out / f"{stem}_diff_regions.png"
    cv2.imwrite(str(heat_path), heat)
    cv2.imwrite(str(box_path), boxes)

    return {
        "compared_area": f"{w} x {h}",
        "size_mismatch": size_mismatch,
        "changed_pixels_pct": round(float((mask > 0).mean() * 100), 2),
        "changed_regions": len(regions),
        "heatmap": str(heat_path),
        "regions_image": str(box_path),
    }


def compare(orig_path, susp_path):
    ha = hashing.compute_file_hashes(orig_path)
    hb = hashing.compute_file_hashes(susp_path)
    pa = hashing.compute_perceptual_hashes(orig_path)["phash"]
    pb = hashing.compute_perceptual_hashes(susp_path)["phash"]
    dist = int(hashing.hamming_distance(pa, pb))

    qa, _ = noise_analysis.jpeg_quality_estimate(orig_path)
    qb, _ = noise_analysis.jpeg_quality_estimate(susp_path)

    return {
        "sha256_match": ha["sha256"] == hb["sha256"],
        "phash_distance": dist,
        "phash_interpretation": interpret_phash(dist),
        "quality_original": qa,
        "quality_suspect": qb,
        "metadata_diff": metadata_diff(orig_path, susp_path),
        "pixel": pixel_difference(orig_path, susp_path),
    }