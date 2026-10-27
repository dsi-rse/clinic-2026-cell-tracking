# Ultrack experiment results

This document records completed Ultrack experiments and their interpretation.
It is separate from
[`ultrack-reproducibility.md`](ultrack-reproducibility.md), which documents how
to recreate the environments, workflows, and evaluations.

Large masks, model files, and other run outputs remain in approved cluster
storage. Paths below use the safe alias `<ULTRACK_RUN_ROOT>` rather than a
personal or machine-specific path.

## Fluo-N2DL-HeLa watershed baseline

### Experiment status

Both public training sequences were processed from raw images through
watershed segmentation, Ultrack hypothesis generation, linking, solving, and
CTC export. The resulting CTC directories passed `py-ctcmetrics` validation and
were evaluated on 2026-10-26.

This experiment is a baseline rather than an exact reproduction. The paper
describes an h-minima watershed using a distance transform, but it does not
report all HeLa preprocessing and watershed parameter values needed to recreate
the published labels exactly.

### Configuration

| Item | Value |
| --- | --- |
| Dataset | `Fluo-N2DL-HeLa` |
| Sequences | `01` and `02` |
| Frames per sequence | 92 |
| Watershed foreground | Otsu threshold calculated separately for each frame |
| Gaussian smoothing sigma | 1 pixel |
| h-minima value | 2 |
| Minimum input-object size | 20 pixels |
| Label-to-contour sigma | 4 pixels |
| Ultrack | 0.8.0 |
| Evaluation | `py-ctcmetrics` through `scripts/ultrack/evaluate_ctc_result.py` |

The minimum input-object size above belongs to the initial watershed
preprocessing. It is distinct from Ultrack's
`segmentation_config.min_area`, which controls pruning and merging in the
segmentation-hypothesis hierarchy.

### Evaluation results

| Sequence | Metric | Published | Reproduced | Difference |
| --- | --- | ---: | ---: | ---: |
| 01 | DET | Not reported | 0.675113 | Not applicable |
| 01 | SEG | 0.593 | 0.463852 | -0.129148 |
| 01 | TRA | 0.905 | 0.670664 | -0.234336 |
| 01 | `OP_CTB` | 0.749 | 0.567258 | -0.181742 |
| 02 | DET | Not reported | 0.768702 | Not applicable |
| 02 | SEG | 0.695 | 0.582872 | -0.112128 |
| 02 | TRA | 0.898 | 0.762708 | -0.135292 |
| 02 | `OP_CTB` | 0.796 | 0.672790 | -0.123210 |

The matching published rows are from Table 3 of the
[ECCV 2024 Ultrack paper](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/10114.pdf).
The reproduced values use the public training sequences and the project
implementation described above.

The reports are stored outside Git at:

```text
<ULTRACK_RUN_ROOT>/hela-seq01-full-watershed/evaluation/01_RES/
<ULTRACK_RUN_ROOT>/hela-seq02-full-watershed/evaluation/02_RES/
```

Selected tracking-error diagnostics from the evaluation are:

| Sequence | False negatives | False positives | Edges deleted | Edges added | Edges changed |
| --- | ---: | ---: | ---: | ---: | ---: |
| 01 | 2,690 | 942 | 4 | 3,010 | 95 |
| 02 | 5,374 | 3,131 | 21 | 6,812 | 243 |

The raw counts should not be compared directly across sequences because the
sequences have different cell densities and lineage sizes.

### Runtime and output summary

| Item | Sequence 01 | Sequence 02 |
| --- | ---: | ---: |
| Total recorded pipeline runtime | 840.7 seconds | 805.6 seconds |
| Watershed runtime | 20.2 seconds | 27.1 seconds |
| Mean watershed labels per frame | 94.5 | 294.3 |
| Mean selected Ultrack objects per frame | 74.4 | 247.7 |
| Unique predicted tracks | 341 | 1,040 |
| Ground-truth lineage records | 265 | 674 |

