"""
Debug script to find Azure ML universe selector
"""
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    print("Loading Azure ML Lab...")
    page.goto('http://localhost:8050/azure-ml-lab', wait_until='networkidle')
    time.sleep(3)
    
    # Get all radio inputs
    print("\nSearching for radio inputs...")
    radios = page.evaluate('''() => {
        const inputs = document.querySelectorAll('input[type="radio"]');
        return Array.from(inputs).map(input => ({
            id: input.id,
            name: input.name,
            value: input.value,
            checked: input.checked,
            parentId: input.parentElement ? input.parentElement.id : 'none'
        }));
    }''')
    
    print(f"Found {len(radios)} radio inputs:")
    for radio in radios:
        print(f"  - ID: {radio['id']}, Name: {radio['name']}, Value: {radio['value']}, Checked: {radio['checked']}, Parent: {radio['parentId']}")
    
    # Look for universe-related elements
    print("\nSearching for universe-related elements...")
    universe_elements = page.evaluate('''() => {
        const elements = document.querySelectorAll('[id*="universe"], [class*="universe"]');
        return Array.from(elements).slice(0, 5).map(el => ({
            tag: el.tagName,
            id: el.id,
            className: el.className,
            text: el.textContent.substring(0, 50)
        }));
    }''')
    
    for el in universe_elements:
        print(f"  - {el['tag']} id='{el['id']}' class='{el['className']}' text='{el['text']}'")
    
    # Save HTML
    html = page.content()
    with open('azure_ml_debug.html', 'w') as f:
        f.write(html)
    
    print("\n✅ Saved HTML to azure_ml_debug.html")
    
    browser.close()
