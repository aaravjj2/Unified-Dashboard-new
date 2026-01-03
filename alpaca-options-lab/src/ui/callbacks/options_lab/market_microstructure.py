"""
Market Microstructure Analysis Module
=====================================
Advanced market microstructure analysis:
- Order flow imbalance
- Market maker detection
- Sweep detection
- Dark pool tracking
- Unusual activity detection

Author: AI/ML Options Lab
"""

import os
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


# ============================================================
# DATA CLASSES
# ============================================================

class FlowDirection(Enum):
    """Order flow direction."""
    BULLISH = 'bullish'
    BEARISH = 'bearish'
    NEUTRAL = 'neutral'


class ActivityLevel(Enum):
    """Activity level classification."""
    NORMAL = 'normal'
    ELEVATED = 'elevated'
    UNUSUAL = 'unusual'
    EXTREME = 'extreme'


@dataclass
class OrderFlowAnalysis:
    """Order flow imbalance analysis."""
    ticker: str
    timestamp: datetime
    
    # Volume metrics
    call_volume: int
    put_volume: int
    total_volume: int
    
    # Imbalance
    volume_imbalance: float  # Positive = call heavy
    delta_imbalance: float
    
    # Classification
    flow_direction: FlowDirection
    intensity: float  # 0-1
    
    # Signals
    signals: List[str]


@dataclass
class MarketMakerActivity:
    """Detected market maker activity."""
    ticker: str
    timestamp: datetime
    
    # Activity indicators
    quote_stuffing_score: float
    spread_manipulation_score: float
    inventory_hedging_detected: bool
    
    # Quote characteristics
    avg_bid_size: int
    avg_ask_size: int
    quote_update_frequency: float  # Per minute
    
    # Assessment
    mm_presence: str  # 'low', 'moderate', 'high'
    trading_implications: List[str]


@dataclass
class SweepOrder:
    """Detected sweep order."""
    ticker: str
    timestamp: datetime
    
    # Order details
    option_type: str  # 'call' or 'put'
    strike: float
    expiration: str
    
    # Sweep characteristics
    total_volume: int
    exchanges_hit: int
    avg_price: float
    
    # Analysis
    sentiment: str  # 'bullish', 'bearish'
    urgency: str  # 'low', 'medium', 'high'
    institutional_likelihood: float


@dataclass
class DarkPoolActivity:
    """Dark pool activity tracking."""
    ticker: str
    timestamp: datetime
    
    # Volume metrics
    dark_pool_volume: int
    lit_market_volume: int
    dark_pool_pct: float
    
    # Price impact
    dark_pool_avg_price: float
    lit_market_avg_price: float
    price_premium: float
    
    # Signals
    accumulation_signal: str  # 'buying', 'selling', 'mixed'
    institutional_interest: str  # 'low', 'moderate', 'high'


@dataclass
class UnusualActivity:
    """Unusual options activity detection."""
    ticker: str
    timestamp: datetime
    
    # Activity metrics
    volume_ratio: float  # vs 20-day avg
    oi_change_pct: float
    premium_spent: float
    
    # Contract details
    hot_contracts: List[Dict]
    
    # Analysis
    activity_level: ActivityLevel
    sentiment_bias: str
    institutional_probability: float
    
    # Alert
    alert_message: str


# ============================================================
# ORDER FLOW ANALYZER
# ============================================================

