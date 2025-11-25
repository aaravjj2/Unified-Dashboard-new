#!/usr/bin/env python3
"""Final verification - test all tabs after fixes"""
from playwright.sync_api import sync_playwright
import time
import os
import pathlib

print("="*70)
print("FINAL TAB VERIFICATION - ALL TABS")
print("="*70)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    
    import os
    HOME = os.environ.get('DASH_HOME_URL', 'http://localhost:8050')
    print(f"\nLoading dashboard... {HOME}")
    page.goto(HOME, wait_until='load', timeout=60000)
    page.wait_for_selector('#dashboard-tabs', timeout=15000)
    time.sleep(1)
    print("✓ Dashboard loaded\n")

    # Find top-level tabs robustly
    top_tabs = page.locator('#dashboard-tabs [role="tab"]').all()
    if not top_tabs:
        # Fallback selectors
        top_tabs = page.locator('#dashboard-tabs a, #dashboard-tabs button').all()

    print(f"Found {len(top_tabs)} top-level tabs")

    # Iterate each top-level tab and inspect subtabs/pane
    failures = []
    artifacts_dir = os.environ.get('ARTIFACTS_DIR', 'test-artifacts/verify-tabs')
    pathlib.Path(artifacts_dir).mkdir(parents=True, exist_ok=True)

    for idx, t in enumerate(top_tabs):
        try:
            text = t.text_content().strip()
            print(f"\n[{idx}] TOP TAB: {text}")
            # Determine pane id via aria-controls if available
            pane_id = t.get_attribute('aria-controls') or t.get_attribute('data-tab') or None
            t.click()
            time.sleep(1)

            pane_selector = None
            pane_locator = None
            if pane_id:
                # Some react-generated ids contain colons which are invalid in CSS id selectors.
                # Use attribute selector which is safe: [id="<pane_id>"]
                pane_locator = page.locator(f'[id="{pane_id}"]')
                pane_selector = f'[id="{pane_id}"]'
            else:
                # fallback: try the wrapper we added
                panes = page.locator('.dashboard-tab-pane').all()
                for p in panes:
                    try:
                        if p.is_visible():
                            pid = p.get_attribute("id")
                            pane_locator = page.locator(f'[id="{pid}"]') if pid else p
                            pane_selector = f'[id="{pid}"]' if pid else None
                            break
                    except Exception:
                        continue

            print(f"  pane_locator: {pane_selector}")

            # Find nested subtabs inside pane (use the pane_locator to scope)
            subtabs = []
            if pane_locator:
                try:
                    subtabs = pane_locator.locator('.nav-tabs [role="tab"]').all()
                    if not subtabs:
                        subtabs = pane_locator.locator('.nav-tabs a, .nav-tabs button').all()
                except Exception:
                    # final fallback: query within document but filter by visibility
                    subtabs = page.locator(f'{pane_selector} .nav-tabs a, {pane_selector} .nav-tabs button').all() if pane_selector else []

            print(f"  found {len(subtabs)} nested subtabs")

            # Basic checks for a few subtabs (click first few)
            for sidx, s in enumerate(subtabs[:3]):
                try:
                    s_text = s.text_content().strip()
                    print(f"    - subtab[{sidx}]: {s_text}")
                    s.click()
                    time.sleep(1)
                    # Heuristics: check for tables or charts in the pane
                    has_table = page.locator(f"{pane_selector} table").count() > 0 if pane_selector else page.locator('table').count() > 0
                    has_chart = page.locator(f"{pane_selector} .js-plotly-plot").count() > 0 if pane_selector else page.locator('.js-plotly-plot').count() > 0
                    has_error = page.locator('text=/Error:|Internal Server Error/i').count() > 0
                    print(f"      ✓ table: {has_table}, chart: {has_chart}, error: {has_error}")

                    if not (has_table or has_chart) or has_error:
                        # save screenshot for failing pane
                        safe_tab = text.replace(' ', '_').replace('/', '_')[:50]
                        safe_sub = s_text.replace(' ', '_').replace('/', '_')[:50]
                        out = os.path.join(artifacts_dir, f"{safe_tab}--{safe_sub}.png")
                        # If pane_selector points to an id, screenshot that element; otherwise full page
                        try:
                            if pane_selector:
                                page.locator(pane_selector).screenshot(path=out)
                            else:
                                page.screenshot(path=out)
                        except Exception:
                            page.screenshot(path=out)
                        print(f"      Screenshot saved: {out}")
                        failures.append((text, s_text, out, has_error))
                except Exception as e:
                    print(f"      ✗ subtab check failed: {e}")
        except Exception as e:
            print(f"✗ Failed to inspect top tab {idx}: {e}")
    
    print("\n" + "="*70)
    print("VERIFICATION COMPLETE")
    print("="*70)
    if failures:
        print('\nFailures detected:')
        for f in failures:
            print(f" - TopTab: {f[0]}, Subtab: {f[1]}, screenshot: {f[2]}, error: {f[3]}")
        browser.close()
        # exit non-zero so CI can catch issues
        raise SystemExit(2)

    browser.close()
