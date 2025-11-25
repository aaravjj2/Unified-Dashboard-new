from playwright.sync_api import sync_playwright
import time
import os

OUT_DIR = 'outputs'
os.makedirs(OUT_DIR, exist_ok=True)
SCREENSHOT = os.path.join(OUT_DIR, 'research_lab_playwright.png')


def run_test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        url = 'http://localhost:8050'
        print('Navigating to', url)
        page.goto(url, timeout=60000)

        # Open Research Lab tab by text
        try:
            page.click("text=Research Lab", timeout=5000)
        except Exception:
            print('Could not click Research Lab by text; trying alternate selector')

        # Click Market Scan subtab
        try:
            page.click("text=Market Scan", timeout=5000)
        except Exception:
            # fallback: try to click tab element with id
            try:
                page.click("[id='market-scan-tab']", timeout=5000)
            except Exception as e:
                print('Failed to open Market Scan tab:', e)

        # Fill tickers input
        try:
            page.fill("input[id='market-scan-tickers']", 'AAPL, MSFT, TSLA')
        except Exception as e:
            print('Failed to fill tickers input:', e)

    # Try to set sliders (market-cap, pe, beta) to wide ranges via DOM manipulation
        try:
            # market-cap: expects [min, max] in billions on UI (callback multiplies by 1e9)
            page.evaluate("""
            () => {
                const setRange = (id, low, high) => {
                    const container = document.querySelector("[id='" + id + "']");
                    if (!container) return false;
                    // try to find input elements inside (Dash RangeSlider uses input elements for handles)
                    const inputs = container.querySelectorAll('input');
                    if (inputs.length >= 2) {
                        inputs[0].value = low;
                        inputs[1].value = high;
                        inputs[0].dispatchEvent(new Event('input', {bubbles:true}));
                        inputs[1].dispatchEvent(new Event('input', {bubbles:true}));
                        inputs[0].dispatchEvent(new Event('change', {bubbles:true}));
                        inputs[1].dispatchEvent(new Event('change', {bubbles:true}));
                        return true;
                    }
                    // else try to set data attribute
                    container.setAttribute('data-value', JSON.stringify([low, high]));
                    return true;
                };
                setRange('market-scan-market-cap', 0, 3000);
                setRange('market-scan-pe-ratio', 0, 1000);
                setRange('market-scan-beta', 0, 10);
                return true;
            }
            """)
        except Exception as e:
            print('Failed to set sliders via eval:', e)

        # Debug: print current slider/selector text for inspection
        try:
            mc = page.locator("[id='market-scan-market-cap']").inner_text()
            pe = page.locator("[id='market-scan-pe-ratio']").inner_text()
            be = page.locator("[id='market-scan-beta']").inner_text()
            print('market-cap container text:', mc[:200])
            print('pe container text:', pe[:200])
            print('beta container text:', be[:200])
        except Exception as e:
            print('Failed to read slider containers:', e)

        # Try selecting all options in the filter containers to be permissive
        try:
            page.evaluate("""
            () => {
                ['market-scan-market-cap','market-scan-pe-ratio','market-scan-beta'].forEach(id => {
                    const container = document.querySelector("[id='"+id+"']");
                    if (!container) return;
                    // click any button or input inside
                    const buttons = container.querySelectorAll('button, input, label');
                    buttons.forEach(b => {
                        try { b.click(); } catch(e) {}
                    });
                });
                return true;
            }
            """)
            time.sleep(0.5)
            print('Tried clicking filter options to widen selection')
        except Exception as e:
            print('Failed to click filter options:', e)

        # Try moving slider handles to max positions by sending ArrowRight to the second handle
        try:
            for cid in ['market-scan-market-cap','market-scan-pe-ratio','market-scan-beta']:
                handles = page.locator(f"[id='{cid}'] .rc-slider-handle")
                count = handles.count()
                if count >= 2:
                    handle = handles.nth(1)
                    handle.focus()
                    # press ArrowRight many times to push to the right-most mark
                    for _ in range(12):
                        handle.press('ArrowRight')
                    print(f'Moved second handle for {cid}')
                else:
                    print(f'No handle pair found for {cid} (count={count})')
        except Exception as e:
            print('Failed to move slider handles:', e)

        # Click run button
        try:
            page.click("button[id='market-scan-run-button']")
        except Exception as e:
            print('Failed to click run button:', e)

        # Wait for results container
        try:
            page.wait_for_selector("#market-scan-results-container", timeout=20000)
            locator = page.locator('#market-scan-results-container')
            # ensure content loaded
            time.sleep(1)
            locator.screenshot(path=SCREENSHOT)
            text = locator.inner_text()
            print('Result container text snippet:', text[:200])
            print('Saved screenshot to', SCREENSHOT)
        except Exception as e:
            print('No results container found or timeout:', e)

        browser.close()


if __name__ == '__main__':
    run_test()
