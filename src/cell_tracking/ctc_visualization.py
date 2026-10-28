"""Render diagnostic overlays for 2D Cell Tracking Challenge results."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

EXPECTED_DIMENSIONS = 2
RGB_MAXIMUM = 255
DEFAULT_HEADER_HEIGHT = 62
DEFAULT_TEXT_SIZE = 15

GROUND_TRUTH_COLOR = np.array([0, 255, 90], dtype=np.float32)
PREDICTION_COLOR = np.array([255, 0, 210], dtype=np.float32)
OVERLAP_COLOR = np.array([70, 220, 70], dtype=np.float32)
PREDICTION_ONLY_COLOR = np.array([255, 70, 70], dtype=np.float32)
GROUND_TRUTH_ONLY_COLOR = np.array([60, 190, 255], dtype=np.float32)


@dataclass(frozen=True)
class ObjectMatchCounts:
    """Counts from one-to-one instance matching in a single frame."""

    matched: int
    unmatched_prediction: int
    unmatched_ground_truth: int


def normalize_raw_image(
    image: np.ndarray,
    lower_percentile: float = 1.0,
    upper_percentile: float = 99.8,
) -> np.ndarray:
    """Normalize a microscopy image to an 8-bit grayscale image."""
    lower, upper = np.percentile(image, [lower_percentile, upper_percentile])
    if upper <= lower:
        return np.zeros(image.shape, dtype=np.uint8)

    normalized = np.clip((image.astype(np.float32) - lower) / (upper - lower), 0, 1)
    return (normalized * RGB_MAXIMUM).astype(np.uint8)


def find_label_boundaries(labels: np.ndarray) -> np.ndarray:
    """Return inner boundaries between labels and their neighbors."""
    boundaries = np.zeros_like(labels, dtype=bool)
    boundaries[1:, :] |= labels[1:, :] != labels[:-1, :]
    boundaries[:-1, :] |= labels[:-1, :] != labels[1:, :]
    boundaries[:, 1:] |= labels[:, 1:] != labels[:, :-1]
    boundaries[:, :-1] |= labels[:, :-1] != labels[:, 1:]
    return boundaries & (labels != 0)


def widen_mask(mask: np.ndarray, width: int) -> np.ndarray:
    """Expand a binary mask without requiring an image-processing dependency."""
    if width < 1:
        raise ValueError("Boundary width must be at least 1.")

    widened = mask.copy()
    for _ in range(width - 1):
        expanded = widened.copy()
        expanded[1:, :] |= widened[:-1, :]
        expanded[:-1, :] |= widened[1:, :]
        expanded[:, 1:] |= widened[:, :-1]
        expanded[:, :-1] |= widened[:, 1:]
        widened = expanded
    return widened


def match_instances(
    ground_truth: np.ndarray,
    prediction: np.ndarray,
    iou_threshold: float,
) -> ObjectMatchCounts:
    """Greedily match overlapping instances using intersection over union."""
    ground_truth_ids, ground_truth_areas = np.unique(
        ground_truth[ground_truth > 0],
        return_counts=True,
    )
    prediction_ids, prediction_areas = np.unique(
        prediction[prediction > 0],
        return_counts=True,
    )

    ground_truth_area = dict(
        zip(ground_truth_ids.tolist(), ground_truth_areas.tolist())
    )
    prediction_area = dict(zip(prediction_ids.tolist(), prediction_areas.tolist()))
    overlap = (ground_truth > 0) & (prediction > 0)

    candidates: list[tuple[float, int, int]] = []
    if np.any(overlap):
        pairs = np.column_stack((ground_truth[overlap], prediction[overlap]))
        unique_pairs, intersections = np.unique(pairs, axis=0, return_counts=True)
        for (ground_truth_id, prediction_id), intersection in zip(
            unique_pairs,
            intersections,
        ):
            union = (
                ground_truth_area[int(ground_truth_id)]
                + prediction_area[int(prediction_id)]
                - int(intersection)
            )
            iou = float(intersection) / union
            if iou >= iou_threshold:
                candidates.append((iou, int(ground_truth_id), int(prediction_id)))

    matched_ground_truth: set[int] = set()
    matched_prediction: set[int] = set()
    for _, ground_truth_id, prediction_id in sorted(candidates, reverse=True):
        if (
            ground_truth_id not in matched_ground_truth
            and prediction_id not in matched_prediction
        ):
            matched_ground_truth.add(ground_truth_id)
            matched_prediction.add(prediction_id)

    return ObjectMatchCounts(
        matched=len(matched_prediction),
        unmatched_prediction=len(prediction_ids) - len(matched_prediction),
        unmatched_ground_truth=len(ground_truth_ids) - len(matched_ground_truth),
    )


def blend_color(
    image: np.ndarray,
    mask: np.ndarray,
    color: np.ndarray,
    alpha: float,
) -> None:
    """Blend one color into an RGB image in place."""
    image[mask] = (image[mask].astype(np.float32) * (1 - alpha) + color * alpha).astype(
        np.uint8
    )


def _load_font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    """Load a readable bundled font, with a basic fallback."""
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size=size)
    except OSError:
        return ImageFont.load_default()


def _largest_label_centroids(
    labels: np.ndarray,
    maximum_labels: int,
) -> list[tuple[int, float, float]]:
    """Return centroids for the largest labels in a frame."""
    label_ids, counts = np.unique(labels[labels > 0], return_counts=True)
    order = np.argsort(counts)[::-1][:maximum_labels]
    centroids = []
    for index in order:
        label_id = int(label_ids[index])
        rows, columns = np.nonzero(labels == label_id)
        centroids.append((label_id, float(columns.mean()), float(rows.mean())))
    return centroids


def _draw_track_ids(
    canvas: Image.Image,
    labels: np.ndarray,
    prefix: str,
    color: tuple[int, int, int],
    x_offset: int,
    y_offset: int,
    maximum_labels: int,
) -> None:
    """Draw track identifiers at object centroids."""
    draw = ImageDraw.Draw(canvas)
    font = _load_font(DEFAULT_TEXT_SIZE)
    for label_id, x_position, y_position in _largest_label_centroids(
        labels,
        maximum_labels,
    ):
        draw.text(
            (x_offset + x_position, y_offset + y_position),
            f"{prefix}{label_id}",
            fill=color,
            font=font,
            stroke_width=2,
            stroke_fill=(0, 0, 0),
        )


def render_overlay_frame(
    raw: np.ndarray,
    ground_truth: np.ndarray | None,
    prediction: np.ndarray,
    frame_number: int,
    ground_truth_source: str,
    alpha: float,
    boundary_width: int,
    iou_threshold: float,
    show_track_ids: bool,
    maximum_track_labels: int,
    tracking_only: bool,
) -> Image.Image:
    """Render boundaries and segmentation agreement for one 2D frame."""
    if raw.ndim != EXPECTED_DIMENSIONS or prediction.ndim != EXPECTED_DIMENSIONS:
        raise ValueError("The overlay renderer currently supports only 2D images.")
    if raw.shape != prediction.shape:
        raise ValueError(
            f"Raw and prediction shapes differ: {raw.shape} and {prediction.shape}."
        )
    if ground_truth is not None and ground_truth.shape != raw.shape:
        raise ValueError(
            "Raw and ground-truth shapes differ: "
            f"{raw.shape} and {ground_truth.shape}."
        )

    grayscale = normalize_raw_image(raw)
    base = np.repeat(grayscale[:, :, np.newaxis], 3, axis=2)
    boundary_panel = base.copy()
    agreement_panel = base.copy()

    prediction_boundary = widen_mask(
        find_label_boundaries(prediction),
        boundary_width,
    )
    boundary_panel[prediction_boundary] = PREDICTION_COLOR.astype(np.uint8)

    match_counts = None
    if ground_truth is not None:
        ground_truth_boundary = widen_mask(
            find_label_boundaries(ground_truth),
            boundary_width,
        )
        boundary_panel[ground_truth_boundary] = GROUND_TRUTH_COLOR.astype(np.uint8)
        coincident_boundary = ground_truth_boundary & prediction_boundary
        boundary_panel[coincident_boundary] = RGB_MAXIMUM

        if not tracking_only:
            overlap = (ground_truth > 0) & (prediction > 0)
            prediction_only = (prediction > 0) & (ground_truth == 0)
            ground_truth_only = (ground_truth > 0) & (prediction == 0)
            blend_color(agreement_panel, overlap, OVERLAP_COLOR, alpha)
            blend_color(
                agreement_panel,
                prediction_only,
                PREDICTION_ONLY_COLOR,
                alpha,
            )
            blend_color(
                agreement_panel,
                ground_truth_only,
                GROUND_TRUTH_ONLY_COLOR,
                alpha,
            )
            match_counts = match_instances(ground_truth, prediction, iou_threshold)

    height, width = grayscale.shape
    canvas = Image.new(
        "RGB",
        (width if tracking_only else width * 2, height + DEFAULT_HEADER_HEIGHT),
        color=(18, 18, 18),
    )
    canvas.paste(Image.fromarray(boundary_panel), (0, DEFAULT_HEADER_HEIGHT))
    if not tracking_only:
        canvas.paste(Image.fromarray(agreement_panel), (width, DEFAULT_HEADER_HEIGHT))

    draw = ImageDraw.Draw(canvas)
    font = _load_font(DEFAULT_TEXT_SIZE)
    title = f"Frame {frame_number:03d} | GT source: {ground_truth_source}"
    if ground_truth is None:
        title += " | ground truth unavailable"
    elif match_counts is not None:
        title += (
            f" | IoU >= {iou_threshold:g}: matched {match_counts.matched}, "
            f"unmatched prediction {match_counts.unmatched_prediction}, "
            f"unmatched GT {match_counts.unmatched_ground_truth}"
        )
    draw.text((10, 6), title, fill=(255, 255, 255), font=font)
    draw.text(
        (10, 34),
        "Boundaries: GT green | prediction magenta | coincident white",
        fill=(230, 230, 230),
        font=font,
    )
    if not tracking_only:
        draw.text(
            (width + 10, 34),
            "Pixels: overlap green | prediction-only red | GT-only cyan",
            fill=(230, 230, 230),
            font=font,
        )

    if show_track_ids:
        if ground_truth is not None:
            _draw_track_ids(
                canvas,
                ground_truth,
                prefix="G",
                color=(0, 255, 90),
                x_offset=0,
                y_offset=DEFAULT_HEADER_HEIGHT,
                maximum_labels=maximum_track_labels,
            )
        _draw_track_ids(
            canvas,
            prediction,
            prefix="P",
            color=(255, 0, 210),
            x_offset=0,
            y_offset=DEFAULT_HEADER_HEIGHT,
            maximum_labels=maximum_track_labels,
        )

    return canvas


def save_animated_gif(
    frames: list[Image.Image],
    output_path: Path,
    frames_per_second: float,
    scale: float,
) -> None:
    """Save rendered frames as a looping animated GIF."""
    if not frames:
        raise ValueError("At least one rendered frame is required.")
    if frames_per_second <= 0:
        raise ValueError("Frames per second must be greater than zero.")
    if scale <= 0:
        raise ValueError("Scale must be greater than zero.")

    if scale != 1:
        resized_frames = []
        for frame in frames:
            size = (
                max(1, round(frame.width * scale)),
                max(1, round(frame.height * scale)),
            )
            resized_frames.append(frame.resize(size, Image.Resampling.LANCZOS))
        frames = resized_frames

    output_path.parent.mkdir(parents=True, exist_ok=True)
    duration_milliseconds = round(1000 / frames_per_second)
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=duration_milliseconds,
        loop=0,
        disposal=2,
    )
