#!/usr/bin/env python3
"""
Deep inspection of Research Lab tab - check actual DOM state
"""
import asyncio
from playwright.async_api import async_playwright
import json

async def inspect_research_lab():
    """Inspect Research Lab tab deeply."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        console_errors = []
        page.on('console', lambda msg: console_errors.append({
            'type': msg.type,
            'text': msg.text
        }) if msg.type == 'error' else None)
        
        print("🌐 Loading dashboard...")
        await page.goto('http://localhost:8052', wait_until='networkidle', timeout=60000)
        await asyncio.sleep(5)
        
        # Click Research Lab tab
        print("\n📋 Clicking Research Lab tab...")
        await page.click('a[role="tab"]:has-text("🔬 Research Lab")', timeout=10000)
        await asyncio.sleep(3)
        
        # Take screenshot
        await page.screenshot(path='reports/research_lab_actual_state.png', full_page=True)
        print("📸 Screenshot saved: reports/research_lab_actual_state.png")
        
        # Get ALL content
        content = await page.content()
        
        # Save full HTML
        with open('reports/research_lab_full_html.html', 'w') as f:
            f.write(content)
        print("💾 Full HTML saved: reports/research_lab_full_html.html")
        
        # Check for Research Lab specific elements
        print("\n🔍 Searching for Research Lab elements...")
        
        # Check for subtabs
        subtabs = await page.query_selector_all('a[role="tab"]')
        print(f"\nFound {len(subtabs)} tabs total")
        
        # Get visible text
        visible_text = await page.evaluate('() => document.body.innerText')
        
        # Check for specific keywords
        keywords = ['Research', 'Brief', 'Market Scan', 'Factor Analysis', 'Correlation']
        for kw in keywords:
            if kw.lower() in visible_text.lower():
                print(f"  ✅ Found keyword: {kw}")
            else:
                print(f"  ❌ Missing keyword: {kw}")
        
        # Check for actual content divs
        print("\n🔍 Checking for content containers...")
        containers = await page.query_selector_all('div[id*="research"]')
        print(f"Found {len(containers)} divs with 'research' in ID")
        
        for i, container in enumerate(containers[:10]):
            div_id = await container.get_attribute('id')
            is_visible = await container.is_visible()
            print(f"  Container {i}: {div_id} - Visible: {is_visible}")
        
        # Count console errors
        syntax_errors = [e for e in console_errors if 'SyntaxError' in e['text']]
        
        print(f"\n📊 Console Errors: {len(console_errors)}")
        print(f"📊 Syntax Errors: {len(syntax_errors)}")
        
        if syntax_errors:
            print("\n⚠️ SYNTAX ERRORS FOUND:")
            for err in syntax_errors[:5]:
                print(f"  - {err['text'][:200]}")
        
        # Check for empty state
        if len(visible_text.strip()) < 100:
            print("\n❌ TAB APPEARS EMPTY!")
            print(f"Visible text length: {len(visible_text)}")
            print(f"Preview: {visible_text[:200]}")
        else:
            print(f"\n✅ Tab has content ({len(visible_text)} characters)")
        
        # Save report
        report = {
            'tab': 'Research Lab',
            'console_errors': len(console_errors),
            'syntax_errors': len(syntax_errors),
            'visible_text_length': len(visible_text),
            'containers_found': len(containers),
            'keywords_found': [kw for kw in keywords if kw.lower() in visible_text.lower()],
            'error_samples': console_errors[:20]
        }
        
        with open('reports/research_lab_inspection.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("\n👁️ Browser will stay open for 60 seconds for manual inspection...")
        await asyncio.sleep(60)
        
        await browser.close()

if __name__ == '__main__':
    import os
    os.makedirs('reports', exist_ok=True)
    asyncio.run(inspect_research_lab())
