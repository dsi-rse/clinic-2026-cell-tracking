#!/bin/bash
#SBATCH --job-name=kitge-seg
#SBATCH --partition=general
#SBATCH --gres=gpu:1
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
source "$JOBS_DIR/datasets.sh" "${1:?usage: sbatch segmentation.sh <dataset>}"

EXTRA=()
if [ "$FUSE" = 1 ]; then EXTRA+=(--fuse_z_seeds); fi
if [ "$AC" = 1 ]; then EXTRA+=(--artifact_correction); fi

echo "job: ${SLURM_JOB_ID:-local}  node: $(hostname)  start: $(date)"
nvidia-smi --query-gpu=name,memory.total --format=csv || true
"$SEG_PY" -u "$JOBS_DIR/segment_only.py" --seg_repo "$SEG_REPO" --ds "$DS" \
    --th_seed "$TH_SEED" --th_cell "$TH_CELL" --scale "$SCALE" --batch_size "$BS" "${EXTRA[@]}"
echo "end: $(date)"