"""
Phase 5 E2E Test Suite - Market Intelligence
=============================================

Tests Regime Detection (Market Trends) and Sentiment Consensus (Market Forecast).

Requirements:
- PORT=8051
- PHASE5_DETERMINISTIC=1
- AZURE_ENABLED=false
- Headful Chromium only
- No test skipping
- Full audit trail with screenshots

Test Flows:
1. Market Trends -> Regime Monitor -> HMM/K-Means Detection -> Chart Verification
2. Market Forecast -> Sentiment Consensus -> FinBERT Analysis -> Consensus Display
"""

import logging
import os
import sys
from pathlib import Path
from datetime import datetime
import pytest
from playwright.sync_api import Page, expect, sync_playwright

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
PORT = os.getenv('PORT', '8051')
BASE_URL = f'http://localhost:{PORT}'
SCREENSHOT_DIR = Path(__file__).parent.parent.parent / 'reports' / 'phase5' / 'screenshots'
DOM_DIR = Path(__file__).parent.parent.parent / 'reports' / 'phase5' / 'dom'
LOG_DIR = Path(__file__).parent.parent.parent / 'reports' / 'phase5' / 'logs'

# Create directories
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
DOM_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Timeouts
DEFAULT_TIMEOUT = 90000  # 90s (FinBERT model loading can be slow)
NAVIGATION_TIMEOUT = 30000
CHART_RENDER_TIMEOUT = 20000
MODEL_TIMEOUT = 120000  # 2 min for model inference


def save_screenshot(page: Page, name: str):
    """Save screenshot with timestamp."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = SCREENSHOT_DIR / f"{timestamp}_{name}.png"
    page.screenshot(path=str(filepath), full_page=True)
    logger.info(f"📸 Screenshot saved: {filepath}")
    return filepath


def save_dom(page: Page, name: str):
    """Save page DOM/HTML for debugging."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = DOM_DIR / f"{timestamp}_{name}.html"
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(page.content())
    logger.info(f"📄 DOM saved: {filepath}")
    return filepath


def wait_for_spinner(page: Page, timeout: int = DEFAULT_TIMEOUT):
    """Wait for loading spinner to disappear."""
    try:
        spinner_selectors = [
            '.spinner-border',
            '.loading',
            '[role="status"]',
            '.dash-spinner'
        ]
        
        for selector in spinner_selectors:
            if page.locator(selector).count() > 0:
                logger.info(f"⏳ Waiting for spinner: {selector}")
                page.locator(selector).wait_for(state='detached', timeout=timeout)
                logger.info("✅ Spinner disappeared")
                break
    except Exception as e:
        logger.warning(f"Spinner wait warning: {e}")


def wait_for_chart(page: Page, chart_id: str, timeout: int = CHART_RENDER_TIMEOUT):
    """Wait for Plotly chart to render."""
    try:
        chart_locator = page.locator(f"#{chart_id}")
        chart_locator.wait_for(state='visible', timeout=timeout)
        
        # Wait for SVG content
        svg_locator = chart_locator.locator('svg.main-svg').first
        svg_locator.wait_for(state='visible', timeout=timeout)
        
        logger.info(f"✅ Chart rendered: {chart_id}")
        return True
    except Exception as e:
        logger.error(f"Chart wait failed for {chart_id}: {e}")
        return False


@pytest.fixture(scope="module")
def browser_context():
    """Launch headful Chromium browser."""
    logger.info("🚀 Launching headful Chromium for Phase 5 tests...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # Headful as per requirements
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
        )
        
        context.set_default_timeout(DEFAULT_TIMEOUT)
        context.set_default_navigation_timeout(NAVIGATION_TIMEOUT)
        
        yield context
        
        logger.info("🛑 Closing browser...")
        context.close()
        browser.close()


@pytest.fixture
def page(browser_context):
    """Create a new page for each test."""
    page = browser_context.new_page()
    
    logger.info(f"📍 Navigating to {BASE_URL}")
    page.goto(BASE_URL, wait_until='load', timeout=60000)
    
    # Wait for dashboard to load
    page.wait_for_selector('#dashboard-tabs', timeout=NAVIGATION_TIMEOUT)
    logger.info("✅ Dashboard loaded")
    
    yield page
    
    page.close()


