"""
Iron Condor Strategy Engine

An iron condor is a limited risk, limited profit strategy that benefits from low volatility
in the underlying security. It consists of four options:
- Buy 1 OTM put (lower strike)
- Sell 1 OTM put (higher strike)
- Sell 1 OTM call (lower strike)
- Buy 1 OTM call (higher strike)

The strategy profits when the underlying stays between the two short strikes.
"""

from dataclasses import dataclass
from typing import Tuple, Dict
import numpy as np


@dataclass
class IronCondorParams:
    """Parameters for an Iron Condor strategy"""
    underlying_price: float
    put_long_strike: float      # Buy put (lowest strike)
    put_short_strike: float     # Sell put
    call_short_strike: float    # Sell call
    call_long_strike: float     # Buy call (highest strike)
    premium_received: float     # Net credit received
    contracts: int = 1


class IronCondor:
    """
    Iron Condor Strategy Calculator
    
    Calculates P&L, breakevens, and risk metrics for iron condor positions.
    """
    
    def __init__(self, params: IronCondorParams):
        """
        Initialize Iron Condor with strategy parameters.
        
        Args:
            params: IronCondorParams with all position details
        """
        self.params = params
        self._validate_strikes()
    
    def _validate_strikes(self):
        """Validate that strikes are in proper order"""
        if not (self.params.put_long_strike < 
                self.params.put_short_strike < 
                self.params.call_short_strike < 
                self.params.call_long_strike):
            raise ValueError(
                "Strikes must be in order: put_long < put_short < call_short < call_long"
            )
    
    def calculate_max_profit(self) -> float:
        """
        Calculate maximum profit for the iron condor.
        
        Max profit occurs when underlying stays between short strikes at expiration.
        
        Returns:
            Maximum profit in dollars
        """
        # Max profit is the net credit received
        max_profit = self.params.premium_received * 100 * self.params.contracts
        return max_profit
    
    def calculate_max_loss(self) -> float:
        """
        Calculate maximum loss for the iron condor.
        
        Max loss occurs when underlying moves beyond either long strike at expiration.
        
        Returns:
            Maximum loss in dollars (positive number)
        """
        # Max loss is the width of either spread minus the credit received
        put_spread_width = self.params.put_short_strike - self.params.put_long_strike
        call_spread_width = self.params.call_long_strike - self.params.call_short_strike
        
        # Both spreads should have same width, but use max to be safe
        max_spread_width = max(put_spread_width, call_spread_width)
        
        # Max loss = (spread width - credit) * 100 * contracts
        max_loss = (max_spread_width - self.params.premium_received) * 100 * self.params.contracts
        
        return abs(max_loss)
    
    def get_breakevens(self) -> Tuple[float, float]:
        """
        Calculate breakeven points for the iron condor.
        
        Returns:
            Tuple of (lower_breakeven, upper_breakeven)
        """
        # Lower breakeven: short put strike - credit received
        lower_breakeven = self.params.put_short_strike - self.params.premium_received
        
        # Upper breakeven: short call strike + credit received
        upper_breakeven = self.params.call_short_strike + self.params.premium_received
        
        return (lower_breakeven, upper_breakeven)
    
    def get_risk_reward_ratio(self) -> float:
        """
        Calculate risk/reward ratio.
        
        Returns:
            Ratio of max_loss / max_profit
        """
        max_profit = self.calculate_max_profit()
        max_loss = self.calculate_max_loss()
        
        if max_profit == 0:
            return float('inf')
        
        return max_loss / max_profit
    
    def calculate_pnl_at_price(self, price: float) -> float:
        """
        Calculate P&L at a specific underlying price at expiration.
        
        Args:
            price: Underlying price at expiration
            
        Returns:
            P&L in dollars
        """
        # Calculate intrinsic value of each leg at expiration
        put_long_value = max(0, self.params.put_long_strike - price)
        put_short_value = max(0, self.params.put_short_strike - price)
        call_short_value = max(0, price - self.params.call_short_strike)
        call_long_value = max(0, price - self.params.call_long_strike)
        
        # Net value of position at expiration
        # Long positions: we own them (positive when ITM)
        # Short positions: we sold them (negative when ITM)
        total_value = (put_long_value - put_short_value - call_short_value + call_long_value)
        
        # Add the initial credit received
        pnl = (self.params.premium_received + total_value) * 100 * self.params.contracts
        
        return pnl
    
    def generate_pnl_curve(self, 
                          num_points: int = 100,
                          price_range_pct: float = 0.3) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate P&L curve data points for visualization.
        
        Args:
            num_points: Number of points to generate
            price_range_pct: Percentage range around current price (0.3 = ±30%)
            
        Returns:
            Tuple of (prices, pnls) as numpy arrays
        """
        # Generate price range centered on current price
        center = self.params.underlying_price
        price_min = center * (1 - price_range_pct)
        price_max = center * (1 + price_range_pct)
        
        prices = np.linspace(price_min, price_max, num_points)
        pnls = np.array([self.calculate_pnl_at_price(p) for p in prices])
        
        return prices, pnls
    
    def get_summary(self) -> Dict[str, float]:
        """
        Get complete summary of strategy metrics.
        
        Returns:
            Dictionary with all key metrics
        """
        lower_be, upper_be = self.get_breakevens()
        
        return {
            "underlying_price": self.params.underlying_price,
            "max_profit": self.calculate_max_profit(),
            "max_loss": self.calculate_max_loss(),
            "lower_breakeven": lower_be,
            "upper_breakeven": upper_be,
            "risk_reward_ratio": self.get_risk_reward_ratio(),
            "credit_received": self.params.premium_received * 100 * self.params.contracts,
            "put_spread_width": self.params.put_short_strike - self.params.put_long_strike,
            "call_spread_width": self.params.call_long_strike - self.params.call_short_strike,
            "profit_zone_width": upper_be - lower_be,
        }
