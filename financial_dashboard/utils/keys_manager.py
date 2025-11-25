"""
Centralized Key Management Module for Unified Financial Dashboard

This module provides a single source of truth for:
- Ticker symbols across all tabs (Market Trends, Weekly, Monthly)
- Price data field mappings
- Cache key generation and validation

SUPER-AGENT FIX: Ensures consistent key usage across the entire application.
"""

import logging
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass
import json
import os

logger = logging.getLogger(__name__)


# ============================================================================
# CANONICAL TICKER DEFINITIONS
# ============================================================================

# Market Trends core tickers (high priority, always fetch)
MARKET_TRENDS_TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA']

# Standard price data fields expected for all tickers
REQUIRED_PRICE_FIELDS = [
    'current_price',
    'daily_change',
    'week_start_price',
    'month_start_price',
    'profit_loss',
    'source'
]

# Optional fields (may not be present for all tickers)
OPTIONAL_PRICE_FIELDS = [
    'start_date',
    'start_price',
    'timestamp'
]


@dataclass
class TickerData:
    """Represents complete price data for a ticker"""
    ticker: str
    current_price: Optional[float] = None
    daily_change: Optional[float] = None
    week_start_price: Optional[float] = None
    month_start_price: Optional[float] = None
    profit_loss: Optional[float] = None
    source: str = 'unknown'
    start_date: Optional[str] = None
    start_price: Optional[float] = None
    timestamp: Optional[float] = None
    
    def is_complete(self) -> bool:
        """Check if all required fields are present"""
        return all([
            self.current_price is not None,
            self.daily_change is not None,
            self.week_start_price is not None,
            self.month_start_price is not None,
            self.profit_loss is not None
        ])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for caching"""
        return {
            'current_price': self.current_price,
            'daily_change': self.daily_change,
            'week_start_price': self.week_start_price,
            'month_start_price': self.month_start_price,
            'profit_loss': self.profit_loss,
            'source': self.source,
            'start_date': self.start_date,
            'start_price': self.start_price,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, ticker: str, data: Dict[str, Any]) -> 'TickerData':
        """Create from dictionary"""
        return cls(
            ticker=ticker,
            current_price=data.get('current_price'),
            daily_change=data.get('daily_change'),
            week_start_price=data.get('week_start_price'),
            month_start_price=data.get('month_start_price'),
            profit_loss=data.get('profit_loss'),
            source=data.get('source', 'unknown'),
            start_date=data.get('start_date'),
            start_price=data.get('start_price'),
            timestamp=data.get('timestamp')
        )


class KeysManager:
    """
    Centralized manager for ticker keys and price data validation.
    
    SUPER-AGENT FIX: Single source of truth for all ticker operations.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def get_market_trends_tickers(self) -> List[str]:
        """Get canonical list of Market Trends tickers"""
        return MARKET_TRENDS_TICKERS.copy()
    
    def get_required_fields(self) -> List[str]:
        """Get list of required price fields"""
        return REQUIRED_PRICE_FIELDS.copy()
    
    def get_optional_fields(self) -> List[str]:
        """Get list of optional price fields"""
        return OPTIONAL_PRICE_FIELDS.copy()
    
    def validate_ticker_data(self, ticker: str, data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate that ticker data has all required fields.
        
        Returns:
            (is_valid, missing_fields)
        """
        if not isinstance(data, dict):
            return False, ["data is not a dictionary"]
        
        missing = []
        for field in REQUIRED_PRICE_FIELDS:
            if field not in data or data[field] is None:
                missing.append(field)
        
        is_valid = len(missing) == 0
        return is_valid, missing
    
    def get_all_tickers_from_cache(self, cache_dict: Dict[str, Any]) -> Set[str]:
        """Extract all ticker symbols from a cache dictionary"""
        if not isinstance(cache_dict, dict):
            return set()
        
        if 'prices' in cache_dict:
            return set(cache_dict['prices'].keys())
        
        return set(cache_dict.keys())
    
    def validate_cache_completeness(
        self, 
        cache_dict: Dict[str, Any], 
        required_tickers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate cache completeness for required tickers.
        
        Returns:
            {
                'complete': bool,
                'total_tickers': int,
                'valid_tickers': List[str],
                'invalid_tickers': List[str],
                'missing_tickers': List[str],
                'validation_details': Dict[str, List[str]]  # ticker -> missing fields
            }
        """
        if required_tickers is None:
            required_tickers = MARKET_TRENDS_TICKERS
        
        prices = cache_dict.get('prices', {}) if isinstance(cache_dict, dict) else {}
        
        valid_tickers = []
        invalid_tickers = []
        missing_tickers = []
        validation_details = {}
        
        for ticker in required_tickers:
            if ticker not in prices:
                missing_tickers.append(ticker)
                validation_details[ticker] = ['TICKER_NOT_IN_CACHE']
            else:
                is_valid, missing_fields = self.validate_ticker_data(ticker, prices[ticker])
                if is_valid:
                    valid_tickers.append(ticker)
                else:
                    invalid_tickers.append(ticker)
                    validation_details[ticker] = missing_fields
        
        return {
            'complete': len(valid_tickers) == len(required_tickers),
            'total_tickers': len(prices),
            'valid_tickers': valid_tickers,
            'invalid_tickers': invalid_tickers,
            'missing_tickers': missing_tickers,
            'validation_details': validation_details
        }
    
    def format_price_data(
        self,
        current: float,
        previous: float,
        week_start: float,
        month_start: float,
        source: str = 'api'
    ) -> Dict[str, Any]:
        """
        Create standardized price data dictionary.
        
        SUPER-AGENT FIX: Ensures all price data follows the same format.
        """
        return {
            'current_price': round(current, 2),
            'daily_change': round(current - previous, 2),
            'week_start_price': round(week_start, 2),
            'month_start_price': round(month_start, 2),
            'profit_loss': round(current - month_start, 2),
            'source': source
        }
    
    def log_cache_status(self, cache_dict: Dict[str, Any], label: str = "Cache"):
        """Log detailed cache validation status"""
        validation = self.validate_cache_completeness(cache_dict)
        
        self.logger.info(f"{'=' * 60}")
        self.logger.info(f"{label} Validation Report")
        self.logger.info(f"{'=' * 60}")
        self.logger.info(f"Total tickers in cache: {validation['total_tickers']}")
        self.logger.info(f"Valid Market Trends tickers: {len(validation['valid_tickers'])}/{len(MARKET_TRENDS_TICKERS)}")
        self.logger.info(f"  ✅ Complete: {', '.join(validation['valid_tickers'])}")
        
        if validation['invalid_tickers']:
            self.logger.warning(f"  ⚠️  Incomplete: {', '.join(validation['invalid_tickers'])}")
            for ticker in validation['invalid_tickers']:
                missing = validation['validation_details'].get(ticker, [])
                self.logger.warning(f"     {ticker}: missing {', '.join(missing)}")
        
        if validation['missing_tickers']:
            self.logger.error(f"  ❌ Missing: {', '.join(validation['missing_tickers'])}")
        
        self.logger.info(f"Overall status: {'✅ COMPLETE' if validation['complete'] else '❌ INCOMPLETE'}")
        self.logger.info(f"{'=' * 60}")
        
        return validation


# Global instance
_keys_manager = KeysManager()


# Convenience functions
def get_market_trends_tickers() -> List[str]:
    """Get list of Market Trends tickers"""
    return _keys_manager.get_market_trends_tickers()


def validate_ticker_data(ticker: str, data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """Validate ticker price data"""
    return _keys_manager.validate_ticker_data(ticker, data)


def validate_cache(cache_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Validate cache completeness"""
    return _keys_manager.validate_cache_completeness(cache_dict)


def log_cache_status(cache_dict: Dict[str, Any], label: str = "Cache"):
    """Log cache validation status"""
    return _keys_manager.log_cache_status(cache_dict, label)


def format_price_data(current: float, previous: float, week_start: float, month_start: float, source: str = 'api') -> Dict[str, Any]:
    """Format price data in standard structure"""
    return _keys_manager.format_price_data(current, previous, week_start, month_start, source)
