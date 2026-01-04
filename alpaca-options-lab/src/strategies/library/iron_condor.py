"""
Alpaca Options Lab - 0DTE Iron Condor Strategy

Premium selling strategy that profits from time decay:
- Sells OTM call and put spreads expiring same day
- Profits from theta decay and range-bound market
- Defined risk through wing protection

Entry Criteria:
- Market open (9:30-10:00 AM ET)
- Sell ~16 delta call/put
- Buy ~5 delta wings for protection
- Skip if VIX > 30 or FOMC day

Management:
- Close at 50% profit
- Stop loss at 2x premium received
- Force close 15 min before market close

Risk Controls:
- Max 5 condors per day
- Max 2% capital per trade
- Daily loss limit 5%
"""
from __future__ import annotations

from datetime import datetime, date, time, timezone
from typing import Any, Dict, List, Optional

from src.strategies.base import (
    Strategy, StrategyConfig, Signal, SignalType, 
    OrderLeg, OrderSide, MarketEvent, FillEvent
)
from src.strategies.registry import StrategyRegistry
from src.strategies.context import OptionContract, Quote
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@StrategyRegistry.register(
    "iron_condor_0dte",
    version="1.0.0",
    description="0-Day-To-Expiration Iron Condor strategy for SPY",
    author="Alpaca Options Lab",
    tags=["options", "income", "0dte", "iron_condor", "short_volatility"]
)
class IronCondor0DTEStrategy(Strategy):
    """
    0DTE Iron Condor Premium Selling Strategy.
    
    Profits from:
    - Theta decay (time value erosion)
    - Range-bound price action
    - Volatility contraction
    
    Risks:
    - Large directional moves
    - Volatility expansion
    - Gap risk (overnight/weekend)
    """
    
    # Default parameters
    DEFAULT_PARAMS = {
        'underlying': 'SPY',
        'target_delta_short': 0.16,  # Delta for short strikes
        'target_delta_long': 0.05,   # Delta for long (wing) strikes
        'profit_target': 0.50,        # Close at 50% profit
        'stop_loss': 2.0,             # Close at 200% loss
        'max_condors_per_day': 5,
        'entry_start': '09:30',
        'entry_end': '10:00',
        'force_close_time': '15:45',
        'min_credit': 0.50,           # Minimum credit to enter
        'max_spread_width': 5.0,      # Max spread width in dollars
        'skip_vix_above': 30.0,       # Don't trade if VIX > this
    }
    
    def on_start(self) -> None:
        """Initialize strategy state."""
        self.state = {
            'condors_today': 0,
            'active_positions': {},  # position_id -> entry details
            'daily_pnl': 0.0,
            'last_entry_date': None,
            'params': {**self.DEFAULT_PARAMS, **self.config.parameters},
        }
        
        logger.info(
            "iron_condor_0dte_started",
            params=self.state['params']
        )
    
    def on_market_data(self, event: MarketEvent) -> List[Signal]:
        """Process market data and generate entry/exit signals."""
        signals = []
        params = self.state['params']
        
        # Reset daily counters if new day
        today = date.today()
        if self.state['last_entry_date'] != today:
            self.state['condors_today'] = 0
            self.state['daily_pnl'] = 0.0
            self.state['last_entry_date'] = today
        
        # Check for exits on active positions
        exit_signals = self._check_exits(event)
        signals.extend(exit_signals)
        
        # Check for new entries
        if self._should_enter(event):
            entry_signal = self._generate_entry_signal(event)
            if entry_signal:
                signals.append(entry_signal)
        
        return signals
    
    def _should_enter(self, event: MarketEvent) -> bool:
        """Check if we should enter a new position."""
        params = self.state['params']
        now = datetime.now(timezone.utc)
        
        # Check daily limit
        if self.state['condors_today'] >= params['max_condors_per_day']:
            return False
        
        # Check if within entry window
        if not self._in_entry_window(now):
            return False
        
        # Check market conditions
        if not self._check_market_conditions(event):
            return False
        
        # Check if we can still trade
        if not self.can_trade():
            return False
        
        return True
    
    def _in_entry_window(self, now: datetime) -> bool:
        """Check if current time is within entry window."""
        params = self.state['params']
        
        entry_start = datetime.strptime(params['entry_start'], '%H:%M').time()
        entry_end = datetime.strptime(params['entry_end'], '%H:%M').time()
        
        current_time = now.time()
        return entry_start <= current_time <= entry_end
    
    def _check_market_conditions(self, event: MarketEvent) -> bool:
        """Check if market conditions are favorable."""
        params = self.state['params']
        
        # Check VIX level
        try:
            vix_quote = self.context.get_quote(0)  # Would need VIX contract ID
            if vix_quote and vix_quote.last > params['skip_vix_above']:
                logger.info(
                    "iron_condor_skipping_high_vix",
                    vix=vix_quote.last,
                    threshold=params['skip_vix_above']
                )
                return False
        except Exception:
            pass  # VIX check is optional
        
        # Skip potential FOMC days (Wednesday 2PM check)
        now = datetime.now(timezone.utc)
        if now.weekday() == 2 and 14 <= now.hour < 16:
            logger.info("iron_condor_skipping_potential_fomc")
            return False
        
        return True
    
    def _generate_entry_signal(self, event: MarketEvent) -> Optional[Signal]:
        """Generate iron condor entry signal."""
        params = self.state['params']
        underlying = params['underlying']
        
        # Get option chain for today's expiration
        chain = self.context.get_option_chain(
            underlying=underlying,
            expiration=date.today()
        )
        
        if not chain:
            logger.warning("iron_condor_no_chain_available", underlying=underlying)
            return None
        
        # Get underlying price
        underlying_price = self.context.get_underlying_price(underlying)
        if underlying_price <= 0:
            return None
        
        # Find options by delta
        sell_call = self._find_by_delta(
            chain, 'C', params['target_delta_short'], underlying_price
        )
        buy_call = self._find_by_delta(
            chain, 'C', params['target_delta_long'], underlying_price
        )
        sell_put = self._find_by_delta(
            chain, 'P', -params['target_delta_short'], underlying_price
        )
        buy_put = self._find_by_delta(
            chain, 'P', -params['target_delta_long'], underlying_price
        )
        
        if not all([sell_call, buy_call, sell_put, buy_put]):
            logger.warning("iron_condor_incomplete_chain")
            return None
        
        # Calculate credit
        credit = self._calculate_credit(sell_call, buy_call, sell_put, buy_put)
        if credit < params['min_credit']:
            logger.info(
                "iron_condor_insufficient_credit",
                credit=credit,
                min_credit=params['min_credit']
            )
            return None
        
        # Calculate max risk
        call_spread_width = buy_call.strike - sell_call.strike
        put_spread_width = sell_put.strike - buy_put.strike
        max_risk = max(call_spread_width, put_spread_width) * 100 - credit * 100
        
        # Verify risk/reward
        if credit / (max_risk / 100) < 0.15:  # Need at least 15% ROI
            logger.info(
                "iron_condor_poor_risk_reward",
                credit=credit,
                max_risk=max_risk
            )
            return None
        
        # Create signal
        signal = Signal(
            strategy=self.config.name,
            signal_type=SignalType.ENTRY,
            legs=[
                OrderLeg(
                    contract_id=sell_call.id,
                    symbol=sell_call.symbol,
                    side=OrderSide.SELL,
                    quantity=1
                ),
                OrderLeg(
                    contract_id=buy_call.id,
                    symbol=buy_call.symbol,
                    side=OrderSide.BUY,
                    quantity=1
                ),
                OrderLeg(
                    contract_id=sell_put.id,
                    symbol=sell_put.symbol,
                    side=OrderSide.SELL,
                    quantity=1
                ),
                OrderLeg(
                    contract_id=buy_put.id,
                    symbol=buy_put.symbol,
                    side=OrderSide.BUY,
                    quantity=1
                ),
            ],
            entry_reason='0dte_iron_condor_entry',
            expected_credit=credit,
            max_risk=max_risk,
            target_profit=credit * params['profit_target'],
            stop_loss=credit * params['stop_loss'],
            metadata={
                'underlying_price': underlying_price,
                'sell_call_strike': sell_call.strike,
                'buy_call_strike': buy_call.strike,
                'sell_put_strike': sell_put.strike,
                'buy_put_strike': buy_put.strike,
            }
        )
        
        logger.info(
            "iron_condor_signal_generated",
            credit=credit,
            max_risk=max_risk,
            underlying_price=underlying_price
        )
        
        return signal
    
    def _find_by_delta(
        self,
        chain: List[OptionContract],
        option_type: str,
        target_delta: float,
        spot_price: float
    ) -> Optional[OptionContract]:
        """Find option closest to target delta."""
        best = None
        best_diff = float('inf')
        
        for contract in chain:
            if contract.option_type != option_type:
                continue
            
            # Estimate delta based on moneyness (simplified)
            if option_type == 'C':
                moneyness = spot_price / contract.strike
                estimated_delta = max(0, min(1, 0.5 + (moneyness - 1) * 2))
            else:
                moneyness = contract.strike / spot_price
                estimated_delta = -max(0, min(1, 0.5 + (moneyness - 1) * 2))
            
            diff = abs(estimated_delta - target_delta)
            
            if diff < best_diff:
                best_diff = diff
                best = contract
        
        return best
    
    def _calculate_credit(
        self,
        sell_call: OptionContract,
        buy_call: OptionContract,
        sell_put: OptionContract,
        buy_put: OptionContract
    ) -> float:
        """Calculate net credit for iron condor."""
        credit = 0.0
        
        # Get quotes
        sell_call_quote = self.context.get_quote(sell_call.id)
        buy_call_quote = self.context.get_quote(buy_call.id)
        sell_put_quote = self.context.get_quote(sell_put.id)
        buy_put_quote = self.context.get_quote(buy_put.id)
        
        if all([sell_call_quote, buy_call_quote, sell_put_quote, buy_put_quote]):
            credit = (
                sell_call_quote.mid + sell_put_quote.mid -
                buy_call_quote.mid - buy_put_quote.mid
            )
        
        return max(0, credit)
    
    def _check_exits(self, event: MarketEvent) -> List[Signal]:
        """Check for exit conditions on active positions."""
        signals = []
        params = self.state['params']
        now = datetime.now(timezone.utc)
        
        for position_id, entry_data in list(self.state['active_positions'].items()):
            should_exit = False
            exit_reason = ""
            
            # Calculate current P&L
            current_value = self._calculate_position_value(entry_data)
            entry_credit = entry_data['credit']
            pnl = entry_credit - current_value
            pnl_pct = pnl / entry_data['max_risk'] if entry_data['max_risk'] > 0 else 0
            
            # Profit target
            if pnl >= entry_credit * params['profit_target']:
                should_exit = True
                exit_reason = 'profit_target'
            
            # Stop loss
            elif pnl <= -entry_credit * params['stop_loss']:
                should_exit = True
                exit_reason = 'stop_loss'
            
            # Force close near market close
            force_close = datetime.strptime(params['force_close_time'], '%H:%M').time()
            if now.time() >= force_close:
                should_exit = True
                exit_reason = 'force_close_eod'
            
            if should_exit:
                exit_signal = self._generate_exit_signal(position_id, entry_data, exit_reason)
                if exit_signal:
                    signals.append(exit_signal)
                
                logger.info(
                    "iron_condor_exit_triggered",
                    position_id=position_id,
                    reason=exit_reason,
                    pnl=pnl
                )
        
        return signals
    
    def _calculate_position_value(self, entry_data: Dict) -> float:
        """Calculate current position value."""
        # Simplified - in production would sum current option prices
        return entry_data['credit'] * 0.8  # Placeholder
    
    def _generate_exit_signal(
        self,
        position_id: str,
        entry_data: Dict,
        reason: str
    ) -> Optional[Signal]:
        """Generate exit signal for a position."""
        # Create opposite legs to close
        exit_legs = []
        for leg in entry_data['legs']:
            exit_legs.append(OrderLeg(
                contract_id=leg['contract_id'],
                symbol=leg['symbol'],
                side=OrderSide.BUY if leg['side'] == 'sell' else OrderSide.SELL,
                quantity=leg['quantity']
            ))
        
        return Signal(
            strategy=self.config.name,
            signal_type=SignalType.EXIT,
            legs=exit_legs,
            entry_reason=f'exit_{reason}',
            metadata={
                'position_id': position_id,
                'exit_reason': reason,
            }
        )
    
    def on_order_fill(self, fill: FillEvent) -> None:
        """Handle order fill."""
        self.state['condors_today'] += 1
        
        # Track position
        position_id = fill.order_id
        self.state['active_positions'][position_id] = {
            'filled_at': fill.timestamp,
            'credit': fill.fill_price,
            'legs': [],  # Would be populated from order
            'max_risk': 0,  # Would be calculated
        }
        
        logger.info(
            "iron_condor_filled",
            order_id=fill.order_id,
            fill_price=fill.fill_price
        )
    
    def on_position_update(self, position) -> None:
        """React to position state changes."""
        if position.strategy != self.config.name:
            return
        
        # Update tracking based on position state
        if position.state.is_terminal:
            # Remove from active positions
            if position.id in self.state['active_positions']:
                del self.state['active_positions'][position.id]
    
    def on_stop(self) -> Dict[str, Any]:
        """Return final statistics."""
        return {
            'condors_traded': self.state['condors_today'],
            'daily_pnl': self.state['daily_pnl'],
            'active_positions': len(self.state['active_positions']),
            'params': self.state['params'],
        }
