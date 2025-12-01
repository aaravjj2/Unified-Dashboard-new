"""Quick test to check Strategy Lab Run Backtest button functionality"""
import asyncio
from playwright.async_api import async_playwright
import time

DASHBOARD_URL = "http://localhost:8050"

async def test_backtest():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print(f"🌐 Navigating to {DASHBOARD_URL}...")
        await page.goto(DASHBOARD_URL, wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(10000)  # Wait for initial load
        
        # Navigate to Strategy Lab tab
        print("📊 Looking for Strategy Lab tab...")
        try:
            await page.click('text=⚡ Strategy Lab', timeout=10000)
            print("✅ Clicked Strategy Lab tab")
        except Exception as e:
            print(f"❌ Failed to find Strategy Lab tab: {e}")
            await browser.close()
            return
        
        await page.wait_for_timeout(5000)
        
        # Navigate to Execute subtab
        print("🎯 Looking for Execute subtab...")
        try:
            await page.click('text=▶️ Execute', timeout=10000)
            print("✅ Clicked Execute subtab")
        except Exception as e:
            print(f"❌ Failed to find Execute subtab: {e}")
            await browser.close()
            return
        
        await page.wait_for_timeout(3000)
        
        # Look for Run Backtest button
        print("🔍 Looking for Run Backtest button...")
        try:
            button = page.locator('button:has-text("Run Backtest")')
            count = await button.count()
            print(f"✅ Found {count} Run Backtest button(s)")
            
            if count > 0:
                is_visible = await button.first.is_visible()
                is_enabled = await button.first.is_enabled()
                print(f"   Visible: {is_visible}, Enabled: {is_enabled}")
                
                # Try to click it
                if is_visible and is_enabled:
                    print("🖱️ Attempting to click Run Backtest...")
                    await button.first.click()
                    await page.wait_for_timeout(3000)
                    print("✅ Clicked Run Backtest button")
                else:
                    print("⚠️ Button not clickable (might need validation first)")
        except Exception as e:
            print(f"❌ Error with Run Backtest button: {e}")
        
        # Check for any error messages
        print("🔍 Checking for error messages...")
        try:
            errors = await page.locator('.alert-danger, .alert-warning').all_text_contents()
            if errors:
                print(f"⚠️ Found alerts: {errors}")
            else:
                print("✅ No error alerts found")
        except:
            pass
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_backtest())
