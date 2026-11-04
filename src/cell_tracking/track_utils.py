"""Small helpers for drawing tracking results, shared by the visualization scripts."""

import colorsys

import numpy as np
from scipy import ndimage

GOLDEN_RATIO_CONJUGATE = 0.61803398875
RGB_MAXIMUM = 255


def track_color(track_id: int) -> tuple[int, int, int]:
    """Return a bright RGB colour (0..255), the same for a track id in every frame."""
    hue = (track_id * GOLDEN_RATIO_CONJUGATE) % 1.0
    red, green, blue = colorsys.hsv_to_rgb(hue, 0.85, 1.0)
    return (
        int(RGB_MAXIMUM * red),
        int(RGB_MAXIMUM * green),
        int(RGB_MAXIMUM * blue),
    )


def label_centroids(labels: np.ndarray) -> dict[int, tuple[float, float]]:
    """Map each label id to the (x, y) centre of mass of that label in one frame."""
    ids = np.unique(labels)
    ids = ids[ids > 0]
    if len(ids) == 0:
        return {}
    centres = ndimage.center_of_mass(labels > 0, labels, ids)
    return {
        int(label_id): (float(x), float(y))
        for label_id, (y, x) in zip(ids, centres, strict=True)
    }
