"""
Integration tests for MLflow logging in strategy backtests.

These tests verify that:
1. Running backtest initializes MLflow experiment
2. At least one metric is logged during backtest
3. MLflow integration works without errors
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from financial_dashboard.services.options_service.strategies.covered_call_screener import CoveredCallScreener


@pytest.fixture
def sample_backtest_df():
    """Create sample data for backtesting."""
    dates = pd.date_range(end=datetime.now(), periods=60, freq='D')
    
    return pd.DataFrame({
        'Date': dates,
        'Open': np.linspace(100, 120, 60),
        'High': np.linspace(102, 122, 60),
        'Low': np.linspace(98, 118, 60),
        'Close': np.linspace(100, 120, 60),
        'Volume': [1000000] * 60
    })


class TestMLflowInitialization:
    """Test that MLflow experiment is initialized during backtest."""
    
    @patch('financial_dashboard.services.options_service.strategies.covered_call_screener.initialize_mlflow_experiment')
    def test_backtest_initializes_mlflow_experiment(self, mock_init_mlflow, sample_backtest_df):
        """Backtest should call initialize_mlflow_experiment."""
        screener = CoveredCallScreener(
            name="test_mlflow",
            params={"ticker": "TEST"}
        )
        
        # Run backtest
        result = screener.backtest(sample_backtest_df)
        
        # Verify MLflow was initialized
        mock_init_mlflow.assert_called_once()
        
        # Check experiment name contains strategy info
        call_args = mock_init_mlflow.call_args[0]
        experiment_name = call_args[0]
        assert isinstance(experiment_name, str)
        assert len(experiment_name) > 0
    
    @patch('financial_dashboard.services.options_service.strategies.covered_call_screener.mlflow')
    @patch('financial_dashboard.services.options_service.strategies.covered_call_screener.initialize_mlflow_experiment')
    def test_mlflow_initialization_uses_correct_experiment_name(self, mock_init, mock_mlflow, sample_backtest_df):
        """MLflow should be initialized with descriptive experiment name."""
        screener = CoveredCallScreener(
            name="covered_call_test",
            params={"ticker": "AAPL"}
        )
        
        screener.backtest(sample_backtest_df)
        
        # Experiment name should reference strategy
        experiment_name = mock_init.call_args[0][0]
        assert "strategy" in experiment_name.lower() or "covered" in experiment_name.lower()


class TestMLflowMetricLogging:
    """Test that metrics are logged to MLflow during backtest."""
    
    @patch('financial_dashboard.services.options_service.strategies.covered_call_screener.mlflow')
    @patch('financial_dashboard.services.options_service.strategies.covered_call_screener.initialize_mlflow_experiment')
    def test_backtest_logs_at_least_one_metric(self, mock_init, mock_mlflow, sample_backtest_df):
        """Backtest should log at least one metric to MLflow."""
        # Setup mock MLflow
        mock_mlflow.log_metric = Mock()
        mock_mlflow.log_param = Mock()
        
        screener = CoveredCallScreener(
            name="test_metrics",
            params={"ticker": "TEST", "top_n": 3}
        )
        
        # Run backtest
        result = screener.backtest(sample_backtest_df)
        
        # Verify at least one metric was logged
        # Note: This will fail initially because backtest() doesn't exist yet
        assert mock_mlflow.log_metric.call_count >= 1, \
            "Backtest should log at least one metric"
    
    @patch('financial_dashboard.services.options_service.strategies.covered_call_screener.mlflow')
    @patch('financial_dashboard.services.options_service.strategies.covered_call_screener.initialize_mlflow_experiment')
    def test_backtest_logs_parameters(self, mock_init, mock_mlflow, sample_backtest_df):
        """Backtest should log strategy parameters to MLflow."""
        mock_mlflow.log_param = Mock()
        mock_mlflow.log_metric = Mock()
        
        params = {"ticker": "AAPL", "top_n": 5, "min_return": 0.02}
        
        screener = CoveredCallScreener(
            name="test_params",
            params=params
        )
        
        result = screener.backtest(sample_backtest_df)
        
        # Should log some parameters
        assert mock_mlflow.log_param.call_count >= 1, \
            "Backtest should log strategy parameters"


class TestBacktestReturnValue:
    """Test that backtest returns proper data structure."""
    
    @patch('financial_dashboard.services.options_service.strategies.covered_call_screener.mlflow')
    @patch('financial_dashboard.services.options_service.strategies.covered_call_screener.initialize_mlflow_experiment')
    def test_backtest_returns_dict(self, mock_init, mock_mlflow, sample_backtest_df):
        """Backtest should return a dictionary of results."""
        screener = CoveredCallScreener(
            name="test_return",
            params={"ticker": "TEST"}
        )
        
        result = screener.backtest(sample_backtest_df)
        
        assert isinstance(result, dict), "Backtest should return dict"
    
    @patch('financial_dashboard.services.options_service.strategies.covered_call_screener.mlflow')
    @patch('financial_dashboard.services.options_service.strategies.covered_call_screener.initialize_mlflow_experiment')
    def test_backtest_returns_metrics(self, mock_init_mlflow, mock_mlflow, sample_backtest_df):
        """Backtest result should contain performance metrics."""
        mock_mlflow.log_metric = Mock()
        mock_mlflow.log_param = Mock()
        
        screener = CoveredCallScreener(
            name="test_metrics_return",
            params={"ticker": "TEST"}
        )
        
        result = screener.backtest(sample_backtest_df)
        
        # Result should have at least one metric
        assert len(result) > 0, "Backtest should return metrics"
        
        # Should contain numeric values
        has_numeric = any(isinstance(v, (int, float)) for v in result.values())
        assert has_numeric, "Backtest should return numeric metrics"


class TestMLflowIntegrationEndToEnd:
    """End-to-end test of MLflow integration."""
    
    @patch('financial_dashboard.services.options_service.strategies.covered_call_screener.mlflow.start_run')
    @patch('financial_dashboard.services.options_service.strategies.covered_call_screener.mlflow.log_metric')
    @patch('financial_dashboard.services.options_service.strategies.covered_call_screener.mlflow.log_param')
    @patch('financial_dashboard.services.options_service.strategies.covered_call_screener.initialize_mlflow_experiment')
    def test_complete_mlflow_workflow(self, mock_init, mock_log_param, 
                                       mock_log_metric, mock_start_run, 
                                       sample_backtest_df):
        """Test complete MLflow workflow: init -> start run -> log params/metrics."""
        # Setup context manager for start_run
        mock_run_context = MagicMock()
        mock_start_run.return_value.__enter__ = Mock(return_value=mock_run_context)
        mock_start_run.return_value.__exit__ = Mock(return_value=False)
        
        screener = CoveredCallScreener(
            name="e2e_test",
            params={"ticker": "AAPL", "top_n": 3}
        )
        
        # Run backtest - should trigger full MLflow workflow
        result = screener.backtest(sample_backtest_df)
        
        # Verify workflow executed
        mock_init.assert_called_once()  # MLflow initialized
        
        # Should have logged something (params or metrics)
        total_logs = mock_log_param.call_count + mock_log_metric.call_count
        assert total_logs >= 1, "Should log at least one param or metric"
