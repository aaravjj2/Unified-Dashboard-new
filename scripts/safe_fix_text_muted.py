#!/usr/bin/env python3
"""
SAFE Strategy Lab Subtabs Text-Muted Fix

Only removes "text-muted" from within className strings.
Preserves all other classes and structure.

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

def safe_remove_text_muted(filepath):
    """Safely remove only 'text-muted' from className values."""
    
    path = Path(filepath)
    if not path.exists():
        print(f"⚠️  SKIP: {filepath}")
        return 0
    
    with open(path, 'r') as f:
        lines = f.readlines()
    
    modified_lines = []
    fixes = 0
    
    for line in lines:
        original_line = line
        
        # Only process lines with className and text-muted
        if 'className' in line and 'text-muted' in line:
            # Pattern: className="xxx text-muted yyy" or className='xxx text-muted yyy'
            line = re.sub(r'(className\s*=\s*["\'])([^"\']*)\btext-muted\b([^"\']*)', 
                         lambda m: f'{m.group(1)}{m.group(2).strip()} {m.group(3).strip()}'.replace('  ', ' ').rstrip() + ('"' if '"' in m.group(1) else "'"),
                         line)
            
            if line != original_line:
                fixes += 1
        
        modified_lines.append(line)
    
    if fixes > 0:
        # Backup
        backup_path = path.with_suffix(path.suffix + '.bak_safe')
        with open(backup_path, 'w') as f:
            f.writelines(lines)
        
        # Write
        with open(path, 'w') as f:
            f.writelines(modified_lines)
        
        print(f"✅ FIXED: {filepath} ({fixes} lines)")
        return fixes
    else:
        print(f"✓  OK: {filepath}")
        return 0

def main():
    print("=" * 70)
    print("SAFE TEXT-MUTED REMOVAL")
    print("=" * 70)
    print()
    
    total = 0
    for fp in SUBTAB_FILES:
        total += safe_remove_text_muted(fp)
        print()
    
    print(f"Total fixes: {total}")
    print()

if __name__ == '__main__':
    main()
