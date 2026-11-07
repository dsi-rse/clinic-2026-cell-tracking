"""Run the mentor's Cellpose 4 approach on single-channel CTC ZYX frames."""

import argparse
import time
from importlib.metadata import version
from pathlib import Path

from cell_tracking.ctc_io import extract_frame_number


def parse_args() -> argparse.Namespace:
    """Read explicit dataset paths and dataset-specific segmentation settings."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--dataset", choices=["Fluo-C3DL-MDA231", "Fluo-C3DH-H157"], required=True
    )
    parser.add_argument(
        "--diameter",
        type=float,
        required=True,
        help="Approximate cell diameter in XY pixels; measure from raw images.",
    )
    parser.add_argument(
        "--anisotropy",
        type=float,
        required=True,
        help="Voxel spacing Z divided by spacing XY; obtain from metadata.",
    )
    parser.add_argument(
        "--model",
        default="cpsam",
        help="Cellpose 4 pretrained model name or local checkpoint path.",
    )
    parser.add_argument("--gpu", action="store_true")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse valid saved masks with matching experiment settings.",
    )
    parser.add_argument("--frame-start", type=int, default=0)
    parser.add_argument("--frame-stop", type=int, help="Exclusive ending frame number.")
    parser.add_argument("--cellprob-threshold", type=float, default=0.0)
    parser.add_argument("--min-size", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument(
        "--sigma",
        type=float,
        nargs=3,
        default=[0.0, 0.0, 0.0],
        metavar=("Z", "Y", "X"),
        help="Optional Gaussian smoothing.",
    )
    parser.add_argument("--tile-norm-blocksize", type=int, default=0)
    args = parser.parse_args()
    if args.diameter <= 0 or args.anisotropy <= 0:
        parser.error("Diameter and anisotropy must be positive.")
    if args.batch_size <= 0 or args.min_size < 0 or min(args.sigma) < 0:
        parser.error(
            "Batch size must be positive; min-size and sigma must be nonnegative."
        )
    return args


def main() -> None:
    """Segment each time point independently and record partial runs on failure."""
    args = parse_args()
    frames = []
    for path in sorted(args.input_dir.glob("t*.tif")):
        number = extract_frame_number(path, expected_prefix="t")
        if number >= args.frame_start and (
            args.frame_stop is None or number < args.frame_stop
        ):
            frames.append(path)
    if not frames:
        raise ValueError("No matching tNNN.tif frames found in the requested range.")
    if args.output_dir.exists() and any(args.output_dir.iterdir()) and not args.resume:
        raise ValueError("Choose an empty output directory or pass --resume.")

    import numpy as np
    import tifffile
    import torch
    from cellpose import models

    from cell_tracking.cellpose_3d import prepare_volume, save_preview
    from cell_tracking.cellpose_resume import (
        load_checkpoint,
        read_saved_mask,
        write_checkpoint,
    )

    cellpose_version = version("cellpose")
    if cellpose_version != "4.2.1.1":
        raise ValueError(
            f"Use the tutorial's Cellpose 4.2.1.1; found {cellpose_version}."
        )
    if args.gpu and not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA GPU requested but unavailable. Check the cluster allocation."
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "configuration": {
            key: str(value) if isinstance(value, Path) else value
            for key, value in vars(args).items()
        },
        "versions": {
            name: version(name)
            for name in [
                "cellpose",
                "torch",
                "numpy",
                "tifffile",
                "scipy",
                "scikit-image",
            ]
        },
        "device": torch.cuda.get_device_name(0) if args.gpu else "cpu",
        "status": "running",
        "frames": [],
        "note": "Independent segmentation labels; not temporal tracks or a CTC tracking submission.",
    }
    record = args.output_dir / "run.json"
    if args.resume:
        if not record.exists():
            raise ValueError(
                "--resume requires the original run.json in the output directory."
            )
        metadata = load_checkpoint(
            record, metadata["configuration"], metadata["versions"]
        )
    metadata["status"] = "running"
    try:
        write_checkpoint(record, metadata)
        model = None
        for path in frames:
            started = time.perf_counter()
            raw = tifffile.imread(path)
            output_name = f"mask{path.stem[1:]}.tif"
            output_path = args.output_dir / output_name
            preview_path = args.output_dir / f"{path.stem}_preview.png"
            masks = read_saved_mask(output_path, raw.shape) if args.resume else None
            if masks is not None:
                if not preview_path.exists():
                    save_preview(raw, masks, preview_path)
                if not any(entry["input"] == str(path) for entry in metadata["frames"]):
                    metadata["frames"].append(
                        {
                            "input": str(path),
                            "shape_zyx": list(raw.shape),
                            "objects": int(np.unique(masks[masks > 0]).size),
                            "seconds": None,
                            "recovered_from_saved_mask": True,
                        }
                    )
                write_checkpoint(record, metadata)
                print(f"Skipping {path.name}: valid saved mask", flush=True)
                continue
            metadata["frames"] = [
                entry for entry in metadata["frames"] if entry["input"] != str(path)
            ]
            if model is None:
                model = models.CellposeModel(gpu=args.gpu, pretrained_model=args.model)
            image = prepare_volume(raw, args.sigma)
            # A singleton channel replaces the tutorial's nucleus/membrane pair.
            masks, _, _ = model.eval(
                image[..., np.newaxis],
                channel_axis=-1,
                z_axis=0,
                do_3D=True,
                diameter=args.diameter,
                anisotropy=args.anisotropy,
                cellprob_threshold=args.cellprob_threshold,
                min_size=args.min_size,
                batch_size=args.batch_size,
                normalize={
                    "tile_norm_blocksize": args.tile_norm_blocksize,
                    "norm3D": True,
                },
            )
            if masks.shape != raw.shape:
                raise ValueError(
                    f"Mask shape {masks.shape} differs from raw {raw.shape}."
                )
            if masks.max() > np.iinfo(np.uint16).max:
                raise ValueError("Too many labels for uint16 output.")
            temporary_mask = output_path.with_suffix(".tif.tmp")
            tifffile.imwrite(
                temporary_mask, masks.astype(np.uint16), metadata={"axes": "ZYX"}
            )
            temporary_mask.replace(output_path)
            save_preview(raw, masks, preview_path)
            metadata["frames"].append(
                {
                    "input": str(path),
                    "shape_zyx": list(raw.shape),
                    "objects": int(np.unique(masks[masks > 0]).size),
                    "seconds": time.perf_counter() - started,
                }
            )
            write_checkpoint(record, metadata)
            print(f"Finished {path.name}", flush=True)
        metadata["status"] = "complete"
    except Exception as error:
        metadata["status"] = "failed"
        metadata["blocker"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        write_checkpoint(record, metadata)


if __name__ == "__main__":
    main()
