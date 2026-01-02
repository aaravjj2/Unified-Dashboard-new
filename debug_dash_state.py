#!/usr/bin/env python3
"""Debug: Check for JS errors and Dash state"""
from playwright.sync_api import sync_playwright
import time
import json

def main():
    print("=" * 60)
    print("DEBUG: JS ERRORS AND DASH STATE")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Capture console errors
        console_errors = []
        def on_console(msg):
            if msg.type == 'error':
                console_errors.append(msg.text)
        
        page.on('console', on_console)
        
        page.goto("http://localhost:8050", timeout=30000)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        print(f"📋 Console errors on load: {len(console_errors)}")
        for err in console_errors[:5]:
            print(f"   ❌ {err[:100]}")
        
        # Click Market Forecast tab
        page.click("text=Market Forecast")
        time.sleep(2)
        
        # Check Dash renderer state
        dash_state = page.evaluate("""
            () => {
                // Check if Dash renderer is properly initialized
                const result = {
                    hasRenderer: typeof window.dash_clientside !== 'undefined',
                    hasStore: typeof window.dash_clientside?.set_props !== 'undefined',
                    dashDependencies: window._dash_callback_map ? Object.keys(window._dash_callback_map).length : 0,
                };
                
                // Check button element
                const btn = document.getElementById('mf-run-btn');
                if (btn) {
                    result.buttonExists = true;
                    result.buttonDisabled = btn.disabled;
                    
                    // Check React fiber for n_clicks
                    const key = Object.keys(btn).find(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance'));
                    if (key) {
                        const fiber = btn[key];
                        result.hasReactFiber = true;
                        // Try to find props
                        let current = fiber;
                        for (let i = 0; i < 10 && current; i++) {
                            if (current.memoizedProps) {
                                result.nClicks = current.memoizedProps.n_clicks;
                                result.buttonId = current.memoizedProps.id;
                                break;
                            }
                            current = current.return;
                        }
                    }
                }
                
                return result;
            }
        """)
        
        print(f"\n📊 Dash State:")
        print(json.dumps(dash_state, indent=2))
        
        # Try clicking and check if n_clicks increments
        print("\n🖱️ Clicking button...")
        page.click("#mf-run-btn")
        time.sleep(1)
        
        # Check n_clicks after click
        n_clicks_after = page.evaluate("""
            () => {
                const btn = document.getElementById('mf-run-btn');
                const key = Object.keys(btn).find(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance'));
                if (key) {
                    let current = btn[key];
                    for (let i = 0; i < 10 && current; i++) {
                        if (current.memoizedProps) {
                            return current.memoizedProps.n_clicks;
                        }
                        current = current.return;
                    }
                }
                return null;
            }
        """)
        print(f"📊 n_clicks after click: {n_clicks_after}")
        
        # Check for new console errors
        print(f"\n📋 Console errors after click: {len(console_errors)}")
        for err in console_errors[5:10]:
            print(f"   ❌ {err[:100]}")
        
        browser.close()
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
