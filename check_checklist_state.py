#!/usr/bin/env python3
"""Check actual checklist state in DOM"""
from playwright.sync_api import sync_playwright
import time
import json

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.goto("http://localhost:8050", timeout=30000)
        page.wait_for_load_state("networkidle")
        page.click("text=Market Forecast")
        time.sleep(2)
        
        # Get the actual React state of the checklist
        result = page.evaluate("""
            () => {
                // Dash stores component props in React fiber
                // Let's look for the actual checked values
                const checklist = document.getElementById('mf-model-checklist');
                if (!checklist) return {error: 'checklist not found'};
                
                // Get all label/input pairs
                const items = [];
                const labels = checklist.querySelectorAll('label');
                labels.forEach(label => {
                    const input = label.querySelector('input');
                    const text = label.textContent.trim();
                    items.push({
                        text: text.substring(0, 50),
                        checked: input ? input.checked : false,
                        value: input ? input.value : null
                    });
                });
                
                // Try to get React props
                let reactProps = null;
                try {
                    const key = Object.keys(checklist).find(k => k.startsWith('__reactInternalInstance') || k.startsWith('__reactFiber'));
                    if (key) {
                        const fiber = checklist[key];
                        if (fiber && fiber.memoizedProps) {
                            reactProps = {
                                value: fiber.memoizedProps.value,
                                options: fiber.memoizedProps.options?.map(o => o.value)
                            };
                        }
                    }
                } catch (e) {
                    reactProps = {error: e.message};
                }
                
                return {items, reactProps, html: checklist.innerHTML.substring(0, 500)};
            }
        """)
        
        print("📊 Checklist State:")
        print(json.dumps(result, indent=2, default=str))
        
        # Get button disabled state
        btn = page.evaluate("""
            () => {
                const btn = document.getElementById('mf-run-btn');
                return {
                    disabled: btn?.disabled,
                    style: btn?.getAttribute('style'),
                    className: btn?.className
                };
            }
        """)
        print(f"\n📊 Button state: {json.dumps(btn, indent=2)}")
        
        # Try clicking and watch network
        page.click("#mf-run-btn")
        print("\n🖱️ Clicked button, waiting 10s...")
        time.sleep(10)
        
        # Check if anything changed
        metrics = page.inner_text("#mf-model-metrics")
        print(f"\n📊 Metrics after click: {metrics[:100]}...")
        
        browser.close()

if __name__ == "__main__":
    main()
