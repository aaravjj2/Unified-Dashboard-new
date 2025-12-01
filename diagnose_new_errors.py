"""
Diagnostic script to capture and analyze console errors
"""
import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime

async def diagnose_errors():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        console_errors = []
        console_warnings = []
        page_errors = []
        
        # Capture console messages
        page.on("console", lambda msg: 
            console_errors.append({
                "type": msg.type,
                "text": msg.text,
                "location": msg.location
            }) if msg.type == "error" else
            console_warnings.append({
                "type": msg.type,
                "text": msg.text,
                "location": msg.location
            }) if msg.type == "warning" else None
        )
        
        # Capture page errors
        page.on("pageerror", lambda exc: 
            page_errors.append({
                "message": str(exc),
                "timestamp": datetime.now().isoformat()
            })
        )
        
        print("🌐 Navigating to dashboard...")
        await page.goto("http://127.0.0.1:8051", wait_until="networkidle", timeout=60000)
        
        print("⏳ Waiting for initial page load...")
        await page.wait_for_timeout(5000)
        
        # Click through tabs
        tabs = ["Market Trends", "Research Lab"]
        for tab_name in tabs:
            print(f"\n📑 Clicking {tab_name} tab...")
            try:
                tab_button = page.locator(f"button:has-text('{tab_name}')").first
                if await tab_button.is_visible():
                    await tab_button.click()
                    await page.wait_for_timeout(3000)
                    print(f"✅ {tab_name} tab clicked")
                else:
                    print(f"⚠️ {tab_name} tab not visible")
            except Exception as e:
                print(f"❌ Error clicking {tab_name}: {e}")
        
        # Wait a bit more to capture all errors
        await page.wait_for_timeout(5000)
        
        # Analysis
        print("\n" + "="*80)
        print(f"📊 DIAGNOSTIC RESULTS")
        print("="*80)
        print(f"Total Console Errors: {len(console_errors)}")
        print(f"Total Console Warnings: {len(console_warnings)}")
        print(f"Total Page Errors: {len(page_errors)}")
        
        # Show unique error patterns
        if console_errors:
            print("\n🔴 CONSOLE ERRORS (first 10 unique):")
            unique_errors = {}
            for err in console_errors:
                key = err["text"][:100]
                if key not in unique_errors:
                    unique_errors[key] = err
                    if len(unique_errors) <= 10:
                        print(f"  - {err['text'][:200]}")
        
        if page_errors:
            print("\n💥 PAGE ERRORS:")
            for err in page_errors[:10]:
                print(f"  - {err['message'][:200]}")
        
        # Save detailed report
        report = {
            "timestamp": datetime.now().isoformat(),
            "console_errors": console_errors,
            "console_warnings": console_warnings,
            "page_errors": page_errors,
            "summary": {
                "total_errors": len(console_errors),
                "total_warnings": len(console_warnings),
                "total_page_errors": len(page_errors)
            }
        }
        
        with open("error_diagnostic_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Detailed report saved to: error_diagnostic_report.json")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(diagnose_errors())
