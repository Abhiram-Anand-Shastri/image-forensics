from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (Image as RLImage, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)


def _kv_table(rows):
    t = Table(rows, colWidths=[5 * cm, 11 * cm])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def _wrap(rows, style):
    """Wrap long values (like SHA-256) so they don't overflow the cell."""
    return [[Paragraph(str(k), style), Paragraph(str(v), style)] for k, v in rows]


def _image(path, width_cm=16):
    from PIL import Image
    with Image.open(path) as im:
        w, h = im.size
    return RLImage(str(path), width=width_cm * cm, height=width_cm * cm * h / w)


def build_report(results, out_path="outputs/forensic_report.pdf", comparison=None):
    """results = dict with keys: hashing, metadata, ela, copy_move, noise."""
    styles = getSampleStyleSheet()
    small = styles["BodyText"]
    small.fontSize = 8
    doc = SimpleDocTemplate(str(out_path), pagesize=A4,
                            leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm)
    s = []

    s.append(Paragraph("Digital Image Forensics Report", styles["Title"]))
    s.append(Paragraph(f"Generated: {datetime.now():%Y-%m-%d %H:%M}", styles["Normal"]))
    s.append(Spacer(1, 12))

    s.append(Paragraph("1. File integrity", styles["Heading2"]))
    h = results["hashing"]
    keys = ["filename", "size_bytes", "md5", "sha256", "phash", "ahash", "dhash", "copy_verified"]
    s.append(_kv_table(_wrap([(k, h[k]) for k in keys], small)))
    s.append(Spacer(1, 12))

    s.append(Paragraph("2. Metadata", styles["Heading2"]))
    m = results["metadata"]
    rows = [(k, v) for k, v in m.items() if k != "anomalies"]
    s.append(_kv_table(_wrap(rows, small)))
    s.append(Spacer(1, 6))
    flags = m["anomalies"] or ["None"]
    for f in flags:
        s.append(Paragraph(f"&bull; {f}", small))
    s.append(PageBreak())

    s.append(Paragraph("3. Error Level Analysis", styles["Heading2"]))
    e = results["ela"]
    s.append(_kv_table(_wrap([(k, e[k]) for k in
             ("mean_error", "max_block_error", "suspicious_block_pct")], small)))
    s.append(Spacer(1, 6))
    s.append(_image(e["comparison"]))
    s.append(PageBreak())

    s.append(Paragraph("4. Copy-move detection", styles["Heading2"]))
    c = results["copy_move"]
    s.append(_kv_table(_wrap([(k, c[k]) for k in
             ("keypoints", "candidate_pairs", "inliers", "verdict")], small)))
    if c["output"]:
        s.append(Spacer(1, 6))
        s.append(_image(c["output"]))
    s.append(PageBreak())

    s.append(Paragraph("5. Noise analysis", styles["Heading2"]))
    n = results["noise"]
    s.append(_kv_table(_wrap([(k, n[k]) for k in
             ("median_noise", "noise_outlier_pct", "jpeg_quality_est")], small)))
    s.append(Spacer(1, 6))
    s.append(_image(n["noise_map"]))
    s.append(Spacer(1, 12))
    if comparison:
        s.append(PageBreak())
        s.append(Paragraph("6. Comparison with original", styles["Heading2"]))
        px = comparison["pixel"]
        rows = [
            ("SHA-256 identical", comparison["sha256_match"]),
            ("pHash distance", f"{comparison['phash_distance']} / 64"),
            ("Interpretation", comparison["phash_interpretation"]),
            ("JPEG quality (orig / suspect)",
             f"{comparison['quality_original']} / {comparison['quality_suspect']}"),
            ("Compared area", px["compared_area"]),
            ("Changed pixels (%)", px["changed_pixels_pct"]),
            ("Changed regions", px["changed_regions"]),
        ]
        s.append(_kv_table(_wrap(rows, small)))
        s.append(Spacer(1, 6))
        changed = [(d["field"], f"{d['original']}  ->  {d['suspect']}")
                   for d in comparison["metadata_diff"] if d["changed"]]
        s.append(Paragraph("Changed metadata fields", styles["Heading3"]))
        s.append(_kv_table(_wrap(changed or [("None", "No metadata differences")], small)))
        s.append(Spacer(1, 6))
        s.append(_image(px["regions_image"]))
        s.append(Spacer(1, 12))    
    s.append(Paragraph("Note", styles["Heading3"]))
    s.append(Paragraph(
        "Automated indicators are hints, not proof. ELA is unreliable on resized or "
        "heavily recompressed images, copy-move detection only finds duplication "
        "within one image, and noise analysis misses patches from similar sources. "
        "Findings should be interpreted together by a human examiner.", small))

    doc.build(s)
    return str(out_path)