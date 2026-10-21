""" Per-dataset settings for the KIT-GE (3) pipeline.

Defaults come from the best_settings in models/kit-sch-ge/<dataset>_GT+ST_model.json"""

PROJ=/net/scratch/evt-kit-ge/clinic-2026-cell-tracking
JOBS=$PROJ/jobs
SEGREPO=/net/spaces/scratch/evt-kit-ge/clinic-2026-cell-tracking/external/KIT-GE-3-Cell-Segmentation-for-CTC
TRKREPO=/net/spaces/scratch/evt-kit-ge/clinic-2026-cell-tracking/external/KIT-GE-3-Cell-Tracking-for-CTC
SEGENV=$SEGREPO/env
TRKPY=/home/evt/.conda/envs/tracking_env/bin/python
export GRB_LICENSE_FILE=$HOME/gurobi.lic

case "$1" in
  Fluo-N2DL-HeLa)   TH_SEED=0.35; TH_CELL=0.07; SCALE=1; BS=16; FUSE=0; AC=0
                    SEG_TIME=00:45:00; TRACK_TIME=00:45:00; EVAL_TIME=00:30:00 ;;
  Fluo-N2DH-GOWT1)  TH_SEED=0.45; TH_CELL=0.07; SCALE=1; BS=16; FUSE=0; AC=0
                    SEG_TIME=00:45:00; TRACK_TIME=00:45:00; EVAL_TIME=00:30:00 ;;
  Fluo-C3DL-MDA231) TH_SEED=0.45; TH_CELL=0.07; SCALE=1; BS=8;  FUSE=1; AC=0
                    SEG_TIME=00:45:00; TRACK_TIME=00:45:00; EVAL_TIME=00:30:00 ;;
  Fluo-C3DH-H157)   TH_SEED=0.45; TH_CELL=0.07; SCALE=1; BS=8;  FUSE=1; AC=0
                    SEG_TIME=01:30:00; TRACK_TIME=01:30:00; EVAL_TIME=01:00:00 ;;
  *) echo "Unknown dataset '$1'. Add it to datasets.sh."; return 1 2>/dev/null || exit 1 ;;
esac

DS=$1
MODEL_NAME=${DS}_GT+ST_model
TAG=${MODEL_NAME}_${TH_SEED}_${TH_CELL}
DATA=$SEGREPO/training_data/$DS
SEGEVAL_OUT=$PROJ/seg_eval/$DS
TRACK_OUT=$PROJ/tracking_results/$DS