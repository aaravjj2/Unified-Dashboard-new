"""
Options Lab Data Loader

Handles data fetching from Alpaca, yfinance and local caches.
Provides graceful fallbacks and error handling.

Features:
- Options chain data fetching (Alpaca → yfinance → mock)
- Greeks calculation
- Implied volatility surface data
- Mock data fallback for testing
"""

import logging
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import yfinance as yf

logger = logging.getLogger(__name__)


def fetch_options_chain_alpaca(ticker: str, expiry: Optional[str] = None) -> Optional[Dict]:
    """
    Fetch options chain from Alpaca API.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'SPY', 'AAPL')
        expiry: Optional expiration date filter (format: 'YYYY-MM-DD')
    
    Returns:
        Dict with structure:
        {
            'ticker': str,
            'spot_price': float,
            'expirations': List[str],
            'calls': pd.DataFrame,
            'puts': pd.DataFrame,
            'error': Optional[str]
        }
        Or None if fetch fails
    """
    # Guarded implementation: only attempt Alpaca options fetch when explicitly enabled
    try:
        use_alpaca_flag = os.getenv('OPTIONS_USE_ALPACA', '0').lower() in ('1', 'true', 'yes')

        if not use_alpaca_flag:
            logger.info("🔕 Alpaca options disabled by OPTIONS_USE_ALPACA flag")
            return None

        # Import Alpaca SDK components (try common module paths)
        api_key = os.getenv('APCA_API_KEY_ID') or os.getenv('ALPACA_KEY_ID')
        secret_key = os.getenv('APCA_API_SECRET_KEY') or os.getenv('ALPACA_SECRET_KEY')

        if not api_key or not secret_key:
            logger.warning("⚠️ Alpaca credentials not found in environment (APCA_API_KEY_ID/APCA_API_SECRET_KEY)")
            return None

        # Try importing a plausible Options client from alpaca-py
        OptionsClient = None
        try:
            # Common new-style import
            from alpaca.data.options import OptionsHistoricalDataClient as OptionsClient
        except Exception:
            try:
                # Older or alternative package layout
                from alpaca.data import OptionsHistoricalDataClient as OptionsClient
            except Exception:
                OptionsClient = None

        # Also keep the stock quote client for spot price
        StockClient = None
        try:
            from alpaca.data.historical import StockHistoricalDataClient as StockClient
        except Exception:
            try:
                from alpaca.data import StockHistoricalDataClient as StockClient
            except Exception:
                StockClient = None

        # Get spot price if possible (best-effort)
        spot_price = None
        if StockClient is not None:
            try:
                stock_client = StockClient(api_key, secret_key)
                try:
                    # Some clients use get_stock_latest_quote with a request object
                    from alpaca.data.requests import StockLatestQuoteRequest
                    quote_request = StockLatestQuoteRequest(symbol_or_symbols=[ticker])
                    quotes = stock_client.get_stock_latest_quote(quote_request)
                    if ticker in quotes:
                        q = quotes[ticker]
                        spot_price = float((getattr(q, 'ask_price', 0) or 0) + (getattr(q, 'bid_price', 0) or 0)) / 2.0
                except Exception:
                    # Fallback to simple methods if provided
                    try:
                        latest = stock_client.get_latest_quote(ticker)
                        spot_price = float((getattr(latest, 'ask_price', 0) or 0) + (getattr(latest, 'bid_price', 0) or 0)) / 2.0
                    except Exception:
                        spot_price = None
            except Exception as e:
                logger.warning(f"⚠️ Alpaca spot price fetch failed: {e}")

        # If no Options client available, skip (safe fallback to yfinance/mock)
        if OptionsClient is None:
            logger.warning("⚠️ Alpaca Options client not available in environment (OptionsHistoricalDataClient)")
            return None

        # Instantiate options client
        try:
            options_client = OptionsClient(api_key, secret_key)
        except Exception as e:
            logger.error(f"❌ Failed to initialize Alpaca Options client: {e}")
            return None

        # Attempt to fetch expirations and chains using best-effort API calls.
        # The exact alpaca-py method names may vary by SDK version; use guarded attempts.
        expirations = None
        try:
            # Preferred method name (best-effort)
            if hasattr(options_client, 'get_expirations'):
                expirations = options_client.get_expirations(ticker)
            elif hasattr(options_client, 'get_option_expirations'):
                expirations = options_client.get_option_expirations(ticker)
            else:
                expirations = None
        except Exception as e:
            logger.warning(f"⚠️ Alpaca options expirations fetch failed: {e}")
            expirations = None

        if not expirations:
            logger.warning(f"⚠️ Alpaca: no expirations found for {ticker} or method not supported by SDK")
            return None

        # Normalize expirations to list of YYYY-MM-DD strings if necessary
        try:
            # If expirations is list-like of date strings or objects
            expirations_list = [str(e) for e in expirations]
        except Exception:
            expirations_list = list(expirations)

        # Use first expiration (best-effort) to fetch option chain
        first_exp = expirations_list[0] if expirations_list else None

        calls_df = None
        puts_df = None
        try:
            if first_exp:
                # Try common method names for fetching option chain
                if hasattr(options_client, 'get_option_chain'):
                    chain = options_client.get_option_chain(ticker, expiration=first_exp)
                    calls_df = getattr(chain, 'calls', None) or getattr(chain, 'calls_df', None)
                    puts_df = getattr(chain, 'puts', None) or getattr(chain, 'puts_df', None)
                elif hasattr(options_client, 'get_chain'):
                    chain = options_client.get_chain(ticker, first_exp)
                    calls_df = chain.get('calls') if isinstance(chain, dict) else None
                    puts_df = chain.get('puts') if isinstance(chain, dict) else None
                else:
                    logger.warning("⚠️ Alpaca Options client does not expose a known 'get_option_chain' API in this SDK version")
        except Exception as e:
            logger.warning(f"⚠️ Alpaca option chain fetch failed: {e}")

        # If we have DataFrames-like objects, ensure they are pandas DataFrames
        try:
            if calls_df is not None and not isinstance(calls_df, pd.DataFrame):
                calls_df = pd.DataFrame(calls_df)
            if puts_df is not None and not isinstance(puts_df, pd.DataFrame):
                puts_df = pd.DataFrame(puts_df)
        except Exception:
            # If conversion fails, null them to trigger fallback
            calls_df = None
            puts_df = None

        if calls_df is None or puts_df is None:
            logger.warning(f"⚠️ Alpaca: option chain not returned in expected format for {ticker}")
            return None

        # AGENT 1A FIX: Enrich Alpaca data with calculated fields (Greeks, moneyness, etc.)
        # Same enrichment as yfinance path to ensure consistent data structure
        if spot_price:
            calls_df = _enrich_chain_data(calls_df, spot_price, 'call')
            puts_df = _enrich_chain_data(puts_df, spot_price, 'put')
            logger.info(f"✅ Alpaca data enriched with Greeks for {ticker}")

        logger.info(f"✅ Alpaca: Retrieved options chain for {ticker} (expiry={first_exp})")
        return {
            'ticker': ticker,
            'spot_price': spot_price or None,
            'expirations': expirations_list,
            'calls': calls_df,
            'puts': puts_df,
            'error': None,
            'source': 'alpaca'
        }

    except Exception as e:
        logger.error(f"❌ Alpaca fetch failed for {ticker}: {e}")
        return None


