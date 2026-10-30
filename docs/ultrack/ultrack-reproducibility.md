# Ultrack benchmark reproducibility

- [Ultrack benchmark reproducibility](#ultrack-benchmark-reproducibility)
  - [Overview](#overview)
  - [Methodology and status overview](#methodology-and-status-overview)
  - [Results](#results)
  - [General workflow](#general-workflow)
  - [Shared cluster conventions](#shared-cluster-conventions)
  - [Reusable 2D methods and commands](#reusable-2d-methods-and-commands)
  - [Fluo-N2DL-HeLa](#fluo-n2dl-hela)
    - [Dataset and comparison target](#dataset-and-comparison-target)
    - [Data and software](#data-and-software)
    - [StarDist configuration](#stardist-configuration)
    - [Ultrack configuration](#ultrack-configuration)
    - [Full-sequence run records](#full-sequence-run-records)
    - [Output layout](#output-layout)
    - [Evaluation results and commands](#evaluation-results-and-commands)
    - [Executable records and environment notes](#executable-records-and-environment-notes)
  - [Fluo-N2DH-GOWT1](#fluo-n2dh-gowt1)
    - [Dataset and comparison scope](#dataset-and-comparison-scope)
    - [Configuration](#configuration)
    - [Commands](#commands)
    - [Evaluation](#evaluation)
  - [Fluo-C3DL-MDA231](#fluo-c3dl-mda231)
    - [Dataset and comparison target](#dataset-and-comparison-target-1)
    - [Data and software](#data-and-software-1)
    - [Published U-Net and Ultrack configuration](#published-u-net-and-ultrack-configuration)
    - [Container environment](#container-environment)
    - [Full-sequence execution](#full-sequence-execution)
    - [Slurm job and hardware record](#slurm-job-and-hardware-record)
    - [Output layout](#output-layout-1)
    - [Evaluation results and command](#evaluation-results-and-command)
  - [Adding another dataset](#adding-another-dataset)


## Overview

This document records how the project runs and evaluates Ultrack benchmarks.
It is intended to grow as additional datasets and segmentation inputs are
tested. Each dataset section should state exactly what was reproduced, what was
changed, and which comparisons are valid.

The first complete experiments use both `Fluo-N2DL-HeLa` training sequences
with a pretrained StarDist model. No model was trained or fine-tuned during
these runs. StarDist performed inference to create instance labels, and
Ultrack used those labels to construct and select tracks.

The 3D `Fluo-C3DL-MDA231` experiment uses the authors' published U-Net
checkpoint and official sequence script in a GPU container. It is kept
separate from the reusable 2D workflow because it uses the authors' older
pinned Ultrack submission environment and dataset-specific 3D preprocessing.

## Methodology and status overview

The ECCV paper used or compared several segmentation inputs. Only methods
actually run by this project are marked as reproduced or in progress.

| Dataset | Segmentation input | Role | Project status | Valid comparison |
| --- | --- | --- | --- | --- |
| `Fluo-N2DL-HeLa` | Watershed | Published single-method comparator | Complete and evaluated for sequences 01 and 02 | Compare with the matching published watershed row, while documenting the incomplete parameter specification |
| `Fluo-N2DL-HeLa` | Cellpose `cyto2` | Published single-method comparator | Complete and evaluated for sequences 01 and 02 | Compare with the matching published Cellpose row while documenting software and hardware differences |
| `Fluo-N2DL-HeLa` | StarDist `2D_versatile_fluo` | Selected reproduction method | Complete for sequences 01 and 02 | Compare with the matching published StarDist row |
| `Fluo-N2DL-HeLa` | Watershed + Cellpose + StarDist ensemble | Best published experiment for these sequences | Complete and evaluated for sequences 01 and 02 | Compare with the matching published ensemble rows while documenting environment differences |
| `Fluo-N2DH-GOWT1` | Cellpose `cyto2` | Additional 2D project experiment | Complete and evaluated for sequences 01 and 02 | No matching published Ultrack benchmark; report as a project result |
| `Fluo-N2DH-GOWT1` | StarDist `2D_versatile_fluo` | Additional 2D project experiment | Complete and evaluated for sequences 01 and 02 | No matching published Ultrack benchmark; report as a project result |
| `Fluo-N2DH-GOWT1` | Watershed | Additional 2D project baseline | Complete and evaluated for sequences 01 and 02 | No matching published Ultrack benchmark; report as an oversegmented project baseline |
| `Fluo-N2DH-GOWT1` | Watershed + Cellpose + StarDist ensemble | Additional 2D project experiment | Complete and evaluated for sequences 01 and 02 | No matching published Ultrack benchmark; compare only with the project's single-method results |
| `Fluo-C3DL-MDA231` | Trained 3D U-Net foreground and boundary maps | Published CTC submission method | Official sequence 01 workflow complete and evaluated on public training data | Compare descriptively with the hidden-test result, but do not claim a direct numerical reproduction |

For HeLa, the paper converted every segmentation method's instance labels into
a binary foreground map and a contour map. Its ensemble combined foreground
maps with a logical OR and averaged the contour maps. This project selected
StarDist first because the paper used publicly available pretrained weights
without dataset-specific fine-tuning. Watershed and Cellpose have since been
completed as separate experiments. The HeLa and GOWT1 ensembles are also
complete and evaluated. Their evaluation metrics are recorded in
[`ultrack-results.md`](ultrack-results.md), together with their run-report
configuration, runtime, and output summaries. The supplied reports do not
capture the worker settings or hardware allocation.

## Results

Completed scores, runtime summaries, interpretation, and follow-up hypotheses
are recorded separately in
[`ultrack-results.md`](ultrack-results.md). Keeping the numerical results in a
separate document allows this guide to remain focused on reproducible setup and
execution as more segmentation methods and datasets are added.

## General workflow

The reproducible workflow for each dataset is:

1. load the raw microscopy sequence;
2. create instance labels with a documented segmentation method;
3. convert the labels into foreground and contour maps;
4. run Ultrack segmentation, linking, and optimization;
5. export the result in Cell Tracking Challenge (CTC) format; and
6. validate and evaluate the complete sequence with CTC metrics.

Gold annotations are not supplied to the segmentation model or Ultrack. They
are used only after inference for visual checks and quantitative evaluation.

For each new dataset, record:

- the dataset, sequence, and evaluated frame range;
- whether the data are public training data or hidden test data;
- the segmentation model, weights, and preprocessing parameters;
- the Ultrack version and non-default configuration;
- the compute resources and worker settings;
- the output directory naming convention;
- stage runtimes and output counts;
- the reproduced SEG, TRA, and `OP_CTB` scores; and
- the exact published result used for comparison.

## Shared cluster conventions

Raw data, model files, databases, and result masks remain in approved cluster
storage rather than Git. The notebook reads locations from environment
variables so that personal or machine-specific paths are not embedded in the
executable code:

```bash
export CTC_ROOT=/path/to/DSC_CTC
export ULTRACK_RUN_ROOT=/path/to/DSC_CTC/runs/ultrack
export KERAS_HOME=/path/to/DSC_CTC/models/keras-cache
```

`KERAS_HOME` must be defined before importing TensorFlow or StarDist. This
allows the pretrained model to be reused from the shared model cache instead of
being downloaded during every compute session.

The Ultrack database is SQLite. On the shared `/net` filesystem, one linking
worker is used to avoid the database-locking error observed with concurrent
linking workers. Segmentation and Gurobi optimization can still use four
workers or threads:

```python
config.data_config.n_workers = 1
config.segmentation_config.n_workers = 4
config.linking_config.n_workers = 1
config.tracking_config.n_threads = 4
```

The project uses a separate environment for CTC evaluation so the working
tracking environment is not changed. See
[`scripts/README.md`](../../scripts/README.md) for the evaluation command.

## Reusable 2D methods and commands

The completed HeLa and GOWT1 experiments use the following method
configurations. All label-derived methods use a contour sigma of 4 pixels.

| Method | Configuration |
| --- | --- |
| Cellpose | Pretrained `cyto2`; channels `[0, 0]`; automatic diameter; flow threshold 0.4; cell-probability threshold 0; GPU requested |
| StarDist | Pretrained `2D_versatile_fluo`; gamma 1; block size 560; minimum overlap 96 |
| Watershed | Per-frame Otsu foreground; Gaussian sigma 1; h-minima 2; minimum input-object size 20 pixels |
| Ensemble | Logical OR of the three foreground maps; arithmetic mean of the three contour maps; saved labels reused without rerunning inference |

The reusable single-method runner is
[`run_2d_benchmark.py`](../../scripts/ultrack/run_2d_benchmark.py). Set the
dataset variables first. Use the HeLa values here; the GOWT1 section gives the
corresponding GOWT1 values.

```bash
export DATASET=Fluo-N2DL-HeLa
export RUN_PREFIX=hela
export SEQUENCE=01
```

Run Cellpose from the Cellpose environment:

```bash
micromamba activate cell-tracking-ultrack-cellpose
export PYTHONPATH="$PWD/src"

python scripts/ultrack/run_2d_benchmark.py \
    --input-dir "$CTC_ROOT/ctc/$DATASET/$SEQUENCE" \
    --output-dir "$ULTRACK_RUN_ROOT/${RUN_PREFIX}-seq${SEQUENCE}-full-cellpose" \
    --sequence "$SEQUENCE" \
    --method cellpose \
    --cellpose-gpu
```

Run StarDist from the StarDist environment. `KERAS_HOME` must be set before
Python imports TensorFlow or StarDist.

```bash
micromamba activate cell-tracking-ultrack-stardist
export KERAS_HOME=/path/to/DSC_CTC/models/keras-cache

python scripts/ultrack/run_2d_benchmark.py \
    --input-dir "$CTC_ROOT/ctc/$DATASET/$SEQUENCE" \
    --output-dir "$ULTRACK_RUN_ROOT/${RUN_PREFIX}-seq${SEQUENCE}-full-stardist" \
    --sequence "$SEQUENCE" \
    --method stardist
```

Run watershed from the base Ultrack environment:

```bash
micromamba activate cell-tracking-ultrack

python scripts/ultrack/run_2d_benchmark.py \
    --input-dir "$CTC_ROOT/ctc/$DATASET/$SEQUENCE" \
    --output-dir "$ULTRACK_RUN_ROOT/${RUN_PREFIX}-seq${SEQUENCE}-full-watershed" \
    --sequence "$SEQUENCE" \
    --method watershed
```

The single-method runner defaults to four segmentation workers, one linking
worker, and four solver threads. The GOWT1 StarDist sequence 01 run is a known
exception: it used one segmentation worker, so add
`--segmentation-workers 1` when reproducing that particular runtime.

After all three `input_labels` directories exist, run the ensemble from the
base Ultrack environment:

```bash
python scripts/ultrack/run_2d_ensemble.py \
    --input-dir "$CTC_ROOT/ctc/$DATASET/$SEQUENCE" \
    --watershed-label-dir "$ULTRACK_RUN_ROOT/${RUN_PREFIX}-seq${SEQUENCE}-full-watershed/input_labels" \
    --cellpose-label-dir "$ULTRACK_RUN_ROOT/${RUN_PREFIX}-seq${SEQUENCE}-full-cellpose/input_labels" \
    --stardist-label-dir "$ULTRACK_RUN_ROOT/${RUN_PREFIX}-seq${SEQUENCE}-full-stardist/input_labels" \
    --output-dir "$ULTRACK_RUN_ROOT/${RUN_PREFIX}-seq${SEQUENCE}-full-ensemble" \
    --sequence "$SEQUENCE"
```

Repeat each command with `SEQUENCE=02` for the second public training
sequence. Choose a new output directory for a new experiment; use `--overwrite`
only when deliberately replacing a known run.

## Fluo-N2DL-HeLa

### Dataset and comparison target

The targets are the StarDist rows for Files 1 and 2 in Table 3 of the ECCV 2024
Ultrack paper. The published workflow applies a pretrained StarDist
fluorescence model and converts its labels to foreground and contour maps
before running Ultrack.

| Sequence | Metric | Published value | Reproduced value | Difference |
| --- | --- | ---: | ---: | ---: |
| 01 | DET | Not reported | 0.897604 | Not applicable |
| 01 | SEG | 0.724 | 0.701001 | -0.022999 |
| 01 | TRA | 0.910 | 0.894289 | -0.015711 |
| 01 | `OP_CTB` | 0.817 | 0.797645 | -0.019355 |
| 02 | DET | Not reported | 0.923068 | Not applicable |
| 02 | SEG | 0.818 | 0.816860 | -0.001140 |
| 02 | TRA | 0.941 | 0.919480 | -0.021520 |
| 02 | `OP_CTB` | 0.880 | 0.868170 | -0.011830 |

These published values use the public CTC training sequences. Each reproduction
should be compared with the corresponding StarDist row, not with the stronger
ensemble row.
See [Published Ultrack Benchmarks](ultrack-benchmarks.md) for the source and
comparison limits.

### Data and software

| Item | Recorded value |
| --- | --- |
| Tracking method | Ultrack 0.8.0 |
| Paper | [Large-Scale Multi-Hypotheses Cell Tracking Using Ultrametric Contours Maps](https://doi.org/10.1007/978-3-031-72986-7_3) |
| Repository | [`royerlab/ultrack`](https://github.com/royerlab/ultrack) |
| Segmentation input | StarDist 0.9.2 with pretrained `2D_versatile_fluo` model |
| Dataset | `Fluo-N2DL-HeLa` |
| Dataset source | [Cell Tracking Challenge public training archive](https://celltrackingchallenge.net/2d-datasets/) |
| Archive | [`Fluo-N2DL-HeLa.zip`](https://data.celltrackingchallenge.net/training-datasets/Fluo-N2DL-HeLa.zip) |
| Reference archive version | Last modified 2024-01-16; ETag `be1a7cf-60f0f5ba91e40`; 199,337,935 bytes |
| Reference archive SHA-256 | `35dd99d58e071aba0b03880128d920bd1c063783cc280f9531fbdc5be614c82e` (checked 2026-10-21) |
| Input-data provenance | The checksum above identifies the official archive available on 2026-10-21. The runs used an already-extracted shared cluster copy, which was not independently checksummed before the experiments. |
| Sequences | `01` and `02` |
| Frames per sequence | `t000.tif` through `t091.tif` |
| Number of frames per sequence | 92 |
| Image shape | 700 x 1100 pixels |
| Image type | `uint16` |
| Crop or conversion | None; the raw TIFF sequences were read at their original size and type |
| Python | 3.12.15 |
| TensorFlow | 2.21.0 |
| StarDist | 0.9.2 |
| Ultrack | 0.8.0 |
| Solver | Gurobi, `gurobipy` 13.0.3 |
| Project repository commit | The notebooks were run from an uncommitted working copy. They were first committed in `70c2dae` (2026-10-20 22:52 CDT), with lint-only changes in `4229d0f`. The evaluation script was committed in `cfea879`. |
| GPU | Not used; TensorFlow reported no available CUDA device |

The tracking notebooks were executed using the Jupyter kernel associated with
the `cell-tracking-ultrack-stardist` environment. The package versions above
were printed by the executed notebook. The project environments relevant to
the Ultrack experiments are:

| Environment | Purpose | Committed recipe |
| --- | --- | --- |
| `cell-tracking-ultrack` | Ultrack without an optional segmentation model | [`environments/ultrack.yaml`](../../environments/ultrack.yaml) |
| `cell-tracking-ultrack-stardist` | Completed StarDist-to-Ultrack tracking notebooks | [`environments/ultrack-stardist.yaml`](../../environments/ultrack-stardist.yaml) |
| `cell-tracking-ctc-evaluation` | CTC validation and metric calculation | [`environments/ctc-evaluation.yaml`](../../environments/ctc-evaluation.yaml) |

The absolute micromamba installation paths are user-specific and are therefore
not part of the reproducibility record. Recreate the combined Ultrack and
StarDist environment from the committed recipe:

```bash
micromamba create --file environments/ultrack-stardist.yaml
micromamba activate cell-tracking-ultrack-stardist
python -m pip install -e .
```

### StarDist configuration

Each image was normalized independently with Ultrack's `normalize` function
using `gamma=1.0`. Instance labels were then predicted with the pretrained
StarDist `2D_versatile_fluo` model.

| Parameter | Value |
| --- | --- |
| Model | `2D_versatile_fluo` |
| Prediction method | `predict_instances_big` |
| Axes | `YX` |
| Block size | 560 |
| Minimum overlap | 96 |
| Probability threshold | Model default, 0.479071 |
| Non-maximum-suppression threshold | Model default, 0.3 |

The pretrained model was loaded from the shared Keras cache. This stage is
inference, not training: the model weights were not updated.

The instance labels were converted to Ultrack inputs with:

```python
foreground, contours = labels_to_contours(stardist_labels, sigma=4.0)
```

The sparse gold segmentation was displayed only as a qualitative checkpoint.
Different display colors identify different instance-label values; they do not
represent cell type, confidence, or tracking identity.

### Ultrack configuration

The run used Ultrack defaults except for the run directory, worker settings,
and requested solver:

```python
config = MainConfig()
config.data_config.working_dir = RUN_DIR
config.data_config.n_workers = 1
config.segmentation_config.n_workers = 4
config.linking_config.n_workers = 1
config.tracking_config.n_threads = 4
config.tracking_config.solver_name = "GUROBI"
```

The resolved configuration printed by the notebook, which includes all Ultrack
0.8.0 defaults, was:

```text
SegmentationConfig(min_area=100, min_area_factor=4.0, max_area=1000000, n_workers=4,
    min_frontier=0.0, threshold=0.5, max_noise=0.0, random_seed='frame',
    ws_hierarchy=watershed_hierarchy_by_area, anisotropy_penalization=0.0)
LinkingConfig(max_distance=15.0, n_workers=1, max_neighbors=5, distance_weight=0.0,
    z_score_threshold=5.0)
TrackingConfig(solver_name='GUROBI', appear_weight=-0.001, disappear_weight=-0.001,
    division_weight=-0.001, image_border_size=None, n_threads=4, window_size=None,
    overlap_size=1, solution_gap=0.001, time_limit=36000, method=0,
    link_function='power', power=4, bias=-0.0)
```

Defaults can change between Ultrack versions, so this record is more reliable
than stating that defaults were used.

The notebook keeps segmentation, linking, and solving in separate cells. This
makes it possible to diagnose a failed stage without rerunning StarDist
inference or all preceding Ultrack stages.

### Full-sequence run records

| Stage | Parallel setting | Sequence 01 runtime | Sequence 02 runtime |
| --- | ---: | ---: | ---: |
| StarDist inference | CPU inference | 118.60 seconds | 132.27 seconds |
| Label-to-contour conversion | CPU | approximately 4 seconds | approximately 5 seconds |
| Ultrack segmentation hypotheses | 4 workers | 1,352.83 seconds | 796.51 seconds |
| Ultrack linking | 1 worker | 701.13 seconds | 371.59 seconds |
| Ultrack optimization | 4 Gurobi threads | 14.31 seconds | 167.90 seconds |

The long segmentation and linking times are expected for the complete sequence.
Progress can remain unchanged while a worker is processing a frame, so a
stationary progress bar alone does not show that the process is deadlocked.

Apart from the SQLite locking error that was avoided by using one linking
worker, the only warnings were TensorFlow/absl start-up messages (for example,
"All log messages before absl::InitializeLog() is called are written to
STDERR") and the message that no CUDA device was available. Neither affected
the results.

The remaining execution metadata are:

| Item | Recorded value |
| --- | --- |
| Execution interface | Jupyter notebooks in an interactive Slurm allocation on the DSI cluster |
| Slurm job ID | `2216344` for both sequences |
| Slurm state and window | `COMPLETED`; 2026-10-20 20:38:36--22:59:06 CDT |
| Slurm resources | `general` partition; node `j002-ds`; 4 allocated CPUs; 16 GB requested memory |
| Hardware | CPU-only; CPU model was not recorded |
| Sequence 01 export timestamp | 2026-10-20 21:21:11 CDT |
| Sequence 02 export timestamp | 2026-10-20 22:50:33 CDT |
| Peak memory | Slurm `MaxRSS` was 11,122,900 KiB (about 10.6 GiB) for the `extern` step and 1,425,296 KiB for the `bash` step. The notebook kernel was started through a VS Code SSH connection to the compute node, which places it in the `extern` step, so 10.6 GiB is the best estimate of the notebook's peak memory. Both sequences ran in the same job, so this is the peak across both runs, not per sequence. It is about two-thirds of the 16 GB requested. |
| Random seed | No explicit seed was set; Ultrack 0.8.0 reported its default segmentation seed as `frame` |

Both completed exports contained 92 CTC masks, `mask000.tif` through
`mask091.tif`, and a `res_track.txt` lineage file. Their track-table and lineage
counts differed:

| Output | Sequence 01 | Sequence 02 |
| --- | ---: | ---: |
| Track-table rows | 8,448 | 26,342 |
| Unique track IDs | 290 | 836 |
| Lineage graph entries | 42 | 182 |

These counts confirm that the workflow completed and produced a structurally
complete result. They do not measure tracking accuracy; the CTC metrics provide
that assessment.

### Output layout

Each full run uses a descriptive run directory and exports its CTC submission
under the sequence-specific result name:

```text
<ULTRACK_RUN_ROOT>/hela-seq01-full-stardist/
├── data.db
├── segments.zarr/
├── stardist_labels/
├── tracks.csv
└── 01_RES/
    ├── mask000.tif
    ├── ...
    ├── mask091.tif
    └── res_track.txt

<ULTRACK_RUN_ROOT>/hela-seq02-full-stardist/
├── data.db
├── segments.zarr/
├── stardist_labels/
├── tracks.csv
└── 02_RES/
    ├── mask000.tif
    ├── ...
    ├── mask091.tif
    └── res_track.txt
```

The earlier five-frame check uses `subset_RES` instead. This name prevents a
subset from being mistaken for a complete CTC sequence during evaluation.

These directory names do not follow the
`runs/<date>_<method>_<dataset>_<short-description>/` convention in
[`docs/reproducibility.md`](../reproducibility.md). They were created before
that convention was applied. No `metadata.yaml` was written for these runs;
this document is their run record. The `run_report.json` written by
`run_2d_benchmark.py` does not exist for these runs because they were executed
from the notebooks, not the script.

### Evaluation results and commands

The complete `01_RES` and `02_RES` outputs passed structural validation and
were evaluated with the pinned `py-ctcmetrics` 1.3.3 environment. The
evaluations produced:

| Metric | Sequence 01 | Sequence 02 |
| --- | ---: | ---: |
| Valid | 1 | 1 |
| DET | 0.897604 | 0.923068 |
| SEG | 0.701001 | 0.816860 |
| TRA | 0.894289 | 0.919480 |
| `OP_CTB` | 0.797645 | 0.868170 |

Evaluation was much faster than the tracking workflow because it operated on
the completed masks and lineage graph. It did not repeat StarDist inference,
segmentation-hypothesis generation, linking, or optimization.

For sequence 01, the reproduced SEG, TRA, and `OP_CTB` values are respectively
0.022999, 0.015711, and 0.019355 below the published StarDist values. For
sequence 02, they are respectively 0.001140, 0.021520, and 0.011830 below the
published values. Sequence 02 therefore nearly reproduces the published
segmentation score, while its larger difference is in tracking.

The results are numerically close to both published rows, but the differences
should not be treated as random error without further evidence. Possible
contributors include StarDist, TensorFlow, and Ultrack version differences;
preprocessing details; model thresholds; and Ultrack defaults that were not
fully specified in the publication.

The known software differences are:

| Component | Authors' published setup | This reproduction |
| --- | --- | --- |
| Ultrack | Not reported for the HeLa experiments. The authors' 3D CTC submission repository builds on the `royerlab/ultrack:0.6.1-cuda11.8` image. | 0.8.0 |
| `gurobipy` | Not reported for the HeLa experiments. The 3D CTC submission pins 11.0.3. | 13.0.3 |
| StarDist | Not reported | 0.9.2 |
| TensorFlow | Not reported | 2.21.0 |

We did not find the software versions used for the HeLa experiments in the
paper or in the authors' public
[`ultrack_CTC_submission`](https://github.com/royerlab/ultrack_CTC_submission/tree/submission-2023-10)
repository, which contains only the 3D dataset workflows. The 3D submission
versions are listed for context only; they do not show which versions produced
the HeLa table values.

The full JSON and CSV reports remain with the run outputs on cluster storage.
Only a sanitized metric summary should be committed because the raw reports
record absolute cluster paths.

The same evaluation script was used for both sequences. The sequence-specific
ground-truth directory, result directory, and published reference values were
changed as shown below. The documented environment variables keep private
cluster paths out of the repository.

Sequence 01:

```bash
python scripts/ultrack/evaluate_ctc_result.py \
    --ground-truth-dir "$CTC_ROOT/ctc/Fluo-N2DL-HeLa/01_GT" \
    --result-dir "$ULTRACK_RUN_ROOT/hela-seq01-full-stardist/01_RES" \
    --dataset Fluo-N2DL-HeLa \
    --method ultrack-stardist-2D_versatile_fluo \
    --published-seg 0.724 \
    --published-tra 0.910 \
    --published-ctb 0.817 \
    --num-workers 4
```

Sequence 02:

```bash
python scripts/ultrack/evaluate_ctc_result.py \
    --ground-truth-dir "$CTC_ROOT/ctc/Fluo-N2DL-HeLa/02_GT" \
    --result-dir "$ULTRACK_RUN_ROOT/hela-seq02-full-stardist/02_RES" \
    --dataset Fluo-N2DL-HeLa \
    --method ultrack-stardist-2D_versatile_fluo \
    --published-seg 0.818 \
    --published-tra 0.941 \
    --published-ctb 0.880 \
    --num-workers 4
```

These commands were run from the repository root using the
`cell-tracking-ctc-evaluation` environment.

### Executable records and environment notes

The executable records for these experiments are:

- [`02_hela_stardist_seq01_benchmark.ipynb`](../../notebooks/ultrack/02_hela_stardist_seq01_benchmark.ipynb); and
- [`02_hela_stardist_seq02_benchmark.ipynb`](../../notebooks/ultrack/02_hela_stardist_seq02_benchmark.ipynb).

The reusable runner extracts the common raw-image loading, label saving,
label-to-contour conversion, Ultrack stages, CTC export, and run reporting
from these notebooks. Its `--method` option supports StarDist, watershed, and
Cellpose without duplicating the tracking workflow. All three single-method
workflows are complete and evaluated for both HeLa sequences. Their numerical
results and interpretation are recorded in
[`ultrack-results.md`](ultrack-results.md).

Cellpose uses the separate `cell-tracking-ultrack-cellpose` environment, which
pins NumPy 2.0.2 for compatibility with Cellpose 3. The project source is made
available with `export PYTHONPATH="$PWD/src"` rather than an editable install,
because the main project currently requires NumPy 2.2 or newer.

The reusable
[`run_2d_ensemble.py`](../../scripts/ultrack/run_2d_ensemble.py) script combines
the saved foreground maps with logical OR, averages their contour maps, and
runs the common Ultrack stages without rerunning the segmentation models.

Plots remain in the notebooks, but verbose solver outputs are cleared before
committing because they can contain identifying license information.

## Fluo-N2DH-GOWT1

### Dataset and comparison scope

Both public training sequences, `01` and `02`, contain 92 frames and were run
with Cellpose, StarDist, watershed, and the three-method ensemble. The ECCV
2024 Ultrack paper does not report a matching GOWT1 experiment. These runs are
therefore additional project experiments, not reproductions of a published
Ultrack benchmark.

Gold segmentation and tracking annotations were used only for evaluation and
visual review. They were not supplied to the segmentation methods, ensemble,
or Ultrack.

### Configuration

GOWT1 uses the same four method configurations and reusable scripts documented
in [Reusable 2D methods and commands](#reusable-2d-methods-and-commands). The
dataset-specific execution details are:

| Item | Recorded value |
| --- | --- |
| Dataset | `Fluo-N2DH-GOWT1` |
| Sequences | `01` and `02` |
| Frames per sequence | 92 |
| Cellpose hardware | NVIDIA A100 80GB PCIe |
| StarDist sequence 01 segmentation workers | 1 |
| StarDist sequence 02 segmentation workers | 4 |
| Matching published Ultrack result | None |

The unequal StarDist worker counts mean that its sequence 01 and sequence 02
runtimes are not directly comparable. The ensemble run reports record the
method combination and stage runtimes but do not capture the worker settings
or hardware allocation.

### Commands

Set the GOWT1 dataset variables, then use the Cellpose, StarDist, watershed,
and ensemble commands from the reusable 2D section:

```bash
export DATASET=Fluo-N2DH-GOWT1
export RUN_PREFIX=gowt1
export SEQUENCE=01
```

For the historical StarDist sequence 01 configuration, append
`--segmentation-workers 1` to the single-method command. Repeat the workflows
with `SEQUENCE=02`; the sequence 02 StarDist run used the default four
segmentation workers.

### Evaluation

GOWT1 evaluation omits the `--published-*` arguments because there is no
matching published Ultrack row. For example:

```bash
export SEQUENCE=01
export METHOD=cellpose

python scripts/ultrack/evaluate_ctc_result.py \
    --ground-truth-dir "$CTC_ROOT/ctc/Fluo-N2DH-GOWT1/${SEQUENCE}_GT" \
    --result-dir "$ULTRACK_RUN_ROOT/gowt1-seq${SEQUENCE}-full-${METHOD}/${SEQUENCE}_RES" \
    --dataset Fluo-N2DH-GOWT1 \
    --method "ultrack-$METHOD" \
    --num-workers 4
```

Set `METHOD` to `cellpose`, `stardist`, `watershed`, or `ensemble`, and repeat
with `SEQUENCE=02`. The completed scores, run-report summaries, cross-method
comparison, and ensemble carry-over hypothesis are recorded in the
[GOWT1 results section](ultrack-results.md#fluo-n2dh-gowt1).

## Fluo-C3DL-MDA231

### Dataset and comparison target

The project reproduced the authors' official U-Net-to-Ultrack workflow on
public training sequence 01. The ECCV paper reports the following result for
the separate hidden CTC test set:

| Evaluation split | SEG | TRA | `OP_CTB` |
| --- | ---: | ---: | ---: |
| Hidden CTC test set | 0.549 | 0.818 | 0.683 |

The hidden test annotations are not publicly available. The project result is
therefore a method reproduction on public training data, not a direct
numerical reproduction of the published hidden-test score.

### Data and software

| Item | Recorded value |
| --- | --- |
| Dataset | `Fluo-C3DL-MDA231` |
| Selected sequence | `01` |
| Raw frames | `t000.tif` through `t011.tif` |
| Number of frames | 12 |
| Raw volume shape | 30 x 512 x 512 voxels `(Z, Y, X)` |
| Image type | `uint16` |
| Submission code | [`royerlab/ultrack_CTC_submission`, branch `submission-2023-10`](https://github.com/royerlab/ultrack_CTC_submission/tree/submission-2023-10) |
| Submission repository commit | `fa6a20a64ac9e95893d4c0747bb20d333f731d49` |
| Sequence script | `Fluo-C3DL-MDA231-01.sh` |
| Model checkpoint | Published `Fluo-C3DL-MDA231.ckpt`; no local training or fine-tuning |
| Checkpoint SHA-256 | `d4215cdb4c4fc4fb1ef51b7e95a36f33394b046e21207f6e95f1983dc0f8203c` |
| Checkpoint acquisition date | 2026-10-27 |
| Container base | `docker.io/royerlab/ultrack:0.6.1-cuda11.8` |
| Solver | Gurobi WLS using the version pinned by the authors' container |
| GPU | NVIDIA A40; 46,068 MiB available |
| Container runtime | Apptainer SIF built from the authors' Docker image |
| Run date | 2026-10-27 |

The sparse gold segmentation contains selected 2D z-slices named
`man_seg_TTT_ZZZ.tif`. For example, `man_seg_000_013.tif` annotates z-slice 13
of frame 000; it is not a complete 3D segmentation volume. The tracking ground
truth contains complete 3D masks for the 12 public training frames.

### Published U-Net and Ultrack configuration

The authors' `EdgeUNet` predicts voxelwise foreground and boundary maps. The
published checkpoint is used directly; retraining is not part of this
reproduction. The official sequence script applies the complete
preprocessing, inference, Ultrack, and export workflow:

| Stage | Parameter | Value |
| --- | --- | --- |
| Normalization | Lower quantile | `0.0001` |
| Normalization | Upper quantile | `0.9999` |
| Resampling | Z interpolation factor | `5` |
| U-Net inference | Tile shape | `(150, 512, 512)` |
| U-Net inference | Tile overlap | `(0, 0, 0)` |
| Boundary output | Gaussian sigma | `(0.5, 0.5, 0.5)` |
| Ultrack | Dataset configuration | `Fluo-C3DL-MDA231/config.toml` |
| CTC export | Scale | `(0.2, 1, 1)` |
| CTC export | Margin | `25` |
| CTC export | Dilation iterations | `1` |

The predicted foreground is passed to Ultrack as the detection layer, and the
smoothed boundary prediction is passed as the edge layer. The official script
then runs Ultrack segmentation, linking, solving, and CTC export. Gold
segmentation and tracking annotations are used only for evaluation.

### Container environment

The official submission uses older pinned dependencies and must remain
separate from the project's Ultrack 0.8 environments. Docker is unavailable on
the cluster, so the successful workflow builds the image with rootless Podman,
converts it to an Apptainer SIF, and uses Apptainer's `--nv` support at run
time.

Set the storage locations and obtain the official repository and checkpoint:

```bash
export CTC_ROOT=/path/to/DSC_CTC
export ULTRACK_CTC_REPO="$CTC_ROOT/models/ultrack_CTC_submission"
export CONTAINER_ROOT="$ULTRACK_CTC_REPO/container"
export CONTAINER_TAR="$CONTAINER_ROOT/ultrack-ctc.tar"
export CONTAINER_SIF="$CONTAINER_ROOT/ultrack-ctc.sif"

git clone --branch submission-2023-10 --single-branch \
    https://github.com/royerlab/ultrack_CTC_submission.git \
    "$ULTRACK_CTC_REPO"

mkdir -p "$ULTRACK_CTC_REPO/weights"
wget -nc -P "$ULTRACK_CTC_REPO/weights" \
    https://public.czbiohub.org/royerlab/ultrack/CTC/weights/2023_10/Fluo-C3DL-MDA231.ckpt
```

Record the exact source and checkpoint identities before execution:

```bash
git -C "$ULTRACK_CTC_REPO" rev-parse HEAD
sha256sum "$ULTRACK_CTC_REPO/weights/Fluo-C3DL-MDA231.ckpt"
```

The recorded identities are:

| Item | Recorded value |
| --- | --- |
| Repository branch | `submission-2023-10` |
| Repository commit | `fa6a20a64ac9e95893d4c0747bb20d333f731d49` |
| Checkpoint path | `weights/Fluo-C3DL-MDA231.ckpt` |
| Checkpoint SHA-256 | `d4215cdb4c4fc4fb1ef51b7e95a36f33394b046e21207f6e95f1983dc0f8203c` |
| Checkpoint source | [Official CZ Biohub URL used by the authors' `download.sh`](https://public.czbiohub.org/royerlab/ultrack/CTC/weights/2023_10/Fluo-C3DL-MDA231.ckpt) |

The `wget -nc` option prevents an existing checkpoint from being overwritten,
but it does not validate the file. The recorded SHA-256 must be checked before
reuse. A different hash must be treated as a different model artifact until
its provenance is established.

Build the authors' Dockerfile with its fully qualified base-image name. The
`cgroupfs` setting is required for rootless Podman inside a Slurm allocation:

```bash
cd "$ULTRACK_CTC_REPO"
unset XDG_RUNTIME_DIR

podman --cgroup-manager=cgroupfs build \
    --from docker.io/royerlab/ultrack:0.6.1-cuda11.8 \
    --tag ultrack-ctc \
    .
```

Save and convert the image. Apptainer's cache and temporary directories must
be placed in shared storage because unpacking the image exceeds the compute
node's `/tmp` capacity:

```bash
mkdir -p "$CONTAINER_ROOT"

podman save \
    --format docker-archive \
    --output "$CONTAINER_TAR" \
    localhost/ultrack-ctc:latest

export APPTAINER_TMPDIR="$CONTAINER_ROOT/apptainer-tmp"
export APPTAINER_CACHEDIR="$CONTAINER_ROOT/apptainer-cache"
export TMPDIR="$APPTAINER_TMPDIR"

mkdir -p "$APPTAINER_TMPDIR" "$APPTAINER_CACHEDIR"

apptainer build \
    "$CONTAINER_SIF" \
    docker-archive:"$CONTAINER_TAR"
```

The completed Podman image was 17.4 GB, and the SIF was 6.9 GB. Confirm that
the SIF exposes the allocated GPU and that PyTorch can use CUDA:

```bash
apptainer exec --nv "$CONTAINER_SIF" nvidia-smi

apptainer exec --nv "$CONTAINER_SIF" \
    python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

### Full-sequence execution

The official script writes its result below `DATA_DIR`, so the shared CTC
dataset must not be used as the writable output root. Copy the 12 raw volumes
into a private run directory. A copy is used instead of an external symbolic
link because the link target would not be visible at the container mount
point.

```bash
export MDA_RUN_ROOT="$CTC_ROOT/runs/ultrack/mda231-seq01-official-unet"
export GRB_LICENSE_FILE=/path/to/gurobi.lic

mkdir -p "$MDA_RUN_ROOT/data/Fluo-C3DL-MDA231/01"
mkdir -p "$MDA_RUN_ROOT/work"

cp "$CTC_ROOT/ctc/Fluo-C3DL-MDA231/01/"t*.tif \
    "$MDA_RUN_ROOT/data/Fluo-C3DL-MDA231/01/"

find "$MDA_RUN_ROOT/data/Fluo-C3DL-MDA231/01" \
    -maxdepth 1 -name 't*.tif' | wc -l
```

The frame count must be 12. Run the official sequence script inside the SIF:

```bash
apptainer exec --nv --writable-tmpfs \
    --bind "$ULTRACK_CTC_REPO/weights:/app/weights:ro" \
    --bind "$MDA_RUN_ROOT/data:/app/data" \
    --bind "$MDA_RUN_ROOT/work:/wkdir" \
    --bind "$GRB_LICENSE_FILE:/tmp/gurobi.lic:ro" \
    --env DATA_DIR=/app/data \
    --env WK_DIR=/wkdir \
    --env GRB_LICENSE_FILE=/tmp/gurobi.lic \
    "$CONTAINER_SIF" \
    bash -lc 'cd /app && bash Fluo-C3DL-MDA231-01.sh'
```

`--writable-tmpfs` supplies the writable layer needed for the script's local
Ultrack database. The persistent image arrays, predictions, and CTC result are
written through the bound data and work directories.

Apptainer reported a FUSE-overlay cleanup warning after all 12 masks had been
exported. This was treated as nonfatal only after the complete result passed
CTC validation.

### Slurm job and hardware record

The official MDA231 workflow ran inside interactive Slurm allocation
`2259559`. The workflow and evaluation completed while the surrounding
interactive `bash` job remained active. The resource values below are a live
snapshot taken after 2:29:31 of allocation time; the final scheduler state and
elapsed time must be updated after the shell exits.

Capture the active allocation and GPU before execution:

```bash
printf 'SLURM_JOB_ID=%s\n' "${SLURM_JOB_ID:-not-set}"
hostname
nvidia-smi \
    --query-gpu=name,memory.total,driver_version \
    --format=csv,noheader
```

After the job, record its scheduler history using the actual job ID:

```bash
export MDA_JOB_ID=2259559

sacct -j "$MDA_JOB_ID" \
    --format=JobID,JobName,Partition,State,Elapsed,AllocCPUS,ReqMem,MaxRSS,NodeList,AllocTRES
```

| Job field | Recorded value |
| --- | --- |
| Slurm job ID | `2259559` |
| Job name and command | Interactive `bash`; `/bin/bash` |
| Account and QOS | `general_group`; `general` |
| Partition and node | `general`; `g004` |
| Start time | 2026-10-27 20:43:03 |
| Time limit | 4 hours |
| State at snapshot | `RUNNING`; final state pending |
| Elapsed time at snapshot | 2:29:31; final elapsed time pending |
| Allocation | 1 node; 4 CPUs; 32 GB requested memory; 1 GPU |
| GPU | NVIDIA A40; 46,068 MiB available |
| GPU driver | Pending |
| Main-step MaxRSS at snapshot | 33,384,332 KiB, approximately 31.8 GiB |
| Extern-step MaxRSS at snapshot | 1,154,532 KiB, approximately 1.1 GiB |
| Main-step average CPU time at snapshot | 1:50:09 |

The main-step MaxRSS is close to the 32 GB memory request. Because this value
covers the entire interactive `.0` step rather than an isolated invocation of
the MDA231 script, it is a conservative allocation record, not a precise model
inference requirement. Future reproductions should request at least the same
memory unless a controlled run measures the script separately. The validated
CTC output proves that the workflow produced a complete result; it does not
replace the final scheduler record needed to confirm how the interactive
allocation ended.

### Output layout

The successful run produced:

```text
<CTC_ROOT>/runs/ultrack/mda231-seq01-official-unet/
├── data/Fluo-C3DL-MDA231/
│   ├── 01/
│   │   ├── t000.tif
│   │   └── ... t011.tif
│   ├── 01_RES/
│   │   ├── mask000.tif
│   │   ├── ... mask011.tif
│   │   └── res_track.txt
│   └── evaluation/01_RES/
│       ├── ctc_metrics.csv
│       └── ctc_metrics.json
└── work/Fluo-C3DL-MDA231/01/
    ├── image.zarr/
    └── image_pred_both.zarr/
```

The 12 result masks and nonempty lineage file confirm structural completion;
the CTC evaluator provides the accuracy and validity checks.

### Evaluation results and command

Run evaluation from the project repository, not from the authors' submission
repository:

```bash
cd /path/to/clinic-2026-cell-tracking
micromamba activate cell-tracking-ctc-evaluation

python scripts/ultrack/evaluate_ctc_result.py \
    --ground-truth-dir "$CTC_ROOT/ctc/Fluo-C3DL-MDA231/01_GT" \
    --result-dir "$MDA_RUN_ROOT/data/Fluo-C3DL-MDA231/01_RES" \
    --dataset Fluo-C3DL-MDA231 \
    --method ultrack-official-unet \
    --num-workers 4
```

The public-sequence result passed validation:

| Valid | DET | SEG | TRA | `OP_CTB` |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0.909341 | 0.385566 | 0.901970 | 0.643768 |

The evaluation reports remain with the cluster run under
`data/Fluo-C3DL-MDA231/evaluation/01_RES/`. Interpretation and the split-aware
comparison with the authors' hidden-test result are recorded in the
[MDA231 results section](ultrack-results.md#fluo-c3dl-mda231). The executable
preparation record is
[`03_mda231_seq01_benchmark.ipynb`](../../notebooks/ultrack/03_mda231_seq01_benchmark.ipynb).

## Adding another dataset

Add one section per dataset and segmentation input. Use the following minimum
structure so experiments remain comparable:

```text
## Dataset: segmentation input

### Reproduction target
Published source, split, method, and metric values.

### Data and software
Sequence, frames, dimensions, versions, and compute type.

### Segmentation input
Model or algorithm, weights, normalization, and non-default parameters.

### Ultrack configuration
Worker settings, solver, and all other non-default values.

### Run record
Stage runtimes, output counts, warnings, and resolved failures.

### Evaluation
Reproduced metrics, published metrics, differences, and limitations.
```

Do not combine results from different sequences, segmentation inputs, or data
splits in one comparison row. If a compatible published benchmark is not
available, describe the run as an additional experiment rather than a direct
reproduction.
