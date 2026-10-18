import json
from pathlib import Path

DEFAULTS = {"ela_max_block": 3.0, "noise_outlier_pct": 2.0, "calibrated": False}


def load_thresholds(path="thresholds.json"):
    """Read thresholds written by the Step 9 evaluation; fall back to defaults."""
    p = Path(path)
    if p.exists():
        try:
            return {**DEFAULTS, **json.loads(p.read_text())}
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULTS)