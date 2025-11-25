#!/usr/bin/env python3
"""
Find all duplicate Output() registrations across all tab files.
"""

import os
import re
from collections import defaultdict

def find_duplicate_outputs(root_dir):
    """Find all Python files with duplicate Output() registrations."""
    
    # Map of output_id -> list of (file, line, callback_name)
    outputs = defaultdict(list)
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip backup and cache directories
        if '.bak' in dirpath or '__pycache__' in dirpath or '.git' in dirpath:
            continue
            
        for filename in filenames:
            if not filename.endswith('.py') or filename.endswith('.bak'):
                continue
                
            filepath = os.path.join(dirpath, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                current_callback = None
                for i, line in enumerate(lines, 1):
                    # Detect callback function definition
                    if 'def ' in line and '(' in line:
                        match = re.search(r'def\s+(\w+)\s*\(', line)
                        if match:
                            current_callback = match.group(1)
                    
                    # Find Output() statements
                    output_match = re.search(r"Output\s*\(\s*['\"]([^'\"]+)['\"]", line)
                    if output_match:
                        output_id = output_match.group(1)
                        outputs[output_id].append((filepath, i, current_callback or 'unknown'))
                        
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
    
    # Find duplicates
    duplicates = {k: v for k, v in outputs.items() if len(v) > 1}
    
    return duplicates

if __name__ == '__main__':
    root = '/home/aarav/unified-dashboard/financial_dashboard/tabs'
    
    duplicates = find_duplicate_outputs(root)
    
    print(f"\n🔍 DUPLICATE OUTPUT ANALYSIS")
    print("=" * 80)
    print(f"Found {len(duplicates)} output IDs with duplicate registrations\n")
    
    # Group by file
    by_file = defaultdict(list)
    for output_id, locations in duplicates.items():
        for filepath, line, callback in locations:
            by_file[filepath].append((output_id, line, callback))
    
    for filepath in sorted(by_file.keys()):
        rel_path = filepath.replace('/home/aarav/unified-dashboard/', '')
        print(f"\n📄 {rel_path}")
        print("-" * 80)
        
        # Group by output_id for this file
        file_outputs = defaultdict(list)
        for output_id, line, callback in by_file[filepath]:
            file_outputs[output_id].append((line, callback))
        
        for output_id, lines in sorted(file_outputs.items()):
            print(f"  {output_id}:")
            for line, callback in lines:
                print(f"    Line {line:4d}: {callback}()")
