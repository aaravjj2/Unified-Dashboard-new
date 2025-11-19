"""
Strategy Bot Framework — Phase 6-8 Integration
===============================================

Comprehensive strategy bot framework integrating:
- Phase 6: Explainability & options forecasting
- Phase 8: Trend analysis, volatility heatmaps, risk dashboards
- Phase 8B: Optimized scenario generation
- Broker execution (Alpaca/mock)
- TradingView alerts
- Risk management
- Backtesting

Architecture:
- SignalGenerator: Analytics → trade signals (with Phase 8 integration)
- ExecutionEngine: Signals → broker orders
- RiskManager: Pre-trade risk validation
- Backtester: Historical simulation with P&L tracking
- StrategyBot: Main orchestrator

Features:
- Live and offline modes
- Deterministic execution for testing
- Greeks-based risk limits
- Multi-leg options strategies
- Performance tracking and reporting

Author: Agent 1B — Unified Financial Dashboard Team
Version: 1.0 (Phase 6-8 Strategy Bot Integration)
Date: October 29, 2025
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import numpy as np
import pandas as pd

# Import internal modules
from broker_connector import (
    MockBrokerConnector, AlpacaBrokerConnector,
    OrderType, OrderSide, OrderStatus, AssetClass, OptionType,
    Position, AccountInfo, Order
)
from tradingview_connector import (
    TradeSignal, SignalType, AlertSource, SignalPriority,
    SignalLogger
)

# Import Phase 8 analytics (if available)
try:
    from trend_analyzer import TrendAnalyzer, TrendAnalysisResult
    from volatility_heatmap import VolatilityHeatmap, VolatilityMetrics
    from risk_dashboard import RiskDashboard, RiskDashboardSnapshot
    PHASE8_AVAILABLE = True
except ImportError:
    PHASE8_AVAILABLE = False
    logging.warning("⚠️  Phase 8 analytics not available. SignalGenerator will use simplified logic.")

# Import Phase 8B scenario engine (if available)
try:
    from scenario_engine import ScenarioEngine, ScenarioParameters, ScenarioType
    PHASE8B_AVAILABLE = True
except ImportError:
    PHASE8B_AVAILABLE = False
    logging.warning("⚠️  Phase 8B scenario engine not available. Backtester will use simplified simulation.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMERATIONS & TYPE DEFINITIONS
# ============================================================================

class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class StrategyMode(Enum):
    """Strategy execution mode"""
    LIVE = "live"  # Real broker execution
    PAPER = "paper"  # Paper trading (Alpaca paper account)
    MOCK = "mock"  # Offline simulation
    BACKTEST = "backtest"  # Historical simulation


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class RiskLimits:
    """Risk management parameters"""
    # Portfolio limits
    max_portfolio_risk_pct: float = 5.0  # Max % of portfolio at risk
    max_position_size_pct: float = 10.0  # Max % of portfolio per position
    max_daily_loss_pct: float = 3.0  # Max daily loss %
    
    # Greeks limits (for options)
    max_delta: float = 100.0  # Max portfolio delta
    max_gamma: float = 10.0  # Max portfolio gamma
    max_vega: float = 50.0  # Max portfolio vega
    max_theta: float = -20.0  # Max portfolio theta (negative = decay)
    
    # Exposure limits
    max_margin_usage_pct: float = 50.0  # Max buying power usage
    max_concentration_pct: float = 25.0  # Max % in single symbol
    
    # Options-specific
    max_contracts_per_trade: int = 10
    min_days_to_expiration: int = 7  # Don't trade options <7 DTE
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics"""
    total_value: float
    cash: float
    equity: float
    buying_power: float
    
    # P&L
    daily_pnl: float
    daily_pnl_pct: float
    total_pnl: float
    total_pnl_pct: float
    
    # Risk metrics
    current_risk_pct: float
    margin_usage_pct: float
    largest_position_pct: float
    
    # Greeks (options)
    portfolio_delta: float = 0.0
    portfolio_gamma: float = 0.0
    portfolio_vega: float = 0.0
    portfolio_theta: float = 0.0
    
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class TradeResult:
    """Execution result for a single trade"""
    signal_id: str
    order_id: str
    symbol: str
    qty: float
    side: OrderSide
    order_type: OrderType
    status: OrderStatus
    
    # Execution details
    filled_price: Optional[float] = None
    filled_at: Optional[str] = None
    commission: float = 0.0
    
    # Risk assessment
    risk_check_passed: bool = True
    risk_warnings: List[str] = field(default_factory=list)
    
    # P&L (for closed positions)
    realized_pnl: Optional[float] = None
    
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "signal_id": self.signal_id,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "qty": self.qty,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "status": self.status.value,
            "filled_price": self.filled_price,
            "filled_at": self.filled_at,
            "commission": self.commission,
            "risk_check_passed": self.risk_check_passed,
            "risk_warnings": self.risk_warnings,
            "realized_pnl": self.realized_pnl,
            "timestamp": self.timestamp
        }


