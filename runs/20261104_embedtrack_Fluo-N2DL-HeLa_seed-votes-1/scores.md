# EmbedTrack on Fluo-N2DL-HeLa, sequence 02: seed vote threshold 1 (default 4.5)

Pretrained HeLa model, one inference parameter changed, everything else at the
default. Scored against the ground truth on sequence 02, which the model saw in
training, so the numbers are optimistic and are for comparison between settings.

| Run | DET | SEG | TRA | OP_CTB |
|---|---|---|---|---|
| Default (min size about 102 px, 4.5 votes) | 0.990094 | 0.897748 | 0.987955 | 0.942852 |
| This run | 0.990157 | 0.896175 | 0.988041 | 0.942108 |
| Difference | +0.0001 | -0.0016 | +0.0001 | -0.0007 |

Missed objects (AOGM_FN): 78 (default 79). Spurious objects (AOGM_FP): 1317 (default 1293).

The default row comes from scoring the default HeLa run on sequence 02 with the
same Python scorer.

## Reproducing

    conda activate cell-tracking-ctc-evaluation
    PYTHONPATH=src python scripts/ultrack/evaluate_ctc_result.py \
        --ground-truth-dir <CTC_ROOT>/ctc/Fluo-N2DL-HeLa/02_GT \
        --result-dir external/EmbedTrack/results/Fluo-N2DL-HeLa/KIT-Loe-GE_mcp1/train/02_RES \
        --output-dir <OUTPUT_DIR> \
        --dataset Fluo-N2DL-HeLa \
        --method embedtrack-mcp1 \
        --num-workers 4
