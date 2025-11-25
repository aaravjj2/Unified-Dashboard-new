#!/usr/bin/env python3
"""
Comprehensive syntax checker for all Python files in the dashboard.
"""
import os
import ast
import sys
from pathlib import Path

def check_syntax(filepath):
    """Check Python file for syntax errors."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Try to parse the AST
        ast.parse(source, filename=str(filepath))
        return True, None
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    """Check all Python files in tabs directory."""
    tabs_dir = Path('financial_dashboard/tabs')
    
    errors = []
    success = []
    
    # Get all .py files
    for py_file in sorted(tabs_dir.glob('*.py')):
        # Skip backup files
        if 'BACKUP' in py_file.name or 'OLD' in py_file.name or 'CORRUPTED' in py_file.name:
            continue
            
        is_valid, error = check_syntax(py_file)
        
        if is_valid:
            success.append(py_file.name)
            print(f"✅ {py_file.name}")
        else:
            errors.append((py_file.name, error))
            print(f"❌ {py_file.name}: {error}")
    
    # Summary
    print(f"\n{'='*70}")
    print(f"SUMMARY: {len(success)} OK, {len(errors)} ERRORS")
    print(f"{'='*70}")
    
    if errors:
        print("\n🚨 FILES WITH SYNTAX ERRORS:")
        for filename, error in errors:
            print(f"  • {filename}")
            print(f"    {error}")
        sys.exit(1)
    else:
        print("\n✅ All tab files have valid syntax!")
        sys.exit(0)

if __name__ == '__main__':
    main()
