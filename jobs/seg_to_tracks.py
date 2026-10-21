"""Make a DET-scorable copy of segmentation masks for py-ctcmetrics.

Works for 2D and 3D masks.
"""

import sys
from pathlib import Path

import numpy as np
import tifffile

MAX_UINT16_LABEL = 65535

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
dst.mkdir(parents=True, exist_ok=True)
next_id, lines = 1, []
files = sorted(src.glob("mask*.tif"))
if not files:
    sys.exit(f"No mask*.tif files in {src}")
for f in files:
    t = int(f.stem[4:])
    m = tifffile.imread(str(f))
    labels = np.unique(m)
    labels = labels[labels != 0]
    lut = np.zeros(int(m.max()) + 1, dtype=np.uint32)
    lut[labels] = np.arange(next_id, next_id + len(labels))
    lines.extend(f"{new} {t} {t} 0" for new in range(next_id, next_id + len(labels)))
    next_id += len(labels)
    if next_id > MAX_UINT16_LABEL:
        sys.exit("Too many objects for uint16 masks")
    tifffile.imwrite(str(dst / f.name), lut[m].astype(np.uint16))
(dst / "res_track.txt").write_text("\n".join(lines) + "\n")
print(f"{src.name}: wrote {len(lines)} objects to {dst}")
