"""
OpenBB Macro Economic Data Loader

Phase 1: Fetches GDP, CPI, Unemployment from free OpenBB providers.
Falls back to simulated data if OpenBB is not installed.

Author: Agent-P1
Date: 2025-12-28
"""

import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Try to import OpenBB
try:
    from openbb import obb
    OPENBB_AVAILABLE = True
    logger.info("OpenBB SDK loaded successfully")
except ImportError:
    OPENBB_AVAILABLE = False
    logger.warning("OpenBB not available, using simulated macro data")

# Try to import yfinance as fallback
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

# Deterministic mode for testing
DETERMINISTIC = os.getenv('PHASE1_DETERMINISTIC', '0') == '1'

# Supported macro indicators
SUPPORTED_INDICATORS = {
    'gdp': {
        'name': 'GDP Growth',
        'description': 'Gross Domestic Product Growth Rate (Quarterly)',
        'unit': '%',
        'frequency': 'quarterly'
    },
    'cpi': {
        'name': 'CPI Inflation',
        'description': 'Consumer Price Index Year-over-Year Change',
        'unit': '%',
        'frequency': 'monthly'
    },
    'unemployment': {
        'name': 'Unemployment Rate',
        'description': 'Civilian Unemployment Rate',
        'unit': '%',
        'frequency': 'monthly'
    },
    'interest_rate': {
        'name': 'Interest Rate',
        'description': 'Federal Funds Effective Rate',
        'unit': '%',
        'frequency': 'daily'
    },
    'yield_10y': {
        'name': '10Y Treasury Yield',
        'description': '10-Year Treasury Constant Maturity Rate',
        'unit': '%',
        'frequency': 'daily'
    }
}


@dataclass
class MacroDataResult:
    """Result of macro data fetch."""
    indicator: str
    name: str
    dates: List[str]
    values: List[float]
    unit: str
    country: str
    source: str
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    success: bool = True
    error_message: str = ""


