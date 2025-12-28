#!/usr/bin/env python3
"""
Comprehensive End-to-End Test Suite
Tests all major features with real data (not mock):
1. Options Lab with SPY
2. Research Lab RAG queries
3. Forecaster
4. AI Chatbot
5. Data ingestion status
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
SCREENSHOT_DIR = Path("screenshots/comprehensive_e2e")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

class ComprehensiveE2ETest:
    def __init__(self):
        self.test_results = {
            'options_lab': False,
            'research_lab_rag': False,
            'forecaster': False,
            'chatbot': False,
            'data_sources': {}
        }
        
    def run_all_tests(self):
        """Run all comprehensive tests."""
        logger.info("=" * 60)
        logger.info("COMPREHENSIVE E2E TEST SUITE")
        logger.info("=" * 60)
        
        with sync_playwright() as p:
            # Launch browser (non-headless)
            browser = p.chromium.launch(headless=False, slow_mo=300)
            context = browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = context.new_page()
            
            try:
                # Test 1: Load dashboard
                logger.info("\n[TEST 1] Loading Dashboard")
                logger.info("=" * 60)
                if not self.test_dashboard_load(page):
                    logger.error("Dashboard load failed, aborting tests")
                    return False
                
                # Test 2: Options Lab with SPY
                logger.info("\n[TEST 2] Testing Options Lab with SPY")
                logger.info("=" * 60)
                self.test_results['options_lab'] = self.test_options_lab(page)
                
                # Test 3: Research Lab RAG
                logger.info("\n[TEST 3] Testing Research Lab RAG")
                logger.info("=" * 60)
                self.test_results['research_lab_rag'] = self.test_research_lab_rag(page)
                
                # Test 4: Forecaster
                logger.info("\n[TEST 4] Testing Forecaster")
                logger.info("=" * 60)
                self.test_results['forecaster'] = self.test_forecaster(page)
                
                # Test 5: AI Chatbot
                logger.info("\n[TEST 5] Testing AI Chatbot")
                logger.info("=" * 60)
                self.test_results['chatbot'] = self.test_chatbot(page)
                
                # Print summary
                self.print_summary()
                
                # Keep browser open for review
                logger.info("\nKeeping browser open for 10 seconds for review...")
                time.sleep(10)
                
                return all([
                    self.test_results['options_lab'],
                    self.test_results['research_lab_rag'],
                    self.test_results['forecaster']
                ])
                
            except Exception as e:
                logger.error(f"Test suite failed with error: {e}")
                page.screenshot(path=SCREENSHOT_DIR / "error_screenshot.png")
                return False
            finally:
                browser.close()
    
    def test_dashboard_load(self, page):
        """Test dashboard loading."""
        try:
            logger.info(f"Loading {DASHBOARD_URL}...")
            page.goto(DASHBOARD_URL, wait_until='domcontentloaded', timeout=60000)
            time.sleep(3)
            page.screenshot(path=SCREENSHOT_DIR / "01_dashboard_loaded.png")
            logger.info("✓ Dashboard loaded successfully")
            return True
        except Exception as e:
            logger.error(f"✗ Dashboard load failed: {e}")
            return False
    
    def test_options_lab(self, page):
        """Test Options Lab with SPY ticker."""
        try:
            # Navigate to Options Lab
            logger.info("Navigating to Options Lab...")
            options_tab = page.locator('#tab-options_lab')
            options_tab.click()
            time.sleep(2)
            page.screenshot(path=SCREENSHOT_DIR / "02_options_lab_opened.png")
            
            # Enter SPY ticker
            logger.info("Entering SPY ticker...")
            ticker_input = page.locator('input#options-ticker-input')
            ticker_input.clear()
            ticker_input.fill('SPY')
            time.sleep(1)
            
            # Click Load button
            logger.info("Loading options chain...")
            load_btn = page.locator('button#options-load-btn')
            load_btn.click()
            time.sleep(5)
            page.screenshot(path=SCREENSHOT_DIR / "03_spy_chain_loaded.png")
            
            # Check data source
            page_content = page.content().lower()
            if 'alpaca' in page_content:
                self.test_results['data_sources']['options'] = 'alpaca'
                logger.info("✓ Options Lab using ALPACA data")
                return True
            elif 'yfinance' in page_content:
                self.test_results['data_sources']['options'] = 'yfinance'
                logger.info("✓ Options Lab using yfinance data")
                return True
            elif 'mock' in page_content:
                self.test_results['data_sources']['options'] = 'mock'
                logger.warning("⚠ Options Lab using MOCK data")
                return False
            else:
                logger.warning("? Could not determine data source")
                return False
                
        except Exception as e:
            logger.error(f"✗ Options Lab test failed: {e}")
            page.screenshot(path=SCREENSHOT_DIR / "error_options_lab.png")
            return False
    
    def test_research_lab_rag(self, page):
        """Test Research Lab RAG queries."""
        try:
            # Navigate to Research Lab
            logger.info("Navigating to Research Lab...")
            research_tab = page.locator('#tab-research_lab')
            research_tab.click()
            time.sleep(2)
            page.screenshot(path=SCREENSHOT_DIR / "04_research_lab_opened.png")
            
            # Click RAG Chat subtab
            logger.info("Opening RAG Chat...")
            rag_chat_tab = page.locator('a:has-text("RAG Chat")')
            if rag_chat_tab.count() > 0:
                rag_chat_tab.first.click()
                time.sleep(2)
            
            # Enter query using correct ID
            logger.info("Submitting RAG query...")
            query_input = page.locator('#rl-rag-query-input')
            if query_input.is_visible():
                query_input.fill("What are the key market trends?")
                time.sleep(1)
                
                # Click submit using correct ID
                submit_btn = page.locator('#rl-rag-run-btn')
                if submit_btn.is_visible():
                    submit_btn.click()
                    logger.info("Query submitted, waiting for response...")
                    time.sleep(5)
                    page.screenshot(path=SCREENSHOT_DIR / "05_rag_response.png")
                    
                    # Check for response using correct ID
                    answer_text = page.evaluate("""
                        () => {
                            const answerDiv = document.querySelector('#rl-rag-answer');
                            return answerDiv ? answerDiv.innerText : '';
                        }
                    """)
                    
                    if answer_text and len(answer_text) > 30:
                        # Check if using mock
                        if 'mock' in answer_text.lower():
                            self.test_results['data_sources']['rag'] = 'mock'
                            logger.warning("⚠ RAG using MOCK adapter")
                            return False
                        else:
                            logger.info(f"✓ RAG query completed ({len(answer_text)} chars)")
                            return True
            
            logger.warning("? Could not complete RAG test")
            return False
            
        except Exception as e:
            logger.error(f"✗ RAG test failed: {e}")
            page.screenshot(path=SCREENSHOT_DIR / "error_rag.png")
            return False
    
    def test_forecaster(self, page):
        """Test Forecaster."""
        try:
            # Stay in Research Lab (or navigate if needed)
            logger.info("Testing Forecaster...")
            
            # Use JavaScript to set ticker and generate forecast (elements may not be visible)
            page.evaluate("""
                () => {
                    const ticker = document.querySelector('#rl-forecast-ticker');
                    if (ticker) {
                        ticker.value = 'NVDA';
                        ticker.dispatchEvent(new Event('input', { bubbles: true }));
                        ticker.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }
            """)
            time.sleep(1)
            
            # Click generate button
            page.evaluate("""
                () => {
                    const btn = document.querySelector('#rl-forecast-run-btn');
                    if (btn) btn.click();
                }
            """)
            
            logger.info("Forecast generation started...")
            time.sleep(5)
            page.screenshot(path=SCREENSHOT_DIR / "06_forecast_result.png")
            
            # Check for result
            result_text = page.evaluate("""
                () => {
                    const result = document.querySelector('#rl-forecast-result');
                    return result ? result.innerText : '';
                }
            """)
            
            if result_text and ("Prediction:" in result_text or "Analysis" in result_text or "PREDICTION" in result_text):
                if 'mock' in result_text.lower():
                    self.test_results['data_sources']['forecaster'] = 'mock'
                    logger.warning("⚠ Forecaster using MOCK adapter")
                    return False
                else:
                    logger.info(f"✓ Forecast generated")
                    logger.info(f"Preview: {result_text[:120]}...")
                    return True
            else:
                logger.warning(f"? Forecast result unclear: {result_text[:100]}")
                return False
            
        except Exception as e:
            logger.error(f"✗ Forecaster test failed: {e}")
            page.screenshot(path=SCREENSHOT_DIR / "error_forecaster.png")
            return False
    
    def test_chatbot(self, page):
        """Test AI Chatbot."""
        try:
            # Look for chatbot FAB
            logger.info("Testing AI Chatbot...")
            chatbot_fab = page.locator('#chatbot-toggle-btn')
            
            if chatbot_fab.is_visible():
                # Click to open
                chatbot_fab.click()
                time.sleep(2)
                page.screenshot(path=SCREENSHOT_DIR / "07_chatbot_opened.png")
                
                # Enter message
                chatbot_input = page.locator('#chatbot-input')
                if chatbot_input.is_visible():
                    chatbot_input.fill("What is the market outlook?")
                    time.sleep(1)
                    
                    # Click send
                    send_btn = page.locator('#chatbot-send-btn')
                    send_btn.click()
                    logger.info("Chatbot message sent...")
                    time.sleep(5)
                    page.screenshot(path=SCREENSHOT_DIR / "08_chatbot_response.png")
                    
                    # Check for response
                    messages = page.locator('#chatbot-messages')
                    if messages.is_visible():
                        logger.info("✓ Chatbot responded")
                        return True
            else:
                logger.warning("? Chatbot FAB not found")
                
            return False
            
        except Exception as e:
            logger.error(f"✗ Chatbot test failed: {e}")
            page.screenshot(path=SCREENSHOT_DIR / "error_chatbot.png")
            return False
    
    def print_summary(self):
        """Print test summary."""
        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        
        total_tests = 4
        passed_tests = sum([
            self.test_results['options_lab'],
            self.test_results['research_lab_rag'],
            self.test_results['forecaster'],
            self.test_results['chatbot']
        ])
        
        logger.info(f"Tests Passed: {passed_tests}/{total_tests}")
        logger.info("")
        logger.info(f"Options Lab (SPY):     {'✅ PASS' if self.test_results['options_lab'] else '❌ FAIL'}")
        logger.info(f"Research Lab RAG:      {'✅ PASS' if self.test_results['research_lab_rag'] else '❌ FAIL'}")
        logger.info(f"Forecaster:            {'✅ PASS' if self.test_results['forecaster'] else '❌ FAIL'}")
        logger.info(f"AI Chatbot:            {'✅ PASS' if self.test_results['chatbot'] else '❌ FAIL'}")
        logger.info("")
        logger.info("Data Sources:")
        for feature, source in self.test_results['data_sources'].items():
            status = "✅" if source != 'mock' else "⚠"
            logger.info(f"  {status} {feature}: {source.upper()}")
        logger.info("=" * 60)
        logger.info(f"Screenshots saved to: {SCREENSHOT_DIR}")
        logger.info("=" * 60)
        
        # Configuration notes
        if any(source == 'mock' for source in self.test_results['data_sources'].values()):
            logger.warning("\n⚠ CONFIGURATION NOTES:")
            logger.warning("Some features are using MOCK adapters.")
            logger.warning("")
            logger.warning("To enable real LLM:")
            logger.warning("  export LLM_BACKEND=huggingface")
            logger.warning("  export HF_MODEL_NAME=TinyLlama/TinyLlama-1.1B-Chat-v1.0")
            logger.warning("OR")
            logger.warning("  export LLM_BACKEND=openai")
            logger.warning("  export OPENAI_API_KEY=your-key-here")
            logger.warning("")
            logger.warning("To enable Alpaca options:")
            logger.warning("  export OPTIONS_USE_ALPACA=1")
            logger.warning("  export APCA_API_KEY_ID=your-key")
            logger.warning("  export APCA_API_SECRET_KEY=your-secret")

if __name__ == "__main__":
    tester = ComprehensiveE2ETest()
    success = tester.run_all_tests()
    
    if success:
        logger.info("\n✅ ALL CRITICAL TESTS PASSED")
        sys.exit(0)
    else:
        logger.error("\n❌ SOME TESTS FAILED")
        logger.error("Review summary above for details")
        sys.exit(1)
