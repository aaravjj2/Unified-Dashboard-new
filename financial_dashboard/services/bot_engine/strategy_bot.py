"""
Strategy Bot with RSI Logic
===========================

Implements trading strategies using AlphaVantage signals
and Alpaca execution.

RSI Strategy:
- RSI < 30 → Buy signal (oversold)
- RSI > 70 → Sell signal (overbought)

Author: Bot Engine Team
Date: December 2025
"""

import os
import json
import time
import logging
import threading
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .alpha_vantage import AlphaVantageClient, get_av_client
from .broker import AlpacaBroker, get_broker, Side, OrderType, OrderResult

logger = logging.getLogger(__name__)


class BotStatus(Enum):
    """Bot execution status."""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class SignalType(Enum):
    """Trading signal type."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class TradeLog:
    """Log entry for a trade."""
    timestamp: str
    ticker: str
    signal: str
    action: str
    quantity: float
    price: Optional[float]
    order_id: Optional[str]
    success: bool
    reason: str
    rsi_value: Optional[float] = None
    macd_value: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class BotConfig:
    """Configuration for a trading bot."""
    ticker: str
    strategy: str = "rsi"
    quantity: float = 1.0
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    macd_threshold: float = 0.0
    max_position_size: float = 100.0
    tick_interval: float = 60.0  # seconds between ticks
    paper_mode: bool = True
    deterministic: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BotConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class StrategyBot:
    """
    Trading Bot with RSI Strategy.
    
    Features:
    - RSI-based buy/sell signals
    - Optional MACD confirmation
    - Paper trading safety
    - Trade logging
    - Deterministic testing mode
    
    Usage:
        bot = StrategyBot(BotConfig(ticker='AAPL'))
        bot.start()
        ...
        bot.stop()
    """
    
    def __init__(
        self,
        config: BotConfig,
        av_client: AlphaVantageClient = None,
        broker: AlpacaBroker = None,
        log_path: str = None
    ):
        """
        Initialize strategy bot.
        
        Args:
            config: Bot configuration
            av_client: Alpha Vantage client (optional)
            broker: Alpaca broker (optional)
            log_path: Path for trade logs
        """
        self.config = config
        self.ticker = config.ticker.upper().strip()
        
        # Set deterministic from env if not specified
        if config.deterministic is None:
            config.deterministic = os.environ.get('BOT_DETERMINISTIC', '0') == '1'
        
        # Initialize clients
        self._av_client = av_client or get_av_client(deterministic=config.deterministic)
        self._broker = broker or get_broker(deterministic=config.deterministic)
        
        # State
        self._status = BotStatus.STOPPED
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_signal = SignalType.HOLD
        self._last_rsi: Optional[float] = None
        self._last_macd: Optional[Dict] = None
        
        # Trade log
        self._trade_logs: List[TradeLog] = []
        self._log_path = log_path or os.path.join(
            os.path.dirname(__file__),
            '..', '..', '..', 'reports', 'bot_phase', 'diagnostics',
            f'trade_log_{self.ticker}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )
        
        # Callbacks
        self._on_signal: Optional[Callable[[str, SignalType, float], None]] = None
        self._on_trade: Optional[Callable[[TradeLog], None]] = None
        self._on_status_change: Optional[Callable[[BotStatus], None]] = None
        
        logger.info(f"StrategyBot initialized for {self.ticker} (strategy={config.strategy})")
    
    @property
    def status(self) -> BotStatus:
        """Get current bot status."""
        return self._status
    
    @property
    def is_running(self) -> bool:
        """Check if bot is running."""
        return self._status == BotStatus.RUNNING
    
    @property
    def trade_logs(self) -> List[TradeLog]:
        """Get trade log history."""
        return self._trade_logs.copy()
    
    @property
    def last_signal(self) -> SignalType:
        """Get last generated signal."""
        return self._last_signal
    
    def set_callbacks(
        self,
        on_signal: Callable[[str, SignalType, float], None] = None,
        on_trade: Callable[[TradeLog], None] = None,
        on_status_change: Callable[[BotStatus], None] = None
    ):
        """Set callback functions for events."""
        self._on_signal = on_signal
        self._on_trade = on_trade
        self._on_status_change = on_status_change
    
    def _set_status(self, status: BotStatus):
        """Update status and notify."""
        self._status = status
        if self._on_status_change:
            self._on_status_change(status)
        logger.info(f"Bot {self.ticker} status: {status.value}")
    
    def _calculate_rsi_signal(self, rsi_value: float) -> SignalType:
        """
        Calculate signal from RSI value.
        
        RSI < oversold (30) → BUY
        RSI > overbought (70) → SELL
        Otherwise → HOLD
        """
        if rsi_value < self.config.rsi_oversold:
            return SignalType.BUY
        elif rsi_value > self.config.rsi_overbought:
            return SignalType.SELL
        return SignalType.HOLD
    
    def _calculate_macd_signal(self, macd_data: Dict) -> SignalType:
        """
        Calculate signal from MACD.
        
        MACD > Signal → BUY
        MACD < Signal → SELL
        """
        latest = macd_data.get('latest', {})
        macd = latest.get('macd', 0)
        signal = latest.get('signal', 0)
        histogram = latest.get('histogram', 0)
        
        if histogram > self.config.macd_threshold:
            return SignalType.BUY
        elif histogram < -self.config.macd_threshold:
            return SignalType.SELL
        return SignalType.HOLD
    
    def run_tick(self) -> Optional[TradeLog]:
        """
        Execute one tick of the strategy.
        
        Returns:
            TradeLog if a trade was executed, None otherwise
        """
        timestamp = datetime.now().isoformat()
        
        try:
            # Get RSI
            rsi_data = self._av_client.get_rsi(self.ticker)
            rsi_value = rsi_data.get('latest_value', 50)
            self._last_rsi = rsi_value
            
            # Calculate signal
            if self.config.strategy == 'rsi':
                signal = self._calculate_rsi_signal(rsi_value)
            elif self.config.strategy == 'macd':
                macd_data = self._av_client.get_macd(self.ticker)
                self._last_macd = macd_data
                signal = self._calculate_macd_signal(macd_data)
            elif self.config.strategy == 'rsi_macd':
                # Combined: RSI primary, MACD confirmation
                rsi_signal = self._calculate_rsi_signal(rsi_value)
                macd_data = self._av_client.get_macd(self.ticker)
                self._last_macd = macd_data
                macd_signal = self._calculate_macd_signal(macd_data)
                
                # Only act if both agree
                if rsi_signal == macd_signal and rsi_signal != SignalType.HOLD:
                    signal = rsi_signal
                else:
                    signal = SignalType.HOLD
            else:
                signal = SignalType.HOLD
            
            self._last_signal = signal
            
            # Notify signal callback
            if self._on_signal:
                self._on_signal(self.ticker, signal, rsi_value)
            
            logger.info(f"[{self.ticker}] RSI={rsi_value:.2f} → Signal: {signal.value}")
            
            # Execute trade if signal
            if signal == SignalType.HOLD:
                return None
            
            # Check position limits
            positions = self._broker.get_positions()
            current_position = next(
                (p for p in positions if p.ticker == self.ticker),
                None
            )
            
            current_qty = current_position.quantity if current_position else 0
            
            # Execute based on signal
            if signal == SignalType.BUY:
                # Check max position
                if current_qty >= self.config.max_position_size:
                    log = TradeLog(
                        timestamp=timestamp,
                        ticker=self.ticker,
                        signal=signal.value,
                        action='skip',
                        quantity=0,
                        price=None,
                        order_id=None,
                        success=False,
                        reason=f"Max position size reached ({current_qty})",
                        rsi_value=rsi_value
                    )
                    self._log_trade(log)
                    return log
                
                # Calculate buy quantity
                buy_qty = min(
                    self.config.quantity,
                    self.config.max_position_size - current_qty
                )
                
                result = self._broker.submit_order(
                    self.ticker,
                    Side.BUY,
                    buy_qty,
                    OrderType.MARKET
                )
                
                log = TradeLog(
                    timestamp=timestamp,
                    ticker=self.ticker,
                    signal=signal.value,
                    action='buy',
                    quantity=buy_qty,
                    price=result.filled_price,
                    order_id=result.order_id,
                    success=result.success,
                    reason=result.error or "RSI oversold buy",
                    rsi_value=rsi_value
                )
                
            else:  # SELL
                if current_qty <= 0:
                    log = TradeLog(
                        timestamp=timestamp,
                        ticker=self.ticker,
                        signal=signal.value,
                        action='skip',
                        quantity=0,
                        price=None,
                        order_id=None,
                        success=False,
                        reason="No position to sell",
                        rsi_value=rsi_value
                    )
                    self._log_trade(log)
                    return log
                
                # Sell configured quantity or all
                sell_qty = min(self.config.quantity, current_qty)
                
                result = self._broker.submit_order(
                    self.ticker,
                    Side.SELL,
                    sell_qty,
                    OrderType.MARKET
                )
                
                log = TradeLog(
                    timestamp=timestamp,
                    ticker=self.ticker,
                    signal=signal.value,
                    action='sell',
                    quantity=sell_qty,
                    price=result.filled_price,
                    order_id=result.order_id,
                    success=result.success,
                    reason=result.error or "RSI overbought sell",
                    rsi_value=rsi_value
                )
            
            self._log_trade(log)
            return log
            
        except Exception as e:
            logger.error(f"Tick error for {self.ticker}: {e}")
            log = TradeLog(
                timestamp=timestamp,
                ticker=self.ticker,
                signal='error',
                action='error',
                quantity=0,
                price=None,
                order_id=None,
                success=False,
                reason=str(e)
            )
            self._log_trade(log)
            return log
    
    def _log_trade(self, log: TradeLog):
        """Log a trade to history and file."""
        self._trade_logs.append(log)
        
        # Notify callback
        if self._on_trade:
            self._on_trade(log)
        
        # Save to file
        self._save_logs()
    
    def _save_logs(self):
        """Save trade logs to JSON file."""
        try:
            path = Path(self._log_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w') as f:
                json.dump(
                    [log.to_dict() for log in self._trade_logs],
                    f,
                    indent=2
                )
        except Exception as e:
            logger.error(f"Failed to save trade logs: {e}")
    
    def _run_loop(self):
        """Main bot loop (runs in thread)."""
        logger.info(f"Bot loop started for {self.ticker}")
        
        while not self._stop_event.is_set():
            if self._status == BotStatus.RUNNING:
                try:
                    self.run_tick()
                except Exception as e:
                    logger.error(f"Bot tick error: {e}")
                    self._set_status(BotStatus.ERROR)
            
            # Wait for next tick or stop
            self._stop_event.wait(timeout=self.config.tick_interval)
        
        logger.info(f"Bot loop stopped for {self.ticker}")
    
    def start(self):
        """Start the bot."""
        if self._status == BotStatus.RUNNING:
            logger.warning(f"Bot {self.ticker} already running")
            return
        
        self._stop_event.clear()
        self._set_status(BotStatus.RUNNING)
        
        self._thread = threading.Thread(
            target=self._run_loop,
            name=f"Bot-{self.ticker}",
            daemon=True
        )
        self._thread.start()
        
        logger.info(f"Bot {self.ticker} started")
    
    def stop(self):
        """Stop the bot."""
        if self._status == BotStatus.STOPPED:
            return
        
        self._stop_event.set()
        self._set_status(BotStatus.STOPPED)
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        logger.info(f"Bot {self.ticker} stopped")
    
    def pause(self):
        """Pause the bot (stays running but no trades)."""
        if self._status == BotStatus.RUNNING:
            self._set_status(BotStatus.PAUSED)
    
    def resume(self):
        """Resume a paused bot."""
        if self._status == BotStatus.PAUSED:
            self._set_status(BotStatus.RUNNING)
    
    def get_state(self) -> Dict[str, Any]:
        """Get current bot state."""
        return {
            'ticker': self.ticker,
            'status': self._status.value,
            'strategy': self.config.strategy,
            'last_signal': self._last_signal.value,
            'last_rsi': self._last_rsi,
            'trade_count': len(self._trade_logs),
            'config': self.config.to_dict()
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get trading statistics."""
        if not self._trade_logs:
            return {
                'total_trades': 0,
                'successful_trades': 0,
                'failed_trades': 0,
                'buy_count': 0,
                'sell_count': 0,
                'total_volume': 0
            }
        
        successful = [t for t in self._trade_logs if t.success]
        failed = [t for t in self._trade_logs if not t.success]
        buys = [t for t in self._trade_logs if t.action == 'buy' and t.success]
        sells = [t for t in self._trade_logs if t.action == 'sell' and t.success]
        
        return {
            'total_trades': len(self._trade_logs),
            'successful_trades': len(successful),
            'failed_trades': len(failed),
            'buy_count': len(buys),
            'sell_count': len(sells),
            'total_volume': sum(t.quantity for t in successful)
        }


