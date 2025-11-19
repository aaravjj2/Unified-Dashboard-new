#!/usr/bin/env python3
"""
Diagnostic script to check all portfolio data sources.
Helps identify why Portfolio Positions tab may not be loading.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add financial_dashboard to path
sys.path.insert(0, '/app/financial_dashboard')

def check_alpaca_connection():
    """Check if Alpaca API is accessible and has positions."""
    print("=" * 80)
    print("1. ALPACA API CHECK")
    print("=" * 80)
    
    key = os.getenv('APCA_API_KEY_ID') or os.getenv('APCA_API_KEY')
    secret = os.getenv('APCA_API_SECRET_KEY') or os.getenv('APCA_API_SECRET')
    
    print(f"✓ Credentials exist: {'Yes' if (key and secret) else 'No'}")
    
    if not (key and secret):
        print("❌ No Alpaca credentials found")
        return None
    
    try:
        from alpaca.trading.client import TradingClient
        client = TradingClient(key, secret, paper=True)
        account = client.get_account()
        positions = client.get_all_positions()
        
        portfolio_value = float(account.portfolio_value)
        equity = float(account.equity)
        cash = float(account.cash)
        
        print(f"✓ Connection: SUCCESS")
        print(f"✓ Portfolio Value: ${portfolio_value:,.2f}")
        print(f"✓ Equity: ${equity:,.2f}")
        print(f"✓ Cash: ${cash:,.2f}")
        print(f"✓ Positions Count: {len(positions)}")
        
        if positions:
            print(f"\n📊 Sample Positions (first 10):")
            for i, pos in enumerate(positions[:10], 1):
                print(f"  {i}. {pos.symbol}: {float(pos.qty):.6f} shares @ ${float(pos.current_price):.2f}")
        
        # Build positions data structure
        positions_data = []
        for pos in positions:
            positions_data.append({
                'symbol': pos.symbol,
                'qty': float(pos.qty),
                'avg_entry_price': float(pos.avg_entry_price),
                'current_price': float(pos.current_price),
                'cost_basis': float(pos.cost_basis),
                'market_value': float(pos.market_value),
                'unrealized_pl': float(pos.market_value) - float(pos.cost_basis),
                'unrealized_plpc': float(pos.unrealized_plpc) * 100
            })
        
        return {
            'positions': positions_data,
            'account': {
                'portfolio_value': portfolio_value,
                'equity': equity,
                'cash': cash
            },
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        print(f"❌ Alpaca API Error: {e}")
        return None


def check_portfolio_cache():
    """Check portfolio cache file."""
    print("\n" + "=" * 80)
    print("2. PORTFOLIO CACHE CHECK")
    print("=" * 80)
    
    cache_path = Path('/app/financial_dashboard/.cache/portfolio_cache.json')
    
    if not cache_path.exists():
        print(f"❌ Cache file not found: {cache_path}")
        return None
    
    try:
        with open(cache_path, 'r') as f:
            cache_data = json.load(f)
        
        timestamp = cache_data.get('timestamp', 'Unknown')
        positions = cache_data.get('data', {}).get('positions', [])
        
        print(f"✓ Cache file exists: {cache_path}")
        print(f"✓ Last updated: {timestamp}")
        print(f"✓ Positions count: {len(positions)}")
        
        if positions:
            print(f"\n📊 Sample Cached Positions (first 10):")
            for i, pos in enumerate(positions[:10], 1):
                print(f"  {i}. {pos.get('symbol', 'N/A')}: {pos.get('qty', 0)} shares")
        
        return cache_data.get('data')
    
    except Exception as e:
        print(f"❌ Error reading cache: {e}")
        return None


def check_attribution_files():
    """Check attribution JSON files."""
    print("\n" + "=" * 80)
    print("3. ATTRIBUTION FILES CHECK")
    print("=" * 80)
    
    attribution_dir = Path('/app/financial_dashboard/attribution')
    
    if not attribution_dir.exists():
        print(f"❌ Attribution directory not found: {attribution_dir}")
        return None
    
    # Check for latest_portfolio.json
    latest_portfolio_path = attribution_dir / 'latest_portfolio.json'
    
    if not latest_portfolio_path.exists():
        print(f"❌ latest_portfolio.json not found")
        
        # List other portfolio files
        portfolio_files = list(attribution_dir.glob('*portfolio*.json'))
        if portfolio_files:
            print(f"\n📁 Found {len(portfolio_files)} other portfolio files:")
            for f in sorted(portfolio_files)[-5:]:
                print(f"  - {f.name}")
        
        return None
    
    try:
        with open(latest_portfolio_path, 'r') as f:
            portfolio_data = json.load(f)
        
        positions = portfolio_data.get('positions', [])
        
        print(f"✓ latest_portfolio.json exists")
        print(f"✓ Positions count: {len(positions)}")
        
        if positions:
            print(f"\n📊 Sample Attribution Positions (first 10):")
            for i, pos in enumerate(positions[:10], 1):
                ticker = pos.get('ticker') or pos.get('symbol', 'N/A')
                shares = pos.get('shares') or pos.get('qty', 0)
                print(f"  {i}. {ticker}: {shares} shares")
        
        return portfolio_data
    
    except Exception as e:
        print(f"❌ Error reading attribution file: {e}")
        return None


def check_db_snapshot():
    """Check database snapshot."""
    print("\n" + "=" * 80)
    print("4. DATABASE SNAPSHOT CHECK")
    print("=" * 80)
    
    try:
        from utils import db_utils
        
        # Check if DB is initialized
        db_path = Path('/app/financial_dashboard/data/portfolio.db')
        
        if not db_path.exists():
            print(f"❌ Database not found: {db_path}")
            return None
        
        print(f"✓ Database exists: {db_path}")
        print(f"✓ Size: {db_path.stat().st_size / 1024:.2f} KB")
        
        # Try to fetch latest snapshot
        # (db_utils may not have this function, this is a placeholder)
        print("\n💡 Database exists but query methods not implemented in this script")
        
        return None
    
    except ImportError:
        print("❌ db_utils module not available")
        return None
    except Exception as e:
        print(f"❌ Database error: {e}")
        return None


def main():
    """Run all diagnostic checks."""
    print("\n" + "=" * 80)
    print("PORTFOLIO DATA DIAGNOSTIC TOOL")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)
    
    # Run all checks
    alpaca_data = check_alpaca_connection()
    cache_data = check_portfolio_cache()
    attribution_data = check_attribution_files()
    db_data = check_db_snapshot()
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    sources_available = []
    if alpaca_data:
        sources_available.append("Alpaca API")
    if cache_data:
        sources_available.append("Cache File")
    if attribution_data:
        sources_available.append("Attribution File")
    if db_data:
        sources_available.append("Database")
    
    if sources_available:
        print(f"✓ Available data sources: {', '.join(sources_available)}")
        print(f"\n🎯 RECOMMENDATION: Portfolio data is available from {len(sources_available)} source(s)")
        print("   Dashboard should be able to load positions.")
        
        # Check position counts match
        if alpaca_data and cache_data:
            alpaca_count = len(alpaca_data.get('positions', []))
            cache_count = len(cache_data.get('positions', []))
            
            if alpaca_count != cache_count:
                print(f"\n⚠️  WARNING: Position count mismatch!")
                print(f"   Alpaca: {alpaca_count} positions")
                print(f"   Cache: {cache_count} positions")
                print(f"   Cache may be stale - recommend refresh")
    else:
        print("❌ NO DATA SOURCES AVAILABLE")
        print("   Portfolio tab will not be able to load positions.")
        print("\n🔧 TROUBLESHOOTING STEPS:")
        print("   1. Check Alpaca API credentials in environment")
        print("   2. Ensure Alpaca SDK is installed (alpaca-py)")
        print("   3. Check if portfolio has positions in Alpaca account")
        print("   4. Run manual refresh in dashboard")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()
