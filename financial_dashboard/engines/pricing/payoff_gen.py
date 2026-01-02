"""
Payoff Generator for Options Strategies

Generates coordinate arrays (price, P&L) for strategy visualization at different time horizons.
Supports T+0 (today) and T+Expiry (at expiration) scenarios.
"""

import numpy as np
from typing import Tuple, Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class OptionLeg:
    """Single option leg in a strategy"""
    strike: float
    option_type: str  # 'call' or 'put'
    position: str     # 'long' or 'short'
    premium: float    # Premium per share
    quantity: int = 1


class PayoffGenerator:
    """
    Generate payoff curves for options strategies.
    
    Handles multi-leg strategies and calculates P&L at various price points
    for both current time (with time decay) and expiration.
    """
    
    def __init__(self, 
                 underlying_price: float,
                 legs: List[OptionLeg],
                 days_to_expiry: int = 30):
        """
        Initialize payoff generator.
        
        Args:
            underlying_price: Current price of underlying
            legs: List of OptionLeg objects defining the strategy
            days_to_expiry: Days until expiration
        """
        self.underlying_price = underlying_price
        self.legs = legs
        self.days_to_expiry = days_to_expiry
    
    def calculate_intrinsic_value(self, 
                                  price: float, 
                                  strike: float, 
                                  option_type: str) -> float:
        """
        Calculate intrinsic value of an option.
        
        Args:
            price: Current underlying price
            strike: Option strike price
            option_type: 'call' or 'put'
            
        Returns:
            Intrinsic value per share
        """
        if option_type.lower() == 'call':
            return max(0, price - strike)
        else:  # put
            return max(0, strike - price)
    
    def calculate_time_value(self,
                           price: float,
                           strike: float,
                           option_type: str,
                           days_remaining: int,
                           implied_vol: float = 0.20) -> float:
        """
        Estimate time value using simplified approximation.
        
        This is a simplified model. For production, use Black-Scholes or actual market data.
        
        Args:
            price: Current underlying price
            strike: Option strike price
            option_type: 'call' or 'put'
            days_remaining: Days until expiration
            implied_vol: Implied volatility (default 20%)
            
        Returns:
            Time value per share
        """
        if days_remaining <= 0:
            return 0.0
        
        # Simplified time value decay model
        # Time value is higher for ATM options and decays with time
        moneyness = abs(price - strike) / strike
        atm_factor = max(0, 1 - moneyness * 2)  # Peaks at ATM, decays as we move OTM/ITM
        
        # Time decay factor (square root of time)
        time_factor = np.sqrt(days_remaining / 365.0)
        
        # Volatility factor
        vol_factor = implied_vol * price
        
        # Combine factors
        time_value = atm_factor * time_factor * vol_factor * 0.1
        
        return max(0, time_value)
    
    def calculate_option_value(self,
                              price: float,
                              strike: float,
                              option_type: str,
                              days_remaining: int) -> float:
        """
        Calculate total option value (intrinsic + time).
        
        Args:
            price: Current underlying price
            strike: Option strike price
            option_type: 'call' or 'put'
            days_remaining: Days until expiration
            
        Returns:
            Total option value per share
        """
        intrinsic = self.calculate_intrinsic_value(price, strike, option_type)
        time_val = self.calculate_time_value(price, strike, option_type, days_remaining)
        
        return intrinsic + time_val
    
    def calculate_position_pnl(self,
                              price: float,
                              days_remaining: int) -> float:
        """
        Calculate total P&L for all legs at a given price and time.
        
        Args:
            price: Underlying price
            days_remaining: Days until expiration (0 = at expiration)
            
        Returns:
            Total P&L in dollars
        """
        total_pnl = 0.0
        
        for leg in self.legs:
            # Calculate current option value
            current_value = self.calculate_option_value(
                price, leg.strike, leg.option_type, days_remaining
            )
            
            # Calculate P&L for this leg
            # Long: profit when value > premium paid
            # Short: profit when value < premium received
            if leg.position.lower() == 'long':
                leg_pnl = (current_value - leg.premium) * 100 * leg.quantity
            else:  # short
                leg_pnl = (leg.premium - current_value) * 100 * leg.quantity
            
            total_pnl += leg_pnl
        
        return total_pnl
    
    def generate_payoff_at_expiry(self,
                                 num_points: int = 100,
                                 price_range_pct: float = 0.30) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate P&L curve at expiration (T+Expiry).
        
        Args:
            num_points: Number of price points to generate
            price_range_pct: Price range as percentage (0.30 = ±30%)
            
        Returns:
            Tuple of (prices, pnls) as numpy arrays
        """
        # Generate price range
        price_min = self.underlying_price * (1 - price_range_pct)
        price_max = self.underlying_price * (1 + price_range_pct)
        prices = np.linspace(price_min, price_max, num_points)
        
        # Calculate P&L at expiration (days_remaining = 0)
        pnls = np.array([self.calculate_position_pnl(p, 0) for p in prices])
        
        return prices, pnls
    
    def generate_payoff_today(self,
                             num_points: int = 100,
                             price_range_pct: float = 0.30) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate P&L curve for today (T+0) including time value.
        
        Args:
            num_points: Number of price points to generate
            price_range_pct: Price range as percentage (0.30 = ±30%)
            
        Returns:
            Tuple of (prices, pnls) as numpy arrays
        """
        # Generate price range
        price_min = self.underlying_price * (1 - price_range_pct)
        price_max = self.underlying_price * (1 + price_range_pct)
        prices = np.linspace(price_min, price_max, num_points)
        
        # Calculate P&L today (with full days remaining)
        pnls = np.array([
            self.calculate_position_pnl(p, self.days_to_expiry) 
            for p in prices
        ])
        
        return prices, pnls
    
    def generate_multi_timeframe_payoff(self,
                                       timeframes: Optional[List[int]] = None,
                                       num_points: int = 100,
                                       price_range_pct: float = 0.30) -> Dict[int, Tuple[np.ndarray, np.ndarray]]:
        """
        Generate P&L curves for multiple timeframes.
        
        Args:
            timeframes: List of days remaining (None = [current, expiry])
            num_points: Number of price points
            price_range_pct: Price range as percentage
            
        Returns:
            Dictionary mapping days_remaining -> (prices, pnls)
        """
        if timeframes is None:
            timeframes = [self.days_to_expiry, self.days_to_expiry // 2, 0]
        
        result = {}
        price_min = self.underlying_price * (1 - price_range_pct)
        price_max = self.underlying_price * (1 + price_range_pct)
        prices = np.linspace(price_min, price_max, num_points)
        
        for days in timeframes:
            pnls = np.array([self.calculate_position_pnl(p, days) for p in prices])
            result[days] = (prices, pnls)
        
        return result
    
    def get_max_profit(self) -> float:
        """
        Calculate theoretical max profit at expiration.
        
        Returns:
            Maximum profit in dollars
        """
        # Sample across price range
        prices = np.linspace(
            self.underlying_price * 0.5,
            self.underlying_price * 1.5,
            500
        )
        pnls = [self.calculate_position_pnl(p, 0) for p in prices]
        return max(pnls)
    
    def get_max_loss(self) -> float:
        """
        Calculate theoretical max loss at expiration.
        
        Returns:
            Maximum loss in dollars (positive number)
        """
        # Sample across price range
        prices = np.linspace(
            self.underlying_price * 0.5,
            self.underlying_price * 1.5,
            500
        )
        pnls = [self.calculate_position_pnl(p, 0) for p in prices]
        return abs(min(pnls))
    
    def find_breakevens(self, tolerance: float = 1.0) -> List[float]:
        """
        Find breakeven points where P&L crosses zero at expiration.
        
        Args:
            tolerance: P&L tolerance for considering a breakeven
            
        Returns:
            List of breakeven prices
        """
        prices = np.linspace(
            self.underlying_price * 0.5,
            self.underlying_price * 1.5,
            1000
        )
        pnls = np.array([self.calculate_position_pnl(p, 0) for p in prices])
        
        # Find zero crossings
        breakevens = []
        for i in range(len(pnls) - 1):
            if abs(pnls[i]) < tolerance:
                breakevens.append(prices[i])
            elif pnls[i] * pnls[i + 1] < 0:  # Sign change
                # Linear interpolation to find exact crossing
                be = prices[i] + (prices[i + 1] - prices[i]) * (-pnls[i] / (pnls[i + 1] - pnls[i]))
                breakevens.append(be)
        
        # Remove duplicates within tolerance
        unique_breakevens = []
        for be in breakevens:
            if not any(abs(be - existing) < 5.0 for existing in unique_breakevens):
                unique_breakevens.append(be)
        
        return sorted(unique_breakevens)
