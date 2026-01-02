"""
Chromium Clicker Test - Enhanced Quant Dashboard 8052
Automated testing with real browser interactions
"""

import asyncio
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

class DashboardClicker:
    """Automated clicker test for quant dashboard"""
    
    def __init__(self, base_url: str = "http://localhost:8052"):
        self.base_url = base_url
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "url": base_url,
            "tests": [],
            "passed": 0,
            "failed": 0,
            "screenshots": []
        }
        
    async def run_tests(self):
        """Run all dashboard tests"""
        if not PLAYWRIGHT_AVAILABLE:
            print("❌ Playwright not installed. Install with: pip install playwright && playwright install chromium")
            return self.results
            
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # Test 1: Page Load
                await self._test_page_load(page)
                
                # Test 2: API Status Display
                await self._test_api_status(page)
                
                # Test 3: Market Overview Cards
                await self._test_market_cards(page)
                
                # Test 4: Symbol Input and Chart
                await self._test_symbol_chart(page)
                
                # Test 5: Navigation Tabs
                await self._test_navigation(page)
                
                # Test 6: AI Analysis
                await self._test_ai_analysis(page)
                
                # Test 7: Trading Signals
                await self._test_trading_signals(page)
                
                # Take final screenshot
                screenshot_path = "/tmp/dashboard_8052_final.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                self.results["screenshots"].append(screenshot_path)
                
            except Exception as e:
                self._add_result("Global Error", False, str(e))
            finally:
                await browser.close()
        
        return self.results
    
    async def _test_page_load(self, page):
        """Test basic page load"""
        try:
            await page.goto(self.base_url, timeout=30000)
            await page.wait_for_load_state("networkidle")
            
            title = await page.title()
            self._add_result("Page Load", True, f"Page loaded successfully. Title: {title}")
            
            # Take screenshot
            await page.screenshot(path="/tmp/dashboard_8052_load.png")
            self.results["screenshots"].append("/tmp/dashboard_8052_load.png")
            
        except Exception as e:
            self._add_result("Page Load", False, str(e))
    
    async def _test_api_status(self, page):
        """Test API status badges display"""
        try:
            await page.wait_for_selector("#api-status-display", timeout=10000)
            badges = await page.query_selector_all("#api-status-display .badge")
            
            badge_count = len(badges)
            self._add_result("API Status Display", badge_count > 0, f"Found {badge_count} API status badges")
            
        except Exception as e:
            self._add_result("API Status Display", False, str(e))
    
    async def _test_market_cards(self, page):
        """Test market overview cards"""
        try:
            # Wait for cards to load
            await asyncio.sleep(3)
            
            spy_card = await page.query_selector("#spy-card")
            qqq_card = await page.query_selector("#qqq-card")
            
            has_cards = spy_card is not None and qqq_card is not None
            self._add_result("Market Cards", has_cards, "SPY and QQQ cards present" if has_cards else "Cards not found")
            
        except Exception as e:
            self._add_result("Market Cards", False, str(e))
    
    async def _test_symbol_chart(self, page):
        """Test symbol input and chart generation"""
        try:
            # Find symbol input
            symbol_input = await page.query_selector("#symbol-input")
            
            if symbol_input:
                # Clear and enter new symbol
                await symbol_input.fill("MSFT")
                
                # Click load button
                load_btn = await page.query_selector("#load-symbol-btn")
                if load_btn:
                    await load_btn.click()
                    await asyncio.sleep(5)  # Wait for chart to load
                
                # Check for chart
                chart = await page.query_selector("#price-chart")
                self._add_result("Symbol Chart", chart is not None, "Chart generated for MSFT")
                
                # Take screenshot
                await page.screenshot(path="/tmp/dashboard_8052_chart.png")
                self.results["screenshots"].append("/tmp/dashboard_8052_chart.png")
            else:
                self._add_result("Symbol Chart", False, "Symbol input not found")
                
        except Exception as e:
            self._add_result("Symbol Chart", False, str(e))
    
    async def _test_navigation(self, page):
        """Test navigation between tabs"""
        try:
            tabs = ["forecast", "bots", "ai", "news"]
            
            for tab in tabs:
                btn = await page.query_selector(f"#nav-{tab}")
                if btn:
                    await btn.click()
                    await asyncio.sleep(1)
                    
            self._add_result("Navigation", True, f"Tested navigation to {len(tabs)} tabs")
            
            # Go back to dashboard
            dashboard_btn = await page.query_selector("#nav-dashboard")
            if dashboard_btn:
                await dashboard_btn.click()
                await asyncio.sleep(1)
                
        except Exception as e:
            self._add_result("Navigation", False, str(e))
    
    async def _test_ai_analysis(self, page):
        """Test AI analysis display"""
        try:
            await page.wait_for_selector("#ai-analysis-display", timeout=10000)
            analysis = await page.query_selector("#ai-analysis-display")
            
            if analysis:
                content = await analysis.inner_text()
                has_content = len(content) > 20
                self._add_result("AI Analysis", has_content, f"Analysis content length: {len(content)}")
            else:
                self._add_result("AI Analysis", False, "Analysis display not found")
                
        except Exception as e:
            self._add_result("AI Analysis", False, str(e))
    
    async def _test_trading_signals(self, page):
        """Test trading signals display"""
        try:
            signals = await page.query_selector("#trading-signals-display")
            
            if signals:
                content = await signals.inner_text()
                has_signals = "BUY" in content or "SELL" in content or "HOLD" in content or "Enter" in content
                self._add_result("Trading Signals", has_signals or len(content) > 10, f"Signals content: {content[:100]}...")
            else:
                self._add_result("Trading Signals", False, "Signals display not found")
                
        except Exception as e:
            self._add_result("Trading Signals", False, str(e))
    
    def _add_result(self, test_name: str, passed: bool, details: str):
        """Add test result"""
        self.results["tests"].append({
            "name": test_name,
            "passed": passed,
            "details": details
        })
        
        if passed:
            self.results["passed"] += 1
            print(f"  ✅ {test_name}: {details}")
        else:
            self.results["failed"] += 1
            print(f"  ❌ {test_name}: {details}")


async def main():
    """Main entry point"""
    print("=" * 60)
    print("🧪 QUANT DASHBOARD CLICKER TEST - PORT 8052")
    print("=" * 60)
    print()
    
    clicker = DashboardClicker("http://localhost:8052")
    results = await clicker.run_tests()
    
    print()
    print("=" * 60)
    print(f"📊 RESULTS: {results['passed']} passed, {results['failed']} failed")
    print("=" * 60)
    
    # Save results
    results_path = "/tmp/clicker_test_8052_results.json"
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n📁 Results saved to: {results_path}")
    
    if results.get("screenshots"):
        print(f"📸 Screenshots saved: {', '.join(results['screenshots'])}")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
