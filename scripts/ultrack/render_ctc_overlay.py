"""Render a 2D CTC prediction-versus-ground-truth overlay movie."""

import argparse
from pathlib import Path

import tifffile

from cell_tracking.ctc_io import extract_frame_number
from cell_tracking.ctc_visualization import (
    render_overlay_frame,
    save_animated_gif,
)

GROUND_TRUTH_SOURCES = ("TRA", "SEG")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Create an animated 2D overlay of raw CTC images, ground truth, "
            "and predicted result masks."
        )
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        required=True,
        help="CTC sequence directory containing tNNN.tif images.",
    )
    parser.add_argument(
        "--ground-truth-dir",
        type=Path,
        required=True,
        help="CTC NN_GT directory containing TRA and SEG subdirectories.",
    )
    parser.add_argument(
        "--result-dir",
        type=Path,
        required=True,
        help="CTC NN_RES directory containing maskNNN.tif predictions.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        required=True,
        help="Output GIF path.",
    )
    parser.add_argument(
        "--ground-truth-source",
        choices=GROUND_TRUTH_SOURCES,
        default="TRA",
        help=(
            "Use continuous tracking masks (TRA) or sparse segmentation "
            "annotations (SEG)."
        ),
    )
    parser.add_argument("--frame-start", type=int, default=0)
    parser.add_argument("--frame-stop", type=int)
    parser.add_argument("--fps", type=float, default=4.0)
    parser.add_argument("--scale", type=float, default=0.5)
    parser.add_argument("--alpha", type=float, default=0.55)
    parser.add_argument("--boundary-width", type=int, default=2)
    parser.add_argument("--iou-threshold", type=float, default=0.5)
    parser.add_argument(
        "--crop",
        type=int,
        nargs=4,
        metavar=("TOP", "BOTTOM", "LEFT", "RIGHT"),
        help="Optional diagnostic crop in pixel coordinates.",
    )
    parser.add_argument(
        "--show-track-ids",
        action="store_true",
        help="Draw GT and prediction track IDs; best used with --crop.",
    )
    parser.add_argument(
        "--tracking-only",
        action="store_true",
        help="Render only the continuous boundary and track-ID panel.",
    )
    parser.add_argument(
        "--only-annotated",
        action="store_true",
        help="Skip frames that do not have the selected ground-truth mask.",
    )
    parser.add_argument(
        "--max-track-labels",
        type=int,
        default=40,
        help="Maximum number of GT and prediction IDs drawn in each frame.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    """Validate numeric and directory arguments."""
    for directory in (args.raw_dir, args.ground_truth_dir, args.result_dir):
        if not directory.is_dir():
            raise FileNotFoundError(f"Directory does not exist: {directory}")
    if args.output_path.suffix.lower() != ".gif":
        raise ValueError("--output-path must end in .gif.")
    if args.frame_start < 0:
        raise ValueError("--frame-start must be nonnegative.")
    if args.frame_stop is not None and args.frame_stop <= args.frame_start:
        raise ValueError("--frame-stop must be greater than --frame-start.")
    if not 0 < args.alpha <= 1:
        raise ValueError("--alpha must be greater than 0 and at most 1.")
    if not 0 < args.iou_threshold <= 1:
        raise ValueError("--iou-threshold must be greater than 0 and at most 1.")
    if args.max_track_labels < 1:
        raise ValueError("--max-track-labels must be at least 1.")
    if args.crop is not None:
        top, bottom, left, right = args.crop
        if min(top, left) < 0 or bottom <= top or right <= left:
            raise ValueError("--crop must be TOP BOTTOM LEFT RIGHT with valid bounds.")


def crop_image(image, crop: list[int] | None):
    """Apply an optional TOP BOTTOM LEFT RIGHT crop."""
    if crop is None:
        return image
    top, bottom, left, right = crop
    if bottom > image.shape[-2] or right > image.shape[-1]:
        raise ValueError(f"Crop {crop} exceeds image shape {image.shape[-2:]}.")
    return image[top:bottom, left:right]


def ground_truth_path(
    ground_truth_dir: Path,
    source: str,
    frame_number: int,
) -> Path:
    """Construct a CTC ground-truth mask path."""
    prefix = "man_track" if source == "TRA" else "man_seg"
    return ground_truth_dir / source / f"{prefix}{frame_number:03d}.tif"


def main() -> None:
    """Load selected frames, render diagnostic overlays, and save a GIF."""
    args = parse_args()
    validate_args(args)

    result_paths = sorted(args.result_dir.glob("mask*.tif"))
    selected = []
    for path in result_paths:
        frame_number = extract_frame_number(path, expected_prefix="mask")
        if frame_number >= args.frame_start and (
            args.frame_stop is None or frame_number < args.frame_stop
        ):
            selected.append((frame_number, path))
    if args.only_annotated:
        selected = [
            (frame_number, path)
            for frame_number, path in selected
            if ground_truth_path(
                args.ground_truth_dir,
                args.ground_truth_source,
                frame_number,
            ).is_file()
        ]
    if not selected:
        raise ValueError("The requested frame range contains no eligible result masks.")

    frames = []
    ground_truth_frames = 0
    for index, (frame_number, result_path) in enumerate(selected, start=1):
        print(f"Rendering frame {frame_number:03d} ({index}/{len(selected)})")
        raw_path = args.raw_dir / f"t{frame_number:03d}.tif"
        if not raw_path.is_file():
            raise FileNotFoundError(f"Raw image does not exist: {raw_path}")

        raw = crop_image(tifffile.imread(raw_path), args.crop)
        prediction = crop_image(tifffile.imread(result_path), args.crop)
        expected_ground_truth_path = ground_truth_path(
            args.ground_truth_dir,
            args.ground_truth_source,
            frame_number,
        )
        if expected_ground_truth_path.is_file():
            ground_truth = crop_image(
                tifffile.imread(expected_ground_truth_path),
                args.crop,
            )
            ground_truth_frames += 1
        else:
            ground_truth = None

        frames.append(
            render_overlay_frame(
                raw=raw,
                ground_truth=ground_truth,
                prediction=prediction,
                frame_number=frame_number,
                ground_truth_source=args.ground_truth_source,
                alpha=args.alpha,
                boundary_width=args.boundary_width,
                iou_threshold=args.iou_threshold,
                show_track_ids=args.show_track_ids,
                maximum_track_labels=args.max_track_labels,
                tracking_only=args.tracking_only,
            )
        )

    save_animated_gif(
        frames,
        output_path=args.output_path,
        frames_per_second=args.fps,
        scale=args.scale,
    )
    print(f"Saved overlay movie: {args.output_path}")
    print(
        f"Ground truth was available for {ground_truth_frames}/{len(selected)} frames."
    )


if __name__ == "__main__":
    main()
