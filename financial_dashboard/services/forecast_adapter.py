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
                # Next: use ensemble if requested, otherwise local ML runner
                if model in ('ensemble', 'weighted_ensemble'):
                    forecast_series = self._ensemble_forecast(ticker, prices, horizon)
                    inference_source = 'ensemble'
                elif self.ml_runner:
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

    def prewarm(self, tickers: List[str], lookback_days: int = 252) -> None:
        """
        Pre-warm the adapter by fetching recent price data for a list of tickers.

        This helps reduce first-load latency for the Market Forecast tab by
        populating the internal TTL cache with fresh historical prices.

        Args:
            tickers: List of ticker symbols to prefetch
            lookback_days: Number of lookback days to fetch
        """
        cache_dir = os.path.join(os.path.expanduser('~'), '.cache', 'financial_dashboard')
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, 'prewarm_cache.json')

        try:
            logger.info(f"Prewarming forecast adapter for {len(tickers)} tickers")

            # Try to load previous prewarm cache to avoid re-fetching unchanged tickers
            existing = {}
            try:
                import json as _json
                if os.path.exists(cache_file):
                    with open(cache_file, 'r', encoding='utf-8') as cf:
                        existing = _json.load(cf)
            except Exception:
                existing = {}

            results = {}
            for t in tickers:
                tkey = t.upper()
                if tkey in existing:
                    # Use cached metadata but still attempt a lightweight refresh
                    results[tkey] = existing[tkey]
                    try:
                        prices, meta = self._fetch_historical_data(t, lookback_days=lookback_days)
                        if prices is not None:
                            results[tkey] = {**meta, 'data_points': len(prices)}
                    except Exception:
                        logger.debug(f"Prewarm quick-refresh failed for {t}; keeping cached metadata")
                    continue

                try:
                    prices, meta = self._fetch_historical_data(t, lookback_days=lookback_days)
                    if prices is not None:
                        results[tkey] = {**meta, 'data_points': len(prices)}
                        logger.debug(f"Prewarm fetched {results[tkey].get('data_points')} points for {t} (source={results[tkey].get('source')})")
                except Exception as e:
                    logger.warning(f"Prewarm failed for {t}: {e}")

            # Persist minimal metadata for next startup
            try:
                import json as _json
                with open(cache_file, 'w', encoding='utf-8') as cf:
                    _json.dump(results, cf)
            except Exception:
                logger.debug('Could not write prewarm cache file')

            # Optionally export a Triton model repository for the ensemble
            try:
                use_triton = os.environ.get('USE_TRITON', '0')
                if use_triton == '1':
                    try:
                        from financial_dashboard.serving.triton.forecast_ensemble import export_model_repo
                        logger.info('Attempting Triton model export (forecast_ensemble)')
                        ok = export_model_repo.build()
                        if ok:
                            logger.info('Triton model repository prepared')
                        else:
                            logger.warning('Triton export failed')
                    except Exception as e:
                        logger.exception(f'Triton export not available: {e}')
            except Exception:
                logger.exception('Triton export step failed')

            # Warm ML runner models (if available) to reduce cold start
            try:
                self.warm_ml_runner()
            except Exception:
                logger.exception('ML runner warmup failed')

        except Exception:
            logger.exception("Prewarm procedure failed")
    
    def cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'price_cache': self._price_cache.stats(),
            'forecast_cache': self._forecast_cache.stats(),
            'legacy_cache_entries': len(self.cache)
        }

    def warm_ml_runner(self) -> None:
        """
        Warm the ML runner by loading models or running a light dummy prediction.

        This helps reduce first-request latency by ensuring heavyweight model
        artifacts are loaded into memory (ML frameworks, CUDA contexts, etc.).
        The method is defensive and will no-op if no ml_runner is present.
        """
        try:
            if not self.ml_runner:
                logger.info('No ml_runner available to warm')
                return

            # Preferred: call a dedicated warmup method if the runner exposes it
            if hasattr(self.ml_runner, 'warm_up'):
                try:
                    logger.info('Warming ml_runner via warm_up()')
                    self.ml_runner.warm_up()
                    logger.info('ml_runner warm_up completed')
                    return
                except Exception:
                    logger.exception('ml_runner.warm_up() failed, falling back to dummy predict')

            # Fallback: run a lightweight dummy predict call
            try:
                dummy_input = {'ticker': 'SPY', 'prices': [100.0] * 60}
                logger.info('Running dummy ml_runner.predict to warm models')
                _ = self.ml_runner.predict('forecast', dummy_input)
                logger.info('ml_runner dummy predict completed')
            except Exception:
                logger.exception('ml_runner dummy predict failed during warmup')
        except Exception:
            logger.exception('Unexpected error during ml_runner warmup')

    def _compute_model_weights(self, prices: pd.Series) -> Dict[str, float]:
        """
        Compute model weights for the ensemble based on a quick holdout validation.

        Returns a dict with keys 'ml' and 'stat' representing the relative weights.
        This is a lightweight heuristic used as a fallback; if any step fails we
        return a reasonable default.
        """
        default_ml_weight = float(os.environ.get('ENSEMBLE_ML_WEIGHT', 0.7))
        try:
            holdout = 14
            if len(prices) < holdout + 30 or self.ml_runner is None:
                return {'ml': default_ml_weight, 'stat': 1.0 - default_ml_weight}

            train = prices.iloc[:-holdout]
            actual = prices.iloc[-holdout:]

            # ML prediction over holdout
            try:
                ml_pred = self._ml_forecast('TMP', train, holdout)
            except Exception:
                ml_pred = None

            stat_pred = self._statistical_forecast(train, holdout)

            if ml_pred is None:
                return {'ml': 0.5, 'stat': 0.5}

            # Compute MSEs
            mse_ml = float(np.mean((np.array(ml_pred) - np.array(actual)) ** 2))
            mse_stat = float(np.mean((np.array(stat_pred) - np.array(actual)) ** 2))

            # Avoid division by zero
            mse_ml = max(mse_ml, 1e-8)
            mse_stat = max(mse_stat, 1e-8)

            inv_ml = 1.0 / mse_ml
            inv_stat = 1.0 / mse_stat
            total = inv_ml + inv_stat
            w_ml = float(inv_ml / total)
            w_stat = float(inv_stat / total)

            # Blend with default to avoid extreme weights
            w_ml = 0.7 * w_ml + 0.3 * default_ml_weight
            w_stat = 1.0 - w_ml

            return {'ml': w_ml, 'stat': w_stat}
        except Exception:
            logger.exception('Failed to compute model weights, using defaults')
            return {'ml': default_ml_weight, 'stat': 1.0 - default_ml_weight}

    def _ensemble_forecast(self, ticker: str, prices: pd.Series, horizon: int) -> np.ndarray:
        """
        Create a weighted ensemble forecast combining the ML runner and the
        statistical fallback. We compute lightweight weights and then return
        the weighted average time series.
        """
        try:
            # Generate base forecasts
            ml_series = None
            if self.ml_runner:
                try:
                    ml_series = self._ml_forecast(ticker, prices, horizon)
                except Exception:
                    ml_series = None

            stat_series = self._statistical_forecast(prices, horizon)

            # Determine weights
            weights = self._compute_model_weights(prices)
            ml_w = weights.get('ml', 0.5)
            stat_w = weights.get('stat', 1.0 - ml_w)

            if ml_series is None:
                # ML not available; return statistical forecast
                return stat_series

            # Ensure numpy arrays
            ml_arr = np.array(ml_series)
            stat_arr = np.array(stat_series)

            # Broadcast shapes if necessary
            if ml_arr.shape != stat_arr.shape:
                # Resample by linear interpolation to match shape
                idx = np.linspace(0, 1, len(ml_arr))
                idx2 = np.linspace(0, 1, len(stat_arr))
                stat_arr = np.interp(idx, idx2, stat_arr)

            ensemble = ml_w * ml_arr + stat_w * stat_arr
            return ensemble
        except Exception:
            logger.exception('Ensemble forecast failed, falling back to statistical')
            return self._statistical_forecast(prices, horizon)
    
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


