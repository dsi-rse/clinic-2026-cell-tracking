# EmbedTrack on Fluo-N2DL-HeLa, sequence 02: minimum object size x0.25 (about 26 px instead of 102 px)

Pretrained HeLa model, one inference parameter changed, everything else at the
default. Scored against the ground truth on sequence 02, which the model saw in
training, so the numbers are optimistic and are for comparison between settings.

| Run | DET | SEG | TRA | OP_CTB |
|---|---|---|---|---|
| Default (min size about 102 px, 4.5 votes) | 0.990094 | 0.897748 | 0.987955 | 0.942852 |
| This run | 0.989142 | 0.897966 | 0.986845 | 0.942406 |
| Difference | -0.0010 | +0.0002 | -0.0011 | -0.0004 |

Missed objects (AOGM_FN): 69 (default 79). Spurious objects (AOGM_FP): 1645 (default 1293).

The default row comes from scoring the default HeLa run on sequence 02 with the
same Python scorer.

## Reproducing

    conda activate cell-tracking-ctc-evaluation
    PYTHONPATH=src python scripts/ultrack/evaluate_ctc_result.py \
        --ground-truth-dir <CTC_ROOT>/ctc/Fluo-N2DL-HeLa/02_GT \
        --result-dir external/EmbedTrack/results/Fluo-N2DL-HeLa/KIT-Loe-GE_mms0.25/train/02_RES \
        --output-dir <OUTPUT_DIR> \
        --dataset Fluo-N2DL-HeLa \
        --method embedtrack-mms0.25 \
        --num-workers 4
