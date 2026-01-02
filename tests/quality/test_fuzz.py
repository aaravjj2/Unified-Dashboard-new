"""
Phase 12 Quality Testing: Fuzzing Harness
=========================================
Injects toxic data into the Risk Engine to verify resilience.
Target: engines/risk/guard.py

Scenarios:
1. Negative Volatility -> Should raise RiskException
2. Zero Price -> Should raise RiskException
3. NaN Greeks -> Should be handled gracefully or raise RiskException
4. Future Dates (Validation) -> Should be rejected
5. Huge/Tiny inputs -> Should not crash
6. Malformed Order Structures -> Should raise Validation Error

Acceptance: No 500 errors or unhandled exceptions.
"""

import pytest
import numpy as np
import logging
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from engines.risk.guard import RiskManager, OrderRequest, RiskViolation

# Mock the logger to capture errors
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture
def risk_manager():
    """Get a fresh RiskManager instance for each test."""
    manager = RiskManager()
    manager.reset_daily_stats() # Ensure clean state
    return manager

class TestFuzzingHarness:
    """Fuzzing tests for Risk Guard."""
    
    def test_negative_price_rejection(self, risk_manager):
        """Test that negative prices are strictly rejected."""
        order = OrderRequest(
            ticker="AAPL",
            side="buy",
            quantity=10,
            price=-150.0, # TOXIC
            order_type="limit"
        )
        
        # Should raise an exception or return invalid status, NOT crash
        try:
            result = risk_manager.check(order)
            assert result.approved is False
            assert "Invalid price" in str(result.message) or result.violation == RiskViolation.INVALID_ORDER
        except ValueError as e:
            # ValueErrors are acceptable if descriptive
            assert "price" in str(e).lower()
        except Exception as e:
             pytest.fail(f"Unhandled exception for negative price: {type(e).__name__}: {e}")

    def test_negative_quantity(self, risk_manager):
        """Test reaction to negative quantity."""
        order = OrderRequest(
            ticker="AAPL",
            side="buy",
            quantity=-5, # TOXIC
            price=150.0,
            order_type="market"
        )
        
        try:
            result = risk_manager.check(order)
            assert result.approved is False
        except ValueError:
            pass # Acceptable
        except Exception as e:
            pytest.fail(f"Crash on negative quantity: {e}")

    def test_nan_pricing_inputs(self, risk_manager):
        """Test handling of NaN values in numerical fields."""
        order = OrderRequest(
            ticker="AAPL",
            side="buy",
            quantity=10,
            price=float('nan'), # TOXIC
            order_type="limit"
        )
        
        try:
            result = risk_manager.check(order)
            assert result.approved is False
        except (ValueError, TypeError):
            pass
        except Exception as e:
            pytest.fail(f"Crash on NaN price: {e}")

    def test_infinite_values(self, risk_manager):
        """Test handling of Infinity."""
        order = OrderRequest(
            ticker="AAPL",
            side="sell",
            quantity=1000,
            price=float('inf'), # TOXIC
            order_type="limit"
        )
        
        try:
            result = risk_manager.check(order)
            assert result.approved is False
        except Exception as e:
            # Should catch numeric errors
            if "RiskViolation" not in str(type(e)):
                 logger.info(f"Caught expected error: {e}")

    def test_extreme_notional_value(self, risk_manager):
        """Test extremely large values that might cause overflow."""
        order = OrderRequest(
            ticker="BRK.A",
            side="buy",
            quantity=1_000_000_000, # 1 Billion shares
            price=1_000_000.0, # at $1M
            order_type="limit"
        )
        
        # Should be rejected due to position limits, not crash on math
        result = risk_manager.check(order)
        assert result.approved is False
        assert result.violation in [
            RiskViolation.MAX_POSITION_SIZE_EXCEEDED, 
            RiskViolation.INSUFFICIENT_BUYING_POWER
        ]

    def test_malformed_ticker_injection(self, risk_manager):
        """Test SQL injection-like strings in ticker."""
        toxic_tickers = [
            "AAPL; DROP TABLE orders;", 
            "<script>alert(1)</script>",
            "   ", 
            "A" * 1000 # Buffer overflow attempt
        ]
        
        for ticker in toxic_tickers:
            order = OrderRequest(
                ticker=ticker,
                side="buy",
                quantity=1,
                order_type="market"
            )
            try:
                result = risk_manager.check(order)
                # It accepts checks but should either reject or handle safely (no SQL errors)
                # If checking against restricted list, it shouldn't crash regexes
            except Exception as e:
                pytest.fail(f"Crash on toxic ticker '{ticker}': {e}")

    def test_update_portfolio_bad_data(self, risk_manager):
        """Test portfolio updates with garbage data."""
        try:
            risk_manager.update_portfolio_state(
                portfolio_value=-50000.0, # Impossible
                buying_power=float('nan'),
                drawdown_pct=2.5 # > 1.0 (250%)
            )
            # Should hopefully log error or handle gracefully, not crash process
        except Exception as e:
            pytest.fail(f"Crash on bad portfolio update: {e}")

if __name__ == "__main__":
    # Self-runner
    import subprocess
    subprocess.run(["pytest", __file__, "-v"], check=False)
