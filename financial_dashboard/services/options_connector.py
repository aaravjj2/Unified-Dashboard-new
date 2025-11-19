"""
Options Data Connector
Provides options chain data with fallback chain: yfinance → Alpaca (future) → mock

Features:
- Real-time options data (strike, bid, ask, IV, volume, OI)
- Multiple expiration dates
- Caching for performance
- Graceful fallback to mock data if all sources fail

Author: Phase 0.9B - Volatility Lab Full Implementation
"""
import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import yfinance as yf
from functools import lru_cache

logger = logging.getLogger(__name__)

# In-memory cache for options data (TTL: 5 minutes)
_OPTIONS_CACHE: Dict[str, Tuple[datetime, pd.DataFrame, pd.DataFrame]] = {}
_CACHE_TTL_SECONDS = 300


class OptionsConnector:
    """
    Fetches options chain data with intelligent fallback.
    
    Data Sources:
    1. yfinance (primary, free, reliable)
    2. Alpaca Data API (future, requires paid subscription)
    3. Mock generator (fallback for testing/offline)
    """
    
    def __init__(self):
        self.source_priority = ['yfinance', 'alpaca', 'mock']
        self.last_source_used = None
    
    def get_options_chain(
        self,
        symbol: str,
        expiration_date: Optional[str] = None,
        use_cache: bool = True
    ) -> Tuple[pd.DataFrame, pd.DataFrame, str]:
        """
        Fetch options chain (calls + puts) for a symbol.
        
        Args:
            symbol: Stock ticker (e.g., 'SPY')
            expiration_date: Specific expiration (YYYY-MM-DD) or None for nearest
            use_cache: Whether to use cached data
            
        Returns:
            Tuple of (calls_df, puts_df, data_source)
            
        Example:
            >>> connector = OptionsConnector()
            >>> calls, puts, source = connector.get_options_chain('SPY')
            >>> print(f"Got {len(calls)} calls from {source}")
        """
        cache_key = f"{symbol}_{expiration_date}"
        
        # Check cache
        if use_cache and cache_key in _OPTIONS_CACHE:
            cached_time, calls, puts = _OPTIONS_CACHE[cache_key]
            age_seconds = (datetime.now() - cached_time).total_seconds()
            
            if age_seconds < _CACHE_TTL_SECONDS:
                logger.info(f"✅ Using cached options data for {symbol} (age: {age_seconds:.0f}s)")
                return calls.copy(), puts.copy(), f"{self.last_source_used}_cached"
        
        # Try each source in priority order
        for source in self.source_priority:
            try:
                if source == 'yfinance':
                    calls, puts = self._fetch_from_yfinance(symbol, expiration_date)
                elif source == 'alpaca':
                    calls, puts = self._fetch_from_alpaca(symbol, expiration_date)
                elif source == 'mock':
                    calls, puts = self._generate_mock_chain(symbol, expiration_date)
                else:
                    continue
                
                # Validate data
                if calls.empty or puts.empty:
                    logger.warning(f"❌ {source} returned empty data for {symbol}")
                    continue
                
                # Cache successful result
                _OPTIONS_CACHE[cache_key] = (datetime.now(), calls, puts)
                self.last_source_used = source
                
                logger.info(f"✅ Fetched {len(calls)} calls, {len(puts)} puts from {source}")
                return calls, puts, source
                
            except Exception as e:
                logger.warning(f"❌ {source} failed for {symbol}: {e}")
                continue
        
        # All sources failed - raise error
        raise ValueError(f"Failed to fetch options data for {symbol} from all sources")
    
    def get_available_expirations(self, symbol: str) -> List[str]:
        """
        Get list of available expiration dates for a symbol.
        
        Args:
            symbol: Stock ticker
            
        Returns:
            List of expiration dates (YYYY-MM-DD format)
        """
        try:
            ticker = yf.Ticker(symbol)
            expirations = ticker.options
            logger.info(f"✅ Found {len(expirations)} expirations for {symbol}")
            return list(expirations)
        except Exception as e:
            logger.error(f"❌ Failed to get expirations for {symbol}: {e}")
            return []
    
    def _fetch_from_yfinance(
        self,
        symbol: str,
        expiration_date: Optional[str] = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Fetch options from yfinance.
        
        Returns:
            Tuple of (calls_df, puts_df)
        """
        ticker = yf.Ticker(symbol)
        expirations = ticker.options
        
        if not expirations:
            raise ValueError(f"No options available for {symbol}")
        
        # Use specified expiration or nearest
        target_exp = expiration_date if expiration_date else expirations[0]
        
        if target_exp not in expirations:
            logger.warning(f"Expiration {target_exp} not available, using {expirations[0]}")
            target_exp = expirations[0]
        
        # Fetch options chain
        opt_chain = ticker.option_chain(target_exp)
        calls = opt_chain.calls
        puts = opt_chain.puts
        
        # Add metadata
        calls['expiration_date'] = target_exp
        calls['underlying_symbol'] = symbol
        puts['expiration_date'] = target_exp
        puts['underlying_symbol'] = symbol
        
        # Standardize column names
        calls = self._standardize_columns(calls, 'call')
        puts = self._standardize_columns(puts, 'put')
        
        return calls, puts
    
    def _fetch_from_alpaca(
        self,
        symbol: str,
        expiration_date: Optional[str] = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Fetch options from Alpaca Data API (requires paid subscription).
        
        NOTE: Not implemented yet - requires Alpaca Market Data subscription.
        Raises NotImplementedError to trigger fallback to next source.
        """
        raise NotImplementedError("Alpaca options data requires paid subscription")
    
    def _generate_mock_chain(
        self,
        symbol: str,
        expiration_date: Optional[str] = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Generate realistic mock options chain for testing/offline mode.
        
        Creates options around current price with realistic bid/ask spreads and IV.
        """
        logger.warning(f"⚠️ Using MOCK options data for {symbol} (all real sources failed)")
        
        # Get current price (or use default)
        try:
            ticker = yf.Ticker(symbol)
            price = ticker.history(period='1d')['Close'].iloc[-1]
        except:
            price = 450.0  # Default for SPY
        
        # Generate expiration (30 days out if not specified)
        if not expiration_date:
            exp_dt = datetime.now() + timedelta(days=30)
            expiration_date = exp_dt.strftime('%Y-%m-%d')
        
        # Generate strike prices around current price
        strikes = []
        for pct in range(-20, 21, 2):  # -20% to +20% in 2% increments
            strikes.append(round(price * (1 + pct / 100), 2))
        
        calls_data = []
        puts_data = []
        
        for strike in strikes:
            # Calculate moneyness
            moneyness = (strike - price) / price
            
            # Realistic IV (higher for OTM)
            base_iv = 0.20  # 20% base IV
            iv = base_iv + abs(moneyness) * 0.5  # IV smile
            
            # Call option
            if moneyness < -0.05:  # ITM call
                call_price = price - strike + 5.0
                call_bid = call_price - 0.50
                call_ask = call_price + 0.50
            elif moneyness > 0.05:  # OTM call
                call_price = max(0.10, 10.0 * np.exp(-moneyness * 5))
                call_bid = call_price * 0.95
                call_ask = call_price * 1.05
            else:  # ATM call
                call_price = 10.0
                call_bid = 9.50
                call_ask = 10.50
            
            calls_data.append({
                'contractSymbol': f'{symbol}{expiration_date.replace("-", "")}C{int(strike * 1000):08d}',
                'strike': strike,
                'lastPrice': round(call_price, 2),
                'bid': round(call_bid, 2),
                'ask': round(call_ask, 2),
                'impliedVolatility': round(iv, 4),
                'volume': int(np.random.randint(10, 1000)),
                'openInterest': int(np.random.randint(100, 5000)),
                'expiration_date': expiration_date,
                'underlying_symbol': symbol,
                'option_type': 'call'
            })
            
            # Put option (mirror logic)
            if moneyness > 0.05:  # ITM put
                put_price = strike - price + 5.0
                put_bid = put_price - 0.50
                put_ask = put_price + 0.50
            elif moneyness < -0.05:  # OTM put
                put_price = max(0.10, 10.0 * np.exp(moneyness * 5))
                put_bid = put_price * 0.95
                put_ask = put_price * 1.05
            else:  # ATM put
                put_price = 10.0
                put_bid = 9.50
                put_ask = 10.50
            
            puts_data.append({
                'contractSymbol': f'{symbol}{expiration_date.replace("-", "")}P{int(strike * 1000):08d}',
                'strike': strike,
                'lastPrice': round(put_price, 2),
                'bid': round(put_bid, 2),
                'ask': round(put_ask, 2),
                'impliedVolatility': round(iv, 4),
                'volume': int(np.random.randint(10, 1000)),
                'openInterest': int(np.random.randint(100, 5000)),
                'expiration_date': expiration_date,
                'underlying_symbol': symbol,
                'option_type': 'put'
            })
        
        calls_df = pd.DataFrame(calls_data)
        puts_df = pd.DataFrame(puts_data)
        
        return calls_df, puts_df
    
    def _standardize_columns(self, df: pd.DataFrame, option_type: str) -> pd.DataFrame:
        """
        Standardize column names across different data sources.
        """
        df = df.copy()
        df['option_type'] = option_type
        
        # Ensure required columns exist
        required_cols = ['strike', 'lastPrice', 'bid', 'ask', 'impliedVolatility', 
                         'volume', 'openInterest', 'expiration_date', 'underlying_symbol']
        
        for col in required_cols:
            if col not in df.columns:
                df[col] = None
        
        return df


# Convenience function for quick access
def get_options_chain(
    symbol: str,
    expiration_date: Optional[str] = None,
    use_cache: bool = True
) -> Tuple[pd.DataFrame, pd.DataFrame, str]:
    """
    Quick access function to fetch options chain.
    
    Args:
        symbol: Stock ticker
        expiration_date: Optional specific expiration date
        use_cache: Whether to use cached data (default True)
        
    Returns:
        Tuple of (calls_df, puts_df, data_source)
    
    Example:
        >>> calls, puts, source = get_options_chain('SPY')
        >>> print(f"Source: {source}, Calls: {len(calls)}")
    """
    connector = OptionsConnector()
    return connector.get_options_chain(symbol, expiration_date, use_cache)
