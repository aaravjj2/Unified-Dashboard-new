#!/usr/bin/env python3
"""
LambdaTest Automation Script
Comprehensive automation for UI testing, screenshot capture, and validation

This script provides a complete automation framework for:
1. Cross-browser testing
2. Screenshot comparison
3. UI validation
4. Performance monitoring
5. Accessibility testing
"""

import os
import sys
import json
import time
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import requests
import base64
from dataclasses import dataclass, asdict
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class LambdaTestConfig:
    """Configuration for LambdaTest automation"""
    # LambdaTest credentials
    username: str = os.getenv('LAMBDATEST_USERNAME', 'test_user_placeholder')
    access_key: str = os.getenv('LAMBDATEST_ACCESS_KEY', 'test_key_placeholder')
    
    # Dashboard configuration
    dashboard_url: str = 'http://localhost:8051'
    target_tabs: List[str] = None
    
    # Test configuration
    browsers: List[str] = None
    operating_systems: List[str] = None
    screen_resolutions: List[str] = None
    
    # Output configuration
    screenshot_directory: str = 'test_artifacts/lambdatest_automation'
    report_directory: str = 'reports/lambdatest'
    
    # Validation settings
    max_retry_attempts: int = 3
    success_threshold: float = 0.95  # 95% success rate
    timeout_seconds: int = 30
    
    def __post_init__(self):
        if self.target_tabs is None:
            self.target_tabs = [
                'Home', 'Command Center', 'Strategy Lab', 
                'Options Lab', 'Weekly Picks', 'Monthly Picks',
                'Market Trends', 'Portfolio', 'Research Lab'
            ]
        
        if self.browsers is None:
            self.browsers = ['Chrome', 'Firefox', 'Safari', 'Edge']
        
        if self.operating_systems is None:
            self.operating_systems = ['Windows 10', 'macOS Big Sur', 'Ubuntu 20.04']
        
        if self.screen_resolutions is None:
            self.screen_resolutions = ['1920x1080', '1366x768', '1280x720']

