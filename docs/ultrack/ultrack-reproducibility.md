# Ultrack benchmark reproducibility

- [Ultrack benchmark reproducibility](#ultrack-benchmark-reproducibility)
  - [Purpose](#purpose)
  - [Methodology and status overview](#methodology-and-status-overview)
  - [Results](#results)
  - [General workflow](#general-workflow)
  - [Shared cluster conventions](#shared-cluster-conventions)
  - [Fluo-N2DL-HeLa: StarDist input](#fluo-n2dl-hela-stardist-input)
    - [Reproduction target](#reproduction-target)
    - [Data and software](#data-and-software)
    - [StarDist inference](#stardist-inference)
    - [Ultrack configuration](#ultrack-configuration)
    - [Full-sequence run records](#full-sequence-run-records)
    - [Output layout](#output-layout)
    - [Evaluation results](#evaluation-results)
  - [Fluo-C3DL-MDA231: published U-Net and raw baseline](#fluo-c3dl-mda231-published-u-net-and-raw-baseline)
    - [Reproduction target](#reproduction-target-1)
    - [Data](#data)
    - [Published 3D U-Net methodology](#published-3d-u-net-methodology)
    - [Published-workflow resource requirements](#published-workflow-resource-requirements)
    - [Project raw-image subset methodology](#project-raw-image-subset-methodology)
    - [Evaluation and reporting rules](#evaluation-and-reporting-rules)
  - [Adding another dataset](#adding-another-dataset)

## Purpose

This document records how the project runs and evaluates Ultrack benchmarks.
It is intended to grow as additional datasets and segmentation inputs are
tested. Each dataset section should state exactly what was reproduced, what was
changed, and which comparisons are valid.

The first complete experiments use both `Fluo-N2DL-HeLa` training sequences
with a pretrained StarDist model. No model was trained or fine-tuned during
these runs. StarDist performed inference to create instance labels, and
Ultrack used those labels to construct and select tracks.

The 3D `Fluo-C3DL-MDA231` work has two distinct methodologies. The project
first runs a small raw-image baseline to confirm that the 3D Ultrack pipeline
works. The published benchmark instead uses a trained 3D U-Net and requires a
separate GPU environment. These experiments are documented separately so the
raw baseline is not mistaken for a reproduction of the published result.

## Methodology and status overview

The ECCV paper used or compared several segmentation inputs. Only methods
actually run by this project are marked as reproduced or in progress.

| Dataset | Segmentation input | Role | Project status | Valid comparison |
| --- | --- | --- | --- | --- |
| `Fluo-N2DL-HeLa` | Watershed | Published single-method comparator | Complete and evaluated for sequences 01 and 02 | Compare with the matching published watershed row, while documenting the incomplete parameter specification |
| `Fluo-N2DL-HeLa` | Cellpose `cyto2` | Published single-method comparator | Not run | Published values only |
| `Fluo-N2DL-HeLa` | StarDist `2D_versatile_fluo` | Selected reproduction method | Complete for sequences 01 and 02 | Compare with the matching published StarDist row |
| `Fluo-N2DL-HeLa` | Watershed + Cellpose + StarDist ensemble | Best published experiment for these sequences | Not run | Published values only |
| `Fluo-C3DL-MDA231` | Trained 3D U-Net foreground and boundary maps | Published CTC submission method | Documented; GPU run not yet completed | A public-training run may be compared descriptively, but cannot reproduce the hidden-test score directly |
| `Fluo-C3DL-MDA231` | Raw-image foreground and contour processing | Project 3D subset baseline | In progress for frames 000--002 | Qualitative and sparse-slice checks only; not the published benchmark |

For HeLa, the paper converted every segmentation method's instance labels into
a binary foreground map and a contour map. Its ensemble combined foreground
maps with a logical OR and averaged the contour maps. This project selected
StarDist first because the paper used publicly available pretrained weights
without dataset-specific fine-tuning. Reproducing the other three HeLa rows
would be separate experiments and would require recording their own inputs,
parameters, runtimes, and result directories.

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

## Fluo-N2DL-HeLa: StarDist input

### Reproduction target

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

### StarDist inference

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

### Evaluation results

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

The executable records for these experiments are:

- [`02_hela_stardist_seq01_benchmark.ipynb`](../../notebooks/ultrack/02_hela_stardist_seq01_benchmark.ipynb); and
- [`02_hela_stardist_seq02_benchmark.ipynb`](../../notebooks/ultrack/02_hela_stardist_seq02_benchmark.ipynb).

The reusable
[`run_2d_benchmark.py`](../../scripts/ultrack/run_2d_benchmark.py) script
extracts the common raw-image loading, label saving, label-to-contour
conversion, Ultrack stages, CTC export, and run reporting from these notebooks.
Its `--method` option supports StarDist, watershed, and Cellpose so the latter
two methods can be run without duplicating the tracking workflow. Watershed
and Cellpose results must remain marked as pending until their subset labels,
complete outputs, and CTC evaluations have been inspected.

Plots remain in the notebooks, but verbose solver outputs are cleared before
committing because they can contain identifying license information.

## Fluo-C3DL-MDA231: published U-Net and raw baseline

### Reproduction target

The ECCV paper reports the following result for the authors' CTC submission:

| Evaluation split | SEG | TRA | CTB |
| --- | ---: | ---: | ---: |
| Hidden CTC test set | 0.549 | 0.818 | 0.683 |

The project has the public CTC training sequences and annotations, not the
hidden test annotations used for this table. Consequently, even a successful
run with the authors' code and checkpoint is a method reproduction on a
different evaluation split, not a direct numerical reproduction of the
published hidden-test result.

### Data

| Item | Recorded value |
| --- | --- |
| Dataset | `Fluo-C3DL-MDA231` |
| Selected sequence | `01` |
| Raw frames | `t000.tif` through `t011.tif` |
| Number of frames | 12 |
| Raw volume shape | 30 x 512 x 512 voxels `(Z, Y, X)` |
| Image type | `uint16` |
| Sparse gold segmentation | Selected 2D z-slices named `man_seg_TTT_ZZZ.tif` |
| Tracking ground truth | Complete 3D masks for the 12 public training frames |

The sparse segmentation filenames contain both a time index and a z-slice
index. For example, `man_seg_000_013.tif` annotates z-slice 13 of frame 000; it
is not a complete 3D segmentation volume.

### Published 3D U-Net methodology

For MDA231, the authors trained a 3D U-Net to predict two voxelwise outputs:
cell foreground and cell boundaries. The published submission code calls this
network `EdgeUNet`. It uses 3D convolutions, feature widths of 32, 64, 128, and
256, a kernel size of 5, linear interpolation in the decoder, and no residual
connections or batch normalization.

The paper's supplementary methodology reports:

- 20 training epochs;
- an initial learning rate of `1e-4`;
- exponential learning-rate decay of `0.95` after each epoch; and
- both public training sequences for learning the final submission weights.

Retraining is not required for the first reproduction attempt because the
authors published the pretrained `Fluo-C3DL-MDA231.ckpt` checkpoint. The
project should use the authors' checkpoint before considering any locally
trained alternative.

The official sequence 01 script applies the following preprocessing and
inference settings:

| Stage | Parameter | Published submission value |
| --- | --- | --- |
| Normalization | Lower quantile | `0.0001` |
| Normalization | Upper quantile | `0.9999` |
| Resampling | Z interpolation factor | `5` |
| U-Net inference | Tile shape | `(150, 512, 512)` |
| U-Net inference | Tile overlap | `(0, 0, 0)` |
| Boundary output | Gaussian sigma | `(0.5, 0.5, 0.5)` |
| CTC export | Scale | `(0.2, 1, 1)` |
| CTC export | Margin | `25` |
| CTC export | Dilation iterations | `1` |

The U-Net's foreground prediction is passed to Ultrack as the detection layer,
and its smoothed boundary prediction is passed as the edge layer. Ultrack then
performs segmentation-hypothesis generation, linking, optimization, and CTC
export using the dataset-specific configuration in the authors' repository.

The authoritative implementation is the
[`submission-2023-10` branch of `royerlab/ultrack_CTC_submission`](https://github.com/royerlab/ultrack_CTC_submission/tree/submission-2023-10).
The project notebook references that implementation instead of copying and
maintaining a second version of the U-Net architecture.

### Published-workflow resource requirements

The authors document an NVIDIA GPU with at least 12 GB of memory for inference;
their run was tested with a 24 GB GPU. Their Docker workflow also requires a
Gurobi WLS license. Training a new U-Net may require at least 24 GB of GPU
memory, but training is outside the first reproduction attempt because
pretrained weights are available.

The official workflow uses older pinned submission code and dependencies. It
should therefore run in its own environment or container rather than being
merged into the current Ultrack 0.8 CPU environment without validation. A run
record must include:

- the submission repository commit and branch;
- the checkpoint path and file identity;
- the environment or container identifier;
- the GPU model and available memory from `nvidia-smi`;
- the exact sequence script and any local changes;
- the normalization, inference, Ultrack, and export runtimes; and
- all deviations from the authors' configuration.

The executable preparation and validation record is
[`03_mda231_seq01_benchmark.ipynb`](../../notebooks/ultrack/03_mda231_seq01_benchmark.ipynb).
It uses a private staging directory because the official script writes a
`01_RES` directory below its configured data root. The shared CTC dataset must
not be used as that writable output root.

### Project raw-image subset methodology

Before attempting the separate GPU workflow, the project uses frames 000--002
to verify that Ultrack can process the 3D volume structure end to end. This
baseline derives both inputs directly from the raw volumes:

```python
foreground = detect_foreground(
    volume,
    sigma=15.0,
    remove_hist_mode=False,
    min_foreground=0.0,
)
contours = robust_invert(volume, sigma=1.0)
```

The resulting arrays have shape `(T, Z, Y, X)`. Ultrack uses the same shared
filesystem worker settings as the 2D runs: one database worker, four
segmentation workers, one linking worker, and four Gurobi threads.

This is an exploratory baseline, not a replacement for the U-Net. It differs
from the paper in its image normalization, anisotropy handling, foreground
estimator, boundary estimator, learned weights, and possibly the Ultrack
configuration version.

The baseline is inspected with:

- middle z-slices and maximum-intensity projections of the raw volumes;
- corresponding foreground and contour slices;
- sparse gold and detected-foreground overlays on the same annotated z-slice;
- per-object gold-pixel coverage and best-component IoU on annotated slices;
- matched and missed gold-object counts at 50% coverage; and
- result-label overlays after segmentation, linking, and solving.

Detections on unannotated z-slices are not counted as false positives. Exact
boundary overlays are treated as qualitative checks because a one-pixel shift
can remove exact overlap even when two boundaries are visually close.

The executable record is
[`03_mda231_raw_to_tracks.ipynb`](../../notebooks/ultrack/03_mda231_raw_to_tracks.ipynb).
Its output directory is named `mda231-seq01-t000-002-raw`, and any CTC-style
subset export must be named `subset_RES` rather than `01_RES`.

### Evaluation and reporting rules

The appropriate evaluation depends on which methodology and frame range were
run:

| Experiment | Appropriate evaluation | Prohibited claim |
| --- | --- | --- |
| Three-frame raw baseline | Qualitative 3D review and sparse annotated-slice coverage/IoU | Do not report it as the published U-Net result or as a full CTC benchmark |
| Complete public sequence with the authors' U-Net checkpoint | CTC SEG, TRA, and `OP_CTB` against public `01_GT`, plus qualitative review | Do not call the values a direct reproduction of hidden-test scores |
| Authors' published hidden-test submission | Cite SEG 0.549, TRA 0.818, and CTB 0.683 | Do not imply that hidden labels are locally available |

At the time of writing, the HeLa StarDist reproduction is complete, the raw
MDA231 subset is an additional experiment, and the official MDA231 U-Net GPU
workflow is documented but not yet completed. This status should be updated
only after the corresponding outputs and run records have been checked.

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
