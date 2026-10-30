# Per-dataset settings for the KIT-GE (3) pipeline.

# Defaults come from the best_settings in models/kit-sch-ge/<dataset>_GT+ST_model.json

JOBS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=${REPO_ROOT:-$(dirname "$JOBS_DIR")}

SEG_REPO=${SEG_REPO:-$REPO_ROOT/external/KIT-GE-3-Cell-Segmentation-for-CTC}
TRK_REPO=${TRK_REPO:-$REPO_ROOT/external/KIT-GE-3-Cell-Tracking-for-CTC}

SEG_ENV=${SEG_ENV:-$SEG_REPO/env}
TRK_ENV=${TRK_ENV:-$HOME/.conda/envs/tracking_env}

SEG_EVAL_DIR=${SEG_EVAL_DIR:-$REPO_ROOT/seg_eval}
TRACK_DIR=${TRACK_DIR:-$REPO_ROOT/tracking_results}

export GRB_LICENSE_FILE=${GRB_LICENSE_FILE:-$HOME/gurobi.lic}

SEG_PY=$SEG_ENV/bin/python
TRK_PY=$TRK_ENV/bin/python
CTC_EVALUATE=$SEG_ENV/bin/ctc_evaluate
CTC_VALIDATE=$SEG_ENV/bin/ctc_validate

# A warning for paths that don't exist
for p in "$SEG_REPO" "$TRK_REPO" "$SEG_ENV" "$TRK_ENV"; do
  if [ ! -e "$p" ]; then
    echo "WARNING: $p does not exist. Export the matching variable (see datasets.sh)." >&2
  fi
done

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
DATA=$SEG_REPO/training_data/$DS
SEGEVAL_OUT=$SEG_EVAL_DIR/$DS
TRACK_OUT=$TRACK_DIR/$DS