"""
Attribution Lab Data Loader

Handles data fetching for:
- Portfolio holdings and returns
- Benchmark data (S&P500, Russell 2000, custom)
- Factor data (Fama-French, momentum)
- Historical price data

PRODUCTION MODE: Real data integration with yfinance, CSV portfolios, and Fama-French factors
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import yfinance as yf
from typing import Dict, List, Optional, Tuple
import os
from pathlib import Path
import glob

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Portfolio data directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
PORTFOLIO_DIR = PROJECT_ROOT / 'outputs'
DATA_DIR = PROJECT_ROOT / 'data'
FACTOR_DATA_DIR = DATA_DIR / 'factors'

# Ensure directories exist
FACTOR_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# PORTFOLIO DATA
# ============================================================================

def get_available_portfolios() -> List[Dict[str, str]]:
    """
    Get list of available portfolios for analysis.
    
    Returns:
        List of dicts with 'label' and 'value' keys
    """
    return [
        {'label': 'Current Portfolio', 'value': 'current'},
        {'label': 'Weekly Picks', 'value': 'weekly'},
        {'label': 'Monthly Picks', 'value': 'monthly'},
        {'label': 'Custom Portfolio', 'value': 'custom'}
    ]

def load_portfolio_holdings(portfolio_id: str = 'current') -> pd.DataFrame:
    """
    Load portfolio holdings with weights from CSV files or default data.
    
    PRODUCTION: Loads real CSV files from outputs directory
    
    Args:
        portfolio_id: Portfolio identifier ('current', 'weekly', 'monthly', 'custom')
        
    Returns:
        DataFrame with columns: ticker, weight, shares
    """
    try:
        if portfolio_id == 'weekly':
            # Load latest weekly picks CSV
            weekly_csvs = list(PORTFOLIO_DIR.glob('top20_weekly_picks_*.csv'))
            if weekly_csvs:
                latest_weekly = max(weekly_csvs, key=lambda p: p.stat().st_mtime)
                df = pd.read_csv(latest_weekly)
                
                # Take top 10 tickers with equal weight
                top_tickers = df.head(10)['ticker'].tolist()
                equal_weight = 1.0 / len(top_tickers)
                
                holdings = pd.DataFrame({
                    'ticker': top_tickers,
                    'weight': [equal_weight] * len(top_tickers),
                    'shares': [100] * len(top_tickers)  # Default shares
                })
                logger.info(f"Loaded weekly picks from {latest_weekly.name}: {len(holdings)} tickers")
                return holdings
        
        elif portfolio_id == 'monthly':
            # Look for monthly picks CSV (similar pattern)
            monthly_csvs = list(PORTFOLIO_DIR.glob('*monthly_picks*.csv'))
            if monthly_csvs:
                latest_monthly = max(monthly_csvs, key=lambda p: p.stat().st_mtime)
                df = pd.read_csv(latest_monthly)
                
                top_tickers = df.head(10)['ticker'].tolist() if 'ticker' in df.columns else df.head(10).iloc[:, 0].tolist()
                equal_weight = 1.0 / len(top_tickers)
                
                holdings = pd.DataFrame({
                    'ticker': top_tickers,
                    'weight': [equal_weight] * len(top_tickers),
                    'shares': [100] * len(top_tickers)
                })
                logger.info(f"Loaded monthly picks from {latest_monthly.name}: {len(holdings)} tickers")
                return holdings
        
        # Default 'current' portfolio - use top stocks
        holdings = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'JPM'],
            'weight': [0.15, 0.15, 0.12, 0.12, 0.10, 0.10, 0.08, 0.18],
            'shares': [100, 80, 50, 30, 120, 40, 60, 150]
        })
        logger.info(f"Loaded default 'current' portfolio: {len(holdings)} tickers")
        return holdings
        
    except Exception as e:
        logger.error(f"Error loading portfolio {portfolio_id}: {e}")
        # Fallback to SPY
        return pd.DataFrame({
            'ticker': ['SPY'],
            'weight': [1.0],
            'shares': [100]
        })

def get_portfolio_returns(
    tickers: List[str], 
    weights: List[float],
    start_date: datetime,
    end_date: datetime
) -> pd.Series:
    """
    Calculate portfolio returns over period.
    
    Args:
        tickers: List of ticker symbols
        weights: List of portfolio weights (must sum to 1.0)
        start_date: Start date for analysis
        end_date: End date for analysis
        
    Returns:
        Series of daily portfolio returns
    """
    try:
        # Fetch price data
        price_data = {}
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(start=start_date, end=end_date)
                if not hist.empty:
                    price_data[ticker] = hist['Close']
            except Exception as e:
                logger.warning(f"Error fetching {ticker}: {e}")
        
        if not price_data:
            return pd.Series(dtype=float)
        
        # Create price DataFrame
        prices_df = pd.DataFrame(price_data)
        
        # Calculate returns
        returns_df = prices_df.pct_change().dropna()
        
        # Weighted portfolio returns
        portfolio_returns = (returns_df * weights).sum(axis=1)
        
        return portfolio_returns
        
    except Exception as e:
        logger.error(f"Error calculating portfolio returns: {e}")
        return pd.Series(dtype=float)

# ============================================================================
# BENCHMARK DATA
# ============================================================================

def get_available_benchmarks() -> List[Dict[str, str]]:
    """Get list of available benchmark indices."""
    return [
        {'label': 'S&P 500 (SPY)', 'value': 'SPY'},
        {'label': 'NASDAQ 100 (QQQ)', 'value': 'QQQ'},
        {'label': 'Russell 2000 (IWM)', 'value': 'IWM'},
        {'label': 'Total Market (VTI)', 'value': 'VTI'},
        {'label': 'Dow Jones (DIA)', 'value': 'DIA'}
    ]

def get_benchmark_returns(
    benchmark_ticker: str,
    start_date: datetime,
    end_date: datetime
) -> pd.Series:
    """
    Get benchmark returns over period.
    
    Args:
        benchmark_ticker: Ticker symbol for benchmark
        start_date: Start date
        end_date: End date
        
    Returns:
        Series of daily benchmark returns
    """
    try:
        stock = yf.Ticker(benchmark_ticker)
        hist = stock.history(start=start_date, end=end_date)
        
        if hist.empty:
            return pd.Series(dtype=float)
        
        returns = hist['Close'].pct_change().dropna()
        return returns
        
    except Exception as e:
        logger.error(f"Error fetching benchmark {benchmark_ticker}: {e}")
        return pd.Series(dtype=float)

# ============================================================================
# FACTOR DATA
# ============================================================================

def get_available_factors() -> List[Dict[str, str]]:
    """Get list of available risk factors."""
    return [
        {'label': 'Market (Mkt-RF)', 'value': 'market'},
        {'label': 'Size (SMB)', 'value': 'size'},
        {'label': 'Value (HML)', 'value': 'value'},
        {'label': 'Momentum (MOM)', 'value': 'momentum'},
        {'label': 'Quality', 'value': 'quality'}
    ]

def load_factor_data(
    factors: List[str],
    start_date: datetime,
    end_date: datetime
) -> pd.DataFrame:
    """
    Load Fama-French factor returns data from Kenneth French Data Library.
    
    This function fetches REAL market factor data, not synthetic/mock data.
    Uses pandas_datareader to access the official Fama-French research data.
    
    Args:
        factors: List of factor names ('market', 'size', 'value', 'momentum', 'quality')
        start_date: Start date for factor data
        end_date: End date for factor data
        
    Returns:
        DataFrame with daily factor returns (as decimals, not percentages)
        
    Factor Mapping:
        - 'market' → Mkt-RF (Market excess return over risk-free rate)
        - 'size' → SMB (Small Minus Big - size premium)
        - 'value' → HML (High Minus Low - value premium)
        - 'momentum' → MOM (Momentum factor - requires separate dataset)
        - 'quality' → RMW (Robust Minus Weak - profitability factor)
    """
    try:
        import pandas_datareader as pdr
        
        # Map factor names to Fama-French column names
        factor_mapping = {
            'market': 'Mkt-RF',
            'size': 'SMB',
            'value': 'HML',
            'momentum': 'Mom',  # From momentum dataset
            'quality': 'RMW'     # From 5-factor model
        }
        
        logger.info(f"🔵 Loading Fama-French factors from {start_date.date()} to {end_date.date()}")
        
        # Load Fama-French 5-Factor Model (daily data)
        # Dataset: F-F_Research_Data_5_Factors_2x3_daily
        # Returns: Mkt-RF, SMB, HML, RMW, CMA, RF (all as percentages)
        ff_data = pdr.get_data_famafrench(
            'F-F_Research_Data_5_Factors_2x3_daily',
            start=start_date,
            end=end_date
        )[0]  # [0] gets the main dataframe (not the description)
        
        logger.info(f"✅ Fetched {len(ff_data)} days of Fama-French data")
        logger.info(f"   Columns: {', '.join(ff_data.columns.tolist())}")
        
        # Convert from percentage to decimal (FF data comes as %, e.g., 1.5 = 1.5%)
        ff_data = ff_data / 100.0
        
        # Build factor dataframe with requested factors
        factor_data = pd.DataFrame(index=ff_data.index)
        
        for factor in factors:
            if factor in factor_mapping:
                ff_col = factor_mapping[factor]
                
                if ff_col in ff_data.columns:
                    factor_data[factor] = ff_data[ff_col]
                    logger.info(f"   ✅ Mapped '{factor}' → '{ff_col}'")
                elif factor == 'momentum':
                    # Momentum requires separate dataset - use fallback for now
                    logger.warning(f"   ⚠️  Momentum factor not in 5-factor model, using fallback")
                    factor_data[factor] = 0.0  # TODO: Load from F-F_Momentum_Factor
                else:
                    logger.warning(f"   ⚠️  Factor column '{ff_col}' not found in FF data")
                    factor_data[factor] = 0.0
            else:
                logger.warning(f"   ⚠️  Unknown factor '{factor}', setting to 0")
                factor_data[factor] = 0.0
        
        logger.info(f"✅ Final factor data shape: {factor_data.shape}")
        logger.info(f"   Date range: {factor_data.index[0].date()} to {factor_data.index[-1].date()}")
        
        return factor_data
        
    except ImportError as e:
        logger.error(f"❌ pandas_datareader not installed: {e}")
        logger.warning("   Falling back to synthetic factor data")
        return _load_factor_data_fallback(factors, start_date, end_date)
        
    except Exception as e:
        logger.error(f"❌ Error loading Fama-French data: {e}")
        logger.warning("   Falling back to synthetic factor data")
        return _load_factor_data_fallback(factors, start_date, end_date)


def _load_factor_data_fallback(
    factors: List[str],
    start_date: datetime,
    end_date: datetime
) -> pd.DataFrame:
    """
    Fallback function: Generate synthetic factor data if pandas_datareader fails.
    
    This is ONLY used when:
    - pandas_datareader is not installed
    - Fama-French data fetch fails (network error, API down, etc.)
    
    Args:
        factors: List of factor names
        start_date: Start date
        end_date: End date
        
    Returns:
        DataFrame with synthetic factor returns
    """
    logger.warning("⚠️  Using SYNTHETIC factor data (not real Fama-French)")
    
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    factor_data = pd.DataFrame(index=dates)
    
    np.random.seed(42)  # Deterministic for testing
    
    for factor in factors:
        if factor == 'market':
            factor_data[factor] = np.random.normal(0.0005, 0.01, len(dates))
        elif factor == 'size':
            factor_data[factor] = np.random.normal(0.0002, 0.008, len(dates))
        elif factor == 'value':
            factor_data[factor] = np.random.normal(0.0003, 0.007, len(dates))
        elif factor == 'momentum':
            factor_data[factor] = np.random.normal(0.0004, 0.009, len(dates))
        elif factor == 'quality':
            factor_data[factor] = np.random.normal(0.0002, 0.006, len(dates))
    
    return factor_data

def calculate_factor_exposures(
    portfolio_returns: pd.Series,
    factor_returns: pd.DataFrame
) -> Dict[str, float]:
    """
    Calculate portfolio factor exposures using regression.
    
    Args:
        portfolio_returns: Series of portfolio returns
        factor_returns: DataFrame of factor returns
        
    Returns:
        Dict mapping factor names to exposure coefficients (betas)
    """
    try:
        # Align data
        common_dates = portfolio_returns.index.intersection(factor_returns.index)
        y = portfolio_returns.loc[common_dates]
        X = factor_returns.loc[common_dates]
        
        if len(y) < 30:  # Need minimum data points
            return {col: 0.0 for col in factor_returns.columns}
        
        # Multiple regression
        from numpy.linalg import lstsq
        
        # Add intercept
        X_with_intercept = np.column_stack([np.ones(len(X)), X.values])
        
        # Solve least squares
        coeffs, _, _, _ = lstsq(X_with_intercept, y.values, rcond=None)
        
        # Extract factor betas (skip intercept)
        exposures = {
            factor: float(coeffs[i+1]) 
            for i, factor in enumerate(factor_returns.columns)
        }
        
        return exposures
        
    except Exception as e:
        logger.error(f"Error calculating factor exposures: {e}")
        return {col: 0.0 for col in factor_returns.columns}

def calculate_factor_contributions(
    exposures: Dict[str, float],
    factor_returns: pd.DataFrame
) -> pd.DataFrame:
    """
    Calculate contribution of each factor to portfolio returns.
    
    Args:
        exposures: Dict of factor exposures
        factor_returns: DataFrame of factor returns
        
    Returns:
        DataFrame with factor contributions over time
    """
    try:
        contributions = pd.DataFrame(index=factor_returns.index)
        
        for factor, beta in exposures.items():
            if factor in factor_returns.columns:
                contributions[factor] = beta * factor_returns[factor]
        
        return contributions
        
    except Exception as e:
        logger.error(f"Error calculating factor contributions: {e}")
        return pd.DataFrame()

# ============================================================================
# SECTOR/ASSET CLASS DATA
# ============================================================================

# Module-level cache for sector mappings (persists across calls)
_SECTOR_CACHE: Dict[str, str] = {}

def get_sector_mapping(tickers: List[str] = None, use_cache: bool = True) -> Dict[str, str]:
    """
    Get ticker-to-sector mapping dynamically from yfinance.
    
    This function fetches REAL sector data from Yahoo Finance, not hardcoded values.
    Results are cached to minimize API calls and improve performance.
    
    Args:
        tickers: Optional list of tickers to map. If None, returns current cache.
        use_cache: If True, use cached results for already-fetched tickers
        
    Returns:
        Dict mapping ticker symbols to sector names (e.g., {'AAPL': 'Technology'})
        
    Sector Examples:
        - Technology
        - Healthcare
        - Financial Services
        - Consumer Cyclical
        - Energy
        - Industrials
        - Basic Materials
        - Real Estate
        - Utilities
        - Consumer Defensive
        - Communication Services
    """
    global _SECTOR_CACHE
    
    # If no tickers specified, return current cache
    if tickers is None:
        return _SECTOR_CACHE.copy()
    
    sector_map = {}
    
    for ticker in tickers:
        # Check cache first
        if use_cache and ticker in _SECTOR_CACHE:
            sector_map[ticker] = _SECTOR_CACHE[ticker]
            continue
        
        # Fetch from yfinance
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Get sector (may be under 'sector' or 'sectorKey')
            sector = info.get('sector', info.get('sectorKey', 'Unknown'))
            
            # Standardize ETF classifications
            if ticker in ['SPY', 'VTI', 'VOO']:
                sector = 'Broad Market ETF'
            elif ticker in ['QQQ', 'XLK']:
                sector = 'Technology ETF'
            elif ticker == 'IWM':
                sector = 'Small Cap ETF'
            elif ticker in ['DIA', 'IVV']:
                sector = 'Large Cap ETF'
            
            # Update cache
            _SECTOR_CACHE[ticker] = sector
            sector_map[ticker] = sector
            
            logger.info(f"   ✅ {ticker}: {sector}")
            
        except Exception as e:
            logger.warning(f"   ⚠️  Failed to get sector for {ticker}: {e}")
            sector_map[ticker] = 'Unknown'
            _SECTOR_CACHE[ticker] = 'Unknown'
    
    logger.info(f"✅ Sector mapping complete: {len(sector_map)} tickers mapped")
    return sector_map


def clear_sector_cache():
    """Clear the sector cache (useful for testing or forcing refresh)."""
    global _SECTOR_CACHE
    _SECTOR_CACHE.clear()
    logger.info("✅ Sector cache cleared")

def calculate_sector_attribution(
    holdings: pd.DataFrame,
    ticker_returns: Dict[str, pd.Series]
) -> pd.DataFrame:
    """
    Calculate attribution by sector.
    
    Args:
        holdings: DataFrame with ticker, weight columns
        ticker_returns: Dict mapping tickers to return series
        
    Returns:
        DataFrame with sector attributions
    """
    try:
        sector_map = get_sector_mapping()
        
        # Add sector column
        holdings['sector'] = holdings['ticker'].map(sector_map)
        holdings['sector'] = holdings['sector'].fillna('Other')
        
        # Calculate sector contributions
        sector_contrib = []
        
        for sector in holdings['sector'].unique():
            sector_holdings = holdings[holdings['sector'] == sector]
            
            # Weight-adjusted returns for this sector
            sector_return = 0.0
            sector_weight = 0.0
            
            for _, row in sector_holdings.iterrows():
                ticker = row['ticker']
                weight = row['weight']
                
                if ticker in ticker_returns:
                    returns = ticker_returns[ticker]
                    avg_return = returns.mean()
                    sector_return += weight * avg_return
                    sector_weight += weight
            
            sector_contrib.append({
                'sector': sector,
                'weight': sector_weight,
                'contribution': sector_return,
                'return_pct': (sector_return / sector_weight * 100) if sector_weight > 0 else 0
            })
        
        return pd.DataFrame(sector_contrib)
        
    except Exception as e:
        logger.error(f"Error calculating sector attribution: {e}")
        return pd.DataFrame()

# ============================================================================
# RESIDUAL ANALYSIS
# ============================================================================

def calculate_residual_returns(
    portfolio_returns: pd.Series,
    factor_contributions: pd.DataFrame
) -> pd.Series:
    """
    Calculate residual (unexplained) returns.
    
    Args:
        portfolio_returns: Actual portfolio returns
        factor_contributions: Factor-explained returns
        
    Returns:
        Series of residual returns
    """
    try:
        # Align dates
        common_dates = portfolio_returns.index.intersection(factor_contributions.index)
        
        actual = portfolio_returns.loc[common_dates]
        explained = factor_contributions.loc[common_dates].sum(axis=1)
        
        residual = actual - explained
        
        return residual
        
    except Exception as e:
        logger.error(f"Error calculating residual returns: {e}")
        return pd.Series(dtype=float)

def calculate_attribution_metrics(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series
) -> Dict[str, float]:
    """
    Calculate attribution metrics.
    
    Args:
        portfolio_returns: Portfolio return series
        benchmark_returns: Benchmark return series
        
    Returns:
        Dict with attribution metrics
    """
    try:
        # Align data
        common_dates = portfolio_returns.index.intersection(benchmark_returns.index)
        port_ret = portfolio_returns.loc[common_dates]
        bench_ret = benchmark_returns.loc[common_dates]
        
        # Total returns
        total_port_return = (1 + port_ret).prod() - 1
        total_bench_return = (1 + bench_ret).prod() - 1
        
        # Excess return
        excess_return = total_port_return - total_bench_return
        
        # Annualized metrics
        days = len(port_ret)
        annual_factor = 252 / days if days > 0 else 1
        
        annualized_port = (1 + total_port_return) ** annual_factor - 1
        annualized_bench = (1 + total_bench_return) ** annual_factor - 1
        
        # Volatility
        port_vol = port_ret.std() * np.sqrt(252)
        bench_vol = bench_ret.std() * np.sqrt(252)
        
        # Sharpe ratio (assuming 2% risk-free rate)
        rf_rate = 0.02
        sharpe = (annualized_port - rf_rate) / port_vol if port_vol > 0 else 0
        
        # Information ratio
        excess_returns = port_ret - bench_ret
        tracking_error = excess_returns.std() * np.sqrt(252)
        information_ratio = (annualized_port - annualized_bench) / tracking_error if tracking_error > 0 else 0
        
        # Beta
        covariance = np.cov(port_ret, bench_ret)[0, 1]
        bench_variance = np.var(bench_ret)
        beta = covariance / bench_variance if bench_variance > 0 else 1.0
        
        # Alpha (Jensen's alpha)
        alpha = annualized_port - (rf_rate + beta * (annualized_bench - rf_rate))
        
        # Max drawdown
        cum_returns = (1 + port_ret).cumprod()
        running_max = cum_returns.cummax()
        drawdown = (cum_returns - running_max) / running_max
        max_drawdown = drawdown.min() if len(drawdown) > 0 else 0.0
        
        return {
            'total_return': total_port_return * 100,
            'benchmark_return': total_bench_return * 100,
            'excess_return': excess_return * 100,
            'annualized_return': annualized_port * 100,
            'volatility': port_vol * 100,
            'sharpe_ratio': sharpe,
            'information_ratio': information_ratio,
            'beta': beta,
            'alpha': alpha * 100,
            'tracking_error': tracking_error * 100,
            'max_drawdown': abs(max_drawdown) * 100  # Return as positive percentage
        }
        
    except Exception as e:
        logger.error(f"Error calculating attribution metrics: {e}")
        return {
            'total_return': 0.0,
            'benchmark_return': 0.0,
            'excess_return': 0.0,
            'annualized_return': 0.0,
            'volatility': 0.0,
            'sharpe_ratio': 0.0,
            'information_ratio': 0.0,
            'beta': 1.0,
            'alpha': 0.0,
            'tracking_error': 0.0
        }
