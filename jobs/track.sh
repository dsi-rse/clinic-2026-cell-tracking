#!/bin/bash
#SBATCH --job-name=kitge-track
#SBATCH --partition=general
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=00:45:00
#SBATCH --output=%x_%j.out
set -e
source /net/scratch/evt-kit-ge/clinic-2026-cell-tracking/jobs/datasets.sh "${1:?usage: sbatch track.sh <dataset>}"

cd "$TRK_REPO"
for SEQ in 01 02; do
  "$TRK_PY" -u -m run_tracking --image_path "$DATA/$SEQ" \
      --segmentation_path "$DATA/${SEQ}_RES_$TAG" --results_path "$TRACK_OUT/${SEQ}_RES"
done

echo "Done"