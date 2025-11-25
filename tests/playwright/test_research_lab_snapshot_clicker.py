"""
Research Lab - Comprehensive Snapshot & Clicker Test
=====================================================

Tests all 5 subtabs with robust timing and interaction:
1. Market Scan - Ticker screening and metrics
2. Factor Analysis - Fama-French factor exposure
3. Correlation Explorer - Correlation heatmaps
4. Strategy Backtest - Backtest strategy performance
5. Research Notes - Research documentation

Features:
- Resilient to rendering delays
- Screenshots at each step
- Interactive element validation
- Network idle waiting
- Fallback JS click for stubborn elements
"""

import os
import time
import pytest
from pathlib import Path

BASE_URL = os.environ.get("DASH_URL", "http://localhost:8050")
OUT_DIR = Path("test-artifacts/research_lab")


def _safe_text(el):
    """Safely extract text from element."""
    try:
        return el.inner_text().strip()
    except Exception:
        return ""


def _safe_filename(s):
    """Convert string to safe filename."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in s)[:80]


def _robust_click(page, locator, timeout=10000):
    """
    Robust click with fallbacks.
    
    Tries:
    1. Standard click with scroll into view
    2. JavaScript click
    3. Force click
    """
    try:
        locator.scroll_into_view_if_needed()
        locator.click(timeout=timeout)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(700)
        return True
    except Exception as e1:
        try:
            # Fallback: JavaScript click
            locator.evaluate("el => el.click()")
            page.wait_for_timeout(700)
            return True
        except Exception as e2:
            try:
                # Last resort: force click
                locator.click(force=True)
                page.wait_for_timeout(500)
                return True
            except Exception as e3:
                print(f"⚠️ All click attempts failed: {e1}, {e2}, {e3}")
                return False


def test_research_lab_snapshot_overview(page):
    """Test 1: Navigate to Research Lab and capture overview."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("\n🔬 TEST 1: Research Lab Overview")
    print("=" * 60)
    
    # Navigate to dashboard
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1500)
    
    # Save homepage
    page.screenshot(path=str(OUT_DIR / "00_homepage.png"), full_page=True)
    print("✅ Homepage loaded")
    
    # Find Research Lab tab - try multiple selectors
    research_lab_locators = [
        page.locator("text=🔬 Research Lab").first,
        page.locator("[data-rb-event-key='research_lab']").first,
        page.locator("text=Research Lab").first,
    ]
    
    research_lab_tab = None
    for locator in research_lab_locators:
        if locator.count() > 0:
            research_lab_tab = locator
            break
    
    assert research_lab_tab is not None, "❌ Could not find Research Lab tab with any selector"
    
    # Click Research Lab tab
    success = _robust_click(page, research_lab_tab)
    assert success, "❌ Failed to click Research Lab tab"
    
    page.wait_for_timeout(2000)  # Wait for subtabs to render
    
    # Save Research Lab opened state
    page.screenshot(path=str(OUT_DIR / "01_research_lab_opened.png"), full_page=True)
    print("✅ Research Lab tab opened")
    
    # Verify subtabs are present - try multiple selector strategies
    subtab_selectors = [
        # Strategy 1: Direct navigation links within research lab content
        "div:has-text('Market Scan') .nav-link, div:has-text('Factor Analysis') .nav-link",
        # Strategy 2: Any nav-link buttons (after opening Research Lab)
        ".nav-tabs .nav-link",
        # Strategy 3: Tab navigation items
        ".nav-item .nav-link",
        # Strategy 4: Broad button search
        "button.nav-link",
    ]
    
    subtab_count = 0
    for selector in subtab_selectors:
        page.wait_for_timeout(500)
        loc = page.locator(selector)
        count = loc.count()
        if count >= 5:  # Found the right selector
            subtab_count = count
            print(f"✅ Found {subtab_count} subtabs using selector: {selector[:50]}...")
            break
    
    if subtab_count == 0:
        # Last resort: count by text
        text_subtabs = [
            "Market Scan",
            "Factor Analysis",
            "Correlation Explorer",
            "Strategy Backtest",
            "Research Notes",
        ]
        for text in text_subtabs:
            if page.locator(f"text={text}").count() > 0:
                subtab_count += 1
        print(f"✅ Found {subtab_count} subtabs by text matching")
    
    print(f"📊 Total subtabs detected: {subtab_count}")
    
    assert subtab_count >= 5, f"❌ Expected at least 5 subtabs, found {subtab_count}"


