"""
Price Fetcher with yfinance Fallback

Handles fetching missing ticker prices using yfinance.

SUPER-AGENT FIX: Provides reliable fallback when cache is incomplete.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)


class PriceFetcher:
    """
    Fetches price data for tickers using yfinance.
    
    Provides methods to:
    - Fetch current price
    - Fetch historical prices (week/month start)
    - Calculate profit/loss and daily changes
    - Format data for cache storage
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._yf = None
    
    @property
    def yf(self):
        """Lazy import of yfinance"""
        if self._yf is None:
            try:
                import yfinance as yf
                self._yf = yf
                self.logger.info("[PRICE_FETCHER] yfinance imported successfully")
            except ImportError as e:
                self.logger.error(f"[PRICE_FETCHER] Cannot import yfinance: {e}")
                raise ImportError("yfinance is required for price fetching") from e
        return self._yf
    
    def fetch_ticker_prices(
        self, 
        ticker: str,
        period: str = '1mo'
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch complete price data for a ticker.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            period: Historical period to fetch (default '1mo')
            
        Returns:
            Dictionary with price fields or None if fetch fails:
            {
                'current_price': float,
                'daily_change': float,
                'week_start_price': float,
                'month_start_price': float,
                'profit_loss': float,
                'source': 'yfinance',
                'timestamp': float
            }
        """
        try:
            self.logger.info(f"[PRICE_FETCHER] Fetching {ticker} prices...")
            
            # Fetch ticker object
            stock = self.yf.Ticker(ticker)
            
            # Get historical data
            hist = stock.history(period=period)
            
            if hist.empty:
                self.logger.error(f"[PRICE_FETCHER] No historical data for {ticker}")
                return None
            
            # Get current price (most recent close)
            current_price = float(hist['Close'].iloc[-1])
            
            # Get previous day close for daily change
            if len(hist) >= 2:
                previous_close = float(hist['Close'].iloc[-2])
            else:
                previous_close = current_price
            
            # Get week start price (approximately 5 trading days ago)
            week_ago_idx = max(0, len(hist) - 6)
            week_start_price = float(hist['Close'].iloc[week_ago_idx])
            
            # Get month start price (first entry in history)
            month_start_price = float(hist['Close'].iloc[0])
            
            # Calculate metrics
            daily_change = current_price - previous_close
            profit_loss = current_price - month_start_price
            
            result = {
                'current_price': round(current_price, 2),
                'daily_change': round(daily_change, 2),
                'week_start_price': round(week_start_price, 2),
                'month_start_price': round(month_start_price, 2),
                'profit_loss': round(profit_loss, 2),
                'source': 'yfinance',
                'timestamp': time.time()
            }
            
            self.logger.info(
                f"✅ [PRICE_FETCHER] {ticker}: ${current_price:.2f} "
                f"(daily: {daily_change:+.2f}, P/L: {profit_loss:+.2f})"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ [PRICE_FETCHER] Failed to fetch {ticker}: {e}")
            return None
    
    def fetch_multiple_tickers(
        self,
        tickers: List[str],
        delay_seconds: float = 0.2
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetch price data for multiple tickers.
        
        Args:
            tickers: List of ticker symbols
            delay_seconds: Delay between requests to avoid rate limits
            
        Returns:
            Dictionary mapping ticker -> price data
            {
                'AAPL': {...price data...},
                'MSFT': {...price data...}
            }
        """
        results = {}
        
        self.logger.info(f"[PRICE_FETCHER] Fetching {len(tickers)} tickers...")
        
        for i, ticker in enumerate(tickers, 1):
            self.logger.info(f"[PRICE_FETCHER] [{i}/{len(tickers)}] Fetching {ticker}...")
            
            price_data = self.fetch_ticker_prices(ticker)
            
            if price_data is not None:
                results[ticker] = price_data
            
            # Rate limiting delay (except for last ticker)
            if i < len(tickers):
                time.sleep(delay_seconds)
        
        successful = len(results)
        failed = len(tickers) - successful
        
        self.logger.info(
            f"[PRICE_FETCHER] Fetch complete: {successful} successful, {failed} failed"
        )
        
        return results
    
    def update_cache_with_missing_tickers(
        self,
        cache_dict: Dict[str, Any],
        required_tickers: List[str]
    ) -> tuple[Dict[str, Any], List[str]]:
        """
        Update cache with missing tickers.
        
        Args:
            cache_dict: Current cache dictionary
            required_tickers: List of required ticker symbols
            
        Returns:
            (updated_cache, fetched_tickers)
        """
        prices = cache_dict.get('prices', {})
        
        # Find missing tickers
        missing_tickers = [t for t in required_tickers if t not in prices]
        
        if not missing_tickers:
            self.logger.info("[PRICE_FETCHER] No missing tickers to fetch")
            return cache_dict, []
        
        self.logger.info(f"[PRICE_FETCHER] Missing tickers: {', '.join(missing_tickers)}")
        
        # Fetch missing tickers
        fetched_data = self.fetch_multiple_tickers(missing_tickers)
        
        # Update cache
        prices.update(fetched_data)
        cache_dict['prices'] = prices
        
        return cache_dict, list(fetched_data.keys())


# Global instance
_price_fetcher: Optional[PriceFetcher] = None


def get_price_fetcher() -> PriceFetcher:
    """Get global PriceFetcher instance"""
    global _price_fetcher
    
    if _price_fetcher is None:
        _price_fetcher = PriceFetcher()
        logger.info("[PRICE_FETCHER] Initialized")
    
    return _price_fetcher


def fetch_ticker_prices(ticker: str) -> Optional[Dict[str, Any]]:
    """Convenience function to fetch ticker prices"""
    fetcher = get_price_fetcher()
    return fetcher.fetch_ticker_prices(ticker)


def fetch_multiple_tickers(tickers: List[str]) -> Dict[str, Dict[str, Any]]:
    """Convenience function to fetch multiple tickers"""
    fetcher = get_price_fetcher()
    return fetcher.fetch_multiple_tickers(tickers)


def update_cache_with_missing(
    cache_dict: Dict[str, Any],
    required_tickers: List[str]
) -> tuple[Dict[str, Any], List[str]]:
    """Convenience function to update cache with missing tickers"""
    fetcher = get_price_fetcher()
    return fetcher.update_cache_with_missing_tickers(cache_dict, required_tickers)