class MacroDataLoader:
    """
    Macro economic data loader using OpenBB SDK.
    
    Fetches data from free providers (OECD, FRED, etc.)
    Falls back to simulated data if unavailable.
    """
    
    def __init__(self, country: str = 'USA'):
        """
        Initialize macro data loader.
        
        Args:
            country: Country code (default: USA)
        """
        self.country = country.upper()
        self._cache: Dict[str, MacroDataResult] = {}
    
    def get_gdp(self, periods: int = 20) -> MacroDataResult:
        """
        Get GDP growth rate data.
        
        Args:
            periods: Number of periods to fetch
            
        Returns:
            MacroDataResult with GDP data
        """
        cache_key = f"gdp_{self.country}_{periods}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        if DETERMINISTIC:
            result = self._generate_deterministic_gdp(periods)
        elif OPENBB_AVAILABLE:
            result = self._fetch_gdp_openbb(periods)
        else:
            result = self._generate_deterministic_gdp(periods)
        
        self._cache[cache_key] = result
        return result
    
    def _fetch_gdp_openbb(self, periods: int) -> MacroDataResult:
        """Fetch GDP from OpenBB."""
        try:
            # OpenBB economy.gdp
            data = obb.economy.gdp(
                country=self.country.lower(),
                provider='oecd'  # Free provider
            )
            
            if hasattr(data, 'to_df'):
                df = data.to_df()
                df = df.tail(periods)
                
                return MacroDataResult(
                    indicator='gdp',
                    name='GDP Growth Rate',
                    dates=df.index.strftime('%Y-%m-%d').tolist(),
                    values=df['value'].tolist() if 'value' in df.columns else df.iloc[:, 0].tolist(),
                    unit='%',
                    country=self.country,
                    source='OpenBB/OECD'
                )
            
        except Exception as e:
            logger.warning(f"OpenBB GDP fetch failed: {e}")
        
        return self._generate_deterministic_gdp(periods)
    
    def _generate_deterministic_gdp(self, periods: int) -> MacroDataResult:
        """Generate deterministic GDP data for testing."""
        np.random.seed(42)
        
        # Generate quarterly dates
        end_date = datetime.now()
        dates = pd.date_range(end=end_date, periods=periods, freq='Q')
        
        # Generate realistic GDP growth pattern
        base_growth = 2.5  # Long-term average
        cycle = np.sin(np.linspace(0, 2*np.pi, periods)) * 1.5
        noise = np.random.randn(periods) * 0.5
        values = base_growth + cycle + noise
        
        # Add a recession
        recession_idx = len(values) // 3
        values[recession_idx:recession_idx+2] = [-1.5, -2.0]
        
        return MacroDataResult(
            indicator='gdp',
            name='GDP Growth Rate',
            dates=[d.strftime('%Y-Q%q').replace('Q1', 'Q1').replace('Q2', 'Q2').replace('Q3', 'Q3').replace('Q4', 'Q4') 
                   if hasattr(d, 'quarter') else d.strftime('%Y-%m-%d') for d in dates],
            values=values.tolist(),
            unit='%',
            country=self.country,
            source='Simulated'
        )
    
    def get_cpi(self, periods: int = 36) -> MacroDataResult:
        """
        Get CPI inflation data.
        
        Args:
            periods: Number of periods to fetch
            
        Returns:
            MacroDataResult with CPI data
        """
        cache_key = f"cpi_{self.country}_{periods}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        if DETERMINISTIC:
            result = self._generate_deterministic_cpi(periods)
        elif OPENBB_AVAILABLE:
            result = self._fetch_cpi_openbb(periods)
        else:
            result = self._generate_deterministic_cpi(periods)
        
        self._cache[cache_key] = result
        return result
    
    def _fetch_cpi_openbb(self, periods: int) -> MacroDataResult:
        """Fetch CPI from OpenBB."""
        try:
            data = obb.economy.cpi(
                country=self.country.lower(),
                provider='fred'  # Free provider
            )
            
            if hasattr(data, 'to_df'):
                df = data.to_df()
                df = df.tail(periods)
                
                return MacroDataResult(
                    indicator='cpi',
                    name='CPI Inflation',
                    dates=df.index.strftime('%Y-%m-%d').tolist(),
                    values=df['value'].tolist() if 'value' in df.columns else df.iloc[:, 0].tolist(),
                    unit='%',
                    country=self.country,
                    source='OpenBB/FRED'
                )
            
        except Exception as e:
            logger.warning(f"OpenBB CPI fetch failed: {e}")
        
        return self._generate_deterministic_cpi(periods)
    
    def _generate_deterministic_cpi(self, periods: int) -> MacroDataResult:
        """Generate deterministic CPI data for testing."""
        np.random.seed(43)
        
        # Generate monthly dates
        end_date = datetime.now()
        dates = pd.date_range(end=end_date, periods=periods, freq='M')
        
        # Generate realistic CPI pattern (2022-2024 style inflation)
        base_inflation = 2.0  # Long-term target
        
        # Inflation spike pattern
        spike = np.zeros(periods)
        spike_start = periods // 3
        spike_peak = spike_start + periods // 6
        spike_end = periods - periods // 6
        
        # Rising phase
        spike[spike_start:spike_peak] = np.linspace(0, 6.0, spike_peak - spike_start)
        # Falling phase
        spike[spike_peak:spike_end] = np.linspace(6.0, 1.0, spike_end - spike_peak)
        
        noise = np.random.randn(periods) * 0.3
        values = base_inflation + spike + noise
        values = np.clip(values, -1, 10)  # Realistic bounds
        
        return MacroDataResult(
            indicator='cpi',
            name='CPI Inflation',
            dates=[d.strftime('%Y-%m') for d in dates],
            values=values.tolist(),
            unit='%',
            country=self.country,
            source='Simulated'
        )
    
    def get_unemployment(self, periods: int = 36) -> MacroDataResult:
        """
        Get unemployment rate data.
        
        Args:
            periods: Number of periods to fetch
            
        Returns:
            MacroDataResult with unemployment data
        """
        cache_key = f"unemployment_{self.country}_{periods}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        if DETERMINISTIC:
            result = self._generate_deterministic_unemployment(periods)
        elif OPENBB_AVAILABLE:
            result = self._fetch_unemployment_openbb(periods)
        else:
            result = self._generate_deterministic_unemployment(periods)
        
        self._cache[cache_key] = result
        return result
    
    def _fetch_unemployment_openbb(self, periods: int) -> MacroDataResult:
        """Fetch unemployment from OpenBB."""
        try:
            data = obb.economy.unemployment(
                country=self.country.lower(),
                provider='fred'
            )
            
            if hasattr(data, 'to_df'):
                df = data.to_df()
                df = df.tail(periods)
                
                return MacroDataResult(
                    indicator='unemployment',
                    name='Unemployment Rate',
                    dates=df.index.strftime('%Y-%m-%d').tolist(),
                    values=df['value'].tolist() if 'value' in df.columns else df.iloc[:, 0].tolist(),
                    unit='%',
                    country=self.country,
                    source='OpenBB/FRED'
                )
            
        except Exception as e:
            logger.warning(f"OpenBB unemployment fetch failed: {e}")
        
        return self._generate_deterministic_unemployment(periods)
    
    def _generate_deterministic_unemployment(self, periods: int) -> MacroDataResult:
        """Generate deterministic unemployment data."""
        np.random.seed(44)
        
        # Generate monthly dates
        end_date = datetime.now()
        dates = pd.date_range(end=end_date, periods=periods, freq='M')
        
        # Generate unemployment pattern (COVID spike and recovery)
        base_rate = 4.0  # Natural rate
        
        # COVID spike pattern
        values = np.ones(periods) * base_rate
        spike_idx = periods // 2
        
        # Sharp spike
        values[spike_idx:spike_idx+3] = [8.0, 14.0, 11.0]  # COVID spike
        
        # Recovery
        recovery_len = periods - spike_idx - 3
        if recovery_len > 0:
            recovery = np.linspace(11.0, base_rate - 0.5, recovery_len)
            values[spike_idx+3:] = recovery
        
        noise = np.random.randn(periods) * 0.2
        values = values + noise
        values = np.clip(values, 3.0, 15.0)
        
        return MacroDataResult(
            indicator='unemployment',
            name='Unemployment Rate',
            dates=[d.strftime('%Y-%m') for d in dates],
            values=values.tolist(),
            unit='%',
            country=self.country,
            source='Simulated'
        )
    
    def get_all_indicators(self) -> Dict[str, MacroDataResult]:
        """
        Get all supported indicators.
        
        Returns:
            Dict mapping indicator name to MacroDataResult
        """
        return {
            'gdp': self.get_gdp(),
            'cpi': self.get_cpi(),
            'unemployment': self.get_unemployment()
        }
    
    def get_market_index(self, symbol: str = 'SPY', periods: int = 252) -> Optional[pd.DataFrame]:
        """
        Get market index data for correlation analysis.
        
        Args:
            symbol: Index symbol (default: SPY)
            periods: Number of trading days
            
        Returns:
            DataFrame with price and returns, or None
        """
        if DETERMINISTIC or not YFINANCE_AVAILABLE:
            return self._generate_deterministic_market(periods)
        
        try:
            data = yf.download(symbol, period='1y', progress=False)
            data['returns'] = data['Adj Close'].pct_change()
            return data.tail(periods)
        except Exception as e:
            logger.warning(f"Market data fetch failed: {e}")
            return self._generate_deterministic_market(periods)
    
    def _generate_deterministic_market(self, periods: int) -> pd.DataFrame:
        """Generate deterministic market data."""
        np.random.seed(45)
        
        dates = pd.date_range(end=datetime.now(), periods=periods, freq='B')
        
        # Random walk with drift
        returns = np.random.randn(periods) * 0.01 + 0.0003  # ~7.5% annual return
        prices = 100 * np.exp(np.cumsum(returns))
        
        return pd.DataFrame({
            'Adj Close': prices,
            'returns': returns
        }, index=dates)


