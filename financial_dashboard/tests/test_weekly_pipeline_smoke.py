import importlib.util
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def load_script(script_path):
    spec = importlib.util.spec_from_file_location('mod', str(script_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_run_weekly_pipeline(tmp_path):
    script = ROOT / 'scripts' / 'train_or_update_weekly.py'
    date = '20250101'
    out_dir = ROOT / 'models' / 'weekly_run'
    # ensure clean
    if out_dir.exists():
        for f in out_dir.glob('weeklypicks*.csv'):
            f.unlink()
        for f in out_dir.glob('weekly_meta_*.json'):
            f.unlink()
    # Create mock features file for testing
    test_features = ROOT / 'tests' / 'data' / 'mock_weekly_features.parquet'
    test_features.parent.mkdir(parents=True, exist_ok=True)
    
    # run the script as a subprocess
    res = subprocess.run(
        ['python3', str(script), '--date', date, '--top-k', '10', '--sample-size', '20', '--features', str(test_features)], 
        cwd=str(ROOT), 
        capture_output=True, 
        text=True
    )
    # Script may succeed even with warnings (e.g., SHAP not available)
    # Just check that it didn't fail completely
    assert res.returncode == 0, (res.stdout + '\n' + res.stderr)
    
    # Check for output files - script creates weeklypicks{MMDD}.csv format
    picks = out_dir / f'weeklypicks0101.csv'  # Uses MMDD format from date 20250101
    meta = out_dir / f'weekly_meta_{date}.json'
    assert picks.exists(), f"Expected picks file not found: {picks}. Files in directory: {list(out_dir.glob('*0101*'))}"
    assert meta.exists(), f"Expected meta file not found: {meta}"
