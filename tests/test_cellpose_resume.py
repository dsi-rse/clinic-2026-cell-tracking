"""Verify restart safety without loading Cellpose or a GPU."""

import numpy as np
import pytest
import tifffile

from cell_tracking.cellpose_resume import (
    load_checkpoint,
    read_saved_mask,
    write_checkpoint,
)


def test_saved_mask_and_interrupted_write(tmp_path):
    """Reuse complete masks but reject truncated files and wrong shapes."""
    mask = tmp_path / "mask000.tif"
    labels = np.ones((3, 5, 5), dtype=np.uint16)
    tifffile.imwrite(mask, labels, photometric="minisblack")
    np.testing.assert_array_equal(read_saved_mask(mask, labels.shape), labels)
    assert read_saved_mask(mask, (4, 5, 5)) is None
    mask.write_bytes(b"interrupted TIFF write")
    assert read_saved_mask(mask, labels.shape) is None


def test_resume_preserves_history_and_rejects_changed_parameters(tmp_path):
    """Allow a pilot range to expand without mixing different diameters."""
    path = tmp_path / "run.json"
    config = {"diameter": 15, "frame_stop": 3}
    versions = {"cellpose": "4.2.1.1"}
    history = [{"input": "t000.tif", "seconds": 800}]
    write_checkpoint(
        path,
        {
            "configuration": config,
            "versions": versions,
            "frames": history,
            "blocker": "expired",
        },
    )
    resumed = load_checkpoint(path, {**config, "frame_stop": None}, versions)
    assert resumed["frames"] == history
    assert "blocker" not in resumed
    assert resumed["configuration"]["frame_stop"] is None
    with pytest.raises(ValueError, match="diameter changed"):
        load_checkpoint(path, {**config, "diameter": 140}, versions)
