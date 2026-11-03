# Running 2D segmentation parameter experiments

Run `scripts/ultrack/run_segmentation_parameters.py` from the repository root.
Each invocation uses the currently active environment. The script never switches
environments or installs packages. Install the project once in each environment
with `python -m pip install -e . --no-deps`.

## Create and review the experiment plan

```bash
python scripts/ultrack/run_segmentation_parameters.py plan \
  --ctc-root /net/spaces/clinic/CLS/DSC_CTC/ctc \
  --baseline-run-root /net/spaces/clinic/CLS/DSC_CTC/runs/ultrack \
  --plan config/experiments/parameter-plan.json
```

The plan includes HeLa and GOWT1, sequences 01 and 02:

- Contour sigma 4, 2, and 0 for Cellpose, StarDist, plain watershed, and ensemble.
- Image sigma 1, 0.5, and 0 for plain and hole-filled watershed.
- A fresh StarDist default-threshold baseline; probability thresholds 0.4/0.6
  and NMS thresholds 0.2/0.4, changing one threshold at a time.

Review the JSON before running. Baseline paths assume the existing naming
convention `hela-seq01-full-cellpose/input_labels`, etc.; adjust to the actual
saved input labels. The original ensemble explicitly uses plain watershed,
Cellpose, and StarDist. An ensemble with hole-filled watershed is a separate
experiment: give it a new id and point its watershed entry at the filled labels.

The plan also includes `holefilled-contour-4`, `holefilled-contour-2`, and
`holefilled-contour-0` for each dataset/sequence. Their `@experiment-id` label
references resolve to the generated labels of the corresponding
`holefilled-image-1` experiment under the output root. Generate that source
experiment first, or replace the reference with your existing filled-label path.

These are full-sequence experiments. Start with a small explicit selection of
ids; the runner requires `--ids` and does not run the whole plan automatically.
Output paths should remain outside Git. Define shared shell variables:

```bash
export PARAM_PLAN="$PWD/config/experiments/parameter-plan.json"
export PARAM_OUT=/net/spaces/clinic/CLS/DSC_CTC/runs/ultrack/parameter-analysis
```

## Generate new segmentation labels only when needed

In `cell-tracking-ultrack-stardist`, for example:

```bash
python scripts/ultrack/run_segmentation_parameters.py generate \
  --plan "$PARAM_PLAN" --output-root "$PARAM_OUT" --resume \
  --ids hela-01-stardist-baseline-None hela-01-stardist-prob_thresh-0p4 \
        hela-01-stardist-prob_thresh-0p6
```

The settings record stores the actual loaded model's probability and NMS
defaults and the thresholds used. Model, gamma normalization, block size 560,
and overlap 96 match the existing StarDist helper. A GPU allocation can help
StarDist, according to your existing TensorFlow setup.

For watershed in `cell-tracking-ultrack`:

```bash
python scripts/ultrack/run_segmentation_parameters.py generate \
  --plan "$PARAM_PLAN" --output-root "$PARAM_OUT" --resume \
  --ids hela-01-holefilled-image-1 hela-01-holefilled-image-0p5
```

There is no generation step for contour experiments that specify `label_dirs`:
they reuse the existing masks directly. Do not rerun expensive Cellpose inference.

## Track using the common Ultrack environment

Set `PARAM_CONFIG` to a TOML containing the same settings as the 2D baseline.
Use the same config for each controlled comparison. If the baseline used
`MainConfig()` plus worker/solver overrides, export those settings explicitly
in that environment (check the saved baseline report first):

```python
from ultrack import MainConfig
from ultrack.config import save_config

config = MainConfig()
config.data_config.n_workers = 1
config.segmentation_config.n_workers = 4
config.linking_config.n_workers = 1
config.tracking_config.n_threads = 4
config.tracking_config.solver_name = "GUROBI"
save_config(config, "config/experiments/2d-baseline.toml")
```

Confirm the installed `save_config` signature if your version differs. The
tracking runner saves its effective config and source-config SHA-256 for each
experiment. In `cell-tracking-ultrack`, run:

```bash
export PARAM_CONFIG="$PWD/config/experiments/2d-baseline.toml"
python scripts/ultrack/run_segmentation_parameters.py track \
  --plan "$PARAM_PLAN" --output-root "$PARAM_OUT" --config "$PARAM_CONFIG" \
  --resume --ids hela-01-cellpose-contour-4 hela-01-cellpose-contour-2 \
                hela-01-cellpose-contour-0
```

Use the same command with the ids of generated StarDist or watershed experiments
after generation finishes. Ensemble conversion reuses `combine_label_stacks`:
foreground logical OR, contour arithmetic mean. All tracking is CPU-based;
allocate baseline-equivalent RAM, CPU threads, and a working solver license.

## Evaluate and collect results

In `cell-tracking-ctc-evaluation`:

```bash
python scripts/ultrack/run_segmentation_parameters.py evaluate \
  --plan "$PARAM_PLAN" --output-root "$PARAM_OUT" --resume --num-workers 4 \
  --ids hela-01-cellpose-contour-4 hela-01-cellpose-contour-2 \
        hela-01-cellpose-contour-0
```

This invokes the existing evaluator in the active environment. Evaluated scores
and parameter values are collected in `$PARAM_OUT/summary.csv`. Regenerate it
with the `summary` stage and `--output-root "$PARAM_OUT"` at any time. Inspect
overlays against ground truth as well as scores to judge oversized boundaries.
Threshold tuning uses public annotations and must be reported as tuning, not
independent test performance.

## Verify Cellpose's zero threshold

In the existing **Cellpose 3** environment used by the 2D experiments:

```bash
python scripts/ultrack/run_segmentation_parameters.py inspect-cellpose \
  --output-root "$PARAM_OUT"
```

The output records the installed version, signatures, implementation file
paths, and threshold-related source lines. Review this evidence alongside the
[Cellpose settings documentation](https://cellpose.readthedocs.io/en/latest/settings.html):
zero is a threshold on the pre-sigmoid foreground score, corresponding to 0.5
after sigmoid, rather than a zero probability or automatic adaptive setting.
This inspection does not run inference or claim that a local version was
verified before you execute the command in that environment.

## Resume and limitations

- Add `--resume` after interruptions. Generation validates saved masks and
  resumes frame by frame; changed generation package versions/settings are
  rejected to avoid mixing outputs.
- A completed tracking stage is skipped only when all masks and lineage file
  still exist. Interrupted tracking restarts in a new `tracking/attempt-NNN`
  directory; no solver-level checkpoint is claimed. Old attempts remain on disk.
- Completed evaluation stages are skipped when their metrics JSON exists.
- Experiment settings and tracking config hashes cannot change under the same
  id. Use a new id for different settings. Do not edit source images, checkpoints,
  or reused input labels in place; their contents are not hashed.
- Run only one process per experiment directory. Environments are switched
  manually between stages. No jobs are submitted automatically.
- Combined maps are currently assembled in RAM, matching the existing 2D
  ensemble workflow. This runner is for 2D sequences, not the H157 3D experiment.
- No StarDist, solver, or cluster integration has been validated merely by
  generating a plan; test one experiment through all stages first.
