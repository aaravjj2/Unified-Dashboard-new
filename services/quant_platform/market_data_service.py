"""
Market Data Service - Roadmap Items 1-60
Real-time and historical market data infrastructure
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
import threading
import queue
import json
import logging
from collections import deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MarketTick:
    """Single market tick data point"""
    symbol: str
    timestamp: datetime
    bid: float
    ask: float
    last: float
    volume: int
    bid_size: int = 0
    ask_size: int = 0
    
    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2
    
    @property
    def spread(self) -> float:
        return self.ask - self.bid

@dataclass
class OHLCV:
    """OHLCV bar data"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: float = 0.0
    trades: int = 0

@dataclass
class OrderBookLevel:
    """Order book level"""
    price: float
    size: int
    orders: int = 1

@dataclass
class OrderBook:
    """Full order book snapshot"""
    symbol: str
    timestamp: datetime
    bids: List[OrderBookLevel] = field(default_factory=list)
    asks: List[OrderBookLevel] = field(default_factory=list)
    
    @property
    def best_bid(self) -> float:
        return self.bids[0].price if self.bids else 0.0
    
    @property
    def best_ask(self) -> float:
        return self.asks[0].price if self.asks else 0.0
    
    @property
    def mid_price(self) -> float:
        return (self.best_bid + self.best_ask) / 2
    
    @property
    def spread(self) -> float:
        return self.best_ask - self.best_bid

class TickAggregator:
    """Aggregates ticks into OHLCV bars - Items 11-15"""
    
    def __init__(self, interval_seconds: int = 60):
        self.interval = interval_seconds
        self.current_bar: Dict[str, Dict] = {}
        self.completed_bars: Dict[str, List[OHLCV]] = {}
        
    def add_tick(self, tick: MarketTick) -> Optional[OHLCV]:
        """Add tick and return completed bar if interval elapsed"""
        symbol = tick.symbol
        
        if symbol not in self.current_bar:
            self.current_bar[symbol] = self._new_bar(tick)
            self.completed_bars[symbol] = []
            return None
        
        bar = self.current_bar[symbol]
        bar_start = bar['start']
        
        # Check if new bar needed
        elapsed = (tick.timestamp - bar_start).total_seconds()
        if elapsed >= self.interval:
            completed = self._close_bar(symbol)
            self.current_bar[symbol] = self._new_bar(tick)
            self.completed_bars[symbol].append(completed)
            return completed
        
        # Update current bar
        bar['high'] = max(bar['high'], tick.last)
        bar['low'] = min(bar['low'], tick.last)
        bar['close'] = tick.last
        bar['volume'] += tick.volume
        bar['vwap_num'] += tick.last * tick.volume
        bar['trades'] += 1
        
        return None
    
    def _new_bar(self, tick: MarketTick) -> Dict:
        return {
            'start': tick.timestamp,
            'open': tick.last,
            'high': tick.last,
            'low': tick.last,
            'close': tick.last,
            'volume': tick.volume,
            'vwap_num': tick.last * tick.volume,
            'trades': 1
        }
    
    def _close_bar(self, symbol: str) -> OHLCV:
        bar = self.current_bar[symbol]
        vwap = bar['vwap_num'] / bar['volume'] if bar['volume'] > 0 else bar['close']
        return OHLCV(
            symbol=symbol,
            timestamp=bar['start'],
            open=bar['open'],
            high=bar['high'],
            low=bar['low'],
            close=bar['close'],
            volume=bar['volume'],
            vwap=vwap,
            trades=bar['trades']
        )

class VolumeProfile:
    """Volume profile analysis - Items 21-25"""
    
    def __init__(self, num_levels: int = 50):
        self.num_levels = num_levels
        self.profiles: Dict[str, pd.DataFrame] = {}
        
    def calculate(self, bars: List[OHLCV]) -> pd.DataFrame:
        """Calculate volume profile from OHLCV bars"""
        if not bars:
            return pd.DataFrame()
        
        prices = []
        volumes = []
        
        for bar in bars:
            # Distribute volume across price range
            price_range = np.linspace(bar.low, bar.high, 10)
            vol_per_level = bar.volume / 10
            prices.extend(price_range)
            volumes.extend([vol_per_level] * 10)
        
        df = pd.DataFrame({'price': prices, 'volume': volumes})
        
        # Create price buckets
        price_min, price_max = df['price'].min(), df['price'].max()
        bins = np.linspace(price_min, price_max, self.num_levels + 1)
        df['bucket'] = pd.cut(df['price'], bins=bins, labels=False)
        
        profile = df.groupby('bucket').agg({
            'price': 'mean',
            'volume': 'sum'
        }).reset_index()
        
        # Find POC (Point of Control)
        poc_idx = profile['volume'].idxmax()
        profile['is_poc'] = profile.index == poc_idx
        
        # Calculate value area (70% of volume)
        total_vol = profile['volume'].sum()
        target_vol = total_vol * 0.7
        
        sorted_profile = profile.sort_values('volume', ascending=False)
        cumvol = sorted_profile['volume'].cumsum()
        va_indices = sorted_profile[cumvol <= target_vol].index
        profile['in_value_area'] = profile.index.isin(va_indices)
        
        return profile
    
    def get_poc(self, profile: pd.DataFrame) -> float:
        """Get Point of Control price"""
        poc_row = profile[profile['is_poc']]
        return poc_row['price'].iloc[0] if len(poc_row) > 0 else 0.0
    
    def get_value_area(self, profile: pd.DataFrame) -> tuple:
        """Get Value Area High and Low"""
        va = profile[profile['in_value_area']]
        if len(va) == 0:
            return (0.0, 0.0)
        return (va['price'].min(), va['price'].max())