def test_research_lab_market_scan(page):
    """Test 2: Market Scan subtab with ticker screening."""
    print("\n📊 TEST 2: Market Scan Subtab")
    print("=" * 60)
    
    # Navigate to Research Lab (fresh start)
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1200)
    
    # Open Research Lab (robust selection similar to overview)
    research_lab_locators = [
        page.locator("text=🔬 Research Lab").first,
        page.locator("[data-rb-event-key='research_lab']").first,
        page.locator("text=Research Lab").first,
    ]

    research_lab_tab = None
    for locator in research_lab_locators:
        try:
            if locator.count() > 0:
                research_lab_tab = locator
                break
        except Exception:
            continue

    assert research_lab_tab is not None, "❌ Could not find Research Lab tab to open"
    _robust_click(page, research_lab_tab)
    page.wait_for_timeout(1500)
    # Wait for research lab subtabs container to appear (may be rendered by callback)
    try:
        page.wait_for_selector("#research-lab-tabs", timeout=8000)
    except Exception:
        page.wait_for_timeout(1500)
    
    # Find and click Market Scan subtab
    market_scan_locators = [
        page.locator("text=📊 Market Scan").first,
        page.locator("text=Market Scan").first,
        page.locator("[data-rb-event-key='market-scan']").first,
    ]
    
    market_scan_tab = None
    for locator in market_scan_locators:
        if locator.count() > 0:
            market_scan_tab = locator
            break

    # Fallback: scan nav links under research-lab-tabs and match text ignoring emoji
    if market_scan_tab is None:
        nav_links = page.locator("#research-lab-tabs .nav-link")
        try:
            n = nav_links.count()
        except Exception:
            n = 0

        for i in range(n):
            try:
                candidate = nav_links.nth(i)
                txt = _safe_text(candidate)
                if 'market scan' in txt.lower():
                    market_scan_tab = candidate
                    break
            except Exception:
                continue

    if market_scan_tab is None:
        # Debug output: dump nav container HTML and nav link texts
        try:
            cnt = page.locator('#research-lab-tabs').count()
        except Exception:
            cnt = 0
        print(f"DEBUG: '#research-lab-tabs' count = {cnt}")
        if cnt > 0:
            try:
                html_snip = page.locator('#research-lab-tabs').first.inner_html()
                print('DEBUG: research-lab-tabs HTML snippet:')
                print(html_snip[:500])
            except Exception as e:
                print(f"DEBUG: could not get inner_html: {e}")
        else:
            try:
                page_html = page.content()
                print('DEBUG: page.content() snippet:')
                print(page_html[:2000])
            except Exception as e:
                print(f"DEBUG: could not get page.content(): {e}")

        try:
            link_count = nav_links.count()
        except Exception:
            link_count = 0
        print(f"DEBUG: nav_links count = {link_count}")
        for i in range(link_count):
            try:
                item = nav_links.nth(i)
                print(f"DEBUG: nav[{i}] text='" + _safe_text(item) + "'")
            except Exception as e:
                print(f"DEBUG: nav[{i}] error: {e}")

    assert market_scan_tab is not None, "❌ Could not find Market Scan subtab"
    
    _robust_click(page, market_scan_tab)
    page.wait_for_timeout(1000)
    
    # Save initial state
    page.screenshot(path=str(OUT_DIR / "02_market_scan_initial.png"), full_page=True)
    print("✅ Market Scan subtab opened")
    
    # Try to interact with tickers input
    tickers_input_selectors = [
        "#market-scan-tickers",
        "input[placeholder*='ticker']",
        "input[placeholder*='symbol']",
    ]
    
    tickers_input = None
    for selector in tickers_input_selectors:
        loc = page.locator(selector).first
        if loc.count() > 0:
            tickers_input = loc
            break
    
    if tickers_input and tickers_input.count() > 0:
        try:
            tickers_input.fill("SPY,QQQ,IWM")
            page.wait_for_timeout(500)
            print("✅ Entered test tickers: SPY,QQQ,IWM")
            
            # Save with tickers entered
            page.screenshot(path=str(OUT_DIR / "03_market_scan_tickers_entered.png"), full_page=True)
            
            # Try to find and click Run button
            run_button_selectors = [
                "#market-scan-run-button",
                "button:has-text('Run')",
                "button:has-text('Screen')",
                "button:has-text('Analyze')",
            ]
            
            for selector in run_button_selectors:
                btn = page.locator(selector).first
                if btn.count() > 0:
                    _robust_click(page, btn)
                    page.wait_for_timeout(2000)
                    print("✅ Clicked Run button")
                    break
            
            # Save final state
            page.screenshot(path=str(OUT_DIR / "04_market_scan_results.png"), full_page=True)
            
        except Exception as e:
            print(f"⚠️ Could not interact with Market Scan inputs: {e}")
    else:
        print("⚠️ No tickers input found, saving current state")
        page.screenshot(path=str(OUT_DIR / "03_market_scan_no_input.png"), full_page=True)


