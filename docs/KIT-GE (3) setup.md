# KIT-GE (3) Segmentation + Tracking: Cluster Setup and Testing

This document records the environments, commands, errors, and fixes that occured when
testing the KIT-GE (3) Cell Tracking Challenge pipeline on the DSI cluster for one 2D 
dataset (`Fluo-N2DL-HeLa`). The pipeline has two stages:

1. **Segmentation**: a pretrained CNN predicts cell and neighbor distance maps,
   and post-processing turns them into one instance mask per frame.
2. **Tracking**: a tracker links those masks over time, detects
   cell divisions, and corrects some segmentation errors. It solves an integer
   program with Gurobi.

Current Status: segmentation job and tracking job both
completed on sequences `01` and `02`. Provided evaluation file  `eval.py` is not compatible
with the cluster. The next solution to try would be to install and use  `py-ctcmetrics` in the 
segmentation environment.

No source code in either the segmentation or tracking repository was modified. All job scripts and 
live outside the two repositories.

## Contents

- [1. Repositories and directory layout](#1-repositories-and-directory-layout)
- [2. Environment setup](#2-environment-setup)
  - [Segmentation environment](#segmentation-environment)
  - [Tracking environment](#tracking-environment)
  - [Configure Gurobi for cluster use](#configure-gurobi-for-cluster-use)
  - [Pretrained models, data, and evaluation software](#pretrained-models-data-and-evaluation-software)
- [3. Changes relative to the original repositories](#3-changes-relative-to-the-original-repositories)
- [4. Jobs](#4-Jobs)
  - [Segmentation job](#segmentation-job)
  - [Tracking job](#tracking-job)
  - [Submitting and monitoring](#submitting-and-monitoring)
- [5. Inputs and outputs](#5-inputs-and-outputs)
- [6. Evaluation](#6-evaluation)
- [7. Run history and troubleshooting](#7-run-history-and-troubleshooting)
- [8. Reproducing the run](#8-reproducing-the-run)
- [9. Open items](#9-open-items)

## 1. Repositories and directory layout

| Repository | Uses | Upstream |
| --- | --- | --- |
| `KIT-GE-3-Cell-Segmentation-for-CTC` | CNN segmentation and CTC evaluation scripts | https://github.com/TimScherr/KIT-GE-3-Cell-Segmentation-for-CTC |
| `KIT-GE-3-Cell-Tracking-for-CTC` | Graph-based tracking (Löffler et al., PLOS ONE 2021) | https://github.com/kaloeffler/KIT-GE-3-Cell-Tracking-for-CTC |

Layout on the cluster:

```text
/net/scratch/evt-kit-ge/clinic-2026-cell-tracking/
├── external/
│   ├── KIT-GE-3-Cell-Segmentation-for-CTC/   # segmentation repo (+ its conda env in ./env)
│   └── KIT-GE-3-Cell-Tracking-for-CTC/       # tracking repo
├── jobs/                                     # Slurm scripts
└── tracking_results/Fluo-N2DL-HeLa/          # tracking output
```

## 2. Environment setup

The two repositories have incompatible library versions, so each needs its own
conda environment.

### Segmentation environment

The repository's `requirements.yml` lists Python 3.8, PyTorch 1.7.0 with CUDA
11.0, and NumPy 1.19.5. The environment used was created at a prefix
path inside the repo, so it has no name and is activated by its path:

```bash
conda activate /net/spaces/scratch/evt-kit-ge/clinic-2026-cell-tracking/external/KIT-GE-3-Cell-Segmentation-for-CTC/env
```

| Item | Value |
| --- | --- |
| Environment | prefix env at `.../KIT-GE-3-Cell-Segmentation-for-CTC/env` |
| Python | `3.10` |
| PyTorch | `2.1.2+cu121` |
| NumPy | `1.23.5` |
| tifffile | `2021.11.2` (downgraded) |
| py-ctcmetrics | latest from PyPI (for evaluation) |

These versions are newer than the repo's listed requirements. PyTorch 2.1 / CUDA 12.1 also
supports newer GPUs, which PyTorch 1.7 does not. The one incompatibility found
was `tifffile`:

```bash
pip install "tifffile==2021.11.2"
```

Quick check to ensure the libraries are compatible:

```bash
python -c "import torch, numpy; print(torch.__version__, numpy.__version__)"
python -c "import tifffile, numpy as np; tifffile.imsave('/tmp/t.tif', np.zeros((5,5),np.uint16), compress=1); print('tifffile imsave OK')"
```

### Tracking environment

```bash
conda create -y --name tracking_env python=3.8
conda activate tracking_env
conda install -y -c conda-forge "imagecodecs=2021.1.11"
pip install -e /net/scratch/evt-kit-ge/clinic-2026-cell-tracking/external/KIT-GE-3-Cell-Tracking-for-CTC
pip install "gurobipy>=10,<12"
pip install "numpy==1.23.5"
```

| Item | Value |
| --- | --- |
| Environment | `tracking_env` (`/home/evt/.conda/envs/tracking_env`) |
| Python | `3.8` |
| NumPy | `1.23.5` (downgraded from `1.24.4`) |
| gurobipy | `11.0.3` (repo lists `9.1.1`) |
| imagecodecs | `2021.1.11` from conda-forge |
| tifffile | `2021.1.14` |
| Gurobi license | Academic WLS, non-commercial use |

### Configure Gurobi for cluster use

The tracker needs Gurobi to solve its integer programs.

Download `gurobi.lic` from the
  Gurobi portal and place it in your private home directory:

```bash
scp ~/Downloads/gurobi.lic ssh <user>@login:~/gurobi.lic
ssh <user>@login
chmod 600 ~/gurobi.lic
```

Verify on a compute node:

```bash
srun --time=00:05:00 --pty bash -c 'eval "$(conda shell.bash hook)"; conda activate tracking_env; \
  python -c "import gurobipy as gp; m=gp.Model(); print(\"OK\", gp.gurobi.version())"'
```

### Pretrained models, data, and evaluation software

From the segmentation repo root:

```bash
python download_models.py   # downloads models into models/kit-sch-ge/*_GT+ST_model.{pth,json}
python download_data.py     # downloads and unzips data in training_data/, challenge_data/, evaluation_software/ (~40 GiB)
```

Run `download_data.py` from the repo root, because it extracts into paths
relative to the current directory.

`eval.py` only looks for models in `models/all/`, so the submission model was
copied there:

```bash
cd /net/spaces/scratch/evt-kit-ge/clinic-2026-cell-tracking/external/KIT-GE-3-Cell-Segmentation-for-CTC
cp "models/kit-sch-ge/Fluo-N2DL-HeLa_GT+ST_model.pth"  models/all/
cp "models/kit-sch-ge/Fluo-N2DL-HeLa_GT+ST_model.json" models/all/
chmod +x evaluation_software/Linux/*
```

## 3. Changes relative to the original repositories

**No source code was edited in either repository.** All differences from the
upstream instructions are listed here.

| Change | Where | Why |
| --- | --- | --- |
| Copied `Fluo-N2DL-HeLa_GT+ST_model.{pth,json}` into `models/all/` | segmentation repo (data files only) | `eval.py` and our segmentation script look for models there. The downloaded models are in `models/kit-sch-ge/`. |
| Segmentation run with `jobs/segment_only.py` instead of `eval.py` | outside both repos | `eval.py` calls the official `SEGMeasure` binary after each sequence, and that binary segfaults on this cluster. The script calls the repo's own `inference_2d_ctc` with the same settings, without the scoring step.|
| Library versions differ from pins | both envs | See [Section 2](#2-environment-setup). |

## 4. The two jobs

Both jobs are Slurm batch scripts in
`/net/scratch/evt-kit-ge/clinic-2026-cell-tracking/jobs/`. Submit them from that
folder, because `sbatch seg.sh` only looks in the current directory and the
`.out` logs are written there.

### Segmentation job

`seg.sh`:

```bash
#!/bin/bash
#SBATCH --job-name=kitge-seg
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:45:00          # must fit the partition's MaxTime
#SBATCH --output=%x_%j.out
set -e                           # must come AFTER all #SBATCH lines

eval "$(conda shell.bash hook)"
conda activate /net/spaces/scratch/evt-kit-ge/clinic-2026-cell-tracking/external/KIT-GE-3-Cell-Segmentation-for-CTC/env
python -u /net/scratch/evt-kit-ge/clinic-2026-cell-tracking/jobs/segment_only.py
```

- `eval "$(conda shell.bash hook)"` makes `conda activate` work in a
  non-interactive batch shell.
- `python -u` turns off output buffering, so progress appears in the `.out`
  file immediately.
- `set -e` stops the job if a step fails, for example if `conda activate`
  fails, instead of running Python without the environment. It must come
  **after** all `#SBATCH` lines: Slurm stops reading `#SBATCH` directives at
  the first command.

`segment_only.py`:

```python
import sys, torch
from pathlib import Path

REPO = Path("/net/spaces/scratch/evt-kit-ge/clinic-2026-cell-tracking/external/KIT-GE-3-Cell-Segmentation-for-CTC")
sys.path.insert(0, str(REPO))
from eval import EvalArgs                                  # reuse the repo's settings class
from segmentation.inference.inference import inference_2d_ctc

ct, model_name, th_seed, th_cell = "Fluo-N2DL-HeLa", "Fluo-N2DL-HeLa_GT+ST_model", 0.35, 0.07
model = REPO / "models" / "all" / f"{model_name}.pth"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Device:", device, flush=True)

for subset in ["01", "02"]:
    res = REPO / "training_data" / ct / f"{subset}_RES_{model_name}_{th_seed}_{th_cell}"
    res.mkdir(exist_ok=True)
    if len(list(res.glob("mask*.tif"))) == len(list((REPO / "training_data" / ct / subset).glob("t*.tif"))):
        print(f"{subset}: already segmented, skipping", flush=True)
        continue
    args = EvalArgs(th_cell=th_cell, th_seed=th_seed, n_splitting=40, apply_clahe=False, scale=1,
                    cell_type=ct, save_raw_pred=False, artifact_correction=False,
                    apply_merging=False, fuse_z_seeds=False)
    print(f"Segmenting {ct} {subset} -> {res}", flush=True)
    inference_2d_ctc(model=model, data_path=REPO / "training_data" / ct / subset, result_path=res,
                     device=device, batchsize=16, args=args, num_gpus=1)
print("Done", flush=True)
```

The output folder names match what `eval.py` would have produced, so the
tracking job reads them unchanged.

### Tracking job

`track.sh`:

```bash
#!/bin/bash
#SBATCH --job-name=kitge-track
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=02:00:00          # must fit the partition's MaxTime
#SBATCH --output=%x_%j.out
set -e                           # must come AFTER all #SBATCH lines
EXT=/net/scratch/evt-kit-ge/clinic-2026-cell-tracking/external
PROJ=/net/scratch/evt-kit-ge/clinic-2026-cell-tracking

eval "$(conda shell.bash hook)"
conda activate tracking_env
export GRB_LICENSE_FILE=$HOME/gurobi.lic

DS=Fluo-N2DL-HeLa
TAG=Fluo-N2DL-HeLa_GT+ST_model_0.35_0.07
DATA=$EXT/KIT-GE-3-Cell-Segmentation-for-CTC/training_data/$DS
OUT=$PROJ/tracking_results/$DS

cd $EXT/KIT-GE-3-Cell-Tracking-for-CTC     # run_tracking.py is a top-level module
for SEQ in 01 02; do
  python -u -m run_tracking \
      --image_path        $DATA/$SEQ \
      --segmentation_path $DATA/${SEQ}_RES_$TAG \
      --results_path      $OUT/${SEQ}_RES
done
```

Tracking runs on the CPU only, so the script requests no GPU. `--results_path`
must differ from `--segmentation_path`; otherwise the tracker overwrites the
segmentation masks.

### Submitting and monitoring

```bash
cd /net/scratch/evt-kit-ge/clinic-2026-cell-tracking/jobs
SEGJOB=$(sbatch --parsable seg.sh) && echo $SEGJOB
sbatch --dependency=afterok:$SEGJOB track.sh   # tracking starts only if segmentation succeeds

squeue -u $USER                                 # R = running, PD = pending, (Dependency) = waiting on seg
sacct -u $USER --starttime today --format=JobID,JobName,Partition,State,ExitCode,Elapsed
tail -f $(ls -t kitge-seg_*.out | head -1)      # Ctrl+C stops watching, not the job
```

If segmentation fails, the tracking job is left in
`(DependencyNeverSatisfied)` and must be cancelled with
`scancel -u $USER -n kitge-track`.

Final successful runs:

| Job | JobID | Partition | State | Elapsed |
| --- | --- | --- | --- | --- |
| Segmentation (`kitge-seg`) | `2169971` | `general` | COMPLETED (0:0) | 00:04:34 |
| Tracking (`kitge-track`) | `2170072` | `general` | COMPLETED (0:0) | 00:03:56 |


## 5. Inputs and outputs

### Segmentation job

**Input**

| Input | Location | Notes/Details |
| --- | --- | --- |
| Raw microscopy frames | `training_data/Fluo-N2DL-HeLa/01/t000.tif … t091.tif` (and `02/`) | 2D fluorescence images, 92 frames per sequence |
| Pretrained model | `models/all/Fluo-N2DL-HeLa_GT+ST_model.{pth,json}` | Submission model trained on gold truth + silver truth. The `.json` describes the architecture. |
| Post-processing settings | `th_seed=0.35`, `th_cell=0.07`, `scale=1` | Seed threshold controls how cells are split; cell threshold controls cell size |

**Output**

```text
training_data/Fluo-N2DL-HeLa/01_RES_Fluo-N2DL-HeLa_GT+ST_model_0.35_0.07/mask000.tif … mask091.tif
training_data/Fluo-N2DL-HeLa/02_RES_Fluo-N2DL-HeLa_GT+ST_model_0.35_0.07/mask000.tif … mask091.tif
```

Each `maskXXX.tif` is an **instance label image** the same size as the
frame. `0` is background, and each cell has a unique integer within that frame.
Labels are **not** consistent across frames.


### Tracking job

**Input**

| Input | Location |
| --- | --- |
| Raw frames | `training_data/Fluo-N2DL-HeLa/0X/t*.tif` |
| Segmentation masks | `training_data/Fluo-N2DL-HeLa/0X_RES_..._0.35_0.07/mask*.tif` |
| Gurobi license | `~/gurobi.lic` (WLS) |
| Tracker parameters | defaults: `delta_t=3` (frames to look ahead), `default_roi_size=2` |

This job builds a graph of candidate links between cells in
neighboring frames, then uses Gurobi to choose the best set of links, including
divisions.

**Output**

```text
tracking_results/Fluo-N2DL-HeLa/01_RES/mask000.tif … mask091.tif
tracking_results/Fluo-N2DL-HeLa/01_RES/res_track.txt
tracking_results/Fluo-N2DL-HeLa/02_RES/...
```

- **Tracked masks**: same format as the segmentation masks, but every pixel
  value is now a **track ID that stays the same over time**.
- **`res_track.txt`**: one line per track, `L B E P`:
  - **L**: track ID (the mask value)
  - **B**: first frame
  - **E**: last frame
  - **P**: parent track ID, or `0` if none


## 6. Evaluation (Still Needs Work)

Ground truth for each sequence is in `training_data/Fluo-N2DL-HeLa/0X_GT/`:

- `SEG/man_segXXX.tif`: full segmentation ground truth for a subset of frames
- `TRA/man_trackXXX.tif` and `TRA/man_track.txt`: tracking ground truth for all
  frames

The repository and the paper report each value as the mean over sequences `01`
and `02`.

As of now, evaluation does not work during the jobs, as the cluster and the evaluation 
version provided in the Segmentation repository are incompatible. Will need to test new evaluation 
methods or scripts. One method that could be possible is installing and using the `py-ctcmetrics` 
evaluators.

Install the evaluator into the segmentation environment (Python 3.10, the
version its authors tested):

```bash
conda activate /net/spaces/scratch/evt-kit-ge/clinic-2026-cell-tracking/external/KIT-GE-3-Cell-Segmentation-for-CTC/env
pip install py-ctcmetrics
D=/net/spaces/scratch/evt-kit-ge/clinic-2026-cell-tracking/external/KIT-GE-3-Cell-Segmentation-for-CTC/training_data/Fluo-N2DL-HeLa
TAG=Fluo-N2DL-HeLa_GT+ST_model_0.35_0.07
```

## 7. Run history and troubleshooting

Listed in the order they happened.

| # | Error or blocker | Cause | Action taken | Outcome |
| --- | --- | --- | --- | --- |
| 1 | `kit-sch-ge-cell-tracking 1.0.0 requires gurobipy==9.1.1, but you have gurobipy 11.0.3` | Upgrade needed for WLS conflicts with the repo pin | None needed; warning only | Not an error |
| 2 | `eval.py` segmented all of `01`, then `IndexError: list index out of range` in `segmentation/utils/metrics.py` (`float(seg_measure[0])`) | `eval.py` parses a number from `SEGMeasure`'s output and found none. Running `SEGMeasure` by hand gave `Segmentation fault`; `ldd` reports `not a dynamic executable`, consistent with the CTC docs ("statically linked", built with GCC 7.5, tested on Ubuntu 18.04 / RHEL 7.8) | Replaced `eval.py` with `segment_only.py` (no scoring), and scored with `py-ctcmetrics` | Worked around; root cause not confirmed |
| 3 | Tracking: `AttributeError: module 'numpy' has no attribute 'int'` | NumPy 1.24 removed `np.int`, which the tracker uses | `pip install "numpy==1.23.5"` in `tracking_env` (a first attempt failed because of the typo `nump`) | Resolved |

Debugging notes:

- **`squeue` shows only queued and running jobs.** Use `sacct` for finished
  ones, and read the `%x_%j.out` log for the actual error.
- **`ls` alongside `SEGMeasure` output.** The `SEG/` folder holding only some
  frame numbers (for example `man_seg012`, `013`, `015`) is normal: ground
  truth is annotated on a subset of frames, and `SEGMeasure` matches each
  ground-truth frame to the `mask` file with the same number.
- **Stop `tail -f` with Ctrl+C, not Ctrl+Z.** Ctrl+Z only suspends it.

## 8. Reproducing the run

1. Create both environments ([Section 2](#2-environment-setup)), install the
   WLS license, and verify Gurobi on a compute node.
2. Download models and data, and copy the HeLa model into `models/all/`.
3. Create `jobs/seg.sh`, `jobs/segment_only.py`, `jobs/track.sh`, and
   `jobs/seg_to_ctc_tracks.py` as shown above.
4. From `jobs/`:

   ```bash
   SEGJOB=$(sbatch --parsable seg.sh) && echo $SEGJOB
   sbatch --dependency=afterok:$SEGJOB track.sh
   ```

5. Confirm success:
   - `sacct` shows both jobs `COMPLETED 0:0`.
   - Each `0X_RES_..._0.35_0.07` segmentation folder has 92 masks.
   - Each `tracking_results/Fluo-N2DL-HeLa/0X_RES` folder has 92 masks plus
     `res_track.txt`.
6. Run the evaluation commands in [Section 6](#6-evaluation) and record the
   scores.
