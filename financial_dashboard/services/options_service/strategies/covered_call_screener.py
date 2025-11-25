"""
Covered Call Screener Strategy.

This module implements a concrete strategy for screening stocks suitable
for covered call options strategies. Uses volatility and return metrics
to identify stable growth candidates.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime

from .base_strategy import BaseStrategy
from financial_dashboard.utils.mlflow_helpers import initialize_mlflow_experiment
import mlflow


class CoveredCallScreener(BaseStrategy):
    """
    Screen stocks for covered call opportunities based on volatility and returns.
    
    This strategy favors stocks with stable growth (positive returns with low volatility).
    The scoring formula is: mean_daily_return * -volatility, where higher scores indicate
    better candidates for covered calls.
    
    Attributes:
        name: Strategy name
        params: Strategy parameters, should include 'ticker' key
        price_client: Optional injected price client for fetching historical data
        
    Example:
        >>> screener = CoveredCallScreener(
        ...     name="CC_Screen",
        ...     params={"ticker": "AAPL", "lookback_days": 30}
        ... )
        >>> signals = screener.generate_signals(historical_df)
    """
    
    def __init__(self, name: str, params: Dict[str, Any], price_client=None):
        """
        Initialize the covered call screener strategy.
        
        Args:
            name: Strategy name
            params: Parameters including 'ticker' and optionally 'lookback_days'
            price_client: Optional price client for fetching data (for dependency injection)
        """
        super().__init__(name, params)
        self.price_client = price_client
    
    def generate_signals(self, historical_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Generate covered call screening signals based on historical price data.
        
        Analyzes the provided historical data to calculate a score based on mean
        daily returns and volatility. Higher scores indicate better covered call
        candidates (stable growth with low volatility).
        
        Args:
            historical_df: DataFrame with columns [Date, Open, High, Low, Close, Volume]
                          Should contain at least 20 days of data for meaningful analysis
                          
        Returns:
            List of signal dictionaries, each containing:
                - ticker: Stock symbol from params
                - score: Calculated score (mean_return * -volatility)
                - recommended_strike: Strike price (~10% above current price)
                - recommendation_date: Latest date in the dataset
                
        Example:
            >>> signals = screener.generate_signals(price_data)
            >>> # [{"ticker": "AAPL", "score": 0.0023, "recommended_strike": 175.5, ...}]
        """
        if historical_df.empty:
            return []
        
        # Ensure Date column is datetime
        if 'Date' in historical_df.columns:
            historical_df['Date'] = pd.to_datetime(historical_df['Date'])
        
        # Calculate daily returns
        daily_returns = historical_df['Close'].pct_change().dropna()
        
        # Calculate metrics
        mean_return = daily_returns.mean()
        volatility = daily_returns.std()
        
        # Scoring: favor positive returns with low volatility
        # Multiply by -volatility so lower volatility gives higher score
        score = mean_return * -volatility if volatility > 0 else 0.0
        
        # Get current price and calculate strike (~10% OTM)
        current_price = historical_df['Close'].iloc[-1]
        recommended_strike = round(current_price * 1.10, 2)
        
        # Get recommendation date (latest date in data)
        recommendation_date = historical_df['Date'].iloc[-1] if 'Date' in historical_df.columns else pd.Timestamp.now()
        
        # Get ticker from params
        ticker = self.params.get('ticker', 'UNKNOWN')
        
        signal = {
            "ticker": ticker,
            "score": round(score, 6),
            "recommended_strike": recommended_strike,
            "recommendation_date": recommendation_date.strftime('%Y-%m-%d') if isinstance(recommendation_date, pd.Timestamp) else str(recommendation_date)
        }
        
        return [signal]
    
    def backtest(self, historical_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Run a backtest of the covered call screener strategy.
        
        This implementation initializes MLflow experiment tracking, logs strategy
        parameters and performance metrics. The backtest simulates the strategy's
        performance and returns key metrics.
        
        Args:
            historical_df: DataFrame with columns [Date, Open, High, Low, Close, Volume]
                          Should contain sufficient historical data (typically 60+ days)
                          
        Returns:
            Dictionary of performance metrics:
                - sharpe_ratio: Risk-adjusted return measure
                - total_return: Total percentage return over the period
                - max_drawdown: Maximum peak-to-trough decline
                - num_trades: Number of simulated trades
                
        Example:
            >>> results = screener.backtest(historical_data)
            >>> # {"sharpe_ratio": 1.5, "total_return": 0.25, ...}
        """
        # Initialize MLflow experiment for tracking
        experiment_name = self.params.get('experiment_name', 'Strategy Validation')
        initialize_mlflow_experiment(experiment_name)
        
        # Start an MLflow run
        with mlflow.start_run(run_name=f"{self.name}_backtest"):
            # Log strategy parameters
            mlflow.log_param("strategy_name", self.name)
            mlflow.log_param("ticker", self.params.get('ticker', 'UNKNOWN'))
            
            # Log additional params if present
            for key, value in self.params.items():
                if key not in ['experiment_name']:  # Skip non-model params
                    mlflow.log_param(key, value)
            
            # Calculate backtest metrics
            # For simplicity, using basic metrics - real implementation would be more sophisticated
            if not historical_df.empty and 'Close' in historical_df.columns:
                # Calculate returns
                daily_returns = historical_df['Close'].pct_change().dropna()
                total_return = (historical_df['Close'].iloc[-1] / historical_df['Close'].iloc[0]) - 1
                
                # Calculate Sharpe ratio (simplified, assuming 0 risk-free rate)
                mean_return = daily_returns.mean()
                std_return = daily_returns.std()
                sharpe_ratio = (mean_return / std_return) * (252 ** 0.5) if std_return > 0 else 0.0
                
                # Calculate max drawdown
                cumulative = (1 + daily_returns).cumprod()
                running_max = cumulative.expanding().max()
                drawdown = (cumulative - running_max) / running_max
                max_drawdown = drawdown.min()
                
                # Simulate number of trades (e.g., monthly covered calls)
                num_days = len(historical_df)
                num_trades = max(1, num_days // 30)
            else:
                # Default values if data is insufficient
                total_return = 0.0
                sharpe_ratio = 0.0
                max_drawdown = 0.0
                num_trades = 0
            
            # Log metrics to MLflow
            mlflow.log_metric("sharpe_ratio", sharpe_ratio)
            mlflow.log_metric("total_return", total_return)
            mlflow.log_metric("max_drawdown", abs(max_drawdown))
            mlflow.log_metric("num_trades", num_trades)
            
            # Return performance metrics
            results = {
                "sharpe_ratio": round(sharpe_ratio, 4),
                "total_return": round(total_return, 4),
                "max_drawdown": round(abs(max_drawdown), 4),
                "num_trades": num_trades
            }
            
            return results
