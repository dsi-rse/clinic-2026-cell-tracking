"""Run 2D parameter experiments one stage at a time in the active environment."""

import argparse
import json
from pathlib import Path

from cell_tracking.segmentation_parameters import (
    inspect_cellpose,
    load_plan,
    run_stage,
    summarize,
)


def create_plan(ctc_root: Path, run_root: Path, destination: Path) -> None:
    """Write editable experiments for both datasets, sequences, and input methods."""
    experiments = []
    for prefix, dataset in [("hela", "Fluo-N2DL-HeLa"), ("gowt1", "Fluo-N2DH-GOWT1")]:
        for sequence in ["01", "02"]:
            base = {
                "dataset": dataset,
                "sequence": sequence,
                "raw_dir": str(ctc_root / dataset / sequence),
                "ground_truth_dir": str(ctc_root / dataset / f"{sequence}_GT"),
            }
            sources = {
                method: str(
                    run_root / f"{prefix}-seq{sequence}-full-{method}" / "input_labels"
                )
                for method in ["cellpose", "stardist", "watershed"]
            }
            for method in ["cellpose", "stardist", "watershed", "ensemble"]:
                labels = sources if method == "ensemble" else {method: sources[method]}
                for sigma in [4, 2, 0]:
                    experiments.append(
                        {
                            **base,
                            "method": method,
                            "label_dirs": labels,
                            "contour_sigma": sigma,
                            "id": f"{prefix}-{sequence}-{method}-contour-{sigma}",
                        }
                    )
            for sigma in [4, 2, 0]:
                experiments.append(
                    {
                        **base,
                        "method": "holefilled",
                        "contour_sigma": sigma,
                        "label_dirs": {
                            "holefilled": f"@{prefix}-{sequence}-holefilled-image-1"
                        },
                        "id": f"{prefix}-{sequence}-holefilled-contour-{sigma}",
                    }
                )
            # Generate these even for HeLa: no existing hole-filled run is assumed.
            for method in ["watershed", "holefilled"]:
                for sigma in [1, 0.5, 0]:
                    experiments.append(
                        {
                            **base,
                            "method": method,
                            "image_sigma": sigma,
                            "fill_holes": method == "holefilled",
                            "contour_sigma": 4,
                            "id": f"{prefix}-{sequence}-{method}-image-{str(sigma).replace('.', 'p')}",
                        }
                    )
            for parameter, values in [
                ("baseline", [None]),
                ("prob_thresh", [0.4, 0.6]),
                ("nms_thresh", [0.2, 0.4]),
            ]:
                for value in values:
                    entry = {
                        **base,
                        "method": "stardist",
                        "contour_sigma": 4,
                        "id": f"{prefix}-{sequence}-stardist-{parameter}-{str(value).replace('.', 'p')}",
                    }
                    if value is not None:
                        entry[parameter] = value
                    experiments.append(entry)
    if destination.exists():
        raise FileExistsError(f"Plan already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({"experiments": experiments}, indent=2) + "\n")


def main() -> None:
    """Select explicit experiment ids and execute or summarize one stage."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stage",
        choices=[
            "plan",
            "generate",
            "track",
            "evaluate",
            "summary",
            "inspect-cellpose",
        ],
    )
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument(
        "--ids", nargs="+", help="Explicit experiment ids; no implicit expensive sweep."
    )
    parser.add_argument(
        "--config", type=Path, help="Ultrack TOML matching the baseline."
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--ctc-root", type=Path)
    parser.add_argument("--baseline-run-root", type=Path)
    args = parser.parse_args()
    if args.stage == "plan":
        if not all([args.plan, args.ctc_root, args.baseline_run_root]):
            parser.error("plan requires --plan, --ctc-root, and --baseline-run-root")
        create_plan(args.ctc_root, args.baseline_run_root, args.plan)
        return
    if args.output_root is None:
        parser.error("--output-root is required")
    if args.num_workers < 1:
        parser.error("--num-workers must be positive")
    if args.stage == "inspect-cellpose":
        inspect_cellpose(args.output_root / "cellpose_threshold_inspection.json")
        return
    if args.stage == "summary":
        summarize(args.output_root)
        return
    if not args.plan or not args.ids:
        parser.error("Select --plan and --ids explicitly")
    experiments = load_plan(args.plan)
    by_id = {experiment["id"]: experiment for experiment in experiments}
    unknown = set(args.ids) - by_id.keys()
    if unknown:
        parser.error(f"Unknown ids: {sorted(unknown)}")
    failures = []
    for name in dict.fromkeys(args.ids):
        try:
            run_stage(
                by_id[name],
                args.stage,
                args.output_root,
                args.resume,
                args.config,
                args.num_workers,
            )
        except Exception as error:
            print(f"FAILED {name}: {error}", flush=True)
            failures.append(name)
    summarize(args.output_root)
    if failures:
        raise SystemExit(f"Failed experiments: {', '.join(failures)}")


if __name__ == "__main__":
    main()