def test_research_lab_factor_analysis(page):
    """Test 3: Factor Analysis subtab - Fama-French factors."""
    print("\n📈 TEST 3: Factor Analysis Subtab")
    print("=" * 60)
    
    # Navigate to Research Lab
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1200)
    
    # Open Research Lab
    research_lab_tab = page.locator("text=🔬 Research Lab").first
    _robust_click(page, research_lab_tab)
    page.wait_for_timeout(1500)
    
    # Find and click Factor Analysis subtab
    factor_analysis_locators = [
        page.locator("text=📈 Factor Analysis").first,
        page.locator("text=Factor Analysis").first,
        page.locator("[data-rb-event-key='factor-analysis']").first,
    ]
    
    factor_tab = None
    for locator in factor_analysis_locators:
        if locator.count() > 0:
            factor_tab = locator
            break
    
    assert factor_tab is not None, "❌ Could not find Factor Analysis subtab"
    
    _robust_click(page, factor_tab)
    page.wait_for_timeout(1500)
    
    # Save initial state
    page.screenshot(path=str(OUT_DIR / "05_factor_analysis_initial.png"), full_page=True)
    print("✅ Factor Analysis subtab opened")
    
    # Try to interact with ticker input
    ticker_input_selectors = [
        "#factor-ticker-input",
        "input[placeholder*='ticker']",
        "input[type='text']",
    ]
    
    ticker_input = None
    for selector in ticker_input_selectors:
        loc = page.locator(selector).first
        if loc.count() > 0:
            ticker_input = loc
            break
    
    if ticker_input and ticker_input.count() > 0:
        try:
            ticker_input.fill("AAPL")
            page.wait_for_timeout(500)
            print("✅ Entered test ticker: AAPL")
            
            page.screenshot(path=str(OUT_DIR / "06_factor_analysis_ticker_entered.png"), full_page=True)
            
            # Try to find and click Analyze button
            analyze_button_selectors = [
                "#factor-analyze-button",
                "button:has-text('Analyze')",
                "button:has-text('Calculate')",
                "button:has-text('Run')",
            ]
            
            for selector in analyze_button_selectors:
                btn = page.locator(selector).first
                if btn.count() > 0:
                    _robust_click(page, btn)
                    page.wait_for_timeout(3000)  # Factor analysis may take time
                    print("✅ Clicked Analyze button")
                    break
            
            # Save results
            page.screenshot(path=str(OUT_DIR / "07_factor_analysis_results.png"), full_page=True)
            
        except Exception as e:
            print(f"⚠️ Could not interact with Factor Analysis: {e}")
    else:
        print("⚠️ No ticker input found")
        page.screenshot(path=str(OUT_DIR / "06_factor_analysis_no_input.png"), full_page=True)