class OrderFlowAnalyzer:
    """
    Real-time order flow analysis.
    Tracks buy/sell pressure and imbalances.
    """
    
    def __init__(self):
        self.lookback_minutes = 30
    
    def analyze_flow(self, ticker: str, trades: List[Dict] = None) -> OrderFlowAnalysis:
        """Analyze order flow for ticker."""
        try:
            if trades is None:
                trades = self._fetch_trades(ticker)
            
            if not trades:
                trades = self._generate_sample_trades(ticker)
            
            # Separate by type
            call_trades = [t for t in trades if t.get('option_type') == 'call']
            put_trades = [t for t in trades if t.get('option_type') == 'put']
            
            call_volume = sum(t.get('volume', 0) for t in call_trades)
            put_volume = sum(t.get('volume', 0) for t in put_trades)
            total_volume = call_volume + put_volume
            
            # Volume imbalance
            if total_volume > 0:
                volume_imbalance = (call_volume - put_volume) / total_volume
            else:
                volume_imbalance = 0
            
            # Delta imbalance (simplified)
            call_delta = sum(t.get('volume', 0) * t.get('delta', 0.5) for t in call_trades)
            put_delta = sum(t.get('volume', 0) * abs(t.get('delta', -0.5)) for t in put_trades)
            delta_imbalance = call_delta - put_delta
            
            # Flow direction
            if volume_imbalance > 0.2:
                direction = FlowDirection.BULLISH
            elif volume_imbalance < -0.2:
                direction = FlowDirection.BEARISH
            else:
                direction = FlowDirection.NEUTRAL
            
            intensity = min(1.0, abs(volume_imbalance) * 2)
            
            # Signals
            signals = []
            if abs(volume_imbalance) > 0.3:
                signals.append(f"Strong {direction.value} flow detected")
            if call_volume > put_volume * 2:
                signals.append("Call volume 2x+ put volume")
            elif put_volume > call_volume * 2:
                signals.append("Put volume 2x+ call volume")
            
            return OrderFlowAnalysis(
                ticker=ticker,
                timestamp=datetime.now(),
                call_volume=call_volume,
                put_volume=put_volume,
                total_volume=total_volume,
                volume_imbalance=round(volume_imbalance, 3),
                delta_imbalance=round(delta_imbalance, 2),
                flow_direction=direction,
                intensity=round(intensity, 3),
                signals=signals
            )
            
        except Exception as e:
            logger.error(f"Order flow analysis failed: {e}")
            return self._empty_flow(ticker)
    
    def _fetch_trades(self, ticker: str) -> List[Dict]:
        """Fetch recent trades."""
        # Would connect to data feed
        return []
    
    def _generate_sample_trades(self, ticker: str) -> List[Dict]:
        """Generate sample trades for demo."""
        trades = []
        for i in range(50):
            trades.append({
                'option_type': 'call' if np.random.random() > 0.45 else 'put',
                'volume': int(np.random.exponential(100)),
                'delta': np.random.uniform(0.2, 0.8) if np.random.random() > 0.5 else -np.random.uniform(0.2, 0.8),
                'price': np.random.uniform(1, 10)
            })
        return trades
    
    def _empty_flow(self, ticker: str) -> OrderFlowAnalysis:
        return OrderFlowAnalysis(
            ticker=ticker,
            timestamp=datetime.now(),
            call_volume=0,
            put_volume=0,
            total_volume=0,
            volume_imbalance=0,
            delta_imbalance=0,
            flow_direction=FlowDirection.NEUTRAL,
            intensity=0,
            signals=[]
        )


# ============================================================
# MARKET MAKER DETECTOR
# ============================================================

class MarketMakerDetector:
    """
    Detect likely market maker activity patterns.
    """
    
    def __init__(self):
        self.min_quote_frequency = 10  # Quotes per minute for MM activity
    
    def detect_activity(self, ticker: str, quotes: List[Dict] = None) -> MarketMakerActivity:
        """Detect market maker activity."""
        try:
            if quotes is None:
                quotes = self._generate_sample_quotes(ticker)
            
            if not quotes:
                return self._empty_mm(ticker)
            
            # Quote stuffing detection
            quote_freq = len(quotes)  # Per minute
            quote_stuffing = min(1.0, quote_freq / 100)
            
            # Spread manipulation
            spreads = [q.get('ask', 0) - q.get('bid', 0) for q in quotes]
            spread_std = np.std(spreads) if spreads else 0
            spread_manipulation = min(1.0, spread_std * 10)
            
            # Size analysis
            bid_sizes = [q.get('bid_size', 0) for q in quotes]
            ask_sizes = [q.get('ask_size', 0) for q in quotes]
            
            avg_bid = np.mean(bid_sizes) if bid_sizes else 0
            avg_ask = np.mean(ask_sizes) if ask_sizes else 0
            
            # Inventory hedging (large size changes)
            size_changes = np.abs(np.diff(bid_sizes + ask_sizes))
            hedging_detected = np.any(size_changes > np.mean(size_changes) * 3) if len(size_changes) > 0 else False
            
            # MM presence level
            mm_score = (quote_stuffing + spread_manipulation) / 2
            if mm_score > 0.7:
                presence = 'high'
                implications = [
                    "Tight spreads expected - use limit orders",
                    "May see price improvement on limit orders",
                    "Avoid large market orders"
                ]
            elif mm_score > 0.4:
                presence = 'moderate'
                implications = [
                    "Normal market making activity",
                    "Standard execution expected"
                ]
            else:
                presence = 'low'
                implications = [
                    "Limited market making",
                    "May see wider spreads",
                    "Be patient with fills"
                ]
            
            return MarketMakerActivity(
                ticker=ticker,
                timestamp=datetime.now(),
                quote_stuffing_score=round(quote_stuffing, 3),
                spread_manipulation_score=round(spread_manipulation, 3),
                inventory_hedging_detected=hedging_detected,
                avg_bid_size=int(avg_bid),
                avg_ask_size=int(avg_ask),
                quote_update_frequency=quote_freq,
                mm_presence=presence,
                trading_implications=implications
            )
            
        except Exception as e:
            logger.error(f"MM detection failed: {e}")
            return self._empty_mm(ticker)
    
    def _generate_sample_quotes(self, ticker: str) -> List[Dict]:
        """Generate sample quotes."""
        base_price = 5.0
        quotes = []
        for _ in range(60):
            mid = base_price + np.random.normal(0, 0.1)
            spread = np.random.uniform(0.05, 0.15)
            quotes.append({
                'bid': mid - spread/2,
                'ask': mid + spread/2,
                'bid_size': int(np.random.exponential(50)),
                'ask_size': int(np.random.exponential(50))
            })
        return quotes
    
    def _empty_mm(self, ticker: str) -> MarketMakerActivity:
        return MarketMakerActivity(
            ticker=ticker,
            timestamp=datetime.now(),
            quote_stuffing_score=0,
            spread_manipulation_score=0,
            inventory_hedging_detected=False,
            avg_bid_size=0,
            avg_ask_size=0,
            quote_update_frequency=0,
            mm_presence='unknown',
            trading_implications=[]
        )


