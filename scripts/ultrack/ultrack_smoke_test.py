"""Run a small Ultrack smoke test on consecutive segmentation masks."""

import argparse
from pathlib import Path

import numpy as np
import tifffile
from ultrack import MainConfig, Tracker


MIN_FRAMES = 5
MAX_FRAMES = 10


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run the Ultrack smoke test.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing the input segmentation mask TIFF files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory in which to save the smoke-test outputs.",
    )
    parser.add_argument(
        "--inspect-only",
        action="store_true",
        help="Inspect and export the input labels without running Ultrack.",
    )
    return parser.parse_args()


def load_labels(input_dir: Path) -> np.ndarray:
    """Load and validate up to ten consecutive segmentation masks."""
    label_paths = sorted(input_dir.glob("*.tif"))[:MAX_FRAMES]

    if len(label_paths) < MIN_FRAMES:
        raise ValueError(
            f"Expected at least {MIN_FRAMES} label files in {input_dir}, "
            f"but found {len(label_paths)}."
        )

    print(f"Loaded {len(label_paths)} frames")
    print("Selected label files:")
    for path in label_paths:
        print(f"  {path.name}")

    labels = tifffile.imread(label_paths)

    if labels.ndim != 3:
        raise ValueError(
            f"Expected labels shaped (time, y, x), but got {labels.shape}."
        )

    print(f"Label array shape: {labels.shape}")
    print(f"Label data type: {labels.dtype}")

    for time, frame in enumerate(labels):
        print(
            f"Frame {time}: minimum={frame.min()}, "
            f"maximum={frame.max()}"
        )

    return labels


def main() -> None:
    """Inspect input labels and optionally run the Ultrack smoke test."""
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    labels = load_labels(args.input_dir)
    preview_path = args.output_dir / "input-labels-preview.tif"
    tifffile.imwrite(preview_path, labels)
    print(f"Saved input preview to {preview_path}")

    if args.inspect_only:
        print("Inspection complete; Ultrack was not run.")
        return

    config = MainConfig()
    config.data_config.working_dir = args.output_dir

    tracker = Tracker(config=config)
    tracker.track(labels=labels)

    tracks, _ = tracker.to_tracks_layer()
    tracks.to_csv(args.output_dir / "tracks.csv", index=False)
    tracker.to_zarr(args.output_dir / "segments.zarr")

    print(f"Tracks: {len(tracks)}")
    print(f"Output directory: {args.output_dir}")


if __name__ == "__main__":
    main()
