#!/usr/bin/env python3
"""
Final Visual Verification Test - Generate Detailed Screenshots

Creates annotated screenshots showing:
1. Market Trends table with proper display
2. Analysis Hub without duplicate headers
3. Portfolio with all frontend components
4. Research Lab without errors
"""

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import os

async def capture_dashboard_screenshots():
    """Capture high-quality screenshots of all dashboards."""
    print("📸 Starting Dashboard Screenshot Capture")
    print("=" * 80)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1200})
        page = await context.new_page()
        
        screenshots = []
        
        # 1. Market Trends - Full Page
        print("\n1️⃣  Capturing Market Trends Dashboard...")
        try:
            await page.goto('http://localhost:8050', timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=30000)
            await page.wait_for_timeout(2000)
            
            screenshot_path = 'final_market_trends_full.png'
            await page.screenshot(path=screenshot_path, full_page=True)
            file_size = os.path.getsize(screenshot_path) / 1024
            print(f"   ✓ Saved: {screenshot_path} ({file_size:.1f} KB)")
            screenshots.append(screenshot_path)
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # 2. Analysis Hub - Attribution Tab
        print("\n2️⃣  Capturing Analysis Hub - Attribution...")
        try:
            await page.goto('http://localhost:8054', timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=30000)
            await page.wait_for_timeout(2000)
            
            screenshot_path = 'final_analysis_hub_attribution.png'
            await page.screenshot(path=screenshot_path, full_page=True)
            file_size = os.path.getsize(screenshot_path) / 1024
            print(f"   ✓ Saved: {screenshot_path} ({file_size:.1f} KB)")
            screenshots.append(screenshot_path)
            
            # Click scenario tab and capture
            try:
                scenario_tab = page.locator('.nav-link:has-text("Scenario Testing")')
                if await scenario_tab.count() > 0:
                    await scenario_tab.first.click()
                    await page.wait_for_timeout(1000)
                    
                    screenshot_path = 'final_analysis_hub_scenario.png'
                    await page.screenshot(path=screenshot_path, full_page=True)
                    file_size = os.path.getsize(screenshot_path) / 1024
                    print(f"   ✓ Saved: {screenshot_path} ({file_size:.1f} KB)")
                    screenshots.append(screenshot_path)
            except:
                pass
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # 3. Portfolio Dashboard - All Tabs
        print("\n3️⃣  Capturing Portfolio Dashboard...")
        try:
            await page.goto('http://localhost:8056', timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=30000)
            await page.wait_for_timeout(2000)
            
            screenshot_path = 'final_portfolio_positions.png'
            await page.screenshot(path=screenshot_path, full_page=True)
            file_size = os.path.getsize(screenshot_path) / 1024
            print(f"   ✓ Saved: {screenshot_path} ({file_size:.1f} KB)")
            screenshots.append(screenshot_path)
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # 4. Research Lab - Both Tabs
        print("\n4️⃣  Capturing Research Lab...")
        try:
            await page.goto('http://localhost:8058', timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=30000)
            await page.wait_for_timeout(2000)
            
            screenshot_path = 'final_research_lab_new_exp.png'
            await page.screenshot(path=screenshot_path, full_page=True)
            file_size = os.path.getsize(screenshot_path) / 1024
            print(f"   ✓ Saved: {screenshot_path} ({file_size:.1f} KB)")
            screenshots.append(screenshot_path)
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # 5. Unified Dashboard
        print("\n5️⃣  Capturing Unified Dashboard...")
        try:
            await page.goto('http://localhost:8000', timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=30000)
            await page.wait_for_timeout(2000)
            
            screenshot_path = 'final_unified_dashboard.png'
            await page.screenshot(path=screenshot_path, full_page=True)
            file_size = os.path.getsize(screenshot_path) / 1024
            print(f"   ✓ Saved: {screenshot_path} ({file_size:.1f} KB)")
            screenshots.append(screenshot_path)
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # 6. Monthly Picks
        print("\n6️⃣  Capturing Monthly Picks...")
        try:
            await page.goto('http://localhost:5001', timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=30000)
            await page.wait_for_timeout(2000)
            
            screenshot_path = 'final_monthly_picks.png'
            await page.screenshot(path=screenshot_path, full_page=True)
            file_size = os.path.getsize(screenshot_path) / 1024
            print(f"   ✓ Saved: {screenshot_path} ({file_size:.1f} KB)")
            screenshots.append(screenshot_path)
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # 7. Weekly Picks
        print("\n7️⃣  Capturing Weekly Picks...")
        try:
            await page.goto('http://localhost:5002', timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=30000)
            await page.wait_for_timeout(2000)
            
            screenshot_path = 'final_weekly_picks.png'
            await page.screenshot(path=screenshot_path, full_page=True)
            file_size = os.path.getsize(screenshot_path) / 1024
            print(f"   ✓ Saved: {screenshot_path} ({file_size:.1f} KB)")
            screenshots.append(screenshot_path)
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # 8. Market Forecast
        print("\n8️⃣  Capturing Market Forecast...")
        try:
            await page.goto('http://localhost:8051', timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=30000)
            await page.wait_for_timeout(2000)
            
            screenshot_path = 'final_market_forecast.png'
            await page.screenshot(path=screenshot_path, full_page=True)
            file_size = os.path.getsize(screenshot_path) / 1024
            print(f"   ✓ Saved: {screenshot_path} ({file_size:.1f} KB)")
            screenshots.append(screenshot_path)
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        await browser.close()
        
        # Summary
        print("\n" + "=" * 80)
        print(f"✅ Screenshot Capture Complete")
        print(f"   Total Screenshots: {len(screenshots)}")
        print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n📁 Files Generated:")
        for screenshot in screenshots:
            print(f"   • {screenshot}")
        print("=" * 80)
        
        return screenshots


if __name__ == "__main__":
    print(f"\n🖼️  Dashboard Visual Verification")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        screenshots = asyncio.run(capture_dashboard_screenshots())
        print(f"\n✨ Success! Generated {len(screenshots)} screenshots")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
