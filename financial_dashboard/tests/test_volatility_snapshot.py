import requests


def test_volatility_snapshot_has_vix_chart():
    """Fetch local Volatility Lab runner and assert key markers are present."""
    url = "http://127.0.0.1:8050/"
    resp = requests.get(url, timeout=5)
    assert resp.status_code == 200
    html = resp.text.lower()
    # Must contain the VIX graph element id
    assert 'id="vix-chart"' in html or "vix-chart" in html, "vix-chart element not found"
    # Must not contain the 'undefined' placeholder text indicating broken layout
    assert 'undefined' not in html, "Found 'undefined' in rendered page"
