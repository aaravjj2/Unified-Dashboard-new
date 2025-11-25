"""
Volatility Lab - Data Connectors
===================================

Lazy-loaded data connectors to prevent heavy work at import time.

Connectors:
- get_options_data(): Fetch options chain (lazy)
- get_price_data(): Fetch historical prices (lazy)
- get_iv_history(): Fetch historical IV surfaces (lazy)

All connectors support VOLLAB_DETERMINISTIC mode for testing.
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
import pandas as pd

logger = logging.getLogger(__name__)

# Lazy loading flags
_options_connector = None
_price_connector = None

DETERMINISTIC_MODE = os.getenv('VOLLAB_DETERMINISTIC', '0') == '1'


def get_options_data(ticker: str, expiries: Optional[List[str]] = None) -> Dict:
    """
    Lazy-load options chain data.
    
    Args:
        ticker: Stock ticker symbol
        expiries: Optional list of expiry dates
        
    Returns:
        Dict with options chain data or deterministic fixture
    """
    global _options_connector
    
    if DETERMINISTIC_MODE:
        logger.info(f"DETERMINISTIC MODE: Returning fixture options data for {ticker}")
        return {
            'ticker': ticker,
            'expiries': ['2024-12-20', '2025-01-17', '2025-02-21'],
            'strikes': [450, 460, 470, 480, 490, 500, 510],
            'calls': {},  # Populated with fixture data
            'puts': {},
            'deterministic': True
        }
    
    # Lazy load connector on first use
    if _options_connector is None:
        try:
            from financial_dashboard.connectors import options
            _options_connector = options
            logger.info("Loaded options connector")
        except ImportError:
            logger.warning("Options connector not available")
            return {'error': 'Options connector not available'}
    
    try:
        return _options_connector.get_chain(ticker, expiries=expiries)
    except Exception as e:
        logger.error(f"Error fetching options data: {e}")
        return {'error': str(e)}


def get_price_data(ticker: str, period: str = '1y') -> pd.DataFrame:
    """
    Lazy-load historical price data.
    
    Args:
        ticker: Stock ticker symbol
        period: Historical period
        
    Returns:
        DataFrame with OHLCV data or deterministic fixture
    """
    global _price_connector
    
    if DETERMINISTIC_MODE:
        logger.info(f"DETERMINISTIC MODE: Returning fixture price data for {ticker}")
        # Return simple DataFrame fixture
        return pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=252, freq='D'),
            'close': 475 + pd.Series(range(252)) * 0.1  # Slight uptrend
        })
    
    # Lazy load connector on first use
    if _price_connector is None:
        try:
            from financial_dashboard.connectors import prices
            _price_connector = prices
            logger.info("Loaded price connector")
        except ImportError:
            logger.warning("Price connector not available")
            return pd.DataFrame()
    
    try:
        return _price_connector.get_history(ticker, period=period)
    except Exception as e:
        logger.error(f"Error fetching price data: {e}")
        return pd.DataFrame()


def get_iv_history(ticker: str, days: int = 30) -> List[Dict]:
    """
    Fetch historical IV surface computations.
    
    Args:
        ticker: Stock ticker symbol
        days: Number of days to look back
        
    Returns:
        List of historical surface metadata
    """
    if DETERMINISTIC_MODE:
        logger.info(f"DETERMINISTIC MODE: Returning fixture IV history for {ticker}")
        return [
            {
                'surface_id': 'surf_fixture_1',
                'ticker': ticker,
                'timestamp': '2024-11-20T10:00:00',
                'atm_iv': 0.18,
                'deterministic': True
            },
            {
                'surface_id': 'surf_fixture_2',
                'ticker': ticker,
                'timestamp': '2024-11-21T10:00:00',
                'atm_iv': 0.19,
                'deterministic': True
            }
        ]
    
    # In production, query from DB or API
    try:
        # TODO: Implement DB query for vol_surfaces table
        return []
    except Exception as e:
        logger.error(f"Error fetching IV history: {e}")
        return []


__all__ = ['get_options_data', 'get_price_data', 'get_iv_history']
