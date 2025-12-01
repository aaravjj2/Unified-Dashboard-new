"""
Volatility Surface Solver - Newton-Raphson with Brent Fallback
================================================================

Agent-1B Implementation - Robust IV solver with numeric guards.

Features:
- Primary: Newton-Raphson method
- Fallback: Brent's method (scipy.optimize.brentq)
- IV bounds: [0.01, 3.0]
- Numeric guards (no NaN/Inf)
- Detailed solver_info metadata
- Logging to diagnostics file

Owner: Agent-1B
"""

import os
import math
import logging
import time
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Solver diagnostics log
SOLVER_LOG_FILE = Path(__file__).parent.parent.parent / 'reports' / 'vol_lab_compact' / 'diagnostics' / 'solver_logs.log'
SOLVER_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# IV bounds
IV_MIN = 0.01
IV_MAX = 3.0

# Solver constants
MAX_ITERATIONS = 100
TOLERANCE = 1e-6


def log_solver_event(event_type: str, message: str, details: Optional[Dict] = None):
    """
    Log solver event to diagnostics file with enhanced formatting
    
    Agent-1A Enhancement: Structured JSON logging with full stack trace on errors.
    
    Args:
        event_type: Event category (SUCCESS, INCOMPLETE, ERROR, FALLBACK, START)
        message: Human-readable message
        details: Dictionary with solver metadata
    """
    try:
        import json
        timestamp = datetime.now().isoformat()
        
        log_entry_data = {
            'timestamp': timestamp,
            'event_type': event_type,
            'message': message,
            'details': details or {}
        }
        
        # Structured JSON logging for better parsing
        log_line = json.dumps(log_entry_data)
        
        with open(SOLVER_LOG_FILE, 'a') as f:
            f.write(log_line + '\n')
        
        # Also log to Python logger for console visibility
        if event_type == 'ERROR':
            logger.error(f"{event_type}: {message} | {details}")
        elif event_type in ['SUCCESS', 'INCOMPLETE']:
            logger.info(f"{event_type}: {message} | {details}")
        else:
            logger.debug(f"{event_type}: {message} | {details}")
        
    except Exception as e:
        logger.warning(f"Failed to write solver log: {e}")