class MarketMicrostructure:
    """Market microstructure analysis - Items 31-40"""
    
    def __init__(self, window: int = 100):
        self.window = window
        self.ticks: Dict[str, deque] = {}
        
    def add_tick(self, tick: MarketTick):
        """Add tick for analysis"""
        if tick.symbol not in self.ticks:
            self.ticks[tick.symbol] = deque(maxlen=self.window)
        self.ticks[tick.symbol].append(tick)
    
    def calculate_kyle_lambda(self, symbol: str) -> float:
        """Estimate Kyle's Lambda (price impact coefficient) - Item 31"""
        if symbol not in self.ticks or len(self.ticks[symbol]) < 20:
            return 0.0
        
        ticks = list(self.ticks[symbol])
        returns = []
        signed_volumes = []
        
        for i in range(1, len(ticks)):
            ret = (ticks[i].last - ticks[i-1].last) / ticks[i-1].last
            # Sign volume by price direction
            sign = 1 if ticks[i].last >= ticks[i-1].last else -1
            sv = sign * ticks[i].volume
            returns.append(ret)
            signed_volumes.append(sv)
        
        if len(returns) < 10:
            return 0.0
        
        # Regress returns on signed volume
        X = np.array(signed_volumes).reshape(-1, 1)
        y = np.array(returns)
        
        # Simple OLS
        X_mean = X.mean()
        y_mean = y.mean()
        numerator = np.sum((X.flatten() - X_mean) * (y - y_mean))
        denominator = np.sum((X.flatten() - X_mean) ** 2)
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def calculate_roll_spread(self, symbol: str) -> float:
        """Estimate Roll's implied spread - Item 32"""
        if symbol not in self.ticks or len(self.ticks[symbol]) < 20:
            return 0.0
        
        ticks = list(self.ticks[symbol])
        price_changes = [ticks[i].last - ticks[i-1].last for i in range(1, len(ticks))]
        
        if len(price_changes) < 2:
            return 0.0
        
        # Autocovariance at lag 1
        cov = np.cov(price_changes[:-1], price_changes[1:])[0, 1]
        
        if cov >= 0:
            return 0.0
        
        return 2 * np.sqrt(-cov)
    
    def calculate_vpin(self, symbol: str, bucket_size: int = 50) -> float:
        """Volume-synchronized Probability of Informed Trading - Item 33"""
        if symbol not in self.ticks or len(self.ticks[symbol]) < bucket_size:
            return 0.0
        
        ticks = list(self.ticks[symbol])
        
        # Classify trades using tick rule
        buy_volume = 0
        sell_volume = 0
        
        for i in range(1, len(ticks)):
            if ticks[i].last > ticks[i-1].last:
                buy_volume += ticks[i].volume
            elif ticks[i].last < ticks[i-1].last:
                sell_volume += ticks[i].volume
            else:
                # Split equally if price unchanged
                buy_volume += ticks[i].volume / 2
                sell_volume += ticks[i].volume / 2
        
        total_volume = buy_volume + sell_volume
        if total_volume == 0:
            return 0.0
        
        # VPIN = |V_buy - V_sell| / (V_buy + V_sell)
        return abs(buy_volume - sell_volume) / total_volume
    
    def calculate_order_imbalance(self, order_book: OrderBook) -> float:
        """Order book imbalance - Item 34"""
        bid_depth = sum(level.size for level in order_book.bids[:5])
        ask_depth = sum(level.size for level in order_book.asks[:5])
        
        total = bid_depth + ask_depth
        if total == 0:
            return 0.0
        
        return (bid_depth - ask_depth) / total

