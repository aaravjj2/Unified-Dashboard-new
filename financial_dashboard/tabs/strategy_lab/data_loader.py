"""
Strategy Lab Data Loader

Handles data fetching for strategy backtesting:
- Historical price data (yfinance with caching)
- Benchmark data (SPY, QQQ, custom)
- Factor data (from Attribution Lab)
- Universe data (Weekly/Monthly Picks, Options Lab)

PRODUCTION MODE: Real data integration with robust fallback mechanisms
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import yfinance as yf
from typing import Dict, List, Optional, Tuple
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_CACHE_DIR = PROJECT_ROOT / 'cache' / 'strategy_lab'
DATA_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Cache TTL (seconds) - 1 hour for price data
CACHE_TTL = 3600

# ============================================================================
# PRICE DATA FETCHING
# ============================================================================

def fetch_historical_prices(
    tickers: List[str],
    start_date: datetime,
    end_date: datetime,
    use_cache: bool = True
) -> pd.DataFrame:
    """
    Fetch historical adjusted close prices for multiple tickers using yfinance.
    
    Features:
    - Caching to prevent redundant API calls
    - Graceful fallback to synthetic data if API fails
    - Handles missing tickers and data gaps
    
    Args:
        tickers: List of ticker symbols (e.g., ['AAPL', 'MSFT', 'SPY'])
        start_date: Start date for historical data
        end_date: End date for historical data
        use_cache: Enable file-based caching (default: True)
        
    Returns:
        DataFrame with columns for each ticker, rows for each date
        Index: DatetimeIndex
        Values: Adjusted close prices
    """
    try:
        cache_key = f"prices_{'_'.join(sorted(tickers))}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
        cache_path = DATA_CACHE_DIR / cache_key
        
        # Check cache first
        if use_cache and cache_path.exists():
            cache_age = datetime.now().timestamp() - cache_path.stat().st_mtime
            if cache_age < CACHE_TTL:
                logger.info(f"📦 Using cached price data ({cache_age:.0f}s old)")
                df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
                return df
        
        # Fetch from yfinance
        logger.info(f"🌐 Fetching {len(tickers)} tickers from yfinance ({start_date.date()} to {end_date.date()})")
        
        data = yf.download(
            tickers,
            start=start_date,
            end=end_date,
            progress=False,
            auto_adjust=True,  # Use adjusted prices
            threads=True
        )
        
        if data.empty:
            logger.warning("⚠️  No data returned from yfinance, using fallback")
            return _generate_synthetic_prices(tickers, start_date, end_date)
        
        # Extract adjusted close prices
        if len(tickers) == 1:
            # Single ticker: data is Series or DataFrame with single column
            if isinstance(data, pd.DataFrame) and 'Close' in data.columns:
                prices = data[['Close']].rename(columns={'Close': tickers[0]})
            else:
                prices = data.to_frame(name=tickers[0]) if isinstance(data, pd.Series) else data
        else:
            # Multiple tickers: extract Close from multi-level columns
            if 'Close' in data.columns.get_level_values(0):
                prices = data['Close']
            else:
                prices = data
        
        # Remove any tickers with all NaN values
        prices = prices.dropna(axis=1, how='all')
        
        if prices.empty:
            logger.warning("⚠️  All tickers had missing data, using fallback")
            return _generate_synthetic_prices(tickers, start_date, end_date)
        
        # Forward fill missing values (up to 5 days)
        prices = prices.fillna(method='ffill', limit=5)
        
        # Cache results
        if use_cache:
            prices.to_csv(cache_path)
            logger.info(f"💾 Cached price data to {cache_path.name}")
        
        logger.info(f"✅ Fetched {len(prices.columns)} tickers, {len(prices)} days")
        return prices
        
    except Exception as e:
        logger.error(f"❌ Error fetching prices: {e}")
        logger.warning("⚠️  Falling back to synthetic price data")
        return _generate_synthetic_prices(tickers, start_date, end_date)


def fetch_benchmark_data(
    benchmark: str,
    start_date: datetime,
    end_date: datetime
) -> pd.Series:
    """
    Fetch benchmark price data (e.g., SPY for S&P 500).
    
    Args:
        benchmark: Benchmark ticker (SPY, QQQ, IWM, etc.)
        start_date: Start date
        end_date: End date
        
    Returns:
        Series with benchmark prices, DatetimeIndex
    """
    try:
        logger.info(f"📊 Fetching benchmark {benchmark}")
        
        stock = yf.Ticker(benchmark)
        hist = stock.history(start=start_date, end=end_date, auto_adjust=True)
        
        if hist.empty:
            logger.warning(f"⚠️  No benchmark data for {benchmark}, using synthetic")
            return _generate_synthetic_prices([benchmark], start_date, end_date)[benchmark]
        
        prices = hist['Close']
        logger.info(f"✅ Fetched {len(prices)} days of {benchmark} data")
        return prices
        
    except Exception as e:
        logger.error(f"❌ Error fetching benchmark {benchmark}: {e}")
        return _generate_synthetic_prices([benchmark], start_date, end_date)[benchmark]


def _generate_synthetic_prices(
    tickers: List[str],
    start_date: datetime,
    end_date: datetime,
    initial_price: float = 100.0
) -> pd.DataFrame:
    """
    Generate synthetic price data as fallback.
    
    Uses geometric Brownian motion (random walk with drift).
    
    Args:
        tickers: List of ticker symbols
        start_date: Start date
        end_date: End date
        initial_price: Starting price for simulation
        
    Returns:
        DataFrame with synthetic prices
    """
    logger.warning("🔶 GENERATING SYNTHETIC PRICE DATA (not real market data)")
    
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    n_days = len(dates)
    
    prices_dict = {}
    np.random.seed(42)  # Deterministic for testing
    
    for ticker in tickers:
        # Generate random walk
        daily_returns = np.random.normal(0.0005, 0.015, n_days)  # ~13% annual return, ~24% vol
        price_path = initial_price * np.cumprod(1 + daily_returns)
        prices_dict[ticker] = price_path
    
    df = pd.DataFrame(prices_dict, index=dates)
    logger.info(f"🔶 Generated {len(df)} days of synthetic data for {len(tickers)} tickers")
    return df


# ============================================================================
# FACTOR DATA (FROM ATTRIBUTION LAB)
# ============================================================================

def load_factor_data(
    start_date: datetime,
    end_date: datetime
) -> pd.DataFrame:
    """
    Load Fama-French factor data by delegating to Attribution Lab's data loader.
    
    This ensures consistency across labs and avoids duplicating the
    Fama-French integration logic.
    
    Args:
        start_date: Start date for factor data
        end_date: End date for factor data
        
    Returns:
        DataFrame with columns: market, size, value, momentum, quality
        Index: DatetimeIndex (daily data)
    """
    try:
        # Import Attribution Lab's data loader
        from financial_dashboard.tabs.attribution_lab.data_loader import load_factor_data as load_ff_factors
        
        factors = ['market', 'size', 'value', 'momentum', 'quality']
        factor_data = load_ff_factors(factors, start_date, end_date)
        
        logger.info(f"✅ Loaded {len(factor_data)} days of factor data from Attribution Lab")
        return factor_data
        
    except ImportError as e:
        logger.error(f"❌ Cannot import Attribution Lab data loader: {e}")
        return _generate_synthetic_factors(start_date, end_date)
        
    except Exception as e:
        logger.error(f"❌ Error loading factor data: {e}")
        return _generate_synthetic_factors(start_date, end_date)


def _generate_synthetic_factors(
    start_date: datetime,
    end_date: datetime
) -> pd.DataFrame:
    """Generate synthetic factor returns as fallback."""
    logger.warning("🔶 GENERATING SYNTHETIC FACTOR DATA")
    
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    n_days = len(dates)
    
    np.random.seed(42)
    
    factor_data = pd.DataFrame(index=dates)
    factor_data['market'] = np.random.normal(0.0004, 0.01, n_days)  # ~10% annual, 16% vol
    factor_data['size'] = np.random.normal(0.0001, 0.005, n_days)   # ~2.5% annual, 8% vol
    factor_data['value'] = np.random.normal(0.0002, 0.006, n_days)  # ~5% annual, 9.5% vol
    factor_data['momentum'] = np.random.normal(0.0003, 0.008, n_days)  # ~7.5% annual, 12.7% vol
    factor_data['quality'] = np.random.normal(0.0001, 0.004, n_days)  # ~2.5% annual, 6.3% vol
    
    logger.info(f"🔶 Generated {len(factor_data)} days of synthetic factor data")
    return factor_data


# ============================================================================
# UNIVERSE DATA (CROSS-LAB INTEGRATION)
# ============================================================================

def load_universe_tickers(universe_type: str) -> List[str]:
    """
    Load ticker universe from other labs or predefined lists.
    
    Integrates with:
    - Weekly Picks tab (latest weekly picks CSV)
    - Monthly Picks tab (latest monthly picks CSV)
    - Options Lab (high IV stocks)
    - Predefined lists (S&P 500, Tech stocks, etc.)
    
    Args:
        universe_type: One of:
            - 'weekly': Latest weekly picks
            - 'monthly': Latest monthly picks
            - 'sp500': S&P 500 constituents
            - 'tech': Major tech stocks
            - 'custom': User-defined (returns empty, user will input)
            
    Returns:
        List of ticker symbols
    """
    try:
        if universe_type == 'weekly':
            return _load_weekly_picks()
        elif universe_type == 'monthly':
            return _load_monthly_picks()
        elif universe_type == 'sp500':
            return _load_sp500_tickers()
        elif universe_type == 'tech':
            return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'NFLX', 'ADBE', 'CRM']
        elif universe_type == 'custom':
            return []  # User will input manually
        else:
            logger.warning(f"Unknown universe type: {universe_type}, using default tech stocks")
            return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'SPY']
            
    except Exception as e:
        logger.error(f"Error loading universe '{universe_type}': {e}")
        return ['AAPL', 'MSFT', 'SPY']  # Safe fallback


def _load_weekly_picks() -> List[str]:
    """Load tickers from latest weekly picks CSV."""
    try:
        outputs_dir = PROJECT_ROOT / 'outputs'
        weekly_csvs = list(outputs_dir.glob('top20_weekly_picks_*.csv'))
        
        if not weekly_csvs:
            logger.warning("No weekly picks CSV found")
            return []
        
        latest_csv = max(weekly_csvs, key=lambda p: p.stat().st_mtime)
        df = pd.read_csv(latest_csv)
        
        # Extract tickers (column might be 'ticker', 'Ticker', or first column)
        if 'ticker' in df.columns:
            tickers = df['ticker'].tolist()
        elif 'Ticker' in df.columns:
            tickers = df['Ticker'].tolist()
        else:
            tickers = df.iloc[:, 0].tolist()
        
        # Take top 10
        tickers = [str(t).upper().strip() for t in tickers[:10] if pd.notna(t)]
        logger.info(f"✅ Loaded {len(tickers)} tickers from weekly picks: {', '.join(tickers[:5])}...")
        return tickers
        
    except Exception as e:
        logger.error(f"Error loading weekly picks: {e}")
        return []


def _load_monthly_picks() -> List[str]:
    """Load tickers from latest monthly picks CSV."""
    try:
        outputs_dir = PROJECT_ROOT / 'outputs'
        monthly_csvs = list(outputs_dir.glob('*monthly_picks*.csv'))
        
        if not monthly_csvs:
            logger.warning("No monthly picks CSV found")
            return []
        
        latest_csv = max(monthly_csvs, key=lambda p: p.stat().st_mtime)
        df = pd.read_csv(latest_csv)
        
        if 'ticker' in df.columns:
            tickers = df['ticker'].tolist()
        elif 'Ticker' in df.columns:
            tickers = df['Ticker'].tolist()
        else:
            tickers = df.iloc[:, 0].tolist()
        
        tickers = [str(t).upper().strip() for t in tickers[:10] if pd.notna(t)]
        logger.info(f"✅ Loaded {len(tickers)} tickers from monthly picks: {', '.join(tickers[:5])}...")
        return tickers
        
    except Exception as e:
        logger.error(f"Error loading monthly picks: {e}")
        return []


def _load_sp500_tickers() -> List[str]:
    """
    Load S&P 500 constituents from Wikipedia.
    
    Returns top 20 by market cap for backtesting (to avoid excessive API calls).
    """
    try:
        # Fetch S&P 500 list from Wikipedia
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        tables = pd.read_html(url)
        sp500_df = tables[0]
        
        # Get tickers
        tickers = sp500_df['Symbol'].tolist()[:20]  # Top 20 to limit API load
        tickers = [str(t).replace('.', '-') for t in tickers]  # Fix ticker format
        
        logger.info(f"✅ Loaded {len(tickers)} S&P 500 tickers")
        return tickers
        
    except Exception as e:
        logger.error(f"Error loading S&P 500 tickers: {e}")
        # Fallback to hardcoded top 10
        return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'JPM', 'V']


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def calculate_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate daily returns from price data.
    
    Args:
        prices: DataFrame of prices (tickers as columns)
        
    Returns:
        DataFrame of daily returns (same structure)
    """
    return prices.pct_change().dropna()


def calculate_portfolio_returns(
    prices: pd.DataFrame,
    weights: Dict[str, float]
) -> pd.Series:
    """
    Calculate portfolio returns from individual ticker prices and weights.
    
    Args:
        prices: DataFrame of ticker prices
        weights: Dict mapping ticker -> weight (must sum to 1.0)
        
    Returns:
        Series of daily portfolio returns
    """
    returns = calculate_returns(prices)
    
    # Filter to tickers in weights
    valid_tickers = [t for t in weights.keys() if t in returns.columns]
    returns_subset = returns[valid_tickers]
    
    # Weight vector
    weight_vector = pd.Series(weights)[valid_tickers]
    weight_vector = weight_vector / weight_vector.sum()  # Normalize to 1.0
    
    # Portfolio returns = weighted sum
    portfolio_returns = returns_subset.dot(weight_vector)
    return portfolio_returns


def clear_cache():
    """Clear all cached price data."""
    try:
        import shutil
        shutil.rmtree(DATA_CACHE_DIR)
        DATA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("✅ Cleared Strategy Lab cache")
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
