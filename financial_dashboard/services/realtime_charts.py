"""
Real-time Chart Updates with WebSocket
Implements #235 from ROADMAP_ULTIMATE.md

Based on: https://github.com/tradingview/lightweight-charts
"""
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)


class ChartType(Enum):
    """Supported chart types"""
    CANDLESTICK = "candlestick"
    LINE = "line"
    AREA = "area"
    BAR = "bar"
    HISTOGRAM = "histogram"


class UpdateType(Enum):
    """Types of chart updates"""
    NEW_BAR = "new_bar"
    UPDATE_LAST = "update_last"
    HISTORICAL = "historical"
    INDICATOR = "indicator"
    DRAWING = "drawing"
    ANNOTATION = "annotation"


@dataclass
class ChartBar:
    """OHLCV bar data"""
    time: int  # Unix timestamp
    open: float
    high: float
    low: float
    close: float
    volume: float = 0
    
    def to_dict(self) -> Dict:
        return {
            'time': self.time,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume
        }


@dataclass
class ChartUpdate:
    """Real-time chart update"""
    symbol: str
    update_type: UpdateType
    data: Any
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_json(self) -> str:
        return json.dumps({
            'symbol': self.symbol,
            'type': self.update_type.value,
            'data': self.data,
            'timestamp': self.timestamp.isoformat()
        })


@dataclass
class ChartConfig:
    """Chart configuration"""
    symbol: str
    timeframe: str = "1m"
    chart_type: ChartType = ChartType.CANDLESTICK
    show_volume: bool = True
    indicators: List[str] = field(default_factory=list)
    theme: str = "dark"


