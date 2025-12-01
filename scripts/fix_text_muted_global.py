#!/usr/bin/env python3
"""
Global Text Color Fix Script

Systematically replaces all `text-muted` Bootstrap classes with explicit black text styling.
Prevents white-on-white text visibility issues across the entire dashboard.

Author: Autonomous Lead Engineer (Agent v2)
Date: October 28, 2025
"""

import re
import os
from pathlib import Path

# Files to fix (excluding backup files)
TARGET_FILES = [
    'financial_dashboard/tabs/home_lab/layout.py',
    'financial_dashboard/tabs/attribution_lab/layout.py',
    'financial_dashboard/tabs/strategy_lab/layout.py',
    'financial_dashboard/tabs/options_lab/layout.py',
    'financial_dashboard/tabs/research_lab/layout.py',
    # Standalone tab files
    'financial_dashboard/tabs/volatility_lab.py',
    'financial_dashboard/tabs/market_forecast.py',
    'financial_dashboard/tabs/portfolio_tab.py',
]

def fix_text_muted_in_file(file_path):
    """
    Replace text-muted classes with explicit black text styling.
    
    Patterns Fixed:
    1. className="text-muted" → className="", style={'color': '#000000'}
    2. className="text-muted mb-1" → className="mb-1", style={'color': '#000000'}
    3. className="small text-muted" → className="small", style={'color': '#000000'}
    """
    
    if not os.path.exists(file_path):
        print(f"⚠️  SKIP: {file_path} not found")
        return 0
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    fixes_applied = 0
    
    # Pattern 1: text-muted with other classes
    # Example: className="text-muted mb-1" → className="mb-1", style={'color': '#000000'}
    pattern1 = r'className="([^"]*)\btext-muted\b([^"]*)"(?!\s*,\s*style=)'
    
    def replace_with_style(match):
        nonlocal fixes_applied
        classes = match.group(1) + match.group(2)
        # Remove text-muted and extra spaces
        classes = re.sub(r'\btext-muted\b', '', classes).strip()
        
        if classes:
            # Other classes exist, keep className
            replacement = f'className="{classes}", style={{\'color\': \'#000000\'}}'
        else:
            # Only text-muted, remove className entirely
            replacement = 'style={\'color\': \'#000000\'}'
        
        fixes_applied += 1
        return replacement
    
    content = re.sub(pattern1, replace_with_style, content)
    
    # Pattern 2: Already has style but no color (unlikely but check)
    # Example: className="text-muted", style={'fontSize': '14px'} → add color
    pattern2 = r'className="([^"]*)\btext-muted\b([^"]*)",\s*style=\{([^}]+)\}'
    
    def add_color_to_style(match):
        nonlocal fixes_applied
        classes = match.group(1) + match.group(2)
        classes = re.sub(r'\btext-muted\b', '', classes).strip()
        style_content = match.group(3)
        
        # Add color to existing style
        if 'color' not in style_content:
            style_content = f"'color': '#000000', {style_content}"
        
        if classes:
            replacement = f'className="{classes}", style={{{style_content}}}'
        else:
            replacement = f'style={{{style_content}}}'
        
        fixes_applied += 1
        return replacement
    
    content = re.sub(pattern2, add_color_to_style, content)
    
    # Write back only if changes were made
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"✅ FIXED: {file_path} ({fixes_applied} replacements)")
        return fixes_applied
    else:
        print(f"✓  OK: {file_path} (no text-muted found)")
        return 0

def main():
    print("=" * 70)
    print("GLOBAL TEXT COLOR FIX - Starting...")
    print("=" * 70)
    print()
    
    total_fixes = 0
    files_modified = 0
    
    # Get workspace root (script is in scripts/)
    workspace_root = Path(__file__).parent.parent
    os.chdir(workspace_root)
    
    for file_path in TARGET_FILES:
        fixes = fix_text_muted_in_file(file_path)
        if fixes > 0:
            total_fixes += fixes
            files_modified += 1
        print()
    
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Files Modified: {files_modified}/{len(TARGET_FILES)}")
    print(f"Total Replacements: {total_fixes}")
    print()
    
    if files_modified > 0:
        print("🔄 NEXT STEP: Restart dashboard to apply changes")
        print("   docker-compose restart dash_app")
    else:
        print("✅ All files already have proper text styling!")
    
    print()

if __name__ == '__main__':
    main()
