"""Visualize KIT-GE (3) segmentation and tracking results.

Step 1 - color: color-code the cell masks with the Tab10 palette. Each cell keeps one
color in every frame. When a cell first appears it gets a random Tab10 color that its
current neighbours are not using (seeded, so reruns give the same colors), and the
choice is saved in colors.json for later steps.

Tracking masks already use one label per cell over time (the track ID). Segmentation
masks are numbered from scratch in every frame, so pass --match_tracks with the tracking
results: each segmented object then takes the color of the track it overlaps most, and
objects the tracker dropped get a fresh color (they have no identity across frames).

Step 2 - overlay: draw the same colors semi-transparently over the raw images, with
a solid outline around each cell, so you can see what the model found in the data.

Step 3 - movie: a tracking movie. Each frame shows the overlay plus a trajectory line
behind every cell (its centroid over the last --tail frames; --tail 0 for the whole
track), in the cell's color. Each cell has a dot at its current position, and cells
that just divided get a white ring and a line back to their mother cell
(--no_markers turns both off; --no_outline removes the cell outlines).
Needs tracking results (a 0X_RES folder with res_track.txt). Writes the frames as PNGs,
movie.gif, and movie.mp4 when ffmpeg is available.

Colors are assigned frame by frame from the first frame, so a cell has the same color
in every step and with any --frames selection.

Examples:
    python ctc_viz.py color <tracking>/01_RES <out>/tracking_colors
    python ctc_viz.py color <segmentation>/01_RES_<tag> <out>/segmentation_colors \
        --match_tracks <tracking>/01_RES
    python ctc_viz.py overlay <tracking>/01_RES <out>/tracking_overlay --raw_dir <data>/01
    python ctc_viz.py movie <tracking>/01_RES <out>/tracking_movie --raw_dir <data>/01
"""

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

# matplotlib's Tab10 palette
TAB10 = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]  # fmt: skip
TAB10_RGB = np.array([[int(h[i : i + 2], 16) for i in (1, 3, 5)] for h in TAB10])
NEIGHBOUR_MARGIN = 15  # pixels around a cell searched for neighbours with other colors
VOLUME_NDIM = 3
LOW_PCT, HIGH_PCT = 1, 99.8  # raw intensity percentiles mapped to black and white
DIVISION_RING_FRAMES = 3  # frames a new daughter cell is marked with a white ring
FONT_SIZE = 18


def frame_files(folder, prefix):
    """Return {frame number: path} for prefixTTT.tif files in a folder."""
    files = {}
    for f in Path(folder).glob(f"{prefix}*.tif"):
        m = re.fullmatch(rf"{prefix}(\d+)\.tif", f.name)
        if m:
            files[int(m.group(1))] = f
    return dict(sorted(files.items()))


def parse_frames(spec, available):
    """Select frames from 'all', 'a:b' (b exclusive) or 'a,b,c'."""
    if spec == "all":
        return sorted(available)
    if ":" in spec:
        start, stop = (int(s) if s else None for s in spec.split(":"))
        return [
            t
            for t in sorted(available)
            if t >= (start or 0) and (stop is None or t < stop)
        ]
    return [int(s) for s in spec.split(",") if int(s) in available]


