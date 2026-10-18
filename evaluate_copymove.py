import csv
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np

DATA = Path("dataset/copymove")
CACHE = Path("outputs/micc_inliers.csv")
RATIOS = [0.5, 0.6, 0.7, 0.8]
MIN_DIST = 40            # same as copy_move.py
SEED = 42
BASELINE = (0.6, 8)      # the values currently used by the app

cv2.setRNGSeed(0)        # makes RANSAC repeatable


def inliers_for_ratios(path):
    """Same matching logic as copy_move.py, but for several ratio values at once."""
    img = cv2.imread(str(path))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    kps, desc = cv2.SIFT_create().detectAndCompute(gray, None)
    out = {r: 0 for r in RATIOS}
    if desc is None or len(kps) < 10:
        return out
    knn = cv2.BFMatcher(cv2.NORM_L2).knnMatch(desc, desc, k=3)
    for r in RATIOS:
        pairs = {}
        for m in knn:
            if len(m) < 3:
                continue
            a, b = m[1], m[2]
            if a.distance < r * b.distance:
                p1, p2 = kps[a.queryIdx].pt, kps[a.trainIdx].pt
                if np.hypot(p1[0] - p2[0], p1[1] - p2[1]) > MIN_DIST:
                    key = tuple(sorted([(round(p1[0]), round(p1[1])),
                                        (round(p2[0]), round(p2[1]))]))
                    pairs[key] = (p1, p2)
        if len(pairs) < 3:
            continue
        src = np.float32([p[0] for p in pairs.values()])
        dst = np.float32([p[1] for p in pairs.values()])
        _, mask = cv2.estimateAffine2D(src, dst, ransacReprojThreshold=3.0)
        if mask is not None:
            out[r] = int(mask.ravel().astype(bool).sum())
    return out


def build_cache():
    with open(DATA / "labels.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    CACHE.parent.mkdir(exist_ok=True)
    with open(CACHE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["filename", "label", "source"] + [f"inl_{r}" for r in RATIOS])
        for i, row in enumerate(rows, 1):
            folder = "tampered" if row["label"] == "1" else "authentic"
            counts = inliers_for_ratios(DATA / folder / row["filename"])
            w.writerow([row["filename"], row["label"], row["source"]]
                       + [counts[r] for r in RATIOS])
            f.flush()
            print(f"\r{i}/{len(rows)} images processed", end="")
    print()


def split_sources(rows, test_frac=0.3):
    tamp_src = sorted({r["source"] for r in rows if r["label"] == "1"})
    other_src = sorted({r["source"] for r in rows} - set(tamp_src))
    rng = random.Random(SEED)
    test = set()
    for group in (tamp_src, other_src):
        g = group[:]
        rng.shuffle(g)
        test |= set(g[:max(1, round(len(g) * test_frac))])
    return test


def metrics(rows, ratio, k):
    tp = fp = fn = tn = 0
    for r in rows:
        pred = int(r[f"inl_{ratio}"]) >= k
        y = r["label"] == "1"
        tp += pred and y
        fp += pred and not y
        fn += (not pred) and y
        tn += (not pred) and not y
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3)}


def show(title, m):
    print(f"{title:34} P={m['precision']:.3f}  R={m['recall']:.3f}  F1={m['f1']:.3f}  "
          f"(TP={m['tp']} FP={m['fp']} FN={m['fn']} TN={m['tn']})")


if __name__ == "__main__":
    if "--recompute" in sys.argv or not CACHE.exists():
        print("Running SIFT matching on all images (this is the slow part)...")
        build_cache()

    with open(CACHE, newline="") as f:
        rows = list(csv.DictReader(f))

    test_sources = split_sources(rows)
    tune = [r for r in rows if r["source"] not in test_sources]
    test = [r for r in rows if r["source"] in test_sources]
    print(f"Tuning set: {len(tune)} images "
          f"({sum(r['label'] == '1' for r in tune)} tampered)")
    print(f"Test set  : {len(test)} images "
          f"({sum(r['label'] == '1' for r in test)} tampered)\n")

    best = None
    for ratio in RATIOS:
        for k in range(4, 31):
            m = metrics(tune, ratio, k)
            key = (m["f1"], m["precision"])
            if best is None or key > best[0]:
                best = (key, ratio, k, m)
    _, b_ratio, b_k, b_tune = best

    print(f"Best on tuning set: ratio={b_ratio}, min_inliers={b_k}")
    show("Tuning set (best)", b_tune)
    b_test = metrics(test, b_ratio, b_k)
    show("TEST set (best params)", b_test)
    print()
    show(f"TEST set (current {BASELINE})", metrics(test, *BASELINE))
    show(f"ALL images (current {BASELINE})", metrics(rows, *BASELINE))

    Path("outputs").mkdir(exist_ok=True)
    Path("outputs/micc_results.json").write_text(json.dumps(
        {"best_ratio": b_ratio, "best_min_inliers": b_k,
         "tuning": b_tune, "test": b_test}, indent=2))
    print("\nSaved outputs/micc_results.json")