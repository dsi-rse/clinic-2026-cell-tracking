#!/bin/bash
#SBATCH --job-name=et_gowt1_smoke
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

echo "job: $SLURM_JOB_ID  node: $(hostname)  start: $(date)"
nvidia-smi
python -c "import torch; print('cuda:', torch.cuda.is_available(), torch.cuda.get_device_name(0))"
git -C $REPO_ROOT/external/EmbedTrack rev-parse HEAD

cd $REPO_ROOT/external/EmbedTrack
export PYTHONPATH=$PWD:$PYTHONPATH
python embedtrack/scripts/train_gowt1.py
STATUS=$?

echo "end: $(date)  python exit status: $STATUS"
exit $STATUS
