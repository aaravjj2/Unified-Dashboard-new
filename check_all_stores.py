#!/usr/bin/env python
"""Check which stores exist in the DOM."""
from playwright.sync_api import sync_playwright
import time

def check_stores():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print("Loading dashboard...")
        page.goto('http://localhost:8050', wait_until='networkidle', timeout=30000)
        time.sleep(2)
        
        # Stores expected from index.py hidden div (lines 517-533)
        index_stores = [
            'tab-data-store',
            'pa-debug-store',
            'attr-results-store',
            'trends-last-cached',
            'current-job',
            'reload-trigger',
            'dashboard-queued-job',
            'last-cached',
            'theme-store',
            'options-chain-store',
            'options-surface-store',
            'ol-backtest-store',
            'ol-settings-store',
        ]
        
        # Stores expected from get_all_placeholders() (layout_placeholders.py)
        placeholder_stores = [
            'last-edit',
            'trends-results-store',
            'mt-status-store',
            'news-store',
            'rebuild-last-cached',
            'mf-results-store',
            'mp-current-job',
            'mp-page-load-ts',
            'wp-current-job',
        ]
        
        print("\n📦 INDEX.PY STORES (should exist):")
        for store_id in index_stores:
            exists = page.locator(f'#{store_id}').count() > 0
            print(f"  {'✅' if exists else '❌'} {store_id}")
        
        print("\n📦 PLACEHOLDER STORES (should exist):")
        for store_id in placeholder_stores:
            exists = page.locator(f'#{store_id}').count() > 0
            print(f"  {'✅' if exists else '❌'} {store_id}")
        
        browser.close()

if __name__ == '__main__':
    check_stores()
