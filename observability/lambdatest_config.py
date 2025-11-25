"""
LambdaTest Cross-Browser Visual Regression Configuration
Phase 22: Observability, Monitoring, and Optional Enhancements

Provides Selenium Grid integration with LambdaTest for cross-browser testing.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from selenium import webdriver
from selenium.webdriver.remote.remote_connection import RemoteConnection
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

logger = logging.getLogger(__name__)

# LambdaTest credentials
LAMBDATEST_USERNAME = os.getenv('LAMBDATEST_USERNAME')
LAMBDATEST_ACCESS_KEY = os.getenv('LAMBDATEST_ACCESS_KEY')
LAMBDATEST_GRID_URL = f"https://{LAMBDATEST_USERNAME}:{LAMBDATEST_ACCESS_KEY}@hub.lambdatest.com/wd/hub"

# Browser configurations for cross-browser testing
BROWSER_CONFIGS = [
    {
        'name': 'Chrome Latest',
        'platform': 'Windows 11',
        'browserName': 'Chrome',
        'version': 'latest',
        'resolution': '1920x1080'
    },
    {
        'name': 'Firefox Latest',
        'platform': 'Windows 11',
        'browserName': 'Firefox',
        'version': 'latest',
        'resolution': '1920x1080'
    },
    {
        'name': 'Safari Latest',
        'platform': 'macOS Ventura',
        'browserName': 'Safari',
        'version': 'latest',
        'resolution': '1920x1080'
    },
    {
        'name': 'Edge Latest',
        'platform': 'Windows 11',
        'browserName': 'MicrosoftEdge',
        'version': 'latest',
        'resolution': '1920x1080'
    }
]


def get_lambdatest_driver(
    browser_config: Dict[str, str],
    test_name: str,
    build_name: str = 'Phase 22 Visual Regression'
) -> Optional[webdriver.Remote]:
    """
    Create LambdaTest remote WebDriver instance.
    
    Args:
        browser_config: Browser configuration dict
        test_name: Test name for LambdaTest dashboard
        build_name: Build name for organizing tests
    
    Returns:
        WebDriver instance or None if creation fails
    """
    if not LAMBDATEST_USERNAME or not LAMBDATEST_ACCESS_KEY:
        logger.error("❌ LambdaTest credentials not configured")
        return None
    
    try:
        capabilities = {
            'browserName': browser_config['browserName'],
            'browserVersion': browser_config['version'],
            'platformName': browser_config['platform'],
            'LT:Options': {
                'username': LAMBDATEST_USERNAME,
                'accessKey': LAMBDATEST_ACCESS_KEY,
                'build': build_name,
                'name': test_name,
                'resolution': browser_config['resolution'],
                'video': True,
                'network': True,
                'console': True,
                'visual': True,
                'w3c': True,
                'plugin': 'python-python'
            }
        }
        
        driver = webdriver.Remote(
            command_executor=LAMBDATEST_GRID_URL,
            desired_capabilities=capabilities
        )
        
        logger.info(f"✅ LambdaTest driver created: {browser_config['name']}")
        return driver
        
    except Exception as e:
        logger.error(f"❌ Failed to create LambdaTest driver: {e}")
        return None


def mark_test_status(driver: webdriver.Remote, status: str, reason: str = ''):
    """
    Mark test status in LambdaTest dashboard.
    
    Args:
        driver: WebDriver instance
        status: 'passed' or 'failed'
        reason: Failure reason if status is 'failed'
    """
    try:
        driver.execute_script(
            f"lambda-status={status}",
            {'reason': reason}
        )
        logger.info(f"✅ Test marked as {status}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to mark test status: {e}")


def capture_screenshot(
    driver: webdriver.Remote,
    screenshot_name: str,
    output_dir: str = 'phase22_lambdatest_snapshots'
) -> Optional[str]:
    """
    Capture screenshot and save locally.
    
    Args:
        driver: WebDriver instance
        screenshot_name: Screenshot filename
        output_dir: Output directory
    
    Returns:
        Screenshot path or None if capture fails
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        screenshot_path = os.path.join(output_dir, screenshot_name)
        driver.save_screenshot(screenshot_path)
        logger.info(f"📸 Screenshot saved: {screenshot_path}")
        return screenshot_path
    except Exception as e:
        logger.error(f"❌ Failed to capture screenshot: {e}")
        return None


