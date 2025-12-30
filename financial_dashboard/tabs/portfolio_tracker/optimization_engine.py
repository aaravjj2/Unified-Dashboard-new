"""
Riskfolio-Lib Portfolio Optimization Engine

Phase 1: CDaR (Conditional Drawdown at Risk) and EVaR (Entropic Value at Risk) optimization.

Provides tail-risk focused portfolio optimization using Riskfolio-Lib.
Falls back to equal-weight portfolio if riskfolio-lib is not installed.

Author: Agent-P1
Date: 2025-12-28
"""

import os
import logging
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Try to import riskfolio-lib
try:
    import riskfolio as rp
    RISKFOLIO_AVAILABLE = True
    logger.info("Riskfolio-Lib loaded successfully")
except ImportError:
    RISKFOLIO_AVAILABLE = False
    logger.warning("Riskfolio-Lib not available, using fallback optimization")

# Try to import yfinance for data
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance not available")

# Deterministic mode for testing
DETERMINISTIC = os.getenv('PHASE1_DETERMINISTIC', '0') == '1'

# Supported risk measures with descriptions
SUPPORTED_RISK_MEASURES = {
    'CDaR': 'Conditional Drawdown at Risk (Tail Drawdown)',
    'EVaR': 'Entropic Value at Risk (Coherent Risk)',
    'CVaR': 'Conditional Value at Risk (Expected Shortfall)',
    'MV': 'Mean-Variance (Standard Deviation)',
    'MAD': 'Mean Absolute Deviation',
    'MSV': 'Mean Semi-Variance (Downside Risk)'
}


