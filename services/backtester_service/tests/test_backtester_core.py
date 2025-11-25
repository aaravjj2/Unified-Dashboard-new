"""
TDD RED Phase: Core Backtester Logic Tests

These tests will initially fail as backtester.py doesn't exist yet.
Tests cover:
- Metrics computation (PnL, Sharpe, max drawdown)
- Strategy registry integration
- PriceClient mocking
- Parameter passing
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# These imports will fail initially - expected for RED phase
try:
    from services.backtester_service.backtester import BacktesterService
    from services.backtester_service.backtester import compute_metrics
except ImportError:
    BacktesterService = None
    compute_metrics = None


@pytest.fixture
def mock_price_client():
    """Mock PriceClient that returns deterministic data."""
    client = Mock()
    
    # Create deterministic price data
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    prices = pd.DataFrame({
        'Date': dates,
        'Open': 100 + np.arange(100) * 0.5,  # Upward trend
        'High': 101 + np.arange(100) * 0.5,
        'Low': 99 + np.arange(100) * 0.5,
        'Close': 100 + np.arange(100) * 0.5,
        'Volume': 1000000
    })
    
    client.get_historical_data.return_value = prices
    return client


@pytest.fixture
def mock_strategy():
    """Mock strategy that generates deterministic signals."""
    strategy = Mock()
    strategy.name = "MockStrategy"
    
    # Generate signals: buy every 10 days
    def generate_signals(historical_df):
        signals = []
        for i in range(0, len(historical_df), 10):
            signals.append({
                'ticker': 'TEST',
                'date': historical_df.iloc[i]['Date'],
                'action': 'BUY' if i % 20 == 0 else 'SELL',
                'quantity': 10,
                'price': historical_df.iloc[i]['Close']
            })
        return signals
    
    strategy.generate_signals = Mock(side_effect=generate_signals)
    strategy.params = {'ticker': 'TEST'}
    
    return strategy


class TestBacktesterMetricsComputation:
    """Test accurate computation of backtest metrics."""
    
    def test_backtester_computes_metrics_correctly(self, mock_price_client, mock_strategy):
        """
        Test that backtester computes PnL, Sharpe, and max drawdown correctly.
        Uses deterministic data with known outcomes.
        """
        if BacktesterService is None:
            pytest.skip("BacktesterService not yet implemented")
        
        backtester = BacktesterService(price_client=mock_price_client)
        
        results = backtester.run_backtest(
            strategy=mock_strategy,
            start_date='2024-01-01',
            end_date='2024-04-10',
            initial_capital=10000.0
        )
        
        # Assert results structure
        assert 'metrics' in results
        assert 'pnl' in results['metrics']
        assert 'sharpe_ratio' in results['metrics']
        assert 'max_drawdown' in results['metrics']
        assert 'total_return' in results['metrics']
        
        # Assert reasonable values (with deterministic data these should be predictable)
        assert results['metrics']['pnl'] != 0, "PnL should not be zero with trades"
        assert results['metrics']['sharpe_ratio'] is not None
        assert results['metrics']['max_drawdown'] <= 0, "Max drawdown should be negative or zero"
        assert -1.0 <= results['metrics']['max_drawdown'] <= 0.0, "Max drawdown should be between -100% and 0%"
    
    def test_compute_metrics_with_positive_returns(self):
        """Test metrics computation with positive returns."""
        if compute_metrics is None:
            pytest.skip("compute_metrics not yet implemented")
        
        # Create returns series with known properties
        returns = pd.Series([0.01, 0.02, -0.01, 0.03, 0.01])  # Mostly positive
        
        metrics = compute_metrics(returns, initial_capital=10000)
        
        assert metrics['total_return'] > 0, "Total return should be positive"
        assert metrics['sharpe_ratio'] > 0, "Sharpe should be positive with consistent positive returns"
        assert metrics['max_drawdown'] < 0, "Max drawdown should be negative (a drawdown occurred)"
    
    def test_compute_metrics_with_zero_returns(self):
        """Test metrics computation when no trades occur."""
        if compute_metrics is None:
            pytest.skip("compute_metrics not yet implemented")
        
        returns = pd.Series([0.0, 0.0, 0.0, 0.0])
        
        metrics = compute_metrics(returns, initial_capital=10000)
        
        assert metrics['total_return'] == 0.0
        assert metrics['pnl'] == 0.0
        assert metrics['max_drawdown'] == 0.0


class TestBacktesterRegistryIntegration:
    """Test integration with strategy registry."""
    
    @patch('services.backtester_service.backtester.StrategyRegistry')
    def test_backtester_uses_registry_and_params(self, mock_registry_class, mock_price_client):
        """
        Test that backtester correctly uses registry to instantiate strategy with params.
        """
        if BacktesterService is None:
            pytest.skip("BacktesterService not yet implemented")
        
        # Setup mock registry
        mock_registry = Mock()
        mock_registry_class.get_instance.return_value = mock_registry
        
        # Mock strategy class and instance
        mock_strategy_class = Mock()
        mock_strategy_instance = Mock()
        mock_strategy_instance.name = "TestStrategy"
        mock_strategy_instance.params = {'ticker': 'AAPL', 'threshold': 0.5}
        mock_strategy_instance.generate_signals.return_value = []
        
        mock_strategy_class.return_value = mock_strategy_instance
        mock_registry.get_strategy.return_value = mock_strategy_class
        
        # Run backtest
        backtester = BacktesterService(price_client=mock_price_client)
        results = backtester.run_backtest_by_name(
            strategy_name='TestStrategy',
            start_date='2024-01-01',
            end_date='2024-01-31',
            initial_capital=10000.0,
            strategy_params={'ticker': 'AAPL', 'threshold': 0.5}
        )
        
        # Verify registry was used
        mock_registry.get_strategy.assert_called_once_with('TestStrategy')
        
        # Verify strategy was instantiated with correct params
        mock_strategy_class.assert_called_once()
        call_kwargs = mock_strategy_class.call_args[1]
        assert 'params' in call_kwargs
        assert call_kwargs['params']['ticker'] == 'AAPL'
        assert call_kwargs['params']['threshold'] == 0.5


class TestBacktesterMLflowIntegration:
    """Test MLflow logging integration."""
    
    @patch('services.backtester_service.backtester.mlflow')
    def test_backtester_logs_to_mlflow(self, mock_mlflow, mock_price_client, mock_strategy):
        """Test that backtester logs parameters and metrics to MLflow."""
        if BacktesterService is None:
            pytest.skip("BacktesterService not yet implemented")
        
        backtester = BacktesterService(
            price_client=mock_price_client,
            mlflow_tracking=True
        )
        
        results = backtester.run_backtest(
            strategy=mock_strategy,
            start_date='2024-01-01',
            end_date='2024-01-31',
            initial_capital=10000.0
        )
        
        # Verify MLflow was used
        assert mock_mlflow.set_experiment.called or mock_mlflow.start_run.called
        
        # Verify run_id is returned
        assert 'run_id' in results
        assert results['run_id'] is not None


class TestBacktesterEdgeCases:
    """Test edge cases and error handling."""
    
    def test_backtester_handles_no_signals(self, mock_price_client):
        """Test backtester handles strategy that generates no signals."""
        if BacktesterService is None:
            pytest.skip("BacktesterService not yet implemented")
        
        # Strategy that returns empty signals
        empty_strategy = Mock()
        empty_strategy.name = "EmptyStrategy"
        empty_strategy.generate_signals.return_value = []
        empty_strategy.params = {}
        
        backtester = BacktesterService(price_client=mock_price_client)
        results = backtester.run_backtest(
            strategy=empty_strategy,
            start_date='2024-01-01',
            end_date='2024-01-31',
            initial_capital=10000.0
        )
        
        # Should complete without error and return zero metrics
        assert results['metrics']['pnl'] == 0.0
        assert results['metrics']['total_return'] == 0.0
    
    def test_backtester_validates_dates(self, mock_price_client, mock_strategy):
        """Test backtester validates start_date < end_date."""
        if BacktesterService is None:
            pytest.skip("BacktesterService not yet implemented")
        
        backtester = BacktesterService(price_client=mock_price_client)
        
        with pytest.raises(ValueError, match="start_date must be before end_date"):
            backtester.run_backtest(
                strategy=mock_strategy,
                start_date='2024-12-31',
                end_date='2024-01-01',  # Before start
                initial_capital=10000.0
            )
