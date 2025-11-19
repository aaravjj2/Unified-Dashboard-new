#!/usr/bin/env python3
"""
Direct API test for Weekly/Monthly Picks price data
"""

import requests
import json

def test_picks_api():
    """Test the API endpoints directly"""
    
    base_url = 'http://localhost:8050'
    
    print("=" * 80)
    print("TESTING PICKS API ENDPOINTS")
    print("=" * 80)
    
    # Test Weekly Picks API
    print("\n1️⃣ Testing Weekly Picks API...")
    try:
        response = requests.get(f'{base_url}/api/weekly_picks')
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ API responded: {response.status_code}")
            print(f"   📊 Data keys: {list(data.keys())}")
            
            if 'picks' in data:
                picks = data['picks']
                print(f"   📈 Number of picks: {len(picks)}")
                if picks:
                    sample = picks[0]
                    print(f"   📊 Sample pick: {sample.get('ticker', 'N/A')}")
                    print(f"       Current Price: {sample.get('current_price', 'N/A')}")
                    print(f"       Week Start: {sample.get('week_start_price', 'N/A')}")
                    print(f"       Profit/Loss: {sample.get('profit_loss', 'N/A')}")
        else:
            print(f"   ❌ API error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test Monthly Picks API
    print("\n2️⃣ Testing Monthly Picks API...")
    try:
        response = requests.get(f'{base_url}/api/monthly_picks')
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ API responded: {response.status_code}")
            print(f"   📊 Data keys: {list(data.keys())}")
            
            if 'picks' in data:
                picks = data['picks']
                print(f"   📈 Number of picks: {len(picks)}")
                if picks:
                    sample = picks[0]
                    print(f"   📊 Sample pick: {sample.get('ticker', 'N/A')}")
                    print(f"       Current Price: {sample.get('current_price', 'N/A')}")
                    print(f"       Month Start: {sample.get('month_start_price', 'N/A')}")
                    print(f"       Profit/Loss: {sample.get('profit_loss', 'N/A')}")
        else:
            print(f"   ❌ API error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    test_picks_api()
