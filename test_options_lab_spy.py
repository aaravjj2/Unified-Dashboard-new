#!/usr/bin/env python3
"""
Comprehensive Options Lab test with SPY ticker.
Tests:
1. Options chain loading (with both Alpaca and yfinance fallback)
2. Chain viewer display
3. Data source verification (not mock)
4. AI recommendations
5. Strategy builder
"""
import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, expect

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
DASHBOARD_URL = "http://localhost:8051"
TEST_TICKER = "SPY"
SCREENSHOT_DIR = Path("screenshots/options_lab_spy_test")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

def wait_for_element(page, selector, timeout=10000):
    """Wait for element and return it."""
    try:
        element = page.wait_for_selector(selector, timeout=timeout, state='visible')
        return element
    except Exception as e:
        logger.error(f"Element not found: {selector} - {e}")
        return None

def test_options_lab_spy():
    """Test Options Lab with SPY ticker."""
    logger.info("Starting Options Lab SPY test...")
    
    with sync_playwright() as p:
        # Launch browser (non-headless for debugging)
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        try:
            # Step 1: Navigate to dashboard
            logger.info(f"Loading dashboard at {DASHBOARD_URL}")
            page.goto(DASHBOARD_URL, wait_until='domcontentloaded', timeout=60000)
            time.sleep(3)  # Give extra time for dynamic content
            page.screenshot(path=SCREENSHOT_DIR / "01_dashboard_loaded.png")
            logger.info("✓ Dashboard loaded")
            
            # Step 2: Click Options Lab tab
            logger.info("Navigating to Options Lab...")
            options_tab = page.locator('#tab-options_lab')
            if not options_tab.is_visible():
                logger.error("Options Lab tab not found")
                return False
            
            options_tab.click()
            time.sleep(2)
            page.screenshot(path=SCREENSHOT_DIR / "02_options_lab_opened.png")
            logger.info("✓ Options Lab tab opened")
            
            # Step 3: Enter SPY ticker
            logger.info(f"Entering ticker: {TEST_TICKER}")
            ticker_input = page.locator('input#options-ticker-input')
            if not ticker_input.is_visible():
                logger.error("Ticker input not found")
                return False
            
            ticker_input.clear()
            ticker_input.fill(TEST_TICKER)
            time.sleep(1)
            page.screenshot(path=SCREENSHOT_DIR / "03_ticker_entered.png")
            logger.info(f"✓ Ticker entered: {TEST_TICKER}")
            
            # Step 4: Click "Load Chain" button (NOT mock button)
            logger.info("Loading options chain...")
            load_btn = page.locator('button#options-load-btn')
            if not load_btn.is_visible():
                logger.error("Load button not found")
                return False
            
            load_btn.click()
            logger.info("Load button clicked, waiting for data...")
            
            # Wait for chain to load (check for loading spinner to disappear)
            time.sleep(5)  # Give it time to fetch data
            page.screenshot(path=SCREENSHOT_DIR / "04_chain_loading.png")
            
            # Step 5: Check data source indicator
            logger.info("Checking data source...")
            
            # Look for source indicator text
            source_indicators = [
                'alpaca',
                'yfinance', 
                'mock',
                'data source'
            ]
            
            page_content = page.content().lower()
            detected_source = None
            for indicator in source_indicators:
                if indicator in page_content:
                    detected_source = indicator
                    break
            
            if detected_source:
                logger.info(f"✓ Data source detected: {detected_source}")
                if detected_source == 'mock':
                    logger.warning("⚠ WARNING: Using MOCK data! Check OPTIONS_USE_ALPACA flag.")
            else:
                logger.warning("Could not determine data source")
            
            time.sleep(2)
            page.screenshot(path=SCREENSHOT_DIR / "05_data_source_check.png")
            
            # Step 6: Verify chain viewer has data
            logger.info("Verifying chain data...")
            
            # Look for table or data display
            chain_table = page.locator('#options-chain-table')
            if chain_table.is_visible():
                logger.info("✓ Options chain table visible")
                
                # Count rows
                rows = page.locator('#options-chain-table tbody tr')
                row_count = rows.count()
                logger.info(f"✓ Chain has {row_count} rows")
                
                if row_count == 0:
                    logger.warning("⚠ WARNING: Chain table is empty!")
                    
            else:
                logger.warning("Chain table #options-chain-table not found, checking for alternative display...")
                
                # Check for call/put radio buttons (more specific selector)
                chain_type_calls = page.locator('input[value="calls"]')
                chain_type_puts = page.locator('input[value="puts"]')
                
                if chain_type_calls.count() > 0 or chain_type_puts.count() > 0:
                    logger.info("✓ Call/Put radio buttons found - chain loaded!")
                    
                    # Check for data in status message
                    status_msg = page.locator('#options-status-message')
                    if status_msg.is_visible():
                        status_text = status_msg.inner_text()
                        logger.info(f"✓ Status message: {status_text[:100]}")
                else:
                    logger.error("❌ No chain data display found!")
            
            page.screenshot(path=SCREENSHOT_DIR / "06_chain_display.png")
            
            # Step 7: Test AI recommendations (if available)
            logger.info("Checking AI recommendations...")
            ai_rec_btn = page.locator('button:has-text("AI Recommendations")')
            if ai_rec_btn.is_visible():
                logger.info("AI Recommendations button found, clicking...")
                ai_rec_btn.click()
                time.sleep(3)
                page.screenshot(path=SCREENSHOT_DIR / "07_ai_recommendations.png")
                logger.info("✓ AI Recommendations tested")
            else:
                logger.info("AI Recommendations button not found (may not be visible)")
            
            # Step 8: Test strategy builder (if available)
            logger.info("Checking strategy builder...")
            strategy_tab = page.locator('a:has-text("Strategy Builder")')
            if strategy_tab.is_visible():
                logger.info("Strategy Builder tab found, clicking...")
                strategy_tab.click()
                time.sleep(2)
                page.screenshot(path=SCREENSHOT_DIR / "08_strategy_builder.png")
                logger.info("✓ Strategy Builder tested")
            else:
                logger.info("Strategy Builder tab not found")
            
            # Final screenshot
            page.screenshot(path=SCREENSHOT_DIR / "09_final_state.png")
            
            logger.info("=" * 60)
            logger.info("TEST SUMMARY")
            logger.info("=" * 60)
            logger.info(f"✓ Dashboard loaded successfully")
            logger.info(f"✓ Options Lab navigation successful")
            logger.info(f"✓ Ticker input successful ({TEST_TICKER})")
            logger.info(f"✓ Chain load attempted")
            logger.info(f"✓ Data source: {detected_source or 'unknown'}")
            logger.info(f"Screenshots saved to: {SCREENSHOT_DIR}")
            logger.info("=" * 60)
            
            # Check if we used real data
            used_real_data = detected_source in ['alpaca', 'yfinance']
            
            if detected_source == 'mock':
                logger.warning("\n⚠ IMPORTANT: Test used MOCK data!")
                logger.warning("To use real data:")
                logger.warning("1. Set OPTIONS_USE_ALPACA=1 in environment")
                logger.warning("2. Set Alpaca API credentials:")
                logger.warning("   - APCA_API_KEY_ID")
                logger.warning("   - APCA_API_SECRET_KEY")
                logger.warning("   - APCA_API_BASE_URL")
                logger.warning("OR")
                logger.warning("3. Ensure yfinance fallback is working (may require retry logic)")
            elif used_real_data:
                logger.info(f"\n✅ SUCCESS: Using real data from {detected_source.upper()}")
            
            return used_real_data  # Return True if using real data
            
        except Exception as e:
            logger.error(f"Test failed with error: {e}")
            page.screenshot(path=SCREENSHOT_DIR / "error_screenshot.png")
            return False
        
        finally:
            # Keep browser open for 5 seconds to review
            logger.info("Keeping browser open for 5 seconds...")
            time.sleep(5)
            browser.close()

