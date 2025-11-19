"""
Backtester Service - Core Logic

This module provides the core backtesting functionality:
- Strategy execution on historical data
- Metrics computation (PnL, Sharpe ratio, max drawdown)
- MLflow integration for experiment tracking
- Integration with Strategy Registry
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import json

try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False

from financial_dashboard.services.options_service.strategies.strategy_registry import (
    StrategyRegistry,
    StrategyNotFoundError
)


def compute_metrics(returns: pd.Series, initial_capital: float = 10000.0) -> Dict[str, float]:
    """
    Compute backtest performance metrics from returns series.
    
    Args:
        returns: Series of period returns (e.g., daily returns)
        initial_capital: Starting capital
    
    Returns:
        Dictionary with metrics:
            - pnl: Profit and loss
            - total_return: Total percentage return
            - sharpe_ratio: Risk-adjusted return metric
            - max_drawdown: Maximum peak-to-trough decline
    """
    if len(returns) == 0 or returns.sum() == 0:
        return {
            'pnl': 0.0,
            'total_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'num_trades': 0
        }
    
    # Calculate cumulative returns
    cumulative_returns = (1 + returns).cumprod()
    
    # Total return
    total_return = cumulative_returns.iloc[-1] - 1.0
    
    # PnL
    pnl = initial_capital * total_return
    
    # Sharpe ratio (annualized, assuming daily returns)
    mean_return = returns.mean()
    std_return = returns.std()
    
    if std_return > 0:
        sharpe_ratio = (mean_return / std_return) * np.sqrt(252)  # Annualized
    else:
        sharpe_ratio = 0.0
    
    # Max drawdown
    cumulative_max = cumulative_returns.cummax()
    drawdown = (cumulative_returns - cumulative_max) / cumulative_max
    max_drawdown = drawdown.min()
    
    return {
        'pnl': round(pnl, 2),
        'total_return': round(total_return, 4),
        'sharpe_ratio': round(sharpe_ratio, 4),
        'max_drawdown': round(max_drawdown, 4),
        'num_trades': len(returns)
    }


class BacktesterService:
    """
    Core backtesting service that runs strategies on historical data.
    
    Features:
    - Strategy execution via registry
    - Historical data fetching via PriceClient
    - Metrics computation
    - MLflow experiment tracking
    
    Example:
        >>> backtester = BacktesterService(price_client=my_client, mlflow_tracking=True)
        >>> results = backtester.run_backtest_by_name(
        ...     strategy_name='CoveredCallScreener',
        ...     start_date='2024-01-01',
        ...     end_date='2024-12-31',
        ...     initial_capital=10000.0,
        ...     strategy_params={'ticker': 'AAPL'}
        ... )
        >>> print(results['metrics']['sharpe_ratio'])
    """
    
    def __init__(
        self,
        price_client=None,
        mlflow_tracking: bool = False,
        mlflow_experiment: str = "backtester-experiments"
    ):
        """
        Initialize BacktesterService.
        
        Args:
            price_client: Client for fetching historical price data
            mlflow_tracking: Enable MLflow experiment tracking
            mlflow_experiment: MLflow experiment name
        """
        self.price_client = price_client
        self.mlflow_tracking = mlflow_tracking and MLFLOW_AVAILABLE
        self.mlflow_experiment = mlflow_experiment
        
        if self.mlflow_tracking:
            mlflow.set_experiment(self.mlflow_experiment)
    
    def run_backtest(
        self,
        strategy,
        start_date: str,
        end_date: str,
        initial_capital: float = 10000.0
    ) -> Dict[str, Any]:
        """
        Run backtest with a strategy instance.
        
        Args:
            strategy: Strategy instance (must have generate_signals method)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            initial_capital: Starting capital
        
        Returns:
            Dictionary with run_id, metrics, and status
        
        Raises:
            ValueError: If dates are invalid
        """
        # Validate dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        if start_dt >= end_dt:
            raise ValueError("start_date must be before end_date")
        
        # Generate run ID
        run_id = str(uuid.uuid4())
        
        # Start MLflow run if enabled
        if self.mlflow_tracking:
            mlflow.start_run(run_name=f"{strategy.name}_{start_date}_to_{end_date}")
            mlflow.log_param("strategy_name", strategy.name)
            mlflow.log_param("start_date", start_date)
            mlflow.log_param("end_date", end_date)
            mlflow.log_param("initial_capital", initial_capital)
            
            # Log strategy params
            if hasattr(strategy, 'params') and strategy.params:
                for key, value in strategy.params.items():
                    mlflow.log_param(f"strategy_{key}", value)
            
            run_id = mlflow.active_run().info.run_id
        
        try:
            # Fetch historical data
            if self.price_client:
                ticker = strategy.params.get('ticker', 'SPY')
                historical_df = self.price_client.get_historical_data(
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date
                )
            else:
                # Create dummy data for testing without client
                historical_df = pd.DataFrame({
                    'Date': pd.date_range(start=start_date, end=end_date, freq='D'),
                    'Close': 100.0
                })
            
            # Generate signals
            signals = strategy.generate_signals(historical_df)
            
            # Simulate trading and compute returns
            returns = self._simulate_trading(signals, historical_df, initial_capital)
            
            # Compute metrics
            metrics = compute_metrics(returns, initial_capital)
            
            # Log metrics to MLflow
            if self.mlflow_tracking:
                for metric_name, metric_value in metrics.items():
                    if isinstance(metric_value, (int, float)):
                        mlflow.log_metric(metric_name, metric_value)
            
            result = {
                'run_id': run_id,
                'status': 'completed',
                'metrics': metrics,
                'num_signals': len(signals)
            }
            
            return result
            
        except Exception as e:
            if self.mlflow_tracking and mlflow.active_run():
                mlflow.log_param("error", str(e))
                mlflow.end_run(status='FAILED')
            raise
        finally:
            if self.mlflow_tracking and mlflow.active_run():
                mlflow.end_run()
    
    def run_backtest_by_name(
        self,
        strategy_name: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 10000.0,
        strategy_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run backtest by strategy name using registry.
        
        Args:
            strategy_name: Name of strategy in registry
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            initial_capital: Starting capital
            strategy_params: Parameters to pass to strategy
        
        Returns:
            Dictionary with run_id, metrics, and status
        
        Raises:
            StrategyNotFoundError: If strategy not in registry
        """
        # Get strategy from registry
        registry = StrategyRegistry.get_instance()
        strategy_class = registry.get_strategy(strategy_name)
        
        # Instantiate strategy with params
        if strategy_params is None:
            strategy_params = {}
        
        strategy = strategy_class(
            name=strategy_name,
            params=strategy_params
        )
        
        # Run backtest
        return self.run_backtest(
            strategy=strategy,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital
        )
    
    def _simulate_trading(
        self,
        signals: List[Dict[str, Any]],
        historical_df: pd.DataFrame,
        initial_capital: float
    ) -> pd.Series:
        """
        Simulate trading based on signals and compute returns.
        
        Args:
            signals: List of trading signals
            historical_df: Historical price data
            initial_capital: Starting capital
        
        Returns:
            Series of period returns
        """
        if len(signals) == 0:
            # No trades, zero returns
            return pd.Series([0.0])
        
        # Simple simulation: buy on BUY signal, sell on SELL signal
        # Track position and compute returns
        returns = []
        position = 0  # Current position size
        entry_price = 0.0
        
        for signal in signals:
            action = signal.get('action', 'HOLD')
            price = signal.get('price', 0.0)
            quantity = signal.get('quantity', 1)
            
            if action == 'BUY' and position == 0:
                # Enter position
                position = quantity
                entry_price = price
            elif action == 'SELL' and position > 0:
                # Exit position and compute return
                exit_price = price
                trade_return = (exit_price - entry_price) / entry_price
                returns.append(trade_return)
                position = 0
                entry_price = 0.0
        
        if len(returns) == 0:
            return pd.Series([0.0])
        
        return pd.Series(returns)
