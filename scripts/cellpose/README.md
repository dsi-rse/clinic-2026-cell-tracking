# Cellpose 3D pilot

`run_3d.py` adapts Liya Ding's Cellpose 2D/3D tutorial to a directory of
single-channel CTC `tNNN.tif` volumes. Each TIFF must be ZYX, with one time point
per file. It does not transpose or squeeze ambiguous inputs.

## Separate cluster environment

From the repository root, create a separate environment with micromamba:

```bash
micromamba create -n cellpose4-3d -c conda-forge python=3.12 pip
micromamba activate cellpose4-3d
python -m pip install 'cellpose==4.2.1.1' matplotlib tifffile scipy scikit-image
python -m pip install -e . --no-deps
```

The mentor also installed DINOv3 from its official GitHub repository. Whether
this is needed depends on the selected model.

- We can start with the explicit `cpsam` model; record model-loading errors rather than silently switching models.
- First model use may download weights, so cluster network/cache access is a
possible blocker. 
- Record the downloaded checkpoint location and checksum inthe experiment notes. The script records model selection and package versions, but does not hash downloaded weights automatically.

## Pilot

The pilot here measures the approximate cell diameter in XY pixels and obtains the Z/XY voxel-spacing
ratio from the dataset metadata. 

Note that the tutorial used;
- dimaeter: 200,
- anisotropy: 4,
- minimum size: 20000

Do not copy the tutorial's parameters until the images are checked and validated.

Set these shell variables to your own measured values and external data paths:

```bash
python scripts/cellpose/run_3d.py \
  --dataset Fluo-C3DL-MDA231 \
  --input-dir "$CTC_ROOT/ctc/Fluo-C3DL-MDA231/01" \
  --output-dir "$RUN_ROOT/mda231-cellpose3d-pilot" \
  --diameter "$DIAMETER_XY" --anisotropy "$Z_TO_XY_RATIO" \
  --frame-start 0 --frame-stop 3 --gpu
```

Repeat for `Fluo-C3DH-H157`, changing dataset, paths, diameter, and spacing ratio.
Use a fresh output directory for each configuration. Omit the frame limits only
after inspecting pilot results. Request a CUDA GPU allocation before using
`--gpu`; batch size starts at 1 to reduce memory pressure, but large volumes
can still exceed GPU memory.

## What changed from the tutorial

- Removed Colab mounting, notebook installation commands, and hard-coded paths.
- Uses one fluorescence channel, without inventing a separate nucleus channel.
- Keeps true volumetric `do_3D=True`; no temporal tracking or 2D stitching.
- Starts with no smoothing and global volume normalization. Smoothing is an
  experiment: try `--sigma 0.5 1 1` in a separate run, then compare.
- Exposes cell probability threshold, minimum size, local normalization, diameter,
  and anisotropy. A cell probability threshold of zero is a threshold on model
  scores, not a zero probability or an automatic adaptive setting.
- Omits flow threshold because Cellpose does not use it in true 3D mode.

## Inspect and report

Outputs are independent segmentation masks, central XY/XZ PNG previews, and
`run.json` with configuration, versions, GPU, per-frame counts/timing, and errors.
Preview XZ axes are voxel indices, not physically scaled distances. Label colors
are for inspection only and do not establish identities across time.

For each dataset, compare the same frames and noisy regions against the U-Net
baseline where available. Central previews are an initial check; inspect other
slices and annotated regions too. Look for missed cells, background false
positives, merged/split objects, and continuity through Z. Use the same raw-image
contrast and annotations for both methods. Counts alone do not establish an
improvement. Agree on the sparse-slice segmentation evaluation with Erick before
reporting SEG; these masks are not ready for the existing full tracking evaluator.

Record dataset/sequence/frames, measured spacing and diameter, model/checkpoint,
settings, visual observations, comparable segmentation scores, runtime, and
blockers. No experimental improvement is established until these runs finish.

References: [Cellpose API](https://cellpose.readthedocs.io/en/latest/api.html)
and [3D guidance](https://cellpose.readthedocs.io/en/latest/do3d.html).
