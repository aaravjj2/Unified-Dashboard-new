"""
Options Greeks Calculator
==========================
Real-time Greeks calculation using py_vollib_vectorized for speed.

Provides:
- Delta, Gamma, Theta, Vega, Rho for individual options
- Portfolio-level Greeks aggregation
- IV calculation from market prices
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Literal
from datetime import datetime, date

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Try to import vectorized vollib
try:
    from py_vollib_vectorized import vectorized_implied_volatility, get_all_greeks
    from py_vollib_vectorized.api import price_dataframe
    VOLLIB_AVAILABLE = True
except ImportError:
    logger.warning("py_vollib_vectorized not available, falling back to scipy")
    VOLLIB_AVAILABLE = False

# Fallback to scipy Black-Scholes
from scipy.stats import norm
from scipy.optimize import brentq


@dataclass
class OptionGreeks:
    """Greeks for a single option."""
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    iv: float
    
    def __repr__(self):
        return (f"Greeks(Δ={self.delta:.3f}, Γ={self.gamma:.4f}, "
                f"Θ={self.theta:.3f}, V={self.vega:.3f}, ρ={self.rho:.3f}, IV={self.iv:.2%})")


@dataclass
class PortfolioGreeks:
    """Aggregated Greeks for a portfolio of options."""
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    net_delta_shares: float  # Delta exposure in terms of shares
    
    def __repr__(self):
        return (f"PortfolioGreeks(Δ={self.delta:.2f}, Γ={self.gamma:.3f}, "
                f"Θ={self.theta:.2f}, V={self.vega:.2f}, Shares={self.net_delta_shares:.0f})")


class GreeksCalculator:
    """
    High-performance Greeks calculator.
    
    Uses py_vollib_vectorized for batch calculations when available,
    falls back to scipy Black-Scholes implementation.
    """
    
    def __init__(self, risk_free_rate: float = 0.05):
        """
        Initialize calculator.
        
        Args:
            risk_free_rate: Annualized risk-free rate (default 5%)
        """
        self.risk_free_rate = risk_free_rate
        self._use_vollib = VOLLIB_AVAILABLE
        logger.info(f"GreeksCalculator initialized (vollib={self._use_vollib})")
    
    def calculate_single(
        self,
        spot: float,
        strike: float,
        expiration: date,
        option_type: Literal["call", "put"],
        price: Optional[float] = None,
        iv: Optional[float] = None,
    ) -> OptionGreeks:
        """
        Calculate Greeks for a single option.
        
        Args:
            spot: Current underlying price
            strike: Option strike price
            expiration: Expiration date
            option_type: "call" or "put"
            price: Market price (for IV calculation)
            iv: Implied volatility (if known)
            
        Returns:
            OptionGreeks dataclass
        """
        # Calculate time to expiration in years
        if isinstance(expiration, str):
            expiration = datetime.strptime(expiration, "%Y-%m-%d").date()
        
        today = date.today()
        dte = (expiration - today).days
        t = max(dte / 365.0, 0.001)  # Avoid division by zero
        
        # Calculate IV if not provided
        if iv is None and price is not None:
            iv = self._calculate_iv(spot, strike, t, price, option_type)
        elif iv is None:
            iv = 0.20  # Default 20% IV
        
        # Calculate Greeks
        if self._use_vollib:
            return self._vollib_greeks(spot, strike, t, iv, option_type)
        else:
            return self._scipy_greeks(spot, strike, t, iv, option_type)
    
    def calculate_batch(
        self,
        options_df: pd.DataFrame,
        spot: float,
    ) -> pd.DataFrame:
        """
        Calculate Greeks for multiple options at once.
        
        Args:
            options_df: DataFrame with columns: strike, expiration, option_type, price/iv
            spot: Current underlying price
            
        Returns:
            DataFrame with added Greek columns
        """
        df = options_df.copy()
        
        # Calculate DTE
        today = pd.Timestamp.today().normalize()
        df['expiration'] = pd.to_datetime(df['expiration'])
        df['dte'] = (df['expiration'] - today).dt.days
        df['t'] = df['dte'].clip(lower=1) / 365.0
        
        # Ensure IV column exists
        if 'iv' not in df.columns:
            df['iv'] = 0.20  # Default
        
        if self._use_vollib and len(df) > 5:
            # Use vectorized calculation for large batches
            return self._vollib_batch(df, spot)
        else:
            # Calculate row by row
            greeks_list = []
            for _, row in df.iterrows():
                g = self.calculate_single(
                    spot=spot,
                    strike=row['strike'],
                    expiration=row['expiration'].date(),
                    option_type=row['option_type'],
                    iv=row.get('iv'),
                    price=row.get('price'),
                )
                greeks_list.append({
                    'delta': g.delta,
                    'gamma': g.gamma,
                    'theta': g.theta,
                    'vega': g.vega,
                    'rho': g.rho,
                    'iv': g.iv,
                })
            
            greeks_df = pd.DataFrame(greeks_list)
            return pd.concat([df.reset_index(drop=True), greeks_df], axis=1)
    
    def portfolio_greeks(
        self,
        positions: List[dict],
        spot: float,
    ) -> PortfolioGreeks:
        """
        Calculate aggregated Greeks for a portfolio.
        
        Args:
            positions: List of position dicts with keys:
                - strike, expiration, option_type, quantity, iv/price
            spot: Current underlying price
            
        Returns:
            PortfolioGreeks dataclass
        """
        total_delta = 0.0
        total_gamma = 0.0
        total_theta = 0.0
        total_vega = 0.0
        total_rho = 0.0
        
        for pos in positions:
            qty = pos.get('quantity', 1)
            multiplier = 100  # Standard option contract
            
            greeks = self.calculate_single(
                spot=spot,
                strike=pos['strike'],
                expiration=pos['expiration'],
                option_type=pos['option_type'],
                iv=pos.get('iv'),
                price=pos.get('price'),
            )
            
            # Aggregate (short positions have negative qty)
            total_delta += greeks.delta * qty * multiplier
            total_gamma += greeks.gamma * qty * multiplier
            total_theta += greeks.theta * qty * multiplier
            total_vega += greeks.vega * qty * multiplier
            total_rho += greeks.rho * qty * multiplier
        
        return PortfolioGreeks(
            delta=total_delta / 100,  # Normalize back
            gamma=total_gamma / 100,
            theta=total_theta / 100,
            vega=total_vega / 100,
            rho=total_rho / 100,
            net_delta_shares=total_delta,
        )
    
    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================
    
    def _calculate_iv(
        self,
        spot: float,
        strike: float,
        t: float,
        price: float,
        option_type: str,
    ) -> float:
        """Calculate IV from market price using Brent's method."""
        try:
            def objective(sigma):
                return self._bs_price(spot, strike, t, sigma, option_type) - price
            
            iv = brentq(objective, 0.001, 5.0, xtol=1e-6)
            return iv
        except Exception:
            return 0.20  # Default on failure
    
    def _bs_price(
        self,
        s: float,
        k: float,
        t: float,
        sigma: float,
        option_type: str,
    ) -> float:
        """Black-Scholes option price."""
        r = self.risk_free_rate
        
        d1 = (np.log(s / k) + (r + 0.5 * sigma ** 2) * t) / (sigma * np.sqrt(t))
        d2 = d1 - sigma * np.sqrt(t)
        
        if option_type == "call":
            return s * norm.cdf(d1) - k * np.exp(-r * t) * norm.cdf(d2)
        else:
            return k * np.exp(-r * t) * norm.cdf(-d2) - s * norm.cdf(-d1)
    
    def _scipy_greeks(
        self,
        s: float,
        k: float,
        t: float,
        sigma: float,
        option_type: str,
    ) -> OptionGreeks:
        """Calculate Greeks using scipy (Black-Scholes formulas)."""
        r = self.risk_free_rate
        
        d1 = (np.log(s / k) + (r + 0.5 * sigma ** 2) * t) / (sigma * np.sqrt(t))
        d2 = d1 - sigma * np.sqrt(t)
        
        # Delta
        if option_type == "call":
            delta = norm.cdf(d1)
        else:
            delta = norm.cdf(d1) - 1
        
        # Gamma (same for call and put)
        gamma = norm.pdf(d1) / (s * sigma * np.sqrt(t))
        
        # Theta (per day)
        if option_type == "call":
            theta = (-(s * norm.pdf(d1) * sigma) / (2 * np.sqrt(t))
                    - r * k * np.exp(-r * t) * norm.cdf(d2)) / 365
        else:
            theta = (-(s * norm.pdf(d1) * sigma) / (2 * np.sqrt(t))
                    + r * k * np.exp(-r * t) * norm.cdf(-d2)) / 365
        
        # Vega (per 1% change in IV)
        vega = s * norm.pdf(d1) * np.sqrt(t) / 100
        
        # Rho (per 1% change in rate)
        if option_type == "call":
            rho = k * t * np.exp(-r * t) * norm.cdf(d2) / 100
        else:
            rho = -k * t * np.exp(-r * t) * norm.cdf(-d2) / 100
        
        return OptionGreeks(
            delta=delta,
            gamma=gamma,
            theta=theta,
            vega=vega,
            rho=rho,
            iv=sigma,
        )
    
    def _vollib_greeks(
        self,
        s: float,
        k: float,
        t: float,
        sigma: float,
        option_type: str,
    ) -> OptionGreeks:
        """Calculate Greeks using py_vollib_vectorized."""
        flag = 'c' if option_type == "call" else 'p'
        
        try:
            # Create single-row DataFrame for vectorized function
            df = pd.DataFrame({
                'S': [s],
                'K': [k],
                'sigma': [sigma],
                'T': [t],
                'r': [self.risk_free_rate],
                'flag': [flag],
            })
            
            result = get_all_greeks(
                flag=df['flag'],
                S=df['S'],
                K=df['K'],
                t=df['T'],
                r=df['r'],
                sigma=df['sigma'],
                return_as='dataframe'
            )
            
            return OptionGreeks(
                delta=float(result['delta'].iloc[0]),
                gamma=float(result['gamma'].iloc[0]),
                theta=float(result['theta'].iloc[0]) / 365,  # Convert to daily
                vega=float(result['vega'].iloc[0]) / 100,  # Per 1% IV
                rho=float(result['rho'].iloc[0]) / 100,  # Per 1% rate
                iv=sigma,
            )
        except Exception as e:
            logger.warning(f"vollib failed, falling back to scipy: {e}")
            return self._scipy_greeks(s, k, t, sigma, option_type)
    
    def _vollib_batch(self, df: pd.DataFrame, spot: float) -> pd.DataFrame:
        """Batch calculation using py_vollib_vectorized."""
        df = df.copy()
        df['flag'] = df['option_type'].map({'call': 'c', 'put': 'p'})
        df['S'] = spot
        df['K'] = df['strike']
        df['r'] = self.risk_free_rate
        df['sigma'] = df['iv']
        
        try:
            greeks = get_all_greeks(
                flag=df['flag'],
                S=df['S'],
                K=df['K'],
                t=df['t'],
                r=df['r'],
                sigma=df['sigma'],
                return_as='dataframe'
            )
            
            df['delta'] = greeks['delta']
            df['gamma'] = greeks['gamma']
            df['theta'] = greeks['theta'] / 365
            df['vega'] = greeks['vega'] / 100
            df['rho'] = greeks['rho'] / 100
            
        except Exception as e:
            logger.warning(f"Batch vollib failed: {e}")
            # Fallback to row-by-row
            for idx, row in df.iterrows():
                g = self._scipy_greeks(spot, row['strike'], row['t'], row['iv'], row['option_type'])
                df.at[idx, 'delta'] = g.delta
                df.at[idx, 'gamma'] = g.gamma
                df.at[idx, 'theta'] = g.theta
                df.at[idx, 'vega'] = g.vega
                df.at[idx, 'rho'] = g.rho
        
        return df


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_calculator: Optional[GreeksCalculator] = None

