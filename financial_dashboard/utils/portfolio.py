"""
Phase 4: Advanced Portfolio Analytics Module

Provides:
1. Portfolio Optimization (Mean-Variance, Risk Parity, Maximum Sharpe)
2. Risk Metrics (VaR, CVaR, Max Drawdown, Sharpe, Sortino)
3. Backtesting Engine (Historical performance simulation)
4. Advanced Analytics (Factor exposure, correlation analysis)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy.optimize import minimize
import logging

logger = logging.getLogger(__name__)


class PortfolioOptimizer:
    """Portfolio optimization using various strategies."""
    
    def __init__(self, tickers, start_date=None, end_date=None, risk_free_rate=0.04):
        """
        Initialize optimizer with ticker list and date range.
        
        Args:
            tickers: List of ticker symbols
            start_date: Start date for historical data (default: 1 year ago)
            end_date: End date for historical data (default: today)
            risk_free_rate: Risk-free rate for Sharpe ratio (default: 4%)
        """
        self.tickers = tickers
        self.risk_free_rate = risk_free_rate
        
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365)
        
        self.start_date = start_date
        self.end_date = end_date
        
        # Fetch data using Alpaca/Finnhub instead of yfinance
        self.prices = self._fetch_prices()
        
        # Update tickers list to only include those with valid data
        self.tickers = list(self.prices.columns)
        
        if len(self.tickers) < 2:
            logger.error(f"Insufficient valid tickers after data fetch: {len(self.tickers)}")
            self.returns = pd.DataFrame()
            self.mean_returns = pd.Series(dtype=float)
            self.cov_matrix = pd.DataFrame()
            self.optimization_status = 'insufficient_data'
        else:
            self.returns = self.prices.pct_change().dropna()
            
            # Clean returns: remove NaN, inf values
            self.returns = self._clean_returns(self.returns)
            
            # Calculate statistics
            self.mean_returns = self.returns.mean() * 252  # Annualized
            self.cov_matrix = self.returns.cov() * 252  # Annualized
            
            # Check for singular/problematic covariance matrix
            self.optimization_status = self._validate_covariance()
    
    def _clean_returns(self, returns):
        """
        Clean return series by removing NaN and inf values.
        
        Args:
            returns: DataFrame of returns
        
        Returns:
            Cleaned DataFrame
        """
        # Replace inf with NaN
        returns = returns.replace([np.inf, -np.inf], np.nan)
        
        # Drop rows with any NaN
        initial_len = len(returns)
        returns = returns.dropna()
        dropped = initial_len - len(returns)
        
        if dropped > 0:
            logger.warning(f"⚠️ Dropped {dropped} rows with NaN/inf values from returns")
        
        # If too few observations remain, interpolate
        if len(returns) < 30:
            logger.warning(f"⚠️ Only {len(returns)} observations after cleaning - insufficient for optimization")
        
        return returns
    
    def _validate_covariance(self):
        """
        Validate covariance matrix and determine if fallback is needed.
        
        Returns:
            Status string: 'healthy', 'singular', 'needs_shrinkage'
        """
        try:
            # Check if matrix is singular by attempting Cholesky decomposition
            np.linalg.cholesky(self.cov_matrix)
            logger.info("✓ Covariance matrix is positive definite")
            return 'healthy'
        except np.linalg.LinAlgError:
            logger.warning("⚠️ Covariance matrix is singular - will use Ledoit-Wolf shrinkage")
            return 'needs_shrinkage'
    
    def _get_regularized_covariance(self):
        """
        Apply Ledoit-Wolf shrinkage to regularize covariance matrix.
        
        Returns:
            Regularized covariance matrix
        """
        try:
            from sklearn.covariance import ledoit_wolf
            
            logger.info("📊 Applying Ledoit-Wolf shrinkage to covariance matrix...")
            shrunk_cov, _ = ledoit_wolf(self.returns)
            
            # Annualize the shrunk covariance
            shrunk_cov = shrunk_cov * 252
            
            logger.info("✓ Successfully applied covariance shrinkage")
            return pd.DataFrame(shrunk_cov, index=self.cov_matrix.index, columns=self.cov_matrix.columns)
        
        except Exception as e:
            logger.error(f"❌ Ledoit-Wolf shrinkage failed: {e}")
            # Ultimate fallback: return diagonal covariance (assumes zero correlation)
            logger.warning("⚠️ Using diagonal covariance as fallback")
            return pd.DataFrame(np.diag(np.diag(self.cov_matrix)), 
                               index=self.cov_matrix.index, 
                               columns=self.cov_matrix.columns)
    
    def _fetch_prices(self):
        """Fetch historical prices for all tickers using Alpaca/Finnhub."""
        try:
            from utils.price_fetch import fetch_historical_data
            
            logger.info(f"Fetching historical data for {len(self.tickers)} tickers using Alpaca/Finnhub")
            data = fetch_historical_data(self.tickers, self.start_date, self.end_date, use_alpaca=True)
            
            if data.empty:
                logger.error("No historical data retrieved for any ticker")
                return pd.DataFrame()
            
            logger.info(f"Successfully fetched data for {len(data.columns)} tickers ({len(data)} days)")
            return data
        except Exception as e:
            logger.error(f"Error fetching prices: {e}", exc_info=True)
            return pd.DataFrame()
    
    def optimize_sharpe(self, constraints=None):
        """
        Optimize portfolio for maximum Sharpe ratio with robust fallback logic.
        
        Fallback sequence:
        1. Try with original covariance matrix
        2. If singular, apply Ledoit-Wolf shrinkage
        3. If still fails, return equal weights
        
        Returns:
            dict with weights, expected_return, volatility, sharpe_ratio, optimization_status
        """
        n_assets = len(self.tickers)
        
        # Check if we have sufficient data
        if n_assets < 2:
            logger.error("❌ Need at least 2 tickers for optimization")
            return self._fallback_equal_weight(reason="insufficient_tickers")
        
        # PHASE 6 FIX: Enhanced data sufficiency check with actionable guidance
        min_observations = 30
        if len(self.returns) < min_observations:
            logger.warning(f"⚠️ Only {len(self.returns)} observations (need {min_observations})")
            logger.info(f"💡 Recommendation: Extend date range to get more historical data")
            logger.info(f"   Current period: {self.start_date} to {self.end_date}")
            
            # Calculate recommended lookback
            days_missing = min_observations - len(self.returns)
            from datetime import timedelta
            
            if isinstance(self.start_date, str):
                from datetime import datetime
                current_start = datetime.strptime(self.start_date, '%Y-%m-%d')
            else:
                current_start = self.start_date
            
            recommended_start = current_start - timedelta(days=days_missing + 10)  # +10 buffer for weekends
            logger.info(f"   Recommended start: {recommended_start.strftime('%Y-%m-%d')}")
            
            # If we have at least 20 observations, try optimization with warning
            if len(self.returns) >= 20:
                logger.info("✓ Proceeding with optimization (20+ observations available, but results may be less stable)")
            else:
                logger.warning("❌ <20 observations - falling back to equal weights for safety")
                return self._fallback_equal_weight(reason=f"insufficient_data_{len(self.returns)}_obs")
        
        # Determine which covariance matrix to use
        cov_to_use = self.cov_matrix
        if self.optimization_status == 'needs_shrinkage':
            cov_to_use = self._get_regularized_covariance()
        
        def neg_sharpe(weights):
            portfolio_return = np.sum(self.mean_returns * weights)
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_to_use, weights)))
            
            # Avoid division by zero
            if portfolio_vol < 1e-10:
                return 1e10
            
            return -(portfolio_return - self.risk_free_rate) / portfolio_vol
        
        # Constraints: weights sum to 1
        cons = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        
        # Bounds: 0 <= weight <= 0.4 (max 40% in any single asset)
        bounds = tuple((0, 0.4) for _ in range(n_assets))
        
        # Initial guess: equal weights
        init_guess = np.array([1/n_assets] * n_assets)
        
        try:
            result = minimize(neg_sharpe, init_guess, method='SLSQP', bounds=bounds, constraints=cons)
            
            if result.success:
                weights = result.x
                portfolio_return = np.sum(self.mean_returns * weights)
                portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_to_use, weights)))
                
                # Avoid division by zero in Sharpe calculation
                if portfolio_vol < 1e-10:
                    logger.warning("⚠️ Portfolio volatility near zero - using equal weights")
                    return self._fallback_equal_weight(reason="zero_volatility")
                
                sharpe = (portfolio_return - self.risk_free_rate) / portfolio_vol
                
                opt_status = 'success'
                if self.optimization_status == 'needs_shrinkage':
                    opt_status = 'success_with_shrinkage'
                
                logger.info(f"✓ Optimization successful (status: {opt_status})")
                
                return {
                    'weights': {ticker: float(w) for ticker, w in zip(self.tickers, weights)},
                    'expected_return': float(portfolio_return),
                    'volatility': float(portfolio_vol),
                    'sharpe_ratio': float(sharpe),
                    'optimization': 'Maximum Sharpe',
                    'optimization_status': opt_status
                }
            else:
                logger.warning(f"⚠️ Optimization did not converge: {result.message}")
                return self._fallback_equal_weight(reason=f"optimization_failed: {result.message}")
        
        except Exception as e:
            logger.error(f"❌ Optimization error: {e}", exc_info=True)
            return self._fallback_equal_weight(reason=f"exception: {str(e)}")
    
    def _fallback_equal_weight(self, reason: str = "unknown"):
        """
        Fallback to equal-weighted portfolio when optimization fails.
        
        Args:
            reason: Reason for fallback (for logging/status)
        
        Returns:
            dict with equal weights and computed metrics
        """
        logger.info(f"📊 Falling back to equal weights (reason: {reason})")
        
        n = len(self.tickers)
        if n == 0:
            return None
        
        weights = {t: 1/n for t in self.tickers}
        weights_array = np.array(list(weights.values()))
        
        expected_return = float(np.sum(self.mean_returns * weights_array))
        
        # Calculate volatility only if covariance matrix is valid
        volatility = 0.0
        if self.cov_matrix is not None and self.cov_matrix.size > 0:
            # Use regularized covariance if needed
            cov_to_use = self.cov_matrix
            if self.optimization_status == 'needs_shrinkage':
                cov_to_use = self._get_regularized_covariance()
            
            try:
                volatility = float(np.sqrt(np.dot(weights_array.T, np.dot(cov_to_use, weights_array))))
            except (ValueError, np.linalg.LinAlgError) as e:
                logger.warning(f"⚠️ Could not compute volatility in fallback: {e}")
                volatility = 0.0
        
        sharpe_ratio = 0.0
        if volatility > 1e-10:
            sharpe_ratio = (expected_return - self.risk_free_rate) / volatility
        
        return {
            'weights': weights,
            'expected_return': expected_return,
            'volatility': volatility,
            'sharpe_ratio': float(sharpe_ratio),
            'optimization': 'Equal Weight (Fallback)',
            'optimization_status': f'fallback_{reason}'
        }
    
    # Backwards-compatibility / convenience wrapper expected by UI
    def maximize_sharpe(self, *args, **kwargs):
        """Compatibility wrapper for optimize_sharpe used by the dashboard."""
        return self.optimize_sharpe(*args, **kwargs)

    def minimize_volatility(self, *args, **kwargs):
        """Compatibility wrapper mapping to optimize_min_variance."""
        return self.optimize_min_variance(*args, **kwargs)

    def maximize_return(self, *args, **kwargs):
        """Simple maximization of expected return subject to constraints (bounds + weights sum to 1)."""
        # Maximize return is equivalent to optimizing for max expected return with given bounds
        n_assets = len(self.tickers)
        cons = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0, 0.4) for _ in range(n_assets))
        init_guess = np.array([1/n_assets] * n_assets)

        def neg_return(weights):
            return -np.sum(self.mean_returns * weights)

        result = minimize(neg_return, init_guess, method='SLSQP', bounds=bounds, constraints=cons)
        if result.success:
            weights = result.x
            portfolio_return = np.sum(self.mean_returns * weights)
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))
            return {
                'weights': {ticker: float(w) for ticker, w in zip(self.tickers, weights)},
                'expected_return': float(portfolio_return),
                'volatility': float(portfolio_vol),
                'optimization': 'Maximize Return'
            }
        logger.error(f"Maximize return optimization failed: {result.message}")
        return None

    def equal_weight(self):
        """Return equal-weighted portfolio result."""
        n = len(self.tickers)
        weights = {t: 1/n for t in self.tickers}
        expected_return = float(np.sum(self.mean_returns * np.array(list(weights.values()))))
        volatility = float(np.sqrt(np.dot(np.array(list(weights.values())).T, np.dot(self.cov_matrix, np.array(list(weights.values()))))))
        return {
            'weights': weights,
            'expected_return': expected_return,
            'volatility': volatility,
            'optimization': 'Equal Weight'
        }

    def efficient_frontier(self, num_points=50):
        """Generate points on the efficient frontier (returns, volatility) for plotting.

        Returns dict with keys 'return' and 'volatility' (lists).
        """
        n = len(self.tickers)
        results_return = []
        results_vol = []
        # Grid search over target returns between min and max mean returns
        min_r, max_r = float(np.min(self.mean_returns)), float(np.max(self.mean_returns))
        target_returns = np.linspace(min_r, max_r, num_points)
        cons = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1},)
        bounds = tuple((0, 0.4) for _ in range(n))
        for targ in target_returns:
            def variance_with_target(weights):
                # Penalize deviation from target return
                port_ret = np.sum(self.mean_returns * weights)
                var = np.dot(weights.T, np.dot(self.cov_matrix, weights))
                # Penalize return difference strongly
                return var + 1000 * (port_ret - targ) ** 2

            init = np.array([1/n] * n)
            res = minimize(variance_with_target, init, method='SLSQP', bounds=bounds, constraints=cons)
            if res.success:
                w = res.x
                port_ret = float(np.sum(self.mean_returns * w))
                port_vol = float(np.sqrt(np.dot(w.T, np.dot(self.cov_matrix, w))))
                results_return.append(port_ret)
                results_vol.append(port_vol)
        if results_return and results_vol:
            return {'return': results_return, 'volatility': results_vol}
        return None
    
    def optimize_min_variance(self):
        """
        Optimize portfolio for minimum variance with robust fallback handling.
        
        Returns:
            dict with weights, expected_return, volatility, optimization_status
        """
        n_assets = len(self.tickers)
        
        # Early fallback if insufficient assets
        if n_assets < 2:
            logger.warning(f"⚠️ Only {n_assets} asset(s) - cannot optimize minimum variance")
            return self._fallback_equal_weight("insufficient_assets")
        
        # Check data sufficiency
        if len(self.returns) < 30:
            logger.warning(f"⚠️ Only {len(self.returns)} observations - using equal weights fallback")
            return self._fallback_equal_weight("insufficient_data")
        
        # Validate and potentially regularize covariance
        cov_status = self._validate_covariance()
        if cov_status == 'needs_shrinkage':
            self._get_regularized_covariance()
        
        def portfolio_variance(weights):
            return np.dot(weights.T, np.dot(self.cov_matrix, weights))
        
        cons = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0, 0.4) for _ in range(n_assets))
        init_guess = np.array([1/n_assets] * n_assets)
        
        try:
            result = minimize(portfolio_variance, init_guess, method='SLSQP', bounds=bounds, constraints=cons)
            
            if result.success:
                weights = result.x
                portfolio_return = np.sum(self.mean_returns * weights)
                portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))
                
                status = 'success_with_shrinkage' if cov_status == 'needs_shrinkage' else 'success'
                
                return {
                    'weights': {ticker: float(w) for ticker, w in zip(self.tickers, weights)},
                    'expected_return': float(portfolio_return),
                    'volatility': float(portfolio_vol),
                    'optimization': 'Minimum Variance',
                    'optimization_status': status
                }
            else:
                logger.warning(f"⚠️ Min variance optimization did not converge: {result.message}")
                return self._fallback_equal_weight(f"optimization_failed: {result.message}")
                
        except Exception as e:
            logger.error(f"❌ Min variance optimization error: {e}")
            return self._fallback_equal_weight(f"exception: {str(e)}")
        
        return self._fallback_equal_weight("unknown_error")
    
    def risk_parity(self):
        """
        Risk parity portfolio - equal risk contribution from each asset.
        
        Returns:
            dict with weights, expected_return, volatility
        """
        n_assets = len(self.tickers)
        
        def risk_contribution_diff(weights):
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))
            marginal_contrib = np.dot(self.cov_matrix, weights)
            risk_contrib = weights * marginal_contrib / portfolio_vol
            target_risk = portfolio_vol / n_assets
            return np.sum((risk_contrib - target_risk) ** 2)
        
        cons = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0, 1) for _ in range(n_assets))
        init_guess = np.array([1/n_assets] * n_assets)
        
        result = minimize(risk_contribution_diff, init_guess, method='SLSQP', bounds=bounds, constraints=cons)
        
        if result.success:
            weights = result.x
            portfolio_return = np.sum(self.mean_returns * weights)
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))
            
            return {
                'weights': {ticker: float(w) for ticker, w in zip(self.tickers, weights)},
                'expected_return': float(portfolio_return),
                'volatility': float(portfolio_vol),
                'optimization': 'Risk Parity'
            }
        return None


class RiskMetrics:
    """Calculate portfolio risk metrics."""
    
    @staticmethod
    def calculate_var(returns, confidence=0.95):
        """
        Calculate Value at Risk (VaR).
        
        Args:
            returns: Series or array of returns
            confidence: Confidence level (default 95%)
            
        Returns:
            VaR as a positive number (e.g., 0.05 means 5% loss)
        """
        return -np.percentile(returns, (1 - confidence) * 100)
    
    @staticmethod
    def calculate_cvar(returns, confidence=0.95):
        """
        Calculate Conditional Value at Risk (CVaR) / Expected Shortfall.
        
        Args:
            returns: Series or array of returns
            confidence: Confidence level (default 95%)
            
        Returns:
            CVaR as a positive number
        """
        var = RiskMetrics.calculate_var(returns, confidence)
        return -returns[returns <= -var].mean()
    
    @staticmethod
    def calculate_max_drawdown(prices):
        """
        Calculate maximum drawdown.
        
        Args:
            prices: Series of prices
            
        Returns:
            Maximum drawdown as a positive number
        """
        cumulative = (1 + prices.pct_change()).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        return abs(drawdown.min())
    
    @staticmethod
    def calculate_sharpe(returns, risk_free_rate=0.04):
        """
        Calculate Sharpe ratio.
        
        Args:
            returns: Series of returns
            risk_free_rate: Annual risk-free rate
            
        Returns:
            Sharpe ratio
        """
        excess_returns = returns - risk_free_rate / 252
        return np.sqrt(252) * excess_returns.mean() / excess_returns.std()
    
    @staticmethod
    def calculate_sortino(returns, risk_free_rate=0.04):
        """
        Calculate Sortino ratio (uses downside deviation).
        
        Args:
            returns: Series of returns
            risk_free_rate: Annual risk-free rate
            
        Returns:
            Sortino ratio
        """
        excess_returns = returns - risk_free_rate / 252
        downside_returns = returns[returns < 0]
        downside_std = np.sqrt(np.mean(downside_returns ** 2))
        return np.sqrt(252) * excess_returns.mean() / downside_std if downside_std > 0 else 0


class Backtester:
    """Backtest portfolio strategies."""
    
    def __init__(self, tickers, weights, start_date, end_date, rebalance_freq='monthly'):
        """
        Initialize backtester.
        
        Args:
            tickers: List of tickers
            weights: Dict of ticker: weight
            start_date: Backtest start date
            end_date: Backtest end date
            rebalance_freq: 'daily', 'weekly', 'monthly', 'quarterly'
        """
        self.tickers = tickers
        self.weights = weights
        self.start_date = start_date
        self.end_date = end_date
        self.rebalance_freq = rebalance_freq
        
        # Fetch prices
        self.prices = self._fetch_prices()
        self.returns = self.prices.pct_change().dropna()
    
    def _fetch_prices(self):
        """Fetch historical prices using Alpaca/Finnhub."""
        try:
            from utils.price_fetch import fetch_historical_data
            
            logger.info(f"Backtester: Fetching data for {len(self.tickers)} tickers")
            data = fetch_historical_data(self.tickers, self.start_date, self.end_date, use_alpaca=True)
            
            if data.empty:
                logger.error("Backtester: No data retrieved")
                return pd.DataFrame()
            
            return data
        except Exception as e:
            logger.error(f"Error fetching backtest prices: {e}")
            return pd.DataFrame()
    
    def run(self):
        """
        Run backtest simulation.
        
        Returns:
            dict with portfolio_value, returns, metrics
        """
        if self.prices.empty:
            return None
        
        # Calculate portfolio returns
        portfolio_returns = pd.Series(index=self.returns.index, dtype=float)
        
        for date in self.returns.index:
            daily_return = sum(self.weights.get(ticker, 0) * self.returns.loc[date, ticker] 
                             for ticker in self.tickers if ticker in self.returns.columns)
            portfolio_returns[date] = daily_return
        
        # Calculate cumulative value
        portfolio_value = (1 + portfolio_returns).cumprod()
        
        # Calculate metrics
        total_return = portfolio_value.iloc[-1] - 1
        annualized_return = (1 + total_return) ** (252 / len(portfolio_value)) - 1
        annualized_vol = portfolio_returns.std() * np.sqrt(252)
        sharpe = RiskMetrics.calculate_sharpe(portfolio_returns)
        max_dd = RiskMetrics.calculate_max_drawdown(portfolio_value)
        
        return {
            'portfolio_value': portfolio_value.to_dict(),
            'returns': portfolio_returns.to_dict(),
            'metrics': {
                'total_return': float(total_return),
                'annualized_return': float(annualized_return),
                'annualized_volatility': float(annualized_vol),
                'sharpe_ratio': float(sharpe),
                'max_drawdown': float(max_dd),
                'var_95': float(RiskMetrics.calculate_var(portfolio_returns)),
                'cvar_95': float(RiskMetrics.calculate_cvar(portfolio_returns))
            }
        }


def calculate_portfolio_metrics(tickers, weights=None, start_date=None, end_date=None):
    """
    Convenience function to calculate portfolio metrics.
    
    Args:
        tickers: List of tickers
        weights: Dict of weights (default: equal weight)
        start_date: Start date (default: 1 year ago)
        end_date: End date (default: today)
        
    Returns:
        dict with comprehensive metrics
    """
    if weights is None:
        weights = {ticker: 1/len(tickers) for ticker in tickers}
    
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date - timedelta(days=365)
    
    # Fetch data using Alpaca/Finnhub
    try:
        from utils.price_fetch import fetch_historical_data
        
        prices = fetch_historical_data(tickers, start_date, end_date, use_alpaca=True)
        if prices.empty:
            raise ValueError("No historical data available")
        
        returns = prices.pct_change().dropna()
        
        # Calculate portfolio returns
        portfolio_returns = pd.Series(index=returns.index, dtype=float)
        for date in returns.index:
            daily_return = sum(weights.get(ticker, 0) * returns.loc[date, ticker] 
                             for ticker in tickers if ticker in returns.columns)
            portfolio_returns[date] = daily_return
        
        # Calculate metrics
        total_return = (1 + portfolio_returns).prod() - 1
        annualized_return = (1 + total_return) ** (252 / len(portfolio_returns)) - 1
        annualized_vol = portfolio_returns.std() * np.sqrt(252)
        
        return {
            'total_return': float(total_return),
            'annualized_return': float(annualized_return),
            'annualized_volatility': float(annualized_vol),
            'sharpe_ratio': float(RiskMetrics.calculate_sharpe(portfolio_returns)),
            'sortino_ratio': float(RiskMetrics.calculate_sortino(portfolio_returns)),
            'max_drawdown': float(RiskMetrics.calculate_max_drawdown((1 + portfolio_returns).cumprod())),
            'var_95': float(RiskMetrics.calculate_var(portfolio_returns)),
            'cvar_95': float(RiskMetrics.calculate_cvar(portfolio_returns)),
            'best_day': float(portfolio_returns.max()),
            'worst_day': float(portfolio_returns.min()),
            'positive_days': int((portfolio_returns > 0).sum()),
            'negative_days': int((portfolio_returns < 0).sum()),
            'win_rate': float((portfolio_returns > 0).sum() / len(portfolio_returns))
        }
    except Exception as e:
        logger.error(f"Error calculating portfolio metrics: {e}")
        return None