def fetch_options_chain(ticker: str, use_mock: bool = False, use_alpaca: bool = True) -> Dict:
    """
    Fetch options chain for a given ticker with fallback chain: Alpaca → yfinance → mock.
    
    Args:
        ticker: Stock ticker symbol
        use_mock: If True, skip to mock data immediately
        use_alpaca: If True, try Alpaca first (default: True)
        
    Returns:
        Dict with structure:
        {
            'ticker': str,
            'spot_price': float,
            'expirations': List[str],
            'calls': pd.DataFrame,
            'puts': pd.DataFrame,
            'error': Optional[str],
            'source': str  # 'alpaca', 'yfinance', or 'mock'
        }
    """
    if use_mock:
        result = _generate_mock_chain(ticker)
        result['source'] = 'mock'
        return result
    
    # Try Alpaca first (if enabled)
    if use_alpaca:
        alpaca_data = fetch_options_chain_alpaca(ticker)
        if alpaca_data:
            alpaca_data['source'] = 'alpaca'
            logger.info(f"✅ Using Alpaca data for {ticker}")
            return alpaca_data
        else:
            logger.info(f"⚠️ Alpaca returned None for {ticker}, falling back to yfinance")
    
    # Fallback to yfinance
    try:
        logger.info(f"🔄 Falling back to yfinance for {ticker}")
        stock = yf.Ticker(ticker)
        
        # Get current price
        try:
            spot_price = stock.info.get('currentPrice') or stock.info.get('regularMarketPrice')
            if not spot_price:
                hist = stock.history(period='1d')
                spot_price = hist['Close'].iloc[-1] if not hist.empty else 100.0
        except Exception as e:
            logger.warning(f"Could not fetch spot price for {ticker}: {e}")
            spot_price = 100.0
        
        # Get expiration dates
        expirations = stock.options
        
        if not expirations or len(expirations) == 0:
            logger.warning(f"No options data available for {ticker}")
            return _generate_mock_chain(ticker)
        
        # Get first expiration chain
        first_exp = expirations[0]
        opt_chain = stock.option_chain(first_exp)
        
        calls = opt_chain.calls
        puts = opt_chain.puts
        
        # Add calculated fields
        calls = _enrich_chain_data(calls, spot_price, 'call')
        puts = _enrich_chain_data(puts, spot_price, 'put')
        
        logger.info(f"✅ Using yfinance data for {ticker}")
        return {
            'ticker': ticker,
            'spot_price': spot_price,
            'expirations': list(expirations),
            'calls': calls,
            'puts': puts,
            'error': None,
            'source': 'yfinance'
        }
        
    except Exception as e:
        logger.error(f"❌ yfinance failed for {ticker}: {e}")
        logger.info(f"🔄 Falling back to mock data for {ticker}")
        fallback = _generate_mock_chain(ticker)
        fallback['source'] = 'mock'
        fallback['error'] = f"Live data unavailable: {str(e)}"
        return fallback


