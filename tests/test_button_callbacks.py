"""
Quick button test - Check if callbacks are firing
"""
import requests
import json

# Test if server responds
response = requests.get('http://localhost:8050/')
print(f"Server status: {response.status_code}")

# Get the initial layout
if response.status_code == 200:
    print("✅ Server is responding")
    
    # Check if _dash-dependencies endpoint exists
    deps_response = requests.get('http://localhost:8050/_dash-dependencies')
    if deps_response.status_code == 200:
        deps = deps_response.json()
        print(f"\n📊 Dash Dependencies:")
        print(f"  Total callbacks: {len(deps)}")
        
        # Print first few callback structures to understand format
        print(f"\n📋 Sample callback structures:")
        for i, dep in enumerate(deps[:3]):
            print(f"\nCallback {i+1}:")
            print(f"  Type: {type(dep)}")
            if isinstance(dep, dict):
                print(f"  Keys: {dep.keys()}")
                print(f"  Output: {dep.get('output', 'N/A')}")
                print(f"  Inputs: {dep.get('inputs', 'N/A')[:100]}...")
            else:
                print(f"  Value: {str(dep)[:200]}")
        
        # Look for run-btn in all callbacks
        print(f"\n🔍 Searching for 'run-btn' in callbacks...")
        for i, dep in enumerate(deps):
            dep_str = str(dep)
            if 'run-btn' in dep_str:
                print(f"  Found in callback {i}: {dep_str[:300]}")
    else:
        print(f"⚠️  Dependencies endpoint returned: {deps_response.status_code}")

# Test a simple callback trigger
print("\n🔘 Testing callback trigger...")
try:
    # Simulate clicking the Market Trends tab
    callback_data = {
        "output": "..results-area.children...",
        "inputs": [{"id": "dashboard-tabs", "property": "active_tab", "value": "market-trends"}],
        "changedPropIds": ["dashboard-tabs.active_tab"]
    }
    
    headers = {"Content-Type": "application/json"}
    cb_response = requests.post(
        'http://localhost:8050/_dash-update-component',
        data=json.dumps(callback_data),
        headers=headers
    )
    
    print(f"Callback response status: {cb_response.status_code}")
    if cb_response.status_code == 200:
        print(f"✅ Callback fired successfully")
        print(f"Response length: {len(cb_response.text)} chars")
    else:
        print(f"❌ Callback failed: {cb_response.text[:200]}")
except Exception as e:
    print(f"❌ Error testing callback: {e}")
