"""
Deep diagnostic test for Market Trends dashboard
Captures full DOM structure and identifies missing elements
"""
import asyncio
from playwright.async_api import async_playwright
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def deep_diagnostic():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Capture all console activity
        console_log = []
        page.on("console", lambda msg: console_log.append({
            'type': msg.type,
            'text': msg.text,
            'location': f"{msg.location.get('url', '')}:{msg.location.get('lineNumber', '')}",
            'args': [str(arg) for arg in msg.args]
        }))
        
        # Capture any page errors
        page_errors = []
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        
        try:
            logger.info("=" * 70)
            logger.info("MARKET TRENDS DEEP DIAGNOSTIC")
            logger.info("=" * 70)
            
            logger.info("\n1. Loading page...")
            await page.goto('http://localhost:8050', wait_until='networkidle', timeout=30000)
            logger.info("✅ Page loaded")
            
            # Wait a bit for any dynamic content
            await page.wait_for_timeout(5000)
            
            logger.info("\n2. Capturing full page HTML structure...")
            html_content = await page.content()
            with open('/tmp/market_trends_full_html.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info("✅ Saved to /tmp/market_trends_full_html.html")
            
            logger.info("\n3. Searching for key elements...")
            
            # Search for various selectors
            selectors_to_check = [
                ('h3:has-text("Market Trends")', 'Page title'),
                ('[data-testid="trends-results-table"]', 'Results table with testid'),
                ('div[id="mt-results-table-container"]', 'Results table container by ID'),
                ('table', 'Any table element'),
                ('.dash-table', 'Dash table class'),
                ('div[role="grid"]', 'Grid role (DataTable)'),
                ('#mt-brief-text', 'Brief text div'),
                ('#mt-job-status', 'Job status div'),
                ('#mt-model-status', 'Model status div'),
                ('textarea[id="mt-tickers-input"]', 'Ticker input'),
                ('button:has-text("Run Full Analysis")', 'Run button'),
                ('button:has-text("Refresh cached display")', 'Refresh button'),
                ('button:has-text("Reload Model")', 'Reload button'),
            ]
            
            found_elements = {}
            for selector, description in selectors_to_check:
                count = await page.locator(selector).count()
                found_elements[description] = count
                if count > 0:
                    logger.info(f"✅ {description}: Found {count}")
                    # Try to get some content
                    try:
                        first_elem = page.locator(selector).first
                        text = await first_elem.inner_text(timeout=1000)
                        if text and len(text) < 200:
                            logger.info(f"   Content: {text[:100]}")
                    except:
                        pass
                else:
                    logger.warning(f"❌ {description}: NOT FOUND")
            
            logger.info("\n4. Searching for ALL divs with IDs...")
            all_divs_with_ids = await page.locator('div[id]').all()
            logger.info(f"Found {len(all_divs_with_ids)} divs with IDs:")
            div_ids = []
            for div in all_divs_with_ids[:50]:  # Limit to first 50
                div_id = await div.get_attribute('id')
                div_ids.append(div_id)
                logger.info(f"  - {div_id}")
            
            logger.info("\n5. Searching for data-testid attributes...")
            testid_elements = await page.locator('[data-testid]').all()
            logger.info(f"Found {len(testid_elements)} elements with data-testid:")
            for elem in testid_elements[:20]:  # Limit to first 20
                testid = await elem.get_attribute('data-testid')
                logger.info(f"  - {testid}")
            
            logger.info("\n6. Checking Dash app structure...")
            # Check for Dash-specific elements
            dash_app = await page.locator('#react-entry-point').count()
            logger.info(f"Dash react-entry-point: {'Found' if dash_app > 0 else 'NOT FOUND'}")
            
            dash_loading = await page.locator('._dash-loading').count()
            logger.info(f"Dash loading indicators: {dash_loading}")
            
            logger.info("\n7. Extracting page structure...")
            # Get a structured view of the page
            page_structure = await page.evaluate('''() => {
                function getStructure(element, depth = 0, maxDepth = 5) {
                    if (depth > maxDepth) return null;
                    
                    const info = {
                        tag: element.tagName,
                        id: element.id || null,
                        classes: element.className || null,
                        testid: element.getAttribute('data-testid') || null,
                        children: []
                    };
                    
                    for (let child of element.children) {
                        const childInfo = getStructure(child, depth + 1, maxDepth);
                        if (childInfo) info.children.push(childInfo);
                    }
                    
                    return info;
                }
                
                return getStructure(document.body);
            }''')
            
            with open('/tmp/market_trends_structure.json', 'w') as f:
                json.dump(page_structure, f, indent=2)
            logger.info("✅ Page structure saved to /tmp/market_trends_structure.json")
            
            logger.info("\n8. Taking screenshots...")
            await page.screenshot(path='/tmp/market_trends_diagnostic.png', full_page=True)
            logger.info("✅ Full page screenshot saved")
            
            logger.info("\n9. Console messages:")
            if console_log:
                logger.info(f"Total console messages: {len(console_log)}")
                for msg in console_log[-20:]:  # Last 20
                    logger.info(f"  [{msg['type']}] {msg['text']}")
            else:
                logger.info("No console messages")
            
            logger.info("\n10. Page errors:")
            if page_errors:
                logger.error(f"Total page errors: {len(page_errors)}")
                for err in page_errors:
                    logger.error(f"  {err}")
            else:
                logger.info("No page errors")
            
            # Save diagnostic report
            logger.info("\n11. Saving diagnostic report...")
            report = {
                'timestamp': str(asyncio.get_event_loop().time()),
                'found_elements': found_elements,
                'div_ids': div_ids,
                'console_log': console_log,
                'page_errors': page_errors,
            }
            with open('/tmp/market_trends_diagnostic_report.json', 'w') as f:
                json.dump(report, f, indent=2)
            logger.info("✅ Report saved to /tmp/market_trends_diagnostic_report.json")
            
            logger.info("\n" + "=" * 70)
            logger.info("DIAGNOSTIC COMPLETE")
            logger.info("=" * 70)
            logger.info("\nFiles created:")
            logger.info("  - /tmp/market_trends_full_html.html")
            logger.info("  - /tmp/market_trends_structure.json")
            logger.info("  - /tmp/market_trends_diagnostic.png")
            logger.info("  - /tmp/market_trends_diagnostic_report.json")
            
        except Exception as e:
            logger.error(f"❌ Error during diagnostic: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Keep browser open for manual inspection
            logger.info("\nKeeping browser open for 10 seconds for manual inspection...")
            await page.wait_for_timeout(10000)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(deep_diagnostic())
