"""
Fama-French Factor Model Implementation

Provides multi-factor attribution using the Fama-French 3-Factor model:
- Market factor (Rm - Rf)
- SMB (Small Minus Big)
- HML (High Minus Low)

Data source: Kenneth French's data library or cached CSV
"""

import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Cache directory for Fama-French factor data
CACHE_DIR = '.cache/fama_french'
os.makedirs(CACHE_DIR, exist_ok=True)


def fetch_fama_french_factors(start_date=None, end_date=None):
    """
    Fetch Fama-French 3-factor model data.
    
    Args:
        start_date: Start date for factor data (datetime or string)
        end_date: End date for factor data (datetime or string)
    
    Returns:
        DataFrame with columns: Date, Mkt-RF, SMB, HML, RF
    """
    try:
        # Try to load from cached CSV first
        cache_file = os.path.join(CACHE_DIR, 'ff_factors.csv')
        
        if os.path.exists(cache_file):
            logger.info("Loading Fama-French factors from cache")
            df = pd.read_csv(cache_file, parse_dates=['Date'])
            df = df.set_index('Date')
            
            # Filter by date range if provided
            if start_date:
                df = df[df.index >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df.index <= pd.to_datetime(end_date)]
            
            if not df.empty:
                return df
        
        # If cache doesn't exist or is empty, try downloading from pandas_datareader
        try:
            import pandas_datareader.data as web
            
            logger.info("Downloading Fama-French factors from Kenneth French's data library")
            
            # Download Fama-French 3-Factor data
            # Dataset name: F-F_Research_Data_Factors_daily
            ff_data = web.DataReader('F-F_Research_Data_Factors_daily', 'famafrench', 
                                      start=start_date or '2020-01-01', 
                                      end=end_date or datetime.now())[0]
            
            # pandas_datareader returns data in percentage points, convert to decimal
            ff_data = ff_data / 100
            
            # Cache for future use
            ff_data.to_csv(cache_file)
            logger.info(f"Cached Fama-French factors to {cache_file}")
            
            return ff_data
            
        except ImportError:
            logger.warning("pandas_datareader not installed, using simulated data")
        except Exception as e:
            logger.warning(f"Error downloading Fama-French factors: {e}, using simulated data")
        
        # Fallback: Generate simulated factor data
        logger.warning("Using simulated Fama-French factors (not real data)")
        return _generate_simulated_factors(start_date, end_date)
        
    except Exception as e:
        logger.error(f"Error fetching Fama-French factors: {e}")
        return _generate_simulated_factors(start_date, end_date)


def _generate_simulated_factors(start_date=None, end_date=None):
    """Generate simulated factor returns for testing."""
    if start_date is None:
        start_date = datetime.now() - timedelta(days=365)
    if end_date is None:
        end_date = datetime.now()
    
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Simulate factor returns with realistic characteristics
    np.random.seed(42)
    mkt_rf = np.random.normal(0.0004, 0.012, len(dates))  # Market premium
    smb = np.random.normal(0.0001, 0.005, len(dates))     # Size factor
    hml = np.random.normal(0.0002, 0.006, len(dates))     # Value factor
    rf = np.full(len(dates), 0.00008)                     # Risk-free rate (~2% annually)
    
    df = pd.DataFrame({
        'Mkt-RF': mkt_rf,
        'SMB': smb,
        'HML': hml,
        'RF': rf
    }, index=dates)
    
    return df


def run_fama_french_regression(returns, factors):
    """
    Run Fama-French 3-factor regression.
    
    Args:
        returns: Series of asset returns (excess returns over RF)
        factors: DataFrame with Mkt-RF, SMB, HML columns
    
    Returns:
        dict with:
            - alpha: Intercept (Jensen's alpha)
            - beta_market: Market beta
            - beta_smb: SMB beta
            - beta_hml: HML beta
            - r_squared: R-squared of regression
    """
    try:
        from sklearn.linear_model import LinearRegression
        
        # Align returns and factors
        aligned = pd.DataFrame({
            'returns': returns,
            'mkt_rf': factors['Mkt-RF'],
            'smb': factors['SMB'],
            'hml': factors['HML']
        }).dropna()
        
        if len(aligned) < 10:
            logger.warning("Insufficient data for Fama-French regression")
            return {
                'alpha': 0.0,
                'beta_market': 1.0,
                'beta_smb': 0.0,
                'beta_hml': 0.0,
                'r_squared': 0.0
            }
        
        # Prepare data
        X = aligned[['mkt_rf', 'smb', 'hml']].values
        y = aligned['returns'].values
        
        # Run regression
        model = LinearRegression()
        model.fit(X, y)
        
        alpha = model.intercept_
        beta_market, beta_smb, beta_hml = model.coef_
        
        # Calculate R-squared
        y_pred = model.predict(X)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        
        return {
            'alpha': float(alpha),
            'beta_market': float(beta_market),
            'beta_smb': float(beta_smb),
            'beta_hml': float(beta_hml),
            'r_squared': float(r_squared)
        }
        
    except Exception as e:
        logger.error(f"Error in Fama-French regression: {e}")
        return {
            'alpha': 0.0,
            'beta_market': 1.0,
            'beta_smb': 0.0,
            'beta_hml': 0.0,
            'r_squared': 0.0
        }


def calculate_factor_contributions(ff_results, factors):
    """
    Calculate factor contributions to returns.
    
    Args:
        ff_results: Results from run_fama_french_regression
        factors: DataFrame with factor returns
    
    Returns:
        dict with contribution of each factor
    """
    # Average factor returns over the period
    avg_mkt_rf = factors['Mkt-RF'].mean()
    avg_smb = factors['SMB'].mean()
    avg_hml = factors['HML'].mean()
    
    contributions = {
        'alpha': ff_results['alpha'],
        'market': ff_results['beta_market'] * avg_mkt_rf,
        'smb': ff_results['beta_smb'] * avg_smb,
        'hml': ff_results['beta_hml'] * avg_hml
    }
    
    return contributions


def decompose_returns_ff(stock_returns, benchmark_returns, start_date=None, end_date=None):
    """
    Decompose stock returns using Fama-French model.
    
    Args:
        stock_returns: Series of stock returns
        benchmark_returns: Series of benchmark (SPY) returns
        start_date: Start date for factor data
        end_date: End date for factor data
    
    Returns:
        dict with alpha, betas, and factor contributions
    """
    try:
        # Fetch Fama-French factors
        factors = fetch_fama_french_factors(start_date, end_date)
        
        if factors is None or factors.empty:
            logger.warning("No Fama-French factor data available")
            return None
        
        # Calculate excess returns (stock returns - risk-free rate)
        # Align indices
        aligned = pd.DataFrame({
            'stock': stock_returns,
            'rf': factors['RF']
        }).dropna()
        
        excess_returns = aligned['stock'] - aligned['rf']
        
        # Run regression
        ff_results = run_fama_french_regression(excess_returns, factors)
        
        # Calculate contributions
        contributions = calculate_factor_contributions(ff_results, factors)
        
        return {
            'model_results': ff_results,
            'contributions': contributions,
            'total_return': stock_returns.sum(),
            'factor_data': factors
        }
        
    except Exception as e:
        logger.error(f"Error decomposing returns with Fama-French: {e}")
        return None
