"""
NeuralForecast Engine for Market Forecast Tab
==============================================

Integrates NBEATS and NHITS models from neuralforecast for deep learning-based
time series forecasting with confidence intervals.

Features:
- NBEATS (Neural Basis Expansion Analysis for Interpretable Time Series)
- NHITS (Neural Hierarchical Interpolation for Time Series)
- Model caching to avoid re-training on every click
- Fan chart visualization with multiple confidence intervals
- Model performance comparison (RMSE, MAE, MAPE)

Phase 4 Requirements:
- PORT=8051
- PHASE4_DETERMINISTIC=1
- Cache trained models to disk
"""

import logging
import os
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import hashlib
import json

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Neural forecast imports with graceful fallback
try:
    from neuralforecast import NeuralForecast
    from neuralforecast.models import NBEATS, NHITS
    from neuralforecast.losses.pytorch import MAE, MSE
    import torch
    NEURAL_AVAILABLE = True
    
    # Set deterministic mode for Phase 4
    if os.getenv('PHASE4_DETERMINISTIC', '0') == '1':
        torch.manual_seed(42)
        np.random.seed(42)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(42)
        logger.info("✅ Phase 4 deterministic mode enabled for PyTorch")
        
except ImportError as e:
    NEURAL_AVAILABLE = False
    logger.warning(f"NeuralForecast not available: {e}")


