"""Shared helpers for Cell Tracking Challenge file names."""

import re
from pathlib import Path

FRAME_NUMBER_PATTERN = re.compile(r"(\d+)$")


def extract_frame_number(path: Path, expected_prefix: str | None = None) -> int:
    """Extract the trailing frame number from a CTC TIFF filename.

    Args:
        path: Path whose filename ends with a numeric frame identifier.
        expected_prefix: Optional filename prefix to validate, such as ``t``
            for a raw image or ``mask`` for a result mask.

    Returns:
        The numeric frame identifier.

    Raises:
        ValueError: If the filename does not have the expected CTC form.
    """
    if expected_prefix is not None:
        pattern = rf"{re.escape(expected_prefix)}(?P<frame>\d+)\.tif"
        match = re.fullmatch(pattern, path.name)
        if match is None:
            example = f"{expected_prefix}000.tif"
            raise ValueError(f"Expected a filename like {example}, got {path.name}.")
        return int(match.group("frame"))

    match = FRAME_NUMBER_PATTERN.search(path.stem)
    if match is None:
        raise ValueError(f"Could not read a frame number from {path.name}.")
    return int(match.group(1))
