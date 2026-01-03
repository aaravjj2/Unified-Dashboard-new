#!/usr/bin/env python3
"""
test_lob_core.py - Rigorous Verification Suite for Institutional LOB Engine

Tests the C++20 Limit Order Book for:
1. Basic Add/Cancel Operations
2. Crossed Book / Matching Logic
3. Price-Time Priority (FIFO)
4. Performance Benchmarking (>50k ops/sec target)
5. Edge Cases and Stress Tests

Run from institutional_engine directory:
    python tests/test_lob_core.py
"""

import sys
import os
import time
import json
import random
from typing import List, Tuple

# Add parent directory to path for module import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import institutional_engine as ie
except ImportError as e:
    print(f"❌ FATAL: Could not import institutional_engine: {e}")
    print("   Make sure to run build_and_test.sh first!")
    sys.exit(1)


# =============================================================================
# TEST UTILITIES
# =============================================================================

class TestResult:
    """Test result tracker"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []
    
    def record(self, name: str, passed: bool, message: str = ""):
        self.results.append((name, passed, message))
        if passed:
            self.passed += 1
            print(f"  ✅ PASSED: {name}")
        else:
            self.failed += 1
            print(f"  ❌ FAILED: {name} - {message}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY: {self.passed}/{total} passed")
        print(f"{'='*60}")
        return self.failed == 0


results = TestResult()


def assert_eq(actual, expected, name: str, tolerance: float = 1e-9):
    """Assert equality with optional floating-point tolerance"""
    if isinstance(expected, float):
        passed = abs(actual - expected) < tolerance
    else:
        passed = actual == expected
    
    if not passed:
        results.record(name, False, f"Expected {expected}, got {actual}")
    else:
        results.record(name, True)
    return passed


def assert_true(condition: bool, name: str, message: str = "Condition was False"):
    """Assert condition is true"""
    if not condition:
        results.record(name, False, message)
    else:
        results.record(name, True)
    return condition


def assert_none(value, name: str):
    """Assert value is None"""
    if value is not None:
        results.record(name, False, f"Expected None, got {value}")
    else:
        results.record(name, True)
    return value is None


# =============================================================================
# TEST 1: BASIC ADD OPERATIONS
# =============================================================================

def test_basic_add():
    """Test basic order addition and best bid/ask"""
    print("\n📊 TEST 1: Basic Add Operations")
    print("-" * 40)
    
    book = ie.OrderBook("TEST")
    
    # Add buy order @ 100.00
    order_id = book.add_order(1, 100.0, 100, True)
    assert_eq(order_id, 1, "Buy order accepted")
    
    # Add sell order @ 101.00
    order_id = book.add_order(2, 101.0, 50, False)
    assert_eq(order_id, 2, "Sell order accepted")
    
    # Verify best bid = 100.00
    best_bid = book.get_best_bid()
    assert_eq(best_bid, 100.0, "Best bid = 100.00")
    
    # Verify best ask = 101.00
    best_ask = book.get_best_ask()
    assert_eq(best_ask, 101.0, "Best ask = 101.00")
    
    # Verify spread = 1.00
    spread = book.get_spread()
    assert_eq(spread, 1.0, "Spread = 1.00")
    
    # Verify order count
    assert_eq(book.get_order_count(), 2, "Order count = 2")
    
    # Verify mid price
    mid = book.get_mid_price()
    assert_eq(mid, 100.5, "Mid price = 100.50")
    
    print(f"   Book state: {book}")


# =============================================================================
# TEST 2: CROSSED BOOK / MATCHING
# =============================================================================

def test_crossing_match():
    """Test immediate matching when order crosses the spread"""
    print("\n📊 TEST 2: Crossing/Matching Logic")
    print("-" * 40)
    
    book = ie.OrderBook("TEST")
    
    # Add sell order @ 100.00 (Qty 10)
    book.add_order(1, 100.0, 10, False)
    assert_eq(book.get_best_ask(), 100.0, "Sell @ 100 added")
    
    # Add buy order @ 101.00 (Qty 5) - THIS SHOULD MATCH IMMEDIATELY
    book.add_order(2, 101.0, 5, True)
    
    # Expected: Buy fills instantly against Sell @ 100
    # Sell remaining qty should be 5
    # Best Ask should still be 100
    
    # Check trade was executed
    trade_count = book.get_trade_count()
    assert_eq(trade_count, 1, "One trade executed")
    
    # Check traded volume
    traded_vol = book.get_traded_volume()
    assert_eq(traded_vol, 5.0, "Traded volume = 5")
    
    # Check remaining sell quantity
    best_ask_qty = book.get_best_ask_qty()
    assert_eq(best_ask_qty, 5.0, "Sell remaining qty = 5")
    
    # Best ask should still be 100.00
    best_ask = book.get_best_ask()
    assert_eq(best_ask, 100.0, "Best ask still 100.00")
    
    # No buy orders should remain (fully filled)
    best_bid = book.get_best_bid()
    assert_none(best_bid, "No remaining buy orders")
    
    # Get recent trades
    trades = book.get_recent_trades(1)
    assert_eq(len(trades), 1, "Can retrieve recent trade")
    if trades:
        trade = trades[0]
        assert_eq(trade.price, 100.0, "Trade price = 100.00 (passive)")
        assert_eq(trade.quantity, 5.0, "Trade quantity = 5")
    
    print(f"   Book state: {book}")


def test_full_fill():
    """Test full fill when aggressive order is larger"""
    print("\n📊 TEST 2b: Full Fill (aggressive > passive)")
    print("-" * 40)
    
    book = ie.OrderBook("TEST")
    
    # Add sell order @ 100.00 (Qty 5)
    book.add_order(1, 100.0, 5, False)
    
    # Add buy order @ 100.00 (Qty 10) - crosses at same price
    book.add_order(2, 100.0, 10, True)
    
    # Sell should be fully consumed, Buy should have 5 remaining
    assert_eq(book.get_trade_count(), 1, "One trade executed")
    assert_eq(book.get_traded_volume(), 5.0, "Traded volume = 5")
    
    # No more asks (sell fully consumed)
    assert_none(book.get_best_ask(), "Sell fully consumed")
    
    # Buy should have 5 remaining at 100.00
    assert_eq(book.get_best_bid(), 100.0, "Buy @ 100 remaining")
    assert_eq(book.get_best_bid_qty(), 5.0, "Buy remaining qty = 5")
    
    print(f"   Book state: {book}")


# =============================================================================
# TEST 3: QUEUE PRIORITY (FIFO)
# =============================================================================

def test_queue_priority():
    """Test Price-Time Priority (FIFO at same price level)"""
    print("\n📊 TEST 3: Queue Priority (FIFO)")
    print("-" * 40)
    
    book = ie.OrderBook("TEST")
    
    # Add two buy orders at same price
    # Order A (id=1) should have priority over Order B (id=2)
    book.add_order(1, 100.0, 10, True)  # Order A - first
    book.add_order(2, 100.0, 10, True)  # Order B - second
    
    assert_eq(book.get_best_bid_qty(), 20.0, "Total bid qty = 20")
    
    # Add sell order that partially fills
    book.add_order(3, 100.0, 5, False)  # Crosses, fills against best bid
    
    # Order A should fill first (FIFO)
    # Expected: Order A has 5 remaining, Order B has 10 remaining
    
    trades = book.get_recent_trades(1)
    assert_eq(len(trades), 1, "One trade executed")
    
    if trades:
        trade = trades[0]
        # The buy_order_id should be 1 (Order A, first in queue)
        assert_eq(trade.buy_order_id, 1, "Order A (id=1) fills first - FIFO verified")
    
    # Check remaining quantities
    # Best bid should have 15 total (5 from A + 10 from B)
    assert_eq(book.get_best_bid_qty(), 15.0, "Remaining bid qty = 15")
    
    # Add another sell to consume Order A completely
    book.add_order(4, 100.0, 5, False)
    
    trades = book.get_recent_trades(1)
    if trades:
        trade = trades[0]
        # Still Order A (finishing its remaining 5)
        assert_eq(trade.buy_order_id, 1, "Order A still being filled - FIFO correct")
    
    # Now Order A is exhausted, only Order B remains
    assert_eq(book.get_best_bid_qty(), 10.0, "Only Order B remains (qty=10)")
    
    # Final sell to verify Order B now matches
    book.add_order(5, 100.0, 3, False)
    
    trades = book.get_recent_trades(1)
    if trades:
        trade = trades[0]
        assert_eq(trade.buy_order_id, 2, "Order B (id=2) now fills - FIFO complete")
    
    print(f"   TEST PASSED: Queue Priority verified")
    print(f"   Book state: {book}")


# =============================================================================
# TEST 4: PERFORMANCE BENCHMARK
# =============================================================================

def test_performance():
    """Benchmark: Insert 100,000 orders and measure throughput"""
    print("\n📊 TEST 4: Performance Benchmark")
    print("-" * 40)
    
    book = ie.OrderBook("PERF")
    num_orders = 100_000
    
    # Pre-generate random orders for fair timing
    orders: List[Tuple[int, float, float, bool]] = []
    for i in range(num_orders):
        price = round(100.0 + random.uniform(-5.0, 5.0), 2)
        qty = random.randint(1, 100)
        is_buy = random.choice([True, False])
        orders.append((i + 1, price, qty, is_buy))
    
    # Time the insertions
    start = time.perf_counter()
    
    for order_id, price, qty, is_buy in orders:
        book.add_order(order_id, price, qty, is_buy)
    
    elapsed = time.perf_counter() - start
    
    ops_per_sec = num_orders / elapsed
    
    print(f"   Orders inserted: {num_orders:,}")
    print(f"   Time elapsed:    {elapsed:.3f} seconds")
    print(f"   Throughput:      {ops_per_sec:,.0f} ops/sec")
    print(f"   Active orders:   {book.get_order_count():,}")
    print(f"   Trades executed: {book.get_trade_count():,}")
    
    # Target: >50,000 ops/sec
    target_ops = 50_000
    assert_true(
        ops_per_sec > target_ops,
        f"Throughput > {target_ops:,} ops/sec",
        f"Only achieved {ops_per_sec:,.0f} ops/sec"
    )
    
    # Additional benchmark: cancellation
    cancel_count = min(10_000, book.get_order_count())
    if cancel_count > 0:
        start = time.perf_counter()
        cancelled = 0
        for i in range(1, cancel_count + 1):
            if book.cancel_order(i):
                cancelled += 1
        cancel_elapsed = time.perf_counter() - start
        cancel_rate = cancelled / cancel_elapsed if cancel_elapsed > 0 else 0
        print(f"   Cancel rate:     {cancel_rate:,.0f} ops/sec ({cancelled} orders)")


# =============================================================================
# TEST 5: EDGE CASES
# =============================================================================

def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n📊 TEST 5: Edge Cases")
    print("-" * 40)
    
    book = ie.OrderBook("EDGE")
    
    # Test 1: Duplicate order ID rejection
    book.add_order(1, 100.0, 10, True)
    result = book.add_order(1, 101.0, 10, True)  # Same ID
    assert_eq(result, 0, "Duplicate ID rejected")
    
    # Test 2: Invalid price rejection
    result = book.add_order(999, -10.0, 10, True)  # Negative price
    assert_eq(result, 0, "Negative price rejected")
    
    result = book.add_order(998, 0.0, 10, True)  # Zero price
    assert_eq(result, 0, "Zero price rejected")
    
    # Test 3: Cancel non-existent order
    result = book.cancel_order(99999)
    assert_eq(result, False, "Cancel non-existent order returns False")
    
    # Test 4: Empty book queries
    empty_book = ie.OrderBook("EMPTY")
    assert_none(empty_book.get_best_bid(), "Empty book has no best bid")
    assert_none(empty_book.get_best_ask(), "Empty book has no best ask")
    assert_eq(empty_book.get_spread(), -1.0, "Empty book spread = -1")
    
    # Test 5: Clear book
    book.clear()
    assert_eq(book.get_order_count(), 0, "Clear removes all orders")
    
    print(f"   Book state: {book}")


# =============================================================================
# TEST 6: SNAPSHOT AND JSON OUTPUT
# =============================================================================

def test_snapshot():
    """Test snapshot functionality and JSON output"""
    print("\n📊 TEST 6: Snapshot and JSON Output")
    print("-" * 40)
    
    book = ie.OrderBook("SPY")
    
    # Build a realistic book
    # Bids: 450.00, 449.95, 449.90, 449.85, 449.80
    for i, price in enumerate([450.00, 449.95, 449.90, 449.85, 449.80]):
        book.add_order(i + 1, price, 100 + i * 10, True)
    
    # Asks: 450.05, 450.10, 450.15, 450.20, 450.25
    for i, price in enumerate([450.05, 450.10, 450.15, 450.20, 450.25]):
        book.add_order(100 + i, price, 50 + i * 5, False)
    
    # Get snapshot
    snapshot = book.get_snapshot(5)
    
    assert_eq(snapshot.bid_levels, 5, "Snapshot has 5 bid levels")
    assert_eq(snapshot.ask_levels, 5, "Snapshot has 5 ask levels")
    
    bids = snapshot.get_bids()
    asks = snapshot.get_asks()
    
    assert_eq(bids[0].price, 450.00, "Top bid = 450.00")
    assert_eq(asks[0].price, 450.05, "Top ask = 450.05")
    
    # Get JSON
    json_str = book.get_snapshot_json(5)
    assert_true(len(json_str) > 100, "JSON output is non-trivial")
    
    # Parse and validate JSON
    try:
        data = json.loads(json_str)
        assert_eq(data["symbol"], "SPY", "JSON symbol correct")
        assert_eq(len(data["bids"]), 5, "JSON has 5 bids")
        assert_eq(len(data["asks"]), 5, "JSON has 5 asks")
        print(f"\n   📋 Book Snapshot (JSON):")
        print(json.dumps(data, indent=2))
    except json.JSONDecodeError as e:
        results.record("JSON is valid", False, str(e))


# =============================================================================
# TEST 7: MULTI-LEVEL MATCHING
# =============================================================================

def test_multi_level_matching():
    """Test matching across multiple price levels"""
    print("\n📊 TEST 7: Multi-Level Matching")
    print("-" * 40)
    
    book = ie.OrderBook("TEST")
    
    # Set up multiple ask levels
    book.add_order(1, 100.0, 10, False)  # Sell 10 @ 100
    book.add_order(2, 100.5, 10, False)  # Sell 10 @ 100.5
    book.add_order(3, 101.0, 10, False)  # Sell 10 @ 101
    
    assert_eq(book.get_total_ask_volume(), 30.0, "Total ask volume = 30")
    
    # Large buy that sweeps multiple levels
    book.add_order(10, 101.0, 25, True)  # Buy 25 @ 101 (crosses all three levels)
    
    # Expected fills:
    # - 10 @ 100.0 (level 1 fully consumed)
    # - 10 @ 100.5 (level 2 fully consumed)
    # - 5 @ 101.0 (level 3 partially filled)
    
    assert_eq(book.get_trade_count(), 3, "Three trades executed (one per level)")
    assert_eq(book.get_traded_volume(), 25.0, "Total traded volume = 25")
    
    # Remaining: 5 @ 101 ask
    assert_eq(book.get_best_ask(), 101.0, "Best ask now 101.0")
    assert_eq(book.get_best_ask_qty(), 5.0, "Remaining ask qty = 5")
    
    # No buy orders remain (fully filled)
    assert_none(book.get_best_bid(), "No remaining buy orders")
    
    print(f"   Book state: {book}")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    print("\n" + "=" * 60)
    print("🏛️  INSTITUTIONAL ENGINE - LOB VERIFICATION SUITE")
    print("=" * 60)
    print(f"Module Version: {ie.__version__}")
    print(f"Tick Size (Equity): {ie.TICK_SIZE_EQUITY}")
    print(f"Timestamp: {ie.get_timestamp_ns()} ns")
    
    # Run all tests
    test_basic_add()
    test_crossing_match()
    test_full_fill()
    test_queue_priority()
    test_performance()
    test_edge_cases()
    test_snapshot()
    test_multi_level_matching()
    
    # Print summary
    success = results.summary()
    
    if success:
        print("\n🎉 ALL TESTS PASSED - LOB Engine Verified!")
        print("   Ready for institutional-grade backtesting.\n")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED - Review output above.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())





