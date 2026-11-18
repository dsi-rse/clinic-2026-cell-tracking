"""Crop selected frames and region from a TYX TIFF movie."""

from pathlib import Path

import tifffile


SOURCE_MOVIE = Path("external/data/cls_raw/MAX_ch1_z3_10_Loose_colonies_H2B_T_17HRSto24HRS_20minintervals-2-2.tif")
OUTPUT_DIR = Path(
    "external/data/cropped_movies_frame0_19_scripted/runner_input"
)

FRAME_START = 0
FRAME_STOP = 20  # Exclusive: includes frames 0 through 19

X = 2048
Y = 320
WIDTH = 1024
HEIGHT = 1024


def main() -> None:
    """Crop the movie and save one TIFF per frame."""
    movie = tifffile.imread(SOURCE_MOVIE)
    print(f"Original movie: shape={movie.shape}, dtype={movie.dtype}")

    if movie.ndim != 3:
        raise ValueError(
            f"Expected a movie shaped (T, Y, X), but found {movie.shape}."
        )

    if FRAME_STOP > movie.shape[0]:
        raise ValueError(
            f"Requested frames through {FRAME_STOP - 1}, "
            f"but the movie has only {movie.shape[0]} frames."
        )

    x_stop = X + WIDTH
    y_stop = Y + HEIGHT

    if y_stop > movie.shape[1] or x_stop > movie.shape[2]:
        raise ValueError(
            "The requested crop extends outside the original image."
        )

    cropped = movie[FRAME_START:FRAME_STOP, Y:y_stop, X:x_stop]

    expected_shape = (
        FRAME_STOP - FRAME_START,
        HEIGHT,
        WIDTH,
    )
    if cropped.shape != expected_shape:
        raise ValueError(
            f"Expected crop shape {expected_shape}, found {cropped.shape}."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    existing_outputs = list(OUTPUT_DIR.glob("t*.tif"))
    if existing_outputs:
        raise FileExistsError(
            f"{OUTPUT_DIR} already contains TIFF files. "
            "Use a new directory to avoid overwriting previous data."
        )

    for frame_number, image in enumerate(cropped, start=FRAME_START):
        output_path = OUTPUT_DIR / f"t{frame_number:03d}.tif"
        tifffile.imwrite(output_path, image)
        print(f"Saved {output_path}")

    print(f"Finished: {len(cropped)} frames with shape {cropped.shape[1:]}")


if __name__ == "__main__":
    main()