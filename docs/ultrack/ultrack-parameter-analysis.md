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

No new parameter-analysis results have been supplied yet. Keep the completed
[HeLa reproduction results](ultrack-results.md#fluo-n2dl-hela) as references.
Add separate method sections when sensitivity experiments are evaluated;
do not infer HeLa outcomes from the GOWT1 experiment.

## Remaining parameter investigations

- **Watershed:** inspect crowded-region overlays for the hole-filling comparison.
- **Contour smoothing:** test separately from watershed image smoothing, reusing
  fixed input labels to isolate the parameter change.
- **Cellpose:** verify the meaning of `cellprob_threshold=0` in the installed
  Cellpose 3 implementation used for the 2D experiments.
- **StarDist:** record actual loaded probability/NMS defaults, then vary one
  threshold at a time on HeLa and GOWT1.
- **Ultrack tracking:** document displacement limits, appearance/disappearance
  and division settings, plus whether and how missing-frame gap closing is
  supported in the installed version, before selecting tracking experiments.
