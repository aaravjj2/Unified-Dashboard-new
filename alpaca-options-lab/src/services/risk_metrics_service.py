"""
Value-at-Risk (VaR) and Risk Metrics Service
Implements #201-230 from ROADMAP_ULTIMATE.md
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from scipy import stats
from scipy.optimize import minimize
import logging

logger = logging.getLogger(__name__)


class RiskMetricsService:
    """
    Comprehensive risk metrics:
    - Value-at-Risk (VaR) - Parametric, Historical, Monte Carlo
    - Expected Shortfall (CVaR)
    - Stress Testing
    - Risk Attribution
    - Portfolio Risk Analysis
    """
    
    TRADING_DAYS = 252
    
    def __init__(self):
        self.risk_free_rate = 0.05
        
    def calculate_var_parametric(self, returns: pd.Series, 
                                confidence: float = 0.95,
                                horizon: int = 1,
                                portfolio_value: float = 1.0) -> Dict[str, float]:
        """
        Parametric (Variance-Covariance) VaR
        Assumes normal distribution
        """
        mu = returns.mean()
        sigma = returns.std()
        
        # Z-score for confidence level
        z = stats.norm.ppf(1 - confidence)
        
        # VaR for single period
        var_1d = -(mu + z * sigma)
        
        # Scale to horizon (square-root of time)
        var_horizon = var_1d * np.sqrt(horizon)
        
        # Dollar VaR
        dollar_var = var_horizon * portfolio_value
        
        return {
            'var_pct': var_horizon,
            'var_dollar': dollar_var,
            'confidence': confidence,
            'horizon_days': horizon,
            'method': 'parametric',
            'mean_return': mu,
            'volatility': sigma,
            'annualized_vol': sigma * np.sqrt(self.TRADING_DAYS)
        }
    
    def calculate_var_historical(self, returns: pd.Series,
                                confidence: float = 0.95,
                                horizon: int = 1,
                                portfolio_value: float = 1.0) -> Dict[str, float]:
        """
        Historical Simulation VaR
        Uses actual return distribution
        """
        # Sort returns
        sorted_returns = returns.sort_values()
        
        # Find percentile
        var_pct = np.percentile(returns, (1 - confidence) * 100)
        
        # Scale to horizon
        var_horizon = var_pct * np.sqrt(horizon)
        
        # Dollar VaR
        dollar_var = abs(var_horizon) * portfolio_value
        
        return {
            'var_pct': abs(var_horizon),
            'var_dollar': dollar_var,
            'confidence': confidence,
            'horizon_days': horizon,
            'method': 'historical',
            'worst_return': sorted_returns.iloc[0],
            'percentile_5': np.percentile(returns, 5),
            'percentile_1': np.percentile(returns, 1)
        }
    
    def calculate_var_monte_carlo(self, returns: pd.Series,
                                 confidence: float = 0.95,
                                 horizon: int = 1,
                                 portfolio_value: float = 1.0,
                                 n_sims: int = 10000) -> Dict[str, float]:
        """
        Monte Carlo VaR
        Simulates future returns
        """
        mu = returns.mean()
        sigma = returns.std()
        
        # Simulate returns
        simulated_returns = np.random.normal(mu * horizon, 
                                            sigma * np.sqrt(horizon), 
                                            n_sims)
        
        # Sort simulated returns
        sorted_sims = np.sort(simulated_returns)
        
        # Find VaR
        var_idx = int((1 - confidence) * n_sims)
        var_pct = abs(sorted_sims[var_idx])
        
        # Dollar VaR
        dollar_var = var_pct * portfolio_value
        
        return {
            'var_pct': var_pct,
            'var_dollar': dollar_var,
            'confidence': confidence,
            'horizon_days': horizon,
            'method': 'monte_carlo',
            'simulations': n_sims,
            'sim_mean': np.mean(simulated_returns),
            'sim_std': np.std(simulated_returns)
        }
    
    def calculate_cvar(self, returns: pd.Series,
                      confidence: float = 0.95,
                      portfolio_value: float = 1.0) -> Dict[str, float]:
        """
        Conditional VaR (Expected Shortfall)
        Average loss beyond VaR
        """
        var_result = self.calculate_var_historical(returns, confidence)
        var_pct = var_result['var_pct']
        
        # CVaR: average of returns worse than VaR
        tail_returns = returns[returns <= -var_pct]
        cvar_pct = abs(tail_returns.mean()) if len(tail_returns) > 0 else var_pct
        
        return {
            'cvar_pct': cvar_pct,
            'cvar_dollar': cvar_pct * portfolio_value,
            'var_pct': var_pct,
            'var_dollar': var_pct * portfolio_value,
            'confidence': confidence,
            'tail_events': len(tail_returns),
            'cvar_var_ratio': cvar_pct / var_pct if var_pct > 0 else 1
        }
    
    def calculate_drawdown(self, prices: pd.Series) -> Dict[str, Any]:
        """
        Calculate drawdown metrics
        """
        # Running maximum
        running_max = prices.cummax()
        
        # Drawdown series
        drawdown = (prices - running_max) / running_max
        
        # Maximum drawdown
        max_dd = drawdown.min()
        max_dd_idx = drawdown.idxmin()
        
        # Find peak before max drawdown
        peak_idx = prices[:max_dd_idx].idxmax()
        
        # Find recovery (if any)
        recovery_idx = None
        if max_dd_idx < prices.index[-1]:
            post_dd = prices[max_dd_idx:]
            recovery_mask = post_dd >= running_max[max_dd_idx]
            if recovery_mask.any():
                recovery_idx = recovery_mask.idxmax()
        
        # Drawdown duration
        if recovery_idx:
            dd_duration = (recovery_idx - peak_idx).days
        else:
            dd_duration = (prices.index[-1] - peak_idx).days
            
        # Average drawdown
        avg_dd = drawdown.mean()
        
        # Calmar ratio
        returns = prices.pct_change().dropna()
        annual_return = returns.mean() * self.TRADING_DAYS
        calmar = annual_return / abs(max_dd) if max_dd != 0 else 0
        
        return {
            'max_drawdown': max_dd,
            'max_drawdown_pct': f"{max_dd:.2%}",
            'peak_date': peak_idx,
            'trough_date': max_dd_idx,
            'recovery_date': recovery_idx,
            'drawdown_duration_days': dd_duration,
            'average_drawdown': avg_dd,
            'calmar_ratio': calmar,
            'drawdown_series': drawdown
        }
    
    def calculate_sharpe_ratio(self, returns: pd.Series,
                              risk_free_rate: float = None) -> float:
        """Calculate Sharpe Ratio"""
        if risk_free_rate is None:
            risk_free_rate = self.risk_free_rate
            
        excess_returns = returns - risk_free_rate / self.TRADING_DAYS
        
        if returns.std() == 0:
            return 0
            
        return (excess_returns.mean() / returns.std()) * np.sqrt(self.TRADING_DAYS)
    
    def calculate_sortino_ratio(self, returns: pd.Series,
                               risk_free_rate: float = None,
                               target: float = 0) -> float:
        """Calculate Sortino Ratio (downside risk adjusted)"""
        if risk_free_rate is None:
            risk_free_rate = self.risk_free_rate
            
        excess_returns = returns.mean() - risk_free_rate / self.TRADING_DAYS
        
        # Downside deviation
        downside_returns = returns[returns < target]
        downside_std = np.sqrt(np.mean(downside_returns ** 2)) if len(downside_returns) > 0 else returns.std()
        
        if downside_std == 0:
            return 0
            
        return (excess_returns / downside_std) * np.sqrt(self.TRADING_DAYS)
    
    def calculate_information_ratio(self, returns: pd.Series,
                                   benchmark_returns: pd.Series) -> float:
        """Calculate Information Ratio"""
        active_returns = returns - benchmark_returns
        tracking_error = active_returns.std() * np.sqrt(self.TRADING_DAYS)
        
        if tracking_error == 0:
            return 0
            
        return (active_returns.mean() * self.TRADING_DAYS) / tracking_error
    
    def calculate_all_ratios(self, returns: pd.Series,
                            benchmark_returns: pd.Series = None,
                            risk_free_rate: float = None) -> Dict[str, float]:
        """Calculate all performance ratios"""
        if risk_free_rate is None:
            risk_free_rate = self.risk_free_rate
            
        sharpe = self.calculate_sharpe_ratio(returns, risk_free_rate)
        sortino = self.calculate_sortino_ratio(returns, risk_free_rate)
        
        # Annualized metrics
        annual_return = returns.mean() * self.TRADING_DAYS
        annual_vol = returns.std() * np.sqrt(self.TRADING_DAYS)
        
        # Higher moments
        skewness = returns.skew()
        kurtosis = returns.kurtosis()
        
        result = {
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'annual_return': annual_return,
            'annual_volatility': annual_vol,
            'skewness': skewness,
            'kurtosis': kurtosis,
            'positive_days_pct': (returns > 0).mean(),
            'best_day': returns.max(),
            'worst_day': returns.min()
        }
        
        if benchmark_returns is not None:
            result['information_ratio'] = self.calculate_information_ratio(
                returns, benchmark_returns
            )
            result['beta'] = returns.cov(benchmark_returns) / benchmark_returns.var()
            result['alpha'] = annual_return - result['beta'] * (
                benchmark_returns.mean() * self.TRADING_DAYS
            )
            result['treynor_ratio'] = (annual_return - risk_free_rate) / result['beta'] if result['beta'] != 0 else 0
        
        return result
    
    def stress_test(self, returns: pd.Series,
                   scenarios: Dict[str, float] = None) -> Dict[str, Any]:
        """
        Run stress test scenarios
        """
        if scenarios is None:
            # Default scenarios
            scenarios = {
                '2008 GFC': -0.40,
                '2020 COVID': -0.34,
                '1987 Black Monday': -0.22,
                'Flash Crash': -0.10,
                '10% Decline': -0.10,
                '20% Decline': -0.20,
                '30% Decline': -0.30,
                '50% Decline': -0.50
            }
        
        current_vol = returns.std() * np.sqrt(self.TRADING_DAYS)
        
        results = {}
        for scenario_name, shock in scenarios.items():
            # Calculate stressed return distribution
            stressed_return = shock
            vol_multiplier = abs(shock) / 0.20  # Scale vol with shock
            stressed_vol = current_vol * max(vol_multiplier, 1)
            
            results[scenario_name] = {
                'shock': shock,
                'portfolio_impact_pct': shock,
                'stressed_volatility': stressed_vol,
                'expected_recovery_days': int(abs(shock) * 500)  # Rough estimate
            }
        
        return {
            'scenarios': results,
            'current_volatility': current_vol,
            'worst_historical': returns.min(),
            'worst_scenario': min(scenarios.values())
        }
    
    def correlation_stress_test(self, returns_df: pd.DataFrame,
                               correlation_shock: float = 0.3) -> Dict[str, Any]:
        """
        Test portfolio under stressed correlations
        """
        # Current correlation
        current_corr = returns_df.corr()
        
        # Stressed correlation (move towards 1)
        stressed_corr = current_corr + correlation_shock * (1 - current_corr)
        
        # Calculate portfolio variance under both
        n = len(returns_df.columns)
        equal_weights = np.ones(n) / n
        vols = returns_df.std().values
        
        # Current portfolio vol
        current_port_var = np.dot(equal_weights, 
                                  np.dot(current_corr.values * np.outer(vols, vols), 
                                        equal_weights))
        current_port_vol = np.sqrt(current_port_var) * np.sqrt(self.TRADING_DAYS)
        
        # Stressed portfolio vol
        stressed_port_var = np.dot(equal_weights,
                                   np.dot(stressed_corr.values * np.outer(vols, vols),
                                         equal_weights))
        stressed_port_vol = np.sqrt(stressed_port_var) * np.sqrt(self.TRADING_DAYS)
        
        return {
            'current_correlation_avg': current_corr.values[np.triu_indices(n, 1)].mean(),
            'stressed_correlation_avg': stressed_corr.values[np.triu_indices(n, 1)].mean(),
            'current_portfolio_vol': current_port_vol,
            'stressed_portfolio_vol': stressed_port_vol,
            'vol_increase_pct': (stressed_port_vol / current_port_vol - 1) * 100,
            'correlation_shock': correlation_shock
        }
    
    def calculate_component_var(self, returns_df: pd.DataFrame,
                               weights: np.ndarray,
                               confidence: float = 0.95) -> Dict[str, Any]:
        """
        Calculate component VaR (marginal risk contribution)
        """
        n = len(weights)
        cov_matrix = returns_df.cov().values
        
        # Portfolio variance
        port_var = np.dot(weights, np.dot(cov_matrix, weights))
        port_std = np.sqrt(port_var)
        
        # Z-score
        z = stats.norm.ppf(1 - confidence)
        
        # Portfolio VaR
        port_var_value = -z * port_std
        
        # Marginal VaR
        marginal_var = np.dot(cov_matrix, weights) / port_std * (-z)
        
        # Component VaR
        component_var = weights * marginal_var
        
        # Percentage contribution
        var_contribution = component_var / port_var_value * 100
        
        return {
            'portfolio_var': port_var_value,
            'portfolio_std': port_std,
            'marginal_var': dict(zip(returns_df.columns, marginal_var)),
            'component_var': dict(zip(returns_df.columns, component_var)),
            'var_contribution_pct': dict(zip(returns_df.columns, var_contribution)),
            'confidence': confidence
        }
    
    def get_risk_report(self, prices: pd.Series,
                       returns: pd.Series = None,
                       portfolio_value: float = 100000,
                       benchmark_returns: pd.Series = None) -> Dict[str, Any]:
        """Generate comprehensive risk report"""
        if returns is None:
            returns = prices.pct_change().dropna()
        
        # VaR calculations
        var_95_param = self.calculate_var_parametric(returns, 0.95, 1, portfolio_value)
        var_99_param = self.calculate_var_parametric(returns, 0.99, 1, portfolio_value)
        var_95_hist = self.calculate_var_historical(returns, 0.95, 1, portfolio_value)
        var_95_mc = self.calculate_var_monte_carlo(returns, 0.95, 1, portfolio_value)
        
        # CVaR
        cvar = self.calculate_cvar(returns, 0.95, portfolio_value)
        
        # Drawdown
        drawdown = self.calculate_drawdown(prices)
        
        # Ratios
        ratios = self.calculate_all_ratios(returns, benchmark_returns)
        
        # Stress test
        stress = self.stress_test(returns)
        
        return {
            'var': {
                '95_parametric': var_95_param,
                '99_parametric': var_99_param,
                '95_historical': var_95_hist,
                '95_monte_carlo': var_95_mc
            },
            'cvar': cvar,
            'drawdown': {k: v for k, v in drawdown.items() if k != 'drawdown_series'},
            'ratios': ratios,
            'stress_test': stress,
            'portfolio_value': portfolio_value,
            'analysis_period': len(returns),
            'timestamp': datetime.now().isoformat()
        }


# Singleton instance
_risk_service = None

def get_risk_service() -> RiskMetricsService:
    global _risk_service
    if _risk_service is None:
        _risk_service = RiskMetricsService()
    return _risk_service
