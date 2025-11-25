#!/usr/bin/env python3
"""
Simple snapshot test - just capture screenshots of the dashboard
No clicking, just load and capture
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def capture_dashboard_snapshot(url="http://localhost:8000"):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path(f'outputs/snapshot_test_{timestamp}')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Non-headless to see what's happening
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        logger.info(f"Loading {url}...")
        await page.goto(url, timeout=60000, wait_until='networkidle')
        await asyncio.sleep(5)  # Wait for tabs to render
        
        # Capture initial state
        screenshot_path = output_dir / "dashboard_initial.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        logger.info(f"✓ Saved screenshot: {screenshot_path}")
        
        # Get page HTML for inspection
        html_path = output_dir / "dashboard.html"
        content = await page.content()
        html_path.write_text(content)
        logger.info(f"✓ Saved HTML: {html_path}")
        
        # Try to find tabs
        tabs = await page.query_selector_all('.nav-link')
        logger.info(f"Found {len(tabs)} .nav-link elements")
        
        for i, tab in enumerate(tabs):
            try:
                text = await tab.inner_text()
                logger.info(f"  Tab {i}: {text}")
            except:
                pass
        
        await browser.close()
        logger.info(f"✅ Test complete! Output: {output_dir}")

if __name__ == '__main__':
    asyncio.run(capture_dashboard_snapshot())
