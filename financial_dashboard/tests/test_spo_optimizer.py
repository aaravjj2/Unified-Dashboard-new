"""
Tests for SPO Portfolio Optimizer
=================================
Unit tests for portfolio optimization methods.
"""

import pytest
import numpy as np


class TestSPOOptimizer:
    """Test SPO optimizer functionality."""
    
    def test_optimizer_initialization(self):
        """Test optimizer initializes."""
        from financial_dashboard.services.spo_optimizer import SPOOptimizer
        
        optimizer = SPOOptimizer()
        assert optimizer is not None
        assert optimizer.risk_free_rate == 0.04
    
    def test_mean_variance_optimize(self):
        """Test mean-variance optimization."""
        from financial_dashboard.services.spo_optimizer import SPOOptimizer
        
        optimizer = SPOOptimizer()
        
        # Simple 3-asset case
        returns = np.array([0.10, 0.15, 0.12])
        cov = np.array([
            [0.04, 0.01, 0.02],
            [0.01, 0.09, 0.03],
            [0.02, 0.03, 0.06]
        ])
        
        weights = optimizer.mean_variance_optimize(returns, cov, gamma=1.0)
        
        # Weights should sum to 1
        assert np.isclose(np.sum(weights), 1.0, atol=0.01)
        # All weights should be non-negative (long-only)
        assert all(w >= -0.01 for w in weights)
    
    def test_minimum_variance_portfolio(self):
        """Test minimum variance optimization."""
        from financial_dashboard.services.spo_optimizer import SPOOptimizer
        
        optimizer = SPOOptimizer()
        
        cov = np.array([
            [0.04, 0.01],
            [0.01, 0.09]
        ])
        
        weights = optimizer.minimum_variance_portfolio(cov)
        
        assert np.isclose(np.sum(weights), 1.0, atol=0.01)
        # First asset has lower variance, should have higher weight
        assert weights[0] > weights[1]
    
    def test_risk_parity_portfolio(self):
        """Test risk parity (inverse volatility) optimization."""
        from financial_dashboard.services.spo_optimizer import SPOOptimizer
        
        optimizer = SPOOptimizer()
        
        cov = np.array([
            [0.04, 0.00],
            [0.00, 0.16]
        ])
        
        weights = optimizer.risk_parity_portfolio(cov)
        
        assert np.isclose(np.sum(weights), 1.0, atol=0.01)
        # Lower vol asset should have higher weight
        assert weights[0] > weights[1]
    
    def test_portfolio_metrics(self):
        """Test portfolio metrics calculation."""
        from financial_dashboard.services.spo_optimizer import SPOOptimizer
        
        optimizer = SPOOptimizer()
        
        weights = np.array([0.5, 0.5])
        returns = np.array([0.001, 0.002])  # Daily returns
        cov = np.array([
            [0.0004, 0.0001],
            [0.0001, 0.0009]
        ])
        
        metrics = optimizer.compute_portfolio_metrics(weights, returns, cov)
        
        assert "expected_return" in metrics
        assert "volatility" in metrics
        assert "sharpe_ratio" in metrics
        assert "weights" in metrics


class TestSPOSingleton:
    """Test SPO singleton pattern."""
    
    def test_singleton(self):
        """Test get_spo_optimizer returns same instance."""
        from financial_dashboard.services.spo_optimizer import get_spo_optimizer
        
        opt1 = get_spo_optimizer()
        opt2 = get_spo_optimizer()
        
        assert opt1 is opt2


@pytest.mark.asyncio
class TestAsyncOptimization:
    """Test async portfolio optimization."""
    
    async def test_optimize_portfolio_basic(self):
        """Test full portfolio optimization with real tickers."""
        from financial_dashboard.services.spo_optimizer import optimize_portfolio
        
        result = await optimize_portfolio(
            tickers=["AAPL", "MSFT", "GOOGL"],
            method="mean_variance"
        )
        
        assert "tickers" in result
        assert "allocations" in result
        assert "metrics" in result
        assert len(result["allocations"]) == 3
    
    async def test_optimize_risk_parity(self):
        """Test risk parity optimization."""
        from financial_dashboard.services.spo_optimizer import optimize_portfolio
        
        result = await optimize_portfolio(
            tickers=["SPY", "TLT"],
            method="risk_parity"
        )
        
        assert result["method"] == "risk_parity"
        assert len(result["allocations"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
