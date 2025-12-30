"""
Portfolio Optimization Module
=============================
Advanced portfolio optimization tools:
- Kelly Criterion calculator
- Portfolio beta optimizer
- Sharpe ratio maximizer
- Efficient frontier generator
- Rebalancing advisor

Author: AI/ML Options Lab
"""

import os
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from scipy.optimize import minimize, minimize_scalar
from scipy.stats import norm

logger = logging.getLogger(__name__)


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class KellyResult:
    """Kelly Criterion calculation result."""
    ticker: str
    win_rate: float
    avg_win: float
    avg_loss: float
    kelly_fraction: float
    half_kelly: float
    quarter_kelly: float
    recommended_allocation: float
    max_position_size: float
    expected_growth: float
    risk_of_ruin: float


@dataclass
class BetaOptimization:
    """Beta optimization result."""
    current_beta: float
    target_beta: float
    required_hedge: Dict[str, float]
    hedge_cost: float
    instruments: List[Dict]
    optimal_allocation: Dict[str, float]


@dataclass
class SharpeAnalysis:
    """Sharpe ratio analysis."""
    ticker: str
    returns_mean: float
    returns_std: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    risk_adjusted_rank: int


@dataclass
class EfficientFrontierPoint:
    """Point on efficient frontier."""
    expected_return: float
    volatility: float
    sharpe_ratio: float
    weights: Dict[str, float]


@dataclass
class RebalanceRecommendation:
    """Rebalancing recommendation."""
    ticker: str
    current_weight: float
    target_weight: float
    action: str  # 'buy', 'sell', 'hold'
    shares_to_trade: int
    dollar_amount: float
    priority: str  # 'high', 'medium', 'low'


# ============================================================
# KELLY CRITERION CALCULATOR
# ============================================================

class KellyCriterionCalculator:
    """
    Calculate optimal position sizing using Kelly Criterion.
    f* = (p*b - q) / b
    where p = win probability, q = 1-p, b = win/loss ratio
    """
    
    def __init__(self):
        self.max_kelly = 0.25  # Cap at 25% of portfolio
    
    def calculate(self, trade_history: List[Dict] = None,
                  win_rate: float = None,
                  avg_win: float = None,
                  avg_loss: float = None) -> KellyResult:
        """Calculate Kelly fraction from trade history or parameters."""
        try:
            if trade_history and len(trade_history) >= 10:
                # Calculate from history
                wins = [t['pnl'] for t in trade_history if t['pnl'] > 0]
                losses = [t['pnl'] for t in trade_history if t['pnl'] < 0]
                
                if not losses:
                    losses = [-100]  # Default loss
                
                win_rate = len(wins) / len(trade_history)
                avg_win = np.mean(wins) if wins else 100
                avg_loss = abs(np.mean(losses))
            else:
                # Use provided parameters or defaults
                win_rate = win_rate or 0.55
                avg_win = avg_win or 150
                avg_loss = avg_loss or 100
            
            # Kelly formula
            b = avg_win / avg_loss  # Win/loss ratio
            p = win_rate
            q = 1 - p
            
            kelly = (p * b - q) / b
            kelly = max(0, min(kelly, self.max_kelly))  # Bound between 0 and max
            
            # Calculate risk of ruin
            if kelly > 0:
                risk_of_ruin = ((1 - p) / p) ** (1 / kelly) if p > 0.5 else 0.5
            else:
                risk_of_ruin = 1.0
            
            # Expected growth rate
            expected_growth = p * np.log(1 + kelly * b) + q * np.log(1 - kelly)
            
            return KellyResult(
                ticker='PORTFOLIO',
                win_rate=round(win_rate, 3),
                avg_win=round(avg_win, 2),
                avg_loss=round(avg_loss, 2),
                kelly_fraction=round(kelly, 4),
                half_kelly=round(kelly / 2, 4),
                quarter_kelly=round(kelly / 4, 4),
                recommended_allocation=round(kelly / 2, 4),  # Half Kelly is safer
                max_position_size=round(kelly * 100, 1),
                expected_growth=round(expected_growth * 100, 2),
                risk_of_ruin=round(risk_of_ruin, 4)
            )
            
        except Exception as e:
            logger.error(f"Kelly calculation failed: {e}")
            return KellyResult(
                ticker='PORTFOLIO',
                win_rate=0.5,
                avg_win=100,
                avg_loss=100,
                kelly_fraction=0,
                half_kelly=0,
                quarter_kelly=0,
                recommended_allocation=0.02,
                max_position_size=2,
                expected_growth=0,
                risk_of_ruin=0.5
            )
    
    def position_size(self, portfolio_value: float, kelly_result: KellyResult,
                      risk_multiplier: float = 0.5) -> float:
        """Calculate dollar position size."""
        return portfolio_value * kelly_result.kelly_fraction * risk_multiplier


