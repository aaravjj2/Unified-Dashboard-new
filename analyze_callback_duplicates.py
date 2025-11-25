"""
Analyze callback duplicates by parsing the JSON diagnostic report
"""
import json
import re
from collections import defaultdict

# Load the diagnostic report
with open("error_diagnostic_report.json", "r") as f:
    report = json.load(f)

console_errors = report.get("console_errors", [])

# Parse duplicate callback errors
duplicate_pattern = re.compile(r'(?:output\(s\):\s+)([a-z0-9-]+)', re.IGNORECASE)

component_duplicates = defaultdict(int)

for error in console_errors:
    text = error.get("text", "")
    if "Duplicate callback outputs" in text:
        matches = duplicate_pattern.findall(text)
        for match in matches:
            component_duplicates[match] += 1

# Sort by count
sorted_components = sorted(component_duplicates.items(), key=lambda x: x[1], reverse=True)

print("="*80)
print("DUPLICATE CALLBACK ANALYSIS")
print("="*80)
print(f"Total unique components with duplicates: {len(sorted_components)}\n")

print("Top components by duplicate count:")
for component_id, count in sorted_components[:20]:
    print(f"  {component_id}: {count} duplicates")

print(f"\nTotal errors from duplicates: {sum(component_duplicates.values())}")

# Group by tab prefix
tab_groups = defaultdict(list)
for component_id, count in sorted_components:
    prefix = component_id.split('-')[0]
    tab_groups[prefix].append((component_id, count))

print("\n" + "="*80)
print("DUPLICATES BY TAB PREFIX:")
print("="*80)
for prefix, components in sorted(tab_groups.items(), key=lambda x: sum(c[1] for c in x[1]), reverse=True):
    total = sum(c[1] for c in components)
    print(f"\n{prefix.upper()} ({total} total duplicates):")
    for comp_id, count in components[:10]:
        print(f"  - {comp_id}: {count}")
