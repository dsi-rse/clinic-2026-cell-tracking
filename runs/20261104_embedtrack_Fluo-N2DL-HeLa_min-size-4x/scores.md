# EmbedTrack on Fluo-N2DL-HeLa, sequence 02: minimum object size x4 (about 410 px instead of 102 px)

Pretrained HeLa model, one inference parameter changed, everything else at the
default. Scored against the ground truth on sequence 02, which the model saw in
training, so the numbers are optimistic and are for comparison between settings.

| Run | DET | SEG | TRA | OP_CTB |
|---|---|---|---|---|
| Default (min size about 102 px, 4.5 votes) | 0.990094 | 0.897748 | 0.987955 | 0.942852 |
| This run | 0.860810 | 0.752573 | 0.857042 | 0.804807 |
| Difference | -0.1293 | -0.1452 | -0.1309 | -0.1380 |

Missed objects (AOGM_FN): 3437 (default 79). Spurious objects (AOGM_FP): 607 (default 1293).

The default row comes from scoring the default HeLa run on sequence 02 with the
same Python scorer.

## Reproducing

    conda activate cell-tracking-ctc-evaluation
    PYTHONPATH=src python scripts/ultrack/evaluate_ctc_result.py \
        --ground-truth-dir <CTC_ROOT>/ctc/Fluo-N2DL-HeLa/02_GT \
        --result-dir external/EmbedTrack/results/Fluo-N2DL-HeLa/KIT-Loe-GE_mms4/train/02_RES \
        --output-dir <OUTPUT_DIR> \
        --dataset Fluo-N2DL-HeLa \
        --method embedtrack-mms4 \
        --num-workers 4
