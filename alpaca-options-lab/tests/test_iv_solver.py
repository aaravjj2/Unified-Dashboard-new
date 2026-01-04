"""
Tests for src.pricing.iv_solver - Implied Volatility Solver

Tests cover:
- Newton-Raphson IV solving
- Bisection method fallback
- Edge cases (deep ITM/OTM)
- Error handling
- Performance benchmarks
"""
from __future__ import annotations

import math
import time

import pytest
import numpy as np

from src.pricing.iv_solver import (
    IVSolver,
    solve_iv,
    solve_iv_newton_raphson,
    solve_iv_bisection,
    IVSolverError,
    IVNotFoundError,
    IVConvergenceError,
)
from src.pricing.black_scholes import black_scholes_price


class TestSolveIV:
    """Test main IV solving function."""
    
    def test_atm_call_iv(self):
        """Test IV solving for ATM call."""
        S, K, r, T = 100, 100, 0.05, 0.25
        true_iv = 0.25
        
        # Calculate market price with known IV
        market_price = black_scholes_price(S, K, r, T, true_iv, "call")
        
        # Solve for IV
        solved_iv = solve_iv(
            market_price=market_price,
            spot=S, strike=K, rate=r,
            time_to_expiry=T, option_type="call",
        )
        
        assert abs(solved_iv - true_iv) < 0.001
    
    def test_atm_put_iv(self):
        """Test IV solving for ATM put."""
        S, K, r, T = 100, 100, 0.05, 0.25
        true_iv = 0.25
        
        market_price = black_scholes_price(S, K, r, T, true_iv, "put")
        
        solved_iv = solve_iv(
            market_price=market_price,
            spot=S, strike=K, rate=r,
            time_to_expiry=T, option_type="put",
        )
        
        assert abs(solved_iv - true_iv) < 0.001
    
    def test_itm_call_iv(self):
        """Test IV solving for ITM call."""
        S, K, r, T = 110, 100, 0.05, 0.25
        true_iv = 0.30
        
        market_price = black_scholes_price(S, K, r, T, true_iv, "call")
        
        solved_iv = solve_iv(
            market_price=market_price,
            spot=S, strike=K, rate=r,
            time_to_expiry=T, option_type="call",
        )
        
        assert abs(solved_iv - true_iv) < 0.001
    
    def test_otm_call_iv(self):
        """Test IV solving for OTM call."""
        S, K, r, T = 90, 100, 0.05, 0.25
        true_iv = 0.30
        
        market_price = black_scholes_price(S, K, r, T, true_iv, "call")
        
        solved_iv = solve_iv(
            market_price=market_price,
            spot=S, strike=K, rate=r,
            time_to_expiry=T, option_type="call",
        )
        
        assert abs(solved_iv - true_iv) < 0.002
    
    def test_high_iv(self):
        """Test IV solving with high volatility."""
        S, K, r, T = 100, 100, 0.05, 0.25
        true_iv = 0.80  # 80% volatility
        
        market_price = black_scholes_price(S, K, r, T, true_iv, "call")
        
        solved_iv = solve_iv(
            market_price=market_price,
            spot=S, strike=K, rate=r,
            time_to_expiry=T, option_type="call",
        )
        
        assert abs(solved_iv - true_iv) < 0.005
    
    def test_low_iv(self):
        """Test IV solving with low volatility."""
        S, K, r, T = 100, 100, 0.05, 0.25
        true_iv = 0.10  # 10% volatility
        
        market_price = black_scholes_price(S, K, r, T, true_iv, "call")
        
        solved_iv = solve_iv(
            market_price=market_price,
            spot=S, strike=K, rate=r,
            time_to_expiry=T, option_type="call",
        )
        
        assert abs(solved_iv - true_iv) < 0.001
    
    def test_various_ivs(self):
        """Test IV solving across range of volatilities."""
        S, K, r, T = 100, 100, 0.05, 0.25
        
        for true_iv in [0.10, 0.20, 0.30, 0.50, 0.80]:
            market_price = black_scholes_price(S, K, r, T, true_iv, "call")
            
            solved_iv = solve_iv(
                market_price=market_price,
                spot=S, strike=K, rate=r,
                time_to_expiry=T, option_type="call",
            )
            
            assert abs(solved_iv - true_iv) < 0.005, f"Failed for IV={true_iv}"


