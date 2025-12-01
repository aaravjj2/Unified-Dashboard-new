#!/usr/bin/env python3
"""
Direct Text-Muted Replacement Script

Manually replaces each text-muted occurrence with explicit black styling.
No complex regex - straightforward string replacement.

Author: Autonomous Lead Engineer (Agent v2)  
Date: October 28, 2025
"""

import re
from pathlib import Path

FILES_TO_FIX = [
    "financial_dashboard/tabs/home_lab/layout.py",
    "financial_dashboard/tabs/attribution_lab/layout.py", 
    "financial_dashboard/tabs/research_lab/layout.py",
    "financial_dashboard/tabs/options_lab/layout.py",
    "financial_dashboard/tabs/strategy_lab/layout.py",
    "financial_dashboard/tabs/home.py",
    "financial_dashboard/tabs/attribution_tab.py",
    "financial_dashboard/tabs/portfolio_tab.py",
    "financial_dashboard/tabs/volatility_lab.py",
    "financial_dashboard/tabs/market_forecast.py",
    "financial_dashboard/tabs/options_lab.py",
    "financial_dashboard/tabs/analysis_hub_refactored.py",
]

def fix_file(filepath):
    """Replace text-muted with black text styling in Python file."""
    
    path = Path(filepath)
    if not path.exists():
        print(f"⚠️  SKIP: {filepath} (not found)")
        return 0
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    fixes = 0
    
    # Find all className="..." with text-muted
    pattern = r'className\s*=\s*"([^"]*)"'
    
    def replacer(match):
        nonlocal fixes
        class_value = match.group(1)
        
        if 'text-muted' not in class_value:
            return match.group(0)  # No change
        
        # Remove text-muted from classes
        new_classes = ' '.join([c for c in class_value.split() if c != 'text-muted'])
        
        # Build replacement
        if new_classes:
            replacement = f'className="{new_classes}", style={{\'color\': \'#000000\'}}'
        else:
            replacement = 'style={\'color\': \'#000000\'}'
        
        fixes += 1
        return replacement
    
    content = re.sub(pattern, replacer, content)
    
    if content != original:
        # Create backup
        backup_path = path.with_suffix(path.suffix + '.bak_text_muted')
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original)
        
        # Write fixed version
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ FIXED: {filepath} ({fixes} replacements)")
        return fixes
    else:
        print(f"✓  OK: {filepath} (no text-muted)")
        return 0

def main():
    print("=" * 70)
    print("DIRECT TEXT-MUTED REPLACEMENT")
    print("=" * 70)
    print()
    
    total_fixes = 0
    files_modified = 0
    
    for filepath in FILES_TO_FIX:
        fixes = fix_file(filepath)
        if fixes > 0:
            total_fixes += fixes
            files_modified += 1
        print()
    
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Files Modified: {files_modified}/{len(FILES_TO_FIX)}")
    print(f"Total Fixes: {total_fixes}")
    print()
    
    if files_modified > 0:
        print("🔄 Restart dashboard:")
        print("   docker-compose restart dash_app")
    print()

if __name__ == '__main__':
    main()
