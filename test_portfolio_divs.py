from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    page.goto('http://localhost:8051/', timeout=60000)
    page.wait_for_load_state('domcontentloaded')
    time.sleep(5)
    
    # Get all main tabs
    main_tabs = page.evaluate("""
        () => {
            const tabs = Array.from(document.querySelectorAll('a[role="tab"]'));
            return tabs.map((t, i) => ({
                index: i,
                id: t.id,
                text: t.textContent.trim(),
                href: t.href
            }));
        }
    """)
    
    print('Main tabs:')
    for tab in main_tabs:
        print(f"  [{tab['index']}] '{tab['text']}' - id:{tab['id']}")
        if 'Portfolio' in tab['text']:
            print(f"      ✅ FOUND Portfolio tab!")
    
    # Click Portfolio
    print("\nClicking Portfolio...")
    page.evaluate("""
        Array.from(document.querySelectorAll('a[role="tab"]'))
            .find(el => el.textContent.includes('Portfolio'))?.click()
    """)
    time.sleep(5)
    
    # Check what content exists
    content_check = page.evaluate("""
        () => {
            const allDivs = Array.from(document.querySelectorAll('div[id*="portfolio"]'));
            return allDivs.map(d => ({
                id: d.id,
                classes: d.className,
                hasContent: d.innerHTML.length > 0
            }));
        }
    """)
    
    print("\nPortfolio-related divs:")
    for div in content_check:
        print(f"  ID: {div['id']}, Classes: {div['classes']}, HasContent: {div['hasContent']}")
    
    browser.close()
