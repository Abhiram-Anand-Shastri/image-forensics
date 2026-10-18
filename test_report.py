import sys
from modules import hashing, metadata, ela, copy_move, noise_analysis
from modules.report import build_report

path = sys.argv[1] if len(sys.argv) > 1 else "samples/tampered.jpg"

results = {
    "hashing": hashing.analyze(path),
    "metadata": metadata.analyze(path),
    "ela": ela.analyze(path),
    "copy_move": copy_move.analyze(path),
    "noise": noise_analysis.analyze(path),
}
print("Report saved to:", build_report(results))