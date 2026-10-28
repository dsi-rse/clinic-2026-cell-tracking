"""Segment CTC training sequences with a pretrained KIT-GE (3) model, without eval.py's scoring.

Uses the same segmentation functions and post-processing settings as the repository's eval.py

Example:
    python segment_only.py --seg_repo /path/to/KIT-GE-3-Cell-Segmentation-for-CTC \
        --ds Fluo-N2DL-HeLa --th_seed 0.35 --th_cell 0.07
"""

import argparse
import json
import os
import sys
from pathlib import Path


def parse_args():
    """Parse command-line arguments; --seg_repo falls back to the SEG_REPO environment variable."""
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--seg_repo",
        default=os.environ.get("SEG_REPO"),
        help="path to KIT-GE-3-Cell-Segmentation-for-CTC (default: $SEG_REPO)",
    )
    p.add_argument("--ds", required=True, help="dataset, e.g. Fluo-N2DH-GOWT1")
    p.add_argument("--th_seed", type=float, required=True)
    p.add_argument("--th_cell", type=float, required=True)
    p.add_argument("--scale", type=float, default=1.0)
    p.add_argument("--batch_size", type=int, default=8)
    p.add_argument("--fuse_z_seeds", action="store_true")
    p.add_argument("--artifact_correction", action="store_true")
    p.add_argument("--n_splitting", type=int, default=40)
    p.add_argument("--model_dir", help="default: <seg_repo>/models/kit-sch-ge")
    p.add_argument("--data_dir", help="default: <seg_repo>/training_data")
    p.add_argument("--subsets", nargs="+", default=["01", "02"])
    a = p.parse_args()
    if not a.seg_repo:
        p.error("--seg_repo is required (or set the SEG_REPO environment variable)")
    a.seg_repo = Path(a.seg_repo)
    a.model_dir = (
        Path(a.model_dir) if a.model_dir else a.seg_repo / "models" / "kit-sch-ge"
    )
    a.data_dir = Path(a.data_dir) if a.data_dir else a.seg_repo / "training_data"
    return a


def main():
    """Run segmentation on each requested training sequence."""
    a = parse_args()
    if not a.seg_repo.is_dir():
        sys.exit(f"Segmentation repository not found: {a.seg_repo}")

    sys.path.insert(0, str(a.seg_repo))
    import torch
    from eval import EvalArgs
    from segmentation.inference.inference import inference_2d_ctc, inference_3d_ctc

    model = a.model_dir / f"{a.ds}_GT+ST_model.pth"
    if not model.exists():
        sys.exit(f"Model not found: {model}")
    with model.with_suffix(".json").open() as f:
        info = json.load(f)
    print("Model:", model, flush=True)
    print(
        "Authors' best_settings in model json:", info.get("best_settings"), flush=True
    )
    print(
        f"Using: th_seed={a.th_seed} th_cell={a.th_cell} scale={a.scale} "
        f"fuse_z_seeds={a.fuse_z_seeds} artifact_correction={a.artifact_correction} "
        f"batch_size={a.batch_size}",
        flush=True,
    )

    if "2D" in a.ds:
        infer = inference_2d_ctc
    elif "3D" in a.ds:
        infer = inference_3d_ctc
    else:
        sys.exit("Dataset name must contain '2D' or '3D'")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cuda":
        torch.backends.cudnn.benchmark = True
    print("Device:", device, flush=True)

    for subset in a.subsets:
        img_dir = a.data_dir / a.ds / subset
        n_imgs = len(list(img_dir.glob("t*.tif")))
        if n_imgs == 0:
            sys.exit(f"No images found in {img_dir}")
        res = a.data_dir / a.ds / f"{subset}_RES_{model.stem}_{a.th_seed}_{a.th_cell}"
        res.mkdir(exist_ok=True)
        if len(list(res.glob("mask*.tif"))) == n_imgs:
            print(f"{subset}: already segmented ({n_imgs} masks), skipping", flush=True)
            continue
        args = EvalArgs(
            th_cell=a.th_cell,
            th_seed=a.th_seed,
            n_splitting=a.n_splitting,
            apply_clahe=False,
            scale=a.scale,
            cell_type=a.ds,
            save_raw_pred=False,
            artifact_correction=a.artifact_correction,
            apply_merging=False,
            fuse_z_seeds=a.fuse_z_seeds,
        )
        print(f"Segmenting {a.ds} {subset} ({n_imgs} frames) -> {res}", flush=True)
        infer(
            model=model,
            data_path=img_dir,
            result_path=res,
            device=device,
            batchsize=a.batch_size,
            args=args,
            num_gpus=1,
        )
    print("Done", flush=True)


if __name__ == "__main__":
    main()
