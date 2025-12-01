#!/usr/bin/env python3
"""Verify all changes: Stock Picks graphs, AI Picks Portfolio, port 8051."""

import time
import os

def main():
    from playwright.sync_api import sync_playwright
    
    screenshot_dir = "/home/aarav/Unified-Dashboard/test_artifacts/final_verification"
    os.makedirs(screenshot_dir, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        print("=" * 60)
        print("VERIFICATION TEST - Port 8051")
        print("=" * 60)
        
        # Test 1: Dashboard loads on port 8051
        print("\n1. Testing dashboard on port 8051...")
        try:
            page.goto("http://localhost:8051", wait_until="networkidle", timeout=60000)
            time.sleep(3)
            print("   ✅ Dashboard loaded successfully on port 8051")
            page.screenshot(path=f"{screenshot_dir}/01_home.png")
        except Exception as e:
            print(f"   ❌ Failed to load dashboard: {e}")
            browser.close()
            return
        
        # Test 2: Navigate to Stock Picks tab
        print("\n2. Testing Stock Picks tab with graphs...")
        try:
            # Click on Stock Picks tab
            picks_tab = page.locator("a:has-text('Stock Picks'), button:has-text('Stock Picks'), [id*='picks']").first
            if picks_tab.is_visible(timeout=5000):
                picks_tab.click()
                time.sleep(2)
                page.screenshot(path=f"{screenshot_dir}/02_stock_picks.png")
                
                # Check for graphs
                graphs = page.locator(".dash-graph, .js-plotly-plot").all()
                print(f"   ✅ Stock Picks tab loaded with {len(graphs)} graph(s)")
            else:
                print("   ⚠️ Stock Picks tab not found")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 3: Check for AI Picks Portfolio subtab
        print("\n3. Testing AI Picks Portfolio subtab...")
        try:
            # Look for AI Picks tab within Stock Picks
            ai_tab = page.locator("a:has-text('AI Picks'), button:has-text('AI Picks'), [id*='ai-picks']").first
            if ai_tab.is_visible(timeout=5000):
                ai_tab.click()
                time.sleep(2)
                page.screenshot(path=f"{screenshot_dir}/03_ai_picks_portfolio.png")
                
                # Check for AI Picks specific elements
                buy_weekly_btn = page.locator("#buy-weekly-picks-btn, button:has-text('Buy All Weekly')").first
                buy_monthly_btn = page.locator("#buy-monthly-picks-btn, button:has-text('Buy All Monthly')").first
                backtest_btn = page.locator("#run-backtest-btn, button:has-text('Run AI Backtest')").first
                
                found = []
                if buy_weekly_btn.is_visible(timeout=2000):
                    found.append("Buy Weekly Picks")
                if buy_monthly_btn.is_visible(timeout=2000):
                    found.append("Buy Monthly Picks")
                if backtest_btn.is_visible(timeout=2000):
                    found.append("Run AI Backtest")
                
                print(f"   ✅ AI Picks Portfolio loaded with buttons: {', '.join(found)}")
            else:
                print("   ⚠️ AI Picks Portfolio subtab not found")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 4: Check chatbot toggle
        print("\n4. Testing AI Chatbot...")
        try:
            chatbot_btn = page.locator("#chatbot-toggle-btn, button:has-text('Chat'), .chatbot-toggle").first
            if chatbot_btn.is_visible(timeout=5000):
                chatbot_btn.click()
                time.sleep(1)
                
                # Check if chatbot container opened
                chatbot_container = page.locator("#chatbot-container, .chatbot-container").first
                if chatbot_container.is_visible(timeout=2000):
                    print("   ✅ Chatbot opened successfully")
                    page.screenshot(path=f"{screenshot_dir}/04_chatbot_open.png")
                else:
                    print("   ⚠️ Chatbot container not visible after click")
            else:
                print("   ⚠️ Chatbot toggle button not found")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 5: Check Weekly Picks subtab for graphs
        print("\n5. Testing Weekly Picks subtab with performance chart...")
        try:
            weekly_tab = page.locator("a:has-text('Weekly Picks'), button:has-text('Weekly Picks'), [id*='weekly']").first
            if weekly_tab.is_visible(timeout=5000):
                weekly_tab.click()
                time.sleep(2)
                page.screenshot(path=f"{screenshot_dir}/05_weekly_picks.png")
                
                # Check for performance chart
                weekly_chart = page.locator("#weekly-picks-chart, [id*='weekly-performance']").first
                if weekly_chart.is_visible(timeout=3000):
                    print("   ✅ Weekly Picks performance chart found")
                else:
                    print("   ⚠️ Weekly Picks performance chart not visible")
            else:
                print("   ⚠️ Weekly Picks subtab not found")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        browser.close()
        
        print("\n" + "=" * 60)
        print("VERIFICATION COMPLETE")
        print(f"Screenshots saved to: {screenshot_dir}")
        print("=" * 60)

if __name__ == "__main__":
    main()
