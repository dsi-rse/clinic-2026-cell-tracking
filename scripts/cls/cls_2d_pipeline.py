"""Segment a 2D CLS movie with Cellpose and track it with Ultrack.


Examples:
  python cls_2d_pipeline.py movie_MIP.tif out/movie1_ds4 --downsample 4 --frames 0:30 --napari
  python cls_2d_pipeline.py movie_MIP.tif out/movie1_ds4 --downsample 4 \
      --labels out/movie1_ds4/cellpose_labels.tif --max_distance 10 --gpu --napari
"""

import argparse
import json
import re
import time
from pathlib import Path

import numpy as np
import tifffile

MOVIE_NDIM = 3  # T, Y, X


def parse_args():
    """Parse command-line arguments."""
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "movie", type=Path, help="T x Y x X TIFF, or folder of tTTT.tif frames"
    )
    p.add_argument("out_dir", type=Path)
    p.add_argument(
        "--channel", type=int, help="channel to use if the movie has several"
    )
    p.add_argument("--channel_axis", type=int, default=1, help="axis of the channels")
    p.add_argument("--frames", default="all", help="'all' or 'a:b' (b exclusive)")
    p.add_argument("--crop", help="y0:y1,x0:x1 (in original pixels)")
    p.add_argument(
        "--downsample", type=int, default=1, help="average N x N pixel blocks"
    )
    g = p.add_argument_group("Cellpose")
    g.add_argument(
        "--labels", type=Path, help="reuse a T x Y x X labels TIFF, skip Cellpose"
    )
    g.add_argument(
        "--model", default="cyto3", help="Cellpose model (cyto3, nuclei, ...)"
    )
    g.add_argument(
        "--diameter", type=float, help="cell diameter in pixels (default: auto)"
    )
    g.add_argument(
        "--gpu", action="store_true", help="use the GPU / Apple MPS if available"
    )
    g = p.add_argument_group("Ultrack")
    g.add_argument("--min_area", type=int, default=20, help="smallest segment (pixels)")
    g.add_argument(
        "--max_area", type=int, default=100_000, help="largest segment (pixels)"
    )
    g.add_argument(
        "--max_distance", type=float, default=15.0, help="max link distance (px)"
    )
    g.add_argument("--solver", default="CBC", choices=["CBC", "GUROBI"])
    g.add_argument("--sigma", type=float, default=1.0, help="contour smoothing")
    p.add_argument("--napari", action="store_true", help="open the results in napari")
    return p.parse_args()


def load_movie(path, channel, channel_axis):
    """Load a movie as a T x Y x X array."""
    if path.is_dir():
        frames = sorted(
            (int(m.group(1)), f)
            for f in path.glob("t*.tif")
            if (m := re.fullmatch(r"t(\d+)\.tif", f.name))
        )
        movie = np.stack([tifffile.imread(str(f)) for _, f in frames])
    else:
        movie = tifffile.imread(str(path))
    movie = np.squeeze(movie)
    if channel is not None:
        movie = np.take(movie, channel, axis=channel_axis)
    if movie.ndim != MOVIE_NDIM:
        raise SystemExit(
            f"expected a T x Y x X movie, got shape {movie.shape}; "
            "use --channel / --channel_axis for multi-channel movies"
        )
    return movie


def preprocess(movie, frames, crop, factor):
    """Select frames, crop and downsample (block mean)."""
    if frames != "all":
        start, stop = (int(s) if s else None for s in frames.split(":"))
        movie = movie[start:stop]
    if crop:
        (y0, y1), (x0, x1) = (map(int, part.split(":")) for part in crop.split(","))
        movie = movie[:, y0:y1, x0:x1]
    if factor > 1:
        t, h, w = movie.shape
        h, w = h // factor * factor, w // factor * factor
        movie = movie[:, :h, :w].astype(np.float32)
        movie = movie.reshape(t, h // factor, factor, w // factor, factor).mean(
            axis=(2, 4)
        )
    return movie


def run_cellpose(movie, a):
    """Segment each frame with Cellpose; return a T x Y x X uint32 label stack."""
    from cellpose import models

    model = models.Cellpose(gpu=a.gpu, model_type=a.model)
    labels = np.zeros(movie.shape, dtype=np.uint32)
    for t, frame in enumerate(movie):
        masks, _, _, diams = model.eval(frame, diameter=a.diameter, channels=[0, 0])
        labels[t] = masks
        print(
            f"cellpose frame {t + 1}/{len(movie)}: {masks.max()} cells, diameter {diams:.1f}"
        )
    return labels


def run_ultrack(labels, a):
    """Track a label stack with Ultrack; return (tracks table, tracked labels)."""
    from ultrack import MainConfig, Tracker

    config = MainConfig()
    config.data_config.working_dir = a.out_dir / "ultrack"
    config.data_config.working_dir.mkdir(parents=True, exist_ok=True)
    config.segmentation_config.min_area = a.min_area
    config.segmentation_config.max_area = a.max_area
    config.linking_config.max_distance = a.max_distance
    config.tracking_config.solver_name = a.solver

    tracker = Tracker(config)
    tracker.track(labels=labels, sigma=a.sigma, overwrite="all")
    tracks_df, _ = tracker.to_tracks_layer()
    tracked = np.asarray(tracker.to_zarr(tracks_df=tracks_df))
    tracker.to_ctc(a.out_dir / "ctc" / "01_RES", overwrite=True)
    return tracks_df, tracked, config


def main():
    """Run the pipeline and save the outputs."""
    a = parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    start = time.time()

    movie = preprocess(
        load_movie(a.movie, a.channel, a.channel_axis), a.frames, a.crop, a.downsample
    )
    print(f"movie used: {movie.shape} (T, Y, X)")
    tifffile.imwrite(str(a.out_dir / "images.tif"), movie.astype(np.float32))

    if a.labels:
        labels = tifffile.imread(str(a.labels)).astype(np.uint32)
        if labels.shape != movie.shape:
            raise SystemExit(
                f"labels shape {labels.shape} != movie shape {movie.shape}"
            )
    else:
        labels = run_cellpose(movie, a)
        tifffile.imwrite(str(a.out_dir / "cellpose_labels.tif"), labels)
    seg_time = time.time() - start

    tracks_df, tracked, config = run_ultrack(labels, a)
    tracks_df.to_csv(a.out_dir / "tracks.csv", index=False)
    tifffile.imwrite(str(a.out_dir / "tracked_labels.tif"), tracked.astype(np.uint32))

    settings = {
        "args": {k: str(v) for k, v in vars(a).items()},
        "movie_shape_used": list(movie.shape),
        "n_tracks": int(tracks_df["track_id"].nunique()),
        "seconds_segmentation": round(seg_time, 1),
        "seconds_total": round(time.time() - start, 1),
        "ultrack_config": json.loads(config.model_dump_json(by_alias=True)),
    }
    (a.out_dir / "settings.json").write_text(json.dumps(settings, indent=1))
    print(f"{settings['n_tracks']} tracks; outputs in {a.out_dir}")

    if a.napari:
        import napari

        viewer = napari.Viewer()
        viewer.add_image(movie, name="images")
        viewer.add_labels(labels, name="cellpose_labels", visible=False)
        viewer.add_labels(tracked, name="tracked_labels")
        viewer.add_tracks(tracks_df[["track_id", "t", "y", "x"]], name="tracks")
        napari.run()


if __name__ == "__main__":
    main()