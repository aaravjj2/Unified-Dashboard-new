import requests

BASE = 'http://localhost:8057'


def test_health_and_summary():
    r = requests.get(f"{BASE}/health", timeout=5)
    assert r.status_code == 200
    js = r.json()
    assert js.get('status') == 'healthy'

    # Summary may return 503 if Alpaca not configured; accept 200 or 503
    r = requests.get(f"{BASE}/portfolio/summary", timeout=10)
    assert r.status_code in (200, 503)
