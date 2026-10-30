"""Run a reusable 2D segmentation-to-Ultrack benchmark workflow."""

import argparse
import json
import time
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import numpy as np
import tifffile

from cell_tracking.ctc_io import extract_frame_number
from cell_tracking.ultrack_2d import (
    load_image_stack,
    segment_with_cellpose,
    segment_with_stardist,
    segment_with_watershed,
    validate_labels,
)

METHODS = ("stardist", "watershed", "cellpose")
MINIMUM_WORKER_COUNT = 1


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate 2D instance labels, convert them to Ultrack inputs, "
            "run tracking, and export a CTC result."
        )
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing raw tNNN.tif images.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Dedicated output directory for this method and sequence.",
    )
    parser.add_argument(
        "--sequence",
        required=True,
        help="CTC sequence identifier, such as 01 or 02.",
    )
    parser.add_argument("--method", choices=METHODS, required=True)
    parser.add_argument("--frame-start", type=int, default=0)
    parser.add_argument(
        "--frame-stop",
        type=int,
        help="Exclusive ending frame. Omit to process the complete sequence.",
    )
    parser.add_argument(
        "--labels-only",
        action="store_true",
        help="Generate and save instance labels without running Ultrack.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow reuse of a nonempty output directory.",
    )
    parser.add_argument("--contour-sigma", type=float, default=4.0)

    worker_group = parser.add_argument_group("Ultrack workers")
    worker_group.add_argument("--segmentation-workers", type=int, default=4)
    worker_group.add_argument("--linking-workers", type=int, default=1)
    worker_group.add_argument("--solver-threads", type=int, default=4)
    worker_group.add_argument("--solver", default="GUROBI")

    stardist_group = parser.add_argument_group("StarDist")
    stardist_group.add_argument(
        "--stardist-model",
        default="2D_versatile_fluo",
    )
    stardist_group.add_argument("--stardist-block-size", type=int, default=560)
    stardist_group.add_argument("--stardist-min-overlap", type=int, default=96)

    cellpose_group = parser.add_argument_group("Cellpose")
    cellpose_group.add_argument("--cellpose-model", default="cyto2")
    cellpose_group.add_argument("--cellpose-gpu", action="store_true")
    cellpose_group.add_argument("--cellpose-diameter", type=float)
    cellpose_group.add_argument(
        "--cellpose-flow-threshold",
        type=float,
        default=0.4,
    )
    cellpose_group.add_argument(
        "--cellpose-cellprob-threshold",
        type=float,
        default=0.0,
    )
    cellpose_group.add_argument("--cellpose-model-cache", type=Path)

    watershed_group = parser.add_argument_group("Watershed")
    watershed_group.add_argument(
        "--watershed-smoothing-sigma",
        type=float,
        default=1.0,
    )
    watershed_group.add_argument(
        "--watershed-h-minima",
        type=float,
        default=2.0,
    )
    watershed_group.add_argument(
        "--watershed-minimum-object-size",
        type=int,
        default=20,
    )
    return parser.parse_args()


def select_raw_paths(
    input_dir: Path,
    frame_start: int,
    frame_stop: int | None,
) -> tuple[list[Path], list[int], bool]:
    """Select a consecutive frame range and identify a complete sequence."""
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
    if frame_start < 0:
        raise ValueError("--frame-start must be nonnegative.")
    if frame_stop is not None and frame_stop <= frame_start:
        raise ValueError("--frame-stop must be greater than --frame-start.")

    all_paths = sorted(input_dir.glob("t*.tif"))
    all_frames = [extract_frame_number(path, expected_prefix="t") for path in all_paths]
    selected = [
        (path, frame)
        for path, frame in zip(all_paths, all_frames)
        if frame >= frame_start and (frame_stop is None or frame < frame_stop)
    ]
    if not selected:
        raise ValueError("The requested frame range contains no raw images.")

    paths, frames = map(list, zip(*selected))
    expected_frames = list(range(frames[0], frames[-1] + 1))
    if frames != expected_frames:
        raise ValueError(f"Selected frames are not consecutive: {frames}")

    is_complete = frames == all_frames
    return paths, frames, is_complete


