"""Export the CLS annotation and one result as a provisional CTC dataset."""

import argparse
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import tifffile


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Export corrected segmentation masks, partial tracking masks, "
            "and an Ultrack result in CTC directory format."
        )
    )
    parser.add_argument("--segmentation-dir", type=Path, required=True)
    parser.add_argument("--tracking-dir", type=Path, required=True)
    parser.add_argument("--result-dir", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--sequence", default="01")
    parser.add_argument("--frames", type=int, default=20)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def _mask_paths(directory: Path, frames: int) -> list[Path]:
    """Return expected mask paths and fail if any are missing."""
    paths = [directory / f"mask{frame:03d}.tif" for frame in range(frames)]
    missing = [path for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing masks: {missing}")
    return paths


def _contiguous_spans(frames: list[int]) -> list[list[int]]:
    """Split sorted frame numbers into contiguous spans."""
    spans = [[frames[0]]]
    for frame in frames[1:]:
        if frame == spans[-1][-1] + 1:
            spans[-1].append(frame)
        else:
            spans.append([frame])
    return spans


def _split_disconnected_track_spans(
    tracking_masks: list[np.ndarray],
) -> tuple[list[np.ndarray], list[dict[str, int]]]:
    """Give each non-contiguous temporal span a valid CTC track ID."""
    exported_masks = [mask.astype(np.uint32, copy=True) for mask in tracking_masks]
    frames_by_track: dict[int, list[int]] = {}
    for frame, mask in enumerate(exported_masks):
        for track_id in np.unique(mask):
            track_id = int(track_id)
            if track_id != 0:
                frames_by_track.setdefault(track_id, []).append(frame)

    next_track_id = max(frames_by_track, default=0) + 1
    split_records = []
    for track_id, frames in sorted(frames_by_track.items()):
        spans = _contiguous_spans(frames)
        for span in spans[1:]:
            new_track_id = next_track_id
            next_track_id += 1
            for frame in span:
                exported_masks[frame][
                    exported_masks[frame] == track_id
                ] = new_track_id
            split_records.append(
                {
                    "source_track_id": track_id,
                    "exported_track_id": new_track_id,
                    "start_frame": span[0],
                    "end_frame": span[-1],
                }
            )

    return exported_masks, split_records


def _track_rows(tracking_masks: list[np.ndarray]) -> list[tuple[int, int, int, int]]:
    """Derive CTC track spans with unknown parents recorded as zero."""
    frames_by_track: dict[int, list[int]] = {}
    for frame, mask in enumerate(tracking_masks):
        for track_id in np.unique(mask):
            track_id = int(track_id)
            if track_id != 0:
                frames_by_track.setdefault(track_id, []).append(frame)

    rows = []
    for track_id, frames in sorted(frames_by_track.items()):
        expected = list(range(min(frames), max(frames) + 1))
        if frames != expected:
            raise ValueError(
                f"Track {track_id} is not temporally contiguous: {frames}"
            )
        rows.append((track_id, min(frames), max(frames), 0))
    return rows


def _prepare_output(output_root: Path, overwrite: bool) -> None:
    """Create an empty output root without deleting unrelated files."""
    if output_root.exists() and any(output_root.iterdir()):
        if not overwrite:
            raise FileExistsError(
                f"Output root is not empty: {output_root}. "
                "Pass --overwrite to replace known export files."
            )
        for pattern in (
            "*_GT/SEG/man_seg*.tif",
            "*_GT/TRA/man_track*.tif",
            "*_GT/TRA/man_track.txt",
            "*_RES/mask*.tif",
            "*_RES/res_track.txt",
            "provisional_ctc_export.json",
        ):
            for path in output_root.glob(pattern):
                path.unlink()
    output_root.mkdir(parents=True, exist_ok=True)


def main() -> None:
    """Create the provisional CTC ground truth and result directories."""
    args = parse_args()
    if args.frames <= 0:
        raise ValueError("--frames must be greater than zero.")
    if not args.sequence.isdigit():
        raise ValueError("--sequence must contain only digits, such as 01.")

    segmentation_paths = _mask_paths(args.segmentation_dir, args.frames)
    tracking_paths = _mask_paths(args.tracking_dir, args.frames)
    result_paths = _mask_paths(args.result_dir, args.frames)
    result_track_path = args.result_dir / "res_track.txt"
    if not result_track_path.is_file():
        raise FileNotFoundError(
            f"Missing result track file: {result_track_path}"
        )

    segmentation_masks = [
        tifffile.imread(path) for path in segmentation_paths
    ]
    tracking_masks = [tifffile.imread(path) for path in tracking_paths]
    expected_shape = segmentation_masks[0].shape
    for frame, (segmentation, tracking) in enumerate(
        zip(segmentation_masks, tracking_masks)
    ):
        if segmentation.shape != expected_shape or tracking.shape != expected_shape:
            raise ValueError(
                f"Unexpected shape in frame {frame}: "
                f"{segmentation.shape} and {tracking.shape}."
            )
        if np.any((tracking != 0) & (segmentation == 0)):
            raise ValueError(
                f"Tracking pixels extend outside segmentation in frame {frame}."
            )

    exported_tracking, split_records = _split_disconnected_track_spans(
        tracking_masks
    )
    track_rows = _track_rows(exported_tracking)

    _prepare_output(args.output_root, args.overwrite)
    ground_truth_dir = args.output_root / f"{args.sequence}_GT"
    segmentation_output_dir = ground_truth_dir / "SEG"
    tracking_output_dir = ground_truth_dir / "TRA"
    result_output_dir = args.output_root / f"{args.sequence}_RES"
    segmentation_output_dir.mkdir(parents=True, exist_ok=True)
    tracking_output_dir.mkdir(parents=True, exist_ok=True)
    result_output_dir.mkdir(parents=True, exist_ok=True)

    for frame, (segmentation, tracking, result_path) in enumerate(
        zip(segmentation_masks, exported_tracking, result_paths)
    ):
        tifffile.imwrite(
            segmentation_output_dir / f"man_seg{frame:03d}.tif",
            segmentation.astype(np.uint16),
        )
        tifffile.imwrite(
            tracking_output_dir / f"man_track{frame:03d}.tif",
            tracking.astype(np.uint16),
        )
        shutil.copy2(result_path, result_output_dir / result_path.name)

    ground_truth_track_path = tracking_output_dir / "man_track.txt"
    ground_truth_track_path.write_text(
        "".join(
            f"{track_id} {start} {end} {parent}\n"
            for track_id, start, end, parent in track_rows
        ),
        encoding="utf-8",
    )
    shutil.copy2(result_track_path, result_output_dir / "res_track.txt")

    unassigned_instances = 0
    total_instances = 0
    for segmentation, tracking in zip(segmentation_masks, tracking_masks):
        for segment_id in np.unique(segmentation):
            if segment_id == 0:
                continue
            total_instances += 1
            if not np.any(tracking[segmentation == segment_id]):
                unassigned_instances += 1

    report = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "provisional": True,
        "sequence": args.sequence,
        "frames": args.frames,
        "shape": list(expected_shape),
        "segmentation_instances": total_instances,
        "unassigned_tracking_instances": unassigned_instances,
        "tracking_coverage": 1 - unassigned_instances / total_instances,
        "exported_tracks": len(track_rows),
        "split_non_contiguous_spans": split_records,
        "lineage_policy": (
            "All ground-truth parent IDs are zero because divisions have not "
            "been manually validated."
        ),
        "limitations": [
            "Tracking ground truth omits unresolved frame-level instances.",
            "Division parent-child relationships are not annotated.",
            "The reference was initialized from an Ultrack max-distance-50 run.",
        ],
    }
    report_path = args.output_root / "provisional_ctc_export.json"
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Ground truth: {ground_truth_dir}")
    print(f"Result: {result_output_dir}")
    print(f"Track rows: {len(track_rows)}")
    print(f"Split temporal spans: {len(split_records)}")
    print(f"Unassigned instances: {unassigned_instances}/{total_instances}")
    print(f"Export report: {report_path}")


if __name__ == "__main__":
    main()
