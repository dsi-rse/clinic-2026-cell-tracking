#!/bin/bash
#SBATCH --job-name=et_pretrained
#SBATCH --partition=general
#SBATCH --qos=protected
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

REPO_ROOT=${REPO_ROOT:-$HOME/clinic-2026-cell-tracking}

source /opt/conda/etc/profile.d/conda.sh
conda activate embedtrack

echo "start: $(date)  host: $(hostname)"
nvidia-smi | head -15
python -c "import torch; print('cuda:', torch.cuda.is_available(), torch.cuda.get_device_name(0))"

export PYTHONPATH=$REPO_ROOT/external/EmbedTrack:${PYTHONPATH:-}
cd "$REPO_ROOT"
jupyter nbconvert --to notebook --execute $REPO_ROOT/notebooks/embedtrack/embedtrack_pretrained_eval.ipynb --output-dir "$HOME" \
  --output embedtrack_pretrained_eval_executed.ipynb \
  --ExecutePreprocessor.timeout=3000
STATUS=$?
echo "end: $(date)  nbconvert exit status: $STATUS"
exit $STATUS