# ============================================================
# BETA OPTIMIZER
# ============================================================

class PortfolioBetaOptimizer:
    """
    Optimize portfolio beta using options and hedges.
    Target specific beta exposure.
    """
    
    def __init__(self):
        self.spy_beta = 1.0  # SPY as benchmark
    
    def optimize(self, positions: List[Dict], 
                 target_beta: float = 1.0,
                 portfolio_value: float = 100000) -> BetaOptimization:
        """Optimize portfolio to target beta."""
        try:
            # Calculate current beta
            total_value = sum(p.get('value', 0) for p in positions)
            if total_value == 0:
                total_value = portfolio_value
            
            weighted_beta = sum(
                p.get('beta', 1.0) * p.get('value', 0) / total_value
                for p in positions
            )
            
            beta_diff = target_beta - weighted_beta
            
            # Determine hedge requirements
            hedge_instruments = []
            
            if beta_diff > 0.1:
                # Need more beta - buy SPY calls or SPY
                spy_value_needed = abs(beta_diff) * total_value
                hedge_instruments.append({
                    'instrument': 'SPY',
                    'action': 'buy',
                    'shares': int(spy_value_needed / 500),  # Assume SPY ~$500
                    'beta_contribution': round(beta_diff, 3),
                    'cost': round(spy_value_needed, 2)
                })
            elif beta_diff < -0.1:
                # Need less beta - sell SPY or buy puts
                spy_value_needed = abs(beta_diff) * total_value
                hedge_instruments.append({
                    'instrument': 'SPY_PUT',
                    'action': 'buy',
                    'contracts': int(spy_value_needed / 50000),  # SPY put ~$500 controls 50k
                    'beta_contribution': round(beta_diff, 3),
                    'cost': round(spy_value_needed * 0.03, 2)  # ~3% for puts
                })
            
            # Optimal allocation
            optimal = {}
            for p in positions:
                ticker = p.get('ticker', 'UNKNOWN')
                optimal[ticker] = round(p.get('value', 0) / total_value, 4)
            
            hedge_cost = sum(h.get('cost', 0) for h in hedge_instruments)
            
            return BetaOptimization(
                current_beta=round(weighted_beta, 3),
                target_beta=target_beta,
                required_hedge={'beta_adjustment': round(beta_diff, 3)},
                hedge_cost=round(hedge_cost, 2),
                instruments=hedge_instruments,
                optimal_allocation=optimal
            )
            
        except Exception as e:
            logger.error(f"Beta optimization failed: {e}")
            return BetaOptimization(
                current_beta=1.0,
                target_beta=target_beta,
                required_hedge={},
                hedge_cost=0,
                instruments=[],
                optimal_allocation={}
            )


# ============================================================
# SHARPE RATIO ANALYZER
# ============================================================

