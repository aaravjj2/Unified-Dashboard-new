"""
Debug Portfolio Callbacks - Capture Screenshots and Analyze
"""
import asyncio
import json
from playwright.async_api import async_playwright
from datetime import datetime

async def debug_portfolio():
    """Capture screenshots and analyze callback behavior."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        # Track network requests
        requests = []
        responses = []
        console_logs = []
        errors = []
        
        page.on('request', lambda req: requests.append({
            'url': req.url,
            'method': req.method,
            'time': datetime.now().isoformat()
        }))
        
        page.on('response', lambda resp: responses.append({
            'url': resp.url,
            'status': resp.status,
            'time': datetime.now().isoformat()
        }))
        
        page.on('console', lambda msg: console_logs.append({
            'type': msg.type,
            'text': msg.text,
            'time': datetime.now().isoformat()
        }))
        
        page.on('pageerror', lambda err: errors.append({
            'error': str(err),
            'time': datetime.now().isoformat()
        }))
        
        print("🔍 Loading dashboard...")
        await page.goto('http://localhost:8056/')
        
        # Take initial screenshot
        await page.screenshot(path='_debug_step1_initial_load.png', full_page=True)
        print("✅ Screenshot 1: Initial load")
        
        # Wait for Dash to initialize
        await page.wait_for_timeout(3000)
        
        # Take screenshot after Dash initialization
        await page.screenshot(path='_debug_step2_after_dash_init.png', full_page=True)
        print("✅ Screenshot 2: After Dash init")
        
        # Check for portfolio-value element
        portfolio_value = await page.query_selector('#portfolio-value')
        if portfolio_value:
            value_text = await portfolio_value.inner_text()
            print(f"📊 Portfolio Value: {value_text}")
        else:
            print("❌ Portfolio value element not found!")
        
        # Check for portfolio-data-store
        data_store = await page.query_selector('#portfolio-data-store')
        if data_store:
            print("✅ Portfolio data store found")
            # Try to get its content
            store_content = await page.evaluate('() => document.getElementById("portfolio-data-store").textContent')
            print(f"📦 Store content length: {len(store_content) if store_content else 0}")
        else:
            print("❌ Portfolio data store not found!")
        
        # Wait a bit more
        await page.wait_for_timeout(5000)
        
        # Click refresh button
        print("🔄 Clicking refresh button...")
        refresh_btn = await page.query_selector('#portfolio-refresh-btn')
        if refresh_btn:
            await refresh_btn.click()
            await page.wait_for_timeout(2000)
            await page.screenshot(path='_debug_step3_after_refresh.png', full_page=True)
            print("✅ Screenshot 3: After refresh click")
        else:
            print("❌ Refresh button not found!")
        
        # Check value again
        if portfolio_value:
            value_text = await portfolio_value.inner_text()
            print(f"📊 Portfolio Value after refresh: {value_text}")
        
        # Filter for Dash callback requests
        dash_callbacks = [r for r in requests if '_dash-update-component' in r['url']]
        print(f"\n📡 Total requests: {len(requests)}")
        print(f"📡 Dash callback requests: {len(dash_callbacks)}")
        
        # Check for errors
        print(f"\n❌ Console errors: {len([log for log in console_logs if log['type'] == 'error'])}")
        print(f"❌ Page errors: {len(errors)}")
        
        # Print console errors
        for log in console_logs:
            if log['type'] == 'error':
                print(f"  - {log['text']}")
        
        for err in errors:
            print(f"  - {err['error']}")
        
        # Save detailed logs
        with open('_debug_network_log.json', 'w') as f:
            json.dump({
                'requests': requests[-50:],  # Last 50 requests
                'responses': responses[-50:],
                'console_logs': console_logs,
                'errors': errors,
                'dash_callbacks': dash_callbacks
            }, f, indent=2)
        
        print("\n✅ Debug logs saved to _debug_network_log.json")
        print("✅ Screenshots saved: _debug_step1_initial_load.png, _debug_step2_after_dash_init.png, _debug_step3_after_refresh.png")
        
        # Keep browser open for manual inspection
        print("\n⏸️  Browser will stay open for 30 seconds for manual inspection...")
        await page.wait_for_timeout(30000)
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(debug_portfolio())
