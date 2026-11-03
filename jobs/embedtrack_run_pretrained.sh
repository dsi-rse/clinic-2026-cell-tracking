#!/bin/bash
# Usage (from the repo root): sbatch --exclude=k003 jobs/embedtrack_run_pretrained.sh <dataset> <model-dataset> [sequences...]
# Example: sbatch --exclude=k003 jobs/embedtrack_run_pretrained.sh Fluo-N2DL-HeLa Fluo-N2DH-GOWT1 01 02
#SBATCH --job-name=et_run
#SBATCH --partition=general
#SBATCH --qos=protected
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

REPO_ROOT=${REPO_ROOT:-$HOME/clinic-2026-cell-tracking}
CTC_ROOT=${CTC_ROOT:-/net/spaces/clinic/CLS/DSC_CTC/ctc}

DATASET=$1
MODEL_DATASET=$2
shift 2
SEQUENCES=${*:-01 02}

source /opt/conda/etc/profile.d/conda.sh
conda activate embedtrack

echo "start: $(date)  host: $(hostname)  data: $DATASET  model: $MODEL_DATASET  sequences: $SEQUENCES"
nvidia-smi | head -15

export PYTHONPATH=$REPO_ROOT/external/EmbedTrack:${PYTHONPATH:-}
cd "$REPO_ROOT/external/EmbedTrack"
# shellcheck disable=SC2086  # SEQUENCES is a space-separated list on purpose
python "$REPO_ROOT/scripts/embedtrack/run_pretrained.py" \
  --dataset "$DATASET" --model-dataset "$MODEL_DATASET" --sequences $SEQUENCES \
  --raw-root "$CTC_ROOT" --models-root KIT-Loe-GE/models --results-root results
STATUS=$?
echo "end: $(date)  exit status: $STATUS"
exit $STATUS
