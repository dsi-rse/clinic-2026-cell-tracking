"""Run 2D segmentation-parameter experiments for the Ultrack pipeline.

Used by scripts/ultrack/run_segmentation_parameters.py for HeLa and GOWT1.
Segmentation settings vary while downstream Ultrack tracking settings stay
fixed within each comparison. Each stage uses its active method environment.
"""

import csv
import hashlib
import inspect
import json
import re
import subprocess
import sys
import time
from importlib.metadata import version
from pathlib import Path


def write_json(path: Path, value: dict) -> None:
    """Atomically save a stage record."""
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def load_plan(path: Path) -> list[dict]:
    """Validate experiment identifiers and reject unsupported parameter names."""
    experiments = json.loads(path.read_text())["experiments"]
    seen = set()
    allowed = {
        "id",
        "dataset",
        "sequence",
        "method",
        "raw_dir",
        "label_dirs",
        "ground_truth_dir",
        "contour_sigma",
        "image_sigma",
        "fill_holes",
        "prob_thresh",
        "nms_thresh",
    }
    for experiment in experiments:
        name = experiment["id"]
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", name) or name in seen:
            raise ValueError(f"Duplicate or unsafe experiment id: {name}")
        seen.add(name)
        if set(experiment) - allowed:
            raise ValueError(
                f"Unknown experiment settings: {set(experiment) - allowed}"
            )
        if experiment["method"] not in {
            "cellpose",
            "stardist",
            "watershed",
            "holefilled",
            "ensemble",
        }:
            raise ValueError(f"Unsupported method: {experiment['method']}")
        if experiment["sequence"] not in {"01", "02"}:
            raise ValueError("Sequence must be the string 01 or 02.")
        for key in ("contour_sigma", "image_sigma"):
            value = experiment.get(key, 4 if key == "contour_sigma" else 1)
            if not isinstance(value, int | float) or not 0 <= value < float("inf"):
                raise ValueError(f"Invalid {key}: {value}")
        for key in ("prob_thresh", "nms_thresh"):
            value = experiment.get(key)
            if value is not None and not 0 <= value <= 1:
                raise ValueError(f"Invalid {key}: {value}")
    return experiments


def frame_paths(experiment: dict) -> list[Path]:
    """Require a complete zero-based, consecutive raw sequence."""
    from cell_tracking.ctc_io import extract_frame_number

    paths = sorted(Path(experiment["raw_dir"]).glob("t*.tif"), key=extract_frame_number)
    frames = [extract_frame_number(p, "t") for p in paths]
    if not paths or frames != list(range(len(paths))):
        raise ValueError("Raw frames must start at zero and be consecutive.")
    return paths


def valid_labels(directory: Path, paths: list[Path]) -> bool:
    """Check every saved label's readability, shape, and integer contents."""
    import tifffile

    from cell_tracking.cellpose_resume import read_saved_mask

    for path in paths:
        with tifffile.TiffFile(path) as raw:
            shape = raw.series[0].shape
        if read_saved_mask(directory / f"mask{path.stem[1:]}.tif", shape) is None:
            return False
    return True


def generate_labels(experiment: dict, directory: Path, resume: bool) -> None:
    """Generate watershed or StarDist labels, checkpointing individual frames."""
    import numpy as np
    import tifffile

    from cell_tracking.cellpose_resume import read_saved_mask
    from cell_tracking.ultrack_2d import segment_with_watershed

    method = experiment["method"]
    if method not in {"watershed", "holefilled", "stardist"}:
        raise ValueError(
            "Label generation supports watershed and StarDist; reuse Cellpose masks."
        )
    model = None
    details = {
        "method": method,
        "versions": {
            name: version(name)
            for name in ["numpy", "scipy", "scikit-image", "tifffile", "ultrack"]
        },
    }
    if method == "stardist":
        from stardist.models import StarDist2D

        model = StarDist2D.from_pretrained("2D_versatile_fluo")
        details.update(
            model="2D_versatile_fluo",
            stardist_version=version("stardist"),
            baseline_probability=float(model.thresholds.prob),
            baseline_nms=float(model.thresholds.nms),
            probability=experiment.get("prob_thresh", float(model.thresholds.prob)),
            nms=experiment.get("nms_thresh", float(model.thresholds.nms)),
        )
    directory.mkdir(parents=True, exist_ok=True)
    settings_path = directory / "settings.json"
    settings = {**experiment, **details}
    if settings_path.exists() and json.loads(settings_path.read_text()) != settings:
        raise ValueError(
            "Generation environment or model defaults changed; use a new id."
        )
    write_json(settings_path, settings)
    for path in frame_paths(experiment):
        image = tifffile.imread(path)
        expected_dimensions = 2
        if image.ndim != expected_dimensions:
            raise ValueError(f"Expected YX image, got {image.shape}")
        output = directory / f"mask{path.stem[1:]}.tif"
        if resume and read_saved_mask(output, image.shape) is not None:
            print(f"Skipping saved {output.name}", flush=True)
            continue
        if model is None:
            labels = segment_with_watershed(
                image[np.newaxis],
                experiment.get("image_sigma", 1),
                2,
                20,
                fill_holes=experiment.get("fill_holes", method == "holefilled"),
            )[0]
        else:
            from ultrack.imgproc import normalize

            labels, _ = model.predict_instances_big(
                normalize(image, gamma=1.0),
                axes="YX",
                block_size=560,
                min_overlap=96,
                show_progress=False,
                prob_thresh=details["probability"],
                nms_thresh=details["nms"],
            )
        temporary = output.with_suffix(".tif.tmp")
        tifffile.imwrite(temporary, labels.astype(np.uint32))
        temporary.replace(output)
        print(f"Saved {output}", flush=True)


