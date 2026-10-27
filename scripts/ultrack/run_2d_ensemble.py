"""Combine saved 2D segmentation methods and run the Ultrack workflow."""

import argparse
import json
import re
import time
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import tifffile

from cell_tracking.ultrack_2d import combine_label_stacks

FRAME_PATTERN = re.compile(r"^t(?P<frame>\d+)\.tif$")
EXPECTED_IMAGE_DIMENSIONS = 2
MINIMUM_WORKER_COUNT = 1


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Combine watershed, Cellpose, and StarDist label-derived maps, "
            "run Ultrack, and export a CTC result."
        )
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing raw tNNN.tif images.",
    )
    parser.add_argument(
        "--watershed-label-dir",
        type=Path,
        required=True,
        help="Watershed input_labels directory.",
    )
    parser.add_argument(
        "--cellpose-label-dir",
        type=Path,
        required=True,
        help="Cellpose input_labels directory.",
    )
    parser.add_argument(
        "--stardist-label-dir",
        type=Path,
        required=True,
        help="StarDist input_labels directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Dedicated output directory for the ensemble run.",
    )
    parser.add_argument(
        "--sequence",
        required=True,
        help="CTC sequence identifier, such as 01 or 02.",
    )
    parser.add_argument("--frame-start", type=int, default=0)
    parser.add_argument(
        "--frame-stop",
        type=int,
        help="Exclusive ending frame. Omit to process the complete sequence.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow reuse of a nonempty output directory.",
    )
    parser.add_argument("--contour-sigma", type=float, default=4.0)

    worker_group = parser.add_argument_group("Ultrack workers")
    worker_group.add_argument("--segmentation-workers", type=int, default=1)
    worker_group.add_argument("--linking-workers", type=int, default=1)
    worker_group.add_argument("--solver-threads", type=int, default=4)
    worker_group.add_argument("--solver", default="GUROBI")
    return parser.parse_args()


def extract_frame_number(path: Path) -> int:
    """Extract a frame number from a raw CTC filename."""
    match = FRAME_PATTERN.fullmatch(path.name)
    if match is None:
        raise ValueError(f"Expected a filename like t000.tif, got {path.name}.")
    return int(match.group("frame"))


def select_raw_paths(
    input_dir: Path,
    frame_start: int,
    frame_stop: int | None,
) -> tuple[list[Path], list[int], bool]:
    """Select consecutive raw frames and identify a complete sequence."""
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    all_paths = sorted(input_dir.glob("t*.tif"))
    all_frames = [extract_frame_number(path) for path in all_paths]
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

    return paths, frames, frames == all_frames


def validate_args(args: argparse.Namespace) -> None:
    """Validate numeric command-line arguments."""
    if args.frame_start < 0:
        raise ValueError("--frame-start must be nonnegative.")
    if args.frame_stop is not None and args.frame_stop <= args.frame_start:
        raise ValueError("--frame-stop must be greater than --frame-start.")
    if args.contour_sigma < 0:
        raise ValueError("--contour-sigma must be nonnegative.")

    worker_counts = (
        args.segmentation_workers,
        args.linking_workers,
        args.solver_threads,
    )
    if any(count < MINIMUM_WORKER_COUNT for count in worker_counts):
        raise ValueError("All worker and thread counts must be at least 1.")


def prepare_output_directory(output_dir: Path, overwrite: bool) -> None:
    """Create the run directory without silently reusing existing outputs."""
    if output_dir.is_dir() and any(output_dir.iterdir()) and not overwrite:
        raise FileExistsError(
            f"Output directory is not empty: {output_dir}. "
            "Choose a new directory or pass --overwrite."
        )
    output_dir.mkdir(parents=True, exist_ok=True)


def package_versions() -> dict[str, str]:
    """Collect installed versions relevant to the ensemble workflow."""
    versions = {}
    for package in ("numpy", "tifffile", "ultrack"):
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "not installed"
    return versions


def write_run_report(report: dict[str, Any], output_dir: Path) -> Path:
    """Write a machine-readable record of the ensemble run."""
    report_path = output_dir / "run_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return report_path


def main() -> None:
    """Combine saved inputs, run Ultrack, and export the result."""
    args = parse_args()
    validate_args(args)
    prepare_output_directory(args.output_dir, args.overwrite)

    raw_paths, frame_numbers, is_complete = select_raw_paths(
        args.input_dir,
        args.frame_start,
        args.frame_stop,
    )
    first_image = tifffile.imread(raw_paths[0])
    if first_image.ndim != EXPECTED_IMAGE_DIMENSIONS:
        raise ValueError(f"Expected a 2D raw image, found shape {first_image.shape}.")
    expected_shape = (len(frame_numbers), *first_image.shape)
    print(f"Files: {raw_paths[0].name} to {raw_paths[-1].name}")
    print(f"Expected map shape: {expected_shape}")

    label_dirs = {
        "watershed": args.watershed_label_dir,
        "cellpose": args.cellpose_label_dir,
        "stardist": args.stardist_label_dir,
    }
    runtimes = {}
    start_time = time.perf_counter()
    foreground, contours, label_counts = combine_label_stacks(
        label_dirs,
        frame_numbers,
        expected_shape,
        args.contour_sigma,
    )
    runtimes["ensemble_input_conversion"] = time.perf_counter() - start_time
    input_summary = {
        "foreground_fraction": float(foreground.mean()),
        "contour_minimum": float(contours.min()),
        "contour_maximum": float(contours.max()),
        "contour_mean": float(contours.mean()),
    }
    print(
        "Combined foreground fraction: " f"{input_summary['foreground_fraction']:.6f}"
    )
    print(
        "Combined contour range: "
        f"{input_summary['contour_minimum']:.6f} to "
        f"{input_summary['contour_maximum']:.6f}"
    )

    try:
        from ultrack import MainConfig, Tracker
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            "Ultrack is required for the ensemble workflow."
        ) from error

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

    report: dict[str, Any] = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "method": "ensemble",
        "sequence": args.sequence,
        "frame_numbers": frame_numbers,
        "complete_sequence": is_complete,
        "input_dir": str(args.input_dir.resolve()),
        "input_label_dirs": {
            method: str(path.resolve()) for method, path in label_dirs.items()
        },
        "output_dir": str(args.output_dir.resolve()),
        "map_shape": list(expected_shape),
        "label_counts": label_counts,
        "combined_input_summary": input_summary,
        "method_parameters": {
            "component_methods": list(label_dirs),
            "foreground_combination": "logical OR",
            "contour_combination": "arithmetic mean",
        },
        "contour_sigma": args.contour_sigma,
        "versions": package_versions(),
        "runtimes_seconds": runtimes,
        "ultrack": {
            "data_workers": 1,
            "segmentation_workers": args.segmentation_workers,
            "linking_workers": args.linking_workers,
            "solver_threads": args.solver_threads,
            "solver": args.solver,
        },
        "outputs": {
            "tracks_csv": str(tracks_path),
            "segments_zarr": str(segments_path),
            "ctc_result_dir": str(ctc_output_dir),
            "track_rows": len(tracks),
            "unique_tracks": int(tracks["track_id"].nunique()),
            "lineage_entries": len(graph),
        },
    }
    report_path = write_run_report(report, args.output_dir)

    print(f"CTC output: {ctc_output_dir}")
    print(f"Track rows: {len(tracks)}")
    print(f"Unique tracks: {tracks['track_id'].nunique()}")
    print(f"Lineage entries: {len(graph)}")
    print(f"Run report: {report_path}")


if __name__ == "__main__":
    main()
