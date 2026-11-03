"""Validate and evaluate one complete result sequence in CTC format."""

import argparse
import csv
import json
import re
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from cell_tracking.ctc_io import extract_frame_number

RESULT_DIRECTORY_PATTERN = re.compile(r"^(?P<sequence>\d+)_RES$")
REPORTED_METRICS = ("Valid", "DET", "SEG", "TRA", "OP_CTB")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Validate a complete CTC result sequence and calculate DET, SEG, "
            "TRA, and OP_CTB with py-ctcmetrics."
        )
    )
    parser.add_argument(
        "--ground-truth-dir",
        type=Path,
        required=True,
        help="CTC ground-truth directory, such as Fluo-N2DL-HeLa/01_GT.",
    )
    parser.add_argument(
        "--result-dir",
        type=Path,
        required=True,
        help="Complete CTC result directory, such as 01_RES.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help=(
            "Directory for ctc_metrics.json and ctc_metrics.csv. The default "
            "is <result parent>/evaluation/<result name>."
        ),
    )
    parser.add_argument(
        "--dataset",
        default="unknown",
        help="Dataset name to record in the evaluation files.",
    )
    parser.add_argument(
        "--method",
        default="unknown",
        help="Method or experiment name to record in the evaluation files.",
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        default=1,
        help="Number of py-ctcmetrics worker processes. Default: 1.",
    )
    parser.add_argument(
        "--published-seg",
        type=float,
        help="Optional published SEG value for comparison.",
    )
    parser.add_argument(
        "--published-tra",
        type=float,
        help="Optional published TRA value for comparison.",
    )
    parser.add_argument(
        "--published-ctb",
        type=float,
        help="Optional published CTB value for comparison.",
    )
    return parser.parse_args()


def validate_directory_structure(
    ground_truth_dir: Path,
    result_dir: Path,
) -> tuple[str, int, int]:
    """Check paths, sequence names, and full-frame alignment before scoring."""
    if not ground_truth_dir.is_dir():
        raise FileNotFoundError(
            f"Ground-truth directory does not exist: {ground_truth_dir}"
        )
    if not result_dir.is_dir():
        raise FileNotFoundError(f"Result directory does not exist: {result_dir}")

    result_name_match = RESULT_DIRECTORY_PATTERN.fullmatch(result_dir.name)
    if result_name_match is None:
        raise ValueError(
            f"Expected a complete result directory named like 01_RES, got "
            f"{result_dir.name!r}. Subset results must not be benchmarked."
        )

    sequence = result_name_match.group("sequence")
    expected_ground_truth_name = f"{sequence}_GT"
    if ground_truth_dir.name != expected_ground_truth_name:
        raise ValueError(
            f"Result {result_dir.name} must be compared with "
            f"{expected_ground_truth_name}, not {ground_truth_dir.name}."
        )

    track_file = result_dir / "res_track.txt"
    if not track_file.is_file():
        raise FileNotFoundError(f"Missing CTC track file: {track_file}")

    result_masks = sorted(result_dir.glob("mask*.tif"))
    tracking_masks = sorted((ground_truth_dir / "TRA").glob("man_track*.tif"))
    segmentation_masks = sorted((ground_truth_dir / "SEG").glob("man_seg*.tif"))

    if not result_masks:
        raise ValueError(f"No mask*.tif files found in {result_dir}.")
    if not tracking_masks:
        raise ValueError(f"No tracking masks found in {ground_truth_dir / 'TRA'}.")
    if not segmentation_masks:
        raise ValueError(f"No segmentation masks found in {ground_truth_dir / 'SEG'}.")

    result_frames = [extract_frame_number(path) for path in result_masks]
    tracking_frames = [extract_frame_number(path) for path in tracking_masks]
    if result_frames != tracking_frames:
        raise ValueError(
            "Result frames do not match the complete tracking ground truth. "
            f"Found {len(result_frames)} result masks and "
            f"{len(tracking_frames)} ground-truth tracking masks."
        )

    return sequence, len(result_masks), len(segmentation_masks)


def import_ctc_metrics() -> tuple[Any, Any, str]:
    """Import py-ctcmetrics with an actionable installation error."""
    try:
        from ctc_metrics import evaluate_sequence, validate_sequence
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            "py-ctcmetrics is required. Install it with: "
            "python -m pip install py-ctcmetrics==1.3.3"
        ) from error

    try:
        package_version = version("py-ctcmetrics")
    except PackageNotFoundError:
        package_version = "unknown"

    return evaluate_sequence, validate_sequence, package_version


