"""Convert a multi-page 2D CLS movie (T, Y, X) into CTC-style frames t000.tif, ...

Example:
    python prepare_cls_frames.py --tif MAX_tneon.tif --out ~/cls_2d/CLS_tneon_MAX/01 \
        --frames 10 --crop 2048
"""

import argparse
from pathlib import Path

import tifffile


def main():
    """Write the first frames of a multi-page tif as separate CTC-style files."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--tif", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--frames", type=int, default=10)
    parser.add_argument(
        "--crop", type=int, default=0, help="centre crop size (0 = none)"
    )
    args = parser.parse_args()

    args.out.expanduser().mkdir(parents=True, exist_ok=True)
    with tifffile.TiffFile(args.tif) as tif:
        n = min(args.frames, len(tif.pages))
        for i in range(n):
            frame = tif.pages[i].asarray()
            if args.crop:
                y0 = (frame.shape[0] - args.crop) // 2
                x0 = (frame.shape[1] - args.crop) // 2
                frame = frame[y0 : y0 + args.crop, x0 : x0 + args.crop]
            tifffile.imwrite(args.out.expanduser() / f"t{i:03d}.tif", frame)
    print(f"wrote {n} frames to {args.out}")


if __name__ == "__main__":
    main()
