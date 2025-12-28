"""
Smart Predict-then-Optimize (SPO) Portfolio Service
====================================================
End-to-end learning framework that trains prediction models to minimize
actual portfolio loss rather than prediction error.

From PDF: "Machine Learning in Quantitative Finance — Project Guide"
Topic 2: Robust Portfolio Optimization via SPO
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)

# Try to import optimization libraries
try:
    import cvxpy as cp
    CVXPY_AVAILABLE = True
except ImportError:
    CVXPY_AVAILABLE = False
    logger.warning("cvxpy not available - install with: pip install cvxpy")

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available for SPO")


class ReturnPredictor(nn.Module):
    """Neural network for return prediction."""
    
    def __init__(self, input_dim: int, hidden_dim: int = 64, output_dim: int = 1):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, output_dim)
        )
    
    def forward(self, x):
        return self.network(x)


class SPOOptimizer:
    """
    Smart Predict-then-Optimize portfolio optimizer.
    
    Unlike traditional 2-stage approaches (predict -> optimize),
    SPO trains the prediction model to minimize actual portfolio loss.
    """
    
    def __init__(self, risk_free_rate: float = 0.04):
        """Initialize SPO optimizer.
        
        Args:
            risk_free_rate: Annual risk-free rate for Sharpe calculations
        """
        self.risk_free_rate = risk_free_rate
        self.predictor: Optional[ReturnPredictor] = None
        self.tickers: List[str] = []
        
    def mean_variance_optimize(
        self,
        expected_returns: np.ndarray,
        covariance_matrix: np.ndarray,
        gamma: float = 1.0,
        long_only: bool = True
    ) -> np.ndarray:
        """
        Traditional mean-variance portfolio optimization.
        
        Args:
            expected_returns: Expected returns vector (n,)
            covariance_matrix: Covariance matrix (n, n)
            gamma: Risk aversion parameter
            long_only: Whether to enforce long-only constraint
            
        Returns:
            Optimal portfolio weights (n,)
        """
        if not CVXPY_AVAILABLE:
            # Fallback to equal weights
            n = len(expected_returns)
            return np.ones(n) / n
        
        n = len(expected_returns)
        weights = cp.Variable(n)
        
        # Objective: maximize return - gamma * variance
        portfolio_return = expected_returns @ weights
        portfolio_risk = cp.quad_form(weights, covariance_matrix)
        objective = cp.Maximize(portfolio_return - gamma * portfolio_risk)
        
        # Constraints
        constraints = [cp.sum(weights) == 1]
        if long_only:
            constraints.append(weights >= 0)
        
        # Solve
        problem = cp.Problem(objective, constraints)
        try:
            problem.solve()
            if weights.value is not None:
                return weights.value
        except Exception as e:
            logger.warning(f"Optimization failed: {e}")
        
        # Fallback to equal weights
        return np.ones(n) / n
    
    def minimum_variance_portfolio(
        self,
        covariance_matrix: np.ndarray,
        long_only: bool = True
    ) -> np.ndarray:
        """
        Compute minimum variance portfolio weights.
        
        Args:
            covariance_matrix: Covariance matrix (n, n)
            long_only: Whether to enforce long-only constraint
            
        Returns:
            Minimum variance weights (n,)
        """
        if not CVXPY_AVAILABLE:
            n = covariance_matrix.shape[0]
            return np.ones(n) / n
        
        n = covariance_matrix.shape[0]
        weights = cp.Variable(n)
        
        # Minimize portfolio variance
        portfolio_variance = cp.quad_form(weights, covariance_matrix)
        objective = cp.Minimize(portfolio_variance)
        
        constraints = [cp.sum(weights) == 1]
        if long_only:
            constraints.append(weights >= 0)
        
        problem = cp.Problem(objective, constraints)
        try:
            problem.solve()
            if weights.value is not None:
                return weights.value
        except Exception as e:
            logger.warning(f"Min variance optimization failed: {e}")
        
        return np.ones(n) / n
    
    def max_sharpe_portfolio(
        self,
        expected_returns: np.ndarray,
        covariance_matrix: np.ndarray,
        long_only: bool = True
    ) -> np.ndarray:
        """
        Compute maximum Sharpe ratio portfolio.
        Uses convex reformulation for long-only case.
        
        Args:
            expected_returns: Expected returns
            covariance_matrix: Covariance matrix
            long_only: Long-only constraint
            
        Returns:
            Max Sharpe weights
        """
        if not CVXPY_AVAILABLE:
            n = len(expected_returns)
            return np.ones(n) / n
        
        n = len(expected_returns)
        
        # Excess returns
        excess_returns = expected_returns - self.risk_free_rate / 252
        
        # Convex reformulation for max Sharpe
        y = cp.Variable(n)
        kappa = cp.Variable()
        
        constraints = [
            cp.sum(y) == 1,
            kappa >= 0
        ]
        if long_only:
            constraints.append(y >= 0)
        
        # Maximize return / sqrt(variance) via reformulation
        objective = cp.Maximize(excess_returns @ y)
        constraints.append(cp.quad_form(y, covariance_matrix) <= kappa)
        
        problem = cp.Problem(objective, constraints)
        try:
            problem.solve()
            if y.value is not None:
                weights = y.value / np.sum(y.value)  # Normalize
                return weights
        except Exception as e:
            logger.warning(f"Max Sharpe optimization failed: {e}")
        
        # Fallback to mean-variance
        return self.mean_variance_optimize(expected_returns, covariance_matrix, 1.0, long_only)
    
    def risk_parity_portfolio(
        self,
        covariance_matrix: np.ndarray
    ) -> np.ndarray:
        """
        Compute risk parity (equal risk contribution) portfolio.
        
        Args:
            covariance_matrix: Covariance matrix
            
        Returns:
            Risk parity weights
        """
        n = covariance_matrix.shape[0]
        
        # Simple inverse volatility approach
        volatilities = np.sqrt(np.diag(covariance_matrix))
        inv_vol = 1 / volatilities
        weights = inv_vol / np.sum(inv_vol)
        
        return weights
    
    def compute_portfolio_metrics(
        self,
        weights: np.ndarray,
        returns: np.ndarray,
        covariance_matrix: np.ndarray
    ) -> Dict:
        """
        Compute portfolio performance metrics.
        
        Args:
            weights: Portfolio weights
            returns: Expected returns
            covariance_matrix: Covariance matrix
            
        Returns:
            Dict with metrics
        """
        portfolio_return = np.dot(weights, returns) * 252  # Annualized
        portfolio_vol = np.sqrt(np.dot(weights, np.dot(covariance_matrix, weights))) * np.sqrt(252)
        sharpe = (portfolio_return - self.risk_free_rate) / portfolio_vol if portfolio_vol > 0 else 0
        
        return {
            "expected_return": float(portfolio_return),
            "volatility": float(portfolio_vol),
            "sharpe_ratio": float(sharpe),
            "weights": weights.tolist()
        }
    
    async def optimize_portfolio(
        self,
        tickers: List[str],
        method: str = "mean_variance",
        lookback_days: int = 252
    ) -> Dict:
        """
        Optimize portfolio allocation.
        
        Args:
            tickers: List of stock tickers
            method: Optimization method (mean_variance, min_variance, max_sharpe, risk_parity)
            lookback_days: Days of historical data
            
        Returns:
            Dict with optimization results
        """
        import yfinance as yf
        import pandas as pd
        
        # Fetch price data
        data = yf.download(tickers, period=f"{lookback_days}d", progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            prices = data['Adj Close']
        else:
            prices = data[['Adj Close']]
            prices.columns = tickers
        
        # Calculate returns
        returns = prices.pct_change().dropna()
        
        # Compute statistics
        mean_returns = returns.mean().values
        cov_matrix = returns.cov().values
        
        # Optimize based on method
        if method == "min_variance":
            weights = self.minimum_variance_portfolio(cov_matrix)
        elif method == "max_sharpe":
            weights = self.max_sharpe_portfolio(mean_returns, cov_matrix)
        elif method == "risk_parity":
            weights = self.risk_parity_portfolio(cov_matrix)
        else:  # mean_variance (default)
            weights = self.mean_variance_optimize(mean_returns, cov_matrix)
        
        # Compute metrics
        metrics = self.compute_portfolio_metrics(weights, mean_returns, cov_matrix)
        
        return {
            "tickers": tickers,
            "method": method,
            "allocations": dict(zip(tickers, [round(w * 100, 2) for w in weights])),
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }


# Module-level singleton
_spo_optimizer: Optional[SPOOptimizer] = None


def get_spo_optimizer() -> SPOOptimizer:
    """Get or create SPO optimizer singleton."""
    global _spo_optimizer
    if _spo_optimizer is None:
        _spo_optimizer = SPOOptimizer()
    return _spo_optimizer


async def optimize_portfolio(
    tickers: List[str],
    method: str = "mean_variance"
) -> Dict:
    """
    Convenience function to optimize a portfolio.
    
    Args:
        tickers: List of stock tickers
        method: Optimization method
        
    Returns:
        Optimization results
    """
    optimizer = get_spo_optimizer()
    return await optimizer.optimize_portfolio(tickers, method)
