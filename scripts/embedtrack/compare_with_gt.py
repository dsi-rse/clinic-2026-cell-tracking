"""Overlay EmbedTrack predictions and ground-truth outlines on the raw frames.

Predictions are drawn in magenta and ground truth in green. Ground truth is only
drawn on frames that have a ground-truth file (the SEG folder is sparse, the TRA
folder usually covers every frame). Writes an animated GIF and one PNG per frame
that has ground truth.

Example (from the repository root):
    PYTHONPATH=src python scripts/embedtrack/compare_with_gt.py \
        --raw /net/spaces/clinic/CLS/DSC_CTC/ctc/Fluo-N2DL-HeLa/02 \
        --res external/EmbedTrack/results/Fluo-N2DL-HeLa/KIT-Loe-GE/train/02_RES \
        --gt /net/spaces/clinic/CLS/DSC_CTC/ctc/Fluo-N2DL-HeLa/02_GT/SEG \
        --out ~/viz/hela_02_vs_gt --only-gt-frames
"""

import argparse
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw

from cell_tracking.ctc_io import extract_frame_number
from cell_tracking.ctc_visualization import normalize_raw_image
from cell_tracking.ultrack_2d import find_label_boundaries

PRED_COLOR = (255, 0, 255)
GT_COLOR = (0, 255, 0)


def main():
    """Draw prediction and ground-truth outlines on every selected frame."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--raw", required=True, type=Path, help="raw frames t000.tif, ..."
    )
    parser.add_argument(
        "--res",
        required=True,
        type=Path,
        help="EmbedTrack output folder (mask000.tif, ...)",
    )
    parser.add_argument(
        "--gt",
        required=True,
        type=Path,
        help="ground-truth folder, e.g. 02_GT/SEG or 02_GT/TRA",
    )
    parser.add_argument(
        "--out", required=True, type=Path, help="output folder (created)"
    )
    parser.add_argument(
        "--only-gt-frames",
        action="store_true",
        help="only keep frames that have ground truth",
    )
    parser.add_argument(
        "--duration", type=int, default=400, help="ms per GIF frame (default 400)"
    )
    args = parser.parse_args()

    pred_files = {extract_frame_number(p): p for p in args.res.glob("mask*.tif")}
    gt_files = {extract_frame_number(p): p for p in args.gt.glob("*.tif")}
    if args.only_gt_frames:
        numbers = sorted(n for n in pred_files if n in gt_files)
    else:
        numbers = sorted(pred_files)
    if not numbers:
        raise SystemExit("no frames to draw: check --res and --gt")

    out = args.out.expanduser()
    out.mkdir(parents=True, exist_ok=True)
    frames = []
    for n in numbers:
        gray = normalize_raw_image(tifffile.imread(args.raw / f"t{n:03d}.tif"))
        rgb = np.stack([gray] * 3, axis=-1)
        rgb[find_label_boundaries(tifffile.imread(pred_files[n]))] = PRED_COLOR
        label = "magenta = EmbedTrack"
        if n in gt_files:
            rgb[find_label_boundaries(tifffile.imread(gt_files[n]))] = GT_COLOR
            label += ", green = ground truth"
        img = Image.fromarray(rgb)
        ImageDraw.Draw(img).text((8, 8), f"frame {n}   {label}", fill=(255, 255, 255))
        if n in gt_files:
            img.save(out / f"frame_{n:03d}.png")
        frames.append(img.convert("P", palette=Image.ADAPTIVE))

    gif = out / "compare_with_gt.gif"
    frames[0].save(
        gif, save_all=True, append_images=frames[1:], duration=args.duration, loop=0
    )
    print(f"{len(frames)} frames -> {gif}")


if __name__ == "__main__":
    main()
