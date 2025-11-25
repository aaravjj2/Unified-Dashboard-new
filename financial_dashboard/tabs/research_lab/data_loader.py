"""
Research Lab Data Loader

Handles data fetching from multiple sources:
- yfinance: Historical prices, fundamentals
- Alpaca: Real-time quotes, market data
- CSV files: Precomputed factors (Fama-French, etc.)
- PortfolioDB: User portfolio data

All functions return standardized dict formats for consistency.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Literal
import logging
import os

logger = logging.getLogger(__name__)

# ============================================================================
# PRICE DATA FETCHING
# ============================================================================

def fetch_price_data(
    tickers: List[str],
    start_date: str,
    end_date: str,
    interval: str = '1d'
) -> Dict[str, pd.DataFrame]:
    """
    Fetch historical price data for multiple tickers.
    
    Args:
        tickers: List of ticker symbols
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        interval: Data interval ('1d', '1wk', '1mo')
    
    Returns:
        Dict mapping ticker -> DataFrame with OHLCV data
    """
    results = {}
    
    for ticker in tickers:
        try:
            logger.info(f"📊 Fetching price data for {ticker}")
            stock = yf.Ticker(ticker)
            df = stock.history(start=start_date, end=end_date, interval=interval)
            
            if not df.empty:
                results[ticker] = df
                logger.info(f"✅ {ticker}: {len(df)} data points")
            else:
                logger.warning(f"⚠️ {ticker}: No data available")
                results[ticker] = pd.DataFrame()
                
        except Exception as e:
            logger.error(f"❌ Error fetching {ticker}: {e}")
            results[ticker] = pd.DataFrame()
    
    return results


def fetch_ticker_info(tickers: List[str]) -> pd.DataFrame:
    """
    Fetch metadata for tickers (sector, market cap, etc.).
    
    Args:
        tickers: List of ticker symbols
        
    Returns:
        DataFrame with ticker metadata
    """
    info_list = []
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            info_list.append({
                'ticker': ticker,
                'name': info.get('longName', ticker),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', None),
                'beta': info.get('beta', None),
                'dividend_yield': info.get('dividendYield', 0),
            })
        except Exception as e:
            logger.error(f"❌ Error fetching info for {ticker}: {e}")
            info_list.append({
                'ticker': ticker,
                'name': ticker,
                'sector': 'Unknown',
                'industry': 'Unknown',
                'market_cap': 0,
                'pe_ratio': None,
                'beta': None,
                'dividend_yield': 0,
            })
    
    return pd.DataFrame(info_list)


# ============================================================================
# FACTOR DATA
# ============================================================================

def load_fama_french_factors(
    start_date: str,
    end_date: str
) -> pd.DataFrame:
    """
    Load Fama-French factor data (3-factor or 5-factor).
    
    For now, generates synthetic data. In production, load from CSV or API.
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        DataFrame with factor returns (Mkt-RF, SMB, HML, RMW, CMA)
    """
    # Generate date range
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Synthetic factor data (replace with actual data)
    np.random.seed(42)
    factor_data = pd.DataFrame({
        'Date': dates,
        'Mkt-RF': np.random.normal(0.0003, 0.01, len(dates)),  # Market premium
        'SMB': np.random.normal(0.0001, 0.005, len(dates)),    # Size factor
        'HML': np.random.normal(0.0002, 0.005, len(dates)),    # Value factor
        'RMW': np.random.normal(0.0001, 0.004, len(dates)),    # Profitability
        'CMA': np.random.normal(0.0001, 0.004, len(dates)),    # Investment
        'RF': np.random.normal(0.00001, 0.0001, len(dates)),   # Risk-free rate
    })
    
    factor_data.set_index('Date', inplace=True)
    
    logger.info(f"✅ Loaded Fama-French factors: {len(factor_data)} days")
    return factor_data


def calculate_factor_exposures(
    returns: pd.Series,
    factors: pd.DataFrame
) -> Dict[str, Union[str, float]]:
    """
    Calculate factor exposures using linear regression.
    
    Args:
        returns: Asset returns (Series)
        factors: Factor returns (DataFrame)
        
    Returns:
        Dict with factor loadings and R-squared
    """
    from sklearn.linear_model import LinearRegression
    
    # Remove timezone info for alignment
    if isinstance(returns.index, pd.DatetimeIndex) and returns.index.tz is not None:
        returns.index = returns.index.tz_localize(None)
    if isinstance(factors.index, pd.DatetimeIndex) and factors.index.tz is not None:
        factors.index = factors.index.tz_localize(None)
    
    # Align data
    common_index = returns.index.intersection(factors.index)  # type: ignore
    if len(common_index) < 10:  # Need at least 10 observations
        logger.warning(f"⚠️ Only {len(common_index)} overlapping dates found")
        return {
            'error': 'Insufficient overlapping dates',
            'overlapping_dates': float(len(common_index)),
            'alpha': 0.0,
            'r_squared': 0.0
        }
    
    y = np.array(returns.loc[common_index].values).reshape(-1, 1)
    X = np.array(factors.loc[common_index].values)
    
    # Regression
    model = LinearRegression()
    model.fit(X, y.ravel())
    
    # Build result
    result = {
        'alpha': float(model.intercept_),
        'r_squared': float(model.score(X, y.ravel())),
        'overlapping_dates': float(len(common_index))
    }
    
    for i, col in enumerate(factors.columns):
        result[f'beta_{col}'] = float(model.coef_[i])
    
    return result  # type: ignore


# ============================================================================
# CORRELATION & STATISTICS
# ============================================================================

def calculate_correlation_matrix(
    price_data: Dict[str, pd.DataFrame],
    method: Literal['pearson', 'spearman', 'kendall'] = 'pearson'
) -> pd.DataFrame:
    """
    Calculate correlation matrix of returns.
    
    Args:
        price_data: Dict of ticker -> price DataFrame
        method: 'pearson', 'spearman', or 'kendall'
        
    Returns:
        Correlation matrix
    """
    # Extract returns
    returns_dict = {}
    for ticker, df in price_data.items():
        if not df.empty and 'Close' in df.columns:
            returns_dict[ticker] = df['Close'].pct_change().dropna()
    
    if not returns_dict:
        return pd.DataFrame()
    
    # Combine into DataFrame
    returns_df = pd.DataFrame(returns_dict)
    
    # Calculate correlation
    corr_matrix = returns_df.corr(method=method)
    
    return corr_matrix


def calculate_rolling_statistics(
    df: pd.DataFrame,
    window: int = 30
) -> pd.DataFrame:
    """
    Calculate rolling statistics (volatility, beta, etc.).
    
    Args:
        df: Price DataFrame
        window: Rolling window size
        
    Returns:
        DataFrame with rolling stats
    """
    stats = pd.DataFrame(index=df.index)
    
    if 'Close' in df.columns:
        returns = df['Close'].pct_change()
        
        stats['volatility'] = returns.rolling(window).std() * np.sqrt(252)
        stats['sharpe'] = (returns.rolling(window).mean() / 
                          returns.rolling(window).std()) * np.sqrt(252)
        stats['max_drawdown'] = (df['Close'] / df['Close'].cummax() - 1).rolling(window).min()
    
    return stats


# ============================================================================
# SCREENING & FILTERING
# ============================================================================

def apply_market_filters(
    ticker_info: pd.DataFrame,
    min_market_cap: float = 0,
    max_market_cap: float = float('inf'),
    sectors: Optional[List[str]] = None,
    min_pe: Optional[float] = None,
    max_pe: Optional[float] = None,
    min_beta: Optional[float] = None,
    max_beta: Optional[float] = None
) -> pd.DataFrame:
    """
    Apply screening filters to ticker list.
    
    Args:
        ticker_info: DataFrame with ticker metadata
        min_market_cap: Minimum market cap
        max_market_cap: Maximum market cap
        sectors: List of sectors to include
        min_pe: Minimum P/E ratio
        max_pe: Maximum P/E ratio
        min_beta: Minimum beta
        max_beta: Maximum beta
        
    Returns:
        Filtered DataFrame
    """
    filtered = ticker_info.copy()
    
    # Market cap filter (be lenient with 0/missing data)
    # Only filter if user explicitly set tight bounds (not default max)
    if min_market_cap > 0:
        # Keep tickers with market_cap >= min OR market_cap == 0 (missing data)
        filtered = filtered[
            (filtered['market_cap'] >= min_market_cap) | 
            (filtered['market_cap'] == 0)
        ]
    if max_market_cap < 1e13:  # Only filter if user set a reasonable max (not default $10T+)
        filtered = filtered[filtered['market_cap'] <= max_market_cap]
    
    # Sector filter
    if sectors and len(sectors) > 0:
        # Be lenient: include 'Unknown' sector if no specific sectors selected
        filtered = filtered[
            (filtered['sector'].isin(sectors)) | 
            (filtered['sector'] == 'Unknown')
        ]
    
    # P/E ratio filter (handle NaN values)
    # P/E ratio filter (handle NaN values) - be lenient and allow tickers with missing P/E
    if min_pe is not None and min_pe > 0:
        # Keep tickers that meet the min P/E OR where P/E is missing
        filtered = filtered[(filtered['pe_ratio'].isna()) | (filtered['pe_ratio'] >= min_pe)]
    if max_pe is not None and max_pe < float('inf'):
        # Keep tickers that meet the max P/E OR where P/E is missing
        filtered = filtered[(filtered['pe_ratio'].isna()) | (filtered['pe_ratio'] <= max_pe)]
    
    # Beta filter (handle NaN values) - be lenient and allow missing beta values
    if min_beta is not None and min_beta > -float('inf'):
        filtered = filtered[(filtered['beta'].isna()) | (filtered['beta'] >= min_beta)]
    if max_beta is not None and max_beta < float('inf'):
        filtered = filtered[(filtered['beta'].isna()) | (filtered['beta'] <= max_beta)]
    
    logger.info(f"📊 Filtered: {len(filtered)} / {len(ticker_info)} tickers passed")
    
    return filtered


# ============================================================================
# BACKTEST HELPER FUNCTIONS
# ============================================================================

def simulate_portfolio_returns(
    price_data: Dict[str, pd.DataFrame],
    weights: Dict[str, float],
    rebalance_freq: str = 'monthly'
) -> pd.Series:
    """
    Simulate portfolio returns with periodic rebalancing.
    
    Args:
        price_data: Dict of ticker -> price DataFrame
        weights: Dict of ticker -> weight
        rebalance_freq: 'daily', 'weekly', 'monthly', 'quarterly'
        
    Returns:
        Series with portfolio returns
    """
    # Combine all returns
    returns_dict = {}
    for ticker, df in price_data.items():
        if not df.empty and 'Close' in df.columns:
            returns_dict[ticker] = df['Close'].pct_change()
    
    if not returns_dict:
        return pd.Series()
    
    returns_df = pd.DataFrame(returns_dict)
    
    # Apply weights
    weighted_returns = returns_df * pd.Series(weights)
    portfolio_returns = weighted_returns.sum(axis=1)
    
    return portfolio_returns


def calculate_performance_metrics(returns: pd.Series) -> Dict[str, float]:
    """
    Calculate standard performance metrics.
    
    Args:
        returns: Return series
        
    Returns:
        Dict with metrics
    """
    if returns.empty:
        return {}
    
    cumulative_return = float((1 + returns).prod() - 1)  # type: ignore
    annual_return = float(returns.mean() * 252)
    annual_vol = float(returns.std() * np.sqrt(252))
    sharpe_ratio = float(annual_return / annual_vol if annual_vol > 0 else 0)
    
    # Drawdown
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative / running_max - 1)
    max_drawdown = float(drawdown.min())
    
    return {
        'cumulative_return': cumulative_return,
        'annual_return': annual_return,
        'annual_volatility': annual_vol,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'total_days': float(len(returns))
    }


# ============================================================================
# MOCK DATA FOR TESTING
# ============================================================================

def generate_mock_screening_data(n_tickers: int = 50) -> pd.DataFrame:
    """Generate mock ticker data for testing."""
    np.random.seed(42)
    
    sectors = ['Technology', 'Healthcare', 'Finance', 'Energy', 'Consumer']
    
    data = []
    for i in range(n_tickers):
        data.append({
            'ticker': f'TICK{i:03d}',
            'name': f'Company {i}',
            'sector': np.random.choice(sectors),
            'industry': f'Industry {i % 10}',
            'market_cap': np.random.lognormal(20, 2),
            'pe_ratio': np.random.uniform(5, 50),
            'beta': np.random.uniform(0.5, 2.0),
            'dividend_yield': np.random.uniform(0, 0.05),
        })
    
    return pd.DataFrame(data)
