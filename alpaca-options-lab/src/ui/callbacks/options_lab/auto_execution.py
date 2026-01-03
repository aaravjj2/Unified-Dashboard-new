"""
Auto-Execution Features Module
==============================
Advanced automation for trade execution:
- One-click trade setup (enhanced)
- Auto-adjustment triggers
- Smart order routing
- Position migration
- Auto-journaling

Author: AI/ML Options Lab
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


# ============================================================
# ENUMS & DATA CLASSES
# ============================================================

class OrderType(Enum):
    """Order types."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class AdjustmentType(Enum):
    """Types of position adjustments."""
    ROLL_OUT = "roll_out"           # Roll to further expiration
    ROLL_UP = "roll_up"             # Roll to higher strike
    ROLL_DOWN = "roll_down"         # Roll to lower strike
    ADD_WING = "add_wing"           # Add protective wing
    CLOSE_PARTIAL = "close_partial" # Close part of position
    CLOSE_FULL = "close_full"       # Close entire position
    ADD_HEDGE = "add_hedge"         # Add hedging position


class MigrationReason(Enum):
    """Reasons for position migration."""
    PROFIT_TARGET = "profit_target"
    STOP_LOSS = "stop_loss"
    EXPIRATION = "expiration"
    REGIME_CHANGE = "regime_change"
    REBALANCE = "rebalance"


@dataclass
class TradeOrder:
    """Complete trade order ready for execution."""
    order_id: str
    ticker: str
    strategy: str
    
    # Legs
    legs: List[Dict]
    
    # Order details
    order_type: OrderType
    limit_price: Optional[float]
    
    # Risk parameters
    max_slippage: float
    time_in_force: str  # 'day', 'gtc', 'ioc'
    
    # Metadata
    rationale: str
    created_at: datetime
    expires_at: datetime
    
    # Execution status
    status: str = "pending"  # 'pending', 'submitted', 'filled', 'cancelled'


@dataclass
class AdjustmentTrigger:
    """Auto-adjustment trigger configuration."""
    trigger_id: str
    position_id: str
    ticker: str
    
    # Trigger conditions
    trigger_type: str  # 'price', 'delta', 'pnl', 'time', 'iv'
    condition: str     # 'above', 'below', 'equals'
    threshold: float
    
    # Adjustment to make
    adjustment_type: AdjustmentType
    adjustment_params: Dict
    
    # Status
    is_active: bool
    triggered_at: Optional[datetime]
    
    created_at: datetime


@dataclass
class PositionMigration:
    """Position migration plan."""
    migration_id: str
    ticker: str
    reason: MigrationReason
    
    # Current position
    current_strategy: str
    current_legs: List[Dict]
    
    # Target position  
    target_strategy: str
    target_legs: List[Dict]
    
    # Execution plan
    close_orders: List[TradeOrder]
    open_orders: List[TradeOrder]
    
    # Cost/benefit
    estimated_debit_credit: float
    risk_change: float
    
    # Timing
    execution_window: str  # 'immediate', 'market_open', 'optimal'
    created_at: datetime


@dataclass
class JournalEntry:
    """Auto-generated trade journal entry."""
    entry_id: str
    trade_date: str
    ticker: str
    strategy: str
    
    # Trade details
    entry_price: float
    exit_price: Optional[float]
    pnl: Optional[float]
    pnl_pct: Optional[float]
    
    # Context at entry
    iv_rank_entry: float
    market_regime: str
    sentiment: str
    
    # AI analysis
    entry_rationale: str
    exit_rationale: Optional[str]
    lessons_learned: Optional[str]
    
    # Tags
    tags: List[str]
    
    created_at: datetime
    updated_at: datetime


# ============================================================
# ENHANCED ONE-CLICK TRADER
# ============================================================

