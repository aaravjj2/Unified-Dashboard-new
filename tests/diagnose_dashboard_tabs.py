#!/usr/bin/env python3
"""
Diagnose Dashboard Tabs and Find Options Lab & Portfolio Issues
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, '.')

Path('test-artifacts/diagnosis').mkdir(parents=True, exist_ok=True)

def diagnose_dashboard():
    """Find all tabs and diagnose issues."""
    print("="*80)
    print("🔬 DASHBOARD TAB DIAGNOSIS")
    print("="*80)
    
    try:
        from playwright.sync_api import sync_playwright
        import requests
        
        # Check if app is running
        try:
            response = requests.get('http://localhost:8050', timeout=2)
            print("✅ Dash app is running\n")
        except:
            print("❌ Dash app not running. Start with: python financial_dashboard/app.py")
            return 1
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=300)
            page = browser.new_page()
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            # Console logging
            console_logs = []
            page.on('console', lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
            
            print("📄 Loading dashboard...")
            page.goto('http://localhost:8050', wait_until='networkidle', timeout=30000)
            time.sleep(3)
            
            page.screenshot(path='test-artifacts/diagnosis/homepage.png', full_page=True)
            print("📸 Screenshot saved\n")
            
            # Find ALL tabs
            print("🔍 SCANNING ALL TABS:")
            print("-" * 80)
            
            # Try multiple selectors for tabs
            tab_selectors = [
                'a.nav-link',
                'a[role="tab"]',
                '.nav-tabs a',
                'button[role="tab"]'
            ]
            
            all_tabs = []
            for selector in tab_selectors:
                try:
                    tabs = page.query_selector_all(selector)
                    if tabs:
                        print(f"\n✅ Found {len(tabs)} tabs using: {selector}")
                        for i, tab in enumerate(tabs):
                            try:
                                text = tab.inner_text().strip()
                                href = tab.get_attribute('href') or ''
                                classes = tab.get_attribute('class') or ''
                                is_visible = tab.is_visible()
                                all_tabs.append({
                                    'text': text,
                                    'href': href,
                                    'classes': classes,
                                    'visible': is_visible,
                                    'element': tab
                                })
                                print(f"   {i+1}. '{text}' | href: {href} | visible: {is_visible}")
                            except:
                                pass
                        break
                except:
                    continue
            
            if not all_tabs:
                print("❌ No tabs found!")
                browser.close()
                return 1
            
            # Look for Options Lab
            print("\n" + "="*80)
            print("🔍 SEARCHING FOR OPTIONS LAB:")
            print("-" * 80)
            
            options_lab_found = False
            for tab_info in all_tabs:
                text = tab_info['text'].lower()
                if 'option' in text:
                    print(f"✅ FOUND: '{tab_info['text']}'")
                    print(f"   Classes: {tab_info['classes']}")
                    print(f"   Href: {tab_info['href']}")
                    print(f"   Visible: {tab_info['visible']}")
                    options_lab_found = True
                    
                    # Try to click it
                    print("\n🖱️  Attempting to click...")
                    try:
                        tab_info['element'].click()
                        time.sleep(3)
                        page.screenshot(path='test-artifacts/diagnosis/options_lab_opened.png', full_page=True)
                        print("✅ Clicked successfully!")
                        print("📸 Screenshot: options_lab_opened.png")
                        
                        # Now look for Load Chain button
                        print("\n🔍 Looking for Load Chain button...")
                        button_selectors = [
                            'button:has-text("Load Chain")',
                            'button.options-load-btn',
                            '#options-load-btn',
                            'button:has-text("Load")'
                        ]
                        
                        for btn_sel in button_selectors:
                            try:
                                btn = page.query_selector(btn_sel)
                                if btn:
                                    print(f"✅ Found button using: {btn_sel}")
                                    print(f"   Text: {btn.inner_text()}")
                                    print(f"   Visible: {btn.is_visible()}")
                                    print(f"   Enabled: {btn.is_enabled()}")
                                    break
                            except:
                                pass
                        
                    except Exception as e:
                        print(f"❌ Click failed: {e}")
                    
                    break
            
            if not options_lab_found:
                print("❌ Options Lab tab NOT FOUND in dashboard")
                print("\n💡 Available tabs:")
                for tab_info in all_tabs:
                    print(f"   • {tab_info['text']}")
            
            # Look for Portfolio tab
            print("\n" + "="*80)
            print("🔍 SEARCHING FOR PORTFOLIO TAB:")
            print("-" * 80)
            
            portfolio_found = False
            for tab_info in all_tabs:
                text = tab_info['text'].lower()
                if 'portfolio' in text or 'portf' in text:
                    print(f"✅ FOUND: '{tab_info['text']}'")
                    print(f"   Classes: {tab_info['classes']}")
                    print(f"   Visible: {tab_info['visible']}")
                    portfolio_found = True
                    
                    # Try to click it
                    print("\n🖱️  Attempting to click Portfolio...")
                    try:
                        tab_info['element'].click()
                        time.sleep(3)
                        page.screenshot(path='test-artifacts/diagnosis/portfolio_opened.png', full_page=True)
                        print("✅ Clicked successfully!")
                        print("📸 Screenshot: portfolio_opened.png")
                        
                        # Check for errors
                        time.sleep(2)
                        error_elements = page.query_selector_all('.alert-danger, .text-danger, .error')
                        if error_elements:
                            print(f"\n⚠️  Found {len(error_elements)} error elements:")
                            for i, err in enumerate(error_elements[:5]):
                                try:
                                    err_text = err.inner_text()
                                    print(f"   {i+1}. {err_text[:100]}...")
                                except:
                                    pass
                        
                    except Exception as e:
                        print(f"❌ Click failed: {e}")
                    
                    break
            
            if not portfolio_found:
                print("❌ Portfolio tab NOT FOUND")
            
            # Check console for errors
            print("\n" + "="*80)
            print("📝 CONSOLE LOGS (last 30):")
            print("-" * 80)
            if console_logs:
                for log in console_logs[-30:]:
                    print(f"   {log}")
            else:
                print("   (No console logs)")
            
            errors = [log for log in console_logs if 'error' in log.lower()]
            if errors:
                print(f"\n❌ {len(errors)} CONSOLE ERRORS:")
                for err in errors:
                    print(f"   {err}")
            
            print("\n" + "="*80)
            print("DIAGNOSIS COMPLETE")
            print("="*80)
            
            browser.close()
            
    except Exception as e:
        print(f"❌ Diagnosis failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(diagnose_dashboard())
