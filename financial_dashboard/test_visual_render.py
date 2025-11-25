#!/usr/bin/env python3
"""
Test if tabs are visible in browser by checking rendered HTML and layout
"""
import requests
import json

ports = {
    8054: "Analysis Hub",
    8056: "Portfolio Dashboard",
    8057: "Event Monitor",
    8058: "Research Lab"
}

print("=" * 70)
print("Phase 4 Visual Render Test")
print("=" * 70)
print()

for port, name in ports.items():
    print(f"Testing {name} (port {port})...")
    
    try:
        # Check main page
        response = requests.get(f'http://localhost:{port}/')
        if response.status_code == 200:
            html = response.text
            has_content = len(html) > 1000
            print(f"  ✓ Main page loads ({len(html)} bytes)")
        else:
            print(f"  ✗ Main page failed: HTTP {response.status_code}")
            continue
        
        # Check layout
        layout_response = requests.get(f'http://localhost:{port}/_dash-layout')
        if layout_response.status_code == 200:
            layout = layout_response.json()
            layout_str = json.dumps(layout)
            print(f"  ✓ Layout endpoint ({len(layout_str)} bytes)")
            
            # Check for specific components
            if port == 8054:
                has_tabs = 'Attribution' in layout_str and 'Scenario' in layout_str
                print(f"  {'✓' if has_tabs else '✗'} Tabs content found: {has_tabs}")
            elif port == 8056:
                has_portfolio = 'Positions' in layout_str or 'Portfolio' in layout_str
                print(f"  {'✓' if has_portfolio else '✗'} Portfolio content found: {has_portfolio}")
            elif port == 8057:
                has_events = 'Event' in layout_str or 'events' in layout_str
                print(f"  {'✓' if has_events else '✗'} Events content found: {has_events}")
            elif port == 8058:
                has_research = 'Experiment' in layout_str or 'Research' in layout_str
                print(f"  {'✓' if has_research else '✗'} Research content found: {has_research}")
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    print()

print("=" * 70)
print("To test in browser, visit:")
print("  • http://localhost:8054 (Analysis Hub)")
print("  • http://localhost:8056 (Portfolio)")
print("  • http://localhost:8057 (Event Monitor)")
print("  • http://localhost:8058 (Research Lab)")
print("=" * 70)
