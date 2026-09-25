# Candidate Methods

The final project should focus on approximately three methods. Selection should consider scientific relevance, published performance, source-code availability, licensing, cluster compatibility, documentation, and realistic setup effort.

## Initial candidates

### 1. EmbedTrack — KIT-GE (4)

- Source: [kaloeffler/EmbedTrack](https://github.com/kaloeffler/EmbedTrack)
- Type: deep-learning segmentation and tracking
- Dimension: 2D+t
- Role: primary end-to-end DL benchmark and a comparatively accessible reproduction target
- Watch for: older CUDA/PyTorch dependencies and lack of direct 3D support

### 2. KIT-GE (3)

- Segmentation source: [TimScherr/KIT-GE-3-Cell-Segmentation-for-CTC](https://github.com/TimScherr/KIT-GE-3-Cell-Segmentation-for-CTC)
- Tracking source: [kaloeffler/KIT-GE-3-Cell-Tracking-for-CTC](https://github.com/kaloeffler/KIT-GE-3-Cell-Tracking-for-CTC)
- Type: DL segmentation followed by graph-based tracking
- Dimension: 2D+t and 3D+t
- Role: high-performing CTC reference pipeline and possible 3D benchmark
- Watch for: Gurobi dependency, licensing/setup, and the complexity of coordinating separate segmentation and tracking components

### 3. Ultrack

- Paper: Bragantini et al., [Ultrack: pushing the limits of cell tracking across biological scales](https://www.nature.com/articles/s41592-025-02778-0), *Nature Methods* (2025)
- Source: [royerlab/ultrack](https://github.com/royerlab/ultrack)
- Documentation: [Ultrack documentation](https://royerlab.github.io/ultrack/)
- Type: multi-hypothesis segmentation selection and optimization-based tracking; the core tracker is not DL but can consume results from Cellpose, StarDist, PlantSeg, MicroSAM, and other DL models
- Dimension: 2D+t, 3D+t, and multichannel
- Role: primary modern 3D candidate and a useful comparison with end-to-end DL
- Watch for: Gurobi is optional but recommended; the open-source CBC solver may be slower and use more memory

## Optional stretch candidate

- [Cell-Tracker-GNN](https://github.com/talbenha/cell-tracker-gnn): Python/PyTorch graph neural network for 2D and 3D linking. Consider only after the core methods run because its environment is older and integration may require additional work.

## Method intake checklist

For each candidate, record:

- paper and official repository;
- software license;
- exact Git commit or release;
- supported dimensions and input type;
- pretrained model availability;
- Python, CUDA, GPU, solver, and system requirements;
- expected output format;
- datasets and parameter settings reported in the paper;
- successful smoke-test command;
- known blockers and estimated setup effort.

Do not copy third-party source directly into this repository without preserving its license and history. Prefer a documented clone at a pinned commit, a fork, or a Git submodule after the team agrees on the approach.
