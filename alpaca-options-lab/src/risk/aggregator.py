"""
Alpaca Options Lab - Portfolio Risk Aggregator

Production-grade portfolio risk aggregation with:
- Multi-underlying Greeks aggregation
- Dollar Greeks for position sizing
- Correlation-adjusted risk metrics
- Stress testing scenarios

Greeks Aggregation Logic:
- Delta: Sum of position deltas (directional exposure)
- Gamma: Sum of gammas (acceleration risk)
- Theta: Sum of thetas (time decay)
- Vega: Sum of vegas (volatility exposure)
- Rho: Sum of rhos (rate sensitivity)

Dollar Greeks (for position sizing):
- Dollar Delta: Delta * Spot * Contracts * 100
- Dollar Gamma: Gamma * Spot^2 * 0.01 * Contracts * 100
- Dollar Theta: Theta * Contracts * 100
- Dollar Vega: Vega * Contracts * 100

Usage:
    from src.risk.aggregator import RiskAggregator, get_risk_aggregator
    
    aggregator = get_risk_aggregator()
    
    # Update with current Greeks
    aggregator.update_position_greeks("AAPL240119C00150000", greeks)
    
    # Get portfolio summary
    portfolio = aggregator.get_portfolio_greeks()
    print(f"Portfolio Delta: {portfolio.total_delta}")
    print(f"Dollar Delta: ${portfolio.dollar_delta:,.0f}")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from src.data.symbology import parse_osi_symbol
from src.pricing.black_scholes import Greeks
from src.utils.logging_config import get_logger
from src.utils.metrics import get_metrics

logger = get_logger(__name__)
metrics = get_metrics()


@dataclass
class PositionRisk:
    """Risk metrics for a single position."""
    symbol: str
    underlying: str
    quantity: int  # Positive = long, negative = short
    spot: float
    
    # Raw Greeks (per contract)
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    rho: float = 0.0
    
    # Position Greeks (adjusted for quantity)
    position_delta: float = 0.0
    position_gamma: float = 0.0
    position_theta: float = 0.0
    position_vega: float = 0.0
    position_rho: float = 0.0
    
    # Dollar Greeks
    dollar_delta: float = 0.0
    dollar_gamma: float = 0.0
    dollar_theta: float = 0.0
    dollar_vega: float = 0.0
    
    # Value metrics
    market_value: float = 0.0
    notional_value: float = 0.0
    
    # Metadata
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def from_greeks(
        cls,
        symbol: str,
        quantity: int,
        spot: float,
        greeks: Greeks,
        option_price: float = 0.0,
    ) -> "PositionRisk":
        """Create from Greeks dataclass."""
        option = parse_osi_symbol(symbol)
        multiplier = 100  # Standard option contract
        
        # Position-adjusted Greeks
        pos_delta = greeks.delta * quantity
        pos_gamma = greeks.gamma * quantity
        pos_theta = greeks.theta * quantity
        pos_vega = greeks.vega * quantity
        pos_rho = greeks.rho * quantity if hasattr(greeks, 'rho') else 0.0
        
        # Dollar Greeks
        # Delta: Change in value for $1 move in underlying
        dollar_delta = pos_delta * spot * multiplier
        
        # Gamma: Change in delta for 1% move (approximate)
        dollar_gamma = pos_gamma * (spot ** 2) * 0.01 * multiplier
        
        # Theta: Daily time decay in dollars
        dollar_theta = pos_theta * multiplier
        
        # Vega: Change in value for 1 vol point move
        dollar_vega = pos_vega * multiplier
        
        return cls(
            symbol=symbol,
            underlying=option.underlying,
            quantity=quantity,
            spot=spot,
            delta=greeks.delta,
            gamma=greeks.gamma,
            theta=greeks.theta,
            vega=greeks.vega,
            rho=greeks.rho if hasattr(greeks, 'rho') else 0.0,
            position_delta=pos_delta,
            position_gamma=pos_gamma,
            position_theta=pos_theta,
            position_vega=pos_vega,
            position_rho=pos_rho,
            dollar_delta=dollar_delta,
            dollar_gamma=dollar_gamma,
            dollar_theta=dollar_theta,
            dollar_vega=dollar_vega,
            market_value=option_price * quantity * multiplier,
            notional_value=spot * abs(quantity) * multiplier,
        )


@dataclass
class UnderlyingRisk:
    """Aggregated risk for a single underlying."""
    underlying: str
    spot: float
    
    # Aggregated Greeks
    total_delta: float = 0.0
    total_gamma: float = 0.0
    total_theta: float = 0.0
    total_vega: float = 0.0
    total_rho: float = 0.0
    
    # Dollar Greeks
    dollar_delta: float = 0.0
    dollar_gamma: float = 0.0
    dollar_theta: float = 0.0
    dollar_vega: float = 0.0
    
    # Position breakdown
    long_delta: float = 0.0
    short_delta: float = 0.0
    call_positions: int = 0
    put_positions: int = 0
    
    # Value metrics
    total_market_value: float = 0.0
    total_notional: float = 0.0
    
    # Risk metrics
    beta_adjusted_delta: float = 0.0  # If beta available
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "underlying": self.underlying,
            "spot": self.spot,
            "total_delta": round(self.total_delta, 4),
            "total_gamma": round(self.total_gamma, 6),
            "total_theta": round(self.total_theta, 2),
            "total_vega": round(self.total_vega, 2),
            "dollar_delta": round(self.dollar_delta, 2),
            "dollar_gamma": round(self.dollar_gamma, 2),
            "dollar_theta": round(self.dollar_theta, 2),
            "dollar_vega": round(self.dollar_vega, 2),
            "long_delta": round(self.long_delta, 4),
            "short_delta": round(self.short_delta, 4),
            "call_positions": self.call_positions,
            "put_positions": self.put_positions,
        }


@dataclass
class PortfolioGreeks:
    """
    Portfolio-level risk aggregation.
    
    Provides comprehensive view of all Greeks and risk metrics
    across the entire portfolio.
    """
    # Total Greeks (sum across all positions)
    total_delta: float = 0.0
    total_gamma: float = 0.0
    total_theta: float = 0.0
    total_vega: float = 0.0
    total_rho: float = 0.0
    
    # Dollar Greeks (for sizing)
    dollar_delta: float = 0.0
    dollar_gamma: float = 0.0
    dollar_theta: float = 0.0
    dollar_vega: float = 0.0
    
    # Directional breakdown
    long_delta: float = 0.0
    short_delta: float = 0.0
    net_delta: float = 0.0
    
    # Position counts
    total_positions: int = 0
    long_positions: int = 0
    short_positions: int = 0
    
    # Value metrics
    total_market_value: float = 0.0
    total_notional: float = 0.0
    
    # By underlying
    underlying_risks: Dict[str, UnderlyingRisk] = field(default_factory=dict)
    
    # Risk ratios
    theta_to_delta_ratio: float = 0.0  # Income vs directional
    gamma_to_theta_ratio: float = 0.0  # Convexity vs decay
    
    # Metadata
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_delta": round(self.total_delta, 4),
            "total_gamma": round(self.total_gamma, 6),
            "total_theta": round(self.total_theta, 2),
            "total_vega": round(self.total_vega, 2),
            "dollar_delta": round(self.dollar_delta, 2),
            "dollar_gamma": round(self.dollar_gamma, 2),
            "dollar_theta": round(self.dollar_theta, 2),
            "dollar_vega": round(self.dollar_vega, 2),
            "net_delta": round(self.net_delta, 4),
            "total_positions": self.total_positions,
            "total_market_value": round(self.total_market_value, 2),
            "total_notional": round(self.total_notional, 2),
            "theta_to_delta_ratio": round(self.theta_to_delta_ratio, 4),
            "underlying_count": len(self.underlying_risks),
        }


class RiskAggregator:
    """
    Portfolio-level risk aggregation engine.
    
    Features:
    - Real-time Greeks aggregation
    - Multi-underlying portfolio view
    - Dollar Greeks for position sizing
    - Beta-adjusted metrics (optional)
    - Stress testing scenarios
    
    Architecture:
    - Position-level Greeks stored in dictionary
    - Underlying-level aggregation computed on demand
    - Portfolio-level metrics computed from underlying
    
    Example:
        aggregator = RiskAggregator()
        
        # Update positions
        aggregator.update_position("AAPL240119C00150000", 10, 152.50, greeks)
        aggregator.update_position("AAPL240119P00145000", -5, 152.50, greeks)
        
        # Get portfolio view
        portfolio = aggregator.get_portfolio_greeks()
        
        # Get underlying breakdown
        aapl_risk = aggregator.get_underlying_risk("AAPL")
    """
    
    def __init__(
        self,
        beta_lookup: Optional[Dict[str, float]] = None,
    ) -> None:
        """
        Initialize the risk aggregator.
        
        Args:
            beta_lookup: Optional dict mapping underlying to beta vs benchmark
        """
        # Position-level risks
        self._positions: Dict[str, PositionRisk] = {}
        
        # Beta lookup for adjustment
        self._betas = beta_lookup or {}
        
        # Cache invalidation flag
        self._cache_valid = False
        self._cached_portfolio: Optional[PortfolioGreeks] = None
        
        logger.info("RiskAggregator initialized")
    
    def set_beta(self, underlying: str, beta: float) -> None:
        """Set beta for an underlying."""
        self._betas[underlying.upper()] = beta
        self._cache_valid = False
    
    def update_position(
        self,
        symbol: str,
        quantity: int,
        spot: float,
        greeks: Greeks,
        option_price: float = 0.0,
    ) -> PositionRisk:
        """
        Update or add a position's risk metrics.
        
        Args:
            symbol: OSI option symbol
            quantity: Number of contracts (negative for short)
            spot: Current underlying price
            greeks: Greeks for the position
            option_price: Current option price
            
        Returns:
            Updated PositionRisk
        """
        risk = PositionRisk.from_greeks(
            symbol=symbol,
            quantity=quantity,
            spot=spot,
            greeks=greeks,
            option_price=option_price,
        )
        
        self._positions[symbol] = risk
        self._cache_valid = False
        
        return risk
    
    def remove_position(self, symbol: str) -> bool:
        """Remove a position from tracking."""
        if symbol in self._positions:
            del self._positions[symbol]
            self._cache_valid = False
            return True
        return False
    
    def clear_all(self) -> None:
        """Clear all positions."""
        self._positions.clear()
        self._cache_valid = False
        self._cached_portfolio = None
    
    def get_position_risk(self, symbol: str) -> Optional[PositionRisk]:
        """Get risk metrics for a specific position."""
        return self._positions.get(symbol)
    
    def get_underlying_risk(self, underlying: str) -> Optional[UnderlyingRisk]:
        """Get aggregated risk for a specific underlying."""
        underlying = underlying.upper()
        
        # Filter positions for this underlying
        positions = [
            p for p in self._positions.values()
            if p.underlying == underlying
        ]
        
        if not positions:
            return None
        
        # Aggregate
        risk = UnderlyingRisk(
            underlying=underlying,
            spot=positions[0].spot,  # All should have same spot
        )
        
        for pos in positions:
            risk.total_delta += pos.position_delta
            risk.total_gamma += pos.position_gamma
            risk.total_theta += pos.position_theta
            risk.total_vega += pos.position_vega
            risk.total_rho += pos.position_rho
            
            risk.dollar_delta += pos.dollar_delta
            risk.dollar_gamma += pos.dollar_gamma
            risk.dollar_theta += pos.dollar_theta
            risk.dollar_vega += pos.dollar_vega
            
            risk.total_market_value += pos.market_value
            risk.total_notional += pos.notional_value
            
            if pos.position_delta > 0:
                risk.long_delta += pos.position_delta
            else:
                risk.short_delta += pos.position_delta
            
            option = parse_osi_symbol(pos.symbol)
            if option.option_type.is_call:
                risk.call_positions += 1
            else:
                risk.put_positions += 1
        
        # Beta adjustment
        beta = self._betas.get(underlying, 1.0)
        risk.beta_adjusted_delta = risk.total_delta * beta
        
        return risk
    
    def get_portfolio_greeks(self) -> PortfolioGreeks:
        """
        Get portfolio-level aggregated Greeks.
        
        Returns cached result if positions haven't changed.
        """
        if self._cache_valid and self._cached_portfolio is not None:
            return self._cached_portfolio
        
        portfolio = PortfolioGreeks()
        underlying_risks: Dict[str, UnderlyingRisk] = {}
        
        # Get unique underlyings
        underlyings = set(p.underlying for p in self._positions.values())
        
        for underlying in underlyings:
            ul_risk = self.get_underlying_risk(underlying)
            if ul_risk:
                underlying_risks[underlying] = ul_risk
                
                # Aggregate to portfolio level
                portfolio.total_delta += ul_risk.total_delta
                portfolio.total_gamma += ul_risk.total_gamma
                portfolio.total_theta += ul_risk.total_theta
                portfolio.total_vega += ul_risk.total_vega
                portfolio.total_rho += ul_risk.total_rho
                
                portfolio.dollar_delta += ul_risk.dollar_delta
                portfolio.dollar_gamma += ul_risk.dollar_gamma
                portfolio.dollar_theta += ul_risk.dollar_theta
                portfolio.dollar_vega += ul_risk.dollar_vega
                
                portfolio.long_delta += ul_risk.long_delta
                portfolio.short_delta += ul_risk.short_delta
                
                portfolio.total_market_value += ul_risk.total_market_value
                portfolio.total_notional += ul_risk.total_notional
        
        # Calculate net delta
        portfolio.net_delta = portfolio.long_delta + portfolio.short_delta
        
        # Count positions
        portfolio.total_positions = len(self._positions)
        portfolio.long_positions = sum(
            1 for p in self._positions.values() if p.quantity > 0
        )
        portfolio.short_positions = sum(
            1 for p in self._positions.values() if p.quantity < 0
        )
        
        # Risk ratios
        if portfolio.total_delta != 0:
            portfolio.theta_to_delta_ratio = (
                portfolio.total_theta / abs(portfolio.total_delta)
            )
        
        if portfolio.total_theta != 0:
            portfolio.gamma_to_theta_ratio = (
                portfolio.total_gamma / abs(portfolio.total_theta)
            )
        
        portfolio.underlying_risks = underlying_risks
        portfolio.calculated_at = datetime.now(timezone.utc)
        
        # Cache result
        self._cached_portfolio = portfolio
        self._cache_valid = True
        
        return portfolio
    
    def stress_test(
        self,
        spot_move_pct: float = 0.0,
        vol_move_pct: float = 0.0,
        days_forward: int = 0,
    ) -> Dict[str, float]:
        """
        Perform stress test on portfolio.
        
        Args:
            spot_move_pct: Percentage move in spot (e.g., -10 for -10%)
            vol_move_pct: Percentage move in vol (e.g., 20 for +20%)
            days_forward: Days to advance time
            
        Returns:
            Dict with estimated P&L impact
        """
        portfolio = self.get_portfolio_greeks()
        
        results = {
            "delta_pnl": 0.0,
            "gamma_pnl": 0.0,
            "theta_pnl": 0.0,
            "vega_pnl": 0.0,
            "total_pnl": 0.0,
        }
        
        # Delta P&L from spot move
        if spot_move_pct != 0:
            # First-order delta effect
            results["delta_pnl"] = portfolio.dollar_delta * (spot_move_pct / 100)
            
            # Second-order gamma effect
            results["gamma_pnl"] = 0.5 * portfolio.dollar_gamma * (spot_move_pct / 100) ** 2
        
        # Theta P&L from time decay
        if days_forward > 0:
            results["theta_pnl"] = portfolio.dollar_theta * days_forward
        
        # Vega P&L from vol move
        if vol_move_pct != 0:
            # Vega is per 1% vol move
            results["vega_pnl"] = portfolio.dollar_vega * vol_move_pct
        
        # Total
        results["total_pnl"] = sum([
            results["delta_pnl"],
            results["gamma_pnl"],
            results["theta_pnl"],
            results["vega_pnl"],
        ])
        
        return results
    
    def get_scenario_matrix(
        self,
        spot_moves: List[float] = [-10, -5, 0, 5, 10],
        vol_moves: List[float] = [-20, -10, 0, 10, 20],
    ) -> Dict[str, Dict[str, float]]:
        """
        Generate scenario analysis matrix.
        
        Args:
            spot_moves: List of spot move percentages
            vol_moves: List of vol move percentages
            
        Returns:
            Nested dict: spot_move -> vol_move -> P&L
        """
        matrix = {}
        
        for spot_move in spot_moves:
            matrix[f"spot_{spot_move}"] = {}
            
            for vol_move in vol_moves:
                result = self.stress_test(
                    spot_move_pct=spot_move,
                    vol_move_pct=vol_move,
                )
                matrix[f"spot_{spot_move}"][f"vol_{vol_move}"] = result["total_pnl"]
        
        return matrix


# =============================================================================
# MODULE-LEVEL UTILITIES
# =============================================================================

_risk_aggregator: Optional[RiskAggregator] = None


def get_risk_aggregator() -> RiskAggregator:
    """Get global risk aggregator instance."""
    global _risk_aggregator
    if _risk_aggregator is None:
        _risk_aggregator = RiskAggregator()
    return _risk_aggregator
