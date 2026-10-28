#!/bin/bash
#SBATCH --job-name=kitge-segeval
#SBATCH --partition=general
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --output=%x_%j.out
set -e
source /net/scratch/evt-kit-ge/clinic-2026-cell-tracking/jobs/datasets.sh "${1:?usage: sbatch seg_eval.sh <dataset>}"

mkdir -p "$SEG_EVAL_DIR"
for SEQ in 01 02; do
  "$SEG_PY" "$JOBS_DIR/seg_to_tracks.py" "$DATA/${SEQ}_RES_$TAG" "$SEGEVAL_OUT/${SEQ}_RES"
  "$CTC_EVALUATE" --gt "$DATA/${SEQ}_GT" --res "$SEGEVAL_OUT/${SEQ}_RES" --det --seg \
      --csv-file "$SEG_EVAL_DIR/${DS}_${SEQ}_SEG_DET.csv"
done
"$SEG_PY" "$JOBS_DIR/summarize_scores.py" "$DS" --seg_eval_dir "$SEG_EVAL_DIR" --track_dir "$TRACK_DIR" || true

echo "Done"