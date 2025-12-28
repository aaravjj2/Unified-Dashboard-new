#!/usr/bin/env python3
"""
Comprehensive E2E Test for All Enhancements
Tests: Keys loading, Greeks calculator, AI recommendations, Flow analysis, All callbacks
"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
SERVER_URL = "http://localhost:8053"
TICKER = "AAPL"

def init_driver():
    """Initialize headless Chrome driver."""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def test_keys_loading():
    """Test 1: Verify 42 API keys loaded."""
    logger.info("\n=== TEST 1: Keys Loading ===")
    try:
        with open('/home/aarav/Unified-Dashboard/server_enhanced.log', 'r') as f:
            logs = f.read()
            if '🔑 Loaded 42 API keys' in logs:
                logger.info("✅ 42 API keys loaded from keys.env")
                return True
            else:
                logger.error("❌ Keys not loaded properly")
                return False
    except Exception as e:
        logger.error(f"❌ Error checking keys: {e}")
        return False

def test_async_components(driver):
    """Test 2: Verify async-dropdown.js loads without errors."""
    logger.info("\n=== TEST 2: Async Components ===")
    try:
        driver.get(SERVER_URL)
        time.sleep(5)
        
        # Check for JavaScript errors
        logs = driver.get_log('browser')
        js_errors = [log for log in logs if log['level'] == 'SEVERE' and 'async-dropdown' in log['message']]
        
        if not js_errors:
            logger.info("✅ No async-dropdown.js errors (eager_loading=True worked)")
            return True
        else:
            logger.error(f"❌ Found {len(js_errors)} async-dropdown errors")
            for error in js_errors[:3]:
                logger.error(f"  {error['message']}")
            return False
    except Exception as e:
        logger.error(f"❌ Error checking async components: {e}")
        return False

def test_options_chain_loading(driver):
    """Test 3: Load options chain and verify data."""
    logger.info("\n=== TEST 3: Options Chain Loading ===")
    try:
        # Navigate to Options Lab
        driver.get(SERVER_URL)
        time.sleep(2)
        
        # Find and click Options Lab tab
        tabs = driver.find_elements(By.CSS_SELECTOR, '.custom-tab')
        for tab in tabs:
            if 'Options Lab' in tab.text:
                tab.click()
                logger.info("Clicked Options Lab tab")
                break
        
        time.sleep(2)
        
        # Enter ticker
        ticker_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'alpaca-ticker-input'))
        )
        ticker_input.clear()
        ticker_input.send_keys(TICKER)
        logger.info(f"Entered ticker: {TICKER}")
        
        # Click Load button
        load_btn = driver.find_element(By.ID, 'alpaca-load-chain')
        load_btn.click()
        logger.info("Clicked Load Chain button")
        
        # Wait for data to load
        time.sleep(8)
        
        # Check if expiration dropdown populated
        exp_dropdown = driver.find_element(By.ID, 'alpaca-expiration-dropdown')
        options = exp_dropdown.find_elements(By.TAG_NAME, 'option')
        
        if len(options) > 1:  # More than just placeholder
            logger.info(f"✅ Options chain loaded - {len(options)-1} expirations found")
            return True
        else:
            logger.error("❌ No options chain data loaded")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error loading options chain: {e}")
        return False

def test_greeks_calculation(driver):
    """Test 4: Verify real Greeks (Black-Scholes) calculated."""
    logger.info("\n=== TEST 4: Greeks Calculation ===")
    try:
        # Select first expiration
        exp_dropdown = driver.find_element(By.ID, 'alpaca-expiration-dropdown')
        options = exp_dropdown.find_elements(By.TAG_NAME, 'option')
        if len(options) > 1:
            options[1].click()
            logger.info(f"Selected expiration: {options[1].text}")
            time.sleep(3)
        
        # Check Greeks panel
        delta_elem = driver.find_element(By.ID, 'greeks-delta')
        gamma_elem = driver.find_element(By.ID, 'greeks-gamma')
        theta_elem = driver.find_element(By.ID, 'greeks-theta')
        vega_elem = driver.find_element(By.ID, 'greeks-vega')
        
        delta_val = delta_elem.text
        gamma_val = gamma_elem.text
        theta_val = theta_elem.text
        vega_val = vega_elem.text
        
        # Check if values are real (not 0.00 or N/A)
        if delta_val not in ['0.00', 'N/A', ''] and gamma_val not in ['0.00', 'N/A', '']:
            logger.info(f"✅ Real Greeks calculated:")
            logger.info(f"   Delta: {delta_val}, Gamma: {gamma_val}")
            logger.info(f"   Theta: {theta_val}, Vega: {vega_val}")
            return True
        else:
            logger.error("❌ Greeks not calculated (showing defaults)")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error checking Greeks: {e}")
        return False

def test_ai_recommendations(driver):
    """Test 5: Verify AI recommendations using GROQ."""
    logger.info("\n=== TEST 5: AI Recommendations ===")
    try:
        # Click ML Analysis subtab
        ml_tab = driver.find_element(By.ID, 'alpaca-ml-tab')
        ml_tab.click()
        logger.info("Clicked ML Analysis tab")
        time.sleep(3)
        
        # Check for recommendations
        rec_elem = driver.find_element(By.ID, 'ml-recommendations')
        recommendations = rec_elem.text
        
        if recommendations and len(recommendations) > 50:
            logger.info(f"✅ AI recommendations generated ({len(recommendations)} chars)")
            logger.info(f"   Preview: {recommendations[:100]}...")
            return True
        else:
            logger.warning(f"⚠️ Recommendations short or empty: {recommendations[:50]}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error checking AI recommendations: {e}")
        return False

def test_flow_analysis(driver):
    """Test 6: Verify Flow analysis (P/C ratio, max pain)."""
    logger.info("\n=== TEST 6: Flow Analysis ===")
    try:
        # Click Flow subtab
        flow_tab = driver.find_element(By.ID, 'alpaca-flow-tab')
        flow_tab.click()
        logger.info("Clicked Flow Analysis tab")
        time.sleep(3)
        
        # Check P/C ratios
        pcr_vol = driver.find_element(By.ID, 'flow-pcr-volume').text
        pcr_oi = driver.find_element(By.ID, 'flow-pcr-oi').text
        max_pain = driver.find_element(By.ID, 'flow-max-pain').text
        sentiment = driver.find_element(By.ID, 'flow-sentiment').text
        
        if pcr_vol not in ['0.00', 'N/A'] and max_pain.startswith('$'):
            logger.info(f"✅ Flow analysis working:")
            logger.info(f"   P/C Volume: {pcr_vol}, P/C OI: {pcr_oi}")
            logger.info(f"   Max Pain: {max_pain}, Sentiment: {sentiment}")
            return True
        else:
            logger.error("❌ Flow analysis not working (default values)")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error checking flow analysis: {e}")
        return False

def test_strategy_builder(driver):
    """Test 7: Verify Strategy Builder works."""
    logger.info("\n=== TEST 7: Strategy Builder ===")
    try:
        # Click Strategy Builder tab
        strategy_tab = driver.find_element(By.ID, 'alpaca-strategy-tab')
        strategy_tab.click()
        logger.info("Clicked Strategy Builder tab")
        time.sleep(2)
        
        # Select a strategy
        strategy_dropdown = driver.find_element(By.ID, 'alpaca-strategy-type')
        options = strategy_dropdown.find_elements(By.TAG_NAME, 'option')
        if len(options) > 1:
            options[1].click()  # Select first strategy
            logger.info(f"Selected strategy: {options[1].text}")
            time.sleep(2)
        
        # Check if payoff chart rendered
        payoff_chart = driver.find_element(By.ID, 'alpaca-strategy-payoff')
        if payoff_chart.is_displayed():
            logger.info("✅ Strategy Builder working (payoff chart visible)")
            return True
        else:
            logger.error("❌ Strategy payoff chart not rendered")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error checking strategy builder: {e}")
        return False

def run_all_tests():
    """Run comprehensive E2E test suite."""
    logger.info("=" * 60)
    logger.info("COMPREHENSIVE E2E TEST - All Enhancements")
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    results = {}
    driver = None
    
    try:
        # Test 1: Keys loading (no driver needed)
        results['Keys Loading'] = test_keys_loading()
        
        # Initialize driver for browser tests
        driver = init_driver()
        logger.info("✅ Chrome driver initialized")
        
        # Test 2: Async components
        results['Async Components'] = test_async_components(driver)
        
        # Test 3: Options chain loading
        results['Chain Loading'] = test_options_chain_loading(driver)
        
        # Test 4: Greeks calculation
        results['Greeks Calculation'] = test_greeks_calculation(driver)
        
        # Test 5: AI recommendations
        results['AI Recommendations'] = test_ai_recommendations(driver)
        
        # Test 6: Flow analysis
        results['Flow Analysis'] = test_flow_analysis(driver)
        
        # Test 7: Strategy Builder
        results['Strategy Builder'] = test_strategy_builder(driver)
        
    except Exception as e:
        logger.error(f"❌ Test suite error: {e}")
        
    finally:
        if driver:
            driver.quit()
            logger.info("Chrome driver closed")
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
    
    logger.info("-" * 60)
    logger.info(f"TOTAL: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    logger.info(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