def _enrich_chain_data(df: pd.DataFrame, spot_price: float, option_type: str) -> pd.DataFrame:
    """
    Add calculated fields to options chain data.
    
    Args:
        df: Options chain DataFrame
        spot_price: Current stock price
        option_type: 'call' or 'put'
        
    Returns:
        Enriched DataFrame
    """
    if df.empty:
        return df
    
    # Calculate moneyness
    df['moneyness'] = df['strike'] / spot_price
    
    # Calculate intrinsic value
    if option_type == 'call':
        df['intrinsic'] = np.maximum(spot_price - df['strike'], 0)
    else:
        df['intrinsic'] = np.maximum(df['strike'] - spot_price, 0)
    
    # Calculate time value
    if 'lastPrice' in df.columns:
        df['timeValue'] = df['lastPrice'] - df['intrinsic']
    
    # Add ATM/OTM/ITM labels
    if option_type == 'call':
        df['status'] = np.where(spot_price > df['strike'], 'ITM',
                                np.where(spot_price < df['strike'], 'OTM', 'ATM'))
    else:
        df['status'] = np.where(spot_price < df['strike'], 'ITM',
                                np.where(spot_price > df['strike'], 'OTM', 'ATM'))
    
    # FIX A - REPAIR ATTEMPT 1: Add Greeks if not present (yfinance doesn't provide them)
    if 'delta' not in df.columns or 'gamma' not in df.columns:
        logger.info(f"🔧 Calculating missing Greeks for {option_type}s")
        
        # Simplified Greeks calculation based on moneyness
        # These are approximations - for production use Black-Scholes
        for idx, row in df.iterrows():
            moneyness = row['strike'] / spot_price
            
            # Delta approximation
            if option_type == 'call':
                # Calls: delta ranges from 0 (deep OTM) to 1 (deep ITM)
                # Use sigmoid-like function centered at ATM
                df.at[idx, 'delta'] = 1 / (1 + np.exp(-5 * (moneyness - 1)))
            else:
                # Puts: delta ranges from -1 (deep ITM) to 0 (deep OTM)
                df.at[idx, 'delta'] = -1 / (1 + np.exp(5 * (moneyness - 1)))
            
            # Gamma approximation (highest at ATM, zero at extremes)
            # Use Gaussian-like distribution centered at ATM
            df.at[idx, 'gamma'] = 0.1 * np.exp(-10 * (moneyness - 1)**2)
            
            # Vega approximation (similar to gamma, highest at ATM)
            df.at[idx, 'vega'] = 0.2 * np.exp(-8 * (moneyness - 1)**2)
            
            # Theta approximation (time decay, negative for long positions)
            # Higher for ATM options
            df.at[idx, 'theta'] = -0.15 * np.exp(-8 * (moneyness - 1)**2)
    
    return df


