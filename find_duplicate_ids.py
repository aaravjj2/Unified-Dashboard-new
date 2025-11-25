#!/usr/bin/env python3
"""
Find all duplicate component IDs in Dash layout files
"""
import re
import sys
from pathlib import Path
from collections import defaultdict

def extract_ids_from_file(filepath):
    """Extract all id='...' and id="..." patterns from a Python file"""
    ids = []
    try:
        content = filepath.read_text()
        # Match id='xxx' or id="xxx"
        pattern = r"id\s*=\s*['\"]([^'\"]+)['\"]"
        matches = re.findall(pattern, content)
        ids = [(match, str(filepath)) for match in matches]
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
    return ids

def find_all_duplicates():
    """Scan all Python files for duplicate IDs"""
    id_locations = defaultdict(list)
    
    # Scan financial_dashboard directory
    dashboard_dir = Path("financial_dashboard")
    if dashboard_dir.exists():
        for py_file in dashboard_dir.rglob("*.py"):
            if "test" not in str(py_file) and "__pycache__" not in str(py_file):
                ids = extract_ids_from_file(py_file)
                for id_name, filepath in ids:
                    id_locations[id_name].append(filepath)
    
    # Scan index.py
    index_file = Path("index.py")
    if index_file.exists():
        ids = extract_ids_from_file(index_file)
        for id_name, filepath in ids:
            id_locations[id_name].append(filepath)
    
    # Find duplicates
    duplicates = {id_name: files for id_name, files in id_locations.items() if len(set(files)) > 1}
    
    return duplicates, id_locations

if __name__ == "__main__":
    print("=" * 80)
    print("SCANNING FOR DUPLICATE COMPONENT IDs")
    print("=" * 80)
    
    duplicates, all_ids = find_all_duplicates()
    
    if duplicates:
        print(f"\n❌ Found {len(duplicates)} DUPLICATE IDs:\n")
        for id_name, files in sorted(duplicates.items()):
            unique_files = list(set(files))
            print(f"\n🔴 ID: '{id_name}'")
            print(f"   Appears in {len(unique_files)} files:")
            for filepath in unique_files:
                count = files.count(filepath)
                print(f"     - {filepath} ({count}x)")
    else:
        print("\n✅ No duplicate IDs found!")
    
    print(f"\n📊 Total unique IDs: {len(all_ids)}")
    print("=" * 80)
    
    sys.exit(1 if duplicates else 0)
