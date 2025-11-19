"""Quick Monthly Picks diagnostic to check what's actually rendering"""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    
    page.goto('http://localhost:8050', wait_until='networkidle')
    page.wait_for_selector('#dashboard-tabs', timeout=30000)
    page.locator('text=Monthly Picks').first.click()
    page.wait_for_timeout(5000)
    
    # Check for table
    tables = page.locator('table').count()
    print(f"Tables found: {tables}")
    
    if tables > 0:
        # Check for rows with data-ticker
        rows = page.locator('table tbody tr[data-ticker]').count()
        print(f"Rows with data-ticker: {rows}")
        
        if rows > 0:
            # Get first row attributes
            first_row = page.locator('table tbody tr[data-ticker]').first
            ticker = first_row.get_attribute('data-ticker')
            print(f"First ticker: {ticker}")
            
            # Check for columns
            cells = first_row.locator('td').count()
            print(f"Cells in first row: {cells}")
            
            # Get all data-col values
            for i in range(min(cells, 10)):
                cell = first_row.locator('td').nth(i)
                col_name = cell.get_attribute('data-col')
                data_value = cell.get_attribute('data-value')
                print(f"  Cell {i}: data-col={col_name}, data-value={data_value[:20] if data_value else 'None'}")
        else:
            print("No rows with data-ticker found")
            # Check raw HTML
            html = page.locator('body').inner_html()
            if 'Monthly Picks' in html:
                print("'Monthly Picks' text found in body")
            if '<table' in html:
                print("Table HTML tag found")
    else:
        print("No tables found")
    
    page.screenshot(path='test-artifacts/monthly_diagnostic.png', full_page=True)
    browser.close()
    print("Screenshot saved to test-artifacts/monthly_diagnostic.png")
