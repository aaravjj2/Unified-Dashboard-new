"""
Alpaca Options Lab - Calendar Spread Strategy

Volatility arbitrage strategy exploiting term structure:
- Sell front-month option (high theta decay)
- Buy back-month option (volatility protection)
- Profit from vol term structure and time decay

Entry Criteria:
- IV in front month > IV in back month (contango)
- ATM options for maximum vega
- 7-14 DTE front leg, 30-45 DTE back leg

Management:
- Close at 25% profit
- Close if front leg < 7 DTE
- Roll front leg if profitable
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
    "calendar_spread",
    version="1.0.0",
    description="Calendar spread volatility arbitrage",
    author="Alpaca Options Lab",
    tags=["options", "volatility", "calendar", "spread", "arbitrage"]
)
class CalendarSpreadStrategy(Strategy):
    """
    Calendar Spread Volatility Arbitrage Strategy.
    
    Profits from:
    - Theta decay differential (front decays faster)
    - Volatility term structure normalization
    - Implied volatility increase
    
    Risks:
    - Large directional moves
    - Volatility collapse
    - Term structure inversion
    """
    
    DEFAULT_PARAMS = {
        'underlyings': ['SPY', 'QQQ', 'IWM'],
        'option_type': 'C',  # Calls or puts
        'front_dte_min': 7,
        'front_dte_max': 14,
        'back_dte_min': 30,
        'back_dte_max': 45,
        'min_iv_diff': 0.02,  # 2% IV difference required
        'profit_target': 0.25,
        'stop_loss': 0.50,
        'max_spreads': 5,
    }
    
    def on_start(self) -> None:
        """Initialize strategy state."""
        self.state = {
            'params': {**self.DEFAULT_PARAMS, **self.config.parameters},
            'spreads': {},  # spread_id -> details
            'daily_spreads': 0,
        }
        
        logger.info("calendar_spread_started", params=self.state['params'])
    
    def on_market_data(self, event: MarketEvent) -> List[Signal]:
        """Process market data for calendar spread opportunities."""
        signals = []
        params = self.state['params']
        
        # Check for exits first
        exit_signals = self._check_exits(event)
        signals.extend(exit_signals)
        
        # Look for new entries
        if len(self.state['spreads']) < params['max_spreads']:
            for underlying in params['underlyings']:
                entry_signal = self._find_calendar_opportunity(underlying, event)
                if entry_signal:
                    signals.append(entry_signal)
                    break  # One entry per event
        
        return signals
    
    def _find_calendar_opportunity(
        self, 
        underlying: str, 
        event: MarketEvent
    ) -> Optional[Signal]:
        """Find calendar spread opportunity."""
        params = self.state['params']
        
        underlying_price = self.context.get_underlying_price(underlying)
        if underlying_price <= 0:
            return None
        
        # Find front and back month expirations
        front_exp = date.today() + timedelta(days=params['front_dte_min'])
        back_exp = date.today() + timedelta(days=params['back_dte_min'])
        
        front_chain = self.context.get_option_chain(underlying, front_exp)
        back_chain = self.context.get_option_chain(underlying, back_exp)
        
        if not front_chain or not back_chain:
            return None
        
        # Find ATM options
        front_option = self._find_atm_option(
            front_chain, params['option_type'], underlying_price
        )
        back_option = self._find_atm_option(
            back_chain, params['option_type'], underlying_price
        )
        
        if not front_option or not back_option:
            return None
        
        # Check IV differential
        front_iv = self._estimate_iv(front_option, underlying_price)
        back_iv = self._estimate_iv(back_option, underlying_price)
        
        if front_iv - back_iv < params['min_iv_diff']:
            logger.debug(
                "calendar_insufficient_iv_diff",
                underlying=underlying,
                front_iv=front_iv,
                back_iv=back_iv
            )
            return None
        
        # Get quotes
        front_quote = self.context.get_quote(front_option.id)
        back_quote = self.context.get_quote(back_option.id)
        
        if not front_quote or not back_quote:
            return None
        
        # Calculate debit
        debit = back_quote.ask - front_quote.bid
        if debit <= 0:
            return None
        
        return Signal(
            strategy=self.config.name,
            signal_type=SignalType.ENTRY,
            legs=[
                OrderLeg(
                    contract_id=front_option.id,
                    symbol=front_option.symbol,
                    side=OrderSide.SELL,
                    quantity=1,
                    price=front_quote.bid
                ),
                OrderLeg(
                    contract_id=back_option.id,
                    symbol=back_option.symbol,
                    side=OrderSide.BUY,
                    quantity=1,
                    price=back_quote.ask
                ),
            ],
            entry_reason='calendar_spread_entry',
            expected_debit=debit,
            max_risk=debit * 100,
            metadata={
                'underlying': underlying,
                'strike': front_option.strike,
                'front_exp': str(front_option.expiration),
                'back_exp': str(back_option.expiration),
                'front_iv': front_iv,
                'back_iv': back_iv,
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
    
    def _estimate_iv(self, contract: OptionContract, spot: float) -> float:
        """Estimate implied volatility (simplified)."""
        # In production, would use actual IV from market data
        moneyness = abs(contract.strike - spot) / spot
        base_iv = 0.20  # 20% base
        return base_iv + moneyness * 0.5  # Skew adjustment
    
    def _check_exits(self, event: MarketEvent) -> List[Signal]:
        """Check for exit conditions."""
        signals = []
        params = self.state['params']
        
        for spread_id, spread_data in list(self.state['spreads'].items()):
            should_exit = False
            reason = ""
            
            # Calculate current spread value
            current_value = self._calculate_spread_value(spread_data)
            entry_debit = spread_data['entry_debit']
            pnl = current_value - entry_debit
            pnl_pct = pnl / entry_debit if entry_debit > 0 else 0
            
            # Profit target
            if pnl_pct >= params['profit_target']:
                should_exit = True
                reason = 'profit_target'
            
            # Stop loss
            elif pnl_pct <= -params['stop_loss']:
                should_exit = True
                reason = 'stop_loss'
            
            # Front leg near expiration
            front_dte = (spread_data['front_exp'] - date.today()).days
            if front_dte <= 3:
                should_exit = True
                reason = 'front_near_expiry'
            
            if should_exit:
                signals.append(self._generate_exit_signal(spread_id, spread_data, reason))
        
        return signals
    
    def _calculate_spread_value(self, spread_data: Dict) -> float:
        """Calculate current spread value."""
        # Simplified - would get actual quotes in production
        return spread_data['entry_debit'] * 1.1  # Placeholder
    
    def _generate_exit_signal(
        self,
        spread_id: str,
        spread_data: Dict,
        reason: str
    ) -> Signal:
        """Generate exit signal."""
        return Signal(
            strategy=self.config.name,
            signal_type=SignalType.EXIT,
            legs=[
                OrderLeg(
                    contract_id=spread_data['front_id'],
                    symbol=spread_data['front_symbol'],
                    side=OrderSide.BUY,
                    quantity=1
                ),
                OrderLeg(
                    contract_id=spread_data['back_id'],
                    symbol=spread_data['back_symbol'],
                    side=OrderSide.SELL,
                    quantity=1
                ),
            ],
            entry_reason=f'calendar_exit_{reason}',
            metadata={
                'spread_id': spread_id,
                'reason': reason,
            }
        )
    
    def on_order_fill(self, fill: FillEvent) -> None:
        """Handle order fill."""
        logger.info(
            "calendar_spread_filled",
            order_id=fill.order_id,
            fill_price=fill.fill_price
        )
    
    def on_position_update(self, position) -> None:
        """React to position changes."""
        pass
    
    def on_stop(self) -> Dict[str, Any]:
        """Return final statistics."""
        return {
            'spreads_traded': self.state['daily_spreads'],
            'active_spreads': len(self.state['spreads']),
        }