class BotManager:
    """
    Manager for multiple trading bots.
    
    Usage:
        manager = BotManager()
        manager.create_bot('AAPL', 'rsi')
        manager.start_bot('AAPL')
    """
    
    def __init__(self):
        self._bots: Dict[str, StrategyBot] = {}
        self._lock = threading.Lock()
    
    def create_bot(
        self,
        ticker: str,
        strategy: str = 'rsi',
        **config_kwargs
    ) -> StrategyBot:
        """Create a new bot."""
        ticker = ticker.upper().strip()
        
        with self._lock:
            if ticker in self._bots:
                raise ValueError(f"Bot for {ticker} already exists")
            
            config = BotConfig(
                ticker=ticker,
                strategy=strategy,
                **config_kwargs
            )
            
            bot = StrategyBot(config)
            self._bots[ticker] = bot
            
            return bot
    
    def get_bot(self, ticker: str) -> Optional[StrategyBot]:
        """Get a bot by ticker."""
        return self._bots.get(ticker.upper().strip())
    
    def remove_bot(self, ticker: str):
        """Remove a bot."""
        ticker = ticker.upper().strip()
        
        with self._lock:
            if ticker in self._bots:
                self._bots[ticker].stop()
                del self._bots[ticker]
    
    def start_bot(self, ticker: str):
        """Start a specific bot."""
        bot = self.get_bot(ticker)
        if bot:
            bot.start()
    
    def stop_bot(self, ticker: str):
        """Stop a specific bot."""
        bot = self.get_bot(ticker)
        if bot:
            bot.stop()
    
    def stop_all(self):
        """Stop all bots."""
        with self._lock:
            for bot in self._bots.values():
                bot.stop()
    
    def get_all_states(self) -> List[Dict[str, Any]]:
        """Get state of all bots."""
        return [bot.get_state() for bot in self._bots.values()]
    
    def list_bots(self) -> List[str]:
        """List all bot tickers."""
        return list(self._bots.keys())


# Global bot manager
_bot_manager: Optional[BotManager] = None


def get_bot_manager() -> BotManager:
    """Get or create the global bot manager."""
    global _bot_manager
    if _bot_manager is None:
        _bot_manager = BotManager()
    return _bot_manager