def to_2d(volume, z):
    """Reduce a 3D stack to 2D: a slice index, 'mid', or 'max' (maximum projection)."""
    if volume.ndim < VOLUME_NDIM:
        return volume
    if z == "max":
        return volume.max(axis=0)
    return volume[volume.shape[0] // 2 if z == "mid" else int(z)]


def match_to_tracks(seg, trk, next_free):
    """Relabel a segmentation mask with the track ID each object overlaps most.

    Objects that overlap no track get new labels starting at next_free[0].
    """
    out = np.zeros_like(seg, dtype=np.int64)
    both = (seg > 0) & (trk > 0)
    pairs, counts = np.unique(
        np.stack([seg[both], trk[both]]), axis=1, return_counts=True
    )
    best = {}
    for (s, k), n in zip(pairs.T, counts):
        if n > best.get(s, (0, 0))[1]:
            best[s] = (k, n)
    for s in np.unique(seg):
        if s == 0:
            continue
        if s in best:
            label = best[s][0]
        else:
            label, next_free[0] = next_free[0], next_free[0] + 1
        out[seg == s] = label
    return out


class ColorAssigner:
    """Give each label a Tab10 color once, avoiding the colors of touching cells."""

    def __init__(self, seed):
        """Start with no colors assigned."""
        self.rng = np.random.default_rng(seed)
        self.extra_rng = np.random.default_rng(seed + 1)  # for objects without a track
        self.colors = {}

    def update(self, mask, extra=False):
        """Assign colors to labels seen for the first time in this frame.

        Tracks draw from the main random generator, so a track gets the same color in
        the tracking and the matched segmentation output. Objects without a track
        (extra=True) draw from a separate generator, so they cannot shift those colors.
        """
        rng = self.extra_rng if extra else self.rng
        boxes = ndimage.find_objects(mask)
        for i, box in enumerate(boxes):
            label = i + 1
            if box is None or label in self.colors:
                continue
            window = tuple(
                slice(max(s.start - NEIGHBOUR_MARGIN, 0), s.stop + NEIGHBOUR_MARGIN)
                for s in box
            )
            near = {self.colors.get(int(n)) for n in np.unique(mask[window])}
            free = [c for c in range(len(TAB10)) if c not in near]
            self.colors[label] = int(rng.choice(free or range(len(TAB10))))

    def paint(self, mask):
        """Return an RGB uint8 image (black background) for a 2D or 3D mask."""
        lut = np.zeros((int(mask.max()) + 1, 3), dtype=np.uint8)
        for label, c in self.colors.items():
            if label < len(lut):
                lut[label] = TAB10_RGB[c]
        return lut[mask]


def labelled_frames(a):
    """Yield (frame, mask, assigner) for the selected frames, with colors assigned.

    Every frame from the first one up to the last selected one is read in order, so
    colors do not depend on which frames are selected. With --match_tracks the mask is
    relabelled with track IDs (see match_to_tracks).
    """
    masks = frame_files(a.mask_dir, "mask")
    tracks = frame_files(a.match_tracks, "mask") if a.match_tracks else {}
    selected = set(parse_frames(a.frames, masks.keys()))
    if not selected:
        raise SystemExit(f"no maskTTT.tif files in {a.mask_dir}")
    if not (a.mask_dir / "res_track.txt").exists() and not a.match_tracks:
        print(
            "Note: segmentation masks without --match_tracks: labels are per frame, "
            "so colors are NOT consistent across frames."
        )

    assigner = ColorAssigner(a.seed)
    next_free = [10**6]  # labels for objects the tracker dropped (above every track ID)
    track_file = (a.match_tracks or Path()) / "res_track.txt"
    if track_file.is_file():
        ids = [
            int(r.split()[0]) for r in track_file.read_text().split("\n") if r.strip()
        ]
        next_free = [max(ids, default=0) + 1]
    for t in [t for t in masks if t <= max(selected)]:
        mask = tifffile.imread(str(masks[t])).astype(np.int64)
        if a.match_tracks:
            trk = tifffile.imread(str(tracks[t])).astype(np.int64)
            mask = match_to_tracks(mask, trk, next_free)
            assigner.update(trk)  # same colors as the tracking output
            assigner.update(mask, extra=True)  # objects the tracker dropped
        else:
            assigner.update(mask)
        if t in selected:
            yield t, mask, assigner


def save_colors(assigner, out_dir):
    """Write colors.json: {label: Tab10 hex color}."""
    colors = {str(k): TAB10[c] for k, c in sorted(assigner.colors.items())}
    (out_dir / "colors.json").write_text(json.dumps(colors, indent=1))
    return len(colors)


def color(a):
    """Write color-coded PNGs (and optionally RGB TIFFs) for every selected frame."""
    a.out_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for t, mask, assigner in labelled_frames(a):
        rgb = assigner.paint(mask)
        if a.tiff:
            tifffile.imwrite(
                str(a.out_dir / f"color{t:03d}.tif"), rgb, photometric="rgb"
            )
        view = rgb if mask.ndim < VOLUME_NDIM else to_2d_rgb(rgb, mask, a.z)
        Image.fromarray(view).save(a.out_dir / f"color{t:03d}.png")
        n += 1
    cells = save_colors(assigner, a.out_dir)
    print(f"wrote {n} frames and colors.json ({cells} cells) to {a.out_dir}")


def mask_view(mask, z):
    """2D view of a label mask: a slice, or for 'max' the topmost cell at each pixel."""
    if mask.ndim < VOLUME_NDIM or z != "max":
        return to_2d(mask, z)
    top = np.argmax(mask > 0, axis=0)
    return np.take_along_axis(mask, top[None], axis=0)[0]


def outlines(mask):
    """Return a boolean image that is True on the border pixels of each object."""
    edge = np.zeros(mask.shape, dtype=bool)
    edge[1:, :] |= mask[1:, :] != mask[:-1, :]
    edge[:-1, :] |= mask[:-1, :] != mask[1:, :]
    edge[:, 1:] |= mask[:, 1:] != mask[:, :-1]
    edge[:, :-1] |= mask[:, :-1] != mask[:, 1:]
    return edge & (mask > 0)


def blend(raw, mask, assigner, lo, hi, alpha, outline=True):
    """Return raw as grayscale RGB with colored cells (alpha fill, solid outline)."""
    gray = np.clip((raw.astype(np.float32) - lo) / max(hi - lo, 1e-6), 0, 1) * 255
    rgb = np.repeat(gray[..., None], 3, axis=2)
    colors = assigner.paint(mask).astype(np.float32)
    inside = mask > 0
    rgb[inside] = (1 - alpha) * rgb[inside] + alpha * colors[inside]
    if outline:
        edge = outlines(mask)
        rgb[edge] = colors[edge]
    return rgb.astype(np.uint8)


def overlay(a):
    """Write PNGs of the masks drawn semi-transparently over the raw images."""
    raws = frame_files(a.raw_dir, "t")
    if not raws:
        raise SystemExit(f"no tTTT.tif raw images in {a.raw_dir}")
    a.out_dir.mkdir(parents=True, exist_ok=True)
    lo = hi = None
    n = 0
    for t, mask, assigner in labelled_frames(a):
        if t not in raws:
            print(f"frame {t}: no raw image, skipped")
            continue
        raw = to_2d(tifffile.imread(str(raws[t])), a.z)
        if lo is None:  # same contrast for every frame, from the first one
            lo, hi = np.percentile(raw, [LOW_PCT, HIGH_PCT])
        img = Image.fromarray(
            blend(raw, mask_view(mask, a.z), assigner, lo, hi, a.alpha)
        )
        if a.side_by_side:
            gray = blend(raw, np.zeros(raw.shape, np.int64), assigner, lo, hi, 0)
            both = Image.new("RGB", (img.width * 2, img.height))
            both.paste(Image.fromarray(gray), (0, 0))
            both.paste(img, (img.width, 0))
            img = both
        if a.scale != 1.0:
            img = img.resize((round(img.width * a.scale), round(img.height * a.scale)))
        img.save(a.out_dir / f"overlay{t:03d}.png")
        n += 1
    cells = save_colors(assigner, a.out_dir)
    print(f"wrote {n} overlays and colors.json ({cells} cells) to {a.out_dir}")


def load_font():
    """Return a readable font (older Pillow versions only have a small fixed one)."""
    try:
        return ImageFont.load_default(size=FONT_SIZE)
    except TypeError:
        return ImageFont.load_default()


def read_tracks(path):
    """Read res_track.txt into {track ID: (first frame, last frame, parent ID)}."""
    tracks = {}
    for line in Path(path).read_text().split("\n"):
        if line.strip():
            label, begin, end, parent = map(int, line.split())
            tracks[label] = (begin, end, parent)
    return tracks


def centroids(mask):
    """Return {label: (x, y)} image-plane centroids (3D cells use their full volume)."""
    labels = [int(v) for v in np.unique(mask) if v]
    if not labels:
        return {}
    centers = ndimage.center_of_mass(mask > 0, mask, labels)
    return {lab: (c[-1], c[-2]) for lab, c in zip(labels, centers)}


def movie(a):
    """Write a tracking movie: overlay plus trajectory lines, as PNGs, GIF and MP4."""
    track_file = a.mask_dir / "res_track.txt"
    if not track_file.exists():
        raise SystemExit(f"{track_file} not found: the movie needs tracking results")
    tracks = read_tracks(track_file)
    raws = frame_files(a.raw_dir, "t")
    if not raws:
        raise SystemExit(f"no tTTT.tif raw images in {a.raw_dir}")
    frames_dir = a.out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for old in frames_dir.glob("movie*.png"):
        old.unlink()

    font = load_font()
    history = {}  # track ID -> [(frame, x, y)], in output pixel coordinates
    lo = hi = None
    images = []
    for t, mask, assigner in labelled_frames(a):
        if t not in raws:
            print(f"frame {t}: no raw image, skipped")
            continue
        raw = to_2d(tifffile.imread(str(raws[t])), a.z)
        if lo is None:
            lo, hi = np.percentile(raw, [LOW_PCT, HIGH_PCT])
        img = Image.fromarray(
            blend(
                raw, mask_view(mask, a.z), assigner, lo, hi, a.alpha, not a.no_outline
            )
        )
        if a.scale != 1.0:
            img = img.resize((round(img.width * a.scale), round(img.height * a.scale)))
        for lab, (x, y) in centroids(mask).items():
            history.setdefault(lab, []).append((t, x * a.scale, y * a.scale))

        draw = ImageDraw.Draw(img)
        for lab, pts in history.items():
            rgb = tuple(int(v) for v in TAB10_RGB[assigner.colors.get(lab, 0)])
            path = [(x, y) for f, x, y in pts if a.tail == 0 or t - f <= a.tail]
            if len(path) > 1:
                draw.line(path, fill=rgb, width=a.line_width, joint="curve")
            if pts[-1][0] != t:
                continue  # track has ended: keep its line, no marker
            x, y = pts[-1][1:]
            r = a.line_width + 2
            if not a.no_markers:
                draw.ellipse([x - r, y - r, x + r, y + r], fill=rgb)
                begin, _, parent = tracks.get(lab, (t, t, 0))
                if parent and t - begin < DIVISION_RING_FRAMES:
                    draw.ellipse(
                        [x - 12, y - 12, x + 12, y + 12], outline="white", width=3
                    )
                    if parent in history:
                        draw.line(
                            [history[parent][-1][1:], (x, y)], fill="white", width=2
                        )
            if a.labels:
                draw.text((x + r + 2, y - r - 2), str(lab), fill="white", font=font)

        if a.side_by_side:
            gray = Image.fromarray(
                blend(raw, np.zeros(raw.shape, np.int64), assigner, lo, hi, 0)
            ).resize(img.size)
            both = Image.new("RGB", (img.width * 2, img.height))
            both.paste(gray, (0, 0))
            both.paste(img, (img.width, 0))
            img = both
        ImageDraw.Draw(img).text((10, 8), f"t = {t}", fill="yellow", font=font)
        img.save(frames_dir / f"movie{len(images):04d}.png")
        images.append(img)

    if not images:
        raise SystemExit("no frames written")
    gif = a.out_dir / "movie.gif"
    images[0].save(
        gif, save_all=True, append_images=images[1:], duration=int(1000 / a.fps), loop=0
    )
    print(f"wrote {len(images)} frames to {frames_dir} and {gif}")
    write_mp4(frames_dir, a.out_dir / "movie.mp4", a.fps)
    save_colors(assigner, a.out_dir)


def write_mp4(frames_dir, mp4, fps):
    """Encode movieNNNN.png frames to an MP4 with ffmpeg, if it is installed."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        try:
            import imageio_ffmpeg

            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            print("ffmpeg not found: skipped movie.mp4 (the GIF and PNGs are written)")
            return
    cmd = [
        ffmpeg, "-y", "-loglevel", "error", "-framerate", str(fps),
        "-i", str(frames_dir / "movie%04d.png"),
        "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",  # H.264 needs even width and height
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(mp4),
    ]  # fmt: skip
    subprocess.run(cmd, check=True)  # noqa: S603
    print(f"wrote {mp4}")


def to_2d_rgb(rgb, mask, z):
    """Pick the 2D view of an RGB volume; 'max' shows the topmost cell at each pixel."""
    if z != "max":
        return to_2d(rgb, z)
    top = np.argmax(mask > 0, axis=0)  # first z with a cell at each (y, x)
    return np.take_along_axis(rgb, top[None, ..., None], axis=0)[0]


def parse_args():
    """Parse command-line arguments."""
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="step", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("mask_dir", type=Path, help="folder with maskTTT.tif")
    common.add_argument("out_dir", type=Path)
    common.add_argument(
        "--match_tracks", type=Path, help="tracking 0X_RES folder (for segmentation)"
    )
    common.add_argument("--frames", default="all", help="'all', 'a:b' or 'a,b,c'")
    common.add_argument("--z", default="mid", help="3D view: slice index, 'mid', 'max'")
    common.add_argument("--seed", type=int, default=0, help="seed for random colors")

    c = sub.add_parser(
        "color", parents=[common], help="color-code masks with consistent Tab10 colors"
    )
    c.add_argument("--tiff", action="store_true", help="also save full RGB TIFFs")
    c.set_defaults(func=color)

    o = sub.add_parser(
        "overlay", parents=[common], help="semi-transparent masks over the raw images"
    )
    o.add_argument("--raw_dir", type=Path, required=True, help="raw tTTT.tif folder")
    o.add_argument("--alpha", type=float, default=0.4, help="fill opacity, 0 to 1")
    o.add_argument("--side_by_side", action="store_true", help="raw next to overlay")
    o.add_argument("--scale", type=float, default=1.0, help="resize output, e.g. 0.5")
    o.set_defaults(func=overlay)

    m = sub.add_parser(
        "movie", parents=[common], help="tracking movie with trajectory lines"
    )
    m.add_argument("--raw_dir", type=Path, required=True, help="raw tTTT.tif folder")
    m.add_argument("--alpha", type=float, default=0.3, help="fill opacity, 0 to 1")
    m.add_argument("--tail", type=int, default=15, help="trajectory length in frames")
    m.add_argument("--line_width", type=int, default=2, help="trajectory line width")
    m.add_argument("--labels", action="store_true", help="write track IDs on cells")
    m.add_argument(
        "--no_outline", action="store_true", help="no colored outline around cells"
    )
    m.add_argument(
        "--no_markers",
        action="store_true",
        help="no dot on each cell and no white ring on new daughter cells",
    )
    m.add_argument("--side_by_side", action="store_true", help="raw next to movie")
    m.add_argument("--scale", type=float, default=1.0, help="resize output, e.g. 0.5")
    m.add_argument("--fps", type=float, default=5.0, help="frames per second")
    m.set_defaults(func=movie)
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    args.func(args)