#!/bin/bash
# Collect everything needed for a runs/<date>_kitge3_<dataset>_<description>/ experiment record.
# Run on the cluster from the clinic repo's jobs/ folder:
#   bash collect_run_info.sh <dataset> <job id> [<job id> ...]
#   e.g. bash collect_run_info.sh Fluo-N2DL-HeLa 2169821 2169971 2170072 <segeval id> <trackeval id>
# Writes run_info_<dataset>.txt in the current folder. It only reads files; it changes nothing.

DS=${1:?usage: bash collect_run_info.sh <dataset> <job id> [<job id> ...]}
shift
JOBIDS=("$@")
source ./datasets.sh "$DS" || exit 1
OUT=run_info_${DS}.txt

{
echo "##### dataset / settings"
echo "dataset=$DS th_seed=$TH_SEED th_cell=$TH_CELL scale=$SCALE batch=$BS fuse_z_seeds=$FUSE artifact_correction=$AC"
echo "collected: $(date)  host: $(hostname)"

echo; echo "##### repository commits"
echo "clinic:       $(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null) ($(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null))"
echo "segmentation: $(git -C "$SEG_REPO" rev-parse HEAD 2>/dev/null)"
echo "tracking:     $(git -C "$TRK_REPO" rev-parse HEAD 2>/dev/null)"

echo; echo "##### model"
sha256sum "$SEG_REPO/models/kit-sch-ge/${MODEL_NAME}.pth" 2>&1
"$SEG_PY" -c "import json; print('best_settings:', json.load(open('$SEG_REPO/models/kit-sch-ge/${MODEL_NAME}.json')).get('best_settings'))" 2>&1

echo; echo "##### data"
for SEQ in 01 02; do
  echo "$SEQ: $(ls "$DATA/$SEQ" 2>/dev/null | wc -l) frames, $(ls "$DATA/${SEQ}_GT/SEG" 2>/dev/null | wc -l) SEG GT files, $(ls "$DATA/${SEQ}_GT/TRA" 2>/dev/null | grep -c tif) TRA GT files"
  echo "    SEG GT examples: $(ls "$DATA/${SEQ}_GT/SEG" 2>/dev/null | head -3 | tr '\n' ' ')"
done
ZIP=$(find "$SEG_REPO" "$REPO_ROOT" "$HOME" -maxdepth 3 -name "${DS}.zip" 2>/dev/null | head -1)
if [ -n "$ZIP" ]; then sha256sum "$ZIP"; else echo "archive ${DS}.zip not found (deleted after download)"; fi

echo; echo "##### environments"
"$SEG_PY" -c "import sys, torch, numpy, tifffile; print('segmentation env: python', sys.version.split()[0], '| torch', torch.__version__, '| numpy', numpy.__version__, '| tifffile', tifffile.__version__)" 2>&1
"$SEG_ENV/bin/pip" show py-ctcmetrics 2>/dev/null | grep -i '^version' | sed 's/^/py-ctcmetrics /'
"$TRK_PY" -c "import sys, numpy, gurobipy, tifffile; print('tracking env: python', sys.version.split()[0], '| numpy', numpy.__version__, '| gurobipy', gurobipy.gurobi.version(), '| tifffile', tifffile.__version__)" 2>&1

echo; echo "##### jobs (sacct)"
if [ ${#JOBIDS[@]} -gt 0 ]; then
  IDS=$(IFS=,; echo "${JOBIDS[*]}")
  sacct -j "$IDS" --format=JobID,JobName%30,State,ExitCode,Start,Elapsed,NodeList,AllocTRES%60,MaxRSS 2>&1
else
  echo "no job IDs given"
fi
echo; echo "##### job logs for these IDs (in $(pwd))"
for id in "${JOBIDS[@]}"; do ls ./*_"${id}".out 2>/dev/null; done

echo; echo "##### outputs"
for SEQ in 01 02; do
  echo "segmentation $SEQ: $(ls "$DATA/${SEQ}_RES_$TAG" 2>/dev/null | wc -l) files in $DATA/${SEQ}_RES_$TAG"
  echo "tracking     $SEQ: $(ls "$TRACK_OUT/${SEQ}_RES" 2>/dev/null | wc -l) files in $TRACK_OUT/${SEQ}_RES"
done

echo; echo "##### score CSVs"
for f in "$SEG_EVAL_DIR/${DS}"_*_SEG_DET.csv "$TRACK_DIR/${DS}"_*_tracking_metrics.csv; do
  [ -f "$f" ] && { echo "--- $f"; cat "$f"; echo; }
done
echo; echo "##### summary"
"$SEG_PY" "$JOBS_DIR/summarize_scores.py" "$DS" --seg_eval_dir "$SEG_EVAL_DIR" --track_dir "$TRACK_DIR" 2>&1
} > "$OUT" 2>&1

echo "Wrote $(pwd)/$OUT"