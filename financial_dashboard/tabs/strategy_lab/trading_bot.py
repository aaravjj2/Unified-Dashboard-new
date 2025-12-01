"""
Strategy Lab Trading Bot Engine
===============================

Live trading bot implementation for Strategy Lab with:
- Alpaca API integration for paper/live trading
- Bot templates similar to Alpha Vantage
- Automated strategy execution
- Position management
- Real-time monitoring

Author: Enhanced Dashboard Team
Date: December 2025
"""

import logging
import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
import queue

logger = logging.getLogger(__name__)

# Try to import Alpaca
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, GetOrdersRequest
    from alpaca.trading.enums import OrderSide, TimeInForce, OrderStatus, QueryOrderStatus
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    logger.warning("Alpaca SDK not available. Install with: pip install alpaca-py")


class BotStatus(Enum):
    """Bot execution status."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class SignalType(Enum):
    """Trading signal types."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


@dataclass
class TradingSignal:
    """Represents a trading signal from a strategy."""
    ticker: str
    signal_type: SignalType
    price: float
    quantity: int
    confidence: float
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)


@dataclass
class BotConfig:
    """Configuration for a trading bot."""
    name: str
    strategy_type: str
    tickers: List[str]
    max_position_size: float = 0.10  # 10% of portfolio per position
    max_positions: int = 10
    stop_loss_pct: float = 0.05  # 5% stop loss
    take_profit_pct: float = 0.15  # 15% take profit
    rebalance_interval: int = 3600  # Seconds between rebalance checks
    paper_trading: bool = True
    enabled: bool = True
    parameters: Dict = field(default_factory=dict)


