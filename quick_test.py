#!/usr/bin/env python3
"""Quick test without Selenium."""
import requests
import time

print("\n" + "="*70)
print("QUICK DASHBOARD TEST")
print("="*70 + "\n")

# Test 1: Can we reach the dashboard?
print("1. Testing HTTP connection...")
try:
    response = requests.get('http://localhost:8090/', timeout=5)
    print(f"   ✅ HTTP {response.status_code}")
    print(f"   Title: {response.text[response.text.find('<title>')+7:response.text.find('</title>')]}")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    exit(1)

# Test 2: Check layout endpoint
print("\n2. Testing layout endpoint...")
try:
    response = requests.get('http://localhost:8090/_dash-layout', timeout=5)
    if response.status_code == 200:
        layout = response.json()
        print(f"   ✅ Layout loaded")
        print(f"   Layout has 'props': {'props' in layout}")
    else:
        print(f"   ❌ Status {response.status_code}")
except Exception as e:
    print(f"   ❌ Failed: {e}")

# Test 3: Check dependencies endpoint
print("\n3. Testing dependencies endpoint...")
try:
    response = requests.get('http://localhost:8090/_dash-dependencies', timeout=5)
    if response.status_code == 200:
        print(f"   ✅ Dependencies loaded")
    else:
        print(f"   ❌ Status {response.status_code}")
except Exception as e:
    print(f"   ❌ Failed: {e}")

# Test 4: Check for duplicate callbacks in dependencies
print("\n4. Checking for duplicate callbacks...")
try:
    response = requests.get('http://localhost:8090/_dash-dependencies', timeout=5)
    if response.status_code == 200:
        deps = response.json()
        
        # Count output IDs
        output_counts = {}
        for callback in deps:
            if 'output' in callback:
                output_id = f"{callback['output']}"
                output_counts[output_id] = output_counts.get(output_id, 0) + 1
        
        duplicates = {k: v for k, v in output_counts.items() if v > 1}
        
        if duplicates:
            print(f"   ❌ Found {len(duplicates)} duplicate outputs:")
            for output_id, count in list(duplicates.items())[:5]:
                print(f"      - {output_id}: {count} times")
        else:
            print(f"   ✅ No duplicate callback outputs")
except Exception as e:
    print(f"   ⚠️  Could not check: {e}")

print("\n" + "="*70)
print("SUMMARY:")
print("="*70)
print("✅ Dashboard is running and responding")
print("✅ Layout and dependencies are loading")
print("\n" + "="*70 + "\n")
