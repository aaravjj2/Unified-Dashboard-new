#!/usr/bin/env python3
"""
Simple test: Click Options Lab → Load Chain → Check if data appears
"""
import time
from playwright.sync_api import sync_playwright

PORT = 8050
URL = f"http://localhost:{PORT}"

print("=" * 80)
print("GREEKS SIMPLE LOAD TEST")
print("=" * 80)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print(f"✓ Navigating to {URL}")
    page.goto(URL, wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)
    
    print("✓ Clicking Options Lab tab...")
    page.click("text=💹 Options Lab")
    time.sleep(3)
    
    print("✓ Looking for Chain Viewer...")
    # The tab is already active by default, no need to click
    # But let's verify it's there
    chain_tab = page.query_selector("#options-chain-tab")
    if chain_tab:
        print("   ✓ Chain Viewer tab found (already active)")
    else:
        print("   ⚠️ Chain Viewer tab not found")
    
    print("✓ Typing SPY in ticker input...")
    ticker_input = page.query_selector("#options-ticker-input")
    if ticker_input:
        ticker_input.fill("SPY")
        time.sleep(1)
    else:
        print("   ⚠️ Ticker input not found")
    
    print("✓ Clicking Load Chain button...")
    load_btn = page.query_selector("#options-load-btn")
    if load_btn:
        load_btn.click()
        print("   Waiting 30 seconds for data to load...")
        time.sleep(30)
    else:
        print("   ⚠️ Load button not found")
    
    # Check store
    store_data = page.evaluate("""
        () => {
            const store = document.getElementById('options-chain-store');
            if (store && store.textContent) {
                try {
                    const data = JSON.parse(store.textContent);
                    return {
                        has_data: data && Object.keys(data).length > 0,
                        keys: Object.keys(data || {})
                    };
                } catch (e) {
                    return { error: e.message };
                }
            }
            return { has_data: false };
        }
    """)
    
    print(f"\n📦 Chain Store: {store_data}")
    
    # Check Greeks tab
    print("\n✓ Clicking Greeks tab...")
    greeks_tab = page.query_selector("#options-greeks-tab")
    if greeks_tab:
        # Click the actual nav-link inside the tab container
        page.click("#options-greeks-tab .nav-link, #options-greeks-tab")
        time.sleep(3)
        print("   ✓ Greeks tab clicked")
    else:
        print("   ⚠️ Greeks tab not found")
    
    # Check graphs
    for graph_id in ['greeks-delta-chart', 'greeks-gamma-chart']:
        result = page.evaluate(f"""
            () => {{
                const el = document.getElementById('{graph_id}');
                if (!el) return {{ exists: false }};
                
                return {{
                    exists: true,
                    has_plotly_data: el.data && el.data.length > 0,
                    trace_count: el.data ? el.data.length : 0
                }};
            }}
        """)
        print(f"   {graph_id}: {result}")
    
    print("\n✅ Test complete")
    browser.close()
