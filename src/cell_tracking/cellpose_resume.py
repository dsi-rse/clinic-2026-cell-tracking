"""Checkpoint helpers for Cellpose segmentation in the Ultrack workflow.

Used by the 3D Cellpose runner and the 2D segmentation-parameter runner under
scripts/ultrack. These checkpoints cover saved segmentation masks, not the
Ultrack solver state.
"""

import json
from pathlib import Path

import numpy as np
import tifffile

RESUME_SETTINGS = (
    "input_dir",
    "dataset",
    "model",
    "diameter",
    "anisotropy",
    "cellprob_threshold",
    "min_size",
    "batch_size",
    "sigma",
    "tile_norm_blocksize",
)


def write_checkpoint(path: Path, metadata: dict) -> None:
    """Replace the run record only after the new JSON is fully written."""
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(metadata, indent=2) + "\n")
    temporary.replace(path)


def load_checkpoint(path: Path, configuration: dict, versions: dict) -> dict:
    """Reject resume attempts that would mix different experiment settings."""
    metadata = json.loads(path.read_text())
    previous = metadata["configuration"]
    for key in RESUME_SETTINGS:
        if previous.get(key) != configuration.get(key):
            raise ValueError(
                f"Cannot resume: {key} changed. Use a new output directory."
            )
    if metadata["versions"]["cellpose"] != versions["cellpose"]:
        raise ValueError("Cannot resume with a different Cellpose version.")
    metadata["configuration"] = configuration
    metadata.pop("blocker", None)
    return metadata


def read_saved_mask(path: Path, shape: tuple) -> np.ndarray | None:
    """Return a readable, integer mask of the expected shape, otherwise retry it."""
    if not path.exists():
        return None
    try:
        masks = tifffile.imread(path)
    except (OSError, ValueError, EOFError):
        return None
    if masks.shape != shape or not np.issubdtype(masks.dtype, np.integer):
        return None
    if masks.min() < 0:
        return None
    return masks
