"""
Implied Volatility Surface Calculator
Implements Black-Scholes option pricing and IV inversion using Newton-Raphson method.

Features:
- Vectorized IV calculation for performance
- Robust Newton-Raphson with fallback to bisection
- IV surface interpolation for sparse strike grids
- Greeks calculation (delta, gamma, vega, theta)

Mathematical Foundation:
- Black-Scholes-Merton model for European options
- Newton-Raphson inversion for implied volatility
- Thin-plate spline interpolation for surface smoothing

Author: Phase 0.9B - Volatility Lab Full Implementation
"""
import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.interpolate import griddata, Rbf
from typing import Optional, Tuple, Dict, List
import logging

logger = logging.getLogger(__name__)

# Constants
TRADING_DAYS_PER_YEAR = 252
RISK_FREE_RATE = 0.05  # Default 5% risk-free rate (can be overridden)


def black_scholes_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = 'call'
) -> float:
    """
    Calculate Black-Scholes option price.
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (years)
        r: Risk-free rate (annual)
        sigma: Volatility (annual)
        option_type: 'call' or 'put'
        
    Returns:
        Option price
        
    Formula:
        C = S * N(d1) - K * exp(-rT) * N(d2)
        P = K * exp(-rT) * N(-d2) - S * N(-d1)
        
        where:
        d1 = [ln(S/K) + (r + σ²/2)T] / (σ√T)
        d2 = d1 - σ√T
    """
    if T <= 0:
        # At expiration
        if option_type == 'call':
            return max(S - K, 0)
        else:
            return max(K - S, 0)
    
    if sigma <= 0:
        sigma = 0.001  # Prevent division by zero
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type == 'call':
        price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:  # put
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    
    return price


def vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Calculate option vega (sensitivity to volatility changes).
    
    Vega = S * φ(d1) * √T
    where φ is the standard normal PDF
    
    Used in Newton-Raphson iteration for IV calculation.
    """
    if T <= 0 or sigma <= 0:
        return 0.001  # Prevent division by zero
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    vega_value = S * norm.pdf(d1) * np.sqrt(T)
    
    return max(vega_value, 0.001)  # Prevent division by zero


def implied_volatility_newton(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: str = 'call',
    initial_guess: float = 0.25,
    max_iterations: int = 100,
    tolerance: float = 1e-6
) -> Optional[float]:
    """
    Calculate implied volatility using Newton-Raphson method.
    
    Args:
        market_price: Observed market price of option
        S: Current stock price
        K: Strike price
        T: Time to expiration (years)
        r: Risk-free rate
        option_type: 'call' or 'put'
        initial_guess: Starting volatility estimate
        max_iterations: Maximum Newton-Raphson iterations
        tolerance: Convergence tolerance
        
    Returns:
        Implied volatility (annualized) or None if failed to converge
        
    Algorithm:
        σ_(n+1) = σ_n - [BS(σ_n) - Market Price] / Vega(σ_n)
    """
    # Edge cases
    if T <= 0:
        return None
    
    if option_type == 'call' and market_price >= S:
        return None  # Deep ITM call, IV undefined
    
    if option_type == 'put' and market_price >= K:
        return None  # Deep ITM put, IV undefined
    
    sigma = initial_guess
    
    for i in range(max_iterations):
        # Calculate theoretical price and vega
        price = black_scholes_price(S, K, T, r, sigma, option_type)
        vega_val = vega(S, K, T, r, sigma)
        
        # Newton-Raphson update
        price_diff = price - market_price
        
        if abs(price_diff) < tolerance:
            return sigma  # Converged
        
        # Update sigma
        sigma = sigma - price_diff / vega_val
        
        # Bound sigma to reasonable range
        sigma = max(0.001, min(sigma, 5.0))  # 0.1% to 500%
    
    # Did not converge
    logger.warning(f"IV Newton-Raphson did not converge for K={K}, T={T}")
    return None


def implied_volatility_bisection(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: str = 'call',
    vol_min: float = 0.001,
    vol_max: float = 5.0,
    max_iterations: int = 100,
    tolerance: float = 1e-6
) -> Optional[float]:
    """
    Calculate implied volatility using bisection method (fallback for Newton-Raphson).
    
    More robust but slower than Newton-Raphson.
    """
    if T <= 0:
        return None
    
    for i in range(max_iterations):
        sigma = (vol_min + vol_max) / 2
        price = black_scholes_price(S, K, T, r, sigma, option_type)
        
        if abs(price - market_price) < tolerance:
            return sigma
        
        if price > market_price:
            vol_max = sigma
        else:
            vol_min = sigma
    
    return None


def calculate_iv_surface(
    options_df: pd.DataFrame,
    underlying_price: float,
    risk_free_rate: float = RISK_FREE_RATE
) -> pd.DataFrame:
    """
    Calculate implied volatility for all options in a dataframe.
    
    Args:
        options_df: DataFrame with columns: strike, expiration_date, option_type, bid, ask
        underlying_price: Current stock price
        risk_free_rate: Annual risk-free rate
        
    Returns:
        DataFrame with additional 'implied_vol' column
        
    Uses mid price (bid+ask)/2 for IV calculation.
    """
    df = options_df.copy()
    
    # Calculate mid price
    df['mid_price'] = (df['bid'] + df['ask']) / 2
    
    # Handle missing mid prices - use lastPrice if available
    if 'lastPrice' in df.columns:
        df['mid_price'].fillna(df['lastPrice'], inplace=True)
    
    # Convert expiration to years
    def calculate_tte(exp_date):
        try:
            from datetime import datetime
            if isinstance(exp_date, str):
                exp_dt = datetime.strptime(exp_date, '%Y-%m-%d')
            else:
                exp_dt = exp_date
            today = datetime.now()
            days_to_exp = (exp_dt - today).days
            return max(days_to_exp / 365.0, 0.001)  # Prevent T=0
        except:
            return 0.03  # ~10 days default
    
    df['time_to_expiry'] = df['expiration_date'].apply(calculate_tte)
    
    # Calculate IV for each row
    ivs = []
    for idx, row in df.iterrows():
        market_price = row['mid_price']
        K = row['strike']
        T = row['time_to_expiry']
        opt_type = row['option_type']
        
        # Skip if no valid price
        if pd.isna(market_price) or market_price <= 0:
            ivs.append(None)
            continue
        
        # Try Newton-Raphson first
        iv = implied_volatility_newton(
            market_price, underlying_price, K, T, risk_free_rate, opt_type
        )
        
        # Fallback to bisection if Newton-Raphson failed
        if iv is None:
            iv = implied_volatility_bisection(
                market_price, underlying_price, K, T, risk_free_rate, opt_type
            )
        
        ivs.append(iv)
    
    df['implied_vol'] = ivs
    
    # Log statistics
    valid_ivs = df['implied_vol'].dropna()
    if len(valid_ivs) > 0:
        logger.info(f"✅ Calculated IV for {len(valid_ivs)}/{len(df)} options")
        logger.info(f"   IV range: {valid_ivs.min():.2%} to {valid_ivs.max():.2%}")
        logger.info(f"   IV mean: {valid_ivs.mean():.2%}")
    else:
        logger.warning(f"❌ Failed to calculate IV for any options")
    
    return df


def interpolate_iv_surface(
    df: pd.DataFrame,
    grid_size: int = 50
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Interpolate IV surface for smooth 3D visualization.
    
    Args:
        df: DataFrame with columns: strike, time_to_expiry, implied_vol
        grid_size: Resolution of interpolated grid
        
    Returns:
        Tuple of (strike_grid, tte_grid, iv_grid) for 3D plotting
        
    Uses Radial Basis Function (RBF) interpolation for smooth surface.
    """
    # Filter valid IV data
    valid_df = df[df['implied_vol'].notna()].copy()
    
    if len(valid_df) < 4:
        logger.warning("Not enough data points for IV surface interpolation")
        return None, None, None
    
    # Extract coordinates
    strikes = valid_df['strike'].values
    ttes = valid_df['time_to_expiry'].values
    ivs = valid_df['implied_vol'].values
    
    # Create grid
    strike_min, strike_max = strikes.min(), strikes.max()
    tte_min, tte_max = ttes.min(), ttes.max()
    
    strike_grid = np.linspace(strike_min, strike_max, grid_size)
    tte_grid = np.linspace(tte_min, tte_max, grid_size)
    
    strike_mesh, tte_mesh = np.meshgrid(strike_grid, tte_grid)
    
    # Interpolate using RBF (smooth interpolation)
    try:
        rbf = Rbf(strikes, ttes, ivs, function='thin_plate', smooth=0.1)
        iv_mesh = rbf(strike_mesh, tte_mesh)
        
        # Clip to reasonable bounds
        iv_mesh = np.clip(iv_mesh, 0.01, 3.0)
        
        return strike_mesh, tte_mesh, iv_mesh
        
    except Exception as e:
        logger.error(f"RBF interpolation failed: {e}")
        
        # Fallback to griddata (linear interpolation)
        try:
            points = np.column_stack([strikes, ttes])
            iv_mesh = griddata(points, ivs, (strike_mesh, tte_mesh), method='linear')
            return strike_mesh, tte_mesh, iv_mesh
        except Exception as e2:
            logger.error(f"Griddata interpolation also failed: {e2}")
            return None, None, None


def calculate_greeks(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = 'call'
) -> Dict[str, float]:
    """
    Calculate option Greeks.
    
    Returns:
        Dict with keys: delta, gamma, vega, theta, rho
    """
    if T <= 0 or sigma <= 0:
        return {'delta': 0, 'gamma': 0, 'vega': 0, 'theta': 0, 'rho': 0}
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    # Delta
    if option_type == 'call':
        delta = norm.cdf(d1)
    else:
        delta = norm.cdf(d1) - 1
    
    # Gamma (same for calls and puts)
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    
    # Vega (same for calls and puts)
    vega_val = S * norm.pdf(d1) * np.sqrt(T)
    
    # Theta
    theta_common = -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
    if option_type == 'call':
        theta = theta_common - r * K * np.exp(-r * T) * norm.cdf(d2)
    else:
        theta = theta_common + r * K * np.exp(-r * T) * norm.cdf(-d2)
    
    # Rho
    if option_type == 'call':
        rho = K * T * np.exp(-r * T) * norm.cdf(d2)
    else:
        rho = -K * T * np.exp(-r * T) * norm.cdf(-d2)
    
    return {
        'delta': delta,
        'gamma': gamma,
        'vega': vega_val,
        'theta': theta / 365,  # Per-day theta
        'rho': rho / 100  # Per 1% change in r
    }
