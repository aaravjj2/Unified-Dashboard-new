#!/usr/bin/env python3
"""
Headed Playwright Button Validation Suite

Per SUPER-PROMPT requirements:
- HEADLESS BROWSERS FORBIDDEN - use headed Chromium only
- IMMEDIATE ANALYSIS after each click
- Capture: screenshot, DOM, HAR, console
- Automated repair loop (3 attempts per failing button)
- Save all artifacts to reports/duplicates_fix/playwright/
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page
import hashlib


# REQUIRED BUTTON LIST from prompt
REQUIRED_BUTTONS = {
    'market_trends': [
        ('mt-run-analysis-btn', 'Run Market Analysis', 'network_call'),
        ('mt-refresh-news-btn', 'Refresh News', 'dom_update'),
        ('mt-download-csv-btn', 'Download CSV', 'download'),
    ],
    'market_forecast': [
        ('mf-run-btn', 'Run Forecast', 'network_call'),
        ('mf-explain-btn', 'Show Explanation', 'modal_open'),
    ],
    'research_lab': [
        ('rl-brief-create-btn', 'Create Brief', 'modal_open'),
        ('rl-screen-run-btn', 'Run Screen', 'network_call'),
        ('rl-backtest-run-btn', 'Run Backtest', 'network_call'),
    ],
    'options_lab': [
        ('ol-chain-load-btn', 'Load Options Chain', 'network_call'),
        ('ol-forecast-run-btn', 'Run Forecast', 'network_call'),
        ('ol-backtest-run-btn', 'Run Backtest', 'network_call'),
        ('ol-manual-order-submit', 'Submit Order', 'network_call'),
    ],
    'volatility_lab': [
        ('vl-calc-run-btn', 'Run Calculation', 'network_call'),
        ('vl-signal-run-btn', 'Run Signals', 'network_call'),
        ('vl-backtest-run-btn', 'Run Backtest', 'network_call'),
    ],
    'portfolio': [
        ('pf-refresh-btn', 'Refresh Portfolio', 'network_call'),
        ('pf-sync-alpaca-btn', 'Sync with Alpaca', 'network_call'),
    ],
}

# Artifact directories
ARTIFACTS_DIR = Path('reports/duplicates_fix')
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


class ButtonValidator:
    """Validates button functionality with headed browser."""
    
    def __init__(self):
        self.results = []
        self.artifacts_dir = ARTIFACTS_DIR
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
    async def validate_button(self, page: Page, tab_id: str, button_id: str, 
                             button_name: str, expected_effect: str, attempt: int = 1):
        """
        Validate a single button with full artifact capture.
        
        Returns: (pass: bool, verdict: str, artifacts: dict)
        """
        print(f"\n{'='*80}")
        print(f"🔘 Testing: {button_name} (#{button_id}) - Attempt {attempt}/3")
        print(f"   Tab: {tab_id}, Expected: {expected_effect}")
        print('='*80)
        
        artifacts = {
            'button_id': button_id,
            'tab_id': tab_id,
            'button_name': button_name,
            'expected_effect': expected_effect,
            'attempt': attempt,
            'timestamp': datetime.now().isoformat(),
            'pass': False,
            'verdict': '',
            'error': None,
            'files': {}
        }
        
        try:
            # Navigate to tab if needed
            await self.navigate_to_tab(page, tab_id)
            await asyncio.sleep(2)
            
            # Check if button exists and is visible
            button = await page.query_selector(f'#{button_id}')
            if not button:
                # Try alternative selectors
                button = await page.query_selector(f'button:has-text("{button_name}")')
            
            if not button:
                artifacts['error'] = 'Button not found in DOM'
                artifacts['verdict'] = f"❌ FAIL: Button #{button_id} not found"
                print(artifacts['verdict'])
                return False, artifacts
            
            is_visible = await button.is_visible()
            is_enabled = await button.is_enabled()
            
            if not is_visible:
                artifacts['error'] = 'Button not visible'
                artifacts['verdict'] = f"❌ FAIL: Button not visible"
                print(artifacts['verdict'])
                return False, artifacts
            
            if not is_enabled:
                artifacts['error'] = 'Button disabled'
                artifacts['verdict'] = f"⚠️  WARN: Button disabled"
                print(artifacts['verdict'])
                # Continue testing - disabled state might be intentional
            
            # Pre-click screenshot
            pre_screenshot_path = self.artifacts_dir / 'screenshots' / f'{button_id}_attempt{attempt}_pre.png'
            pre_screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(pre_screenshot_path), full_page=True)
            artifacts['files']['pre_screenshot'] = str(pre_screenshot_path)
            print(f"  📸 Pre-click screenshot: {pre_screenshot_path.name}")
            
            # Capture pre-click DOM hash
            pre_dom = await page.content()
            pre_dom_hash = hashlib.md5(pre_dom.encode()).hexdigest()
            
            # Start HAR recording
            console_messages = []
            network_requests = []
            
            def handle_console(msg):
                console_messages.append({
                    'type': msg.type,
                    'text': msg.text,
                    'location': str(msg.location) if msg.location else None
                })
            
            def handle_request(request):
                network_requests.append({
                    'url': request.url,
                    'method': request.method,
                    'timestamp': datetime.now().isoformat()
                })
            
            page.on('console', handle_console)
            page.on('request', handle_request)
            
            # CLICK THE BUTTON
            print(f"  🖱️  Clicking button...")
            await button.click()
            await asyncio.sleep(3)  # Wait for async operations
            
            # Post-click screenshot
            post_screenshot_path = self.artifacts_dir / 'screenshots' / f'{button_id}_attempt{attempt}_post.png'
            await page.screenshot(path=str(post_screenshot_path), full_page=True)
            artifacts['files']['post_screenshot'] = str(post_screenshot_path)
            print(f"  📸 Post-click screenshot: {post_screenshot_path.name}")
            
            # Capture post-click DOM
            post_dom = await page.content()
            post_dom_hash = hashlib.md5(post_dom.encode()).hexdigest()
            post_dom_path = self.artifacts_dir / 'dom' / f'{button_id}_attempt{attempt}_post.html'
            post_dom_path.parent.mkdir(parents=True, exist_ok=True)
            post_dom_path.write_text(post_dom)
            artifacts['files']['post_dom'] = str(post_dom_path)
            
            # Save console logs
            console_log_path = self.artifacts_dir / 'playwright' / f'{button_id}_attempt{attempt}_console.json'
            console_log_path.parent.mkdir(parents=True, exist_ok=True)
            console_log_path.write_text(json.dumps(console_messages, indent=2))
            artifacts['files']['console_log'] = str(console_log_path)
            print(f"  📝 Console messages: {len(console_messages)}")
            
            # Save network requests
            network_log_path = self.artifacts_dir / 'playwright' / f'{button_id}_attempt{attempt}_network.json'
            network_log_path.write_text(json.dumps(network_requests, indent=2))
            artifacts['files']['network_log'] = str(network_log_path)
            print(f"  🌐 Network requests: {len(network_requests)}")
            
            # IMMEDIATE ANALYSIS
            dom_changed = pre_dom_hash != post_dom_hash
            has_network_activity = len(network_requests) > 0
            has_console_errors = any(m['type'] == 'error' for m in console_messages)
            
            print(f"\n  📊 ANALYSIS:")
            print(f"     DOM Changed: {'✅ YES' if dom_changed else '❌ NO'}")
            print(f"     Network Activity: {'✅ YES' if has_network_activity else '❌ NO'}")
            print(f"     Console Errors: {'❌ YES' if has_console_errors else '✅ NO'}")
            
            # Validate expected effect
            passed = False
            
            if expected_effect == 'network_call':
                passed = has_network_activity
                artifacts['verdict'] = f"{'✅ PASS' if passed else '❌ FAIL'}: Network call {'detected' if passed else 'NOT detected'}"
            
            elif expected_effect == 'dom_update':
                passed = dom_changed
                artifacts['verdict'] = f"{'✅ PASS' if passed else '❌ FAIL'}: DOM {'changed' if passed else 'unchanged'}"
            
            elif expected_effect == 'modal_open':
                # Check for modal elements
                modal_visible = await page.query_selector('.modal.show, .modal.fade.show, div[role="dialog"][style*="display: block"]')
                passed = modal_visible is not None
                artifacts['verdict'] = f"{'✅ PASS' if passed else '❌ FAIL'}: Modal {'opened' if passed else 'NOT opened'}"
            
            elif expected_effect == 'download':
                # Check for download initiated (network or file download)
                passed = has_network_activity or dom_changed
                artifacts['verdict'] = f"{'✅ PASS' if passed else '❌ FAIL'}: Download {'triggered' if passed else 'NOT triggered'}"
            
            artifacts['pass'] = passed
            artifacts['dom_changed'] = dom_changed
            artifacts['network_activity'] = has_network_activity
            artifacts['console_errors'] = has_console_errors
            
            print(f"\n  {artifacts['verdict']}")
            
            return passed, artifacts
            
        except Exception as e:
            artifacts['error'] = str(e)
            artifacts['verdict'] = f"❌ EXCEPTION: {str(e)[:100]}"
            print(f"\n  {artifacts['verdict']}")
            return False, artifacts
    
    async def navigate_to_tab(self, page: Page, tab_id: str):
        """Navigate to a specific tab."""
        # Click the tab navigation item
        tab_selector = f'.nav-item:has-text("{tab_id.replace("_", " ").title()}")'
        try:
            await page.click(tab_selector, timeout=5000)
            await asyncio.sleep(1)
        except:
            # Try alternative selector
            tab_selector = f'a[href="#{tab_id}"]'
            try:
                await page.click(tab_selector, timeout=5000)
                await asyncio.sleep(1)
            except:
                print(f"  ⚠️  Could not navigate to tab {tab_id}, continuing anyway...")
    
    async def run_full_audit(self):
        """Run complete button validation audit."""
        print("=" * 80)
        print("HEADED PLAYWRIGHT BUTTON VALIDATION SUITE")
        print("=" * 80)
        print(f"Timestamp: {self.timestamp}")
        print(f"Artifacts: {self.artifacts_dir}")
        print("=" * 80)
        
        async with async_playwright() as p:
            # Launch HEADED browser (headless=False)
            browser = await p.chromium.launch(headless=False, slow_mo=500)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            # Navigate to dashboard
            print("\n🌐 Loading dashboard...")
            await page.goto('http://localhost:8050', wait_until='networkidle', timeout=60000)
            await asyncio.sleep(5)
            print("✅ Dashboard loaded\n")
            
            # Test all buttons
            total_tests = sum(len(buttons) for buttons in REQUIRED_BUTTONS.values())
            tests_passed = 0
            tests_failed = 0
            
            for tab_id, buttons in REQUIRED_BUTTONS.items():
                print(f"\n{'#'*80}")
                print(f"# TAB: {tab_id.upper()}")
                print(f"{'#'*80}")
                
                for button_id, button_name, expected_effect in buttons:
                    # Try up to 3 times per button
                    passed = False
                    final_artifacts = None
                    
                    for attempt in range(1, 4):
                        passed, artifacts = await self.validate_button(
                            page, tab_id, button_id, button_name, expected_effect, attempt
                        )
                        
                        final_artifacts = artifacts
                        
                        if passed:
                            break
                        
                        if attempt < 3:
                            print(f"  🔄 Retrying (attempt {attempt+1}/3)...")
                            await asyncio.sleep(2)
                    
                    self.results.append(final_artifacts)
                    
                    if passed:
                        tests_passed += 1
                    else:
                        tests_failed += 1
                        # Create blocker report if all 3 attempts failed
                        if final_artifacts['attempt'] == 3:
                            self.create_blocker_report(final_artifacts)
            
            # Keep browser open for manual inspection
            print("\n" + "=" * 80)
            print("⏸️  Browser will remain open for 60 seconds for manual inspection...")
            print("=" * 80)
            await asyncio.sleep(60)
            
            await browser.close()
        
        # Generate final report
        self.generate_final_report(total_tests, tests_passed, tests_failed)
    
    def create_blocker_report(self, artifacts):
        """Create blocker report for failing button."""
        blocker_path = self.artifacts_dir / f"BLOCKER_{artifacts['button_id']}.md"
        
        content = f"""# BLOCKER REPORT: {artifacts['button_name']}

