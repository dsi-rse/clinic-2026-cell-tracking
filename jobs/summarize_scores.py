"""Print per-sequence and mean scores, OP_CSB and OP_CTB, from ctc_evaluate CSV files."""

import sys
from pathlib import Path

import pandas as pd

PROJ = Path("/net/scratch/evt-kit-ge/clinic-2026-cell-tracking")
SEQUENCES = ("01", "02")


def read_metrics(path):
    """Return the SEG/DET/TRA values from one ctc_evaluate CSV file, or None if it is missing."""
    if not path.exists():
        return None
    metrics_df = pd.read_csv(path)
    cols = {c.strip().upper(): c for c in metrics_df.columns}
    out = {m: float(metrics_df[cols[m]].iloc[0]) for m in ("SEG", "DET", "TRA") if m in cols}
    if not out:
        print(f"  (no SEG/DET/TRA columns in {path}; columns are: {list(metrics_df.columns)})")
    return out


def report(title, files, combo):
    """Print per-sequence scores, their means, and the combined OP score for one result type."""
    print(f"\n== {title} ==")
    per_seq = {}
    for seq, f in files.items():
        r = read_metrics(f)
        if r is None:
            print(f"  {seq}: missing {f}")
            continue
        per_seq[seq] = r
        print(f"  {seq}: " + "  ".join(f"{k}={v:.4f}" for k, v in r.items()))
    if len(per_seq) == len(SEQUENCES) and all(set(combo) <= set(r) for r in per_seq.values()):
        ops = [0.5 * (r[combo[0]] + r[combo[1]]) for r in per_seq.values()]
        name = "OP_CSB" if combo == ("DET", "SEG") else "OP_CTB"
        means = {k: sum(r[k] for r in per_seq.values()) / len(SEQUENCES) for k in per_seq[SEQUENCES[0]]}
        print("  mean: " + "  ".join(f"{k}={v:.4f}" for k, v in means.items()))
        print(f"  {name}: 01={ops[0]:.4f}  02={ops[1]:.4f}  mean={sum(ops) / len(ops):.4f}")


ds = sys.argv[1]
report(
    f"{ds} segmentation (OP_CSB = 0.5*(DET+SEG))",
    {s: PROJ / "seg_eval" / f"{ds}_{s}_SEG_DET.csv" for s in SEQUENCES},
    ("DET", "SEG"),
)
report(
    f"{ds} tracking (OP_CTB = 0.5*(SEG+TRA))",
    {s: PROJ / "tracking_results" / f"{ds}_{s}_tracking_metrics.csv" for s in SEQUENCES},
    ("SEG", "TRA"),
)