# Published Ultrack Benchmarks

This document records the published Ultrack results relevant to the datasets
selected for the project. It identifies the source and evaluation setting for
each value so that future project results are compared with appropriate
benchmarks.

The main source is the ECCV 2024 paper by Bragantini, Lange, and Royer,
[Large-Scale Multi-Hypotheses Cell Tracking Using Ultrametric Contours
Maps](https://doi.org/10.1007/978-3-031-72986-7_3). An
[open-access PDF](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/10114.pdf)
is available from the European Computer Vision Association.

## Metrics

The paper reports three Cell Tracking Challenge metrics:

- **SEG** measures segmentation quality by comparing predicted cell regions
  with matching reference regions using intersection over union.
- **TRA** measures the accuracy of the tracking and lineage graph, including
  temporal links and cell divisions.
- **CTB** is the average of SEG and TRA. The Cell Tracking Challenge also
  refers to this combined measure as `OP_CTB`.

All three scores are better when they are closer to 1.

## Fluo-N2DL-HeLa

The paper uses the public training set of `Fluo-N2DL-HeLa`, a 2D fluorescence
dataset of HeLa cells expressing H2b-GFP. The experiment compares three
segmentation methods and an ensemble:

- a watershed method;
- Cellpose with pretrained `cyto2` weights;
- StarDist with the pretrained `2d versatile fluorescence` model; and
- an ensemble of all three methods.

For each method, the authors convert instance labels into a binary foreground
map and a contour map. The ensemble uses a logical OR to combine the foreground
maps and averages the contour maps. Ultrack then constructs segmentation
hypotheses and selects temporally consistent segments and links.

### Published results

The following values are reported in Table 3 of the ECCV paper.

| Sequence | Segmentation input | TRA | SEG | CTB |
| --- | --- | ---: | ---: | ---: |
| File 1 | Watershed | 0.905 | 0.593 | 0.749 |
| File 1 | Cellpose | 0.863 | 0.671 | 0.767 |
| File 1 | StarDist | 0.910 | 0.724 | 0.817 |
| File 1 | Ensemble | **0.956** | **0.740** | **0.848** |
| File 2 | Watershed | 0.898 | 0.695 | 0.796 |
| File 2 | Cellpose | 0.908 | 0.743 | 0.825 |
| File 2 | StarDist | 0.941 | 0.818 | 0.880 |
| File 2 | Ensemble | **0.956** | **0.826** | **0.891** |

The ensemble produced the highest CTB score for both sequences. The paper
explains that combining contour information allowed Ultrack to select better
segments and tracks than it obtained from any single segmentation input.

### Comparison limits

These are public training-set results, not scores from the hidden CTC test set.
The authors also state that the purpose was to evaluate Ultrack's ability to
combine segmentation inputs, not to compare against state-of-the-art methods;
the segmentation models were not fine-tuned for this dataset.

Project results should be compared sequence by sequence with the row that uses
the same segmentation input. Results from a different segmentation model or
preprocessing workflow are not direct reproductions and should be described as
such.

## Fluo-C3DL-MDA231

`Fluo-C3DL-MDA231` contains 3D fluorescence images of human breast carcinoma
cells embedded in a collagen matrix. The CTC training data include public
tracking ground truth and silver-standard segmentation annotations. The test
annotations are hidden, and the challenge organizers evaluate submitted test
results.

For the published submission, the authors trained a U-Net to predict cell
foreground and edge maps. These maps were used as the segmentation inputs to
Ultrack.

### Published results

Table 1 of the ECCV paper reports the following hidden-test result:

| Historical rank | CTB | TRA | SEG |
| ---: | ---: | ---: | ---: |
| 7th | **0.683** | **0.818** | **0.549** |

The rank is the submission's position at the time the article was submitted;
it should not be presented as a current leaderboard rank. The authors identify
MDA231 as their weakest ranking among the five reported 3D CTC datasets and
suggest that their edge-detection network did not generalize well to the hidden
test images.

### Comparison limits

The project has access to the CTC training data, not the hidden test labels used
to produce the published scores. A run evaluated against the public training
ground truth is therefore not a direct reproduction of the published hidden-test
result.

When comparing project results with this benchmark, report:

1. that the published score uses the hidden test set;
2. which public training sequence and frames the project evaluated;
3. whether the same U-Net segmentation workflow and weights were used;
4. the project SEG, TRA, and CTB values; and
5. likely reasons for differences in the results.

## Fluo-N2DH-GOWT1

The ECCV 2024 paper does not report an Ultrack benchmark for
`Fluo-N2DH-GOWT1`. The dataset may still be useful as an additional project
experiment and for continuity with the Week 2 smoke test, but its results should
not be presented as a reproduction of a value from this paper.

If another primary Ultrack source with a `Fluo-N2DH-GOWT1` result is found,
record the exact source, evaluation split, segmentation input, metric, and
value before using it as a benchmark.

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

