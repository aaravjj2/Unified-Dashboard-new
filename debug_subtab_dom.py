#!/usr/bin/env python3
"""
Debug script to investigate actual subtab DOM structure
"""

import asyncio
from playwright.async_api import async_playwright

DASHBOARD_URL = "http://localhost:8051"

async def inspect_subtab_structure():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        
        await page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_selector("#dashboard-tabs", state="visible", timeout=10000)
        
        print("🔍 Inspecting Research Lab subtab structure...")
        
        # Navigate to Research Lab
        await page.click("#tab-research_lab", timeout=15000)
        await asyncio.sleep(3)
        
        # Get all subtab-related elements
        print("\n1. Looking for dbc.Tabs elements:")
        tabs_elements = await page.query_selector_all("[role='tablist']")
        print(f"   Found {len(tabs_elements)} tablist elements")
        
        for idx, elem in enumerate(tabs_elements[:3]):
            html = await elem.inner_html()
            print(f"\n   Tablist {idx}:")
            print(f"   {html[:500]}")
        
        print("\n2. Looking for tab buttons:")
        tab_buttons = await page.query_selector_all("button[role='tab']")
        print(f"   Found {len(tab_buttons)} tab buttons")
        
        for idx, btn in enumerate(tab_buttons[:10]):
            text = await btn.text_content()
            btn_id = await btn.get_attribute("id")
            aria_controls = await btn.get_attribute("aria-controls")
            print(f"   Button {idx}: text='{text}', id='{btn_id}', aria-controls='{aria_controls}'")
        
        print("\n3. Looking for specific subtab (Market Scan):")
        selectors = [
            "#market-scan",
            "button:has-text('Market Scan')",
            "[aria-label*='Market Scan']",
            "a:has-text('Market Scan')"
        ]
        
        for sel in selectors:
            try:
                elem = await page.query_selector(sel)
                if elem:
                    tag = await elem.evaluate("el => el.tagName")
                    classes = await elem.get_attribute("class")
                    btn_id = await elem.get_attribute("id")
                    print(f"   ✅ Found with selector: {sel}")
                    print(f"      Tag: {tag}, ID: {btn_id}, Classes: {classes}")
                else:
                    print(f"   ❌ Not found: {sel}")
            except Exception as e:
                print(f"   ❌ Error with {sel}: {e}")
        
        print("\n4. Checking Volatility Lab subtab structure:")
        await page.click("#tab-volatility_lab", timeout=15000)
        await asyncio.sleep(3)
        
        tab_buttons = await page.query_selector_all("button[role='tab']")
        print(f"   Found {len(tab_buttons)} tab buttons in Volatility Lab")
        
        for idx, btn in enumerate(tab_buttons[:12]):
            text = await btn.text_content()
            btn_id = await btn.get_attribute("id")
            aria_selected = await btn.get_attribute("aria-selected")
            print(f"   Button {idx}: '{text}' | ID: {btn_id} | Selected: {aria_selected}")
        
        print("\n5. Checking Portfolio subtab structure:")
        await page.click("#tab-portfolio", timeout=15000)
        await asyncio.sleep(3)
        
        tab_buttons = await page.query_selector_all("button[role='tab']")
        print(f"   Found {len(tab_buttons)} tab buttons in Portfolio")
        
        for idx, btn in enumerate(tab_buttons[:10]):
            text = await btn.text_content()
            btn_id = await btn.get_attribute("id")
            aria_selected = await btn.get_attribute("aria-selected")
            print(f"   Button {idx}: '{text}' | ID: {btn_id} | Selected: {aria_selected}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_subtab_structure())
