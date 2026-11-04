# HeLa data, GOWT1 model (cross-dataset)

| Sequence | SEG | TRA | DET |
|---|---|---|---|
| 01 | 0.200370 | 0.221962 | 0.237574 |
| 02 | 0.112124 | 0.173708 | 0.181735 |
| Mean | 0.156 | 0.198 | 0.210 |

| | SEG | TRA | OP_CTB |
|---|---|---|---|
| HeLa model on HeLa (own dataset, `../20261020_embedtrack_Fluo-N2DL-HeLa_pretrained-kit-loe-ge/`) | 0.884 | 0.990 | 0.937 |
| GOWT1 model on HeLa (this run) | 0.156 | 0.198 | 0.177 |

The GOWT1 model reaches roughly a fifth of the own-dataset score on HeLa. EmbedTrack
models are specific to the dataset they were trained on (cell appearance, size, imaging).

## Reproducing the scores

A teammate can reproduce the numbers on the cluster with the Python scorer from
`scripts/ultrack/evaluate_ctc_result.py` (environment `environments/ctc-evaluation.yaml`):

```bash
conda activate cell-tracking-ctc-evaluation
G=<CTC_ROOT>/ctc/Fluo-N2DL-HeLa
R=external/EmbedTrack/results/Fluo-N2DL-HeLa/KIT-Loe-GE_model-Fluo-N2DH-GOWT1/train

PYTHONPATH=src python scripts/ultrack/evaluate_ctc_result.py \
    --ground-truth-dir $G/01_GT \
    --result-dir $R/01_RES \
    --output-dir <OUTPUT_DIR> \
    --dataset Fluo-N2DL-HeLa \
    --method embedtrack-gowt1-model \
    --num-workers 4
```

Use `02_GT` and `02_RES` for sequence 02. Comparison on sequence 01 against the
Mac build of the official CTC scorers (the source of the table above):

| Scorer | SEG | TRA | DET |
|---|---|---|---|
| CTC EvaluationSoftware (Mac build) | 0.200370 | 0.221962 | 0.237574 |
| Python scorer (cluster) | 0.200370 | 0.221962 | 0.237574 |

The Python scorer also reports OP_CTB = 0.211166 for sequence 01.
