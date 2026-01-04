"""
Alpaca Options Lab - Covered Call Wheel Strategy

Income-generating strategy that combines:
1. Selling cash-secured puts to acquire stock at discount
2. Selling covered calls on owned shares for income
3. Repeat the "wheel" when called away

Entry (Put Side):
- Sell OTM put on stocks you want to own
- Strike at 5-10% below current price
- 30-45 DTE for optimal theta decay

Entry (Call Side):
- When assigned, sell covered call
- Strike at 5-10% above cost basis
- 30-45 DTE

Management:
- Roll puts down if stock drops significantly
- Let calls expire or get called away
- Close at 50% profit for early exit
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


class WheelPhase:
    """Current phase of the wheel."""
    CASH = "cash"           # Have cash, looking to sell puts
    PUT_OPEN = "put_open"   # Short put position open
    STOCK = "stock"         # Own stock, looking to sell calls
    CALL_OPEN = "call_open" # Short call position open


@StrategyRegistry.register(
    "covered_call_wheel",
    version="1.0.0",
    description="Wheel strategy: sell puts then covered calls",
    author="Alpaca Options Lab",
    tags=["options", "income", "wheel", "covered_call", "cash_secured_put"]
)
class CoveredCallWheelStrategy(Strategy):
    """
    Covered Call Wheel Income Strategy.
    
    Profits from:
    - Premium collection (theta decay)
    - Acquiring stock at discount via assignment
    - Selling upside via covered calls
    
    Risks:
    - Stock drops significantly
    - Miss large upside moves
    - Gap risk
    """
    
    DEFAULT_PARAMS = {
        'underlyings': ['AAPL', 'MSFT', 'GOOGL'],  # Stocks to wheel
        'put_delta': 0.30,           # Delta for short puts
        'call_delta': 0.30,          # Delta for short calls
        'min_dte': 30,               # Minimum days to expiration
        'max_dte': 45,               # Maximum days to expiration
        'profit_target': 0.50,       # Close at 50% profit
        'roll_at_loss': 1.5,         # Roll if losing 150%
        'max_positions_per_stock': 1,
        'position_size': 100,        # Shares per wheel
    }
    
    def on_start(self) -> None:
        """Initialize strategy state."""
        self.state = {
            'params': {**self.DEFAULT_PARAMS, **self.config.parameters},
            'wheels': {},  # underlying -> wheel state
            'positions': {},  # position_id -> details
        }
        
        # Initialize wheel state for each underlying
        for underlying in self.state['params']['underlyings']:
            self.state['wheels'][underlying] = {
                'phase': WheelPhase.CASH,
                'shares_owned': 0,
                'cost_basis': 0.0,
                'active_option': None,
                'total_premium_collected': 0.0,
            }
        
        logger.info(
            "wheel_strategy_started",
            underlyings=self.state['params']['underlyings']
        )
    
    def on_market_data(self, event: MarketEvent) -> List[Signal]:
        """Process market data for wheel opportunities."""
        signals = []
        params = self.state['params']
        
        for underlying in params['underlyings']:
            wheel = self.state['wheels'][underlying]
            
            if wheel['phase'] == WheelPhase.CASH:
                # Look for put selling opportunity
                signal = self._generate_put_signal(underlying, event)
                if signal:
                    signals.append(signal)
            
            elif wheel['phase'] == WheelPhase.STOCK:
                # Look for call selling opportunity
                signal = self._generate_call_signal(underlying, event)
                if signal:
                    signals.append(signal)
            
            elif wheel['phase'] in (WheelPhase.PUT_OPEN, WheelPhase.CALL_OPEN):
                # Check for management actions
                management_signals = self._check_position_management(underlying, event)
                signals.extend(management_signals)
        
        return signals
    
    def _generate_put_signal(
        self, 
        underlying: str, 
        event: MarketEvent
    ) -> Optional[Signal]:
        """Generate cash-secured put signal."""
        params = self.state['params']
        
        # Check capital availability
        available = self.get_available_capital()
        underlying_price = self.context.get_underlying_price(underlying)
        
        if underlying_price <= 0:
            return None
        
        capital_required = underlying_price * params['position_size']
        if available < capital_required:
            logger.debug(
                "wheel_insufficient_capital",
                underlying=underlying,
                required=capital_required,
                available=available
            )
            return None
        
        # Find appropriate expiration
        target_dte = (params['min_dte'] + params['max_dte']) // 2
        expiration = date.today() + timedelta(days=target_dte)
        
        # Get option chain
        chain = self.context.get_option_chain(underlying, expiration)
        if not chain:
            return None
        
        # Find put at target delta
        put = self._find_option_by_delta(
            chain, 'P', -params['put_delta'], underlying_price
        )
        
        if not put:
            return None
        
        # Get quote
        quote = self.context.get_quote(put.id)
        if not quote or quote.bid <= 0:
            return None
        
        # Create signal
        contracts = params['position_size'] // 100  # 1 contract = 100 shares
        
        return Signal(
            strategy=self.config.name,
            signal_type=SignalType.ENTRY,
            legs=[
                OrderLeg(
                    contract_id=put.id,
                    symbol=put.symbol,
                    side=OrderSide.SELL,
                    quantity=contracts,
                    price=quote.bid
                )
            ],
            entry_reason='wheel_sell_put',
            expected_credit=quote.bid * contracts * 100,
            metadata={
                'underlying': underlying,
                'strike': put.strike,
                'expiration': str(put.expiration),
                'phase': 'put',
            }
        )
    
    def _generate_call_signal(
        self, 
        underlying: str, 
        event: MarketEvent
    ) -> Optional[Signal]:
        """Generate covered call signal."""
        params = self.state['params']
        wheel = self.state['wheels'][underlying]
        
        if wheel['shares_owned'] < params['position_size']:
            return None
        
        underlying_price = self.context.get_underlying_price(underlying)
        if underlying_price <= 0:
            return None
        
        # Find appropriate expiration
        target_dte = (params['min_dte'] + params['max_dte']) // 2
        expiration = date.today() + timedelta(days=target_dte)
        
        # Get option chain
        chain = self.context.get_option_chain(underlying, expiration)
        if not chain:
            return None
        
        # Find call above cost basis
        target_strike = max(
            wheel['cost_basis'] * 1.05,  # At least 5% above cost
            underlying_price * (1 - params['call_delta'])
        )
        
        call = self._find_option_near_strike(chain, 'C', target_strike)
        if not call:
            return None
        
        quote = self.context.get_quote(call.id)
        if not quote or quote.bid <= 0:
            return None
        
        contracts = wheel['shares_owned'] // 100
        
        return Signal(
            strategy=self.config.name,
            signal_type=SignalType.ENTRY,
            legs=[
                OrderLeg(
                    contract_id=call.id,
                    symbol=call.symbol,
                    side=OrderSide.SELL,
                    quantity=contracts,
                    price=quote.bid
                )
            ],
            entry_reason='wheel_sell_call',
            expected_credit=quote.bid * contracts * 100,
            metadata={
                'underlying': underlying,
                'strike': call.strike,
                'expiration': str(call.expiration),
                'phase': 'call',
                'cost_basis': wheel['cost_basis'],
            }
        )
    
    def _find_option_by_delta(
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
            
            # Estimate delta
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
    
    def _find_option_near_strike(
        self,
        chain: List[OptionContract],
        option_type: str,
        target_strike: float
    ) -> Optional[OptionContract]:
        """Find option closest to target strike."""
        candidates = [c for c in chain if c.option_type == option_type]
        if not candidates:
            return None
        
        # Find strike >= target for calls
        if option_type == 'C':
            valid = [c for c in candidates if c.strike >= target_strike]
            if valid:
                return min(valid, key=lambda c: c.strike)
        else:
            valid = [c for c in candidates if c.strike <= target_strike]
            if valid:
                return max(valid, key=lambda c: c.strike)
        
        return min(candidates, key=lambda c: abs(c.strike - target_strike))
    
    def _check_position_management(
        self, 
        underlying: str, 
        event: MarketEvent
    ) -> List[Signal]:
        """Check for position management actions."""
        signals = []
        params = self.state['params']
        wheel = self.state['wheels'][underlying]
        
        if not wheel['active_option']:
            return signals
        
        option_id = wheel['active_option']['contract_id']
        entry_price = wheel['active_option']['entry_price']
        
        quote = self.context.get_quote(option_id)
        if not quote:
            return signals
        
        # Calculate P&L
        current_value = quote.ask  # Cost to buy back
        pnl = entry_price - current_value
        pnl_pct = pnl / entry_price if entry_price > 0 else 0
        
        # Profit target
        if pnl_pct >= params['profit_target']:
            signals.append(self._generate_close_signal(underlying, 'profit_target'))
        
        # Roll if losing
        elif pnl_pct <= -params['roll_at_loss']:
            signals.append(self._generate_roll_signal(underlying, 'roll_loss'))
        
        return signals
    
    def _generate_close_signal(
        self, 
        underlying: str, 
        reason: str
    ) -> Signal:
        """Generate signal to close position."""
        wheel = self.state['wheels'][underlying]
        option = wheel['active_option']
        
        return Signal(
            strategy=self.config.name,
            signal_type=SignalType.EXIT,
            legs=[
                OrderLeg(
                    contract_id=option['contract_id'],
                    symbol=option['symbol'],
                    side=OrderSide.BUY,
                    quantity=option['quantity']
                )
            ],
            entry_reason=f'wheel_close_{reason}',
            metadata={
                'underlying': underlying,
                'reason': reason,
            }
        )
    
    def _generate_roll_signal(
        self, 
        underlying: str, 
        reason: str
    ) -> Signal:
        """Generate signal to roll position."""
        # In production, would find new strike/expiration
        # For now, just close
        return self._generate_close_signal(underlying, reason)
    
    def on_order_fill(self, fill: FillEvent) -> None:
        """Handle order fill and update wheel state."""
        # Parse metadata to update wheel state
        logger.info(
            "wheel_order_filled",
            order_id=fill.order_id,
            symbol=fill.symbol,
            fill_price=fill.fill_price
        )
    
    def on_position_update(self, position) -> None:
        """React to position state changes."""
        if position.strategy != self.config.name:
            return
        
        # Handle assignment (put) or exercise (call)
        if position.state.value == 'assigned':
            # We got assigned on put - now own stock
            underlying = position.underlying
            if underlying in self.state['wheels']:
                wheel = self.state['wheels'][underlying]
                wheel['phase'] = WheelPhase.STOCK
                wheel['shares_owned'] = self.state['params']['position_size']
                wheel['cost_basis'] = position.strike
                wheel['active_option'] = None
                
                logger.info(
                    "wheel_assigned",
                    underlying=underlying,
                    shares=wheel['shares_owned'],
                    cost_basis=wheel['cost_basis']
                )
    
    def on_stop(self) -> Dict[str, Any]:
        """Return final statistics."""
        return {
            'wheels': self.state['wheels'],
            'total_premium': sum(
                w['total_premium_collected'] 
                for w in self.state['wheels'].values()
            ),
        }