def check_environment():
    """Check environment configuration."""
    logger.info("Checking environment configuration...")
    
    alpaca_enabled = os.getenv('OPTIONS_USE_ALPACA', '0') == '1'
    alpaca_key = os.getenv('APCA_API_KEY_ID')
    alpaca_secret = os.getenv('APCA_API_SECRET_KEY')
    
    logger.info(f"OPTIONS_USE_ALPACA: {alpaca_enabled}")
    logger.info(f"APCA_API_KEY_ID: {'Set' if alpaca_key else 'Not set'}")
    logger.info(f"APCA_API_SECRET_KEY: {'Set' if alpaca_secret else 'Not set'}")
    
    if alpaca_enabled and not (alpaca_key and alpaca_secret):
        logger.warning("⚠ Alpaca enabled but credentials missing!")
    
    if not alpaca_enabled:
        logger.info("ℹ Alpaca not enabled, will use yfinance fallback")
    
    return alpaca_enabled

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("OPTIONS LAB SPY TEST")
    logger.info("=" * 60)
    
    # Check environment first
    alpaca_configured = check_environment()
    
    # Run test
    success = test_options_lab_spy()
    
    if success:
        logger.info("\n✅ TEST PASSED: Options Lab working with real data")
        sys.exit(0)
    else:
        logger.error("\n❌ TEST FAILED: Options Lab using mock data or errors occurred")
        logger.error("See warnings above for configuration steps")
        sys.exit(1)
