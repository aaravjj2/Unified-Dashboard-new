#!/usr/bin/env python3
"""
Strategy Lab Subtabs - Remove text-muted Classes

Removes all text-muted Bootstrap classes from Strategy Lab subtabs.
Keeps only explicit black text styling to ensure visibility.

Author: Autonomous Lead Engineer (Agent v2)
Date: October 28, 2025
"""

import re
from pathlib import Path

SUBTAB_FILES = [
    "financial_dashboard/tabs/strategy_lab/subtabs/setup.py",
    "financial_dashboard/tabs/strategy_lab/subtabs/backtest.py",
    "financial_dashboard/tabs/strategy_lab/subtabs/execution.py",
    "financial_dashboard/tabs/strategy_lab/subtabs/results.py",
    "financial_dashboard/tabs/strategy_lab/subtabs/benchmark.py",
    "financial_dashboard/tabs/strategy_lab/subtabs/risk.py",
]

def clean_text_muted(filepath):
    """Remove text-muted from className while preserving inline styles."""
    
    path = Path(filepath)
    if not path.exists():
        print(f"⚠️  SKIP: {filepath} (not found)")
        return 0
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    fixes = 0
    
    # Pattern: className="... text-muted ...", style={...}
    # Action: Remove text-muted from className
    pattern = r'className="([^"]*)\btext-muted\b([^"]*)"'
    
    def replacer(match):
        nonlocal fixes
        before = match.group(1)
        after = match.group(2)
        
        # Combine and clean
        new_classes = (before + after).strip()
        
        # Remove extra spaces
        new_classes = ' '.join(new_classes.split())
        
        if new_classes:
            fixes += 1
            return f'className="{new_classes}"'
        else:
            # If no classes left, remove className entirely
            fixes += 1
            return ''
    
    content = re.sub(pattern, replacer, content)
    
    # Clean up orphaned commas (e.g., ", style={...}" after className removal)
    content = re.sub(r',\s*style=', ' style=', content)
    content = re.sub(r'\(\s*,\s*style=', '(style=', content)
    
    if content != original:
        # Backup
        backup_path = path.with_suffix(path.suffix + '.bak_phase3')
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original)
        
        # Write cleaned version
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ FIXED: {filepath} ({fixes} text-muted removed)")
        return fixes
    else:
        print(f"✓  OK: {filepath} (no text-muted found)")
        return 0

def main():
    print("=" * 70)
    print("STRATEGY LAB SUBTABS - TEXT-MUTED CLEANUP")
    print("=" * 70)
    print()
    
    total_fixes = 0
    files_modified = 0
    
    for filepath in SUBTAB_FILES:
        fixes = clean_text_muted(filepath)
        if fixes > 0:
            total_fixes += fixes
            files_modified += 1
        print()
    
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Files Modified: {files_modified}/{len(SUBTAB_FILES)}")
    print(f"Total text-muted Removed: {total_fixes}")
    print()
    
    if files_modified > 0:
        print("✅ Subtabs cleaned - inline styles will now take precedence")
        print()
        print("🔄 Next: Restart dashboard")
        print("   docker-compose restart dash_app")
    
    print()

if __name__ == '__main__':
    main()
