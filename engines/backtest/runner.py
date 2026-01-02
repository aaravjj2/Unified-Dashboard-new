"""
Backtest Runner Engine

Historical backtesting simulation for options strategies.
Iterates day-by-day through historical data, checking for entry/exit signals.
"""

import os
import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
import numpy as np
import random

logger = logging.getLogger(__name__)

# Deterministic mode for reproducible testing
DETERMINISTIC = os.environ.get('RESEARCH_DETERMINISTIC', '0') == '1'
if DETERMINISTIC:
    random.seed(42)
    np.random.seed(42)


class StrategyType(Enum):
    """Supported strategy types for backtesting"""
    IRON_CONDOR = "iron_condor"
    COVERED_CALL = "covered_call"
    CASH_SECURED_PUT = "cash_secured_put"
    LONG_CALL = "long_call"
    LONG_PUT = "long_put"
    STRADDLE = "straddle"


class TradeStatus(Enum):
    """Trade lifecycle status"""
    OPEN = "open"
    CLOSED = "closed"
    EXPIRED = "expired"
    STOPPED_OUT = "stopped_out"


@dataclass
class Trade:
    """Represents a single trade in the backtest"""
    id: str
    strategy: StrategyType
    symbol: str
    entry_date: date
    entry_price: float
    position_size: int
    cost_basis: float
    exit_date: Optional[date] = None
    exit_price: Optional[float] = None
    pnl: float = 0.0
    status: TradeStatus = TradeStatus.OPEN
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DailySnapshot:
    """Daily portfolio snapshot"""
    date: date
    portfolio_value: float
    cash: float
    positions_value: float
    daily_pnl: float
    cumulative_pnl: float
    open_positions: int
    high_water_mark: float
    drawdown_pct: float


@dataclass
class BacktestConfig:
    """Configuration for backtest run"""
    start_date: date
    end_date: date
    initial_capital: float = 100000.0
    strategy: StrategyType = StrategyType.IRON_CONDOR
    symbol: str = "SPY"
    # Strategy-specific params
    max_positions: int = 5
    position_size_pct: float = 0.1  # 10% of capital per trade
    profit_target_pct: float = 0.50  # 50% of max credit
    stop_loss_pct: float = 2.0  # 200% of max credit
    days_to_expiration: int = 30
    delta_target: float = 0.16  # ~16 delta for short strikes
    iv_entry_threshold: float = 0.20  # Min IV to enter
    min_premium: float = 1.00  # Min credit to collect


@dataclass
class BacktestResult:
    """Complete backtest results"""
    config: BacktestConfig
    trades: List[Trade]
    daily_snapshots: List[DailySnapshot]
    # Summary metrics
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    best_trade: float
    worst_trade: float
    avg_days_in_trade: float
    # Time series
    equity_curve: List[float]
    drawdown_series: List[float]
    dates: List[date]


