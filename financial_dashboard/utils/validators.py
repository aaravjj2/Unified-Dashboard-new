"""
Options Lab Data Validators

Provides strict validation for options chain data, Greeks, and volatility surfaces.
Used to ensure data quality before visualization.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


def validate_chain(df: pd.DataFrame, option_type: str = "unknown") -> Tuple[bool, Optional[str]]:
    """
    Validate options chain DataFrame.
    
    Args:
        df: Options chain DataFrame (calls or puts)
        option_type: 'call' or 'put' for better error messages
        
    Returns:
        (is_valid, error_message)
    """
    if df is None or df.empty:
        return False, f"{option_type} chain is empty"
    
    # Required columns for options chain
    required_cols = ['strike', 'lastPrice', 'volume', 'openInterest', 'impliedVolatility']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        return False, f"{option_type} chain missing columns: {missing_cols}"
    
    # Check for NaN values in critical columns
    for col in ['strike', 'lastPrice']:
        if df[col].isna().any():
            nan_count = df[col].isna().sum()
            return False, f"{option_type} chain has {nan_count} NaN values in {col}"
    
    # Validate numeric ranges
    if (df['strike'] <= 0).any():
        return False, f"{option_type} chain has non-positive strikes"
    
    if (df['lastPrice'] < 0).any():
        return False, f"{option_type} chain has negative prices"
    
    if (df['impliedVolatility'] < 0).any() or (df['impliedVolatility'] > 5).any():
        return False, f"{option_type} chain has implausible IV values (should be 0-500%)"
    
    # Check row count
    if len(df) < 3:
        return False, f"{option_type} chain has too few strikes ({len(df)})"
    
    logger.info(f"✅ {option_type.capitalize()} chain validated: {len(df)} strikes, IV range: {df['impliedVolatility'].min():.2%}-{df['impliedVolatility'].max():.2%}")
    return True, None


def validate_greeks(df: pd.DataFrame, option_type: str = "unknown") -> Tuple[bool, Optional[str]]:
    """
    Validate Greeks calculations in options chain.
    
    Args:
        df: DataFrame with Greeks columns
        option_type: 'call' or 'put'
        
    Returns:
        (is_valid, error_message)
    """
    if df is None or df.empty:
        return False, f"{option_type} Greeks DataFrame is empty"
    
    # Greek columns that should exist
    greek_cols = ['delta', 'gamma', 'theta', 'vega']
    present_greeks = [col for col in greek_cols if col in df.columns]
    
    if not present_greeks:
        return False, f"No Greeks found in {option_type} data (expected: {greek_cols})"
    
    # Validate delta bounds
    if 'delta' in df.columns:
        if option_type == 'call':
            # Call delta should be 0 to 1
            if (df['delta'] < 0).any() or (df['delta'] > 1).any():
                return False, f"Call delta out of bounds [0, 1]: {df['delta'].min():.3f} to {df['delta'].max():.3f}"
        elif option_type == 'put':
            # Put delta should be -1 to 0
            if (df['delta'] < -1).any() or (df['delta'] > 0).any():
                return False, f"Put delta out of bounds [-1, 0]: {df['delta'].min():.3f} to {df['delta'].max():.3f}"
    
    # Validate gamma (always positive)
    if 'gamma' in df.columns:
        if (df['gamma'] < 0).any():
            return False, f"Gamma should be positive, found negative values"
        if (df['gamma'] > 1).any():
            logger.warning(f"⚠️ Unusually high gamma detected: max={df['gamma'].max():.4f}")
    
    # Validate theta (usually negative for long positions)
    if 'theta' in df.columns:
        # Just check for absurd values
        if abs(df['theta']).max() > 100:
            return False, f"Theta values seem unrealistic: max={df['theta'].max():.2f}"
    
    # Validate vega (always positive)
    if 'vega' in df.columns:
        if (df['vega'] < 0).any():
            return False, f"Vega should be positive, found negative values"
    
    logger.info(f"✅ {option_type.capitalize()} Greeks validated: {len(present_greeks)} Greeks present")
    return True, None


def validate_surface(surface_data: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate volatility surface data structure.
    
    Args:
        surface_data: Dict with 'moneyness', 'days_to_exp', 'implied_vol' arrays
        
    Returns:
        (is_valid, error_message)
    """
    if not surface_data:
        return False, "Surface data is None or empty"
    
    required_keys = ['moneyness', 'days_to_exp', 'implied_vol']
    missing_keys = [k for k in required_keys if k not in surface_data]
    
    if missing_keys:
        return False, f"Surface data missing keys: {missing_keys}"
    
    X = surface_data['moneyness']
    Y = surface_data['days_to_exp']
    Z = surface_data['implied_vol']
    
    # Check if arrays exist
    if X is None or Y is None or Z is None:
        return False, "Surface arrays contain None values"
    
    # Convert to numpy arrays if needed
    try:
        X = np.asarray(X)
        Y = np.asarray(Y)
        Z = np.asarray(Z)
    except Exception as e:
        return False, f"Failed to convert surface data to arrays: {e}"
    
    # Check dimensions match
    if X.shape != Y.shape or X.shape != Z.shape:
        return False, f"Surface dimension mismatch: X{X.shape}, Y{Y.shape}, Z{Z.shape}"
    
    # Check for NaN/Inf
    if np.isnan(Z).any() or np.isinf(Z).any():
        return False, "Surface contains NaN or Inf values"
    
    # Check plausible IV range (0-500%)
    if (Z < 0).any() or (Z > 5).any():
        return False, f"Surface IV out of range [0, 5]: {Z.min():.2f} to {Z.max():.2f}"
    
    # Check moneyness range
    if X.min() < 0.5 or X.max() > 2.0:
        logger.warning(f"⚠️ Unusual moneyness range: {X.min():.2f} to {X.max():.2f}")
    
    logger.info(f"✅ Vol surface validated: {X.shape} grid points, IV range: {Z.min():.2%}-{Z.max():.2%}")
    return True, None


