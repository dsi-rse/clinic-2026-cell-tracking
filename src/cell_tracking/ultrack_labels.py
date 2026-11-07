"""Load saved 3D instance labels and run the Ultrack tracking pipeline.

Used by scripts/ultrack/track_3d_labels.py, including Cellpose-generated masks.
The tracking and export functions in this module are specific to Ultrack.
"""

from pathlib import Path

import numpy as np
import tifffile

from cell_tracking.ctc_io import extract_frame_number
from cell_tracking.ultrack_2d import validate_labels


def prepare_label_series(
    raw_dir: Path, label_dir: Path, output_path: Path, frame_stop: int | None = None
) -> tuple[np.memmap, list[int], bool]:
    """Validate matching ZYX frames and assemble a disk-backed TZYX array.

    Frames must start at zero because Ultrack exports time indices from zero.
    A shorter range is explicitly identified as a subset of the raw directory.
    """
    if not raw_dir.is_dir() or not label_dir.is_dir():
        raise FileNotFoundError("Both raw and label directories must exist.")
    if frame_stop is not None and frame_stop <= 0:
        raise ValueError("frame_stop must be positive.")
    raw_paths = sorted(raw_dir.glob("t*.tif"), key=extract_frame_number)
    frames = [extract_frame_number(path, "t") for path in raw_paths]
    if not frames or frames != list(range(len(frames))):
        raise ValueError("Raw frames must be consecutive and start at t000.tif.")
    selected = [
        path
        for path, frame in zip(raw_paths, frames)
        if frame_stop is None or frame < frame_stop
    ]
    selected_frames = frames[: len(selected)]
    label_paths = {
        extract_frame_number(path, "mask"): path for path in label_dir.glob("mask*.tif")
    }
    missing = set(selected_frames) - label_paths.keys()
    if missing:
        raise FileNotFoundError(f"Missing masks for frames {sorted(missing)}.")

    shape = None
    stack = None
    volume_dimensions = 3
    for index, path in enumerate(selected):
        with tifffile.TiffFile(path) as raw:
            raw_shape = raw.series[0].shape
        if len(raw_shape) != volume_dimensions:
            raise ValueError(f"Expected ZYX raw volume: {path}, shape={raw_shape}.")
        if shape is not None and raw_shape != shape:
            raise ValueError(f"Raw volume shape changed at {path.name}.")
        shape = raw_shape
        labels = tifffile.imread(label_paths[selected_frames[index]])
        validate_labels(labels, shape)
        if labels.max() > np.iinfo(np.uint32).max:
            raise ValueError("Labels exceed uint32 storage capacity.")
        if stack is None:
            stack = np.lib.format.open_memmap(
                output_path,
                mode="w+",
                dtype=np.uint32,
                shape=(len(selected), *shape),
            )
        stack[index] = labels
    stack.flush()
    return stack, selected_frames, len(selected) == len(raw_paths)


def track_label_series(labels, config, output_dir: Path, scale, contour_sigma):
    """Convert saved labels, run Ultrack, and export tracks and CTC masks.

    Scale is spatial Z/Y/X spacing in the same units as linking distances.
    Contour sigma is Z/Y/X Gaussian smoothing in voxels, not physical units.
    """
    from ultrack import link, segment, solve
    from ultrack.utils import labels_to_contours

    foreground, contours = labels_to_contours(
        labels,
        sigma=contour_sigma,
        foreground_store_or_path=str(output_dir / "foreground.zarr"),
        contours_store_or_path=str(output_dir / "contours.zarr"),
    )
    segment(foreground, contours, config)
    link(config, scale=scale)
    solve(config)
    return config


def export_label_tracks(config, output_dir: Path, result_dir: Path) -> dict:
    """Export a persisted solution without relying on a new Tracker's state.

    This can be called after an export failure without rerunning the solver.
    Only derived export files are replaced; the tracking database is read.
    """
    from ultrack import to_ctc, to_tracks_layer, tracks_to_zarr

    tracks, graph = to_tracks_layer(config)
    tracks.to_csv(output_dir / "tracks.csv", index=False)
    tracks_to_zarr(
        config, tracks, store_or_path=output_dir / "segments.zarr", overwrite=True
    )
    to_ctc(result_dir, config, overwrite=True)
    return {
        "track_rows": len(tracks),
        "unique_tracks": int(tracks["track_id"].nunique()),
        "lineage_entries": len(graph),
    }
