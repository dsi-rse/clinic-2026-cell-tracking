"""Run a pretrained EmbedTrack (KIT-Loe-GE) model on a CTC training dataset.

The model can come from a different dataset than the data (cross-dataset test).
Predictions are moved from the shared dataset folder into the results folder:

    <results-root>/<dataset>/<tag>/train/<seq>_RES

Example (HeLa data, GOWT1 model):
    python run_pretrained.py --dataset Fluo-N2DL-HeLa --model-dataset Fluo-N2DH-GOWT1 \
        --raw-root /net/spaces/clinic/CLS/DSC_CTC/ctc --models-root KIT-Loe-GE/models \
        --results-root results
"""

import argparse
import shutil
from pathlib import Path
from time import time


def main():
    """Parse arguments, check inputs, run inference and move the results."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--dataset", required=True, help="CTC dataset to predict, e.g. Fluo-N2DL-HeLa"
    )
    parser.add_argument(
        "--model-dataset", required=True, help="dataset whose pretrained model is used"
    )
    parser.add_argument("--sequences", nargs="+", default=["01", "02"])
    parser.add_argument(
        "--raw-root", required=True, type=Path, help="folder holding the CTC datasets"
    )
    parser.add_argument(
        "--models-root", required=True, type=Path, help="KIT-Loe-GE/models"
    )
    parser.add_argument("--results-root", required=True, type=Path)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument(
        "--no-gt", action="store_true", help="data has no ground truth (<seq>_GT)"
    )
    args = parser.parse_args()

    model_dir = args.models_root / args.model_dataset
    if args.dataset != args.model_dataset:
        # EmbedTrack refuses a model path that does not contain the dataset name.
        # For a deliberate cross-dataset test, reach the same files through a
        # symlink whose name contains the dataset name.
        link = (
            args.results_root
            / "_cross_model_links"
            / f"{args.dataset}_with_{args.model_dataset}"
        )
        link.parent.mkdir(parents=True, exist_ok=True)
        if not link.is_symlink():
            link.symlink_to(model_dir.resolve())
        model_dir = link
    model_path = model_dir / "best_iou_model.pth"
    config_file = model_dir / "config.json"
    tag = (
        "KIT-Loe-GE"
        if args.dataset == args.model_dataset
        else f"KIT-Loe-GE_model-{args.model_dataset}"
    )

    missing = [model_path, config_file]
    for seq in args.sequences:
        missing += [
            args.raw_root / args.dataset / seq,
            *([] if args.no_gt else [args.raw_root / args.dataset / f"{seq}_GT"]),
        ]
    missing = [p for p in missing if not p.exists()]
    if missing:
        raise SystemExit("missing inputs:\n" + "\n".join(f"  {p}" for p in missing))

    # Imported here so that --help works on machines without torch.
    from embedtrack.infer.infer_ctc_data import inference

    for seq in args.sequences:
        img_path = args.raw_root / args.dataset / seq
        res_path = args.results_root / args.dataset / tag / "train" / f"{seq}_RES"
        if res_path.exists():
            print("reusing existing results:", res_path)
            continue
        start = time()
        inference(
            str(img_path), str(model_path), str(config_file), batch_size=args.batch_size
        )
        print(
            f"{args.dataset} {seq} (model {args.model_dataset}): {time() - start:.0f} s"
        )
        res_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(img_path) + "_RES", str(res_path))
        print("results:", res_path)


if __name__ == "__main__":
    main()
