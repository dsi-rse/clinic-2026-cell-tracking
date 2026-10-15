"""Run KIT-GE (3) segmentation only (no tracking or eval) on Fluo-N2DL-HeLa."""

import sys
from pathlib import Path

import torch

REPO = Path(
    "/net/spaces/scratch/evt-kit-ge/clinic-2026-cell-tracking/external/KIT-GE-3-Cell-Segmentation-for-CTC"
)
sys.path.insert(0, str(REPO))
from eval import EvalArgs  # noqa: E402
from segmentation.inference.inference import inference_2d_ctc  # noqa: E402

ct, model_name, th_seed, th_cell = (
    "Fluo-N2DL-HeLa",
    "Fluo-N2DL-HeLa_GT+ST_model",
    0.35,
    0.07,
)
model = REPO / "models" / "all" / f"{model_name}.pth"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Device:", device, flush=True)

for subset in ["01", "02"]:
    res = REPO / "training_data" / ct / f"{subset}_RES_{model_name}_{th_seed}_{th_cell}"
    res.mkdir(exist_ok=True)
    if len(list(res.glob("mask*.tif"))) == len(
        list((REPO / "training_data" / ct / subset).glob("t*.tif"))
    ):
        print(f"{subset}: already segmented, skipping", flush=True)
        continue
    args = EvalArgs(
        th_cell=th_cell,
        th_seed=th_seed,
        n_splitting=40,
        apply_clahe=False,
        scale=1,
        cell_type=ct,
        save_raw_pred=False,
        artifact_correction=False,
        apply_merging=False,
        fuse_z_seeds=False,
    )
    print(f"Segmenting {ct} {subset} -> {res}", flush=True)
    inference_2d_ctc(
        model=model,
        data_path=REPO / "training_data" / ct / subset,
        result_path=res,
        device=device,
        batchsize=16,
        args=args,
        num_gpus=1,
    )
print("Done", flush=True)
