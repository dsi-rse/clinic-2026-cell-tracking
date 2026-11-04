# Ultrack parameter analysis

This document records preprocessing comparisons and parameter sensitivity
experiments, organized by dataset and segmentation method. Plain watershed and
hole-filled watershed are treated as separate methods. Smoothing settings are
variants within each method. All reported scores evaluate the resulting
segmentation-and-Ultrack pipeline.

Original reproduction results remain in [Ultrack experiment results](ultrack-results.md).
Execution details are in [Ultrack reproducibility](ultrack-reproducibility.md).
These follow-up experiments investigate project performance; they are not new
reproductions of published parameter settings.

- [Fluo-N2DH-GOWT1](#fluo-n2dh-gowt1)
  - [Overall comparison](#overall-comparison)
  - [Plain watershed](#plain-watershed)
  - [Hole-filled watershed](#hole-filled-watershed)
- [Fluo-N2DL-HeLa](#fluo-n2dl-hela)
  - [Cellpose](#cellpose)
    - [Contour smoothing](#contour-smoothing)
- [Remaining parameter investigations](#remaining-parameter-investigations)

## Fluo-N2DH-GOWT1

### Overall comparison

Full public training sequences 01 and 02 were evaluated against their
corresponding CTC ground truth. Scores range from 0 to 1; higher is better.
Values below are rounded to six decimals.

| Sequence | Method | Image smoothing sigma | DET | SEG | TRA | OP_CTB |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 01 | Plain watershed | 1.0 | 0.097911 | 0.075761 | 0.112959 | 0.094360 |
| 01 | Hole-filled watershed | 1.0 | **0.422692** | **0.246408** | **0.427822** | **0.337115** |
| 01 | Hole-filled watershed | 0.5 | 0.397182 | 0.233387 | 0.402243 | 0.317815 |
| 02 | Plain watershed | 1.0 | 0.076003 | 0.163528 | 0.093791 | 0.128659 |
| 02 | Hole-filled watershed | 1.0 | **0.347239** | **0.450789** | **0.353262** | **0.402026** |
| 02 | Hole-filled watershed | 0.5 | 0.344617 | 0.394356 | 0.347687 | 0.371022 |

Bold identifies the best tested watershed variant within each sequence, not
the best method overall. The previously recorded Cellpose and StarDist results
remain higher than these watershed results.

### Plain watershed

#### Configuration and reference results

The original baseline uses per-frame Otsu thresholding, small-object removal,
distance-transform seed detection, and watershed. No binary hole filling is
applied. Recorded settings are Gaussian image smoothing sigma 1, h-maxima
height 2 (the CLI option is named `--watershed-h-minima`), minimum object size
20 pixels, and Ultrack contour smoothing sigma 4.

The baseline values in the comparison table are taken from the existing
[GOWT1 results](ultrack-results.md#fluo-n2dh-gowt1). OP_CTB is approximately
9.4% for sequence 01 and 12.9% for sequence 02.

Baseline run directories:

```text
<ULTRACK_RUN_ROOT>/gowt1-seq01-full-watershed/
<ULTRACK_RUN_ROOT>/gowt1-seq02-full-watershed/
```

### Hole-filled watershed

#### Method and experiment design

Binary hole filling is applied independently to each 2D foreground mask,
after Otsu thresholding and small-object removal, but before the distance
transform and seed detection. The implementation uses
`scipy.ndimage.binary_fill_holes`, enabled by `--watershed-fill-holes`.
Raw fluorescence images are unchanged. This preprocessing is specific to
watershed; Cellpose and StarDist are not modified.

Two comparisons were run:

1. Plain versus hole-filled watershed at image smoothing sigma 1.
2. Hole-filled watershed at image smoothing sigma 1 versus 0.5.

The supplied experiment commands retain h-maxima height 2, minimum object size
20, and contour smoothing sigma 4. Confirm these against the saved run reports
when archiving the experiments; the evaluation summaries alone do not establish
that every other setting was held fixed.

Image smoothing occurs before Otsu thresholding. Contour smoothing occurs after
instance segmentation when labels are converted into Ultrack inputs. The
0.5 experiment changes **image smoothing**, not contour smoothing.

#### Effect of hole filling

Differences below are hole-filled sigma 1 minus plain watershed sigma 1,
calculated from the six-decimal reported scores.

| Sequence | DET change | SEG change | TRA change | OP_CTB change |
| --- | ---: | ---: | ---: | ---: |
| 01 | +0.324781 | +0.170647 | +0.314863 | +0.242755 |
| 02 | +0.271236 | +0.287261 | +0.259471 | +0.273367 |

Hole filling improves all four metrics on both sequences. OP_CTB increases
by 24.28 percentage points on sequence 01 and 27.34 on sequence 02.
This supports retaining the preprocessing step among the tested configurations.
It does not by itself establish that over-segmentation is resolved: visual
inspection is still needed for missed cells, extra detections, splits, and
merges, especially enclosed background gaps in crowded regions.

#### Sensitivity to image smoothing

Differences below are hole-filled sigma 0.5 minus hole-filled sigma 1.

| Sequence | DET change | SEG change | TRA change | OP_CTB change |
| --- | ---: | ---: | ---: | ---: |
| 01 | -0.025510 | -0.013021 | -0.025579 | -0.019300 |
| 02 | -0.002622 | -0.056433 | -0.005575 | -0.031004 |

Reducing image smoothing lowers every reported metric on both sequences.
OP_CTB decreases by 1.93 and 3.10 percentage points, respectively. Sequence 02
shows its largest decline in SEG. Less smoothing may preserve noise that changes
the foreground or seed placement, but that explanation has not been verified
with overlays.

**Best tested watershed configuration:** hole filling enabled, image smoothing
sigma 1, with the remaining baseline settings retained. This is a choice among
the tested configurations, not evidence of a globally optimal parameter value.

#### Evaluation records and outputs

Both hole-filled smoothing settings passed CTC structural validation
(`Valid = 1`) on both sequences. Structural validity does not establish accuracy.
New scores were supplied from cluster evaluation terminal output on November 3,
2026. Sigma 1 scores were supplied to six decimals; sigma 0.5 output also
included unrounded scores. The table consistently uses six decimals.

```text
<ULTRACK_RUN_ROOT>/gowt1-seq01-full-watershed-holefilled/01_RES/
<ULTRACK_RUN_ROOT>/gowt1-seq02-full-watershed-holefilled/02_RES/
<ULTRACK_RUN_ROOT>/gowt1-seq01-full-watershed-holefilled-smoothing-0.5/01_RES/
<ULTRACK_RUN_ROOT>/gowt1-seq02-full-watershed-holefilled-smoothing-0.5/02_RES/
```

Evaluation uses `scripts/ultrack/evaluate_ctc_result.py` with the corresponding
`01_GT` or `02_GT`, and four workers. Its default evaluation output is
`<run directory>/evaluation/<sequence>_RES/`, containing `ctc_metrics.json` and
`ctc_metrics.csv`. Preserve these files and each run's `run_report.json` as the
machine-readable evidence. Runtime and configuration verification for these
new runs have not yet been added to this document.

## Fluo-N2DL-HeLa

### Cellpose

#### Contour smoothing

Ultrack converts the saved Cellpose object labels into a foreground mask and
an image of object boundaries (the contour map). The contour-smoothing parameter,
`contour_sigma`, controls the width of the Gaussian filter applied to that
boundary map, measured in pixels for these 2D experiments.

- **Sigma 4:** the baseline; spreads boundary values over a wider neighborhood.
- **Sigma 2:** applies a narrower smoothing filter.
- **Sigma 0:** applies no contour smoothing, preserving sharp label boundaries.

These maps guide Ultrack's segmentation hypotheses and therefore can affect
its final masks and tracks. Changing sigma does not rerun Cellpose or edit its
saved input labels. It also does not guarantee smaller final masks: the effect
on boundary placement must be checked against ground truth. This parameter is
part of Ultrack's input conversion, rather than Cellpose's neural network.


##### Experiment design

The same saved Cellpose segmentation labels were reused for full public
training sequences 01 and 02. Ultrack contour smoothing sigma was varied over
4 (baseline), 2, and 0, with the same tracking configuration requested across
the sweep. No Cellpose inference was repeated. Sigma is applied during
label-to-contour conversion; it is distinct from the Gaussian image smoothing
tested inside watershed on GOWT1.

The experiment ids are `hela-01-cellpose-contour-{4,2,0}` and
`hela-02-cellpose-contour-{4,2,0}`. Each result was evaluated against its
corresponding CTC ground truth. Scores were supplied from the parameter
runner's summary CSV; saved configuration and input records have not been
independently inspected for this entry.

##### Evaluation results

| Sequence | Contour sigma | DET | SEG | TRA | OP_CTB |
| --- | ---: | ---: | ---: | ---: | ---: |
| 01 | 4 (baseline) | 0.936625 | 0.779104 | 0.933606 | 0.856355 |
| 01 | 2 | 0.929355 | 0.750823 | 0.924153 | 0.837488 |
| 01 | **0** | **0.938129** | **0.791604** | **0.935410** | **0.863507** |
| 02 | 4 (baseline) | 0.967144 | 0.838270 | 0.964703 | 0.901486 |
| 02 | 2 | 0.963611 | 0.831811 | 0.960327 | 0.896069 |
| 02 | **0** | **0.967396** | **0.841843** | **0.964789** | **0.903316** |

All six outputs passed structural validation (`Valid = 1`). Bold identifies
the best tested contour sigma for Cellpose inputs in each sequence.

Differences below are relative to sigma 4 in the same sweep, calculated from
the supplied unrounded scores and then rounded to six decimals.

| Sequence | Contour sigma | DET change | SEG change | TRA change | OP_CTB change |
| --- | ---: | ---: | ---: | ---: | ---: |
| 01 | 2 | -0.007269 | -0.028281 | -0.009453 | -0.018867 |
| 01 | 0 | +0.001505 | +0.012500 | +0.001804 | +0.007152 |
| 02 | 2 | -0.003533 | -0.006459 | -0.004376 | -0.005417 |
| 02 | 0 | +0.000252 | +0.003574 | +0.000086 | +0.001830 |

##### Interpretation and baseline consistency

Removing contour smoothing improves all four metrics on both sequences.
OP_CTB increases by approximately 0.72 percentage points on sequence 01 and
0.18 on sequence 02. SEG increases by approximately 1.25 and 0.36 percentage
points, respectively. Sigma 2 reduces all four metrics on both sequences,
so performance does not improve monotonically as sigma decreases.

**Best tested setting for these HeLa Cellpose-input runs: contour sigma 0.**
The gains are modest and do not establish that this setting is best for other
segmentation inputs or datasets. Overlays against ground truth are still
needed to determine whether the improvement specifically corrects oversized
boundaries.

Sequence 01's sigma 4 result agrees with the original recorded baseline to
six decimals. Sequence 02's sigma 4 OP_CTB is 0.901486, compared with 0.901470
in the original reproduction record; DET and TRA also differ slightly. Use
the baseline from this sweep for the differences above. The cause of the small
rerun difference has not been established. Preserve the original reproduction
values in [Ultrack results](ultrack-results.md#fluo-n2dl-hela).

##### Records and follow-up

With the recommended output root, experiment records are organized as:

```text
<ULTRACK_RUN_ROOT>/segmentation-parameter-analysis/<experiment-id>/
  experiment.json
  track.json
  tracking/attempt-NNN/effective_config.json
  evaluation/ctc_metrics.json
  evaluation/ctc_metrics.csv
```

The shared `summary.csv` contains the supplied scores. Retain full-precision
JSON/CSV values even though tables here are rounded. Runtime and hardware
details have not yet been supplied for this sweep.

Next comparisons are GOWT1 Cellpose contour smoothing, followed by StarDist,
watershed variants, and ensemble inputs on both datasets. These are follow-up
parameter experiments, not changes to the original reproduction benchmarks.

## Remaining parameter investigations

- **Watershed:** inspect crowded-region overlays for the hole-filling comparison.
- **Contour smoothing:** HeLa Cellpose sequences 01 and 02 are complete. Extend
  to GOWT1 and the remaining segmentation methods, reusing fixed input labels
  and keeping this separate from watershed image smoothing.
- **Cellpose:** verify the meaning of `cellprob_threshold=0` in the installed
  Cellpose 3 implementation used for the 2D experiments.
- **StarDist:** record actual loaded probability/NMS defaults, then vary one
  threshold at a time on HeLa and GOWT1.
- **Ultrack tracking:** document displacement limits, appearance/disappearance
  and division settings, plus whether and how missing-frame gap closing is
  supported in the installed version, before selecting tracking experiments.
