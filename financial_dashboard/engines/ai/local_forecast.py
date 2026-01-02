"""
Local Forecast Engine - Phase 2: Real Math-Based Forecasting
=============================================================
No external AI APIs - uses numpy/pandas time-series analysis.

Models:
1. Price Forecast: EMA Crossover + Linear Regression slope projection
2. Volatility Forecast: Historical Volatility (HV) cone with Parkinson's range estimator
3. Direction Signal: Combined momentum indicators

Focus Assets: NVDA, TSLA, SPY, GLD, SLV
"""

import os
import sys
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

import numpy as np
import pandas as pd

# Optional: scipy for advanced stats
try:
    from scipy import stats
    from scipy.signal import savgol_filter
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# Add parent path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS & DATA CLASSES
# =============================================================================

class TrendDirection(Enum):
    """Market trend direction."""
    BULLISH = "Bullish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"
    STRONGLY_BULLISH = "Strongly Bullish"
    STRONGLY_BEARISH = "Strongly Bearish"


class VolatilityRegime(Enum):
    """Volatility regime classification."""
    LOW = "Low"
    NORMAL = "Normal"
    HIGH = "High"
    EXTREME = "Extreme"


@dataclass
class ForecastResult:
    """Result from price forecast."""
    symbol: str
    current_price: float
    
    # 5-day price forecast
    price_path: List[float]        # Projected prices [day1, day2, ..., day5]
    upper_bound: List[float]       # Upper confidence band
    lower_bound: List[float]       # Lower confidence band
    
    # Direction & confidence
    direction: TrendDirection
    confidence: float              # 0-1 confidence in forecast
    
    # Technical signals
    ema_signal: str                # 'Bullish', 'Bearish', 'Neutral'
    regression_slope: float        # Daily slope from linear regression
    momentum_score: float          # -1 to 1 momentum indicator
    
    # Metadata
    forecast_days: int = 5
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'symbol': self.symbol,
            'current_price': round(self.current_price, 2),
            'price_path': [round(p, 2) for p in self.price_path],
            'upper_bound': [round(p, 2) for p in self.upper_bound],
            'lower_bound': [round(p, 2) for p in self.lower_bound],
            'direction': self.direction.value,
            'confidence': round(self.confidence, 2),
            'ema_signal': self.ema_signal,
            'regression_slope': round(self.regression_slope, 4),
            'momentum_score': round(self.momentum_score, 2),
            'forecast_days': self.forecast_days,
            'timestamp': self.timestamp.isoformat()
        }
    
    @property
    def expected_return(self) -> float:
        """Expected 5-day return."""
        if self.price_path:
            return (self.price_path[-1] - self.current_price) / self.current_price
        return 0.0
    
    @property
    def is_bullish(self) -> bool:
        return self.direction in (TrendDirection.BULLISH, TrendDirection.STRONGLY_BULLISH)
    
    @property
    def is_bearish(self) -> bool:
        return self.direction in (TrendDirection.BEARISH, TrendDirection.STRONGLY_BEARISH)


@dataclass
class VolatilityForecast:
    """Result from volatility forecast."""
    symbol: str
    current_hv: float              # Current historical volatility (annualized)
    
    # Volatility cone projections
    hv_forecast: List[float]       # Projected HV [day1, ..., day5]
    hv_upper: List[float]          # Upper HV cone
    hv_lower: List[float]          # Lower HV cone
    
    # Regime classification
    regime: VolatilityRegime
    percentile: float              # Current HV percentile (0-100)
    
    # IV vs HV comparison (if IV provided)
    iv_premium: Optional[float] = None  # IV - HV spread
    
    # Parkinson's estimator
    parkinson_vol: float = 0.0
    
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'symbol': self.symbol,
            'current_hv': round(self.current_hv * 100, 2),  # As percentage
            'hv_forecast': [round(h * 100, 2) for h in self.hv_forecast],
            'hv_upper': [round(h * 100, 2) for h in self.hv_upper],
            'hv_lower': [round(h * 100, 2) for h in self.hv_lower],
            'regime': self.regime.value,
            'percentile': round(self.percentile, 1),
            'iv_premium': round(self.iv_premium * 100, 2) if self.iv_premium else None,
            'parkinson_vol': round(self.parkinson_vol * 100, 2),
            'timestamp': self.timestamp.isoformat()
        }


# =============================================================================
# LOCAL FORECAST ENGINE
# =============================================================================