def validate_args(args: argparse.Namespace) -> None:
    """Validate shared and method-specific numeric arguments."""
    worker_counts = (
        args.segmentation_workers,
        args.linking_workers,
        args.solver_threads,
    )
    if any(count < MINIMUM_WORKER_COUNT for count in worker_counts):
        raise ValueError("All worker and thread counts must be at least 1.")
    if args.contour_sigma < 0:
        raise ValueError("--contour-sigma must be nonnegative.")
    if args.watershed_h_minima <= 0:
        raise ValueError("--watershed-h-minima must be greater than 0.")
    if args.watershed_minimum_object_size < 1:
        raise ValueError("--watershed-minimum-object-size must be at least 1.")


def prepare_output_directory(output_dir: Path, overwrite: bool) -> None:
    """Create the run directory without silently reusing existing outputs."""
    if output_dir.is_dir() and any(output_dir.iterdir()) and not overwrite:
        raise FileExistsError(
            f"Output directory is not empty: {output_dir}. "
            "Choose a new directory or pass --overwrite."
        )
    output_dir.mkdir(parents=True, exist_ok=True)


def generate_labels(
    images: np.ndarray,
    args: argparse.Namespace,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Generate labels with the selected method and record its parameters."""
    if args.method == "stardist":
        labels = segment_with_stardist(
            images,
            model_name=args.stardist_model,
            block_size=args.stardist_block_size,
            min_overlap=args.stardist_min_overlap,
        )
        parameters = {
            "model": args.stardist_model,
            "gamma": 1.0,
            "block_size": args.stardist_block_size,
            "min_overlap": args.stardist_min_overlap,
        }
    elif args.method == "cellpose":
        labels = segment_with_cellpose(
            images,
            model_name=args.cellpose_model,
            use_gpu=args.cellpose_gpu,
            diameter=args.cellpose_diameter,
            flow_threshold=args.cellpose_flow_threshold,
            cellprob_threshold=args.cellpose_cellprob_threshold,
            model_cache_dir=args.cellpose_model_cache,
        )
        parameters = {
            "model": args.cellpose_model,
            "gpu_requested": args.cellpose_gpu,
            "diameter": args.cellpose_diameter,
            "channels": [0, 0],
            "flow_threshold": args.cellpose_flow_threshold,
            "cellprob_threshold": args.cellpose_cellprob_threshold,
        }
    else:
        labels = segment_with_watershed(
            images,
            smoothing_sigma=args.watershed_smoothing_sigma,
            h_minima=args.watershed_h_minima,
            minimum_object_size=args.watershed_minimum_object_size,
        )
        parameters = {
            "foreground_threshold": "Otsu per frame",
            "smoothing_sigma": args.watershed_smoothing_sigma,
            "h_minima": args.watershed_h_minima,
            "minimum_object_size": args.watershed_minimum_object_size,
        }

    validate_labels(labels, images.shape)
    return labels, parameters


def save_labels(labels: np.ndarray, frames: list[int], output_dir: Path) -> Path:
    """Save one generated instance-label TIFF per original frame number."""
    label_dir = output_dir / "input_labels"
    label_dir.mkdir(parents=True, exist_ok=True)
    for frame, frame_labels in zip(frames, labels):
        tifffile.imwrite(
            label_dir / f"mask{frame:03d}.tif",
            frame_labels.astype(np.uint32),
        )
    return label_dir


def package_versions(method: str) -> dict[str, str]:
    """Collect installed versions relevant to the selected workflow."""
    packages = ["numpy", "tifffile", "ultrack"]
    if method == "stardist":
        packages.extend(["stardist", "tensorflow"])
    elif method == "cellpose":
        packages.extend(["cellpose", "torch"])
    else:
        packages.extend(["scikit-image", "scipy"])

    versions = {}
    for package in packages:
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "not installed"
    return versions


def write_run_report(report: dict[str, Any], output_dir: Path) -> Path:
    """Write a machine-readable record of inputs, parameters, and outputs."""
    report_path = output_dir / "run_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return report_path


def main() -> None:
    """Run segmentation, Ultrack, export, and reproducibility reporting."""
    args = parse_args()
    validate_args(args)
    prepare_output_directory(args.output_dir, args.overwrite)

    raw_paths, frame_numbers, is_complete = select_raw_paths(
        args.input_dir,
        args.frame_start,
        args.frame_stop,
    )
    images = load_image_stack(raw_paths)
    print(f"Files: {raw_paths[0].name} to {raw_paths[-1].name}")
    print(f"Raw array: shape={images.shape}, dtype={images.dtype}")

    runtimes = {}
    start_time = time.perf_counter()
    labels, method_parameters = generate_labels(images, args)
    runtimes["instance_segmentation"] = time.perf_counter() - start_time

    label_dir = save_labels(labels, frame_numbers, args.output_dir)
    label_counts = [
        int(np.count_nonzero(np.unique(frame_labels))) for frame_labels in labels
    ]
    print(f"Saved labels: {label_dir}")
    print(f"Label counts by frame: {dict(zip(frame_numbers, label_counts))}")

    report: dict[str, Any] = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "method": args.method,
        "sequence": args.sequence,
        "frame_numbers": frame_numbers,
        "complete_sequence": is_complete,
        "input_dir": str(args.input_dir.resolve()),
        "output_dir": str(args.output_dir.resolve()),
        "image_shape": list(images.shape),
        "image_dtype": str(images.dtype),
        "label_counts": dict(zip(map(str, frame_numbers), label_counts)),
        "method_parameters": method_parameters,
        "contour_sigma": args.contour_sigma,
        "versions": package_versions(args.method),
        "runtimes_seconds": runtimes,
    }

    if args.labels_only:
        report_path = write_run_report(report, args.output_dir)
        print(f"Labels-only run complete. Report: {report_path}")
        return

    try:
        from ultrack import MainConfig, Tracker
        from ultrack.utils import labels_to_contours
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            "Ultrack is required unless --labels-only is used. "
            "Activate an Ultrack environment."
        ) from error

    start_time = time.perf_counter()
    foreground, contours = labels_to_contours(labels, sigma=args.contour_sigma)
    foreground = np.asarray(foreground).astype(bool)
    contours = np.asarray(contours).astype(np.float32)
    runtimes["label_to_contours"] = time.perf_counter() - start_time

    config = MainConfig()
    config.data_config.working_dir = args.output_dir
    config.data_config.n_workers = 1
    config.segmentation_config.n_workers = args.segmentation_workers
    config.linking_config.n_workers = args.linking_workers
    config.tracking_config.n_threads = args.solver_threads
    config.tracking_config.solver_name = args.solver

    tracker = Tracker(config=config)

    start_time = time.perf_counter()
    tracker.segment(foreground=foreground, contours=contours, overwrite=True)
    runtimes["ultrack_segmentation"] = time.perf_counter() - start_time

    start_time = time.perf_counter()
    tracker.link(overwrite=True)
    runtimes["ultrack_linking"] = time.perf_counter() - start_time

    start_time = time.perf_counter()
    tracker.solve(overwrite=True)
    runtimes["ultrack_solving"] = time.perf_counter() - start_time

    tracks, graph = tracker.to_tracks_layer()
    tracks_path = args.output_dir / "tracks.csv"
    segments_path = args.output_dir / "segments.zarr"
    ctc_name = f"{args.sequence}_RES" if is_complete else "subset_RES"
    ctc_output_dir = args.output_dir / ctc_name

    tracks.to_csv(tracks_path, index=False)
    tracker.to_zarr(store_or_path=segments_path, overwrite=True)
    tracker.to_ctc(ctc_output_dir, overwrite=True)

    report["ultrack"] = {
        "data_workers": 1,
        "segmentation_workers": args.segmentation_workers,
        "linking_workers": args.linking_workers,
        "solver_threads": args.solver_threads,
        "solver": args.solver,
    }
    report["outputs"] = {
        "tracks_csv": str(tracks_path),
        "segments_zarr": str(segments_path),
        "ctc_result_dir": str(ctc_output_dir),
        "track_rows": len(tracks),
        "unique_tracks": int(tracks["track_id"].nunique()),
        "lineage_entries": len(graph),
    }
    report_path = write_run_report(report, args.output_dir)

    print(f"CTC output: {ctc_output_dir}")
    print(f"Track rows: {len(tracks)}")
    print(f"Unique tracks: {tracks['track_id'].nunique()}")
    print(f"Lineage entries: {len(graph)}")
    print(f"Run report: {report_path}")


if __name__ == "__main__":
    main()
