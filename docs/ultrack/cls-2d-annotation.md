# CLS 2D annotation and CTC evaluation runbook

This document is the operational handoff for creating, correcting, and
evaluating the CLS loose-colony reference subset. It records the selected
workflow rather than the earlier crop-selection and Cellpose experiments.

For environment installation, see the
[local macOS setup](ultrack-setup.md#local-macos-setup).

## Current reference status

The reference is **Cellpose/Ultrack-assisted**, not independently drawn ground
truth.

| Item | Current state |
| --- | --- |
| Corrected segmentation | 1,615 frame-level nucleus instances |
| Tracking coverage | 1,548/1,615 instances assigned (95.85%) |
| Unresolved tracking | 67 ambiguous instances have ID `0` |
| Tracking seed | Ultrack with `max_distance=50` |
| Comparison run | Fresh Ultrack run with `max_distance=40` |
| Division lineage | Not validated; provisional GT parent IDs are `0` |
| Evaluation | Provisional CTC metrics available; final evaluation pending mentor review |

Do not evaluate the `max_distance=50` seed as an independent result because it
initialized many reference identities. The `max_distance=40` run is the current
comparison result.

## Dataset and subset

| Item | Value |
| --- | --- |
| Source | `MAX_ch1_z3_10_Loose_colonies_H2B_T_17HRSto24HRS_20minintervals-2-2.tif` |
| Signal | H2B nuclear fluorescence |
| Structure | 2D maximum projection over time |
| Frame interval | 20 minutes |
| Selected frames | Data frames 0–19 |
| Excluded frame | Frame 20, because it may follow an unusual time gap |
| Crop | Top-left `(x=2048, y=320)`, width `1024`, height `1024` |
| Array slice | `movie[0:20, 320:1344, 2048:3072]` |
| Downsampling | None |

Expected local input:

```text
external/data/cropped_movies_frame0_19/runner_input/
  t000.tif
  ...
  t019.tif
```

All 20 files must be uint16 images shaped `1024 × 1024`.

## 1. Activate the environment

Run commands from the repository root:

```bash
conda activate ultrack-cell-tracking-local
export NUMBA_CACHE_DIR=/private/tmp/ultrack-numba-cache
```

The cache override avoids write errors from Numba in a read-only environment.
Verify that Cellpose, Napari, Ultrack, and Gurobi work before continuing.

## 2. Create the fixed crop

Use `scripts/annotation/crop_2d_movie.py`; Fiji is not required. Before running
it, verify the hard-coded `SOURCE_MOVIE` and `OUTPUT_DIR` at the top of the
script. `OUTPUT_DIR` must be:

```text
external/data/cropped_movies_frame0_19/runner_input
```

Run:

```bash
python scripts/annotation/crop_2d_movie.py
```

The script refuses to overwrite existing TIFFs. After it finishes, verify that
the directory contains `t000.tif` through `t019.tif` and no additional frames.

## 3. Generate the automated annotation seed

The selected Cellpose configuration is:

| Parameter | Value |
| --- | --- |
| Model | `nuclei` |
| Cell-probability threshold | `-0.5` |
| Flow threshold | `0.4` |
| Diameter | Automatic (`None`) |
| Channels | Grayscale `[0, 0]` |
| GPU | Disabled in the verified local environment |

Generate Cellpose masks and the `max_distance=50` Ultrack tracking seed:

```bash
python scripts/ultrack/run_2d_benchmark.py \
  --input-dir external/data/cropped_movies_frame0_19/runner_input \
  --output-dir external/runs/cls-frames0-19-ultrack-maxdist50 \
  --sequence CLS \
  --method cellpose \
  --frame-start 0 \
  --frame-stop 20 \
  --max-distance 50 \
  --contour-sigma 4 \
  --segmentation-workers 4 \
  --linking-workers 1 \
  --solver-threads 4 \
  --solver GUROBI \
  --cellpose-model nuclei \
  --cellpose-flow-threshold 0.4 \
  --cellpose-cellprob-threshold -0.5
```

Preserve this automated run unchanged. For a new annotation only, initialize
separate working directories from its outputs:

```bash
mkdir -p external/annotations/cls-loose-colony
cp -R \
  external/runs/cls-frames0-19-ultrack-maxdist50/input_labels \
  external/annotations/cls-loose-colony/labels-working
cp -R \
  external/runs/cls-frames0-19-ultrack-maxdist50/CLS_RES \
  external/annotations/cls-loose-colony/tracking-working

python scripts/annotation/initialize_tracking_draft.py
```

Do not repeat these copy commands after manual correction; they would replace
the working annotation. The initializer creates
`tracking-draft-mutual-best/` and refuses to reuse a nonempty output directory.
It transfers a seed ID only when the corrected segment and seed track are
mutual-best overlaps with IoU at least `0.5` and dominance at least `0.8`.

## 4. Correct the annotation in Napari

Open the viewer:

```bash
python scripts/annotation/open_annotation_napari.py
```

### Layer meanings

| Layer | Purpose |
| --- | --- |
| `raw-images` | Image evidence used to make annotation decisions |
| `labels-working` | Corrected nucleus boundary for each frame |
| `track-labels-working` | Track ID assigned to each corrected nucleus |
| `tracking-needs-review` | Magenta outline around a nucleus with no track ID |
| `ultrack-seed-tracks` | Original Ultrack suggestion; it does not update during editing |
| `freehand-annotations` | Temporary freehand shapes before they are committed |

Segmentation label colors do not represent identity across frames. Identity is
stored only in `track-labels-working`.

### Shortcuts

| Key | Action |
| --- | --- |
| `N` | Commit each freehand shape as a new segmentation object |
| `E` | Extend the selected existing segmentation object |
| `A` | Assign the selected existing track ID to the selected segmentation object |
| `R` | Assign the selected segmentation object a new track ID |
| `X` | Clear the selected object's tracking assignment |
| Physical `Control+S` | Save segmentation masks, tracking masks, and checkpoint metadata |

Freehand shapes are temporary. Commit them before saving or closing Napari.

### Segmentation pass

Review every frame before correcting identities.

- Add a missed nucleus only when it is visible and defensible in that frame.
- Use one segmentation label per visible nucleus per frame.
- Correct boundaries using the raw image and adjacent frames as evidence.
- Split touching nuclei only when a visible boundary or temporal evidence
  supports the split.
- Exclude debris that cannot be followed as a nucleus.
- Leave uncertain maximum-projection overlaps unresolved for mentor review.
- Do not infer a boundary for a faint object from a single uncertain frame.

For an already tracked nucleus whose segmentation must change:

1. Pick its ID in `track-labels-working`.
2. Pick the nucleus in `labels-working` and press `X`.
3. Correct the segmentation.
4. Pick the corrected nucleus and press `A` to restore the track ID using the
   corrected boundary.

### Tracking pass

Resolve magenta objects frame by frame.

- At frame 0, pick an unassigned nucleus in `labels-working` and press `R`.
- For a continuation, pick the correct ID in the preceding frame, advance one
  frame, pick the corresponding segmentation object, and press `A`.
- Use `R` only for a genuine new appearance or new daughter identity.
- Use `X` to clear an incorrect assignment before replacing it.
- Treat entry or exit at the crop boundary as an appearance or disappearance.

At a confirmed division, the mother ends before the split and both daughters
receive new IDs. Parent-child lineage must be recorded separately; the current
viewer does not edit `man_track.txt`.

Press `Control+S` regularly. A successful save updates:

```text
external/annotations/cls-loose-colony/labels-working/
external/annotations/cls-loose-colony/tracking-draft-mutual-best/
external/annotations/cls-loose-colony/annotation_checkpoint.json
```

## 5. Run the comparison workflow

The current comparison changes only Ultrack `max_distance` from the annotation
seed value of `50` to `40`:

```bash
python scripts/ultrack/run_2d_benchmark.py \
  --input-dir external/data/cropped_movies_frame0_19/runner_input \
  --output-dir external/runs/cls-frames0-19-ultrack-maxdist40-preliminary \
  --sequence CLS \
  --method cellpose \
  --frame-start 0 \
  --frame-stop 20 \
  --max-distance 40 \
  --contour-sigma 4 \
  --segmentation-workers 4 \
  --linking-workers 1 \
  --solver-threads 4 \
  --solver GUROBI \
  --cellpose-model nuclei \
  --cellpose-flow-threshold 0.4 \
  --cellpose-cellprob-threshold -0.5
```

The recorded run produced 1,490 tracked detections, 207 tracks, and 44 proposed
lineage entries. Its complete configuration and runtimes are in
`external/runs/cls-frames0-19-ultrack-maxdist40-preliminary/run_report.json`.

## 6. Export and evaluate in CTC format

Install the pinned evaluator once:

```bash
python -m pip install py-ctcmetrics==1.3.3
```

Export the working reference and comparison result:

```bash
python scripts/annotation/export_provisional_ctc.py \
  --segmentation-dir external/annotations/cls-loose-colony/labels-working \
  --tracking-dir external/annotations/cls-loose-colony/tracking-draft-mutual-best \
  --result-dir external/runs/cls-frames0-19-ultrack-maxdist40-preliminary/CLS_RES \
  --output-root external/ctc/cls-loose-colony-provisional-maxdist40 \
  --sequence 01 \
  --frames 20
```

The exporter creates:

```text
external/ctc/cls-loose-colony-provisional-maxdist40/
  01_GT/
    SEG/man_seg000.tif ... man_seg019.tif
    TRA/man_track000.tif ... man_track019.tif
    TRA/man_track.txt
  01_RES/
    mask000.tif ... mask019.tif
    res_track.txt
  provisional_ctc_export.json
```

It splits temporally disconnected reference IDs into valid CTC spans and
records every change in `provisional_ctc_export.json`. It does not invent
division parents: unresolved parent IDs remain `0`.

Run CTC evaluation:

```bash
python scripts/ultrack/evaluate_ctc_result.py \
  --ground-truth-dir external/ctc/cls-loose-colony-provisional-maxdist40/01_GT \
  --result-dir external/ctc/cls-loose-colony-provisional-maxdist40/01_RES \
  --output-dir external/ctc/cls-loose-colony-provisional-maxdist40/evaluation \
  --dataset CLS-loose-colony-frames0-19-provisional \
  --method cellpose-ultrack-maxdist40 \
  --num-workers 1
```

The exported result passed CTC format validation. Current provisional scores:

| CTC metric | Score |
| --- | ---: |
| DET | 0.950129 |
| SEG | 0.910834 |
| TRA | 0.943702 |
| OP_CTB | 0.927268 |

These are not final scores. The 67 unassigned tracking instances are absent
from `TRA`, and all reference parent IDs are `0`. Either limitation can move
the final metrics up or down. The assisted reference may also share errors with
the automated workflow.

`scripts/ultrack/evaluate_reviewed_subset.py` provides optional diagnostics
that explicitly ignore unassigned objects. Its precision, recall, IoU, and
identity outputs are **not CTC metrics** and should not replace the table above.

## 7. Outputs to preserve

Keep these ignored local artifacts:

```text
external/data/cropped_movies_frame0_19/runner_input/        # fixed raw crop
external/runs/cls-frames0-19-ultrack-maxdist50/             # annotation seed
external/annotations/cls-loose-colony/labels-working/       # corrected SEG
external/annotations/cls-loose-colony/tracking-draft-mutual-best/ # corrected TRA
external/annotations/cls-loose-colony/annotation_checkpoint.json
external/runs/cls-frames0-19-ultrack-maxdist40-preliminary/  # comparison run
external/ctc/cls-loose-colony-provisional-maxdist40/        # CTC export and scores
```

Preserve the automated seed separately from all manual corrections. Do not
rerun initialization commands over a working annotation.

## 8. Completion checklist

Completed:

- fixed 20-frame crop;
- Cellpose `-0.5` segmentation initialization;
- manual correction of clear segmentation errors;
- Ultrack-assisted tracking initialization and partial correction;
- fresh `max_distance=40` comparison run; and
- provisional CTC export and evaluation.

Outstanding before final ground truth:

- review the 67 unassigned instances with the mentor;
- validate all division parent-child relationships;
- review track starts, ends, appearances, and disappearances;
- obtain a second-person review of divisions and a sample of masks;
- regenerate `01_GT` after corrections; and
- rerun CTC evaluation and replace the provisional scores.
