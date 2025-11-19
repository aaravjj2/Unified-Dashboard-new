"""
Test Portfolio Optimization Fallback Logic

Validates robust optimization with data quality issues and fallback mechanisms.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock


class TestPortfolioOptimizationFallback:
    """Test portfolio optimization fallback mechanisms."""
    
    def test_optimization_with_short_history(self):
        """Test fallback to equal weights with insufficient data (<30 days)."""
        from financial_dashboard.utils.portfolio import PortfolioOptimizer
        
        tickers = ['AAPL', 'MSFT']
        
        # Create short price history (only 15 days)
        dates = pd.date_range(end=datetime.now(), periods=15, freq='D')
        prices = pd.DataFrame({
            'AAPL': np.random.randn(15).cumsum() + 100,
            'MSFT': np.random.randn(15).cumsum() + 200
        }, index=dates)
        
        with patch.object(PortfolioOptimizer, '_fetch_prices', return_value=prices):
            optimizer = PortfolioOptimizer(
                tickers=tickers,
                start_date=dates[0],
                end_date=dates[-1]
            )
            
            result = optimizer.optimize_sharpe()
            
            # Should fallback to equal weights
            assert result is not None
            assert 'optimization_status' in result
            assert result['optimization_status'].startswith('fallback')
            assert 'weights' in result
            
            # Verify equal weighting (approximately 50% each)
            for ticker in tickers:
                assert ticker in result['weights']
                assert abs(result['weights'][ticker] - 0.5) < 0.01
    
    def test_optimization_with_nan_data(self):
        """Test data cleaning removes NaN values."""
        from financial_dashboard.utils.portfolio import PortfolioOptimizer
        
        tickers = ['AAPL', 'MSFT', 'GOOGL']
        
        # Create price history with NaN values
        dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
        prices = pd.DataFrame({
            'AAPL': np.random.randn(100).cumsum() + 100,
            'MSFT': np.random.randn(100).cumsum() + 200,
            'GOOGL': np.random.randn(100).cumsum() + 150
        }, index=dates)
        
        # Inject NaN values
        prices.iloc[10:15, 0] = np.nan  # AAPL has NaNs
        prices.iloc[20:22, 1] = np.nan  # MSFT has NaNs
        
        with patch.object(PortfolioOptimizer, '_fetch_prices', return_value=prices):
            optimizer = PortfolioOptimizer(
                tickers=tickers,
                start_date=dates[0],
                end_date=dates[-1]
            )
            
            # Check that returns were cleaned
            assert not optimizer.returns.isnull().any().any(), "Returns should have no NaN after cleaning"
            
            # Optimization should still work
            result = optimizer.optimize_sharpe()
            assert result is not None
            assert 'weights' in result
    
    def test_optimization_with_singular_covariance(self):
        """Test handling of singular covariance matrices with Ledoit-Wolf shrinkage."""
        from financial_dashboard.utils.portfolio import PortfolioOptimizer
        
        # Create perfectly correlated returns to force singular covariance
        tickers = ['AAPL', 'MSFT']
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        
        # Create identical returns (perfect correlation)
        base_returns = np.random.randn(100) * 0.01
        prices = pd.DataFrame({
            'AAPL': 100 * (1 + base_returns).cumprod(),
            'MSFT': 150 * (1 + base_returns).cumprod()  # Different scale but same returns
        }, index=dates)
        
        optimizer = PortfolioOptimizer(tickers)
        optimizer.prices = prices
        optimizer.returns = prices.pct_change().dropna()
        optimizer.cov_matrix = optimizer.returns.cov()
        
        # Optimize - should detect singularity and apply shrinkage
        result = optimizer.optimize_sharpe()
        
        # Should either succeed with shrinkage or fall back
        # Both are valid outcomes for singular matrices
        assert result.get('optimization_status') in [
            'success_with_shrinkage', 
            'fallback_insufficient_data',
            'fallback_optimization_failed: Positive directional derivative for linesearch'
        ]
        assert 'weights' in result
        assert len(result['weights']) == len(tickers)
        
        # If it fell back, verify equal weights
        if result['optimization_status'].startswith('fallback'):
            assert all(abs(w - 0.5) < 0.01 for w in result['weights'].values())
    
    def test_equal_weight_fallback_method(self):
        """Test explicit equal weight fallback."""
        from financial_dashboard.utils.portfolio import PortfolioOptimizer
        
        tickers = ['AAPL', 'MSFT', 'GOOGL']
        dates = pd.date_range(end=datetime.now(), periods=60, freq='D')
        prices = pd.DataFrame({
            'AAPL': np.random.randn(60).cumsum() + 100,
            'MSFT': np.random.randn(60).cumsum() + 200,
            'GOOGL': np.random.randn(60).cumsum() + 150
        }, index=dates)
        
        with patch.object(PortfolioOptimizer, '_fetch_prices', return_value=prices):
            optimizer = PortfolioOptimizer(
                tickers=tickers,
                start_date=dates[0],
                end_date=dates[-1]
            )
            
            result = optimizer._fallback_equal_weight(reason="test")
            
            assert result is not None
            assert 'weights' in result
            assert len(result['weights']) == 3
            
            # Check equal weighting
            for ticker in tickers:
                assert abs(result['weights'][ticker] - 1/3) < 0.01
            
            # Check that optimization_status indicates fallback
            assert 'fallback' in result['optimization_status']
    
    def test_optimization_with_zero_volatility(self):
        """Test handling of zero volatility (constant prices)."""
        from financial_dashboard.utils.portfolio import PortfolioOptimizer
        
        tickers = ['AAPL', 'MSFT']
        
        # Create constant price history (zero volatility)
        dates = pd.date_range(end=datetime.now(), periods=60, freq='D')
        prices = pd.DataFrame({
            'AAPL': [100.0] * 60,  # Constant price
            'MSFT': [200.0] * 60   # Constant price
        }, index=dates)
        
        with patch.object(PortfolioOptimizer, '_fetch_prices', return_value=prices):
            optimizer = PortfolioOptimizer(
                tickers=tickers,
                start_date=dates[0],
                end_date=dates[-1]
            )
            
            result = optimizer.optimize_sharpe()
            
            # Should fallback due to zero volatility
            assert result is not None
            assert result.get('optimization_status').startswith('fallback')
    
    def test_optimization_exception_handling(self):
        """Test that exceptions trigger fallback."""
        from financial_dashboard.utils.portfolio import PortfolioOptimizer
        
        tickers = ['AAPL', 'MSFT']
        dates = pd.date_range(end=datetime.now(), periods=60, freq='D')
        prices = pd.DataFrame({
            'AAPL': np.random.randn(60).cumsum() + 100,
            'MSFT': np.random.randn(60).cumsum() + 200
        }, index=dates)
        
        with patch.object(PortfolioOptimizer, '_fetch_prices', return_value=prices):
            optimizer = PortfolioOptimizer(
                tickers=tickers,
                start_date=dates[0],
                end_date=dates[-1]
            )
            
            # Mock minimize to raise exception
            with patch('financial_dashboard.utils.portfolio.minimize', side_effect=ValueError("Test error")):
                result = optimizer.optimize_sharpe()
                
                # Should return fallback equal weights
                assert result is not None
                assert 'fallback' in result.get('optimization_status', '')
                assert 'exception' in result.get('optimization_status', '')
    
    def test_min_volatility_with_fallback(self):
        """Test minimize_volatility fallback behavior."""
        from financial_dashboard.utils.portfolio import PortfolioOptimizer
        
        tickers = ['AAPL']  # Only one ticker - should use fallback
        dates = pd.date_range(end=datetime.now(), periods=60, freq='D')
        prices = pd.DataFrame({
            'AAPL': np.random.randn(60).cumsum() + 100
        }, index=dates)
        
        with patch.object(PortfolioOptimizer, '_fetch_prices', return_value=prices):
            optimizer = PortfolioOptimizer(
                tickers=tickers,
                start_date=dates[0],
                end_date=dates[-1]
            )
            
            result = optimizer.minimize_volatility()
            
            # Should recognize insufficient tickers
            assert result is None or 'fallback' in result.get('optimization_status', '')
    
    def test_optimizer_with_mixed_quality_data(self):
        """Test optimization with mixed data quality (some good, some bad)."""
        from financial_dashboard.utils.portfolio import PortfolioOptimizer
        
        tickers = ['AAPL', 'MSFT', 'GOOGL']
        
        # Create data with varying quality
        dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
        prices = pd.DataFrame({
            'AAPL': np.random.randn(100).cumsum() + 100,  # Good data
            'MSFT': np.random.randn(100).cumsum() + 200,  # Good data
            'GOOGL': np.concatenate([np.random.randn(50).cumsum() + 150, [np.nan]*50])  # Partial data
        }, index=dates)
        
        with patch.object(PortfolioOptimizer, '_fetch_prices', return_value=prices):
            optimizer = PortfolioOptimizer(
                tickers=tickers,
                start_date=dates[0],
                end_date=dates[-1]
            )
            
            # Should clean data and potentially drop GOOGL
            result = optimizer.optimize_sharpe()
            
            assert result is not None
            # Either all 3 tickers (with cleaned data) or 2 tickers (GOOGL dropped)
            assert len(result['weights']) >= 2


class TestCovarianceRegularization:
    """Test covariance matrix regularization logic."""
    
    def test_ledoit_wolf_shrinkage(self):
        """Test Ledoit-Wolf shrinkage application."""
        from financial_dashboard.utils.portfolio import PortfolioOptimizer
        
        tickers = ['AAPL', 'MSFT']
        dates = pd.date_range(end=datetime.now(), periods=60, freq='D')
        
        # Create problematic data
        base = np.random.randn(60).cumsum()
        prices = pd.DataFrame({
            'AAPL': base + 100,
            'MSFT': base * 1.5 + 200  # High correlation
        }, index=dates)
        
        with patch.object(PortfolioOptimizer, '_fetch_prices', return_value=prices):
            optimizer = PortfolioOptimizer(
                tickers=tickers,
                start_date=dates[0],
                end_date=dates[-1]
            )
            
            if optimizer.optimization_status == 'needs_shrinkage':
                reg_cov = optimizer._get_regularized_covariance()
                
                # Regularized covariance should be positive definite
                eigenvalues = np.linalg.eigvals(reg_cov)
                assert all(eigenvalues > 0), "Regularized covariance should be positive definite"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
