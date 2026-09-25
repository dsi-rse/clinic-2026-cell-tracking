# Cell Tracking Challenge Overview

The [Cell Tracking Challenge](https://celltrackingchallenge.net/) provides standardized 2D+t and 3D+t microscopy datasets, reference annotations, evaluation software, and public leaderboards for cell segmentation and tracking.

## Required reading

- Maška et al., [The Cell Tracking Challenge: 10 years of objective benchmarking](https://www.nature.com/articles/s41592-023-01879-y), *Nature Methods* (2023).
- [CTC dataset description](https://celltrackingchallenge.net/datasets/)
- [Reference annotations](https://celltrackingchallenge.net/annotations/)
- [Evaluation methodology](https://celltrackingchallenge.net/evaluation-methodology/)
- [Cell Tracking Benchmark leaderboard](https://celltrackingchallenge.net/latest-ctb-results/)
- [Cell Linking Benchmark leaderboard](https://celltrackingchallenge.net/latest-clb-results/)

## Why CTC is useful for this project

- Training sequences include public annotations.
- Datasets span cells and nuclei, fluorescence and transmitted-light imaging, and 2D and 3D acquisitions.
- Standard metrics make method comparisons more meaningful.
- The benchmark reveals that performance depends strongly on dataset properties; no single method should be assumed to work best everywhere.

## Annotation types

- **Gold tracking truth:** manually identified cells linked through time to form tracks and lineage trees. It generally emphasizes detection and identity rather than precise boundaries.
- **Gold segmentation truth:** accurate cell-instance masks for a limited subset because manual contour annotation is expensive.
- **Silver segmentation truth:** broader-coverage masks produced by fusing results from several competitive methods.

Public training annotations may be used for reproduction and parameter experiments. Test annotations are hidden and should not be treated as available ground truth.

## Main technical metrics

- **SEG:** region overlap between predicted and reference instance masks.
- **DET:** correctness of cell detection, including missing, extra, merged, or split objects.
- **TRA:** correctness of the tracking and lineage graph.
- **OP_CTB:** combined segmentation-and-tracking performance used by the Cell Tracking Benchmark.

Use the official evaluation tools whenever the output format is compatible. Do not replace CTC metrics with a home-built approximation without documenting the difference.