class EnhancedOneClickTrader:
    """
    Enhanced one-click trade setup with:
    - Multiple strategy templates
    - Risk-adjusted sizing
    - Smart strike selection
    - Optimal timing suggestions
    """
    
    def __init__(self):
        self._order_counter = 0
        
        # Strategy templates
        self.templates = {
            'iron_condor': {
                'legs': 4,
                'default_width': 5,
                'default_dte': 45,
                'delta_target': 0.16
            },
            'bull_put_spread': {
                'legs': 2,
                'default_width': 5,
                'default_dte': 30,
                'delta_target': 0.30
            },
            'bear_call_spread': {
                'legs': 2,
                'default_width': 5,
                'default_dte': 30,
                'delta_target': -0.30
            },
            'straddle': {
                'legs': 2,
                'default_width': 0,
                'default_dte': 21,
                'delta_target': 0
            },
            'strangle': {
                'legs': 2,
                'default_width': 10,
                'default_dte': 21,
                'delta_target': 0
            },
            'covered_call': {
                'legs': 2,  # Stock + call
                'default_width': 0,
                'default_dte': 30,
                'delta_target': -0.30
            },
            'cash_secured_put': {
                'legs': 1,
                'default_width': 0,
                'default_dte': 30,
                'delta_target': -0.30
            },
            'butterfly': {
                'legs': 4,
                'default_width': 5,
                'default_dte': 21,
                'delta_target': 0
            }
        }
    
    def generate_order(self, ticker: str, strategy: str = 'auto',
                       account_size: float = 10000,
                       risk_pct: float = 2.0) -> TradeOrder:
        """Generate complete trade order."""
        self._order_counter += 1
        
        # Auto-select strategy if needed
        if strategy == 'auto':
            strategy = self._select_strategy(ticker)
        
        template = self.templates.get(strategy, self.templates['iron_condor'])
        
        # Get market data
        spot_price = self._get_spot_price(ticker)
        iv_data = self._get_iv_data(ticker)
        
        # Generate legs
        legs = self._generate_legs(ticker, strategy, template, spot_price, iv_data)
        
        # Calculate sizing
        contracts = self._calculate_position_size(
            account_size, risk_pct, legs, spot_price
        )
        
        # Update legs with quantity
        for leg in legs:
            leg['quantity'] = contracts
        
        # Calculate order price
        order_price = self._calculate_order_price(legs)
        
        # Generate rationale
        rationale = self._generate_rationale(ticker, strategy, iv_data)
        
        return TradeOrder(
            order_id=f"order_{self._order_counter}_{int(datetime.now().timestamp())}",
            ticker=ticker,
            strategy=strategy,
            legs=legs,
            order_type=OrderType.LIMIT,
            limit_price=order_price,
            max_slippage=0.05,
            time_in_force='day',
            rationale=rationale,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=8)
        )
    
    def _select_strategy(self, ticker: str) -> str:
        """AI-select optimal strategy for ticker."""
        try:
            from .ai_ml_engine import get_ai_selector
            selector = get_ai_selector()
            rec = selector.get_best_strategy(ticker)
            if rec:
                # Map recommendation to template name
                name_map = {
                    'Iron Condor': 'iron_condor',
                    'Bull Put Spread': 'bull_put_spread',
                    'Bear Call Spread': 'bear_call_spread',
                    'Long Straddle': 'straddle',
                    'Long Strangle': 'strangle'
                }
                return name_map.get(rec.strategy_name, 'iron_condor')
        except:
            pass
        return 'iron_condor'
    
    def _get_spot_price(self, ticker: str) -> float:
        """Get current spot price."""
        try:
            from .alpaca_data_loader import get_alpaca_client
            client = get_alpaca_client()
            return client.get_stock_quote(ticker) or 100
        except:
            return 100
    
    def _get_iv_data(self, ticker: str) -> Dict:
        """Get IV data for ticker."""
        try:
            from .ml_price_predictor import IVForecaster
            forecaster = IVForecaster()
            forecast = forecaster.forecast(ticker)
            return {
                'current_iv': forecast.current_iv,
                'iv_rank': forecast.iv_rank,
                'iv_percentile': forecast.iv_percentile,
                'regime': forecast.forecast_regime
            }
        except:
            return {'current_iv': 25, 'iv_rank': 50, 'iv_percentile': 50, 'regime': 'stable'}
    
    def _generate_legs(self, ticker: str, strategy: str, template: Dict,
                       spot: float, iv_data: Dict) -> List[Dict]:
        """Generate option legs for strategy."""
        dte = template['default_dte']
        width = template['default_width']
        
        # Calculate expected move
        iv = iv_data.get('current_iv', 25) / 100
        expected_move = spot * iv * (dte / 365) ** 0.5
        
        # Round to standard strikes
        strike_increment = 5 if spot > 100 else 1
        atm = round(spot / strike_increment) * strike_increment
        
        # Expiration
        expiry = (datetime.now() + timedelta(days=dte)).strftime('%Y-%m-%d')
        
        legs = []
        
        if strategy == 'iron_condor':
            put_short = atm - round(expected_move / strike_increment) * strike_increment
            put_long = put_short - width
            call_short = atm + round(expected_move / strike_increment) * strike_increment
            call_long = call_short + width
            
            legs = [
                {'action': 'BUY', 'type': 'PUT', 'strike': put_long, 'expiry': expiry, 'premium': 0.50},
                {'action': 'SELL', 'type': 'PUT', 'strike': put_short, 'expiry': expiry, 'premium': 1.20},
                {'action': 'SELL', 'type': 'CALL', 'strike': call_short, 'expiry': expiry, 'premium': 1.20},
                {'action': 'BUY', 'type': 'CALL', 'strike': call_long, 'expiry': expiry, 'premium': 0.50}
            ]
        
        elif strategy == 'bull_put_spread':
            short_strike = atm - round(expected_move * 0.5 / strike_increment) * strike_increment
            long_strike = short_strike - width
            
            legs = [
                {'action': 'BUY', 'type': 'PUT', 'strike': long_strike, 'expiry': expiry, 'premium': 0.80},
                {'action': 'SELL', 'type': 'PUT', 'strike': short_strike, 'expiry': expiry, 'premium': 1.50}
            ]
        
        elif strategy == 'bear_call_spread':
            short_strike = atm + round(expected_move * 0.5 / strike_increment) * strike_increment
            long_strike = short_strike + width
            
            legs = [
                {'action': 'SELL', 'type': 'CALL', 'strike': short_strike, 'expiry': expiry, 'premium': 1.50},
                {'action': 'BUY', 'type': 'CALL', 'strike': long_strike, 'expiry': expiry, 'premium': 0.80}
            ]
        
        elif strategy == 'straddle':
            legs = [
                {'action': 'BUY', 'type': 'CALL', 'strike': atm, 'expiry': expiry, 'premium': 3.00},
                {'action': 'BUY', 'type': 'PUT', 'strike': atm, 'expiry': expiry, 'premium': 3.00}
            ]
        
        elif strategy == 'strangle':
            call_strike = atm + width
            put_strike = atm - width
            
            legs = [
                {'action': 'BUY', 'type': 'CALL', 'strike': call_strike, 'expiry': expiry, 'premium': 2.00},
                {'action': 'BUY', 'type': 'PUT', 'strike': put_strike, 'expiry': expiry, 'premium': 2.00}
            ]
        
        elif strategy == 'cash_secured_put':
            put_strike = atm - round(expected_move * 0.5 / strike_increment) * strike_increment
            
            legs = [
                {'action': 'SELL', 'type': 'PUT', 'strike': put_strike, 'expiry': expiry, 'premium': 2.00}
            ]
        
        else:  # Default to bull put spread
            short_strike = atm - width
            long_strike = short_strike - width
            
            legs = [
                {'action': 'BUY', 'type': 'PUT', 'strike': long_strike, 'expiry': expiry, 'premium': 0.80},
                {'action': 'SELL', 'type': 'PUT', 'strike': short_strike, 'expiry': expiry, 'premium': 1.50}
            ]
        
        return legs
    
    def _calculate_position_size(self, account: float, risk_pct: float,
                                  legs: List[Dict], spot: float) -> int:
        """Calculate appropriate position size."""
        max_risk = account * (risk_pct / 100)
        
        # Calculate max loss per contract
        sell_legs = [l for l in legs if l['action'] == 'SELL']
        buy_legs = [l for l in legs if l['action'] == 'BUY']
        
        if sell_legs and buy_legs:
            # Spread - max loss is width minus credit
            width = abs(sell_legs[0]['strike'] - buy_legs[0]['strike'])
            credit = sum(l['premium'] for l in sell_legs) - sum(l['premium'] for l in buy_legs)
            max_loss_per_contract = (width - credit) * 100
        elif sell_legs:
            # Naked short - max loss is large (use strike)
            max_loss_per_contract = sell_legs[0]['strike'] * 100 * 0.5  # Assume 50% move
        else:
            # Long options - max loss is premium
            max_loss_per_contract = sum(l['premium'] for l in buy_legs) * 100
        
        if max_loss_per_contract <= 0:
            max_loss_per_contract = 500  # Default
        
        contracts = int(max_risk / max_loss_per_contract)
        
        return max(1, min(10, contracts))  # Between 1 and 10 contracts
    
    def _calculate_order_price(self, legs: List[Dict]) -> float:
        """Calculate limit order price."""
        # Net credit/debit
        total = 0
        for leg in legs:
            if leg['action'] == 'SELL':
                total += leg['premium']
            else:
                total -= leg['premium']
        
        return round(total, 2)
    
    def _generate_rationale(self, ticker: str, strategy: str, 
                            iv_data: Dict) -> str:
        """Generate trade rationale."""
        parts = [f"One-click {strategy.replace('_', ' ').title()} on {ticker}:"]
        
        iv_rank = iv_data.get('iv_rank', 50)
        if iv_rank > 60:
            parts.append(f"• IV Rank at {iv_rank:.0f}% - favorable for premium selling")
        elif iv_rank < 40:
            parts.append(f"• IV Rank at {iv_rank:.0f}% - options are relatively cheap")
        else:
            parts.append(f"• IV Rank at {iv_rank:.0f}% - neutral environment")
        
        regime = iv_data.get('regime', 'stable')
        parts.append(f"• Volatility regime: {regime}")
        
        return "\n".join(parts)


