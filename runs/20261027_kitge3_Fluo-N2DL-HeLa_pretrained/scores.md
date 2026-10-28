# KIT-GE (3), pretrained, Fluo-N2DL-HeLa

Scores from `py-ctcmetrics` 1.3.3, from the CSV files written by
`jobs/seg_eval.sh` and `jobs/track_eval.sh`.

## Segmentation (raw segmentation masks)

| Sequence | SEG | DET | OP_CSB |
|---|---|---|---|
| 01 | 0.8558 | 0.9845 | 0.9201 |
| 02 | 0.8867 | 0.9892 | 0.9380 |
| Mean | 0.8713 | 0.9869 | **0.9291** |

## Tracking (tracker output)

| Sequence | SEG | DET | TRA | OP_CTB |
|---|---|---|---|---|
| 01 | 0.8553 | 0.9852 | 0.9834 | 0.9194 |
| 02 | 0.8819 | 0.9896 | 0.9878 | 0.9348 |
| Mean | 0.8686 | 0.9874 | 0.9856 | **0.9271** |


## Comparison with published values

| | SEG | DET | OP_CSB | Data |
|---|---|---|---|---|
| Published, CTC website | 0.883 | 0.994 | 0.938 | hidden challenge sequences |
| **Reproduced (this run)** | 0.8713 | 0.9869 | **0.9291** | training sequences 01 + 02 |

1. **Published values:** OP_CSB 0.938 on the challenge sequences.
2. **Reproduced value:** OP_CSB 0.9291 on the training sequences.
3. **Known differences in setup:**
   - **Images:** challenge vs. training sequences, for the website values.
   - **Libraries:** PyTorch 2.1 and newer libraries vs. PyTorch 1.7 / CUDA 11.0.
   - **Scoring tool:** `py-ctcmetrics` vs. the official CTC binaries.

   The thresholds, scale and model weights are identical to the authors'.
4. **Most likely explanation:**
   - **Against 0.938 / 0.883 (challenge data):** these were computed on different images, so they
     cannot be compared directly.