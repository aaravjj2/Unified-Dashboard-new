"""
Alpaca-Only Options Data Loader
================================
Pure Alpaca implementation for options chain data.
Falls back to mock data only if Alpaca is unavailable.

Uses Alpaca Market Data API v2 for:
- Real-time and historical options data
- Stock quotes for spot price
- Options chain by expiration
"""

import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests

logger = logging.getLogger(__name__)

# Load keys from environment
ALPACA_KEY = os.getenv('APCA_API_KEY_ID')
ALPACA_SECRET = os.getenv('APCA_API_SECRET_KEY')
ALPACA_DATA_URL = "https://data.alpaca.markets"
ALPACA_PAPER_URL = os.getenv('APCA_ENDPOINT', 'https://paper-api.alpaca.markets')


class AlpacaOptionsClient:
    """
    Direct REST API client for Alpaca Options Data.
    Uses v1beta1 options endpoints.
    """
    
    def __init__(self, api_key: str = None, secret_key: str = None):
        self.api_key = api_key or ALPACA_KEY
        self.secret_key = secret_key or ALPACA_SECRET
        self.base_url = "https://data.alpaca.markets/v1beta1/options"
        self.stock_url = "https://data.alpaca.markets/v2/stocks"
        self.headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key
        }
        
    def is_configured(self) -> bool:
        """Check if API keys are configured."""
        return bool(self.api_key and self.secret_key)
    
    def get_stock_quote(self, symbol: str) -> Optional[float]:
        """Get latest stock quote for spot price."""
        if not self.is_configured():
            return None
            
        try:
            url = f"{self.stock_url}/{symbol}/quotes/latest"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                quote = data.get('quote', {})
                bid = quote.get('bp', 0) or quote.get('bid_price', 0)
                ask = quote.get('ap', 0) or quote.get('ask_price', 0)
                
                if bid and ask:
                    return (bid + ask) / 2
                    
                # Try alternate keys
                if 'p' in quote:  # trade price
                    return quote['p']
                    
            logger.warning(f"Alpaca quote response: {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get Alpaca quote for {symbol}: {e}")
            return None
    
    def get_options_chain(self, underlying: str, expiration_date: str = None) -> Dict:
        """
        Get options chain for underlying symbol.
        
        Args:
            underlying: Stock symbol (e.g., 'SPY')
            expiration_date: Optional specific expiration (YYYY-MM-DD)
            
        Returns:
            Dict with calls and puts DataFrames
        """
        if not self.is_configured():
            logger.warning("Alpaca not configured, returning empty chain")
            return {'calls': pd.DataFrame(), 'puts': pd.DataFrame(), 'expirations': []}
        
        try:
            # Build option symbols pattern - Alpaca uses OCC symbology
            # Format: SPY240119C00450000 (symbol + YYMMDD + C/P + strike*1000)
            
            # First, get available contracts
            params = {
                'underlying_symbols': underlying,
                'status': 'active',
                'limit': 1000
            }
            
            if expiration_date:
                params['expiration_date'] = expiration_date
            
            # Get option contracts
            url = f"{self.base_url}/contracts"
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"Alpaca contracts response: {response.status_code} - {response.text[:200]}")
                return {'calls': pd.DataFrame(), 'puts': pd.DataFrame(), 'expirations': []}
            
            data = response.json()
            contracts = data.get('option_contracts', []) or data.get('contracts', [])
            
            if not contracts:
                logger.info(f"No options contracts found for {underlying}")
                return {'calls': pd.DataFrame(), 'puts': pd.DataFrame(), 'expirations': []}
            
            # Parse contracts into calls and puts
            calls_data = []
            puts_data = []
            expirations = set()
            
            for contract in contracts:
                exp_date = contract.get('expiration_date', '')
                expirations.add(exp_date)
                
                option_type = contract.get('type', '').lower()
                strike = float(contract.get('strike_price', 0))
                symbol = contract.get('symbol', '')
                
                # Get quote for this contract
                quote = self._get_option_quote(symbol)
                
                contract_data = {
                    'contractSymbol': symbol,
                    'strike': strike,
                    'expiration': exp_date,
                    'lastPrice': quote.get('last', 0),
                    'bid': quote.get('bid', 0),
                    'ask': quote.get('ask', 0),
                    'volume': quote.get('volume', 0),
                    'openInterest': contract.get('open_interest', 0),
                    'impliedVolatility': quote.get('iv', 0.25),
                }
                
                if option_type == 'call':
                    calls_data.append(contract_data)
                else:
                    puts_data.append(contract_data)
            
            calls_df = pd.DataFrame(calls_data) if calls_data else pd.DataFrame()
            puts_df = pd.DataFrame(puts_data) if puts_data else pd.DataFrame()
            
            return {
                'calls': calls_df,
                'puts': puts_df,
                'expirations': sorted(list(expirations))
            }
            
        except Exception as e:
            logger.error(f"Alpaca options chain failed: {e}")
            return {'calls': pd.DataFrame(), 'puts': pd.DataFrame(), 'expirations': []}
    
    def _get_option_quote(self, symbol: str) -> Dict:
        """Get latest quote for an option contract."""
        try:
            url = f"{self.base_url}/quotes/latest"
            params = {'symbols': symbol}
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                quotes = data.get('quotes', {})
                if symbol in quotes:
                    q = quotes[symbol]
                    return {
                        'bid': q.get('bp', 0) or q.get('bid_price', 0),
                        'ask': q.get('ap', 0) or q.get('ask_price', 0),
                        'last': q.get('c', 0) or q.get('close', 0),
                        'volume': q.get('v', 0) or q.get('volume', 0),
                        'iv': q.get('iv', 0.25)
                    }
            return {'bid': 0, 'ask': 0, 'last': 0, 'volume': 0, 'iv': 0.25}
            
        except Exception:
            return {'bid': 0, 'ask': 0, 'last': 0, 'volume': 0, 'iv': 0.25}
    
    def get_snapshots(self, symbols: List[str]) -> Dict:
        """Get snapshots for multiple option symbols at once (more efficient)."""
        if not symbols or not self.is_configured():
            return {}
            
        try:
            url = f"{self.base_url}/snapshots"
            params = {'symbols': ','.join(symbols[:100])}  # API limit
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                return response.json().get('snapshots', {})
            return {}
            
        except Exception as e:
            logger.error(f"Alpaca snapshots failed: {e}")
            return {}


