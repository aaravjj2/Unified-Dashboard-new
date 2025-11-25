#!/usr/bin/env python3
"""
Phase 20A UI Clicker Test - Azure ML Lab
Quick Playwright test to click Run Prediction and capture what happens
"""
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime

DASHBOARD_URL = "http://localhost:8050"

async def main():
    print("\n🚀 Phase 20A UI Clicker Test - Azure ML Lab\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # visible browser
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            # Navigate to dashboard
            print(f"🌐 Loading {DASHBOARD_URL}...")
            await page.goto(DASHBOARD_URL, wait_until='networkidle', timeout=60000)
            await page.wait_for_timeout(3000)
            
            # Screenshot 1: Homepage
            await page.screenshot(path='screenshot_1_home.png', full_page=True)
            print("📸 Screenshot 1: Homepage")
            
            # Find and click Azure ML Lab tab
            print("\n🔍 Looking for Azure ML Lab tab...")
            try:
                # Try multiple selectors
                selectors = [
                    'text=Azure ML Lab',
                    'text=🤖 Azure ML Lab',
                    '[data-tab="azure_ml_lab"]',
                    'a:has-text("Azure ML")',
                    '.nav-link:has-text("ML")'
                ]
                
                clicked = False
                for selector in selectors:
                    try:
                        print(f"   Trying selector: {selector}")
                        await page.click(selector, timeout=3000)
                        clicked = True
                        print(f"   ✅ Clicked with: {selector}")
                        break
                    except:
                        continue
                
                if not clicked:
                    print("   ❌ Could not find Azure ML Lab tab")
                    await page.screenshot(path='screenshot_ERROR_no_tab.png', full_page=True)
                    return
                
                await page.wait_for_timeout(5000)
                
                # Screenshot 2: Azure ML Lab tab
                await page.screenshot(path='screenshot_2_azure_ml_lab.png', full_page=True)
                print("📸 Screenshot 2: Azure ML Lab tab")
                
            except Exception as e:
                print(f"   ❌ Tab navigation failed: {e}")
                await page.screenshot(path='screenshot_ERROR_tab_nav.png', full_page=True)
                return
            
            # Find and click Run Prediction button
            print("\n🔍 Looking for Run Prediction button...")
            try:
                button_selectors = [
                    'button:has-text("Run Prediction")',
                    'button:has-text("Prediction")',
                    '[id*="run-prediction"]',
                    '[id*="predict"]'
                ]
                
                clicked = False
                for selector in button_selectors:
                    try:
                        print(f"   Trying selector: {selector}")
                        await page.click(selector, timeout=3000)
                        clicked = True
                        print(f"   ✅ Clicked with: {selector}")
                        break
                    except:
                        continue
                
                if not clicked:
                    print("   ❌ Could not find Run Prediction button")
                    # Save page content to check structure
                    content = await page.content()
                    with open('page_content_no_button.html', 'w') as f:
                        f.write(content)
                    print("   💾 Saved page HTML to page_content_no_button.html")
                    await page.screenshot(path='screenshot_ERROR_no_button.png', full_page=True)
                    return
                
                print("\n⏳ Waiting for prediction to complete (15 seconds)...")
                await page.wait_for_timeout(15000)
                
                # Screenshot 3: After Run Prediction
                await page.screenshot(path='screenshot_3_after_prediction.png', full_page=True)
                print("📸 Screenshot 3: After Run Prediction")
                
            except Exception as e:
                print(f"   ❌ Button click failed: {e}")
                await page.screenshot(path='screenshot_ERROR_button_click.png', full_page=True)
                return
            
            # Check for prediction results
            print("\n🔍 Checking for prediction results...")
            try:
                page_text = await page.inner_text('body')
                
                # Check for Phase 20A indicators
                has_phase20a = '🚀 PHASE 20A' in page_text or 'PHASE 20A' in page_text
                has_azure_ml = 'Azure ML' in page_text
                has_database = 'Saved to database' in page_text or 'run_id' in page_text
                has_mock = 'Phase 17B Mock' in page_text or 'mock predictions' in page_text.lower()
                
                print(f"\n📊 Results Analysis:")
                print(f"   Phase 20A indicators: {'✅' if has_phase20a else '❌'}")
                print(f"   Azure ML mention: {'✅' if has_azure_ml else '❌'}")
                print(f"   Database save: {'✅' if has_database else '❌'}")
                print(f"   Still using mock: {'❌ PROBLEM!' if has_mock else '✅'}")
                
                # Check predictions table
                tables = await page.query_selector_all('table')
                if tables:
                    print(f"\n   Found {len(tables)} table(s) on page")
                    for i, table in enumerate(tables):
                        rows = await table.query_selector_all('tbody tr')
                        print(f"   Table {i+1}: {len(rows)} rows")
                else:
                    print(f"\n   ❌ No tables found")
                
                # Save page content for inspection
                content = await page.content()
                with open('page_content_after_prediction.html', 'w') as f:
                    f.write(content)
                print(f"\n💾 Saved full page HTML to page_content_after_prediction.html")
                
            except Exception as e:
                print(f"   ❌ Results check failed: {e}")
            
            # Try clicking Insights button
            print("\n🔍 Testing Insights button...")
            try:
                insights_selectors = [
                    'button:has-text("Model Insights")',
                    'button:has-text("Insights")',
                    '[id*="insights"]'
                ]
                
                clicked = False
                for selector in insights_selectors:
                    try:
                        await page.click(selector, timeout=3000)
                        clicked = True
                        print(f"   ✅ Clicked Insights button")
                        break
                    except:
                        continue
                
                if clicked:
                    await page.wait_for_timeout(3000)
                    await page.screenshot(path='screenshot_4_insights.png', full_page=True)
                    print("📸 Screenshot 4: After Insights click")
                else:
                    print("   ⚠️  Insights button not found or not clickable")
                
            except Exception as e:
                print(f"   ⚠️  Insights test skipped: {e}")
            
            # Try clicking Metrics button
            print("\n🔍 Testing Metrics button...")
            try:
                metrics_selectors = [
                    'button:has-text("Model Metrics")',
                    'button:has-text("Metrics")',
                    '[id*="metrics"]'
                ]
                
                clicked = False
                for selector in metrics_selectors:
                    try:
                        await page.click(selector, timeout=3000)
                        clicked = True
                        print(f"   ✅ Clicked Metrics button")
                        break
                    except:
                        continue
                
                if clicked:
                    await page.wait_for_timeout(3000)
                    await page.screenshot(path='screenshot_5_metrics.png', full_page=True)
                    print("📸 Screenshot 5: After Metrics click")
                else:
                    print("   ⚠️  Metrics button not found or not clickable")
                
            except Exception as e:
                print(f"   ⚠️  Metrics test skipped: {e}")
            
            # Final wait for inspection
            print("\n⏸️  Browser will stay open for 10 seconds for manual inspection...")
            await page.wait_for_timeout(10000)
            
        finally:
            await browser.close()
    
    print("\n✅ Test Complete - Check screenshots and HTML files\n")

if __name__ == "__main__":
    asyncio.run(main())
