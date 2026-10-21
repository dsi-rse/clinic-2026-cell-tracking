# KIT-GE (3) Evaluation and Reproduction

This week I focused on making the evaluation work on the cluster and generalizing the
job scripts so the same pipeline runs on other 2D and 3D datasets.

## Contents

- [1. Evaluation setup](#1-evaluation-setup)
  - [Why py-ctcmetrics instead of eval.py](#why-py-ctcmetrics-instead-of-evalpy)
  - [Installation](#installation)
  - [What the metrics measure](#what-the-metrics-measure)
  - [SEG](#seg)
  - [DET and the res_track.txt helper](#det-and-the-res_tracktxt-helper)
  - [Tracking evaluation](#tracking-evaluation)
- [2. Fluo-N2DL-HeLa results and comparison with the publication](#2-fluo-n2dl-hela-results-and-comparison-with-the-publication)
- [3. Generalized job scripts](#3-generalized-job-scripts)
- [4. Troubleshooting this week](#4-troubleshooting-this-week)
- [5. Notes on the data](#5-notes-on-the-data)
- [6. Next steps](#6-next-steps)

## 1. Evaluation setup

### Why py-ctcmetrics instead of eval.py

The repository's `eval.py` segments each sequence and then scores it with the
official Cell Tracking Challenge programs `SEGMeasure` and `DETMeasure`.
On the cluster, `SEGMeasure` crashes with `Segmentation fault`.

The workaround, set up and used throughout this week:

- `jobs/segment_only.py` runs the same segmentation function (`inference_2d_ctc`
  / `inference_3d_ctc`) with the same settings as `eval.py`, without the scoring
  step.
- Scoring is done with [`py-ctcmetrics`](https://github.com/CellTrackingChallenge/py-ctcmetrics),
  a Python reimplementation of the CTC measures published by the challenge
  organizers.

### Installation

`py-ctcmetrics` was installed into the segmentation environment.

```bash
conda activate <PATH_TO_SEG_REPO>/env
pip install py-ctcmetrics
ctc_evaluate --help
```

### What the metrics measure

All metrics first match predicted cells to true cells: a predicted cell matches a
true cell if it covers **more than half** of the true cell's pixels.

| Metric | Question | Ground truth used |
| --- | --- | --- |
| **SEG** | How well do the cell outlines match? | `0X_GT/SEG/man_segXXX.tif`: full outlines, only on some frames and often only some cells per frame |
| **DET** | Was every cell found once, without extras or merges? | `0X_GT/TRA/man_trackXXX.tif`: a marker for every cell in every frame |
| **TRA** | Were cells linked correctly over time, including divisions? | `TRA/` markers plus `TRA/man_track.txt` (true lineage) |
| **OP_CSB** | Overall segmentation score | 0.5 · (DET + SEG) |
| **OP_CTB** | Overall tracking score | 0.5 · (SEG + TRA) |

The repository and the authors report each value as the mean over sequences
`01` and `02`.

### SEG

For every outlined true cell R, SEG finds the predicted cell S that covers more
than half of R. It scores that cell with the Jaccard index
J = |R ∩ S| / |R ∪ S|, or J = 0 if no predicted cell qualifies. SEG is the
average J over all outlined true cells. Extra predicted cells do not affect SEG.

SEG alone can be scored directly on the segmentation output. Pass `--seg` by
itself.

```bash
D=<PATH_TO_SEG_REPO>/training_data/Fluo-N2DL-HeLa
TAG=Fluo-N2DL-HeLa_GT+ST_model_0.35_0.07
ctc_evaluate --gt $D/01_GT --res $D/01_RES_$TAG --seg --csv-file Fluo-N2DL-HeLa_01_SEG.csv
```
`--csv-file` saves the results into a CSV file.

### DET and the res_track.txt helper

DET works works frame by frame, using pixel overlap. For each true
cell's marker in frame t (a small set of pixel coordinates), DET looks at the same
pixel positions in our mask for frame t. If one of our cells covers more than half
of the marker, the true cell counts as detected. It then counts the cheapest edits
that turn our detections into the true ones:

| Error | Edit | Cost |
| --- | --- | --- |
| Missed cell (false negative) | add a cell | 10 |
| One predicted cell covering two or more true cells (merge) | split it | 5 per split |
| Predicted cell matching no true cell (false positive) | delete it | 1 |

DET depends on **where** our cells are, not on how many there are. Predicted cells
in the wrong places match nothing and are counted as both missed and extra.

**Why a helper is needed.**

- The official `DETMeasure`, which `eval.py` calls, reads only the mask images in
  `01_RES` and the markers in `01_GT/TRA`. It does not need a `res_track.txt`.
- `py-ctcmetrics` always loads `res_track.txt`, and when DET is requested it also
  validates the tracks. Run on the segmentation folder, which has no
  `res_track.txt`, it crashes with
  `TypeError: object of type 'NoneType' has no len()`.

The helper, `jobs/seg_to_tracks.py`, writes a copy of the masks in which
every cell in every frame gets a unique ID. It also writes a `res_track.txt` with the same
format as the tracking list generating after tracking, that lists every
cell as a one-frame track with no parent, for example `1 0 0 0`, `2 0 0 0`, …,
`4 1 1 0`.

- Shapes and positions are unchanged, so DET and SEG are the same as scoring the
  raw masks with the official programs.
- The file contains no links.
- The renumbering is needed because segmentation labels restart in every frame.
  Keeping the original labels in a `res_track.txt` would claim false links
  between unrelated cells.

Running the helper and scoring DET and SEG together:

```bash
D=<PATH_TO_SEG_REPO>/training_data/Fluo-N2DL-HeLa
TAG=Fluo-N2DL-HeLa_GT+ST_model_0.35_0.07
OUT=<PROJECT_DIR>/seg_eval/Fluo-N2DL-HeLa

for SEQ in 01 02; do
  python <PROJECT_DIR>/jobs/seg_to_tracks.py $D/${SEQ}_RES_$TAG $OUT/${SEQ}_RES
  ctc_evaluate --gt $D/${SEQ}_GT --res $OUT/${SEQ}_RES --det --seg \
      --csv-file <PROJECT_DIR>/seg_eval/Fluo-N2DL-HeLa_${SEQ}_SEG_DET.csv
done
```

- The helper creates the `seg_eval/` folders itself.
- SEG on the copies equals SEG on the originals.
- From now on, SEG and DET are both scored on the copies in one command.
- Each sequence gets its own CSV.
- Generated folders such as `seg_eval/` stay on the cluster and are not
  committed.

### Tracking evaluation

The tracker writes a real `res_track.txt`, so its output is scored with no metric
flags. That computes SEG, DET, TRA and the biological measures:

```bash
T=<PROJECT_DIR>/tracking_results/Fluo-N2DL-HeLa
for SEQ in 01 02; do
  ctc_validate --res $T/${SEQ}_RES
  ctc_evaluate --gt $D/${SEQ}_GT --res $T/${SEQ}_RES \
      --csv-file <PROJECT_DIR>/tracking_results/Fluo-N2DL-HeLa_${SEQ}_tracking_metrics.csv
done
```

## 2. Fluo-N2DL-HeLa results and comparison with the publication

### Published values

On the official CTC website, this method reported a SEG value of 0.883, a DET value of 0.994, and an OP_CSB value of 0.938. 
These values were the results that came from the hidden challenge datasets.

The values I obtained when calculating the evaluation metrics on training sequences 01 + 02 were a SEG value of 

The model json also confirms how the selected model was built and evaluated, even including the OP_CSB of .9302 they found:

- Ranger optimizer with Mish activation;
- `th_cell` 0.07, `th_seed` 0.35, scale 1, no CLAHE;
- 480 training epochs plus a second run of 48 epochs.

### Known differences from the authors' setup

- **Images:** our training-set scores and the challenge-set scores use different
  images.
- **Scoring tool:** `py-ctcmetrics` instead of the official programs.

The thresholds, scale and model are **identical** to the authors'.

### Most likely explanation

- **Against 0.883 / 0.938:** the scores come from different images, so they
  cannot be compared directly.

## 3. Generalized job scripts

The HeLa-only scripts were replaced by scripts that take the dataset name as an
argument. All live in `jobs/`, and all call the environments' programs by full
path.

| File | Purpose |
| --- | --- |
| `datasets.sh` | Per-dataset settings (thresholds, scale, batch size, `fuse_z_seeds`, run times) and all paths |
| `segment_only.py` | Segmentation for 2D and 3D datasets. Prints the authors' `best_settings` for comparison. |
| `segmentation.sh` | GPU job: segmentation of sequences 01 and 02 |
| `seg_eval.sh` | `seg_to_tracks.py` conversion, then SEG + DET, OP_CSB |
| `track.sh` | CPU + Gurobi job: tracking |
| `track_eval.sh` | Validation, then SEG + DET + TRA, OP_CTB of the tracking output |
| `seg_to_tracks.py` | DET helper (Section 1) |
| `summarize_scores.py` | Prints per-sequence scores, means, OP_CSB and OP_CTB from the CSV files |
| `full_job.sh` | Submits all four jobs with dependencies: segmentation, then tracking and seg_eval, then track_eval |

Settings currently in `datasets.sh`, taken from the json files of the models:

| Dataset | Dim | th_seed | th_cell | scale | batch | Extra |
| --- | --- | --- | --- | --- | --- | --- |
| Fluo-N2DL-HeLa | 2D | 0.35 | 0.07 | 1 | 16 | none |
| Fluo-N2DH-GOWT1 | 2D | 0.45 | 0.07 | 1 | 16 | none |
| Fluo-C3DL-MDA231 | 3D | 0.45 | 0.07 | 1 | 8 | `fuse_z_seeds` |
| Fluo-C3DH-H157 | 3D | 0.45 | 0.07 | 1 | 8 | `fuse_z_seeds` |

Usage:

```bash
cd <PROJECT_DIR>/jobs
bash full_job.sh Fluo-N2DH-GOWT1 Fluo-C3DL-MDA231 Fluo-C3DH-H157   # whole pipeline per dataset
```

Run times per dataset (`SEG_TIME`, `TRACK_TIME`, `EVAL_TIME`) must stay within
the partition's limit; check it with `sinfo -o "%P %l"`.

## 4. Troubleshooting this week

| # | Error or blocker | Cause | Resolution |
| --- | --- | --- | --- |
| 1 | `ctc_evaluate ... --det --seg` on `01_RES_..._0.35_0.07`: `TypeError: object of type 'NoneType' has no len()` | DET needs `res_track.txt`; the segmentation folder has none | DET + SEG on the `seg_to_tracks.py` copy |
| 2 | GitHub pre-commit check failed: `end-of-file-fixer`, `ruff` (D200, D103, PLR2004, PTH123, PD901), `ruff-format` | Style rules enforced by the repo; the auto-fixes only apply to CI's temporary copy | Fixed the code: one-line docstrings, function docstrings, named constants, `Path.open()`, renamed `df`. Ran `uv run pre-commit run --all-files` locally until it passed, then committed. `uv run pre-commit install` runs the checks on every commit. |
| 3 | Could not reach the CTC submission files from some sessions (`blocked-by-allowlist`) | Network allowlist | Downloaded on the cluster, which can reach `public.celltrackingchallenge.net` |

## 5. Notes on the data

- **The gold segmentation truth is partial.** In Fluo-N2DL-HeLa, `0X_GT/SEG` has
  outlines for only some frames, such as `man_seg012`, `013` and `015`, and often
  only some cells within a frame.
- **Model weights and description.** The weights are in `<model>.pth`, a PyTorch
  `state_dict`. `<model>.json` holds the architecture and training metadata, plus
  `best_settings`.

## 6. Next steps

- [ ] Training: retrain with both optimizers (Adam + ReLU, Ranger + Mish) on the 
  split, select by OP_CSB, and compare with the pretrained models and 0.9302.
- [ ] Optional: confirm the `SEGMeasure` segfault cause with the bundled test,
  `./Linux/SEGMeasure testing_dataset 01 3`, which should print
  `SEG measure: 0.232874`.
- [ ] Test CLS data on this method to see if it generalizes even further.
