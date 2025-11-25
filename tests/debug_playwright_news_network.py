"""
Debug script: open dashboard, click Market Trends tab, capture network requests,
wait up to 15s for news to populate, then dump '#news-container' HTML and children.
"""
from playwright.sync_api import sync_playwright
import time

BASE_URL = 'http://localhost:8050'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    requests = []
    page.on('request', lambda req: requests.append((req.method, req.url)))
    console_msgs = []
    page.on('console', lambda msg: console_msgs.append(f"{msg.type}: {msg.text}"))

    page.goto(BASE_URL, wait_until='domcontentloaded')
    time.sleep(1)

    # Click market trends tab
    try:
        tab = page.locator('#tab-market_trends')
        if tab.count() > 0:
            tab.first.click()
            print('Clicked #tab-market_trends')
        else:
            print('#tab-market_trends not found, trying alternative')
            alt = page.locator('a:has-text("Market Trends")')
            if alt.count() > 0:
                alt.first.click()
                print('Clicked alt selector')
    except Exception as e:
        print('Click error:', e)

    # Wait up to 15s for news items
    news_items = []
    for i in range(15):
        time.sleep(1)
        news_items = page.locator('[data-testid="news-panel"] > div, [data-testid*="news-item"], .news-item').all()
        cnt = len(news_items)
        print(f'Wait {i+1}s: news_items count = {cnt}')
        if cnt > 0:
            break

    # Dump news container
    news = page.locator('#news-container')
    print('news count:', news.count())
    if news.count() > 0:
        print('news inner_text:', news.first.inner_text()[:1000])
        print('news inner_html (first 1000):', news.first.inner_html()[:1000])

    print('\nCaptured network requests (last 30):')
    for m, url in requests[-30:]:
        print(m, url)

    print('\nConsole messages (last 20):')
    for m in console_msgs[-20:]:
        print(m)

    # Save screenshot
    page.screenshot(path='test-artifacts/debug_news_network.png', full_page=True)
    print('Saved screenshot to test-artifacts/debug_news_network.png')

    browser.close()
