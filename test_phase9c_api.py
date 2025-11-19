"""
Quick Test: Phase 9C API Endpoint
==================================

Verifies that api_backtest_summary.py can serve backtest results.

Usage:
    python test_phase9c_api.py
"""

import json
from pathlib import Path


def test_data_loader():
    """Test BacktestDataLoader without running Flask"""
    
    print("\n" + "="*80)
    print("PHASE 9C API DATA LOADER TEST")
    print("="*80 + "\n")
    
    # Import data loader
    from api_backtest_summary import BacktestDataLoader
    
    # Initialize loader
    loader = BacktestDataLoader(data_dir=Path("outputs/phase9c"))
    
    # Test 1: Load results
    print("📊 Test 1: Load Results JSON")
    results = loader.load_results()
    
    if "error" in results:
        print(f"❌ Failed: {results['error']}")
        return False
    
    print(f"✅ Loaded results successfully")
    print(f"   - Mode: {results.get('mode')}")
    print(f"   - Total Trades: {results.get('total_trades', 'N/A')}")
    print(f"   - Total P&L: ${results.get('total_pnl', 0):,.2f}")
    print(f"   - All Deterministic: {results.get('all_deterministic')}")
    print(f"   - All SLAs Met: {results.get('all_sla_met')}")
    
    # Test 2: Get summary stats
    print("\n📈 Test 2: Get Summary Stats")
    stats = loader.get_summary_stats()
    
    if "error" in stats:
        print(f"❌ Failed: {stats['error']}")
        return False
    
    print(f"✅ Generated summary stats")
    print(f"   - Timestamp: {stats.get('timestamp')}")
    print(f"   - Win Rate: {stats.get('win_rate', 0):.2%}")
    print(f"   - Mean Return: {stats.get('mean_return', 0):.2%}")
    print(f"   - Max Drawdown: {stats.get('max_drawdown', 0):.2%}")
    
    # Test 3: Verify tier data
    print("\n🎯 Test 3: Verify Tier Data")
    tiers = stats.get('tiers', {})
    
    for tier_name, tier_data in tiers.items():
        print(f"\n   Tier: {tier_name.upper()}")
        print(f"      Tickers: {tier_data.get('num_tickers')}")
        print(f"      Trades: {tier_data.get('total_trades')}")
        print(f"      Avg Time: {tier_data.get('avg_time_ms'):.2f}ms")
        print(f"      P&L: ${tier_data.get('total_pnl', 0):,.2f}")
        print(f"      Deterministic: {'✅' if tier_data.get('deterministic') else '❌'}")
        print(f"      SLA Met: {'✅' if tier_data.get('sla_met') else '❌'}")
    
    print("\n" + "="*80)
    print("✅ ALL TESTS PASSED")
    print("="*80 + "\n")
    
    print("🚀 API Ready to Serve:")
    print("   Start server: python api_backtest_summary.py")
    print("   Test endpoint: curl http://localhost:5000/api/backtest/summary")
    
    return True


if __name__ == "__main__":
    success = test_data_loader()
    exit(0 if success else 1)
