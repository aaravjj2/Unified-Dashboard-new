"""
Alpaca Price Connector for Picks Pipeline (Optional)

Provides price snapshots from Alpaca Markets API (paper trading only).
"""

import os
import json
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import requests

ALPACA_ENABLED = os.environ.get('ALPACA_ENABLED', 'false').lower() == 'true'
ALPACA_API_KEY = os.environ.get('ALPACA_API_KEY', '')
ALPACA_SECRET = os.environ.get('ALPACA_SECRET', '')
ALPACA_BASE_URL = os.environ.get('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')

DIAGNOSTICS_DIR = Path(__file__).parent.parent.parent / 'reports' / 'picks' / 'diagnostics'
DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)


def is_alpaca_available() -> bool:
    """Check if Alpaca is configured and enabled."""
    return ALPACA_ENABLED and bool(ALPACA_API_KEY) and bool(ALPACA_SECRET)


def fetch_alpaca_prices(tickers: List[str]) -> Optional[Dict[str, Dict]]:
    """
    Fetch latest prices from Alpaca Markets API.
    
    Args:
        tickers: List of ticker symbols
        
    Returns:
        Dict mapping ticker -> price data, or None if Alpaca unavailable
    """
    if not is_alpaca_available():
        print("⚠️  Alpaca not available (ALPACA_ENABLED=false or missing keys)")
        return None
    
    prices_data = {}
    failed_tickers = []
    
    headers = {
        'APCA-API-KEY-ID': ALPACA_API_KEY,
        'APCA-API-SECRET-KEY': ALPACA_SECRET
    }
    
    # Use Alpaca's latest quotes endpoint
    try:
        # Batch request for all tickers
        symbols_str = ','.join(tickers)
        url = f'{ALPACA_BASE_URL}/v2/stocks/quotes/latest'
        params = {'symbols': symbols_str}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        quotes = data.get('quotes', {})
        
        for ticker in tickers:
            if ticker in quotes:
                quote = quotes[ticker]
                prices_data[ticker] = {
                    'last_price': quote.get('ap', quote.get('bp', 0)),  # Ask or bid
                    'bid': quote.get('bp', 0),
                    'ask': quote.get('ap', 0),
                    'bid_size': quote.get('bs', 0),
                    'ask_size': quote.get('as', 0),
                    'last_price_timestamp': quote.get('t', datetime.now().isoformat()),
                    'price_provenance': 'alpaca',
                    'fetched_at': datetime.now().isoformat()
                }
            else:
                failed_tickers.append(ticker)
        
    except Exception as e:
        print(f"Alpaca API error: {e}")
        return None
    
    # Save diagnostics
    timestamp = int(time.time())
    output_file = DIAGNOSTICS_DIR / f'alpaca_prices_{timestamp}.json'
    
    diagnostic_data = {
        'timestamp': datetime.now().isoformat(),
        'tickers_requested': len(tickers),
        'tickers_succeeded': len(prices_data),
        'failed_tickers': failed_tickers,
        'prices_data': prices_data
    }
    
    with open(output_file, 'w') as f:
        json.dump(diagnostic_data, f, indent=2)
    
    print(f"✅ Alpaca prices fetched: {len(prices_data)}/{len(tickers)} tickers")
    print(f"   Diagnostics: {output_file}")
    
    return prices_data


def get_alpaca_account_info() -> Optional[Dict]:
    """
    Get Alpaca account info (paper account only, for verification).
    
    Returns:
        Account info dict or None
    """
    if not is_alpaca_available():
        return None
    
    headers = {
        'APCA-API-KEY-ID': ALPACA_API_KEY,
        'APCA-API-SECRET-KEY': ALPACA_SECRET
    }
    
    try:
        url = f'{ALPACA_BASE_URL}/v2/account'
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        account = response.json()
        
        # Verify it's a paper account
        if account.get('account_number', '').startswith('PA'):
            print(f"✅ Alpaca paper account verified: {account.get('account_number')}")
            return account
        else:
            print("⚠️  WARNING: Alpaca account is not a paper account!")
            return None
            
    except Exception as e:
        print(f"Alpaca account verification failed: {e}")
        return None
