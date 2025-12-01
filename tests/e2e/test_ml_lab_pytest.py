"""
Pytest E2E template for ML Integration Lab

This is a small pytest template that uses requests to assert endpoint availability
and checks that placeholder JSON endpoints (if implemented) return expected keys.

It intentionally does NOT start or stop the dashboard.
"""
import json
import pytest
import requests


BASE = "http://localhost:8050"


def test_ml_lab_homepage_available():
    """Check that ML lab homepage responds (if server is up)."""
    try:
        r = requests.get(f"{BASE}/ml_integration_lab", timeout=3)
    except Exception:
        pytest.skip("Dashboard not running on localhost:8050 - skipping live check")
    assert r.status_code == 200


def test_ml_prediction_placeholder_api():
    """If placeholder JSON endpoint exists, verify contract (non-fatal)."""
    try:
        r = requests.get(f"{BASE}/api/ml/predictions", timeout=2)
    except Exception:
        pytest.skip("No ML API endpoint available - skip")
    assert r.status_code == 200
    payload = r.json()
    assert isinstance(payload, dict)
