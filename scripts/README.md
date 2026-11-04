# Scripts

Add reproducible scripts here for:

- downloading and verifying public CTC training data;
- converting image formats and axis orders;
- launching method-specific jobs;
- converting outputs to CTC format;
- running official metrics; and
- generating final comparison tables and figures.

Scripts should accept paths and parameters as arguments or configuration values. Do not hard-code a student's personal directory.

## Ultrack CTC evaluation

[`ultrack/evaluate_ctc_result.py`](ultrack/evaluate_ctc_result.py) validates and
evaluates one complete sequence in Cell Tracking Challenge format. It reports
DET, SEG, TRA, and OP_CTB, then saves the full results as JSON and CSV. The
script checks that result frames align with the complete tracking ground truth,
so a five-frame `subset_RES` directory cannot be mistaken for a benchmark run.

Create and activate the small evaluation environment. Keeping evaluation
separate avoids changing packages in a working tracking environment:

```bash
micromamba create --file environments/ctc-evaluation.yaml
micromamba activate cell-tracking-ctc-evaluation
```

For the full StarDist-to-Ultrack run on sequence 01 of `Fluo-N2DL-HeLa`, run:

```bash
python scripts/ultrack/evaluate_ctc_result.py \
    --ground-truth-dir <CTC_ROOT>/ctc/Fluo-N2DL-HeLa/01_GT \
    --result-dir <ULTRACK_RUN_ROOT>/hela-seq01-full-stardist/01_RES \
    --dataset Fluo-N2DL-HeLa \
    --method ultrack-stardist-2D_versatile_fluo \
    --published-seg 0.724 \
    --published-tra 0.910 \
    --published-ctb 0.817 \
    --num-workers 4
```

By default, the script writes `ctc_metrics.json` and `ctc_metrics.csv` beneath
`<result parent>/evaluation/01_RES`. Use `--output-dir` to select a different
location. Large result masks and private cluster paths remain outside Git; only
sanitized summary tables should be committed.

## Reusable 2D Ultrack benchmark

[`ultrack/run_2d_benchmark.py`](ultrack/run_2d_benchmark.py) applies one of
three segmentation methods to a 2D CTC sequence, converts the instance labels
to the same Ultrack foreground/contour representation, runs the common Ultrack
pipeline, and exports a CTC result. Supported methods are `stardist`,
`watershed`, and `cellpose`.

The headline StarDist results used the combined Ultrack-StarDist environment.
Create it from the committed recipe, activate it, and install this project
before running the StarDist workflow:

```bash
micromamba create --file environments/ultrack-stardist.yaml
micromamba activate cell-tracking-ultrack-stardist
python -m pip install -e .
```

