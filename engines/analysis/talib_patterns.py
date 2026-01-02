"""
TA-Lib Candlestick Pattern Recognition Engine
Enhanced pattern detection using TA-Lib's 61 candlestick patterns.

Inspired by vectorbt's candlestick-patterns app.
Reference: https://github.com/polakowo/vectorbt

Usage:
    from engines.analysis.talib_patterns import TALibPatternEngine
    
    engine = TALibPatternEngine()
    patterns = engine.scan_patterns(symbol, ohlc_data)
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# Try to import talib - fallback to manual patterns if not available
try:
    import talib
    TALIB_AVAILABLE = True
    ALL_PATTERNS = talib.get_function_groups().get('Pattern Recognition', [])
except ImportError:
    TALIB_AVAILABLE = False
    ALL_PATTERNS = []
    logger.warning("TA-Lib not installed. Using fallback pattern detection.")


class PatternCategory(Enum):
    """Candlestick pattern categories."""
    REVERSAL_BULLISH = "reversal_bullish"
    REVERSAL_BEARISH = "reversal_bearish"
    CONTINUATION_BULLISH = "continuation_bullish"
    CONTINUATION_BEARISH = "continuation_bearish"
    NEUTRAL = "neutral"


@dataclass
class CandlePattern:
    """Represents a detected candlestick pattern."""
    name: str
    display_name: str
    signal: str  # 'bullish', 'bearish', 'neutral'
    category: PatternCategory
    bar_index: int
    timestamp: Optional[datetime]
    strength: int  # -100 to 100 from TA-Lib
    confidence: float  # Normalized 0-1
    description: str
    action: str  # 'buy', 'sell', 'hold'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "signal": self.signal,
            "category": self.category.value,
            "bar_index": self.bar_index,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "strength": self.strength,
            "confidence": round(self.confidence, 3),
            "description": self.description,
            "action": self.action,
        }


# Pattern metadata - descriptions and categories
PATTERN_INFO = {
    # Single Candlestick Patterns
    'CDL2CROWS': {'name': 'Two Crows', 'category': PatternCategory.REVERSAL_BEARISH, 'desc': 'Bearish reversal pattern formed by two black crows after an uptrend'},
    'CDL3BLACKCROWS': {'name': 'Three Black Crows', 'category': PatternCategory.REVERSAL_BEARISH, 'desc': 'Strong bearish reversal with three consecutive declining candles'},
    'CDL3INSIDE': {'name': 'Three Inside Up/Down', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Reversal pattern with harami followed by confirmation'},
    'CDL3LINESTRIKE': {'name': 'Three-Line Strike', 'category': PatternCategory.CONTINUATION_BULLISH, 'desc': 'Continuation pattern with three candles followed by engulfing'},
    'CDL3OUTSIDE': {'name': 'Three Outside Up/Down', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Reversal with engulfing followed by confirmation'},
    'CDL3STARSINSOUTH': {'name': 'Three Stars In The South', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Rare bullish reversal pattern'},
    'CDL3WHITESOLDIERS': {'name': 'Three White Soldiers', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Strong bullish reversal with three consecutive rising candles'},
    'CDLABANDONEDBABY': {'name': 'Abandoned Baby', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Major reversal pattern with a gap doji'},
    'CDLADVANCEBLOCK': {'name': 'Advance Block', 'category': PatternCategory.REVERSAL_BEARISH, 'desc': 'Bearish sign of weakening uptrend'},
    'CDLBELTHOLD': {'name': 'Belt Hold', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Reversal pattern opening at extreme'},
    'CDLBREAKAWAY': {'name': 'Breakaway', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Five-candle reversal pattern'},
    'CDLCLOSINGMARUBOZU': {'name': 'Closing Marubozu', 'category': PatternCategory.CONTINUATION_BULLISH, 'desc': 'Strong momentum with close at extreme'},
    'CDLCONCEALBABYSWALL': {'name': 'Concealing Baby Swallow', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Rare four-candle bullish reversal'},
    'CDLCOUNTERATTACK': {'name': 'Counterattack', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Two-candle reversal with same close'},
    'CDLDARKCLOUDCOVER': {'name': 'Dark Cloud Cover', 'category': PatternCategory.REVERSAL_BEARISH, 'desc': 'Bearish reversal penetrating prior candle'},
    'CDLDOJI': {'name': 'Doji', 'category': PatternCategory.NEUTRAL, 'desc': 'Indecision pattern with open=close'},
    'CDLDOJISTAR': {'name': 'Doji Star', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Doji gap from prior candle'},
    'CDLDRAGONFLYDOJI': {'name': 'Dragonfly Doji', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Bullish doji with long lower shadow'},
    'CDLENGULFING': {'name': 'Engulfing', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Strong reversal with candle engulfing prior'},
    'CDLEVENINGDOJISTAR': {'name': 'Evening Doji Star', 'category': PatternCategory.REVERSAL_BEARISH, 'desc': 'Major bearish reversal with doji'},
    'CDLEVENINGSTAR': {'name': 'Evening Star', 'category': PatternCategory.REVERSAL_BEARISH, 'desc': 'Bearish three-candle reversal pattern'},
    'CDLGAPSIDESIDEWHITE': {'name': 'Up/Down Gap Side-by-Side White Lines', 'category': PatternCategory.CONTINUATION_BULLISH, 'desc': 'Continuation with gap and parallel candles'},
    'CDLGRAVESTONEDOJI': {'name': 'Gravestone Doji', 'category': PatternCategory.REVERSAL_BEARISH, 'desc': 'Bearish doji with long upper shadow'},
    'CDLHAMMER': {'name': 'Hammer', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Bullish reversal with long lower shadow'},
    'CDLHANGINGMAN': {'name': 'Hanging Man', 'category': PatternCategory.REVERSAL_BEARISH, 'desc': 'Bearish reversal appearing in uptrend'},
    'CDLHARAMI': {'name': 'Harami', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Inside bar reversal pattern'},
    'CDLHARAMICROSS': {'name': 'Harami Cross', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Harami with doji inside bar'},
    'CDLHIGHWAVE': {'name': 'High Wave', 'category': PatternCategory.NEUTRAL, 'desc': 'Indecision with long shadows'},
    'CDLHIKKAKE': {'name': 'Hikkake', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Failed inside bar breakout'},
    'CDLHIKKAKEMOD': {'name': 'Modified Hikkake', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Modified version of hikkake pattern'},
    'CDLHOMINGPIGEON': {'name': 'Homing Pigeon', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Bullish harami variant'},
    'CDLIDENTICAL3CROWS': {'name': 'Identical Three Crows', 'category': PatternCategory.REVERSAL_BEARISH, 'desc': 'Three crows opening at prior close'},
    'CDLINNECK': {'name': 'In-Neck', 'category': PatternCategory.CONTINUATION_BEARISH, 'desc': 'Bearish continuation pattern'},
    'CDLINVERTEDHAMMER': {'name': 'Inverted Hammer', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Potential bullish reversal after downtrend'},
    'CDLKICKING': {'name': 'Kicking', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Strong reversal with marubozu gap'},
    'CDLKICKINGBYLENGTH': {'name': 'Kicking (by Length)', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Kicking pattern by candle length'},
    'CDLLADDERBOTTOM': {'name': 'Ladder Bottom', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Five-candle bullish reversal'},
    'CDLLONGLEGGEDDOJI': {'name': 'Long Legged Doji', 'category': PatternCategory.NEUTRAL, 'desc': 'Extreme indecision with long shadows'},
    'CDLLONGLINE': {'name': 'Long Line Candle', 'category': PatternCategory.CONTINUATION_BULLISH, 'desc': 'Strong momentum candle'},
    'CDLMARUBOZU': {'name': 'Marubozu', 'category': PatternCategory.CONTINUATION_BULLISH, 'desc': 'Full body candle no shadows'},
    'CDLMATCHINGLOW': {'name': 'Matching Low', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Two candles with same low'},
    'CDLMATHOLD': {'name': 'Mat Hold', 'category': PatternCategory.CONTINUATION_BULLISH, 'desc': 'Five-candle bullish continuation'},
    'CDLMORNINGDOJISTAR': {'name': 'Morning Doji Star', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Major bullish reversal with doji'},
    'CDLMORNINGSTAR': {'name': 'Morning Star', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Bullish three-candle reversal pattern'},
    'CDLONNECK': {'name': 'On-Neck', 'category': PatternCategory.CONTINUATION_BEARISH, 'desc': 'Bearish continuation pattern'},
    'CDLPIERCING': {'name': 'Piercing', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Bullish reversal penetrating prior candle'},
    'CDLRICKSHAWMAN': {'name': 'Rickshaw Man', 'category': PatternCategory.NEUTRAL, 'desc': 'Doji with equal shadows'},
    'CDLRISEFALL3METHODS': {'name': 'Rising/Falling Three Methods', 'category': PatternCategory.CONTINUATION_BULLISH, 'desc': 'Five-candle continuation pattern'},
    'CDLSEPARATINGLINES': {'name': 'Separating Lines', 'category': PatternCategory.CONTINUATION_BULLISH, 'desc': 'Continuation with same open'},
    'CDLSHOOTINGSTAR': {'name': 'Shooting Star', 'category': PatternCategory.REVERSAL_BEARISH, 'desc': 'Bearish reversal with long upper shadow'},
    'CDLSHORTLINE': {'name': 'Short Line Candle', 'category': PatternCategory.NEUTRAL, 'desc': 'Small body candle'},
    'CDLSPINNINGTOP': {'name': 'Spinning Top', 'category': PatternCategory.NEUTRAL, 'desc': 'Indecision with small body'},
    'CDLSTALLEDPATTERN': {'name': 'Stalled Pattern', 'category': PatternCategory.REVERSAL_BEARISH, 'desc': 'Weakening uptrend signal'},
    'CDLSTICKSANDWICH': {'name': 'Stick Sandwich', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Three-candle with same bottom'},
    'CDLTAKURI': {'name': 'Takuri', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Dragonfly doji variant'},
    'CDLTASUKIGAP': {'name': 'Tasuki Gap', 'category': PatternCategory.CONTINUATION_BULLISH, 'desc': 'Gap with inside partial fill'},
    'CDLTHRUSTING': {'name': 'Thrusting', 'category': PatternCategory.CONTINUATION_BEARISH, 'desc': 'Weak bullish counter-move'},
    'CDLTRISTAR': {'name': 'Tristar', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Three doji reversal pattern'},
    'CDLUNIQUE3RIVER': {'name': 'Unique Three River', 'category': PatternCategory.REVERSAL_BULLISH, 'desc': 'Rare bullish reversal pattern'},
    'CDLUPSIDEGAP2CROWS': {'name': 'Upside Gap Two Crows', 'category': PatternCategory.REVERSAL_BEARISH, 'desc': 'Bearish reversal in uptrend'},
    'CDLXSIDEGAP3METHODS': {'name': 'Upside/Downside Gap Three Methods', 'category': PatternCategory.CONTINUATION_BULLISH, 'desc': 'Gap continuation pattern'},
}

# Top patterns for entry signals (Bullish)
ENTRY_PATTERNS = [
    'CDLHAMMER',
    'CDLINVERTEDHAMMER', 
    'CDLPIERCING',
    'CDLMORNINGSTAR',
    'CDLMORNINGDOJISTAR',
    'CDL3WHITESOLDIERS',
    'CDLENGULFING',
    'CDLHARAMI',
    'CDLHARAMICROSS',
    'CDLDRAGONFLYDOJI',
]

# Top patterns for exit signals (Bearish)
EXIT_PATTERNS = [
    'CDLHANGINGMAN',
    'CDLSHOOTINGSTAR',
    'CDLEVENINGSTAR',
    'CDLEVENINGDOJISTAR',
    'CDL3BLACKCROWS',
    'CDLDARKCLOUDCOVER',
    'CDLENGULFING',
    'CDLGRAVESTONEDOJI',
    'CDLADVANCEBLOCK',
    'CDL2CROWS',
]


class TALibPatternEngine:
    """
    TA-Lib candlestick pattern recognition engine.
    
    Scans OHLC data for all 61 candlestick patterns and returns actionable signals.
    """
    
    def __init__(self, min_confidence: float = 0.5):
        """
        Initialize the pattern engine.
        
        Args:
            min_confidence: Minimum confidence threshold (0-1) for pattern detection
        """
        self.min_confidence = min_confidence
        self.patterns_available = TALIB_AVAILABLE
        logger.info(f"TALibPatternEngine initialized. TA-Lib available: {TALIB_AVAILABLE}")
        if TALIB_AVAILABLE:
            logger.info(f"Available patterns: {len(ALL_PATTERNS)}")
    
    def scan_all_patterns(
        self,
        open_prices: np.ndarray,
        high_prices: np.ndarray,
        low_prices: np.ndarray,
        close_prices: np.ndarray,
        timestamps: Optional[List[datetime]] = None,
    ) -> List[CandlePattern]:
        """
        Scan for all TA-Lib candlestick patterns.
        
        Args:
            open_prices: Array of open prices
            high_prices: Array of high prices
            low_prices: Array of low prices
            close_prices: Array of close prices
            timestamps: Optional list of timestamps
            
        Returns:
            List of detected CandlePattern objects
        """
        if not TALIB_AVAILABLE:
            return self._fallback_scan(close_prices, timestamps)
        
        detected = []
        
        # Ensure numpy arrays
        o = np.asarray(open_prices, dtype=np.float64)
        h = np.asarray(high_prices, dtype=np.float64)
        l = np.asarray(low_prices, dtype=np.float64)
        c = np.asarray(close_prices, dtype=np.float64)
        
        for pattern_name in ALL_PATTERNS:
            try:
                # Get the pattern function
                pattern_func = getattr(talib, pattern_name)
                
                # Execute pattern detection
                result = pattern_func(o, h, l, c)
                
                # Find non-zero values (pattern detected)
                signals = np.where(result != 0)[0]
                
                for idx in signals:
                    strength = result[idx]
                    
                    # Get pattern metadata
                    info = PATTERN_INFO.get(pattern_name, {
                        'name': pattern_name.replace('CDL', '').title(),
                        'category': PatternCategory.NEUTRAL,
                        'desc': f'{pattern_name} pattern detected',
                    })
                    
                    # Determine signal direction
                    if strength > 0:
                        signal = 'bullish'
                        action = 'buy'
                    elif strength < 0:
                        signal = 'bearish'
                        action = 'sell'
                    else:
                        signal = 'neutral'
                        action = 'hold'
                    
                    # Normalize confidence (TA-Lib returns -100 to 100)
                    confidence = abs(strength) / 100.0
                    
                    if confidence >= self.min_confidence:
                        timestamp = timestamps[idx] if timestamps and idx < len(timestamps) else None
                        
                        detected.append(CandlePattern(
                            name=pattern_name,
                            display_name=info.get('name', pattern_name),
                            signal=signal,
                            category=info.get('category', PatternCategory.NEUTRAL),
                            bar_index=int(idx),
                            timestamp=timestamp,
                            strength=int(strength),
                            confidence=confidence,
                            description=info.get('desc', ''),
                            action=action,
                        ))
                        
            except Exception as e:
                logger.debug(f"Pattern {pattern_name} scan error: {e}")
                continue
        
        # Sort by bar_index descending (most recent first)
        detected.sort(key=lambda x: x.bar_index, reverse=True)
        
        return detected
    
    def scan_entry_patterns(
        self,
        open_prices: np.ndarray,
        high_prices: np.ndarray,
        low_prices: np.ndarray,
        close_prices: np.ndarray,
        timestamps: Optional[List[datetime]] = None,
    ) -> List[CandlePattern]:
        """Scan for bullish entry patterns only."""
        all_patterns = self.scan_all_patterns(o, h, l, c, timestamps)
        return [p for p in all_patterns if p.name in ENTRY_PATTERNS and p.signal == 'bullish']
    
    def scan_exit_patterns(
        self,
        open_prices: np.ndarray,
        high_prices: np.ndarray,
        low_prices: np.ndarray,
        close_prices: np.ndarray,
        timestamps: Optional[List[datetime]] = None,
    ) -> List[CandlePattern]:
        """Scan for bearish exit patterns only."""
        all_patterns = self.scan_all_patterns(o, h, l, c, timestamps)
        return [p for p in all_patterns if p.name in EXIT_PATTERNS and p.signal == 'bearish']
    
    def get_recent_patterns(
        self,
        open_prices: np.ndarray,
        high_prices: np.ndarray,
        low_prices: np.ndarray,
        close_prices: np.ndarray,
        lookback: int = 5,
        timestamps: Optional[List[datetime]] = None,
    ) -> List[CandlePattern]:
        """
        Get patterns detected in the last N bars.
        
        Args:
            lookback: Number of recent bars to check
            
        Returns:
            List of recent patterns sorted by recency
        """
        all_patterns = self.scan_all_patterns(
            open_prices, high_prices, low_prices, close_prices, timestamps
        )
        
        min_idx = len(close_prices) - lookback
        recent = [p for p in all_patterns if p.bar_index >= min_idx]
        
        return recent
    
    def get_pattern_summary(
        self,
        open_prices: np.ndarray,
        high_prices: np.ndarray,
        low_prices: np.ndarray,
        close_prices: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Get a summary of pattern analysis.
        
        Returns:
            Dictionary with bullish/bearish counts and signals
        """
        patterns = self.scan_all_patterns(open_prices, high_prices, low_prices, close_prices)
        
        # Count recent patterns (last 5 bars)
        min_idx = len(close_prices) - 5
        recent = [p for p in patterns if p.bar_index >= min_idx]
        
        bullish_count = sum(1 for p in recent if p.signal == 'bullish')
        bearish_count = sum(1 for p in recent if p.signal == 'bearish')
        
        # Overall signal
        if bullish_count > bearish_count + 1:
            overall_signal = 'bullish'
        elif bearish_count > bullish_count + 1:
            overall_signal = 'bearish'
        else:
            overall_signal = 'neutral'
        
        return {
            'total_patterns': len(patterns),
            'recent_patterns': len(recent),
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'overall_signal': overall_signal,
            'patterns': [p.to_dict() for p in recent[:10]],  # Top 10 recent
        }
    
    def _fallback_scan(
        self,
        close_prices: np.ndarray,
        timestamps: Optional[List[datetime]] = None,
    ) -> List[CandlePattern]:
        """
        Fallback pattern detection when TA-Lib is not available.
        Uses simple price action analysis.
        """
        detected = []
        
        if len(close_prices) < 5:
            return detected
        
        c = np.asarray(close_prices, dtype=np.float64)
        
        # Simple momentum detection
        for i in range(4, len(c)):
            # Check for 3 consecutive up days (simple bullish)
            if c[i] > c[i-1] > c[i-2] > c[i-3]:
                detected.append(CandlePattern(
                    name='MOMENTUM_UP',
                    display_name='Bullish Momentum',
                    signal='bullish',
                    category=PatternCategory.CONTINUATION_BULLISH,
                    bar_index=i,
                    timestamp=timestamps[i] if timestamps else None,
                    strength=75,
                    confidence=0.75,
                    description='Three consecutive higher closes',
                    action='buy',
                ))
            
            # Check for 3 consecutive down days (simple bearish)
            elif c[i] < c[i-1] < c[i-2] < c[i-3]:
                detected.append(CandlePattern(
                    name='MOMENTUM_DOWN',
                    display_name='Bearish Momentum',
                    signal='bearish',
                    category=PatternCategory.CONTINUATION_BEARISH,
                    bar_index=i,
                    timestamp=timestamps[i] if timestamps else None,
                    strength=-75,
                    confidence=0.75,
                    description='Three consecutive lower closes',
                    action='sell',
                ))
        
        return detected
    
    @staticmethod
    def get_available_patterns() -> List[str]:
        """Get list of all available pattern names."""
        return ALL_PATTERNS if TALIB_AVAILABLE else ['MOMENTUM_UP', 'MOMENTUM_DOWN']
    
    @staticmethod
    def get_pattern_info(pattern_name: str) -> Dict[str, Any]:
        """Get information about a specific pattern."""
        return PATTERN_INFO.get(pattern_name, {
            'name': pattern_name,
            'category': PatternCategory.NEUTRAL.value,
            'desc': 'Pattern information not available',
        })


