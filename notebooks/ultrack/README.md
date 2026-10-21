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

2. `02_hela_stardist_seq01_benchmark.ipynb`
   - Load either a five-frame check or the complete HeLa sequence 01.
   - Generate instance labels with the pretrained StarDist
     `2D_versatile_fluo` model.
   - Convert labels to Ultrack foreground and contour inputs.
   - Export the complete result in CTC format for benchmark evaluation.

3. `02_hela_stardist_seq02_benchmark.ipynb`
   - Apply the same StarDist-to-Ultrack workflow to HeLa sequence 02.
   - Inspect the eight frames with sparse gold segmentation.
   - Export and evaluate the complete 92-frame result.

4. `03_mda231_raw_to_tracks.ipynb`
   - Run an exploratory three-frame 3D subset directly from the raw images.
   - Inspect middle z-slices, sparse gold slices, and Ultrack result labels.
   - Treat this as an additional experiment, not as a reproduction of the
     published U-Net benchmark.

5. `03_mda231_seq01_benchmark.ipynb`
   - Document the authors' published 3D U-Net foreground-and-boundary workflow.
   - Validate the official repository, pretrained checkpoint, raw sequence,
     and resulting CTC output.
   - Keep public-training evaluation separate from the published hidden-test
     benchmark values.

Planned follow-up: an optional `Fluo-N2DH-GOWT1` run if time permits.

Once the interactive workflow is stable, reusable processing would be moved into a
script under `scripts/ultrack/`. 

Generated images, databases, Zarr arrays, model files, or other run outputs are not committed.

Before committing notebooks, clear bulky outputs and confirm that no private
credentials or identifying license information are present.
