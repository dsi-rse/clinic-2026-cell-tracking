#!/bin/bash
#SBATCH --job-name=kitge-track
#SBATCH --partition=general
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=06:00:00
#SBATCH --output=%x_%j.out
EXT=/net/scratch/evt-kit-ge/clinic-2026-cell-tracking/external
PROJ=/net/scratch/evt-kit-ge/clinic-2026-cell-tracking

eval "$(conda shell.bash hook)"
conda activate tracking_env
export GRB_LICENSE_FILE=$HOME/gurobi.lic

DS=Fluo-N2DL-HeLa
TAG=Fluo-N2DL-HeLa_GT+ST_model_0.35_0.07
DATA=$EXT/KIT-GE-3-Cell-Segmentation-for-CTC/training_data/$DS
OUT=$PROJ/tracking_results/$DS

cd $EXT/KIT-GE-3-Cell-Tracking-for-CTC
for SEQ in 01 02; do
  python -u -m run_tracking \
      --image_path        $DATA/$SEQ \
      --segmentation_path $DATA/${SEQ}_RES_$TAG \
      --results_path      $OUT/${SEQ}_RES
done
