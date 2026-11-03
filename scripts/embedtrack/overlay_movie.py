"""Overlay EmbedTrack masks and trajectories on the raw movie.

Every frame of the raw movie is drawn as the background. Each segmented cell is
filled with a translucent colour that belongs to its track id, and the path each
track has taken so far is drawn as a line in the same colour. Writes an animated
GIF and a few PNG frames.

Example (from the repository root):
    PYTHONPATH=src python scripts/embedtrack/overlay_movie.py \
        --raw /net/spaces/clinic/CLS/DSC_CTC/ctc/Fluo-N2DL-HeLa/02 \
        --res external/EmbedTrack/results/Fluo-N2DL-HeLa/KIT-Loe-GE/train/02_RES \
        --out ~/viz/hela_02_movie
"""

import argparse
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw

from cell_tracking.ctc_io import extract_frame_number
from cell_tracking.ctc_visualization import normalize_raw_image
from cell_tracking.track_utils import RGB_MAXIMUM, label_centroids, track_color
from cell_tracking.ultrack_2d import find_label_boundaries

MIN_POINTS = 2
PNG_EVERY = 10


def render(raw, mask, lut, alpha, outline):
    """Return the greyscale raw frame with the cells of `mask` in translucent colour."""
    grey = normalize_raw_image(raw).astype(float) / RGB_MAXIMUM
    rgb = np.stack([grey] * 3, axis=-1)
    cells = mask > 0
    colours = lut[mask[cells]] / RGB_MAXIMUM
    rgb[cells] = (1 - alpha) * rgb[cells] + alpha * colours
    if outline:
        edge = find_label_boundaries(mask)
        rgb[edge] = lut[mask[edge]] / RGB_MAXIMUM
    return Image.fromarray((rgb * RGB_MAXIMUM).astype(np.uint8))


def draw_trajectories(img, history, frame, tail):
    """Draw every track's path up to `frame` (last `tail` frames; 0 = whole history)."""
    draw = ImageDraw.Draw(img)
    first = frame - tail if tail else -1
    for track_id, by_frame in history.items():
        points = [by_frame[t] for t in sorted(by_frame) if first <= t <= frame]
        if len(points) >= MIN_POINTS:
            draw.line(points, fill=track_color(track_id), width=2)
        if frame in by_frame:
            x, y = by_frame[frame]
            draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(255, 255, 255))


def main():
    """Render the movie with masks and trajectories, then save a GIF and a few PNGs."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--raw", required=True, type=Path, help="raw frames t000.tif, ..."
    )
    parser.add_argument(
        "--res", required=True, type=Path, help="EmbedTrack output (mask000.tif, ...)"
    )
    parser.add_argument(
        "--out", required=True, type=Path, help="output folder (created)"
    )
    parser.add_argument(
        "--alpha", type=float, default=0.4, help="mask opacity 0..1 (default 0.4)"
    )
    parser.add_argument(
        "--tail",
        type=int,
        default=0,
        help="frames of trajectory history, 0 = all (default 0)",
    )
    parser.add_argument(
        "--step", type=int, default=1, help="draw every Nth frame (default 1)"
    )
    parser.add_argument(
        "--width", type=int, default=900, help="output width in pixels (default 900)"
    )
    parser.add_argument(
        "--duration", type=int, default=120, help="ms per GIF frame (default 120)"
    )
    parser.add_argument(
        "--digits", type=int, default=3, help="digits in raw frame names (default 3)"
    )
    parser.add_argument(
        "--outline", action="store_true", help="also draw a solid outline on each cell"
    )
    args = parser.parse_args()

    mask_files = sorted(args.res.glob("mask*.tif"))
    if not mask_files:
        raise SystemExit(f"no mask*.tif files in {args.res}")
    out = args.out.expanduser()
    (out / "frames").mkdir(parents=True, exist_ok=True)

    # Pass 1: where every track is in every frame (for the trajectories).
    history = {}
    masks = {}
    for path in mask_files:
        n = extract_frame_number(path)
        masks[n] = tifffile.imread(path)
        for track_id, centre in label_centroids(masks[n]).items():
            history.setdefault(track_id, {})[n] = centre
    n_ids = max(int(m.max()) for m in masks.values()) + 1
    lut = np.array([track_color(i) for i in range(n_ids)], dtype=float)

    # Pass 2: draw the frames.
    frames = []
    for n in sorted(masks)[:: args.step]:
        raw = tifffile.imread(args.raw / f"t{n:0{args.digits}d}.tif")
        img = render(raw, masks[n], lut, args.alpha, args.outline)
        draw_trajectories(img, history, n, args.tail)
        count = len(np.unique(masks[n][masks[n] > 0]))
        label = f"frame {n}   cells: {count}"
        ImageDraw.Draw(img).text((8, 8), label, fill=(255, 255, 255))
        if img.width > args.width:
            height = round(img.height * args.width / img.width)
            img = img.resize((args.width, height), Image.LANCZOS)
        if n % PNG_EVERY == 0:
            img.save(out / "frames" / f"frame_{n:03d}.png")
        frames.append(img.convert("P", palette=Image.ADAPTIVE))

    gif = out / "movie_overlay.gif"
    frames[0].save(
        gif, save_all=True, append_images=frames[1:], duration=args.duration, loop=0
    )
    print(f"{len(frames)} frames -> {gif}")


if __name__ == "__main__":
    main()