class SharpeRatioAnalyzer:
    """
    Analyze and rank strategies by risk-adjusted returns.
    Calculates Sharpe, Sortino, and Calmar ratios.
    """
    
    def __init__(self):
        self.risk_free_rate = 0.05  # 5% annual
    
    def analyze(self, returns: List[float], ticker: str = 'STRATEGY') -> SharpeAnalysis:
        """Analyze risk-adjusted returns."""
        try:
            if not returns or len(returns) < 5:
                returns = [0.01, -0.005, 0.02, 0.01, -0.01]  # Default
            
            returns_arr = np.array(returns)
            
            # Annualize (assume daily returns)
            annual_mean = np.mean(returns_arr) * 252
            annual_std = np.std(returns_arr) * np.sqrt(252)
            
            # Sharpe Ratio
            sharpe = (annual_mean - self.risk_free_rate) / annual_std if annual_std > 0 else 0
            
            # Sortino Ratio (only downside volatility)
            downside_returns = returns_arr[returns_arr < 0]
            downside_std = np.std(downside_returns) * np.sqrt(252) if len(downside_returns) > 0 else annual_std
            sortino = (annual_mean - self.risk_free_rate) / downside_std if downside_std > 0 else 0
            
            # Calmar Ratio (return / max drawdown)
            cumulative = np.cumprod(1 + returns_arr)
            peak = np.maximum.accumulate(cumulative)
            drawdown = (peak - cumulative) / peak
            max_dd = np.max(drawdown)
            calmar = annual_mean / max_dd if max_dd > 0 else 0
            
            return SharpeAnalysis(
                ticker=ticker,
                returns_mean=round(annual_mean * 100, 2),
                returns_std=round(annual_std * 100, 2),
                sharpe_ratio=round(sharpe, 3),
                sortino_ratio=round(sortino, 3),
                calmar_ratio=round(calmar, 3),
                risk_adjusted_rank=0  # Set by comparison
            )
            
        except Exception as e:
            logger.error(f"Sharpe analysis failed: {e}")
            return SharpeAnalysis(
                ticker=ticker,
                returns_mean=0,
                returns_std=0,
                sharpe_ratio=0,
                sortino_ratio=0,
                calmar_ratio=0,
                risk_adjusted_rank=0
            )
    
    def rank_strategies(self, strategies: List[Dict]) -> List[SharpeAnalysis]:
        """Rank multiple strategies by Sharpe ratio."""
        analyses = []
        for strat in strategies:
            analysis = self.analyze(
                strat.get('returns', []),
                strat.get('name', 'UNKNOWN')
            )
            analyses.append(analysis)
        
        # Sort by Sharpe
        analyses.sort(key=lambda x: x.sharpe_ratio, reverse=True)
        
        # Assign ranks
        for i, a in enumerate(analyses):
            a.risk_adjusted_rank = i + 1
        
        return analyses


# ============================================================
# EFFICIENT FRONTIER GENERATOR
# ============================================================

