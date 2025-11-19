#!/usr/bin/env python3
"""
Deep syntax and import validation across the entire dashboard codebase.
"""
import ast
import importlib.util
import sys
from pathlib import Path
from typing import List, Tuple, Dict

def check_syntax(filepath: Path) -> Tuple[bool, str]:
    """Check Python file for syntax errors."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        ast.parse(source, filename=str(filepath))
        return True, ""
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Parse error: {str(e)}"

def check_imports(filepath: Path) -> Tuple[bool, List[str]]:
    """Check for import issues by analyzing AST."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        
        tree = ast.parse(source, filename=str(filepath))
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        
        return True, imports
    except Exception as e:
        return False, [str(e)]

def main():
    """Run comprehensive validation."""
    base_dir = Path('.')
    
    # Directories to check
    dirs_to_check = [
        'financial_dashboard/tabs',
        'financial_dashboard/tabs/options_lab',
        'financial_dashboard/tabs/portfolio',
        'financial_dashboard/utils',
        'services',
        'ml_model',
    ]
    
    # Main files
    main_files = [
        'financial_dashboard/app.py',
        'financial_dashboard/app_refactored.py',
    ]
    
    results = {
        'syntax_ok': [],
        'syntax_errors': [],
        'import_warnings': []
    }
    
    print("🔍 COMPREHENSIVE SYNTAX & IMPORT VALIDATION")
    print("=" * 70)
    
    # Check main files
    print("\n📄 Main Application Files:")
    for filepath in main_files:
        path = Path(filepath)
        if not path.exists():
            print(f"  ⚠️  {filepath} (not found)")
            continue
            
        is_valid, error = check_syntax(path)
        if is_valid:
            print(f"  ✅ {filepath}")
            results['syntax_ok'].append(str(path))
        else:
            print(f"  ❌ {filepath}: {error}")
            results['syntax_errors'].append((str(path), error))
    
    # Check directories
    for directory in dirs_to_check:
        dir_path = Path(directory)
        if not dir_path.exists():
            continue
            
        print(f"\n📂 {directory}:")
        
        py_files = sorted(dir_path.glob('**/*.py'))
        for py_file in py_files:
            # Skip backups and temp files
            if any(x in py_file.name for x in ['BACKUP', 'OLD', 'CORRUPTED', 'TEMP', '__pycache__']):
                continue
            
            # Syntax check
            is_valid, error = check_syntax(py_file)
            relative_path = py_file.relative_to(base_dir)
            
            if is_valid:
                print(f"  ✅ {relative_path}")
                results['syntax_ok'].append(str(relative_path))
                
                # Import check
                has_imports, imports = check_imports(py_file)
                if has_imports and imports:
                    # Check for common problematic imports
                    problematic = [imp for imp in imports if 'CORRUPTED' in imp or 'BACKUP' in imp]
                    if problematic:
                        print(f"    ⚠️  Imports backup files: {problematic}")
                        results['import_warnings'].append((str(relative_path), problematic))
            else:
                print(f"  ❌ {relative_path}: {error}")
                results['syntax_errors'].append((str(relative_path), error))
    
    # Summary
    print(f"\n{'=' * 70}")
    print("📊 VALIDATION SUMMARY")
    print(f"{'=' * 70}")
    print(f"✅ Files with valid syntax: {len(results['syntax_ok'])}")
    print(f"❌ Files with syntax errors: {len(results['syntax_errors'])}")
    print(f"⚠️  Files with import warnings: {len(results['import_warnings'])}")
    
    if results['syntax_errors']:
        print(f"\n🚨 SYNTAX ERRORS FOUND:")
        for filepath, error in results['syntax_errors']:
            print(f"\n  File: {filepath}")
            print(f"  Error: {error}")
        sys.exit(1)
    
    if results['import_warnings']:
        print(f"\n⚠️  IMPORT WARNINGS:")
        for filepath, warnings in results['import_warnings']:
            print(f"\n  File: {filepath}")
            print(f"  Issues: {warnings}")
    
    print(f"\n✅ All {len(results['syntax_ok'])} files have valid Python syntax!")
    sys.exit(0)

if __name__ == '__main__':
    main()
