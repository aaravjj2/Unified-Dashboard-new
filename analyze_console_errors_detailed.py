"""
Detailed analysis of browser console errors to distinguish:
1. Callback registration duplicates (BAD - need to fix)
2. allow_duplicate output warnings (OK - intentional)
"""

from playwright.sync_api import sync_playwright
import time
import re

def analyze_console_errors():
    """Capture and categorize all console errors"""
    
    console_messages = []
    
    def handle_console(msg):
        if msg.type == 'error' or 'duplicate' in msg.text.lower():
            console_messages.append({
                'type': msg.type,
                'text': msg.text,
                'location': msg.location
            })
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on('console', handle_console)
        
        print("🔍 Loading dashboard and capturing console errors...")
        page.goto('http://localhost:8051', wait_until='networkidle', timeout=60000)
        time.sleep(10)  # Let all callbacks register
        
        browser.close()
    
    # Analyze messages
    print(f"\n📊 Captured {len(console_messages)} console messages\n")
    
    # Categorize errors
    registration_duplicates = []
    output_duplicates = []
    allow_duplicate_warnings = []
    other_errors = []
    
    for msg in console_messages:
        text = msg['text']
        
        # Pattern 1: Callback registration duplicate (BAD)
        if re.search(r'Attempting to register a duplicate callback', text):
            registration_duplicates.append(msg)
        
        # Pattern 2: Output duplicate without allow_duplicate (BAD)
        elif re.search(r'duplicate output.+without.+allow_duplicate', text, re.IGNORECASE):
            output_duplicates.append(msg)
        
        # Pattern 3: allow_duplicate warning (OK - intentional)
        elif re.search(r'allow_duplicate.+(true|True)', text):
            allow_duplicate_warnings.append(msg)
        
        # Pattern 4: Other duplicates
        elif 'duplicate' in text.lower():
            other_errors.append(msg)
    
    # Report
    print("="*80)
    print("🚨 CALLBACK REGISTRATION DUPLICATES (BAD - need to fix):")
    print("="*80)
    for msg in registration_duplicates[:10]:
        print(f"\n{msg['text'][:200]}")
    if len(registration_duplicates) > 10:
        print(f"\n... and {len(registration_duplicates) - 10} more")
    print(f"\n📊 Total: {len(registration_duplicates)}")
    
    print("\n" + "="*80)
    print("⚠️  OUTPUT DUPLICATES WITHOUT allow_duplicate (BAD - need flag):")
    print("="*80)
    for msg in output_duplicates[:10]:
        print(f"\n{msg['text'][:200]}")
    if len(output_duplicates) > 10:
        print(f"\n... and {len(output_duplicates) - 10} more")
    print(f"\n📊 Total: {len(output_duplicates)}")
    
    print("\n" + "="*80)
    print("✅ allow_duplicate WARNINGS (OK - intentional):")
    print("="*80)
    for msg in allow_duplicate_warnings[:10]:
        print(f"\n{msg['text'][:200]}")
    if len(allow_duplicate_warnings) > 10:
        print(f"\n... and {len(allow_duplicate_warnings) - 10} more")
    print(f"\n📊 Total: {len(allow_duplicate_warnings)}")
    
    print("\n" + "="*80)
    print("❓ OTHER DUPLICATE ERRORS:")
    print("="*80)
    for msg in other_errors[:10]:
        print(f"\n{msg['text'][:200]}")
    if len(other_errors) > 10:
        print(f"\n... and {len(other_errors) - 10} more")
    print(f"\n📊 Total: {len(other_errors)}")
    
    # Summary
    print("\n" + "="*80)
    print("📋 SUMMARY:")
    print("="*80)
    print(f"🚨 Callback registration duplicates: {len(registration_duplicates)} (MUST FIX)")
    print(f"⚠️  Output duplicates without flag: {len(output_duplicates)} (MUST FIX)")
    print(f"✅ allow_duplicate warnings: {len(allow_duplicate_warnings)} (OK)")
    print(f"❓ Other duplicate errors: {len(other_errors)}")
    print(f"📊 Total console messages: {len(console_messages)}")
    
    print("\n" + "="*80)
    print("🎯 ACTION ITEMS:")
    print("="*80)
    critical_count = len(registration_duplicates) + len(output_duplicates)
    if critical_count == 0:
        print("✅ NO CRITICAL ERRORS - All duplicates are intentional with allow_duplicate=True")
        print("✅ Dashboard callbacks are correctly configured!")
    else:
        print(f"❌ {critical_count} CRITICAL ERRORS need to be fixed")
        print(f"   - {len(registration_duplicates)} callback registration duplicates")
        print(f"   - {len(output_duplicates)} output duplicates without allow_duplicate flag")

if __name__ == '__main__':
    analyze_console_errors()
