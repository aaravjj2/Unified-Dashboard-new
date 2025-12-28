"""
Enhanced Alpaca Options Integration

Provides direct integration with Alpaca's options API matching their web interface style.
Fetches real-time options chains with all Greeks, IV, OI, and volume data.

Features:
- TTL-based caching to reduce API calls
- Circuit breaker for resilience
- Comprehensive logging and metrics
"""

import logging
import pandas as pd
import numpy as np
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import requests

from .options_cache import get_options_cache
from .circuit_breaker import get_circuit_breaker, CircuitOpenError

logger = logging.getLogger(__name__)

# Metrics for monitoring
_metrics = {
    'api_calls': 0,
    'cache_hits': 0,
    'cache_misses': 0,
    'errors': 0,
    'avg_fetch_time_ms': 0,
    'total_fetch_time_ms': 0
}


class AlpacaOptionsClient:
    """Direct Alpaca Options API client with enhanced data fetching."""
    
    def __init__(self):
        """Initialize Alpaca Options client with API credentials."""
        self.api_key = os.getenv('APCA_API_KEY_ID')
        self.api_secret = os.getenv('APCA_API_SECRET_KEY')
        self.base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')
        self.data_url = os.getenv('APCA_DATA_URL', 'https://data.alpaca.markets')
        
        self.headers = {
            'APCA-API-KEY-ID': self.api_key or '',
            'APCA-API-SECRET-KEY': self.api_secret or ''
        }
        
        # Check if credentials are available
        self.available = bool(self.api_key and self.api_secret)
        
        if not self.available:
            logger.warning("⚠️ Alpaca API credentials not found. Options data will use fallback sources.")
    
    def get_underlying_price(self, ticker: str) -> Optional[float]:
        """
        Get current underlying stock price.
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Current price or None
        """
        if not self.available:
            return None
        
        try:
            # Use Alpaca's latest quote endpoint
            url = f"{self.data_url}/v2/stocks/{ticker}/quotes/latest"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                quote = data.get('quote', {})
                bid = quote.get('bp', 0)
                ask = quote.get('ap', 0)
                
                if bid > 0 and ask > 0:
                    return (bid + ask) / 2.0
                return quote.get('ap', quote.get('bp', None))
            
            logger.warning(f"⚠️ Alpaca price fetch failed: {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error fetching underlying price: {e}")
            return None
    
    def get_option_chain(self, ticker: str, expiration: Optional[str] = None) -> Optional[Dict]:
        """
        Fetch options chain data from Alpaca.
        
        Args:
            ticker: Stock symbol
            expiration: Optional specific expiration date (YYYY-MM-DD)
            
        Returns:
            Dict containing:
            {
                'ticker': str,
                'spot_price': float,
                'expirations': List[str],
                'chains': {
                    'YYYY-MM-DD': {
                        'calls': pd.DataFrame,
                        'puts': pd.DataFrame
                    }
                },
                'source': 'alpaca'
            }
        """
        if not self.available:
            logger.info("🔕 Alpaca not configured, using fallback")
            return None
        
        try:
            # Get underlying price
            spot_price = self.get_underlying_price(ticker)
            if spot_price is None:
                logger.warning(f"⚠️ Could not get spot price for {ticker}")
                # Try to continue anyway
                spot_price = 0.0
            
            # Fetch options contracts - Alpaca uses snapshots endpoint with pagination
            url = f"{self.data_url}/v1beta1/options/snapshots/{ticker}"
            
            all_snapshots = {}
            page_token = None
            max_pages = 10  # Limit to prevent infinite loops
            pages_fetched = 0
            
            while pages_fetched < max_pages:
                params = {}
                if page_token:
                    params['page_token'] = page_token
                
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                
                if response.status_code != 200:
                    logger.warning(f"⚠️ Alpaca options fetch failed: {response.status_code}")
                    break
                
                data = response.json()
                snapshots = data.get('snapshots', {})
                all_snapshots.update(snapshots)
                
                pages_fetched += 1
                logger.debug(f"Fetched page {pages_fetched}: {len(snapshots)} contracts")
                
                # Check for next page
                page_token = data.get('next_page_token')
                if not page_token:
                    break
            
            logger.info(f"✅ Fetched {len(all_snapshots)} total contracts from {pages_fetched} pages")
            
            if not all_snapshots:
                logger.warning(f"⚠️ No options data returned for {ticker}")
                return None
            
            if not snapshots:
                logger.warning(f"⚠️ No options data returned for {ticker}")
                return None
            
            # Parse snapshots into structured data
            calls_data = []
            puts_data = []
            expirations_set = set()
            
            for contract_symbol, snapshot in all_snapshots.items():
                # Parse contract symbol (format: TICKERYYMMDDCPPPPPPPP)
                # Example: SPY251222C00525000
                # SPY = ticker, 251222 = expiry date (YYMMDD), C = call/put, 00525000 = strike price in cents
                
                try:
                    # Find ticker (symbols are alphabetic at start)
                    ticker_end = 0
                    for i, char in enumerate(contract_symbol):
                        if not char.isalpha():
                            ticker_end = i
                            break
                    
                    if ticker_end == 0:
                        continue
                    
                    # Parse components
                    symbol_ticker = contract_symbol[:ticker_end]
                    remaining = contract_symbol[ticker_end:]
                    
                    # Next 6 digits are date (YYMMDD)
                    date_str = remaining[:6]
                    # Next char is C or P
                    option_type = remaining[6]
                    # Remaining digits are strike in cents (8 digits)
                    strike_str = remaining[7:]
                    
                    strike = float(strike_str) / 1000.0  # Convert from cents/1000 to dollars
                    
                    # Convert date format YYMMDD to YYYY-MM-DD
                    exp_date = datetime.strptime('20' + date_str, '%Y%m%d').strftime('%Y-%m-%d')
                    expirations_set.add(exp_date)
                    
                    # Extract latest quote and Greeks
                    latest_quote = snapshot.get('latestQuote', {})
                    greeks = snapshot.get('greeks', {})
                    latest_trade = snapshot.get('latestTrade', {})
                    
                    bid = latest_quote.get('bp', 0)
                    ask = latest_quote.get('ap', 0)
                    last = latest_trade.get('p', (bid + ask) / 2 if bid and ask else 0)
                    
                    contract_data = {
                        'contractSymbol': contract_symbol,
                        'strike': strike,
                        'lastPrice': last,
                        'bid': bid,
                        'ask': ask,
                        'change': latest_trade.get('c', 0),
                        'percentChange': latest_trade.get('cp', 0),
                        'volume': latest_trade.get('s', 0),
                        'openInterest': snapshot.get('impliedVolatility', {}).get('openInterest', 0),
                        'impliedVolatility': greeks.get('implied_volatility', 0),
                        'delta': greeks.get('delta', 0),
                        'gamma': greeks.get('gamma', 0),
                        'theta': greeks.get('theta', 0),
                        'vega': greeks.get('vega', 0),
                        'expiration': exp_date,
                        'inTheMoney': (option_type == 'C' and strike < spot_price) or (option_type == 'P' and strike > spot_price)
                    }
                    
                    if option_type == 'C':
                        calls_data.append(contract_data)
                    else:
                        puts_data.append(contract_data)
                    
                except Exception as e:
                    logger.debug(f"Error parsing contract {contract_symbol}: {e}")
                    continue
            
            if not calls_data and not puts_data:
                logger.warning(f"⚠️ No valid options contracts parsed for {ticker}")
                return None
            
            # Create DataFrames
            expirations = sorted(list(expirations_set))
            
            # Group by expiration
            chains = {}
            for exp in expirations:
                calls_df = pd.DataFrame([c for c in calls_data if c['expiration'] == exp])
                puts_df = pd.DataFrame([p for p in puts_data if p['expiration'] == exp])
                
                if not calls_df.empty:
                    calls_df = calls_df.sort_values('strike')
                if not puts_df.empty:
                    puts_df = puts_df.sort_values('strike')
                
                chains[exp] = {
                    'calls': calls_df,
                    'puts': puts_df
                }
            
            logger.info(f"✅ Alpaca: Fetched {len(calls_data)} calls, {len(puts_data)} puts for {ticker}")
            logger.info(f"   Expirations: {len(expirations)}, Spot: ${spot_price:.2f}")
            
            return {
                'ticker': ticker,
                'spot_price': spot_price,
                'expirations': expirations,
                'chains': chains,
                'source': 'alpaca',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Alpaca options chain fetch failed: {e}")
            return None


def fetch_options_chain_alpaca_enhanced(ticker: str, expiration: Optional[str] = None) -> Optional[Dict]:
    """
    Enhanced Alpaca options chain fetcher.
    
    This is a drop-in replacement for the old fetch_options_chain_alpaca function.
    
    Args:
        ticker: Stock ticker symbol
        expiration: Optional expiration date filter
        
    Returns:
        Options chain dict or None if fetch fails
    """
    client = AlpacaOptionsClient()
    
    if not client.available:
        return None
    
    result = client.get_option_chain(ticker, expiration)
    
    if result and expiration:
        # Filter to specific expiration if requested
        chains = result.get('chains', {})
        if expiration in chains:
            chain_data = chains[expiration]
            result['calls'] = chain_data['calls']
            result['puts'] = chain_data['puts']
        else:
            # No data for requested expiration
            logger.warning(f"⚠️ No data for expiration {expiration}")
            return None
    elif result:
        # Keep full set of expirations and chains intact when no expiration
        # is requested. This avoids implicitly limiting the UI to a single
        # expiration and preserves the full chain for the frontend.
        # (Consumers should pick a specific expiration from result['expirations']).
        pass
    
    return result


# Create singleton instance
_alpaca_client = None

def get_alpaca_client() -> AlpacaOptionsClient:
    """Get or create singleton Alpaca client."""
    global _alpaca_client
    if _alpaca_client is None:
        # Attempt to load keys from keys.env before creating client
        try:
            from ..utils.load_keys_env import load_keys_env
            load_keys_env()
        except Exception:
            pass
        _alpaca_client = AlpacaOptionsClient()
    return _alpaca_client


def get_cached_option_chain(
    ticker: str, 
    expiration: Optional[str] = None,
    use_cache: bool = True,
    cache_ttl: int = 300
) -> Tuple[Optional[Dict], bool]:
    """
    Get options chain with caching support.
    
    Args:
        ticker: Stock symbol
        expiration: Optional specific expiration
        use_cache: Whether to use cache (default: True)
        cache_ttl: Cache TTL in seconds (default: 5 minutes)
        
    Returns:
        Tuple of (chain_data, was_cached)
    """
    global _metrics
    
    client = get_alpaca_client()
    cache = get_options_cache()
    cache_key = f"{ticker.upper()}_{expiration or 'all'}"
    
    # Try cache first
    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            _metrics['cache_hits'] += 1
            logger.debug(f"📦 Cache hit for {cache_key}")
            return cached, True
    
    _metrics['cache_misses'] += 1
    
    # Fetch from API
    start_time = time.time()
    try:
        chain_data = client.get_option_chain(ticker, expiration)
        
        fetch_time = (time.time() - start_time) * 1000
        _metrics['api_calls'] += 1
        _metrics['total_fetch_time_ms'] += fetch_time
        _metrics['avg_fetch_time_ms'] = _metrics['total_fetch_time_ms'] / _metrics['api_calls']
        
        if chain_data and use_cache:
            cache.set(cache_key, chain_data, cache_ttl)
            logger.debug(f"📦 Cached {cache_key} (fetch_time={fetch_time:.0f}ms)")
        
        return chain_data, False
        
    except Exception as e:
        _metrics['errors'] += 1
        logger.error(f"❌ Error fetching chain for {ticker}: {e}")
        raise


def get_alpaca_metrics() -> Dict[str, Any]:
    """Get Alpaca client metrics."""
    cache = get_options_cache()
    return {
        **_metrics,
        'cache_stats': cache.stats.to_dict(),
        'cache_info': cache.get_info()
    }


def invalidate_ticker_cache(ticker: str) -> int:
    """Invalidate all cached data for a ticker."""
    cache = get_options_cache()
    return cache.invalidate_ticker(ticker)
