import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WL_PATH = ROOT / 'scripts' / 'weekly_lock.py'

def _load_wl():
    spec = importlib.util.spec_from_file_location('weekly_lock', str(WL_PATH))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_acquire_release_tmp_lock(tmp_path):
    wl = _load_wl()
    # use a temporary name to avoid colliding with real lock
    name = 'test_weekly_lock'
    assert wl.acquire_lock(name=name) is True
    status = wl.lock_status(name=name)
    assert status.get('locked') is True
    assert wl.release_lock(name=name) is True
    status = wl.lock_status(name=name)
    assert status.get('locked') in (False, None)