class HistoricalDataProvider:
    """
    Provides historical OHLCV data.
    
    In production, this would connect to TimescaleDB.
    For now, generates synthetic data for testing.
    """
    
    def __init__(self):
        self._cache: Dict[str, Dict[date, Dict[str, float]]] = {}
    
    def get_ohlcv(self, symbol: str, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """
        Get historical OHLCV data for a symbol.
        
        Args:
            symbol: Ticker symbol
            start_date: Start date
            end_date: End date
            
        Returns:
            List of OHLCV bars
        """
        # Try to load real data first
        bars = self._try_load_real_data(symbol, start_date, end_date)
        if bars:
            return bars
        
        # Generate synthetic data for testing
        logger.info(f"Generating synthetic data for {symbol} from {start_date} to {end_date}")
        return self._generate_synthetic_data(symbol, start_date, end_date)
    
    def _try_load_real_data(self, symbol: str, start_date: date, end_date: date) -> Optional[List[Dict[str, Any]]]:
        """Attempt to load real data from various sources"""
        try:
            # Try yfinance if available
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date)
            
            if hist.empty:
                return None
            
            bars = []
            for idx, row in hist.iterrows():
                bars.append({
                    'date': idx.date() if hasattr(idx, 'date') else idx,
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume']),
                })
            return bars
        except Exception as e:
            logger.debug(f"Could not load real data: {e}")
            return None
    
    def _generate_synthetic_data(self, symbol: str, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Generate synthetic OHLCV data for testing"""
        # Base prices for common symbols
        base_prices = {
            'SPY': 450.0,
            'QQQ': 380.0,
            'IWM': 200.0,
            'GLD': 180.0,
            'AAPL': 175.0,
            'MSFT': 380.0,
            'NVDA': 500.0,
        }
        
        price = base_prices.get(symbol, 100.0)
        volatility = 0.015  # 1.5% daily volatility
        
        bars = []
        current_date = start_date
        
        while current_date <= end_date:
            # Skip weekends
            if current_date.weekday() < 5:
                # Generate daily return
                daily_return = np.random.normal(0.0003, volatility)  # Slight upward drift
                
                # OHLCV
                open_price = price
                close_price = price * (1 + daily_return)
                high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, 0.005)))
                low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, 0.005)))
                volume = int(np.random.uniform(50_000_000, 150_000_000))
                
                bars.append({
                    'date': current_date,
                    'open': round(open_price, 2),
                    'high': round(high_price, 2),
                    'low': round(low_price, 2),
                    'close': round(close_price, 2),
                    'volume': volume,
                })
                
                price = close_price
            
            current_date += timedelta(days=1)
        
        return bars
    
    def get_iv(self, symbol: str, current_date: date, price: float) -> float:
        """
        Get implied volatility for a symbol on a given date.
        
        In production, this would come from options data.
        """
        # Simulate IV with mean reversion around 20%
        base_iv = 0.20
        noise = np.random.normal(0, 0.03)
        return max(0.10, min(0.60, base_iv + noise))


class BacktestRunner:
    """
    Main backtest engine.
    
    Simulates trading strategies over historical data.
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.data_provider = HistoricalDataProvider()
        self._running = False
        self._progress = 0.0
        self._initialized = True
    
    @classmethod
    def get_instance(cls) -> 'BacktestRunner':
        """Get singleton instance"""
        return cls()
    
    def is_running(self) -> bool:
        """Check if backtest is currently running"""
        return self._running
    
    def get_progress(self) -> float:
        """Get current progress (0.0 to 1.0)"""
        return self._progress
    
    def run(self, config: BacktestConfig) -> BacktestResult:
        """
        Run backtest with given configuration.
        
        Args:
            config: Backtest configuration
            
        Returns:
            BacktestResult with all metrics and time series
        """
        logger.info(f"Starting backtest: {config.strategy.value} on {config.symbol}")
        logger.info(f"Period: {config.start_date} to {config.end_date}")
        logger.info(f"Initial capital: ${config.initial_capital:,.2f}")
        
        self._running = True
        self._progress = 0.0
        
        try:
            # Load historical data
            bars = self.data_provider.get_ohlcv(config.symbol, config.start_date, config.end_date)
            
            if not bars:
                raise ValueError(f"No data available for {config.symbol}")
            
            # Initialize state
            cash = config.initial_capital
            trades: List[Trade] = []
            daily_snapshots: List[DailySnapshot] = []
            open_trades: List[Trade] = []
            trade_counter = 0
            high_water_mark = config.initial_capital
            
            total_days = len(bars)
            
            # Iterate day-by-day
            for day_idx, bar in enumerate(bars):
                current_date = bar['date']
                current_price = bar['close']
                current_iv = self.data_provider.get_iv(config.symbol, current_date, current_price)
                
                # Update progress
                self._progress = (day_idx + 1) / total_days
                
                # Check exit signals for open trades
                closed_trades = []
                for trade in open_trades:
                    should_exit, exit_reason = self._check_exit_signal(
                        trade, current_date, current_price, current_iv, config
                    )
                    
                    if should_exit:
                        trade = self._close_trade(trade, current_date, current_price, exit_reason)
                        closed_trades.append(trade)
                        cash += trade.cost_basis + trade.pnl
                
                # Remove closed trades from open list
                for trade in closed_trades:
                    open_trades.remove(trade)
                    trades.append(trade)
                
                # Check entry signals
                if len(open_trades) < config.max_positions:
                    should_enter, entry_params = self._check_entry_signal(
                        config.strategy, current_date, current_price, current_iv, config
                    )
                    
                    if should_enter and cash >= config.initial_capital * config.position_size_pct:
                        trade_counter += 1
                        trade = self._open_trade(
                            trade_id=f"T{trade_counter:04d}",
                            strategy=config.strategy,
                            symbol=config.symbol,
                            entry_date=current_date,
                            entry_price=current_price,
                            cash=cash,
                            config=config,
                            params=entry_params
                        )
                        
                        if trade:
                            cash -= trade.cost_basis
                            open_trades.append(trade)
                
                # Calculate portfolio value
                positions_value = sum(
                    self._estimate_position_value(t, current_price, current_iv)
                    for t in open_trades
                )
                portfolio_value = cash + positions_value
                
                # Update high water mark and drawdown
                if portfolio_value > high_water_mark:
                    high_water_mark = portfolio_value
                drawdown_pct = (high_water_mark - portfolio_value) / high_water_mark * 100
                
                # Daily P&L
                prev_value = daily_snapshots[-1].portfolio_value if daily_snapshots else config.initial_capital
                daily_pnl = portfolio_value - prev_value
                cumulative_pnl = portfolio_value - config.initial_capital
                
                # Record snapshot
                snapshot = DailySnapshot(
                    date=current_date,
                    portfolio_value=portfolio_value,
                    cash=cash,
                    positions_value=positions_value,
                    daily_pnl=daily_pnl,
                    cumulative_pnl=cumulative_pnl,
                    open_positions=len(open_trades),
                    high_water_mark=high_water_mark,
                    drawdown_pct=drawdown_pct
                )
                daily_snapshots.append(snapshot)
            
            # Close any remaining open trades at end
            for trade in open_trades:
                final_price = bars[-1]['close']
                trade = self._close_trade(trade, config.end_date, final_price, "end_of_backtest")
                trades.append(trade)
            
            # Calculate summary metrics
            result = self._calculate_results(config, trades, daily_snapshots)
            
            logger.info(f"Backtest complete: {result.total_trades} trades, {result.total_return_pct:.2f}% return")
            
            return result
            
        finally:
            self._running = False
            self._progress = 1.0
    
    def _check_entry_signal(
        self,
        strategy: StrategyType,
        current_date: date,
        price: float,
        iv: float,
        config: BacktestConfig
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if entry conditions are met"""
        
        params = {}
        
        if strategy == StrategyType.IRON_CONDOR:
            # Enter when IV is elevated
            if iv >= config.iv_entry_threshold:
                # Calculate strikes based on delta target
                put_short = round(price * (1 - config.delta_target), 0)
                put_long = put_short - 5  # $5 wide
                call_short = round(price * (1 + config.delta_target), 0)
                call_long = call_short + 5  # $5 wide
                
                # Estimate premium (simplified)
                premium = iv * price * 0.05 * (config.days_to_expiration / 365) ** 0.5
                
                if premium >= config.min_premium:
                    params = {
                        'put_long': put_long,
                        'put_short': put_short,
                        'call_short': call_short,
                        'call_long': call_long,
                        'premium': premium,
                        'iv_at_entry': iv,
                    }
                    return True, params
        
        elif strategy == StrategyType.COVERED_CALL:
            # Enter on any day (simplified)
            call_strike = round(price * 1.05, 0)  # 5% OTM
            premium = iv * price * 0.02
            
            if premium >= config.min_premium * 0.5:
                params = {
                    'call_strike': call_strike,
                    'premium': premium,
                    'iv_at_entry': iv,
                }
                return True, params
        
        elif strategy == StrategyType.CASH_SECURED_PUT:
            # Enter when price dips
            put_strike = round(price * 0.95, 0)  # 5% OTM
            premium = iv * price * 0.015
            
            if premium >= config.min_premium * 0.5:
                params = {
                    'put_strike': put_strike,
                    'premium': premium,
                    'iv_at_entry': iv,
                }
                return True, params
        
        elif strategy in [StrategyType.LONG_CALL, StrategyType.LONG_PUT]:
            # Enter when IV is low (buy cheap options)
            if iv < config.iv_entry_threshold:
                strike = round(price, 0)  # ATM
                premium = iv * price * 0.03
                params = {
                    'strike': strike,
                    'premium': premium,
                    'iv_at_entry': iv,
                }
                return True, params
        
        return False, params
    
    def _check_exit_signal(
        self,
        trade: Trade,
        current_date: date,
        price: float,
        iv: float,
        config: BacktestConfig
    ) -> Tuple[bool, str]:
        """Check if exit conditions are met"""
        
        days_in_trade = (current_date - trade.entry_date).days
        
        # Time-based exit (expiration)
        if days_in_trade >= config.days_to_expiration:
            return True, "expiration"
        
        # Estimate current P&L
        current_pnl = self._estimate_unrealized_pnl(trade, price, iv, days_in_trade, config)
        pnl_pct = current_pnl / trade.cost_basis if trade.cost_basis > 0 else 0
        
        # Profit target
        if pnl_pct >= config.profit_target_pct:
            return True, "profit_target"
        
        # Stop loss
        if pnl_pct <= -config.stop_loss_pct:
            return True, "stop_loss"
        
        return False, ""
    
    def _open_trade(
        self,
        trade_id: str,
        strategy: StrategyType,
        symbol: str,
        entry_date: date,
        entry_price: float,
        cash: float,
        config: BacktestConfig,
        params: Dict[str, Any]
    ) -> Optional[Trade]:
        """Open a new trade"""
        
        # Calculate position size and cost
        position_size = max(1, int((cash * config.position_size_pct) / (entry_price * 100)))
        
        if strategy == StrategyType.IRON_CONDOR:
            # Credit received upfront
            premium = params.get('premium', 1.0)
            cost_basis = premium * 100 * position_size  # Credit (negative cost)
            # But we need margin/collateral
            spread_width = 5  # $5 wide spreads
            collateral = spread_width * 100 * position_size
            cost_basis = collateral - (premium * 100 * position_size)
        
        elif strategy == StrategyType.COVERED_CALL:
            # Buy stock + sell call
            premium = params.get('premium', 0.5)
            stock_cost = entry_price * 100 * position_size
            call_credit = premium * 100 * position_size
            cost_basis = stock_cost - call_credit
        
        elif strategy == StrategyType.CASH_SECURED_PUT:
            # Cash secured for assignment
            premium = params.get('premium', 0.5)
            put_strike = params.get('put_strike', entry_price * 0.95)
            cost_basis = put_strike * 100 * position_size - premium * 100 * position_size
        
        else:
            # Long options (debit)
            premium = params.get('premium', 1.0)
            cost_basis = premium * 100 * position_size
        
        if cost_basis > cash:
            return None
        
        return Trade(
            id=trade_id,
            strategy=strategy,
            symbol=symbol,
            entry_date=entry_date,
            entry_price=entry_price,
            position_size=position_size,
            cost_basis=cost_basis,
            metadata=params
        )
    
    def _close_trade(
        self,
        trade: Trade,
        exit_date: date,
        exit_price: float,
        reason: str
    ) -> Trade:
        """Close a trade and calculate P&L"""
        
        trade.exit_date = exit_date
        trade.exit_price = exit_price
        
        # Calculate P&L based on strategy
        if trade.strategy == StrategyType.IRON_CONDOR:
            # Iron Condor P&L
            entry_params = trade.metadata
            put_short = entry_params.get('put_short', trade.entry_price * 0.95)
            call_short = entry_params.get('call_short', trade.entry_price * 1.05)
            premium = entry_params.get('premium', 1.0)
            
            # Check if price is within short strikes
            if put_short <= exit_price <= call_short:
                # Max profit (keep premium)
                trade.pnl = premium * 100 * trade.position_size
            elif exit_price < put_short:
                # Loss on put side
                intrinsic = put_short - exit_price
                loss = min(intrinsic, 5)  # Capped by spread width
                trade.pnl = (premium - loss) * 100 * trade.position_size
            else:
                # Loss on call side
                intrinsic = exit_price - call_short
                loss = min(intrinsic, 5)  # Capped by spread width
                trade.pnl = (premium - loss) * 100 * trade.position_size
        
        elif trade.strategy == StrategyType.COVERED_CALL:
            # Stock + call P&L
            stock_pnl = (exit_price - trade.entry_price) * 100 * trade.position_size
            premium = trade.metadata.get('premium', 0.5)
            call_strike = trade.metadata.get('call_strike', trade.entry_price * 1.05)
            
            if exit_price >= call_strike:
                # Called away
                trade.pnl = (call_strike - trade.entry_price) * 100 * trade.position_size + premium * 100 * trade.position_size
            else:
                # Keep stock + premium
                trade.pnl = stock_pnl + premium * 100 * trade.position_size
        
        elif trade.strategy == StrategyType.CASH_SECURED_PUT:
            # Cash secured put P&L
            premium = trade.metadata.get('premium', 0.5)
            put_strike = trade.metadata.get('put_strike', trade.entry_price * 0.95)
            
            if exit_price >= put_strike:
                # Expires worthless, keep premium
                trade.pnl = premium * 100 * trade.position_size
            else:
                # Assigned, buy stock at strike
                loss = (put_strike - exit_price) * 100 * trade.position_size
                trade.pnl = premium * 100 * trade.position_size - loss
        
        else:
            # Long options
            # Simplified: assume we sell at intrinsic value
            premium_paid = trade.metadata.get('premium', 1.0)
            strike = trade.metadata.get('strike', trade.entry_price)
            
            if trade.strategy == StrategyType.LONG_CALL:
                intrinsic = max(0, exit_price - strike)
            else:  # LONG_PUT
                intrinsic = max(0, strike - exit_price)
            
            trade.pnl = (intrinsic - premium_paid) * 100 * trade.position_size
        
        # Set status
        if reason == "stop_loss":
            trade.status = TradeStatus.STOPPED_OUT
        elif reason == "expiration":
            trade.status = TradeStatus.EXPIRED
        else:
            trade.status = TradeStatus.CLOSED
        
        return trade
    
    def _estimate_position_value(self, trade: Trade, current_price: float, current_iv: float) -> float:
        """Estimate current market value of a position"""
        
        days_held = (date.today() - trade.entry_date).days
        time_decay = max(0.1, 1 - days_held / 30)  # Simplified theta decay
        
        if trade.strategy == StrategyType.IRON_CONDOR:
            premium = trade.metadata.get('premium', 1.0)
            # Value decreases as we approach expiration (good for sellers)
            current_value = premium * time_decay * 100 * trade.position_size
            return trade.cost_basis - current_value
        
        elif trade.strategy in [StrategyType.COVERED_CALL, StrategyType.CASH_SECURED_PUT]:
            # Approximate mark-to-market
            return trade.cost_basis * (1 + np.random.normal(0, 0.02))
        
        else:
            # Long options decay
            premium = trade.metadata.get('premium', 1.0)
            return premium * time_decay * 100 * trade.position_size
    
    def _estimate_unrealized_pnl(
        self,
        trade: Trade,
        current_price: float,
        current_iv: float,
        days_held: int,
        config: BacktestConfig
    ) -> float:
        """Estimate unrealized P&L for exit decision"""
        
        if trade.strategy == StrategyType.IRON_CONDOR:
            entry_params = trade.metadata
            premium = entry_params.get('premium', 1.0)
            put_short = entry_params.get('put_short', trade.entry_price * 0.95)
            call_short = entry_params.get('call_short', trade.entry_price * 1.05)
            
            # Time decay
            time_remaining = max(0.1, (config.days_to_expiration - days_held) / config.days_to_expiration)
            
            # Distance from strikes
            if put_short <= current_price <= call_short:
                # Safe zone, profit from theta
                profit_pct = 1 - time_remaining
                return premium * profit_pct * 100 * trade.position_size
            else:
                # In danger zone
                if current_price < put_short:
                    loss = (put_short - current_price) * time_remaining
                else:
                    loss = (current_price - call_short) * time_remaining
                return (premium - loss) * 100 * trade.position_size
        
        # Simplified for other strategies
        return 0.0
    
    def _calculate_results(
        self,
        config: BacktestConfig,
        trades: List[Trade],
        daily_snapshots: List[DailySnapshot]
    ) -> BacktestResult:
        """Calculate summary statistics from backtest"""
        
        if not daily_snapshots:
            raise ValueError("No daily snapshots recorded")
        
        # Basic metrics
        final_value = daily_snapshots[-1].portfolio_value
        total_return_pct = ((final_value - config.initial_capital) / config.initial_capital) * 100
        
        # Equity curve and drawdown
        equity_curve = [s.portfolio_value for s in daily_snapshots]
        drawdown_series = [s.drawdown_pct for s in daily_snapshots]
        dates = [s.date for s in daily_snapshots]
        
        max_drawdown_pct = max(drawdown_series) if drawdown_series else 0.0
        
        # Trade statistics
        total_trades = len(trades)
        pnls = [t.pnl for t in trades]
        
        winning_trades = len([p for p in pnls if p > 0])
        losing_trades = len([p for p in pnls if p <= 0])
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        wins = [p for p in pnls if p > 0]
        losses = [abs(p) for p in pnls if p < 0]
        
        avg_win = np.mean(wins) if wins else 0.0
        avg_loss = np.mean(losses) if losses else 0.0
        
        total_wins = sum(wins) if wins else 0.0
        total_losses = sum(losses) if losses else 0.0
        profit_factor = (total_wins / total_losses) if total_losses > 0 else float('inf')
        
        best_trade = max(pnls) if pnls else 0.0
        worst_trade = min(pnls) if pnls else 0.0
        
        # Average days in trade
        days_in_trade = [
            (t.exit_date - t.entry_date).days
            for t in trades
            if t.exit_date
        ]
        avg_days_in_trade = np.mean(days_in_trade) if days_in_trade else 0.0
        
        # Sharpe ratio (annualized)
        daily_returns = []
        for i in range(1, len(daily_snapshots)):
            prev_val = daily_snapshots[i-1].portfolio_value
            curr_val = daily_snapshots[i].portfolio_value
            daily_ret = (curr_val - prev_val) / prev_val if prev_val > 0 else 0
            daily_returns.append(daily_ret)
        
        if daily_returns:
            mean_return = np.mean(daily_returns)
            std_return = np.std(daily_returns)
            sharpe_ratio = (mean_return / std_return * np.sqrt(252)) if std_return > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        return BacktestResult(
            config=config,
            trades=trades,
            daily_snapshots=daily_snapshots,
            total_return_pct=total_return_pct,
            sharpe_ratio=sharpe_ratio,
            max_drawdown_pct=max_drawdown_pct,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_win=avg_win,
            avg_loss=avg_loss,
            best_trade=best_trade,
            worst_trade=worst_trade,
            avg_days_in_trade=avg_days_in_trade,
            equity_curve=equity_curve,
            drawdown_series=drawdown_series,
            dates=dates
        )
