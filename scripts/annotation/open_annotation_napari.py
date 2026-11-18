"""Open the CLS images and masks in guaranteed frame order."""

import json
from datetime import UTC, datetime
from pathlib import Path

import napari
import numpy as np
import pandas as pd
import tifffile
from napari.utils.colormaps import DirectLabelColormap
from napari.utils.notifications import show_info, show_warning


raw_dir = Path(
    "external/data/cropped_movies_frame0_19/runner_input"
)
mask_dir = Path(
    "external/annotations/cls-loose-colony/labels-working"
)
track_mask_dir = Path(
    "external/annotations/cls-loose-colony/tracking-draft-mutual-best"
)
checkpoint_path = Path(
    "external/annotations/cls-loose-colony/annotation_checkpoint.json"
)

raw_paths = [raw_dir / f"t{frame:03d}.tif" for frame in range(20)]
mask_paths = [mask_dir / f"mask{frame:03d}.tif" for frame in range(20)]
track_mask_paths = [
    track_mask_dir / f"mask{frame:03d}.tif" for frame in range(20)
]

missing = [
    path for path in raw_paths + mask_paths + track_mask_paths
    if not path.is_file()
]
if missing:
    raise FileNotFoundError(f"Missing input files: {missing}")

images = np.stack([tifffile.imread(path) for path in raw_paths])
labels = np.stack([tifffile.imread(path) for path in mask_paths])
track_labels = np.stack(
    [tifffile.imread(path) for path in track_mask_paths]
)

expected_shape = (20, 1024, 1024)
if images.shape != expected_shape:
    raise ValueError(f"Unexpected image shape: {images.shape}")
if labels.shape != expected_shape:
    raise ValueError(f"Unexpected label shape: {labels.shape}")
if track_labels.shape != expected_shape:
    raise ValueError(
        f"Unexpected track-label shape: {track_labels.shape}"
    )

print(f"Raw images: {images.shape}, {images.dtype}")
print(f"Labels: {labels.shape}, {labels.dtype}")
print(f"Track labels: {track_labels.shape}, {track_labels.dtype}")

viewer = napari.Viewer()
viewer.add_image(images, name="raw-images")

labels_layer = viewer.add_labels(
    labels,
    name="labels-working",
    opacity=1.0,
)
labels_layer.contour = 2

track_labels_layer = viewer.add_labels(
    track_labels,
    name="track-labels-working",
    opacity=1.0,
    visible=True,
)
track_labels_layer.contour = 2

unassigned_tracking = (
    (labels_layer.data != 0) & (track_labels_layer.data == 0)
).astype(np.uint8)
review_colormap = DirectLabelColormap(
    color_dict={
        0: np.array([0.0, 0.0, 0.0, 0.0]),
        1: np.array([1.0, 0.0, 1.0, 1.0]),
        None: np.array([0.0, 0.0, 0.0, 0.0]),
    }
)
unassigned_tracking_layer = viewer.add_labels(
    unassigned_tracking,
    name="tracking-needs-review",
    colormap=review_colormap,
    opacity=1.0,
)
unassigned_tracking_layer.contour = 4

freehand_layer = viewer.add_shapes(
    name="freehand-annotations",
    ndim=3,
    edge_color="yellow",
    face_color=[1.0, 1.0, 0.0, 0.2],
)
freehand_layer.mode = "add_polygon_lasso"


def _shapes_are_single_frame(layer) -> bool:
    """Return whether every freehand shape belongs to one time frame."""
    for polygon in layer.data:
        if polygon.shape[1] != 3:
            show_warning("Expected freehand coordinates shaped (T, Y, X).")
            return False
        if not np.allclose(polygon[:, 0], polygon[0, 0]):
            show_warning("Each freehand shape must stay within one time frame.")
            return False
    return True


def _clear_freehand_shapes(layer) -> None:
    """Remove all committed freehand shapes from the temporary layer."""
    layer.selected_data = set(range(layer.nshapes))
    layer.remove_selected()


@freehand_layer.bind_key("N", overwrite=True)
def commit_new_segmentation_labels(layer) -> None:
    """Commit each freehand shape as a new segmentation label."""
    if layer.nshapes == 0:
        show_warning("Draw at least one freehand shape before pressing N.")
        return
    if not _shapes_are_single_frame(layer):
        return

    next_label = int(labels_layer.data.max()) + 1
    preserve_labels = labels_layer.preserve_labels
    labels_layer.preserve_labels = True
    try:
        for polygon in layer.data:
            labels_layer.paint_polygon(polygon, next_label)
            next_label += 1
    finally:
        labels_layer.preserve_labels = preserve_labels

    labels_layer.selected_label = next_label - 1
    committed_count = layer.nshapes
    _clear_freehand_shapes(layer)
    show_info(
        f"Added {committed_count} new segmentation label(s)."
    )


