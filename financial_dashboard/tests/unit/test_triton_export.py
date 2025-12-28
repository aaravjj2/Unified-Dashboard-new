import importlib
import os
import sys
import pytest

from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
EXPORT_SCRIPT = ROOT / 'financial_dashboard' / 'serving' / 'triton' / 'forecast_ensemble' / 'export_model_repo.py'
MODEL_REPO = ROOT / 'financial_dashboard' / 'serving' / 'triton' / 'forecast_ensemble' / 'model_repository' / 'forecast_ensemble'


def test_export_model_repo_runs_or_skips():
    """
    Attempt to run the export script to produce a TorchScript model. If
    PyTorch isn't installed in the environment, skip this test. The test will
    assert the model file exists when runnable.
    """
    try:
        import torch  # type: ignore
    except Exception:
        pytest.skip('PyTorch not available in this environment')

    # Run the export script
    res = os.system(f"{sys.executable} {EXPORT_SCRIPT}")
    assert res == 0

    model_path = MODEL_REPO / '1' / 'model.pt'
    assert model_path.exists(), "Expected model.pt to be created in model repo"
