"""
Check Alpaca options table and RAG/FinGPT response.
Saves screenshots and compares Alpaca table to baseline.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from PIL import Image, ImageChops

BASELINE = Path('screenshots/baseline/alpaca_table.png')
OUT_DIR = Path('screenshots/check')
OUT_DIR.mkdir(parents=True, exist_ok=True)


async def run(url='http://localhost:8051', headless=True):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(1500)

        # Navigate to Options Lab
        try:
            await page.click('text=💹 Options Lab', timeout=8000)
        except Exception:
            await page.click('text=Options Lab', timeout=8000)
        await page.wait_for_timeout(1500)

        # Ensure header and table container are present (wait for table to be populated)
        header = await page.query_selector('#alpaca-header-container')
        # Wait up to 12s for the alpaca table container to appear
        table_container = None
        try:
            await page.wait_for_selector('#alpaca-table-container', timeout=12000)
            table_container = await page.query_selector('#alpaca-table-container')
        except Exception:
            # fallback to specific DataTable
            try:
                await page.wait_for_selector('#alpaca-options-table', timeout=2000)
                table_container = await page.query_selector('#alpaca-options-table')
            except Exception:
                table_container = None

        if header:
            header_text = await header.inner_text()
        else:
            header_text = ''

        print('Header text snippet:', header_text[:200])

        # Capture table screenshot
        table_path = OUT_DIR / 'alpaca_current.png'
        if table_container:
            await table_container.scroll_into_view_if_needed()
            await page.screenshot(path=str(table_path), clip=None, full_page=False)
            print('Saved table screenshot to', table_path)
        else:
            # fallback full page
            await page.screenshot(path=str(table_path), full_page=True)
            print('Table container not found; saved full page to', table_path)

        # Compare to baseline if exists
        if BASELINE.exists() and table_path.exists():
            im1 = Image.open(BASELINE).convert('RGB')
            im2 = Image.open(table_path).convert('RGB')
            # Resize if different sizes
            if im1.size != im2.size:
                im2 = im2.resize(im1.size)
            diff = ImageChops.difference(im1, im2)
            bbox = diff.getbbox()
            if bbox:
                print('Alpaca table DIFFER from baseline; diff bbox:', bbox)
                diff.save(OUT_DIR / 'alpaca_diff.png')
            else:
                print('Alpaca table MATCHES baseline')
        else:
            print('Baseline or current screenshot missing; skipping visual diff')

        # Test RAG/FinGPT: navigate to Research Lab -> RAG Chat
        try:
            await page.click('text=🔬 Research Lab', timeout=8000)
        except Exception:
            pass
        await page.wait_for_timeout(1000)
        try:
            await page.click('text=🤖 RAG Chat', timeout=5000)
        except Exception:
            pass
        await page.wait_for_timeout(1000)

        rag_input = await page.query_selector('#rl-rag-query-input')
        rag_result = ''
        if rag_input and await rag_input.is_visible():
            await rag_input.fill('What are key metrics for options analysis?')
            submit = await page.query_selector('#rl-rag-run-btn')
            if submit:
                await submit.click()
                await page.wait_for_timeout(8000)
                ans = await page.query_selector('#rl-rag-answer')
                if ans:
                    rag_result = await ans.inner_text()
                    print('RAG answer snippet:', rag_result[:300])
                    # Save screenshot
                    await page.screenshot(path=str(OUT_DIR / 'rag_response.png'))
        else:
            print('RAG input not found or not visible')

        await browser.close()


if __name__ == '__main__':
    asyncio.run(run())
