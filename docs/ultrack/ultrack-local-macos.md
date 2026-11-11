# Local Ultrack and Cellpose setup on macOS

This guide recreates the local environment used for Cellpose, Ultrack, and
Napari. It was verified on an Apple Silicon MacBook Air on November 10, 2026.
The cluster setup remains documented separately in
[`ultrack-setup.md`](ultrack-setup.md), and the dataset-specific annotation
workflow is recorded in
[`cls-2d-annotation.md`](cls-2d-annotation.md).

## Scope

The environment supports Cellpose segmentation, Ultrack tracking with Gurobi,
and Napari inspection. Dataset selection, cropping, experimental parameters,
and manual-annotation decisions do not belong in this setup guide.

The verified PyTorch build is CPU-only. Do not pass `--cellpose-gpu` in this
environment. The selected CLS crop is small enough for a CPU pilot.

## Verified direct versions

| Component | Version or setting |
| --- | --- |
| Environment name | `ultrack-cell-tracking-local` |
| Python | 3.12.16 |
| NumPy | 2.0.2 |
| PyTorch | 2.14.1, conda CPU build |
| Cellpose | 3.1.1.3 |
| Ultrack | 0.8.0 |
| Napari | 0.10.0 |
| PyQt6 | 6.11.0 |
| Qt selection | `QT_API=pyqt6` |
| GurobiPy | 13.0.3 |
| Solver interface | Python-MIP with Gurobi |

## 1. Create the environment

Install a conda distribution that supports Apple Silicon, then run the
following commands from the repository root:

```bash
conda env create --file environments/ultrack-cellpose-macos.yaml
conda activate ultrack-cell-tracking-local
python -m pip install -e . --no-deps
```

The environment file deliberately installs PyTorch through conda before pip
installs Cellpose and Ultrack. Do not replace it with pip PyTorch in this
environment. On macOS, conda NumPy/OpenBLAS and the pip PyTorch wheel can load
separate copies of `libomp.dylib`, causing the process to abort before Ultrack
runs.

The environment also uses PyQt6. Ultrack's Napari dependency resolves to
Napari 0.10.0, which requires Qt 6.7 or newer.

## 2. Configure Gurobi

Place the private license file at the per-user default location:

```text
/Users/<username>/gurobi.lic
```

Do not place `gurobi.lic` in this repository, commit it to Git, or share its
contents. The environment pins `gurobipy==13.0.3`, so the license must permit
Gurobi 13. A version-13 license can run Gurobi 13 and earlier but not Gurobi
14.

Check that the command-line installation can find the license:

```bash
gurobi_cl --license
```

The output should identify the license file in the user's home directory and
report a valid license. Do not copy the username, license ID, or other private
license details into project documentation.

## 3. Verify the complete environment

Activate the environment before every local session:

```bash
conda activate ultrack-cell-tracking-local
```

Verify that NumPy and PyTorch can be imported together without an OpenMP
error:

```bash
python -c "import numpy, torch; print('NumPy:', numpy.__version__); print('PyTorch:', torch.__version__); print('MPS:', torch.backends.mps.is_available())"
```

The verified environment reports NumPy 2.0.2, PyTorch 2.14.1, and
`MPS: False`.

Verify that Napari selects PyQt6:

```bash
python -c "import os, qtpy, napari; print('QT_API:', os.environ.get('QT_API')); print('Qt:', qtpy.API_NAME); print('Napari:', napari.__version__)"
```

The output should report `QT_API: pyqt6`, a PyQt6 Qt API, and Napari 0.10.0.

Verify Gurobi through Ultrack:

```bash
ultrack check_gurobi
```

A successful check reports that the Gurobi module imported and a Gurobi
environment was created.

Finally, verify the Python-MIP interface used by Ultrack's solver:

```bash
python -c "from mip import GUROBI, Model; model = Model(solver_name=GUROBI); print(model.solver_name)"
```

The expected final line is `GRB`.

## 4. Continue to the annotation workflow

After every verification command succeeds, continue with the separate
[`CLS 2D annotation guide`](cls-2d-annotation.md). That document records the
selected movie, fixed subset, Fiji preparation, Cellpose and Ultrack workflow,
manual-correction conventions, and annotation status.

## 5. Troubleshooting decisions captured by this environment

### Duplicate OpenMP runtime

**Symptom:** importing PyTorch or running `ultrack check_gurobi` aborts with
`OMP: Error #15` and reports that `libomp.dylib` was already initialized.

**Cause:** conda NumPy/OpenBLAS loads one OpenMP runtime while pip PyTorch loads
its bundled copy.

**Resolution:** recreate this environment from the supplied macOS file, which
installs PyTorch through conda. Do not use the
`KMP_DUPLICATE_LIB_OK=TRUE` workaround; it can hide crashes or incorrect
results.

### Napari imports PyQt5

**Symptom:** Napari reports that Qt 6.7 or newer is required but PyQt5 was
imported.

**Resolution:** use the supplied PyQt6 environment. It records
`QT_API=pyqt6`, so the Qt backend is selected before Napari imports it.

### Gurobi package is newer than the license

**Symptom:** `ultrack check_gurobi` imports Gurobi but reports that version 14
is installed while the license permits version 13.

**Resolution:** keep `gurobipy==13.0.3`, as pinned in the environment file, or
obtain a license for the newer major version. Ultrack 0.8.0 accepts GurobiPy
13.0.3.