def get_macro_data(
    indicator: str,
    country: str = 'USA',
    use_cache: bool = True
) -> MacroDataResult:
    """
    Convenience function to get macro data.
    
    Args:
        indicator: Indicator name (gdp, cpi, unemployment)
        country: Country code
        use_cache: Whether to use cached data
        
    Returns:
        MacroDataResult
    """
    from financial_dashboard.utils.cache_manager import (
        get_redis_cache,
        cache_key_macro
    )
    
    cache = get_redis_cache()
    cache_key = cache_key_macro(indicator, country)
    
    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            logger.info(f"Using cached macro data: {cache_key}")
            return MacroDataResult(**cached)
    
    # Fetch data
    loader = MacroDataLoader(country)
    
    if indicator == 'gdp':
        result = loader.get_gdp()
    elif indicator == 'cpi':
        result = loader.get_cpi()
    elif indicator == 'unemployment':
        result = loader.get_unemployment()
    else:
        result = MacroDataResult(
            indicator=indicator,
            name='Unknown',
            dates=[],
            values=[],
            unit='',
            country=country,
            source='',
            success=False,
            error_message=f"Unknown indicator: {indicator}"
        )
    
    # Cache result
    if result.success:
        cache.set(cache_key, {
            'indicator': result.indicator,
            'name': result.name,
            'dates': result.dates,
            'values': result.values,
            'unit': result.unit,
            'country': result.country,
            'source': result.source,
            'last_updated': result.last_updated,
            'success': result.success
        }, ttl=86400)  # 24 hour cache for macro data
    
    return result