class AlpacaConnector:
    """
    Alpaca API connector for Strategy Lab.
    
    Supports both paper and live trading with comprehensive
    order management and position tracking.
    """
    
    def __init__(self, api_key: str = None, api_secret: str = None, paper: bool = True):
        """
        Initialize Alpaca connector.
        
        Args:
            api_key: Alpaca API key (uses env var if not provided)
            api_secret: Alpaca API secret (uses env var if not provided)
            paper: Use paper trading endpoint
        """
        # Load keys from environment if not provided
        self.api_key = api_key or os.getenv('ALPACA3_KEY') or os.getenv('STRATEGY_LAB_ALPACA_KEY')
        self.api_secret = api_secret or os.getenv('ALPACA3_SECRET') or os.getenv('STRATEGY_LAB_ALPACA_SECRET')
        self.paper = paper
        
        if not self.api_key or not self.api_secret:
            raise ValueError("Alpaca API credentials not provided. Set ALPACA3_KEY and ALPACA3_SECRET environment variables.")
        
        self.trading_client = None
        self.data_client = None
        self._connected = False
        
        self._connect()
    
    def _connect(self):
        """Establish connection to Alpaca."""
        if not ALPACA_AVAILABLE:
            raise ImportError("Alpaca SDK not available. Install with: pip install alpaca-py")
        
        try:
            self.trading_client = TradingClient(
                api_key=self.api_key,
                secret_key=self.api_secret,
                paper=self.paper
            )
            
            self.data_client = StockHistoricalDataClient(
                api_key=self.api_key,
                secret_key=self.api_secret
            )
            
            # Verify connection
            account = self.trading_client.get_account()
            self._connected = True
            logger.info(f"✅ Connected to Alpaca {'Paper' if self.paper else 'Live'} Trading")
            logger.info(f"   Account: {account.account_number}, Equity: ${float(account.equity):,.2f}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Alpaca: {e}")
            self._connected = False
            raise
    
    def get_account(self) -> Dict:
        """Get account information."""
        if not self._connected:
            raise ConnectionError("Not connected to Alpaca")
        
        account = self.trading_client.get_account()
        return {
            "account_number": account.account_number,
            "status": account.status.value if hasattr(account.status, 'value') else str(account.status),
            "equity": float(account.equity),
            "buying_power": float(account.buying_power),
            "cash": float(account.cash),
            "portfolio_value": float(account.portfolio_value),
            "pattern_day_trader": account.pattern_day_trader,
            "trading_blocked": account.trading_blocked,
            "daytrade_count": account.daytrade_count
        }
    
    def get_positions(self) -> List[Dict]:
        """Get all open positions."""
        if not self._connected:
            raise ConnectionError("Not connected to Alpaca")
        
        positions = self.trading_client.get_all_positions()
        return [{
            "symbol": p.symbol,
            "qty": float(p.qty),
            "side": p.side.value if hasattr(p.side, 'value') else str(p.side),
            "market_value": float(p.market_value),
            "cost_basis": float(p.cost_basis),
            "unrealized_pl": float(p.unrealized_pl),
            "unrealized_plpc": float(p.unrealized_plpc),
            "current_price": float(p.current_price),
            "avg_entry_price": float(p.avg_entry_price)
        } for p in positions]
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get position for a specific symbol."""
        try:
            position = self.trading_client.get_open_position(symbol)
            return {
                "symbol": position.symbol,
                "qty": float(position.qty),
                "side": position.side.value if hasattr(position.side, 'value') else str(position.side),
                "market_value": float(position.market_value),
                "unrealized_pl": float(position.unrealized_pl),
                "current_price": float(position.current_price)
            }
        except Exception:
            return None
    
    def submit_market_order(self, symbol: str, qty: int, side: str) -> Dict:
        """
        Submit a market order.
        
        Args:
            symbol: Stock symbol
            qty: Number of shares
            side: 'buy' or 'sell'
            
        Returns:
            Order details
        """
        if not self._connected:
            raise ConnectionError("Not connected to Alpaca")
        
        order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
        
        order_request = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            time_in_force=TimeInForce.DAY
        )
        
        order = self.trading_client.submit_order(order_request)
        
        logger.info(f"📤 Order submitted: {side.upper()} {qty} {symbol}")
        
        return {
            "id": str(order.id),
            "symbol": order.symbol,
            "qty": float(order.qty),
            "side": order.side.value if hasattr(order.side, 'value') else str(order.side),
            "type": order.type.value if hasattr(order.type, 'value') else str(order.type),
            "status": order.status.value if hasattr(order.status, 'value') else str(order.status),
            "submitted_at": str(order.submitted_at)
        }
    
    def submit_limit_order(self, symbol: str, qty: int, side: str, limit_price: float) -> Dict:
        """Submit a limit order."""
        if not self._connected:
            raise ConnectionError("Not connected to Alpaca")
        
        order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
        
        order_request = LimitOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            time_in_force=TimeInForce.DAY,
            limit_price=limit_price
        )
        
        order = self.trading_client.submit_order(order_request)
        
        logger.info(f"📤 Limit order submitted: {side.upper()} {qty} {symbol} @ ${limit_price}")
        
        return {
            "id": str(order.id),
            "symbol": order.symbol,
            "qty": float(order.qty),
            "side": order.side.value if hasattr(order.side, 'value') else str(order.side),
            "limit_price": float(order.limit_price),
            "status": order.status.value if hasattr(order.status, 'value') else str(order.status)
        }
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        try:
            self.trading_client.cancel_order_by_id(order_id)
            logger.info(f"❌ Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    def get_orders(self, status: str = "open") -> List[Dict]:
        """Get orders by status."""
        if not self._connected:
            raise ConnectionError("Not connected to Alpaca")
        
        # Map status string to enum
        status_map = {
            "open": QueryOrderStatus.OPEN,
            "closed": QueryOrderStatus.CLOSED,
            "all": QueryOrderStatus.ALL
        }
        query_status = status_map.get(status.lower(), QueryOrderStatus.OPEN)
        
        request = GetOrdersRequest(status=query_status)
        orders = self.trading_client.get_orders(request)
        
        return [{
            "id": str(o.id),
            "symbol": o.symbol,
            "qty": float(o.qty) if o.qty else 0,
            "filled_qty": float(o.filled_qty) if o.filled_qty else 0,
            "side": o.side.value if hasattr(o.side, 'value') else str(o.side),
            "type": o.type.value if hasattr(o.type, 'value') else str(o.type),
            "status": o.status.value if hasattr(o.status, 'value') else str(o.status),
            "submitted_at": str(o.submitted_at)
        } for o in orders]
    
    def close_position(self, symbol: str) -> Dict:
        """Close all shares of a position."""
        try:
            self.trading_client.close_position(symbol)
            logger.info(f"📤 Position closed: {symbol}")
            return {"success": True, "symbol": symbol}
        except Exception as e:
            logger.error(f"Failed to close position {symbol}: {e}")
            return {"success": False, "error": str(e)}
    
    def close_all_positions(self) -> Dict:
        """Close all open positions."""
        try:
            self.trading_client.close_all_positions(cancel_orders=True)
            logger.info("📤 All positions closed")
            return {"success": True}
        except Exception as e:
            logger.error(f"Failed to close all positions: {e}")
            return {"success": False, "error": str(e)}
    
    def get_bars(self, symbol: str, timeframe: str = "1Day", limit: int = 100) -> List[Dict]:
        """Get historical bars for a symbol."""
        if not self._connected:
            raise ConnectionError("Not connected to Alpaca")
        
        tf_map = {
            "1Min": TimeFrame.Minute,
            "5Min": TimeFrame.Minute,
            "15Min": TimeFrame.Minute,
            "1Hour": TimeFrame.Hour,
            "1Day": TimeFrame.Day
        }
        tf = tf_map.get(timeframe, TimeFrame.Day)
        
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=tf,
            limit=limit
        )
        
        bars = self.data_client.get_stock_bars(request)
        
        return [{
            "timestamp": str(bar.timestamp),
            "open": float(bar.open),
            "high": float(bar.high),
            "low": float(bar.low),
            "close": float(bar.close),
            "volume": int(bar.volume)
        } for bar in bars[symbol]]


class TradingBot:
    """
    Automated trading bot for Strategy Lab.
    
    Implements various strategy templates with automated execution.
    """
    
    def __init__(self, config: BotConfig, connector: AlpacaConnector = None):
        """
        Initialize trading bot.
        
        Args:
            config: Bot configuration
            connector: Alpaca connector (creates one if not provided)
        """
        self.config = config
        self.connector = connector or AlpacaConnector(paper=config.paper_trading)
        
        self.status = BotStatus.IDLE
        self.signals_queue = queue.Queue()
        self.trade_history = []
        self.last_rebalance = None
        self._stop_event = threading.Event()
        self._thread = None
        
        logger.info(f"🤖 Trading bot initialized: {config.name}")
    
    def start(self):
        """Start the trading bot."""
        if self.status == BotStatus.RUNNING:
            logger.warning("Bot is already running")
            return
        
        self.status = BotStatus.RUNNING
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"🚀 Bot started: {self.config.name}")
    
    def stop(self):
        """Stop the trading bot."""
        self.status = BotStatus.STOPPED
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info(f"🛑 Bot stopped: {self.config.name}")
    
    def pause(self):
        """Pause the trading bot."""
        self.status = BotStatus.PAUSED
        logger.info(f"⏸️ Bot paused: {self.config.name}")
    
    def resume(self):
        """Resume the trading bot."""
        if self.status == BotStatus.PAUSED:
            self.status = BotStatus.RUNNING
            logger.info(f"▶️ Bot resumed: {self.config.name}")
    
    def _run_loop(self):
        """Main bot execution loop."""
        while not self._stop_event.is_set():
            try:
                if self.status == BotStatus.PAUSED:
                    time.sleep(1)
                    continue
                
                # Check if it's time to rebalance
                now = datetime.now()
                if self.last_rebalance is None or \
                   (now - self.last_rebalance).seconds >= self.config.rebalance_interval:
                    
                    # Generate signals
                    signals = self._generate_signals()
                    
                    # Execute signals
                    for signal in signals:
                        self._execute_signal(signal)
                    
                    self.last_rebalance = now
                
                # Check stop losses and take profits
                self._check_exit_conditions()
                
                # Sleep before next iteration
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Bot error: {e}")
                self.status = BotStatus.ERROR
                time.sleep(60)
    
    def _generate_signals(self) -> List[TradingSignal]:
        """Generate trading signals based on strategy."""
        signals = []
        
        strategy = self.config.strategy_type.lower()
        
        for ticker in self.config.tickers:
            try:
                if strategy == "momentum":
                    signal = self._momentum_signal(ticker)
                elif strategy == "mean_reversion":
                    signal = self._mean_reversion_signal(ticker)
                elif strategy == "breakout":
                    signal = self._breakout_signal(ticker)
                elif strategy == "trend_following":
                    signal = self._trend_following_signal(ticker)
                else:
                    signal = self._default_signal(ticker)
                
                if signal and signal.signal_type != SignalType.HOLD:
                    signals.append(signal)
                    
            except Exception as e:
                logger.warning(f"Failed to generate signal for {ticker}: {e}")
        
        return signals
    
    def _momentum_signal(self, ticker: str) -> Optional[TradingSignal]:
        """Generate momentum-based signal."""
        try:
            bars = self.connector.get_bars(ticker, "1Day", 50)
            if len(bars) < 50:
                return None
            
            closes = [b['close'] for b in bars]
            
            # Calculate momentum indicators
            sma_20 = sum(closes[-20:]) / 20
            sma_50 = sum(closes) / 50
            current_price = closes[-1]
            
            # RSI calculation
            gains = []
            losses = []
            for i in range(1, 15):
                change = closes[-i] - closes[-i-1]
                if change > 0:
                    gains.append(change)
                else:
                    losses.append(abs(change))
            
            avg_gain = sum(gains) / 14 if gains else 0
            avg_loss = sum(losses) / 14 if losses else 0.001
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            # Signal generation
            if current_price > sma_20 > sma_50 and rsi < 70:
                return TradingSignal(
                    ticker=ticker,
                    signal_type=SignalType.BUY,
                    price=current_price,
                    quantity=self._calculate_position_size(current_price),
                    confidence=min(0.9, 0.5 + (current_price - sma_20) / sma_20),
                    reason=f"Bullish momentum: Price > SMA20 > SMA50, RSI={rsi:.1f}"
                )
            elif current_price < sma_20 < sma_50:
                return TradingSignal(
                    ticker=ticker,
                    signal_type=SignalType.SELL,
                    price=current_price,
                    quantity=self._calculate_position_size(current_price),
                    confidence=min(0.9, 0.5 + (sma_20 - current_price) / sma_20),
                    reason=f"Bearish momentum: Price < SMA20 < SMA50"
                )
            
            return TradingSignal(
                ticker=ticker,
                signal_type=SignalType.HOLD,
                price=current_price,
                quantity=0,
                confidence=0.5,
                reason="No clear momentum signal"
            )
            
        except Exception as e:
            logger.warning(f"Momentum signal error for {ticker}: {e}")
            return None
    
    def _mean_reversion_signal(self, ticker: str) -> Optional[TradingSignal]:
        """Generate mean reversion signal."""
        try:
            bars = self.connector.get_bars(ticker, "1Day", 30)
            if len(bars) < 20:
                return None
            
            closes = [b['close'] for b in bars]
            current_price = closes[-1]
            
            # Bollinger Bands
            sma_20 = sum(closes[-20:]) / 20
            std = (sum((c - sma_20) ** 2 for c in closes[-20:]) / 20) ** 0.5
            upper_band = sma_20 + 2 * std
            lower_band = sma_20 - 2 * std
            
            # RSI
            gains = []
            losses = []
            for i in range(1, 15):
                change = closes[-i] - closes[-i-1]
                if change > 0:
                    gains.append(change)
                else:
                    losses.append(abs(change))
            
            avg_gain = sum(gains) / 14 if gains else 0
            avg_loss = sum(losses) / 14 if losses else 0.001
            rsi = 100 - (100 / (1 + avg_gain / avg_loss))
            
            if current_price < lower_band and rsi < 30:
                return TradingSignal(
                    ticker=ticker,
                    signal_type=SignalType.BUY,
                    price=current_price,
                    quantity=self._calculate_position_size(current_price),
                    confidence=min(0.85, 0.5 + (lower_band - current_price) / current_price),
                    reason=f"Oversold: Price below lower BB, RSI={rsi:.1f}"
                )
            elif current_price > upper_band and rsi > 70:
                return TradingSignal(
                    ticker=ticker,
                    signal_type=SignalType.SELL,
                    price=current_price,
                    quantity=self._calculate_position_size(current_price),
                    confidence=min(0.85, 0.5 + (current_price - upper_band) / current_price),
                    reason=f"Overbought: Price above upper BB, RSI={rsi:.1f}"
                )
            
            return TradingSignal(
                ticker=ticker,
                signal_type=SignalType.HOLD,
                price=current_price,
                quantity=0,
                confidence=0.5,
                reason="No mean reversion signal"
            )
            
        except Exception as e:
            logger.warning(f"Mean reversion signal error for {ticker}: {e}")
            return None
    
    def _breakout_signal(self, ticker: str) -> Optional[TradingSignal]:
        """Generate breakout signal."""
        try:
            bars = self.connector.get_bars(ticker, "1Day", 30)
            if len(bars) < 20:
                return None
            
            current_price = bars[-1]['close']
            
            # 20-day high/low
            highs = [b['high'] for b in bars[-20:]]
            lows = [b['low'] for b in bars[-20:]]
            high_20 = max(highs)
            low_20 = min(lows)
            
            # Volume confirmation
            volumes = [b['volume'] for b in bars[-20:]]
            avg_volume = sum(volumes) / 20
            current_volume = bars[-1]['volume']
            volume_ratio = current_volume / avg_volume
            
            if current_price > high_20 and volume_ratio > 1.5:
                return TradingSignal(
                    ticker=ticker,
                    signal_type=SignalType.BUY,
                    price=current_price,
                    quantity=self._calculate_position_size(current_price),
                    confidence=min(0.9, 0.6 + volume_ratio * 0.1),
                    reason=f"Bullish breakout above 20-day high with {volume_ratio:.1f}x volume"
                )
            elif current_price < low_20 and volume_ratio > 1.5:
                return TradingSignal(
                    ticker=ticker,
                    signal_type=SignalType.SELL,
                    price=current_price,
                    quantity=self._calculate_position_size(current_price),
                    confidence=min(0.9, 0.6 + volume_ratio * 0.1),
                    reason=f"Bearish breakdown below 20-day low"
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"Breakout signal error for {ticker}: {e}")
            return None
    
    def _trend_following_signal(self, ticker: str) -> Optional[TradingSignal]:
        """Generate trend following signal."""
        try:
            bars = self.connector.get_bars(ticker, "1Day", 60)
            if len(bars) < 50:
                return None
            
            closes = [b['close'] for b in bars]
            current_price = closes[-1]
            
            # EMA calculations
            ema_12 = self._calculate_ema(closes, 12)
            ema_26 = self._calculate_ema(closes, 26)
            ema_50 = self._calculate_ema(closes, 50)
            
            # MACD
            macd = ema_12 - ema_26
            
            # Trend strength
            atr = self._calculate_atr(bars, 14)
            trend_strength = abs(ema_12 - ema_50) / atr if atr > 0 else 0
            
            if ema_12 > ema_26 > ema_50 and macd > 0:
                return TradingSignal(
                    ticker=ticker,
                    signal_type=SignalType.BUY,
                    price=current_price,
                    quantity=self._calculate_position_size(current_price),
                    confidence=min(0.9, 0.5 + trend_strength * 0.1),
                    reason=f"Strong uptrend: EMAs aligned, MACD positive"
                )
            elif ema_12 < ema_26 < ema_50 and macd < 0:
                return TradingSignal(
                    ticker=ticker,
                    signal_type=SignalType.SELL,
                    price=current_price,
                    quantity=self._calculate_position_size(current_price),
                    confidence=min(0.9, 0.5 + trend_strength * 0.1),
                    reason=f"Strong downtrend: EMAs aligned, MACD negative"
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"Trend following signal error for {ticker}: {e}")
            return None
    
    def _default_signal(self, ticker: str) -> Optional[TradingSignal]:
        """Default signal generator (simple SMA crossover)."""
        return self._momentum_signal(ticker)
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate EMA."""
        if len(prices) < period:
            return prices[-1]
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def _calculate_atr(self, bars: List[Dict], period: int = 14) -> float:
        """Calculate Average True Range."""
        if len(bars) < period + 1:
            return 0
        
        trs = []
        for i in range(1, len(bars)):
            high = bars[i]['high']
            low = bars[i]['low']
            prev_close = bars[i-1]['close']
            
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        
        return sum(trs[-period:]) / period
    
    def _calculate_position_size(self, price: float) -> int:
        """Calculate position size based on account and config."""
        try:
            account = self.connector.get_account()
            equity = account['equity']
            
            max_value = equity * self.config.max_position_size
            shares = int(max_value / price)
            
            return max(1, shares)
        except Exception:
            return 10  # Default to 10 shares
    
    def _execute_signal(self, signal: TradingSignal):
        """Execute a trading signal."""
        try:
            if signal.signal_type == SignalType.BUY:
                # Check if we already have a position
                position = self.connector.get_position(signal.ticker)
                if position:
                    logger.info(f"Already have position in {signal.ticker}, skipping buy")
                    return
                
                # Check max positions
                positions = self.connector.get_positions()
                if len(positions) >= self.config.max_positions:
                    logger.info(f"Max positions reached ({self.config.max_positions}), skipping buy")
                    return
                
                # Submit buy order
                order = self.connector.submit_market_order(
                    symbol=signal.ticker,
                    qty=signal.quantity,
                    side='buy'
                )
                
                self.trade_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "signal": signal.signal_type.value,
                    "ticker": signal.ticker,
                    "price": signal.price,
                    "quantity": signal.quantity,
                    "reason": signal.reason,
                    "order_id": order['id']
                })
                
            elif signal.signal_type == SignalType.SELL:
                # Check if we have a position to sell
                position = self.connector.get_position(signal.ticker)
                if not position:
                    logger.info(f"No position in {signal.ticker}, skipping sell")
                    return
                
                # Close the position
                result = self.connector.close_position(signal.ticker)
                
                self.trade_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "signal": signal.signal_type.value,
                    "ticker": signal.ticker,
                    "price": signal.price,
                    "reason": signal.reason,
                    "result": result
                })
                
        except Exception as e:
            logger.error(f"Failed to execute signal: {e}")
    
    def _check_exit_conditions(self):
        """Check stop loss and take profit conditions."""
        try:
            positions = self.connector.get_positions()
            
            for position in positions:
                ticker = position['symbol']
                pnl_pct = position['unrealized_plpc']
                
                # Stop loss check
                if pnl_pct <= -self.config.stop_loss_pct:
                    logger.info(f"🛑 Stop loss triggered for {ticker}: {pnl_pct:.2%}")
                    self.connector.close_position(ticker)
                    
                    self.trade_history.append({
                        "timestamp": datetime.now().isoformat(),
                        "signal": "stop_loss",
                        "ticker": ticker,
                        "pnl_pct": pnl_pct
                    })
                
                # Take profit check
                elif pnl_pct >= self.config.take_profit_pct:
                    logger.info(f"🎯 Take profit triggered for {ticker}: {pnl_pct:.2%}")
                    self.connector.close_position(ticker)
                    
                    self.trade_history.append({
                        "timestamp": datetime.now().isoformat(),
                        "signal": "take_profit",
                        "ticker": ticker,
                        "pnl_pct": pnl_pct
                    })
                    
        except Exception as e:
            logger.warning(f"Error checking exit conditions: {e}")
    
    def get_status(self) -> Dict:
        """Get bot status and statistics."""
        try:
            account = self.connector.get_account()
            positions = self.connector.get_positions()
            
            return {
                "name": self.config.name,
                "status": self.status.value,
                "strategy": self.config.strategy_type,
                "tickers": self.config.tickers,
                "account_equity": account['equity'],
                "buying_power": account['buying_power'],
                "open_positions": len(positions),
                "positions": positions,
                "trade_count": len(self.trade_history),
                "last_rebalance": self.last_rebalance.isoformat() if self.last_rebalance else None,
                "config": {
                    "max_position_size": self.config.max_position_size,
                    "stop_loss_pct": self.config.stop_loss_pct,
                    "take_profit_pct": self.config.take_profit_pct,
                    "paper_trading": self.config.paper_trading
                }
            }
        except Exception as e:
            return {
                "name": self.config.name,
                "status": self.status.value,
                "error": str(e)
            }


