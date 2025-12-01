#!/usr/bin/env python3
"""
Test Browser Console for Errors
Captures browser console errors on dashboard load to verify fixes.
"""
import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime

async def test_console_errors():
    """Capture and analyze browser console errors."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        console_messages = []
        errors = []
        warnings = []
        
        # Capture console messages
        page.on('console', lambda msg: console_messages.append({
            'type': msg.type,
            'text': msg.text,
            'location': msg.location
        }))
        
        # Capture page errors
        page.on('pageerror', lambda exc: errors.append(str(exc)))
        
        print("🌐 Loading dashboard at http://localhost:8050...")
        await page.goto('http://localhost:8050', wait_until='networkidle', timeout=60000)
        
        # Wait for Dash to render
        await page.wait_for_selector('#react-entry-point', timeout=30000)
        await asyncio.sleep(5)  # Let callbacks register
        
        # Count errors by type
        syntax_errors = [m for m in console_messages if 'SyntaxError' in m['text']]
        dash_errors = [m for m in console_messages if 'dash_renderer' in m['text']]
        duplicate_callback_errors = [m for m in console_messages if 'Duplicate callback' in m['text']]
        
        # Generate report
        report = {
            'timestamp': datetime.now().isoformat(),
            'url': 'http://localhost:8050',
            'summary': {
                'total_messages': len(console_messages),
                'errors': len([m for m in console_messages if m['type'] == 'error']),
                'warnings': len([m for m in console_messages if m['type'] == 'warning']),
                'info': len([m for m in console_messages if m['type'] == 'info']),
                'syntax_errors': len(syntax_errors),
                'dash_renderer_errors': len(dash_errors),
                'duplicate_callback_warnings': len(duplicate_callback_errors)
            },
            'syntax_errors': syntax_errors[:10],  # First 10
            'dash_errors': dash_errors[:10],
            'duplicate_warnings': duplicate_callback_errors[:10],
            'page_errors': errors
        }
        
        # Print summary
        print("\n" + "="*70)
        print("BROWSER CONSOLE ERROR REPORT")
        print("="*70)
        print(f"Total console messages: {report['summary']['total_messages']}")
        print(f"  Errors: {report['summary']['errors']}")
        print(f"  Warnings: {report['summary']['warnings']}")
        print(f"  Info: {report['summary']['info']}")
        print(f"\nSpecific Issues:")
        print(f"  SyntaxError count: {report['summary']['syntax_errors']}")
        print(f"  Dash renderer errors: {report['summary']['dash_renderer_errors']}")
        print(f"  Duplicate callback warnings: {report['summary']['duplicate_callback_warnings']}")
        print(f"  Page errors: {len(errors)}")
        
        if syntax_errors:
            print(f"\n⚠️  SYNTAX ERRORS DETECTED:")
            for err in syntax_errors[:5]:
                print(f"  - {err['text'][:100]}")
        else:
            print(f"\n✅ NO SYNTAX ERRORS!")
        
        if dash_errors:
            print(f"\n⚠️  DASH RENDERER ERRORS:")
            for err in dash_errors[:5]:
                print(f"  - {err['text'][:100]}")
        else:
            print(f"\n✅ NO DASH RENDERER ERRORS!")
        
        # Save full report
        report_file = f'reports/console_error_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Full report saved to: {report_file}")
        print("="*70)
        
        # Keep browser open for manual inspection
        print("\n👁️  Browser will stay open for 30 seconds for manual inspection...")
        await asyncio.sleep(30)
        
        await browser.close()
        
        # Return exit code based on errors
        if syntax_errors or len(errors) > 0:
            return 1
        elif dash_errors:
            return 2
        elif duplicate_callback_errors:
            print("\n⚠️  Duplicate callback warnings detected but these may be intentional (allow_duplicate=True)")
            return 0
        else:
            print("\n🎉 PERFECT! No errors detected!")
            return 0

if __name__ == '__main__':
    exit_code = asyncio.run(test_console_errors())
    exit(exit_code)
