from playwright.sync_api import sync_playwright

url = 'http://localhost:8050'
screenshot_path = 'reports/chat_agent/screenshots/chat_color_after.png'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    try:
        page.goto(url, wait_until='networkidle', timeout=30000)
        
        # Wait for diagnostic element
        page.wait_for_selector('#chat-color-diagnostic', timeout=10000)
        print('Diagnostic element found')
        
        # Get diagnostic color directly
        diagnostic_color = page.evaluate('''() => {
            const el = document.getElementById('chat-color-diagnostic');
            return el ? window.getComputedStyle(el).color : null;
        }''')
        print(f'Diagnostic element color: {diagnostic_color}')
        
        # Get chatbot messages container color
        messages_color = page.evaluate('''() => {
            const el = document.getElementById('chatbot-messages-container');
            return el ? window.getComputedStyle(el).color : null;
        }''')
        print(f'Chatbot messages container color: {messages_color}')
        
        # Check if chat.css is loaded
        css_loaded = page.evaluate('''() => {
            const links = Array.from(document.querySelectorAll('link[rel="stylesheet"]'));
            return links.some(link => link.href.includes('chat.css'));
        }''')
        print(f'chat.css loaded: {css_loaded}')
        
        # Take full page screenshot
        page.screenshot(path=screenshot_path, full_page=True)
        print(f'Screenshot saved: {screenshot_path}')
        
        # Verify expected color
        expected = 'rgb(0, 0, 0)'
        if diagnostic_color == expected:
            print(f'✓ PASS: Diagnostic color matches expected {expected}')
        else:
            print(f'✗ FAIL: Diagnostic color {diagnostic_color} != expected {expected}')
        
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
    finally:
        browser.close()