class TestNewtonRaphson:
    """Test Newton-Raphson IV solver."""
    
    def test_newton_converges_atm(self):
        """Test Newton-Raphson convergence for ATM option."""
        S, K, r, T = 100, 100, 0.05, 0.25
        true_iv = 0.25
        
        market_price = black_scholes_price(S, K, r, T, true_iv, "call")
        
        solved_iv = solve_iv_newton_raphson(
            market_price=market_price,
            spot=S, strike=K, rate=r,
            time_to_expiry=T, option_type="call",
        )
        
        assert abs(solved_iv - true_iv) < 0.0001
    
    def test_newton_fast_convergence(self):
        """Test Newton-Raphson converges quickly."""
        S, K, r, T = 100, 100, 0.05, 0.25
        true_iv = 0.25
        market_price = black_scholes_price(S, K, r, T, true_iv, "call")
        
        # Newton-Raphson should converge in few iterations
        solved_iv = solve_iv_newton_raphson(
            market_price=market_price,
            spot=S, strike=K, rate=r,
            time_to_expiry=T, option_type="call",
            max_iterations=10,
        )
        
        assert abs(solved_iv - true_iv) < 0.001
    
    def test_newton_with_initial_guess(self):
        """Test Newton-Raphson with good initial guess."""
        S, K, r, T = 100, 100, 0.05, 0.25
        true_iv = 0.25
        market_price = black_scholes_price(S, K, r, T, true_iv, "call")
        
        # Good initial guess
        solved_iv = solve_iv_newton_raphson(
            market_price=market_price,
            spot=S, strike=K, rate=r,
            time_to_expiry=T, option_type="call",
            initial_guess=0.24,
        )
        
        assert abs(solved_iv - true_iv) < 0.0001


class TestBisection:
    """Test bisection IV solver."""
    
    def test_bisection_converges(self):
        """Test bisection convergence."""
        S, K, r, T = 100, 100, 0.05, 0.25
        true_iv = 0.25
        
        market_price = black_scholes_price(S, K, r, T, true_iv, "call")
        
        solved_iv = solve_iv_bisection(
            market_price=market_price,
            spot=S, strike=K, rate=r,
            time_to_expiry=T, option_type="call",
        )
        
        assert abs(solved_iv - true_iv) < 0.001
    
    def test_bisection_robust(self):
        """Test bisection handles edge cases Newton might miss."""
        S, K, r, T = 100, 120, 0.05, 0.1  # OTM, short time
        true_iv = 0.40
        
        market_price = black_scholes_price(S, K, r, T, true_iv, "call")
        
        solved_iv = solve_iv_bisection(
            market_price=market_price,
            spot=S, strike=K, rate=r,
            time_to_expiry=T, option_type="call",
        )
        
        assert abs(solved_iv - true_iv) < 0.005


class TestIVSolverClass:
    """Test IVSolver class."""
    
    @pytest.fixture
    def solver(self):
        """Create solver instance."""
        return IVSolver()
    
    def test_solve_call(self, solver):
        """Test solving call IV with class."""
        S, K, r, T = 100, 100, 0.05, 0.25
        true_iv = 0.25
        market_price = black_scholes_price(S, K, r, T, true_iv, "call")
        
        solved_iv = solver.solve(
            market_price=market_price,
            spot=S, strike=K, rate=r,
            time_to_expiry=T, option_type="call",
        )
        
        assert abs(solved_iv - true_iv) < 0.001
    
    def test_solve_put(self, solver):
        """Test solving put IV with class."""
        S, K, r, T = 100, 100, 0.05, 0.25
        true_iv = 0.25
        market_price = black_scholes_price(S, K, r, T, true_iv, "put")
        
        solved_iv = solver.solve(
            market_price=market_price,
            spot=S, strike=K, rate=r,
            time_to_expiry=T, option_type="put",
        )
        
        assert abs(solved_iv - true_iv) < 0.001
    
    def test_solve_batch(self, solver):
        """Test batch IV solving."""
        S, K, r, T = 100, 100, 0.05, 0.25
        true_ivs = [0.15, 0.20, 0.25, 0.30, 0.35]
        
        market_prices = [
            black_scholes_price(S, K, r, T, iv, "call")
            for iv in true_ivs
        ]
        
        solved_ivs = solver.solve_batch(
            market_prices=market_prices,
            spots=[S] * 5,
            strikes=[K] * 5,
            rates=[r] * 5,
            times=[T] * 5,
            option_types=["call"] * 5,
        )
        
        for solved, true in zip(solved_ivs, true_ivs):
            assert abs(solved - true) < 0.002


class TestErrorHandling:
    """Test error handling."""
    
    def test_invalid_price_raises(self):
        """Test that invalid price raises error."""
        with pytest.raises(IVSolverError):
            solve_iv(
                market_price=-1.0,  # Negative price
                spot=100, strike=100, rate=0.05,
                time_to_expiry=0.25, option_type="call",
            )
    
    def test_price_below_intrinsic_raises(self):
        """Test that price below intrinsic raises error."""
        S, K = 110, 100  # ITM call, intrinsic = 10
        
        with pytest.raises(IVSolverError):
            solve_iv(
                market_price=5.0,  # Below intrinsic of 10
                spot=S, strike=K, rate=0.05,
                time_to_expiry=0.25, option_type="call",
            )
    
    def test_zero_time_raises(self):
        """Test that zero time to expiry raises error."""
        with pytest.raises(IVSolverError):
            solve_iv(
                market_price=5.0,
                spot=100, strike=100, rate=0.05,
                time_to_expiry=0.0, option_type="call",
            )
    
    def test_convergence_failure_handled(self):
        """Test that convergence failure is handled."""
        # This should either succeed or raise appropriate error
        try:
            result = solve_iv(
                market_price=0.0001,  # Very small price
                spot=100, strike=200, rate=0.05,  # Deep OTM
                time_to_expiry=0.01, option_type="call",
            )
            # If it succeeds, IV should be high
            assert result > 0
        except IVSolverError:
            # Expected for extreme cases
            pass


