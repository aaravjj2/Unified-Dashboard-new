#!/usr/bin/env python3
"""Directly invoke the forecast callback via HTTP"""
import requests
import json

# Simulate what Dash sends when the button is clicked
payload = {
    "output": "..mf-forecast-store.data...mf-forecast-chart.figure...mf-model-comparison-chart.figure...mf-model-metrics.children...mf-status-banner.children...mf-scenario-apply-btn.disabled...mf-price-info.children...mf-sentiment-display.children...mf-sentiment-distribution.children...mf-sentiment-headlines.children..",
    "outputs": [
        {"id": "mf-forecast-store", "property": "data"},
        {"id": "mf-forecast-chart", "property": "figure"},
        {"id": "mf-model-comparison-chart", "property": "figure"},
        {"id": "mf-model-metrics", "property": "children"},
        {"id": "mf-status-banner", "property": "children"},
        {"id": "mf-scenario-apply-btn", "property": "disabled"},
        {"id": "mf-price-info", "property": "children"},
        {"id": "mf-sentiment-display", "property": "children"},
        {"id": "mf-sentiment-distribution", "property": "children"},
        {"id": "mf-sentiment-headlines", "property": "children"}
    ],
    "inputs": [
        {"id": "mf-run-btn", "property": "n_clicks", "value": 1},
        {"id": "mf-train-all-btn", "property": "n_clicks", "value": None}
    ],
    "changedPropIds": ["mf-run-btn.n_clicks"],
    "state": [
        {"id": "mf-ticker-input", "property": "value", "value": "AAPL"},
        {"id": "mf-horizon-select", "property": "value", "value": 14},
        {"id": "mf-model-checklist", "property": "value", "value": ["prophet", "ensemble"]},
        {"id": "mf-interval-checklist", "property": "value", "value": ["80", "95"]}
    ]
}

print("🚀 Invoking forecast callback directly via HTTP...")
print(f"📦 Payload: ticker=AAPL, horizon=14, models=['prophet', 'ensemble']")

try:
    resp = requests.post(
        "http://localhost:8050/_dash-update-component",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=120
    )
    
    print(f"\n📬 Response Status: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        response = data.get('response', {})
        
        # Check forecast chart
        chart_data = response.get('mf-forecast-chart', {}).get('figure', {}).get('data', [])
        print(f"📊 Forecast chart traces: {len(chart_data)}")
        for i, trace in enumerate(chart_data[:3]):
            print(f"   Trace {i+1}: {trace.get('name', 'unnamed')} ({len(trace.get('y', []))} points)")
        
        # Check metrics
        metrics = response.get('mf-model-metrics', {})
        print(f"📊 Metrics: {str(metrics)[:200]}...")
        
        # Check status banner
        status = response.get('mf-status-banner', {})
        print(f"📊 Status: {str(status)[:200]}...")
        
    elif resp.status_code == 204:
        print("⚠️ Callback returned 204 (no update/PreventUpdate)")
    else:
        print(f"❌ Error: {resp.text[:500]}")
        
except requests.exceptions.Timeout:
    print("⏰ Request timed out after 120 seconds")
except Exception as e:
    print(f"❌ Exception: {e}")

print("\n" + "=" * 60)