def get_greeks_calculator() -> GreeksCalculator:
    """Get or create the global Greeks calculator."""
    global _calculator
    if _calculator is None:
        _calculator = GreeksCalculator()
    return _calculator


def calculate_greeks(
    spot: float,
    strike: float,
    expiration: date,
    option_type: str,
    iv: float = 0.20,
) -> OptionGreeks:
    """
    Convenience function to calculate Greeks for a single option.
    
    Example:
        greeks = calculate_greeks(
            spot=200.0,
            strike=205.0,
            expiration=date(2024, 3, 15),
            option_type="call",
            iv=0.25
        )
        print(f"Delta: {greeks.delta:.3f}")
    """
    calc = get_greeks_calculator()
    return calc.calculate_single(spot, strike, expiration, option_type, iv=iv)


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    from datetime import date, timedelta
    
    print("=" * 60)
    print("Testing Greeks Calculator")
    print("=" * 60)
    
    # Test single option
    calc = GreeksCalculator()
    
    expiry = date.today() + timedelta(days=45)
    
    call_greeks = calc.calculate_single(
        spot=200.0,
        strike=205.0,
        expiration=expiry,
        option_type="call",
        iv=0.25,
    )
    
    print(f"\nCall Option Greeks (K=205, IV=25%):")
    print(f"  {call_greeks}")
    
    put_greeks = calc.calculate_single(
        spot=200.0,
        strike=195.0,
        expiration=expiry,
        option_type="put",
        iv=0.25,
    )
    
    print(f"\nPut Option Greeks (K=195, IV=25%):")
    print(f"  {put_greeks}")
    
    # Test portfolio
    positions = [
        {"strike": 190, "expiration": expiry, "option_type": "put", "quantity": -1, "iv": 0.25},
        {"strike": 195, "expiration": expiry, "option_type": "put", "quantity": 1, "iv": 0.25},
    ]
    
    port_greeks = calc.portfolio_greeks(positions, spot=200.0)
    print(f"\nShort Put Spread Portfolio Greeks:")
    print(f"  {port_greeks}")
    
    print("\n✅ Greeks calculator working!")