# ============================================================
# AUTO-ADJUSTMENT ENGINE
# ============================================================

class AutoAdjustmentEngine:
    """
    Automatically adjusts positions based on triggers.
    No user intervention needed.
    """
    
    def __init__(self):
        self._triggers: Dict[str, AdjustmentTrigger] = {}
        self._trigger_counter = 0
    
    def create_trigger(self, position_id: str, ticker: str,
                       trigger_type: str, condition: str,
                       threshold: float,
                       adjustment_type: AdjustmentType,
                       adjustment_params: Dict = None) -> AdjustmentTrigger:
        """Create an auto-adjustment trigger."""
        self._trigger_counter += 1
        
        trigger = AdjustmentTrigger(
            trigger_id=f"trigger_{self._trigger_counter}",
            position_id=position_id,
            ticker=ticker,
            trigger_type=trigger_type,
            condition=condition,
            threshold=threshold,
            adjustment_type=adjustment_type,
            adjustment_params=adjustment_params or {},
            is_active=True,
            triggered_at=None,
            created_at=datetime.now()
        )
        
        self._triggers[trigger.trigger_id] = trigger
        return trigger
    
    def check_triggers(self, positions: List[Dict], 
                       market_data: Dict) -> List[Tuple[AdjustmentTrigger, Dict]]:
        """Check all triggers and return those that fired."""
        fired = []
        
        for trigger_id, trigger in self._triggers.items():
            if not trigger.is_active:
                continue
            
            # Find matching position
            position = next(
                (p for p in positions if p.get('id') == trigger.position_id),
                None
            )
            
            if not position:
                continue
            
            # Check condition
            current_value = self._get_trigger_value(trigger, position, market_data)
            
            if self._evaluate_condition(current_value, trigger.condition, trigger.threshold):
                # Trigger fired!
                trigger.triggered_at = datetime.now()
                trigger.is_active = False
                
                adjustment = self._generate_adjustment(trigger, position)
                fired.append((trigger, adjustment))
        
        return fired
    
    def _get_trigger_value(self, trigger: AdjustmentTrigger,
                          position: Dict, market_data: Dict) -> float:
        """Get current value for trigger comparison."""
        if trigger.trigger_type == 'price':
            return market_data.get(f'{trigger.ticker}_price', 0)
        elif trigger.trigger_type == 'pnl':
            return position.get('pnl_pct', 0)
        elif trigger.trigger_type == 'delta':
            return position.get('delta', 0)
        elif trigger.trigger_type == 'time':
            return position.get('dte', 999)
        elif trigger.trigger_type == 'iv':
            return market_data.get(f'{trigger.ticker}_iv', 0)
        else:
            return 0
    
    def _evaluate_condition(self, value: float, condition: str, 
                            threshold: float) -> bool:
        """Evaluate trigger condition."""
        if condition == 'above':
            return value > threshold
        elif condition == 'below':
            return value < threshold
        elif condition == 'equals':
            return abs(value - threshold) < 0.01
        else:
            return False
    
    def _generate_adjustment(self, trigger: AdjustmentTrigger,
                             position: Dict) -> Dict:
        """Generate adjustment order based on trigger."""
        return {
            'trigger_id': trigger.trigger_id,
            'adjustment_type': trigger.adjustment_type.value,
            'position_id': trigger.position_id,
            'ticker': trigger.ticker,
            'params': trigger.adjustment_params,
            'generated_at': datetime.now().isoformat()
        }
    
    def create_default_triggers(self, position_id: str, ticker: str,
                                 entry_price: float) -> List[AdjustmentTrigger]:
        """Create standard set of triggers for a new position."""
        triggers = []
        
        # Profit target at 50%
        triggers.append(self.create_trigger(
            position_id, ticker,
            trigger_type='pnl',
            condition='above',
            threshold=50,
            adjustment_type=AdjustmentType.CLOSE_PARTIAL,
            adjustment_params={'close_pct': 50}
        ))
        
        # Stop loss at 100%
        triggers.append(self.create_trigger(
            position_id, ticker,
            trigger_type='pnl',
            condition='below',
            threshold=-100,
            adjustment_type=AdjustmentType.CLOSE_FULL
        ))
        
        # Roll at 14 DTE
        triggers.append(self.create_trigger(
            position_id, ticker,
            trigger_type='time',
            condition='below',
            threshold=14,
            adjustment_type=AdjustmentType.ROLL_OUT,
            adjustment_params={'target_dte': 45}
        ))
        
        return triggers
    
    def get_active_triggers(self) -> List[AdjustmentTrigger]:
        """Get all active triggers."""
        return [t for t in self._triggers.values() if t.is_active]


