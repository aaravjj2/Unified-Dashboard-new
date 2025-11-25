#!/usr/bin/env python3
"""Find actual button IDs in dashboard tabs."""
import asyncio
from playwright.async_api import async_playwright
import json


async def find_button_ids():
    """Scan dashboard to find actual button IDs."""
    
    tabs = [
        'market_trends',
        'market_forecast', 
        'research_lab',
        'options_lab',
        'volatility_lab',
        'portfolio'
    ]
    
    results = {}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto('http://localhost:8050', wait_until='networkidle', timeout=60000)
        await asyncio.sleep(3)
        
        for tab_id in tabs:
            print(f"\n{'='*80}")
            print(f"TAB: {tab_id}")
            print('='*80)
            
            # Navigate to tab
            tab_selector = f'.nav-item:has-text("{tab_id.replace("_", " ").title()}")'
            try:
                await page.click(tab_selector, timeout=5000)
                await asyncio.sleep(2)
            except:
                print(f"Could not navigate to {tab_id}")
                continue
            
            # Find all buttons
            buttons = await page.query_selector_all('button')
            
            tab_buttons = []
            for button in buttons:
                button_id = await button.get_attribute('id')
                button_text = await button.inner_text()
                is_visible = await button.is_visible()
                
                if button_id or (button_text and len(button_text) < 50):
                    tab_buttons.append({
                        'id': button_id or 'NO_ID',
                        'text': button_text.strip()[:50] if button_text else '',
                        'visible': is_visible
                    })
            
            # Also check for input buttons
            inputs = await page.query_selector_all('input[type="button"], input[type="submit"]')
            for inp in inputs:
                inp_id = await inp.get_attribute('id')
                inp_value = await inp.get_attribute('value')
                is_visible = await inp.is_visible()
                
                if inp_id:
                    tab_buttons.append({
                        'id': inp_id,
                        'text': inp_value or '',
                        'visible': is_visible,
                        'type': 'input'
                    })
            
            results[tab_id] = tab_buttons
            
            print(f"Found {len(tab_buttons)} buttons/inputs:")
            for btn in tab_buttons[:20]:  # Show first 20
                vis = '✅' if btn.get('visible') else '❌'
                print(f"  {vis} ID: {btn['id']:30s} Text: {btn['text']}")
        
        await browser.close()
    
    # Save results
    with open('reports/duplicates_fix/diagnostics/actual_button_ids.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Saved to: reports/duplicates_fix/diagnostics/actual_button_ids.json")
    
    return results


if __name__ == '__main__':
    asyncio.run(find_button_ids())
