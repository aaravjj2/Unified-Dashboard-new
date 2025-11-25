#!/usr/bin/env python3
"""
Fix broken imports across all tab files.
Changes `import _shared` to `from financial_dashboard import _shared`
and `from utils.` to `from financial_dashboard.utils.`
"""

import re
from pathlib import Path

def fix_imports_in_file(filepath):
    """Fix import statements in a single file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes = []
        
        # Fix 1: import _shared as SH
        if 'import _shared as SH' in content:
            content = content.replace(
                'import _shared as SH',
                'from financial_dashboard import _shared as SH'
            )
            changes.append('import _shared as SH → from financial_dashboard import _shared as SH')
        
        # Fix 2: from _shared import
        if 'from _shared import' in content:
            content = content.replace(
                'from _shared import',
                'from financial_dashboard._shared import'
            )
            changes.append('from _shared import → from financial_dashboard._shared import')
        
        # Fix 3: from utils. import (but not from financial_dashboard.utils)
        pattern = r'from utils\.'
        if re.search(pattern, content) and 'from financial_dashboard.utils.' not in content[:500]:
            content = re.sub(
                r'from utils\.',
                'from financial_dashboard.utils.',
                content
            )
            changes.append('from utils.* → from financial_dashboard.utils.*')
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes
        
        return False, []
        
    except Exception as e:
        return False, [f'Error: {e}']

def main():
    """Fix imports in all tab files."""
    tabs_dir = Path('financial_dashboard/tabs')
    
    fixed_files = []
    skipped_files = []
    
    print("🔧 FIXING BROKEN IMPORTS")
    print("=" * 70)
    
    for py_file in sorted(tabs_dir.glob('*.py')):
        # Skip backup files
        if any(x in py_file.name for x in ['BACKUP', 'OLD', 'CORRUPTED', 'TEMP']):
            skipped_files.append(py_file.name)
            continue
        
        was_fixed, changes = fix_imports_in_file(py_file)
        
        if was_fixed:
            print(f"\n✅ {py_file.name}")
            for change in changes:
                print(f"   • {change}")
            fixed_files.append(py_file.name)
        else:
            if changes:  # Error case
                print(f"\n❌ {py_file.name}")
                for change in changes:
                    print(f"   • {change}")
    
    print(f"\n{'=' * 70}")
    print(f"📊 SUMMARY")
    print(f"{'=' * 70}")
    print(f"Fixed: {len(fixed_files)} files")
    print(f"Skipped: {len(skipped_files)} backup files")
    
    if fixed_files:
        print(f"\n✅ Fixed files:")
        for f in fixed_files:
            print(f"   • {f}")

if __name__ == '__main__':
    main()