# ============================================================
# SMART ORDER ROUTING
# ============================================================

class SmartOrderRouter:
    """
    Optimizes order placement for best execution.
    """
    
    def __init__(self):
        self.exchanges = ['CBOE', 'PHLX', 'ISE', 'AMEX', 'BOX']
    
    def route_order(self, order: TradeOrder) -> Dict:
        """Route order to optimal exchange/venue."""
        # Analyze order characteristics
        order_analysis = self._analyze_order(order)
        
        # Determine best routing
        routing = self._determine_routing(order_analysis)
        
        # Generate execution plan
        execution_plan = self._create_execution_plan(order, routing)
        
        return execution_plan
    
    def _analyze_order(self, order: TradeOrder) -> Dict:
        """Analyze order characteristics."""
        total_contracts = sum(leg.get('quantity', 0) for leg in order.legs)
        is_spread = len(order.legs) > 1
        
        return {
            'total_contracts': total_contracts,
            'is_spread': is_spread,
            'leg_count': len(order.legs),
            'order_type': order.order_type.value,
            'urgency': 'normal'
        }
    
    def _determine_routing(self, analysis: Dict) -> Dict:
        """Determine optimal routing."""
        if analysis['is_spread']:
            # Complex orders route to exchanges with good spread execution
            exchange = 'CBOE'
            strategy = 'spread_book'
        else:
            # Simple orders can price improve
            exchange = 'BEST'
            strategy = 'price_improve'
        
        return {
            'primary_exchange': exchange,
            'strategy': strategy,
            'allow_partial': analysis['total_contracts'] > 5,
            'price_improve_allowed': True
        }
    
    def _create_execution_plan(self, order: TradeOrder, 
                               routing: Dict) -> Dict:
        """Create detailed execution plan."""
        return {
            'order_id': order.order_id,
            'routing': routing,
            'execution_steps': [
                {
                    'step': 1,
                    'action': 'submit_to_exchange',
                    'exchange': routing['primary_exchange'],
                    'order_type': order.order_type.value,
                    'limit_price': order.limit_price
                },
                {
                    'step': 2,
                    'action': 'monitor_fill',
                    'timeout_seconds': 60
                },
                {
                    'step': 3,
                    'action': 'adjust_if_needed',
                    'price_increment': 0.01
                }
            ],
            'created_at': datetime.now().isoformat()
        }