def test_research_lab_correlation_explorer(page):
    """Test 4: Correlation Explorer subtab."""
    print("\n🔗 TEST 4: Correlation Explorer Subtab")
    print("=" * 60)
    
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1200)
    
    # Open Research Lab
    research_lab_tab = page.locator("text=🔬 Research Lab").first
    _robust_click(page, research_lab_tab)
    page.wait_for_timeout(1500)
    
    # Find and click Correlation Explorer subtab
    correlation_locators = [
        page.locator("text=🔗 Correlation Explorer").first,
        page.locator("text=Correlation Explorer").first,
        page.locator("[data-rb-event-key='correlation-explorer']").first,
    ]
    
    correlation_tab = None
    for locator in correlation_locators:
        if locator.count() > 0:
            correlation_tab = locator
            break
    
    assert correlation_tab is not None, "❌ Could not find Correlation Explorer subtab"
    
    _robust_click(page, correlation_tab)
    page.wait_for_timeout(1500)
    
    # Save state
    page.screenshot(path=str(OUT_DIR / "08_correlation_explorer_initial.png"), full_page=True)
    print("✅ Correlation Explorer subtab opened")
    
    # Try to interact with tickers input
    tickers_input = page.locator("input[placeholder*='ticker']").first
    
    if tickers_input.count() > 0:
        try:
            tickers_input.fill("AAPL,MSFT,GOOGL,NVDA")
            page.wait_for_timeout(500)
            print("✅ Entered correlation tickers")
            
            page.screenshot(path=str(OUT_DIR / "09_correlation_explorer_tickers_entered.png"), full_page=True)
            
            # Try to generate correlation matrix
            generate_button = page.locator("button:has-text('Generate')").first
            if generate_button.count() > 0:
                _robust_click(page, generate_button)
                page.wait_for_timeout(2500)
                print("✅ Generated correlation matrix")
            
            page.screenshot(path=str(OUT_DIR / "10_correlation_explorer_results.png"), full_page=True)
            
        except Exception as e:
            print(f"⚠️ Could not interact with Correlation Explorer: {e}")
    else:
        page.screenshot(path=str(OUT_DIR / "09_correlation_explorer_no_input.png"), full_page=True)


def test_research_lab_strategy_backtest(page):
    """Test 5: Strategy Backtest subtab."""
    print("\n⚙️ TEST 5: Strategy Backtest Subtab")
    print("=" * 60)
    
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1200)
    
    # Open Research Lab
    research_lab_tab = page.locator("text=🔬 Research Lab").first
    _robust_click(page, research_lab_tab)
    page.wait_for_timeout(1500)
    
    # Find and click Strategy Backtest subtab
    backtest_locators = [
        page.locator("text=⚙️ Strategy Backtest").first,
        page.locator("text=Strategy Backtest").first,
        page.locator("[data-rb-event-key='strategy-backtest']").first,
    ]
    
    backtest_tab = None
    for locator in backtest_locators:
        if locator.count() > 0:
            backtest_tab = locator
            break
    
    assert backtest_tab is not None, "❌ Could not find Strategy Backtest subtab"
    
    _robust_click(page, backtest_tab)
    page.wait_for_timeout(1500)
    
    # Save state
    page.screenshot(path=str(OUT_DIR / "11_strategy_backtest_initial.png"), full_page=True)
    print("✅ Strategy Backtest subtab opened")
    
    # Try to interact with strategy selection
    strategy_dropdown = page.locator("select").first
    
    if strategy_dropdown.count() > 0:
        try:
            # Select a strategy (if options available)
            strategy_dropdown.select_option(index=1)
            page.wait_for_timeout(500)
            print("✅ Selected strategy")
            
            page.screenshot(path=str(OUT_DIR / "12_strategy_backtest_strategy_selected.png"), full_page=True)
            
            # Try to run backtest
            run_button = page.locator("button:has-text('Run Backtest')").first
            if run_button.count() > 0:
                _robust_click(page, run_button)
                page.wait_for_timeout(3000)  # Backtest may take time
                print("✅ Ran backtest")
            
            page.screenshot(path=str(OUT_DIR / "13_strategy_backtest_results.png"), full_page=True)
            
        except Exception as e:
            print(f"⚠️ Could not interact with Strategy Backtest: {e}")
    else:
        page.screenshot(path=str(OUT_DIR / "12_strategy_backtest_no_dropdown.png"), full_page=True)


