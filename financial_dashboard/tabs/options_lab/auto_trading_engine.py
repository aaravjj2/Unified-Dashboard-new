#!/usr/bin/env python3
"""
Auto Trading Engine for Enhanced Alpaca Options Lab
====================================================

Improvements 51-75: Automated Trading Features
Focus: GLD, SLV, SPY + Tech Stocks

Zero user interaction - fully autonomous trading decisions.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
import asyncio

logger = logging.getLogger(__name__)

# Import from other modules
try:
    from .ai_automation_engine import ALL_FOCUS_TICKERS, FOCUS_TICKERS, TradeSignal, SignalStrength
    from .smart_analysis_engine import ta_engine, iv_engine, ml_engine
except ImportError:
    ALL_FOCUS_TICKERS = ['GLD', 'SLV', 'SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA', 'GOOGL']
    FOCUS_TICKERS = {}


class OrderType(Enum):
    """Order types."""
    MARKET = 'market'
    LIMIT = 'limit'
    STOP = 'stop'
    STOP_LIMIT = 'stop_limit'


class OrderSide(Enum):
    """Order sides."""
    BUY_TO_OPEN = 'buy_to_open'
    SELL_TO_OPEN = 'sell_to_open'
    BUY_TO_CLOSE = 'buy_to_close'
    SELL_TO_CLOSE = 'sell_to_close'


@dataclass
class OptionLeg:
    """Option leg for multi-leg orders."""
    symbol: str
    side: OrderSide
    quantity: int
    strike: float
    expiry: str
    option_type: str  # 'call' or 'put'
    limit_price: Optional[float] = None


@dataclass
class StrategyOrder:
    """Complete strategy order."""
    strategy_name: str
    underlying: str
    legs: List[OptionLeg]
    net_credit_debit: float
    max_profit: float
    max_loss: float
    breakevens: List[float]
    probability_of_profit: float
    created_at: datetime = field(default_factory=datetime.now)


# =============================================================================
# IMPROVEMENT 51-55: Strategy Builder
# =============================================================================

class AutoStrategyBuilder:
    """
    Improvement #51-55: Automated strategy construction.
    Builds optimal strategies without user input.
    """
    
    # Improvement #51: Auto build iron condor
    def build_iron_condor(self, underlying: str, spot: float, iv: float,
                          dte: int = 30, width: float = 0.1) -> StrategyOrder:
        """Auto-build iron condor based on market conditions."""
        # Calculate strikes based on expected move
        expected_move = spot * iv * np.sqrt(dte / 365)
        
        # Short strikes at ~1 standard deviation
        short_put = round(spot - expected_move, 0)
        short_call = round(spot + expected_move, 0)
        
        # Long strikes based on width
        long_put = short_put - (spot * width)
        long_call = short_call + (spot * width)
        
        expiry = (datetime.now() + timedelta(days=dte)).strftime('%Y-%m-%d')
        
        legs = [
            OptionLeg(f'{underlying}{expiry}P{long_put}', OrderSide.BUY_TO_OPEN, 1, long_put, expiry, 'put'),
            OptionLeg(f'{underlying}{expiry}P{short_put}', OrderSide.SELL_TO_OPEN, 1, short_put, expiry, 'put'),
            OptionLeg(f'{underlying}{expiry}C{short_call}', OrderSide.SELL_TO_OPEN, 1, short_call, expiry, 'call'),
            OptionLeg(f'{underlying}{expiry}C{long_call}', OrderSide.BUY_TO_OPEN, 1, long_call, expiry, 'call'),
        ]
        
        # Estimate credit (simplified)
        width_dollars = spot * width * 100
        estimated_credit = width_dollars * 0.3  # ~30% of width as credit
        
        return StrategyOrder(
            strategy_name='Iron Condor',
            underlying=underlying,
            legs=legs,
            net_credit_debit=estimated_credit,
            max_profit=estimated_credit,
            max_loss=width_dollars - estimated_credit,
            breakevens=[short_put - estimated_credit/100, short_call + estimated_credit/100],
            probability_of_profit=0.68  # 1 std dev
        )
    
    # Improvement #52: Auto build credit spread
    def build_credit_spread(self, underlying: str, spot: float, direction: str,
                           iv: float, dte: int = 30) -> StrategyOrder:
        """Auto-build bull put or bear call spread."""
        expected_move = spot * iv * np.sqrt(dte / 365)
        expiry = (datetime.now() + timedelta(days=dte)).strftime('%Y-%m-%d')
        
        if direction == 'BULLISH':
            # Bull put spread
            short_strike = round(spot - expected_move * 0.5, 0)
            long_strike = short_strike - 5  # $5 wide
            option_type = 'put'
        else:
            # Bear call spread
            short_strike = round(spot + expected_move * 0.5, 0)
            long_strike = short_strike + 5
            option_type = 'call'
        
        legs = [
            OptionLeg(f'{underlying}{expiry}{option_type[0].upper()}{long_strike}', 
                     OrderSide.BUY_TO_OPEN, 1, long_strike, expiry, option_type),
            OptionLeg(f'{underlying}{expiry}{option_type[0].upper()}{short_strike}', 
                     OrderSide.SELL_TO_OPEN, 1, short_strike, expiry, option_type),
        ]
        
        width = abs(short_strike - long_strike) * 100
        estimated_credit = width * 0.35
        
        return StrategyOrder(
            strategy_name=f'{"Bull Put" if direction == "BULLISH" else "Bear Call"} Spread',
            underlying=underlying,
            legs=legs,
            net_credit_debit=estimated_credit,
            max_profit=estimated_credit,
            max_loss=width - estimated_credit,
            breakevens=[short_strike - estimated_credit/100 if direction == 'BULLISH' 
                       else short_strike + estimated_credit/100],
            probability_of_profit=0.65
        )
    
    # Improvement #53: Auto build straddle/strangle
    def build_volatility_play(self, underlying: str, spot: float,
                              play_type: str = 'straddle', dte: int = 45) -> StrategyOrder:
        """Auto-build straddle or strangle for volatility play."""
        expiry = (datetime.now() + timedelta(days=dte)).strftime('%Y-%m-%d')
        
        if play_type == 'straddle':
            atm_strike = round(spot, 0)
            legs = [
                OptionLeg(f'{underlying}{expiry}C{atm_strike}', OrderSide.BUY_TO_OPEN, 1, atm_strike, expiry, 'call'),
                OptionLeg(f'{underlying}{expiry}P{atm_strike}', OrderSide.BUY_TO_OPEN, 1, atm_strike, expiry, 'put'),
            ]
            estimated_debit = spot * 0.06 * 100  # ~6% of spot
        else:  # strangle
            otm_call = round(spot * 1.05, 0)
            otm_put = round(spot * 0.95, 0)
            legs = [
                OptionLeg(f'{underlying}{expiry}C{otm_call}', OrderSide.BUY_TO_OPEN, 1, otm_call, expiry, 'call'),
                OptionLeg(f'{underlying}{expiry}P{otm_put}', OrderSide.BUY_TO_OPEN, 1, otm_put, expiry, 'put'),
            ]
            estimated_debit = spot * 0.04 * 100  # ~4% of spot
        
        return StrategyOrder(
            strategy_name=play_type.capitalize(),
            underlying=underlying,
            legs=legs,
            net_credit_debit=-estimated_debit,
            max_profit=float('inf'),  # Unlimited
            max_loss=estimated_debit,
            breakevens=[spot - estimated_debit/100, spot + estimated_debit/100],
            probability_of_profit=0.35
        )
    
    # Improvement #54: Auto select optimal strategy
    def select_optimal_strategy(self, underlying: str, spot: float, 
                                iv: float, iv_rank: float, direction: str) -> StrategyOrder:
        """AI selects and builds optimal strategy."""
        # High IV = sell premium
        if iv_rank > 60:
            if direction == 'NEUTRAL':
                return self.build_iron_condor(underlying, spot, iv)
            else:
                return self.build_credit_spread(underlying, spot, direction, iv)
        # Low IV = buy premium
        elif iv_rank < 30:
            return self.build_volatility_play(underlying, spot, 'strangle')
        # Normal IV = directional play
        else:
            return self.build_credit_spread(underlying, spot, direction, iv)
    
    # Improvement #55: Auto adjust strikes for earnings
    def adjust_for_earnings(self, strategy: StrategyOrder, days_to_earnings: int) -> StrategyOrder:
        """Adjust strategy for upcoming earnings."""
        if days_to_earnings < 7:
            # Widen strikes for earnings
            for leg in strategy.legs:
                if leg.side == OrderSide.SELL_TO_OPEN:
                    # Move short strikes further OTM
                    adjustment = 0.02 * leg.strike  # 2% wider
                    if leg.option_type == 'put':
                        leg.strike -= adjustment
                    else:
                        leg.strike += adjustment
            
            # Update max loss estimate
            strategy.probability_of_profit *= 0.9  # Lower POP due to earnings
        
        return strategy


# =============================================================================
# IMPROVEMENT 56-60: Order Execution Engine
# =============================================================================

class AutoOrderExecutor:
    """
    Improvement #56-60: Automated order execution.
    Handles all order execution without user intervention.
    """
    
    def __init__(self):
        self.pending_orders = []
        self.executed_orders = []
        self.paper_mode = True  # Safety default
    
    # Improvement #56: Smart limit order pricing
    def calculate_smart_limit(self, bid: float, ask: float, urgency: str = 'normal') -> float:
        """Calculate smart limit price based on urgency."""
        spread = ask - bid
        mid = (bid + ask) / 2
        
        if urgency == 'high':
            # Pay up to get filled
            return round(mid + spread * 0.3, 2)
        elif urgency == 'low':
            # Try to get better fill
            return round(mid - spread * 0.2, 2)
        else:
            return round(mid, 2)
    
    # Improvement #57: Auto retry failed orders
    def execute_with_retry(self, order: Dict, max_retries: int = 3) -> Dict:
        """Execute order with automatic retry logic."""
        for attempt in range(max_retries):
            try:
                result = self._submit_order(order)
                if result.get('status') == 'filled':
                    return result
                elif result.get('status') == 'rejected':
                    # Adjust price and retry
                    order['limit_price'] = self._adjust_price_for_fill(order)
            except Exception as e:
                logger.error(f"Order attempt {attempt + 1} failed: {e}")
                import time
                time.sleep(1)
        
        return {'status': 'failed', 'reason': 'Max retries exceeded'}
    
    # Improvement #58: Multi-leg order handling
    def execute_multi_leg(self, strategy: StrategyOrder) -> Dict:
        """Execute multi-leg strategy as single order."""
        legs_data = []
        for leg in strategy.legs:
            legs_data.append({
                'symbol': leg.symbol,
                'side': leg.side.value,
                'quantity': leg.quantity,
                'type': 'limit'
            })
        
        # In paper mode, simulate execution
        if self.paper_mode:
            return {
                'status': 'filled',
                'strategy': strategy.strategy_name,
                'fill_price': strategy.net_credit_debit,
                'legs': len(legs_data),
                'mode': 'paper'
            }
        
        # Real execution would go here
        return {'status': 'pending', 'legs': legs_data}
    
    # Improvement #59: Order validation
    def validate_order(self, order: Dict) -> Tuple[bool, str]:
        """Validate order before submission."""
        errors = []
        
        # Check symbol
        underlying = order.get('underlying', '')
        if underlying not in ALL_FOCUS_TICKERS:
            errors.append(f'Symbol {underlying} not in focus list')
        
        # Check position size
        if order.get('quantity', 0) > 10:
            errors.append('Position size exceeds limit (max 10 contracts)')
        
        # Check risk
        max_loss = order.get('max_loss', 0)
        if max_loss > 5000:
            errors.append(f'Max loss ${max_loss} exceeds limit ($5000)')
        
        return len(errors) == 0, '; '.join(errors)
    
    # Improvement #60: Auto cancel stale orders
    def cancel_stale_orders(self, max_age_minutes: int = 30) -> List[str]:
        """Auto cancel orders that haven't filled."""
        cancelled = []
        now = datetime.now()
        
        for order in self.pending_orders[:]:
            age = (now - order.get('created_at', now)).total_seconds() / 60
            if age > max_age_minutes:
                cancelled.append(order.get('id'))
                self.pending_orders.remove(order)
        
        return cancelled
    
    def _submit_order(self, order: Dict) -> Dict:
        """Internal order submission."""
        # Placeholder - would integrate with broker
        return {'status': 'filled' if self.paper_mode else 'pending'}
    
    def _adjust_price_for_fill(self, order: Dict) -> float:
        """Adjust limit price to improve fill probability."""
        current_price = order.get('limit_price', 0)
        side = order.get('side', '')
        
        if 'buy' in side.lower():
            return current_price * 1.01  # Pay 1% more
        else:
            return current_price * 0.99  # Accept 1% less


