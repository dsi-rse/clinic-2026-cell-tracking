#!/bin/bash
#SBATCH --job-name=kitge-seg
#SBATCH --partition=general
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=00:45:00
#SBATCH --output=%x_%j.out
set -e
source /net/scratch/evt-kit-ge/clinic-2026-cell-tracking/jobs/datasets.sh "${1:?usage: sbatch segmentation.sh <dataset>}"

EXTRA=""
if [ "$FUSE" = 1 ]; then EXTRA="$EXTRA --fuse_z_seeds"; fi
if [ "$AC" = 1 ];   then EXTRA="$EXTRA --artifact_correction"; fi

nvidia-smi --query-gpu=name,memory.total --format=csv || true
$SEGENV/bin/python -u $JOBS/segment_only.py --ds "$DS" \
    --th_seed $TH_SEED --th_cell $TH_CELL --scale $SCALE --batch_size $BS $EXTRA