def convert_to_builtin(value: Any) -> Any:
    """Convert NumPy scalar-like values into JSON-compatible Python values."""
    if hasattr(value, "item"):
        return value.item()
    return value


def build_published_reference(args: argparse.Namespace) -> dict[str, float]:
    """Collect optional published benchmark values from the arguments."""
    published = {}
    if args.published_seg is not None:
        published["SEG"] = args.published_seg
    if args.published_tra is not None:
        published["TRA"] = args.published_tra
    if args.published_ctb is not None:
        published["OP_CTB"] = args.published_ctb
    elif "SEG" in published and "TRA" in published:
        published["OP_CTB"] = (published["SEG"] + published["TRA"]) / 2
    return published


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    """Validate the CTC result and calculate the requested benchmark metrics."""
    if args.num_workers < 1:
        raise ValueError("--num-workers must be at least 1.")

    sequence, result_mask_count, gold_segmentation_count = validate_directory_structure(
        args.ground_truth_dir, args.result_dir
    )
    evaluate_sequence, validate_sequence, package_version = import_ctc_metrics()

    validation = validate_sequence(
        str(args.result_dir),
        threads=args.num_workers,
    )
    if not bool(validation.get("Valid")):
        raise ValueError("py-ctcmetrics reported that the CTC result is invalid.")

    raw_metrics = evaluate_sequence(
        str(args.result_dir),
        str(args.ground_truth_dir),
        metrics=["Valid", "DET", "SEG", "TRA"],
        threads=args.num_workers,
    )
    reproduced = {
        key: convert_to_builtin(value)
        for key, value in raw_metrics.items()
        if value is not None
    }

    if "OP_CTB" not in reproduced:
        reproduced["OP_CTB"] = (reproduced["SEG"] + reproduced["TRA"]) / 2

    published = build_published_reference(args)
    differences = {
        metric: reproduced[metric] - published_value
        for metric, published_value in published.items()
        if metric in reproduced
    }

    return {
        "metadata": {
            "evaluated_at_utc": datetime.now(UTC).isoformat(),
            "dataset": args.dataset,
            "sequence": sequence,
            "method": args.method,
            "ground_truth_dir": str(args.ground_truth_dir.resolve()),
            "result_dir": str(args.result_dir.resolve()),
            "result_mask_count": result_mask_count,
            "gold_segmentation_mask_count": gold_segmentation_count,
            "num_workers": args.num_workers,
            "py_ctcmetrics_version": package_version,
        },
        "reproduced": reproduced,
        "published_reference": published,
        "difference_reproduced_minus_published": differences,
    }


def flatten_report(report: dict[str, Any]) -> dict[str, Any]:
    """Flatten the structured JSON report into one row for CSV output."""
    row = dict(report["metadata"])
    row.update(report["reproduced"])
    row.update(
        {
            f"published_{key}": value
            for key, value in report["published_reference"].items()
        }
    )
    row.update(
        {
            f"difference_{key}": value
            for key, value in report["difference_reproduced_minus_published"].items()
        }
    )
    return row


def write_report(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    """Write the evaluation report as JSON and a one-row CSV file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "ctc_metrics.json"
    csv_path = output_dir / "ctc_metrics.csv"

    with json_path.open("w", encoding="utf-8") as output_file:
        json.dump(report, output_file, indent=2)
        output_file.write("\n")

    row = flatten_report(report)
    with csv_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=row.keys())
        writer.writeheader()
        writer.writerow(row)

    return json_path, csv_path


def print_summary(report: dict[str, Any]) -> None:
    """Print the main reproduced and published metrics."""
    reproduced = report["reproduced"]
    published = report["published_reference"]
    differences = report["difference_reproduced_minus_published"]

    print("\nCTC evaluation summary")
    for metric in REPORTED_METRICS:
        if metric not in reproduced:
            continue
        message = f"  {metric}: {reproduced[metric]:.6f}"
        if metric in published:
            message += (
                f" | published: {published[metric]:.6f}"
                f" | difference: {differences[metric]:+.6f}"
            )
        print(message)


def main() -> None:
    """Run validation, evaluation, reporting, and result comparison."""
    args = parse_args()
    output_dir = args.output_dir
    if output_dir is None:
        output_dir = args.result_dir.parent / "evaluation" / args.result_dir.name

    report = evaluate(args)
    json_path, csv_path = write_report(report, output_dir)
    print_summary(report)
    print(f"\nJSON report: {json_path}")
    print(f"CSV report: {csv_path}")


if __name__ == "__main__":
    main()