class RealTimeChartManager:
    """
    Manages real-time chart data and updates
    Supports multiple symbols and timeframes
    """
    
    def __init__(self, max_bars: int = 500):
        self.max_bars = max_bars
        self.charts: Dict[str, Dict[str, List[ChartBar]]] = {}  # symbol -> timeframe -> bars
        self.subscribers: Dict[str, List[Callable]] = {}
        self.indicators: Dict[str, Dict[str, List[float]]] = {}
        self.last_prices: Dict[str, float] = {}
        
    def register_chart(self, config: ChartConfig) -> bool:
        """Register a new chart for updates"""
        key = f"{config.symbol}_{config.timeframe}"
        
        if config.symbol not in self.charts:
            self.charts[config.symbol] = {}
        
        if config.timeframe not in self.charts[config.symbol]:
            self.charts[config.symbol][config.timeframe] = []
        
        if key not in self.subscribers:
            self.subscribers[key] = []
        
        logger.info(f"Registered chart: {key}")
        return True
    
    def subscribe(self, symbol: str, timeframe: str, callback: Callable):
        """Subscribe to chart updates"""
        key = f"{symbol}_{timeframe}"
        if key not in self.subscribers:
            self.subscribers[key] = []
        self.subscribers[key].append(callback)
    
    def unsubscribe(self, symbol: str, timeframe: str, callback: Callable):
        """Unsubscribe from chart updates"""
        key = f"{symbol}_{timeframe}"
        if key in self.subscribers and callback in self.subscribers[key]:
            self.subscribers[key].remove(callback)
    
    def load_historical(self, symbol: str, timeframe: str, bars: List[Dict]) -> int:
        """Load historical bar data"""
        if symbol not in self.charts:
            self.charts[symbol] = {}
        
        chart_bars = [
            ChartBar(
                time=bar['time'],
                open=bar['open'],
                high=bar['high'],
                low=bar['low'],
                close=bar['close'],
                volume=bar.get('volume', 0)
            )
            for bar in bars
        ]
        
        self.charts[symbol][timeframe] = chart_bars[-self.max_bars:]
        
        if chart_bars:
            self.last_prices[symbol] = chart_bars[-1].close
        
        # Notify subscribers
        update = ChartUpdate(
            symbol=symbol,
            update_type=UpdateType.HISTORICAL,
            data=[b.to_dict() for b in chart_bars[-self.max_bars:]]
        )
        self._notify(symbol, timeframe, update)
        
        return len(chart_bars)
    
    def update_tick(self, symbol: str, price: float, volume: float = 0):
        """Process a new tick and update all timeframes"""
        current_time = int(datetime.now().timestamp())
        self.last_prices[symbol] = price
        
        if symbol not in self.charts:
            return
        
        for timeframe in self.charts[symbol]:
            bars = self.charts[symbol][timeframe]
            bar_seconds = self._timeframe_to_seconds(timeframe)
            
            if not bars:
                # Create first bar
                bar_time = (current_time // bar_seconds) * bar_seconds
                new_bar = ChartBar(
                    time=bar_time,
                    open=price,
                    high=price,
                    low=price,
                    close=price,
                    volume=volume
                )
                bars.append(new_bar)
                
                update = ChartUpdate(
                    symbol=symbol,
                    update_type=UpdateType.NEW_BAR,
                    data=new_bar.to_dict()
                )
            else:
                last_bar = bars[-1]
                current_bar_time = (current_time // bar_seconds) * bar_seconds
                
                if current_bar_time > last_bar.time:
                    # New bar
                    new_bar = ChartBar(
                        time=current_bar_time,
                        open=price,
                        high=price,
                        low=price,
                        close=price,
                        volume=volume
                    )
                    bars.append(new_bar)
                    
                    # Trim to max bars
                    if len(bars) > self.max_bars:
                        bars.pop(0)
                    
                    update = ChartUpdate(
                        symbol=symbol,
                        update_type=UpdateType.NEW_BAR,
                        data=new_bar.to_dict()
                    )
                else:
                    # Update current bar
                    last_bar.high = max(last_bar.high, price)
                    last_bar.low = min(last_bar.low, price)
                    last_bar.close = price
                    last_bar.volume += volume
                    
                    update = ChartUpdate(
                        symbol=symbol,
                        update_type=UpdateType.UPDATE_LAST,
                        data=last_bar.to_dict()
                    )
            
            self._notify(symbol, timeframe, update)
    
    def _timeframe_to_seconds(self, timeframe: str) -> int:
        """Convert timeframe string to seconds"""
        multipliers = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400,
            'w': 604800
        }
        
        unit = timeframe[-1].lower()
        value = int(timeframe[:-1]) if len(timeframe) > 1 else 1
        
        return value * multipliers.get(unit, 60)
    
    def _notify(self, symbol: str, timeframe: str, update: ChartUpdate):
        """Notify all subscribers of update"""
        key = f"{symbol}_{timeframe}"
        if key in self.subscribers:
            for callback in self.subscribers[key]:
                try:
                    callback(update)
                except Exception as e:
                    logger.error(f"Subscriber callback error: {e}")
    
    def calculate_indicator(self, 
                           symbol: str,
                           timeframe: str,
                           indicator: str,
                           params: Dict = None) -> List[float]:
        """Calculate indicator values"""
        if params is None:
            params = {}
        
        bars = self.get_bars(symbol, timeframe)
        if not bars:
            return []
        
        closes = [b.close for b in bars]
        highs = [b.high for b in bars]
        lows = [b.low for b in bars]
        volumes = [b.volume for b in bars]
        
        result = []
        
        if indicator.lower() == 'sma':
            period = params.get('period', 20)
            result = self._sma(closes, period)
            
        elif indicator.lower() == 'ema':
            period = params.get('period', 20)
            result = self._ema(closes, period)
            
        elif indicator.lower() == 'rsi':
            period = params.get('period', 14)
            result = self._rsi(closes, period)
            
        elif indicator.lower() == 'macd':
            fast = params.get('fast', 12)
            slow = params.get('slow', 26)
            signal = params.get('signal', 9)
            result = self._macd(closes, fast, slow, signal)
            
        elif indicator.lower() == 'bb':
            period = params.get('period', 20)
            std_dev = params.get('std_dev', 2)
            result = self._bollinger_bands(closes, period, std_dev)
            
        elif indicator.lower() == 'vwap':
            result = self._vwap(highs, lows, closes, volumes)
            
        elif indicator.lower() == 'atr':
            period = params.get('period', 14)
            result = self._atr(highs, lows, closes, period)
        
        # Store indicator data
        key = f"{symbol}_{timeframe}"
        if key not in self.indicators:
            self.indicators[key] = {}
        self.indicators[key][indicator] = result
        
        # Notify with indicator update
        update = ChartUpdate(
            symbol=symbol,
            update_type=UpdateType.INDICATOR,
            data={
                'indicator': indicator,
                'params': params,
                'values': result
            }
        )
        self._notify(symbol, timeframe, update)
        
        return result
    
    def _sma(self, data: List[float], period: int) -> List[float]:
        """Simple Moving Average"""
        result = [None] * (period - 1)
        for i in range(period - 1, len(data)):
            result.append(sum(data[i - period + 1:i + 1]) / period)
        return result
    
    def _ema(self, data: List[float], period: int) -> List[float]:
        """Exponential Moving Average"""
        multiplier = 2 / (period + 1)
        result = [None] * (period - 1)
        
        # First EMA is SMA
        ema = sum(data[:period]) / period
        result.append(ema)
        
        for price in data[period:]:
            ema = (price - ema) * multiplier + ema
            result.append(ema)
        
        return result
    
    def _rsi(self, data: List[float], period: int) -> List[float]:
        """Relative Strength Index"""
        deltas = [data[i] - data[i-1] for i in range(1, len(data))]
        
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        result = [None] * period
        
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        if avg_loss == 0:
            result.append(100)
        else:
            rs = avg_gain / avg_loss
            result.append(100 - (100 / (1 + rs)))
        
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss == 0:
                result.append(100)
            else:
                rs = avg_gain / avg_loss
                result.append(100 - (100 / (1 + rs)))
        
        return result
    
    def _macd(self, data: List[float], fast: int, slow: int, signal: int) -> Dict[str, List[float]]:
        """MACD indicator"""
        ema_fast = self._ema(data, fast)
        ema_slow = self._ema(data, slow)
        
        macd_line = []
        for f, s in zip(ema_fast, ema_slow):
            if f is not None and s is not None:
                macd_line.append(f - s)
            else:
                macd_line.append(None)
        
        # Filter out None values for signal line calculation
        valid_macd = [m for m in macd_line if m is not None]
        signal_line = [None] * (len(macd_line) - len(valid_macd))
        signal_line.extend(self._ema(valid_macd, signal))
        
        histogram = []
        for m, s in zip(macd_line, signal_line):
            if m is not None and s is not None:
                histogram.append(m - s)
            else:
                histogram.append(None)
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def _bollinger_bands(self, data: List[float], period: int, std_dev: float) -> Dict[str, List[float]]:
        """Bollinger Bands"""
        import statistics
        
        middle = self._sma(data, period)
        upper = []
        lower = []
        
        for i in range(len(data)):
            if middle[i] is None:
                upper.append(None)
                lower.append(None)
            else:
                std = statistics.stdev(data[max(0, i - period + 1):i + 1])
                upper.append(middle[i] + std_dev * std)
                lower.append(middle[i] - std_dev * std)
        
        return {
            'upper': upper,
            'middle': middle,
            'lower': lower
        }
    
    def _vwap(self, highs: List[float], lows: List[float], 
             closes: List[float], volumes: List[float]) -> List[float]:
        """Volume Weighted Average Price"""
        typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
        
        result = []
        cum_vol = 0
        cum_pv = 0
        
        for tp, vol in zip(typical_prices, volumes):
            cum_vol += vol
            cum_pv += tp * vol
            
            if cum_vol > 0:
                result.append(cum_pv / cum_vol)
            else:
                result.append(tp)
        
        return result
    
    def _atr(self, highs: List[float], lows: List[float], 
            closes: List[float], period: int) -> List[float]:
        """Average True Range"""
        tr = []
        for i in range(len(highs)):
            if i == 0:
                tr.append(highs[i] - lows[i])
            else:
                tr.append(max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i-1]),
                    abs(lows[i] - closes[i-1])
                ))
        
        return self._sma(tr, period)
    
    def get_bars(self, symbol: str, timeframe: str) -> List[ChartBar]:
        """Get bars for symbol/timeframe"""
        if symbol in self.charts and timeframe in self.charts[symbol]:
            return self.charts[symbol][timeframe]
        return []
    
    def get_chart_state(self, symbol: str, timeframe: str) -> Dict:
        """Get full chart state for rendering"""
        bars = self.get_bars(symbol, timeframe)
        key = f"{symbol}_{timeframe}"
        
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'bars': [b.to_dict() for b in bars],
            'indicators': self.indicators.get(key, {}),
            'last_price': self.last_prices.get(symbol, 0)
        }
    
    def add_annotation(self, symbol: str, timeframe: str,
                      annotation_type: str,
                      time: int,
                      price: float,
                      text: str = "",
                      color: str = "#ffffff"):
        """Add annotation to chart"""
        update = ChartUpdate(
            symbol=symbol,
            update_type=UpdateType.ANNOTATION,
            data={
                'type': annotation_type,
                'time': time,
                'price': price,
                'text': text,
                'color': color
            }
        )
        self._notify(symbol, timeframe, update)


