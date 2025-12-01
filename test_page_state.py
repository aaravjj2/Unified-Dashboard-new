from playwright.sync_api import sync_playwright
import time

print('Checking page state...')
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    page.goto('http://localhost:8051/', timeout=60000)
    page.wait_for_load_state('domcontentloaded')
    time.sleep(6)
    
    # Click to Portfolio
    page.evaluate("""
        const portfolioTab = Array.from(document.querySelectorAll('a[role="tab"]'))
            .find(el => el.textContent.includes('Portfolio'));
        if (portfolioTab) portfolioTab.click();
    """)
    time.sleep(3)
    
    # Click to Positions
    page.evaluate("""
        const positionsTab = Array.from(document.querySelectorAll('a[role="tab"]'))
            .find(el => el.textContent.includes('Positions'));
        if (positionsTab) positionsTab.click();
    """)
    time.sleep(3)
    
    # Check what's on the page
    html = page.evaluate("""
        () => {
            const container = document.querySelector('#portfolio-tracker-tab-positions-content');
            if (!container) return 'NO CONTAINER FOUND';
            return container.innerHTML.substring(0, 1000);
        }
    """)
    print('Page content:')
    print(html)
    
    # Check button
    btn_exists = page.evaluate("""
        () => !!document.querySelector('button#portfolio-positions-refresh-btn')
    """)
    print(f'\nRefresh button exists: {btn_exists}')
    
    # Check table
    table_exists = page.evaluate("""
        () => !!document.querySelector('table#positions-datatable')
    """)
    print(f'Table exists: {table_exists}')
    
    browser.close()
