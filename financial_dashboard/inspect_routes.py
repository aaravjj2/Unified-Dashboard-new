#!/usr/bin/env python
"""Quick test to verify Flask routes are registered"""
import sys
sys.path.insert(0, '/mnt/c/Aarav/fin_env/unified-dashboard/financial_dashboard')

from app import app, server

print("="*70)
print("FLASK ROUTE INSPECTION")
print("="*70)
print(f"\nApp type: {type(app)}")
print(f"Server type: {type(server)}")
print(f"\nRegistered routes:")
for rule in server.url_map.iter_rules():
    print(f"  {rule.rule} -> {rule.endpoint}")

print(f"\nTotal routes: {len(list(server.url_map.iter_rules()))}")
