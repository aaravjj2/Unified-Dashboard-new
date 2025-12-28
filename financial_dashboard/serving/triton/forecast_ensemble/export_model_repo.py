"""
Create a Triton-style model repository layout for the example TorchScript
model produced by `model.py`.

This script will call the example `model.py` to produce `model.pt` and then
place it in `model_repository/forecast_ensemble/1/model.pt` alongside the
`config.pbtxt` file so Triton can serve it.
"""
import os
import shutil
"""
Create a Triton-style model repository layout for the example TorchScript
model produced by `model.py`.

This script will call the example `model.py` to produce `model.pt` and then
place it in `model_repository/forecast_ensemble/1/model.pt` alongside the
`config.pbtxt` file so Triton can serve it.
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MODEL_PY = os.path.join(ROOT, 'model.py')
MODEL_REPO = os.path.join(ROOT, 'model_repository', 'forecast_ensemble')
VERSION_DIR = os.path.join(MODEL_REPO, '1')


def build(seq_length=60, horizon=7, output_name='model.pt'):
    os.makedirs(VERSION_DIR, exist_ok=True)
    out_path = os.path.join(VERSION_DIR, output_name)

    # Call the model export script (works if torch is installed)
    try:
        cmd = [sys.executable, MODEL_PY, '--output', out_path, '--seq-length', str(seq_length), '--horizon', str(horizon)]
        print('Running:', ' '.join(cmd))
        subprocess.check_call(cmd)
        # Copy config
        cfg_src = os.path.join(ROOT, 'config.pbtxt')
        cfg_dst = os.path.join(MODEL_REPO, 'config.pbtxt')
        if os.path.exists(cfg_src):
            shutil.copy(cfg_src, cfg_dst)
        print('Model repository prepared at', MODEL_REPO)
        return True
    except Exception as e:
        print('Failed to build model repository:', e)
        return False


if __name__ == '__main__':
    success = build()
    if not success:
        sys.exit(2)
    print('Done')
