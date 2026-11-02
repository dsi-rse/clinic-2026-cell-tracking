"""Overlay CTC-format tracking results on the raw frames.

Writes one PNG per frame (cell outlines coloured by track id, plus a short tail
showing where each cell has been), an animated GIF, and one image with the full
trajectory of every track.

Example:
    python visualize_tracks.py \
        --raw ~/cls_2d/CLS_tneon_MAX/01 \
        --res external/EmbedTrack/results/CLS_tneon_MAX/KIT-Loe-GE_model-Fluo-N2DH-GOWT1/train/01_RES \
        --out ~/viz/cls_01
"""

import argparse
import colorsys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import tifffile
from PIL import Image
from scipy import ndimage

MIN_TAIL_POINTS = 2


def track_color(track_id):
    """A bright colour that is the same for a given track id in every frame."""
    hue = (track_id * 0.61803398875) % 1.0
    return colorsys.hsv_to_rgb(hue, 0.85, 1.0)


def outlines(mask):
    """Boolean image that is True on the one-pixel border of every labelled cell."""
    edge = np.zeros(mask.shape, dtype=bool)
    for axis in (0, 1):
        for shift in (1, -1):
            edge |= mask != np.roll(mask, shift, axis)
    return edge & (mask > 0)


def centroids(mask):
    """Map track id -> (y, x) centre of mass for one label image."""
    ids = np.unique(mask)
    ids = ids[ids > 0]
    if len(ids) == 0:
        return {}
    centres = ndimage.center_of_mass(mask > 0, mask, ids)
    return {int(i): (float(y), float(x)) for i, (y, x) in zip(ids, centres)}


def scale_image(img):
    """Stretch the 1st to 99.5th intensity percentile to 0..1 for display."""
    lo, hi = np.percentile(img, (1, 99.5))
    return np.clip((img.astype(float) - lo) / max(hi - lo, 1e-9), 0, 1)


def new_axes(shape, dpi):
    """A figure with one axes that fills it, sized to the image."""
    height, width = shape
    fig = plt.figure(figsize=(width / 100, height / 100), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    return fig, ax


def main():
    """Draw one annotated PNG per frame, a GIF and a trajectories image."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--raw", required=True, type=Path, help="folder with raw frames t000.tif, ..."
    )
    parser.add_argument(
        "--res",
        required=True,
        type=Path,
        help="folder with mask000.tif, ... (e.g. 01_RES)",
    )
    parser.add_argument(
        "--out", required=True, type=Path, help="output folder (created)"
    )
    parser.add_argument(
        "--step", type=int, default=1, help="draw every Nth frame (default 1)"
    )
    parser.add_argument(
        "--tail",
        type=int,
        default=10,
        help="frames of history in each tail (default 10)",
    )
    parser.add_argument(
        "--dpi", type=int, default=70, help="lower = smaller files (default 70)"
    )
    args = parser.parse_args()

    mask_files = sorted(args.res.glob("mask*.tif"))
    if not mask_files:
        raise SystemExit(f"no mask*.tif files in {args.res}")
    frames_dir = args.out.expanduser() / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    # Pass 1: centroid of every track in every frame (for tails and trajectories).
    history = {}  # track id -> {frame number: (y, x)}
    frame_numbers = []
    for path in mask_files:
        n = int(path.stem.replace("mask", ""))
        frame_numbers.append(n)
        for track_id, centre in centroids(tifffile.imread(path)).items():
            history.setdefault(track_id, {})[n] = centre

    # Pass 2: one annotated PNG per frame.
    pngs = []
    for path, n in list(zip(mask_files, frame_numbers))[:: args.step]:
        raw = tifffile.imread(args.raw / f"t{n:03d}.tif")
        mask = tifffile.imread(path)
        fig, ax = new_axes(mask.shape, args.dpi)
        ax.imshow(scale_image(raw), cmap="gray", interpolation="nearest")

        lut = np.zeros((int(mask.max()) + 1, 4))
        for track_id in np.unique(mask[mask > 0]):
            lut[track_id, :3] = track_color(int(track_id))
        rgba = lut[mask]
        rgba[..., 3] = outlines(mask)
        ax.imshow(rgba, interpolation="nearest")

        for track_id in np.unique(mask[mask > 0]):
            points = [
                history[int(track_id)][t]
                for t in range(n - args.tail, n + 1)
                if t in history[int(track_id)]
            ]
            if len(points) >= MIN_TAIL_POINTS:
                ys, xs = zip(*points)
                ax.plot(xs, ys, color=track_color(int(track_id)), linewidth=1)

        ax.text(
            8,
            22,
            f"frame {n}   cells: {len(np.unique(mask[mask > 0]))}",
            color="white",
            fontsize=11,
        )
        png = frames_dir / f"frame_{n:03d}.png"
        fig.savefig(png, dpi=args.dpi)
        plt.close(fig)
        pngs.append(png)

    images = [Image.open(p).convert("P", palette=Image.ADAPTIVE) for p in pngs]
    gif = args.out.expanduser() / "tracks.gif"
    images[0].save(gif, save_all=True, append_images=images[1:], duration=150, loop=0)

    # One picture with every track's full path on the first frame.
    first = tifffile.imread(args.raw / f"t{frame_numbers[0]:03d}.tif")
    fig, ax = new_axes(first.shape, args.dpi)
    ax.imshow(scale_image(first), cmap="gray", interpolation="nearest")
    for track_id, by_frame in history.items():
        ys, xs = zip(*[by_frame[t] for t in sorted(by_frame)])
        ax.plot(xs, ys, color=track_color(track_id), linewidth=1)
        ax.plot(xs[-1], ys[-1], "o", color=track_color(track_id), markersize=2)
    ax.text(
        8,
        22,
        f"{len(history)} tracks over {len(frame_numbers)} frames",
        color="white",
        fontsize=11,
    )
    trajectories = args.out.expanduser() / "trajectories.png"
    fig.savefig(trajectories, dpi=args.dpi)
    plt.close(fig)

    print(f"{len(pngs)} frames -> {frames_dir}")
    print(f"gif -> {gif}")
    print(f"trajectories -> {trajectories}")


if __name__ == "__main__":
    main()
