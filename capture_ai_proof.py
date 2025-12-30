#!/usr/bin/env python3
"""
Capture screenshot of Enhanced Alpaca Options Lab with AI Automation
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def capture_ai_automation():
    """Capture screenshot of AI Automation Hub."""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        print("Loading Enhanced Alpaca Options Lab...")
        driver.get('http://localhost:8053')
        time.sleep(3)
        
        # Take initial screenshot
        driver.save_screenshot('/home/aarav/Unified-Dashboard/ai_automation_proof_1.png')
        print("✅ Screenshot 1: Main page saved")
        
        # Click on AI tab
        try:
            ai_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'AI')]"))
            )
            ai_tab.click()
            time.sleep(2)
            driver.save_screenshot('/home/aarav/Unified-Dashboard/ai_automation_proof_2.png')
            print("✅ Screenshot 2: AI tab saved")
        except Exception as e:
            print(f"⚠️ Could not click AI tab: {e}")
        
        # Scroll down to see AI Automation Hub
        driver.execute_script("window.scrollTo(0, 500)")
        time.sleep(1)
        driver.save_screenshot('/home/aarav/Unified-Dashboard/ai_automation_proof_3.png')
        print("✅ Screenshot 3: Scrolled view saved")
        
        # Get page content
        page_source = driver.page_source
        
        # Check for AI components
        ai_components = [
            'AI Automation Hub',
            'ai-regime-display',
            'ai-scanner-results',
            'ai-signals-container',
            'GLD', 'SLV', 'SPY', 'NVDA'
        ]
        
        found = [c for c in ai_components if c in page_source]
        print(f"\n📊 AI Components Found: {len(found)}/{len(ai_components)}")
        for c in found:
            print(f"   ✅ {c}")
        
        print("\n🎉 Screenshots captured successfully!")
        print("Check: ai_automation_proof_1.png, ai_automation_proof_2.png, ai_automation_proof_3.png")
        
    finally:
        driver.quit()

if __name__ == '__main__':
    capture_ai_automation()
