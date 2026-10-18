import hashlib
import shutil
from pathlib import Path

import imagehash
from PIL import Image


def compute_file_hashes(path, chunk_size=8192):
    """Cryptographic hashes of the raw file bytes (proves file integrity)."""
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            md5.update(chunk)
            sha256.update(chunk)
    return {"md5": md5.hexdigest(), "sha256": sha256.hexdigest()}


def compute_perceptual_hashes(path):
    """Hashes of the visual content (similar images give similar hashes)."""
    with Image.open(path) as img:
        return {
            "phash": str(imagehash.phash(img)),
            "ahash": str(imagehash.average_hash(img)),
            "dhash": str(imagehash.dhash(img)),
        }


def hamming_distance(hash_a, hash_b):
    """How different two perceptual hashes are (0 = identical)."""
    return imagehash.hex_to_hash(hash_a) - imagehash.hex_to_hash(hash_b)


def create_working_copy(path, out_dir="outputs"):
    """Copy the original and verify the copy is bit-for-bit identical.
    All later analysis should be done on the copy, never the original."""
    src = Path(path)
    out = Path(out_dir)
    out.mkdir(exist_ok=True)
    dst = out / f"working_copy_{src.name}"
    shutil.copy2(src, dst)

    verified = compute_file_hashes(src)["sha256"] == compute_file_hashes(dst)["sha256"]
    return str(dst), verified


def analyze(path):
    """Run the full hashing module and return one result dictionary."""
    p = Path(path)
    result = {
        "filename": p.name,
        "size_bytes": p.stat().st_size,
        **compute_file_hashes(p),
        **compute_perceptual_hashes(p),
    }
    copy_path, verified = create_working_copy(p)
    result["working_copy"] = copy_path
    result["copy_verified"] = verified
    return result