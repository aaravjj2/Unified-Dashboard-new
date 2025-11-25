"""
Simple test: Check if Run Analysis callback fires by monitoring server logs
"""
import requests
import time
import json

def test_run_button_callback():
    """Test if clicking Run Analysis triggers the callback"""
    
    print("Testing Run Analysis button callback...")
    print("=" * 60)
    
    # Get initial layout to find run-btn component
    try:
        resp = requests.get('http://localhost:8051/_dash-layout', timeout=10)
        layout = resp.json()
        print("✅ Dashboard layout loaded")
    except Exception as e:
        print(f"❌ Failed to load layout: {e}")
        return False
    
    # Simulate button click by posting to _dash-update-component
    # This mimics what happens when user clicks the button in browser
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
            {"id": "tickers-input", "property": "value", "value": "AAPL,MSFT"},
            {"id": "period-input", "property": "value", "value": "1d"},
            {"id": "current-job", "property": "data", "value": None},
            {"id": "analysis-options", "property": "value", "value": []}
        ]
    }
    
    print("\n📤 Sending callback request (simulating Run Analysis click)...")
    try:
        resp = requests.post(
            'http://localhost:8051/_dash-update-component',
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"📥 Response status: {resp.status_code}")
        
        if resp.status_code == 200:
            result = resp.json()
            print(f"✅ Callback executed successfully!")
            print(f"📊 Response keys: {list(result.keys())}")
            
            # Check if we got actual data back
            if 'response' in result:
                response_data = result['response']
                print(f"\n📋 Response data:")
                for key, value in response_data.items():
                    if isinstance(value, dict):
                        print(f"  {key}: {list(value.keys()) if value else 'None'}")
                    elif isinstance(value, str):
                        print(f"  {key}: {value[:100]}")
                    else:
                        print(f"  {key}: {type(value)}")
                return True
            else:
                print(f"⚠️ Unexpected response format: {result}")
                return False
        else:
            print(f"❌ Callback failed with status {resp.status_code}")
            print(f"Response: {resp.text[:500]}")
            return False
            
    except Exception as e:
        print(f"❌ Error calling callback: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_run_button_callback()
    print("\n" + "=" * 60)
    if success:
        print("✅ TEST PASSED: Run Analysis callback is working!")
    else:
        print("❌ TEST FAILED: Run Analysis callback not working")
    print("=" * 60)
