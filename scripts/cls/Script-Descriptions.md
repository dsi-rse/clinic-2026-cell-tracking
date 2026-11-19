# CLS scripts: first-pass tracking, manual ground truth and scoring

These scripts do four things:

1. make a first-pass segmentation and tracking with Cellpose + Ultrack;
2. open that result in napari, where it is corrected by hand into ground truth;
3. convert the ground truth and the uncorrected results to CTC format, so they 
    can be scored with the same metrics we used for KIT-GE (3);
4. measure cell motions to explain why a tracker does well or badly on this data.


## Workflow

```
CLS movie (.tif file)
   │  cls_2d_pipeline.py          crop, downsample, Cellpose, Ultrack
   ▼
run folder: images.tif, cellpose_labels.tif, tracked_labels.tif, tracks.csv
   │  open_in_napari.py           correct by hand, save corrected_labels.tif
   ▼
corrected_labels.tif
   │  labels_to_ctc.py gt / res   CTC folders for ground truth and results
   ▼
ctc_evaluate                       SEG, DET, TRA, LNK, ...
   +
cell_motion_stats.py               how far cells move between frames
```

## Scripts

### `cls_2d_pipeline.py`: first pass (Cellpose + Ultrack)

**What it does**

1. Loads the movie.
2. Selects the channel and frames.
3. Crops and downsamples.
4. Segments every frame with Cellpose.
5. Tracks with Ultrack.
6. Saves everything in a run folder.

Example (the settings used for `movie2_crop3`):

```bash
python scripts/cls/cls_2d_pipeline.py <movie.tif> ~/cls_runs/movie2_crop3 \
    --crop 2800:4084,2600:4084 --downsample 2 --frames 0:20 \
    --min_area 50 --max_distance 35 --gpu
```

Main options:

| Option | Meaning |
| --- | --- |
| `--channel` | channel to use, if the movie has several |
| `--frames a:b` | frames to process (b exclusive) |
| `--crop y0:y1,x0:x1` | crop in **original** pixels; rows first, then columns |
| `--downsample n` | block-average by n (the movies are about 5300 × 5700 px; 2 keeps nuclei about 33 px wide) |
| `--model`, `--diameter`, `--gpu` | Cellpose model (default `cyto3`), cell diameter (estimated if not given), use the GPU|
| `--labels` | reuse an existing `cellpose_labels.tif` and only rerun Ultrack (much faster when testing Ultrack settings) |
| `--min_area`, `--max_area` | smallest and largest candidate segments Ultrack keeps (pixels) |
| `--max_distance` | how far (pixels) a cell may move between frames and still be linked |
| `--napari` | open the result in napari when done |

Run `python scripts/cls/cls_2d_pipeline.py --help` for the full list.

Outputs in the run folder:

| File | Content |
| --- | --- |
| `images.tif` | the cropped, downsampled movie |
| `cellpose_labels.tif` | Cellpose masks, frame by frame (no tracking) |
| `tracked_labels.tif` | Ultrack's labels |
| `tracks.csv` | one row per cell per frame (`track_id`, `t`, `y`, `x`, `parent_track_id`) |
| `ctc/01_RES/` | Ultrack's result in CTC format |
| `settings.json` | the settings used, for the record |

Things to know:

- Cellpose's `cellprob_threshold` and `flow_threshold` are left at their defaults, and so
  are Ultrack's link `power` and appear/disappear/division weights.

### `open_in_napari.py`: view and correct a run

**What it does:** opens a run folder in napari with:

- `images.tif`;
- the labels as a layer called `labels`: `corrected_labels.tif` if it exists,
  otherwise `tracked_labels.tif`;
- the tracks from `tracks.csv`.

```bash
python scripts/cls/open_in_napari.py ~/cls_runs/movie2_crop3
```

Correcting:

- Use the Labels-layer tools: picker, paint, eraser and fill.
- Save with **File → Save Selected Layers** as `corrected_labels.tif` in the run folder.

Annotation rules:

- Each cell keeps one ID in all frames.
- At a division, the parent's ID ends, and both daughters get new IDs (the CTC
  convention).


### `labels_to_ctc.py`: convert to CTC format

**What it does:** writes a T × Y × X label movie in CTC format. It has two modes:

- **`gt`:** writes the ground truth from `corrected_labels.tif`.
  - Output: `01_GT/TRA/man_trackTTT.tif` + `man_track.txt`, and
    `01_GT/SEG/man_segTTT.tif`.
  - Parents come from `divisions.csv`.
- **`res`:** writes a result to score.
  - Output: `01_RES/maskTTT.tif` + `res_track.txt`.
  - Parents come from Ultrack's `tracks.csv`.


Scoring frames 0–9:

```bash
RUN=~/cls_runs/movie2_crop3
python scripts/cls/labels_to_ctc.py gt  $RUN/corrected_labels.tif $RUN/ctc_eval --frames 0:10 \
    --divisions $RUN/divisions.csv
python scripts/cls/labels_to_ctc.py res $RUN/tracked_labels.tif   $RUN/ctc_eval --frames 0:10 \
    --tracks_csv $RUN/tracks.csv
python scripts/cls/labels_to_ctc.py res $RUN/cellpose_labels.tif  $RUN/ctc_eval_cellpose --frames 0:10 \
    --single_frame
cp -r $RUN/ctc_eval/01_GT $RUN/ctc_eval_cellpose/

ctc_validate --res $RUN/ctc_eval/01_RES
ctc_evaluate --gt $RUN/ctc_eval/01_GT --res $RUN/ctc_eval/01_RES
ctc_evaluate --gt $RUN/ctc_eval_cellpose/01_GT --res $RUN/ctc_eval_cellpose/01_RES --seg --det
```

Only SEG and DET mean anything for Cellpose alone, because it does no tracking.

### `cell_motion_stats.py`: how much do cells move?

**What it does:** for every cell present in frames t and t+1 (same ID), it computes:

- the displacement of its centre;
- its equivalent diameter;
- the IoU (intersection over union) of its masks in the two frames.

It writes a per-cell table (`<labels>_motion.csv`) and prints a summary:

- the median diameter;
- the median, 90th-percentile and maximum displacement;
- the displacement divided by the diameter;
- the median IoU, and how many moves have IoU = 0 and IoU < 0.2;
- how many moves exceed `--max_distance`.


These numbers explain dropped cells and broken tracks, and they guide settings such as
`max_distance` and `power`. Run it on the corrected labels so the IDs are right:

```bash
python scripts/cls/cell_motion_stats.py ~/cls_runs/movie2_crop3/corrected_labels.tif \
    --frames 0:10 --max_distance 35
```

## Setup notes (macOS)

Install the packages in a conda environment. Two problems came up during setup:

- **napari 0.10 needs Qt 6**, which failed to import. Install `pip install "napari<0.10"`.
- **OpenMP error #15 or a segfault** (two copies of `libomp`) came from a pip-installed
  PyTorch. Fix it with `pip uninstall torch` then
  `conda install -c conda-forge pytorch`. Don't use `KMP_DUPLICATE_LIB_OK`; it led to a
  segfault.

Ultrack uses the free CBC solver here, so no Gurobi license is needed.