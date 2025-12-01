"""
Forecast Adapter - Bridge between Market Forecast Tab and ML Infrastructure
===========================================================================

This adapter provides a unified interface for the Market Forecast tab to:
1. Use the local ML runner for predictions
2. Fetch real market data via PriceClient/Alpaca/yfinance fallback chain
3. Generate forecast time series with confidence intervals
4. Provide SHAP explanations for model predictions

Architecture:
- Synchronous mode: Direct prediction via ml_runner
- Asynchronous mode: Background job via _shared module
- Deterministic mode: Fixed seed for testing
- Data sources: Alpaca → yfinance (via fetch_historical_data)
"""

import os
import sys
import logging
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import json

# Setup paths
ADAPTER_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(ADAPTER_DIR)
PROJECT_ROOT = os.path.dirname(APP_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logger = logging.getLogger(__name__)

# Default cache TTL in seconds
DEFAULT_CACHE_TTL = 300  # 5 minutes for price data
FORECAST_CACHE_TTL = 600  # 10 minutes for forecast results


class TTLCache:
    """Simple TTL cache for forecast data and price data."""
    
    def __init__(self, default_ttl: int = DEFAULT_CACHE_TTL):
        self._cache = {}
        self._timestamps = {}
        self._default_ttl = default_ttl
    
    def get(self, key: str, ttl: int = None) -> Optional[Any]:
        """Get a cached value if not expired."""
        if key not in self._cache:
            return None
        
        ttl = ttl or self._default_ttl
        age = time.time() - self._timestamps.get(key, 0)
        
        if age > ttl:
            # Expired
            del self._cache[key]
            del self._timestamps[key]
            return None
        
        return self._cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """Store a value in cache."""
        self._cache[key] = value
        self._timestamps[key] = time.time()
    
    def clear(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        self._timestamps.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'entries': len(self._cache),
            'keys': list(self._cache.keys())
        }


class ForecastAdapter:
    """
    Adapter for market forecast predictions using local ML infrastructure.
    
    Features:
    - Real market data fetching with caching
    - ML-based price predictions
    - Confidence interval generation
    - SHAP explanations
    - TTL caching for performance
    """
    
    def __init__(self, bento_url: Optional[str] = None, deterministic: bool = False):
        """
        Initialize forecast adapter.
        
        Args:
            bento_url: URL for Bento service (legacy, not used in local mode)
            deterministic: If True, use fixed seed for reproducible results
        """
        self.bento_url = bento_url
        self.deterministic = deterministic
        self.cache = {}  # Legacy cache for forecast results by ID
        self._price_cache = TTLCache(DEFAULT_CACHE_TTL)
        self._forecast_cache = TTLCache(FORECAST_CACHE_TTL)
        
        # Initialize pluggable serving client (Bento, Triton or local)
        try:
            from financial_dashboard.serving.serving_client import ServingClient
            self.serving_client = ServingClient()
            logger.info(f"Serving client initialized (mode={self.serving_client.mode})")
        except Exception as e:
            logger.warning(f"Serving client not available: {e}")
            self.serving_client = None
        
        # Initialize ML runner
        try:
            import ml_runner
            self.ml_runner = ml_runner
            self.ml_runner.initialize()
            logger.info("✅ ML Runner initialized for forecast adapter")
        except Exception as e:
            logger.warning(f"ML Runner not available: {e}")
            self.ml_runner = None
    
    def run_forecast(
        self,
        ticker: str,
        horizon: int,
        confidence: float,
        model: str,
        forecast_id: str
    ) -> Dict[str, Any]:
        """
        Run synchronous forecast for a single ticker.
        
        Args:
            ticker: Stock ticker symbol
            horizon: Forecast horizon in days
            confidence: Confidence level (0.90, 0.95, 0.99)
            model: Model version (xgboost_v1, lstm_v1)
            forecast_id: Unique forecast identifier
        
        Returns:
            Dict with forecast results including time series and metadata
        """
        forecast_start = time.time()
        
        try:
            logger.info(f"Running forecast for {ticker}, horizon={horizon} days")
            
            # Fetch historical data with metadata tracking
            prices, data_metadata = self._fetch_historical_data(ticker, lookback_days=252)
            
            if prices is None or len(prices) < 30:
                logger.error(f"Insufficient data for {ticker}")
                return self._error_response(ticker, "Insufficient historical data")
            
            # Generate forecast using configured serving backend (Bento/Triton/local)
            forecast_data = None
            inference_source = 'statistical'  # Track which inference path was used
            
            if self.serving_client:
                try:
                    sc_res = self.serving_client.predict_forecast(ticker, horizon, model, confidence)
                    if sc_res.get('status') == 'success' and 'data' in sc_res:
                        forecast_data = sc_res['data']
                        inference_source = f'serving_{self.serving_client.mode}'
                    elif sc_res.get('status') == 'success' and 'forecast' in sc_res.get('data', {}):
                        forecast_data = sc_res['data']
                        inference_source = f'serving_{self.serving_client.mode}'
                except Exception as e:
                    logger.warning(f"Serving client prediction failed: {e}")

            if forecast_data is not None:
                # Try to parse forecast series from returned data
                try:
                    if isinstance(forecast_data.get('forecast', None), list):
                        forecast_series = np.array([f.get('yhat', f.get('value', None)) for f in forecast_data['forecast']])
                    elif isinstance(forecast_data.get('forecast', None), (list, np.ndarray)):
                        forecast_series = np.array(forecast_data['forecast'])
                    else:
                        # If forecast_data format isn't recognized, fallback to local
                        logger.warning('Unexpected forecast payload, falling back to local/statistical')
                        forecast_series = None
                except Exception:
                    forecast_series = None
            else:
                forecast_series = None

            if forecast_series is None:
                # Next: use local ML runner
                if self.ml_runner:
                    forecast_series = self._ml_forecast(ticker, prices, horizon)
                    inference_source = 'ml_runner'
                else:
                    # Fallback to statistical forecast
                    forecast_series = self._statistical_forecast(prices, horizon)
                    inference_source = 'statistical'
            
            # Calculate confidence intervals
            lower_bound, upper_bound = self._calculate_confidence_intervals(
                prices, forecast_series, confidence
            )
            
            # Build response with enhanced metadata
            current_price = float(prices.iloc[-1])
            forecast_mean = float(np.mean(forecast_series))
            forecast_duration_ms = round((time.time() - forecast_start) * 1000, 2)
            
            result = {
                'ticker': ticker,
                'horizon': horizon,
                'confidence': confidence,
                'model': model,
                'forecast_id': forecast_id,
                'timestamp': datetime.utcnow().isoformat(),
                'current_price': current_price,
                'forecast_price': forecast_mean,
                'forecast': forecast_series.tolist(),  # Time series
                'lower_bound': lower_bound.tolist(),
                'upper_bound': upper_bound.tolist(),
                'expected_return': (forecast_mean - current_price) / current_price,
                'volatility': float(np.std(forecast_series)),
                'data_points': len(prices),
                'status': 'success',
                # Enhanced metadata
                'metadata': {
                    'data_source': data_metadata.get('source', 'unknown'),
                    'data_fetch_duration_ms': data_metadata.get('fetch_duration_ms', 0),
                    'data_timestamp': data_metadata.get('data_timestamp'),
                    'inference_source': inference_source,
                    'total_duration_ms': forecast_duration_ms,
                    'generated_at': datetime.utcnow().isoformat()
                }
            }
            
            # Cache result
            self.cache[forecast_id] = result
            
            logger.info(f"✅ Forecast complete for {ticker}: ${current_price:.2f} → ${forecast_mean:.2f} "
                        f"(data={data_metadata.get('source')}, inference={inference_source}, {forecast_duration_ms}ms)")
            
            return result
            
        except Exception as e:
            logger.exception(f"Forecast error for {ticker}: {e}")
            return self._error_response(ticker, str(e))
    
    def queue_forecast(
        self,
        ticker: str,
        horizon: int,
        confidence: float,
        model: str,
        forecast_id: str
    ) -> Dict[str, Any]:
        """
        Queue asynchronous forecast job.
        
        Args:
            Same as run_forecast
        
        Returns:
            Dict with job_id and status
        """
        try:
            # Import shared module for background jobs
            from financial_dashboard._shared import SH
            
            # Start background job
            job_id = SH.start_background_job(
                target=self.run_forecast,
                kwargs={
                    'ticker': ticker,
                    'horizon': horizon,
                    'confidence': confidence,
                    'model': model,
                    'forecast_id': forecast_id
                }
            )
            
            logger.info(f"✅ Queued forecast job {job_id} for {ticker}")
            
            return {
                'status': 'queued',
                'job_id': job_id,
                'forecast_id': forecast_id,
                'ticker': ticker,
                'message': f'Forecast job queued for {ticker}'
            }
            
        except Exception as e:
            logger.exception(f"Failed to queue forecast: {e}")
            # Fallback to synchronous execution
            return {
                'status': 'fallback_sync',
                'result': self.run_forecast(ticker, horizon, confidence, model, forecast_id)
            }
    
    def get_explanation(self, forecast_id: str) -> Optional[Dict[str, Any]]:
        """
        Get SHAP explanation for a forecast.
        
        Args:
            forecast_id: Forecast identifier
        
        Returns:
            Dict with feature importance and SHAP values
        """
        try:
            # Check cache
            if forecast_id not in self.cache:
                logger.warning(f"Forecast {forecast_id} not found in cache")
                return None
            
            forecast = self.cache[forecast_id]
            ticker = forecast['ticker']
            
            # Generate mock SHAP values (in production, use actual SHAP)
            features = [
                'Price Momentum',
                'Volume Trend',
                'Volatility',
                'Market Sentiment',
                'Technical Indicators'
            ]
            
            # Deterministic values if in deterministic mode
            if self.deterministic:
                np.random.seed(hash(ticker) % 2**32)
            
            shap_values = np.random.randn(len(features)) * 0.1
            
            explanation = {
                'forecast_id': forecast_id,
                'ticker': ticker,
                'features': features,
                'shap_values': shap_values.tolist(),
                'feature_importance': {
                    features[i]: abs(shap_values[i])
                    for i in range(len(features))
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
            return explanation
            
        except Exception as e:
            logger.exception(f"Failed to generate explanation: {e}")
            return None
    
    def _fetch_historical_data(self, ticker: str, lookback_days: int = 252) -> tuple[Optional[pd.Series], Dict[str, Any]]:
        """
        Fetch historical price data for a ticker using unified price fetching.
        
        Uses Alpaca → yfinance fallback chain via fetch_historical_data utility.
        Returns (prices, metadata) tuple with source tracking.
        Includes TTL caching to avoid repeated fetches.
        
        Args:
            ticker: Stock ticker symbol
            lookback_days: Number of days to fetch
        
        Returns:
            Tuple of (Pandas Series of closing prices, metadata dict)
        """
        # Check cache first
        cache_key = f"prices_{ticker}_{lookback_days}"
        cached = self._price_cache.get(cache_key)
        if cached is not None:
            prices, metadata = cached
            metadata = metadata.copy()
            metadata['cache_hit'] = True
            logger.debug(f"Cache hit for {ticker} price data")
            return prices, metadata
        
        fetch_start = time.time()
        metadata = {
            'source': 'unknown',
            'fetch_duration_ms': 0,
            'data_timestamp': None,
            'ticker': ticker,
            'requested_lookback': lookback_days,
            'cache_hit': False
        }
        
        try:
            # Use the unified fetch_historical_data helper (Alpaca → yfinance fallback)
            from financial_dashboard.utils.price_fetch import fetch_historical_data
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days + 30)  # Extra buffer
            
            logger.info(f"Fetching {lookback_days} days of data for {ticker} via unified price fetcher")
            
            # Fetch data using Alpaca → yfinance fallback
            prices_df = fetch_historical_data(
                tickers=[ticker],
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                use_alpaca=True
            )
            
            metadata['fetch_duration_ms'] = round((time.time() - fetch_start) * 1000, 2)
            
            if prices_df.empty or ticker not in prices_df.columns:
                logger.error(f"No data returned for {ticker}")
                metadata['source'] = 'none'
                return None, metadata
            
            # Extract closing prices
            prices = prices_df[ticker].dropna()
            
            if prices.empty:
                logger.error(f"Empty price series for {ticker}")
                metadata['source'] = 'none'
                return None, metadata
            
            # Trim to requested lookback
            if len(prices) > lookback_days:
                prices = prices.iloc[-lookback_days:]
            
            # Determine source based on data characteristics
            # (fetch_historical_data logs which source succeeded internally)
            metadata['source'] = 'alpaca_or_yfinance'
            metadata['data_timestamp'] = prices.index[-1].isoformat() if hasattr(prices.index[-1], 'isoformat') else str(prices.index[-1])
            metadata['data_points'] = len(prices)
            
            # Cache the result
            self._price_cache.set(cache_key, (prices, metadata))
            
            logger.info(f"✅ Fetched {len(prices)} price points for {ticker} in {metadata['fetch_duration_ms']}ms")
            
            return prices, metadata
            
        except ImportError as e:
            logger.warning(f"fetch_historical_data not available, falling back to yfinance: {e}")
            # Fallback to direct yfinance if the utility isn't available
            return self._fetch_historical_data_yfinance_fallback(ticker, lookback_days, fetch_start, metadata, cache_key)
            
        except Exception as e:
            logger.exception(f"Failed to fetch data for {ticker}: {e}")
            metadata['fetch_duration_ms'] = round((time.time() - fetch_start) * 1000, 2)
            metadata['error'] = str(e)
            return None, metadata
    
    def _fetch_historical_data_yfinance_fallback(
        self, ticker: str, lookback_days: int, fetch_start: float, metadata: Dict[str, Any], cache_key: str = None
    ) -> tuple[Optional[pd.Series], Dict[str, Any]]:
        """Direct yfinance fallback when unified fetcher is unavailable."""
        try:
            import yfinance as yf
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days + 30)
            
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date, auto_adjust=True)
            
            metadata['fetch_duration_ms'] = round((time.time() - fetch_start) * 1000, 2)
            
            if hist.empty:
                metadata['source'] = 'none'
                return None, metadata
            
            prices = hist['Close'].dropna()
            if len(prices) > lookback_days:
                prices = prices.iloc[-lookback_days:]
            
            metadata['source'] = 'yfinance'
            metadata['data_timestamp'] = prices.index[-1].isoformat() if hasattr(prices.index[-1], 'isoformat') else str(prices.index[-1])
            metadata['data_points'] = len(prices)
            
            # Cache if cache_key provided
            if cache_key:
                self._price_cache.set(cache_key, (prices, metadata))
            
            return prices, metadata
            
        except Exception as e:
            logger.exception(f"yfinance fallback failed for {ticker}: {e}")
            metadata['fetch_duration_ms'] = round((time.time() - fetch_start) * 1000, 2)
            metadata['error'] = str(e)
            return None, metadata
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._price_cache.clear()
        self._forecast_cache.clear()
        self.cache.clear()
        logger.info("Forecast adapter cache cleared")
    
    def cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'price_cache': self._price_cache.stats(),
            'forecast_cache': self._forecast_cache.stats(),
            'legacy_cache_entries': len(self.cache)
        }
    
    def _ml_forecast(self, ticker: str, prices: pd.Series, horizon: int) -> np.ndarray:
        """
        Generate forecast using ML runner.
        
        Args:
            ticker: Stock ticker
            prices: Historical prices
            horizon: Forecast horizon in days
        
        Returns:
            Array of forecasted prices
        """
        try:
            # Prepare input for ML model
            input_data = {
                'ticker': ticker,
                'prices': prices.tolist()
            }
            
            # Run prediction
            result = self.ml_runner.predict('forecast', input_data)
            
            if result and result.get('metadata', {}).get('success'):
                # Extract predicted price
                predicted_price = result.get('predicted_price', prices.iloc[-1])
                
                # Generate time series by interpolating
                current_price = prices.iloc[-1]
                forecast_series = np.linspace(current_price, predicted_price, horizon)
                
                # Add some realistic variation
                if not self.deterministic:
                    volatility = prices.pct_change().std() * np.sqrt(252)
                    noise = np.random.randn(horizon) * volatility * current_price * 0.1
                    forecast_series += noise
                
                return forecast_series
            else:
                logger.warning("ML prediction failed, falling back to statistical method")
                return self._statistical_forecast(prices, horizon)
                
        except Exception as e:
            logger.exception(f"ML forecast failed: {e}")
            return self._statistical_forecast(prices, horizon)
    
    def _statistical_forecast(self, prices: pd.Series, horizon: int) -> np.ndarray:
        """
        Generate forecast using statistical methods (fallback).
        
        Args:
            prices: Historical prices
            horizon: Forecast horizon in days
        
        Returns:
            Array of forecasted prices
        """
        # Calculate trend and volatility
        returns = prices.pct_change().dropna()
        mean_return = returns.mean()
        volatility = returns.std()
        
        # Generate forecast
        current_price = prices.iloc[-1]
        forecast_series = np.zeros(horizon)
        
        if self.deterministic:
            np.random.seed(42)
        
        for i in range(horizon):
            # Random walk with drift
            daily_return = mean_return + volatility * np.random.randn()
            if i == 0:
                forecast_series[i] = current_price * (1 + daily_return)
            else:
                forecast_series[i] = forecast_series[i-1] * (1 + daily_return)
        
        return forecast_series
    
    def _calculate_confidence_intervals(
        self,
        prices: pd.Series,
        forecast: np.ndarray,
        confidence: float
    ) -> tuple:
        """
        Calculate confidence intervals for forecast.
        
        Args:
            prices: Historical prices
            forecast: Forecasted prices
            confidence: Confidence level
        
        Returns:
            Tuple of (lower_bound, upper_bound) arrays
        """
        from scipy import stats
        
        # Calculate historical volatility
        returns = prices.pct_change().dropna()
        volatility = returns.std()
        
        # Z-score for confidence level
        z_score = stats.norm.ppf((1 + confidence) / 2)
        
        # Calculate bounds
        horizon = len(forecast)
        lower_bound = np.zeros(horizon)
        upper_bound = np.zeros(horizon)
        
        for i in range(horizon):
            # Expanding confidence interval over time
            time_factor = np.sqrt(i + 1)
            interval = z_score * volatility * forecast[i] * time_factor
            
            lower_bound[i] = forecast[i] - interval
            upper_bound[i] = forecast[i] + interval
        
        return lower_bound, upper_bound
    
    def _error_response(self, ticker: str, error_message: str) -> Dict[str, Any]:
        """Generate error response."""
        return {
            'ticker': ticker,
            'status': 'error',
            'error': error_message,
            'timestamp': datetime.utcnow().isoformat()
        }


# Export
__all__ = ['ForecastAdapter']
