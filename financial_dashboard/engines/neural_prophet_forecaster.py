#!/usr/bin/env python3
"""
NeuralProphet Forecaster
========================
Time series forecasting with trend, seasonality, and neural components.

Inspired by: https://github.com/ourownstory/neural_prophet

Implements:
- Trend decomposition (linear, logistic)
- Multiple seasonality (daily, weekly, yearly)
- Auto-regression with neural network
- External regressors
- Uncertainty quantification
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class TrendComponent:
    """Trend decomposition result"""
    values: np.ndarray
    changepoints: List[datetime]
    growth_rate: float
    trend_type: str  # 'linear', 'logistic', 'flat'


@dataclass
class SeasonalityComponent:
    """Seasonality decomposition result"""
    name: str
    period: float
    fourier_order: int
    values: np.ndarray
    strength: float


@dataclass
class ForecastResult:
    """Complete forecast result"""
    dates: List[datetime]
    yhat: np.ndarray  # Point forecast
    yhat_lower: np.ndarray  # Lower confidence bound
    yhat_upper: np.ndarray  # Upper confidence bound
    trend: TrendComponent
    seasonalities: List[SeasonalityComponent]
    residuals: np.ndarray
    metrics: Dict[str, float]
    
    def to_dict(self) -> Dict:
        return {
            'dates': [d.isoformat() if isinstance(d, datetime) else str(d) for d in self.dates],
            'forecast': self.yhat.tolist(),
            'lower': self.yhat_lower.tolist(),
            'upper': self.yhat_upper.tolist(),
            'trend': {
                'values': self.trend.values.tolist(),
                'growth_rate': self.trend.growth_rate,
                'type': self.trend.trend_type
            },
            'seasonalities': [
                {
                    'name': s.name,
                    'period': s.period,
                    'strength': s.strength
                }
                for s in self.seasonalities
            ],
            'metrics': self.metrics
        }


class NeuralProphetForecaster:
    """
    NeuralProphet-style time series forecaster.
    
    Combines:
    - Facebook Prophet's decomposable model
    - Neural network auto-regression (AR-Net)
    - Lagged regressors
    - Uncertainty intervals
    
    Falls back to statistical methods when neural_prophet not available.
    """
    
    def __init__(self,
                 growth: str = 'linear',
                 seasonality_mode: str = 'additive',
                 yearly_seasonality: bool = True,
                 weekly_seasonality: bool = True,
                 daily_seasonality: bool = False,
                 n_lags: int = 5,
                 n_forecasts: int = 5,
                 ar_layers: List[int] = None,
                 learning_rate: float = 0.1,
                 epochs: int = 100,
                 quantiles: List[float] = None):
        """
        Args:
            growth: 'linear', 'logistic', or 'flat'
            seasonality_mode: 'additive' or 'multiplicative'
            yearly_seasonality: Include yearly seasonality
            weekly_seasonality: Include weekly seasonality  
            daily_seasonality: Include daily seasonality
            n_lags: Number of lags for AR
            n_forecasts: Forecast horizon
            ar_layers: Hidden layer sizes for AR-Net
            learning_rate: Learning rate
            epochs: Training epochs
            quantiles: Quantiles for uncertainty (e.g., [0.05, 0.5, 0.95])
        """
        self.growth = growth
        self.seasonality_mode = seasonality_mode
        self.yearly_seasonality = yearly_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.daily_seasonality = daily_seasonality
        self.n_lags = n_lags
        self.n_forecasts = n_forecasts
        self.ar_layers = ar_layers or [32]
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.quantiles = quantiles or [0.1, 0.5, 0.9]
        
        self._model = None
        self._fitted = False
        self._neural_prophet_available = False
        self._history_df = None
        self._trend_params = {}
        self._seasonal_params = {}
        
    def initialize(self) -> bool:
        """Initialize and check for neural_prophet"""
        try:
            from neuralprophet import NeuralProphet
            self._neural_prophet_available = True
            logger.info("✅ NeuralProphet available")
        except ImportError:
            self._neural_prophet_available = False
            logger.warning("NeuralProphet not available - using statistical fallback")
        
        return True
    
    def _fourier_series(self, 
                        t: np.ndarray, 
                        period: float, 
                        order: int) -> np.ndarray:
        """Generate Fourier series for seasonality"""
        features = []
        for i in range(1, order + 1):
            features.append(np.sin(2 * np.pi * i * t / period))
            features.append(np.cos(2 * np.pi * i * t / period))
        return np.column_stack(features)
    
    def _fit_trend(self, 
                   t: np.ndarray, 
                   y: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """Fit trend component"""
        if self.growth == 'flat':
            trend = np.full_like(y, np.mean(y))
            params = {'m': float(np.mean(y)), 'k': 0}
            
        elif self.growth == 'logistic':
            # Logistic growth
            cap = np.max(y) * 1.2
            y_scaled = y / cap
            # Simple logistic fit
            k = 1.0  # Growth rate
            m = float(np.mean(y_scaled))
            trend = cap / (1 + np.exp(-k * (t - len(t)//2)))
            params = {'cap': cap, 'k': k, 'm': m}
            
        else:  # linear
            # Linear regression
            t_scaled = (t - t.min()) / (t.max() - t.min() + 1e-10)
            A = np.column_stack([np.ones_like(t_scaled), t_scaled])
            coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            trend = A @ coef
            params = {'m': float(coef[0]), 'k': float(coef[1])}
        
        return trend, params
    
    def _fit_seasonality(self,
                         t: np.ndarray,
                         residuals: np.ndarray,
                         period: float,
                         order: int,
                         name: str) -> SeasonalityComponent:
        """Fit seasonality component"""
        # Generate Fourier features
        X = self._fourier_series(t, period, order)
        
        # Fit coefficients
        coef, _, _, _ = np.linalg.lstsq(X, residuals, rcond=None)
        
        # Calculate seasonal values
        seasonal = X @ coef
        
        # Strength = variance explained
        strength = 1 - np.var(residuals - seasonal) / (np.var(residuals) + 1e-10)
        
        return SeasonalityComponent(
            name=name,
            period=period,
            fourier_order=order,
            values=seasonal,
            strength=float(max(0, strength))
        )
    
    def fit(self, df: pd.DataFrame, target_col: str = 'y') -> 'NeuralProphetForecaster':
        """
        Fit the forecaster.
        
        Args:
            df: DataFrame with 'ds' (datetime) and target column
            target_col: Name of target column
            
        Returns:
            self
        """
        self.initialize()
        
        # Prepare data
        if 'ds' not in df.columns:
            if 'date' in df.columns:
                df = df.rename(columns={'date': 'ds'})
            elif isinstance(df.index, pd.DatetimeIndex):
                df = df.reset_index().rename(columns={df.index.name or 'index': 'ds'})
        
        if target_col not in df.columns:
            # Try common column names
            for col in ['close', 'Close', 'value', 'y']:
                if col in df.columns:
                    target_col = col
                    break
        
        self._history_df = df.copy()
        
        if self._neural_prophet_available:
            try:
                from neuralprophet import NeuralProphet
                
                # Prepare for NeuralProphet format
                train_df = df[['ds', target_col]].copy()
                train_df = train_df.rename(columns={target_col: 'y'})
                train_df['ds'] = pd.to_datetime(train_df['ds'])
                
                # Create model
                self._model = NeuralProphet(
                    growth=self.growth,
                    seasonality_mode=self.seasonality_mode,
                    yearly_seasonality=self.yearly_seasonality,
                    weekly_seasonality=self.weekly_seasonality,
                    daily_seasonality=self.daily_seasonality,
                    n_lags=self.n_lags,
                    n_forecasts=self.n_forecasts,
                    learning_rate=self.learning_rate,
                    epochs=self.epochs
                )
                
                self._model.fit(train_df, freq='D')
                self._fitted = True
                return self
                
            except Exception as e:
                logger.warning(f"NeuralProphet fitting failed: {e}, using fallback")
        
        # Statistical fallback
        y = df[target_col].values
        t = np.arange(len(y))
        
        # Fit trend
        trend, self._trend_params = self._fit_trend(t, y)
        residuals = y - trend
        
        # Fit seasonalities
        self._seasonal_params = {}
        
        if self.yearly_seasonality and len(y) >= 365:
            yearly = self._fit_seasonality(t, residuals, 365.25, 10, 'yearly')
            self._seasonal_params['yearly'] = yearly
            residuals = residuals - yearly.values
        
        if self.weekly_seasonality and len(y) >= 14:
            weekly = self._fit_seasonality(t, residuals, 7, 3, 'weekly')
            self._seasonal_params['weekly'] = weekly
            residuals = residuals - weekly.values
        
        if self.daily_seasonality:
            daily = self._fit_seasonality(t, residuals, 1, 4, 'daily')
            self._seasonal_params['daily'] = daily
        
        # Fit AR model on residuals
        self._ar_coeffs = self._fit_ar(residuals, self.n_lags)
        
        self._fitted = True
        return self
    
    def _fit_ar(self, y: np.ndarray, lags: int) -> np.ndarray:
        """Fit simple AR model"""
        if len(y) <= lags + 1:
            return np.zeros(lags)
            
        # Build lagged features
        X = []
        Y = []
        for i in range(lags, len(y)):
            X.append(y[i-lags:i][::-1])
            Y.append(y[i])
        
        X = np.array(X)
        Y = np.array(Y)
        
        # Fit
        coef, _, _, _ = np.linalg.lstsq(X, Y, rcond=None)
        return coef
    
    def predict(self, periods: int = None) -> ForecastResult:
        """
        Generate forecast.
        
        Args:
            periods: Number of periods to forecast
            
        Returns:
            ForecastResult with predictions and components
        """
        if not self._fitted:
            raise ValueError("Model not fitted. Call fit() first.")
        
        periods = periods or self.n_forecasts
        
        if self._neural_prophet_available and self._model is not None:
            try:
                future = self._model.make_future_dataframe(
                    self._history_df, 
                    periods=periods
                )
                forecast = self._model.predict(future)
                
                # Extract results
                yhat = forecast['yhat'].values[-periods:]
                
                # Uncertainty - approximate
                std = np.std(self._history_df[['close', 'Close', 'y']].iloc[:, 0].pct_change().dropna()) * \
                      self._history_df[['close', 'Close', 'y']].iloc[:, 0].iloc[-1]
                
                return ForecastResult(
                    dates=list(forecast['ds'].iloc[-periods:]),
                    yhat=yhat,
                    yhat_lower=yhat - 1.96 * std * np.sqrt(np.arange(1, periods + 1)),
                    yhat_upper=yhat + 1.96 * std * np.sqrt(np.arange(1, periods + 1)),
                    trend=TrendComponent(
                        values=forecast.get('trend', yhat)[-periods:].values if 'trend' in forecast else yhat,
                        changepoints=[],
                        growth_rate=0,
                        trend_type=self.growth
                    ),
                    seasonalities=[],
                    residuals=np.zeros(periods),
                    metrics={'method': 'neuralprophet'}
                )
            except Exception as e:
                logger.warning(f"NeuralProphet prediction failed: {e}")
        
        # Statistical fallback
        return self._predict_statistical(periods)
    
    def _predict_statistical(self, periods: int) -> ForecastResult:
        """Statistical prediction fallback"""
        # Get historical data
        history = self._history_df
        for col in ['close', 'Close', 'y', 'value']:
            if col in history.columns:
                y_hist = history[col].values
                break
        else:
            y_hist = history.iloc[:, -1].values
        
        n = len(y_hist)
        t_future = np.arange(n, n + periods)
        
        # Extend trend
        if self.growth == 'linear':
            m = self._trend_params.get('m', y_hist.mean())
            k = self._trend_params.get('k', 0)
            t_scaled = (t_future - 0) / (n + periods)
            trend = m + k * t_scaled
        else:
            trend = np.full(periods, y_hist[-1])
        
        # Extend seasonalities
        seasonal = np.zeros(periods)
        seasonalities = []
        
        for name, comp in self._seasonal_params.items():
            if len(comp.values) > 0:
                # Extrapolate seasonal pattern
                X = self._fourier_series(t_future, comp.period, comp.fourier_order)
                # Fit coefficients from history
                t_hist = np.arange(n)
                X_hist = self._fourier_series(t_hist, comp.period, comp.fourier_order)
                coef, _, _, _ = np.linalg.lstsq(X_hist, comp.values, rcond=None)
                s = X @ coef
                seasonal += s
                seasonalities.append(SeasonalityComponent(
                    name=name,
                    period=comp.period,
                    fourier_order=comp.fourier_order,
                    values=s,
                    strength=comp.strength
                ))
        
        # AR component
        ar_pred = []
        recent = list(y_hist[-self.n_lags:])
        for _ in range(periods):
            if len(self._ar_coeffs) > 0:
                pred = np.dot(self._ar_coeffs, recent[-self.n_lags:][::-1])
            else:
                pred = 0
            ar_pred.append(pred)
            recent.append(pred)
        ar_pred = np.array(ar_pred)
        
        # Combine
        if self.seasonality_mode == 'multiplicative':
            yhat = trend * (1 + seasonal) + ar_pred
        else:
            yhat = trend + seasonal + ar_pred
        
        # Uncertainty
        residuals_hist = y_hist - (self._trend_params.get('m', y_hist.mean()) + 
                                   self._trend_params.get('k', 0) * np.arange(n) / n)
        sigma = np.std(residuals_hist)
        
        # Widen uncertainty with horizon
        uncertainty = sigma * np.sqrt(np.arange(1, periods + 1))
        
        # Quantile-based bounds
        q_low = self.quantiles[0]
        q_high = self.quantiles[-1]
        from scipy.stats import norm
        z_low = norm.ppf(q_low)
        z_high = norm.ppf(q_high)
        
        yhat_lower = yhat + z_low * uncertainty
        yhat_upper = yhat + z_high * uncertainty
        
        # Generate dates
        last_date = pd.to_datetime(history['ds'].iloc[-1]) if 'ds' in history.columns else datetime.now()
        dates = [last_date + timedelta(days=i+1) for i in range(periods)]
        
        return ForecastResult(
            dates=dates,
            yhat=yhat,
            yhat_lower=yhat_lower,
            yhat_upper=yhat_upper,
            trend=TrendComponent(
                values=trend,
                changepoints=[],
                growth_rate=float(self._trend_params.get('k', 0)),
                trend_type=self.growth
            ),
            seasonalities=seasonalities,
            residuals=np.zeros(periods),
            metrics={
                'method': 'statistical_fallback',
                'n_lags': self.n_lags,
                'sigma': float(sigma)
            }
        )
    
    def cross_validate(self, 
                       df: pd.DataFrame,
                       initial: int = 180,
                       horizon: int = 30,
                       period: int = 30) -> Dict[str, float]:
        """
        Time-series cross-validation.
        
        Args:
            df: Data
            initial: Initial training period
            horizon: Forecast horizon
            period: Period between cutoffs
            
        Returns:
            Dict with error metrics
        """
        for col in ['close', 'Close', 'y', 'value']:
            if col in df.columns:
                y = df[col].values
                break
        else:
            y = df.iloc[:, -1].values
        
        n = len(y)
        maes = []
        rmses = []
        
        cutoff = initial
        while cutoff + horizon <= n:
            # Train
            train_df = df.iloc[:cutoff].copy()
            self.fit(train_df)
            
            # Predict
            result = self.predict(horizon)
            
            # Actual
            actual = y[cutoff:cutoff + horizon]
            
            # Metrics
            mae = np.mean(np.abs(result.yhat - actual))
            rmse = np.sqrt(np.mean((result.yhat - actual) ** 2))
            
            maes.append(mae)
            rmses.append(rmse)
            
            cutoff += period
        
        return {
            'mae': float(np.mean(maes)),
            'rmse': float(np.mean(rmses)),
            'n_folds': len(maes)
        }
    
    def decompose(self, df: pd.DataFrame = None) -> Dict[str, np.ndarray]:
        """
        Decompose time series into components.
        
        Returns:
            Dict with trend, seasonality, residual
        """
        if df is None:
            df = self._history_df
            
        if not self._fitted:
            self.fit(df)
        
        for col in ['close', 'Close', 'y', 'value']:
            if col in df.columns:
                y = df[col].values
                break
        else:
            y = df.iloc[:, -1].values
        
        n = len(y)
        t = np.arange(n)
        
        # Trend
        trend, _ = self._fit_trend(t, y)
        
        # Seasonality
        residuals = y - trend
        seasonal = np.zeros(n)
        
        for name, comp in self._seasonal_params.items():
            if len(comp.values) == n:
                seasonal += comp.values
        
        # Residual
        residual = y - trend - seasonal
        
        return {
            'observed': y,
            'trend': trend,
            'seasonal': seasonal,
            'residual': residual
        }
    
    def get_summary(self) -> Dict:
        """Get model summary"""
        return {
            'growth': self.growth,
            'seasonality_mode': self.seasonality_mode,
            'seasonalities': {
                'yearly': self.yearly_seasonality,
                'weekly': self.weekly_seasonality,
                'daily': self.daily_seasonality
            },
            'n_lags': self.n_lags,
            'n_forecasts': self.n_forecasts,
            'fitted': self._fitted,
            'neural_prophet_available': self._neural_prophet_available
        }
