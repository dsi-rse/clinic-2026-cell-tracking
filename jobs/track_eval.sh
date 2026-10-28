#!/bin/bash
#SBATCH --job-name=kitge-trackeval
#SBATCH --partition=general
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --output=%x_%j.out
set -e
source /net/scratch/evt-kit-ge/clinic-2026-cell-tracking/jobs/datasets.sh "${1:?usage: sbatch track_eval.sh <dataset>}"

mkdir -p "$TRACK_DIR"
for SEQ in 01 02; do
  "$CTC_VALIDATE" --res "$TRACK_OUT/${SEQ}_RES" || true
  "$CTC_EVALUATE" --gt "$DATA/${SEQ}_GT" --res "$TRACK_OUT/${SEQ}_RES" \
      --csv-file "$TRACK_DIR/${DS}_${SEQ}_tracking_metrics.csv"
done
"$SEG_PY" "$JOBS_DIR/summarize_scores.py" "$DS" --seg_eval_dir "$SEG_EVAL_DIR" --track_dir "$TRACK_DIR" || true
echo "Done"