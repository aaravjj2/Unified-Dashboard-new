"""
Alpaca Options Lab - Delta Neutral Strategy

Market-making style strategy that profits from gamma:
- Maintain delta-neutral portfolio
- Profit from gamma scalping as underlying moves
- Hedge theta decay with realized volatility

Entry:
- Buy ATM straddle (long gamma)
- Delta hedge continuously

Management:
- Rebalance delta at thresholds
- Close if theta > expected gamma profits
- Roll before expiration
"""
from __future__ import annotations

from datetime import datetime, date, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.strategies.base import (
    Strategy, StrategyConfig, Signal, SignalType,
    OrderLeg, OrderSide, MarketEvent, FillEvent
)
from src.strategies.registry import StrategyRegistry
from src.strategies.context import OptionContract
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@StrategyRegistry.register(
    "delta_neutral",
    version="1.0.0",
    description="Delta-neutral gamma scalping strategy",
    author="Alpaca Options Lab",
    tags=["options", "delta_neutral", "gamma", "scalping", "market_making"]
)
class DeltaNeutralStrategy(Strategy):
    """
    Delta-Neutral Gamma Scalping Strategy.
    
    Profits from:
    - Gamma (convexity) - larger moves = more profit
    - Realized volatility > implied volatility
    - Bid-ask spread capture
    
    Risks:
    - Theta decay (time value erosion)
    - Low realized volatility
    - Execution costs from rebalancing
    """
    
    DEFAULT_PARAMS = {
        'underlying': 'SPY',
        'target_dte': 30,           # Days to expiration
        'delta_threshold': 0.10,    # Rebalance when |delta| > 10
        'max_rebalances_per_day': 20,
        'min_move_to_scalp': 0.25,  # Min % move to trigger scalp
        'profit_target': 0.20,      # 20% of debit
        'max_loss': 0.50,           # 50% of debit
        'roll_at_dte': 7,           # Roll when 7 DTE
    }
    
    def on_start(self) -> None:
        """Initialize strategy state."""
        self.state = {
            'params': {**self.DEFAULT_PARAMS, **self.config.parameters},
            'position': None,  # Current straddle position
            'hedge_shares': 0,  # Delta hedge in shares
            'last_hedge_price': None,
            'rebalances_today': 0,
            'scalp_pnl': 0.0,
            'last_rebalance_date': None,
        }
        
        logger.info("delta_neutral_started", params=self.state['params'])
    
    def on_market_data(self, event: MarketEvent) -> List[Signal]:
        """Process market data for delta neutral management."""
        signals = []
        params = self.state['params']
        underlying = params['underlying']
        
        # Reset daily counters
        today = date.today()
        if self.state['last_rebalance_date'] != today:
            self.state['rebalances_today'] = 0
            self.state['last_rebalance_date'] = today
        
        # If no position, look to enter
        if not self.state['position']:
            entry_signal = self._generate_entry_signal(event)
            if entry_signal:
                signals.append(entry_signal)
            return signals
        
        # Check for exit conditions
        exit_signal = self._check_exit_conditions(event)
        if exit_signal:
            signals.append(exit_signal)
            return signals
        
        # Check for delta rebalancing
        hedge_signal = self._check_delta_hedge(event)
        if hedge_signal:
            signals.append(hedge_signal)
        
        return signals
    
    def _generate_entry_signal(self, event: MarketEvent) -> Optional[Signal]:
        """Generate straddle entry signal."""
        params = self.state['params']
        underlying = params['underlying']
        
        underlying_price = self.context.get_underlying_price(underlying)
        if underlying_price <= 0:
            return None
        
        # Find expiration around target DTE
        expiration = date.today() + timedelta(days=params['target_dte'])
        chain = self.context.get_option_chain(underlying, expiration)
        
        if not chain:
            return None
        
        # Find ATM call and put
        atm_call = self._find_atm_option(chain, 'C', underlying_price)
        atm_put = self._find_atm_option(chain, 'P', underlying_price)
        
        if not atm_call or not atm_put:
            return None
        
        # Get quotes
        call_quote = self.context.get_quote(atm_call.id)
        put_quote = self.context.get_quote(atm_put.id)
        
        if not call_quote or not put_quote:
            return None
        
        # Calculate straddle debit
        debit = call_quote.ask + put_quote.ask
        
        return Signal(
            strategy=self.config.name,
            signal_type=SignalType.ENTRY,
            legs=[
                OrderLeg(
                    contract_id=atm_call.id,
                    symbol=atm_call.symbol,
                    side=OrderSide.BUY,
                    quantity=1,
                    price=call_quote.ask
                ),
                OrderLeg(
                    contract_id=atm_put.id,
                    symbol=atm_put.symbol,
                    side=OrderSide.BUY,
                    quantity=1,
                    price=put_quote.ask
                ),
            ],
            entry_reason='delta_neutral_straddle',
            expected_debit=debit,
            max_risk=debit * 100,
            metadata={
                'underlying': underlying,
                'strike': atm_call.strike,
                'expiration': str(atm_call.expiration),
                'underlying_price': underlying_price,
            }
        )
    
    def _find_atm_option(
        self,
        chain: List[OptionContract],
        option_type: str,
        spot_price: float
    ) -> Optional[OptionContract]:
        """Find ATM option."""
        candidates = [c for c in chain if c.option_type == option_type]
        if not candidates:
            return None
        return min(candidates, key=lambda c: abs(c.strike - spot_price))
    
    def _check_delta_hedge(self, event: MarketEvent) -> Optional[Signal]:
        """Check if delta hedge is needed."""
        params = self.state['params']
        
        if self.state['rebalances_today'] >= params['max_rebalances_per_day']:
            return None
        
        if not self.state['position']:
            return None
        
        # Calculate current position delta
        portfolio_greeks = self.get_portfolio_greeks()
        current_delta = portfolio_greeks.get('delta', 0)
        
        # Add share hedge delta
        total_delta = current_delta + self.state['hedge_shares'] / 100
        
        # Check if rebalance needed
        if abs(total_delta) < params['delta_threshold']:
            return None
        
        # Calculate shares to hedge
        shares_to_trade = -int(total_delta * 100)
        if shares_to_trade == 0:
            return None
        
        self.state['rebalances_today'] += 1
        
        logger.info(
            "delta_hedge_triggered",
            current_delta=total_delta,
            shares_to_trade=shares_to_trade
        )
        
        # Return signal for share trade
        return Signal(
            strategy=self.config.name,
            signal_type=SignalType.ADJUSTMENT,
            legs=[],  # Share trade handled separately
            entry_reason='delta_hedge',
            metadata={
                'shares': shares_to_trade,
                'current_delta': total_delta,
            }
        )
    
    def _check_exit_conditions(self, event: MarketEvent) -> Optional[Signal]:
        """Check for exit conditions."""
        params = self.state['params']
        position = self.state['position']
        
        if not position:
            return None
        
        # Calculate P&L
        current_value = self._calculate_position_value()
        entry_debit = position['entry_debit']
        pnl = current_value - entry_debit
        pnl_pct = pnl / entry_debit if entry_debit > 0 else 0
        
        should_exit = False
        reason = ""
        
        # Profit target
        if pnl_pct >= params['profit_target']:
            should_exit = True
            reason = 'profit_target'
        
        # Max loss
        elif pnl_pct <= -params['max_loss']:
            should_exit = True
            reason = 'stop_loss'
        
        # Near expiration - roll
        dte = (position['expiration'] - date.today()).days
        if dte <= params['roll_at_dte']:
            should_exit = True
            reason = 'roll_expiry'
        
        if should_exit:
            return self._generate_exit_signal(reason)
        
        return None
    
    def _calculate_position_value(self) -> float:
        """Calculate current position value."""
        # Simplified - would get actual quotes
        if not self.state['position']:
            return 0.0
        return self.state['position']['entry_debit'] * 0.95  # Placeholder
    
    def _generate_exit_signal(self, reason: str) -> Signal:
        """Generate exit signal."""
        position = self.state['position']
        
        return Signal(
            strategy=self.config.name,
            signal_type=SignalType.EXIT,
            legs=[
                OrderLeg(
                    contract_id=position['call_id'],
                    symbol=position['call_symbol'],
                    side=OrderSide.SELL,
                    quantity=1
                ),
                OrderLeg(
                    contract_id=position['put_id'],
                    symbol=position['put_symbol'],
                    side=OrderSide.SELL,
                    quantity=1
                ),
            ],
            entry_reason=f'delta_neutral_exit_{reason}',
            metadata={
                'reason': reason,
                'hedge_shares': self.state['hedge_shares'],
            }
        )
    
    def on_order_fill(self, fill: FillEvent) -> None:
        """Handle order fill."""
        if 'delta_hedge' in fill.correlation_id:
            # Update hedge shares
            # Actual implementation would parse fill details
            pass
        else:
            # Straddle fill
            logger.info(
                "delta_neutral_filled",
                order_id=fill.order_id,
                fill_price=fill.fill_price
            )
    
    def on_position_update(self, position) -> None:
        """React to position changes."""
        pass
    
    def on_stop(self) -> Dict[str, Any]:
        """Return final statistics."""
        return {
            'scalp_pnl': self.state['scalp_pnl'],
            'total_rebalances': self.state['rebalances_today'],
            'final_hedge_shares': self.state['hedge_shares'],
        }
