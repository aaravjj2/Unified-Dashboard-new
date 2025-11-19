"""Test create_layout directly to see diagnostic output"""

import os
import sys

# Add paths
project_dir = '/mnt/c/Aarav/fin_env/unified-dashboard'
os.chdir(project_dir)
sys.path.insert(0, os.path.join(project_dir, 'financial_dashboard'))

print("Importing index...")
from financial_dashboard import index

print("\nCalling create_layout()...")
layout = index.create_layout()

print("\nLayout created successfully!")
print(f"Layout type: {type(layout)}")
print(f"Has children: {hasattr(layout, 'children')}")

if hasattr(layout, 'children'):
    print(f"Number of children: {len(layout.children)}")