class DeepForecaster:
    """
    Deep Learning Forecaster using NBEATS and NHITS models.
    
    Implements intelligent caching to avoid re-training on identical data.
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the Deep Forecaster.
        
        Args:
            cache_dir: Directory to cache trained models (default: ./cache/neural_models)
        """
        if not NEURAL_AVAILABLE:
            raise ImportError("neuralforecast and torch must be installed for DeepForecaster")
        
        self.cache_dir = Path(cache_dir or './cache/neural_models')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.models_cache = {}
        self.last_train_params = {}
        
        logger.info(f"DeepForecaster initialized with cache at {self.cache_dir}")
    
    def _generate_cache_key(self, ticker: str, horizon: int, data_hash: str) -> str:
        """Generate unique cache key for model based on params and data."""
        key_str = f"{ticker}_{horizon}_{data_hash}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _hash_data(self, df: pd.DataFrame) -> str:
        """Generate hash of dataframe for cache validation."""
        # Use last 10 rows and shape to detect data changes
        data_repr = f"{df.shape}_{df.tail(10).to_json()}"
        return hashlib.md5(data_repr.encode()).hexdigest()[:16]
    
    def _load_cached_model(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Load cached model from disk if exists and valid."""
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'rb') as f:
                cached = pickle.load(f)
            
            # Validate cache freshness (24 hours)
            cache_age_hours = (datetime.now() - cached['timestamp']).total_seconds() / 3600
            if cache_age_hours > 24:
                logger.info(f"Cache expired for {cache_key} (age: {cache_age_hours:.1f}h)")
                return None
            
            logger.info(f"✅ Loaded cached model {cache_key} (age: {cache_age_hours:.1f}h)")
            return cached
            
        except Exception as e:
            logger.error(f"Failed to load cache {cache_key}: {e}")
            return None
    
    def _save_cached_model(self, cache_key: str, model_data: Dict[str, Any]):
        """Save trained model to disk cache."""
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        try:
            model_data['timestamp'] = datetime.now()
            with open(cache_file, 'wb') as f:
                pickle.dump(model_data, f)
            logger.info(f"✅ Cached model saved: {cache_key}")
        except Exception as e:
            logger.error(f"Failed to save cache {cache_key}: {e}")
    
    def prepare_data(self, df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """
        Prepare data in NeuralForecast format.
        
        Args:
            df: DataFrame with DatetimeIndex and 'Close' column
            ticker: Stock ticker symbol
        
        Returns:
            DataFrame with columns: unique_id, ds, y
        """
        if 'Close' not in df.columns:
            raise ValueError("DataFrame must contain 'Close' column")
        
        # NeuralForecast expects: unique_id, ds (datetime), y (target)
        prepared = pd.DataFrame({
            'unique_id': ticker,
            'ds': df.index,
            'y': df['Close'].values
        })
        
        # Remove any NaN values
        prepared = prepared.dropna()
        
        logger.info(f"Prepared {len(prepared)} data points for {ticker}")
        return prepared
    
    def forecast_nbeats(
        self,
        df: pd.DataFrame,
        ticker: str,
        horizon: int = 14,
        confidence_levels: List[int] = [80, 95],
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Generate forecast using NBEATS model.
        
        Args:
            df: Historical price data with DatetimeIndex and 'Close' column
            ticker: Stock ticker
            horizon: Forecast horizon in days
            confidence_levels: List of confidence levels (e.g., [80, 95])
            use_cache: Whether to use cached models
        
        Returns:
            Dict containing forecast, intervals, metrics, and metadata
        """
        try:
            # Prepare data
            data = self.prepare_data(df, ticker)
            data_hash = self._hash_data(df)
            cache_key = self._generate_cache_key(ticker, horizon, data_hash)
            
            # Check cache
            if use_cache:
                cached = self._load_cached_model(cache_key)
                if cached and cached.get('model') == 'nbeats':
                    logger.info("Using cached NBEATS forecast")
                    return cached['results']
            
            # Initialize NBEATS model
            # Smaller model for faster training (Phase 4 requirement)
            model = NBEATS(
                h=horizon,
                input_size=min(5 * horizon, len(data) - horizon),  # Lookback window
                max_steps=50,  # Reduced for speed
                scaler_type='robust',
                loss=MAE(),
                random_seed=42 if os.getenv('PHASE4_DETERMINISTIC') == '1' else None
            )
            
            # Train model
            logger.info(f"Training NBEATS model for {ticker} (horizon={horizon})...")
            train_start = datetime.now()
            
            nf = NeuralForecast(models=[model], freq='D')
            nf.fit(df=data)
            
            train_duration = (datetime.now() - train_start).total_seconds()
            logger.info(f"✅ NBEATS training complete ({train_duration:.2f}s)")
            
            # Generate forecast
            forecast_df = nf.predict()
            
            # Extract predictions
            predictions = forecast_df['NBEATS'].values
            
            # Generate confidence intervals (approximate using historical volatility)
            historical_returns = df['Close'].pct_change().dropna()
            volatility = historical_returns.std()
            
            intervals = {}
            for level in confidence_levels:
                z_score = {50: 0.67, 80: 1.28, 95: 1.96, 99: 2.58}.get(level, 1.96)
                expanding_std = volatility * np.sqrt(np.arange(1, horizon + 1))
                
                intervals[f'{level}_lower'] = predictions - (z_score * df['Close'].iloc[-1] * expanding_std)
                intervals[f'{level}_upper'] = predictions + (z_score * df['Close'].iloc[-1] * expanding_std)
            
            # Calculate metrics on validation set (last 20% of data)
            val_size = int(len(data) * 0.2)
            if val_size > 0:
                val_data = data.iloc[-val_size:]
                nf_val = NeuralForecast(models=[model], freq='D')
                nf_val.fit(df=data.iloc[:-val_size])
                val_forecast = nf_val.predict()
                
                rmse = np.sqrt(np.mean((val_data['y'].values - val_forecast['NBEATS'].values[:len(val_data)]) ** 2))
                mae = np.mean(np.abs(val_data['y'].values - val_forecast['NBEATS'].values[:len(val_data)]))
                mape = np.mean(np.abs((val_data['y'].values - val_forecast['NBEATS'].values[:len(val_data)]) / val_data['y'].values)) * 100
            else:
                rmse = mae = mape = 0.0
            
            # Build result
            last_date = df.index[-1]
            forecast_dates = pd.date_range(start=last_date + timedelta(days=1), periods=horizon, freq='D')
            
            result = {
                'model': 'NBEATS',
                'ticker': ticker,
                'horizon': horizon,
                'dates': forecast_dates.tolist(),
                'predictions': predictions.tolist(),
                'intervals': {k: v.tolist() for k, v in intervals.items()},
                'metrics': {
                    'rmse': float(rmse),
                    'mae': float(mae),
                    'mape': float(mape)
                },
                'metadata': {
                    'train_duration_s': train_duration,
                    'data_points': len(data),
                    'last_price': float(df['Close'].iloc[-1]),
                    'forecast_start': forecast_dates[0].isoformat(),
                    'forecast_end': forecast_dates[-1].isoformat()
                }
            }
            
            # Cache result
            if use_cache:
                self._save_cached_model(cache_key, {
                    'model': 'nbeats',
                    'results': result,
                    'timestamp': datetime.now()
                })
            
            return result
            
        except Exception as e:
            logger.error(f"NBEATS forecast failed: {e}", exc_info=True)
            raise
    
    def forecast_nhits(
        self,
        df: pd.DataFrame,
        ticker: str,
        horizon: int = 14,
        confidence_levels: List[int] = [80, 95],
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Generate forecast using NHITS model.
        
        Args:
            df: Historical price data
            ticker: Stock ticker
            horizon: Forecast horizon in days
            confidence_levels: Confidence levels for intervals
            use_cache: Whether to use cached models
        
        Returns:
            Dict containing forecast, intervals, metrics
        """
        try:
            # Prepare data
            data = self.prepare_data(df, ticker)
            data_hash = self._hash_data(df)
            cache_key = self._generate_cache_key(f"{ticker}_nhits", horizon, data_hash)
            
            # Check cache
            if use_cache:
                cached = self._load_cached_model(cache_key)
                if cached and cached.get('model') == 'nhits':
                    logger.info("Using cached NHITS forecast")
                    return cached['results']
            
            # Initialize NHITS model
            model = NHITS(
                h=horizon,
                input_size=min(5 * horizon, len(data) - horizon),
                max_steps=50,  # Reduced for speed
                scaler_type='robust',
                loss=MAE(),
                random_seed=42 if os.getenv('PHASE4_DETERMINISTIC') == '1' else None
            )
            
            # Train model
            logger.info(f"Training NHITS model for {ticker} (horizon={horizon})...")
            train_start = datetime.now()
            
            nf = NeuralForecast(models=[model], freq='D')
            nf.fit(df=data)
            
            train_duration = (datetime.now() - train_start).total_seconds()
            logger.info(f"✅ NHITS training complete ({train_duration:.2f}s)")
            
            # Generate forecast
            forecast_df = nf.predict()
            predictions = forecast_df['NHITS'].values
            
            # Generate confidence intervals
            historical_returns = df['Close'].pct_change().dropna()
            volatility = historical_returns.std()
            
            intervals = {}
            for level in confidence_levels:
                z_score = {50: 0.67, 80: 1.28, 95: 1.96, 99: 2.58}.get(level, 1.96)
                expanding_std = volatility * np.sqrt(np.arange(1, horizon + 1))
                
                intervals[f'{level}_lower'] = predictions - (z_score * df['Close'].iloc[-1] * expanding_std)
                intervals[f'{level}_upper'] = predictions + (z_score * df['Close'].iloc[-1] * expanding_std)
            
            # Calculate metrics
            val_size = int(len(data) * 0.2)
            if val_size > 0:
                val_data = data.iloc[-val_size:]
                nf_val = NeuralForecast(models=[model], freq='D')
                nf_val.fit(df=data.iloc[:-val_size])
                val_forecast = nf_val.predict()
                
                rmse = np.sqrt(np.mean((val_data['y'].values - val_forecast['NHITS'].values[:len(val_data)]) ** 2))
                mae = np.mean(np.abs(val_data['y'].values - val_forecast['NHITS'].values[:len(val_data)]))
                mape = np.mean(np.abs((val_data['y'].values - val_forecast['NHITS'].values[:len(val_data)]) / val_data['y'].values)) * 100
            else:
                rmse = mae = mape = 0.0
            
            # Build result
            last_date = df.index[-1]
            forecast_dates = pd.date_range(start=last_date + timedelta(days=1), periods=horizon, freq='D')
            
            result = {
                'model': 'NHITS',
                'ticker': ticker,
                'horizon': horizon,
                'dates': forecast_dates.tolist(),
                'predictions': predictions.tolist(),
                'intervals': {k: v.tolist() for k, v in intervals.items()},
                'metrics': {
                    'rmse': float(rmse),
                    'mae': float(mae),
                    'mape': float(mape)
                },
                'metadata': {
                    'train_duration_s': train_duration,
                    'data_points': len(data),
                    'last_price': float(df['Close'].iloc[-1]),
                    'forecast_start': forecast_dates[0].isoformat(),
                    'forecast_end': forecast_dates[-1].isoformat()
                }
            }
            
            # Cache result
            if use_cache:
                self._save_cached_model(cache_key, {
                    'model': 'nhits',
                    'results': result,
                    'timestamp': datetime.now()
                })
            
            return result
            
        except Exception as e:
            logger.error(f"NHITS forecast failed: {e}", exc_info=True)
            raise
    
    def forecast_ensemble(
        self,
        df: pd.DataFrame,
        ticker: str,
        horizon: int = 14,
        confidence_levels: List[int] = [80, 95]
    ) -> Dict[str, Any]:
        """
        Generate ensemble forecast by averaging NBEATS and NHITS predictions.
        
        Args:
            df: Historical price data
            ticker: Stock ticker
            horizon: Forecast horizon
            confidence_levels: Confidence levels
        
        Returns:
            Dict with ensemble forecast
        """
        try:
            # Get individual forecasts
            nbeats_result = self.forecast_nbeats(df, ticker, horizon, confidence_levels)
            nhits_result = self.forecast_nhits(df, ticker, horizon, confidence_levels)
            
            # Average predictions
            nbeats_pred = np.array(nbeats_result['predictions'])
            nhits_pred = np.array(nhits_result['predictions'])
            ensemble_pred = (nbeats_pred + nhits_pred) / 2
            
            # Average confidence intervals
            intervals = {}
            for key in nbeats_result['intervals']:
                nbeats_int = np.array(nbeats_result['intervals'][key])
                nhits_int = np.array(nhits_result['intervals'][key])
                intervals[key] = ((nbeats_int + nhits_int) / 2).tolist()
            
            # Average metrics
            metrics = {
                'rmse': (nbeats_result['metrics']['rmse'] + nhits_result['metrics']['rmse']) / 2,
                'mae': (nbeats_result['metrics']['mae'] + nhits_result['metrics']['mae']) / 2,
                'mape': (nbeats_result['metrics']['mape'] + nhits_result['metrics']['mape']) / 2
            }
            
            result = {
                'model': 'Neural Ensemble (NBEATS + NHITS)',
                'ticker': ticker,
                'horizon': horizon,
                'dates': nbeats_result['dates'],
                'predictions': ensemble_pred.tolist(),
                'intervals': intervals,
                'metrics': metrics,
                'metadata': {
                    'components': ['NBEATS', 'NHITS'],
                    'data_points': nbeats_result['metadata']['data_points'],
                    'last_price': nbeats_result['metadata']['last_price'],
                    'forecast_start': nbeats_result['metadata']['forecast_start'],
                    'forecast_end': nbeats_result['metadata']['forecast_end']
                }
            }
            
            logger.info(f"✅ Ensemble forecast complete for {ticker}")
            return result
            
        except Exception as e:
            logger.error(f"Ensemble forecast failed: {e}", exc_info=True)
            raise


def is_neural_available() -> bool:
    """Check if NeuralForecast is available."""
    return NEURAL_AVAILABLE


def get_neural_models_list() -> List[str]:
    """Get list of available neural models."""
    if not NEURAL_AVAILABLE:
        return []
    return ['nbeats', 'nhits', 'neural_ensemble']
