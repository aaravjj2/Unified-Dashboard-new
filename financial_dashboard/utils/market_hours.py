"""
Market hours checker and data caching utilities
Prevents P/L from changing when market is closed
"""

import os
import logging
from datetime import datetime, time
import pytz
import json

logger = logging.getLogger(__name__)

# US market hours (NYSE/NASDAQ)
MARKET_OPEN_TIME = time(9, 30)  # 9:30 AM ET
MARKET_CLOSE_TIME = time(16, 0)  # 4:00 PM ET
MARKET_TIMEZONE = pytz.timezone('America/New_York')

# Cache file for after-hours data
CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.cache', 'portfolio_cache.json')


def is_market_open():
    """
    Check if US stock market is currently open.
    
    Returns:
        bool: True if market is open, False otherwise
    """
    try:
        # Get current time in ET
        now_et = datetime.now(MARKET_TIMEZONE)
        
        # Check if weekend
        if now_et.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Check if within trading hours
        current_time = now_et.time()
        if MARKET_OPEN_TIME <= current_time <= MARKET_CLOSE_TIME:
            return True
        
        return False
    
    except Exception as e:
        logger.error(f"Error checking market hours: {e}")
        # Default to True to allow live updates if check fails
        return True


def cache_portfolio_data(portfolio_data):
    """
    Cache portfolio data to file for use when market is closed.
    
    Args:
        portfolio_data: Dictionary containing portfolio information
    """
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        
        cache_entry = {
            'timestamp': datetime.now().isoformat(),
            'data': portfolio_data
        }
        
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_entry, f, indent=2)
        
        logger.debug(f"Cached portfolio data at {cache_entry['timestamp']}")
    
    except Exception as e:
        logger.error(f"Error caching portfolio data: {e}")


def get_cached_portfolio_data():
    """
    Retrieve cached portfolio data from file.
    
    Returns:
        dict: Cached portfolio data or None if not available
    """
    try:
        if not os.path.exists(CACHE_FILE):
            return None
        
        with open(CACHE_FILE, 'r') as f:
            cache_entry = json.load(f)
        
        # Check cache age (don't use if older than 24 hours)
        cache_time = datetime.fromisoformat(cache_entry['timestamp'])
        age_hours = (datetime.now() - cache_time).total_seconds() / 3600
        
        if age_hours > 24:
            logger.warning(f"Cache is {age_hours:.1f} hours old - may be stale")
            return None
        
        logger.debug(f"Using cached portfolio data from {cache_entry['timestamp']}")
        return cache_entry['data']
    
    except Exception as e:
        logger.error(f"Error loading cached portfolio data: {e}")
        return None


def get_portfolio_data_smart(live_fetcher_func):
    """
    Smart wrapper that returns live data when market is open,
    cached data when market is closed.
    
    Args:
        live_fetcher_func: Function that fetches live portfolio data
    
    Returns:
        dict: Portfolio data (live or cached)
    """
    market_is_open = is_market_open()
    
    if market_is_open:
        # Market is open - fetch live data
        logger.info("Market is OPEN - fetching live data")
        try:
            live_data = live_fetcher_func()
            # Cache the live data for after-hours use
            if live_data:
                cache_portfolio_data(live_data)
            return live_data
        except Exception as e:
            logger.error(f"Error fetching live data: {e}")
            # Fallback to cache if live fetch fails
            cached = get_cached_portfolio_data()
            if cached:
                logger.warning("Live fetch failed, using cached data")
                return cached
            raise
    else:
        # Market is closed - use cached data
        logger.info("Market is CLOSED - using cached data")
        cached = get_cached_portfolio_data()
        
        if cached:
            # Add indicator that this is cached data
            if isinstance(cached, dict):
                cached['_cached'] = True
                cached['_cache_note'] = 'Market closed - showing last trading day data'
            return cached
        else:
            # No cache available - fetch live anyway (for initialization)
            logger.warning("No cache available, fetching live data despite market being closed")
            live_data = live_fetcher_func()
            if live_data:
                cache_portfolio_data(live_data)
            return live_data


if __name__ == '__main__':
    # Test the module
    logging.basicConfig(level=logging.INFO)
    
    print(f"Current time: {datetime.now()}")
    print(f"Market is open: {is_market_open()}")
    
    # Test caching
    test_data = {
        'account': {'portfolio_value': 100000, 'cash': 5000},
        'positions': [{'symbol': 'AAPL', 'qty': 10}]
    }
    
    print("\nTesting cache...")
    cache_portfolio_data(test_data)
    
    cached = get_cached_portfolio_data()
    print(f"Retrieved from cache: {cached is not None}")
    
    if cached:
        print(f"Cached timestamp: {cached.get('timestamp', 'N/A')}")
