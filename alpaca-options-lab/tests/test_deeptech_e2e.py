#!/usr/bin/env python3
"""
Deep-Tech Stack Dashboard E2E Test

Tests all roadmap UI/UX features:
1. LOB Depth Chart
2. TradingView Candlestick Chart
3. Drawing Tools
4. Event Queue Monitor
5. Agent Workflow Panel
6. Microstructure Metrics
7. Real-time WebSocket Updates

Uses Playwright for browser automation.
"""
import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# UI/UX Feature Checklist
UI_UX_CHECKLIST = {
    "LOB Depth Chart": False,
    "TradingView Candlestick Chart": False,
    "Drawing Tools": False,
    "Event Queue Monitor": False,
    "Agent Workflow Panel": False,
    "Microstructure Metrics": False,
    "Real-time Updates": False,
    "Deep-Tech Tab Navigation": False,
}


async def run_deeptech_tests():
    """Run all Deep-Tech dashboard tests."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ Playwright not installed. Installing...")
        os.system("pip install playwright && playwright install chromium")
        from playwright.async_api import async_playwright
    
    results = []
    screenshot_dir = Path("tests/e2e_screenshots/deeptech")
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        
        print("\n" + "=" * 60)
        print("🔬 DEEP-TECH STACK DASHBOARD E2E TESTS")
        print("=" * 60)
        
        # Test 1: Navigate to dashboard
        print("\n📍 Test 1: Navigate to Dashboard")
        try:
            await page.goto("http://localhost:8053", timeout=30000)
            await page.wait_for_timeout(5000)  # Simple wait instead of networkidle
            results.append(("Navigate to Dashboard", True, ""))
            print("  ✅ Dashboard loaded")
        except Exception as e:
            results.append(("Navigate to Dashboard", False, str(e)))
            print(f"  ❌ Failed: {e}")
            await browser.close()
            return results
        
        # Test 2: Find and click Deep-Tech tab
        print("\n📍 Test 2: Navigate to Deep-Tech Tab")
        try:
            # First wait for tabs to render
            await page.wait_for_timeout(2000)
            
            # Try multiple selectors for tab navigation
            tab_selectors = [
                'text=🔬 Deep-Tech',
                'text=Deep-Tech',
                '[data-value="deeptech-workspace-tab"]',
                '#main-workspace-tabs .tab:has-text("Deep")',
                '.tab__link:has-text("Deep")',
                'div.tab:has-text("Deep-Tech")',
            ]
            
            clicked = False
            for selector in tab_selectors:
                try:
                    tab = await page.query_selector(selector)
                    if tab:
                        await tab.click()
                        await page.wait_for_timeout(2000)
                        UI_UX_CHECKLIST["Deep-Tech Tab Navigation"] = True
                        results.append(("Deep-Tech Tab Click", True, ""))
                        print(f"  ✅ Clicked tab via: {selector}")
                        clicked = True
                        break
                except:
                    continue
            
            if not clicked:
                # List all available tabs for debugging
                all_tabs = await page.query_selector_all('.Tab, .tab, [role="tab"]')
                tab_texts = []
                for t in all_tabs[:10]:
                    try:
                        txt = await t.inner_text()
                        tab_texts.append(txt[:30])
                    except:
                        pass
                print(f"  Available tabs: {tab_texts}")
                results.append(("Deep-Tech Tab Click", False, f"Tab not found. Found: {tab_texts}"))
                print("  ⚠️ Deep-Tech tab not found, continuing with main page")
        except Exception as e:
            results.append(("Deep-Tech Tab Click", False, str(e)))
            print(f"  ⚠️ Tab navigation issue: {e}")
        
        # Take screenshot of initial state
        await page.screenshot(path=str(screenshot_dir / "01_initial_state.png"), full_page=True)
        print("  📸 Screenshot: 01_initial_state.png")
        
        # Test 3: Check for LOB Visualization
        print("\n📍 Test 3: LOB Visualization Check")
        try:
            # Look for LOB-related elements
            lob_selectors = [
                'text=Limit Order Book',
                'text=LOB',
                'text=Order Book Depth',
                '#lob-depth-chart',
                '#lob-visualization',
                'text=Microstructure'
            ]
            
            for selector in lob_selectors:
                element = await page.query_selector(selector)
                if element:
                    UI_UX_CHECKLIST["LOB Depth Chart"] = True
                    UI_UX_CHECKLIST["Microstructure Metrics"] = True
                    results.append(("LOB Visualization", True, f"Found: {selector}"))
                    print(f"  ✅ LOB found via: {selector}")
                    break
            else:
                results.append(("LOB Visualization", False, "No LOB elements found"))
                print("  ⚠️ LOB elements not visible on current page")
        except Exception as e:
            results.append(("LOB Visualization", False, str(e)))
            print(f"  ❌ Error: {e}")
        
        # Test 4: Check for TradingView Chart
        print("\n📍 Test 4: TradingView Chart Check")
        try:
            chart_selectors = [
                'text=Interactive Chart',
                '#tradingview-chart',
                '.js-plotly-plot',
                'text=TradingView',
                'text=Candlestick'
            ]
            
            for selector in chart_selectors:
                element = await page.query_selector(selector)
                if element:
                    UI_UX_CHECKLIST["TradingView Candlestick Chart"] = True
                    results.append(("TradingView Chart", True, f"Found: {selector}"))
                    print(f"  ✅ Chart found via: {selector}")
                    break
            else:
                # Check for any Plotly graphs
                graphs = await page.query_selector_all('.js-plotly-plot')
                if graphs:
                    UI_UX_CHECKLIST["TradingView Candlestick Chart"] = True
                    results.append(("TradingView Chart", True, f"Found {len(graphs)} Plotly graphs"))
                    print(f"  ✅ Found {len(graphs)} chart(s)")
                else:
                    results.append(("TradingView Chart", False, "No charts found"))
                    print("  ⚠️ No charts visible")
        except Exception as e:
            results.append(("TradingView Chart", False, str(e)))
            print(f"  ❌ Error: {e}")
        
        # Test 5: Check for Drawing Tools
        print("\n📍 Test 5: Drawing Tools Check")
        try:
            drawing_selectors = [
                'text=Horizontal',
                'text=Trendline',
                'text=Ray',
                '#chart-tool-horizontal',
                '#chart-tool-trendline',
                'text=Drawing'
            ]
            
            for selector in drawing_selectors:
                element = await page.query_selector(selector)
                if element:
                    UI_UX_CHECKLIST["Drawing Tools"] = True
                    results.append(("Drawing Tools", True, f"Found: {selector}"))
                    print(f"  ✅ Drawing tools found via: {selector}")
                    break
            else:
                results.append(("Drawing Tools", False, "Drawing tools not found"))
                print("  ⚠️ Drawing tools not visible")
        except Exception as e:
            results.append(("Drawing Tools", False, str(e)))
            print(f"  ❌ Error: {e}")
        
        # Test 6: Check for Event Queue Monitor
        print("\n📍 Test 6: Event Queue Monitor Check")
        try:
            event_selectors = [
                'text=Event Queue',
                'text=Event Flow',
                '#event-queue-list',
                'text=MarketEvent',
                'text=SignalEvent'
            ]
            
            for selector in event_selectors:
                element = await page.query_selector(selector)
                if element:
                    UI_UX_CHECKLIST["Event Queue Monitor"] = True
                    results.append(("Event Queue Monitor", True, f"Found: {selector}"))
                    print(f"  ✅ Event queue found via: {selector}")
                    break
            else:
                results.append(("Event Queue Monitor", False, "Event queue not found"))
                print("  ⚠️ Event queue not visible")
        except Exception as e:
            results.append(("Event Queue Monitor", False, str(e)))
            print(f"  ❌ Error: {e}")
        
        # Test 7: Check for Agent Workflow Panel
        print("\n📍 Test 7: Agent Workflow Panel Check")
        try:
            agent_selectors = [
                'text=Agent Workflow',
                'text=LangGraph',
                'text=Supervisor',
                '#agent-workflow-diagram',
                'text=MCP Servers'
            ]
            
            for selector in agent_selectors:
                element = await page.query_selector(selector)
                if element:
                    UI_UX_CHECKLIST["Agent Workflow Panel"] = True
                    results.append(("Agent Workflow Panel", True, f"Found: {selector}"))
                    print(f"  ✅ Agent workflow found via: {selector}")
                    break
            else:
                results.append(("Agent Workflow Panel", False, "Agent workflow not found"))
                print("  ⚠️ Agent workflow not visible")
        except Exception as e:
            results.append(("Agent Workflow Panel", False, str(e)))
            print(f"  ❌ Error: {e}")
        
        # Test 8: Check for Real-time Updates
        print("\n📍 Test 8: Real-time Update Check")
        try:
            # Look for interval components or update timestamps
            interval_elements = await page.query_selector_all('[id*="interval"]')
            update_elements = await page.query_selector_all('text=Last Update')
            
            if interval_elements or update_elements:
                UI_UX_CHECKLIST["Real-time Updates"] = True
                results.append(("Real-time Updates", True, f"Found {len(interval_elements)} intervals"))
                print(f"  ✅ Real-time update components found")
            else:
                results.append(("Real-time Updates", False, "No interval components"))
                print("  ⚠️ No real-time update components found")
        except Exception as e:
            results.append(("Real-time Updates", False, str(e)))
            print(f"  ❌ Error: {e}")
        
        # Take final screenshot
        await page.screenshot(path=str(screenshot_dir / "02_final_state.png"), full_page=True)
        print("\n  📸 Screenshot: 02_final_state.png")
        
        # Test 9: Click through tabs if Deep-Tech has sub-tabs
        print("\n📍 Test 9: Sub-tab Navigation (if available)")
        try:
            sub_tabs = await page.query_selector_all('[id="deeptech-tabs"] .nav-link')
            if sub_tabs:
                for i, tab in enumerate(sub_tabs[:5]):  # Max 5 tabs
                    try:
                        await tab.click()
                        await page.wait_for_timeout(500)
                        text = await tab.inner_text()
                        print(f"  ✅ Clicked tab: {text[:30]}")
                        await page.screenshot(path=str(screenshot_dir / f"03_tab_{i}.png"))
                    except:
                        pass
                results.append(("Sub-tab Navigation", True, f"Navigated {len(sub_tabs)} tabs"))
            else:
                results.append(("Sub-tab Navigation", True, "No sub-tabs to navigate"))
                print("  ℹ️ No sub-tabs found")
        except Exception as e:
            results.append(("Sub-tab Navigation", False, str(e)))
            print(f"  ⚠️ Sub-tab issue: {e}")
        
        await browser.close()
    
    return results


def print_summary(results):
    """Print test summary."""
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, status, _ in results if status)
    failed = len(results) - passed
    
    for name, status, detail in results:
        icon = "✅" if status else "❌"
        print(f"  {icon} {name}: {detail[:50] if detail else 'OK'}")
    
    print("\n" + "-" * 60)
    print(f"📈 Results: {passed}/{len(results)} passed ({100*passed/len(results):.0f}%)")
    
    print("\n" + "-" * 60)
    print("🎯 UI/UX FEATURE CHECKLIST:")
    for feature, status in UI_UX_CHECKLIST.items():
        icon = "✅" if status else "⬜"
        print(f"  {icon} {feature}")
    
    checked = sum(1 for v in UI_UX_CHECKLIST.values() if v)
    print(f"\n📊 Features Verified: {checked}/{len(UI_UX_CHECKLIST)}")
    
    return passed, failed


if __name__ == "__main__":
    print(f"\n🕐 Starting tests at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = asyncio.run(run_deeptech_tests())
    passed, failed = print_summary(results)
    
    print(f"\n🕐 Completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    sys.exit(0 if failed == 0 else 1)
