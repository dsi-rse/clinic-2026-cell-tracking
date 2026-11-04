#!/bin/bash
#SBATCH --job-name=kitge-segeval
#SBATCH --partition=general
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --output=%x_%j.out
set -e
JOBS_DIR=${JOBS_DIR:-$SLURM_SUBMIT_DIR}
if [ ! -f "$JOBS_DIR/datasets.sh" ]; then
  echo "datasets.sh not found in JOBS_DIR=$JOBS_DIR. Submit from the jobs/ folder or export JOBS_DIR." >&2
  exit 1
fi
source "$JOBS_DIR/datasets.sh" "${1:?usage: sbatch seg_eval.sh <dataset>}"

mkdir -p "$SEG_METRICS"
for SEQ in 01 02; do
  "$SEG_PY" "$SCRIPTS_DIR/seg_to_tracks.py" "$SEG_RES/${SEQ}_RES_$TAG" "$SEGEVAL_OUT/${SEQ}_RES"
  "$CTC_EVALUATE" --gt "$DATA/${SEQ}_GT" --res "$SEGEVAL_OUT/${SEQ}_RES" --det --seg \
      -n "${SLURM_CPUS_PER_TASK:-4}" \
      --csv-file "$SEG_METRICS/${DS}_${SEQ}_SEG_DET.csv"
  if compgen -G "$DATA/${SEQ}_GT/SEG/man_seg_*_*.tif" > /dev/null; then
    "$SEG_PY" "$SCRIPTS_DIR/seg_3d_check.py" "$DATA/${SEQ}_GT" "$SEG_RES/${SEQ}_RES_$TAG" \
        | tee "$SEG_METRICS/${DS}_${SEQ}_SEG_3d_check.txt" \
        || echo "seg_3d_check.py failed for $SEQ (see above)" >&2
  fi
done
"$SEG_PY" "$SCRIPTS_DIR/summarize_scores.py" "$DS" --seg_eval_dir "$SEG_METRICS" --track_dir "$TRACK_METRICS" || true

echo "Done"