def run_tracking(
    experiment: dict, labels: dict, attempt: Path, config_path: Path
) -> Path:
    """Reuse foreground-OR/contour-mean conversion and Ultrack's existing API."""
    import tifffile
    from ultrack import Tracker, load_config

    from cell_tracking.ultrack_2d import combine_label_stacks

    paths = frame_paths(experiment)
    with tifffile.TiffFile(paths[0]) as raw:
        shape = (len(paths), *raw.series[0].shape)
    foreground, contours, counts = combine_label_stacks(
        {k: Path(v) for k, v in labels.items()},
        list(range(len(paths))),
        shape,
        experiment.get("contour_sigma", 4),
    )
    config = load_config(config_path)
    config.data_config.working_dir = attempt.resolve()
    write_json(
        attempt / "input_summary.json",
        {"label_counts": counts, "experiment": experiment},
    )
    (attempt / "effective_config.json").write_text(config.model_dump_json(indent=2))
    tracker = Tracker(config=config)
    tracker.segment(foreground=foreground, contours=contours)
    tracker.link()
    tracker.solve()
    tracks, _ = tracker.to_tracks_layer()
    tracks.to_csv(attempt / "tracks.csv", index=False)
    result = attempt / f"{experiment['sequence']}_RES"
    tracker.to_ctc(result)
    return result


