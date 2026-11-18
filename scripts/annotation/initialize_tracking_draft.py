"""Transfer clear Ultrack IDs onto corrected segmentation boundaries."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import tifffile


DEFAULT_SEGMENTATION_DIR = Path(
    "external/annotations/cls-loose-colony/labels-working"
)
DEFAULT_TRACKING_DIR = Path(
    "external/annotations/cls-loose-colony/tracking-working"
)
DEFAULT_OUTPUT_DIR = Path(
    "external/annotations/cls-loose-colony/tracking-draft-mutual-best"
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Create tracking masks with corrected segmentation boundaries. "
            "Only strong mutual-best overlaps inherit an existing track ID."
        )
    )
    parser.add_argument(
        "--segmentation-dir",
        type=Path,
        default=DEFAULT_SEGMENTATION_DIR,
    )
    parser.add_argument(
        "--tracking-dir",
        type=Path,
        default=DEFAULT_TRACKING_DIR,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )
    parser.add_argument("--frames", type=int, default=20)
    parser.add_argument("--minimum-iou", type=float, default=0.5)
    parser.add_argument("--minimum-dominance", type=float, default=0.8)
    return parser.parse_args()


def _input_paths(directory: Path, frames: int) -> list[Path]:
    """Return the expected mask paths and check that they exist."""
    paths = [directory / f"mask{frame:03d}.tif" for frame in range(frames)]
    missing = [path for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing input masks: {missing}")
    return paths


def _overlap_counts(
    segmentation: np.ndarray,
    tracking: np.ndarray,
) -> dict[tuple[int, int], int]:
    """Count pixels shared by each segmentation and tracking ID pair."""
    intersections = {}

    for segment_id in np.unique(segmentation):
        segment_id = int(segment_id)
        if segment_id == 0:
            continue
        track_ids, counts = np.unique(
            tracking[segmentation == segment_id],
            return_counts=True,
        )
        for track_id, count in zip(track_ids, counts):
            track_id = int(track_id)
            if track_id != 0:
                intersections[(segment_id, track_id)] = int(count)

    return intersections


def initialize_frame(
    segmentation: np.ndarray,
    tracking: np.ndarray,
    minimum_iou: float,
    minimum_dominance: float,
) -> tuple[np.ndarray, list[dict[str, object]]]:
    """Create one tracking frame and its assignment review rows."""
    if segmentation.shape != tracking.shape:
        raise ValueError(
            "Segmentation and tracking frame shapes differ: "
            f"{segmentation.shape} and {tracking.shape}."
        )

    intersections = _overlap_counts(
        segmentation,
        tracking,
    )
    draft = np.zeros(segmentation.shape, dtype=np.uint32)
    review_rows = []

    segment_ids = [
        int(segment_id)
        for segment_id in np.unique(segmentation)
        if segment_id != 0
    ]
    track_ids = [
        int(track_id)
        for track_id in np.unique(tracking)
        if track_id != 0
    ]

    best_segment_for_track = {}
    for track_id in track_ids:
        overlapping_segments = [
            segment_id
            for segment_id in segment_ids
            if (segment_id, track_id) in intersections
        ]
        if overlapping_segments:
            overlapping_segments.sort(
                key=lambda segment_id: intersections[
                    (segment_id, track_id)
                ],
                reverse=True,
            )
            best_segment = overlapping_segments[0]
            best_count = intersections[(best_segment, track_id)]
            second_count = (
                intersections[(overlapping_segments[1], track_id)]
                if len(overlapping_segments) > 1
                else 0
            )
            best_segment_for_track[track_id] = (
                best_segment if best_count > second_count else 0
            )

    for segment_id in segment_ids:
        overlapping_track_ids = [
            track_id
            for track_id in track_ids
            if (segment_id, track_id) in intersections
        ]
        assigned_track_id = 0
        best_track_id = 0
        best_iou = 0.0
        dominance = 0.0

        if not overlapping_track_ids:
            status = "no_overlap"
        else:
            overlapping_track_ids.sort(
                key=lambda track_id: intersections[
                    (segment_id, track_id)
                ],
                reverse=True,
            )
            best_track_id = overlapping_track_ids[0]
            best_intersection = intersections[
                (segment_id, best_track_id)
            ]
            second_intersection = (
                intersections[(segment_id, overlapping_track_ids[1])]
                if len(overlapping_track_ids) > 1
                else 0
            )
            dominance = best_intersection / (
                best_intersection + second_intersection
            )

            segment_area = int(np.count_nonzero(segmentation == segment_id))
            track_area = int(np.count_nonzero(tracking == best_track_id))
            best_iou = best_intersection / (
                segment_area + track_area - best_intersection
            )

            if best_segment_for_track[best_track_id] != segment_id:
                status = "not_mutual_best"
            elif best_iou < minimum_iou:
                status = "low_iou"
            elif dominance < minimum_dominance:
                status = "low_dominance"
            else:
                status = "assigned"
                assigned_track_id = best_track_id
                draft[segmentation == segment_id] = best_track_id

        review_rows.append(
            {
                "segmentation_label": segment_id,
                "status": status,
                "overlapping_track_ids": ";".join(
                    str(track_id) for track_id in overlapping_track_ids
                ),
                "best_track_id": best_track_id,
                "best_iou": round(best_iou, 4),
                "dominance": round(dominance, 4),
                "assigned_track_id": assigned_track_id,
            }
        )

    return draft, review_rows


def main() -> None:
    """Create a separate, reviewable tracking draft."""
    args = parse_args()
    if args.frames <= 0:
        raise ValueError("--frames must be greater than zero.")
    if not 0.0 <= args.minimum_iou <= 1.0:
        raise ValueError("--minimum-iou must be between zero and one.")
    if not 0.0 <= args.minimum_dominance <= 1.0:
        raise ValueError(
            "--minimum-dominance must be between zero and one."
        )

    segmentation_paths = _input_paths(args.segmentation_dir, args.frames)
    tracking_paths = _input_paths(args.tracking_dir, args.frames)

    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise FileExistsError(
            f"Output directory is not empty: {args.output_dir}. "
            "Use a new directory so existing annotations are not overwritten."
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)

    all_review_rows = []
    frame_summaries = []
    for frame, (segmentation_path, tracking_path) in enumerate(
        zip(segmentation_paths, tracking_paths)
    ):
        segmentation = tifffile.imread(segmentation_path)
        tracking = tifffile.imread(tracking_path)
        draft, review_rows = initialize_frame(
            segmentation,
            tracking,
            minimum_iou=args.minimum_iou,
            minimum_dominance=args.minimum_dominance,
        )

        output_path = args.output_dir / f"mask{frame:03d}.tif"
        tifffile.imwrite(output_path, draft)

        for row in review_rows:
            row["frame"] = frame
            all_review_rows.append(row)

        assigned = sum(row["status"] == "assigned" for row in review_rows)
        review = len(review_rows) - assigned
        frame_summaries.append(
            {
                "frame": frame,
                "segmentation_objects": len(review_rows),
                "assigned": assigned,
                "needs_review": review,
            }
        )
        print(
            f"Frame {frame:02d}: assigned {assigned}, "
            f"needs review {review}"
        )

    review_path = args.output_dir / "assignment_review.csv"
    with review_path.open("w", newline="", encoding="utf-8") as review_file:
        writer = csv.DictWriter(
            review_file,
            fieldnames=[
                "frame",
                "segmentation_label",
                "status",
                "overlapping_track_ids",
                "best_track_id",
                "best_iou",
                "dominance",
                "assigned_track_id",
            ],
        )
        writer.writeheader()
        writer.writerows(all_review_rows)

    report = {
        "segmentation_dir": str(args.segmentation_dir),
        "source_tracking_dir": str(args.tracking_dir),
        "output_dir": str(args.output_dir),
        "assignment_rule": (
            "Assign an existing track ID when the segment and track are "
            "mutual-best overlaps and both configured thresholds pass."
        ),
        "minimum_iou": args.minimum_iou,
        "minimum_dominance": args.minimum_dominance,
        "frames": frame_summaries,
    }
    report_path = args.output_dir / "initialization_report.json"
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Saved tracking draft to {args.output_dir}")
    print(f"Saved manual-review list to {review_path}")


if __name__ == "__main__":
    main()
