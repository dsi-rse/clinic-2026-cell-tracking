# Ultrack benchmark reproducibility

## Purpose

This document records how the project runs and evaluates Ultrack benchmarks.
It is intended to grow as additional datasets and segmentation inputs are
tested. Each dataset section should state exactly what was reproduced, what was
changed, and which comparisons are valid.

The first complete experiment uses `Fluo-N2DL-HeLa` sequence 01 with a
pretrained StarDist model. No model was trained or fine-tuned during this run.
StarDist performed inference to create instance labels, and Ultrack used those
labels to construct and select tracks.

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

The target is the StarDist row for File 1 in Table 3 of the ECCV 2024 Ultrack
paper. The published workflow applies a pretrained StarDist fluorescence model
and converts its labels to foreground and contour maps before running Ultrack.

| Metric | Published File 1 value | Reproduced value |
| --- | ---: | ---: |
| SEG | 0.724 | Pending evaluation |
| TRA | 0.910 | Pending evaluation |
| `OP_CTB` | 0.817 | Pending evaluation |

These published values use the public CTC training sequence. The reproduction
should be compared with this StarDist row, not with the stronger ensemble row.
See [Published Ultrack Benchmarks](ultrack-benchmarks.md) for the source and
comparison limits.

### Data and software

| Item | Recorded value |
| --- | --- |
| Dataset | `Fluo-N2DL-HeLa` |
| Sequence | `01` |
| Frames | `t000.tif` through `t091.tif` |
| Number of frames | 92 |
| Image shape | 700 x 1100 pixels |
| Image type | `uint16` |
| Python | 3.12.15 |
| TensorFlow | 2.21.0 |
| StarDist | 0.9.2 |
| Ultrack | 0.8.0 |
| Solver | Gurobi |
| GPU | Not used; TensorFlow reported no available CUDA device |

The run used the `cell-tracking-ultrack-stardist` environment. The package
versions above were printed by the executed notebook. An environment recipe for
this combined Ultrack and StarDist environment still needs to be committed
before the workflow can be considered fully reproducible from a fresh account.

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

The notebook keeps segmentation, linking, and solving in separate cells. This
makes it possible to diagnose a failed stage without rerunning StarDist
inference or all preceding Ultrack stages.

### Full-sequence run record

| Stage | Parallel setting | Recorded runtime |
| --- | ---: | ---: |
| StarDist inference | CPU inference | 118.60 seconds |
| Label-to-contour conversion | CPU | approximately 4 seconds |
| Ultrack segmentation hypotheses | 4 workers | 1,352.83 seconds |
| Ultrack linking | 1 worker | 701.13 seconds |
| Ultrack optimization | 4 Gurobi threads | 14.31 seconds |

The long segmentation and linking times are expected for the complete sequence.
Progress can remain unchanged while a worker is processing a frame, so a
stationary progress bar alone does not show that the process is deadlocked.

The completed export contained:

- 92 CTC masks, `mask000.tif` through `mask091.tif`;
- 8,448 rows in the Ultrack track table;
- 290 unique track IDs;
- 42 entries in the lineage graph; and
- a `res_track.txt` lineage file.

These counts confirm that the workflow completed and produced a structurally
complete result. They do not measure tracking accuracy; the CTC metrics provide
that assessment.

### Output layout

The full run uses a descriptive run directory and exports its CTC submission
under `01_RES`:

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
```

The earlier five-frame check uses `subset_RES` instead. This name prevents a
subset from being mistaken for a complete CTC sequence during evaluation.

### Evaluation status

The full output has been generated, but its CTC metrics have not yet been added
to this document. Evaluation will use
[`evaluate_ctc_result.py`](../../scripts/ultrack/evaluate_ctc_result.py), which
first verifies that the result masks cover the complete sequence and then
reports DET, SEG, TRA, and `OP_CTB`.

After evaluation:

1. add the reproduced values to the comparison table above;
2. record the `py-ctcmetrics` version and worker count;
3. preserve a sanitized CSV summary in the repository if useful; and
4. discuss differences from the published values without assuming that close
   scores prove an exact reproduction.

The executable record for this experiment is
[`02_hela_stardist_benchmark.ipynb`](../../notebooks/ultrack/02_hela_stardist_benchmark.ipynb).
Plots may remain in the notebook, but verbose solver output should be cleared
before committing because it can contain identifying license information.

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
