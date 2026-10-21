#!/bin/bash
#SBATCH --job-name=kitge-segeval
#SBATCH --partition=general
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --output=%x_%j.out
set -e
source /net/scratch/evt-kit-ge/clinic-2026-cell-tracking/jobs/datasets.sh "${1:?usage: sbatch seg_eval.sh <dataset>}"

for SEQ in 01 02; do
  echo "===== $DS $SEQ: convert for DET ====="
  $SEGENV/bin/python $JOBS/seg_to_tracks.py $DATA/${SEQ}_RES_$TAG $SEGEVAL_OUT/${SEQ}_RES
  echo "===== $DS $SEQ: DET + SEG ====="
  $SEGENV/bin/ctc_evaluate --gt $DATA/${SEQ}_GT --res $SEGEVAL_OUT/${SEQ}_RES --det --seg \
      --csv-file $PROJ/seg_eval/${DS}_${SEQ}_SEG_DET.csv
done
$SEGENV/bin/python $JOBS/summarize_scores.py "$DS" || true
echo "Done"