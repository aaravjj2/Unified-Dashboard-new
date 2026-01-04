"""
Alpaca Options Lab - Risk Management Module

Production-grade risk management with:
- Portfolio Greeks aggregation
- Risk limit enforcement
- Position sizing with Kelly/HRP
- Real-time risk monitoring

Components:
- RiskAggregator: Portfolio-level Greeks and risk metrics
- LimitEnforcer: Risk limit validation and blocking
- PortfolioOptimizer: HRP-based position sizing
"""
from src.risk.aggregator import (
    PortfolioGreeks,
    RiskAggregator,
    get_risk_aggregator,
)
from src.risk.limits import (
    LimitBreach,
    LimitEnforcer,
    RiskLimit,
    RiskLimitType,
    get_limit_enforcer,
)
from src.risk.optimizer import (
    HRPOptimizer,
    OptimizationResult,
    PortfolioOptimizer,
    get_portfolio_optimizer,
)

__all__ = [
    # Aggregator
    "PortfolioGreeks",
    "RiskAggregator",
    "get_risk_aggregator",
    # Limits
    "RiskLimitType",
    "RiskLimit",
    "LimitBreach",
    "LimitEnforcer",
    "get_limit_enforcer",
    # Optimizer
    "OptimizationResult",
    "PortfolioOptimizer",
    "HRPOptimizer",
    "get_portfolio_optimizer",
]
