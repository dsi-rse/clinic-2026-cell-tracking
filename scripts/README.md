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
