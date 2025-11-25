"""
Capture Playwright Screenshots of Dashboard Services

Connects to all running dashboard services and captures full-page screenshots.
Saves screenshots with timestamps for visual regression testing.

Usage:
    python capture_initial_state.py [--output-dir DIR]
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
from datetime import datetime
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Service configuration
SERVICES = {
    'integrated_dashboard': 'http://localhost:8000',
    'market_trends': 'http://localhost:8050',
    'market_forecast': 'http://localhost:8051',
    'analysis_hub': 'http://localhost:8054',
    'portfolio_tracker': 'http://localhost:8056',
    'research_lab': 'http://localhost:8058',
}

async def capture_service_screenshot(page, service_name, url, output_dir):
    """
    Capture screenshot of a single service.
    
    Args:
        page: Playwright page object
        service_name: Name of the service (for filename)
        url: Service URL
        output_dir: Directory to save screenshots
    """
    try:
        logger.info(f"📸 Capturing {service_name} at {url}...")
        
        # Navigate to the service
        response = await page.goto(url, wait_until='networkidle', timeout=30000)
        
        if response and response.status >= 400:
            logger.error(f"❌ {service_name}: HTTP {response.status}")
            return False
        
        # Wait for page to be interactive
        await page.wait_for_load_state('domcontentloaded')
        await asyncio.sleep(2)  # Give Dash time to render
        
        # Additional wait for Dash-specific elements
        try:
            await page.wait_for_selector('#react-entry-point', timeout=5000)
            logger.info(f"  ✓ Found Dash react-entry-point")
        except:
            logger.warning(f"  ⚠ No react-entry-point found (may not be a Dash app)")
        
        # Take full-page screenshot
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_path = output_dir / f'{service_name}_{timestamp}.png'
        await page.screenshot(path=str(screenshot_path), full_page=True)
        
        logger.info(f"  ✓ Saved screenshot: {screenshot_path}")
        
        # Capture console logs
        logs_path = output_dir / f'{service_name}_{timestamp}.log'
        with open(logs_path, 'w') as f:
            f.write(f"Service: {service_name}\n")
            f.write(f"URL: {url}\n")
            f.write(f"Title: {await page.title()}\n")
            f.write(f"Status: {response.status if response else 'N/A'}\n")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to capture {service_name}: {e}")
        return False


async def main():
    """Main entry point for capturing screenshots."""
    parser = argparse.ArgumentParser(description='Capture dashboard service screenshots')
    parser.add_argument('--output-dir', type=str, default='screenshots',
                       help='Directory to save screenshots (default: screenshots/)')
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 Output directory: {output_dir}")
    
    # Launch Playwright
    async with async_playwright() as p:
        # Use Chromium for consistent rendering
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            device_scale_factor=1
        )
        page = await context.new_page()
        
        # Enable console logging
        page.on('console', lambda msg: logger.debug(f"Browser console: {msg.text}"))
        
        # Capture each service
        results = {}
        for service_name, url in SERVICES.items():
            success = await capture_service_screenshot(page, service_name, url, output_dir)
            results[service_name] = success
        
        await browser.close()
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("SCREENSHOT CAPTURE SUMMARY")
    logger.info("="*60)
    for service_name, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        logger.info(f"{status:12} | {service_name}")
    
    total = len(results)
    success_count = sum(results.values())
    logger.info("="*60)
    logger.info(f"Total: {success_count}/{total} services captured successfully")
    
    # Exit code
    return 0 if success_count == total else 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    exit(exit_code)
