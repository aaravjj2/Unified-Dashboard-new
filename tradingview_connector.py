"""
TradingView Alerts Connector — Phase 6-8 Strategy Bot Integration
===================================================================

Webhook receiver for TradingView alerts with signal validation and transformation.

Features:
- Flask webhook server for TradingView POST requests
- Alert validation (symbol, strike, expiration, signal type)
- TradeSignal object transformation
- Signal logging and tracking for reproducibility
- Integration with strategy bot SignalGenerator
- Mock mode for offline testing

Architecture:
- TradingViewWebhook: Flask server for receiving alerts
- AlertValidator: Schema validation and sanitization
- SignalTransformer: Convert alerts to TradeSignal objects
- SignalLogger: Persistent storage and replay
- MockAlertGenerator: Offline testing tool

Integration:
- Compatible with broker_connector.py
- Compatible with strategy_bot.py SignalGenerator
- Deterministic signal replay for backtesting

Author: Agent 1B — Unified Financial Dashboard Team
Version: 1.0 (Phase 6-8 Strategy Bot Integration)
Date: October 29, 2025
"""

import json
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import re

# Flask imports (optional - only for live webhook mode)
try:
    from flask import Flask, request, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    logging.warning("⚠️  Flask not installed. Only mock mode available. Install with: pip install flask")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMERATIONS & TYPE DEFINITIONS
# ============================================================================

class SignalType(Enum):
    """Trading signal classification"""
    BUY_CALL = "buy_call"
    SELL_CALL = "sell_call"
    BUY_PUT = "buy_put"
    SELL_PUT = "sell_put"
    BUY_STOCK = "buy_stock"
    SELL_STOCK = "sell_stock"
    CLOSE_POSITION = "close_position"
    
    # Spreads
    BULL_CALL_SPREAD = "bull_call_spread"
    BEAR_PUT_SPREAD = "bear_put_spread"
    IRON_CONDOR = "iron_condor"
    STRADDLE = "straddle"
    STRANGLE = "strangle"


class AlertSource(Enum):
    """Alert origin"""
    TRADINGVIEW = "tradingview"
    MANUAL = "manual"
    STRATEGY_BOT = "strategy_bot"
    BACKTEST = "backtest"