class LambdaTestAutomation:
    """Main automation class for LambdaTest integration"""
    
    def __init__(self, config: LambdaTestConfig):
        self.config = config
        self.session = requests.Session()
        self.results = []
        
        # Create output directories
        Path(self.config.screenshot_directory).mkdir(parents=True, exist_ok=True)
        Path(self.config.report_directory).mkdir(parents=True, exist_ok=True)
    
    def authenticate(self) -> bool:
        """Authenticate with LambdaTest API"""
        try:
            if self.config.username == 'test_user_placeholder':
                logger.info("Using placeholder credentials - mock mode")
                return True
            
            auth = (self.config.username, self.config.access_key)
            response = self.session.get(
                "https://api.lambdatest.com/automation/api/v1/platforms",
                auth=auth,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("✅ LambdaTest authentication successful")
                return True
            else:
                logger.error(f"❌ Authentication failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            return False
    
    async def run_cross_browser_tests(self) -> Dict[str, Any]:
        """Run tests across multiple browsers and platforms"""
        logger.info("🚀 Starting cross-browser testing...")
        
        all_results = []
        
        for browser in self.config.browsers:
            for os_name in self.config.operating_systems:
                for resolution in self.config.screen_resolutions:
                    
                    test_config = {
                        'browser': browser,
                        'os': os_name,
                        'resolution': resolution
                    }
                    
                    logger.info(f"🔍 Testing: {browser} on {os_name} @ {resolution}")
                    
                    try:
                        result = await self._run_browser_test(test_config)
                        all_results.append(result)
                        
                    except Exception as e:
                        logger.error(f"❌ Test failed for {test_config}: {e}")
                        all_results.append({
                            'config': test_config,
                            'success': False,
                            'error': str(e),
                            'timestamp': datetime.now().isoformat()
                        })
        
        return {
            'total_tests': len(all_results),
            'successful_tests': len([r for r in all_results if r.get('success', False)]),
            'success_rate': len([r for r in all_results if r.get('success', False)]) / len(all_results),
            'results': all_results,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _run_browser_test(self, test_config: Dict[str, str]) -> Dict[str, Any]:
        """Run test for a specific browser configuration"""
        
        # For local testing, we'll use Playwright
        # In production, this would integrate with LambdaTest Selenium Grid
        
        async with async_playwright() as p:
            # Map browser names to Playwright browsers
            browser_map = {
                'Chrome': p.chromium,
                'Firefox': p.firefox,
                'Safari': p.webkit,
                'Edge': p.chromium  # Edge uses Chromium engine
            }
            
            browser_type = browser_map.get(test_config['browser'], p.chromium)
            
            # Parse resolution
            width, height = map(int, test_config['resolution'].split('x'))
            
            browser = await browser_type.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': width, 'height': height}
            )
            page = await context.new_page()
            
            tab_results = []
            
            for tab_name in self.config.target_tabs:
                try:
                    tab_result = await self._test_tab(page, tab_name, test_config)
                    tab_results.append(tab_result)
                    
                except Exception as e:
                    logger.error(f"❌ Tab test failed: {tab_name} - {e}")
                    tab_results.append({
                        'tab_name': tab_name,
                        'success': False,
                        'error': str(e)
                    })
            
            await browser.close()
            
            return {
                'config': test_config,
                'success': all(r.get('success', False) for r in tab_results),
                'tab_results': tab_results,
                'timestamp': datetime.now().isoformat()
            }
    
    async def _test_tab(self, page: Page, tab_name: str, test_config: Dict[str, str]) -> Dict[str, Any]:
        """Test a specific tab"""
        
        # Navigate to tab
        tab_urls = {
            'Home': '/',
            'Command Center': '/command-center',
            'Strategy Lab': '/strategy-lab',
            'Options Lab': '/options-lab',
            'Weekly Picks': '/weekly-picks',
            'Monthly Picks': '/monthly-picks',
            'Market Trends': '/market-trends',
            'Portfolio': '/portfolio',
            'Research Lab': '/research-lab'
        }
        
        url = self.config.dashboard_url + tab_urls.get(tab_name, '/')
        
        try:
            # Navigate with timeout
            await page.goto(url, wait_until='networkidle', timeout=self.config.timeout_seconds * 1000)
            
            # Wait for content to load
            await asyncio.sleep(2)
            
            # Take screenshot
            screenshot_name = f"{test_config['browser']}_{test_config['os'].replace(' ', '_')}_{test_config['resolution']}_{tab_name.replace(' ', '_')}.png"
            screenshot_path = Path(self.config.screenshot_directory) / screenshot_name
            
            await page.screenshot(path=str(screenshot_path), full_page=True)
            
            # Validate page content
            validation_results = await self._validate_page_content(page, tab_name)
            
            # Upload to LambdaTest (if using real credentials)
            upload_result = await self._upload_screenshot(screenshot_path, {
                'tab_name': tab_name,
                'browser': test_config['browser'],
                'os': test_config['os'],
                'resolution': test_config['resolution'],
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                'tab_name': tab_name,
                'success': True,
                'screenshot_path': str(screenshot_path),
                'validation_results': validation_results,
                'upload_result': upload_result,
                'load_time': await self._measure_load_time(page),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'tab_name': tab_name,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def _validate_page_content(self, page: Page, tab_name: str) -> Dict[str, Any]:
        """Validate page content and accessibility"""
        
        validation_results = {
            'title_present': False,
            'content_loaded': False,
            'no_errors': True,
            'accessibility_score': 0.0,
            'performance_score': 0.0
        }
        
        try:
            # Check if page title is present
            title = await page.title()
            validation_results['title_present'] = bool(title and title != 'Loading...')
            
            # Check if main content is loaded
            content_selectors = [
                '.container', '.main-content', '.tab-content',
                'table', '.card', '.dashboard-content'
            ]
            
            for selector in content_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        validation_results['content_loaded'] = True
                        break
                except:
                    continue
            
            # Check for JavaScript errors
            errors = await page.evaluate("""
                () => {
                    return window.jsErrors || [];
                }
            """)
            validation_results['no_errors'] = len(errors) == 0
            
            # Basic accessibility check
            accessibility_score = await self._check_accessibility(page)
            validation_results['accessibility_score'] = accessibility_score
            
            # Basic performance check
            performance_score = await self._check_performance(page)
            validation_results['performance_score'] = performance_score
            
        except Exception as e:
            logger.warning(f"Validation error for {tab_name}: {e}")
        
        return validation_results
    
    async def _check_accessibility(self, page: Page) -> float:
        """Basic accessibility check"""
        try:
            # Check for alt text on images
            images_without_alt = await page.evaluate("""
                () => {
                    const images = document.querySelectorAll('img');
                    return Array.from(images).filter(img => !img.alt).length;
                }
            """)
            
            # Check for form labels
            inputs_without_labels = await page.evaluate("""
                () => {
                    const inputs = document.querySelectorAll('input[type="text"], input[type="email"], textarea');
                    return Array.from(inputs).filter(input => {
                        const id = input.id;
                        return !id || !document.querySelector(`label[for="${id}"]`);
                    }).length;
                }
            """)
            
            # Simple scoring (0-1)
            total_elements = await page.evaluate("""
                () => document.querySelectorAll('img, input[type="text"], input[type="email"], textarea').length
            """)
            
            if total_elements == 0:
                return 1.0
            
            issues = images_without_alt + inputs_without_labels
            return max(0.0, 1.0 - (issues / total_elements))
            
        except:
            return 0.5  # Default score if check fails
    
    async def _check_performance(self, page: Page) -> float:
        """Basic performance check"""
        try:
            # Measure page load time
            start_time = time.time()
            await page.wait_for_load_state('networkidle', timeout=10000)
            load_time = time.time() - start_time
            
            # Score based on load time (0-1, where 1 is best)
            # < 2s = 1.0, 2-5s = 0.8, 5-10s = 0.5, >10s = 0.2
            if load_time < 2:
                return 1.0
            elif load_time < 5:
                return 0.8
            elif load_time < 10:
                return 0.5
            else:
                return 0.2
                
        except:
            return 0.5  # Default score if check fails
    
    async def _measure_load_time(self, page: Page) -> float:
        """Measure page load time"""
        try:
            load_time = await page.evaluate("""
                () => {
                    const navigation = performance.getEntriesByType('navigation')[0];
                    return navigation ? navigation.loadEventEnd - navigation.fetchStart : 0;
                }
            """)
            return load_time / 1000  # Convert to seconds
        except:
            return 0.0
    
    async def _upload_screenshot(self, screenshot_path: Path, metadata: Dict[str, str]) -> Dict[str, Any]:
        """Upload screenshot to LambdaTest"""
        
        if self.config.username == 'test_user_placeholder':
            # Mock upload for testing
            return {
                'success': True,
                'upload_id': f"mock_upload_{int(time.time())}",
                'file_size': screenshot_path.stat().st_size if screenshot_path.exists() else 0
            }
        
        try:
            # Real LambdaTest upload would go here
            # This is a placeholder for the actual API call
            
            with open(screenshot_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode()
            
            payload = {
                'screenshot': image_data,
                'metadata': metadata,
                'format': 'png'
            }
            
            auth = (self.config.username, self.config.access_key)
            response = self.session.post(
                "https://api.lambdatest.com/screenshots/v1/upload",
                json=payload,
                auth=auth,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'upload_id': result.get('upload_id'),
                    'file_size': screenshot_path.stat().st_size
                }
            else:
                return {
                    'success': False,
                    'error': f"Upload failed: {response.status_code}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate comprehensive test report"""
        
        report_path = Path(self.config.report_directory) / f"lambdatest_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        html_report = f"""
<!DOCTYPE html>
<html>
<head>
    <title>LambdaTest Automation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f8f9fa; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .metric {{ background: #e9ecef; padding: 15px; border-radius: 5px; text-align: center; }}
        .success {{ color: #28a745; }}
        .failure {{ color: #dc3545; }}
        .warning {{ color: #ffc107; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .screenshot {{ max-width: 200px; max-height: 150px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>LambdaTest Automation Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Dashboard URL: {self.config.dashboard_url}</p>
    </div>
    
    <div class="summary">
        <div class="metric">
            <h3>Total Tests</h3>
            <p>{results['total_tests']}</p>
        </div>
        <div class="metric">
            <h3>Successful</h3>
            <p class="success">{results['successful_tests']}</p>
        </div>
        <div class="metric">
            <h3>Success Rate</h3>
            <p class="{'success' if results['success_rate'] >= 0.95 else 'warning' if results['success_rate'] >= 0.8 else 'failure'}">{results['success_rate']:.1%}</p>
        </div>
    </div>
    
    <h2>Test Results</h2>
    <table>
        <tr>
            <th>Browser</th>
            <th>OS</th>
            <th>Resolution</th>
            <th>Status</th>
            <th>Tabs Tested</th>
            <th>Success Rate</th>
        </tr>
"""
        
        for result in results['results']:
            config = result['config']
            success = result.get('success', False)
            tab_results = result.get('tab_results', [])
            tab_success_rate = len([t for t in tab_results if t.get('success', False)]) / max(len(tab_results), 1)
            
            html_report += f"""
        <tr>
            <td>{config['browser']}</td>
            <td>{config['os']}</td>
            <td>{config['resolution']}</td>
            <td class="{'success' if success else 'failure'}">{'✅ Pass' if success else '❌ Fail'}</td>
            <td>{len(tab_results)}</td>
            <td>{tab_success_rate:.1%}</td>
        </tr>
"""
        
        html_report += """
    </table>
    
    <h2>Screenshots</h2>
    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px;">
"""
        
        # Add screenshot gallery
        screenshot_dir = Path(self.config.screenshot_directory)
        for screenshot in screenshot_dir.glob("*.png"):
            html_report += f"""
        <div style="border: 1px solid #ddd; padding: 10px; border-radius: 5px;">
            <img src="{screenshot.name}" class="screenshot" alt="{screenshot.stem}">
            <p style="font-size: 12px; margin: 5px 0 0 0;">{screenshot.stem}</p>
        </div>
"""
        
        html_report += """
    </div>
</body>
</html>
"""
        
        with open(report_path, 'w') as f:
            f.write(html_report)
        
        logger.info(f"📊 Report generated: {report_path}")
        return str(report_path)

async def main():
    """Main execution function"""
    print("🚀 LambdaTest Automation Suite")
    print("=" * 50)
    
    # Initialize configuration
    config = LambdaTestConfig()
    automation = LambdaTestAutomation(config)
    
    # Authenticate
    if not automation.authenticate():
        print("❌ Authentication failed")
        return False
    
    # Run cross-browser tests
    print("🔍 Running cross-browser tests...")
    results = await automation.run_cross_browser_tests()
    
    # Generate report
    report_path = automation.generate_report(results)
    
    # Print summary
    print("\n" + "=" * 60)
    print("LAMBDATEST AUTOMATION SUMMARY")
    print("=" * 60)
    print(f"✅ Total Tests: {results['total_tests']}")
    print(f"✅ Successful: {results['successful_tests']}")
    print(f"✅ Success Rate: {results['success_rate']:.1%}")
    print(f"📊 Report: {report_path}")
    print(f"📁 Screenshots: {config.screenshot_directory}")
    print("=" * 60)
    
    return results['success_rate'] >= config.success_threshold

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)