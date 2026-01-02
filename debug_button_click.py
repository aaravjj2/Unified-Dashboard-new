#!/usr/bin/env python3
"""Debug: Check if button is clickable and what's blocking it"""
from playwright.sync_api import sync_playwright
import time

def main():
    print("=" * 60)
    print("DEBUG: BUTTON CLICKABILITY")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.goto("http://localhost:8050", timeout=30000)
        page.wait_for_load_state("networkidle")
        
        # Click Market Forecast tab
        page.click("text=Market Forecast")
        time.sleep(2)
        
        # Get button position and check what's at that position
        button_info = page.evaluate("""
            () => {
                const btn = document.getElementById('mf-run-btn');
                if (!btn) return {error: 'Button not found'};
                
                const rect = btn.getBoundingClientRect();
                const centerX = rect.left + rect.width / 2;
                const centerY = rect.top + rect.height / 2;
                
                // Check what element is at the center of the button
                const elementAtPoint = document.elementFromPoint(centerX, centerY);
                
                // Get computed styles
                const styles = window.getComputedStyle(btn);
                
                return {
                    buttonId: btn.id,
                    rect: {
                        top: rect.top,
                        left: rect.left,
                        width: rect.width,
                        height: rect.height
                    },
                    center: {x: centerX, y: centerY},
                    elementAtCenter: {
                        tagName: elementAtPoint?.tagName,
                        id: elementAtPoint?.id,
                        className: elementAtPoint?.className?.substring(0, 50),
                        isSameAsButton: elementAtPoint === btn || btn.contains(elementAtPoint)
                    },
                    styles: {
                        display: styles.display,
                        visibility: styles.visibility,
                        opacity: styles.opacity,
                        pointerEvents: styles.pointerEvents,
                        zIndex: styles.zIndex,
                        position: styles.position
                    },
                    parentVisibility: btn.offsetParent !== null,
                    isInViewport: rect.top >= 0 && rect.left >= 0 && 
                                  rect.bottom <= window.innerHeight && 
                                  rect.right <= window.innerWidth
                };
            }
        """)
        
        print("📊 Button Info:")
        import json
        print(json.dumps(button_info, indent=2))
        
        # Try scrolling to button first
        print("\n📜 Scrolling to button...")
        page.evaluate("document.getElementById('mf-run-btn').scrollIntoView({block: 'center'})")
        time.sleep(1)
        
        # Check again
        in_viewport = page.evaluate("""
            () => {
                const btn = document.getElementById('mf-run-btn');
                const rect = btn.getBoundingClientRect();
                return {
                    inViewport: rect.top >= 0 && rect.top < window.innerHeight,
                    newTop: rect.top
                };
            }
        """)
        print(f"📊 After scroll: {in_viewport}")
        
        # Try clicking with Playwright's built-in scroll
        print("\n🖱️ Clicking with scroll_into_view_if_needed...")
        page.locator("#mf-run-btn").scroll_into_view_if_needed()
        time.sleep(0.5)
        page.locator("#mf-run-btn").click()
        time.sleep(2)
        
        # Check n_clicks
        n_clicks = page.evaluate("""
            () => {
                const btn = document.getElementById('mf-run-btn');
                const key = Object.keys(btn).find(k => k.startsWith('__reactFiber'));
                if (key) {
                    let current = btn[key];
                    for (let i = 0; i < 10 && current; i++) {
                        if (current.memoizedProps) return current.memoizedProps.n_clicks;
                        current = current.return;
                    }
                }
                return null;
            }
        """)
        print(f"📊 n_clicks after scroll+click: {n_clicks}")
        
        # Check metrics
        metrics = page.inner_text("#mf-model-metrics")
        print(f"📊 Metrics: {metrics[:80]}...")
        
        browser.close()
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