class EfficientFrontierGenerator:
    """
    Generate efficient frontier for portfolio optimization.
    Uses mean-variance optimization.
    """
    
    def __init__(self):
        self.num_portfolios = 1000
        self.risk_free_rate = 0.05
    
    def generate(self, assets: List[Dict]) -> List[EfficientFrontierPoint]:
        """Generate efficient frontier points."""
        try:
            if not assets or len(assets) < 2:
                return self._default_frontier()
            
            # Extract returns and covariance
            n_assets = len(assets)
            expected_returns = np.array([a.get('expected_return', 0.10) for a in assets])
            volatilities = np.array([a.get('volatility', 0.20) for a in assets])
            
            # Simple correlation assumption
            corr_matrix = np.eye(n_assets) * 0.5 + 0.5  # All correlate at 0.5
            cov_matrix = np.outer(volatilities, volatilities) * corr_matrix
            
            # Generate random portfolios
            frontier_points = []
            
            for _ in range(self.num_portfolios):
                # Random weights
                weights = np.random.random(n_assets)
                weights /= weights.sum()
                
                # Portfolio return and risk
                port_return = np.dot(weights, expected_returns)
                port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
                
                # Sharpe
                sharpe = (port_return - self.risk_free_rate) / port_vol if port_vol > 0 else 0
                
                weight_dict = {assets[i].get('ticker', f'ASSET_{i}'): round(w, 4) 
                              for i, w in enumerate(weights)}
                
                frontier_points.append(EfficientFrontierPoint(
                    expected_return=round(port_return * 100, 2),
                    volatility=round(port_vol * 100, 2),
                    sharpe_ratio=round(sharpe, 3),
                    weights=weight_dict
                ))
            
            # Sort by volatility for frontier
            frontier_points.sort(key=lambda x: x.volatility)
            
            # Keep only efficient (highest return for each vol level)
            efficient = []
            max_return = -float('inf')
            for point in frontier_points:
                if point.expected_return > max_return:
                    efficient.append(point)
                    max_return = point.expected_return
            
            return efficient[:50]  # Top 50 points
            
        except Exception as e:
            logger.error(f"Frontier generation failed: {e}")
            return self._default_frontier()
    
    def _default_frontier(self) -> List[EfficientFrontierPoint]:
        """Default frontier for demo."""
        points = []
        for vol in range(5, 30, 2):
            ret = 5 + vol * 0.4 + np.random.normal(0, 2)
            sharpe = (ret - 5) / vol
            points.append(EfficientFrontierPoint(
                expected_return=round(ret, 2),
                volatility=vol,
                sharpe_ratio=round(sharpe, 3),
                weights={'SPY': 0.6, 'QQQ': 0.4}
            ))
        return points
    
    def find_optimal_portfolio(self, frontier: List[EfficientFrontierPoint]) -> EfficientFrontierPoint:
        """Find maximum Sharpe ratio portfolio."""
        if not frontier:
            return self._default_frontier()[0]
        return max(frontier, key=lambda x: x.sharpe_ratio)


# ============================================================
# REBALANCING ADVISOR
# ============================================================

class RebalancingAdvisor:
    """
    Advise on portfolio rebalancing.
    Suggests trades to match target allocation.
    """
    
    def __init__(self):
        self.rebalance_threshold = 0.05  # 5% drift triggers rebalance
        self.min_trade_value = 100  # Minimum trade value
    
    def analyze(self, current_positions: List[Dict],
                target_allocation: Dict[str, float],
                portfolio_value: float) -> List[RebalanceRecommendation]:
        """Analyze and recommend rebalancing trades."""
        try:
            recommendations = []
            
            # Calculate current weights
            current_weights = {}
            for pos in current_positions:
                ticker = pos.get('ticker', 'UNKNOWN')
                value = pos.get('value', 0)
                current_weights[ticker] = value / portfolio_value if portfolio_value > 0 else 0
            
            # Compare to targets
            all_tickers = set(current_weights.keys()) | set(target_allocation.keys())
            
            for ticker in all_tickers:
                current = current_weights.get(ticker, 0)
                target = target_allocation.get(ticker, 0)
                diff = target - current
                
                # Determine action
                if abs(diff) < 0.01:  # Less than 1% difference
                    action = 'hold'
                    priority = 'low'
                elif diff > 0:
                    action = 'buy'
                    priority = 'high' if diff > self.rebalance_threshold else 'medium'
                else:
                    action = 'sell'
                    priority = 'high' if abs(diff) > self.rebalance_threshold else 'medium'
                
                dollar_amount = abs(diff) * portfolio_value
                
                # Get current price for shares calculation
                current_price = next(
                    (p.get('price', 100) for p in current_positions if p.get('ticker') == ticker),
                    100
                )
                shares = int(dollar_amount / current_price) if current_price > 0 else 0
                
                if dollar_amount >= self.min_trade_value or action == 'hold':
                    recommendations.append(RebalanceRecommendation(
                        ticker=ticker,
                        current_weight=round(current * 100, 2),
                        target_weight=round(target * 100, 2),
                        action=action,
                        shares_to_trade=shares,
                        dollar_amount=round(dollar_amount, 2),
                        priority=priority
                    ))
            
            # Sort by priority
            priority_order = {'high': 0, 'medium': 1, 'low': 2}
            recommendations.sort(key=lambda x: priority_order.get(x.priority, 2))
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Rebalancing analysis failed: {e}")
            return []
    
    def get_rebalance_schedule(self, volatility: float) -> Dict:
        """Suggest rebalancing frequency based on volatility."""
        if volatility > 0.30:
            return {
                'frequency': 'weekly',
                'reason': 'High volatility warrants frequent monitoring',
                'threshold': 0.03
            }
        elif volatility > 0.20:
            return {
                'frequency': 'bi-weekly',
                'reason': 'Moderate volatility needs regular check-ins',
                'threshold': 0.05
            }
        else:
            return {
                'frequency': 'monthly',
                'reason': 'Low volatility allows less frequent rebalancing',
                'threshold': 0.07
            }