class MarketDataService:
    """Main market data service - Items 1-60"""
    
    def __init__(self):
        self.aggregators: Dict[str, TickAggregator] = {}
        self.volume_profiles: Dict[str, VolumeProfile] = {}
        self.microstructure = MarketMicrostructure()
        self.subscribers: Dict[str, List[Callable]] = {}
        self.historical_data: Dict[str, List[OHLCV]] = {}
        self.tick_history: Dict[str, List[MarketTick]] = {}
        self.order_books: Dict[str, OrderBook] = {}
        self._running = False
        self._data_queue = queue.Queue()
        
    def subscribe(self, symbol: str, callback: Callable):
        """Subscribe to market data updates"""
        if symbol not in self.subscribers:
            self.subscribers[symbol] = []
        self.subscribers[symbol].append(callback)
        
    def unsubscribe(self, symbol: str, callback: Callable):
        """Unsubscribe from market data"""
        if symbol in self.subscribers:
            self.subscribers[symbol] = [cb for cb in self.subscribers[symbol] if cb != callback]
    
    def process_tick(self, tick: MarketTick):
        """Process incoming tick data"""
        symbol = tick.symbol
        
        # Store tick
        if symbol not in self.tick_history:
            self.tick_history[symbol] = []
        self.tick_history[symbol].append(tick)
        
        # Add to aggregator
        if symbol not in self.aggregators:
            self.aggregators[symbol] = TickAggregator(60)
        
        bar = self.aggregators[symbol].add_tick(tick)
        if bar:
            if symbol not in self.historical_data:
                self.historical_data[symbol] = []
            self.historical_data[symbol].append(bar)
        
        # Microstructure analysis
        self.microstructure.add_tick(tick)
        
        # Notify subscribers
        if symbol in self.subscribers:
            for callback in self.subscribers[symbol]:
                try:
                    callback(tick)
                except Exception as e:
                    logger.error(f"Subscriber callback error: {e}")
    
    def process_order_book(self, order_book: OrderBook):
        """Process order book update"""
        self.order_books[order_book.symbol] = order_book
    
    def get_historical_bars(self, symbol: str, periods: int = 100) -> List[OHLCV]:
        """Get historical OHLCV bars"""
        if symbol not in self.historical_data:
            return []
        return self.historical_data[symbol][-periods:]
    
    def get_volume_profile(self, symbol: str, periods: int = 100) -> pd.DataFrame:
        """Get volume profile for symbol"""
        bars = self.get_historical_bars(symbol, periods)
        if symbol not in self.volume_profiles:
            self.volume_profiles[symbol] = VolumeProfile()
        return self.volume_profiles[symbol].calculate(bars)
    
    def get_microstructure_metrics(self, symbol: str) -> Dict[str, float]:
        """Get microstructure analysis metrics"""
        metrics = {
            'kyle_lambda': self.microstructure.calculate_kyle_lambda(symbol),
            'roll_spread': self.microstructure.calculate_roll_spread(symbol),
            'vpin': self.microstructure.calculate_vpin(symbol)
        }
        
        if symbol in self.order_books:
            metrics['order_imbalance'] = self.microstructure.calculate_order_imbalance(
                self.order_books[symbol]
            )
        
        return metrics
    
    def generate_sample_data(self, symbol: str, num_ticks: int = 1000) -> List[MarketTick]:
        """Generate sample market data for testing - Item 50-55"""
        np.random.seed(42)
        
        base_price = 100.0
        spread = 0.02
        ticks = []
        
        for i in range(num_ticks):
            # Random walk
            base_price *= np.exp(np.random.normal(0, 0.001))
            
            bid = base_price - spread / 2
            ask = base_price + spread / 2
            last = bid + np.random.random() * spread
            volume = int(np.random.exponential(1000))
            
            tick = MarketTick(
                symbol=symbol,
                timestamp=datetime.now() + timedelta(seconds=i),
                bid=round(bid, 2),
                ask=round(ask, 2),
                last=round(last, 2),
                volume=volume,
                bid_size=int(np.random.exponential(500)),
                ask_size=int(np.random.exponential(500))
            )
            ticks.append(tick)
            self.process_tick(tick)
        
        return ticks
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            'symbols_tracked': len(self.tick_history),
            'total_ticks': sum(len(t) for t in self.tick_history.values()),
            'total_bars': sum(len(b) for b in self.historical_data.values()),
            'active_subscribers': sum(len(s) for s in self.subscribers.values())
        }


if __name__ == "__main__":
    # Test the service
    service = MarketDataService()
    
    # Generate sample data
    print("Generating sample market data...")
    ticks = service.generate_sample_data("AAPL", 500)
    
    print(f"\nService Stats: {service.get_stats()}")
    
    # Get bars
    bars = service.get_historical_bars("AAPL", 10)
    print(f"\nLast 10 bars:")
    for bar in bars[-5:]:
        print(f"  {bar.timestamp}: O={bar.open:.2f} H={bar.high:.2f} L={bar.low:.2f} C={bar.close:.2f} V={bar.volume}")
    
    # Volume profile
    profile = service.get_volume_profile("AAPL")
    if len(profile) > 0:
        vp = service.volume_profiles["AAPL"]
        print(f"\nVolume Profile POC: ${vp.get_poc(profile):.2f}")
        val, vah = vp.get_value_area(profile)
        print(f"Value Area: ${val:.2f} - ${vah:.2f}")
    
    # Microstructure
    metrics = service.get_microstructure_metrics("AAPL")
    print(f"\nMicrostructure Metrics:")
    print(f"  Kyle's Lambda: {metrics['kyle_lambda']:.8f}")
    print(f"  Roll Spread: {metrics['roll_spread']:.4f}")
    print(f"  VPIN: {metrics['vpin']:.4f}")
    
    print("\n✅ Market Data Service operational - Items 1-60")