def run_stage(
    experiment: dict,
    stage: str,
    root: Path,
    resume: bool,
    config_path: Path | None,
    workers: int,
) -> None:
    """Run a stage, preserving finished work and isolating tracking retries."""
    directory = root / experiment["id"]
    directory.mkdir(parents=True, exist_ok=True)
    spec_path = directory / "experiment.json"
    if spec_path.exists() and json.loads(spec_path.read_text()) != experiment:
        raise ValueError("Experiment settings changed: use a new experiment id.")
    write_json(spec_path, experiment)
    paths = frame_paths(experiment)
    generated = directory / "labels"
    labels = experiment.get("label_dirs") or {experiment["method"]: str(generated)}
    labels = {
        key: str(root / value[1:] / "labels") if value.startswith("@") else value
        for key, value in labels.items()
    }
    marker = directory / f"{stage}.json"
    fingerprint = None
    if stage == "track":
        if config_path is None:
            raise ValueError(
                "Tracking requires --config with explicit baseline settings."
            )
        fingerprint = hashlib.sha256(config_path.read_bytes()).hexdigest()
    evaluation_tracking = None
    if stage == "evaluate":
        tracking = json.loads((directory / "track.json").read_text())
        if tracking["status"] != "complete":
            raise ValueError("Tracking has not completed.")
        evaluation_tracking = tracking["result_dir"]
    previous = json.loads(marker.read_text()) if marker.exists() else {}
    if previous and not resume:
        raise FileExistsError(
            "Stage already attempted; add --resume or choose a new output root."
        )
    if previous.get("config_sha256") not in (None, fingerprint):
        raise ValueError("Tracking config changed: use a new experiment id.")
    if resume and previous.get("status") == "complete":
        # Generation checks the environment and every frame inside generate_labels.
        if (
            stage == "track"
            and valid_labels(Path(previous["result_dir"]), paths)
            and (Path(previous["result_dir"]) / "res_track.txt").exists()
        ):
            print(f"Skipping completed tracking: {experiment['id']}", flush=True)
            return
        if (
            stage == "evaluate"
            and previous.get("tracking_result") == evaluation_tracking
            and (directory / "evaluation/ctc_metrics.json").exists()
        ):
            return
    record = {"status": "running", "config_sha256": fingerprint}
    if stage == "evaluate":
        record["tracking_result"] = evaluation_tracking
    write_json(marker, record)
    started = time.perf_counter()
    try:
        if stage == "generate":
            if experiment.get("label_dirs"):
                raise ValueError(
                    "This experiment reuses labels; run the track stage directly."
                )
            generate_labels(experiment, generated, resume)
        elif stage == "track":
            for value in labels.values():
                if not valid_labels(Path(value), paths):
                    raise ValueError(f"Missing or invalid labels: {value}")
            minimum_ensemble_size = 2
            if (
                experiment["method"] == "ensemble"
                and len(labels) < minimum_ensemble_size
            ):
                raise ValueError("An ensemble requires multiple label directories.")
            if experiment["method"] != "ensemble" and len(labels) != 1:
                raise ValueError(
                    "Single-method experiments require exactly one label directory."
                )
            attempts = directory / "tracking"
            attempts.mkdir(exist_ok=True)
            attempt = attempts / f"attempt-{len(list(attempts.iterdir())) + 1:03d}"
            attempt.mkdir()
            # A new tracking attempt invalidates any old evaluation stage.
            write_json(directory / "evaluate.json", {"status": "pending"})
            record["result_dir"] = str(
                run_tracking(experiment, labels, attempt, config_path).resolve()
            )
            record["ultrack_version"] = version("ultrack")
        else:
            tracking = json.loads((directory / "track.json").read_text())
            if tracking["status"] != "complete":
                raise ValueError("Tracking has not completed.")
            script = (
                Path(__file__).resolve().parents[2]
                / "scripts/ultrack/evaluate_ctc_result.py"
            )
            subprocess.run(  # noqa: S603 -- fixed local script; no shell invocation
                [
                    sys.executable,
                    str(script),
                    "--ground-truth-dir",
                    experiment["ground_truth_dir"],
                    "--result-dir",
                    tracking["result_dir"],
                    "--dataset",
                    experiment["dataset"],
                    "--method",
                    experiment["id"],
                    "--num-workers",
                    str(workers),
                    "--output-dir",
                    str(directory / "evaluation"),
                ],
                check=True,
            )
        record["status"] = "complete"
    except Exception as error:
        record.update(status="failed", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        record["seconds"] = time.perf_counter() - started
        write_json(marker, record)


def summarize(root: Path) -> None:
    """Collect evaluated experiment scores with their dataset and parameters."""
    rows = []
    for path in sorted(root.glob("*/evaluation/ctc_metrics.json")):
        marker = path.parent.parent / "evaluate.json"
        if (
            not marker.exists()
            or json.loads(marker.read_text()).get("status") != "complete"
        ):
            continue
        spec = json.loads((path.parent.parent / "experiment.json").read_text())
        scores = json.loads(path.read_text())["reproduced"]
        rows.append(
            {
                "id": spec["id"],
                "dataset": spec["dataset"],
                "sequence": spec["sequence"],
                "method": spec["method"],
                "contour_sigma": spec.get("contour_sigma", 4),
                "image_sigma": spec.get("image_sigma", ""),
                "prob_thresh": spec.get("prob_thresh", "model default"),
                "nms_thresh": spec.get("nms_thresh", "model default"),
                **{
                    key: scores.get(key)
                    for key in ["Valid", "DET", "SEG", "TRA", "OP_CTB"]
                },
            }
        )
    if rows:
        with (root / "summary.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def inspect_cellpose(output: Path) -> None:
    """Save the installed Cellpose 3 threshold signature and implementation evidence."""
    from cellpose import dynamics, models

    installed = version("cellpose")
    if installed.split(".")[0] != "3":
        raise ValueError(
            "Activate the Cellpose 3 environment used for 2D reproduction."
        )
    evidence = {}
    for name, function in {
        "eval": models.Cellpose.eval,
        "compute_masks": dynamics.compute_masks,
    }.items():
        source = inspect.getsource(function).splitlines()
        evidence[name] = {
            "signature": str(inspect.signature(function)),
            "source_file": inspect.getsourcefile(function),
            "threshold_lines": [line.strip() for line in source if "cellprob" in line],
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        output,
        {
            "cellpose_version": installed,
            "evidence": evidence,
            "interpretation": "Zero thresholds the foreground score before sigmoid; "
            "it is not zero probability or adaptive mode. Sigmoid(0) = 0.5.",
            "reference": "https://cellpose.readthedocs.io/en/latest/settings.html",
        },
    )
