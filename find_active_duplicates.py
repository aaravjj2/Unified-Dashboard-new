#!/usr/bin/env python3
"""
Find duplicate IDs but ONLY in active files used by the running dashboard.
Filters out legacy/backup/refactored files that aren't imported.
"""
import re
from pathlib import Path
from collections import defaultdict

# Files that are NOT loaded by the active app
EXCLUDED_PATTERNS = [
    'legacy/',
    '_backup',
    '_old',
    '_refactored',
    '_new.py',
    '_fixed.py',
    '_debug.py',
    '_clean',
    '_full.py',
    '_minimal.py',
    '_simplified.py',
    '_standalone',
    'market_trends_new.py',
    'market_trends_refactored.py',
    'market_trends_callbacks_fixed.py',
    'app_refactored.py',
    'app_simplified.py',
    'app_minimal.py',
    'app_standalone_ssr.py',
    'app_fixed.py',
    'app_debug.py',
    'monthly_picks_app.py',
    'market_trends_dash.py',
    'index_full.py',
    'index_clean.py',
    'dashboard_clean_fixed.py',
]

def is_active_file(filepath: str) -> bool:
    """Check if file is part of the active codebase."""
    for pattern in EXCLUDED_PATTERNS:
        if pattern in filepath:
            return False
    return True

def extract_ids_from_file(filepath):
    """Extract all component IDs from a Python file."""
    try:
        content = filepath.read_text()
        # Match id='...' or id="..."
        pattern = r"id\s*=\s*['\"]([^'\"]+)['\"]"
        matches = re.findall(pattern, content)
        return [(match, str(filepath)) for match in matches]
    except Exception as e:
        return []

def main():
    dashboard_dir = Path(__file__).parent / "financial_dashboard"
    
    print("=" * 80)
    print("SCANNING FOR DUPLICATE IDs IN ACTIVE FILES ONLY")
    print("=" * 80)
    print()
    
    # Collect all IDs and their locations
    id_locations = defaultdict(list)
    active_files = 0
    skipped_files = 0
    
    for py_file in dashboard_dir.rglob("*.py"):
        filepath_str = str(py_file)
        
        if is_active_file(filepath_str):
            active_files += 1
            ids = extract_ids_from_file(py_file)
            for id_name, filepath in ids:
                id_locations[id_name].append(filepath)
        else:
            skipped_files += 1
    
    print(f"📁 Scanned {active_files} active files (skipped {skipped_files} legacy/backup files)")
    print()
    
    # Find duplicates (IDs appearing in multiple unique files)
    duplicates = {
        id_name: files 
        for id_name, files in id_locations.items() 
        if len(set(files)) > 1
    }
    
    if not duplicates:
        print("✅ No duplicate IDs found in active files!")
        return 0
    
    print(f"❌ Found {len(duplicates)} DUPLICATE IDs:\n")
    
    for id_name, files in sorted(duplicates.items()):
        unique_files = list(set(files))
        print(f"🔴 ID: '{id_name}'")
        print(f"   Appears in {len(unique_files)} active files:")
        for filepath in sorted(unique_files):
            # Count occurrences in this file
            count = files.count(filepath)
            rel_path = filepath.replace(str(dashboard_dir) + '/', '')
            print(f"     - {rel_path} ({count}x)")
        print()
    
    print("=" * 80)
    print(f"📊 Total duplicate IDs in active files: {len(duplicates)}")
    print("=" * 80)
    
    return 1

if __name__ == '__main__':
    exit(main())
