"""Check SEG for 3D datasets whose gold segmentation is given as 2D slices (man_seg_T_Z.tif).

Usage:
    python seg_3d_check.py <sequence GT folder, e.g. .../01_GT> <result folder with maskTTT.tif>
"""

import argparse
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import tifffile

MATCH_FRACTION = 0.5


def jaccard_scores(ref, res):
    """Return one Jaccard value per reference object (0 if no result object covers > half of it)."""
    scores = []
    for lab in np.unique(ref):
        if lab == 0:
            continue
        r = ref == lab
        n = int(r.sum())
        labels, counts = np.unique(res[r], return_counts=True)
        j = 0.0
        for c, k in zip(labels, counts):
            if c != 0 and k > MATCH_FRACTION * n:
                j = k / (n + int((res == c).sum()) - k)
        scores.append(j)
    return scores


def main():
    """Score slice-annotated GT in both ways and print a comparison."""
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("gt_dir", type=Path)
    p.add_argument("res_dir", type=Path)
    a = p.parse_args()

    slice_files = defaultdict(list)  # frame -> [(z, path)]
    volume_files = []
    for f in sorted((a.gt_dir / "SEG").glob("man_seg*.tif")):
        m = re.match(r"man_seg_?(\d+)(?:_(\d+))?\.tif$", f.name)
        if m.group(2) is None:
            volume_files.append(f)
        else:
            slice_files[m.group(1)].append((int(m.group(2)), f))

    if volume_files and not slice_files:
        print(
            f"{len(volume_files)} full-volume GT files (man_segT.tif): py-ctcmetrics scores these"
        )
        print(
            "normally, so a low SEG is not caused by the slice issue; check the cells' z-extent instead."
        )
    print(
        f"slice GT: {sum(len(v) for v in slice_files.values())} slice files in {len(slice_files)} frames"
    )

    official, stacked = [], []
    reused, reused_far = 0, 0
    for t, items in sorted(slice_files.items()):
        res = tifffile.imread(str(a.res_dir / f"mask{t}.tif"))
        refs = []
        for z, f in sorted(items):
            ref = tifffile.imread(str(f))
            if ref.shape != res.shape[1:]:
                print(
                    f"shape mismatch {f.name}: GT {ref.shape} vs result slice {res.shape[1:]}"
                )
                continue
            refs.append((z, ref))
            official.extend(jaccard_scores(ref, res[z]))
        if not refs:
            continue
        # py-ctcmetrics 1.3.3 behaviour: stack the annotated slices, one object per label,
        # and the frame is evaluated once per slice file (duplicate entries in its file list)
        ref_stack = np.stack([r for _, r in refs])
        res_stack = np.stack([res[z] for z, _ in refs])
        stacked.extend(jaccard_scores(ref_stack, res_stack) * len(refs))
        # label reuse: same label in several slices, and whether those regions are far apart
        where = defaultdict(list)
        for z, r in refs:
            for lab in np.unique(r):
                if lab != 0:
                    ys, xs = np.nonzero(r == lab)
                    where[lab].append((z, ys.mean(), xs.mean(), np.sqrt(len(ys))))
        for occ in where.values():
            if len(occ) > 1:
                reused += 1
                cy, cx = np.mean([o[1] for o in occ]), np.mean([o[2] for o in occ])
                size = np.mean([o[3] for o in occ])
                if max(np.hypot(o[1] - cy, o[2] - cx) for o in occ) > size:
                    reused_far += 1

    official, stacked = np.array(official), np.array(stacked)
    if official.size:
        print(
            f"\nofficial-style SEG = {official.mean():.4f}  ({official.size} 2D objects, "
            f"{np.mean(official == 0):.1%} with J=0, median J of matched "
            f"{np.median(official[official > 0]) if (official > 0).any() else 0:.3f})"
        )
    if stacked.size:
        print(f"stacked SEG       = {stacked.mean():.4f}  (py-ctcmetrics-style)")
    print(
        f"labels appearing in more than one slice of a frame: {reused}; "
        f"of those, at clearly different positions (different cells): {reused_far}"
    )


if __name__ == "__main__":
    main()
