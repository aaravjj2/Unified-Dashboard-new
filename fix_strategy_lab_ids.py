#!/usr/bin/env python3
"""
Direct file fixer for Strategy Lab component IDs
Bypasses caching issues by reading/writing files directly
"""
import os

fixes = [
    {
        'file': 'financial_dashboard/tabs/strategy_lab/subtabs/setup.py',
        'replacements': [
            ("html.Div(id='sl-validation-feedback'", "html.Div(id='sl-validation-result'"),
        ]
    },
]

for fix in fixes:
    filepath = fix['file']
    print(f"\n📝 Processing: {filepath}")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    changes_made = []
    
    for old, new in fix['replacements']:
        if old in content:
            content = content.replace(old, new)
            changes_made.append(f"  ✅ {old[:50]} → {new[:50]}")
        else:
            print(f"  ⚠️  NOT FOUND: {old[:80]}")
    
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"  💾 Saved {len(changes_made)} changes:")
        for change in changes_made:
            print(change)
        os.sync()  # Force filesystem sync
    else:
        print(f"  ℹ️  No changes needed")

print("\n✅ All fixes applied!")
