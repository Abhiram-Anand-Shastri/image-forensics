import csv
import json
import random
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from modules.ela import run_ela, block_statistics
from modules.noise_analysis import noise_residual, block_noise_map

DATA = Path("dataset/splicing")
CACHE = Path("outputs/casia_features.csv")
SEED = 42
TEST_FRAC = 0.3
FIELDS = ["filename", "label", "type", "ela_mean", "ela_max", "noise_median", "noise_pct"]


def features(path):
    """Same ELA and noise calculations as the modules, without saving figures."""
    _, _, diff = run_ela(path)
    stats = block_statistics(diff)
    with Image.open(path) as im:
        gray = np.asarray(im.convert("L")).astype(np.float32)
    nmap = block_noise_map(noise_residual(gray))
    med = np.median(nmap)
    mad = np.median(np.abs(nmap - med)) or 1e-6
    z = 0.6745 * (nmap - med) / mad
    return {"ela_mean": stats["mean_error"], "ela_max": stats["max_block_error"],
            "noise_median": round(float(med), 3),
            "noise_pct": round(float((np.abs(z) > 3.5).mean() * 100), 2)}


def build_cache():
    files = [(p, 0) for p in sorted((DATA / "authentic").glob("*.jpg"))] + \
            [(p, 1) for p in sorted((DATA / "tampered").glob("*.jpg"))]
    CACHE.parent.mkdir(exist_ok=True)
    with open(CACHE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for i, (p, label) in enumerate(files, 1):
            try:
                feat = features(p)
            except Exception as e:
                print(f"\nSkipped {p.name}: {e}")
                continue
            ftype = p.name.split("_")[1] if label == 1 else "-"   # D or S for tampered
            w.writerow({"filename": p.name, "label": label, "type": ftype, **feat})
            f.flush()
            print(f"\r{i}/{len(files)} images processed", end="")
    print()


def source_ids(name, label):
    """Image IDs embedded in the CASIA file name, used to group related images."""
    if label == 0:
        m = re.match(r"Au_([a-z]+)_(\d+)", name)
        return [m.group(1) + m.group(2)] if m else [name]
    return re.findall(r"[a-z]{3}\d{5}", name) or [name]


def load_rows():
    with open(CACHE, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["label"] = int(r["label"])
        for k in ("ela_mean", "ela_max", "noise_median", "noise_pct"):
            r[k] = float(r[k])
        r["ids"] = source_ids(r["filename"], r["label"])

    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for r in rows:                       # images sharing any ID end up in one group
        root = find(r["ids"][0])
        for other in r["ids"][1:]:
            parent[find(other)] = root
    for r in rows:
        r["group"] = find(r["ids"][0])
    return rows


def split(rows):
    groups = {}
    for r in rows:
        groups.setdefault(r["group"], []).append(r)
    keys = sorted(groups)
    random.Random(SEED).shuffle(keys)
    test, n = [], 0
    for k in keys:
        if n >= TEST_FRAC * len(rows):
            break
        test += groups[k]
        n += len(groups[k])
    test_ids = {id(r) for r in test}
    tune = [r for r in rows if id(r) not in test_ids]
    print(f"{len(groups)} groups, largest has {max(len(g) for g in groups.values())} images")
    return tune, test


def prf(y, pred):
    tp = int(np.sum(pred & y)); fp = int(np.sum(pred & ~y))
    fn = int(np.sum(~pred & y)); tn = int(np.sum(~pred & ~y))
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "p": p, "r": r, "f1": f1}


def best_threshold(v, y):
    best = None
    for t in np.concatenate([[v.min() - 1], np.unique(v)]):
        m = prf(y, v > t)
        if best is None or m["f1"] >= best[1]["f1"]:   # ties: keep the higher threshold
            best = (float(t), m)
    return best


def show(title, m):
    print(f"{title:32} P={m['p']:.3f}  R={m['r']:.3f}  F1={m['f1']:.3f}  "
          f"(TP={m['tp']} FP={m['fp']} FN={m['fn']} TN={m['tn']})")


def arr(rows, key):
    return np.array([r[key] for r in rows], dtype=float)


def labels(rows):
    return np.array([r["label"] == 1 for r in rows])


if __name__ == "__main__":
    if "--recompute" in sys.argv or not CACHE.exists():
        print("Computing ELA and noise features for every image...")
        build_cache()

    rows = load_rows()
    tune, test = split(rows)
    ytu, yte, yall = labels(tune), labels(test), labels(rows)
    print(f"Tuning set: {len(tune)} images ({ytu.sum()} tampered)")
    print(f"Test set  : {len(test)} images ({yte.sum()} tampered)")

    thr, test_pred = {}, {}
    for name, key, default in (("ELA (max block error)", "ela_max", 3.0),
                               ("Noise (outlier %)", "noise_pct", 2.0)):
        t, m_tune = best_threshold(arr(tune, key), ytu)
        thr[key] = round(t, 3)
        test_pred[key] = arr(test, key) > thr[key]
        print(f"\n{name}: best threshold = {thr[key]}")
        show("  tuning set", m_tune)
        show("  TEST (tuned)", prf(yte, test_pred[key]))
        show(f"  TEST (default {default})", prf(yte, arr(test, key) > default))
        show("  ALL (tuned)", prf(yall, arr(rows, key) > thr[key]))

    either = test_pred["ela_max"] | test_pred["noise_pct"]
    either_def = (arr(test, "ela_max") > 3.0) | (arr(test, "noise_pct") > 2.0)
    print("\nEither module flags the image:")
    show("  TEST (tuned)", prf(yte, either))
    show("  TEST (default 3.0 / 2.0)", prf(yte, either_def))

    print("\nRecall by forgery type (test set, tuned thresholds):")
    types = np.array([r["type"] for r in test])
    for T in ("D", "S"):
        sel = yte & (types == T)
        if sel.any():
            print(f"  {T}-type forgeries n={int(sel.sum()):3}  "
                  f"ELA={test_pred['ela_max'][sel].mean():.3f}  "
                  f"Noise={test_pred['noise_pct'][sel].mean():.3f}  "
                  f"Either={either[sel].mean():.3f}")

    if "--write" in sys.argv:
        Path("thresholds.json").write_text(json.dumps(
            {"ela_max_block": thr["ela_max"], "noise_outlier_pct": thr["noise_pct"],
             "calibrated": True}, indent=2))
        print("\nSaved thresholds.json")
    else:
        print("\n(thresholds.json not written. Rerun with --write to save it.)")