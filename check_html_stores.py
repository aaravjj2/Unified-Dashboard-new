#!/usr/bin/env python
"""Check if stores exist in the actual running app."""
import requests
from bs4 import BeautifulSoup

# Fetch the page
response = requests.get('http://localhost:8050')
soup = BeautifulSoup(response.text, 'html.parser')

# Find all elements with IDs containing 'store'
stores = soup.find_all(attrs={'id': lambda x: x and 'store' in x.lower()})

print(f"📦 Found {len(stores)} stores in HTML:")
for store in stores:
    print(f"  {store.get('id')}")

# Check for dcc.Store specifically
dcc_stores = soup.find_all('div', attrs={'data-dash-component': True, 'id': lambda x: x and 'store' in x.lower()})
print(f"\n🎯 dcc.Store components: {len(dcc_stores)}")
for store in dcc_stores:
    print(f"  {store.get('id')}")

# Check if hidden div exists
hidden_divs = soup.find_all('div', style=lambda x: x and 'display: none' in x.lower() if x else False)
print(f"\n👻 Hidden divs: {len(hidden_divs)}")
for div in hidden_divs[:5]:  # First 5
    children = div.find_all(True, recursive=False)  # Direct children only
    print(f"  Hidden div with {len(children)} direct children")
    for child in children[:3]:  # First 3 children
        print(f"    - {child.name} id={child.get('id', 'NO_ID')}")
