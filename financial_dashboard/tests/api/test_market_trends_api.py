import requests
import time

BASE = 'http://localhost:8055'


def test_create_and_poll_job():
    payload = {"tickers":["SPY","QQQ","DIA"], "period":"1mo"}
    r = requests.post(f"{BASE}/api/jobs", json=payload, timeout=10)
    assert r.status_code == 200
    data = r.json()
    job_id = data.get('job_id')
    assert job_id

    # Poll until completed or timeout
    deadline = time.time() + 30
    status = None
    while time.time() < deadline:
        r = requests.get(f"{BASE}/api/jobs/{job_id}")
        assert r.status_code == 200
        js = r.json()
        status = js.get('status')
        if status == 'completed':
            break
        time.sleep(1)
    assert status == 'completed'


def test_get_latest_results():
    r = requests.get(f"{BASE}/api/results/latest", timeout=10)
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        js = r.json()
        assert js.get('success') is True
