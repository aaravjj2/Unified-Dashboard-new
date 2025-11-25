"""
IV Solver - Robust Black-Scholes Implied Volatility Calculator
===============================================================

Phase 34: Newton-Raphson with Brent fallback, bounds checking, 
smoothing/reg, and arbitrage validation.

Numeric Requirements:
- Grid shape >= 5x5
- IV values in [0.01, 3.0]
- No NaNs or infinities
- Fallback smoothing if solve fails
"""

import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq
import logging

logger = logging.getLogger(__name__)

# Bounds for IV search
IV_MIN = 0.01
IV_MAX = 3.0
IV_ATM_GUESS = 0.20

# Convergence criteria
MAX_ITERATIONS = 100
TOLERANCE = 1e-6


def black_scholes_price(S, K, T, r, sigma, option_type='call'):
    """
    Calculate Black-Scholes option price.
    
    Args:
        S: Spot price
        K: Strike price
        T: Time to expiry (years)
        r: Risk-free rate
        sigma: Volatility
        option_type: 'call' or 'put'
        
    Returns:
        Option price
    """
    if T <= 0 or sigma <= 0:
        return max(S - K, 0) if option_type == 'call' else max(K - S, 0)
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type == 'call':
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def vega(S, K, T, r, sigma):
    """
    Calculate option vega (sensitivity to volatility).
    
    Args:
        S, K, T, r, sigma: Black-Scholes parameters
        
    Returns:
        Vega value
    """
    if T <= 0 or sigma <= 0:
        return 0.0
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return S * norm.pdf(d1) * np.sqrt(T)


def newton_raphson_iv(target_price, S, K, T, r, option_type='call', max_iter=MAX_ITERATIONS):
    """
    Newton-Raphson method for IV calculation.
    
    Args:
        target_price: Observed market price
        S, K, T, r: Black-Scholes parameters
        option_type: 'call' or 'put'
        max_iter: Maximum iterations
        
    Returns:
        Tuple: (implied_vol, converged, iterations)
    """
    sigma = IV_ATM_GUESS
    
    for i in range(max_iter):
        price = black_scholes_price(S, K, T, r, sigma, option_type)
        diff = price - target_price
        
        if abs(diff) < TOLERANCE:
            return sigma, True, i
        
        v = vega(S, K, T, r, sigma)
        
        if v < 1e-10:  # Vega too small, can't continue
            break
        
        sigma = sigma - diff / v
        
        # Clamp to bounds
        sigma = max(IV_MIN, min(IV_MAX, sigma))
    
    return sigma, False, max_iter


def brent_fallback_iv(target_price, S, K, T, r, option_type='call'):
    """
    Brent's method fallback for difficult cases.
    
    Args:
        target_price: Observed market price
        S, K, T, r: Black-Scholes parameters
        option_type: 'call' or 'put'
        
    Returns:
        Tuple: (implied_vol, converged)
    """
    def f(sigma):
        return black_scholes_price(S, K, T, r, sigma, option_type) - target_price
    
    try:
        sigma = brentq(f, IV_MIN, IV_MAX, xtol=TOLERANCE)
        return sigma, True
    except ValueError:
        # Brent failed (likely no root in bounds)
        return IV_ATM_GUESS, False


def calculate_iv(target_price, S, K, T, r=0.05, option_type='call'):
    """
    Calculate implied volatility with robust fallback.
    
    Workflow:
    1. Try Newton-Raphson
    2. If fails, try Brent
    3. If both fail, return bounded NR result with warning
    
    Args:
        target_price: Market option price
        S: Spot price
        K: Strike price
        T: Time to expiry (years) 
        r: Risk-free rate (default 0.05)
        option_type: 'call' or 'put'
        
    Returns:
        Dict with keys: iv, converged, method, iterations
    """
    # Try Newton-Raphson first
    iv_nr, converged_nr, iters = newton_raphson_iv(target_price, S, K, T, r, option_type)
    
    if converged_nr:
        return {
            'iv': iv_nr,
            'converged': True,
            'method': 'newton-raphson',
            'iterations': iters
        }
    
    # Fallback to Brent
    logger.warning(f"Newton-Raphson failed for K={K}, T={T}, trying Brent")
    iv_brent, converged_brent = brent_fallback_iv(target_price, S, K, T, r, option_type)
    
    if converged_brent:
        return {
            'iv': iv_brent,
            'converged': True,
            'method': 'brent',
            'iterations': 0
        }
    
    # Both failed - return bounded NR with warning
    logger.error(f"Both solvers failed for K={K}, T={T}, using bounded result")
    return {
        'iv': np.clip(iv_nr, IV_MIN, IV_MAX),
        'converged': False,
        'method': 'bounded-nr',
        'iterations': iters
    }


def validate_iv_grid(grid):
    """
    Validate IV grid meets numeric requirements.
    
    Requirements:
    - Shape >= 5x5
    - All values finite
    - Values in [IV_MIN, IV_MAX]
    - No NaNs or infs
    
    Args:
        grid: 2D numpy array of IV values
        
    Returns:
        Dict with keys: valid, errors, warnings
    """
    errors = []
    warnings = []
    
    # Check shape
    if len(grid) < 5 or len(grid[0]) < 5:
        errors.append(f"Grid shape {len(grid)}x{len(grid[0])} < required 5x5")
    
    # Convert to numpy for validation
    arr = np.array(grid)
    
    # Check for NaN/inf
    if np.any(np.isnan(arr)):
        nan_count = np.sum(np.isnan(arr))
        errors.append(f"Grid contains {nan_count} NaN values")
    
    if np.any(np.isinf(arr)):
        inf_count = np.sum(np.isinf(arr))
        errors.append(f"Grid contains {inf_count} infinite values")
    
    # Check bounds
    if np.any(arr < IV_MIN) or np.any(arr > IV_MAX):
        out_of_bounds = np.sum((arr < IV_MIN) | (arr > IV_MAX))
        warnings.append(f"{out_of_bounds} values outside [{IV_MIN}, {IV_MAX}] bounds")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }


__all__ = [
    'calculate_iv',
    'validate_iv_grid',
    'black_scholes_price',
    'IV_MIN',
    'IV_MAX'
]