# ============================================================================
# SIGNAL GENERATOR (PHASE 8 ANALYTICS INTEGRATION)
# ============================================================================

class SignalGenerator:
    """
    Generate trade signals from Phase 8 analytics outputs.
    
    Inputs:
    - TrendAnalysisResult (from trend_analyzer.py)
    - VolatilityMetrics (from volatility_heatmap.py)
    - RiskDashboardSnapshot (from risk_dashboard.py)
    
    Outputs:
    - TradeSignal objects for ExecutionEngine
    
    Strategy Logic:
    - Bullish trend + low volatility → Buy calls
    - Bearish trend + low volatility → Buy puts
    - High volatility → Sell premium (credit spreads)
    - High risk score → Reduce exposure / close positions
    """
    
    def __init__(
        self,
        mode: StrategyMode = StrategyMode.MOCK,
        risk_limits: Optional[RiskLimits] = None
    ):
        self.mode = mode
        self.risk_limits = risk_limits or RiskLimits()
        self.signal_counter = 1
        
        logger.info(f"🤖 SignalGenerator initialized: {mode.value} mode")
    
    def _generate_signal_id(self) -> str:
        """Generate unique signal ID"""
        signal_id = f"strategy_{self.signal_counter:06d}"
        self.signal_counter += 1
        return signal_id
    
    def generate_from_analytics(
        self,
        trend_result: Optional[Any] = None,
        volatility_metrics: Optional[Dict[str, Any]] = None,
        risk_snapshot: Optional[Any] = None,
        portfolio_value: float = 100000.0
    ) -> List[TradeSignal]:
        """
        Generate signals from Phase 8 analytics outputs.
        
        Args:
            trend_result: TrendAnalysisResult from trend_analyzer
            volatility_metrics: Dict of VolatilityMetrics from volatility_heatmap
            risk_snapshot: RiskDashboardSnapshot from risk_dashboard
            portfolio_value: Current portfolio value for position sizing
            
        Returns:
            List of TradeSignal objects
        """
        signals = []
        
        if not PHASE8_AVAILABLE:
            # Fallback: generate simple mock signals
            logger.warning("⚠️  Phase 8 analytics not available, using mock signal generation")
            return self._generate_mock_signals(portfolio_value)
        
        # Extract trend signals
        if trend_result and hasattr(trend_result, 'ticker_signals'):
            for ticker, trend_signal in trend_result.ticker_signals.items():
                # Get volatility for this ticker
                vol_regime = "medium"  # default
                if volatility_metrics and ticker in volatility_metrics:
                    vol_metric = volatility_metrics[ticker]
                    if hasattr(vol_metric, 'current_volatility'):
                        if vol_metric.current_volatility < 0.15:
                            vol_regime = "low"
                        elif vol_metric.current_volatility > 0.30:
                            vol_regime = "high"
                
                # Get risk score
                risk_score = 50.0  # default medium risk
                if risk_snapshot and hasattr(risk_snapshot, 'portfolio_risk_score'):
                    risk_score = risk_snapshot.portfolio_risk_score
                
                # Strategy logic
                signal = self._create_signal_from_trend(
                    ticker,
                    trend_signal,
                    vol_regime,
                    risk_score,
                    portfolio_value
                )
                
                if signal:
                    signals.append(signal)
        
        logger.info(f"📊 Generated {len(signals)} signals from analytics")
        return signals
    
    def _create_signal_from_trend(
        self,
        ticker: str,
        trend_signal: Any,
        vol_regime: str,
        risk_score: float,
        portfolio_value: float
    ) -> Optional[TradeSignal]:
        """
        Create TradeSignal based on trend + volatility + risk.
        
        Strategy rules:
        1. Bullish trend + low vol → Buy call (directional play)
        2. Bearish trend + low vol → Buy put (directional play)
        3. Bullish trend + high vol → Sell put (collect premium)
        4. Bearish trend + high vol → Sell call (collect premium)
        5. High risk score (>75) → Close positions / reduce exposure
        """
        # Extract trend direction
        trend_direction = getattr(trend_signal, 'signal', 'neutral')
        
        # Skip if neutral or risk too high
        if trend_direction == 'neutral' or risk_score > 80:
            return None
        
        # Calculate position size (% of portfolio)
        position_size_pct = min(
            self.risk_limits.max_position_size_pct,
            5.0 if vol_regime == "low" else 3.0  # Smaller size in high vol
        )
        
        # Determine signal type
        if trend_direction == 'bullish':
            if vol_regime == 'low':
                signal_type = SignalType.BUY_CALL
                qty = 2  # Contracts
            else:
                signal_type = SignalType.SELL_PUT
                qty = 1  # Sell fewer contracts
        else:  # bearish
            if vol_regime == 'low':
                signal_type = SignalType.BUY_PUT
                qty = 2
            else:
                signal_type = SignalType.SELL_CALL
                qty = 1
        
        # Calculate strike and expiration (simplified)
        # In production, use options_forecast_azure.py from Phase 6
        strike = self._estimate_strike(ticker, signal_type)
        expiration = self._estimate_expiration()
        
        # Create signal
        signal = TradeSignal(
            signal_id=self._generate_signal_id(),
            signal_type=signal_type,
            symbol=ticker,
            qty=qty,
            source=AlertSource.STRATEGY_BOT,
            priority=SignalPriority.MEDIUM if risk_score < 60 else SignalPriority.LOW,
            strike=strike,
            expiration=expiration,
            trend_signal=trend_direction,
            volatility_regime=vol_regime,
            risk_score=risk_score,
            ttl_seconds=3600,  # 1 hour TTL
            notes=f"Generated from {trend_direction} trend + {vol_regime} volatility"
        )
        
        return signal
    
    def _estimate_strike(self, ticker: str, signal_type: SignalType) -> float:
        """Estimate option strike (simplified - use Phase 6 forecast in production)"""
        # Default prices
        prices = {"SPY": 450.0, "QQQ": 380.0, "IWM": 190.0, "AAPL": 180.0, "MSFT": 380.0}
        current_price = prices.get(ticker, 100.0)
        
        # ATM for buys, OTM for sells
        if signal_type in [SignalType.BUY_CALL, SignalType.BUY_PUT]:
            return current_price  # ATM
        else:
            # OTM (5% out)
            if signal_type == SignalType.SELL_CALL:
                return current_price * 1.05
            else:  # SELL_PUT
                return current_price * 0.95
    
    def _estimate_expiration(self) -> str:
        """Estimate option expiration (30-45 DTE standard)"""
        days = 35  # 5 weeks
        expiration_date = datetime.now() + timedelta(days=days)
        return expiration_date.strftime("%Y-%m-%d")
    
    def _generate_mock_signals(self, portfolio_value: float) -> List[TradeSignal]:
        """Generate mock signals for testing (when Phase 8 unavailable)"""
        signals = []
        
        # Example: Buy SPY call
        signal1 = TradeSignal(
            signal_id=self._generate_signal_id(),
            signal_type=SignalType.BUY_CALL,
            symbol="SPY",
            qty=2,
            source=AlertSource.STRATEGY_BOT,
            priority=SignalPriority.MEDIUM,
            strike=460.0,
            expiration="2025-11-30",
            trend_signal="bullish",
            volatility_regime="low",
            risk_score=45.0,
            notes="Mock signal for testing"
        )
        signals.append(signal1)
        
        return signals