# ============================================================
# UNIFIED PORTFOLIO OPTIMIZER
# ============================================================

class PortfolioOptimizer:
    """Unified portfolio optimization engine."""
    
    def __init__(self):
        self.kelly_calc = KellyCriterionCalculator()
        self.beta_optimizer = PortfolioBetaOptimizer()
        self.sharpe_analyzer = SharpeRatioAnalyzer()
        self.frontier_generator = EfficientFrontierGenerator()
        self.rebalancing_advisor = RebalancingAdvisor()
    
    def full_optimization(self, positions: List[Dict],
                          portfolio_value: float,
                          target_beta: float = 1.0,
                          target_allocation: Dict[str, float] = None) -> Dict:
        """Complete portfolio optimization analysis."""
        # Kelly
        kelly = self.kelly_calc.calculate()
        
        # Beta
        beta = self.beta_optimizer.optimize(positions, target_beta, portfolio_value)
        
        # Sharpe for each position
        sharpe_analyses = []
        for pos in positions:
            returns = pos.get('returns', [0.01, 0.02, -0.01, 0.015])
            analysis = self.sharpe_analyzer.analyze(returns, pos.get('ticker', 'UNKNOWN'))
            sharpe_analyses.append({
                'ticker': analysis.ticker,
                'sharpe': analysis.sharpe_ratio,
                'sortino': analysis.sortino_ratio
            })
        
        # Efficient frontier
        assets = [{'ticker': p.get('ticker'), 'expected_return': 0.10, 'volatility': 0.20}
                  for p in positions]
        frontier = self.frontier_generator.generate(assets)
        optimal_port = self.frontier_generator.find_optimal_portfolio(frontier)
        
        # Rebalancing
        if target_allocation is None:
            target_allocation = {p.get('ticker', 'X'): 1/len(positions) for p in positions}
        rebalance = self.rebalancing_advisor.analyze(positions, target_allocation, portfolio_value)
        
        return {
            'kelly_criterion': {
                'optimal_fraction': kelly.kelly_fraction,
                'half_kelly': kelly.half_kelly,
                'recommended_size': kelly.recommended_allocation,
                'risk_of_ruin': kelly.risk_of_ruin
            },
            'beta_optimization': {
                'current_beta': beta.current_beta,
                'target_beta': beta.target_beta,
                'hedge_instruments': beta.instruments
            },
            'sharpe_analysis': sharpe_analyses,
            'efficient_frontier': {
                'optimal_return': optimal_port.expected_return,
                'optimal_volatility': optimal_port.volatility,
                'optimal_sharpe': optimal_port.sharpe_ratio,
                'optimal_weights': optimal_port.weights
            },
            'rebalancing': {
                'recommendations_count': len(rebalance),
                'high_priority': sum(1 for r in rebalance if r.priority == 'high'),
                'total_trades_value': sum(r.dollar_amount for r in rebalance)
            },
            'generated_at': datetime.now().isoformat()
        }


# ============================================================
# SINGLETON GETTER
# ============================================================

_portfolio_optimizer = None

def get_portfolio_optimizer() -> PortfolioOptimizer:
    """Get singleton instance."""
    global _portfolio_optimizer
    if _portfolio_optimizer is None:
        _portfolio_optimizer = PortfolioOptimizer()
    return _portfolio_optimizer
