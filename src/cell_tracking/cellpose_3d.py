"""Prepare Cellpose 3D inputs and previews for the Ultrack experiment workflow.

Used by scripts/ultrack/run_3d_cellpose.py to generate segmentation inputs for
Ultrack. This module performs preprocessing and visualization, not tracking.
"""

from pathlib import Path

import numpy as np


def prepare_volume(image: np.ndarray, sigma: list[float]) -> np.ndarray:
    """Validate ZYX input and optionally smooth it in Z, Y, X order."""
    from scipy.ndimage import gaussian_filter

    volume_dimensions = 3
    if image.ndim != volume_dimensions:
        raise ValueError(f"Expected one ZYX volume, got shape {image.shape}.")
    if not np.isfinite(image).all():
        raise ValueError("Input contains non-finite intensities.")
    image = image.astype(np.float32)
    if any(sigma):
        image = gaussian_filter(image, sigma=sigma)
    return image


def save_preview(image: np.ndarray, masks: np.ndarray, destination: Path) -> None:
    """Save raw and labeled central XY/XZ planes with reproducible colors."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from skimage.color import label2rgb

    low, high = np.percentile(image, [1, 99])
    background = np.clip((image - low) / max(float(high - low), 1e-6), 0, 1)
    z = image.shape[0] // 2
    y = image.shape[1] // 2
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    for row, (raw, labels, name) in enumerate(
        [
            (background[z], masks[z], f"XY z={z}"),
            (background[:, y, :], masks[:, y, :], f"XZ y={y}"),
        ]
    ):
        axes[row, 0].imshow(raw, cmap="gray", vmin=0, vmax=1)
        axes[row, 1].imshow(label2rgb(labels, image=raw, bg_label=0, alpha=0.4))
        axes[row, 0].set_title(f"{name}: raw")
        axes[row, 1].set_title(f"{name}: masks")
        for axis in axes[row]:
            axis.axis("off")
    fig.tight_layout()
    fig.savefig(destination, dpi=150)
    plt.close(fig)
