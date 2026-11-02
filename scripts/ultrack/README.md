# Cellpose 3D segmentation and Ultrack tracking

`run_3d_cellpose.py` adapts Liya's Cellpose 2D/3D tutorial to a directory of
single-channel CTC `tNNN.tif` volumes.

Each TIFF must be ZYX, with one time point per file. It does not transpose or squeeze ambiguous inputs.

This guide follows the complete workflow in order:

1. Generate segmentation masks with `run_3d_cellpose.py`.
2. Track those masks with `track_3d_labels.py`.
3. Evaluate the exported results with `evaluate_ctc_result.py`.

The three-frame pilot tests these steps on a subset. A full experiment needs
Cellpose masks for every raw frame before running full-sequence tracking.
Throughout this guide, `CTC_ROOT` means the directory directly containing the
dataset folders (for example, `external/data` locally, or the cluster's `ctc`
directory). `RUN_ROOT` is the output root. Run commands from the repository root.

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

### MDA231 starting settings

The [CTC 3D dataset page](https://celltrackingchallenge.net/3d-datasets/)
lists the following acquisition settings for `Fluo-C3DL-MDA231`
(metadata supplied from the website):

| Setting | Value |
| --- | --- |
| Microscope | Olympus FluoView F1000 |
| Objective | Plan 20x/0.7 |
| Voxel size (X × Y × Z) | 1.242 × 1.242 × 6.0 µm |
| Time step | 80 minutes |

Cellpose anisotropy describes voxel spacing, not cell shape:
`6.0 / 1.242 ≈ 4.83`. Use `--anisotropy 4.83` for this dataset.

**Parameter Settings**

- We use `--diameter 15` as a provisional pilot value: 15 XY pixels correspond to
18.63 µm at this resolution. This is based on the approximate cell-size range
discussed during setup, not a measurement of cells in this sequence. 
- We would measure several representative cells in raw XY slices and adjust it before a full run.
Convert physical diameter to pixels with `diameter_um / 1.242`.
- The local `01/t000.tif` has 30 planes of 512 × 512 pixels, one channel, and 16-bit intensities. Its inspected TIFF tags provide XY resolution but no Z spacing; the Z spacing above comes from the supplied CTC metadata.


### Running the Pilot Experiment
- Set `CTC_ROOT` and `RUN_ROOT` to your external data and output locations.
- Run on a GPU allocation on the cluster:  Request a CUDA GPU allocation before using
`--gpu`; batch size starts at 1 to reduce memory pressure, but large volumes
can still exceed GPU memory.

```bash
python scripts/ultrack/run_3d_cellpose.py \
  --dataset Fluo-C3DL-MDA231 \
  --input-dir "$CTC_ROOT/Fluo-C3DL-MDA231/01" \
  --output-dir "$RUN_ROOT/mda231-cellpose3d-pilot" \
  --diameter 15 --anisotropy 4.83 \
  --frame-start 0 --frame-stop 3 --gpu
```

Repeat for `Fluo-C3DH-H157`, changing dataset, paths, diameter, and spacing ratio.
**Note**: H157 settings are still to be determined from its own metadata and images; Do not reuse the MDA231 values without checking.

Use a fresh output directory for each configuration. Omit the frame limits only
after inspecting pilot results. 

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

- Outputs are independent segmentation masks, central XY/XZ PNG previews, and
`run.json` with configuration, versions, GPU, per-frame counts/timing, and errors.

- Preview XZ axes are voxel indices, not physically scaled distances. Label colors
are for inspection only and do not establish identities across time.

For each dataset:

- Compare the same frames and noisy regions against the U-Net
baseline where available. Central previews are an initial check; inspect other
slices and annotated regions too. 
- Look for missed cells, background false positives, merged/split objects, and continuity through Z.
- Use the same raw-image contrast and annotations for both methods. Counts alone do not establish an
improvement. 
- **Note to self (TBR)**: Agree on the sparse-slice segmentation evaluation with Erick before reporting SEG; these masks are not ready for the existing full tracking evaluator.
- Record dataset/sequence/frames, measured spacing and diameter, model/checkpoint, settings, visual observations, comparable segmentation scores, runtime, and blockers. 

References: [Cellpose API](https://cellpose.readthedocs.io/en/latest/api.html)
and [3D guidance](https://cellpose.readthedocs.io/en/latest/do3d.html).

## Track saved 3D segmentation masks

`track_3d_labels.py` runs Ultrack on saved `maskNNN.tif` volumes. It does not
load Cellpose or rerun its neural network. Reusable loading and tracking helpers
live in `src/cell_tracking/ultrack_labels.py`; the loader reuses the existing
CTC filename parser and dimension-independent label validator.

Activate the existing Ultrack environment, rather than adding Ultrack to the
Cellpose 4 environment, and install the project from the repository root:

```bash
micromamba activate cell-tracking-ultrack
python -m pip install -e . --no-deps
```

### Configuration and pilot

- Obtain the `config.toml` used by the official MDA231 baseline from the authors'
CTC submission checkout on the cluster. 
- The downloaded local run does not contain that file. Set `ULTRACK_CONFIG` to its full path; do not substitute the defaults used by the 2D experiments.
- Preserve the baseline's solver, segmentation size limits, linking settings, and worker counts initially. Its solver may require a working license in your allocation.

Set `CTC_ROOT` to the directory containing the dataset folders and `RUN_ROOT`
to your output root. First test tracking on the three existing pilot masks:

```bash
python scripts/ultrack/track_3d_labels.py \
  --dataset Fluo-C3DL-MDA231 --sequence 01 \
  --input-dir "$CTC_ROOT/Fluo-C3DL-MDA231/01" \
  --label-dir "$RUN_ROOT/mda231-cellpose3d-pilot" \
  --output-dir "$RUN_ROOT/mda231-cellpose3d-tracking-pilot" \
  --config "$ULTRACK_CONFIG" \
  --scale 4.83 1 1 --contour-sigma 0 0 0 --frame-stop 3
```

`--scale` is Z/Y/X scaling for linking distances, not Cellpose inference.
The example expresses distances in XY-pixel units: Z is 4.83 times XY.
Confirm how the baseline supplied linking scale before claiming identical
tracking settings. If it used physical µm, use `6 1.242 1.242` instead, with
distance thresholds in matching units. The runner does not infer scale from
the TOML or image metadata. H157 needs its own scale and configuration.

`--contour-sigma` is smoothing in Z/Y/X voxels. Zero is an explicit starting
point that preserves sharp mask boundaries; record and compare any later
changes. Ultrack generates segmentation hypotheses from the masks, so its
final objects may differ from the original Cellpose labels.

### Full experiment

1. Run `scripts/ultrack/run_3d_cellpose.py` on the complete sequence in a **new** output
   directory, without `--frame-stop`. This step needs the GPU allocation.
2. Run the tracking command above with that full label directory, a new tracking
   output directory, and **without** `--frame-stop`. Ultrack runs on CPU and may
   need substantial RAM/disk; follow the baseline's cluster resource allocation.
3. Inspect the exported tracks and masks, then evaluate the full result.

Missing masks cause an error rather than silently shortening the experiment.
Frames must start at zero and be consecutive. Completeness is relative to the
raw directory supplied: point at the full downloaded sequence, not a copied
pilot-only raw folder. A pilot exports `subset_RES`; a full sequence exports
`01_RES` or `02_RES`. All output directories must be new or empty.

The runner stores disk-backed `labels.npy`, foreground and contour Zarr maps,
the Ultrack database, `tracks.csv`, `segments.zarr`, CTC masks and lineage,
source/effective configurations, and `run_report.json` with status/errors,
runtime, versions, and the source Cellpose run record when available. Disk-backed
inputs reduce loading pressure but do not bound Ultrack's own peak memory use.

### Evaluation

Reuse the existing evaluator in its separate evaluation environment:

```bash
micromamba activate cell-tracking-ctc-evaluation
python scripts/ultrack/evaluate_ctc_result.py \
  --ground-truth-dir "$CTC_ROOT/Fluo-C3DL-MDA231/01_GT" \
  --result-dir "$RUN_ROOT/mda231-cellpose3d-tracking-full/01_RES" \
  --dataset Fluo-C3DL-MDA231 --method cellpose3d-ultrack
```

Compare against the official U-Net run on the same public sequence using the
same evaluator, version, and available annotations. Inspect sparse-slice 3D
annotation handling with Erick before interpreting SEG. This evaluates the
**Cellpose + Ultrack pipeline**, not the untouched Cellpose masks. No new
evaluation implementation or automatic tuning on ground truth is introduced.

API references: [Ultrack](https://royerlab.github.io/ultrack/api.html).