def scan_symbol_patterns(
    symbol: str,
    client: Any = None,
    lookback_days: int = 90,
) -> Dict[str, Any]:
    """
    Convenience function to scan patterns for a symbol.
    
    Args:
        symbol: Stock/crypto symbol
        client: Alpaca client (optional, will create if not provided)
        lookback_days: Number of days of data to analyze
        
    Returns:
        Pattern summary dictionary
    """
    try:
        # Import data loader
        if client is None:
            from financial_dashboard.tabs.options_lab.alpaca_data_loader import get_alpaca_client
            client = get_alpaca_client()
        
        # Get historical bars
        bars = client.get_historical_bars(symbol, '1Day', limit=lookback_days)
        
        if bars.empty:
            return {'error': f'No data for {symbol}', 'patterns': []}
        
        # Initialize engine
        engine = TALibPatternEngine()
        
        # Get OHLC data
        o = bars['o'].values
        h = bars['h'].values
        l = bars['l'].values
        c = bars['c'].values
        
        # Get timestamps if available
        timestamps = list(bars.index) if hasattr(bars.index, '__iter__') else None
        
        # Scan patterns
        summary = engine.get_pattern_summary(o, h, l, c)
        summary['symbol'] = symbol
        
        return summary
        
    except Exception as e:
        logger.error(f"Pattern scan failed for {symbol}: {e}")
        return {'error': str(e), 'patterns': [], 'symbol': symbol}


