#!/usr/bin/env python3
"""
Portfolio Subtabs Validation Script
Validates all 5 Portfolio subtabs using Playwright automation.

Subtabs:
1. Positions
2. Order History
3. Analytics
4. Factor Exposure
5. Optimization

Validation checks:
- Subtab content renders (not empty)
- DataTables exist where expected
- Graphs/charts render
- Callbacks execute
- No console errors
- Screenshot capture
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://127.0.0.1:8050/"
ARTIFACTS_DIR = Path("tests/logs/portfolio_validation")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

SUBTABS = [
    {"id": "positions", "name": "Positions", "selector": "text=Positions"},
    {"id": "orders", "name": "Order History", "selector": "text=Order History"},
    {"id": "analytics", "name": "Analytics", "selector": "text=Analytics"},
    {"id": "factors", "name": "Factor Exposure", "selector": "text=Factor Exposure"},
    {"id": "optimization", "name": "Optimization", "selector": "text=Optimization"}
]


async def check_server_health():
    """Verify server is responding."""
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(BASE_URL, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    logger.info("✅ Server is healthy")
                    return True
                else:
                    logger.error(f"❌ Server returned status {resp.status}")
                    return False
    except Exception as e:
        logger.error(f"❌ Server health check failed: {e}")
        return False


async def validate_subtab(page, subtab_info, iteration=1):
    """
    Validate a single portfolio subtab.
    
    Returns dict with validation results.
    """
    subtab_id = subtab_info["id"]
    subtab_name = subtab_info["name"]
    selector = subtab_info["selector"]
    
    results = {
        "subtab_id": subtab_id,
        "subtab_name": subtab_name,
        "timestamp": datetime.now().isoformat(),
        "iteration": iteration,
        "status": "PENDING",
        "checks": {}
    }
    
    logger.info(f"\n{'='*80}")
    logger.info(f"VALIDATING SUBTAB: {subtab_name} (iteration {iteration})")
    logger.info(f"{'='*80}")
    
    try:
        # Navigate to home page
        logger.info(f"📍 Navigating to {BASE_URL}...")
        await page.goto(BASE_URL, wait_until='networkidle', timeout=30000)
        await asyncio.sleep(2)  # Wait for initial render
        
        # Click Portfolio tab
        logger.info("🖱️  Clicking Portfolio tab...")
        try:
            portfolio_tab = page.locator("text=Portfolio").first
            await portfolio_tab.click(timeout=5000)
            await asyncio.sleep(1)
            results["checks"]["portfolio_tab_click"] = True
        except Exception as e:
            logger.error(f"❌ Failed to click Portfolio tab: {e}")
            results["checks"]["portfolio_tab_click"] = False
            results["status"] = "FAILED"
            return results
        
        # Click subtab
        logger.info(f"🖱️  Clicking {subtab_name} subtab...")
        try:
            subtab = page.locator(selector).first
            await subtab.click(timeout=5000)
            await asyncio.sleep(3)  # Wait for content to load
            results["checks"]["subtab_click"] = True
        except Exception as e:
            logger.error(f"❌ Failed to click {subtab_name} subtab: {e}")
            results["checks"]["subtab_click"] = False
            results["status"] = "FAILED"
            return results
        
        # Check for content visibility
        logger.info(f"🔍 Checking content visibility for {subtab_name}...")
        
        # Check for common elements
        checks = {
            "has_datatable": False,
            "has_graph": False,
            "has_content": False,
            "is_empty": True,
            "still_loading": False,  # Initialize to avoid KeyError
            "no_data_message": False  # Initialize to avoid KeyError
        }
        
        # Look for DataTables
        datatables = await page.locator('.dash-table').count()
        if datatables > 0:
            logger.info(f"✅ Found {datatables} DataTable(s)")
            checks["has_datatable"] = True
            checks["is_empty"] = False
        
        # Look for graphs
        graphs = await page.locator('.plotly').count()
        if graphs > 0:
            logger.info(f"✅ Found {graphs} Plotly graph(s)")
            checks["has_graph"] = True
            checks["is_empty"] = False
        
        # Check for any non-empty divs
        content_divs = await page.locator('div:not(:empty)').count()
        if content_divs > 10:  # More than basic layout divs
            checks["has_content"] = True
            checks["is_empty"] = False
        
        # Get text content to detect "Loading...", "No data", etc.
        page_text = await page.inner_text('body')
        if "Loading" in page_text:
            logger.warning(f"⚠️  Page contains 'Loading...' text")
            checks["still_loading"] = True
        
        if "No data" in page_text or "No positions" in page_text:
            logger.warning(f"⚠️  Page contains 'No data' message")
            checks["no_data_message"] = True
        
        results["checks"].update(checks)
        
        # Capture screenshot
        screenshot_path = ARTIFACTS_DIR / f"{subtab_id}_iteration{iteration}.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        logger.info(f"📸 Screenshot saved: {screenshot_path}")
        results["screenshot"] = str(screenshot_path)
        
        # Check console errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        await asyncio.sleep(1)  # Collect any async errors
        
        if console_errors:
            logger.warning(f"⚠️  Console errors detected: {len(console_errors)}")
            results["console_errors"] = console_errors[:10]  # First 10
        else:
            logger.info("✅ No console errors")
            results["console_errors"] = []
        
        # Determine overall status
        if checks["is_empty"]:
            results["status"] = "FAILED_EMPTY"
            logger.error(f"❌ {subtab_name}: Content is EMPTY")
        elif checks["still_loading"]:
            results["status"] = "FAILED_LOADING"
            logger.warning(f"⚠️  {subtab_name}: Still showing 'Loading...'")
        elif checks["no_data_message"]:
            results["status"] = "WARNING_NO_DATA"
            logger.warning(f"⚠️  {subtab_name}: Shows 'No data' message")
        elif checks["has_datatable"] or checks["has_graph"]:
            results["status"] = "SUCCESS"
            logger.info(f"✅ {subtab_name}: Content rendered successfully!")
        else:
            results["status"] = "PARTIAL"
            logger.warning(f"⚠️  {subtab_name}: Some content exists but no tables/graphs detected")
        
    except PlaywrightTimeout as e:
        logger.error(f"❌ Timeout validating {subtab_name}: {e}")
        results["status"] = "TIMEOUT"
        results["error"] = str(e)
    except Exception as e:
        logger.error(f"❌ Error validating {subtab_name}: {e}")
        results["status"] = "ERROR"
        results["error"] = str(e)
    
    return results


async def validate_all_subtabs(iteration=1):
    """Validate all 5 portfolio subtabs."""
    logger.info(f"\n🚀 Starting Portfolio Subtabs Validation (Iteration {iteration})")
    logger.info(f"📁 Artifacts directory: {ARTIFACTS_DIR}")
    
    # Check server health
    if not await check_server_health():
        logger.error("❌ Server is not responding. Aborting validation.")
        return None
    
    all_results = {
        "iteration": iteration,
        "timestamp": datetime.now().isoformat(),
        "subtabs": []
    }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        for subtab_info in SUBTABS:
            result = await validate_subtab(page, subtab_info, iteration)
            all_results["subtabs"].append(result)
        
        await browser.close()
    
    # Generate summary
    success_count = sum(1 for r in all_results["subtabs"] if r["status"] == "SUCCESS")
    total_count = len(all_results["subtabs"])
    
    all_results["summary"] = {
        "total": total_count,
        "success": success_count,
        "failed": total_count - success_count,
        "success_rate": f"{(success_count/total_count)*100:.1f}%"
    }
    
    logger.info(f"\n{'='*80}")
    logger.info(f"VALIDATION SUMMARY (Iteration {iteration})")
    logger.info(f"{'='*80}")
    logger.info(f"Total subtabs: {total_count}")
    logger.info(f"✅ Success: {success_count}")
    logger.info(f"❌ Failed: {total_count - success_count}")
    logger.info(f"Success rate: {all_results['summary']['success_rate']}")
    
    for result in all_results["subtabs"]:
        status_emoji = "✅" if result["status"] == "SUCCESS" else "❌"
        logger.info(f"{status_emoji} {result['subtab_name']}: {result['status']}")
    
    # Save results
    results_file = ARTIFACTS_DIR / f"validation_results_iteration{iteration}.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    logger.info(f"\n📄 Results saved to: {results_file}")
    
    return all_results


async def main():
    """Main entry point."""
    results = await validate_all_subtabs(iteration=1)
    
    if results:
        # Exit code: 0 if all success, 1 otherwise
        success_count = results["summary"]["success"]
        total_count = results["summary"]["total"]
        
        if success_count == total_count:
            logger.info("\n🎉 ALL SUBTABS VALIDATED SUCCESSFULLY!")
            exit(0)
        else:
            logger.warning(f"\n⚠️  VALIDATION INCOMPLETE: {success_count}/{total_count} passed")
            exit(1)
    else:
        logger.error("\n❌ VALIDATION FAILED")
        exit(2)


if __name__ == "__main__":
    asyncio.run(main())
