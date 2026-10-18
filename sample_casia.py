import random
import shutil
from pathlib import Path

SRC = Path(r"E:\CASIA2")      # <-- change to your extracted folder
DST = Path("dataset/splicing")
N = 400                                 # images per class
SEED = 42

for folder in ("authentic", "tampered"):
    (DST / folder).mkdir(parents=True, exist_ok=True)

def jpgs(prefix):
    return sorted(p for p in SRC.rglob("*")
                  if p.suffix.lower() in (".jpg", ".jpeg")
                  and p.name.startswith(prefix))

au, tp = jpgs("Au_"), jpgs("Tp_")
print(f"Found {len(au)} authentic and {len(tp)} tampered JPEGs")

n = min(N, len(au), len(tp))
rng = random.Random(SEED)
for files, folder in ((rng.sample(au, n), "authentic"),
                      (rng.sample(tp, n), "tampered")):
    for p in files:
        shutil.copy2(p, DST / folder / p.name)

print(f"Copied {n} per class into {DST}")