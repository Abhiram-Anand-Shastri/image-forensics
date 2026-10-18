import csv
import re
import shutil
from pathlib import Path

SRC = Path(r"E:\MICC-F220")   # <-- change to your MICC folder
DST = Path("dataset/copymove")

label_file = next(SRC.glob("*.txt"))
print("Using label file:", label_file.name)

(DST / "authentic").mkdir(parents=True, exist_ok=True)
(DST / "tampered").mkdir(parents=True, exist_ok=True)

rows, missing = [], []
for line in label_file.read_text().splitlines():
    parts = line.split()
    if len(parts) != 2:
        continue
    name, label = parts[0], int(parts[1])
    src_file = SRC / name
    if not src_file.exists():
        missing.append(name)
        continue
    folder = "tampered" if label == 1 else "authentic"
    shutil.copy2(src_file, DST / folder / name)
    # source photo id: remove "_scale" or "tampNN" and the extension
    source = re.sub(r"(_scale|tamp\d+)\.jpg$", "", name, flags=re.IGNORECASE)
    rows.append((name, label, source))

with open(DST / "labels.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["filename", "label", "source"])
    w.writerows(rows)

print("Authentic:", sum(1 for r in rows if r[1] == 0))
print("Tampered :", sum(1 for r in rows if r[1] == 1))
print("Distinct sources:", len({r[2] for r in rows}))
print("Missing files:", missing if missing else "none")