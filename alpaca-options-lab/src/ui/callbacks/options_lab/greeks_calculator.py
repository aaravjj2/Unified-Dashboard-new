"""
Real Options Greeks Calculator

Calculates Delta, Gamma, Theta, Vega, Rho using Black-Scholes model.
"""
import numpy as np
from scipy.stats import norm
from datetime import datetime
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def calculate_time_to_expiry(expiration_date: str) -> float:
    """
    Calculate time to expiration in years.
    
    Args:
        expiration_date: Expiration date in format 'YYYY-MM-DD'
        
    Returns:
        Time to expiration in years
    """
    try:
        exp_dt = datetime.strptime(expiration_date, '%Y-%m-%d')
        now = datetime.now()
        days_to_exp = (exp_dt - now).days
        return max(days_to_exp / 365.0, 0.001)  # Minimum 0.001 years to avoid division by zero
    except Exception as e:
        logger.error(f"Error calculating time to expiry: {e}")
        return 0.1  # Default to ~36 days


def black_scholes_d1_d2(S: float, K: float, T: float, r: float, sigma: float) -> tuple:
    """
    Calculate d1 and d2 for Black-Scholes formula.
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (years)
        r: Risk-free rate
        sigma: Implied volatility
        
    Returns:
        Tuple of (d1, d2)
    """
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return d1, d2


def calculate_delta(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call') -> float:
    """
    Calculate option delta.
    
    Delta measures the rate of change of option value with respect to changes in the underlying asset's price.
    Call delta ranges from 0 to 1, put delta from -1 to 0.
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (years)
        r: Risk-free rate
        sigma: Implied volatility
        option_type: 'call' or 'put'
        
    Returns:
        Delta value
    """
    try:
        d1, _ = black_scholes_d1_d2(S, K, T, r, sigma)
        
        if option_type.lower() == 'call':
            return norm.cdf(d1)
        else:  # put
            return norm.cdf(d1) - 1
    except Exception as e:
        logger.error(f"Error calculating delta: {e}")
        return 0.5 if option_type == 'call' else -0.5


def calculate_gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Calculate option gamma.
    
    Gamma measures the rate of change in delta with respect to changes in the underlying price.
    Same for both calls and puts.
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (years)
        r: Risk-free rate
        sigma: Implied volatility
        
    Returns:
        Gamma value
    """
    try:
        d1, _ = black_scholes_d1_d2(S, K, T, r, sigma)
        return norm.pdf(d1) / (S * sigma * np.sqrt(T))
    except Exception as e:
        logger.error(f"Error calculating gamma: {e}")
        return 0.01


def calculate_theta(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call') -> float:
    """
    Calculate option theta (time decay).
    
    Theta measures the rate of change of option value with respect to the passage of time.
    Typically negative for long options (lose value over time).
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (years)
        r: Risk-free rate
        sigma: Implied volatility
        option_type: 'call' or 'put'
        
    Returns:
        Theta value (per day)
    """
    try:
        d1, d2 = black_scholes_d1_d2(S, K, T, r, sigma)
        
        if option_type.lower() == 'call':
            theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) 
                    - r * K * np.exp(-r * T) * norm.cdf(d2))
        else:  # put
            theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) 
                    + r * K * np.exp(-r * T) * norm.cdf(-d2))
        
        # Convert to per-day theta
        return theta / 365.0
    except Exception as e:
        logger.error(f"Error calculating theta: {e}")
        return -0.05


def calculate_vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Calculate option vega.
    
    Vega measures sensitivity to implied volatility.
    Same for both calls and puts.
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (years)
        r: Risk-free rate
        sigma: Implied volatility
        
    Returns:
        Vega value (per 1% change in IV)
    """
    try:
        d1, _ = black_scholes_d1_d2(S, K, T, r, sigma)
        return S * norm.pdf(d1) * np.sqrt(T) / 100.0  # Divide by 100 for 1% change
    except Exception as e:
        logger.error(f"Error calculating vega: {e}")
        return 0.1


def calculate_rho(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call') -> float:
    """
    Calculate option rho.
    
    Rho measures sensitivity to interest rate changes.
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (years)
        r: Risk-free rate
        sigma: Implied volatility
        option_type: 'call' or 'put'
        
    Returns:
        Rho value (per 1% change in rate)
    """
    try:
        _, d2 = black_scholes_d1_d2(S, K, T, r, sigma)
        
        if option_type.lower() == 'call':
            return K * T * np.exp(-r * T) * norm.cdf(d2) / 100.0
        else:  # put
            return -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100.0
    except Exception as e:
        logger.error(f"Error calculating rho: {e}")
        return 0.01


def calculate_all_greeks(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = 'call'
) -> Dict[str, float]:
    """
    Calculate all Greeks for an option.
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (years)
        r: Risk-free rate (e.g., 0.05 for 5%)
        sigma: Implied volatility (e.g., 0.20 for 20%)
        option_type: 'call' or 'put'
        
    Returns:
        Dictionary with all Greeks
    """
    return {
        'delta': calculate_delta(S, K, T, r, sigma, option_type),
        'gamma': calculate_gamma(S, K, T, r, sigma),
        'theta': calculate_theta(S, K, T, r, sigma, option_type),
        'vega': calculate_vega(S, K, T, r, sigma),
        'rho': calculate_rho(S, K, T, r, sigma, option_type)
    }


def enrich_options_with_greeks(options_df, spot_price: float, expiration_date: str, risk_free_rate: float = 0.045) -> None:
    """
    Add calculated Greeks to options DataFrame in-place.
    
    Args:
        options_df: DataFrame with options data
        spot_price: Current underlying price
        expiration_date: Expiration date string
        risk_free_rate: Risk-free interest rate (default 4.5%)
    """
    if options_df.empty:
        return
    
    T = calculate_time_to_expiry(expiration_date)
    
    # Determine option type from column or context
    is_call = 'call' in str(options_df.get('contractSymbol', [''])[0]).lower() if 'contractSymbol' in options_df else True
    option_type = 'call' if is_call else 'put'
    
    # Calculate Greeks for each row
    for idx, row in options_df.iterrows():
        K = row.get('strike', spot_price)
        sigma = row.get('impliedVolatility', 0.25)  # Default 25% IV
        
        # Ensure sigma is valid
        if sigma <= 0 or sigma > 5:  # Cap at 500% IV
            sigma = 0.25
        
        greeks = calculate_all_greeks(spot_price, K, T, risk_free_rate, sigma, option_type)
        
        # Add to DataFrame if columns don't exist
        for greek, value in greeks.items():
            if greek not in options_df.columns:
                options_df[greek] = 0.0
            options_df.at[idx, greek] = value


if __name__ == '__main__':
    # Test the calculator
    S = 590.0  # SPY price
    K = 600.0  # Strike
    T = 0.1    # ~36 days
    r = 0.045  # 4.5% risk-free rate
    sigma = 0.18  # 18% IV
    
    greeks = calculate_all_greeks(S, K, T, r, sigma, 'call')
    print("Test Greeks Calculation:")
    print(f"Spot: ${S}, Strike: ${K}, T: {T:.3f} years, IV: {sigma*100:.1f}%")
    print(f"Delta: {greeks['delta']:.4f}")
    print(f"Gamma: {greeks['gamma']:.4f}")
    print(f"Theta: {greeks['theta']:.4f} (per day)")
    print(f"Vega: {greeks['vega']:.4f} (per 1% IV)")
    print(f"Rho: {greeks['rho']:.4f} (per 1% rate)")