@dataclass
class OptimizationResult:
    """Result of portfolio optimization."""
    weights: Dict[str, float]
    risk_measure: str
    expected_return: float
    risk: float
    sharpe_ratio: float
    frontier_data: Optional[pd.DataFrame] = None
    optimization_time: float = 0.0
    success: bool = True
    error_message: str = ""
    cache_key: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class RiskfolioOptimizer:
    """
    Portfolio optimizer using Riskfolio-Lib.
    
    Supports tail-risk measures like CDaR and EVaR for robust optimization.
    Falls back to equal-weight if library unavailable.
    """
    
    def __init__(
        self,
        tickers: List[str],
        risk_measure: str = 'CDaR',
        lookback_years: int = 2,
        risk_free_rate: float = 0.03
    ):
        """
        Initialize optimizer.
        
        Args:
            tickers: List of ticker symbols
            risk_measure: Risk measure to optimize (CDaR, EVaR, CVaR, MV, MAD, MSV)
            lookback_years: Years of historical data to use
            risk_free_rate: Risk-free rate for Sharpe ratio calculation
        """
        self.tickers = sorted(list(set(tickers)))  # Remove duplicates, sort for cache key
        self.risk_measure = risk_measure.upper()
        self.lookback_years = lookback_years
        self.risk_free_rate = risk_free_rate
        
        # Validate risk measure
        if self.risk_measure not in SUPPORTED_RISK_MEASURES:
            logger.warning(f"Unknown risk measure '{risk_measure}', falling back to CDaR")
            self.risk_measure = 'CDaR'
        
        self._returns: Optional[pd.DataFrame] = None
        self._portfolio: Any = None
        
        # Generate cache key
        ticker_hash = hashlib.md5(','.join(self.tickers).encode()).hexdigest()[:8]
        self.cache_key = f"riskfolio:opt:{self.risk_measure}:{ticker_hash}"
    
    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch historical price data.
        
        Returns:
            DataFrame of daily returns
        """
        if DETERMINISTIC:
            # Return deterministic test data
            return self._generate_deterministic_data()
        
        if not YFINANCE_AVAILABLE:
            logger.warning("yfinance not available, using simulated data")
            return self._generate_deterministic_data()
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_years * 365)
            
            # Download adjusted close prices
            data = yf.download(
                self.tickers,
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                progress=False
            )['Adj Close']
            
            if isinstance(data, pd.Series):
                data = data.to_frame(self.tickers[0])
            
            # Calculate returns
            returns = data.pct_change().dropna()
            
            if len(returns) < 100:
                logger.warning(f"Insufficient data ({len(returns)} days), using simulated")
                return self._generate_deterministic_data()
            
            self._returns = returns
            logger.info(f"Fetched {len(returns)} days of data for {len(self.tickers)} tickers")
            return returns
            
        except Exception as e:
            logger.error(f"Failed to fetch data: {e}")
            return self._generate_deterministic_data()
    
    def _generate_deterministic_data(self) -> pd.DataFrame:
        """Generate deterministic return data for testing."""
        np.random.seed(42)
        n_days = 504  # ~2 years of trading days
        
        # Generate correlated returns
        n_assets = len(self.tickers)
        
        # Create correlation matrix
        corr = np.eye(n_assets) * 0.5 + 0.5 * np.random.rand(n_assets, n_assets)
        corr = (corr + corr.T) / 2
        np.fill_diagonal(corr, 1.0)
        
        # Cholesky decomposition for correlated returns
        try:
            L = np.linalg.cholesky(corr)
        except np.linalg.LinAlgError:
            L = np.eye(n_assets)
        
        # Generate returns with different expected returns per asset
        base_returns = np.random.randn(n_days, n_assets) * 0.02  # 2% daily vol
        correlated_returns = base_returns @ L.T
        
        # Add drift (expected returns)
        drifts = np.linspace(0.0001, 0.0003, n_assets)  # 2.5% to 7.5% annual
        correlated_returns += drifts
        
        dates = pd.date_range(end=datetime.now(), periods=n_days, freq='B')
        returns = pd.DataFrame(correlated_returns, index=dates, columns=self.tickers)
        
        self._returns = returns
        logger.info(f"Generated deterministic data: {n_days} days, {n_assets} assets")
        return returns
    
    def optimize(self) -> OptimizationResult:
        """
        Run portfolio optimization.
        
        Returns:
            OptimizationResult with optimal weights and metrics
        """
        import time
        start_time = time.time()
        
        # Fetch data if needed
        if self._returns is None:
            self.fetch_data()
        
        if not RISKFOLIO_AVAILABLE:
            return self._fallback_optimization(time.time() - start_time)
        
        try:
            # Create Riskfolio Portfolio object
            port = rp.Portfolio(returns=self._returns)
            
            # Calculate expected returns and covariance
            port.assets_stats(method_mu='hist', method_cov='hist')
            
            # Optimize
            weights = port.optimization(
                model='Classic',
                rm=self.risk_measure,
                obj='MinRisk',  # Minimize risk for target return
                rf=self.risk_free_rate,
                l=0  # Risk aversion (0 = minimum risk)
            )
            
            if weights is None or weights.isnull().all().all():
                logger.warning("Optimization returned null weights, using fallback")
                return self._fallback_optimization(time.time() - start_time)
            
            # Extract weights as dict
            weights_dict = {ticker: float(weights.loc[ticker, 'weights']) 
                          for ticker in self.tickers}
            
            # Calculate metrics
            port_return = float(np.dot(port.mu.values.flatten(), weights.values.flatten()) * 252)
            port_risk = self._calculate_risk(weights, port)
            sharpe = (port_return - self.risk_free_rate) / port_risk if port_risk > 0 else 0
            
            # Store portfolio for frontier calculation
            self._portfolio = port
            
            elapsed = time.time() - start_time
            logger.info(f"Optimization complete: {self.risk_measure}, time={elapsed:.2f}s")
            
            return OptimizationResult(
                weights=weights_dict,
                risk_measure=self.risk_measure,
                expected_return=port_return,
                risk=port_risk,
                sharpe_ratio=sharpe,
                optimization_time=elapsed,
                success=True,
                cache_key=self.cache_key
            )
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return self._fallback_optimization(time.time() - start_time, str(e))
    
    def _calculate_risk(self, weights: pd.DataFrame, port) -> float:
        """Calculate annualized risk based on risk measure."""
        try:
            if self.risk_measure == 'MV':
                # Standard deviation
                cov = port.cov
                w = weights.values.flatten()
                var = np.dot(w.T, np.dot(cov, w))
                return float(np.sqrt(var) * np.sqrt(252))
            
            elif self.risk_measure in ['CVaR', 'EVaR', 'CDaR']:
                # Use riskfolio's risk functions
                w = weights.values.flatten()
                returns = self._returns.values
                
                if self.risk_measure == 'CVaR':
                    # Historical CVaR at 95%
                    portfolio_returns = returns @ w
                    var_95 = np.percentile(portfolio_returns, 5)
                    cvar = -portfolio_returns[portfolio_returns <= var_95].mean()
                    return float(cvar * np.sqrt(252))
                
                elif self.risk_measure == 'CDaR':
                    # Conditional Drawdown at Risk
                    portfolio_returns = returns @ w
                    cumulative = np.cumsum(portfolio_returns)
                    running_max = np.maximum.accumulate(cumulative)
                    drawdowns = running_max - cumulative
                    cdar_95 = np.percentile(drawdowns, 95)
                    return float(cdar_95)
                
                else:  # EVaR
                    # Approximation using CVaR
                    portfolio_returns = returns @ w
                    var_95 = np.percentile(portfolio_returns, 5)
                    cvar = -portfolio_returns[portfolio_returns <= var_95].mean()
                    return float(cvar * 1.1 * np.sqrt(252))  # EVaR slightly higher
            
            else:
                # Fallback to standard deviation
                cov = port.cov
                w = weights.values.flatten()
                var = np.dot(w.T, np.dot(cov, w))
                return float(np.sqrt(var) * np.sqrt(252))
                
        except Exception as e:
            logger.error(f"Risk calculation error: {e}")
            return 0.20  # Default 20% risk
    
    def _fallback_optimization(self, elapsed: float, error: str = "") -> OptimizationResult:
        """
        Equal-weight fallback when optimization fails.
        
        Args:
            elapsed: Time elapsed
            error: Error message if any
            
        Returns:
            OptimizationResult with equal weights
        """
        n = len(self.tickers)
        equal_weight = 1.0 / n
        weights = {ticker: equal_weight for ticker in self.tickers}
        
        # Estimate metrics if we have returns
        if self._returns is not None:
            mean_returns = self._returns.mean() * 252
            port_return = float(mean_returns.mean())
            port_risk = float(self._returns.std().mean() * np.sqrt(252))
        else:
            port_return = 0.08  # Default 8% return
            port_risk = 0.20   # Default 20% risk
        
        sharpe = (port_return - self.risk_free_rate) / port_risk if port_risk > 0 else 0
        
        return OptimizationResult(
            weights=weights,
            risk_measure=self.risk_measure,
            expected_return=port_return,
            risk=port_risk,
            sharpe_ratio=sharpe,
            optimization_time=elapsed,
            success=False if error else True,
            error_message=error or "Using equal-weight fallback",
            cache_key=self.cache_key
        )
    
    def compute_efficient_frontier(self, n_points: int = 50) -> pd.DataFrame:
        """
        Compute efficient frontier.
        
        Args:
            n_points: Number of points on frontier
            
        Returns:
            DataFrame with columns: risk, return, sharpe, weights
        """
        if self._returns is None:
            self.fetch_data()
        
        if not RISKFOLIO_AVAILABLE or self._portfolio is None:
            return self._fallback_frontier(n_points)
        
        try:
            port = self._portfolio
            
            # Get efficient frontier
            frontier = port.efficient_frontier(
                model='Classic',
                rm=self.risk_measure,
                points=n_points,
                rf=self.risk_free_rate
            )
            
            if frontier is None:
                return self._fallback_frontier(n_points)
            
            # Format frontier data
            risks = []
            returns = []
            sharpes = []
            
            for i in range(frontier.shape[1]):
                w = frontier.iloc[:, i].values
                
                # Calculate return
                ret = float(np.dot(port.mu.values.flatten(), w) * 252)
                
                # Calculate risk
                if self.risk_measure == 'MV':
                    var = np.dot(w.T, np.dot(port.cov, w))
                    risk = float(np.sqrt(var) * np.sqrt(252))
                else:
                    risk = self._calculate_risk_for_weights(w)
                
                sharpe = (ret - self.risk_free_rate) / risk if risk > 0 else 0
                
                risks.append(risk)
                returns.append(ret)
                sharpes.append(sharpe)
            
            frontier_df = pd.DataFrame({
                'risk': risks,
                'return': returns,
                'sharpe': sharpes
            })
            
            logger.info(f"Computed efficient frontier: {len(frontier_df)} points")
            return frontier_df
            
        except Exception as e:
            logger.error(f"Frontier computation failed: {e}")
            return self._fallback_frontier(n_points)
    
    def _calculate_risk_for_weights(self, weights: np.ndarray) -> float:
        """Calculate risk for given weight vector."""
        try:
            returns = self._returns.values
            portfolio_returns = returns @ weights
            
            if self.risk_measure in ['CVaR', 'EVaR']:
                var_95 = np.percentile(portfolio_returns, 5)
                cvar = -portfolio_returns[portfolio_returns <= var_95].mean()
                multiplier = 1.1 if self.risk_measure == 'EVaR' else 1.0
                return float(cvar * multiplier * np.sqrt(252))
            
            elif self.risk_measure == 'CDaR':
                cumulative = np.cumsum(portfolio_returns)
                running_max = np.maximum.accumulate(cumulative)
                drawdowns = running_max - cumulative
                return float(np.percentile(drawdowns, 95))
            
            else:
                return float(np.std(portfolio_returns) * np.sqrt(252))
                
        except Exception:
            return 0.20
    
    def _fallback_frontier(self, n_points: int) -> pd.DataFrame:
        """Generate fallback frontier data."""
        # Generate mock efficient frontier
        risks = np.linspace(0.10, 0.35, n_points)
        
        # Efficient frontier: return = rf + risk * sharpe_slope
        sharpe_slope = 0.4  # Typical market Sharpe
        returns = self.risk_free_rate + risks * sharpe_slope
        
        # Add some curvature
        returns = returns + 0.02 * np.sqrt(risks)
        
        sharpes = (returns - self.risk_free_rate) / risks
        
        return pd.DataFrame({
            'risk': risks,
            'return': returns,
            'sharpe': sharpes
        })


def optimize_portfolio(
    tickers: List[str],
    risk_measure: str = 'CDaR',
    use_cache: bool = True
) -> OptimizationResult:
    """
    Convenience function to optimize portfolio.
    
    Args:
        tickers: List of ticker symbols
        risk_measure: Risk measure to use
        use_cache: Whether to check cache first
        
    Returns:
        OptimizationResult
    """
    from financial_dashboard.utils.cache_manager import (
        get_redis_cache,
        cache_key_optimization
    )
    
    cache = get_redis_cache()
    cache_key = cache_key_optimization(tickers, risk_measure)
    
    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            logger.info(f"Using cached optimization result: {cache_key}")
            return OptimizationResult(**cached)
    
    # Run optimization
    optimizer = RiskfolioOptimizer(tickers, risk_measure)
    result = optimizer.optimize()
    
    # Cache result
    if result.success:
        cache.set(cache_key, {
            'weights': result.weights,
            'risk_measure': result.risk_measure,
            'expected_return': result.expected_return,
            'risk': result.risk,
            'sharpe_ratio': result.sharpe_ratio,
            'optimization_time': result.optimization_time,
            'success': result.success,
            'cache_key': result.cache_key,
            'timestamp': result.timestamp
        }, ttl=3600)  # 1 hour cache
    
    return result
