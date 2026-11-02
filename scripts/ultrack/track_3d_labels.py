"""Track saved 3D masks with Ultrack without rerunning Cellpose."""

import argparse
import hashlib
import json
import math
import time
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Read paths, explicit Ultrack configuration, and spatial settings."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Complete raw sequence containing tNNN.tif.",
    )
    parser.add_argument(
        "--label-dir",
        type=Path,
        required=True,
        help="Saved maskNNN.tif volumes, e.g. Cellpose output.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Ultrack TOML; use the baseline configuration for comparison.",
    )
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--sequence", choices=["01", "02"], required=True)
    parser.add_argument(
        "--scale",
        type=float,
        nargs=3,
        required=True,
        metavar=("Z", "Y", "X"),
        help="Spatial scale for linking; match baseline units.",
    )
    parser.add_argument(
        "--contour-sigma",
        type=float,
        nargs=3,
        default=[0.0, 0.0, 0.0],
        metavar=("Z", "Y", "X"),
    )
    parser.add_argument(
        "--frame-stop", type=int, help="Exclusive end, for pilot tracking."
    )
    args = parser.parse_args()
    if any(not math.isfinite(v) or v <= 0 for v in args.scale):
        parser.error("Scale values must be finite and positive.")
    if any(not math.isfinite(v) or v < 0 for v in args.contour_sigma):
        parser.error("Contour sigma values must be finite and nonnegative.")
    return args


def main() -> None:
    """Validate saved masks, track, export, and preserve configuration and errors."""
    args = parse_args()
    from ultrack import load_config

    from cell_tracking.ultrack_labels import prepare_label_series, track_label_series

    config_text = args.config.read_text()
    config = load_config(args.config)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise FileExistsError("Choose a new or empty tracking output directory.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    config.data_config.working_dir = args.output_dir.resolve()
    (args.output_dir / "source_config.toml").write_text(config_text)
    # Record the actual config, including the new working directory and defaults.
    (args.output_dir / "effective_config.json").write_text(
        config.model_dump_json(indent=2)
    )
    source_report = args.label_dir / "run.json"
    report = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": "running",
        "arguments": {
            k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()
        },
        "config_sha256": hashlib.sha256(config_text.encode()).hexdigest(),
        "versions": {name: version(name) for name in ["ultrack", "numpy", "tifffile"]},
        "segmentation_run": json.loads(source_report.read_text())
        if source_report.exists()
        else None,
    }
    started = time.perf_counter()
    record = args.output_dir / "run_report.json"
    try:
        record.write_text(json.dumps(report, indent=2) + "\n")
        labels, frames, complete = prepare_label_series(
            args.input_dir,
            args.label_dir,
            args.output_dir / "labels.npy",
            args.frame_stop,
        )
        report.update(
            frame_numbers=frames,
            complete_sequence=complete,
            shape_tzyx=list(labels.shape),
        )
        print(
            f"Tracking {len(frames)} frames; complete sequence: {complete}", flush=True
        )
        tracker, summary = track_label_series(
            labels, config, args.output_dir, args.scale, args.contour_sigma
        )
        result_dir = args.output_dir / (
            f"{args.sequence}_RES" if complete else "subset_RES"
        )
        tracker.to_ctc(result_dir)
        report.update(
            status="complete",
            tracking_summary=summary,
            ctc_result_dir=str(result_dir.resolve()),
        )
        print(f"CTC result: {result_dir}", flush=True)
    except Exception as error:
        report.update(status="failed", blocker=f"{type(error).__name__}: {error}")
        raise
    finally:
        report["seconds"] = time.perf_counter() - started
        record.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
