"""Evaluate an Ultrack result against the reviewed CLS annotation subset."""

import argparse
import csv
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import tifffile
from scipy.optimize import linear_sum_assignment


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Calculate provisional segmentation and identity metrics while "
            "excluding unassigned reference nuclei. These are not official "
            "CTC DET, SEG, or TRA scores."
        )
    )
    parser.add_argument("--segmentation-dir", type=Path, required=True)
    parser.add_argument("--tracking-reference-dir", type=Path, required=True)
    parser.add_argument("--result-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--frames", type=int, default=20)
    parser.add_argument("--iou-threshold", type=float, default=0.5)
    parser.add_argument(
        "--ambiguous-overlap-threshold",
        type=float,
        default=0.5,
        help=(
            "Ignore an unmatched prediction when at least this fraction of "
            "its pixels overlap an unassigned reference nucleus."
        ),
    )
    return parser.parse_args()


def _paths(directory: Path, prefix: str, frames: int) -> list[Path]:
    """Return expected frame paths and fail if any are missing."""
    paths = [directory / f"{prefix}{frame:03d}.tif" for frame in range(frames)]
    missing = [path for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing input masks: {missing}")
    return paths


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    """Return a ratio, or zero when the denominator is zero."""
    return float(numerator / denominator) if denominator else 0.0


def _match_frame(
    reference: np.ndarray,
    prediction: np.ndarray,
    unassigned_mask: np.ndarray,
    iou_threshold: float,
    ambiguous_overlap_threshold: float,
) -> tuple[list[dict[str, int | float]], dict[str, int | float], set[int]]:
    """Match one frame of reviewed reference and predicted objects."""
    if reference.shape != prediction.shape:
        raise ValueError(
            "Reference and prediction shapes differ: "
            f"{reference.shape} and {prediction.shape}."
        )

    reference_ids, reference_inverse = np.unique(
        reference,
        return_inverse=True,
    )
    prediction_ids, prediction_inverse = np.unique(
        prediction,
        return_inverse=True,
    )
    overlap_counts = np.bincount(
        reference_inverse.ravel() * len(prediction_ids)
        + prediction_inverse.ravel(),
        minlength=len(reference_ids) * len(prediction_ids),
    ).reshape(len(reference_ids), len(prediction_ids))

    reference_areas = overlap_counts.sum(axis=1)
    prediction_areas = overlap_counts.sum(axis=0)
    intersections = overlap_counts[1:, 1:]
    unions = (
        reference_areas[1:, None]
        + prediction_areas[None, 1:]
        - intersections
    )
    ious = np.divide(
        intersections,
        unions,
        out=np.zeros_like(intersections, dtype=float),
        where=unions != 0,
    )

    matches = []
    matched_prediction_indices = set()
    if ious.size:
        reference_indices, prediction_indices = linear_sum_assignment(-ious)
        for reference_index, prediction_index in zip(
            reference_indices,
            prediction_indices,
        ):
            iou = float(ious[reference_index, prediction_index])
            if iou < iou_threshold:
                continue
            matched_prediction_indices.add(int(prediction_index))
            matches.append(
                {
                    "reference_id": int(reference_ids[reference_index + 1]),
                    "prediction_id": int(prediction_ids[prediction_index + 1]),
                    "iou": iou,
                }
            )

    unmatched_prediction_indices = set(range(len(prediction_ids) - 1))
    unmatched_prediction_indices -= matched_prediction_indices
    ambiguous_counts = np.bincount(
        prediction_inverse.ravel(),
        weights=unassigned_mask.ravel().astype(np.uint8),
        minlength=len(prediction_ids),
    )
    ignored_prediction_indices = {
        prediction_index
        for prediction_index in unmatched_prediction_indices
        if _safe_ratio(
            ambiguous_counts[prediction_index + 1],
            prediction_areas[prediction_index + 1],
        )
        >= ambiguous_overlap_threshold
    }

    reference_count = len(reference_ids) - 1
    prediction_count = len(prediction_ids) - 1
    matched_count = len(matches)
    ignored_count = len(ignored_prediction_indices)
    false_positive_count = prediction_count - matched_count - ignored_count
    false_negative_count = reference_count - matched_count

    metrics = {
        "reference_objects": reference_count,
        "predicted_objects": prediction_count,
        "matched_objects": matched_count,
        "ignored_predictions": ignored_count,
        "false_positives": false_positive_count,
        "false_negatives": false_negative_count,
        "matched_iou_sum": sum(match["iou"] for match in matches),
    }
    present_reference_ids = {int(reference_id) for reference_id in reference_ids[1:]}
    return matches, metrics, present_reference_ids


def _identity_metrics(
    matches_by_frame: list[list[dict[str, int | float]]],
    reference_detections: int,
    evaluated_prediction_detections: int,
) -> dict[str, int | float]:
    """Calculate provisional identity precision, recall, and F1."""
    pair_counts: dict[tuple[int, int], int] = defaultdict(int)
    for frame_matches in matches_by_frame:
        for match in frame_matches:
            pair = (
                int(match["reference_id"]),
                int(match["prediction_id"]),
            )
            pair_counts[pair] += 1

    reference_ids = sorted({pair[0] for pair in pair_counts})
    prediction_ids = sorted({pair[1] for pair in pair_counts})
    identity_true_positives = 0
    if reference_ids and prediction_ids:
        reference_index = {
            reference_id: index
            for index, reference_id in enumerate(reference_ids)
        }
        prediction_index = {
            prediction_id: index
            for index, prediction_id in enumerate(prediction_ids)
        }
        counts = np.zeros(
            (len(reference_ids), len(prediction_ids)),
            dtype=int,
        )
        for (reference_id, prediction_id), count in pair_counts.items():
            counts[
                reference_index[reference_id],
                prediction_index[prediction_id],
            ] = count
        rows, columns = linear_sum_assignment(-counts)
        identity_true_positives = int(counts[rows, columns].sum())

    identity_false_negatives = reference_detections - identity_true_positives
    identity_false_positives = (
        evaluated_prediction_detections - identity_true_positives
    )
    identity_precision = _safe_ratio(
        identity_true_positives,
        identity_true_positives + identity_false_positives,
    )
    identity_recall = _safe_ratio(
        identity_true_positives,
        identity_true_positives + identity_false_negatives,
    )
    identity_f1 = _safe_ratio(
        2 * identity_precision * identity_recall,
        identity_precision + identity_recall,
    )
    return {
        "identity_true_positives": identity_true_positives,
        "identity_false_positives": identity_false_positives,
        "identity_false_negatives": identity_false_negatives,
        "identity_precision": identity_precision,
        "identity_recall": identity_recall,
        "identity_f1": identity_f1,
    }


def _link_metrics(
    matches_by_frame: list[list[dict[str, int | float]]],
    reference_ids_by_frame: list[set[int]],
) -> dict[str, int | float]:
    """Measure same-ID links across consecutive frames, excluding lineage."""
    match_maps = [
        {
            int(match["reference_id"]): int(match["prediction_id"])
            for match in frame_matches
        }
        for frame_matches in matches_by_frame
    ]
    reference_links = 0
    evaluable_links = 0
    correct_links = 0
    identity_switches = 0

    for frame in range(len(reference_ids_by_frame) - 1):
        continuing_ids = (
            reference_ids_by_frame[frame]
            & reference_ids_by_frame[frame + 1]
        )
        reference_links += len(continuing_ids)
        for reference_id in continuing_ids:
            first_prediction = match_maps[frame].get(reference_id)
            second_prediction = match_maps[frame + 1].get(reference_id)
            if first_prediction is None or second_prediction is None:
                continue
            evaluable_links += 1
            if first_prediction == second_prediction:
                correct_links += 1
            else:
                identity_switches += 1

    return {
        "reference_consecutive_links": reference_links,
        "evaluable_consecutive_links": evaluable_links,
        "correct_consecutive_links": correct_links,
        "identity_switches": identity_switches,
        "consecutive_link_recall": _safe_ratio(
            correct_links,
            reference_links,
        ),
        "matched_link_accuracy": _safe_ratio(
            correct_links,
            evaluable_links,
        ),
    }


def evaluate(args: argparse.Namespace) -> tuple[dict[str, object], list[dict[str, object]]]:
    """Evaluate all frames and return a report and per-frame rows."""
    if args.frames <= 0:
        raise ValueError("--frames must be greater than zero.")
    for name, value in (
        ("--iou-threshold", args.iou_threshold),
        ("--ambiguous-overlap-threshold", args.ambiguous_overlap_threshold),
    ):
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be between zero and one.")

    segmentation_paths = _paths(args.segmentation_dir, "mask", args.frames)
    reference_paths = _paths(
        args.tracking_reference_dir,
        "mask",
        args.frames,
    )
    prediction_paths = _paths(args.result_dir, "mask", args.frames)

    frame_rows = []
    matches_by_frame = []
    reference_ids_by_frame = []
    total_segmentation_objects = 0
    total_unassigned_objects = 0

    for frame, paths in enumerate(
        zip(segmentation_paths, reference_paths, prediction_paths)
    ):
        segmentation = tifffile.imread(paths[0])
        reference = tifffile.imread(paths[1])
        prediction = tifffile.imread(paths[2])
        if not (
            segmentation.shape == reference.shape == prediction.shape
        ):
            raise ValueError(
                f"Frame {frame} shapes differ: {segmentation.shape}, "
                f"{reference.shape}, and {prediction.shape}."
            )

        segmentation_ids = [
            segment_id
            for segment_id in np.unique(segmentation)
            if segment_id != 0
        ]
        unassigned_mask = (segmentation != 0) & (reference == 0)
        unassigned_ids = [
            segment_id
            for segment_id in np.unique(segmentation[unassigned_mask])
            if segment_id != 0
        ]
        total_segmentation_objects += len(segmentation_ids)
        total_unassigned_objects += len(unassigned_ids)

        matches, frame_metrics, present_reference_ids = _match_frame(
            reference,
            prediction,
            unassigned_mask,
            args.iou_threshold,
            args.ambiguous_overlap_threshold,
        )
        matches_by_frame.append(matches)
        reference_ids_by_frame.append(present_reference_ids)
        frame_rows.append(
            {
                "frame": frame,
                "segmentation_objects": len(segmentation_ids),
                "unassigned_objects": len(unassigned_ids),
                **frame_metrics,
            }
        )

    totals = {
        key: sum(row[key] for row in frame_rows)
        for key in (
            "reference_objects",
            "predicted_objects",
            "matched_objects",
            "ignored_predictions",
            "false_positives",
            "false_negatives",
            "matched_iou_sum",
        )
    }
    evaluated_predictions = (
        totals["predicted_objects"] - totals["ignored_predictions"]
    )
    detection_precision = _safe_ratio(
        totals["matched_objects"],
        totals["matched_objects"] + totals["false_positives"],
    )
    detection_recall = _safe_ratio(
        totals["matched_objects"],
        totals["reference_objects"],
    )
    detection_f1 = _safe_ratio(
        2 * detection_precision * detection_recall,
        detection_precision + detection_recall,
    )

    identity = _identity_metrics(
        matches_by_frame,
        int(totals["reference_objects"]),
        int(evaluated_predictions),
    )
    links = _link_metrics(matches_by_frame, reference_ids_by_frame)
    metrics = {
        "annotation_coverage": _safe_ratio(
            totals["reference_objects"],
            total_segmentation_objects,
        ),
        "segmentation_objects": total_segmentation_objects,
        "reviewed_reference_detections": totals["reference_objects"],
        "unassigned_reference_detections": total_unassigned_objects,
        "predicted_detections": totals["predicted_objects"],
        "ignored_predictions": totals["ignored_predictions"],
        "matched_detections": totals["matched_objects"],
        "false_positives": totals["false_positives"],
        "false_negatives": totals["false_negatives"],
        "detection_precision": detection_precision,
        "detection_recall": detection_recall,
        "detection_f1": detection_f1,
        "mean_matched_iou": _safe_ratio(
            totals["matched_iou_sum"],
            totals["matched_objects"],
        ),
        "reference_averaged_iou": _safe_ratio(
            totals["matched_iou_sum"],
            totals["reference_objects"],
        ),
        **identity,
        **links,
    }
    report = {
        "metadata": {
            "evaluated_at_utc": datetime.now(UTC).isoformat(),
            "run_name": args.run_name,
            "segmentation_dir": str(args.segmentation_dir.resolve()),
            "tracking_reference_dir": str(
                args.tracking_reference_dir.resolve()
            ),
            "result_dir": str(args.result_dir.resolve()),
            "frames": args.frames,
            "iou_threshold": args.iou_threshold,
            "ambiguous_overlap_threshold": (
                args.ambiguous_overlap_threshold
            ),
        },
        "metrics": metrics,
        "limitations": [
            "These are provisional reviewed-subset metrics, not official CTC scores.",
            "Unassigned reference nuclei and predictions centered on them are excluded.",
            "Division parent-child relationships are not evaluated.",
            "The tracking reference was initialized from the max-distance-50 run.",
        ],
    }
    return report, frame_rows


def write_outputs(
    report: dict[str, object],
    frame_rows: list[dict[str, object]],
    output_dir: Path,
) -> None:
    """Write JSON summary and per-frame CSV outputs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "reviewed_subset_metrics.json"
    csv_path = output_dir / "reviewed_subset_frames.csv"
    json_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    with csv_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=frame_rows[0].keys())
        writer.writeheader()
        writer.writerows(frame_rows)
    print(f"Saved {json_path}")
    print(f"Saved {csv_path}")


def print_summary(report: dict[str, object]) -> None:
    """Print the main provisional metrics."""
    metadata = report["metadata"]
    metrics = report["metrics"]
    print(f"\nProvisional reviewed-subset metrics: {metadata['run_name']}")
    for name in (
        "annotation_coverage",
        "detection_f1",
        "reference_averaged_iou",
        "identity_f1",
        "consecutive_link_recall",
        "matched_link_accuracy",
    ):
        print(f"  {name}: {metrics[name]:.6f}")


def main() -> None:
    """Evaluate and save provisional reviewed-subset metrics."""
    args = parse_args()
    report, frame_rows = evaluate(args)
    write_outputs(report, frame_rows, args.output_dir)
    print_summary(report)


if __name__ == "__main__":
    main()