def black_scholes_call(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Black-Scholes call option pricing formula
    
    Args:
        S: Stock price
        K: Strike price
        T: Time to maturity (years)
        r: Risk-free rate
        sigma: Volatility (IV)
    
    Returns:
        Call option price
    """
    if T <= 0 or sigma <= 0:
        return max(S - K, 0)  # Intrinsic value
    
    try:
        sqrt_T = math.sqrt(T)
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
        d2 = d1 - sigma * sqrt_T
        
        # Standard normal CDF approximation
        def norm_cdf(x):
            return 0.5 * (1 + math.erf(x / math.sqrt(2)))
        
        price = S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
        return price
    
    except Exception as e:
        logger.warning(f"BS formula error: {e}")
        return max(S - K, 0)


def vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Calculate option vega (sensitivity to volatility)
    
    Returns:
        Vega value
    """
    if T <= 0 or sigma <= 0:
        return 0.0
    
    try:
        sqrt_T = math.sqrt(T)
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
        
        # Vega formula
        vega_val = S * math.sqrt(T) * math.exp(-0.5 * d1 ** 2) / math.sqrt(2 * math.pi)
        return vega_val
    
    except Exception as e:
        logger.warning(f"Vega calculation error: {e}")
        return 0.0


def newton_raphson_iv(market_price: float, S: float, K: float, T: float, r: float,
                      initial_guess: float = 0.2, max_iter: int = MAX_ITERATIONS,
                      tol: float = TOLERANCE) -> Tuple[Optional[float], Dict[str, Any]]:
    """
    Newton-Raphson IV solver
    
    Args:
        market_price: Observed option price
        S: Stock price
        K: Strike price
        T: Time to maturity (years)
        r: Risk-free rate
        initial_guess: Starting IV guess
        max_iter: Maximum iterations
        tol: Convergence tolerance
    
    Returns:
        (iv, solver_info) tuple
    """
    start_time = time.time()
    
    sigma = max(IV_MIN, min(IV_MAX, initial_guess))
    iterations = 0
    converged = False
    
    try:
        for i in range(max_iter):
            iterations = i + 1
            
            # Calculate price and vega
            price = black_scholes_call(S, K, T, r, sigma)
            v = vega(S, K, T, r, sigma)
            
            # Check for numeric issues
            if math.isnan(price) or math.isinf(price) or v < 1e-10:
                break
            
            # Newton-Raphson update
            diff = price - market_price
            
            if abs(diff) < tol:
                converged = True
                break
            
            # Update sigma
            sigma_new = sigma - diff / v
            
            # Enforce bounds
            sigma = max(IV_MIN, min(IV_MAX, sigma_new))
        
        runtime_ms = (time.time() - start_time) * 1000
        
        solver_info = {
            'solver_name': 'newton_raphson',
            'iterations': iterations,
            'converged': converged,
            'fallback_used': False,
            'runtime_ms': round(runtime_ms, 2),
            'final_iv': round(sigma, 6) if converged else None
        }
        
        if converged:
            log_solver_event('SUCCESS', 'Newton-Raphson converged', solver_info)
            return sigma, solver_info
        else:
            log_solver_event('INCOMPLETE', 'Newton-Raphson did not converge', solver_info)
            return None, solver_info
    
    except Exception as e:
        runtime_ms = (time.time() - start_time) * 1000
        solver_info = {
            'solver_name': 'newton_raphson',
            'iterations': iterations,
            'converged': False,
            'fallback_used': False,
            'runtime_ms': round(runtime_ms, 2),
            'error': str(e)
        }
        log_solver_event('ERROR', f'Newton-Raphson failed: {e}', solver_info)
        return None, solver_info


def brent_fallback_iv(market_price: float, S: float, K: float, T: float, r: float) -> Tuple[Optional[float], Dict[str, Any]]:
    """
    Brent's method IV solver (fallback)
    
    Uses scipy.optimize.brentq for robust root finding.
    
    Agent-1A Enhancement: Added detailed logging and error handling.
    
    Returns:
        (iv, solver_info) tuple
    """
    start_time = time.time()
    
    try:
        from scipy.optimize import brentq
        
        # Define objective function
        def objective(sigma):
            return black_scholes_call(S, K, T, r, sigma) - market_price
        
        # Solve using Brent's method (returns float)
        # Note: Type checker shows error but brentq actually returns float, not tuple
        iv_result: float = brentq(objective, IV_MIN, IV_MAX, maxiter=MAX_ITERATIONS, xtol=TOLERANCE)  # type: ignore
        iv = iv_result
        
        runtime_ms = (time.time() - start_time) * 1000
        
        solver_info = {
            'solver_name': 'brent',
            'iterations': MAX_ITERATIONS,  # Brent doesn't expose iteration count easily
            'converged': True,
            'fallback_used': True,
            'runtime_ms': round(runtime_ms, 2),
            'final_iv': round(iv, 6)
        }
        
        log_solver_event('SUCCESS', 'Brent fallback converged', solver_info)
        return iv, solver_info
    
    except Exception as e:
        runtime_ms = (time.time() - start_time) * 1000
        solver_info = {
            'solver_name': 'brent',
            'iterations': 0,
            'converged': False,
            'fallback_used': True,
            'runtime_ms': round(runtime_ms, 2),
            'error': str(e)
        }
        log_solver_event('ERROR', f'Brent fallback failed: {e}', solver_info)
        return None, solver_info


def solve_iv(market_price: float, S: float, K: float, T: float, r: float = 0.02,
             use_fallback: bool = True) -> Tuple[Optional[float], Dict[str, Any]]:
    """
    Main IV solver with Newton-Raphson primary and Brent fallback
    
    Args:
        market_price: Observed option price
        S: Stock price
        K: Strike price
        T: Time to maturity (years)
        r: Risk-free rate (default 2%)
        use_fallback: Whether to use Brent if NR fails
    
    Returns:
        (iv, solver_info) tuple
    """
    # Try Newton-Raphson first
    iv, solver_info = newton_raphson_iv(market_price, S, K, T, r)
    
    if iv is not None:
        return iv, solver_info
    
    # Fallback to Brent if enabled
    if use_fallback:
        log_solver_event('FALLBACK', 'Attempting Brent method after NR failure')
        return brent_fallback_iv(market_price, S, K, T, r)
    
    return None, solver_info


def compute_surface_grid(S: float, strikes: list, expiries: list, 
                         option_prices: Dict[Tuple[float, float], float],
                         r: float = 0.02) -> Tuple[list, list, list, Dict[str, Any]]:
    """
    Compute IV surface grid
    
    Args:
        S: Current stock price
        strikes: List of strike prices
        expiries: List of days to expiry
        option_prices: Dict mapping (strike, days_to_expiry) -> market_price
        r: Risk-free rate
    
    Returns:
        (xs, ys, grid, meta) tuple where grid is 2D list of IVs
    """
    xs = sorted(strikes)
    ys = sorted(expiries)
    
    grid = []
    total_solves = 0
    successful_solves = 0
    fallback_count = 0
    
    for days in ys:
        row = []
        T = days / 365.0  # Convert days to years
        
        for K in xs:
            market_price = option_prices.get((K, days))
            
            if market_price is None or T <= 0:
                row.append(None)
                continue
            
            total_solves += 1
            iv, solver_info = solve_iv(market_price, S, K, T, r)
            
            if iv is not None:
                successful_solves += 1
                if solver_info.get('fallback_used'):
                    fallback_count += 1
                row.append(round(iv, 6))
            else:
                row.append(None)
        
        grid.append(row)
    
    meta = {
        'total_solves': total_solves,
        'successful_solves': successful_solves,
        'fallback_count': fallback_count,
        'success_rate': successful_solves / total_solves if total_solves > 0 else 0
    }
    
    return xs, ys, grid, meta
