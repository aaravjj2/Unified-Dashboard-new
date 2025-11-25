"""
Comprehensive test for Market Trends and Research Lab tabs
with headed browser and screenshot capture
"""
import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime
import os

async def test_tabs_with_screenshots():
    """Test Market Trends and Research Lab tabs, capture screenshots"""
    
    # Create screenshots directory
    os.makedirs("screenshots", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    async with async_playwright() as p:
        # Launch headed browser for visual inspection
        browser = await p.chromium.launch(
            headless=False,
            args=['--start-maximized']
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        console_errors = []
        console_warnings = []
        
        # Capture console messages
        page.on("console", lambda msg: 
            console_errors.append(msg.text) if msg.type == "error" else
            console_warnings.append(msg.text) if msg.type == "warning" else None
        )
        
        print("="*80)
        print("COMPREHENSIVE TAB TEST WITH SCREENSHOTS")
        print("="*80)
        
        # Navigate to dashboard
        print("\n🌐 Navigating to dashboard...")
        await page.goto("http://127.0.0.1:8051", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(3000)
        
        # Capture initial page
        await page.screenshot(path=f"screenshots/{timestamp}_01_initial_load.png")
        print("📸 Screenshot: Initial page loaded")
        
        # Test Market Trends Tab
        print("\n" + "="*80)
        print("TESTING MARKET TRENDS TAB")
        print("="*80)
        
        try:
            # Find and click Market Trends tab using correct selector
            market_trends_tab = page.locator('.nav-item:has-text("Market Trends")').first
            
            if await market_trends_tab.is_visible(timeout=5000):
                print("✅ Market Trends tab is visible")
                await market_trends_tab.click()
                await page.wait_for_timeout(3000)
                print("✅ Clicked Market Trends tab")
                
                # Capture screenshot
                await page.screenshot(path=f"screenshots/{timestamp}_02_market_trends.png")
                print("📸 Screenshot: Market Trends tab")
                
                # Check for content
                market_content = page.locator('#market-trends')
                if await market_content.is_visible(timeout=2000):
                    print("✅ Market Trends content is visible")
                    
                    # Check for specific elements
                    sp500_card = page.locator('[data-testid="market-sp500-card"]')
                    if await sp500_card.is_visible(timeout=2000):
                        print("✅ S&P 500 card is visible")
                    else:
                        print("⚠️  S&P 500 card not found")
                    
                    # Check for news section
                    news_panel = page.locator('[data-testid="news-panel"]')
                    if await news_panel.is_visible(timeout=2000):
                        print("✅ News panel is visible")
                    else:
                        print("⚠️  News panel not found")
                else:
                    print("❌ Market Trends content container not found")
                    
            else:
                print("❌ Market Trends tab NOT visible")
                
        except Exception as e:
            print(f"❌ Error testing Market Trends: {e}")
            await page.screenshot(path=f"screenshots/{timestamp}_02_market_trends_ERROR.png")
        
        # Test Research Lab Tab
        print("\n" + "="*80)
        print("TESTING RESEARCH LAB TAB")
        print("="*80)
        
        try:
            # Find and click Research Lab tab using correct selector
            research_tab = page.locator('.nav-item:has-text("Research Lab")').first
            
            if await research_tab.is_visible(timeout=5000):
                print("✅ Research Lab tab is visible")
                await research_tab.click()
                await page.wait_for_timeout(3000)
                print("✅ Clicked Research Lab tab")
                
                # Capture screenshot
                await page.screenshot(path=f"screenshots/{timestamp}_03_research_lab.png")
                print("📸 Screenshot: Research Lab tab")
                
                # Check for content
                research_content = page.locator('#research-lab-container')
                if await research_content.is_visible(timeout=2000):
                    print("✅ Research Lab content container is visible")
                    
                    # Test subtabs
                    subtabs = [
                        ("Brief List", "research-lab-briefs"),
                        ("Create New", "research-lab-create"),
                        ("Analysis", "research-lab-analysis")
                    ]
                    
                    for subtab_name, subtab_id in subtabs:
                        print(f"\n  Testing subtab: {subtab_name}")
                        try:
                            subtab_button = page.locator(f'button:has-text("{subtab_name}")').first
                            if await subtab_button.is_visible(timeout=2000):
                                await subtab_button.click()
                                await page.wait_for_timeout(2000)
                                print(f"  ✅ Clicked {subtab_name} subtab")
                                
                                # Capture screenshot
                                screenshot_name = subtab_name.lower().replace(" ", "_")
                                await page.screenshot(
                                    path=f"screenshots/{timestamp}_04_research_{screenshot_name}.png"
                                )
                                print(f"  📸 Screenshot: {subtab_name} subtab")
                                
                                # Check for subtab content
                                subtab_content = page.locator(f'#{subtab_id}')
                                if await subtab_content.is_visible(timeout=1000):
                                    print(f"  ✅ {subtab_name} content is visible")
                                else:
                                    print(f"  ⚠️  {subtab_name} content not visible")
                            else:
                                print(f"  ⚠️  {subtab_name} subtab button not visible")
                        except Exception as e:
                            print(f"  ❌ Error with {subtab_name} subtab: {e}")
                else:
                    print("❌ Research Lab content container not found")
                    
            else:
                print("❌ Research Lab tab NOT visible")
                
        except Exception as e:
            print(f"❌ Error testing Research Lab: {e}")
            await page.screenshot(path=f"screenshots/{timestamp}_03_research_lab_ERROR.png")
        
        # Final console error check
        await page.wait_for_timeout(2000)
        
        print("\n" + "="*80)
        print("CONSOLE ERROR SUMMARY")
        print("="*80)
        print(f"Total Console Errors: {len(console_errors)}")
        print(f"Total Console Warnings: {len(console_warnings)}")
        
        if console_errors:
            # Count duplicate callback errors
            duplicate_errors = [e for e in console_errors if "Duplicate callback" in e]
            print(f"Duplicate Callback Errors: {len(duplicate_errors)}")
            
            # Show unique error patterns
            unique_errors = set(console_errors[:20])
            print("\nFirst 10 unique errors:")
            for i, err in enumerate(list(unique_errors)[:10], 1):
                print(f"  {i}. {err[:100]}")
        
        # Save report
        report = {
            "timestamp": timestamp,
            "console_errors": console_errors,
            "console_warnings": console_warnings,
            "error_count": len(console_errors),
            "warning_count": len(console_warnings)
        }
        
        with open(f"screenshots/test_report_{timestamp}.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Test report saved to: screenshots/test_report_{timestamp}.json")
        print(f"📁 Screenshots saved to: screenshots/ directory")
        
        # Keep browser open for manual inspection
        print("\n⏸️  Browser will remain open for 30 seconds for inspection...")
        await page.wait_for_timeout(30000)
        
        await browser.close()
        print("\n✅ Test complete!")

if __name__ == "__main__":
    asyncio.run(test_tabs_with_screenshots())
