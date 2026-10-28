#!/bin/bash
#SBATCH --job-name=kitge-segeval
#SBATCH --partition=general
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=%x_%j.out
set -e

ENV=/net/spaces/scratch/evt-kit-ge/clinic-2026-cell-tracking/external/KIT-GE-3-Cell-Segmentation-for-CTC/env
D=/net/spaces/scratch/evt-kit-ge/clinic-2026-cell-tracking/external/KIT-GE-3-Cell-Segmentation-for-CTC/training_data/Fluo-N2DL-HeLa
MODEL=Fluo-N2DL-HeLa_GT+ST_model_0.35_0.07
OUT=/net/scratch/evt-kit-ge/clinic-2026-cell-tracking/seg_eval/Fluo-N2DL-HeLa
CSV=/net/scratch/evt-kit-ge/clinic-2026-cell-tracking/seg_eval

for SEQ in 01 02; do
  echo "===== $SEQ: convert ====="
  $ENV/bin/python /net/scratch/evt-kit-ge/clinic-2026-cell-tracking/jobs/seg_to_tracks.py $D/${SEQ}_RES_$MODEL $OUT/${SEQ}_RES
  echo "===== $SEQ: DET + SEG ====="
  $ENV/bin/ctc_evaluate --gt $D/${SEQ}_GT --res $OUT/${SEQ}_RES --det --seg \
    --csv-file $CSV/Fluo-N2DL-HeLa_${SEQ}_SEG_DET.csv
done
echo "Done"