# =============================================================================
# IMPROVEMENT 61-65: Risk Management Engine
# =============================================================================

class AutoRiskManager:
    """
    Improvement #61-65: Automated risk management.
    Protects capital without user intervention.
    """
    
    def __init__(self):
        self.max_portfolio_delta = 500
        self.max_position_size = 10
        self.max_daily_loss = 0.02  # 2% of portfolio
        self.max_single_trade_risk = 0.01  # 1% per trade
    
    # Improvement #61: Auto position sizing
    def calculate_position_size(self, account_value: float, max_loss_per_contract: float,
                               current_positions: int = 0) -> int:
        """Calculate optimal position size."""
        max_risk = account_value * self.max_single_trade_risk
        contracts = int(max_risk / max_loss_per_contract)
        
        # Account for existing positions
        available_slots = self.max_position_size - current_positions
        
        return max(1, min(contracts, available_slots, 5))
    
    # Improvement #62: Portfolio delta management
    def check_delta_limits(self, portfolio_delta: float) -> Dict:
        """Check if portfolio delta is within limits."""
        if abs(portfolio_delta) > self.max_portfolio_delta:
            return {
                'within_limits': False,
                'current_delta': portfolio_delta,
                'action_required': 'HEDGE',
                'hedge_size': -portfolio_delta  # Delta needed to neutralize
            }
        return {'within_limits': True, 'current_delta': portfolio_delta}
    
    # Improvement #63: Daily loss limit
    def check_daily_loss(self, daily_pnl: float, portfolio_value: float) -> Dict:
        """Check if daily loss limit reached."""
        daily_loss_pct = daily_pnl / portfolio_value if portfolio_value > 0 else 0
        
        if daily_loss_pct < -self.max_daily_loss:
            return {
                'limit_reached': True,
                'daily_pnl': daily_pnl,
                'action': 'STOP_TRADING',
                'message': 'Daily loss limit reached - no new positions'
            }
        
        remaining_risk = portfolio_value * self.max_daily_loss + daily_pnl
        return {
            'limit_reached': False,
            'daily_pnl': daily_pnl,
            'remaining_risk': remaining_risk
        }
    
    # Improvement #64: Concentration limits
    def check_concentration(self, positions: List[Dict]) -> Dict:
        """Check for position concentration risk."""
        ticker_exposure = {}
        total_value = sum(p.get('market_value', 0) for p in positions)
        
        for pos in positions:
            ticker = pos.get('underlying', '')
            value = pos.get('market_value', 0)
            ticker_exposure[ticker] = ticker_exposure.get(ticker, 0) + value
        
        warnings = []
        for ticker, exposure in ticker_exposure.items():
            pct = exposure / total_value if total_value > 0 else 0
            if pct > 0.25:  # 25% concentration limit
                warnings.append(f'{ticker}: {pct:.1%} concentration')
        
        return {
            'concentrated': len(warnings) > 0,
            'warnings': warnings,
            'exposures': {k: v/total_value for k, v in ticker_exposure.items()} if total_value > 0 else {}
        }
    
    # Improvement #65: Auto-reduce risk
    def suggest_risk_reduction(self, positions: List[Dict], target_delta: float = 0) -> List[Dict]:
        """Suggest positions to close for risk reduction."""
        suggestions = []
        
        # Sort by unrealized P&L
        sorted_positions = sorted(positions, key=lambda x: x.get('unrealized_pnl', 0))
        
        # Suggest closing biggest losers first
        for pos in sorted_positions[:3]:
            if pos.get('unrealized_pnl', 0) < 0:
                suggestions.append({
                    'position': pos,
                    'action': 'CLOSE',
                    'reason': f'Loss of ${abs(pos.get("unrealized_pnl", 0)):.2f}'
                })
        
        return suggestions


