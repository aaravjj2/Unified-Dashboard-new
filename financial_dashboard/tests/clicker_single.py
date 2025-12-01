#!/usr/bin/env python3
"""Run the clicker check for a single tab.

Usage: python3 tests/clicker_single.py "Market Trends"
"""
import sys
import time
from playwright.sync_api import sync_playwright

from pathlib import Path

# import the helper functions from clicker_tests if available
try:
    from tests.clicker_tests import click_tab_and_snapshot, RESULTS
except Exception:
    # fallback: copy minimal logic inline if import fails
    RESULTS = []

    def click_tab_and_snapshot(page, tab_name):
        tab = page.locator(f"text={tab_name}").first
        tab.click(timeout=10000)
        time.sleep(1.0)
        # minimal heuristic
        selectors = [f"h2:has-text('{tab_name}')", f"text={tab_name}"]
        ok = False
        for sel in selectors:
            try:
                page.locator(sel).first.wait_for(state='visible', timeout=5000)
                ok = True
                break
            except Exception:
                continue
        RESULTS.append((tab_name, 'PASS' if ok else 'FAIL'))


def run_single(tab_name: str):
    url = 'http://localhost:8000'
    print(f"Running clicker for: {tab_name}")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        # small wait for initial load
        page.wait_for_load_state('networkidle')
        time.sleep(0.5)
        click_tab_and_snapshot(page, tab_name)
        browser.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 tests/clicker_single.py \"Tab Name\"")
        sys.exit(1)
    tab = sys.argv[1]
    run_single(tab)
    for name, status in RESULTS:
        if name == tab:
            print(f"Result for '{name}': {status}")


if __name__ == '__main__':
    main()
