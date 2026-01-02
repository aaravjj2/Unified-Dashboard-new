"""
Technical Feature Engine - Comprehensive Technical Indicators
==============================================================

Based on stefan-jansen/machine-learning-for-trading patterns:
- Trend indicators: SMA, EMA, MACD, ADX
- Momentum indicators: RSI, Stochastic, Williams %R
- Volatility indicators: Bollinger Bands, ATR, Keltner
- Volume indicators: OBV, VWAP, MFI
- Price patterns and momentum features
"""

import numpy as np
import pandas as pd
from typing import List, Optional, Dict, Union, Tuple


class TechnicalFeatureEngine:
    """
    Comprehensive technical indicator calculator.
    
    Categories:
    - Trend: SMA, EMA, MACD, ADX
    - Momentum: RSI, Stochastic, Williams %R
    - Volatility: Bollinger Bands, ATR, Keltner
    - Volume: OBV, VWAP, MFI
    """
    
    REQUIRED_COLS = ['close']
    OPTIONAL_COLS = ['open', 'high', 'low', 'volume']
    
    def __init__(self, df: pd.DataFrame):
        """
        Initialize with price data.
        
        Args:
            df: DataFrame with at least 'close' column.
                Optional: 'open', 'high', 'low', 'volume'
        """
        self.df = df.copy()
        self._validate_columns()
        self._fill_missing_ohlc()
    
    def _validate_columns(self):
        """Validate required columns exist."""
        # Check for required columns
        if 'close' not in self.df.columns and 'y' not in self.df.columns:
            raise ValueError("DataFrame must have 'close' or 'y' column")
        
        # Rename 'y' to 'close' if needed
        if 'close' not in self.df.columns:
            self.df['close'] = self.df['y']
    
    def _fill_missing_ohlc(self):
        """Fill missing OHLC columns with close price."""
        close = self.df['close']
        
        if 'open' not in self.df.columns:
            self.df['open'] = close
        if 'high' not in self.df.columns:
            self.df['high'] = close
        if 'low' not in self.df.columns:
            self.df['low'] = close
        if 'volume' not in self.df.columns:
            self.df['volume'] = 1000000  # Default volume
    
    def compute_all(
        self,
        periods: List[int] = None,
        include_volume: bool = True
    ) -> pd.DataFrame:
        """
        Compute all technical indicators.
        
        Args:
            periods: List of periods for rolling indicators
            include_volume: Whether to include volume indicators
            
        Returns:
            DataFrame with all features
        """
        periods = periods or [5, 10, 20, 50]
        
        # Trend indicators
        self._add_sma(periods)
        self._add_ema(periods)
        self._add_macd()
        self._add_adx()
        
        # Momentum
        self._add_rsi(periods)
        self._add_stochastic()
        self._add_williams_r()
        
        # Volatility
        self._add_bollinger_bands()
        self._add_atr()
        self._add_keltner_channels()
        
        # Volume
        if include_volume:
            self._add_obv()
            self._add_vwap()
            self._add_mfi()
        
        # Price patterns
        self._add_price_patterns()
        
        # Forward fill then fill remaining NaNs with 0
        self.df = self.df.ffill().fillna(0)
        
        # Replace inf values
        self.df = self.df.replace([np.inf, -np.inf], 0)
        
        return self.df
    
    def compute_subset(
        self,
        indicators: List[str],
        periods: List[int] = None
    ) -> pd.DataFrame:
        """
        Compute only specified indicators.
        
        Args:
            indicators: List of indicator names
            periods: Periods for rolling indicators
            
        Returns:
            DataFrame with specified features
        """
        periods = periods or [14]
        
        indicator_map = {
            'sma': lambda: self._add_sma(periods),
            'ema': lambda: self._add_ema(periods),
            'macd': self._add_macd,
            'adx': self._add_adx,
            'rsi': lambda: self._add_rsi(periods),
            'stochastic': self._add_stochastic,
            'williams_r': self._add_williams_r,
            'bollinger': self._add_bollinger_bands,
            'atr': self._add_atr,
            'keltner': self._add_keltner_channels,
            'obv': self._add_obv,
            'vwap': self._add_vwap,
            'mfi': self._add_mfi,
            'patterns': self._add_price_patterns
        }
        
        for ind in indicators:
            if ind.lower() in indicator_map:
                indicator_map[ind.lower()]()
        
        return self.df.ffill().fillna(0)
    
    # ========== TREND INDICATORS ==========
    
    def _add_sma(self, periods: List[int]):
        """Simple Moving Average."""
        for p in periods:
            self.df[f'sma_{p}'] = self.df['close'].rolling(p, min_periods=1).mean()
            self.df[f'sma_{p}_ratio'] = self.df['close'] / self.df[f'sma_{p}']
            self.df[f'sma_{p}_slope'] = self.df[f'sma_{p}'].diff(5)
    
    def _add_ema(self, periods: List[int]):
        """Exponential Moving Average."""
        for p in periods:
            self.df[f'ema_{p}'] = self.df['close'].ewm(span=p, adjust=False).mean()
            self.df[f'ema_{p}_ratio'] = self.df['close'] / self.df[f'ema_{p}']
    
    def _add_macd(self, fast: int = 12, slow: int = 26, signal: int = 9):
        """MACD indicator."""
        ema_fast = self.df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = self.df['close'].ewm(span=slow, adjust=False).mean()
        
        self.df['macd'] = ema_fast - ema_slow
        self.df['macd_signal'] = self.df['macd'].ewm(span=signal, adjust=False).mean()
        self.df['macd_histogram'] = self.df['macd'] - self.df['macd_signal']
        self.df['macd_crossover'] = np.where(
            (self.df['macd'] > self.df['macd_signal']) & 
            (self.df['macd'].shift(1) <= self.df['macd_signal'].shift(1)),
            1, 0
        )
    
    def _add_adx(self, period: int = 14):
        """Average Directional Index."""
        high = self.df['high']
        low = self.df['low']
        close = self.df['close']
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Directional Movement
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
        
        # Smoothed
        atr = tr.rolling(period, min_periods=1).mean()
        plus_di = 100 * (plus_dm.rolling(period, min_periods=1).mean() / (atr + 1e-10))
        minus_di = 100 * (minus_dm.rolling(period, min_periods=1).mean() / (atr + 1e-10))
        
        # ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        self.df['adx'] = dx.rolling(period, min_periods=1).mean()
        self.df['plus_di'] = plus_di
        self.df['minus_di'] = minus_di
        self.df['adx_trend'] = np.where(self.df['adx'] > 25, 1, 0)
    
    # ========== MOMENTUM INDICATORS ==========
    
    def _add_rsi(self, periods: List[int]):
        """Relative Strength Index."""
        for p in periods:
            delta = self.df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=p, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=p, min_periods=1).mean()
            rs = gain / (loss + 1e-10)
            self.df[f'rsi_{p}'] = 100 - (100 / (1 + rs))
            
            # RSI zones
            self.df[f'rsi_{p}_oversold'] = np.where(self.df[f'rsi_{p}'] < 30, 1, 0)
            self.df[f'rsi_{p}_overbought'] = np.where(self.df[f'rsi_{p}'] > 70, 1, 0)
    
    def _add_stochastic(self, k_period: int = 14, d_period: int = 3):
        """Stochastic Oscillator."""
        low_min = self.df['low'].rolling(k_period, min_periods=1).min()
        high_max = self.df['high'].rolling(k_period, min_periods=1).max()
        
        self.df['stoch_k'] = 100 * (self.df['close'] - low_min) / (high_max - low_min + 1e-10)
        self.df['stoch_d'] = self.df['stoch_k'].rolling(d_period, min_periods=1).mean()
        self.df['stoch_crossover'] = np.where(
            (self.df['stoch_k'] > self.df['stoch_d']) & 
            (self.df['stoch_k'].shift(1) <= self.df['stoch_d'].shift(1)),
            1, 0
        )
    
    def _add_williams_r(self, period: int = 14):
        """Williams %R."""
        high_max = self.df['high'].rolling(period, min_periods=1).max()
        low_min = self.df['low'].rolling(period, min_periods=1).min()
        
        self.df['williams_r'] = -100 * (high_max - self.df['close']) / (high_max - low_min + 1e-10)
    
    # ========== VOLATILITY INDICATORS ==========
    
    def _add_bollinger_bands(self, period: int = 20, std_dev: float = 2.0):
        """Bollinger Bands."""
        sma = self.df['close'].rolling(period, min_periods=1).mean()
        std = self.df['close'].rolling(period, min_periods=1).std()
        
        self.df['bb_upper'] = sma + (std * std_dev)
        self.df['bb_middle'] = sma
        self.df['bb_lower'] = sma - (std * std_dev)
        self.df['bb_width'] = (self.df['bb_upper'] - self.df['bb_lower']) / (self.df['bb_middle'] + 1e-10)
        self.df['bb_pct'] = (self.df['close'] - self.df['bb_lower']) / (self.df['bb_upper'] - self.df['bb_lower'] + 1e-10)
        
        # Squeeze indicator
        self.df['bb_squeeze'] = np.where(self.df['bb_width'] < self.df['bb_width'].rolling(20).mean(), 1, 0)
    
    def _add_atr(self, period: int = 14):
        """Average True Range."""
        high = self.df['high']
        low = self.df['low']
        close = self.df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        self.df['atr'] = tr.rolling(period, min_periods=1).mean()
        self.df['atr_pct'] = self.df['atr'] / (self.df['close'] + 1e-10) * 100
        self.df['atr_normalized'] = self.df['atr'] / self.df['atr'].rolling(50, min_periods=1).mean()
    
    def _add_keltner_channels(self, period: int = 20, atr_mult: float = 2.0):
        """Keltner Channels."""
        ema = self.df['close'].ewm(span=period, adjust=False).mean()
        
        # Use ATR if already computed, otherwise compute
        if 'atr' not in self.df.columns:
            self._add_atr(period)
        
        self.df['keltner_upper'] = ema + (self.df['atr'] * atr_mult)
        self.df['keltner_middle'] = ema
        self.df['keltner_lower'] = ema - (self.df['atr'] * atr_mult)
    
    # ========== VOLUME INDICATORS ==========
    
    def _add_obv(self):
        """On-Balance Volume."""
        obv = [0]
        for i in range(1, len(self.df)):
            if self.df['close'].iloc[i] > self.df['close'].iloc[i-1]:
                obv.append(obv[-1] + self.df['volume'].iloc[i])
            elif self.df['close'].iloc[i] < self.df['close'].iloc[i-1]:
                obv.append(obv[-1] - self.df['volume'].iloc[i])
            else:
                obv.append(obv[-1])
        
        self.df['obv'] = obv
        self.df['obv_ema'] = pd.Series(obv).ewm(span=20, adjust=False).mean().values
        self.df['obv_slope'] = pd.Series(obv).diff(5).values
    
    def _add_vwap(self):
        """Volume Weighted Average Price."""
        tp = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        cumulative_tp_vol = (tp * self.df['volume']).cumsum()
        cumulative_vol = self.df['volume'].cumsum()
        
        self.df['vwap'] = cumulative_tp_vol / (cumulative_vol + 1e-10)
        self.df['vwap_ratio'] = self.df['close'] / (self.df['vwap'] + 1e-10)
    
    def _add_mfi(self, period: int = 14):
        """Money Flow Index."""
        tp = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        mf = tp * self.df['volume']
        
        pos_mf = mf.where(tp > tp.shift(1), 0).rolling(period, min_periods=1).sum()
        neg_mf = mf.where(tp < tp.shift(1), 0).rolling(period, min_periods=1).sum()
        
        mfi = 100 - (100 / (1 + pos_mf / (neg_mf + 1e-10)))
        self.df['mfi'] = mfi
        self.df['mfi_oversold'] = np.where(mfi < 20, 1, 0)
        self.df['mfi_overbought'] = np.where(mfi > 80, 1, 0)
    
    # ========== PRICE PATTERNS ==========
    
    def _add_price_patterns(self):
        """Price-based patterns and features."""
        close = self.df['close']
        
        # Returns at various horizons
        self.df['return_1d'] = close.pct_change(1)
        self.df['return_5d'] = close.pct_change(5)
        self.df['return_10d'] = close.pct_change(10)
        self.df['return_20d'] = close.pct_change(20)
        
        # Log returns
        self.df['log_return_1d'] = np.log(close / close.shift(1))
        
        # Volatility
        self.df['volatility_5d'] = close.pct_change().rolling(5, min_periods=1).std()
        self.df['volatility_20d'] = close.pct_change().rolling(20, min_periods=1).std()
        self.df['volatility_ratio'] = self.df['volatility_5d'] / (self.df['volatility_20d'] + 1e-10)
        
        # Annualized volatility
        self.df['volatility_ann'] = self.df['volatility_20d'] * np.sqrt(252)
        
        # Distance from highs/lows
        self.df['dist_52w_high'] = close / close.rolling(252, min_periods=1).max() - 1
        self.df['dist_52w_low'] = close / close.rolling(252, min_periods=1).min() - 1
        
        # Trend strength
        self.df['trend_strength'] = (close - close.rolling(50, min_periods=1).mean()) / (close.rolling(50, min_periods=1).std() + 1e-10)
        
        # Price momentum
        self.df['momentum_5'] = close / close.shift(5) - 1
        self.df['momentum_10'] = close / close.shift(10) - 1
        self.df['momentum_20'] = close / close.shift(20) - 1
        
        # Acceleration
        self.df['acceleration'] = self.df['momentum_5'] - self.df['momentum_5'].shift(5)
        
        # Range position
        high_20 = self.df['high'].rolling(20, min_periods=1).max()
        low_20 = self.df['low'].rolling(20, min_periods=1).min()
        self.df['range_position'] = (close - low_20) / (high_20 - low_20 + 1e-10)
    
    def get_feature_names(self) -> List[str]:
        """Get list of all feature column names."""
        base_cols = ['open', 'high', 'low', 'close', 'volume']
        if 'ds' in self.df.columns:
            base_cols.append('ds')
        if 'y' in self.df.columns:
            base_cols.append('y')
        if 'date' in self.df.columns:
            base_cols.append('date')
        
        return [c for c in self.df.columns if c not in base_cols]
    
    def get_features_array(self) -> np.ndarray:
        """Get features as numpy array."""
        feature_cols = self.get_feature_names()
        return self.df[feature_cols].values
    
    def get_feature_stats(self) -> pd.DataFrame:
        """Get statistics for all features."""
        feature_cols = self.get_feature_names()
        return self.df[feature_cols].describe()


def compute_features_for_training(
    df: pd.DataFrame,
    periods: List[int] = None
) -> Tuple[np.ndarray, List[str]]:
    """
    Convenience function to compute all features for ML training.
    
    Args:
        df: Price DataFrame
        periods: Periods for rolling indicators
        
    Returns:
        Tuple of (feature_array, feature_names)
    """
    engine = TechnicalFeatureEngine(df)
    engine.compute_all(periods=periods)
    
    return engine.get_features_array(), engine.get_feature_names()
