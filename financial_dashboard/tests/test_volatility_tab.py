import importlib.util
from pathlib import Path


def load_volatility_tab():
    p = Path(__file__).resolve().parents[1] / 'tabs' / 'volatility_lab.py'
    spec = importlib.util.spec_from_file_location('volatility_lab_test', str(p))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_layout_returns_container():
    """Ensure volatility tab's layout() returns a non-empty container object."""
    mod = load_volatility_tab()
    layout_obj = mod.layout()
    assert layout_obj is not None
    # Basic type check: dash-bootstrap Container class name appears in repr
    tname = type(layout_obj).__name__.lower()
    assert 'container' in tname or 'div' in tname
