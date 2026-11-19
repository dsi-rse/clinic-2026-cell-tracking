"""Measure how far cells move between consecutive frames of a tracked label movie.

For every label present in frames t and t+1 (same ID = same cell), it computes:
  displacement - distance between the cell's centres (pixels)
  diameter - equivalent diameter of the cell in frame t (pixels)
  iou - overlap of the cell's masks in t and t+1 (what Ultrack links on)

Use it on corrected labels, where IDs are right, so the numbers describe the cells
rather than tracking errors.

Example:
  python cell_motion_stats.py run/corrected_labels.tif --frames 0:10 --max_distance 35
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import tifffile
from scipy import ndimage

LOW_IOU = 0.2


def parse_args():
    """Parse command-line arguments."""
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("labels", type=Path, help="T x Y x X tracked labels TIFF")
    p.add_argument("--frames", default="all", help="'all' or 'a:b' (b exclusive)")
    p.add_argument("--max_distance", type=float, default=15.0, help="Ultrack setting")
    p.add_argument(
        "--out_csv", type=Path, help="per-cell table (default: next to labels)"
    )
    return p.parse_args()


def cell_props(frame):
    """Return {label: (centre_y, centre_x, area)} for one frame."""
    ids = np.unique(frame)
    ids = ids[ids > 0]
    centres = ndimage.center_of_mass(frame > 0, frame, ids)
    areas = ndimage.sum(frame > 0, frame, ids)
    return {int(i): (c[0], c[1], a) for i, c, a in zip(ids, centres, areas)}


def main():
    """Compute and summarize frame-to-frame motion."""
    a = parse_args()
    labels = tifffile.imread(str(a.labels))
    if a.frames != "all":
        start, stop = (int(s) if s else None for s in a.frames.split(":"))
        labels = labels[start:stop]

    rows = []
    props = [cell_props(f) for f in labels]
    for t in range(len(labels) - 1):
        for i in props[t].keys() & props[t + 1].keys():
            y0, x0, area = props[t][i]
            y1, x1, _ = props[t + 1][i]
            m0, m1 = labels[t] == i, labels[t + 1] == i
            inter = np.logical_and(m0, m1).sum()
            union = np.logical_or(m0, m1).sum()
            rows.append(
                {
                    "frame": t,
                    "label": i,
                    "displacement": float(np.hypot(y1 - y0, x1 - x0)),
                    "diameter": float(2 * np.sqrt(area / np.pi)),
                    "iou": float(inter / union),
                }
            )
    if not rows:
        raise SystemExit("no label appears in two consecutive frames")
    df = pd.DataFrame(rows)
    df["displacement_per_diameter"] = df["displacement"] / df["diameter"]
    out_csv = a.out_csv or a.labels.with_name(a.labels.stem + "_motion.csv")
    df.to_csv(out_csv, index=False, float_format="%.3f")

    n = len(df)
    print(f"{n} cell moves between consecutive frames ({df['label'].nunique()} cells)")
    print(f"median cell diameter:        {df['diameter'].median():.1f} px")
    print(
        f"displacement (px):           median {df['displacement'].median():.1f}, "
        f"90th percentile {df['displacement'].quantile(0.9):.1f}, "
        f"max {df['displacement'].max():.1f}"
    )
    print(
        "displacement / diameter:     median "
        f"{df['displacement_per_diameter'].median():.2f}"
    )
    print(
        f"IoU between frames:          median {df['iou'].median():.2f}; "
        f"IoU = 0: {np.mean(df['iou'] == 0):.0%}; IoU < {LOW_IOU}: "
        f"{np.mean(df['iou'] < LOW_IOU):.0%}"
    )
    print(
        f"moves > max_distance ({a.max_distance:g} px): "
        f"{np.mean(df['displacement'] > a.max_distance):.0%}"
    )
    print(f"per-cell table: {out_csv}")


if __name__ == "__main__":
    main()