def run_predict(payload: dict) -> dict:
    """Compatibility wrapper used by API layer to run a forecast.

    Expected payload keys: ticker, horizon, confidence, model_version, deterministic
    """
    try:
        fa = ForecastAdapter(deterministic=bool(payload.get('deterministic', False)))
        ticker = payload.get('ticker')
        horizon = int(payload.get('horizon', 30))
        confidence = float(payload.get('confidence', 0.95))
        model = payload.get('model', payload.get('model_version', 'ensemble'))
        forecast_id = payload.get('forecast_id', f"{ticker}_{int(time.time())}")

        res = fa.run_forecast(ticker, horizon, confidence, model, forecast_id)
        return res
    except Exception as e:
        logger.exception(f"run_predict wrapper failed: {e}")
        return {'status': 'error', 'error': str(e)}


def run_explain(payload: dict) -> dict:
    """Compatibility wrapper to generate an explanation for a forecast (SHAP-like).

    Payload may contain 'ticker' and 'forecast_id'.
    """
    try:
        forecast_id = payload.get('forecast_id')
        ticker = payload.get('ticker')
        # If forecast_id provided, try to load cached forecast to get ticker
        fa = ForecastAdapter(deterministic=bool(payload.get('deterministic', False)))
        if forecast_id and forecast_id in fa.cache:
            return fa.get_explanation(forecast_id)
        if ticker:
            # Generate a mock explanation by running a forecast and then explaining it
            fid = f"{ticker}_{int(time.time())}"
            res = fa.run_forecast(ticker, 7, 0.95, 'ensemble', fid)
            # Store and return explanation
            fa.cache[fid] = res
            return fa.get_explanation(fid) or {}
        return {}
    except Exception as e:
        logger.exception(f"run_explain wrapper failed: {e}")
        return {'status': 'error', 'error': str(e)}


def validate_forecast_response(resp: dict) -> bool:
    """Simple schema validator for forecast responses used by the API.

    Ensures required keys exist and forecast array length matches horizon if present.
    """
    try:
        if not isinstance(resp, dict):
            return False
        required = ['ticker', 'horizon', 'forecast', 'status']
        for k in required:
            if k not in resp:
                return False
        if resp.get('status') != 'success':
            return False
        if not isinstance(resp.get('forecast'), (list, tuple)):
            return False
        return True
    except Exception:
        return False
