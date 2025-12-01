#!/usr/bin/env python3
"""
Verify that Options Forecast has been removed from Market Forecast
"""

import sys
import re

print("="*80)
print("PHASE 20B - FORECAST ISOLATION VERIFICATION")
print("="*80)

# Read the market_forecast.py file
with open('financial_dashboard/tabs/market_forecast.py', 'r') as f:
    content = f.read()

# Check for Options Forecast elements that should NOT exist
forbidden_patterns = [
    r'ticker-dropdown-options',
    r'expiration-dropdown',
    r'fetch-options-btn',
    r'OptionsForecastEngine',
    r'Phase 6.*Options Forecast Section',
]

issues_found = []

for pattern in forbidden_patterns:
    matches = re.findall(pattern, content, re.IGNORECASE)
    if matches:
        issues_found.append(f"❌ Found forbidden pattern: '{pattern}' ({len(matches)} occurrences)")

# Check that Phase 20B comment exists
if "# Phase 20B: Options Forecast moved to Options Lab" in content:
    print("✅ Phase 20B comment found")
else:
    issues_found.append("❌ Phase 20B comment missing")

# Check line count (should be around 750)
line_count = len(content.split('\n'))
print(f"📄 File has {line_count} lines")

if line_count > 800:
    issues_found.append(f"⚠️  File too long ({line_count} lines, expected ~750)")

print("\n" + "="*80)
if issues_found:
    print("❌ FORECAST ISOLATION FAILED")
    print("="*80)
    for issue in issues_found:
        print(issue)
    sys.exit(1)
else:
    print("✅ FORECAST ISOLATION SUCCESSFUL")
    print("="*80)
    print("✓ No forbidden Options Forecast elements found in Market Forecast")
    print("✓ Phase 20B comment present")
    print("✓ File size appropriate")
    sys.exit(0)
