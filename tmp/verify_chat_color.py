from playwright.sync_api import sync_playwright
import sys

url = 'http://localhost:8050'
screenshot_path = 'reports/chat_agent/screenshots/chat_color_after.png'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    try:
        page.goto(url, wait_until='networkidle', timeout=30000)
        page.wait_for_selector('#chatbot-toggle-btn', timeout=10000)
        
        # Click chat toggle to open chat
        page.click('#chatbot-toggle-btn')
        page.wait_for_timeout(1000)
        
        # Take screenshot
        page.screenshot(path=screenshot_path, full_page=True)
        print(f'Screenshot saved: {screenshot_path}')
        
        # Check diagnostic color
        diagnostic = page.query_selector('#chat-color-diagnostic')
        if diagnostic:
            color = page.evaluate('(el) => window.getComputedStyle(el).color', diagnostic)
            print(f'Diagnostic element color: {color}')
        else:
            print('Diagnostic element not found')
        
        # Check window variable
        window_color = page.evaluate('() => window.__chat_last_computed_color || "not_set"')
        print(f'Window.__chat_last_computed_color: {window_color}')
        
        # Check chatbot messages container color
        msg_container = page.query_selector('#chatbot-messages-container')
        if msg_container:
            msg_color = page.evaluate('(el) => window.getComputedStyle(el).color', msg_container)
            print(f'Chatbot messages container color: {msg_color}')
        
    except Exception as e:
        print(f'Error: {e}')
    finally:
        browser.close()