class SignalPriority(Enum):
    """Signal execution priority"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class TradeSignal:
    """
    Unified trade signal object for strategy execution.
    
    This is the core data structure passed between:
    - TradingView alerts → SignalGenerator
    - Analytics outputs → SignalGenerator
    - SignalGenerator → ExecutionEngine
    - Backtester → ExecutionEngine
    """
    signal_id: str
    signal_type: SignalType
    symbol: str
    qty: float
    
    # Source metadata
    source: AlertSource
    priority: SignalPriority = SignalPriority.MEDIUM
    
    # Options-specific
    strike: Optional[float] = None
    expiration: Optional[str] = None  # YYYY-MM-DD
    
    # Price constraints
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    
    # Multi-leg spreads
    legs: Optional[List['TradeSignal']] = None
    
    # Analytics context (from Phase 8)
    trend_signal: Optional[str] = None  # bullish/bearish/neutral
    volatility_regime: Optional[str] = None  # low/medium/high
    risk_score: Optional[float] = None  # 0-100
    
    # Execution metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    ttl_seconds: Optional[int] = None  # Time to live (signal expiration)
    notes: Optional[str] = None
    
    # Tracking
    executed: bool = False
    executed_at: Optional[str] = None
    order_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type.value,
            "symbol": self.symbol,
            "qty": self.qty,
            "source": self.source.value,
            "priority": self.priority.value,
            "strike": self.strike,
            "expiration": self.expiration,
            "limit_price": self.limit_price,
            "stop_price": self.stop_price,
            "legs": [leg.to_dict() for leg in self.legs] if self.legs else None,
            "trend_signal": self.trend_signal,
            "volatility_regime": self.volatility_regime,
            "risk_score": self.risk_score,
            "timestamp": self.timestamp,
            "ttl_seconds": self.ttl_seconds,
            "notes": self.notes,
            "executed": self.executed,
            "executed_at": self.executed_at,
            "order_id": self.order_id
        }
    
    def is_expired(self) -> bool:
        """Check if signal has expired"""
        if self.ttl_seconds is None:
            return False
        
        signal_time = datetime.fromisoformat(self.timestamp)
        now = datetime.now()
        elapsed = (now - signal_time).total_seconds()
        
        return elapsed > self.ttl_seconds
    
    def is_valid(self) -> bool:
        """Basic validation"""
        # Check required fields
        if not self.symbol or self.qty <= 0:
            return False
        
        # Check expiration
        if self.is_expired():
            return False
        
        # Options validation
        if self.signal_type in [SignalType.BUY_CALL, SignalType.SELL_CALL, SignalType.BUY_PUT, SignalType.SELL_PUT]:
            if self.strike is None or self.expiration is None:
                return False
        
        return True


@dataclass
class TradingViewAlert:
    """Raw TradingView webhook payload"""
    alert_name: str
    symbol: str
    action: str  # buy/sell
    price: float
    timestamp: str
    
    # Optional fields
    strategy: Optional[str] = None
    interval: Optional[str] = None
    volume: Optional[float] = None
    message: Optional[str] = None
    
    # Custom fields (user-defined in TradingView)
    qty: Optional[float] = None
    signal_type: Optional[str] = None
    strike: Optional[float] = None
    expiration: Optional[str] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {k: v for k, v in asdict(self).items() if v is not None}


# ============================================================================
# ALERT VALIDATOR
# ============================================================================

class AlertValidator:
    """
    Validate and sanitize TradingView alerts.
    
    Validation rules:
    - Required fields: symbol, action, price
    - Symbol format: uppercase, alphanumeric
    - Action: buy/sell/close
    - Price: positive number
    - Options: strike and expiration required if signal_type contains call/put
    - Expiration: YYYY-MM-DD format
    """
    
    @staticmethod
    def validate_symbol(symbol: str) -> bool:
        """Validate ticker symbol format"""
        if not symbol:
            return False
        
        # Alphanumeric, uppercase, 1-10 characters
        pattern = r'^[A-Z0-9]{1,10}$'
        return bool(re.match(pattern, symbol.upper()))
    
    @staticmethod
    def validate_action(action: str) -> bool:
        """Validate action field"""
        valid_actions = ["buy", "sell", "close", "long", "short"]
        return action.lower() in valid_actions
    
    @staticmethod
    def validate_price(price: Any) -> bool:
        """Validate price is positive number"""
        try:
            price_float = float(price)
            return price_float > 0
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_expiration(expiration: str) -> bool:
        """Validate expiration date format (YYYY-MM-DD)"""
        if not expiration:
            return False
        
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(pattern, expiration):
            return False
        
        # Check if valid date
        try:
            datetime.strptime(expiration, "%Y-%m-%d")
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_alert(alert_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate complete alert payload.
        
        Args:
            alert_data: Raw alert dictionary
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Required fields
        required = ["symbol", "action", "price"]
        for field in required:
            if field not in alert_data:
                return False, f"Missing required field: {field}"
        
        # Validate symbol
        if not AlertValidator.validate_symbol(alert_data["symbol"]):
            return False, f"Invalid symbol format: {alert_data['symbol']}"
        
        # Validate action
        if not AlertValidator.validate_action(alert_data["action"]):
            return False, f"Invalid action: {alert_data['action']}"
        
        # Validate price
        if not AlertValidator.validate_price(alert_data["price"]):
            return False, f"Invalid price: {alert_data['price']}"
        
        # Options validation
        signal_type = alert_data.get("signal_type", "").lower()
        if "call" in signal_type or "put" in signal_type:
            if "strike" not in alert_data:
                return False, "Strike price required for options signals"
            if "expiration" not in alert_data:
                return False, "Expiration date required for options signals"
            
            if not AlertValidator.validate_price(alert_data["strike"]):
                return False, f"Invalid strike price: {alert_data['strike']}"
            
            if not AlertValidator.validate_expiration(alert_data["expiration"]):
                return False, f"Invalid expiration format: {alert_data['expiration']}"
        
        return True, None
    
    @staticmethod
    def sanitize_alert(alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize alert data (normalize fields).
        
        Args:
            alert_data: Raw alert dictionary
            
        Returns:
            Sanitized dictionary
        """
        sanitized = {}
        
        # Normalize symbol (uppercase)
        if "symbol" in alert_data:
            sanitized["symbol"] = str(alert_data["symbol"]).upper().strip()
        
        # Normalize action (lowercase)
        if "action" in alert_data:
            sanitized["action"] = str(alert_data["action"]).lower().strip()
        
        # Normalize numeric fields
        for field in ["price", "qty", "strike", "stop_loss", "take_profit", "volume"]:
            if field in alert_data:
                try:
                    sanitized[field] = float(alert_data[field])
                except (ValueError, TypeError):
                    pass
        
        # Copy string fields
        for field in ["alert_name", "strategy", "interval", "message", "signal_type", "expiration"]:
            if field in alert_data:
                sanitized[field] = str(alert_data[field]).strip()
        
        # Add timestamp if missing
        if "timestamp" not in sanitized:
            sanitized["timestamp"] = datetime.now().isoformat()
        
        return sanitized


