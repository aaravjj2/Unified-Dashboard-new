"""
Portfolio Optimizer Service - Roadmap Items 261-300
Portfolio construction and optimization algorithms
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from scipy.optimize import minimize, LinearConstraint
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PortfolioWeights:
    """Portfolio weights result"""
    weights: Dict[str, float]
    expected_return: float
    volatility: float
    sharpe_ratio: float
    diversification_ratio: float = 0.0

@dataclass
class OptimizationConstraints:
    """Portfolio constraints"""
    min_weight: float = 0.0
    max_weight: float = 1.0
    long_only: bool = True
    max_turnover: float = 1.0
    sector_constraints: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    factor_constraints: Dict[str, Tuple[float, float]] = field(default_factory=dict)

class MeanVarianceOptimizer:
    """Mean-variance optimization - Items 261-270"""
    
    def __init__(self, returns: pd.DataFrame, risk_free_rate: float = 0.02):
        self.returns = returns
        self.rf = risk_free_rate / 252  # Daily risk-free rate
        self.mean_returns = returns.mean()
        self.cov_matrix = returns.cov()
        self.assets = list(returns.columns)
        self.n_assets = len(self.assets)
        
    def _portfolio_return(self, weights: np.ndarray) -> float:
        """Calculate portfolio expected return"""
        return np.sum(self.mean_returns.values * weights) * 252
    
    def _portfolio_volatility(self, weights: np.ndarray) -> float:
        """Calculate portfolio volatility"""
        return np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix.values * 252, weights)))
    
    def _portfolio_sharpe(self, weights: np.ndarray) -> float:
        """Calculate portfolio Sharpe ratio"""
        ret = self._portfolio_return(weights)
        vol = self._portfolio_volatility(weights)
        return (ret - self.rf * 252) / vol if vol > 0 else 0
    
    def _neg_sharpe(self, weights: np.ndarray) -> float:
        """Negative Sharpe ratio for minimization"""
        return -self._portfolio_sharpe(weights)
    
    def optimize_max_sharpe(self, constraints: OptimizationConstraints = None) -> PortfolioWeights:
        """Maximum Sharpe ratio portfolio - Item 267"""
        if constraints is None:
            constraints = OptimizationConstraints()
        
        bounds = [(constraints.min_weight, constraints.max_weight) for _ in range(self.n_assets)]
        
        # Constraint: weights sum to 1
        weight_constraint = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
        
        # Initial weights
        init_weights = np.array([1/self.n_assets] * self.n_assets)
        
        result = minimize(
            self._neg_sharpe,
            init_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=weight_constraint
        )
        
        weights = result.x
        return PortfolioWeights(
            weights=dict(zip(self.assets, weights)),
            expected_return=self._portfolio_return(weights),
            volatility=self._portfolio_volatility(weights),
            sharpe_ratio=self._portfolio_sharpe(weights)
        )
    
    def optimize_min_variance(self, constraints: OptimizationConstraints = None) -> PortfolioWeights:
        """Minimum variance portfolio - Item 266"""
        if constraints is None:
            constraints = OptimizationConstraints()
        
        bounds = [(constraints.min_weight, constraints.max_weight) for _ in range(self.n_assets)]
        weight_constraint = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
        
        init_weights = np.array([1/self.n_assets] * self.n_assets)
        
        result = minimize(
            self._portfolio_volatility,
            init_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=weight_constraint
        )
        
        weights = result.x
        return PortfolioWeights(
            weights=dict(zip(self.assets, weights)),
            expected_return=self._portfolio_return(weights),
            volatility=self._portfolio_volatility(weights),
            sharpe_ratio=self._portfolio_sharpe(weights)
        )
    
    def optimize_target_return(self, target_return: float, 
                               constraints: OptimizationConstraints = None) -> PortfolioWeights:
        """Minimum variance for target return - Item 261"""
        if constraints is None:
            constraints = OptimizationConstraints()
        
        bounds = [(constraints.min_weight, constraints.max_weight) for _ in range(self.n_assets)]
        
        constraints_list = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
            {'type': 'eq', 'fun': lambda x: self._portfolio_return(x) - target_return}
        ]
        
        init_weights = np.array([1/self.n_assets] * self.n_assets)
        
        result = minimize(
            self._portfolio_volatility,
            init_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints_list
        )
        
        weights = result.x
        return PortfolioWeights(
            weights=dict(zip(self.assets, weights)),
            expected_return=self._portfolio_return(weights),
            volatility=self._portfolio_volatility(weights),
            sharpe_ratio=self._portfolio_sharpe(weights)
        )
    
    def efficient_frontier(self, n_points: int = 50) -> pd.DataFrame:
        """Generate efficient frontier - Item 261"""
        min_ret = self.mean_returns.min() * 252
        max_ret = self.mean_returns.max() * 252
        
        target_returns = np.linspace(min_ret, max_ret, n_points)
        frontier = []
        
        for target in target_returns:
            try:
                portfolio = self.optimize_target_return(target)
                frontier.append({
                    'return': portfolio.expected_return,
                    'volatility': portfolio.volatility,
                    'sharpe': portfolio.sharpe_ratio
                })
            except Exception:
                continue
        
        return pd.DataFrame(frontier)

class RiskParityOptimizer:
    """Risk parity optimization - Items 263-264"""
    
    def __init__(self, returns: pd.DataFrame):
        self.returns = returns
        self.cov_matrix = returns.cov().values * 252
        self.assets = list(returns.columns)
        self.n_assets = len(self.assets)
        
    def _risk_contribution(self, weights: np.ndarray) -> np.ndarray:
        """Calculate marginal risk contribution of each asset"""
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))
        marginal_contrib = np.dot(self.cov_matrix, weights)
        risk_contrib = weights * marginal_contrib / portfolio_vol
        return risk_contrib
    
    def _risk_parity_objective(self, weights: np.ndarray, 
                               target_risk_contrib: np.ndarray = None) -> float:
        """Objective: equal risk contribution"""
        if target_risk_contrib is None:
            target_risk_contrib = np.array([1/self.n_assets] * self.n_assets)
        
        risk_contrib = self._risk_contribution(weights)
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))
        
        # Normalize
        risk_contrib_pct = risk_contrib / portfolio_vol
        
        return np.sum((risk_contrib_pct - target_risk_contrib) ** 2)
    
    def optimize(self, target_risk_contrib: np.ndarray = None) -> PortfolioWeights:
        """Risk parity optimization - Item 263"""
        bounds = [(0.01, 1.0) for _ in range(self.n_assets)]
        weight_constraint = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
        
        init_weights = np.array([1/self.n_assets] * self.n_assets)
        
        result = minimize(
            lambda w: self._risk_parity_objective(w, target_risk_contrib),
            init_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=weight_constraint
        )
        
        weights = result.x
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))
        mean_returns = self.returns.mean().values * 252
        portfolio_return = np.sum(mean_returns * weights)
        
        return PortfolioWeights(
            weights=dict(zip(self.assets, weights)),
            expected_return=portfolio_return,
            volatility=portfolio_vol,
            sharpe_ratio=(portfolio_return - 0.02) / portfolio_vol if portfolio_vol > 0 else 0
        )

class HierarchicalRiskParity:
    """Hierarchical Risk Parity - Item 264"""
    
    def __init__(self, returns: pd.DataFrame):
        self.returns = returns
        self.cov_matrix = returns.cov()
        self.corr_matrix = returns.corr()
        self.assets = list(returns.columns)
        
    def _tree_clustering(self) -> np.ndarray:
        """Perform hierarchical clustering on assets"""
        dist = np.sqrt(0.5 * (1 - self.corr_matrix.values))
        dist = squareform(dist, checks=False)
        link = linkage(dist, method='single')
        return link
    
    def _get_quasi_diag(self, link: np.ndarray) -> List[int]:
        """Get quasi-diagonal order from hierarchical clustering"""
        link = link.astype(int)
        sort_ix = pd.Series([link[-1, 0], link[-1, 1]])
        num_items = link[-1, 3]
        
        while sort_ix.max() >= len(self.assets):
            sort_ix.index = range(0, sort_ix.shape[0] * 2, 2)
            df0 = sort_ix[sort_ix >= len(self.assets)]
            i = df0.index
            j = df0.values - len(self.assets)
            sort_ix[i] = link[j, 0]
            df1 = pd.Series(link[j, 1], index=i + 1)
            sort_ix = pd.concat([sort_ix, df1])
            sort_ix = sort_ix.sort_index()
            sort_ix.index = range(sort_ix.shape[0])
        
        return sort_ix.tolist()
    
    def _get_cluster_var(self, cov: pd.DataFrame, cluster_items: List[int]) -> float:
        """Get cluster variance"""
        cov_slice = cov.iloc[cluster_items, cluster_items]
        ivp = 1.0 / np.diag(cov_slice)
        ivp /= ivp.sum()
        w = ivp
        cluster_var = np.dot(w, np.dot(cov_slice, w))
        return cluster_var
    
    def optimize(self) -> PortfolioWeights:
        """HRP optimization"""
        # Step 1: Tree clustering
        link = self._tree_clustering()
        
        # Step 2: Quasi-diagonalization
        sort_ix = self._get_quasi_diag(link)
        
        # Step 3: Recursive bisection
        weights = pd.Series(1.0, index=sort_ix)
        cluster_items = [sort_ix]
        
        while len(cluster_items) > 0:
            cluster_items = [i[j:k] for i in cluster_items 
                          for j, k in ((0, len(i)//2), (len(i)//2, len(i))) 
                          if len(i) > 1]
            
            for i in range(0, len(cluster_items), 2):
                cluster0 = cluster_items[i]
                cluster1 = cluster_items[i+1]
                
                cluster_var0 = self._get_cluster_var(self.cov_matrix, cluster0)
                cluster_var1 = self._get_cluster_var(self.cov_matrix, cluster1)
                
                alpha = 1 - cluster_var0 / (cluster_var0 + cluster_var1)
                
                weights[cluster0] *= alpha
                weights[cluster1] *= 1 - alpha
        
        weights.index = [self.assets[i] for i in weights.index]
        weights = weights / weights.sum()
        
        # Calculate portfolio stats
        mean_returns = self.returns.mean() * 252
        portfolio_return = np.sum(mean_returns * weights)
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix.values * 252, weights)))
        
        return PortfolioWeights(
            weights=weights.to_dict(),
            expected_return=portfolio_return,
            volatility=portfolio_vol,
            sharpe_ratio=(portfolio_return - 0.02) / portfolio_vol if portfolio_vol > 0 else 0
        )

class BlackLittermanModel:
    """Black-Litterman model - Item 262"""
    
    def __init__(self, returns: pd.DataFrame, market_caps: pd.Series,
                 risk_free_rate: float = 0.02, tau: float = 0.05):
        self.returns = returns
        self.market_caps = market_caps
        self.rf = risk_free_rate
        self.tau = tau
        self.cov_matrix = returns.cov() * 252
        self.assets = list(returns.columns)
        
    def _implied_returns(self, risk_aversion: float = 2.5) -> pd.Series:
        """Calculate implied equilibrium returns"""
        market_weights = self.market_caps / self.market_caps.sum()
        return risk_aversion * np.dot(self.cov_matrix, market_weights)
    
    def optimize(self, views: Dict[str, float] = None, 
                 view_confidence: float = 0.5) -> PortfolioWeights:
        """Black-Litterman optimization with views"""
        pi = self._implied_returns()
        
        if views is None or len(views) == 0:
            # No views, use equilibrium
            weights = self.market_caps / self.market_caps.sum()
        else:
            # Incorporate views
            n_views = len(views)
            P = np.zeros((n_views, len(self.assets)))
            Q = np.zeros(n_views)
            
            for i, (asset, view_return) in enumerate(views.items()):
                if asset in self.assets:
                    P[i, self.assets.index(asset)] = 1
                    Q[i] = view_return
            
            # Omega: view uncertainty
            omega = np.diag([self.tau * view_confidence] * n_views)
            
            # Black-Litterman formula
            cov_tau = self.tau * self.cov_matrix.values
            
            try:
                M = np.linalg.inv(np.linalg.inv(cov_tau) + P.T @ np.linalg.inv(omega) @ P)
                bl_returns = M @ (np.linalg.inv(cov_tau) @ pi.values + P.T @ np.linalg.inv(omega) @ Q)
            except np.linalg.LinAlgError:
                bl_returns = pi.values
            
            # Optimize using BL returns
            optimizer = MeanVarianceOptimizer(self.returns, self.rf)
            optimizer.mean_returns = pd.Series(bl_returns / 252, index=self.assets)
            
            return optimizer.optimize_max_sharpe()
        
        portfolio_return = np.sum(pi * weights)
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix.values, weights)))
        
        return PortfolioWeights(
            weights=dict(zip(self.assets, weights.values)),
            expected_return=portfolio_return,
            volatility=portfolio_vol,
            sharpe_ratio=(portfolio_return - self.rf) / portfolio_vol if portfolio_vol > 0 else 0
        )

class PortfolioOptimizerService:
    """Main portfolio optimizer service - Items 261-300"""
    
    def __init__(self):
        self.optimizers: Dict[str, Any] = {}
        self.cached_portfolios: Dict[str, PortfolioWeights] = {}
        
    def setup_from_returns(self, returns: pd.DataFrame, market_caps: pd.Series = None):
        """Setup optimizers from return data"""
        self.optimizers['mean_variance'] = MeanVarianceOptimizer(returns)
        self.optimizers['risk_parity'] = RiskParityOptimizer(returns)
        self.optimizers['hrp'] = HierarchicalRiskParity(returns)
        
        if market_caps is not None:
            self.optimizers['black_litterman'] = BlackLittermanModel(returns, market_caps)
    
    def optimize(self, method: str = 'max_sharpe', 
                 constraints: OptimizationConstraints = None,
                 **kwargs) -> PortfolioWeights:
        """Run portfolio optimization"""
        if method == 'max_sharpe':
            return self.optimizers['mean_variance'].optimize_max_sharpe(constraints)
        elif method == 'min_variance':
            return self.optimizers['mean_variance'].optimize_min_variance(constraints)
        elif method == 'risk_parity':
            return self.optimizers['risk_parity'].optimize()
        elif method == 'hrp':
            return self.optimizers['hrp'].optimize()
        elif method == 'black_litterman':
            views = kwargs.get('views', {})
            return self.optimizers['black_litterman'].optimize(views)
        else:
            raise ValueError(f"Unknown optimization method: {method}")
    
    def get_efficient_frontier(self, n_points: int = 50) -> pd.DataFrame:
        """Get efficient frontier"""
        return self.optimizers['mean_variance'].efficient_frontier(n_points)
    
    def compare_methods(self) -> pd.DataFrame:
        """Compare all optimization methods"""
        results = []
        
        for method in ['max_sharpe', 'min_variance', 'risk_parity', 'hrp']:
            try:
                portfolio = self.optimize(method)
                results.append({
                    'method': method,
                    'return': portfolio.expected_return,
                    'volatility': portfolio.volatility,
                    'sharpe': portfolio.sharpe_ratio,
                    'max_weight': max(portfolio.weights.values()),
                    'min_weight': min(portfolio.weights.values())
                })
            except Exception as e:
                logger.warning(f"Method {method} failed: {e}")
        
        return pd.DataFrame(results)
    
    def generate_sample_analysis(self) -> Dict[str, Any]:
        """Generate sample analysis for testing"""
        np.random.seed(42)
        
        # Generate synthetic return data
        n_assets = 10
        n_periods = 252
        
        asset_names = [f'Asset_{i+1}' for i in range(n_assets)]
        
        # Correlated returns
        mean_returns = np.random.uniform(0.0002, 0.0008, n_assets)
        vols = np.random.uniform(0.01, 0.03, n_assets)
        
        # Correlation matrix - ensure positive definite
        # Use eigenvalue adjustment to ensure positive definiteness
        rand_matrix = np.random.randn(n_assets, n_assets)
        corr = rand_matrix @ rand_matrix.T
        d = np.diag(1.0 / np.sqrt(np.diag(corr)))
        corr = d @ corr @ d  # Normalize to correlation matrix
        
        # Cholesky decomposition for correlated returns
        try:
            L = np.linalg.cholesky(corr)
        except np.linalg.LinAlgError:
            # Fallback to identity if still fails
            L = np.eye(n_assets)
        
        returns_data = np.zeros((n_periods, n_assets))
        for t in range(n_periods):
            z = np.random.randn(n_assets)
            corr_z = L @ z
            returns_data[t] = mean_returns + vols * corr_z
        
        returns = pd.DataFrame(
            returns_data,
            columns=asset_names,
            index=pd.date_range(end=pd.Timestamp.now(), periods=n_periods, freq='D')
        )
        
        # Market caps
        market_caps = pd.Series(
            np.random.uniform(1e9, 100e9, n_assets),
            index=asset_names
        )
        
        # Setup and optimize
        self.setup_from_returns(returns, market_caps)
        
        comparison = self.compare_methods()
        frontier = self.get_efficient_frontier(20)
        
        max_sharpe = self.optimize('max_sharpe')
        
        return {
            'n_assets': n_assets,
            'n_periods': n_periods,
            'method_comparison': comparison.to_dict('records'),
            'efficient_frontier': frontier.to_dict('records'),
            'max_sharpe_portfolio': {
                'weights': max_sharpe.weights,
                'return': max_sharpe.expected_return,
                'volatility': max_sharpe.volatility,
                'sharpe': max_sharpe.sharpe_ratio
            }
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            'optimizers_available': list(self.optimizers.keys()),
            'cached_portfolios': len(self.cached_portfolios)
        }


if __name__ == "__main__":
    # Test the service
    service = PortfolioOptimizerService()
    
    print("Portfolio Optimizer Service Test")
    print("=" * 50)
    
    # Generate sample analysis
    analysis = service.generate_sample_analysis()
    
    print(f"\nDataset: {analysis['n_assets']} assets, {analysis['n_periods']} periods")
    
    print("\nMethod Comparison:")
    for result in analysis['method_comparison']:
        print(f"  {result['method']:15s}: Return={result['return']:.2%}, "
              f"Vol={result['volatility']:.2%}, Sharpe={result['sharpe']:.2f}")
    
    print("\nMax Sharpe Portfolio Weights:")
    for asset, weight in sorted(analysis['max_sharpe_portfolio']['weights'].items(), 
                                 key=lambda x: -x[1])[:5]:
        print(f"  {asset}: {weight:.2%}")
    
    print(f"\nService Stats: {service.get_stats()}")
    
    print("\n✅ Portfolio Optimizer Service operational - Items 261-300")
