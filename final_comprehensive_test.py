"""
Final comprehensive test with extended wait times and better selectors
Tests Market Trends and Research Lab with screenshots
"""
import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime
import os

async def final_comprehensive_test():
    os.makedirs("screenshots/final", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--start-maximized'])
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        console_errors = []
        page.on("console", lambda msg: 
            console_errors.append(msg.text) if msg.type == "error" else None
        )
        
        print("="*80)
        print("FINAL COMPREHENSIVE TEST")
        print("="*80)
        
        await page.goto("http://127.0.0.1:8051", wait_until="networkidle")
        await page.wait_for_timeout(5000)
        
        await page.screenshot(path=f"screenshots/final/{timestamp}_00_initial.png", full_page=True)
        print("📸 Initial load")
        
        # Test Market Trends
        print("\n" + "="*80)
        print("MARKET TRENDS TAB")
        print("="*80)
        
        mt_tab = page.locator('.nav-item', has_text="Market Trends").first
        if await mt_tab.is_visible(timeout=3000):
            await mt_tab.click()
            print("✅ Clicked Market Trends tab")
            await page.wait_for_timeout(5000)
            
            await page.screenshot(path=f"screenshots/final/{timestamp}_01_market_trends.png", full_page=True)
            print("📸 Market Trends screenshot")
            
            # Check for any visible content
            visible_divs = await page.locator('div:visible').count()
            print(f"✅ {visible_divs} visible div elements on page")
            
            # Try to find specific market trends elements
            tickers_input = page.locator('#tickers-input')
            if await tickers_input.is_visible(timeout=2000):
                print("✅ Found tickers input field")
            else:
                print("⚠️  Tickers input not visible")
            
            run_btn = page.locator('#run-btn')
            if await run_btn.is_visible(timeout=2000):
                print("✅ Found Run Analysis button")
            else:
                print("⚠️  Run button not visible")
        else:
            print("❌ Market Trends tab not found")
        
        # Test Research Lab
        print("\n" + "="*80)
        print("RESEARCH LAB TAB")
        print("="*80)
        
        rl_tab = page.locator('.nav-item', has_text="Research Lab").first
        if await rl_tab.is_visible(timeout=3000):
            await rl_tab.click()
            print("✅ Clicked Research Lab tab")
            await page.wait_for_timeout(5000)
            
            await page.screenshot(path=f"screenshots/final/{timestamp}_02_research_lab.png", full_page=True)
            print("📸 Research Lab screenshot")
            
            # Check for subtabs
            subtab_selectors = [
                ("Brief List", "text=Brief List"),
                ("Create New", "text=Create New"),
                ("Analysis", "text=Analysis")
            ]
            
            for name, selector in subtab_selectors:
                try:
                    subtab = page.locator(selector).first
                    if await subtab.is_visible(timeout=1000):
                        print(f"✅ Found {name} subtab")
                        await subtab.click()
                        await page.wait_for_timeout(2000)
                        
                        screenshot_name = name.lower().replace(" ", "_")
                        await page.screenshot(
                            path=f"screenshots/final/{timestamp}_03_rl_{screenshot_name}.png",
                            full_page=True
                        )
                        print(f"📸 {name} screenshot")
                    else:
                        print(f"⚠️  {name} subtab not visible")
                except Exception as e:
                    print(f"❌ Error with {name}: {e}")
        else:
            print("❌ Research Lab tab not found")
        
        # Error summary
        await page.wait_for_timeout(3000)
        
        duplicate_errors = [e for e in console_errors if "Duplicate callback" in e]
        
        print("\n" + "="*80)
        print(f"CONSOLE ERROR SUMMARY")
        print("="*80)
        print(f"Total Errors: {len(console_errors)}")
        print(f"Duplicate Callback Errors: {len(duplicate_errors)}")
        
        # Save report
        report = {
            "timestamp": timestamp,
            "total_errors": len(console_errors),
            "duplicate_errors": len(duplicate_errors),
            "console_errors": console_errors[:50]  # First 50
        }
        
        with open(f"screenshots/final/report_{timestamp}.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Report saved: screenshots/final/report_{timestamp}.json")
        print(f"📁 Screenshots: screenshots/final/")
        
        print("\n⏸️  Browser open for 45s inspection...")
        await page.wait_for_timeout(45000)
        
        await browser.close()
        print("\n✅ Test complete!")
        
        return {
            "total_errors": len(console_errors),
            "duplicate_errors": len(duplicate_errors)
        }

if __name__ == "__main__":
    result = asyncio.run(final_comprehensive_test())
    print(f"\nFINAL RESULT: {result['duplicate_errors']} duplicate callback errors remain")