@freehand_layer.bind_key("E", overwrite=True)
def extend_selected_segmentation_label(layer) -> None:
    """Extend the selected segmentation label into one freehand shape."""
    if layer.nshapes != 1:
        show_warning("Draw exactly one freehand shape before pressing E.")
        return
    if not _shapes_are_single_frame(layer):
        return

    polygon = layer.data[0]
    frame = int(round(float(polygon[0, 0])))
    label_id = int(labels_layer.selected_label)
    if label_id == 0 or not np.any(
        labels_layer.data[frame] == label_id
    ):
        show_warning(
            "Select an existing segmentation label in this frame with the "
            "picker before pressing E."
        )
        return

    pixel_count_before = np.count_nonzero(
        labels_layer.data[frame] == label_id
    )
    preserve_labels = labels_layer.preserve_labels
    labels_layer.preserve_labels = True
    try:
        labels_layer.paint_polygon(polygon, label_id)
    finally:
        labels_layer.preserve_labels = preserve_labels

    pixel_count_after = np.count_nonzero(
        labels_layer.data[frame] == label_id
    )
    added_pixels = pixel_count_after - pixel_count_before
    _clear_freehand_shapes(layer)
    show_info(
        f"Extended segmentation label {label_id} by {added_pixels} pixel(s)."
    )


@freehand_layer.bind_key("T", overwrite=True)
def commit_selected_track_id(layer) -> None:
    """Commit one freehand shape using the selected tracking ID."""
    if layer.nshapes != 1:
        show_warning("Draw exactly one freehand shape before pressing T.")
        return
    if not _shapes_are_single_frame(layer):
        return

    track_id = int(track_labels_layer.selected_label)
    if track_id == 0 or not np.any(track_labels_layer.data == track_id):
        show_warning(
            "Select an existing track ID with the picker before pressing T."
        )
        return

    track_labels_layer.paint_polygon(layer.data[0], track_id)
    _clear_freehand_shapes(layer)
    show_info(f"Applied track ID {track_id} to the freehand shape.")


print(
    "Freehand controls: draw on 'freehand-annotations', then press N for "
    "new segmentation labels, E to extend the selected segmentation label, "
    "or T for the selected tracking ID."
)


def _selected_segmentation_mask() -> tuple[int, int, np.ndarray] | None:
    """Return the current frame, selected ID, and selected nucleus mask."""
    frame = int(viewer.dims.current_step[0])
    segment_id = int(labels_layer.selected_label)
    segment_mask = labels_layer.data[frame] == segment_id
    if segment_id == 0 or not np.any(segment_mask):
        show_warning(
            "Select a nucleus in labels-working with the picker first."
        )
        return None
    return frame, segment_id, segment_mask


def _refresh_tracking_review(frame: int) -> None:
    """Update the magenta review overlay after a tracking edit."""
    unassigned_tracking_layer.data[frame] = (
        (labels_layer.data[frame] != 0)
        & (track_labels_layer.data[frame] == 0)
    )
    unassigned_tracking_layer.refresh()
    track_labels_layer.refresh()


def _assign_track_id_to_segment(track_id: int) -> None:
    """Assign one complete corrected nucleus mask to a track ID."""
    selected = _selected_segmentation_mask()
    if selected is None:
        return
    frame, segment_id, segment_mask = selected

    track_frame = track_labels_layer.data[frame]
    track_elsewhere = (track_frame == track_id) & ~segment_mask
    if np.any(track_elsewhere):
        show_warning(
            f"Track ID {track_id} is already assigned to another nucleus "
            f"in frame {frame}."
        )
        return

    track_frame[segment_mask] = track_id
    track_labels_layer.selected_label = track_id
    _refresh_tracking_review(frame)
    show_info(
        f"Assigned segmentation label {segment_id} in frame {frame} "
        f"to track ID {track_id}."
    )


@viewer.bind_key("A", overwrite=True)
def assign_selected_track_id(_viewer) -> None:
    """Assign the selected existing track ID to the selected nucleus."""
    track_id = int(track_labels_layer.selected_label)
    if track_id == 0 or not np.any(track_labels_layer.data == track_id):
        show_warning(
            "Select an existing ID in track-labels-working with the picker "
            "before pressing A."
        )
        return
    _assign_track_id_to_segment(track_id)