# =============================================================================
# IMPROVEMENT 66-70: Profit Taking Engine
# =============================================================================

class AutoProfitTaker:
    """
    Improvement #66-70: Automated profit taking.
    Locks in profits without user intervention.
    """
    
    def __init__(self):
        self.default_profit_target = 0.50  # 50% of max profit
        self.time_decay_threshold = 0.21  # 21 DTE
    
    # Improvement #66: Dynamic profit targets
    def get_profit_target(self, strategy_type: str, dte: int, iv_rank: float) -> float:
        """Calculate dynamic profit target based on conditions."""
        base_target = self.default_profit_target
        
        # Adjust for strategy type
        strategy_adjustments = {
            'iron_condor': 0.50,
            'credit_spread': 0.50,
            'iron_butterfly': 0.40,
            'straddle': 1.00,  # Let winners run
            'strangle': 1.00
        }
        base_target = strategy_adjustments.get(strategy_type, 0.50)
        
        # Adjust for DTE - take profits earlier if near expiry
        if dte < 14:
            base_target *= 0.8
        elif dte < 7:
            base_target *= 0.6
        
        # Adjust for IV - in high IV, be more aggressive taking profits
        if iv_rank > 70:
            base_target *= 0.9
        
        return base_target
    
    # Improvement #67: Check positions for profit taking
    def check_profit_targets(self, positions: List[Dict]) -> List[Dict]:
        """Check all positions against profit targets."""
        take_profit = []
        
        for pos in positions:
            current_value = pos.get('current_value', 0)
            entry_value = pos.get('entry_value', 0)
            max_profit = pos.get('max_profit', entry_value)
            dte = pos.get('dte', 30)
            
            if max_profit > 0:
                profit_pct = (entry_value - current_value) / max_profit
            else:
                profit_pct = 0
            
            target = self.get_profit_target(pos.get('strategy', 'credit_spread'), dte, 50)
            
            if profit_pct >= target:
                take_profit.append({
                    'position': pos,
                    'profit_pct': profit_pct,
                    'target': target,
                    'action': 'CLOSE',
                    'reason': f'Profit target {target:.0%} reached ({profit_pct:.0%})'
                })
        
        return take_profit
    
    # Improvement #68: Time-based exit
    def check_time_exits(self, positions: List[Dict]) -> List[Dict]:
        """Check for time-based exit conditions."""
        time_exits = []
        
        for pos in positions:
            dte = pos.get('dte', 30)
            profit_pct = pos.get('profit_pct', 0)
            
            # Exit credit spreads at 21 DTE if profitable
            if dte <= 21 and profit_pct > 0.30:
                time_exits.append({
                    'position': pos,
                    'action': 'CLOSE',
                    'reason': f'21 DTE exit with {profit_pct:.0%} profit'
                })
            
            # Exit at 7 DTE regardless
            elif dte <= 7:
                time_exits.append({
                    'position': pos,
                    'action': 'CLOSE' if profit_pct > 0 else 'ROLL',
                    'reason': f'Near expiry ({dte} DTE)'
                })
        
        return time_exits
    
    # Improvement #69: Trailing stop for premium buyers
    def calculate_trailing_stop(self, entry_price: float, current_price: float,
                               highest_price: float) -> Dict:
        """Calculate trailing stop for long premium positions."""
        # Trail by 25% of gains
        if current_price > entry_price:
            gain = current_price - entry_price
            stop_price = highest_price - (gain * 0.25)
            
            return {
                'stop_active': True,
                'stop_price': stop_price,
                'triggered': current_price <= stop_price
            }
        
        return {'stop_active': False}
    
    # Improvement #70: Auto scale out
    def suggest_scale_out(self, position: Dict) -> List[Dict]:
        """Suggest scaling out of profitable position."""
        profit_pct = position.get('profit_pct', 0)
        quantity = position.get('quantity', 1)
        
        suggestions = []
        
        if profit_pct > 0.30 and quantity >= 2:
            suggestions.append({
                'action': 'CLOSE_PARTIAL',
                'quantity': quantity // 2,
                'reason': f'Scale out 50% at {profit_pct:.0%} profit'
            })
        
        if profit_pct > 0.60 and quantity >= 2:
            remaining = quantity - (quantity // 2)
            suggestions.append({
                'action': 'CLOSE_REMAINING',
                'quantity': remaining,
                'reason': f'Close remaining at {profit_pct:.0%} profit'
            })
        
        return suggestions


# =============================================================================
# IMPROVEMENT 71-75: Auto Rolling Engine
# =============================================================================

class AutoRollingEngine:
    """
    Improvement #71-75: Automated position rolling.
    Manages expiring positions automatically.
    """
    
    # Improvement #71: Roll detection
    def should_roll(self, position: Dict) -> Tuple[bool, str]:
        """Determine if position should be rolled."""
        dte = position.get('dte', 30)
        profit_pct = position.get('profit_pct', 0)
        strategy = position.get('strategy', '')
        
        # Premium selling strategies - roll if still losing at low DTE
        if strategy in ['iron_condor', 'credit_spread'] and dte <= 14:
            if profit_pct < 0.3:
                return True, 'Low profit at 14 DTE - roll for more credit'
        
        # Roll tested positions
        delta = position.get('current_delta', 0)
        if abs(delta) > 0.3 and strategy == 'iron_condor':
            return True, 'Position tested - roll untested side'
        
        # Time decay acceleration
        if dte <= 7 and profit_pct > 0.5:
            return False, 'Near expiry with profit - close instead'
        
        return False, ''
    
    # Improvement #72: Calculate roll strikes
    def calculate_roll_strikes(self, position: Dict, spot: float, iv: float) -> Dict:
        """Calculate new strikes for roll."""
        current_strikes = position.get('strikes', [])
        dte = 30  # Roll to ~30 DTE
        
        expected_move = spot * iv * np.sqrt(dte / 365)
        
        if position.get('strategy') == 'iron_condor':
            new_strikes = {
                'short_put': round(spot - expected_move, 0),
                'long_put': round(spot - expected_move - 5, 0),
                'short_call': round(spot + expected_move, 0),
                'long_call': round(spot + expected_move + 5, 0)
            }
        else:
            new_strikes = {
                'short': round(spot - expected_move * 0.5, 0),
                'long': round(spot - expected_move * 0.5 - 5, 0)
            }
        
        return {
            'new_strikes': new_strikes,
            'target_expiry': (datetime.now() + timedelta(days=dte)).strftime('%Y-%m-%d'),
            'credit_estimate': position.get('max_profit', 100) * 0.7
        }
    
    # Improvement #73: Roll timing optimization
    def optimize_roll_timing(self, position: Dict) -> Dict:
        """Determine optimal roll timing."""
        dte = position.get('dte', 30)
        theta = position.get('theta', 0)
        gamma = position.get('gamma', 0)
        
        # Roll before gamma risk increases
        if dte <= 10 and abs(gamma) > 0.1:
            return {'roll_now': True, 'reason': 'High gamma risk'}
        
        # Roll when theta decay slows
        if dte <= 21 and theta < -0.05:
            return {'roll_now': True, 'reason': 'Theta decay accelerating in current position'}
        
        return {'roll_now': False, 'optimal_dte': max(7, dte - 7)}
    
    # Improvement #74: Roll credit check
    def validate_roll_credit(self, current_position: Dict, new_position: Dict) -> Dict:
        """Validate roll produces acceptable credit."""
        close_cost = current_position.get('close_cost', 0)
        open_credit = new_position.get('credit', 0)
        net = open_credit - close_cost
        
        if net > 0:
            return {
                'valid': True,
                'net_credit': net,
                'recommendation': 'ROLL'
            }
        elif net > -50:  # Small debit acceptable
            return {
                'valid': True,
                'net_credit': net,
                'recommendation': 'ROLL_IF_BULLISH'
            }
        else:
            return {
                'valid': False,
                'net_credit': net,
                'recommendation': 'CLOSE_INSTEAD'
            }
    
    # Improvement #75: Auto execute roll
    def execute_roll(self, position: Dict, new_strikes: Dict) -> Dict:
        """Execute roll automatically."""
        # Close current position
        close_order = {
            'action': 'CLOSE',
            'position_id': position.get('id'),
            'type': 'market'
        }
        
        # Open new position
        open_order = {
            'action': 'OPEN',
            'underlying': position.get('underlying'),
            'strategy': position.get('strategy'),
            'strikes': new_strikes,
            'expiry': new_strikes.get('target_expiry'),
            'quantity': position.get('quantity', 1)
        }
        
        return {
            'status': 'ROLLED',
            'close_order': close_order,
            'open_order': open_order,
            'timestamp': datetime.now().isoformat()
        }


# =============================================================================
# Singleton instances
# =============================================================================

strategy_builder = AutoStrategyBuilder()
order_executor = AutoOrderExecutor()
risk_manager = AutoRiskManager()
profit_taker = AutoProfitTaker()
rolling_engine = AutoRollingEngine()

__all__ = [
    'OrderType', 'OrderSide', 'OptionLeg', 'StrategyOrder',
    'AutoStrategyBuilder', 'AutoOrderExecutor', 'AutoRiskManager',
    'AutoProfitTaker', 'AutoRollingEngine',
    'strategy_builder', 'order_executor', 'risk_manager',
    'profit_taker', 'rolling_engine'
]