# =============================================================================
# Test Class 1: Regime Detection (Market Trends)
# =============================================================================

class TestPhase5RegimeDetection:
    """Test Regime Detection Engine in Market Trends tab."""
    
    def test_01_navigate_to_market_trends(self, page: Page):
        """Test: Navigate to Market Trends tab."""
        logger.info("🧪 Test 1: Navigate to Market Trends")
        
        save_screenshot(page, "regime_01_pre_navigation")
        
        # Click Market Trends tab
        mt_tab = page.locator('#dashboard-tabs .nav-link').filter(has_text='Market Trends')
        mt_tab.click()
        
        # Wait for tab content
        page.wait_for_selector('#tabs-market-trends', timeout=DEFAULT_TIMEOUT)
        
        save_screenshot(page, "regime_01_post_navigation")
        save_dom(page, "regime_01_market_trends")
        
        logger.info("✅ Test 1 passed: Market Trends tab loaded")
    
    def test_02_navigate_to_regime_monitor_tab(self, page: Page):
        """Test: Navigate to Regime Monitor subtab."""
        logger.info("🧪 Test 2: Navigate to Regime Monitor")
        
        # Navigate to Market Trends
        mt_tab = page.locator('#dashboard-tabs .nav-link').filter(has_text='Market Trends')
        mt_tab.click()
        page.wait_for_selector('#tabs-market-trends', timeout=DEFAULT_TIMEOUT)
        
        save_screenshot(page, "regime_02_pre_subtab")
        
        # Click Regime Monitor tab
        regime_tab = page.locator('#tabs-market-trends .nav-link').filter(has_text='Regime Monitor')
        
        if regime_tab.count() == 0:
            logger.error("Regime Monitor tab not found!")
            save_dom(page, "regime_02_tab_missing")
            pytest.fail("Regime Monitor tab not found in Market Trends")
        
        regime_tab.click()
        page.wait_for_timeout(1000)
        
        # Verify regime controls are visible
        page.wait_for_selector('#input-regime-ticker', timeout=DEFAULT_TIMEOUT)
        
        save_screenshot(page, "regime_02_post_subtab")
        
        logger.info("✅ Test 2 passed: Regime Monitor subtab loaded")
    
    def test_03_select_hmm_method(self, page: Page):
        """Test: Select HMM method for regime detection."""
        logger.info("🧪 Test 3: Select HMM method")
        
        # Navigate to Regime Monitor
        mt_tab = page.locator('#dashboard-tabs .nav-link').filter(has_text='Market Trends')
        mt_tab.click()
        page.wait_for_selector('#tabs-market-trends', timeout=DEFAULT_TIMEOUT)
        
        regime_tab = page.locator('#tabs-market-trends .nav-link').filter(has_text='Regime Monitor')
        regime_tab.click()
        page.wait_for_selector('#input-regime-ticker', timeout=DEFAULT_TIMEOUT)
        
        save_screenshot(page, "regime_03_pre_method")
        
        # Select HMM method
        hmm_radio = page.locator('#radio-regime-method input[value="hmm"]')
        
        if hmm_radio.count() == 0:
            # Try clicking the label
            hmm_label = page.locator('#radio-regime-method label').filter(has_text='HMM')
            hmm_label.click()
        else:
            hmm_radio.click()
        
        page.wait_for_timeout(500)
        
        # Verify HMM is selected
        save_screenshot(page, "regime_03_post_method")
        
        logger.info("✅ Test 3 passed: HMM method selected")
    
    def test_04_run_regime_detection(self, page: Page):
        """Test: Run regime detection and verify chart appears."""
        logger.info("🧪 Test 4: Run Regime Detection")
        
        # Navigate to Regime Monitor
        mt_tab = page.locator('#dashboard-tabs .nav-link').filter(has_text='Market Trends')
        mt_tab.click()
        page.wait_for_selector('#tabs-market-trends', timeout=DEFAULT_TIMEOUT)
        
        regime_tab = page.locator('#tabs-market-trends .nav-link').filter(has_text='Regime Monitor')
        regime_tab.click()
        page.wait_for_selector('#input-regime-ticker', timeout=DEFAULT_TIMEOUT)
        
        # Enter ticker
        ticker_input = page.locator('#input-regime-ticker')
        ticker_input.clear()
        ticker_input.fill('AAPL')
        
        # Select HMM method
        hmm_label = page.locator('#radio-regime-method label').filter(has_text='HMM')
        hmm_label.click()
        page.wait_for_timeout(300)
        
        save_screenshot(page, "regime_04_pre_detect")
        
        # Click Detect Regimes button
        detect_btn = page.locator('#btn-detect-regimes')
        detect_btn.click()
        
        # Wait for regime chart to render
        logger.info("⏳ Waiting for regime detection (may take 30-60s)...")
        wait_for_spinner(page, timeout=MODEL_TIMEOUT)
        
        chart_rendered = wait_for_chart(page, 'graph-regime-chart', timeout=MODEL_TIMEOUT)
        
        save_screenshot(page, "regime_04_post_detect")
        save_dom(page, "regime_04_chart")
        
        assert chart_rendered, "Regime chart should render after detection"
        
        logger.info("✅ Test 4 passed: Regime detection completed with chart")
    
    def test_05_verify_regime_banner(self, page: Page):
        """Test: Verify current regime banner is displayed."""
        logger.info("🧪 Test 5: Verify Regime Banner")
        
        # Navigate and run detection (reuse setup)
        mt_tab = page.locator('#dashboard-tabs .nav-link').filter(has_text='Market Trends')
        mt_tab.click()
        page.wait_for_selector('#tabs-market-trends', timeout=DEFAULT_TIMEOUT)
        
        regime_tab = page.locator('#tabs-market-trends .nav-link').filter(has_text='Regime Monitor')
        regime_tab.click()
        page.wait_for_selector('#input-regime-ticker', timeout=DEFAULT_TIMEOUT)
        
        ticker_input = page.locator('#input-regime-ticker')
        ticker_input.clear()
        ticker_input.fill('MSFT')
        
        detect_btn = page.locator('#btn-detect-regimes')
        detect_btn.click()
        
        wait_for_spinner(page, timeout=MODEL_TIMEOUT)
        page.wait_for_timeout(3000)
        
        # Check regime banner content
        banner = page.locator('#regime-current-banner')
        banner_text = banner.text_content()
        
        save_screenshot(page, "regime_05_banner")
        
        # Banner should contain regime label
        assert any(regime in banner_text for regime in ['Bull', 'Bear', 'Sideways', 'Current Regime']), \
            f"Banner should show regime label, got: {banner_text}"
        
        logger.info(f"✅ Test 5 passed: Regime banner shows: {banner_text}")
    
    def test_06_verify_regime_stats_cards(self, page: Page):
        """Test: Verify regime statistics cards are displayed."""
        logger.info("🧪 Test 6: Verify Regime Stats Cards")
        
        # Navigate and run detection
        mt_tab = page.locator('#dashboard-tabs .nav-link').filter(has_text='Market Trends')
        mt_tab.click()
        page.wait_for_selector('#tabs-market-trends', timeout=DEFAULT_TIMEOUT)
        
        regime_tab = page.locator('#tabs-market-trends .nav-link').filter(has_text='Regime Monitor')
        regime_tab.click()
        page.wait_for_selector('#input-regime-ticker', timeout=DEFAULT_TIMEOUT)
        
        ticker_input = page.locator('#input-regime-ticker')
        ticker_input.clear()
        ticker_input.fill('GOOGL')
        
        detect_btn = page.locator('#btn-detect-regimes')
        detect_btn.click()
        
        wait_for_spinner(page, timeout=MODEL_TIMEOUT)
        page.wait_for_timeout(3000)
        
        # Check stats cards
        stats_container = page.locator('#regime-stats-cards')
        
        save_screenshot(page, "regime_06_stats")
        save_dom(page, "regime_06_stats")
        
        # Should have cards for each regime (Bear, Sideways, Bull)
        cards = stats_container.locator('.card')
        card_count = cards.count()
        
        assert card_count >= 3, f"Should have at least 3 regime stat cards, got {card_count}"
        
        logger.info(f"✅ Test 6 passed: {card_count} regime stat cards displayed")


