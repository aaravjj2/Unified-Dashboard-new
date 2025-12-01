"""
Unified Market Data Ingestion

This module provides a unified interface for fetching market data with automatic
fallback across multiple data sources (Finnhub → Alpaca → yfinance).

yfinance is used as last-resort fallback only.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from data_ingestion.source_clients import FinnhubClient, AlpacaClient

logger = logging.getLogger(__name__)


def fetch_market_data(
    tickers: List[str], 
    period: str = '1mo',
    preferred_source: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch market data with automatic fallback across multiple sources
    
    Fallback order: Finnhub → Alpaca → yfinance (last resort)
    
    Args:
        tickers: List of stock ticker symbols (e.g., ['AAPL', 'TSLA', 'MSFT'])
        period: Time period for historical data ('1d', '1w', '1mo', '3mo', '1y')
        preferred_source: Override fallback order ('finnhub', 'alpaca')
    
    Returns:
        Dict with:
            - 'success': bool (True if any data was fetched)
            - 'source': str (which client succeeded)
            - 'data': List[Dict] (market data for each ticker)
            - 'tickers': List[str] (requested tickers)
            - 'period': str (time period)
            - 'fetched_at': str (ISO timestamp)
            - 'errors': List[str] (errors from failed sources)
    
    Example:
        >>> result = fetch_market_data(['AAPL', 'TSLA'], period='1mo')
        >>> if result['success']:
        ...     for ticker_data in result['data']:
        ...         print(f"{ticker_data['ticker']}: ${ticker_data['current_price']}")
    """
    # Initialize clients (Polygon removed per Mission A2 revision)
    clients = {
        'finnhub': FinnhubClient(),
        'alpaca': AlpacaClient()
    }
    
    # Determine fallback order (Polygon removed)
    if preferred_source and preferred_source in clients:
        client_order = [preferred_source] + [k for k in clients.keys() if k != preferred_source]
    else:
        client_order = ['finnhub', 'alpaca']
    
    errors = []
    
    # Try each client in order
    for source_name in client_order:
        client = clients[source_name]
        
        try:
            logger.info(f"Attempting to fetch data from {source_name} for {len(tickers)} tickers")
            
            # Call unified interface
            data = client.get_market_data(tickers, period)
            
            # Validate data
            if data and len(data) > 0:
                # Check if any ticker has valid data
                has_valid_data = any(
                    ticker_data.get('current_price') is not None 
                    for ticker_data in data
                )
                
                if has_valid_data:
                    logger.info(f"✅ Successfully fetched data from {source_name}")
                    
                    return {
                        'success': True,
                        'source': source_name,
                        'data': data,
                        'tickers': tickers,
                        'period': period,
                        'fetched_at': datetime.utcnow().isoformat(),
                        'errors': errors
                    }
                else:
                    error_msg = f"{source_name}: No valid price data returned"
                    logger.warning(error_msg)
                    errors.append(error_msg)
            else:
                error_msg = f"{source_name}: Empty response"
                logger.warning(error_msg)
                errors.append(error_msg)
        
        except Exception as e:
            error_msg = f"{source_name}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            errors.append(error_msg)
    
    # All premium sources failed - try yfinance as last resort
    logger.warning("All premium data sources failed, attempting yfinance fallback")
    try:
        import yfinance as yf
        
        period_map = {
            '1d': '1d',
            '1w': '5d',
            '1mo': '1mo',
            '3mo': '3mo',
            '1y': '1y'
        }
        yf_period = period_map.get(period, '1mo')
        
        data = []
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period=yf_period)
                info = stock.info
                
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                    previous_close = hist['Close'].iloc[-2] if len(hist) >= 2 else current_price
                    change_pct = ((current_price - previous_close) / previous_close) * 100 if previous_close else None
                    
                    data.append({
                        'ticker': ticker,
                        'source': 'yfinance',
                        'current_price': float(current_price),
                        'previous_close': float(previous_close),
                        'change_pct': float(change_pct) if change_pct is not None else None,
                        'high': float(hist['High'].iloc[-1]),
                        'low': float(hist['Low'].iloc[-1]),
                        'volume': int(hist['Volume'].iloc[-1]),
                        'company_name': info.get('longName', ticker),
                        'fetched_at': datetime.utcnow().isoformat()
                    })
                    logger.info(f"✅ yfinance fallback: {ticker} @ ${current_price:.2f}")
            except Exception as ticker_error:
                logger.warning(f"yfinance failed for {ticker}: {ticker_error}")
        
        if data:
            logger.info(f"✅ Successfully fetched data from yfinance fallback ({len(data)} tickers)")
            return {
                'success': True,
                'source': 'yfinance',
                'data': data,
                'tickers': tickers,
                'period': period,
                'fetched_at': datetime.utcnow().isoformat(),
                'errors': errors
            }
        else:
            errors.append("yfinance: No valid data for any ticker")
            
    except ImportError:
        error_msg = "yfinance: Package not installed (pip install yfinance)"
        logger.error(error_msg)
        errors.append(error_msg)
    except Exception as e:
        error_msg = f"yfinance: {str(e)}"
        logger.error(f"❌ {error_msg}")
        errors.append(error_msg)
    
    # All sources including fallback failed
    logger.error(f"❌ All data sources (including yfinance) failed for tickers: {tickers}")
    
    return {
        'success': False,
        'source': None,
        'data': [],
        'tickers': tickers,
        'period': period,
        'fetched_at': datetime.utcnow().isoformat(),
        'errors': errors
    }


def get_available_sources() -> List[str]:
    """
    Get list of available data sources
    
    Returns:
        List of source names that have API keys configured
    """
    import os
    
    sources = []
    
    if os.getenv('FINNHUB_API_KEY'):
        sources.append('finnhub')
    
    if os.getenv('APCA_API_KEY_ID') and os.getenv('APCA_API_SECRET_KEY'):
        sources.append('alpaca')
    
    # yfinance always available as fallback (no API key needed)
    try:
        import yfinance
        sources.append('yfinance')
    except ImportError:
        pass
    
    return sources


def health_check() -> Dict[str, Any]:
    """
    Check health of all data source clients
    
    Returns:
        Dict with health status for each source
    """
    import os
    
    health = {
        'finnhub': {
            'configured': bool(os.getenv('FINNHUB_API_KEY')),
            'status': 'unknown'
        },
        'alpaca': {
            'configured': bool(os.getenv('APCA_API_KEY_ID') and os.getenv('APCA_API_SECRET_KEY')),
            'status': 'unknown'
        },
        'yfinance': {
            'configured': True,  # No API key needed
            'status': 'unknown'
        }
    }
    
    # Try fetching test data from each source
    test_ticker = ['AAPL']
    
    for source in health.keys():
        if health[source]['configured']:
            try:
                result = fetch_market_data(test_ticker, period='1d', preferred_source=source)
                health[source]['status'] = 'healthy' if result['success'] else 'unhealthy'
            except Exception as e:
                health[source]['status'] = 'error'
                health[source]['error'] = str(e)
        else:
            health[source]['status'] = 'not_configured'
    
    return health