# JavaScript/Dash integration code
REALTIME_CHART_JS = '''
// Real-time chart update handler for Dash
window.dashRealTimeChart = {
    charts: {},
    
    init: function(containerId, symbol, timeframe) {
        console.log('Initializing real-time chart:', symbol, timeframe);
        this.charts[containerId] = {
            symbol: symbol,
            timeframe: timeframe,
            data: []
        };
    },
    
    update: function(containerId, updateData) {
        const chart = this.charts[containerId];
        if (!chart) return;
        
        const update = JSON.parse(updateData);
        
        switch(update.type) {
            case 'new_bar':
                chart.data.push(update.data);
                break;
            case 'update_last':
                if (chart.data.length > 0) {
                    chart.data[chart.data.length - 1] = update.data;
                }
                break;
            case 'historical':
                chart.data = update.data;
                break;
        }
        
        // Trigger Dash callback or direct update
        if (window.Plotly && document.getElementById(containerId)) {
            this.updatePlotly(containerId, chart.data);
        }
    },
    
    updatePlotly: function(containerId, data) {
        const traces = [{
            type: 'candlestick',
            x: data.map(d => new Date(d.time * 1000)),
            open: data.map(d => d.open),
            high: data.map(d => d.high),
            low: data.map(d => d.low),
            close: data.map(d => d.close),
            increasing: {line: {color: '#26a69a'}},
            decreasing: {line: {color: '#ef5350'}}
        }];
        
        const layout = {
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            xaxis: {color: '#888'},
            yaxis: {color: '#888'},
            margin: {t: 10, b: 30, l: 50, r: 10}
        };
        
        Plotly.react(containerId, traces, layout);
    }
};
'''


# Singleton instance
_chart_manager = None

def get_chart_manager() -> RealTimeChartManager:
    global _chart_manager
    if _chart_manager is None:
        _chart_manager = RealTimeChartManager()
    return _chart_manager