The full workflows took approximately 14 minutes each. The much shorter CTC
evaluation runtime is expected because evaluation reads existing masks and
does not rerun watershed or Ultrack.

### Interpretation

The CTC result structure is valid, but both sequences fall below the published
watershed values. The gap is larger for tracking than for segmentation,
especially in sequence 01. The evaluation also reports many false negatives,
false positives, and missing temporal edges. The predicted output contains
more track identities than the ground-truth lineage, which is consistent with
false tracks or fragmentation of one biological track into several predicted
tracks.

The most likely first explanation is that the project watershed labels and
contours differ from the unpublished details of the labels used for the paper.
Per-frame Otsu thresholding can omit dim nuclei, while the h-minima and
minimum-size settings can split or retain small regions. Ultrack cannot recover
a cell that is absent from the foreground input, and inaccurate contour maps
limit the segmentation hypotheses it can construct.

### Follow-up hypotheses

The following are hypotheses to inspect, not conclusions from the current
evaluation:

1. Compare raw images, watershed labels, and final Ultrack labels in several
   low-scoring frames to identify missed nuclei, splits, and mergers.
2. Inspect the distribution of expected nucleus areas before changing
   `segmentation_config.min_area`. Ultrack's
   [official tuning guide](https://royerlab.github.io/ultrack/optimizing.html)
   recommends using approximately half the expected or smallest non-outlier
   cell area as a starting point and increasing `min_area` when results are
   oversegmented.
3. Verify and record `tracking_config.link_function` and
   `tracking_config.power` in the next run. The
   [official configuration reference](https://royerlab.github.io/ultrack/configuration.html)
   documents power-transformed IoU linking and a default power of 4. The
   current runner constructs `MainConfig()` without overriding or recording
   these fields, so the saved run report alone does not prove their runtime
   values.
4. Preserve these outputs as the untuned baseline. If watershed is tuned, use
   sequence 01 for development and retain sequence 02 as a less-biased
   comparison rather than repeatedly optimizing both against their scores.
5. Complete the planned ensemble experiment before deciding whether a larger
   watershed parameter study is worth the compute time.

## Fluo-N2DL-HeLa Cellpose

### Experiment status

Both public training sequences were processed with Cellpose labels followed by
Ultrack hypothesis generation, linking, solving, and CTC export. Both CTC
result directories passed `py-ctcmetrics` validation and were evaluated on
2026-10-26.

The project workflow uses the pretrained Cellpose `cyto2` model from the
published experiment. The evaluation reports and both `run_report.json` files
were inspected to verify the inference parameters, software versions,
runtimes, and output counts below.

### Configuration

| Item | Recorded value |
| --- | --- |
| Dataset | `Fluo-N2DL-HeLa` |
| Sequences | `01` and `02` |
| Frames per sequence | 92 |
| Cellpose model | Pretrained `cyto2` |
| Cellpose | 3.1.1.3 |
| PyTorch | 2.14.1 |
| NumPy | 2.0.2 |
| Ultrack | 0.8.0 |
| Channels | `[0, 0]` |
| Diameter | Automatic (`None`) |
| Flow threshold | 0.4 |
| Cell-probability threshold | 0.0 |
| GPU | NVIDIA A40; GPU execution requested and used |
| Label-to-contour sigma | 4 pixels |
| Evaluation | `py-ctcmetrics` through `scripts/ultrack/evaluate_ctc_result.py` |

### Evaluation results

| Sequence | Metric | Published | Reproduced | Difference |
| --- | --- | ---: | ---: | ---: |
| 01 | DET | Not reported | 0.936625 | Not applicable |
| 01 | SEG | 0.671 | 0.779104 | +0.108104 |
| 01 | TRA | 0.863 | 0.933606 | +0.070606 |
| 01 | `OP_CTB` | 0.767 | 0.856355 | +0.089355 |
| 02 | DET | Not reported | 0.967124 | Not applicable |
| 02 | SEG | 0.743 | 0.838270 | +0.095270 |
| 02 | TRA | 0.908 | 0.964671 | +0.056671 |
| 02 | `OP_CTB` | 0.825 | 0.901470 | +0.076470 |

The matching published rows are the Cellpose results from Table 3 of the
[ECCV 2024 Ultrack paper](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/10114.pdf).
The reproduced result exceeds the reported Cellpose SEG, TRA, and CTB values
for both sequences. This is encouraging, but the published environment and
hardware are not specified in enough detail to attribute the improvement to a
particular dependency or configuration change. Qualitative overlays must also
be inspected before drawing a final conclusion.

The reports are stored outside Git at:

```text
<ULTRACK_RUN_ROOT>/hela-seq01-full-cellpose/evaluation/01_RES/
<ULTRACK_RUN_ROOT>/hela-seq02-full-cellpose/evaluation/02_RES/
```

Selected tracking-error diagnostics are:

| Sequence | False negatives | False positives | Edges deleted | Edges added | Edges changed |
| --- | ---: | ---: | ---: | ---: | ---: |
| 01 | 460 | 775 | 6 | 693 | 68 |
| 02 | 392 | 3,857 | 27 | 1,147 | 210 |

As with the watershed results, raw error counts should not be compared directly
between sequences because their cell densities and lineage sizes differ.

### Runtime and output summary

| Item | Sequence 01 | Sequence 02 |
| --- | ---: | ---: |
| Total recorded pipeline runtime | 407.9 seconds | 646.7 seconds |
| Cellpose inference | 110.1 seconds | 168.4 seconds |
| Label-to-contour conversion | 5.1 seconds | 5.9 seconds |
| Ultrack hypothesis generation | 223.5 seconds | 363.3 seconds |
| Ultrack linking | 57.9 seconds | 80.7 seconds |
| Ultrack solving | 11.2 seconds | 28.4 seconds |
| Mean Cellpose labels per frame | 96.8 | 315.4 |
| Mean selected Ultrack objects per frame | 97.1 | 312.7 |
| Unique predicted tracks | 304 | 968 |
| Lineage entries | 46 | 282 |
| Ground-truth lineage records | 265 | 674 |

The complete workflows took approximately 6.8 minutes for sequence 01 and
10.8 minutes for sequence 02 using an NVIDIA A40. These runtimes describe this
specific environment and hardware allocation and should not be treated as
hardware-independent performance measurements.

### Comparison with completed project runs

| Sequence | Segmentation input | SEG | TRA | `OP_CTB` |
| --- | --- | ---: | ---: | ---: |
| 01 | Watershed | 0.463852 | 0.670664 | 0.567258 |
| 01 | StarDist | 0.701001 | 0.894289 | 0.797645 |
| 01 | Cellpose | **0.779104** | **0.933606** | **0.856355** |
| 02 | Watershed | 0.582872 | 0.762708 | 0.672790 |
| 02 | StarDist | 0.816860 | 0.919480 | 0.868170 |
| 02 | Cellpose | **0.838270** | **0.964671** | **0.901470** |

Cellpose is the strongest completed project input on both sequences. Relative
to the watershed baseline, its CTB is higher by 0.289097 on sequence 01 and
0.228680 on sequence 02. The reduction in false negatives and missing temporal
edges is consistent with the large improvements in DET and TRA. Sequence 02
still has many false-positive operations, so qualitative review remains
important even though its aggregate scores are high.

### Follow-up

1. Inspect raw, Cellpose, and final Ultrack overlays for representative frames,
   including examples of apparent false positives and track fragmentation.
2. Extend future run reports to capture the selected CUDA device automatically
   rather than recording only that GPU use was requested.
3. Use the saved Cellpose labels as one of the three inputs to the planned
   watershed, Cellpose, and StarDist ensemble.
