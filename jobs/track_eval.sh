#!/bin/bash
#SBATCH --job-name=kitge-trackeval
#SBATCH --partition=general
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --output=%x_%j.out
set -e
source /net/scratch/evt-kit-ge/clinic-2026-cell-tracking/jobs/datasets.sh "${1:?usage: sbatch track_eval.sh <dataset>}"

for SEQ in 01 02; do
  echo "===== $DS $SEQ: validate + evaluate tracking ====="
  $SEGENV/bin/ctc_validate --res $TRACK_OUT/${SEQ}_RES || true
  $SEGENV/bin/ctc_evaluate --gt $DATA/${SEQ}_GT --res $TRACK_OUT/${SEQ}_RES \
      --csv-file $PROJ/tracking_results/${DS}_${SEQ}_tracking_metrics.csv
done
$SEGENV/bin/python $JOBS/summarize_scores.py "$DS" || true
echo "Done"