#!/usr/bin/env python3
"""
Direct test: POST to /_dash-update-component to trigger run-btn callback
"""
import json
import requests
import time

base_url = "http://localhost:8051"

# Construct callback payload for run-btn click
payload = {
    "output": "trends-results-store.data",
    "outputs": [
        {"id": "trends-results-store", "property": "data"},
        {"id": "trends-last-cached", "property": "data"},
        {"id": "status", "property": "children"},
        {"id": "status", "property": "style"},
        {"id": "job-history", "property": "children"}
    ],
    "inputs": [
        {"id": "run-btn", "property": "n_clicks", "value": 1},
        {"id": "poll-interval", "property": "n_intervals", "value": 0},
        {"id": "dashboard-queued-job", "property": "data", "value": None}
    ],
    "state": [
        {"id": "reload-trigger", "property": "data", "value": None},
        {"id": "tickers-input", "property": "value", "value": "AAPL,GOOGL,MSFT,NVDA,TSLA"},
        {"id": "period-input", "property": "value", "value": "1mo"},
        {"id": "current-job", "property": "data", "value": None},
        {"id": "analysis-options", "property": "value", "value": []}
    ],
    "changedPropIds": ["run-btn.n_clicks"]
}

print("📤 Sending callback request to", base_url + "/_dash-update-component")
print("📦 Payload:", json.dumps(payload, indent=2))

try:
    response = requests.post(
        base_url + "/_dash-update-component",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    
    print(f"\n✅ Response status: {response.status_code}")
    print(f"📨 Response body ({len(response.text)} chars):")
    print(response.text[:500])
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"\n📊 Response data keys: {list(data.keys())}")
        except:
            pass
    
except requests.Timeout:
    print("\n❌ Request timed out after 10 seconds")
except Exception as e:
    print(f"\n❌ Error: {e}")
