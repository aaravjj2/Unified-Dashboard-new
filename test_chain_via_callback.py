#!/usr/bin/env python
"""Test if chain data is actually being stored, even if DOM element doesn't exist."""
from playwright.sync_api import sync_playwright
import time
import json

def test_chain_load_via_callback():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print("Loading dashboard...")
        page.goto('http://localhost:8050', wait_until='networkidle', timeout=30000)
        time.sleep(2)
        
        # Navigate to Options Lab
        print("\nClicking Options Lab...")
        page.click('#tab-options_lab')
        time.sleep(1)
        
        # Enter ticker
        print("Entering ticker SPY...")
        page.fill('#options-ticker-input', 'SPY')
        time.sleep(0.5)
        
        # Click Load Chain
        print("Clicking Load Chain button...")
        page.click('#options-load-btn')
        time.sleep(3)
        
        # Check status message
        status = page.locator('#options-status-message').inner_text()
        print(f"\n📊 Status message: {status}")
        
        # Try to access store data via Dash's window object
        try:
            store_data = page.evaluate('''
                () => {
                    // Try to access Dash's store registry
                    if (window.dash && window.dash._dashprivate) {
                        const stores = window.dash._dashprivate.stores || {};
                        return {
                            'options-chain-store': stores['options-chain-store'],
                            keys: Object.keys(stores)
                        };
                    }
                    return null;
                }
            ''')
            print(f"\n📦 Store data from window.dash: {json.dumps(store_data, indent=2)[:500]}")
        except Exception as e:
            print(f"\n⚠️ Couldn't access store via window.dash: {e}")
        
        # Check if the Greeks tab can access the data (callback should have been triggered)
        print("\nClicking Greeks tab...")
        page.click('#options-greeks-tab')
        time.sleep(2)
        
        # Check if Greeks graphs have data
        graphs = ['greeks-delta-chart', 'greeks-gamma-chart', 'greeks-theta-chart', 'greeks-vega-chart']
        for graph_id in graphs:
            try:
                graph_data = page.evaluate(f'''
                    () => {{
                        const elem = document.getElementById('{graph_id}');
                        if (elem && elem.data) {{
                            return {{ hasData: elem.data.length > 0, dataLength: elem.data.length }};
                        }}
                        return {{ hasData: false, dataLength: 0 }};
                    }}
                ''')
                status_symbol = '✅' if graph_data['hasData'] else '❌'
                print(f"  {status_symbol} {graph_id}: {graph_data}")
            except Exception as e:
                print(f"  ❌ {graph_id}: Error - {e}")
        
        print("\n🔍 Test complete. Check if callbacks worked despite missing DOM store...")
        time.sleep(5)
        browser.close()

if __name__ == '__main__':
    test_chain_load_via_callback()
