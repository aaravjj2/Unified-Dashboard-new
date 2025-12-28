"""
Capture Alpaca Options Lab baseline screenshot for visual regression.
Usage:
  python scripts/capture_alpaca_baseline.py --url http://localhost:8051 --output screenshots/baseline/alpaca_table.png

This script uses Playwright to open the dashboard, navigate to Options Lab, load SPY, wait, and capture a screenshot.
"""

import argparse
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

SCREENSHOT_DIR = Path("screenshots/baseline")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

async def capture(url: str, output: str, headless: bool = True):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(2000)

        # Navigate to Options Lab
        try:
            await page.click('text=💹 Options Lab', timeout=8000)
        except Exception:
            try:
                await page.click('text=Options Lab', timeout=8000)
            except Exception:
                print('Could not navigate to Options Lab tab')

        await page.wait_for_timeout(1500)

        # Populate ticker and load chain
        try:
            ticker = await page.query_selector('#alpaca-ticker-input')
            if ticker:
                await ticker.fill('SPY')
        except Exception:
            pass

        try:
            load_btn = await page.query_selector('#alpaca-load-button')
            if load_btn:
                await load_btn.click()
        except Exception:
            pass

        # Wait longer for Alpaca data to load
        await page.wait_for_timeout(7000)

        # Try to focus table container
        try:
            table = await page.query_selector('#alpaca-table-container')
            if table:
                await table.scroll_into_view_if_needed()
        except Exception:
            pass

        out_path = Path(output)
        await page.screenshot(path=out_path, full_page=True)
        print(f"Saved baseline screenshot to {out_path}")
        await browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://localhost:8051')
    parser.add_argument('--output', default=str(SCREENSHOT_DIR / 'alpaca_table.png'))
    parser.add_argument('--headless', action='store_true')
    args = parser.parse_args()

    asyncio.run(capture(args.url, args.output, headless=args.headless))
