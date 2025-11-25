#!/usr/bin/env bash
set -euo pipefail

# Activate venv
source /mnt/c/Aarav/fin_env/.venv_local/bin/activate

python -m pip install --upgrade pip setuptools wheel

# 1) Install PyTorch CPU wheels first (official index)
pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
  "torch==2.2.2+cpu" "torchvision==0.19.2+cpu" "torchaudio==2.2.2+cpu"

# 2) Install core Python packages (no torch-geometric here)
pip install --no-cache-dir \
  scikit-learn==1.4.2 \
  lightgbm==4.4.0 \
  ngboost==0.5.6 \
  joblib==1.5.2 \
  optuna==3.6.0 \
  shap==0.41.0 \
  sentence-transformers==2.2.2 \
  transformers==4.35.0 \
  pyyaml \
  fastapi \
  uvicorn==0.22.0

# 3) Install pytorch-forecasting without a tight pin so pip can resolve a matching build
pip install --no-cache-dir pytorch-forecasting

# 4) Final message
echo "INSTALL2_DONE"
