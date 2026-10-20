# Ultrack notebooks

This directory contains interactive analysis specific to Ultrack. General
dataset inspection remains in `notebooks/verify_ctc_dataset_structure.ipynb`
because it also applies to the other tracking methods in the project.

## Workflow

1. `01_hela_raw_to_tracks.ipynb`
   - Load a small HeLa subset from raw `t*.tif` images.
   - Create foreground and contour maps from the raw intensities.
   - Compare the maps visually with sparse gold segmentation.
   - Run Ultrack segmentation, linking, and solving in separate cells.

Planned follow-up notebooks:

2. A documented `Fluo-C3DL-MDA231` subset run after the 2D workflow works.
3. An optional `Fluo-N2DH-GOWT1` run if time permits.

Once the interactive workflow is stable, reusable processing would be moved into a
script under `scripts/ultrack/`. 

Generated images, databases, Zarr arrays, model files, or other run outputs are not committed.

Before committing notebooks, clear bulky outputs and confirm that no private
credentials or identifying license information are present.