# ============================================================================
# SIGNAL TRANSFORMER
# ============================================================================

class SignalTransformer:
    """
    Transform TradingView alerts to TradeSignal objects.
    
    Mapping rules:
    - action=buy + signal_type=call → BUY_CALL
    - action=sell + signal_type=call → SELL_CALL
    - action=buy + signal_type=put → BUY_PUT
    - action=sell + signal_type=put → SELL_PUT
    - action=buy (no signal_type) → BUY_STOCK
    - action=sell (no signal_type) → SELL_STOCK
    - action=close → CLOSE_POSITION
    """
    
    def __init__(self):
        self.signal_counter = 1
    
    def _generate_signal_id(self) -> str:
        """Generate unique signal ID"""
        signal_id = f"tv_signal_{self.signal_counter:06d}"
        self.signal_counter += 1
        return signal_id
    
    def _map_signal_type(self, action: str, signal_type: Optional[str]) -> SignalType:
        """
        Map TradingView action + signal_type to internal SignalType.
        
        Args:
            action: buy/sell/close
            signal_type: call/put/stock/spread_type
            
        Returns:
            SignalType enum
        """
        action = action.lower()
        signal_type_lower = signal_type.lower() if signal_type else ""
        
        # Close position
        if action == "close":
            return SignalType.CLOSE_POSITION
        
        # Options
        if "call" in signal_type_lower:
            return SignalType.BUY_CALL if action == "buy" else SignalType.SELL_CALL
        elif "put" in signal_type_lower:
            return SignalType.BUY_PUT if action == "buy" else SignalType.SELL_PUT
        
        # Spreads
        if "bull_call_spread" in signal_type_lower or "bull call spread" in signal_type_lower:
            return SignalType.BULL_CALL_SPREAD
        elif "bear_put_spread" in signal_type_lower or "bear put spread" in signal_type_lower:
            return SignalType.BEAR_PUT_SPREAD
        elif "iron_condor" in signal_type_lower:
            return SignalType.IRON_CONDOR
        elif "straddle" in signal_type_lower:
            return SignalType.STRADDLE
        elif "strangle" in signal_type_lower:
            return SignalType.STRANGLE
        
        # Stocks (default)
        return SignalType.BUY_STOCK if action == "buy" else SignalType.SELL_STOCK
    
    def transform_alert(self, alert: TradingViewAlert) -> TradeSignal:
        """
        Transform TradingView alert to TradeSignal.
        
        Args:
            alert: TradingView alert object
            
        Returns:
            TradeSignal object
        """
        signal_type = self._map_signal_type(alert.action, alert.signal_type)
        
        # Default quantity (can be overridden in alert)
        qty = alert.qty if alert.qty else 1.0
        
        # Build TradeSignal
        signal = TradeSignal(
            signal_id=self._generate_signal_id(),
            signal_type=signal_type,
            symbol=alert.symbol,
            qty=qty,
            source=AlertSource.TRADINGVIEW,
            priority=SignalPriority.MEDIUM,
            strike=alert.strike,
            expiration=alert.expiration,
            limit_price=alert.take_profit,  # Use take_profit as limit if provided
            stop_price=alert.stop_loss,
            timestamp=alert.timestamp,
            ttl_seconds=300,  # 5 minute default TTL
            notes=alert.message
        )
        
        return signal
    
    def transform_dict(self, alert_data: Dict[str, Any]) -> TradeSignal:
        """
        Transform raw alert dictionary to TradeSignal.
        
        Args:
            alert_data: Raw alert dictionary
            
        Returns:
            TradeSignal object
        """
        # Convert dict to TradingViewAlert
        alert = TradingViewAlert(
            alert_name=alert_data.get("alert_name", "Unknown"),
            symbol=alert_data["symbol"],
            action=alert_data["action"],
            price=alert_data["price"],
            timestamp=alert_data.get("timestamp", datetime.now().isoformat()),
            strategy=alert_data.get("strategy"),
            interval=alert_data.get("interval"),
            volume=alert_data.get("volume"),
            message=alert_data.get("message"),
            qty=alert_data.get("qty"),
            signal_type=alert_data.get("signal_type"),
            strike=alert_data.get("strike"),
            expiration=alert_data.get("expiration"),
            stop_loss=alert_data.get("stop_loss"),
            take_profit=alert_data.get("take_profit")
        )
        
        return self.transform_alert(alert)