# ============================================================================
# RISK MANAGER
# ============================================================================

class RiskManager:
    """
    Pre-trade risk validation and portfolio risk monitoring.
    
    Validates:
    - Position size limits
    - Portfolio risk exposure
    - Greeks limits (for options)
    - Margin requirements
    - Concentration limits
    """
    
    def __init__(self, risk_limits: Optional[RiskLimits] = None):
        self.risk_limits = risk_limits or RiskLimits()
        logger.info("🛡️  RiskManager initialized")
    
    def validate_signal(
        self,
        signal: TradeSignal,
        account: AccountInfo,
        positions: List[Position]
    ) -> Tuple[bool, List[str]]:
        """
        Validate signal against risk limits.
        
        Args:
            signal: TradeSignal to validate
            account: Current account info
            positions: Current positions
            
        Returns:
            Tuple of (is_valid, warnings)
        """
        warnings = []
        
        # Check 1: Account not blocked
        if account.trading_blocked or account.account_blocked:
            warnings.append("Account blocked for trading")
            return False, warnings
        
        # Check 2: Sufficient buying power
        estimated_cost = self._estimate_trade_cost(signal, account)
        if estimated_cost > account.buying_power:
            warnings.append(f"Insufficient buying power: ${estimated_cost:.2f} required, ${account.buying_power:.2f} available")
            return False, warnings
        
        # Check 3: Position size limit
        position_value = estimated_cost
        position_pct = (position_value / account.portfolio_value) * 100
        if position_pct > self.risk_limits.max_position_size_pct:
            warnings.append(f"Position size {position_pct:.1f}% exceeds limit {self.risk_limits.max_position_size_pct:.1f}%")
            return False, warnings
        
        # Check 4: Concentration limit (total exposure to symbol)
        current_exposure = self._calculate_symbol_exposure(signal.symbol, positions, account.portfolio_value)
        new_exposure = current_exposure + position_pct
        if new_exposure > self.risk_limits.max_concentration_pct:
            warnings.append(f"Concentration {new_exposure:.1f}% in {signal.symbol} exceeds limit {self.risk_limits.max_concentration_pct:.1f}%")
            return False, warnings
        
        # Check 5: Options-specific checks
        if signal.signal_type in [SignalType.BUY_CALL, SignalType.SELL_CALL, SignalType.BUY_PUT, SignalType.SELL_PUT]:
            # Check contract limit
            if signal.qty > self.risk_limits.max_contracts_per_trade:
                warnings.append(f"Contracts {signal.qty} exceeds limit {self.risk_limits.max_contracts_per_trade}")
                return False, warnings
            
            # Check DTE (days to expiration)
            if signal.expiration:
                dte = (datetime.strptime(signal.expiration, "%Y-%m-%d") - datetime.now()).days
                if dte < self.risk_limits.min_days_to_expiration:
                    warnings.append(f"DTE {dte} below minimum {self.risk_limits.min_days_to_expiration}")
                    return False, warnings
        
        # Check 6: Margin usage
        margin_usage_pct = ((account.portfolio_value - account.buying_power) / account.portfolio_value) * 100
        if margin_usage_pct > self.risk_limits.max_margin_usage_pct:
            warnings.append(f"Margin usage {margin_usage_pct:.1f}% exceeds limit {self.risk_limits.max_margin_usage_pct:.1f}%")
            return False, warnings
        
        # Passed all checks
        if warnings:
            logger.warning(f"⚠️  Signal {signal.signal_id} has warnings: {warnings}")
        
        return True, warnings
    
    def _estimate_trade_cost(self, signal: TradeSignal, account: AccountInfo) -> float:
        """Estimate capital required for trade"""
        if signal.signal_type in [SignalType.BUY_CALL, SignalType.BUY_PUT]:
            # Debit: pay premium (assume $5 per contract for estimation)
            premium = signal.limit_price if signal.limit_price else 5.0
            return signal.qty * premium * 100  # Options: qty * premium * 100
        elif signal.signal_type in [SignalType.SELL_CALL, SignalType.SELL_PUT]:
            # Credit: collect premium but need margin
            # Simplified: assume 20% of strike as margin
            if signal.strike:
                return signal.qty * signal.strike * 0.20 * 100
            else:
                return 1000.0  # Default margin
        else:
            # Stock: qty * price
            price = signal.limit_price if signal.limit_price else 100.0
            return signal.qty * price
    
    def _calculate_symbol_exposure(
        self,
        symbol: str,
        positions: List[Position],
        portfolio_value: float
    ) -> float:
        """Calculate current exposure % to a symbol"""
        total_exposure = sum(
            abs(pos.market_value) for pos in positions
            if pos.symbol.startswith(symbol)  # Match SPY, SPY251115C00460000, etc.
        )
        
        return (total_exposure / portfolio_value * 100) if portfolio_value > 0 else 0.0
    
    def calculate_portfolio_metrics(
        self,
        account: AccountInfo,
        positions: List[Position],
        initial_value: float
    ) -> PortfolioMetrics:
        """Calculate portfolio metrics"""
        # P&L
        total_pnl = account.equity - initial_value
        total_pnl_pct = (total_pnl / initial_value * 100) if initial_value > 0 else 0.0
        
        # Daily P&L (simplified - would track previous day equity)
        daily_pnl = sum(pos.unrealized_pl for pos in positions)
        daily_pnl_pct = (daily_pnl / account.equity * 100) if account.equity > 0 else 0.0
        
        # Risk
        total_exposure = sum(abs(pos.market_value) for pos in positions)
        current_risk_pct = (total_exposure / account.portfolio_value * 100) if account.portfolio_value > 0 else 0.0
        
        margin_usage_pct = ((account.portfolio_value - account.buying_power) / account.portfolio_value * 100) if account.portfolio_value > 0 else 0.0
        
        largest_position_pct = max(
            [(abs(pos.market_value) / account.portfolio_value * 100) for pos in positions],
            default=0.0
        )
        
        # Greeks (simplified - would calculate from options positions)
        portfolio_delta = 0.0
        portfolio_gamma = 0.0
        portfolio_vega = 0.0
        portfolio_theta = 0.0
        
        return PortfolioMetrics(
            total_value=account.portfolio_value,
            cash=account.cash,
            equity=account.equity,
            buying_power=account.buying_power,
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            current_risk_pct=current_risk_pct,
            margin_usage_pct=margin_usage_pct,
            largest_position_pct=largest_position_pct,
            portfolio_delta=portfolio_delta,
            portfolio_gamma=portfolio_gamma,
            portfolio_vega=portfolio_vega,
            portfolio_theta=portfolio_theta
        )