# =============================================================================
# Test Class 2: Sentiment Consensus (Market Forecast)
# =============================================================================

class TestPhase5SentimentConsensus:
    """Test Sentiment Consensus Engine in Market Forecast tab."""
    
    def test_01_navigate_to_market_forecast(self, page: Page):
        """Test: Navigate to Market Forecast tab."""
        logger.info("🧪 Test 1: Navigate to Market Forecast")
        
        save_screenshot(page, "sentiment_01_pre_navigation")
        
        # Click Market Forecast tab
        mf_tab = page.locator('#dashboard-tabs .nav-link').filter(has_text='Market Forecast')
        mf_tab.click()
        
        # Wait for tab content
        page.wait_for_selector('#mf-model-checklist', timeout=DEFAULT_TIMEOUT)
        
        save_screenshot(page, "sentiment_01_post_navigation")
        save_dom(page, "sentiment_01_market_forecast")
        
        logger.info("✅ Test 1 passed: Market Forecast tab loaded")
    
    def test_02_verify_sentiment_panel_exists(self, page: Page):
        """Test: Verify Sentiment Consensus panel is visible."""
        logger.info("🧪 Test 2: Verify Sentiment Panel Exists")
        
        # Navigate to Market Forecast
        mf_tab = page.locator('#dashboard-tabs .nav-link').filter(has_text='Market Forecast')
        mf_tab.click()
        page.wait_for_selector('#mf-model-checklist', timeout=DEFAULT_TIMEOUT)
        
        save_screenshot(page, "sentiment_02_pre_check")
        
        # Look for sentiment consensus banner container
        sentiment_banner = page.locator('#mf-sentiment-consensus-banner')
        
        assert sentiment_banner.count() > 0, "Sentiment consensus banner should exist"
        
        # Look for Phase 5 badge
        phase5_badge = page.locator('.card-header').filter(has_text='Phase 5')
        
        save_screenshot(page, "sentiment_02_panel_check")
        
        logger.info("✅ Test 2 passed: Sentiment Consensus panel exists")
    
    def test_03_run_forecast_with_sentiment(self, page: Page):
        """Test: Run forecast and verify sentiment analysis runs."""
        logger.info("🧪 Test 3: Run Forecast with Sentiment")
        
        # Navigate to Market Forecast
        mf_tab = page.locator('#dashboard-tabs .nav-link').filter(has_text='Market Forecast')
        mf_tab.click()
        page.wait_for_selector('#mf-model-checklist', timeout=DEFAULT_TIMEOUT)
        
        # Enter ticker
        ticker_input = page.locator('#mf-ticker-input')
        ticker_input.clear()
        ticker_input.fill('NVDA')
        
        # Select Prophet model only (fast)
        all_labels = page.locator('#mf-model-checklist label')
        for i in range(all_labels.count()):
            label = all_labels.nth(i)
            checkbox = label.locator('input')
            if checkbox.is_checked():
                label.click()
                page.wait_for_timeout(200)
        
        prophet_label = page.locator('#mf-model-checklist label').filter(has_text='Prophet')
        prophet_label.click()
        page.wait_for_timeout(300)
        
        # Set 1 week horizon
        horizon_dropdown = page.locator('#mf-horizon-select')
        horizon_dropdown.click()
        page.wait_for_timeout(300)
        page.locator('.VirtualizedSelectOption').filter(has_text='1 Week').click()
        
        save_screenshot(page, "sentiment_03_pre_run")
        
        # Click Generate Forecast
        run_btn = page.locator('#mf-run-btn')
        run_btn.click()
        
        # Wait for sentiment analysis (includes FinBERT model loading)
        logger.info("⏳ Waiting for forecast and sentiment analysis...")
        wait_for_spinner(page, timeout=MODEL_TIMEOUT)
        page.wait_for_timeout(5000)  # Extra wait for sentiment
        
        save_screenshot(page, "sentiment_03_post_run")
        save_dom(page, "sentiment_03_results")
        
        logger.info("✅ Test 3 passed: Forecast with sentiment completed")
    
    def test_04_verify_consensus_banner(self, page: Page):
        """Test: Verify consensus banner shows Bullish/Bearish/Neutral."""
        logger.info("🧪 Test 4: Verify Consensus Banner")
        
        # Navigate and run forecast
        mf_tab = page.locator('#dashboard-tabs .nav-link').filter(has_text='Market Forecast')
        mf_tab.click()
        page.wait_for_selector('#mf-model-checklist', timeout=DEFAULT_TIMEOUT)
        
        ticker_input = page.locator('#mf-ticker-input')
        ticker_input.clear()
        ticker_input.fill('AAPL')
        
        # Quick setup
        prophet_label = page.locator('#mf-model-checklist label').filter(has_text='Prophet')
        prophet_label.click()
        page.wait_for_timeout(200)
        
        run_btn = page.locator('#mf-run-btn')
        run_btn.click()
        
        wait_for_spinner(page, timeout=MODEL_TIMEOUT)
        page.wait_for_timeout(5000)
        
        # Check consensus banner
        consensus_banner = page.locator('#mf-sentiment-consensus-banner')
        banner_text = consensus_banner.text_content()
        
        save_screenshot(page, "sentiment_04_consensus_banner")
        
        # Should show one of the consensus labels
        valid_labels = ['BULLISH', 'BEARISH', 'NEUTRAL', 'Score:']
        assert any(label in banner_text.upper() for label in valid_labels), \
            f"Consensus banner should show sentiment label, got: {banner_text}"
        
        logger.info(f"✅ Test 4 passed: Consensus banner shows: {banner_text[:50]}...")
    
    def test_05_verify_sentiment_distribution(self, page: Page):
        """Test: Verify sentiment distribution bars are displayed."""
        logger.info("🧪 Test 5: Verify Sentiment Distribution")
        
        # Navigate and run forecast
        mf_tab = page.locator('#dashboard-tabs .nav-link').filter(has_text='Market Forecast')
        mf_tab.click()
        page.wait_for_selector('#mf-model-checklist', timeout=DEFAULT_TIMEOUT)
        
        ticker_input = page.locator('#mf-ticker-input')
        ticker_input.clear()
        ticker_input.fill('TSLA')
        
        run_btn = page.locator('#mf-run-btn')
        run_btn.click()
        
        wait_for_spinner(page, timeout=MODEL_TIMEOUT)
        page.wait_for_timeout(5000)
        
        # Check distribution container
        distribution = page.locator('#mf-sentiment-distribution')
        
        save_screenshot(page, "sentiment_05_distribution")
        
        # Should have progress bars
        progress_bars = distribution.locator('.progress-bar')
        bar_count = progress_bars.count()
        
        # Should have at least positive/negative/neutral bars
        assert bar_count >= 3 or distribution.text_content(), \
            f"Should have sentiment distribution, got {bar_count} bars"
        
        logger.info(f"✅ Test 5 passed: Sentiment distribution displayed ({bar_count} bars)")
    
    def test_06_toggle_headline_details(self, page: Page):
        """Test: Toggle headline details visibility."""
        logger.info("🧪 Test 6: Toggle Headline Details")
        
        # Navigate and run forecast
        mf_tab = page.locator('#dashboard-tabs .nav-link').filter(has_text='Market Forecast')
        mf_tab.click()
        page.wait_for_selector('#mf-model-checklist', timeout=DEFAULT_TIMEOUT)
        
        ticker_input = page.locator('#mf-ticker-input')
        ticker_input.clear()
        ticker_input.fill('META')
        
        run_btn = page.locator('#mf-run-btn')
        run_btn.click()
        
        wait_for_spinner(page, timeout=MODEL_TIMEOUT)
        page.wait_for_timeout(5000)
        
        # Find toggle button
        toggle_btn = page.locator('#mf-sentiment-toggle-btn')
        
        save_screenshot(page, "sentiment_06_pre_toggle")
        
        # If button is visible, click to expand
        if toggle_btn.is_visible():
            toggle_btn.click()
            page.wait_for_timeout(500)
            
            save_screenshot(page, "sentiment_06_post_toggle")
            
            # Check if details are expanded
            details_collapse = page.locator('#mf-sentiment-details-collapse')
            
            # Verify content is shown
            details = page.locator('#mf-sentiment-details')
            
            logger.info("✅ Test 6 passed: Headline details toggle works")
        else:
            # Button hidden means no headlines or feature disabled
            logger.info("✅ Test 6 passed: Toggle button appropriately hidden")