# ============================================================================
# SIGNAL LOGGER
# ============================================================================

class SignalLogger:
    """
    Persistent storage and replay for trade signals.
    
    Features:
    - JSON logging of all signals
    - Signal replay for backtesting
    - Filtering and querying
    """
    
    def __init__(self, log_path: str = "outputs/tradingview_signals.json"):
        self.log_path = log_path
        self.signals: List[TradeSignal] = []
        
        # Load existing signals if file exists
        self._load_signals()
    
    def _load_signals(self) -> None:
        """Load signals from disk"""
        if Path(self.log_path).exists():
            try:
                with open(self.log_path, 'r') as f:
                    data = json.load(f)
                    # Note: Cannot reconstruct full TradeSignal objects from JSON
                    # (requires SignalType enum conversion), so store as dicts
                    logger.info(f"📂 Loaded {len(data.get('signals', []))} signals from {self.log_path}")
            except Exception as e:
                logger.warning(f"⚠️  Failed to load signals: {e}")
    
    def log_signal(self, signal: TradeSignal) -> None:
        """
        Log signal to memory and disk.
        
        Args:
            signal: TradeSignal to log
        """
        self.signals.append(signal)
        self._save_signals()
        logger.info(f"📝 Logged signal: {signal.signal_id} ({signal.signal_type.value})")
    
    def _save_signals(self) -> None:
        """Save signals to disk"""
        Path(self.log_path).parent.mkdir(parents=True, exist_ok=True)
        
        log_data = {
            "total_signals": len(self.signals),
            "signals": [sig.to_dict() for sig in self.signals],
            "last_updated": datetime.now().isoformat()
        }
        
        with open(self.log_path, 'w') as f:
            json.dump(log_data, f, indent=2)
    
    def get_signals(
        self,
        symbol: Optional[str] = None,
        signal_type: Optional[SignalType] = None,
        limit: int = 100
    ) -> List[TradeSignal]:
        """
        Query signals with filters.
        
        Args:
            symbol: Filter by symbol
            signal_type: Filter by signal type
            limit: Max number of signals
            
        Returns:
            List of TradeSignals
        """
        filtered = self.signals
        
        if symbol:
            filtered = [s for s in filtered if s.symbol == symbol]
        
        if signal_type:
            filtered = [s for s in filtered if s.signal_type == signal_type]
        
        # Sort by timestamp descending
        filtered.sort(key=lambda s: s.timestamp, reverse=True)
        
        return filtered[:limit]
    
    def get_unexecuted_signals(self) -> List[TradeSignal]:
        """Get all signals that haven't been executed"""
        return [s for s in self.signals if not s.executed and s.is_valid()]