This recipe pins the Ultrack, StarDist, and TensorFlow versions recorded in the
completed HeLa runs. Set `KERAS_HOME` as described in
[Ultrack reproducibility](../docs/ultrack/ultrack-reproducibility.md#shared-cluster-conventions)
before the first run so the pretrained StarDist model is stored in the shared
model cache.

Always start with a five-frame labels-only check. For watershed:

```bash
python scripts/ultrack/run_2d_benchmark.py \
    --input-dir <CTC_ROOT>/ctc/Fluo-N2DL-HeLa/01 \
    --output-dir <ULTRACK_RUN_ROOT>/hela-seq01-t012-016-watershed-check \
    --sequence 01 \
    --method watershed \
    --frame-start 12 \
    --frame-stop 17 \
    --labels-only
```

Inspect the saved `input_labels` before running the complete workflow. The
watershed defaults are explicit starting values, not parameters reported by
the paper. Adjust them on the small check and record any changed values.

Cellpose must remain on version 3 to use the paper's pretrained `cyto2` model;
Cellpose 4 uses a different model family. Create its separate environment:

```bash
micromamba create --file environments/ultrack-cellpose.yaml
micromamba activate cell-tracking-ultrack-cellpose
export PYTHONPATH="$PWD/src"
```

The environment pins NumPy 2.0.2 because Cellpose 3 requires NumPy below 2.1.
Do not run `python -m pip install -e .` in this environment: the main project
currently requires NumPy 2.2 or newer. `PYTHONPATH` makes the project source
available without changing the Cellpose-compatible NumPy version. The recipe
provides the reproducible `cyto2` software version but does not guarantee a
CUDA-enabled PyTorch build. Use `--cellpose-gpu` only after checking that
`torch.cuda.is_available()` returns `True`; otherwise leave the flag out.

Set the shared model cache before the first Cellpose import, then run the same
five-frame check:

```bash
export CELLPOSE_LOCAL_MODELS_PATH=<CTC_ROOT>/models/cellpose-cache

python scripts/ultrack/run_2d_benchmark.py \
    --input-dir <CTC_ROOT>/ctc/Fluo-N2DL-HeLa/01 \
    --output-dir <ULTRACK_RUN_ROOT>/hela-seq01-t012-016-cellpose-check \
    --sequence 01 \
    --method cellpose \
    --frame-start 12 \
    --frame-stop 17 \
    --cellpose-model-cache "$CELLPOSE_LOCAL_MODELS_PATH" \
    --labels-only
```

Remove `--frame-start`, `--frame-stop`, and `--labels-only` to run a complete
sequence after inspecting the subset. A complete run exports `01_RES` or
`02_RES`; a partial run exports `subset_RES` so it cannot be confused with a
benchmark result. Every run also writes `run_report.json` with package
versions, parameters, runtimes, and output counts.

## Reusable 2D Ultrack ensemble

[`ultrack/run_2d_ensemble.py`](ultrack/run_2d_ensemble.py) reuses the saved
`input_labels` from complete watershed, Cellpose, and StarDist runs. Following
the published Ultrack experiment, it combines the three binary foreground maps
with logical OR and averages the three contour maps. It then runs the common
Ultrack stages and exports a CTC result. The segmentation models are not run
again.

Run the ensemble in the base `cell-tracking-ultrack` environment. The script
defaults to one segmentation worker to limit peak memory on the larger GOWT1
images:

```bash
python scripts/ultrack/run_2d_ensemble.py \
    --input-dir <CTC_ROOT>/ctc/Fluo-N2DH-GOWT1/01 \
    --watershed-label-dir \
        <ULTRACK_RUN_ROOT>/gowt1-seq01-full-watershed/input_labels \
    --cellpose-label-dir \
        <ULTRACK_RUN_ROOT>/gowt1-seq01-full-cellpose/input_labels \
    --stardist-label-dir \
        <ULTRACK_RUN_ROOT>/gowt1-seq01-full-stardist/input_labels \
    --output-dir <ULTRACK_RUN_ROOT>/gowt1-seq01-full-ensemble \
    --sequence 01
```

All three label directories must contain the same requested frame numbers and
image shape. Use `--frame-start` and `--frame-stop` for a subset check. A full
run writes `01_RES` or `02_RES`, while a subset writes `subset_RES`. GOWT1
ensemble results are additional project experiments because the selected
Ultrack paper does not report a matching GOWT1 benchmark.

## CTC overlay movie

[`ultrack/render_ctc_overlay.py`](ultrack/render_ctc_overlay.py) creates a
two-panel animated GIF for qualitative review of a 2D CTC result. The left
panel overlays ground-truth boundaries in green and prediction boundaries in
magenta. The right panel shows overlapping foreground in green,
prediction-only pixels in red, and ground-truth-only pixels in cyan. It also
reports per-frame instance matches using a configurable intersection-over-union
threshold.

Use `TRA` masks for a continuous tracking movie. Ground-truth and prediction
track IDs can be added for a small crop with `--show-track-ids`. Use `SEG` for
segmentation-specific review, noting that CTC segmentation annotations may be
available for only a subset of frames. Add `--tracking-only` to omit the
segmentation-agreement panel and its instance-match counts when using `TRA`.

```bash
export CTC_ROOT=<PROJECT_DATA_ROOT>
export ULTRACK_RUN_ROOT=<PROJECT_DATA_ROOT>/runs/ultrack
export PYTHONPATH="$PWD/src"

python scripts/ultrack/render_ctc_overlay.py \
    --raw-dir "$CTC_ROOT/ctc/Fluo-N2DL-HeLa/01" \
    --ground-truth-dir "$CTC_ROOT/ctc/Fluo-N2DL-HeLa/01_GT" \
    --result-dir "$ULTRACK_RUN_ROOT/hela-seq01-full-ensemble/01_RES" \
    --ground-truth-source TRA \
    --output-path \
        "$ULTRACK_RUN_ROOT/hela-seq01-full-ensemble/visualizations/01_TRA_overlay.gif" \
    --fps 4 \
    --scale 0.5
```

For a segmentation-focused GIF, select the sparse `SEG` annotations and skip
frames that do not have a segmentation mask:

```bash
python scripts/ultrack/render_ctc_overlay.py \
    --raw-dir "$CTC_ROOT/ctc/Fluo-N2DL-HeLa/01" \
    --ground-truth-dir "$CTC_ROOT/ctc/Fluo-N2DL-HeLa/01_GT" \
    --result-dir "$ULTRACK_RUN_ROOT/hela-seq01-full-ensemble/01_RES" \
    --ground-truth-source SEG \
    --only-annotated \
    --output-path \
        "$ULTRACK_RUN_ROOT/hela-seq01-full-ensemble/visualizations/01_SEG_overlay.gif" \
    --fps 1 \
    --scale 0.5
```

For track IDs, first choose a crop containing a manageable number of cells:

```bash
python scripts/ultrack/render_ctc_overlay.py \
    --raw-dir "$CTC_ROOT/ctc/Fluo-N2DL-HeLa/01" \
    --ground-truth-dir "$CTC_ROOT/ctc/Fluo-N2DL-HeLa/01_GT" \
    --result-dir "$ULTRACK_RUN_ROOT/hela-seq01-full-ensemble/01_RES" \
    --ground-truth-source TRA \
    --output-path \
        "$ULTRACK_RUN_ROOT/hela-seq01-full-ensemble/visualizations/01_TRA_crop.gif" \
    --crop 100 500 200 700 \
    --tracking-only \
    --show-track-ids \
    --max-track-labels 30 \
    --fps 4 \
    --scale 1
```

If an MP4 is easier to use in the presentation, convert the GIF with FFmpeg:

```bash
ffmpeg -y \
    -i "$ULTRACK_RUN_ROOT/hela-seq01-full-ensemble/visualizations/01_TRA_overlay.gif" \
    -movflags +faststart \
    -pix_fmt yuv420p \
    "$ULTRACK_RUN_ROOT/hela-seq01-full-ensemble/visualizations/01_TRA_overlay.mp4"
```

## EmbedTrack pretrained inference

[`embedtrack/run_pretrained.py`](embedtrack/run_pretrained.py) runs a pretrained
EmbedTrack model on the sequences of one CTC dataset and writes CTC-format
results (`<seq>_RES`). `--model-dataset` selects the model trained on a different
dataset for cross-dataset tests; EmbedTrack only accepts a model path that
contains the dataset name, so the script creates a symlink for that case. It
checks that the raw data, ground truth and model exist before starting. Run it
from the `embedtrack` environment through the Slurm wrapper
[`../jobs/embedtrack_run_pretrained.sh`](../jobs/embedtrack_run_pretrained.sh), or
directly:

```bash
python scripts/embedtrack/run_pretrained.py \
    --dataset Fluo-N2DL-HeLa \
    --model-dataset Fluo-N2DH-GOWT1 \
    --sequences 01 02 \
    --raw-root <CTC_ROOT>/ctc \
    --models-root <EMBEDTRACK_MODELS_ROOT> \
    --results-root results
```

Omit `--model-dataset` to use the model trained on the same dataset.

## EmbedTrack visualization

These scripts need the project source on the path, so run them from the
repository root with `PYTHONPATH=src`. They share the helpers in
[`../src/cell_tracking/track_utils.py`](../src/cell_tracking/track_utils.py)
(track colours and centroids) and reuse the frame, boundary and image
normalisation helpers from `cell_tracking.ctc_io`, `cell_tracking.ultrack_2d` and
`cell_tracking.ctc_visualization`.

| Script | What it writes |
| --- | --- |
| [`embedtrack/visualize_tracks.py`](embedtrack/visualize_tracks.py) | Per-frame PNGs with outlines coloured by track id and short tails, a GIF, and one image of every full trajectory |
| [`embedtrack/overlay_movie.py`](embedtrack/overlay_movie.py) | A GIF of the raw movie with translucent masks and trajectories |
| [`embedtrack/compare_with_gt.py`](embedtrack/compare_with_gt.py) | A GIF with predictions in magenta and ground truth in green |

```bash
PYTHONPATH=src python scripts/embedtrack/overlay_movie.py \
    --raw <CTC_ROOT>/ctc/Fluo-N2DL-HeLa/02 \
    --res <EMBEDTRACK_RESULTS>/Fluo-N2DL-HeLa/KIT-Loe-GE/train/02_RES \
    --out <OUTPUT_DIR>
```

Use `--step N` to draw every Nth frame for a quick check. `compare_with_gt.py`
takes `--gt <seq>_GT/SEG` or `--gt <seq>_GT/TRA`, and `--only-gt-frames` keeps
only frames that have ground truth.

## KIT-GE (3)

Scripts for the KIT-GE (3) pipeline. The Slurm jobs in `jobs/` call them through
`$SCRIPTS_DIR` (set in `jobs/datasets.sh`).

- [`kit-ge-3/segment_only.py`](kit-ge-3/segment_only.py): Segments CTC sequences
  with a pretrained KIT-GE (3) model, using the same post-processing as the
  authors' `eval.py` but without its scoring step.
- [`kit-ge-3/seg_to_tracks.py`](kit-ge-3/seg_to_tracks.py): Writes one-frame
  tracks for segmentation masks, so py-ctcmetrics can compute DET.
- [`kit-ge-3/seg_3d_check.py`](kit-ge-3/seg_3d_check.py): Computes SEG for 3D
  datasets whose ground truth is given as 2D slices (`man_seg_T_Z.tif`), per
  slice as the CTC defines it.
  Usage: `python seg_3d_check.py <seq>_GT <result folder>`.
- [`kit-ge-3/summarize_scores.py`](kit-ge-3/summarize_scores.py): Per-sequence
  and mean SEG/DET/TRA with OP_CSB and OP_CTB from the evaluation CSVs.
- [`kit-ge-3/ctc_viz.py`](kit-ge-3/ctc_viz.py): Visualizes any CTC-format
  result (masks + `res_track.txt`):
  - `color`: color-coded masks, one Tab10 color per cell kept across frames;
  - `overlay`: semi-transparent masks over the raw images;
  - `movie`: tracking movie with trajectory lines (PNG frames, GIF, MP4).
  Example: `python ctc_viz.py movie <dataset>/tracking/02_RES <out> --raw_dir <data>/02 --tail 0 --no_markers`.