# EmbedTrack on Fluo-N2DL-HeLa, sequence 02: seed vote threshold 9 (default 4.5)

Pretrained HeLa model, one inference parameter changed, everything else at the
default. Scored against the ground truth on sequence 02, which the model saw in
training, so the numbers are optimistic and are for comparison between settings.

| Run | DET | SEG | TRA | OP_CTB |
|---|---|---|---|---|
| Default (min size about 102 px, 4.5 votes) | 0.990094 | 0.897748 | 0.987955 | 0.942852 |
| This run | 0.990035 | 0.897286 | 0.987890 | 0.942588 |
| Difference | -0.0001 | -0.0005 | -0.0001 | -0.0003 |

Missed objects (AOGM_FN): 81 (default 79). Spurious objects (AOGM_FP): 1288 (default 1293).

The default row comes from scoring the default HeLa run on sequence 02 with the
same Python scorer.

## Reproducing

    conda activate cell-tracking-ctc-evaluation
    PYTHONPATH=src python scripts/ultrack/evaluate_ctc_result.py \
        --ground-truth-dir <CTC_ROOT>/ctc/Fluo-N2DL-HeLa/02_GT \
        --result-dir external/EmbedTrack/results/Fluo-N2DL-HeLa/KIT-Loe-GE_mcp9/train/02_RES \
        --output-dir <OUTPUT_DIR> \
        --dataset Fluo-N2DL-HeLa \
        --method embedtrack-mcp9 \
        --num-workers 4