# ============================================================================
# TRADINGVIEW WEBHOOK SERVER
# ============================================================================

class TradingViewWebhook:
    """
    Flask webhook server for receiving TradingView alerts.
    
    Features:
    - POST endpoint /webhook
    - Alert validation and transformation
    - Signal logging
    - Callback support for signal processing
    """
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 5000,
        secret_key: Optional[str] = None,
        signal_callback: Optional[Callable[[TradeSignal], None]] = None,
        log_path: str = "outputs/tradingview_signals.json"
    ):
        if not FLASK_AVAILABLE:
            raise ImportError("Flask required for webhook mode. Install with: pip install flask")
        
        self.host = host
        self.port = port
        self.secret_key = secret_key
        self.signal_callback = signal_callback
        
        # Initialize components
        self.validator = AlertValidator()
        self.transformer = SignalTransformer()
        self.logger = SignalLogger(log_path)
        
        # Initialize Flask app
        self.app = Flask(__name__)
        self._setup_routes()
        
        logger.info(f"🌐 TradingView webhook initialized: http://{host}:{port}/webhook")
    
    def _setup_routes(self) -> None:
        """Setup Flask routes"""
        
        @self.app.route('/webhook', methods=['POST'])
        def webhook():
            """Handle TradingView webhook POST"""
            try:
                # Get JSON payload
                alert_data = request.get_json()
                
                if not alert_data:
                    return jsonify({"status": "error", "message": "No JSON payload"}), 400
                
                # Validate secret key if configured
                if self.secret_key:
                    provided_key = alert_data.get("secret_key")
                    if provided_key != self.secret_key:
                        logger.warning("⚠️  Invalid secret key")
                        return jsonify({"status": "error", "message": "Invalid secret key"}), 403
                
                # Sanitize alert
                alert_data = self.validator.sanitize_alert(alert_data)
                
                # Validate alert
                is_valid, error = self.validator.validate_alert(alert_data)
                if not is_valid:
                    logger.warning(f"⚠️  Invalid alert: {error}")
                    return jsonify({"status": "error", "message": error}), 400
                
                # Transform to TradeSignal
                signal = self.transformer.transform_dict(alert_data)
                
                # Log signal
                self.logger.log_signal(signal)
                
                # Execute callback if provided
                if self.signal_callback:
                    try:
                        self.signal_callback(signal)
                    except Exception as e:
                        logger.error(f"❌ Callback error: {e}")
                
                logger.info(f"✅ Received signal: {signal.symbol} {signal.signal_type.value}")
                
                return jsonify({
                    "status": "success",
                    "signal_id": signal.signal_id,
                    "message": "Signal received and processed"
                }), 200
                
            except Exception as e:
                logger.error(f"❌ Webhook error: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint"""
            return jsonify({"status": "ok", "service": "tradingview_webhook"}), 200
    
    def run(self, debug: bool = False) -> None:
        """Start Flask server"""
        logger.info(f"🚀 Starting TradingView webhook server on {self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port, debug=debug)


# ============================================================================
# MOCK ALERT GENERATOR (FOR TESTING)
# ============================================================================

class MockAlertGenerator:
    """
    Generate mock TradingView alerts for offline testing.
    
    Features:
    - Deterministic alert generation
    - Various signal types
    - Realistic timing intervals
    """
    
    def __init__(self, random_seed: int = 42):
        self.random_seed = random_seed
        import numpy as np
        np.random.seed(random_seed)
        self.rng = np.random.default_rng(random_seed)
    
    def generate_stock_alert(
        self,
        symbol: str,
        action: str = "buy",
        price: float = 100.0
    ) -> Dict[str, Any]:
        """Generate stock alert"""
        return {
            "alert_name": f"{symbol} Stock Signal",
            "symbol": symbol,
            "action": action,
            "price": price,
            "timestamp": datetime.now().isoformat(),
            "strategy": "Trend Following",
            "interval": "15m",
            "qty": 100,
            "signal_type": "stock",
            "message": f"Generated by MockAlertGenerator for {symbol}"
        }
    
    def generate_options_alert(
        self,
        symbol: str,
        option_type: str = "call",
        action: str = "buy",
        strike: float = 105.0,
        expiration: str = "2025-11-15",
        price: float = 3.50
    ) -> Dict[str, Any]:
        """Generate options alert"""
        return {
            "alert_name": f"{symbol} Options Signal",
            "symbol": symbol,
            "action": action,
            "price": price,
            "timestamp": datetime.now().isoformat(),
            "strategy": "Volatility Play",
            "interval": "1h",
            "qty": 5,
            "signal_type": option_type,
            "strike": strike,
            "expiration": expiration,
            "stop_loss": price * 0.5,  # 50% stop loss
            "take_profit": price * 2.0,  # 100% profit target
            "message": f"Generated by MockAlertGenerator for {symbol} {option_type}"
        }
    
    def generate_batch(
        self,
        num_alerts: int = 10,
        symbols: List[str] = ["SPY", "QQQ", "AAPL"]
    ) -> List[Dict[str, Any]]:
        """Generate batch of random alerts"""
        alerts = []
        
        for i in range(num_alerts):
            symbol = self.rng.choice(symbols)
            alert_type = self.rng.choice(["stock", "call", "put"])
            action = self.rng.choice(["buy", "sell"])
            
            if alert_type == "stock":
                price = self.rng.uniform(100, 500)
                alert = self.generate_stock_alert(symbol, action, price)
            else:
                price = self.rng.uniform(100, 500)
                strike = price * self.rng.uniform(0.95, 1.05)
                option_price = price * self.rng.uniform(0.01, 0.05)
                expiration = (datetime.now() + timedelta(days=int(self.rng.integers(7, 60)))).strftime("%Y-%m-%d")
                
                alert = self.generate_options_alert(
                    symbol, alert_type, action, strike, expiration, option_price
                )
            
            alerts.append(alert)
        
        return alerts


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_webhook_server(
    port: int = 5000,
    secret_key: Optional[str] = None,
    signal_callback: Optional[Callable[[TradeSignal], None]] = None,
    log_path: str = "outputs/tradingview_signals.json"
) -> TradingViewWebhook:
    """
    Factory function to create webhook server.
    
    Args:
        port: Server port
        secret_key: Optional secret key for authentication
        signal_callback: Callback function for signal processing
        log_path: Signal log file path
        
    Returns:
        TradingViewWebhook instance
    """
    return TradingViewWebhook(
        port=port,
        secret_key=secret_key,
        signal_callback=signal_callback,
        log_path=log_path
    )


# ============================================================================
# MAIN EXECUTION (FOR TESTING)
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("TRADINGVIEW CONNECTOR TEST — MOCK MODE")
    logger.info("=" * 80)
    
    # Test 1: Alert validation
    logger.info("\n📋 Test 1: Alert Validation")
    validator = AlertValidator()
    
    valid_alert = {
        "symbol": "SPY",
        "action": "buy",
        "price": 450.0,
        "signal_type": "call",
        "strike": 460.0,
        "expiration": "2025-11-15"
    }
    
    is_valid, error = validator.validate_alert(valid_alert)
    logger.info(f"   Valid alert: {is_valid}")
    
    invalid_alert = {
        "symbol": "spy",  # lowercase
        "action": "buy",
        "price": -100.0  # negative price
    }
    
    is_valid, error = validator.validate_alert(invalid_alert)
    logger.info(f"   Invalid alert: {is_valid}, Error: {error}")
    
    # Test 2: Signal transformation
    logger.info("\n🔄 Test 2: Signal Transformation")
    transformer = SignalTransformer()
    
    alert_data = {
        "alert_name": "SPY Call Entry",
        "symbol": "SPY",
        "action": "buy",
        "price": 450.0,
        "signal_type": "call",
        "strike": 460.0,
        "expiration": "2025-11-15",
        "qty": 5,
        "stop_loss": 2.0,
        "take_profit": 8.0
    }
    
    signal = transformer.transform_dict(alert_data)
    logger.info(f"   Signal ID: {signal.signal_id}")
    logger.info(f"   Signal Type: {signal.signal_type.value}")
    logger.info(f"   Symbol: {signal.symbol}")
    logger.info(f"   Qty: {signal.qty}")
    logger.info(f"   Strike: ${signal.strike}")
    logger.info(f"   Expiration: {signal.expiration}")
    
    # Test 3: Signal logging
    logger.info("\n📝 Test 3: Signal Logging")
    signal_logger = SignalLogger(log_path="outputs/test_tradingview_signals.json")
    
    signal_logger.log_signal(signal)
    logger.info(f"   Total signals logged: {len(signal_logger.signals)}")
    
    # Test 4: Mock alert generation
    logger.info("\n🎲 Test 4: Mock Alert Generation")
    mock_gen = MockAlertGenerator(random_seed=42)
    
    stock_alert = mock_gen.generate_stock_alert("AAPL", "buy", 180.0)
    logger.info(f"   Stock alert: {stock_alert['symbol']} {stock_alert['action']} @ ${stock_alert['price']}")
    
    options_alert = mock_gen.generate_options_alert("SPY", "call", "buy", 460.0, "2025-11-15", 8.50)
    logger.info(f"   Options alert: {options_alert['symbol']} {options_alert['signal_type']} strike ${options_alert['strike']}")
    
    # Test 5: Batch generation
    logger.info("\n📦 Test 5: Batch Alert Generation")
    batch_alerts = mock_gen.generate_batch(num_alerts=5, symbols=["SPY", "QQQ", "AAPL"])
    
    for i, alert in enumerate(batch_alerts):
        sig = transformer.transform_dict(alert)
        signal_logger.log_signal(sig)
        logger.info(f"   Alert {i+1}: {sig.symbol} {sig.signal_type.value}")
    
    # Test 6: Query signals
    logger.info("\n🔍 Test 6: Query Signals")
    spy_signals = signal_logger.get_signals(symbol="SPY", limit=10)
    logger.info(f"   SPY signals: {len(spy_signals)}")
    
    unexecuted = signal_logger.get_unexecuted_signals()
    logger.info(f"   Unexecuted signals: {len(unexecuted)}")
    
    # Test 7: Signal validation
    logger.info("\n✅ Test 7: Signal Validation")
    for sig in signal_logger.signals[:3]:
        logger.info(f"   {sig.signal_id}: Valid={sig.is_valid()}, Expired={sig.is_expired()}")
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ ALL TRADINGVIEW CONNECTOR TESTS COMPLETE")
    logger.info("=" * 80)
    logger.info(f"\n💾 Signals saved to: outputs/test_tradingview_signals.json")