class LocalForecastEngine:
    """
    Local forecasting engine using real mathematical models.
    
    No external API calls - all calculations done locally with numpy/pandas.
    
    Models:
    - Price: EMA Crossover (9/21) + Linear Regression (20-day slope)
    - Volatility: Historical Volatility with Parkinson's range estimator
    - Direction: Composite momentum signal
    
    Usage:
        engine = LocalForecastEngine()
        
        # From DataFrame
        forecast = engine.generate_forecast('NVDA', history_df)
        print(f"5-day forecast: {forecast.price_path}")
        
        # Volatility forecast
        vol = engine.forecast_volatility('NVDA', history_df)
        print(f"HV Regime: {vol.regime.value}")
    """
    
    # EMA periods for crossover signal
    EMA_FAST = 9
    EMA_SLOW = 21
    
    # Linear regression lookback
    REGRESSION_PERIOD = 20
    
    # Volatility calculation periods
    HV_PERIOD = 20      # For historical volatility
    HV_LONG = 60        # For percentile calculation
    
    # Annualization factor
    TRADING_DAYS = 252
    
    def __init__(self):
        """Initialize the forecast engine."""
        logger.info("🧠 LocalForecastEngine initialized (Phase 2)")
    
    def generate_forecast(self, symbol: str, history_df: pd.DataFrame,
                         forecast_days: int = 5) -> ForecastResult:
        """
        Generate price forecast using EMA crossover + Linear Regression.
        
        Args:
            symbol: Ticker symbol
            history_df: DataFrame with 'Close', 'High', 'Low', 'Volume' columns
            forecast_days: Number of days to forecast (default 5)
            
        Returns:
            ForecastResult with price path and confidence bands
        """
        # Validate input
        if history_df is None or len(history_df) < 30:
            return self._create_neutral_forecast(symbol, 100.0, forecast_days)
        
        # Ensure we have the right columns
        df = self._prepare_dataframe(history_df)
        if df is None:
            return self._create_neutral_forecast(symbol, 100.0, forecast_days)
        
        close = df['Close'].values
        current_price = close[-1]
        
        # Calculate technical indicators
        ema_fast = self._calculate_ema(close, self.EMA_FAST)
        ema_slow = self._calculate_ema(close, self.EMA_SLOW)
        
        # EMA crossover signal
        ema_signal = self._get_ema_signal(ema_fast, ema_slow)
        
        # Linear regression slope
        slope, r_squared = self._calculate_regression_slope(close)
        
        # Momentum score (-1 to 1)
        momentum = self._calculate_momentum(close, ema_fast, ema_slow, slope)
        
        # Generate price path
        price_path = self._project_prices(current_price, slope, momentum, forecast_days)
        
        # Calculate confidence bands using historical volatility
        hv = self._calculate_hv(close, self.HV_PERIOD)
        daily_std = current_price * hv / np.sqrt(self.TRADING_DAYS)
        
        upper_bound = []
        lower_bound = []
        for i, price in enumerate(price_path):
            # Expand bands with time (sqrt of time)
            band_width = daily_std * np.sqrt(i + 1) * 1.5
            upper_bound.append(price + band_width)
            lower_bound.append(price - band_width)
        
        # Determine direction
        direction = self._determine_direction(momentum, ema_signal, slope)
        
        # Calculate confidence
        confidence = self._calculate_confidence(r_squared, ema_signal, momentum)
        
        return ForecastResult(
            symbol=symbol,
            current_price=current_price,
            price_path=price_path,
            upper_bound=upper_bound,
            lower_bound=lower_bound,
            direction=direction,
            confidence=confidence,
            ema_signal=ema_signal,
            regression_slope=slope,
            momentum_score=momentum,
            forecast_days=forecast_days
        )
    
    def forecast_volatility(self, symbol: str, history_df: pd.DataFrame,
                           current_iv: Optional[float] = None) -> VolatilityForecast:
        """
        Forecast volatility using Historical Volatility cone.
        
        Args:
            symbol: Ticker symbol
            history_df: DataFrame with OHLCV data
            current_iv: Optional current implied volatility for IV premium calc
            
        Returns:
            VolatilityForecast with HV cone and regime classification
        """
        df = self._prepare_dataframe(history_df)
        if df is None or len(df) < self.HV_LONG:
            return self._create_neutral_volatility(symbol)
        
        close = df['Close'].values
        high = df['High'].values if 'High' in df.columns else close
        low = df['Low'].values if 'Low' in df.columns else close
        
        # Current HV
        current_hv = self._calculate_hv(close, self.HV_PERIOD)
        
        # Parkinson's volatility (uses High-Low range)
        parkinson_vol = self._calculate_parkinson_vol(high, low, self.HV_PERIOD)
        
        # HV percentile over longer period
        hv_series = self._rolling_hv(close, self.HV_PERIOD)
        percentile = self._calculate_percentile(current_hv, hv_series)
        
        # Classify regime
        regime = self._classify_vol_regime(percentile)
        
        # Project HV cone (mean-reverting model)
        hv_forecast, hv_upper, hv_lower = self._project_hv_cone(
            current_hv, hv_series, forecast_days=5
        )
        
        # IV premium if IV provided
        iv_premium = None
        if current_iv is not None:
            iv_premium = current_iv - current_hv
        
        return VolatilityForecast(
            symbol=symbol,
            current_hv=current_hv,
            hv_forecast=hv_forecast,
            hv_upper=hv_upper,
            hv_lower=hv_lower,
            regime=regime,
            percentile=percentile,
            iv_premium=iv_premium,
            parkinson_vol=parkinson_vol
        )
    
    # =========================================================================
    # TECHNICAL INDICATORS
    # =========================================================================
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return prices
        
        alpha = 2 / (period + 1)
        ema = np.zeros_like(prices, dtype=float)
        ema[0] = prices[0]
        
        for i in range(1, len(prices)):
            ema[i] = alpha * prices[i] + (1 - alpha) * ema[i - 1]
        
        return ema
    
    def _get_ema_signal(self, ema_fast: np.ndarray, ema_slow: np.ndarray) -> str:
        """Get EMA crossover signal from last values."""
        if len(ema_fast) < 2 or len(ema_slow) < 2:
            return 'Neutral'
        
        # Current state
        fast_above = ema_fast[-1] > ema_slow[-1]
        prev_fast_above = ema_fast[-2] > ema_slow[-2]
        
        # Recent crossover
        if fast_above and not prev_fast_above:
            return 'Bullish'  # Golden cross
        elif not fast_above and prev_fast_above:
            return 'Bearish'  # Death cross
        elif fast_above:
            return 'Bullish'
        else:
            return 'Bearish'
    
    def _calculate_regression_slope(self, prices: np.ndarray) -> Tuple[float, float]:
        """
        Calculate linear regression slope and R-squared.
        
        Returns:
            (slope, r_squared) - slope in price units per day
        """
        n = min(len(prices), self.REGRESSION_PERIOD)
        if n < 5:
            return 0.0, 0.0
        
        y = prices[-n:]
        x = np.arange(n)
        
        # Simple linear regression
        x_mean = x.mean()
        y_mean = y.mean()
        
        numerator = np.sum((x - x_mean) * (y - y_mean))
        denominator = np.sum((x - x_mean) ** 2)
        
        if denominator == 0:
            return 0.0, 0.0
        
        slope = numerator / denominator
        
        # R-squared
        y_pred = slope * x + (y_mean - slope * x_mean)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - y_mean) ** 2)
        
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        return slope, max(0, r_squared)
    
    def _calculate_momentum(self, prices: np.ndarray, 
                           ema_fast: np.ndarray, ema_slow: np.ndarray,
                           slope: float) -> float:
        """
        Calculate composite momentum score (-1 to 1).
        
        Combines:
        - EMA spread (fast - slow)
        - Price vs EMA position
        - Regression slope direction
        """
        if len(prices) < 5:
            return 0.0
        
        current_price = prices[-1]
        
        # EMA spread normalized
        ema_spread = (ema_fast[-1] - ema_slow[-1]) / ema_slow[-1]
        ema_score = np.tanh(ema_spread * 20)  # Scale and bound to (-1, 1)
        
        # Price position vs slow EMA
        price_vs_ema = (current_price - ema_slow[-1]) / ema_slow[-1]
        position_score = np.tanh(price_vs_ema * 10)
        
        # Slope direction
        avg_price = np.mean(prices[-20:]) if len(prices) >= 20 else np.mean(prices)
        slope_normalized = slope / avg_price * 100  # As percentage per day
        slope_score = np.tanh(slope_normalized * 5)
        
        # Weighted combination
        momentum = 0.4 * ema_score + 0.3 * position_score + 0.3 * slope_score
        
        return float(np.clip(momentum, -1, 1))
    
    # =========================================================================
    # VOLATILITY CALCULATIONS
    # =========================================================================
    
    def _calculate_hv(self, prices: np.ndarray, period: int) -> float:
        """Calculate annualized historical volatility (standard deviation of returns)."""
        if len(prices) < period + 1:
            period = len(prices) - 1
        if period < 2:
            return 0.2  # Default 20% vol
        
        returns = np.diff(np.log(prices[-period-1:]))
        daily_vol = np.std(returns, ddof=1)
        annual_vol = daily_vol * np.sqrt(self.TRADING_DAYS)
        
        return float(annual_vol)
    
    def _calculate_parkinson_vol(self, high: np.ndarray, low: np.ndarray, 
                                 period: int) -> float:
        """
        Calculate Parkinson's volatility estimator (uses High-Low range).
        More efficient than close-to-close volatility.
        """
        if len(high) < period or len(low) < period:
            return 0.2
        
        h = high[-period:]
        l = low[-period:]
        
        # Parkinson's formula
        log_hl = np.log(h / l)
        parkinson = np.sqrt(np.sum(log_hl ** 2) / (4 * period * np.log(2)))
        annual_parkinson = parkinson * np.sqrt(self.TRADING_DAYS)
        
        return float(annual_parkinson)
    
    def _rolling_hv(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate rolling historical volatility series."""
        if len(prices) < period + 1:
            return np.array([0.2])
        
        returns = np.diff(np.log(prices))
        hv_series = []
        
        for i in range(period, len(returns) + 1):
            window_returns = returns[i-period:i]
            vol = np.std(window_returns, ddof=1) * np.sqrt(self.TRADING_DAYS)
            hv_series.append(vol)
        
        return np.array(hv_series)
    
    def _calculate_percentile(self, current_val: float, history: np.ndarray) -> float:
        """Calculate percentile rank of current value in history."""
        if len(history) == 0:
            return 50.0
        
        below = np.sum(history < current_val)
        percentile = (below / len(history)) * 100
        
        return float(percentile)
    
    def _classify_vol_regime(self, percentile: float) -> VolatilityRegime:
        """Classify volatility regime based on percentile."""
        if percentile < 20:
            return VolatilityRegime.LOW
        elif percentile < 50:
            return VolatilityRegime.NORMAL
        elif percentile < 80:
            return VolatilityRegime.HIGH
        else:
            return VolatilityRegime.EXTREME
    
    def _project_hv_cone(self, current_hv: float, hv_history: np.ndarray,
                        forecast_days: int = 5) -> Tuple[List[float], List[float], List[float]]:
        """
        Project HV cone using mean-reverting model.
        
        Returns:
            (forecast, upper, lower) - each a list of forecast_days values
        """
        if len(hv_history) < 10:
            mean_hv = 0.25  # Default 25%
            std_hv = 0.05
        else:
            mean_hv = np.mean(hv_history)
            std_hv = np.std(hv_history)
        
        # Mean reversion speed
        kappa = 0.1  # Revert ~10% of gap per day
        
        forecast = []
        upper = []
        lower = []
        
        hv = current_hv
        for day in range(forecast_days):
            # Mean-reverting step
            hv = hv + kappa * (mean_hv - hv)
            
            # Uncertainty increases with time
            uncertainty = std_hv * np.sqrt(day + 1) * 0.5
            
            forecast.append(hv)
            upper.append(hv + uncertainty)
            lower.append(max(0.05, hv - uncertainty))
        
        return forecast, upper, lower
    
    # =========================================================================
    # PROJECTION & DIRECTION
    # =========================================================================
    
    def _project_prices(self, current_price: float, slope: float, 
                       momentum: float, days: int) -> List[float]:
        """
        Project future prices using slope and momentum.
        
        Combines:
        - Linear trend from regression slope
        - Momentum adjustment (acceleration/deceleration)
        """
        prices = []
        price = current_price
        
        # Adjust slope based on momentum
        adjusted_slope = slope * (1 + momentum * 0.3)
        
        for day in range(1, days + 1):
            # Trend component
            trend = adjusted_slope * day
            
            # Momentum decay (trend loses strength over time)
            decay = 0.95 ** day
            
            projected = current_price + trend * decay
            prices.append(projected)
        
        return prices
    
    def _determine_direction(self, momentum: float, ema_signal: str, 
                            slope: float) -> TrendDirection:
        """Determine overall trend direction."""
        # Combine signals
        score = 0
        
        if momentum > 0.3:
            score += 2
        elif momentum > 0:
            score += 1
        elif momentum < -0.3:
            score -= 2
        elif momentum < 0:
            score -= 1
        
        if ema_signal == 'Bullish':
            score += 1
        elif ema_signal == 'Bearish':
            score -= 1
        
        if slope > 0:
            score += 1
        elif slope < 0:
            score -= 1
        
        # Map score to direction
        if score >= 3:
            return TrendDirection.STRONGLY_BULLISH
        elif score >= 1:
            return TrendDirection.BULLISH
        elif score <= -3:
            return TrendDirection.STRONGLY_BEARISH
        elif score <= -1:
            return TrendDirection.BEARISH
        else:
            return TrendDirection.NEUTRAL
    
    def _calculate_confidence(self, r_squared: float, ema_signal: str,
                             momentum: float) -> float:
        """Calculate forecast confidence (0-1)."""
        # Base confidence from R-squared
        base = r_squared * 0.5
        
        # Add confidence for strong signals
        if ema_signal != 'Neutral':
            base += 0.15
        
        # Momentum strength adds confidence
        base += abs(momentum) * 0.2
        
        # Cap at 0.9 - never 100% confident
        return min(0.9, max(0.3, base))
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _prepare_dataframe(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Prepare and validate input DataFrame."""
        if df is None or len(df) == 0:
            return None
        
        # Handle different column naming conventions
        df = df.copy()
        
        # Try to find Close column
        close_cols = ['Close', 'close', 'Adj Close', 'adj_close', 'price']
        for col in close_cols:
            if col in df.columns:
                df['Close'] = df[col]
                break
        
        if 'Close' not in df.columns:
            # If still no Close, try first numeric column
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                df['Close'] = df[numeric_cols[0]]
            else:
                return None
        
        # Ensure numeric and drop NaN
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df = df.dropna(subset=['Close'])
        
        if len(df) < 5:
            return None
        
        return df
    
    def _create_neutral_forecast(self, symbol: str, price: float, 
                                 days: int) -> ForecastResult:
        """Create neutral forecast when data is insufficient."""
        return ForecastResult(
            symbol=symbol,
            current_price=price,
            price_path=[price] * days,
            upper_bound=[price * 1.05] * days,
            lower_bound=[price * 0.95] * days,
            direction=TrendDirection.NEUTRAL,
            confidence=0.3,
            ema_signal='Neutral',
            regression_slope=0.0,
            momentum_score=0.0,
            forecast_days=days
        )
    
    def _create_neutral_volatility(self, symbol: str) -> VolatilityForecast:
        """Create neutral volatility forecast when data is insufficient."""
        return VolatilityForecast(
            symbol=symbol,
            current_hv=0.25,
            hv_forecast=[0.25] * 5,
            hv_upper=[0.30] * 5,
            hv_lower=[0.20] * 5,
            regime=VolatilityRegime.NORMAL,
            percentile=50.0,
            parkinson_vol=0.25
        )


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_engine_instance: Optional[LocalForecastEngine] = None


def get_forecast_engine() -> LocalForecastEngine:
    """Get singleton forecast engine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = LocalForecastEngine()
    return _engine_instance


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("LocalForecastEngine Test")
    print("=" * 60)
    
    # Generate test data
    np.random.seed(42)
    n_days = 100
    
    # Simulated price data with upward trend
    base_price = 150.0
    returns = np.random.randn(n_days) * 0.02 + 0.001  # Slight upward bias
    prices = base_price * np.cumprod(1 + returns)
    
    # Add high/low
    high = prices * (1 + np.abs(np.random.randn(n_days) * 0.01))
    low = prices * (1 - np.abs(np.random.randn(n_days) * 0.01))
    
    df = pd.DataFrame({
        'Close': prices,
        'High': high,
        'Low': low,
        'Volume': np.random.randint(1000000, 5000000, n_days)
    })
    
    engine = LocalForecastEngine()
    
    # Test price forecast
    print("\n📈 Price Forecast Test")
    print("-" * 40)
    forecast = engine.generate_forecast('NVDA', df)
    print(f"  Current Price: ${forecast.current_price:.2f}")
    print(f"  Direction: {forecast.direction.value}")
    print(f"  Confidence: {forecast.confidence:.0%}")
    print(f"  EMA Signal: {forecast.ema_signal}")
    print(f"  Momentum: {forecast.momentum_score:.2f}")
    print(f"  5-Day Path: {[f'${p:.2f}' for p in forecast.price_path]}")
    print(f"  Expected Return: {forecast.expected_return:.2%}")
    
    # Test volatility forecast
    print("\n📊 Volatility Forecast Test")
    print("-" * 40)
    vol = engine.forecast_volatility('NVDA', df, current_iv=0.35)
    print(f"  Current HV: {vol.current_hv*100:.1f}%")
    print(f"  Parkinson Vol: {vol.parkinson_vol*100:.1f}%")
    print(f"  Regime: {vol.regime.value}")
    print(f"  Percentile: {vol.percentile:.1f}%")
    if vol.iv_premium:
        print(f"  IV Premium: {vol.iv_premium*100:.1f}%")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")