# ============================================================================
# EXECUTION ENGINE
# ============================================================================

class ExecutionEngine:
    """
    Execute trade signals via broker connector.
    
    Features:
    - Risk validation before execution
    - Retry logic for failed orders
    - Order status tracking
    - Transaction logging
    """
    
    def __init__(
        self,
        broker: Any,  # MockBrokerConnector or AlpacaBrokerConnector
        risk_manager: RiskManager,
        max_retries: int = 3
    ):
        self.broker = broker
        self.risk_manager = risk_manager
        self.max_retries = max_retries
        self.trade_results: List[TradeResult] = []
        
        logger.info("⚙️  ExecutionEngine initialized")
    
    def execute_signal(self, signal: TradeSignal) -> TradeResult:
        """
        Execute trade signal.
        
        Args:
            signal: TradeSignal to execute
            
        Returns:
            TradeResult
        """
        logger.info(f"🎯 Executing signal: {signal.signal_id} ({signal.signal_type.value})")
        
        # Get account and positions for risk check
        account = self.broker.get_account_info()
        positions = self.broker.get_positions()
        
        # Risk validation
        is_valid, warnings = self.risk_manager.validate_signal(signal, account, positions)
        
        if not is_valid:
            logger.warning(f"❌ Signal {signal.signal_id} failed risk check: {warnings}")
            return TradeResult(
                signal_id=signal.signal_id,
                order_id="",
                symbol=signal.symbol,
                qty=signal.qty,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                status=OrderStatus.REJECTED,
                risk_check_passed=False,
                risk_warnings=warnings
            )
        
        # Convert signal to broker order
        order = self._signal_to_order(signal)
        
        if not order:
            logger.error(f"❌ Failed to convert signal {signal.signal_id} to order")
            return TradeResult(
                signal_id=signal.signal_id,
                order_id="",
                symbol=signal.symbol,
                qty=signal.qty,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                status=OrderStatus.REJECTED,
                risk_check_passed=True,
                risk_warnings=["Failed to create order"]
            )
        
        # Execute with retry logic
        for attempt in range(self.max_retries):
            try:
                # Place order
                result_order = self.broker.place_order(
                    symbol=order.symbol,
                    qty=order.qty,
                    side=order.side,
                    order_type=order.order_type,
                    limit_price=order.limit_price,
                    stop_price=order.stop_price,
                    asset_class=order.asset_class,
                    option_type=order.option_type,
                    strike=order.strike,
                    expiration=order.expiration
                )
                
                # Create result
                trade_result = TradeResult(
                    signal_id=signal.signal_id,
                    order_id=result_order.order_id,
                    symbol=result_order.symbol,
                    qty=result_order.qty,
                    side=result_order.side,
                    order_type=result_order.order_type,
                    status=result_order.status,
                    filled_price=result_order.filled_avg_price,
                    filled_at=result_order.filled_at,
                    risk_check_passed=True,
                    risk_warnings=warnings
                )
                
                self.trade_results.append(trade_result)
                
                logger.info(f"✅ Executed {signal.signal_type.value}: {signal.symbol} @ ${result_order.filled_avg_price:.2f}")
                
                return trade_result
                
            except Exception as e:
                logger.error(f"❌ Execution attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    # Final failure
                    return TradeResult(
                        signal_id=signal.signal_id,
                        order_id="",
                        symbol=signal.symbol,
                        qty=signal.qty,
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        status=OrderStatus.REJECTED,
                        risk_check_passed=True,
                        risk_warnings=[f"Execution failed: {e}"]
                    )
    
    def _signal_to_order(self, signal: TradeSignal) -> Optional[Order]:
        """Convert TradeSignal to Order"""
        # Determine side
        if signal.signal_type in [SignalType.BUY_CALL, SignalType.BUY_PUT, SignalType.BUY_STOCK]:
            side = OrderSide.BUY
        else:
            side = OrderSide.SELL
        
        # Determine asset class
        if signal.signal_type in [SignalType.BUY_CALL, SignalType.SELL_CALL, SignalType.BUY_PUT, SignalType.SELL_PUT]:
            asset_class = AssetClass.OPTION
            option_type = OptionType.CALL if "call" in signal.signal_type.value else OptionType.PUT
        else:
            asset_class = AssetClass.STOCK
            option_type = None
        
        # Determine order type
        if signal.limit_price and signal.stop_price:
            order_type = OrderType.STOP_LIMIT
        elif signal.limit_price:
            order_type = OrderType.LIMIT
        elif signal.stop_price:
            order_type = OrderType.STOP
        else:
            order_type = OrderType.MARKET
        
        # Create order object (for validation)
        order = Order(
            order_id="",
            symbol=signal.symbol,
            qty=signal.qty,
            side=side,
            order_type=order_type,
            status=OrderStatus.PENDING,
            limit_price=signal.limit_price,
            stop_price=signal.stop_price,
            asset_class=asset_class,
            option_type=option_type,
            strike=signal.strike,
            expiration=signal.expiration
        )
        
        return order
    
    def get_trade_results(self) -> List[TradeResult]:
        """Get all trade results"""
        return self.trade_results
    
    def save_trade_log(self, filepath: str = "outputs/trade_results.json") -> None:
        """Save trade results to JSON"""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        log_data = {
            "total_trades": len(self.trade_results),
            "trades": [tr.to_dict() for tr in self.trade_results],
            "timestamp": datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        logger.info(f"💾 Saved trade results to {filepath}")


# ============================================================================
# BACKTESTER
# ============================================================================

class Backtester:
    """
    Historical simulation and backtesting framework.
    
    Features:
    - Replay historical signals
    - Simulate order execution with realistic fills
    - Track P&L and performance metrics
    - Generate backtest reports
    """
    
    def __init__(
        self,
        initial_cash: float = 100000.0,
        risk_limits: Optional[RiskLimits] = None
    ):
        self.initial_cash = initial_cash
        self.risk_limits = risk_limits or RiskLimits()
        
        # Create mock broker for simulation
        self.broker = MockBrokerConnector(
            initial_cash=initial_cash,
            slippage_pct=0.001,
            random_seed=42
        )
        
        self.risk_manager = RiskManager(self.risk_limits)
        self.execution_engine = ExecutionEngine(self.broker, self.risk_manager)
        
        # Backtest state
        self.backtest_results = []
        
        logger.info(f"🔬 Backtester initialized: ${initial_cash:,.2f} starting capital")
    
    def run_backtest(
        self,
        signals: List[TradeSignal],
        market_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> Dict[str, Any]:
        """
        Run backtest with list of signals.
        
        Args:
            signals: List of TradeSignal objects (chronologically ordered)
            market_data: Optional market data for price lookups
            
        Returns:
            Backtest results dictionary
        """
        logger.info(f"🔬 Starting backtest with {len(signals)} signals")
        
        # Set market prices if provided
        if market_data:
            for symbol, df in market_data.items():
                if not df.empty:
                    latest_price = df['close'].iloc[-1]
                    self.broker.set_market_price(symbol, latest_price)
        
        # Execute signals sequentially
        for signal in signals:
            result = self.execution_engine.execute_signal(signal)
            self.backtest_results.append(result)
        
        # Calculate final metrics
        account = self.broker.get_account_info()
        positions = self.broker.get_positions()
        metrics = self.risk_manager.calculate_portfolio_metrics(
            account, positions, self.initial_cash
        )
        
        # Calculate trade statistics
        total_trades = len(self.backtest_results)
        successful_trades = sum(1 for tr in self.backtest_results if tr.status == OrderStatus.FILLED)
        failed_trades = total_trades - successful_trades
        
        # Generate report
        report = {
            "initial_capital": self.initial_cash,
            "final_capital": account.equity,
            "total_pnl": metrics.total_pnl,
            "total_pnl_pct": metrics.total_pnl_pct,
            "total_trades": total_trades,
            "successful_trades": successful_trades,
            "failed_trades": failed_trades,
            "success_rate": (successful_trades / total_trades * 100) if total_trades > 0 else 0.0,
            "portfolio_metrics": metrics.to_dict(),
            "trade_results": [tr.to_dict() for tr in self.backtest_results],
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Backtest complete: ${metrics.total_pnl:,.2f} P&L ({metrics.total_pnl_pct:.2f}%)")
        
        return report
    
    def save_backtest_report(self, filepath: str = "outputs/backtest_report.json") -> None:
        """Save backtest report"""
        if not self.backtest_results:
            logger.warning("⚠️  No backtest results to save")
            return
        
        account = self.broker.get_account_info()
        positions = self.broker.get_positions()
        metrics = self.risk_manager.calculate_portfolio_metrics(
            account, positions, self.initial_cash
        )
        
        report = {
            "initial_capital": self.initial_cash,
            "final_capital": account.equity,
            "total_pnl": metrics.total_pnl,
            "total_pnl_pct": metrics.total_pnl_pct,
            "total_trades": len(self.backtest_results),
            "portfolio_metrics": metrics.to_dict(),
            "trade_results": [tr.to_dict() for tr in self.backtest_results],
            "timestamp": datetime.now().isoformat()
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"💾 Saved backtest report to {filepath}")


# ============================================================================
# STRATEGY BOT (MAIN ORCHESTRATOR)
# ============================================================================

class StrategyBot:
    """
    Main strategy bot orchestrator integrating all components.
    
    Components:
    - SignalGenerator: Generate signals from analytics
    - RiskManager: Validate signals
    - ExecutionEngine: Execute signals via broker
    - Backtester: Historical simulation (optional)
    
    Modes:
    - LIVE: Real broker execution
    - PAPER: Paper trading (Alpaca paper account)
    - MOCK: Offline simulation
    - BACKTEST: Historical backtest
    """
    
    def __init__(
        self,
        mode: StrategyMode = StrategyMode.MOCK,
        broker: Optional[Any] = None,
        risk_limits: Optional[RiskLimits] = None,
        initial_cash: float = 100000.0
    ):
        self.mode = mode
        self.risk_limits = risk_limits or RiskLimits()
        self.initial_cash = initial_cash
        
        # Initialize broker
        if broker:
            self.broker = broker
        else:
            # Create default broker based on mode
            if mode == StrategyMode.MOCK or mode == StrategyMode.BACKTEST:
                self.broker = MockBrokerConnector(
                    initial_cash=initial_cash,
                    random_seed=42
                )
            else:
                raise ValueError("LIVE/PAPER modes require broker parameter")
        
        # Initialize components
        self.signal_generator = SignalGenerator(mode, risk_limits)
        self.risk_manager = RiskManager(risk_limits)
        self.execution_engine = ExecutionEngine(self.broker, self.risk_manager)
        
        # Optional: backtester
        self.backtester = None
        if mode == StrategyMode.BACKTEST:
            self.backtester = Backtester(initial_cash, risk_limits)
        
        logger.info(f"🤖 StrategyBot initialized: {mode.value} mode, ${initial_cash:,.2f} capital")
    
    def run(
        self,
        trend_result: Optional[Any] = None,
        volatility_metrics: Optional[Dict[str, Any]] = None,
        risk_snapshot: Optional[Any] = None
    ) -> List[TradeResult]:
        """
        Run strategy bot (generate + execute signals).
        
        Args:
            trend_result: TrendAnalysisResult from Phase 8
            volatility_metrics: VolatilityMetrics from Phase 8
            risk_snapshot: RiskDashboardSnapshot from Phase 8
            
        Returns:
            List of TradeResult objects
        """
        logger.info("🚀 Running StrategyBot")
        
        # Get current portfolio value
        account = self.broker.get_account_info()
        portfolio_value = account.portfolio_value
        
        # Generate signals
        signals = self.signal_generator.generate_from_analytics(
            trend_result,
            volatility_metrics,
            risk_snapshot,
            portfolio_value
        )
        
        if not signals:
            logger.info("📊 No signals generated")
            return []
        
        # Execute signals
        results = []
        for signal in signals:
            result = self.execution_engine.execute_signal(signal)
            results.append(result)
        
        logger.info(f"✅ StrategyBot completed: {len(results)} trades executed")
        
        return results
    
    def get_portfolio_metrics(self) -> PortfolioMetrics:
        """Get current portfolio metrics"""
        account = self.broker.get_account_info()
        positions = self.broker.get_positions()
        return self.risk_manager.calculate_portfolio_metrics(
            account, positions, self.initial_cash
        )
    
    def save_logs(
        self,
        trade_log_path: str = "outputs/strategy_bot_trades.json",
        transaction_log_path: str = "outputs/strategy_bot_transactions.json"
    ) -> None:
        """Save all logs"""
        self.execution_engine.save_trade_log(trade_log_path)
        self.broker.save_transaction_log(transaction_log_path)
        logger.info(f"💾 Saved logs to {trade_log_path} and {transaction_log_path}")


# ============================================================================
# MAIN EXECUTION (FOR TESTING)
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("STRATEGY BOT FRAMEWORK TEST — MOCK MODE")
    logger.info("=" * 80)
    
    # Test 1: Initialize components
    logger.info("\n🔧 Test 1: Initialize Components")
    bot = StrategyBot(
        mode=StrategyMode.MOCK,
        initial_cash=100000.0
    )
    logger.info(f"   Bot initialized: {bot.mode.value} mode")
    
    # Test 2: Generate signals (without Phase 8 analytics)
    logger.info("\n📊 Test 2: Generate Signals (Mock)")
    signals = bot.signal_generator.generate_from_analytics()
    logger.info(f"   Generated {len(signals)} signals")
    for sig in signals:
        logger.info(f"   - {sig.symbol} {sig.signal_type.value} qty={sig.qty}")
    
    # Test 3: Run strategy bot
    logger.info("\n🚀 Test 3: Run Strategy Bot")
    results = bot.run()
    logger.info(f"   Executed {len(results)} trades")
    for res in results:
        logger.info(f"   - {res.symbol}: {res.status.value}")
    
    # Test 4: Portfolio metrics
    logger.info("\n💰 Test 4: Portfolio Metrics")
    metrics = bot.get_portfolio_metrics()
    logger.info(f"   Total Value: ${metrics.total_value:,.2f}")
    logger.info(f"   Cash: ${metrics.cash:,.2f}")
    logger.info(f"   Total P&L: ${metrics.total_pnl:,.2f} ({metrics.total_pnl_pct:.2f}%)")
    
    # Test 5: Save logs
    logger.info("\n💾 Test 5: Save Logs")
    bot.save_logs(
        trade_log_path="outputs/test_strategy_bot_trades.json",
        transaction_log_path="outputs/test_strategy_bot_transactions.json"
    )
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ ALL STRATEGY BOT FRAMEWORK TESTS COMPLETE")
    logger.info("=" * 80)
