"""Open a cls_2d_pipeline.py run folder in napari for correction."""
import sys
from pathlib import Path

import napari
import pandas as pd
import tifffile

run = Path(sys.argv[1])
viewer = napari.Viewer()
viewer.add_image(tifffile.imread(run / "images.tif"), name="images")
labels_file = run / "corrected_labels.tif"
if not labels_file.exists():  # first time: start from the Ultrack result
    labels_file = run / "tracked_labels.tif"
viewer.add_labels(tifffile.imread(labels_file), name="labels", opacity=0.5)
if (run / "tracks.csv").exists():
    viewer.add_tracks(pd.read_csv(run / "tracks.csv")[["track_id", "t", "y", "x"]], name="tracks", visible=False)
napari.run()