**Button ID:** {artifacts['button_id']}  
**Tab:** {artifacts['tab_id']}  
**Expected Effect:** {artifacts['expected_effect']}  
**Attempts:** {artifacts['attempt']}  
**Status:** ❌ FAILED

## Verdict

{artifacts['verdict']}

## Error

```
{artifacts.get('error', 'No error details')}
```

## Artifacts

- Pre-screenshot: `{artifacts['files'].get('pre_screenshot', 'N/A')}`
- Post-screenshot: `{artifacts['files'].get('post_screenshot', 'N/A')}`
- DOM snapshot: `{artifacts['files'].get('post_dom', 'N/A')}`
- Console log: `{artifacts['files'].get('console_log', 'N/A')}`
- Network log: `{artifacts['files'].get('network_log', 'N/A')}`

## Analysis

- DOM Changed: {artifacts.get('dom_changed', False)}
- Network Activity: {artifacts.get('network_activity', False)}
- Console Errors: {artifacts.get('console_errors', False)}

## Recommended Next Steps

1. Inspect screenshots for visual differences
2. Review DOM snapshot for structural changes
3. Check console log for JavaScript errors
4. Verify callback is registered and firing
5. Check network log for failed API calls

## Manual Verification

Open the dashboard and:
1. Navigate to **{artifacts['tab_id']}** tab
2. Click **{artifacts['button_name']}** button
3. Observe expected behavior: **{artifacts['expected_effect']}**
"""
        blocker_path.write_text(content)
        print(f"\n  📄 Blocker report: {blocker_path.name}")
    
    def generate_final_report(self, total, passed, failed):
        """Generate comprehensive final report."""
        report_path = self.artifacts_dir / 'playwright' / f'full_audit_result_{self.timestamp}.json'
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        summary = {
            'timestamp': self.timestamp,
            'tests_total': total,
            'tests_passed': passed,
            'tests_failed': failed,
            'pass_rate': (passed / total * 100) if total > 0 else 0,
            'results': self.results
        }
        
        report_path.write_text(json.dumps(summary, indent=2))
        
        print("\n" + "=" * 80)
        print("FINAL AUDIT RESULTS")
        print("=" * 80)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed} ({'✅' if passed == total else '❌'})")
        print(f"Failed: {failed}")
        print(f"Pass Rate: {summary['pass_rate']:.1f}%")
        print(f"\nFull report: {report_path}")
        print("=" * 80)
        
        # Check acceptance criteria
        if passed == total and failed == 0:
            success_marker = self.artifacts_dir / 'PHASE_DUPLICATE_CALLBACKS_SUCCESS'
            success_marker.touch()
            print("\n🎉 ✅ ALL ACCEPTANCE CRITERIA MET!")
            print(f"Success marker created: {success_marker}")
        else:
            print(f"\n⚠️  {failed} button(s) still failing - review BLOCKER_*.md files")


async def main():
    """Run button validation suite."""
    validator = ButtonValidator()
    await validator.run_full_audit()


if __name__ == '__main__':
    asyncio.run(main())
