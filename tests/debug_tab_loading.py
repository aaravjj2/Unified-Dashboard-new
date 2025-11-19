#!/usr/bin/env python3
"""
Test script to directly debug tab loading in index.py
"""
import sys
import os
sys.path.insert(0, '/mnt/c/Aarav/fin_env/unified-dashboard')

# Set required env vars
os.environ['DOPPLER_TOKEN'] = 'fake'  # Just to pass validation
os.environ['ALPHA_VANTAGE_API_KEY'] = 'fake'

print("=" * 80)
print("🔬 TAB LOADING DEBUG TEST")
print("=" * 80)

# Import the modules that index.py uses
import importlib
import importlib.util

# Read the TAB_CONFIG from index.py
TAB_CONFIG = [
    {'id': 'market_trends', 'name': 'Market Trends', 'module': 'tabs/market_trends.py'},
    {'id': 'market_forecast', 'name': 'Market Forecast', 'module': 'tabs/market_forecast.py'},
    {'id': 'volatility_lab', 'name': '⚡ Volatility Lab', 'module': 'tabs/volatility_lab.py'},
    {'id': 'monthly_picks', 'name': 'Monthly Picks', 'module': 'tabs/monthly_picks.py'},
    {'id': 'weekly_picks', 'name': 'Weekly Picks', 'module': 'tabs/weekly_picks.py'},
    {'id': 'portfolio', 'name': 'Portfolio', 'module': 'tabs/portfolio_tracker_refactored.py'},
    {'id': 'options_lab', 'name': '💹 Options Lab', 'module': 'tabs/options_lab/__init__.py'},
]

APP_DIR = '/mnt/c/Aarav/fin_env/unified-dashboard/financial_dashboard'

loaded_tabs = {}
print("\n📦 Loading tabs...\n")

for tab_config in TAB_CONFIG:
    tab_id = tab_config['id']
    tab_name = tab_config['name']
    
    print(f"🔄 Loading: {tab_name} (id={tab_id})")
    
    try:
        module_path = os.path.join(APP_DIR, tab_config['module'])
        
        # Special handling for options_lab (copied from index.py)
        if tab_config['id'] == 'options_lab':
            print(f"   Using importlib.import_module for {tab_id}")
            tab_mod = importlib.import_module('financial_dashboard.tabs.options_lab')
        else:
            if not os.path.exists(module_path):
                print(f"   ❌ Module file not found: {module_path}")
                continue

            # Standard loading
            spec = importlib.util.spec_from_file_location(
                f"financial_dashboard.tabs.{tab_config['id']}", module_path
            )
            tab_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(tab_mod)

        loaded_tabs[tab_config['id']] = {
            'module': tab_mod,
            'name': tab_config['name']
        }
        
        # Check if module has layout
        if hasattr(tab_mod, 'layout'):
            layout_obj = tab_mod.layout
            is_callable = callable(layout_obj)
            print(f"   ✅ Loaded successfully - layout is {'callable' if is_callable else 'direct component'}")
        else:
            print(f"   ⚠️  Loaded but NO LAYOUT ATTRIBUTE")
            
    except Exception as e:
        print(f"   ❌ Failed to load: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("📊 SUMMARY")
print("=" * 80)
print(f"\nTotal tabs configured: {len(TAB_CONFIG)}")
print(f"Successfully loaded: {len(loaded_tabs)}")
print(f"\nLoaded tabs:")
for tab_id, tab_info in loaded_tabs.items():
    has_layout = hasattr(tab_info['module'], 'layout')
    print(f"   {'✅' if has_layout else '❌'} {tab_info['name']} (id={tab_id}) - layout: {has_layout}")

# Now check the enabled_tabs filter
enabled_tabs = ['weekly_picks', 'monthly_picks', 'market_trends', 'market_forecast', 'volatility_lab', 'portfolio', 'options_lab']

print(f"\n🎯 Enabled tabs filter: {enabled_tabs}")
print(f"\n📋 Tabs that would appear in UI:")
for tab_key in enabled_tabs:
    if tab_key in loaded_tabs:
        tab_info = loaded_tabs[tab_key]
        has_layout = hasattr(tab_info['module'], 'layout')
        print(f"   {'✅' if has_layout else '❌'} {tab_info['name']} - {tab_key}")
    else:
        print(f"   ❌ {tab_key} - NOT IN LOADED_TABS")

print("\n" + "=" * 80)
