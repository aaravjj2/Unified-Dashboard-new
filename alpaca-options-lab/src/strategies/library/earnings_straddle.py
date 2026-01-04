"""
Alpaca Options Lab - Earnings Straddle Strategy

Event-driven strategy profiting from earnings volatility:
- Buy ATM straddle before earnings
- Profit from post-earnings move
- Close immediately after announcement

Entry:
- 1-3 days before earnings
- Buy ATM straddle
- Check IV rank for value

Exit:
- Close day after earnings
- Close at profit target
- Close at max loss
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
    "earnings_straddle",
    version="1.0.0",
    description="Earnings straddle event-driven strategy",
    author="Alpaca Options Lab",
    tags=["options", "earnings", "straddle", "event", "volatility"]
)
class EarningsStraddleStrategy(Strategy):
    """
    Earnings Straddle Event-Driven Strategy.
    
    Profits from:
    - Large post-earnings moves
    - Realized volatility > implied volatility
    - Event premium
    
    Risks:
    - IV crush after earnings
    - Flat moves (no reaction)
    - Overpaying for volatility
    """
    
    DEFAULT_PARAMS = {
        'watchlist': ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'META', 'NVDA', 'TSLA'],
        'entry_days_before': 2,      # Enter 2 days before earnings
        'exit_days_after': 1,        # Exit 1 day after
        'max_iv_rank': 0.75,         # Don't buy if IV rank > 75%
        'min_expected_move': 0.05,   # Min 5% expected move
        'profit_target': 0.50,       # 50% profit target
        'max_loss': 0.75,            # 75% max loss
        'max_positions': 3,          # Max concurrent earnings plays
    }
    
    def on_start(self) -> None:
        """Initialize strategy state."""
        self.state = {
            'params': {**self.DEFAULT_PARAMS, **self.config.parameters},
            'positions': {},          # symbol -> position details
            'earnings_calendar': {},  # symbol -> earnings date
            'played_earnings': set(), # Symbols already played this quarter
        }
        
        # Load earnings calendar (mock for now)
        self._load_earnings_calendar()
        
        logger.info(
            "earnings_straddle_started",
            watchlist=self.state['params']['watchlist']
        )
    
    def _load_earnings_calendar(self) -> None:
        """Load upcoming earnings dates."""
        # In production, would fetch from financial API
        # Mock: assume earnings in next 2 weeks for some stocks
        base_date = date.today()
        
        self.state['earnings_calendar'] = {
            'AAPL': base_date + timedelta(days=5),
            'GOOGL': base_date + timedelta(days=7),
            'MSFT': base_date + timedelta(days=10),
            'AMZN': base_date + timedelta(days=3),
            'META': base_date + timedelta(days=8),
            'NVDA': base_date + timedelta(days=12),
            'TSLA': base_date + timedelta(days=6),
        }
    
    def on_market_data(self, event: MarketEvent) -> List[Signal]:
        """Process market data for earnings opportunities."""
        signals = []
        params = self.state['params']
        
        # Check exits on existing positions
        exit_signals = self._check_exits(event)
        signals.extend(exit_signals)
        
        # Look for new entries
        if len(self.state['positions']) < params['max_positions']:
            entry_signal = self._find_earnings_opportunity(event)
            if entry_signal:
                signals.append(entry_signal)
        
        return signals
    
    def _find_earnings_opportunity(self, event: MarketEvent) -> Optional[Signal]:
        """Find earnings straddle opportunity."""
        params = self.state['params']
        today = date.today()
        
        for symbol in params['watchlist']:
            # Skip if already played this quarter
            if symbol in self.state['played_earnings']:
                continue
            
            # Skip if already have position
            if symbol in self.state['positions']:
                continue
            
            # Check earnings date
            earnings_date = self.state['earnings_calendar'].get(symbol)
            if not earnings_date:
                continue
            
            # Check if within entry window
            days_to_earnings = (earnings_date - today).days
            if days_to_earnings != params['entry_days_before']:
                continue
            
            # Generate entry signal
            signal = self._generate_entry_signal(symbol, earnings_date)
            if signal:
                return signal
        
        return None
    
    def _generate_entry_signal(
        self, 
        symbol: str, 
        earnings_date: date
    ) -> Optional[Signal]:
        """Generate earnings straddle entry signal."""
        params = self.state['params']
        
        underlying_price = self.context.get_underlying_price(symbol)
        if underlying_price <= 0:
            return None
        
        # Find weekly expiration after earnings
        expiration = earnings_date + timedelta(days=7 - earnings_date.weekday())
        chain = self.context.get_option_chain(symbol, expiration)
        
        if not chain:
            return None
        
        # Find ATM options
        atm_call = self._find_atm_option(chain, 'C', underlying_price)
        atm_put = self._find_atm_option(chain, 'P', underlying_price)
        
        if not atm_call or not atm_put:
            return None
        
        # Get quotes
        call_quote = self.context.get_quote(atm_call.id)
        put_quote = self.context.get_quote(atm_put.id)
        
        if not call_quote or not put_quote:
            return None
        
        # Calculate straddle cost and expected move
        debit = call_quote.ask + put_quote.ask
        expected_move_pct = debit / underlying_price
        
        # Check if expected move is sufficient
        if expected_move_pct < params['min_expected_move']:
            logger.info(
                "earnings_expected_move_too_low",
                symbol=symbol,
                expected_move=expected_move_pct
            )
            return None
        
        # Estimate IV rank (simplified)
        iv_rank = 0.50  # Would calculate from historical IV
        if iv_rank > params['max_iv_rank']:
            logger.info(
                "earnings_iv_rank_too_high",
                symbol=symbol,
                iv_rank=iv_rank
            )
            return None
        
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
            entry_reason='earnings_straddle',
            expected_debit=debit,
            max_risk=debit * 100,
            metadata={
                'underlying': symbol,
                'strike': atm_call.strike,
                'expiration': str(expiration),
                'earnings_date': str(earnings_date),
                'expected_move_pct': expected_move_pct,
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
    
    def _check_exits(self, event: MarketEvent) -> List[Signal]:
        """Check for exit conditions."""
        signals = []
        params = self.state['params']
        today = date.today()
        
        for symbol, position in list(self.state['positions'].items()):
            should_exit = False
            reason = ""
            
            earnings_date = date.fromisoformat(position['earnings_date'])
            days_since_earnings = (today - earnings_date).days
            
            # Exit after earnings window
            if days_since_earnings >= params['exit_days_after']:
                should_exit = True
                reason = 'post_earnings'
            
            # Calculate P&L
            current_value = self._calculate_position_value(position)
            entry_debit = position['entry_debit']
            pnl = current_value - entry_debit
            pnl_pct = pnl / entry_debit if entry_debit > 0 else 0
            
            # Profit target
            if pnl_pct >= params['profit_target']:
                should_exit = True
                reason = 'profit_target'
            
            # Max loss
            elif pnl_pct <= -params['max_loss']:
                should_exit = True
                reason = 'stop_loss'
            
            if should_exit:
                signals.append(self._generate_exit_signal(symbol, position, reason))
                self.state['played_earnings'].add(symbol)
        
        return signals
    
    def _calculate_position_value(self, position: Dict) -> float:
        """Calculate current position value."""
        # Simplified - would get actual quotes
        return position['entry_debit'] * 0.8  # Placeholder with IV crush
    
    def _generate_exit_signal(
        self,
        symbol: str,
        position: Dict,
        reason: str
    ) -> Signal:
        """Generate exit signal."""
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
            entry_reason=f'earnings_exit_{reason}',
            metadata={
                'underlying': symbol,
                'reason': reason,
            }
        )
    
    def on_order_fill(self, fill: FillEvent) -> None:
        """Handle order fill."""
        logger.info(
            "earnings_straddle_filled",
            order_id=fill.order_id,
            fill_price=fill.fill_price
        )
    
    def on_position_update(self, position) -> None:
        """React to position changes."""
        pass
    
    def on_stop(self) -> Dict[str, Any]:
        """Return final statistics."""
        return {
            'positions_traded': len(self.state['played_earnings']),
            'active_positions': len(self.state['positions']),
            'played_symbols': list(self.state['played_earnings']),
        }
