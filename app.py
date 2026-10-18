from pathlib import Path

import streamlit as st

from modules import hashing, metadata, ela, copy_move, noise_analysis, compare
from modules.config import load_thresholds
from modules.report import build_report

st.set_page_config(page_title="Image Forensics Tool", layout="wide")
st.title("Digital Image Forensics Tool")
th = load_thresholds()

col_a, col_b = st.columns(2)
with col_a:
    suspect = st.file_uploader("Available image (required)", type=["jpg", "jpeg"], key="suspect")
with col_b:
    original = st.file_uploader("Original / similar image (optional)",
                                type=["jpg", "jpeg"], key="original")
st.warning("⚠️ Caution: For best performance, upload images of 1280×720 pixels or smaller. "
           "Larger images may cause the copy-move analysis to run very slowly.")

if suspect is None:
    st.info("Upload the available image to begin. Add an original on the right to also compare.")
    st.stop()


def save(upload, prefix):
    d = Path("uploads")
    d.mkdir(exist_ok=True)
    p = d / f"{prefix}_{Path(upload.name).name}"
    p.write_bytes(upload.getvalue())
    return p


susp_path = save(suspect, "suspect")
orig_path = save(original, "original") if original else None

key = (suspect.name, suspect.size, original.name if original else None,
       original.size if original else None)
if st.session_state.get("key") != key:
    with st.spinner("Running all modules..."):
        res = {
            "hashing": hashing.analyze(susp_path),
            "metadata": metadata.analyze(susp_path),
            "ela": ela.analyze(susp_path),
            "copy_move": copy_move.analyze(susp_path),
            "noise": noise_analysis.analyze(susp_path),
        }
        res["comparison"] = compare.compare(orig_path, susp_path) if orig_path else None
        res["report"] = build_report(
            {k: res[k] for k in ("hashing", "metadata", "ela", "copy_move", "noise")},
            out_path=f"outputs/{susp_path.stem}_report.pdf",
            comparison=res["comparison"],
        )
    st.session_state["key"] = key
    st.session_state["res"] = res

r = st.session_state["res"]
cmp_ = r["comparison"]

# ---------- Summary ----------
mode = "Blind analysis + comparison" if cmp_ else "Blind analysis (single image)"
st.subheader(f"Mode: {mode}")
st.caption("Thresholds: calibrated on a dataset." if th["calibrated"]
           else "Thresholds: default values (run the Step 9 evaluation to calibrate them).")

ela_flag = r["ela"]["max_block_error"] > th["ela_max_block"]
noise_flag = r["noise"]["noise_outlier_pct"] > th["noise_outlier_pct"]
cm_flag = r["copy_move"]["verdict"] == "Possible copy-move forgery"
meta_flag = len(r["metadata"]["anomalies"]) > 0

cols = st.columns(5 if cmp_ else 4)
cols[0].metric("Metadata", "Flags" if meta_flag else "Clean")
cols[1].metric("ELA", "Suspicious" if ela_flag else "Normal")
cols[2].metric("Copy-move", "Detected" if cm_flag else "None")
cols[3].metric("Noise", "Inconsistent" if noise_flag else "Consistent")
if cmp_:
    cols[4].metric("Changed pixels", f"{cmp_['pixel']['changed_pixels_pct']}%")

st.warning("These indicators are hints, not proof. Review the evidence in each tab.")

# ---------- Tabs ----------
names = ["Integrity", "Metadata", "ELA", "Copy-move", "Noise"]
if cmp_:
    names.append("Comparison")
names.append("Report")
tabs = dict(zip(names, st.tabs(names)))

with tabs["Integrity"]:
    h = r["hashing"]
    st.json({k: h[k] for k in ("filename", "size_bytes", "md5", "sha256",
                               "phash", "ahash", "dhash", "copy_verified")})
    st.image(str(susp_path), caption="Available image", width="stretch")

with tabs["Metadata"]:
    m = r["metadata"]
    if m["gps"]:
        st.error("This image contains GPS coordinates. Do not share it or its report publicly.")
    for a in m["anomalies"]:
        st.warning(a)
    st.json({k: v for k, v in m.items() if k != "anomalies"})

with tabs["ELA"]:
    e = r["ela"]
    st.json({k: e[k] for k in ("mean_error", "max_block_error", "suspicious_block_pct")})
    st.image(e["comparison"], width="stretch")
    st.caption("Look for rectangular regions that are brighter than their surroundings.")

with tabs["Copy-move"]:
    c = r["copy_move"]
    st.json({k: c[k] for k in ("keypoints", "candidate_pairs", "inliers", "verdict")})
    if c["output"]:
        st.image(c["output"], caption="Green lines link duplicated regions", width="stretch")
    else:
        st.success("No copy-move evidence found.")

with tabs["Noise"]:
    n = r["noise"]
    st.json({k: n[k] for k in ("median_noise", "noise_outlier_pct", "jpeg_quality_est")})
    st.image(n["noise_map"], width="stretch")

if cmp_:
    with tabs["Comparison"]:
        px = cmp_["pixel"]
        if cmp_["sha256_match"]:
            st.success("SHA-256 is identical: the two files are the same.")
        else:
            st.info("SHA-256 differs: the files are not identical.")
        a, b, c3 = st.columns(3)
        a.metric("pHash distance (of 64)", cmp_["phash_distance"])
        b.metric("JPEG quality (orig -> suspect)",
                 f"{cmp_['quality_original']} -> {cmp_['quality_suspect']}")
        c3.metric("Changed regions", px["changed_regions"])
        st.write(f"**pHash reading:** {cmp_['phash_interpretation']}")

        if cmp_["phash_distance"] > 20:
            st.warning("The images look unrelated, so the pixel difference below is unreliable.")
        if px["size_mismatch"]:
            st.info(f"Image sizes differ. Only the overlapping top-left area "
                    f"({px['compared_area']}) was compared.")

        st.image(px["regions_image"], caption="Red boxes: regions that differ from the original",
                 width="stretch")
        st.image(px["heatmap"], caption="Difference heatmap (red = larger change)",
                 width="stretch")
        st.subheader("Metadata differences")
        st.table(cmp_["metadata_diff"])

with tabs["Report"]:
    with open(r["report"], "rb") as f:
        st.download_button("Download PDF report", f.read(),
                           file_name=Path(r["report"]).name, mime="application/pdf")