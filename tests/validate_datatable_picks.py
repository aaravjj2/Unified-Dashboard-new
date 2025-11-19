#!/usr/bin/env python3
"""
DataTable Validation for Weekly and Monthly Picks
Phase 2: Interactive validation with Playwright
"""
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Setup paths
DASH_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(DASH_ROOT))

# Create artifacts directory
ARTIFACTS_DIR = DASH_ROOT / 'tests' / 'logs' / 'datatable_validation'
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

def validate_weekly_picks():
    """Validate Weekly Picks DataTable"""
    print("=" * 80)
    print("VALIDATING WEEKLY PICKS DATATABLE")
    print("=" * 80)
    
    results = {
        'test': 'weekly_picks_datatable',
        'timestamp': datetime.now().isoformat(),
        'checks': {}
    }
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Navigate to dashboard
            print("📍 Navigating to http://127.0.0.1:8050/...")
            page.goto('http://127.0.0.1:8050/', wait_until='networkidle', timeout=30000)
            time.sleep(2)
            
            # Click Weekly Picks tab
            print("🖱️  Clicking Weekly Picks tab...")
            page.click('text=Weekly Picks')
            page.wait_for_timeout(3000)
            
            # Check for DataTable
            print("🔍 Looking for DataTable with id='weekly-table'...")
            datatable = page.query_selector('#weekly-table')
            
            if datatable:
                results['checks']['datatable_exists'] = True
                print("✅ DataTable found!")
                
                # Check table structure
                rows = page.query_selector_all('#weekly-table tbody tr')
                results['checks']['row_count'] = len(rows)
                print(f"✅ Found {len(rows)} rows")
                
                # Check columns
                headers = page.query_selector_all('#weekly-table thead th')
                column_names = [h.inner_text() for h in headers]
                results['checks']['columns'] = column_names
                print(f"✅ Columns: {', '.join(column_names)}")
                
                # Check for data in first row
                if rows:
                    first_row_cells = rows[0].query_selector_all('td')
                    first_row_data = [cell.inner_text() for cell in first_row_cells]
                    results['checks']['first_row_data'] = first_row_data
                    print(f"✅ First row data: {first_row_data}")
                
                # Take screenshot
                screenshot_path = ARTIFACTS_DIR / 'weekly_picks_datatable.png'
                page.screenshot(path=str(screenshot_path), full_page=True)
                results['checks']['screenshot'] = str(screenshot_path)
                print(f"✅ Screenshot saved: {screenshot_path}")
                
                results['status'] = 'SUCCESS'
                
            else:
                print("❌ DataTable NOT found!")
                results['checks']['datatable_exists'] = False
                results['status'] = 'FAILED'
                
                # Check for wp-content div
                wp_content = page.query_selector('#wp-content')
                if wp_content:
                    content_text = wp_content.inner_text()
                    results['checks']['wp_content_text'] = content_text[:500]
                    print(f"⚠️  wp-content exists with text: {content_text[:200]}")
                
                # Take debug screenshot anyway
                screenshot_path = ARTIFACTS_DIR / 'weekly_picks_NO_DATATABLE.png'
                page.screenshot(path=str(screenshot_path), full_page=True)
                results['checks']['debug_screenshot'] = str(screenshot_path)
            
            browser.close()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        results['status'] = 'ERROR'
        results['error'] = str(e)
    
    # Save results
    with open(ARTIFACTS_DIR / 'weekly_picks_validation.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Results saved to: {ARTIFACTS_DIR / 'weekly_picks_validation.json'}")
    return results

def validate_monthly_picks():
    """Validate Monthly Picks DataTable"""
    print("\n" + "=" * 80)
    print("VALIDATING MONTHLY PICKS DATATABLE")
    print("=" * 80)
    
    results = {
        'test': 'monthly_picks_datatable',
        'timestamp': datetime.now().isoformat(),
        'checks': {}
    }
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Navigate to dashboard
            print("📍 Navigating to http://127.0.0.1:8050/...")
            page.goto('http://127.0.0.1:8050/', wait_until='networkidle', timeout=30000)
            time.sleep(2)
            
            # Click Monthly Picks tab
            print("🖱️  Clicking Monthly Picks tab...")
            page.click('text=Monthly Picks')
            page.wait_for_timeout(3000)
            
            # Check for DataTable
            print("🔍 Looking for DataTable with id='monthly-table'...")
            datatable = page.query_selector('#monthly-table')
            
            if datatable:
                results['checks']['datatable_exists'] = True
                print("✅ DataTable found!")
                
                # Check table structure
                rows = page.query_selector_all('#monthly-table tbody tr')
                results['checks']['row_count'] = len(rows)
                print(f"✅ Found {len(rows)} rows")
                
                # Check columns
                headers = page.query_selector_all('#monthly-table thead th')
                column_names = [h.inner_text() for h in headers]
                results['checks']['columns'] = column_names
                print(f"✅ Columns: {', '.join(column_names)}")
                
                # Check for data in first row
                if rows:
                    first_row_cells = rows[0].query_selector_all('td')
                    first_row_data = [cell.inner_text() for cell in first_row_cells]
                    results['checks']['first_row_data'] = first_row_data
                    print(f"✅ First row data: {first_row_data}")
                
                # Take screenshot
                screenshot_path = ARTIFACTS_DIR / 'monthly_picks_datatable.png'
                page.screenshot(path=str(screenshot_path), full_page=True)
                results['checks']['screenshot'] = str(screenshot_path)
                print(f"✅ Screenshot saved: {screenshot_path}")
                
                results['status'] = 'SUCCESS'
                
            else:
                print("❌ DataTable NOT found!")
                results['checks']['datatable_exists'] = False
                results['status'] = 'FAILED'
                
                # Check for mp-content div
                mp_content = page.query_selector('#mp-content')
                if mp_content:
                    content_text = mp_content.inner_text()
                    results['checks']['mp_content_text'] = content_text[:500]
                    print(f"⚠️  mp-content exists with text: {content_text[:200]}")
                
                # Take debug screenshot anyway
                screenshot_path = ARTIFACTS_DIR / 'monthly_picks_NO_DATATABLE.png'
                page.screenshot(path=str(screenshot_path), full_page=True)
                results['checks']['debug_screenshot'] = str(screenshot_path)
            
            browser.close()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        results['status'] = 'ERROR'
        results['error'] = str(e)
    
    # Save results
    with open(ARTIFACTS_DIR / 'monthly_picks_validation.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Results saved to: {ARTIFACTS_DIR / 'monthly_picks_validation.json'}")
    return results

def check_server_logs():
    """Check server logs for DataTable-related messages"""
    print("\n" + "=" * 80)
    print("CHECKING SERVER LOGS")
    print("=" * 80)
    
    log_file = '/tmp/server_DATATABLE_FIX.log'
    if Path(log_file).exists():
        with open(log_file, 'r') as f:
            logs = f.read()
        
        # Search for DataTable-related messages
        datatable_logs = []
        for line in logs.split('\n'):
            if any(keyword in line.lower() for keyword in ['datatable', 'weekly', 'monthly', 'callback fired']):
                datatable_logs.append(line)
        
        if datatable_logs:
            print(f"Found {len(datatable_logs)} DataTable-related log entries (last 20):")
            for log in datatable_logs[-20:]:
                print(f"  {log}")
        else:
            print("No DataTable-related logs found")
    else:
        print(f"⚠️  Log file not found: {log_file}")

def generate_report(weekly_results, monthly_results):
    """Generate final validation report"""
    print("\n" + "=" * 80)
    print("GENERATING VALIDATION REPORT")
    print("=" * 80)
    
    report_lines = [
        "# DataTable Validation Report",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## Weekly Picks DataTable",
        f"- Status: **{weekly_results.get('status', 'UNKNOWN')}**",
        f"- DataTable Exists: {weekly_results.get('checks', {}).get('datatable_exists', 'N/A')}",
        f"- Row Count: {weekly_results.get('checks', {}).get('row_count', 'N/A')}",
        f"- Columns: {weekly_results.get('checks', {}).get('columns', [])}",
        "",
        "## Monthly Picks DataTable",
        f"- Status: **{monthly_results.get('status', 'UNKNOWN')}**",
        f"- DataTable Exists: {monthly_results.get('checks', {}).get('datatable_exists', 'N/A')}",
        f"- Row Count: {monthly_results.get('checks', {}).get('row_count', 'N/A')}",
        f"- Columns: {monthly_results.get('checks', {}).get('columns', [])}",
        "",
        "## Overall Assessment",
    ]
    
    if (weekly_results.get('status') == 'SUCCESS' and 
        monthly_results.get('status') == 'SUCCESS'):
        report_lines.append("✅ **ALL TESTS PASSED** - Both DataTables are rendering correctly!")
    else:
        report_lines.append("❌ **VALIDATION FAILED** - See details above")
    
    report_lines.extend([
        "",
        "## Artifacts",
        "- `weekly_picks_validation.json`",
        "- `monthly_picks_validation.json`",
        "- `weekly_picks_datatable.png`",
        "- `monthly_picks_datatable.png`",
        "",
        "---",
        "End of Report"
    ])
    
    report = "\n".join(report_lines)
    
    # Save report
    report_path = ARTIFACTS_DIR / 'datatable_validation_report.md'
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(report)
    print(f"\n✅ Report saved to: {report_path}")
    
    return report

def main():
    """Run full DataTable validation"""
    print("🚀 Starting DataTable Validation")
    print(f"📁 Artifacts directory: {ARTIFACTS_DIR}\n")
    
    try:
        # Validate Weekly Picks
        weekly_results = validate_weekly_picks()
        
        # Validate Monthly Picks
        monthly_results = validate_monthly_picks()
        
        # Check server logs
        check_server_logs()
        
        # Generate report
        generate_report(weekly_results, monthly_results)
        
        # Exit code based on results
        if (weekly_results.get('status') == 'SUCCESS' and 
            monthly_results.get('status') == 'SUCCESS'):
            print("\n✅ VALIDATION COMPLETE - All DataTables validated!")
            return 0
        else:
            print("\n⚠️  VALIDATION INCOMPLETE - Some checks failed")
            return 1
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 2

if __name__ == '__main__':
    sys.exit(main())
