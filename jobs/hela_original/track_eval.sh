#!/bin/bash
#SBATCH --job-name=kitge-trackeval
#SBATCH --partition=general
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=%x_%j.out
set -e

ENV=/net/spaces/scratch/evt-kit-ge/clinic-2026-cell-tracking/external/KIT-GE-3-Cell-Segmentation-for-CTC/env
D=/net/spaces/scratch/evt-kit-ge/clinic-2026-cell-tracking/external/KIT-GE-3-Cell-Segmentation-for-CTC/training_data/Fluo-N2DL-HeLa
T=/net/scratch/evt-kit-ge/clinic-2026-cell-tracking/tracking_results/Fluo-N2DL-HeLa
CSV=/net/scratch/evt-kit-ge/clinic-2026-cell-tracking/tracking_results

for SEQ in 01 02; do
  echo "===== $SEQ: tracking ====="
  $ENV/bin/ctc_evaluate --gt $D/${SEQ}_GT --res $T/${SEQ}_RES  --seg --tra \
    --csv-file $CSV/Fluo-N2DL-HeLa_${SEQ}_tracking_metrics.csv
done
echo "Done"