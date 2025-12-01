#!/usr/bin/env python3
"""Debug action pattern matching"""
import re

query = "Buy 100 shares of AAPL"
query_lower = query.lower()

patterns = [
    r"(?:create|place|submit|buy|sell).{0,30}(?:order|trade|position)",
    r"(?:buy|sell)\s+\d+\s+(?:shares?\s+(?:of\s+)?)?[A-Z]{1,5}",
    r"paper\s+(?:order|trade)",
]

print(f"Testing query: '{query}'")
print(f"Lowercase: '{query_lower}'")
print()

for i, pattern in enumerate(patterns, 1):
    print(f"Pattern {i}: {pattern}")
    match = re.search(pattern, query_lower)
    if match:
        print(f"  ✅ MATCH: {match.group()}")
    else:
        print(f"  ❌ No match")
    print()

# Now test with original case
print("Testing with ORIGINAL CASE:")
for i, pattern in enumerate(patterns, 1):
    print(f"Pattern {i}: {pattern}")
    match = re.search(pattern, query)  # Original case
    if match:
        print(f"  ✅ MATCH: {match.group()}")
    else:
        print(f"  ❌ No match")