# ============================================================
# POSITION MIGRATOR
# ============================================================

class PositionMigrator:
    """
    Handles position migrations between strategies.
    """
    
    def __init__(self):
        self._migration_counter = 0
        self.trader = EnhancedOneClickTrader()
    
    def plan_migration(self, current_position: Dict,
                       target_strategy: str,
                       reason: MigrationReason) -> PositionMigration:
        """Plan a position migration."""
        self._migration_counter += 1
        
        ticker = current_position.get('ticker', 'UNKNOWN')
        
        # Generate close orders for current position
        close_orders = self._generate_close_orders(current_position)
        
        # Generate open orders for target position
        target_order = self.trader.generate_order(
            ticker, target_strategy,
            account_size=current_position.get('account_size', 10000)
        )
        
        # Calculate cost/benefit
        close_credit = sum(o.limit_price for o in close_orders)
        open_cost = target_order.limit_price
        net = close_credit - open_cost
        
        return PositionMigration(
            migration_id=f"migration_{self._migration_counter}",
            ticker=ticker,
            reason=reason,
            current_strategy=current_position.get('strategy', 'unknown'),
            current_legs=current_position.get('legs', []),
            target_strategy=target_strategy,
            target_legs=target_order.legs,
            close_orders=close_orders,
            open_orders=[target_order],
            estimated_debit_credit=round(net, 2),
            risk_change=0,  # Would need more calculation
            execution_window='market_open',
            created_at=datetime.now()
        )
    
    def _generate_close_orders(self, position: Dict) -> List[TradeOrder]:
        """Generate orders to close current position."""
        legs = position.get('legs', [])
        
        # Reverse each leg to close
        close_legs = []
        for leg in legs:
            close_leg = leg.copy()
            close_leg['action'] = 'SELL' if leg['action'] == 'BUY' else 'BUY'
            close_legs.append(close_leg)
        
        order = TradeOrder(
            order_id=f"close_{position.get('id', 'unknown')}",
            ticker=position.get('ticker', 'UNKNOWN'),
            strategy='close',
            legs=close_legs,
            order_type=OrderType.LIMIT,
            limit_price=position.get('current_value', 0),
            max_slippage=0.05,
            time_in_force='day',
            rationale='Closing position for migration',
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=8)
        )
        
        return [order]
    
    def suggest_migration(self, position: Dict,
                          market_data: Dict) -> Optional[PositionMigration]:
        """AI suggests if position should be migrated."""
        ticker = position.get('ticker', 'UNKNOWN')
        pnl_pct = position.get('pnl_pct', 0)
        dte = position.get('dte', 999)
        
        # Check conditions that warrant migration
        if pnl_pct > 50:
            return self.plan_migration(
                position, 
                self.trader._select_strategy(ticker),
                MigrationReason.PROFIT_TARGET
            )
        
        if pnl_pct < -75:
            return self.plan_migration(
                position,
                'cash_secured_put',  # Conservative alternative
                MigrationReason.STOP_LOSS
            )
        
        if dte < 7:
            return self.plan_migration(
                position,
                position.get('strategy', 'iron_condor'),
                MigrationReason.EXPIRATION
            )
        
        return None