class BotTemplates:
    """Pre-configured bot templates similar to Alpha Vantage."""
    
    @staticmethod
    def momentum_bot(name: str = "Momentum Bot", tickers: List[str] = None) -> BotConfig:
        """Momentum trading bot template."""
        return BotConfig(
            name=name,
            strategy_type="momentum",
            tickers=tickers or ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA'],
            max_position_size=0.10,
            max_positions=10,
            stop_loss_pct=0.05,
            take_profit_pct=0.15,
            rebalance_interval=3600,
            paper_trading=True,
            parameters={
                "fast_sma": 20,
                "slow_sma": 50,
                "rsi_period": 14,
                "rsi_overbought": 70,
                "rsi_oversold": 30
            }
        )
    
    @staticmethod
    def mean_reversion_bot(name: str = "Mean Reversion Bot", tickers: List[str] = None) -> BotConfig:
        """Mean reversion trading bot template."""
        return BotConfig(
            name=name,
            strategy_type="mean_reversion",
            tickers=tickers or ['SPY', 'QQQ', 'IWM', 'DIA'],
            max_position_size=0.15,
            max_positions=5,
            stop_loss_pct=0.03,
            take_profit_pct=0.08,
            rebalance_interval=1800,
            paper_trading=True,
            parameters={
                "bb_period": 20,
                "bb_std": 2.0,
                "rsi_period": 14
            }
        )
    
    @staticmethod
    def breakout_bot(name: str = "Breakout Bot", tickers: List[str] = None) -> BotConfig:
        """Breakout trading bot template."""
        return BotConfig(
            name=name,
            strategy_type="breakout",
            tickers=tickers or ['TSLA', 'AMD', 'COIN', 'MARA', 'RIOT'],
            max_position_size=0.08,
            max_positions=8,
            stop_loss_pct=0.07,
            take_profit_pct=0.20,
            rebalance_interval=1800,
            paper_trading=True,
            parameters={
                "lookback_period": 20,
                "volume_multiplier": 1.5
            }
        )
    
    @staticmethod
    def trend_following_bot(name: str = "Trend Following Bot", tickers: List[str] = None) -> BotConfig:
        """Trend following trading bot template."""
        return BotConfig(
            name=name,
            strategy_type="trend_following",
            tickers=tickers or ['SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA', 'GOOGL'],
            max_position_size=0.12,
            max_positions=8,
            stop_loss_pct=0.06,
            take_profit_pct=0.25,
            rebalance_interval=7200,
            paper_trading=True,
            parameters={
                "ema_fast": 12,
                "ema_slow": 26,
                "ema_signal": 9
            }
        )
    
    @staticmethod
    def sector_rotation_bot(name: str = "Sector Rotation Bot") -> BotConfig:
        """Sector rotation trading bot template."""
        return BotConfig(
            name=name,
            strategy_type="momentum",
            tickers=['XLK', 'XLF', 'XLV', 'XLE', 'XLI', 'XLY', 'XLP', 'XLU', 'XLB', 'XLRE', 'XLC'],
            max_position_size=0.20,
            max_positions=5,
            stop_loss_pct=0.04,
            take_profit_pct=0.12,
            rebalance_interval=86400,  # Daily
            paper_trading=True,
            parameters={
                "lookback_period": 30,
                "top_n_sectors": 3
            }
        )


