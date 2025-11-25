#!/usr/bin/env python3
"""
Emergency Console Error Diagnostic
Captures detailed browser console errors to identify root cause of 989 errors
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

async def diagnose_console_errors():
    """Launch dashboard with headed browser and capture detailed console errors"""
    
    console_errors = []
    console_warnings = []
    console_logs = []
    network_errors = []
    
    async with async_playwright() as p:
        # Launch headed browser for visibility
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )
        
        page = await context.new_page()
        
        # Capture console messages
        def handle_console(msg):
            msg_data = {
                'type': msg.type,
                'text': msg.text,
                'location': msg.location,
                'timestamp': datetime.now().isoformat()
            }
            
            if msg.type == 'error':
                console_errors.append(msg_data)
                print(f"❌ ERROR: {msg.text[:200]}")
            elif msg.type == 'warning':
                console_warnings.append(msg_data)
                print(f"⚠️  WARNING: {msg.text[:200]}")
            else:
                console_logs.append(msg_data)
        
        page.on('console', handle_console)
        
        # Capture page errors
        def handle_page_error(error):
            error_data = {
                'message': str(error),
                'timestamp': datetime.now().isoformat()
            }
            network_errors.append(error_data)
            print(f"🔥 PAGE ERROR: {error}")
        
        page.on('pageerror', handle_page_error)
        
        # Capture failed requests
        def handle_request_failed(request):
            failure = request.failure
            if failure:
                network_errors.append({
                    'url': request.url,
                    'failure': failure,
                    'timestamp': datetime.now().isoformat()
                })
                print(f"🌐 REQUEST FAILED: {request.url}")
        
        page.on('requestfailed', handle_request_failed)
        
        print("\n" + "="*80)
        print("🔍 CONSOLE ERROR DIAGNOSTIC - DASHBOARD STARTUP")
        print("="*80 + "\n")
        
        try:
            print("📡 Navigating to http://localhost:8051...")
            await page.goto('http://localhost:8051', wait_until='networkidle', timeout=60000)
            
            print("⏳ Waiting 10 seconds for dashboard initialization...")
            await asyncio.sleep(10)
            
            print(f"\n📊 INITIAL ERROR COUNT: {len(console_errors)}")
            
            # Try to expand console errors to see full details
            print("\n🔎 Capturing detailed error information...")
            
            # Get specific error details from the page
            error_details = await page.evaluate("""
                () => {
                    const errors = [];
                    const originalError = console.error;
                    
                    // Check for Dash-specific errors
                    if (window._dashprivate_config) {
                        errors.push({
                            type: 'dash_config',
                            config: window._dashprivate_config
                        });
                    }
                    
                    // Check for callback errors
                    if (window._dashprivate_callbacks) {
                        errors.push({
                            type: 'dash_callbacks',
                            callbacks: Object.keys(window._dashprivate_callbacks || {}).length
                        });
                    }
                    
                    return errors;
                }
            """)
            
            print(f"\n📋 Dash Configuration Details:")
            print(json.dumps(error_details, indent=2))
            
            # Wait longer to capture all errors
            print("\n⏳ Waiting 20 more seconds to capture all errors...")
            await asyncio.sleep(20)
            
            print(f"\n📊 FINAL ERROR COUNT: {len(console_errors)}")
            print(f"📊 WARNING COUNT: {len(console_warnings)}")
            print(f"📊 NETWORK ERROR COUNT: {len(network_errors)}")
            
            # Save detailed report
            report = {
                'total_errors': len(console_errors),
                'total_warnings': len(console_warnings),
                'total_network_errors': len(network_errors),
                'console_errors': console_errors[:50],  # First 50 errors
                'console_warnings': console_warnings[:20],  # First 20 warnings
                'network_errors': network_errors,
                'error_details': error_details,
                'timestamp': datetime.now().isoformat()
            }
            
            report_path = Path('/home/aarav/unified-dashboard/reports/console_error_diagnostic.json')
            report_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            print(f"\n💾 Full report saved to: {report_path}")
            
            # Analyze error patterns
            print("\n" + "="*80)
            print("📈 ERROR PATTERN ANALYSIS")
            print("="*80)
            
            # Group errors by type
            error_texts = [e['text'][:100] for e in console_errors[:20]]
            unique_patterns = set(error_texts)
            
            print(f"\n🔢 Unique Error Patterns: {len(unique_patterns)}")
            print("\n📝 Sample Error Messages:")
            for i, pattern in enumerate(list(unique_patterns)[:10], 1):
                print(f"  {i}. {pattern}")
            
            # Check for specific known issues
            print("\n🔍 Checking for Known Issues:")
            
            duplicate_outputs = any('duplicate' in e['text'].lower() or 'already defined' in e['text'].lower() 
                                   for e in console_errors)
            missing_components = any('component' in e['text'].lower() and 'not found' in e['text'].lower() 
                                    for e in console_errors)
            callback_errors = any('callback' in e['text'].lower() for e in console_errors)
            
            print(f"  - Duplicate callback outputs: {'✅ DETECTED' if duplicate_outputs else '❌ Not found'}")
            print(f"  - Missing components: {'✅ DETECTED' if missing_components else '❌ Not found'}")
            print(f"  - Callback errors: {'✅ DETECTED' if callback_errors else '❌ Not found'}")
            
            print("\n⏸️  Browser will stay open for 30 seconds for manual inspection...")
            await asyncio.sleep(30)
            
        except Exception as e:
            print(f"\n❌ DIAGNOSTIC ERROR: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            print("\n🔚 Closing browser...")
            await browser.close()
    
    return len(console_errors)

if __name__ == '__main__':
    print("\n🚀 Starting Console Error Diagnostic...")
    print("⚠️  Make sure the dashboard is running on http://localhost:8051\n")
    
    error_count = asyncio.run(diagnose_console_errors())
    
    print("\n" + "="*80)
    print(f"✅ DIAGNOSTIC COMPLETE - {error_count} errors captured")
    print("="*80 + "\n")
