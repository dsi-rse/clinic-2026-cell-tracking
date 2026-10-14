#!/bin/bash
#SBATCH --job-name=kitge-seg
#SBATCH --partition=general
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=%x_%j.out
EXT=/net/scratch/evt-kit-ge/clinic-2026-cell-tracking/external

eval "$(conda shell.bash hook)"
conda activate /net/spaces/scratch/evt-kit-ge/clinic-2026-cell-tracking/external/KIT-GE-3-Cell-Segmentation-for-CTC/env
cd $EXT/KIT-GE-3-Cell-Segmentation-for-CTC
python -u /net/scratch/evt-kit-ge/clinic-2026-cell-tracking/jobs/segment_only.py