def run_cross_browser_test(
    test_name: str,
    test_func: callable,
    dashboard_url: str = 'http://localhost:8050'
) -> Dict[str, Any]:
    """
    Run test across all configured browsers.
    
    Args:
        test_name: Test name
        test_func: Test function (receives driver and browser_name as args)
        dashboard_url: Dashboard URL to test
    
    Returns:
        Test results dict
    """
    results = {
        'test_name': test_name,
        'browsers': [],
        'passed': 0,
        'failed': 0
    }
    
    for browser_config in BROWSER_CONFIGS:
        browser_name = browser_config['name']
        logger.info(f"🚀 Running {test_name} on {browser_name}")
        
        driver = get_lambdatest_driver(browser_config, test_name)
        
        if not driver:
            results['browsers'].append({
                'name': browser_name,
                'status': 'skipped',
                'error': 'Driver creation failed'
            })
            results['failed'] += 1
            continue
        
        try:
            # Navigate to dashboard
            driver.get(dashboard_url)
            driver.implicitly_wait(10)
            
            # Run test function
            test_func(driver, browser_name)
            
            # Mark as passed
            mark_test_status(driver, 'passed')
            results['browsers'].append({
                'name': browser_name,
                'status': 'passed'
            })
            results['passed'] += 1
            
            logger.info(f"✅ Test passed on {browser_name}")
            
        except Exception as e:
            # Mark as failed
            mark_test_status(driver, 'failed', str(e))
            results['browsers'].append({
                'name': browser_name,
                'status': 'failed',
                'error': str(e)
            })
            results['failed'] += 1
            
            logger.error(f"❌ Test failed on {browser_name}: {e}")
            
        finally:
            driver.quit()
    
    return results


def generate_visual_regression_report(
    results: List[Dict[str, Any]],
    output_file: str = 'phase22_lambdatest_report.json'
) -> None:
    """
    Generate visual regression report.
    
    Args:
        results: List of test result dicts
        output_file: Output JSON file
    """
    try:
        report = {
            'total_tests': len(results),
            'total_passed': sum(r['passed'] for r in results),
            'total_failed': sum(r['failed'] for r in results),
            'tests': results
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"✅ Visual regression report saved: {output_file}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("LAMBDATEST VISUAL REGRESSION REPORT")
        print("=" * 60)
        print(f"Total Tests: {report['total_tests']}")
        print(f"Total Passed: {report['total_passed']}")
        print(f"Total Failed: {report['total_failed']}")
        print("=" * 60)
        
        for test_result in results:
            print(f"\n{test_result['test_name']}:")
            for browser_result in test_result['browsers']:
                status_icon = '✅' if browser_result['status'] == 'passed' else '❌'
                print(f"  {status_icon} {browser_result['name']}: {browser_result['status']}")
                if 'error' in browser_result:
                    print(f"     Error: {browser_result['error']}")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Failed to generate report: {e}")


# JavaScript execution helpers (consistent with Phase 21)

def js_click(driver: webdriver.Remote, selector: str) -> bool:
    """
    Click element using JavaScript (bypasses visibility checks).
    
    Args:
        driver: WebDriver instance
        selector: CSS selector
    
    Returns:
        True if click succeeded, False otherwise
    """
    try:
        driver.execute_script(f"""
            const element = document.querySelector('{selector}');
            if (element) {{
                element.click();
                return true;
            }}
            return false;
        """)
        return True
    except Exception as e:
        logger.error(f"❌ js_click failed for {selector}: {e}")
        return False


def js_set_value(driver: webdriver.Remote, selector: str, value: str) -> bool:
    """
    Set input value using JavaScript.
    
    Args:
        driver: WebDriver instance
        selector: CSS selector
        value: Value to set
    
    Returns:
        True if set succeeded, False otherwise
    """
    try:
        driver.execute_script(f"""
            const element = document.querySelector('{selector}');
            if (element) {{
                element.value = '{value}';
                element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return true;
            }}
            return false;
        """)
        return True
    except Exception as e:
        logger.error(f"❌ js_set_value failed for {selector}: {e}")
        return False


def js_check_visible(driver: webdriver.Remote, selector: str) -> bool:
    """
    Check if element is visible using JavaScript.
    
    Args:
        driver: WebDriver instance
        selector: CSS selector
    
    Returns:
        True if visible, False otherwise
    """
    try:
        result = driver.execute_script(f"""
            const element = document.querySelector('{selector}');
            if (!element) return false;
            
            const style = window.getComputedStyle(element);
            return style.display !== 'none' && 
                   style.visibility !== 'hidden' && 
                   element.offsetWidth > 0 && 
                   element.offsetHeight > 0;
        """)
        return result
    except Exception as e:
        logger.error(f"❌ js_check_visible failed for {selector}: {e}")
        return False
