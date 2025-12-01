#!/usr/bin/env python3
"""
Test script to inspect Flask routing and blueprint registration.
This will help us understand why Dash is intercepting Flask blueprint routes.
"""
import sys
import os

# Add financial_dashboard to path
sys.path.insert(0, '/home/aarav/unified-dashboard')

# Import the create_app factory
from financial_dashboard.app import create_app

# Create the app
print("Creating app...")
app = create_app()

# Get the Flask server
server = app.server

# Print all registered routes
print("\n" + "="*70)
print("FLASK ROUTES REGISTERED:")
print("="*70)

for rule in server.url_map.iter_rules():
    methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
    print(f"{rule.endpoint:50s} {methods:20s} {rule.rule}")

print("\n" + "="*70)
print(f"Total routes: {len(list(server.url_map.iter_rules()))}")
print("="*70)

# Check if volsurface routes are registered
volsurface_routes = [r for r in server.url_map.iter_rules() if 'volsurface' in r.rule]
print(f"\nVolsurface routes found: {len(volsurface_routes)}")
for route in volsurface_routes:
    methods = ','.join(sorted(route.methods - {'HEAD', 'OPTIONS'}))
    print(f"  {methods:20s} {route.rule}")

# Check Dash routes
dash_routes = [r for r in server.url_map.iter_rules() if '_dash' in r.rule or r.rule == '/']
print(f"\nDash routes found: {len(dash_routes)}")
for route in dash_routes[:10]:  # Show first 10
    methods = ','.join(sorted(route.methods - {'HEAD', 'OPTIONS'}))
    print(f"  {methods:20s} {route.rule}")