# Singleton client
_alpaca_client = None

def get_alpaca_client() -> AlpacaOptionsClient:
    """Get singleton Alpaca client."""
    global _alpaca_client
    if _alpaca_client is None:
        _alpaca_client = AlpacaOptionsClient()
    return _alpaca_client


def fetch_options_chain_alpaca_only(ticker: str, expiration: str = None) -> Dict:
    """
    Fetch options chain using Alpaca ONLY.
    Falls back to mock data if Alpaca unavailable.
    
    Args:
        ticker: Stock symbol
        expiration: Optional expiration date filter
        
    Returns:
        Options chain dict with source='alpaca' or 'mock'
    """
    client = get_alpaca_client()
    
    if not client.is_configured():
        logger.warning("Alpaca not configured - using mock data")
        return _generate_mock_chain(ticker)
    
    # Get spot price
    spot_price = client.get_stock_quote(ticker)
    if not spot_price:
        logger.warning(f"Could not get spot price for {ticker}, using estimate")
        spot_price = 150.0  # Default
    
    # Get options chain
    chain = client.get_options_chain(ticker, expiration)
    
    calls_df = chain.get('calls', pd.DataFrame())
    puts_df = chain.get('puts', pd.DataFrame())
    expirations = chain.get('expirations', [])
    
    # Check if we got real data
    if calls_df.empty and puts_df.empty:
        logger.info(f"Alpaca returned empty chain for {ticker}, using mock data")
        mock_data = _generate_mock_chain(ticker)
        mock_data['source'] = 'mock (alpaca empty)'
        return mock_data
    
    # Enrich with calculated fields
    if not calls_df.empty:
        calls_df = _enrich_chain_data(calls_df, spot_price, 'call')
    if not puts_df.empty:
        puts_df = _enrich_chain_data(puts_df, spot_price, 'put')
    
    logger.info(f"✅ Loaded {len(calls_df)} calls and {len(puts_df)} puts from Alpaca for {ticker}")
    
    return {
        'ticker': ticker,
        'spot_price': spot_price,
        'expirations': expirations,
        'calls': calls_df,
        'puts': puts_df,
        'error': None,
        'source': 'alpaca'
    }


def _enrich_chain_data(df: pd.DataFrame, spot_price: float, option_type: str) -> pd.DataFrame:
    """Add calculated fields to options chain."""
    if df.empty:
        return df
    
    df = df.copy()
    
    # Moneyness
    df['moneyness'] = df['strike'] / spot_price
    
    # Intrinsic value
    if option_type == 'call':
        df['intrinsic'] = np.maximum(spot_price - df['strike'], 0)
    else:
        df['intrinsic'] = np.maximum(df['strike'] - spot_price, 0)
    
    # Time value
    if 'lastPrice' in df.columns:
        df['timeValue'] = np.maximum(df['lastPrice'] - df['intrinsic'], 0)
    
    # Status (ITM/ATM/OTM)
    if option_type == 'call':
        df['status'] = np.where(spot_price > df['strike'], 'ITM',
                               np.where(spot_price < df['strike'], 'OTM', 'ATM'))
    else:
        df['status'] = np.where(spot_price < df['strike'], 'ITM',
                               np.where(spot_price > df['strike'], 'OTM', 'ATM'))
    
    # Calculate Greeks using Black-Scholes if not provided
    if 'delta' not in df.columns or df['delta'].isna().all():
        df = _calculate_greeks(df, spot_price, option_type)
    
    return df


