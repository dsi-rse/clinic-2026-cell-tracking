# Published Ultrack benchmark comparison

- [Published Ultrack benchmark comparison](#published-ultrack-benchmark-comparison)
  - [How to read the comparisons](#how-to-read-the-comparisons)
  - [Fluo-N2DL-HeLa](#fluo-n2dl-hela)
    - [Sequence 01 comparison](#sequence-01-comparison)
    - [Sequence 02 comparison](#sequence-02-comparison)
    - [Interpretation and comparison limits](#interpretation-and-comparison-limits)
  - [Fluo-C3DL-MDA231](#fluo-c3dl-mda231)
    - [Descriptive split comparison](#descriptive-split-comparison)
    - [Interpretation and comparison limits](#interpretation-and-comparison-limits-1)
  - [Fluo-N2DH-GOWT1](#fluo-n2dh-gowt1)
  - [Sources](#sources)

This document compares the project's completed Ultrack experiments with the
published values that are valid reference points. It focuses on the comparison
itself: evaluation split, segmentation input, published score, project score,
difference, and interpretation.

For execution details, environments, configurations, and commands, see the
[Ultrack setup and reproducibility guide](ultrack-reproducibility.md). For full
runtime summaries, error counts, and qualitative interpretation, see
[Ultrack experiment results](ultrack-results.md).

The primary source is the ECCV 2024 paper by Bragantini, Lange, and Royer,
[Large-Scale Multi-Hypotheses Cell Tracking Using Ultrametric Contours
Maps](https://doi.org/10.1007/978-3-031-72986-7_3). An
[open-access PDF](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/10114.pdf)
is available from the European Computer Vision Association.

## How to read the comparisons

The paper reports three Cell Tracking Challenge metrics:

- **SEG** measures segmentation overlap between matched predicted and reference
  regions.
- **TRA** measures the accuracy of the tracking and lineage graph.
- **CTB**, also called `OP_CTB`, is the average of SEG and TRA.

All three scores are better when they are closer to 1. Every difference below
is calculated as:

```text
project score - published score
```

A positive difference means that the project score is higher. It does not by
itself prove that the implementation is better, because software, hardware,
parameters, and evaluation data may differ.

| Dataset | Comparison status | Reason |
| --- | --- | --- |
| `Fluo-N2DL-HeLa` | Sequence- and method-matched comparison | The paper and project both evaluate the public training sequences, but the exact published environments and some method details are unavailable |
| `Fluo-C3DL-MDA231` | Descriptive comparison only | The project evaluates public training sequence 01, while the published value uses the hidden CTC test set |
| `Fluo-N2DH-GOWT1` | No published comparison | The ECCV 2024 paper does not report a GOWT1 Ultrack result |

## Fluo-N2DL-HeLa

The paper evaluates watershed, Cellpose, StarDist, and their ensemble on both
public HeLa training sequences. The project ran the same four input categories.
These are the strongest available published comparisons because the dataset,
sequence, and segmentation-input category match.

The authors converted each method's instance labels into foreground and contour
maps. Their ensemble used logical OR for foreground and averaged the contour
maps. The project follows the same combination rule.

### Sequence 01 comparison

| Method | Published SEG | Project SEG | Difference | Published TRA | Project TRA | Difference | Published CTB | Project CTB | Difference |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Cellpose | 0.671 | 0.779104 | +0.108104 | 0.863 | 0.933606 | +0.070606 | 0.767 | 0.856355 | +0.089355 |
| StarDist | 0.724 | 0.701001 | -0.022999 | 0.910 | 0.894289 | -0.015711 | 0.817 | 0.797645 | -0.019355 |
| Watershed | 0.593 | 0.463852 | -0.129148 | 0.905 | 0.670664 | -0.234336 | 0.749 | 0.567258 | -0.181742 |
| Ensemble | 0.740 | 0.794855 | +0.054855 | 0.956 | 0.941088 | -0.014912 | 0.848 | 0.867971 | +0.019971 |

### Sequence 02 comparison

| Method | Published SEG | Project SEG | Difference | Published TRA | Project TRA | Difference | Published CTB | Project CTB | Difference |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Cellpose | 0.743 | 0.838270 | +0.095270 | 0.908 | 0.964671 | +0.056671 | 0.825 | 0.901470 | +0.076470 |
| StarDist | 0.818 | 0.816860 | -0.001140 | 0.941 | 0.919480 | -0.021520 | 0.880 | 0.868170 | -0.011830 |
| Watershed | 0.695 | 0.582872 | -0.112128 | 0.898 | 0.762708 | -0.135292 | 0.796 | 0.672790 | -0.123210 |
| Ensemble | 0.826 | 0.846924 | +0.020924 | 0.956 | 0.967633 | +0.011633 | 0.891 | 0.907279 | +0.016279 |

### Interpretation and comparison limits

The comparison shows three distinct patterns:

- Cellpose exceeds the matching published SEG, TRA, and CTB values on both
  sequences.
- StarDist is close to, but below, the published rows. Its absolute differences
  are at most 0.022999 across the reported metrics.
- Watershed has the largest negative differences, especially for TRA. The paper
  does not provide enough preprocessing and watershed detail to recreate its
  input labels exactly.
- The ensemble exceeds the published SEG and CTB values on both sequences. Its
  TRA is lower on sequence 01 and higher on sequence 02.

These are public-training-set comparisons, not hidden-test results. Cellpose
and StarDist use the corresponding published model categories, but dependency
versions and some Ultrack defaults differ or were not reported by the authors.
The watershed run is best treated as a method-matched baseline rather than an
exact label reproduction.

See the [HeLa setup and execution record](ultrack-reproducibility.md#fluo-n2dl-hela)
and [HeLa detailed results](ultrack-results.md#fluo-n2dl-hela).

## Fluo-C3DL-MDA231

The authors trained an `EdgeUNet` 3D U-Net to predict foreground and edge maps,
then passed those maps to Ultrack. They released the
`Fluo-C3DL-MDA231.ckpt` checkpoint and the dataset-specific
`Fluo-C3DL-MDA231-01.sh` workflow.

Table 1 of the ECCV paper reports a hidden-test CTB of 0.683, TRA of 0.818, and
SEG of 0.549. The submission was ranked seventh at the time the article was
submitted; that historical rank should not be presented as a current
leaderboard position. The authors identify MDA231 as their weakest ranking
among the five reported 3D datasets and suggest that the edge-detection network
did not generalize well to the hidden test images.

### Descriptive split comparison

| Result | Evaluation split | DET | SEG | TRA | `OP_CTB` |
| --- | --- | ---: | ---: | ---: | ---: |
| Project official-workflow run | Public training sequence 01 | 0.909341 | 0.385566 | 0.901970 | 0.643768 |
| Authors' published submission | Hidden CTC test set | Not reported | 0.549 | 0.818 | 0.683 |

| SEG difference | TRA difference | `OP_CTB` difference |
| ---: | ---: | ---: |
| -0.163434 | +0.083970 | -0.039232 |

### Interpretation and comparison limits

The project successfully ran the released checkpoint and official sequence 01
script over all 12 public training frames. The output passed structural
validation. On that public sequence, tracking is strong while segmentation
overlap is the main limitation.

The numerical differences above are descriptive only. They combine a change in
images and reference annotations with any environment or execution differences.
The project reproduces the published method and released checkpoint on public
data; it does not reproduce the authors' hidden-test evaluation split.

See the [MDA231 setup and execution record](ultrack-reproducibility.md#fluo-c3dl-mda231-published-u-net-and-raw-baseline)
and [MDA231 detailed results](ultrack-results.md#fluo-c3dl-mda231).

## Fluo-N2DH-GOWT1

The ECCV 2024 paper does not report an Ultrack benchmark for
`Fluo-N2DH-GOWT1`. The completed Cellpose, StarDist, watershed, and ensemble
runs are useful project experiments, but they must not be described as
reproductions of a published value from this paper.

If another primary Ultrack source reports a GOWT1 result, record its exact
evaluation split, sequence, segmentation input, metrics, and values before
adding it as a benchmark.

See the [GOWT1 setup and execution record](ultrack-reproducibility.md#fluo-n2dh-gowt1)
and [GOWT1 detailed results](ultrack-results.md#fluo-n2dh-gowt1).

## Sources

- Bragantini, J., Lange, M., and Royer, L. A. (2024).
  [Large-Scale Multi-Hypotheses Cell Tracking Using Ultrametric Contours
  Maps](https://doi.org/10.1007/978-3-031-72986-7_3). *Computer Vision -- ECCV
  2024*, 36–54.
- Bragantini, J. et al. (2025).
  [Ultrack: pushing the limits of cell tracking across biological
  scales](https://doi.org/10.1038/s41592-025-02778-0). *Nature Methods*, 22,
  2423–2436.
- Royer Lab.
  [Ultrack CTC submission repository](https://github.com/royerlab/ultrack_CTC_submission).
- Cell Tracking Challenge.
  [2D datasets](https://celltrackingchallenge.net/2d-datasets/) and
  [3D datasets](https://celltrackingchallenge.net/3d-datasets/).
- Cell Tracking Challenge.
  [Evaluation methodology](https://celltrackingchallenge.net/evaluation-methodology/).
