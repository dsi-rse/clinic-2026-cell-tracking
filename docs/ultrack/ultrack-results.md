# Ultrack experiment results

This document records completed Ultrack experiments and their interpretation.
It is separate from
[`ultrack-reproducibility.md`](ultrack-reproducibility.md), which documents how
to recreate the environments, workflows, and evaluations.

Large masks, model files, and other run outputs remain in approved cluster
storage. Paths below use the safe alias `<ULTRACK_RUN_ROOT>` rather than a
personal or machine-specific path.

- [Ultrack experiment results](#ultrack-experiment-results)
  - [Fluo-N2DL-HeLa](#fluo-n2dl-hela)
    - [Overall comparison](#overall-comparison)
    - [Cellpose](#cellpose)
      - [Experiment status](#experiment-status)
      - [Configuration](#configuration)
      - [Evaluation results](#evaluation-results)
      - [Runtime and output summary](#runtime-and-output-summary)
      - [Follow-up](#follow-up)
    - [StarDist](#stardist)
      - [Experiment status](#experiment-status-1)
      - [Evaluation results](#evaluation-results-1)
      - [Configuration](#configuration-1)
      - [Runtime and output summary](#runtime-and-output-summary-1)
    - [Watershed baseline](#watershed-baseline)
      - [Experiment status](#experiment-status-2)
      - [Configuration](#configuration-2)
      - [Evaluation results](#evaluation-results-2)
      - [Runtime and output summary](#runtime-and-output-summary-2)
      - [Interpretation](#interpretation)
      - [Follow-up hypotheses](#follow-up-hypotheses)
    - [Ensemble](#ensemble)
      - [Experiment status](#experiment-status-3)
      - [Evaluation results](#evaluation-results-3)
      - [Interpretation](#interpretation-1)
  - [Fluo-N2DH-GOWT1](#fluo-n2dh-gowt1)
    - [Overall comparison](#overall-comparison-1)
    - [Cellpose](#cellpose-1)
      - [Experiment status](#experiment-status-4)
      - [Evaluation results](#evaluation-results-4)
      - [Interpretation](#interpretation-2)
      - [Configuration](#configuration-3)
      - [Runtime and output summary](#runtime-and-output-summary-3)
    - [StarDist](#stardist-1)
      - [Experiment status](#experiment-status-5)
      - [Evaluation results](#evaluation-results-5)
      - [Interpretation](#interpretation-3)
      - [Configuration](#configuration-4)
      - [Runtime and output summary](#runtime-and-output-summary-4)
    - [Watershed baseline](#watershed-baseline-1)
      - [Experiment status](#experiment-status-6)
      - [Configuration](#configuration-5)
      - [Evaluation results](#evaluation-results-6)
      - [Runtime and output summary](#runtime-and-output-summary-5)
      - [Follow-up hypotheses](#follow-up-hypotheses-1)
    - [Ensemble](#ensemble-1)
      - [Experiment status](#experiment-status-7)
      - [Evaluation results](#evaluation-results-7)
      - [Interpretation](#interpretation-4)

## Fluo-N2DL-HeLa

### Overall comparison

| Sequence | Method | DET | SEG | TRA | `OP_CTB` |
| --- | --- | ---: | ---: | ---: | ---: |
| 01 | Cellpose | 0.936625 | 0.779104 | 0.933606 | 0.856355 |
| 01 | StarDist | 0.897604 | 0.701001 | 0.894289 | 0.797645 |
| 01 | Watershed | 0.675113 | 0.463852 | 0.670664 | 0.567258 |
| 01 | Ensemble | **0.944415** | **0.794855** | **0.941088** | **0.867971** |
| 02 | Cellpose | 0.967124 | 0.838270 | 0.964671 | 0.901470 |
| 02 | StarDist | 0.923068 | 0.816860 | 0.919480 | 0.868170 |
| 02 | Watershed | 0.768702 | 0.582872 | 0.762708 | 0.672790 |
| 02 | Ensemble | **0.969957** | **0.846924** | **0.967633** | **0.907279** |

The ensemble is the strongest completed result on both sequences, while
Cellpose remains the strongest single segmentation input. Relative to
Cellpose, the ensemble improves CTB by 0.011617 on sequence 01 and 0.005809 on
sequence 02. Its CTB improvement over the watershed baseline is 0.300713 and
0.234489, respectively. The ensemble gains are positive but much smaller than
the improvement from watershed to either learned segmentation method.

Compared with StarDist, Cellpose improves CTB by 0.058710 on sequence 01 and
0.033300 on sequence 02. The largest Cellpose-to-StarDist metric gain is SEG
on sequence 01, at 0.078103. On sequence 02 their SEG scores differ by only
0.021410, while Cellpose's TRA is 0.045191 higher.

The relationship with the published benchmarks differs by input method. The
watershed baseline is below every matching published SEG, TRA, and CTB value;
StarDist is close to but below its published rows; and Cellpose exceeds its
published rows on both sequences. The ensemble exceeds the published SEG and
CTB values on both sequences; its TRA is 0.014912 below the published sequence
01 value and 0.011633 above the published sequence 02 value. This pattern
shows that the segmentation input and its preprocessing materially affect the
final Ultrack result. It does not identify one dependency or parameter as the
cause, because the workflows were not run under identical software and
hardware conditions.

StarDist produced the number of unique track identities closest to the
ground-truth lineage count on both sequences, but the ensemble achieved the
best DET, SEG, TRA, and CTB scores. Track-count similarity alone is therefore
not evidence of better tracking; the locations, temporal links, and lineage
structure also matter.

### Cellpose

#### Experiment status

Both public training sequences were processed with Cellpose labels followed by
Ultrack hypothesis generation, linking, solving, and CTC export. Both CTC
result directories passed `py-ctcmetrics` validation and were evaluated on
2026-10-26.

The project workflow uses the pretrained Cellpose `cyto2` model from the
published experiment. The evaluation reports and both `run_report.json` files
were inspected to verify the inference parameters, software versions,
runtimes, and output counts below.

#### Configuration

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

#### Evaluation results

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

#### Runtime and output summary

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

#### Follow-up

1. Inspect raw, Cellpose, and final Ultrack overlays for representative frames,
   including examples of apparent false positives and track fragmentation.
2. Extend future run reports to capture the selected CUDA device automatically
   rather than recording only that GPU use was requested.
3. Use the saved Cellpose labels as one of the three inputs to the planned
   watershed, Cellpose, and StarDist ensemble.

### StarDist

#### Experiment status

Both public training sequences were processed with the pretrained
`2D_versatile_fluo` model followed by Ultrack hypothesis generation, linking,
solving, and CTC export. Both result directories passed structural validation
and were evaluated with `py-ctcmetrics`.

#### Evaluation results

| Sequence | Metric | Published | Reproduced | Difference |
| --- | --- | ---: | ---: | ---: |
| 01 | DET | Not reported | 0.897604 | Not applicable |
| 01 | SEG | 0.724 | 0.701001 | -0.022999 |
| 01 | TRA | 0.910 | 0.894289 | -0.015711 |
| 01 | `OP_CTB` | 0.817 | 0.797645 | -0.019355 |
| 02 | DET | Not reported | 0.923068 | Not applicable |
| 02 | SEG | 0.818 | 0.816860 | -0.001140 |
| 02 | TRA | 0.941 | 0.919480 | -0.021520 |
| 02 | `OP_CTB` | 0.880 | 0.868170 | -0.011830 |

The StarDist results are close to the matching published rows. Sequence 02
nearly reproduces the published SEG value, while its largest difference is in
TRA.

#### Configuration

| Item | Recorded value |
| --- | --- |
| Dataset | `Fluo-N2DL-HeLa` |
| Sequences | `01` and `02` |
| Frames per sequence | 92 |
| StarDist model | Pretrained `2D_versatile_fluo` |
| Prediction method | `predict_instances_big` |
| Block size | 560 pixels |
| Minimum overlap | 96 pixels |
| Probability threshold | Model default, 0.479071 |
| Non-maximum-suppression threshold | Model default, 0.3 |
| Gamma | 1 |
| Label-to-contour sigma | 4 pixels |
| StarDist | 0.9.2 |
| TensorFlow | 2.21.0 |
| Ultrack | 0.8.0 |
| Hardware | CPU-only; TensorFlow reported no available CUDA device |
| Parallel settings | 4 segmentation workers, 1 linking worker, 4 Gurobi threads |

#### Runtime and output summary

| Item | Sequence 01 | Sequence 02 |
| --- | ---: | ---: |
| Approximate total recorded pipeline runtime | 2,190.9 seconds | 1,473.3 seconds |
| StarDist inference | 118.6 seconds | 132.3 seconds |
| Label-to-contour conversion | approximately 4 seconds | approximately 5 seconds |
| Ultrack hypothesis generation | 1,352.8 seconds | 796.5 seconds |
| Ultrack linking | 701.1 seconds | 371.6 seconds |
| Ultrack solving | 14.3 seconds | 167.9 seconds |
| Mean selected Ultrack objects per frame | 91.8 | 286.3 |
| Unique predicted tracks | 290 | 836 |
| Lineage entries | 42 | 182 |
| Ground-truth lineage records | 265 | 674 |

The complete workflows took approximately 36.5 minutes for sequence 01 and
24.6 minutes for sequence 02. Sequence 02 produced about three times as many
selected objects per frame as sequence 01 and required much longer for the
final optimization, while sequence 01 spent longer in hypothesis generation
and linking. These are stage-level observations, not a controlled speed
comparison with Cellpose or watershed.

Additional execution metadata, resolved Ultrack defaults, and output layout
are recorded in the
[StarDist reproducibility section](ultrack-reproducibility.md#fluo-n2dl-hela).

### Watershed baseline

#### Experiment status

Both public training sequences were processed from raw images through
watershed segmentation, Ultrack hypothesis generation, linking, solving, and
CTC export. The resulting CTC directories passed `py-ctcmetrics` validation and
were evaluated on 2026-10-26.

This experiment is a baseline rather than an exact reproduction. The paper
describes an h-minima watershed using a distance transform, but it does not
report all HeLa preprocessing and watershed parameter values needed to recreate
the published labels exactly.

#### Configuration

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

#### Evaluation results

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

#### Runtime and output summary

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

#### Interpretation

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

#### Follow-up hypotheses

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
5. Inspect whether the completed ensemble corrects watershed errors or merely
   suppresses their effect through the stronger learned-model inputs before
   deciding whether a larger watershed parameter study is worth the compute
   time.

### Ensemble

#### Experiment status

Both public training sequences were processed with an ensemble of the saved
Cellpose, StarDist, and watershed labels. The ensemble combines binary
foreground maps with logical OR and averages the three contour maps before
running Ultrack. Both CTC result directories passed `py-ctcmetrics` validation
and were evaluated on 2026-10-27.

#### Evaluation results

| Sequence | Metric | Published | Reproduced | Difference |
| --- | --- | ---: | ---: | ---: |
| 01 | DET | Not reported | 0.944415 | Not applicable |
| 01 | SEG | 0.740 | 0.794855 | +0.054855 |
| 01 | TRA | 0.956 | 0.941088 | -0.014912 |
| 01 | `OP_CTB` | 0.848 | 0.867971 | +0.019971 |
| 02 | DET | Not reported | 0.969957 | Not applicable |
| 02 | SEG | 0.826 | 0.846924 | +0.020924 |
| 02 | TRA | 0.956 | 0.967633 | +0.011633 |
| 02 | `OP_CTB` | 0.891 | 0.907279 | +0.016279 |

The matching published values are the HeLa ensemble rows from Table 3 of the
[ECCV 2024 Ultrack paper](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/10114.pdf).
The project ensemble exceeds the published SEG and CTB values for both
sequences. Its sequence 01 TRA is slightly below the published value, while
its sequence 02 TRA is above it.

The reports are stored outside Git at:

```text
<ULTRACK_RUN_ROOT>/hela-seq01-full-ensemble/evaluation/01_RES/
<ULTRACK_RUN_ROOT>/hela-seq02-full-ensemble/evaluation/02_RES/
```

Selected tracking-error diagnostics are:

| Sequence | Node splits | False negatives | False positives | Edges deleted | Edges added | Edges changed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 01 | 29 | 378 | 877 | 5 | 632 | 91 |
| 02 | 117 | 312 | 3,932 | 26 | 1,051 | 210 |

#### Interpretation

The ensemble improves every aggregate metric over Cellpose, the strongest
single method, but the gains are modest. On sequence 01 it reduces false
negatives and missing temporal edges relative to Cellpose while increasing
false positives. Sequence 02 shows the same tradeoff: fewer false negatives
and edges added, but slightly more false positives. The net effect is a small
improvement in DET, TRA, and CTB on both sequences.

#### Configuration

| Item | Recorded value |
| --- | --- |
| Component methods | Cellpose, StarDist, and watershed |
| Foreground combination | Logical OR |
| Contour combination | Arithmetic mean |
| Label-to-contour sigma | 4 pixels |
| NumPy | 2.5.4 |
| tifffile | 2026.9.20 |
| Ultrack | 0.8.0 |
| Segmentation inference | Reused saved labels; models were not rerun |
| Worker settings and hardware | Not captured in the supplied run reports |

The component-label summaries are:

| Component | Sequence 01 mean (range) | Sequence 02 mean (range) |
| --- | ---: | ---: |
| Cellpose | 96.8 (41--154) | 315.4 (146--411) |
| StarDist | 93.2 (38--149) | 288.9 (131--387) |
| Watershed | 94.5 (36--164) | 294.3 (143--388) |

#### Runtime and output summary

| Item | Sequence 01 | Sequence 02 |
| --- | ---: | ---: |
| Total recorded pipeline runtime | 502.6 seconds | 549.2 seconds |
| Ensemble input conversion | 37.1 seconds | 51.4 seconds |
| Ultrack hypothesis generation | 355.3 seconds | 346.5 seconds |
| Ultrack linking | 95.0 seconds | 99.1 seconds |
| Ultrack solving | 15.2 seconds | 52.2 seconds |
| Mean selected Ultrack objects per frame | 99.0 | 314.4 |
| Unique predicted tracks | 321 | 957 |
| Lineage entries | 80 | 312 |
| Ground-truth lineage records | 265 | 674 |

The workflows took approximately 8.4 and 9.2 minutes. Their selected-object
counts are close to the corresponding Cellpose runs, which is consistent with
the ensemble providing a modest refinement rather than radically changing the
number of accepted objects.

## Fluo-N2DH-GOWT1

### Overall comparison

| Sequence | Method | DET | SEG | TRA | `OP_CTB` |
| --- | --- | ---: | ---: | ---: | ---: |
| 01 | Cellpose | **0.956608** | **0.850406** | **0.956903** | **0.903654** |
| 01 | StarDist | 0.943683 | 0.769468 | 0.944420 | 0.856944 |
| 01 | Watershed | 0.097911 | 0.075761 | 0.112959 | 0.094360 |
| 01 | Ensemble | 0.712391 | 0.702726 | 0.721126 | 0.711926 |
| 02 | Cellpose | 0.849424 | **0.853874** | 0.849609 | 0.851741 |
| 02 | StarDist | **0.875566** | 0.844489 | **0.875649** | **0.860069** |
| 02 | Watershed | 0.076003 | 0.163528 | 0.093791 | 0.128659 |
| 02 | Ensemble | 0.718673 | 0.648553 | 0.725760 | 0.687157 |

Cellpose improves CTB over watershed by 0.809294 on sequence 01 and 0.723082
on sequence 02. Cellpose is strongest on all four sequence 01 metrics. On
sequence 02, Cellpose has the highest SEG score by 0.009385, while StarDist has
the highest DET, TRA, and CTB scores. StarDist's sequence 02 CTB exceeds
Cellpose by 0.008328. These small differences should be considered together
with the planned overlay movies rather than treated as decisive from aggregate
scores alone.

Unlike the HeLa result, the GOWT1 ensemble underperforms both learned single
methods. Its CTB is 0.191728 below Cellpose on sequence 01 and 0.172912 below
StarDist on sequence 02. It remains substantially better than the watershed
baseline, but combining all three inputs does not improve the best available
result for this dataset. A likely explanation is error carry-over from one of
the component methods rather than a failure shared by Cellpose and StarDist.

The watershed input contains approximately 2.4 times as many labels per frame
as Cellpose for sequence 01 and 3.0 times as many for sequence 02. It also
produces 514 and 689 predicted track identities, compared with 28 and 58
ground-truth lineage records. Together with the false-positive and missing-edge
counts, this is strong evidence of extensive oversegmentation and track
fragmentation.

StarDist generated slightly more input labels and substantially more unique
track identities than Cellpose on both sequences. Its runtimes should not be
used for a direct speed comparison with Cellpose because StarDist sequence 01
used one worker and sequence 02 used four workers.

### Cellpose

#### Experiment status

Both public training sequences were processed with Cellpose labels followed by
Ultrack hypothesis generation, linking, solving, and CTC export. Both CTC
result directories passed `py-ctcmetrics` validation and were evaluated on
2026-10-27.

The ECCV 2024 Ultrack paper does not report a matching GOWT1 experiment.
Therefore, these scores are an additional project experiment rather than a
reproduction of a published Ultrack benchmark.

#### Evaluation results

| Sequence | DET | SEG | TRA | `OP_CTB` |
| --- | ---: | ---: | ---: | ---: |
| 01 | 0.956608 | 0.850406 | 0.956903 | 0.903654 |
| 02 | 0.849424 | 0.853874 | 0.849609 | 0.851741 |

The reports are stored outside Git at:

```text
<ULTRACK_RUN_ROOT>/gowt1-seq01-full-cellpose/evaluation/01_RES/
<ULTRACK_RUN_ROOT>/gowt1-seq02-full-cellpose/evaluation/02_RES/
```

Selected tracking-error diagnostics are:

| Sequence | Node splits | False negatives | False positives | Edges deleted | Edges added | Edges changed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 01 | 0 | 76 | 133 | 0 | 83 | 1 |
| 02 | 0 | 358 | 210 | 0 | 368 | 1 |

#### Interpretation

Segmentation quality is similar across the two sequences: their SEG scores
differ by less than 0.004. Sequence 02 has substantially lower DET and TRA,
which reduces CTB by approximately 0.052 relative to sequence 01. Its error
report contains more false negatives and missing temporal edges, suggesting
that detection and temporal continuity are the main weaknesses rather than
boundary accuracy on the annotated segmentation frames.

The result should still be reviewed visually. Aggregate CTC scores can hide
localized failures such as missed dim nuclei, short broken tracks, or errors
in crowded frames.

#### Configuration

The sequence 01 and sequence 02 `run_report.json` files verify that both runs
used the configuration below.

| Item | Recorded value |
| --- | --- |
| Cellpose model | Pretrained `cyto2` |
| Cellpose | 3.1.1.3 |
| PyTorch | 2.14.1 |
| NumPy | 2.0.2 |
| Ultrack | 0.8.0 |
| Channels | `[0, 0]` |
| Diameter | Automatic (`None`) |
| Flow threshold | 0.4 |
| Cell-probability threshold | 0.0 |
| GPU | NVIDIA A100 80GB PCIe; GPU execution requested and used |
| Label-to-contour sigma | 4 pixels |

#### Runtime and output summary

| Item | Sequence 01 | Sequence 02 |
| --- | ---: | ---: |
| Total recorded pipeline runtime | 1,883.0 seconds | 1,806.9 seconds |
| Cellpose inference | 76.3 seconds | 117.7 seconds |
| Label-to-contour conversion | 8.4 seconds | 8.8 seconds |
| Ultrack hypothesis generation | 680.7 seconds | 1,011.0 seconds |
| Ultrack linking | 1,064.3 seconds | 657.7 seconds |
| Ultrack solving | 53.2 seconds | 11.9 seconds |
| Mean Cellpose labels per frame | 22.7 | 25.1 |
| Mean selected Ultrack objects per frame | 23.0 | 25.8 |
| Unique predicted tracks | 46 | 67 |
| Lineage entries | 10 | 14 |
| Ground-truth lineage records | 28 | 58 |

The sequence 01 and sequence 02 workflows took approximately 31.4 and 30.1
minutes, respectively. The A100 record is important context, but most of each
runtime was spent in Ultrack's CPU-based hypothesis-generation and linking
stages rather than Cellpose inference.

### StarDist

#### Experiment status

Both public training sequences were processed with StarDist labels followed by
Ultrack hypothesis generation, linking, solving, and CTC export. Both CTC
result directories passed `py-ctcmetrics` validation and were evaluated on
2026-10-27.

The ECCV 2024 Ultrack paper does not report a matching GOWT1 experiment.
Therefore, these scores are an additional project experiment rather than a
reproduction of a published Ultrack benchmark.

#### Evaluation results

| Sequence | DET | SEG | TRA | `OP_CTB` |
| --- | ---: | ---: | ---: | ---: |
| 01 | 0.943683 | 0.769468 | 0.944420 | 0.856944 |
| 02 | 0.875566 | 0.844489 | 0.875649 | 0.860069 |

The reports are stored outside Git at:

```text
<ULTRACK_RUN_ROOT>/gowt1-seq01-full-stardist/evaluation/01_RES/
<ULTRACK_RUN_ROOT>/gowt1-seq02-full-stardist/evaluation/02_RES/
```

Selected tracking-error diagnostics are:

| Sequence | Node splits | False negatives | False positives | Edges deleted | Edges added | Edges changed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 01 | 0 | 92 | 239 | 0 | 103 | 0 |
| 02 | 0 | 282 | 312 | 1 | 304 | 2 |

#### Interpretation

StarDist produced valid, high-scoring results on both sequences. Sequence 02
has a higher SEG score than sequence 01 but more false negatives,
false positives, and missing temporal edges. This helps explain why its DET and
TRA scores are lower despite its stronger boundary-overlap score.

#### Configuration

The sequence 01 and sequence 02 `run_report.json` files verify that both runs
used the configuration below.

| Item | Recorded value |
| --- | --- |
| StarDist model | Pretrained `2D_versatile_fluo` |
| StarDist | 0.9.2 |
| TensorFlow | 2.21.0 |
| NumPy | 2.5.4 |
| tifffile | 2026.10.15 |
| Ultrack | 0.8.0 |
| Block size | 560 pixels |
| Minimum overlap | 96 pixels |
| Gamma | 1 |
| Label-to-contour sigma | 4 pixels |
| Ultrack workers | Sequence 01: 1; sequence 02: 4 |
| Hardware | Not captured in the supplied run reports |

#### Runtime and output summary

| Item | Sequence 01 | Sequence 02 |
| --- | ---: | ---: |
| Total recorded pipeline runtime | 6,775.3 seconds | 772.5 seconds |
| StarDist inference | 463.1 seconds | 380.4 seconds |
| Label-to-contour conversion | 10.4 seconds | 11.8 seconds |
| Ultrack hypothesis generation | 5,915.9 seconds | 236.3 seconds |
| Ultrack linking | 371.4 seconds | 138.1 seconds |
| Ultrack solving | 14.6 seconds | 5.9 seconds |
| Mean StarDist labels per frame | 24.2 | 28.8 |
| StarDist label range per frame | 21--32 | 22--40 |
| Mean selected Ultrack objects per frame | 24.0 | 27.7 |
| Unique predicted tracks | 68 | 106 |
| Lineage entries | 6 | 18 |
| Ground-truth lineage records | 28 | 58 |

The sequence 01 and sequence 02 workflows took approximately 112.9 and 12.9
minutes, respectively. These runtimes are not directly comparable: sequence 01
used one worker, whereas sequence 02 used four workers. The lower parallelism
in sequence 01 explains why its Ultrack hypothesis-generation stage took much
longer. This worker-count difference must be retained whenever the runtimes are
reported.

### Watershed baseline

#### Experiment status

Both public training sequences were processed from raw images through
watershed segmentation, Ultrack hypothesis generation, linking, solving, and
CTC export. Both CTC result directories passed `py-ctcmetrics` validation and
were evaluated on 2026-10-27.

As with the GOWT1 Cellpose experiment, there is no matching published Ultrack
benchmark for this dataset. These values are project baseline results.

#### Configuration

| Item | Recorded value |
| --- | --- |
| Dataset | `Fluo-N2DH-GOWT1` |
| Sequences | `01` and `02` |
| Frames per sequence | 92 |
| Watershed foreground | Otsu threshold calculated separately for each frame |
| Gaussian smoothing sigma | 1 pixel |
| h-minima value | 2 |
| Minimum input-object size | 20 pixels |
| Label-to-contour sigma | 4 pixels |
| NumPy | 2.5.4 |
| scikit-image | 0.26.0 |
| SciPy | 1.18.1 |
| Ultrack | 0.8.0 |

The 20-pixel input filter is distinct from Ultrack's hierarchy-level
`segmentation_config.min_area` setting.

#### Evaluation results

| Sequence | DET | SEG | TRA | `OP_CTB` |
| --- | ---: | ---: | ---: | ---: |
| 01 | 0.097911 | 0.075761 | 0.112959 | 0.094360 |
| 02 | 0.076003 | 0.163528 | 0.093791 | 0.128659 |

The reports are stored outside Git at:

```text
<ULTRACK_RUN_ROOT>/gowt1-seq01-full-watershed/evaluation/01_RES/
<ULTRACK_RUN_ROOT>/gowt1-seq02-full-watershed/evaluation/02_RES/
```

Selected tracking-error diagnostics are:

| Sequence | Node splits | False negatives | False positives | Edges deleted | Edges added | Edges changed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 01 | 0 | 1,538 | 3,185 | 0 | 1,598 | 1 |
| 02 | 0 | 1,916 | 4,097 | 0 | 1,941 | 1 |

#### Runtime and output summary

| Item | Sequence 01 | Sequence 02 |
| --- | ---: | ---: |
| Total recorded pipeline runtime | 394.7 seconds | 586.5 seconds |
| Watershed segmentation | 44.5 seconds | 43.9 seconds |
| Label-to-contour conversion | 10.2 seconds | 10.2 seconds |
| Ultrack hypothesis generation | 220.9 seconds | 315.0 seconds |
| Ultrack linking | 108.1 seconds | 198.9 seconds |
| Ultrack solving | 11.0 seconds | 18.5 seconds |
| Mean watershed labels per frame | 54.8 | 76.4 |
| Mean selected Ultrack objects per frame | 40.3 | 51.1 |
| Unique predicted tracks | 514 | 689 |
| Lineage entries | 274 | 344 |
| Ground-truth lineage records | 28 | 58 |

The sequence 01 and sequence 02 workflows took approximately 6.6 and 9.8
minutes, respectively.

#### Follow-up hypotheses

1. Inspect raw images, watershed labels, and final Ultrack labels to confirm
   that the additional regions are small fragments rather than valid
   unannotated cells.
2. Measure the area distribution of representative GOWT1 nuclei before
   increasing either the watershed `minimum_object_size` or Ultrack's
   `segmentation_config.min_area`; these parameters affect different stages.
3. If tuning is pursued, use sequence 01 for parameter selection and preserve
   sequence 02 as a less-biased evaluation sequence.
4. Keep the current outputs as the documented untuned baseline rather than
   overwriting them.

### Ensemble

#### Experiment status

Both public training sequences were processed with the saved Cellpose,
StarDist, and watershed labels. Binary foreground maps were combined with
logical OR and the three contour maps were averaged before running Ultrack.
Both CTC result directories passed `py-ctcmetrics` validation and were
evaluated on 2026-10-27.

The ECCV 2024 Ultrack paper does not report a matching GOWT1 experiment, so
these values are project results rather than a published-benchmark
reproduction.

#### Evaluation results

| Sequence | DET | SEG | TRA | `OP_CTB` |
| --- | ---: | ---: | ---: | ---: |
| 01 | 0.712391 | 0.702726 | 0.721126 | 0.711926 |
| 02 | 0.718673 | 0.648553 | 0.725760 | 0.687157 |

The reports are stored outside Git at:

```text
<ULTRACK_RUN_ROOT>/gowt1-seq01-full-ensemble/evaluation/01_RES/
<ULTRACK_RUN_ROOT>/gowt1-seq02-full-ensemble/evaluation/02_RES/
```

Selected tracking-error diagnostics are:

| Sequence | Node splits | False negatives | False positives | Edges deleted | Edges added | Edges changed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 01 | 0 | 384 | 2,079 | 0 | 445 | 4 |
| 02 | 0 | 489 | 2,191 | 1 | 557 | 2 |

#### Interpretation

The ensemble has far more false positives than either Cellpose or StarDist:
2,079 and 2,191 across the two sequences, compared with 133 and 210 for
Cellpose and 239 and 312 for StarDist. It also has more false negatives and
missing temporal edges than the best single method on each sequence.

The ensemble's logical-OR foreground retains a region whenever any component
method predicts it. Errors from one failed input can therefore carry into the
ensemble even when the other two methods reject that region. The GOWT1
watershed run is the leading candidate because it is severely oversegmented
and has thousands of false positives, but the current aggregate metrics do not
prove that it caused each ensemble error. Contour averaging provides a second
possible carry-over path because a poor boundary map can weaken agreement
between the two stronger inputs.

The clearest diagnostic is a leave-one-out ensemble containing only Cellpose
and StarDist. If its scores recover toward the two single-method results, that
would support the watershed carry-over hypothesis. The overlay movies should
also distinguish regions unique to each component foreground so the source of
the extra detections can be inspected directly.

#### Configuration

| Item | Recorded value |
| --- | --- |
| Component methods | Cellpose, StarDist, and watershed |
| Foreground combination | Logical OR |
| Contour combination | Arithmetic mean |
| Label-to-contour sigma | 4 pixels |
| NumPy | 2.5.4 |
| tifffile | 2026.9.20 |
| Ultrack | 0.8.0 |
| Segmentation inference | Reused saved labels; models were not rerun |
| Worker settings and hardware | Not captured in the supplied run reports |

The component-label summaries make the watershed discrepancy visible before
Ultrack is run:

| Component | Sequence 01 mean (range) | Sequence 02 mean (range) |
| --- | ---: | ---: |
| Cellpose | 22.7 (21--25) | 25.1 (22--31) |
| StarDist | 24.2 (21--32) | 28.8 (22--40) |
| Watershed | 54.8 (19--82) | 76.4 (47--112) |

#### Runtime and output summary

| Item | Sequence 01 | Sequence 02 |
| --- | ---: | ---: |
| Total recorded pipeline runtime | 695.3 seconds | 476.6 seconds |
| Ensemble input conversion | 97.2 seconds | 127.3 seconds |
| Ultrack hypothesis generation | 397.5 seconds | 235.4 seconds |
| Ultrack linking | 185.2 seconds | 98.5 seconds |
| Ultrack solving | 15.4 seconds | 15.3 seconds |
| Mean selected Ultrack objects per frame | 40.8 | 45.9 |
| Unique predicted tracks | 366 | 437 |
| Lineage entries | 144 | 196 |
| Ground-truth lineage records | 28 | 58 |

The workflows took approximately 11.6 and 7.9 minutes. The ensemble selects
substantially more objects per frame than either learned input and produces
366 and 437 track identities, compared with 46 and 67 for Cellpose and 68 and
106 for StarDist. This run-level evidence strengthens, but does not by itself
prove, the watershed error carry-over hypothesis.
