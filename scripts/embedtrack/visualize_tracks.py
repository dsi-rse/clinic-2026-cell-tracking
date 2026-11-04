"""Overlay CTC-format tracking results on the raw frames.

Writes one PNG per frame (cell outlines coloured by track id, plus a short tail
showing where each cell has been), an animated GIF, and one image with the full
trajectory of every track.

Example (from the repository root):
    PYTHONPATH=src python scripts/embedtrack/visualize_tracks.py \
        --raw /net/spaces/clinic/CLS/DSC_CTC/ctc/Fluo-N2DL-HeLa/02 \
        --res external/EmbedTrack/results/Fluo-N2DL-HeLa/KIT-Loe-GE/train/02_RES \
        --out ~/viz/hela_02
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import tifffile
from PIL import Image

from cell_tracking.ctc_io import extract_frame_number
from cell_tracking.ctc_visualization import normalize_raw_image
from cell_tracking.track_utils import RGB_MAXIMUM, label_centroids, track_color
from cell_tracking.ultrack_2d import find_label_boundaries

MIN_TAIL_POINTS = 2


def plot_color(track_id):
    """Return the track colour as matplotlib RGB floats (0..1)."""
    return tuple(channel / RGB_MAXIMUM for channel in track_color(track_id))


def new_axes(shape, dpi):
    """Return a figure with one axes that fills it, sized to the image."""
    height, width = shape
    fig = plt.figure(figsize=(width / 100, height / 100), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    return fig, ax


def show_raw(ax, raw):
    """Draw a raw frame in greyscale on the axes."""
    ax.imshow(
        normalize_raw_image(raw), cmap="gray", vmin=0, vmax=255, interpolation="nearest"
    )


def main():
    """Draw one annotated PNG per frame, a GIF and a trajectories image."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--raw", required=True, type=Path, help="folder with raw frames t000.tif, ..."
    )
    parser.add_argument(
        "--res", required=True, type=Path, help="folder with mask000.tif, ... (01_RES)"
    )
    parser.add_argument(
        "--out", required=True, type=Path, help="output folder (created)"
    )
    parser.add_argument("--step", type=int, default=1, help="draw every Nth frame")
    parser.add_argument(
        "--tail", type=int, default=10, help="frames of history in each tail"
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
    history = {}  # track id -> {frame number: (x, y)}
    frame_numbers = []
    for path in mask_files:
        n = extract_frame_number(path)
        frame_numbers.append(n)
        for track_id, centre in label_centroids(tifffile.imread(path)).items():
            history.setdefault(track_id, {})[n] = centre

    # Pass 2: one annotated PNG per frame.
    pngs = []
    for path, n in list(zip(mask_files, frame_numbers, strict=True))[:: args.step]:
        raw = tifffile.imread(args.raw / f"t{n:03d}.tif")
        mask = tifffile.imread(path)
        fig, ax = new_axes(mask.shape, args.dpi)
        show_raw(ax, raw)

        lut = np.zeros((int(mask.max()) + 1, 4))
        for track_id in np.unique(mask[mask > 0]):
            lut[track_id, :3] = plot_color(int(track_id))
        rgba = lut[mask]
        rgba[..., 3] = find_label_boundaries(mask)
        ax.imshow(rgba, interpolation="nearest")

        for track_id in np.unique(mask[mask > 0]):
            by_frame = history[int(track_id)]
            points = [by_frame[t] for t in range(n - args.tail, n + 1) if t in by_frame]
            if len(points) >= MIN_TAIL_POINTS:
                xs, ys = zip(*points, strict=True)
                ax.plot(xs, ys, color=plot_color(int(track_id)), linewidth=1)

        count = len(np.unique(mask[mask > 0]))
        ax.text(8, 22, f"frame {n}   cells: {count}", color="white", fontsize=11)
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
    show_raw(ax, first)
    for track_id, by_frame in history.items():
        xs, ys = zip(*[by_frame[t] for t in sorted(by_frame)], strict=True)
        ax.plot(xs, ys, color=plot_color(track_id), linewidth=1)
        ax.plot(xs[-1], ys[-1], "o", color=plot_color(track_id), markersize=2)
    label = f"{len(history)} tracks over {len(frame_numbers)} frames"
    ax.text(8, 22, label, color="white", fontsize=11)
    trajectories = args.out.expanduser() / "trajectories.png"
    fig.savefig(trajectories, dpi=args.dpi)
    plt.close(fig)

    print(f"{len(pngs)} frames -> {frames_dir}")
    print(f"gif -> {gif}")
    print(f"trajectories -> {trajectories}")


if __name__ == "__main__":
    main()
