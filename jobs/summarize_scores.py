"""Print per-sequence and mean scores, OP_CSB and OP_CTB, from ctc_evaluate CSV files.

Expects the CSV names written by seg_eval.sh and track_eval.sh:
    <seg_eval_dir>/<ds>_<seq>_SEG_DET.csv
    <track_dir>/<ds>_<seq>_tracking_metrics.csv

Usage:
    python summarize_scores.py <dataset> --seg_eval_dir DIR --track_dir DIR
"""

import argparse
import os
from pathlib import Path

import pandas as pd

SEQUENCES = ("01", "02")


def read_metrics(path):
    """Return the SEG/DET/TRA values from one ctc_evaluate CSV file, or None if it is missing."""
    if not path.exists():
        return None
    metrics_df = pd.read_csv(path, sep=None, engine="python")
    cols = {c.strip().upper(): c for c in metrics_df.columns}
    out = {
        m: float(metrics_df[cols[m]].iloc[0])
        for m in ("SEG", "DET", "TRA")
        if m in cols
    }
    if not out:
        print(
            f"  (no SEG/DET/TRA columns in {path}; columns are: {list(metrics_df.columns)})"
        )
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
    if len(per_seq) == len(SEQUENCES) and all(
        set(combo) <= set(r) for r in per_seq.values()
    ):
        ops = [0.5 * (r[combo[0]] + r[combo[1]]) for r in per_seq.values()]
        name = "OP_CSB" if combo == ("DET", "SEG") else "OP_CTB"
        means = {
            k: sum(r[k] for r in per_seq.values()) / len(SEQUENCES)
            for k in per_seq[SEQUENCES[0]]
        }
        print("  mean: " + "  ".join(f"{k}={v:.4f}" for k, v in means.items()))
        print(
            f"  {name}: 01={ops[0]:.4f}  02={ops[1]:.4f}  mean={sum(ops) / len(ops):.4f}"
        )


def main():
    """Parse arguments and print the segmentation and tracking summaries."""
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("ds", help="dataset, e.g. Fluo-N2DL-HeLa")
    p.add_argument("--seg_eval_dir", type=Path, default=os.environ.get("SEG_EVAL_DIR"))
    p.add_argument("--track_dir", type=Path, default=os.environ.get("TRACK_DIR"))
    a = p.parse_args()
    if a.seg_eval_dir is None or a.track_dir is None:
        p.error(
            "--seg_eval_dir and --track_dir are required (or set SEG_EVAL_DIR / TRACK_DIR)"
        )
    a.seg_eval_dir, a.track_dir = Path(a.seg_eval_dir), Path(a.track_dir)

    report(
        f"{a.ds} segmentation (OP_CSB = 0.5*(DET+SEG))",
        {s: a.seg_eval_dir / f"{a.ds}_{s}_SEG_DET.csv" for s in SEQUENCES},
        ("DET", "SEG"),
    )
    report(
        f"{a.ds} tracking (OP_CTB = 0.5*(SEG+TRA))",
        {s: a.track_dir / f"{a.ds}_{s}_tracking_metrics.csv" for s in SEQUENCES},
        ("SEG", "TRA"),
    )


if __name__ == "__main__":
    main()