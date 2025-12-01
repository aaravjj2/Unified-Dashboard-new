#!/usr/bin/env python3
"""Simple check: fetch /_dash-layout and ensure results-area and results-table ids exist."""
import sys
import json
import urllib.request

URL = 'http://127.0.0.1:8050/_dash-layout'
try:
    with urllib.request.urlopen(URL, timeout=5) as r:
        j = json.load(r)
except Exception as e:
    print('ERROR: could not fetch _dash-layout:', e)
    sys.exit(2)

ids=set()

def walk(o):
    if isinstance(o, dict):
        if 'id' in o:
            ids.add(o['id'])
        for v in o.values():
            walk(v)
    elif isinstance(o, list):
        for i in o:
            walk(i)

walk(j)
miss=[]
for need in ('results-area',):
    if need not in ids:
        miss.append(need)
if miss:
    print('MISSING:', ','.join(miss))
    sys.exit(1)

# Ensure at least one of the table ids exists (server preview or client table)
if 'results-table' not in ids and 'results-table-client' not in ids:
    print('MISSING: results-table or results-table-client')
    sys.exit(1)

print('OK: results-area and results-table (server or client) present')
sys.exit(0)