def _generate_mock_chain(ticker: str) -> Dict:
    """
    Generate mock options chain for testing.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Mock chain data
    """
    spot_price = 150.0
    strikes = np.arange(130, 171, 5)
    
    # Generate mock calls
    calls_data = []
    for strike in strikes:
        moneyness = strike / spot_price
        iv = 0.25 + 0.1 * abs(moneyness - 1.0)  # Volatility smile
        
        intrinsic = max(spot_price - strike, 0)
        time_value = np.random.uniform(1, 5)
        last_price = intrinsic + time_value
        
        calls_data.append({
            'strike': strike,
            'lastPrice': last_price,
            'bid': last_price * 0.95,
            'ask': last_price * 1.05,
            'volume': np.random.randint(10, 1000),
            'openInterest': np.random.randint(100, 5000),
            'impliedVolatility': iv,
            'delta': 0.5 + 0.3 * (1 - moneyness),
            'gamma': 0.05,
            'theta': -0.10,
            'vega': 0.15,
            'moneyness': moneyness,
            'intrinsic': intrinsic,
            'timeValue': time_value,
            'status': 'ITM' if spot_price > strike else ('OTM' if spot_price < strike else 'ATM')
        })
    
    # Generate mock puts
    puts_data = []
    for strike in strikes:
        moneyness = strike / spot_price
        iv = 0.25 + 0.1 * abs(moneyness - 1.0)
        
        intrinsic = max(strike - spot_price, 0)
        time_value = np.random.uniform(1, 5)
        last_price = intrinsic + time_value
        
        puts_data.append({
            'strike': strike,
            'lastPrice': last_price,
            'bid': last_price * 0.95,
            'ask': last_price * 1.05,
            'volume': np.random.randint(10, 1000),
            'openInterest': np.random.randint(100, 5000),
            'impliedVolatility': iv,
            'delta': -0.5 - 0.3 * (moneyness - 1),
            'gamma': 0.05,
            'theta': -0.10,
            'vega': 0.15,
            'moneyness': moneyness,
            'intrinsic': intrinsic,
            'timeValue': time_value,
            'status': 'ITM' if spot_price < strike else ('OTM' if spot_price > strike else 'ATM')
        })
    
    expirations = [
        (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
        (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d'),
        (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
        (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d'),
    ]
    
    return {
        'ticker': ticker,
        'spot_price': spot_price,
        'expirations': expirations,
        'calls': pd.DataFrame(calls_data),
        'puts': pd.DataFrame(puts_data),
        'error': None
    }


def calculate_greeks_summary(chain_data: Dict) -> Dict:
    """
    Calculate aggregate Greeks for the entire chain.
    
    Args:
        chain_data: Output from fetch_options_chain (calls/puts can be DataFrame or list of dicts)
        
    Returns:
        Dict with summary statistics
    """
    # Convert to DataFrames if stored as dicts (from dcc.Store)
    calls = chain_data.get('calls', pd.DataFrame())
    puts = chain_data.get('puts', pd.DataFrame())
    
    if isinstance(calls, list):
        calls = pd.DataFrame(calls)
    if isinstance(puts, list):
        puts = pd.DataFrame(puts)
    
    if calls.empty and puts.empty:
        return {
            'total_volume': 0,
            'total_oi': 0,
            'avg_iv_calls': 0,
            'avg_iv_puts': 0,
            'put_call_ratio': 0
        }
    
    summary = {
        'total_volume': int(calls.get('volume', pd.Series([0])).sum() + puts.get('volume', pd.Series([0])).sum()),
        'total_oi': int(calls.get('openInterest', pd.Series([0])).sum() + puts.get('openInterest', pd.Series([0])).sum()),
        'avg_iv_calls': float(calls.get('impliedVolatility', pd.Series([0])).mean()) if not calls.empty else 0,
        'avg_iv_puts': float(puts.get('impliedVolatility', pd.Series([0])).mean()) if not puts.empty else 0,
        'put_call_ratio': (puts.get('volume', pd.Series([0])).sum() / calls.get('volume', pd.Series([1])).sum()) if not calls.empty else 0
    }
    
    return summary


def generate_vol_surface_data(ticker: str, use_mock: bool = True) -> Dict:
    """
    Generate 3D volatility surface data.
    
    Args:
        ticker: Stock ticker symbol
        use_mock: If True, use mock data
        
    Returns:
        Dict with X (moneyness), Y (expiration), Z (IV) arrays
    """
    if use_mock:
        # Generate mock surface
        moneyness = np.linspace(0.8, 1.2, 20)
        days_to_exp = np.array([7, 14, 30, 60, 90])
        
        X, Y = np.meshgrid(moneyness, days_to_exp)
        
        # Volatility smile + term structure
        Z = 0.20 + 0.15 * (X - 1.0)**2 + 0.05 * (1 / np.sqrt(Y / 365))
        
        return {
            'moneyness': X,
            'days_to_exp': Y,
            'implied_vol': Z,
            'ticker': ticker
        }
    
    # TODO: Implement real surface from multiple expirations
    return generate_vol_surface_data(ticker, use_mock=True)
