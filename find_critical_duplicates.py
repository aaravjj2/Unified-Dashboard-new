#!/usr/bin/env python3
"""
Identify CRITICAL duplicate IDs that will cause Dash startup failure.
Filters out:
1. Test files (not loaded by app)
2. Component patterns (where inclusion is intentional)
3. Strategy Lab modular pattern (if only one layout is loaded)
"""
import re
from pathlib import Path
from collections import defaultdict

EXCLUDED_PATTERNS = [
    'legacy/', '_backup', '_old', '_refactored', '_new.py', '_fixed.py',
    '_debug.py', '_clean', '_full.py', '_minimal.py', '_simplified.py',
    '_standalone', 'market_trends_new.py', 'market_trends_refactored.py',
    'market_trends_callbacks_fixed.py', 'app_refactored.py', 'app_simplified.py',
    'app_minimal.py', 'app_standalone_ssr.py', 'app_fixed.py', 'app_debug.py',
    'monthly_picks_app.py', 'market_trends_dash.py', 'index_full.py',
    'index_clean.py', 'dashboard_clean_fixed.py',
]

# Test files - IDs here don't matter
TEST_FILE_PATTERNS = ['test_', '_test', 'tests/']

def is_test_file(filepath: str) -> bool:
    for pattern in TEST_FILE_PATTERNS:
        if pattern in filepath:
            return True
    return False

def is_active_file(filepath: str) -> bool:
    for pattern in EXCLUDED_PATTERNS:
        if pattern in filepath:
            return False
    return True

def extract_ids_from_file(filepath):
    try:
        content = filepath.read_text()
        pattern = r"id\s*=\s*['\"]([^'\"]+)['\"]"
        matches = re.findall(pattern, content)
        return [(match, str(filepath)) for match in matches]
    except Exception as e:
        return []

def main():
    dashboard_dir = Path(__file__).parent / "financial_dashboard"
    
    print("=" * 80)
    print("🔍 CRITICAL DUPLICATE IDs (Dash Startup Blockers)")
    print("=" * 80)
    print()
    
    # Collect all IDs and their locations
    id_locations = defaultdict(list)
    
    for py_file in dashboard_dir.rglob("*.py"):
        filepath_str = str(py_file)
        
        if is_active_file(filepath_str) and not is_test_file(filepath_str):
            ids = extract_ids_from_file(py_file)
            for id_name, filepath in ids:
                id_locations[id_name].append(filepath)
    
    # Find duplicates in non-test active files
    duplicates = {
        id_name: files 
        for id_name, files in id_locations.items() 
        if len(set(files)) > 1
    }
    
    if not duplicates:
        print("✅ No critical duplicate IDs found!")
        return 0
    
    # Categorize duplicates
    critical = []
    component_pattern = []
    strategy_lab = []
    
    for id_name, files in sorted(duplicates.items()):
        unique_files = list(set(files))
        
        # Check if it's a component pattern (component file + index.py)
        if len(unique_files) == 2:
            files_str = '|'.join(unique_files)
            if 'components/' in files_str and 'index.py' in files_str:
                component_pattern.append((id_name, unique_files))
                continue
        
        # Check if it's Strategy Lab modular pattern
        if any('strategy_lab' in f for f in unique_files):
            if all('strategy_lab' in f for f in unique_files):
                strategy_lab.append((id_name, unique_files))
                continue
        
        # Otherwise it's critical
        critical.append((id_name, unique_files))
    
    print("🚨 CRITICAL BLOCKERS (Must Fix):")
    print()
    if critical:
        for id_name, files in critical:
            print(f"❌ ID: '{id_name}'")
            for filepath in sorted(files):
                count = sum(1 for f in duplicates[id_name] if f == filepath)
                rel_path = filepath.replace(str(dashboard_dir) + '/', '')
                print(f"     - {rel_path} ({count}x)")
            print()
    else:
        print("  ✅ None!")
        print()
    
    print("⚠️  COMPONENT PATTERNS (May be intentional):")
    print()
    if component_pattern:
        for id_name, files in component_pattern:
            print(f"🟡 ID: '{id_name}'")
            for filepath in sorted(files):
                rel_path = filepath.replace(str(dashboard_dir) + '/', '')
                print(f"     - {rel_path}")
            print()
    else:
        print("  None")
        print()
    
    print("📦 STRATEGY LAB MODULAR (Check which layout is loaded):")
    print()
    if strategy_lab:
        for id_name, files in strategy_lab:
            print(f"🟠 ID: '{id_name}'")
            for filepath in sorted(files):
                rel_path = filepath.replace(str(dashboard_dir) + '/', '')
                print(f"     - {rel_path}")
            print()
    else:
        print("  None")
        print()
    
    print("=" * 80)
    print(f"📊 Summary:")
    print(f"   🚨 Critical blockers: {len(critical)}")
    print(f"   🟡 Component patterns: {len(component_pattern)}")
    print(f"   📦 Strategy Lab modular: {len(strategy_lab)}")
    print("=" * 80)
    
    return 1 if critical else 0

if __name__ == '__main__':
    exit(main())
