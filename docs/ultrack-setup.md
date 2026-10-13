# Ultrack Cluster Setup and Smoke Test

This document records the commands, software versions, verification results,
and blockers encountered while setting up Ultrack on the DSI cluster. The
installation checks are complete. The dataset smoke test is still pending.

## Environment

| Item | Value |
| --- | --- |
| Cluster compute node used for verification | `i001-ds` |
| Micromamba environment | `cell-tracking-ultrack` |
| Python | `3.12.15` |
| Python compiler | GCC `15.3.0` |
| Ultrack | `0.8.0` |
| NumPy | `2.5.4` |
| pandas | `3.0.6` |
| PyTorch | `2.14.1` |
| Zarr | `3.4.1` |
| scikit-image | `0.26.0` |
| QtPy | `2.4.3` |
| PyQt5 | `5.15.11` |
| gurobipy | `13.0.3` |
| Gurobi license | Restricted, non-production use |
| Gurobi license expiration | November 29, 2027 |

## Installation

The environment was created with Micromamba because this project is designed
to run on the DSI cluster and uses Micromamba for environment management.

```bash
micromamba create -y -n cell-tracking-ultrack python=3.12 pip
micromamba activate cell-tracking-ultrack
python -m pip install "ultrack==0.8.0"
```

Ultrack's command-line interface imports Qt through `qtpy`, but the initial pip
installation did not provide a concrete Qt binding. PyQt 5 was therefore added
from Conda Forge:

```bash
micromamba install -y -c conda-forge "pyqt>=5.15.9,<6"
```

## Installation Verification

### Command-line interface

Command:

```bash
ultrack --help
```

Result: succeeded. The command displayed the Ultrack command-line help and its
available commands, including `segment`, `link`, `solve`, `export`, and
`check_gurobi`.

### Python and Ultrack versions

Command:

```bash
python -c "import sys, ultrack; print('Python:', sys.version); print('Ultrack:', ultrack.__version__)"
```

Result:

```text
Python: 3.12.15 (main, Oct 6 2026, 23:50:18) [GCC 15.3.0]
Ultrack: 0.8.0
```

### Gurobi

Command:

```bash
ultrack check_gurobi
```

Result:

```text
Gurobi module imported successfully.
Restricted license - for non-production use only - expires 2027-11-29
Gurobi environment created successfully.
```

This confirms that Ultrack can import Gurobi, find the restricted academic
license, and create a Gurobi environment on the cluster.

## Blockers and Resolutions

### Micromamba was not initially available in the shell

Observed error:

```text
bash: micromamba: command not found
```

Resolution: installed or initialized Micromamba following the Clinic cluster
instructions, then created and activated the `cell-tracking-ultrack`
environment.

### Qt binding was missing

Observed error:

```text
qtpy.QtBindingsNotFoundError: No Qt bindings could be found
```

Cause: the pip installation included `qtpy`, which provides a common interface
to Qt, but did not provide a concrete Qt implementation.

Resolution:

```bash
micromamba install -y -c conda-forge "pyqt>=5.15.9,<6"
```

After installing PyQt 5, `ultrack --help` succeeded.

## Important Dependency Versions

The following compact version check was used to record the important direct
and runtime dependencies:

```bash
python -c "
from importlib.metadata import version

packages = [
    'ultrack', 'numpy', 'pandas', 'torch', 'zarr',
    'scikit-image', 'qtpy', 'PyQt5', 'gurobipy',
]

for package in packages:
    try:
        print(f'{package}: {version(package)}')
    except Exception:
        print(f'{package}: not installed')
"
```

The resolved versions are recorded in the Environment table above. A full
`pip freeze` is not included here because it contains many indirect packages
that are not useful in the short setup note.

## Dataset Smoke Test

Status: pending.

The smoke test should use the selected small 2D CTC training dataset or a small
consecutive subset. Before running it, record:

- the dataset and sequence name;
- the exact frame range;
- whether the input consists of raw images, foreground and contour images, or
  existing segmentation labels;
- the Ultrack configuration file and any values changed from the defaults;
- the exact command used;
- the output directory; and
- whether the run completed successfully.

### Planned test record

| Field | Value |
| --- | --- |
| Dataset | To be selected |
| Sequence and frames | Pending |
| Input type | Pending |
| Configuration | Pending |
| Exact command | Pending |
| Output directory | Pending |
| Result | Pending |
| Runtime | Pending |
| Errors or warnings | Pending |
| Next action | Select and inspect a small consecutive 2D input subset |

## Current Status

- [x] Create and activate a cluster environment.
- [x] Install Ultrack 0.8.0.
- [x] Resolve the missing Qt binding.
- [x] Verify the Ultrack command-line interface.
- [x] Verify the Python and Ultrack versions.
- [x] Verify the Gurobi installation and license.
- [x] Record the important dependency versions.
- [ ] Select and inspect the smoke-test input.
- [ ] Run the dataset smoke test.
- [ ] Record the exact configuration, output location, runtime, and result.
- [ ] Convert the working environment into a reproducible Micromamba recipe.