def validate_chain_data(chain_data: Dict) -> Tuple[bool, str]:
    """
    Comprehensive validation of full options chain data structure.
    
    Args:
        chain_data: Output from fetch_options_chain()
        
    Returns:
        (is_valid, status_message)
    """
    if not chain_data:
        return False, "❌ Chain data is None or empty"
    
    # Check required fields
    required_fields = ['ticker', 'spot_price', 'calls', 'puts', 'source']
    missing = [f for f in required_fields if f not in chain_data]
    if missing:
        return False, f"❌ Missing required fields: {missing}"
    
    # Validate spot price
    spot = chain_data.get('spot_price')
    if not spot or spot <= 0:
        return False, f"❌ Invalid spot price: {spot}"
    
    # Validate calls
    calls = chain_data.get('calls')
    is_valid, error = validate_chain(calls, 'call')
    if not is_valid:
        return False, f"❌ Calls validation failed: {error}"
    
    # Validate puts
    puts = chain_data.get('puts')
    is_valid, error = validate_chain(puts, 'put')
    if not is_valid:
        return False, f"❌ Puts validation failed: {error}"
    
    # Validate Greeks if present
    if 'delta' in calls.columns:
        is_valid, error = validate_greeks(calls, 'call')
        if not is_valid:
            return False, f"❌ Call Greeks validation failed: {error}"
    
    if 'delta' in puts.columns:
        is_valid, error = validate_greeks(puts, 'put')
        if not is_valid:
            return False, f"❌ Put Greeks validation failed: {error}"
    
    # Success message with stats
    source = chain_data.get('source', 'unknown')
    message = (
        f"✅ {chain_data['ticker']} chain validated | "
        f"Source: {source.upper()} | "
        f"Spot: ${spot:.2f} | "
        f"Calls: {len(calls)} | "
        f"Puts: {len(puts)}"
    )
    
    logger.info(message)
    return True, message
