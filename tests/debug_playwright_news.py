"""
Debug script: open dashboard, click Market Trends tab, dump '#news-container' HTML,
capture console messages and screenshot for diagnosis.
"""
from playwright.sync_api import sync_playwright
import time

BASE_URL = 'http://localhost:8050'
selectors = [
    'a:has-text("Market Trends")',
    'button:has-text("Market Trends")',
    '[data-value="market_trends"]',
    '.nav-link:has-text("Market Trends")'
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    console_msgs = []
    page.on('console', lambda msg: console_msgs.append(f"{msg.type}: {msg.text}"))

    print('Loading dashboard...')
    page.goto(BASE_URL, wait_until='domcontentloaded')
    time.sleep(2)

    clicked = False
    for sel in selectors:
        try:
            loc = page.locator(sel)
            count = loc.count()
            print(f"Selector '{sel}' count: {count}")
            if count > 0:
                loc.first.click()
                print(f"Clicked using selector: {sel}")
                clicked = True
                break
        except Exception as e:
            print(f"Selector '{sel}' exception: {e}")

    if not clicked:
        print('WARNING: Could not find Market Trends tab to click')

    # Wait longer for news to load
    time.sleep(6)

    # Dump news container
    try:
        news = page.locator('#news-container')
        print('news count:', news.count())
        if news.count() > 0:
            html = news.first.inner_html()
            text = news.first.inner_text()
            print('news.inner_text (first 500 chars):')
            print(text[:500])
            print('\nnews.inner_html (first 1000 chars):')
            print(html[:1000])
        else:
            print('news-container not found')
    except Exception as e:
        print('Error reading news container:', e)

    # Save screenshot
    screenshot_path = 'test-artifacts/debug_news_playwright.png'
    try:
        page.screenshot(path=screenshot_path, full_page=True)
        print('Saved screenshot to', screenshot_path)
    except Exception as e:
        print('Screenshot failed:', e)

    print('\nConsole messages (last 20):')
    for m in console_msgs[-20:]:
        print(m)

    browser.close()
