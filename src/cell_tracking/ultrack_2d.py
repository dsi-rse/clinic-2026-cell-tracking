"""Generate 2D instance labels for the Ultrack benchmark workflow."""

import os
from pathlib import Path

import numpy as np
import tifffile

EXPECTED_IMAGE_DIMENSIONS = 2


def load_image_stack(image_paths: list[Path]) -> np.ndarray:
    """Load a time-ordered list of 2D TIFF images into one array."""
    if not image_paths:
        raise ValueError("At least one image path is required.")

    images = [tifffile.imread(path) for path in image_paths]
    shapes = {image.shape for image in images}
    if len(shapes) != 1:
        raise ValueError(f"Raw images do not all have the same shape: {shapes}")
    if images[0].ndim != EXPECTED_IMAGE_DIMENSIONS:
        raise ValueError(
            "Expected 2D images shaped (Y, X), "
            f"but found individual shape {images[0].shape}."
        )

    return np.stack(images)


def load_label_stack(label_dir: Path, frame_numbers: list[int]) -> np.ndarray:
    """Load instance-label TIFFs for a specific ordered list of frames."""
    if not label_dir.is_dir():
        raise FileNotFoundError(f"Label directory does not exist: {label_dir}")
    if not frame_numbers:
        raise ValueError("At least one frame number is required.")

    label_paths = [label_dir / f"mask{frame:03d}.tif" for frame in frame_numbers]
    missing_paths = [path for path in label_paths if not path.is_file()]
    if missing_paths:
        missing_names = ", ".join(path.name for path in missing_paths[:5])
        raise FileNotFoundError(f"Missing label files in {label_dir}: {missing_names}")

    labels = [tifffile.imread(path) for path in label_paths]
    return np.stack(labels)


def combine_label_stacks(
    label_dirs: dict[str, Path],
    frame_numbers: list[int],
    expected_shape: tuple[int, ...],
    contour_sigma: float,
) -> tuple[np.ndarray, np.ndarray, dict[str, dict[str, int]]]:
    """Combine label-derived foregrounds by OR and contours by mean."""
    if not label_dirs:
        raise ValueError("At least one label directory is required.")

    try:
        from ultrack.utils import labels_to_contours
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            "Ultrack is required to combine instance-label inputs."
        ) from error

    combined_foreground = np.zeros(expected_shape, dtype=bool)
    contour_sum = np.zeros(expected_shape, dtype=np.float32)
    label_counts: dict[str, dict[str, int]] = {}

    for method, label_dir in label_dirs.items():
        print(f"Loading {method} labels from {label_dir}")
        labels = load_label_stack(label_dir, frame_numbers)
        validate_labels(labels, expected_shape)
        label_counts[method] = {
            str(frame): int(np.count_nonzero(np.unique(frame_labels)))
            for frame, frame_labels in zip(frame_numbers, labels)
        }

        print(f"Converting {method} labels to foreground and contours")
        method_foreground, method_contours = labels_to_contours(
            labels,
            sigma=contour_sigma,
        )
        combined_foreground |= np.asarray(method_foreground, dtype=bool)
        contour_sum += np.asarray(method_contours, dtype=np.float32)
        del labels, method_foreground, method_contours

    combined_contours = contour_sum / len(label_dirs)
    return combined_foreground, combined_contours, label_counts


def find_label_boundaries(labels: np.ndarray) -> np.ndarray:
    """Find inner boundaries between 2D labels and the background."""
    boundaries = np.zeros_like(labels, dtype=bool)

    boundaries[1:, :] |= labels[1:, :] != labels[:-1, :]
    boundaries[:-1, :] |= labels[:-1, :] != labels[1:, :]
    boundaries[:, 1:] |= labels[:, 1:] != labels[:, :-1]
    boundaries[:, :-1] |= labels[:, :-1] != labels[:, 1:]

    return boundaries & (labels != 0)


def segment_with_stardist(
    images: np.ndarray,
    model_name: str,
    block_size: int,
    min_overlap: int,
) -> np.ndarray:
    """Segment a 2D time series with a pretrained StarDist model."""
    try:
        from stardist.models import StarDist2D
        from ultrack.imgproc import normalize
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            "StarDist is required for --method stardist. Activate the "
            "cell-tracking-ultrack-stardist environment created from "
            "environments/ultrack-stardist.yaml."
        ) from error

    model = StarDist2D.from_pretrained(model_name)
    labels = np.zeros_like(images, dtype=np.int32)

    for index, image in enumerate(images):
        print(f"StarDist frame {index + 1}/{len(images)}")
        normalized = normalize(image, gamma=1.0)
        frame_labels, _ = model.predict_instances_big(
            normalized,
            axes="YX",
            block_size=block_size,
            min_overlap=min_overlap,
            show_progress=False,
        )
        labels[index] = frame_labels

    return labels


def segment_with_cellpose(
    images: np.ndarray,
    model_name: str,
    use_gpu: bool,
    diameter: float | None,
    flow_threshold: float,
    cellprob_threshold: float,
    model_cache_dir: Path | None,
) -> np.ndarray:
    """Segment a 2D time series with a pretrained Cellpose 3 model."""
    if model_cache_dir is not None:
        os.environ["CELLPOSE_LOCAL_MODELS_PATH"] = str(model_cache_dir)

    try:
        from cellpose import models
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            "Cellpose is required for --method cellpose. Activate the "
            "cell-tracking-ultrack-cellpose environment."
        ) from error

    model = models.Cellpose(gpu=use_gpu, model_type=model_name)
    masks, _, _, _ = model.eval(
        list(images),
        diameter=diameter,
        channels=[0, 0],
        do_3D=False,
        flow_threshold=flow_threshold,
        cellprob_threshold=cellprob_threshold,
    )
    return np.stack(masks).astype(np.int32)


def segment_with_watershed(
    images: np.ndarray,
    smoothing_sigma: float,
    h_minima: float,
    minimum_object_size: int,
) -> np.ndarray:
    """Segment bright cells using Otsu foreground and h-minima watershed."""
    from scipy import ndimage as ndi
    from skimage.filters import gaussian, threshold_otsu
    from skimage.morphology import h_maxima, remove_small_objects
    from skimage.segmentation import watershed

    frame_labels = []
    for index, image in enumerate(images):
        print(f"Watershed frame {index + 1}/{len(images)}")
        smoothed = gaussian(image, sigma=smoothing_sigma, preserve_range=True)
        foreground = smoothed > threshold_otsu(smoothed)
        foreground = remove_small_objects(
            foreground,
            min_size=minimum_object_size,
        )

        distance = ndi.distance_transform_edt(foreground)
        seed_mask = h_maxima(distance, h=h_minima)
        markers, marker_count = ndi.label(seed_mask)

        if marker_count == 0:
            labels = np.zeros_like(image, dtype=np.int32)
        else:
            labels = watershed(-distance, markers=markers, mask=foreground)

        frame_labels.append(labels.astype(np.int32))

    return np.stack(frame_labels)


def validate_labels(labels: np.ndarray, image_shape: tuple[int, ...]) -> None:
    """Validate a generated instance-label stack before Ultrack conversion."""
    if labels.shape != image_shape:
        raise ValueError(
            f"Label shape {labels.shape} does not match image shape {image_shape}."
        )
    if not np.issubdtype(labels.dtype, np.integer):
        raise TypeError(f"Expected integer labels, found {labels.dtype}.")
    if labels.min() < 0:
        raise ValueError("Instance labels must be nonnegative.")