# ============================================================
# AUTO-JOURNALING SYSTEM
# ============================================================

class AutoJournalSystem:
    """
    Automatically generates trade journal entries.
    No manual input required.
    """
    
    def __init__(self):
        self._entries: Dict[str, JournalEntry] = {}
        self._entry_counter = 0
    
    def record_entry(self, trade: Dict, market_context: Dict) -> JournalEntry:
        """Record a new trade entry."""
        self._entry_counter += 1
        
        ticker = trade.get('ticker', 'UNKNOWN')
        strategy = trade.get('strategy', 'unknown')
        
        entry = JournalEntry(
            entry_id=f"journal_{self._entry_counter}",
            trade_date=datetime.now().strftime('%Y-%m-%d'),
            ticker=ticker,
            strategy=strategy,
            entry_price=trade.get('entry_price', 0),
            exit_price=None,
            pnl=None,
            pnl_pct=None,
            iv_rank_entry=market_context.get('iv_rank', 50),
            market_regime=market_context.get('regime', 'normal'),
            sentiment=market_context.get('sentiment', 'neutral'),
            entry_rationale=self._generate_entry_rationale(trade, market_context),
            exit_rationale=None,
            lessons_learned=None,
            tags=self._generate_tags(trade, market_context),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self._entries[entry.entry_id] = entry
        return entry
    
    def record_exit(self, entry_id: str, exit_price: float,
                    reason: str) -> Optional[JournalEntry]:
        """Record trade exit."""
        if entry_id not in self._entries:
            return None
        
        entry = self._entries[entry_id]
        entry.exit_price = exit_price
        
        if entry.entry_price != 0:
            entry.pnl = exit_price - entry.entry_price
            entry.pnl_pct = (entry.pnl / abs(entry.entry_price)) * 100
        
        entry.exit_rationale = reason
        entry.lessons_learned = self._generate_lessons(entry)
        entry.updated_at = datetime.now()
        
        return entry
    
    def _generate_entry_rationale(self, trade: Dict, context: Dict) -> str:
        """Generate AI entry rationale."""
        parts = [f"Entered {trade.get('strategy', 'position')} on {trade.get('ticker', 'UNKNOWN')}"]
        
        iv_rank = context.get('iv_rank', 50)
        if iv_rank > 60:
            parts.append(f"• High IV environment ({iv_rank:.0f}%) favored premium selling")
        elif iv_rank < 40:
            parts.append(f"• Low IV ({iv_rank:.0f}%) made options relatively cheap")
        
        regime = context.get('regime', 'normal')
        parts.append(f"• Market regime: {regime}")
        
        sentiment = context.get('sentiment', 'neutral')
        parts.append(f"• Sentiment: {sentiment}")
        
        return "\n".join(parts)
    
    def _generate_lessons(self, entry: JournalEntry) -> str:
        """Generate lessons learned from the trade."""
        lessons = []
        
        if entry.pnl_pct and entry.pnl_pct > 0:
            lessons.append(f"Profitable trade (+{entry.pnl_pct:.1f}%)")
            if entry.iv_rank_entry > 60:
                lessons.append("High IV entry contributed to success")
        elif entry.pnl_pct and entry.pnl_pct < 0:
            lessons.append(f"Loss on trade ({entry.pnl_pct:.1f}%)")
            lessons.append("Review entry criteria for future trades")
        
        return "\n".join(lessons) if lessons else "Trade completed - review for patterns"
    
    def _generate_tags(self, trade: Dict, context: Dict) -> List[str]:
        """Generate tags for the journal entry."""
        tags = [trade.get('strategy', 'unknown')]
        
        iv_rank = context.get('iv_rank', 50)
        if iv_rank > 70:
            tags.append('high_iv')
        elif iv_rank < 30:
            tags.append('low_iv')
        
        if context.get('regime') == 'high_volatility':
            tags.append('volatile_market')
        
        return tags
    
    def get_entries(self, ticker: str = None, 
                    strategy: str = None) -> List[JournalEntry]:
        """Get journal entries with optional filters."""
        entries = list(self._entries.values())
        
        if ticker:
            entries = [e for e in entries if e.ticker == ticker]
        
        if strategy:
            entries = [e for e in entries if e.strategy == strategy]
        
        return sorted(entries, key=lambda e: e.created_at, reverse=True)
    
    def get_statistics(self) -> Dict:
        """Get journal statistics."""
        entries = list(self._entries.values())
        closed = [e for e in entries if e.exit_price is not None]
        
        if not closed:
            return {'total_trades': len(entries), 'closed_trades': 0}
        
        wins = [e for e in closed if e.pnl_pct and e.pnl_pct > 0]
        losses = [e for e in closed if e.pnl_pct and e.pnl_pct < 0]
        
        return {
            'total_trades': len(entries),
            'closed_trades': len(closed),
            'win_count': len(wins),
            'loss_count': len(losses),
            'win_rate': len(wins) / len(closed) * 100 if closed else 0,
            'avg_win': sum(e.pnl_pct for e in wins) / len(wins) if wins else 0,
            'avg_loss': sum(e.pnl_pct for e in losses) / len(losses) if losses else 0
        }


# ============================================================
# UNIFIED AUTO-EXECUTION ENGINE
# ============================================================

class AutoExecutionEngine:
    """
    Unified interface for all auto-execution features.
    """
    
    def __init__(self):
        self.trader = EnhancedOneClickTrader()
        self.adjustment = AutoAdjustmentEngine()
        self.router = SmartOrderRouter()
        self.migrator = PositionMigrator()
        self.journal = AutoJournalSystem()
    
    def one_click_trade(self, ticker: str, strategy: str = 'auto',
                        account_size: float = 10000) -> Dict:
        """Generate one-click trade with full automation."""
        # Generate order
        order = self.trader.generate_order(ticker, strategy, account_size)
        
        # Route order
        execution_plan = self.router.route_order(order)
        
        # Create default triggers
        triggers = self.adjustment.create_default_triggers(
            order.order_id, ticker, order.limit_price
        )
        
        # Journal entry
        market_context = self.trader._get_iv_data(ticker)
        journal_entry = self.journal.record_entry(
            {'ticker': ticker, 'strategy': strategy, 'entry_price': order.limit_price},
            market_context
        )
        
        return {
            'order': order,
            'execution_plan': execution_plan,
            'triggers': triggers,
            'journal_entry': journal_entry
        }
    
    def check_all_triggers(self, positions: List[Dict],
                           market_data: Dict) -> List[Dict]:
        """Check all triggers and return fired adjustments."""
        return self.adjustment.check_triggers(positions, market_data)
    
    def suggest_migrations(self, positions: List[Dict],
                          market_data: Dict) -> List[PositionMigration]:
        """Get migration suggestions for all positions."""
        migrations = []
        for pos in positions:
            migration = self.migrator.suggest_migration(pos, market_data)
            if migration:
                migrations.append(migration)
        return migrations
    
    def get_journal_stats(self) -> Dict:
        """Get trading journal statistics."""
        return self.journal.get_statistics()


# ============================================================
# SINGLETON
# ============================================================

_auto_engine = None

def get_auto_execution_engine() -> AutoExecutionEngine:
    """Get singleton auto-execution engine."""
    global _auto_engine
    if _auto_engine is None:
        _auto_engine = AutoExecutionEngine()
    return _auto_engine
