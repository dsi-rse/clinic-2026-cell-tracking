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
