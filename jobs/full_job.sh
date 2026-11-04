#!/bin/bash

# Usage:  bash full_job.sh <dataset> [<dataset> ...]
#   e.g.  bash full_job.sh Fluo-N2DH-GOWT1 Fluo-C3DL-MDA231 Fluo-C3DH-H157
set -e
cd "$(dirname "$0")"
export JOBS_DIR=$PWD

for D in "$@"; do
  source ./datasets.sh "$D"
  SEG=$(sbatch --parsable -J "seg-$DS" --time=$SEG_TIME segmentation.sh "$DS")
  TRK=$(sbatch --parsable -J "track-$DS" --time=$TRACK_TIME --dependency=afterok:$SEG track.sh "$DS")
  SEV=$(sbatch --parsable -J "segeval-$DS" --time=$EVAL_TIME --dependency=afterok:$SEG seg_eval.sh "$DS")
  TEV=$(sbatch --parsable -J "trackeval-$DS" --time=$EVAL_TIME --dependency=afterok:$TRK track_eval.sh "$DS")
  echo "$DS: seg=$SEG  track=$TRK  segeval=$SEV  trackeval=$TEV"
done