def scan_df_patterns(df: 'pd.DataFrame', lookback: int = 5) -> List[CandlePattern]:
    """
    Convenience function to scan a DataFrame for patterns.
    
    Args:
        df: DataFrame with OHLC data (columns: Open, High, Low, Close or lowercase)
        lookback: Number of recent bars to check
        
    Returns:
        List of detected patterns
    """
    engine = TALibPatternEngine()
    
    # Extract OHLC data from DataFrame - handle both cases
    cols = df.columns.str.lower()
    if 'open' in cols.values:
        o = df['Open'].values if 'Open' in df.columns else df['open'].values
        h = df['High'].values if 'High' in df.columns else df['high'].values
        l = df['Low'].values if 'Low' in df.columns else df['low'].values
        c = df['Close'].values if 'Close' in df.columns else df['close'].values
    else:
        # Assume standard column names
        o = df.iloc[:, 0].values
        h = df.iloc[:, 1].values
        l = df.iloc[:, 2].values
        c = df.iloc[:, 3].values
    
    # Get timestamps if available
    timestamps = None
    if hasattr(df, 'index') and hasattr(df.index, 'tolist'):
        try:
            timestamps = df.index.tolist()
        except:
            pass
    
    return engine.get_recent_patterns(o, h, l, c, lookback=lookback, timestamps=timestamps)


# Export
__all__ = [
    'TALibPatternEngine',
    'CandlePattern',
    'PatternCategory',
    'PATTERN_INFO',
    'ENTRY_PATTERNS',
    'EXIT_PATTERNS',
    'scan_symbol_patterns',
    'scan_df_patterns',
    'TALIB_AVAILABLE',
]