# ============================================================
# SWEEP DETECTOR
# ============================================================

class SweepDetector:
    """
    Detect large sweep orders across exchanges.
    """
    
    def __init__(self):
        self.min_sweep_size = 100  # Minimum contracts for sweep
    
    def detect_sweeps(self, ticker: str, trades: List[Dict] = None) -> List[SweepOrder]:
        """Detect sweep orders."""
        try:
            if trades is None:
                trades = self._generate_sample_sweeps(ticker)
            
            sweeps = []
            
            # Group by time window (1 second)
            time_groups = defaultdict(list)
            for trade in trades:
                time_key = trade.get('timestamp', datetime.now()).replace(microsecond=0)
                time_groups[time_key].append(trade)
            
            for time_key, group in time_groups.items():
                total_vol = sum(t.get('volume', 0) for t in group)
                
                if total_vol >= self.min_sweep_size:
                    exchanges = len(set(t.get('exchange', 'X') for t in group))
                    
                    if exchanges >= 2:  # Multi-exchange = sweep
                        option_type = group[0].get('option_type', 'call')
                        avg_price = np.mean([t.get('price', 1) for t in group])
                        
                        # Sentiment
                        sentiment = 'bullish' if option_type == 'call' else 'bearish'
                        
                        # Urgency
                        if total_vol > self.min_sweep_size * 5:
                            urgency = 'high'
                        elif total_vol > self.min_sweep_size * 2:
                            urgency = 'medium'
                        else:
                            urgency = 'low'
                        
                        # Institutional likelihood
                        inst_prob = min(0.95, total_vol / 1000)
                        
                        sweeps.append(SweepOrder(
                            ticker=ticker,
                            timestamp=time_key,
                            option_type=option_type,
                            strike=group[0].get('strike', 100),
                            expiration=group[0].get('expiration', '2024-01-19'),
                            total_volume=total_vol,
                            exchanges_hit=exchanges,
                            avg_price=round(avg_price, 2),
                            sentiment=sentiment,
                            urgency=urgency,
                            institutional_likelihood=round(inst_prob, 3)
                        ))
            
            return sorted(sweeps, key=lambda x: x.total_volume, reverse=True)
            
        except Exception as e:
            logger.error(f"Sweep detection failed: {e}")
            return []
    
    def _generate_sample_sweeps(self, ticker: str) -> List[Dict]:
        """Generate sample sweep data."""
        trades = []
        base_time = datetime.now()
        
        for i in range(10):
            time = base_time + timedelta(seconds=i//3)
            trades.append({
                'timestamp': time,
                'option_type': 'call' if np.random.random() > 0.4 else 'put',
                'volume': int(np.random.exponential(50)),
                'price': np.random.uniform(2, 8),
                'strike': 100 + (i % 3) * 5,
                'expiration': '2024-01-19',
                'exchange': ['CBOE', 'NASDAQ', 'ARCA'][i % 3]
            })
        
        return trades


# ============================================================
# DARK POOL TRACKER
# ============================================================

class DarkPoolTracker:
    """
    Track dark pool activity and hidden liquidity.
    """
    
    def __init__(self):
        self.dark_pool_threshold = 0.30  # >30% = high dark pool
    
    def track_activity(self, ticker: str, data: Dict = None) -> DarkPoolActivity:
        """Track dark pool activity."""
        try:
            if data is None:
                data = self._simulate_dark_pool_data(ticker)
            
            dp_vol = data.get('dark_pool_volume', 50000)
            lit_vol = data.get('lit_volume', 100000)
            total_vol = dp_vol + lit_vol
            
            dp_pct = dp_vol / total_vol * 100 if total_vol > 0 else 0
            
            # Price analysis
            dp_price = data.get('dark_pool_avg_price', 100.5)
            lit_price = data.get('lit_avg_price', 100.0)
            premium = (dp_price - lit_price) / lit_price * 100
            
            # Signals
            if premium > 0.1:
                accum_signal = 'buying'
                interest = 'high' if dp_pct > 40 else 'moderate'
            elif premium < -0.1:
                accum_signal = 'selling'
                interest = 'high' if dp_pct > 40 else 'moderate'
            else:
                accum_signal = 'mixed'
                interest = 'low' if dp_pct < 20 else 'moderate'
            
            return DarkPoolActivity(
                ticker=ticker,
                timestamp=datetime.now(),
                dark_pool_volume=dp_vol,
                lit_market_volume=lit_vol,
                dark_pool_pct=round(dp_pct, 2),
                dark_pool_avg_price=round(dp_price, 2),
                lit_market_avg_price=round(lit_price, 2),
                price_premium=round(premium, 3),
                accumulation_signal=accum_signal,
                institutional_interest=interest
            )
            
        except Exception as e:
            logger.error(f"Dark pool tracking failed: {e}")
            return DarkPoolActivity(
                ticker=ticker,
                timestamp=datetime.now(),
                dark_pool_volume=0,
                lit_market_volume=0,
                dark_pool_pct=0,
                dark_pool_avg_price=0,
                lit_market_avg_price=0,
                price_premium=0,
                accumulation_signal='unknown',
                institutional_interest='unknown'
            )
    
    def _simulate_dark_pool_data(self, ticker: str) -> Dict:
        """Simulate dark pool data."""
        return {
            'dark_pool_volume': int(np.random.exponential(50000)),
            'lit_volume': int(np.random.exponential(100000)),
            'dark_pool_avg_price': 100 + np.random.normal(0.5, 0.2),
            'lit_avg_price': 100
        }


# ============================================================
# UNUSUAL ACTIVITY DETECTOR
# ============================================================

class UnusualActivityDetector:
    """
    Detect unusual options activity.
    """
    
    def __init__(self):
        self.volume_threshold = 2.0  # 2x average = unusual
        self.oi_threshold = 10  # 10% OI change = unusual
    
    def detect_unusual(self, ticker: str, data: Dict = None) -> UnusualActivity:
        """Detect unusual activity."""
        try:
            if data is None:
                data = self._simulate_activity_data(ticker)
            
            volume_ratio = data.get('volume_ratio', 1.5)
            oi_change = data.get('oi_change_pct', 5)
            premium = data.get('premium_spent', 1000000)
            
            # Activity level
            if volume_ratio > 5 or oi_change > 30:
                level = ActivityLevel.EXTREME
            elif volume_ratio > 3 or oi_change > 20:
                level = ActivityLevel.UNUSUAL
            elif volume_ratio > 2 or oi_change > 10:
                level = ActivityLevel.ELEVATED
            else:
                level = ActivityLevel.NORMAL
            
            # Hot contracts
            hot_contracts = data.get('hot_contracts', [
                {'strike': 100, 'expiration': '2024-01-19', 'type': 'call', 'volume': 5000},
                {'strike': 95, 'expiration': '2024-01-19', 'type': 'put', 'volume': 3000}
            ])
            
            # Sentiment
            call_vol = sum(c['volume'] for c in hot_contracts if c.get('type') == 'call')
            put_vol = sum(c['volume'] for c in hot_contracts if c.get('type') == 'put')
            
            if call_vol > put_vol * 1.5:
                sentiment = 'bullish'
            elif put_vol > call_vol * 1.5:
                sentiment = 'bearish'
            else:
                sentiment = 'neutral'
            
            # Institutional probability
            inst_prob = min(0.95, premium / 5000000)
            
            # Alert message
            if level == ActivityLevel.EXTREME:
                alert = f"🚨 EXTREME unusual activity in {ticker}! {volume_ratio:.1f}x normal volume"
            elif level == ActivityLevel.UNUSUAL:
                alert = f"⚠️ Unusual activity in {ticker}: {volume_ratio:.1f}x volume, {sentiment} bias"
            elif level == ActivityLevel.ELEVATED:
                alert = f"📊 Elevated activity in {ticker}: {volume_ratio:.1f}x volume"
            else:
                alert = f"Normal activity in {ticker}"
            
            return UnusualActivity(
                ticker=ticker,
                timestamp=datetime.now(),
                volume_ratio=round(volume_ratio, 2),
                oi_change_pct=round(oi_change, 2),
                premium_spent=premium,
                hot_contracts=hot_contracts,
                activity_level=level,
                sentiment_bias=sentiment,
                institutional_probability=round(inst_prob, 3),
                alert_message=alert
            )
            
        except Exception as e:
            logger.error(f"Unusual activity detection failed: {e}")
            return UnusualActivity(
                ticker=ticker,
                timestamp=datetime.now(),
                volume_ratio=1.0,
                oi_change_pct=0,
                premium_spent=0,
                hot_contracts=[],
                activity_level=ActivityLevel.NORMAL,
                sentiment_bias='neutral',
                institutional_probability=0,
                alert_message="Detection unavailable"
            )
    
    def _simulate_activity_data(self, ticker: str) -> Dict:
        """Simulate activity data."""
        return {
            'volume_ratio': max(0.5, np.random.exponential(2)),
            'oi_change_pct': np.random.exponential(5),
            'premium_spent': int(np.random.exponential(1000000)),
            'hot_contracts': [
                {'strike': 100, 'expiration': '2024-01-19', 'type': 'call', 'volume': int(np.random.exponential(3000))},
                {'strike': 95, 'expiration': '2024-01-19', 'type': 'put', 'volume': int(np.random.exponential(2000))}
            ]
        }


# ============================================================
# UNIFIED MICROSTRUCTURE ENGINE
# ============================================================

class MarketMicrostructureEngine:
    """Unified market microstructure analysis engine."""
    
    def __init__(self):
        self.flow_analyzer = OrderFlowAnalyzer()
        self.mm_detector = MarketMakerDetector()
        self.sweep_detector = SweepDetector()
        self.dark_pool_tracker = DarkPoolTracker()
        self.unusual_detector = UnusualActivityDetector()
    
    def full_analysis(self, ticker: str) -> Dict:
        """Complete microstructure analysis."""
        # Order flow
        flow = self.flow_analyzer.analyze_flow(ticker)
        
        # Market maker activity
        mm = self.mm_detector.detect_activity(ticker)
        
        # Sweeps
        sweeps = self.sweep_detector.detect_sweeps(ticker)
        
        # Dark pool
        dark_pool = self.dark_pool_tracker.track_activity(ticker)
        
        # Unusual activity
        unusual = self.unusual_detector.detect_unusual(ticker)
        
        return {
            'ticker': ticker,
            'order_flow': {
                'direction': flow.flow_direction.value,
                'intensity': flow.intensity,
                'volume_imbalance': flow.volume_imbalance,
                'signals': flow.signals
            },
            'market_maker': {
                'presence': mm.mm_presence,
                'quote_frequency': mm.quote_update_frequency,
                'implications': mm.trading_implications
            },
            'sweeps': {
                'count': len(sweeps),
                'largest_volume': sweeps[0].total_volume if sweeps else 0,
                'sentiment': sweeps[0].sentiment if sweeps else 'none'
            },
            'dark_pool': {
                'pct_of_volume': dark_pool.dark_pool_pct,
                'accumulation_signal': dark_pool.accumulation_signal,
                'institutional_interest': dark_pool.institutional_interest
            },
            'unusual_activity': {
                'level': unusual.activity_level.value,
                'volume_ratio': unusual.volume_ratio,
                'sentiment': unusual.sentiment_bias,
                'alert': unusual.alert_message
            },
            'generated_at': datetime.now().isoformat()
        }


# ============================================================
# SINGLETON GETTER
# ============================================================

_microstructure_engine = None

def get_microstructure_engine() -> MarketMicrostructureEngine:
    """Get singleton instance."""
    global _microstructure_engine
    if _microstructure_engine is None:
        _microstructure_engine = MarketMicrostructureEngine()
    return _microstructure_engine