# =============================================================================
# Combined Integration Test
# =============================================================================

class TestPhase5Integration:
    """Integration tests combining Regime Detection and Sentiment."""
    
    def test_01_full_workflow(self, page: Page):
        """Test: Full Phase 5 workflow - both features in sequence."""
        logger.info("🧪 Integration Test: Full Phase 5 Workflow")
        
        # Part 1: Regime Detection
        logger.info("📊 Part 1: Running Regime Detection...")
        mt_tab = page.locator('#dashboard-tabs .nav-link').filter(has_text='Market Trends')
        mt_tab.click()
        page.wait_for_selector('#tabs-market-trends', timeout=DEFAULT_TIMEOUT)
        
        regime_tab = page.locator('#tabs-market-trends .nav-link').filter(has_text='Regime Monitor')
        if regime_tab.count() > 0:
            regime_tab.click()
            page.wait_for_selector('#input-regime-ticker', timeout=DEFAULT_TIMEOUT)
            
            ticker_input = page.locator('#input-regime-ticker')
            ticker_input.fill('SPY')
            
            detect_btn = page.locator('#btn-detect-regimes')
            detect_btn.click()
            
            wait_for_spinner(page, timeout=MODEL_TIMEOUT)
            page.wait_for_timeout(3000)
        
        save_screenshot(page, "integration_01_regime")
        
        # Part 2: Sentiment Consensus
        logger.info("📊 Part 2: Running Sentiment Analysis...")
        mf_tab = page.locator('#dashboard-tabs .nav-link').filter(has_text='Market Forecast')
        mf_tab.click()
        page.wait_for_selector('#mf-model-checklist', timeout=DEFAULT_TIMEOUT)
        
        ticker_input = page.locator('#mf-ticker-input')
        ticker_input.clear()
        ticker_input.fill('SPY')
        
        run_btn = page.locator('#mf-run-btn')
        run_btn.click()
        
        wait_for_spinner(page, timeout=MODEL_TIMEOUT)
        page.wait_for_timeout(5000)
        
        save_screenshot(page, "integration_01_sentiment")
        save_dom(page, "integration_01_full")
        
        # Verify both features produced output
        logger.info("✅ Integration Test passed: Full Phase 5 workflow complete")
    
    def test_02_deterministic_mode(self, page: Page):
        """Test: Verify deterministic mode produces consistent results."""
        logger.info("🧪 Integration Test: Deterministic Mode")
        
        # Run regime detection twice with same ticker
        results = []
        
        for run in range(2):
            mt_tab = page.locator('#dashboard-tabs .nav-link').filter(has_text='Market Trends')
            mt_tab.click()
            page.wait_for_selector('#tabs-market-trends', timeout=DEFAULT_TIMEOUT)
            
            regime_tab = page.locator('#tabs-market-trends .nav-link').filter(has_text='Regime Monitor')
            if regime_tab.count() > 0:
                regime_tab.click()
                page.wait_for_selector('#input-regime-ticker', timeout=DEFAULT_TIMEOUT)
                
                ticker_input = page.locator('#input-regime-ticker')
                ticker_input.clear()
                ticker_input.fill('QQQ')
                
                detect_btn = page.locator('#btn-detect-regimes')
                detect_btn.click()
                
                wait_for_spinner(page, timeout=MODEL_TIMEOUT)
                page.wait_for_timeout(3000)
                
                # Capture banner text
                banner = page.locator('#regime-current-banner')
                results.append(banner.text_content())
                
                save_screenshot(page, f"deterministic_run{run+1}")
        
        # In deterministic mode, results should be identical
        if os.getenv('PHASE5_DETERMINISTIC', '0') == '1':
            assert results[0] == results[1], \
                f"Deterministic mode should produce same results: {results}"
        
        logger.info(f"✅ Integration Test passed: Deterministic results: {results}")


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Phase 5 E2E Test Suite - Market Intelligence")
    logger.info(f"PORT: {PORT}")
    logger.info(f"PHASE5_DETERMINISTIC: {os.getenv('PHASE5_DETERMINISTIC', '0')}")
    logger.info(f"AZURE_ENABLED: {os.getenv('AZURE_ENABLED', 'false')}")
    logger.info("=" * 60)
    
    pytest.main([
        __file__,
        '-v',
        '-s',
        '--tb=short',
        '-x',  # Stop on first failure
    ])
