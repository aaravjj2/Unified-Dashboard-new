#!/usr/bin/env bash
set -euo pipefail

# activate venv (adjust if not in same shell)
source /mnt/c/Aarav/fin_env/.venv_local/bin/activate

# 1) safe core python packages (no heavy binary wheels)
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
  uvicorn==0.22.0 \
  pytorch-forecasting==0.11.6

# 2) install PyTorch CPU wheels from official index
pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
  'torch==2.2.2+cpu' 'torchvision==0.19.2+cpu' 'torchaudio==2.2.2+cpu'

# NOTE: torch-geometric is omitted here; it requires matching prebuilt wheels.
# If you want it, install following PyG docs after confirming torch version:
# https://pytorch-geometric.readthedocs.io/en/latest/notes/installation.html

echo "INSTALL_DONE"
