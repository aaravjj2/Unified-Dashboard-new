"""Check if Dash props are being updated when tab is clicked."""
import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Intercept network responses
        responses = []
        async def log_response(response):
            if '_dash-update-component' in response.url:
                try:
                    body = await response.json()
                    responses.append({
                        'url': response.url,
                        'status': response.status,
                        'body': body
                    })
                except:
                    pass
        
        page.on('response', log_response)
        
        await page.goto('http://localhost:8050', wait_until='networkidle')
        await page.wait_for_timeout(2000)
        
        print(f'Initial _dash-update-component responses: {len(responses)}')
        
        # Check if any response updates dashboard-tabs
        for resp in responses:
            body = resp['body']
            if 'response' in body:
                response_data = body['response']
                if 'dashboard-tabs' in str(response_data):
                    print(f'\\nFound dashboard-tabs in response:')
                    print(f'  {response_data}')
        
        # Click Market Trends tab
        responses_before_click = len(responses)
        tab = page.locator('a.nav-link:has-text("Market Trends")')
        await tab.first.click()
        await page.wait_for_timeout(3000)
        
        print(f'\\n_dash-update-component responses after click: {len(responses) - responses_before_click}')
        
        # Check new responses
        for resp in responses[responses_before_click:]:
            body = resp['body']
            print(f'\\nNew response:')
            print(f'  {body}')
        
        await browser.close()

asyncio.run(test())
