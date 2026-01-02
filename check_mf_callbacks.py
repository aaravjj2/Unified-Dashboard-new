#!/usr/bin/env python3
"""Direct check of callback registration"""
import requests
import json

def check_callbacks():
    # Get callback info from Dash
    resp = requests.get("http://localhost:8050/_dash-dependencies")
    if resp.status_code != 200:
        print(f"❌ Failed to get dependencies: {resp.status_code}")
        return
    
    data = resp.json()
    
    # Find mf-run-btn related callbacks
    mf_callbacks = []
    for cb in data:
        inputs = cb.get('inputs', [])
        for inp in inputs:
            inp_id = inp.get('id', '')
            if 'mf-run-btn' in str(inp_id) or 'mf-train' in str(inp_id):
                mf_callbacks.append(cb)
                break
    
    print(f"📋 Found {len(mf_callbacks)} callbacks with mf-run-btn or mf-train input:")
    for i, cb in enumerate(mf_callbacks, 1):
        inputs = cb.get('inputs', [])
        outputs = cb.get('output', '')
        print(f"\n{i}. Inputs: {[inp.get('id') for inp in inputs]}")
        print(f"   Outputs: {outputs[:200]}...")
    
    # Also check for mf-forecast-chart output
    forecast_chart_cbs = []
    for cb in data:
        output = cb.get('output', '')
        if 'mf-forecast-chart' in output:
            forecast_chart_cbs.append(cb)
    
    print(f"\n📊 Found {len(forecast_chart_cbs)} callbacks that output to mf-forecast-chart")
    for cb in forecast_chart_cbs:
        inputs = cb.get('inputs', [])
        print(f"   Input IDs: {[inp.get('id') for inp in inputs]}")

if __name__ == "__main__":
    check_callbacks()
