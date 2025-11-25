#!/usr/bin/env python3
"""
LambdaTest Integration for Phase 24-25 Validation
"""

import os
import json
import requests
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options

class LambdaTestValidator:
    def __init__(self):
        self.username = os.getenv('LAMBDATEST_USERNAME', 'your_username')
        self.access_key = os.getenv('LAMBDATEST_ACCESS_KEY', 'your_access_key')
        self.hub_url = 'https://hub.lambdatest.com/wd/hub'
        
    def create_session(self):
        """Create LambdaTest session"""
        capabilities = {
            "browserName": "Chrome",
            "browserVersion": "latest",
            "platform": "Windows 10",
            "resolution": "1920x1080",
            "build": "Phase 24-25 Critical Fix Validation",
            "name": "Dashboard UI Validation",
            "network": true,
            "visual": true,
            "video": true,
            "console": true
}
        
        capabilities['LT:Options'] = {
            'username': self.username,
            'accessKey': self.access_key,
            'build': 'Phase 24-25 Critical Fix Validation',
            'name': 'Dashboard UI Validation',
            'platformName': 'Windows 10',
            'selenium_version': '4.0.0'
        }
        
        driver = webdriver.Remote(
            command_executor=self.hub_url,
            desired_capabilities=capabilities
        )
        
        return driver
    
    def validate_dashboard(self):
        """Validate dashboard on LambdaTest"""
        driver = None
        try:
            driver = self.create_session()
            
            # Navigate to dashboard
            driver.get('http://localhost:8050')
            
            # Take screenshots of all tabs
            tabs = ['/', '/command-center', '/strategy-lab', '/options-lab', '/weekly-picks', '/monthly-picks']
            
            results = []
            for tab in tabs:
                try:
                    driver.get(f'http://localhost:8050{tab}')
                    driver.implicitly_wait(5)
                    
                    # Take screenshot
                    screenshot_path = f'test_artifacts/phase24_25_complete_fix/lambdatest_{tab.replace("/", "_")}.png'
                    driver.save_screenshot(screenshot_path)
                    
                    # Check for React errors in console
                    logs = driver.get_log('browser')
                    react_errors = [log for log in logs if 'React' in log.get('message', '')]
                    
                    results.append({
                        'tab': tab,
                        'screenshot': screenshot_path,
                        'react_errors': len(react_errors),
                        'console_errors': len([log for log in logs if log.get('level') == 'SEVERE'])
                    })
                    
                except Exception as e:
                    results.append({'tab': tab, 'error': str(e)})
            
            return results
            
        finally:
            if driver:
                driver.quit()

if __name__ == "__main__":
    validator = LambdaTestValidator()
    results = validator.validate_dashboard()
    
    with open('reports/phase24_25_complete_fix/lambdatest_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("LambdaTest validation complete!")
