from pathlib import Path

import cv2
import numpy as np


def detect_copy_move(path, out_dir="outputs", ratio=0.6, min_dist=40, min_inliers=8):
    img = cv2.imread(str(path))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    sift = cv2.SIFT_create()
    kps, desc = sift.detectAndCompute(gray, None)
    result = {"keypoints": len(kps), "candidate_pairs": 0,
              "inliers": 0, "verdict": "Not enough features", "output": None}
    if desc is None or len(kps) < 10:
        return result

    # Match the image against itself. The best match is the keypoint itself,
    # so use the 2nd and 3rd neighbours for the ratio test.
    matcher = cv2.BFMatcher(cv2.NORM_L2)
    knn = matcher.knnMatch(desc, desc, k=3)

    pairs = {}
    for m in knn:
        if len(m) < 3:
            continue
        a, b = m[1], m[2]
        if a.distance < ratio * b.distance:
            p1 = kps[a.queryIdx].pt
            p2 = kps[a.trainIdx].pt
            if np.hypot(p1[0] - p2[0], p1[1] - p2[1]) > min_dist:
                key = tuple(sorted([(round(p1[0]), round(p1[1])),
                                    (round(p2[0]), round(p2[1]))]))
                pairs[key] = (p1, p2)

    result["candidate_pairs"] = len(pairs)
    if len(pairs) < 3:
        result["verdict"] = "No copy-move evidence"
        return result

    src = np.float32([p[0] for p in pairs.values()])
    dst = np.float32([p[1] for p in pairs.values()])
    _, inlier_mask = cv2.estimateAffine2D(src, dst, ransacReprojThreshold=3.0)
    if inlier_mask is None:
        result["verdict"] = "No copy-move evidence"
        return result

    inliers = inlier_mask.ravel().astype(bool)
    result["inliers"] = int(inliers.sum())

    if result["inliers"] >= min_inliers:
        result["verdict"] = "Possible copy-move forgery"
        vis = img.copy()
        for (p1, p2), ok in zip(pairs.values(), inliers):
            if ok:
                a = (int(p1[0]), int(p1[1]))
                b = (int(p2[0]), int(p2[1]))
                cv2.line(vis, a, b, (0, 255, 0), 1)
                cv2.circle(vis, a, 4, (0, 0, 255), -1)
                cv2.circle(vis, b, 4, (0, 0, 255), -1)
        out = Path(out_dir)
        out.mkdir(exist_ok=True)
        out_path = out / f"{Path(path).stem}_copymove.png"
        cv2.imwrite(str(out_path), vis)
        result["output"] = str(out_path)
    else:
        result["verdict"] = "No copy-move evidence"

    return result


def analyze(path):
    return detect_copy_move(path)