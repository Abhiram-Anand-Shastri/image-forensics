from pathlib import Path

import exifread
from PIL import Image

EDITING_SOFTWARE = ["photoshop", "gimp", "lightroom", "paint", "snapseed",
                    "picsart", "canva", "affinity", "pixelmator", "facetune"]


def _to_degrees(values):
    d, m, s = [float(x.num) / float(x.den) for x in values]
    return d + m / 60 + s / 3600


def extract_gps(tags):
    """Convert EXIF GPS tags to decimal latitude/longitude."""
    try:
        lat = _to_degrees(tags["GPS GPSLatitude"].values)
        lon = _to_degrees(tags["GPS GPSLongitude"].values)
        if str(tags["GPS GPSLatitudeRef"]) == "S":
            lat = -lat
        if str(tags["GPS GPSLongitudeRef"]) == "W":
            lon = -lon
        return {"latitude": round(lat, 6), "longitude": round(lon, 6)}
    except (KeyError, ZeroDivisionError):
        return None


def extract_metadata(path):
    """Pull the forensically useful EXIF fields from an image."""
    with open(path, "rb") as f:
        tags = exifread.process_file(f, details=False)

    def get(name):
        return str(tags[name]) if name in tags else None

    with Image.open(path) as img:
        width, height = img.size
        fmt = img.format

    return {
        "format": fmt,
        "dimensions": f"{width} x {height}",
        "make": get("Image Make"),
        "model": get("Image Model"),
        "software": get("Image Software"),
        "datetime_original": get("EXIF DateTimeOriginal"),
        "datetime_digitized": get("EXIF DateTimeDigitized"),
        "datetime_modified": get("Image DateTime"),
        "exposure_time": get("EXIF ExposureTime"),
        "f_number": get("EXIF FNumber"),
        "iso": get("EXIF ISOSpeedRatings"),
        "focal_length": get("EXIF FocalLength"),
        "gps": extract_gps(tags),
        "total_tags": len(tags),
    }


def detect_anomalies(meta):
    """Rule-based red flags. Each one is a hint, not proof of tampering."""
    flags = []

    if meta["total_tags"] == 0:
        flags.append("No EXIF data at all (stripped by editor/messaging app, or a screenshot).")
        return flags

    software = (meta["software"] or "").lower()
    for name in EDITING_SOFTWARE:
        if name in software:
            flags.append(f"Editing software detected: {meta['software']}")
            break

    if not meta["make"] and not meta["model"]:
        flags.append("No camera make/model recorded.")

    orig, mod = meta["datetime_original"], meta["datetime_modified"]
    if orig and mod and orig != mod:
        flags.append(f"Modified time ({mod}) differs from capture time ({orig}).")

    if not orig:
        flags.append("No original capture timestamp.")

    return flags


def analyze(path):
    meta = extract_metadata(path)
    meta["anomalies"] = detect_anomalies(meta)
    return meta