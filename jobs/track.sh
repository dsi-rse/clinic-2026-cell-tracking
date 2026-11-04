#!/bin/bash
#SBATCH --job-name=kitge-track
#SBATCH --partition=general
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=00:45:00
#SBATCH --output=%x_%j.out
set -e
JOBS_DIR=${JOBS_DIR:-$SLURM_SUBMIT_DIR}
if [ ! -f "$JOBS_DIR/datasets.sh" ]; then
  echo "datasets.sh not found in JOBS_DIR=$JOBS_DIR. Submit from the jobs/ folder or export JOBS_DIR." >&2
  exit 1
fi
source "$JOBS_DIR/datasets.sh" "${1:?usage: sbatch track.sh <dataset>}"
 
cd "$TRK_REPO"
for SEQ in 01 02; do
  "$TRK_PY" -u -m run_tracking --image_path "$DATA/$SEQ" \
      --segmentation_path "$SEG_RES/${SEQ}_RES_$TAG" --results_path "$TRACK_OUT/${SEQ}_RES"
done
 
echo "Done"