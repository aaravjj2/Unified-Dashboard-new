"""
Portfolio Optimization Service
Implements #225 from ROADMAP_ULTIMATE.md

Based on: https://github.com/robertmartin8/PyPortfolioOpt
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from scipy.optimize import minimize, LinearConstraint
from scipy import stats

logger = logging.getLogger(__name__)


class OptimizationMethod(Enum):
    """Portfolio optimization methods"""
    MEAN_VARIANCE = "mean_variance"
    MIN_VARIANCE = "min_variance"
    MAX_SHARPE = "max_sharpe"
    MAX_SORTINO = "max_sortino"
    RISK_PARITY = "risk_parity"
    BLACK_LITTERMAN = "black_litterman"
    HRP = "hierarchical_risk_parity"
    EQUAL_WEIGHT = "equal_weight"
    INVERSE_VOLATILITY = "inverse_volatility"
    MAX_DIVERSIFICATION = "max_diversification"


@dataclass
class OptimizationConstraints:
    """Portfolio constraints"""
    min_weight: float = 0.0
    max_weight: float = 1.0
    target_return: Optional[float] = None
    max_volatility: Optional[float] = None
    max_turnover: Optional[float] = None
    sector_limits: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    asset_classes: Dict[str, str] = field(default_factory=dict)


@dataclass
class OptimizationResult:
    """Optimization result"""
    weights: Dict[str, float]
    expected_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    var_95: float
    cvar_95: float
    diversification_ratio: float
    effective_n: float  # Effective number of bets
    method: str
    success: bool
    message: str


class PortfolioOptimizer:
    """
    Advanced portfolio optimization with multiple methods
    """
    
    def __init__(self, risk_free_rate: float = 0.05):
        self.risk_free_rate = risk_free_rate
        self.returns_data: Optional[pd.DataFrame] = None
        self.expected_returns: Optional[pd.Series] = None
        self.cov_matrix: Optional[pd.DataFrame] = None
        self.assets: List[str] = []
        
    def load_data(self, 
                 prices: Optional[pd.DataFrame] = None,
                 returns: Optional[pd.DataFrame] = None):
        """Load price or returns data"""
        if prices is not None:
            self.returns_data = prices.pct_change().dropna()
        elif returns is not None:
            self.returns_data = returns
        else:
            raise ValueError("Must provide either prices or returns")
        
        self.assets = list(self.returns_data.columns)
        self._calculate_statistics()
    
    def _calculate_statistics(self):
        """Calculate expected returns and covariance"""
        # Annualized expected returns
        self.expected_returns = self.returns_data.mean() * 252
        
        # Annualized covariance matrix
        self.cov_matrix = self.returns_data.cov() * 252
        
    def set_expected_returns(self, returns: Dict[str, float]):
        """Override expected returns with custom values"""
        self.expected_returns = pd.Series(returns)
    
    def _portfolio_return(self, weights: np.ndarray) -> float:
        """Calculate portfolio expected return"""
        return np.dot(weights, self.expected_returns)
    
    def _portfolio_volatility(self, weights: np.ndarray) -> float:
        """Calculate portfolio volatility"""
        return np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))
    
    def _portfolio_sharpe(self, weights: np.ndarray) -> float:
        """Calculate portfolio Sharpe ratio"""
        ret = self._portfolio_return(weights)
        vol = self._portfolio_volatility(weights)
        return (ret - self.risk_free_rate) / vol if vol > 0 else 0
    
    def _portfolio_sortino(self, weights: np.ndarray) -> float:
        """Calculate portfolio Sortino ratio"""
        portfolio_returns = self.returns_data @ weights
        ret = self._portfolio_return(weights)
        downside_returns = portfolio_returns[portfolio_returns < 0]
        downside_std = np.sqrt(np.mean(downside_returns**2)) * np.sqrt(252)
        return (ret - self.risk_free_rate) / downside_std if downside_std > 0 else 0
    
    def _diversification_ratio(self, weights: np.ndarray) -> float:
        """Calculate diversification ratio"""
        asset_stds = np.sqrt(np.diag(self.cov_matrix))
        weighted_std = np.dot(weights, asset_stds)
        portfolio_std = self._portfolio_volatility(weights)
        return weighted_std / portfolio_std if portfolio_std > 0 else 1
    
    def _effective_n(self, weights: np.ndarray) -> float:
        """Calculate effective number of bets (Herfindahl index inverse)"""
        return 1 / np.sum(weights**2)
    
    def optimize(self, 
                method: OptimizationMethod = OptimizationMethod.MAX_SHARPE,
                constraints: Optional[OptimizationConstraints] = None,
                views: Optional[Dict[str, float]] = None,
                view_confidences: Optional[Dict[str, float]] = None) -> OptimizationResult:
        """
        Optimize portfolio using specified method
        """
        if self.returns_data is None:
            raise ValueError("Must load data first")
        
        if constraints is None:
            constraints = OptimizationConstraints()
        
        n_assets = len(self.assets)
        initial_weights = np.ones(n_assets) / n_assets
        
        # Bounds
        bounds = [(constraints.min_weight, constraints.max_weight)] * n_assets
        
        # Sum to 1 constraint
        sum_constraint = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        constraint_list = [sum_constraint]
        
        # Target return constraint
        if constraints.target_return is not None:
            ret_constraint = {
                'type': 'eq',
                'fun': lambda w: self._portfolio_return(w) - constraints.target_return
            }
            constraint_list.append(ret_constraint)
        
        # Max volatility constraint
        if constraints.max_volatility is not None:
            vol_constraint = {
                'type': 'ineq',
                'fun': lambda w: constraints.max_volatility - self._portfolio_volatility(w)
            }
            constraint_list.append(vol_constraint)
        
        try:
            if method == OptimizationMethod.EQUAL_WEIGHT:
                weights = initial_weights
                
            elif method == OptimizationMethod.INVERSE_VOLATILITY:
                weights = self._inverse_volatility()
                
            elif method == OptimizationMethod.MIN_VARIANCE:
                result = minimize(
                    lambda w: self._portfolio_volatility(w),
                    initial_weights,
                    method='SLSQP',
                    bounds=bounds,
                    constraints=constraint_list
                )
                weights = result.x
                
            elif method == OptimizationMethod.MAX_SHARPE:
                result = minimize(
                    lambda w: -self._portfolio_sharpe(w),
                    initial_weights,
                    method='SLSQP',
                    bounds=bounds,
                    constraints=constraint_list
                )
                weights = result.x
                
            elif method == OptimizationMethod.MAX_SORTINO:
                result = minimize(
                    lambda w: -self._portfolio_sortino(w),
                    initial_weights,
                    method='SLSQP',
                    bounds=bounds,
                    constraints=constraint_list
                )
                weights = result.x
                
            elif method == OptimizationMethod.RISK_PARITY:
                weights = self._risk_parity(constraints)
                
            elif method == OptimizationMethod.BLACK_LITTERMAN:
                if views is None:
                    raise ValueError("Black-Litterman requires views")
                weights = self._black_litterman(views, view_confidences, constraints)
                
            elif method == OptimizationMethod.HRP:
                weights = self._hierarchical_risk_parity()
                
            elif method == OptimizationMethod.MAX_DIVERSIFICATION:
                result = minimize(
                    lambda w: -self._diversification_ratio(w),
                    initial_weights,
                    method='SLSQP',
                    bounds=bounds,
                    constraints=constraint_list
                )
                weights = result.x
                
            else:
                # Mean-variance with target return
                if constraints.target_return is None:
                    constraints.target_return = self.expected_returns.mean()
                
                result = minimize(
                    lambda w: self._portfolio_volatility(w),
                    initial_weights,
                    method='SLSQP',
                    bounds=bounds,
                    constraints=constraint_list
                )
                weights = result.x
            
            # Clean up weights (remove very small values)
            weights = np.array(weights)
            weights[weights < 0.001] = 0
            weights = weights / weights.sum()
            
            # Calculate metrics
            exp_return = self._portfolio_return(weights)
            volatility = self._portfolio_volatility(weights)
            sharpe = self._portfolio_sharpe(weights)
            sortino = self._portfolio_sortino(weights)
            
            # Calculate VaR and CVaR
            portfolio_returns = self.returns_data @ weights
            var_95 = np.percentile(portfolio_returns, 5) * np.sqrt(252)
            cvar_95 = portfolio_returns[portfolio_returns <= np.percentile(portfolio_returns, 5)].mean() * np.sqrt(252)
            
            # Max drawdown
            cumulative = (1 + portfolio_returns).cumprod()
            rolling_max = cumulative.cummax()
            drawdowns = (cumulative - rolling_max) / rolling_max
            max_dd = drawdowns.min()
            
            return OptimizationResult(
                weights={asset: round(w, 4) for asset, w in zip(self.assets, weights)},
                expected_return=round(exp_return, 4),
                volatility=round(volatility, 4),
                sharpe_ratio=round(sharpe, 4),
                sortino_ratio=round(sortino, 4),
                max_drawdown=round(max_dd, 4),
                var_95=round(var_95, 4),
                cvar_95=round(cvar_95, 4),
                diversification_ratio=round(self._diversification_ratio(weights), 4),
                effective_n=round(self._effective_n(weights), 2),
                method=method.value,
                success=True,
                message="Optimization successful"
            )
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return OptimizationResult(
                weights={asset: 1/n_assets for asset in self.assets},
                expected_return=0,
                volatility=0,
                sharpe_ratio=0,
                sortino_ratio=0,
                max_drawdown=0,
                var_95=0,
                cvar_95=0,
                diversification_ratio=1,
                effective_n=n_assets,
                method=method.value,
                success=False,
                message=str(e)
            )
    
    def _inverse_volatility(self) -> np.ndarray:
        """Inverse volatility weighting"""
        inv_vols = 1 / np.sqrt(np.diag(self.cov_matrix))
        return inv_vols / inv_vols.sum()
    
    def _risk_parity(self, constraints: OptimizationConstraints) -> np.ndarray:
        """
        Risk parity optimization - equal risk contribution
        """
        n = len(self.assets)
        target_risk = 1 / n  # Equal risk contribution
        
        def risk_budget_objective(weights):
            port_vol = self._portfolio_volatility(weights)
            marginal_contrib = np.dot(self.cov_matrix, weights)
            risk_contrib = weights * marginal_contrib / port_vol
            risk_contrib_normalized = risk_contrib / risk_contrib.sum()
            
            # Minimize squared deviation from equal risk
            return np.sum((risk_contrib_normalized - target_risk)**2)
        
        bounds = [(constraints.min_weight, constraints.max_weight)] * n
        constraints_list = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
        
        result = minimize(
            risk_budget_objective,
            np.ones(n) / n,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints_list
        )
        
        return result.x
    
    def _black_litterman(self, 
                        views: Dict[str, float],
                        confidences: Optional[Dict[str, float]] = None,
                        constraints: OptimizationConstraints = None) -> np.ndarray:
        """
        Black-Litterman model with views
        
        views: Dict mapping asset names to expected returns (absolute views)
        confidences: Dict mapping asset names to confidence levels (0-1)
        """
        if constraints is None:
            constraints = OptimizationConstraints()
        
        n = len(self.assets)
        
        # Market equilibrium returns (using CAPM-like approach)
        delta = 2.5  # Risk aversion
        market_weights = np.ones(n) / n  # Start with equal weights
        pi = delta * np.dot(self.cov_matrix, market_weights)
        
        # Construct view matrix P and view vector Q
        view_assets = [a for a in views.keys() if a in self.assets]
        if not view_assets:
            # No valid views, return max sharpe
            return self.optimize(OptimizationMethod.MAX_SHARPE, constraints).weights
        
        k = len(view_assets)
        P = np.zeros((k, n))
        Q = np.zeros(k)
        
        for i, asset in enumerate(view_assets):
            P[i, self.assets.index(asset)] = 1
            Q[i] = views[asset]
        
        # View uncertainty (Omega)
        tau = 0.05  # Scaling factor
        if confidences:
            omega_diag = [(1 - confidences.get(a, 0.5)) * 0.1 for a in view_assets]
        else:
            omega_diag = [0.05] * k
        
        Omega = np.diag(omega_diag)
        
        # Black-Litterman formula
        tau_sigma = tau * self.cov_matrix
        
        # Posterior expected returns
        M1 = np.linalg.inv(np.linalg.inv(tau_sigma) + P.T @ np.linalg.inv(Omega) @ P)
        M2 = np.linalg.inv(tau_sigma) @ pi + P.T @ np.linalg.inv(Omega) @ Q
        bl_returns = M1 @ M2
        
        # Optimize using BL returns
        original_returns = self.expected_returns.copy()
        self.expected_returns = pd.Series(bl_returns, index=self.assets)
        
        result = self.optimize(OptimizationMethod.MAX_SHARPE, constraints)
        
        # Restore original returns
        self.expected_returns = original_returns
        
        return np.array([result.weights[a] for a in self.assets])
    
    def _hierarchical_risk_parity(self) -> np.ndarray:
        """
        Hierarchical Risk Parity (HRP) using correlation clustering
        """
        from scipy.cluster.hierarchy import linkage, leaves_list
        from scipy.spatial.distance import squareform
        
        # Correlation matrix to distance
        corr = self.returns_data.corr()
        dist = np.sqrt((1 - corr) / 2)
        
        # Cluster using single linkage
        dist_condensed = squareform(dist.values, checks=False)
        link = linkage(dist_condensed, method='single')
        
        # Get sorted indices
        sort_idx = leaves_list(link)
        sorted_assets = [self.assets[i] for i in sort_idx]
        
        # Recursive bisection for weights
        def get_cluster_var(cov, assets):
            weights = self._inverse_volatility()
            return np.dot(weights.T, np.dot(cov, weights))
        
        def recursive_bisection(sorted_assets, weights):
            if len(sorted_assets) == 1:
                return
            
            # Split in half
            n = len(sorted_assets) // 2
            left = sorted_assets[:n]
            right = sorted_assets[n:]
            
            # Get cluster covariances
            left_idx = [self.assets.index(a) for a in left]
            right_idx = [self.assets.index(a) for a in right]
            
            left_cov = self.cov_matrix.iloc[left_idx, left_idx]
            right_cov = self.cov_matrix.iloc[right_idx, right_idx]
            
            left_var = np.trace(left_cov) / len(left)
            right_var = np.trace(right_cov) / len(right)
            
            # Allocate inversely proportional to variance
            alpha = 1 - left_var / (left_var + right_var)
            
            for asset in left:
                weights[self.assets.index(asset)] *= alpha
            for asset in right:
                weights[self.assets.index(asset)] *= (1 - alpha)
            
            # Recurse
            recursive_bisection(left, weights)
            recursive_bisection(right, weights)
        
        weights = np.ones(len(self.assets))
        recursive_bisection(sorted_assets, weights)
        weights = weights / weights.sum()
        
        return weights
    
    def efficient_frontier(self, 
                          n_points: int = 50,
                          constraints: Optional[OptimizationConstraints] = None) -> pd.DataFrame:
        """
        Calculate efficient frontier
        """
        if constraints is None:
            constraints = OptimizationConstraints()
        
        # Get return range
        min_ret = self.expected_returns.min()
        max_ret = self.expected_returns.max()
        
        target_returns = np.linspace(min_ret, max_ret, n_points)
        frontier_data = []
        
        for target in target_returns:
            temp_constraints = OptimizationConstraints(
                min_weight=constraints.min_weight,
                max_weight=constraints.max_weight,
                target_return=target
            )
            
            result = self.optimize(OptimizationMethod.MEAN_VARIANCE, temp_constraints)
            
            if result.success:
                frontier_data.append({
                    'return': result.expected_return,
                    'volatility': result.volatility,
                    'sharpe': result.sharpe_ratio
                })
        
        return pd.DataFrame(frontier_data)
    
    def monte_carlo_simulation(self, 
                              n_portfolios: int = 10000) -> pd.DataFrame:
        """
        Generate random portfolios for Monte Carlo analysis
        """
        n = len(self.assets)
        results = []
        
        for _ in range(n_portfolios):
            # Random weights
            weights = np.random.random(n)
            weights = weights / weights.sum()
            
            ret = self._portfolio_return(weights)
            vol = self._portfolio_volatility(weights)
            sharpe = (ret - self.risk_free_rate) / vol if vol > 0 else 0
            
            results.append({
                'return': ret,
                'volatility': vol,
                'sharpe': sharpe,
                'weights': weights.tolist()
            })
        
        return pd.DataFrame(results)
    
    def rebalance_analysis(self, 
                          current_weights: Dict[str, float],
                          target_weights: Dict[str, float],
                          current_prices: Dict[str, float],
                          portfolio_value: float) -> Dict[str, Any]:
        """
        Analyze rebalancing requirements
        """
        trades = {}
        total_turnover = 0
        
        for asset in self.assets:
            current = current_weights.get(asset, 0)
            target = target_weights.get(asset, 0)
            price = current_prices.get(asset, 100)
            
            weight_diff = target - current
            dollar_diff = weight_diff * portfolio_value
            shares = dollar_diff / price if price > 0 else 0
            
            trades[asset] = {
                'current_weight': current,
                'target_weight': target,
                'weight_change': weight_diff,
                'dollar_change': dollar_diff,
                'shares': shares,
                'action': 'BUY' if shares > 0 else 'SELL' if shares < 0 else 'HOLD'
            }
            
            total_turnover += abs(weight_diff)
        
        return {
            'trades': trades,
            'total_turnover': total_turnover / 2,  # One-way turnover
            'estimated_cost': total_turnover * portfolio_value * 0.001  # 10bps
        }
    
    def to_dict(self, result: OptimizationResult) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            'weights': result.weights,
            'expected_return': result.expected_return,
            'volatility': result.volatility,
            'sharpe_ratio': result.sharpe_ratio,
            'sortino_ratio': result.sortino_ratio,
            'max_drawdown': result.max_drawdown,
            'var_95': result.var_95,
            'cvar_95': result.cvar_95,
            'diversification_ratio': result.diversification_ratio,
            'effective_n': result.effective_n,
            'method': result.method,
            'success': result.success,
            'message': result.message
        }


# Singleton instance
_optimizer = None

def get_portfolio_optimizer() -> PortfolioOptimizer:
    global _optimizer
    if _optimizer is None:
        _optimizer = PortfolioOptimizer()
    return _optimizer