class TestPerformance:
    """Test performance characteristics."""
    
    @pytest.mark.slow
    def test_batch_performance(self):
        """Test batch IV solving performance."""
        solver = IVSolver()
        
        # Generate test data
        n = 1000
        S = 100
        r, T = 0.05, 0.25
        
        strikes = np.linspace(80, 120, n)
        true_ivs = np.random.uniform(0.15, 0.35, n)
        
        market_prices = [
            black_scholes_price(S, K, r, T, iv, "call")
            for K, iv in zip(strikes, true_ivs)
        ]
        
        # Time the batch solve
        start = time.time()
        
        solved_ivs = solver.solve_batch(
            market_prices=market_prices,
            spots=[S] * n,
            strikes=list(strikes),
            rates=[r] * n,
            times=[T] * n,
            option_types=["call"] * n,
        )
        
        elapsed = time.time() - start
        
        # Should complete in reasonable time
        assert elapsed < 5.0, f"Batch IV solving took {elapsed:.2f}s for {n} options"
        
        # Check accuracy
        errors = [abs(s - t) for s, t in zip(solved_ivs, true_ivs)]
        avg_error = np.mean(errors)
        
        assert avg_error < 0.01
    
    def test_single_iv_performance(self):
        """Test single IV solve is fast."""
        S, K, r, T = 100, 100, 0.05, 0.25
        true_iv = 0.25
        market_price = black_scholes_price(S, K, r, T, true_iv, "call")
        
        # Warm up
        solve_iv(market_price, S, K, r, T, "call")
        
        # Time
        start = time.time()
        for _ in range(100):
            solve_iv(market_price, S, K, r, T, "call")
        elapsed = time.time() - start
        
        # Should be very fast
        per_call = elapsed / 100 * 1000  # ms
        assert per_call < 1.0, f"Single IV solve took {per_call:.3f}ms"


class TestSpecialCases:
    """Test special cases."""
    
    def test_near_expiry_option(self):
        """Test IV solving for near-expiry option."""
        S, K, r, T = 100, 100, 0.05, 0.01  # 2.5 trading days
        true_iv = 0.25
        
        market_price = black_scholes_price(S, K, r, T, true_iv, "call")
        
        solved_iv = solve_iv(
            market_price=market_price,
            spot=S, strike=K, rate=r,
            time_to_expiry=T, option_type="call",
        )
        
        # Near expiry, tolerance is higher
        assert abs(solved_iv - true_iv) < 0.02
    
    def test_deep_itm_call(self):
        """Test IV solving for deep ITM call."""
        S, K, r, T = 150, 100, 0.05, 0.25
        true_iv = 0.25
        
        market_price = black_scholes_price(S, K, r, T, true_iv, "call")
        
        solved_iv = solve_iv(
            market_price=market_price,
            spot=S, strike=K, rate=r,
            time_to_expiry=T, option_type="call",
        )
        
        # Deep ITM options have less vega sensitivity
        assert abs(solved_iv - true_iv) < 0.02
    
    def test_deep_otm_put(self):
        """Test IV solving for deep OTM put."""
        S, K, r, T = 150, 100, 0.05, 0.25
        true_iv = 0.30
        
        market_price = black_scholes_price(S, K, r, T, true_iv, "put")
        
        if market_price > 0.01:  # Only if there's meaningful price
            solved_iv = solve_iv(
                market_price=market_price,
                spot=S, strike=K, rate=r,
                time_to_expiry=T, option_type="put",
            )
            
            assert abs(solved_iv - true_iv) < 0.05
    
    def test_varying_moneyness(self):
        """Test IV solving across moneyness levels."""
        K, r, T = 100, 0.05, 0.25
        true_iv = 0.25
        
        spots = [80, 90, 100, 110, 120]  # Various moneyness
        
        for S in spots:
            market_price = black_scholes_price(S, K, r, T, true_iv, "call")
            
            if market_price > 0.01:  # Skip if price too small
                solved_iv = solve_iv(
                    market_price=market_price,
                    spot=S, strike=K, rate=r,
                    time_to_expiry=T, option_type="call",
                )
                
                assert abs(solved_iv - true_iv) < 0.02, f"Failed for spot={S}"
