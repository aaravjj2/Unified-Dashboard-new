"""
Verify Command Center tab swap with detailed analysis
"""
import asyncio
from playwright.async_api import async_playwright

async def verify_tab_swap():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1200})
        
        # Clear ALL cache
        await context.clear_cookies()
        await context.clear_permissions()
        
        page = await context.new_page()
        
        print("=" * 80)
        print("VERIFYING COMMAND CENTER TAB SWAP")
        print("=" * 80)
        
        # Load with cache bypass
        print("\n[1/4] Loading dashboard with cache bypass...")
        await page.goto('http://localhost:8051?nocache=' + str(hash('verify')), timeout=15000, wait_until='networkidle')
        await page.wait_for_timeout(8000)
        
        # Get ALL page text
        page_text = await page.evaluate("() => document.body.innerText")
        
        # Check which Command Center is loaded
        has_quick_query = "Quick Query" in page_text
        has_performance_insights = "Performance Insights" in page_text
        has_portfolio_snapshot = "Portfolio Snapshot" in page_text
        
        has_portfolio_summary = "Portfolio Summary" in page_text
        has_market_overview = "Market Overview" in page_text
        has_watchlist = "Watchlist" in page_text
        
        print("\n[2/4] Analyzing which Command Center loaded...")
        print(f"\nOLD command_center_pkg indicators:")
        print(f"  - Quick Query: {has_quick_query}")
        print(f"  - Performance Insights: {has_performance_insights}")
        print(f"  - Portfolio Snapshot: {has_portfolio_snapshot}")
        
        print(f"\nNEW home.py indicators:")
        print(f"  - Portfolio Summary: {has_portfolio_summary}")
        print(f"  - Market Overview: {has_market_overview}")
        print(f"  - Watchlist: {has_watchlist}")
        
        # Determine which is loaded
        if has_quick_query or has_performance_insights:
            loaded_version = "command_center_pkg (OLD)"
        elif has_portfolio_summary or has_market_overview:
            loaded_version = "home.py (NEW)"
        else:
            loaded_version = "UNKNOWN"
        
        print(f"\n✓ Loaded version: {loaded_version}")
        
        # Capture screenshot
        print("\n[3/4] Capturing screenshot...")
        await page.screenshot(path='/home/aarav/unified-dashboard/VERIFY_command_center.png', full_page=True)
        
        # Check for errors
        has_errors = "Connection refused" in page_text or "[Errno 111]" in page_text or "Error:" in page_text
        print(f"✓ Has errors: {has_errors}")
        
        # Get first 2000 chars for analysis
        print("\n[4/4] Page content preview:")
        print(page_text[:2000])
        
        await browser.close()
        
        print("\n" + "=" * 80)
        print("VERIFICATION RESULT")
        print("=" * 80)
        print(f"Loaded: {loaded_version}")
        print(f"Expected: home.py (NEW)")
        print(f"Success: {loaded_version == 'home.py (NEW)'}")

if __name__ == '__main__':
    asyncio.run(verify_tab_swap())
