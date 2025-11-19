#!/usr/bin/env python3
"""
Quick verification script to check if all dashboard tabs are visible
"""
import requests
import json
import re

def check_dashboard_tabs():
    """Check if all expected tabs are present in the dashboard"""
    
    expected_tabs = [
        "🏠 Command Center",
        "🔬 Research Lab", 
        "📊 Attribution Lab",
        "⚡ Strategy Lab",
        "🤖 Azure ML Lab",
        "Weekly Picks",
        "Monthly Picks", 
        "Market Trends",
        "Market Forecast",
        "⚡ Volatility Lab",
        "Portfolio",
        "💹 Options Lab"
    ]
    
    try:
        # Get the layout from the dashboard
        response = requests.get('http://localhost:8051/_dash-layout', timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Failed to get layout: HTTP {response.status_code}")
            return False
            
        layout_data = response.json()
        layout_str = json.dumps(layout_data)
        
        print("🔍 Checking for tabs in dashboard layout...")
        print(f"📊 Layout size: {len(layout_str):,} characters")
        
        found_tabs = []
        missing_tabs = []
        
        for tab_name in expected_tabs:
            if tab_name in layout_str:
                found_tabs.append(tab_name)
                print(f"✅ Found: {tab_name}")
            else:
                missing_tabs.append(tab_name)
                print(f"❌ Missing: {tab_name}")
        
        print(f"\n📈 Summary:")
        print(f"✅ Found tabs: {len(found_tabs)}/12")
        print(f"❌ Missing tabs: {len(missing_tabs)}/12")
        
        if len(found_tabs) == 12:
            print("\n🎉 SUCCESS: All 12 tabs are present in the dashboard!")
            return True
        else:
            print(f"\n⚠️  WARNING: Only {len(found_tabs)} out of 12 tabs found")
            if missing_tabs:
                print(f"Missing: {', '.join(missing_tabs)}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking dashboard: {e}")
        return False

if __name__ == "__main__":
    check_dashboard_tabs()