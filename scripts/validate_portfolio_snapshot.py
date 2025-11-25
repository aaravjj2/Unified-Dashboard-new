#!/usr/bin/env python3
"""
Quick Portfolio Snapshot Validation
Tests data loading logic without starting the full dashboard
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from financial_dashboard.tabs.home_lab.helpers import get_portfolio_summary

def main():
    print("="*60)
    print("Portfolio Snapshot Validation")
    print("="*60)
    
    print("\n📊 Loading portfolio summary...")
    portfolio = get_portfolio_summary()
    
    print(f"\n✅ Portfolio loaded successfully!")
    print(f"   Source: {portfolio.get('source', 'unknown')}")
    if 'csv_file' in portfolio:
        print(f"   CSV File: {portfolio['csv_file']}")
    print(f"   Last Updated: {portfolio.get('last_updated', 'N/A')}")
    
    print(f"\n💼 Portfolio Metrics:")
    print(f"   Total Positions: {portfolio['total_positions']}")
    print(f"   Total Value: ${portfolio['total_value']:,.2f}")
    print(f"   Daily Change: {portfolio['daily_change_pct']:.2f}%")
    
    print(f"\n📋 Top 10 Holdings:")
    print(f"{'Ticker':<10} {'Price':<12} {'Shares':<10} {'Value':<15} {'Daily %':<10}")
    print("-"*60)
    
    for pos in portfolio['positions'][:10]:
        ticker = pos.get('ticker', 'N/A')
        price = pos.get('last_price', pos.get('price', 0))
        shares = pos.get('shares', 0)
        value = pos.get('market_value', 0)
        change = pos.get('daily_change_pct', 0)
        
        print(f"{ticker:<10} ${price:<11.2f} {shares:<10} ${value:<14,.2f} {change:>7.2f}%")
    
    print("\n" + "="*60)
    
    # Validate critical fields
    errors = []
    
    if portfolio['total_positions'] == 0:
        errors.append("No positions found")
    
    if portfolio['total_value'] == 0:
        errors.append("Total value is zero")
    
    if not portfolio.get('positions'):
        errors.append("Positions list is empty")
    
    if errors:
        print("❌ VALIDATION FAILED:")
        for error in errors:
            print(f"   - {error}")
        return 1
    else:
        print("✅ VALIDATION PASSED - All checks OK")
        return 0

if __name__ == "__main__":
    sys.exit(main())
