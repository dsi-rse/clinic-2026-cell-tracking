# Project Scope and Milestones

## Research question

How reproducibly and reliably do selected open-source cell-tracking methods perform across benchmark microscopy datasets, and how well do they transfer to UChicago live-cell movies?

## Core workstreams

### 1. Reproduce representative benchmarks

- Select two to four annotated CTC datasets rather than attempting the complete challenge.
- Obtain the official source code and identify the version used in the publication when possible.
- Run each selected method with the published or recommended settings.
- Compare the reproduced metrics with the paper or leaderboard results.
- Document discrepancies instead of treating an exact numerical match as required.

### 2. Study parameter sensitivity

- Identify a small number of scientifically meaningful parameters for each method.
- Change one factor at a time or use a small, predefined parameter grid.
- Measure effects on accuracy, runtime, memory use, and failure modes.
- Avoid an unbounded hyperparameter search.

### 3. Apply methods to UChicago data

- Inspect image dimensionality, voxel spacing, time interval, channels, labeling, cell density, motion, and division frequency.
- Select the benchmark datasets and methods most comparable to these characteristics.
- Adapt input conversion and preprocessing without modifying the source data.
- Evaluate a small representative region and time window, where feasible.

## Suggested eight-week sequence

| Week | Focus |
|---|---|
| 1 | CTC background, papers, datasets, metrics, and UChicago data inspection |
| 2 | Method selection, environments, smoke tests, and experiment plan |
| 3 | Reproduce the first benchmark results |
| 4 | Complete representative benchmarks and resolve reproducibility issues |
| 5 | Controlled parameter-sensitivity experiments |
| 6 | Prepare and run methods on UChicago data |
| 7 | Small-scale validation and failure analysis |
| 8 | Final comparison, recommendations, documentation, and presentation |

## Minimum viable deliverable

- At least two methods running reproducibly.
- Results on at least two annotated CTC datasets.
- A documented parameter study.
- Application of at least one promising method to the UChicago data.
- Qualitative review and, where feasible, quantitative validation on a small subset.

Three-dimensional tracking is an important target, but a rigorous 2D benchmark remains a valid deliverable if 3D methods prove difficult to reproduce or do not perform adequately.