@viewer.bind_key("R", overwrite=True)
def assign_new_track_id(_viewer) -> None:
    """Assign the selected nucleus a new track ID."""
    new_track_id = int(track_labels_layer.data.max()) + 1
    _assign_track_id_to_segment(new_track_id)


@viewer.bind_key("X", overwrite=True)
def clear_selected_tracking_assignment(_viewer) -> None:
    """Clear the track ID from the selected corrected nucleus."""
    selected = _selected_segmentation_mask()
    if selected is None:
        return
    frame, segment_id, segment_mask = selected
    track_labels_layer.data[frame][segment_mask] = 0
    _refresh_tracking_review(frame)
    show_info(
        f"Cleared the tracking assignment for segmentation label "
        f"{segment_id} in frame {frame}."
    )


print(
    "Tracking controls: select a nucleus in labels-working; press A to "
    "apply the selected existing track ID, R to create a new track ID, or "
    "X to clear its assignment. Magenta nuclei need tracking review."
)

tracks_path = Path(
     "external/runs/cls-frames0-19-ultrack-maxdist50/tracks.csv"
)
tracks = pd.read_csv(tracks_path)

# Reconstruct the mother–daughter relationships.
track_parents = tracks[
    ["track_id", "parent_track_id"]
].drop_duplicates()

graph = {
    int(row.track_id): [int(row.parent_track_id)]
    for row in track_parents.itertuples()
    if int(row.parent_track_id) != -1
}

tracks_layer = viewer.add_tracks(
    tracks[["track_id", "t", "y", "x"]].to_numpy(),
    graph=graph,
    name="ultrack-seed-tracks",
    tail_length=20,
    tail_width=2,
)

tracks_layer.display_id = True
tracks_layer.display_tail = True
tracks_layer.display_graph = True


def _write_mask_temps(
    data: np.ndarray,
    paths: list[Path],
) -> list[tuple[Path, Path]]:
    """Write temporary mask files without replacing saved annotations."""
    temporary_files = []
    for frame_data, destination in zip(data, paths):
        temporary = destination.with_name(
            f".{destination.stem}.tmp{destination.suffix}"
        )
        tifffile.imwrite(temporary, frame_data)
        temporary_files.append((temporary, destination))
    return temporary_files


def _save_annotations() -> None:
    """Atomically save the editable segmentation and tracking masks."""
    if labels_layer.data.shape != expected_shape:
        raise ValueError(
            f"Cannot save segmentation shape {labels_layer.data.shape}."
        )
    if track_labels_layer.data.shape != expected_shape:
        raise ValueError(
            f"Cannot save track-label shape {track_labels_layer.data.shape}."
        )

    temporary_files = []
    try:
        temporary_files.extend(
            _write_mask_temps(labels_layer.data, mask_paths)
        )
        temporary_files.extend(
            _write_mask_temps(track_labels_layer.data, track_mask_paths)
        )
        for temporary, destination in temporary_files:
            temporary.replace(destination)
    except Exception:
        for temporary, _ in temporary_files:
            temporary.unlink(missing_ok=True)
        raise

    current_step = tuple(int(step) for step in viewer.dims.current_step)
    checkpoint = {
        "saved_at_utc": datetime.now(UTC).isoformat(),
        "current_step": current_step,
        "segmentation_shape": list(labels_layer.data.shape),
        "segmentation_dtype": str(labels_layer.data.dtype),
        "segmentation_max_label": int(labels_layer.data.max()),
        "tracking_shape": list(track_labels_layer.data.shape),
        "tracking_dtype": str(track_labels_layer.data.dtype),
        "tracking_max_label": int(track_labels_layer.data.max()),
        "uncommitted_freehand_shapes": freehand_layer.nshapes,
        "lineage_note": (
            "Pixel masks were saved; res_track.txt was not changed."
        ),
    }
    temporary_checkpoint = checkpoint_path.with_suffix(".tmp")
    temporary_checkpoint.write_text(
        json.dumps(checkpoint, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_checkpoint.replace(checkpoint_path)

    message = (
        "Saved segmentation and tracking masks. "
        f"Uncommitted freehand shapes: {freehand_layer.nshapes}."
    )
    print(message)
    show_info(message)


@viewer.bind_key("Control-S", overwrite=True)
def save_annotations(_viewer) -> None:
    """Save an annotation checkpoint with the physical Control+S keys."""
    _save_annotations()


print(
    "Checkpoint controls: press the physical Control+S keys. "
    "The working masks are also saved when Napari closes."
)

napari.run()
_save_annotations()