def _calculate_greeks(df: pd.DataFrame, spot: float, option_type: str) -> pd.DataFrame:
    """Calculate Black-Scholes Greeks."""
    try:
        from scipy.stats import norm
        from math import log, sqrt, exp
        
        r = 0.05  # Risk-free rate
        
        for idx, row in df.iterrows():
            strike = row['strike']
            iv = row.get('impliedVolatility', 0.25) or 0.25
            
            # Calculate days to expiry
            exp_date = row.get('expiration', '')
            if exp_date:
                try:
                    exp_dt = datetime.strptime(str(exp_date)[:10], '%Y-%m-%d')
                    T = max((exp_dt - datetime.now()).days / 365.0, 0.001)
                except:
                    T = 30 / 365.0
            else:
                T = 30 / 365.0
            
            # Black-Scholes
            try:
                d1 = (log(spot / strike) + (r + 0.5 * iv**2) * T) / (iv * sqrt(T))
                d2 = d1 - iv * sqrt(T)
                
                if option_type == 'call':
                    delta = norm.cdf(d1)
                    theta = (-spot * norm.pdf(d1) * iv / (2 * sqrt(T)) 
                             - r * strike * exp(-r * T) * norm.cdf(d2)) / 365
                else:
                    delta = norm.cdf(d1) - 1
                    theta = (-spot * norm.pdf(d1) * iv / (2 * sqrt(T)) 
                             + r * strike * exp(-r * T) * norm.cdf(-d2)) / 365
                
                gamma = norm.pdf(d1) / (spot * iv * sqrt(T))
                vega = spot * norm.pdf(d1) * sqrt(T) / 100
                
                df.at[idx, 'delta'] = round(delta, 4)
                df.at[idx, 'gamma'] = round(gamma, 4)
                df.at[idx, 'theta'] = round(theta, 4)
                df.at[idx, 'vega'] = round(vega, 4)
                
            except Exception:
                df.at[idx, 'delta'] = 0.5 if option_type == 'call' else -0.5
                df.at[idx, 'gamma'] = 0.05
                df.at[idx, 'theta'] = -0.05
                df.at[idx, 'vega'] = 0.10
                
    except ImportError:
        # Fallback if scipy not available
        default_delta = 0.5 if option_type == 'call' else -0.5
        df['delta'] = default_delta
        df['gamma'] = 0.05
        df['theta'] = -0.05
        df['vega'] = 0.10
    
    return df


def _generate_mock_chain(ticker: str) -> Dict:
    """Generate mock options chain for testing."""
    spot_price = 150.0
    strikes = np.arange(130, 171, 5)
    
    expirations = [
        (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
        (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d'),
        (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
        (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d'),
    ]
    
    calls_data = []
    puts_data = []
    
    for expiry in expirations[:1]:  # Just first expiry for mock
        for strike in strikes:
            moneyness = strike / spot_price
            iv = 0.25 + 0.1 * abs(moneyness - 1.0)
            
            # Calls
            intrinsic_call = max(spot_price - strike, 0)
            time_value = np.random.uniform(1, 5)
            last_price = intrinsic_call + time_value
            
            calls_data.append({
                'contractSymbol': f'{ticker}{expiry.replace("-", "")}C{int(strike*1000):08d}',
                'strike': strike,
                'expiration': expiry,
                'lastPrice': last_price,
                'bid': last_price * 0.95,
                'ask': last_price * 1.05,
                'volume': np.random.randint(10, 1000),
                'openInterest': np.random.randint(100, 5000),
                'impliedVolatility': iv,
                'moneyness': moneyness,
                'intrinsic': intrinsic_call,
                'timeValue': time_value,
                'status': 'ITM' if spot_price > strike else 'OTM',
                'delta': 0.5 + 0.3 * (1 - moneyness),
                'gamma': 0.05,
                'theta': -0.10,
                'vega': 0.15,
            })
            
            # Puts
            intrinsic_put = max(strike - spot_price, 0)
            last_price_put = intrinsic_put + time_value
            
            puts_data.append({
                'contractSymbol': f'{ticker}{expiry.replace("-", "")}P{int(strike*1000):08d}',
                'strike': strike,
                'expiration': expiry,
                'lastPrice': last_price_put,
                'bid': last_price_put * 0.95,
                'ask': last_price_put * 1.05,
                'volume': np.random.randint(10, 1000),
                'openInterest': np.random.randint(100, 5000),
                'impliedVolatility': iv,
                'moneyness': moneyness,
                'intrinsic': intrinsic_put,
                'timeValue': time_value,
                'status': 'ITM' if spot_price < strike else 'OTM',
                'delta': -0.5 - 0.3 * (moneyness - 1),
                'gamma': 0.05,
                'theta': -0.10,
                'vega': 0.15,
            })
    
    return {
        'ticker': ticker,
        'spot_price': spot_price,
        'expirations': expirations,
        'calls': pd.DataFrame(calls_data),
        'puts': pd.DataFrame(puts_data),
        'error': None,
        'source': 'mock'
    }
