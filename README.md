# Image Forensics

A digital image forensics tool built with Python and Streamlit that detects signs of tampering in JPEG images using multiple analysis techniques.

## Features

- **Error Level Analysis (ELA)** — detects regions re-saved at different compression levels
- **Copy-Move Detection** — finds duplicated regions within an image using SIFT + RANSAC
- **Noise Analysis** — identifies blocks with anomalous noise patterns
- **Metadata Inspection** — extracts and flags suspicious EXIF data
- **Hash Verification** — MD5, SHA-256, and perceptual hashes
- **Image Comparison** — pixel-level diff and metadata diff between two images
- **PDF Report** — downloadable forensics report for any analysis

## Project Structure
image_forensics/
├── app.py # Streamlit app
├── modules/
│ ├── ela.py
│ ├── copy_move.py
│ ├── noise_analysis.py
│ ├── metadata.py
│ ├── hashing.py
│ ├── compare.py
│ ├── report.py
│ └── config.py
├── samples/ # Demo images
├── evaluate_copymove.py # MICC-F220 evaluation script
├── evaluate_splicing.py # CASIA 2.0 evaluation script
├── thresholds.json # Tuned detection thresholds
├── requirements.txt
└── .gitignore


## Installation

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
streamlit run app.py
```

Upload a suspected tampered image. Optionally upload an original for comparison. Download the PDF report from the Report tab.

## Evaluation Results

### Copy-Move Detection (MICC-F220, 110 authentic / 110 tampered)

| Setting | Precision | Recall | F1 |
|---|---|---|---|
| Tuned (min_inliers=5) | 0.909 | 1.000 | 0.952 |
| Final (min_inliers=8) | 1.000 | 0.867 | 0.929 |

Final setting uses min_inliers=8 to reduce false accusations.

### Splicing Detection (CASIA 2.0, 400 authentic / 400 tampered)

| Module | Precision | Recall | F1 |
|---|---|---|---|
| ELA (tuned, threshold=3.305) | 0.711 | 0.789 | 0.748 |
| ELA (default, threshold=3.0) | 0.639 | 0.862 | 0.734 |
| Noise (default, threshold=2.0) | 0.424 | 0.229 | 0.298 |
| Combined (default thresholds) | 0.576 | 0.899 | 0.703 |

## Known Limitations

- Copy-move detection is slow on images larger than ~1280px due to quadratic SIFT matching
- ELA produces false positives on images that have been resized or recompressed without tampering
- Noise module missed splice regions sourced from visually similar images
- Metadata analysis missed Paint-edited images because Paint preserves EXIF
- CASIA evaluation is approximate due to JPEG quality bias between authentic and tampered sets
- Small test sets mean results are indicative, not definitive

## Ethics

- Always work on copies, never originals
- Hash the file before analysis to prove it was not modified during investigation
- Handle GPS metadata with care — it reveals the photographer's location
- This tool is for educational and research purposes only

## Future Scope

- Deep-learning localisation with segmentation masks
- Ground-truth mask evaluation (IoU scoring)
- Cross-image source matching
- FLANN-based speed-up for copy-move
- AI-generated image detection