def test_research_lab_research_notes(page):
    """Test 6: Research Notes subtab."""
    print("\n📝 TEST 6: Research Notes Subtab")
    print("=" * 60)
    
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1200)
    
    # Open Research Lab
    research_lab_tab = page.locator("text=🔬 Research Lab").first
    _robust_click(page, research_lab_tab)
    page.wait_for_timeout(1500)
    
    # Find and click Research Notes subtab
    notes_locators = [
        page.locator("text=📝 Research Notes").first,
        page.locator("text=Research Notes").first,
        page.locator("[data-rb-event-key='research-notes']").first,
    ]
    
    notes_tab = None
    for locator in notes_locators:
        if locator.count() > 0:
            notes_tab = locator
            break
    
    assert notes_tab is not None, "❌ Could not find Research Notes subtab"
    
    _robust_click(page, notes_tab)
    page.wait_for_timeout(1500)
    
    # Save state
    page.screenshot(path=str(OUT_DIR / "14_research_notes_initial.png"), full_page=True)
    print("✅ Research Notes subtab opened")
    
    # Try to interact with notes
    notes_textarea = page.locator("textarea").first
    
    if notes_textarea.count() > 0:
        try:
            notes_textarea.fill("Test research note: AAPL analysis complete")
            page.wait_for_timeout(500)
            print("✅ Entered research note")
            
            page.screenshot(path=str(OUT_DIR / "15_research_notes_entered.png"), full_page=True)
            
            # Try to save note
            save_button = page.locator("button:has-text('Save')").first
            if save_button.count() > 0:
                _robust_click(page, save_button)
                page.wait_for_timeout(1000)
                print("✅ Saved research note")
            
            page.screenshot(path=str(OUT_DIR / "16_research_notes_saved.png"), full_page=True)
            
        except Exception as e:
            print(f"⚠️ Could not interact with Research Notes: {e}")
    else:
        page.screenshot(path=str(OUT_DIR / "15_research_notes_no_textarea.png"), full_page=True)


def test_research_lab_all_subtabs_rapid(page):
    """Test 7: Rapid cycle through all subtabs for regression testing."""
    print("\n🔄 TEST 7: Rapid Subtab Cycling")
    print("=" * 60)
    
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1200)
    
    # Open Research Lab
    research_lab_tab = page.locator("text=🔬 Research Lab").first
    _robust_click(page, research_lab_tab)
    page.wait_for_timeout(1500)
    
    # Define all subtabs
    subtabs = [
        ("📊 Market Scan", "market-scan"),
        ("📈 Factor Analysis", "factor-analysis"),
        ("🔗 Correlation Explorer", "correlation-explorer"),
        ("⚙️ Strategy Backtest", "strategy-backtest"),
        ("📝 Research Notes", "research-notes"),
    ]
    
    for i, (label, key) in enumerate(subtabs):
        print(f"  Cycling to: {label}")
        
        # Try multiple selectors
        locators = [
            page.locator(f"text={label}").first,
            page.locator(f"[data-rb-event-key='{key}']").first,
        ]
        
        clicked = False
        for loc in locators:
            if loc.count() > 0:
                _robust_click(page, loc)
                page.wait_for_timeout(800)
                clicked = True
                break
        
        if clicked:
            filename = f"17_rapid_cycle_{i}_{_safe_filename(label)}.png"
            page.screenshot(path=str(OUT_DIR / filename), full_page=True)
            print(f"  ✅ {label} cycled")
        else:
            print(f"  ⚠️ Could not find {label}")
    
    print("✅ Rapid cycling complete")


if __name__ == "__main__":
    print("Run with: pytest -v tests/playwright/test_research_lab_snapshot_clicker.py")