# Bot manager for handling multiple bots
class BotManager:
    """Manages multiple trading bots."""
    
    def __init__(self):
        self.bots: Dict[str, TradingBot] = {}
        self._connector = None
    
    def get_connector(self) -> AlpacaConnector:
        """Get or create shared Alpaca connector."""
        if self._connector is None:
            self._connector = AlpacaConnector(paper=True)
        return self._connector
    
    def create_bot(self, config: BotConfig) -> TradingBot:
        """Create a new trading bot."""
        bot = TradingBot(config, self.get_connector())
        self.bots[config.name] = bot
        return bot
    
    def start_bot(self, name: str):
        """Start a bot by name."""
        if name in self.bots:
            self.bots[name].start()
    
    def stop_bot(self, name: str):
        """Stop a bot by name."""
        if name in self.bots:
            self.bots[name].stop()
    
    def stop_all(self):
        """Stop all bots."""
        for bot in self.bots.values():
            bot.stop()
    
    def get_all_status(self) -> Dict[str, Dict]:
        """Get status of all bots."""
        return {name: bot.get_status() for name, bot in self.bots.items()}
    
    def remove_bot(self, name: str):
        """Remove a bot."""
        if name in self.bots:
            self.bots[name].stop()
            del self.bots[name]


# Singleton manager
_bot_manager = None

def get_bot_manager() -> BotManager:
    """Get or create the bot manager singleton."""
    global _bot_manager
    if _bot_manager is None:
        _bot_manager = BotManager()
    return _bot_manager
