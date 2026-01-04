"""
Alpaca Options Lab - Risk Analytics

Portfolio risk analysis:
- Value at Risk (VaR)
- Greeks aggregation
- Stress testing
- Correlation analysis
- Position limits monitoring
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from scipy import stats

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class Position:
    """Single position."""
    symbol: str
    quantity: int  # Positive for long, negative for short
    entry_price: float
    current_price: float
    
    # Greeks (per contract)
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    rho: float = 0.0
    
    # Underlying
    underlying_symbol: str = ""
    underlying_price: float = 0.0
    
    # Contract details
    multiplier: int = 100
    is_option: bool = True
    
    @property
    def market_value(self) -> float:
        """Current market value."""
        return self.quantity * self.current_price * self.multiplier
    
    @property
    def total_delta(self) -> float:
        """Position delta (in underlying shares)."""
        return self.delta * self.quantity * self.multiplier
    
    @property
    def total_gamma(self) -> float:
        """Position gamma."""
        return self.gamma * self.quantity * self.multiplier
    
    @property
    def total_theta(self) -> float:
        """Position theta (daily)."""
        return self.theta * self.quantity
    
    @property
    def total_vega(self) -> float:
        """Position vega (per 1% IV move)."""
        return self.vega * self.quantity


@dataclass
class PortfolioRisk:
    """Portfolio-level risk metrics."""
    # Total Greeks
    total_delta: float
    total_gamma: float
    total_theta: float
    total_vega: float
    total_rho: float
    
    # Risk measures
    delta_dollars: float  # Delta in dollar terms
    gamma_dollars: float  # Gamma in dollar terms
    
    # Concentration
    max_position_pct: float
    top_5_concentration: float
    
    # Limits
    delta_limit_used_pct: float
    theta_limit_used_pct: float
    
    # P&L estimates
    pnl_1_sigma_up: float
    pnl_1_sigma_down: float
    pnl_vol_up_5: float   # P&L if vol +5%
    pnl_vol_down_5: float # P&L if vol -5%


@dataclass
class StressTest:
    """Stress test scenario result."""
    scenario_name: str
    description: str
    
    # Scenario parameters
    price_change_pct: float
    vol_change_pct: float
    
    # Results
    pnl: float
    pnl_pct: float
    max_loss_position: str
    
    # Greeks after stress
    stressed_delta: float
    stressed_gamma: float
    
    # Optional parameters with defaults (must come last)
    time_change_days: int = 0


@dataclass
class CorrelationMatrix:
    """Correlation analysis."""
    symbols: List[str]
    matrix: np.ndarray
    period_days: int
    
    def get_correlation(self, sym1: str, sym2: str) -> Optional[float]:
        """Get correlation between two symbols."""
        if sym1 not in self.symbols or sym2 not in self.symbols:
            return None
        
        i = self.symbols.index(sym1)
        j = self.symbols.index(sym2)
        return float(self.matrix[i, j])
    
    def get_high_correlations(self, threshold: float = 0.7) -> List[Tuple[str, str, float]]:
        """Find highly correlated pairs."""
        pairs = []
        n = len(self.symbols)
        
        for i in range(n):
            for j in range(i + 1, n):
                corr = self.matrix[i, j]
                if abs(corr) >= threshold:
                    pairs.append((self.symbols[i], self.symbols[j], float(corr)))
        
        return sorted(pairs, key=lambda x: abs(x[2]), reverse=True)


class VaRCalculator:
    """
    Value at Risk calculator.
    
    Methods:
    - Historical VaR
    - Parametric VaR
    - Monte Carlo VaR
    """
    
    def __init__(
        self,
        confidence_level: float = 0.95,
        holding_period_days: int = 1,
    ):
        self.confidence_level = confidence_level
        self.holding_period = holding_period_days
    
    def historical_var(
        self,
        returns: List[float],
        portfolio_value: float,
    ) -> float:
        """
        Calculate historical VaR.
        
        Args:
            returns: Historical daily returns
            portfolio_value: Current portfolio value
        
        Returns:
            VaR in dollar terms
        """
        if len(returns) < 10:
            return 0
        
        percentile = (1 - self.confidence_level) * 100
        var_pct = np.percentile(returns, percentile)
        
        # Scale for holding period
        var_scaled = var_pct * np.sqrt(self.holding_period)
        
        return abs(var_scaled * portfolio_value)
    
    def parametric_var(
        self,
        mean_return: float,
        std_return: float,
        portfolio_value: float,
    ) -> float:
        """
        Calculate parametric (variance-covariance) VaR.
        
        Assumes normal distribution.
        """
        z_score = stats.norm.ppf(1 - self.confidence_level)
        
        var = (mean_return - z_score * std_return) * np.sqrt(self.holding_period)
        
        return abs(var * portfolio_value)
    
    def monte_carlo_var(
        self,
        mean_return: float,
        std_return: float,
        portfolio_value: float,
        num_simulations: int = 10000,
    ) -> float:
        """
        Calculate Monte Carlo VaR.
        
        Simulates random returns based on distribution.
        """
        # Generate random returns
        simulated_returns = np.random.normal(
            mean_return,
            std_return,
            (num_simulations, self.holding_period),
        )
        
        # Compound returns over holding period
        cumulative_returns = np.prod(1 + simulated_returns, axis=1) - 1
        
        # Calculate VaR
        percentile = (1 - self.confidence_level) * 100
        var_pct = np.percentile(cumulative_returns, percentile)
        
        return abs(var_pct * portfolio_value)
    
    def expected_shortfall(
        self,
        returns: List[float],
        portfolio_value: float,
    ) -> float:
        """
        Calculate Expected Shortfall (Conditional VaR).
        
        Average loss beyond VaR threshold.
        """
        if len(returns) < 10:
            return 0
        
        percentile = (1 - self.confidence_level) * 100
        threshold = np.percentile(returns, percentile)
        
        # Average of returns below threshold
        tail_returns = [r for r in returns if r <= threshold]
        if not tail_returns:
            return 0
        
        es_pct = np.mean(tail_returns)
        es_scaled = es_pct * np.sqrt(self.holding_period)
        
        return abs(es_scaled * portfolio_value)


class RiskAnalyzer:
    """
    Portfolio risk analyzer.
    
    Aggregates positions and calculates portfolio-level risk.
    """
    
    def __init__(
        self,
        portfolio_value: float = 100000.0,
    ):
        self.portfolio_value = portfolio_value
        
        # Positions
        self._positions: List[Position] = []
        
        # Historical returns for VaR
        self._returns_history: Dict[str, List[float]] = {}
        
        # Risk limits
        self.delta_limit = 1000  # In delta dollars
        self.theta_limit = -500  # Max daily theta burn
        self.concentration_limit = 0.25  # Max 25% in single position
        
        # VaR calculator
        self.var_calc = VaRCalculator()
        
        logger.info(f"RiskAnalyzer initialized: portfolio={portfolio_value}")
    
    # -------------------- Position Management --------------------
    
    def add_position(self, position: Position) -> None:
        """Add a position."""
        self._positions.append(position)
    
    def update_position(
        self,
        symbol: str,
        current_price: float,
        delta: Optional[float] = None,
        gamma: Optional[float] = None,
        theta: Optional[float] = None,
        vega: Optional[float] = None,
    ) -> None:
        """Update position with current market data."""
        for pos in self._positions:
            if pos.symbol == symbol:
                pos.current_price = current_price
                if delta is not None:
                    pos.delta = delta
                if gamma is not None:
                    pos.gamma = gamma
                if theta is not None:
                    pos.theta = theta
                if vega is not None:
                    pos.vega = vega
                break
    
    def add_returns_history(
        self,
        symbol: str,
        returns: List[float],
    ) -> None:
        """Add return history for a symbol."""
        self._returns_history[symbol] = returns
    
    # -------------------- Risk Analysis --------------------
    
    def analyze_portfolio(self) -> PortfolioRisk:
        """
        Analyze portfolio risk.
        
        Returns:
            PortfolioRisk with aggregate metrics
        """
        if not self._positions:
            return self._empty_risk()
        
        # Aggregate Greeks
        total_delta = sum(p.total_delta for p in self._positions)
        total_gamma = sum(p.total_gamma for p in self._positions)
        total_theta = sum(p.total_theta for p in self._positions)
        total_vega = sum(p.total_vega for p in self._positions)
        total_rho = sum(p.rho * p.quantity for p in self._positions)
        
        # Dollar Greeks
        # Delta dollars = delta * underlying price
        delta_dollars = sum(
            p.total_delta * p.underlying_price
            for p in self._positions
        )
        
        # Gamma dollars = gamma * underlying price^2 / 2
        gamma_dollars = sum(
            p.total_gamma * (p.underlying_price ** 2) / 200
            for p in self._positions
        )
        
        # Concentration
        market_values = [abs(p.market_value) for p in self._positions]
        total_abs_value = sum(market_values) if market_values else 1
        
        max_position_pct = max(market_values) / total_abs_value * 100 if market_values else 0
        
        sorted_values = sorted(market_values, reverse=True)
        top_5_value = sum(sorted_values[:5])
        top_5_concentration = top_5_value / total_abs_value * 100 if total_abs_value > 0 else 0
        
        # Limit usage
        delta_limit_used = abs(delta_dollars) / self.delta_limit * 100 if self.delta_limit else 0
        theta_limit_used = abs(total_theta) / abs(self.theta_limit) * 100 if self.theta_limit else 0
        
        # Scenario P&L estimates
        # 1 sigma move (approx 1% for daily)
        pnl_1_sigma_up = delta_dollars * 0.01 + gamma_dollars * (0.01 ** 2)
        pnl_1_sigma_down = -delta_dollars * 0.01 + gamma_dollars * (0.01 ** 2)
        
        # Vol scenarios
        pnl_vol_up_5 = total_vega * 5  # +5% IV
        pnl_vol_down_5 = -total_vega * 5  # -5% IV
        
        return PortfolioRisk(
            total_delta=total_delta,
            total_gamma=total_gamma,
            total_theta=total_theta,
            total_vega=total_vega,
            total_rho=total_rho,
            delta_dollars=delta_dollars,
            gamma_dollars=gamma_dollars,
            max_position_pct=max_position_pct,
            top_5_concentration=top_5_concentration,
            delta_limit_used_pct=delta_limit_used,
            theta_limit_used_pct=theta_limit_used,
            pnl_1_sigma_up=pnl_1_sigma_up,
            pnl_1_sigma_down=pnl_1_sigma_down,
            pnl_vol_up_5=pnl_vol_up_5,
            pnl_vol_down_5=pnl_vol_down_5,
        )
    
    def _empty_risk(self) -> PortfolioRisk:
        """Return empty risk metrics."""
        return PortfolioRisk(
            total_delta=0, total_gamma=0, total_theta=0,
            total_vega=0, total_rho=0,
            delta_dollars=0, gamma_dollars=0,
            max_position_pct=0, top_5_concentration=0,
            delta_limit_used_pct=0, theta_limit_used_pct=0,
            pnl_1_sigma_up=0, pnl_1_sigma_down=0,
            pnl_vol_up_5=0, pnl_vol_down_5=0,
        )
    
    # -------------------- Stress Testing --------------------
    
    def run_stress_test(
        self,
        price_change_pct: float,
        vol_change_pct: float = 0,
        time_change_days: int = 0,
    ) -> StressTest:
        """
        Run stress test scenario.
        
        Args:
            price_change_pct: % change in underlying prices
            vol_change_pct: % change in IV
            time_change_days: Days of theta decay
        
        Returns:
            StressTest with scenario results
        """
        if not self._positions:
            return StressTest(
                scenario_name="empty",
                description="No positions",
                price_change_pct=price_change_pct,
                vol_change_pct=vol_change_pct,
                pnl=0, pnl_pct=0,
                max_loss_position="",
                stressed_delta=0, stressed_gamma=0,
            )
        
        total_pnl = 0
        position_pnls = {}
        
        for pos in self._positions:
            # Delta P&L
            delta_pnl = pos.total_delta * pos.underlying_price * (price_change_pct / 100)
            
            # Gamma P&L (second order)
            gamma_pnl = 0.5 * pos.total_gamma * (pos.underlying_price * price_change_pct / 100) ** 2
            
            # Vega P&L
            vega_pnl = pos.total_vega * vol_change_pct
            
            # Theta P&L
            theta_pnl = pos.total_theta * time_change_days
            
            pos_pnl = delta_pnl + gamma_pnl + vega_pnl + theta_pnl
            position_pnls[pos.symbol] = pos_pnl
            total_pnl += pos_pnl
        
        # Find max loss position
        max_loss_position = min(position_pnls.items(), key=lambda x: x[1])[0]
        
        # Stressed Greeks
        stressed_delta = sum(
            p.total_delta * (1 + price_change_pct / 100 * p.gamma / p.delta)
            if p.delta != 0 else p.total_delta
            for p in self._positions
        )
        stressed_gamma = sum(p.total_gamma for p in self._positions)
        
        return StressTest(
            scenario_name=f"price_{price_change_pct:+.0f}_vol_{vol_change_pct:+.0f}",
            description=f"Price {price_change_pct:+.1f}%, Vol {vol_change_pct:+.1f}%",
            price_change_pct=price_change_pct,
            vol_change_pct=vol_change_pct,
            time_change_days=time_change_days,
            pnl=total_pnl,
            pnl_pct=total_pnl / self.portfolio_value * 100,
            max_loss_position=max_loss_position,
            stressed_delta=stressed_delta,
            stressed_gamma=stressed_gamma,
        )
    
    def run_standard_scenarios(self) -> List[StressTest]:
        """Run standard stress test scenarios."""
        scenarios = [
            (-5, 0, "5% market decline"),
            (-10, 0, "10% market decline"),
            (-20, 0, "20% crash"),
            (5, 0, "5% rally"),
            (10, 0, "10% rally"),
            (0, 10, "Vol spike +10%"),
            (0, -10, "Vol crush -10%"),
            (-10, 20, "Crash + vol spike"),
            (0, 0, 7, "1 week theta decay"),
        ]
        
        results = []
        for scenario in scenarios:
            if len(scenario) == 3:
                price, vol, desc = scenario
                time = 0
            else:
                price, vol, time, desc = scenario[0], scenario[1], scenario[2], scenario[3] if len(scenario) > 3 else ""
            
            test = self.run_stress_test(price, vol, time)
            test.description = desc
            results.append(test)
        
        return results
    
    # -------------------- Correlation Analysis --------------------
    
    def calculate_correlation_matrix(
        self,
        period_days: int = 60,
    ) -> Optional[CorrelationMatrix]:
        """
        Calculate correlation matrix for underlying symbols.
        """
        # Get unique underlyings
        underlyings = list(set(p.underlying_symbol for p in self._positions if p.underlying_symbol))
        
        if len(underlyings) < 2:
            return None
        
        # Check we have returns for all
        available = [s for s in underlyings if s in self._returns_history]
        if len(available) < 2:
            return None
        
        # Build return matrix
        min_len = min(len(self._returns_history[s]) for s in available)
        returns_matrix = np.array([
            self._returns_history[s][-min_len:]
            for s in available
        ])
        
        # Calculate correlation
        corr_matrix = np.corrcoef(returns_matrix)
        
        return CorrelationMatrix(
            symbols=available,
            matrix=corr_matrix,
            period_days=min_len,
        )
    
    # -------------------- Limits and Alerts --------------------
    
    def check_limits(self) -> List[Dict[str, Any]]:
        """Check risk limit breaches."""
        alerts = []
        risk = self.analyze_portfolio()
        
        # Delta limit
        if risk.delta_limit_used_pct > 100:
            alerts.append({
                "type": "limit_breach",
                "metric": "delta",
                "current": risk.delta_dollars,
                "limit": self.delta_limit,
                "severity": "high",
            })
        elif risk.delta_limit_used_pct > 80:
            alerts.append({
                "type": "limit_warning",
                "metric": "delta",
                "usage_pct": risk.delta_limit_used_pct,
                "severity": "medium",
            })
        
        # Theta limit
        if risk.theta_limit_used_pct > 100:
            alerts.append({
                "type": "limit_breach",
                "metric": "theta",
                "current": risk.total_theta,
                "limit": self.theta_limit,
                "severity": "high",
            })
        
        # Concentration
        if risk.max_position_pct > self.concentration_limit * 100:
            alerts.append({
                "type": "concentration",
                "max_position_pct": risk.max_position_pct,
                "limit_pct": self.concentration_limit * 100,
                "severity": "medium",
            })
        
        return alerts
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get risk summary."""
        risk = self.analyze_portfolio()
        
        return {
            "portfolio_value": f"${self.portfolio_value:,.0f}",
            "delta_dollars": f"${risk.delta_dollars:,.0f}",
            "gamma_dollars": f"${risk.gamma_dollars:,.0f}",
            "daily_theta": f"${risk.total_theta:,.2f}",
            "total_vega": f"${risk.total_vega:,.2f}",
            "delta_limit_used": f"{risk.delta_limit_used_pct:.1f}%",
            "max_position_pct": f"{risk.max_position_pct:.1f}%",
            "pnl_1_sigma_up": f"${risk.pnl_1_sigma_up:,.0f}",
            "pnl_1_sigma_down": f"${risk.pnl_1_sigma_down:,.0f}",
            "num_positions": len(self._positions),
        }
    
    def clear(self) -> None:
        """Clear all data."""
        self._positions.clear()
        self._returns_history.clear()
