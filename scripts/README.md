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
