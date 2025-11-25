"""Debug script to inspect tabs element properties."""
import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.goto('http://localhost:8050', wait_until='networkidle')
        await page.wait_for_timeout(2000)
        
        # Inspect the tabs element thoroughly
        tabs_info = await page.evaluate('''() => {
            const tabs = document.getElementById('dashboard-tabs');
            if (tabs === null) return {exists: false};
            
            // Get ALL properties and attributes
            const attrs = {};
            for (let attr of tabs.attributes) {
                attrs[attr.name] = attr.value;
            }
            
            return {
                exists: true,
                attributes: attrs,
                innerHTML_preview: tabs.innerHTML.substring(0, 500),
                children_count: tabs.children.length
            };
        }''')
        
        print('Tabs element inspection:')
        print(f'  exists: {tabs_info.get("exists")}')
        print(f'  attributes: {tabs_info.get("attributes")}')
        print(f'  children: {tabs_info.get("children_count")}')
        print(f'\nInnerHTML preview:\n{tabs_info.get("innerHTML_preview", "")[:300]}')
        
        # NOW click Market Trends and check again
        tab = page.locator('a.nav-link:has-text("Market Trends")')
        count = await tab.count()
        print(f'\n\nMarket Trends tab found: {count}')
        
        if count > 0:
            await tab.first.click()
            await page.wait_for_timeout(2000)
            
            # Check tabs attributes AFTER click
            tabs_after = await page.evaluate('''() => {
                const tabs = document.getElementById('dashboard-tabs');
                if (tabs === null) return {exists: false};
                
                const attrs = {};
                for (let attr of tabs.attributes) {
                    attrs[attr.name] = attr.value;
                }
                
                return {
                    exists: true,
                    attributes: attrs
                };
            }''')
            
            print(f'\nTabs attributes AFTER click:')
            print(f'  {tabs_after.get("attributes")}')
        
        await browser.close()

asyncio.run(test())
