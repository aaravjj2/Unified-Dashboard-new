"""
Wheel Strategy Automation Service
Implements #166 from ROADMAP_ULTIMATE.md

The Wheel Strategy:
1. Sell cash-secured puts (CSP) on stocks you want to own
2. If assigned, hold stock and sell covered calls
3. If called away, restart with CSPs
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class WheelPhase(Enum):
    """Current phase of the wheel strategy"""
    SELLING_PUTS = "selling_puts"
    HOLDING_STOCK = "holding_stock"
    SELLING_CALLS = "selling_calls"
    ASSIGNED = "assigned"
    CALLED_AWAY = "called_away"


@dataclass
class WheelPosition:
    """Represents a position in the wheel strategy"""
    ticker: str
    phase: WheelPhase
    shares: int = 0
    cost_basis: float = 0.0
    current_option: Optional[Dict] = None
    premium_collected: float = 0.0
    total_profit: float = 0.0
    started: datetime = field(default_factory=datetime.now)
    cycles_completed: int = 0
    assignments: int = 0
    call_aways: int = 0
    history: List[Dict] = field(default_factory=list)
    
    @property
    def is_holding_stock(self) -> bool:
        return self.shares > 0
    
    @property
    def roi(self) -> float:
        if self.cost_basis > 0:
            return (self.total_profit / self.cost_basis) * 100
        return 0.0


@dataclass
class WheelCriteria:
    """Criteria for selecting wheel candidates"""
    min_iv_rank: float = 30  # Minimum IV rank %
    max_iv_rank: float = 80  # Maximum IV rank %
    min_delta: float = 0.20  # Minimum delta for puts
    max_delta: float = 0.35  # Maximum delta for puts
    min_premium_yield: float = 1.0  # Minimum annualized yield %
    min_dte: int = 21  # Minimum days to expiration
    max_dte: int = 45  # Maximum days to expiration
    min_volume: int = 100  # Minimum option volume
    min_open_interest: int = 500  # Minimum open interest
    prefer_friday_expiry: bool = True
    max_position_size_pct: float = 5.0  # Max % of portfolio
    

class WheelStrategyService:
    """
    Automated Wheel Strategy Implementation
    """
    
    def __init__(self, criteria: WheelCriteria = None):
        self.criteria = criteria or WheelCriteria()
        self.positions: Dict[str, WheelPosition] = {}
        
    def find_put_candidates(self, ticker: str, 
                           options_chain: pd.DataFrame,
                           stock_price: float,
                           iv_rank: float) -> List[Dict[str, Any]]:
        """Find suitable put options for CSP"""
        if iv_rank < self.criteria.min_iv_rank or iv_rank > self.criteria.max_iv_rank:
            logger.info(f"{ticker}: IV rank {iv_rank:.1f}% outside range")
            return []
        
        candidates = []
        
        # Filter puts
        puts = options_chain[options_chain['option_type'] == 'put'].copy()
        
        for _, opt in puts.iterrows():
            dte = opt.get('dte', 0)
            delta = abs(opt.get('delta', 0))
            volume = opt.get('volume', 0)
            oi = opt.get('open_interest', 0)
            strike = opt.get('strike', 0)
            premium = opt.get('bid', 0)  # Use bid for selling
            
            # Apply filters
            if dte < self.criteria.min_dte or dte > self.criteria.max_dte:
                continue
            if delta < self.criteria.min_delta or delta > self.criteria.max_delta:
                continue
            if volume < self.criteria.min_volume:
                continue
            if oi < self.criteria.min_open_interest:
                continue
            
            # Calculate metrics
            cash_required = strike * 100
            premium_total = premium * 100
            
            # Annualized yield
            yield_to_expiry = (premium_total / cash_required) * 100
            annualized_yield = yield_to_expiry * (365 / dte)
            
            if annualized_yield < self.criteria.min_premium_yield:
                continue
            
            # Break-even
            break_even = strike - premium
            downside_protection = ((stock_price - break_even) / stock_price) * 100
            
            # Probability of profit (approximation from delta)
            pop = (1 - delta) * 100
            
            candidates.append({
                'ticker': ticker,
                'type': 'put',
                'strike': strike,
                'expiry': opt.get('expiry'),
                'dte': dte,
                'premium': premium,
                'total_premium': premium_total,
                'delta': delta,
                'iv': opt.get('implied_volatility', 0),
                'volume': volume,
                'open_interest': oi,
                'cash_required': cash_required,
                'yield_to_expiry': yield_to_expiry,
                'annualized_yield': annualized_yield,
                'break_even': break_even,
                'downside_protection': downside_protection,
                'pop': pop,
                'score': self._score_put_candidate(
                    annualized_yield, delta, dte, pop, downside_protection
                )
            })
        
        # Sort by score
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        return candidates
    
    def find_call_candidates(self, ticker: str,
                            options_chain: pd.DataFrame,
                            stock_price: float,
                            cost_basis: float) -> List[Dict[str, Any]]:
        """Find suitable call options for covered calls"""
        candidates = []
        
        # Filter calls
        calls = options_chain[options_chain['option_type'] == 'call'].copy()
        
        for _, opt in calls.iterrows():
            dte = opt.get('dte', 0)
            delta = abs(opt.get('delta', 0))
            volume = opt.get('volume', 0)
            oi = opt.get('open_interest', 0)
            strike = opt.get('strike', 0)
            premium = opt.get('bid', 0)
            
            # Apply filters - calls typically 0.25-0.35 delta
            if dte < self.criteria.min_dte or dte > self.criteria.max_dte:
                continue
            if delta < 0.20 or delta > 0.40:
                continue
            if volume < self.criteria.min_volume // 2:  # Lower volume ok for calls
                continue
            
            premium_total = premium * 100
            
            # Calculations
            yield_to_expiry = (premium_total / (stock_price * 100)) * 100
            annualized_yield = yield_to_expiry * (365 / dte)
            
            # Max profit if called away
            max_profit = (strike - cost_basis + premium) * 100
            max_profit_pct = (max_profit / (cost_basis * 100)) * 100
            
            # Upside given up
            if strike > stock_price:
                upside_given_up = ((strike - stock_price) / stock_price) * 100
            else:
                upside_given_up = 0
            
            pop = (1 - delta) * 100
            
            candidates.append({
                'ticker': ticker,
                'type': 'call',
                'strike': strike,
                'expiry': opt.get('expiry'),
                'dte': dte,
                'premium': premium,
                'total_premium': premium_total,
                'delta': delta,
                'iv': opt.get('implied_volatility', 0),
                'volume': volume,
                'open_interest': oi,
                'yield_to_expiry': yield_to_expiry,
                'annualized_yield': annualized_yield,
                'max_profit': max_profit,
                'max_profit_pct': max_profit_pct,
                'upside_given_up': upside_given_up,
                'pop': pop,
                'above_cost_basis': strike > cost_basis,
                'score': self._score_call_candidate(
                    annualized_yield, delta, dte, pop, strike > cost_basis
                )
            })
        
        # Sort by score
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        return candidates
    
    def _score_put_candidate(self, yield_ann: float, delta: float, 
                            dte: int, pop: float, protection: float) -> float:
        """Score a put candidate (higher is better)"""
        score = 0
        
        # Yield component (0-40 points)
        score += min(yield_ann * 2, 40)
        
        # Delta component - prefer 0.25-0.30 (0-20 points)
        if 0.25 <= delta <= 0.30:
            score += 20
        elif 0.20 <= delta <= 0.35:
            score += 15
        else:
            score += 10
        
        # DTE component - prefer 30-45 (0-15 points)
        if 30 <= dte <= 45:
            score += 15
        elif 21 <= dte <= 50:
            score += 10
        else:
            score += 5
        
        # POP component (0-15 points)
        score += min(pop / 5, 15)
        
        # Downside protection (0-10 points)
        score += min(protection, 10)
        
        return score
    
    def _score_call_candidate(self, yield_ann: float, delta: float,
                             dte: int, pop: float, above_basis: bool) -> float:
        """Score a call candidate"""
        score = 0
        
        # Yield (0-35 points)
        score += min(yield_ann * 2, 35)
        
        # Delta - prefer 0.25-0.35 (0-20 points)
        if 0.25 <= delta <= 0.35:
            score += 20
        elif 0.20 <= delta <= 0.40:
            score += 15
        else:
            score += 10
        
        # DTE (0-15 points)
        if 30 <= dte <= 45:
            score += 15
        elif 21 <= dte <= 50:
            score += 10
        else:
            score += 5
        
        # Above cost basis bonus (0-20 points)
        if above_basis:
            score += 20
        
        # POP (0-10 points)
        score += min(pop / 7, 10)
        
        return score
    
    def start_wheel(self, ticker: str, initial_put: Dict) -> WheelPosition:
        """Start a new wheel position by selling a put"""
        position = WheelPosition(
            ticker=ticker,
            phase=WheelPhase.SELLING_PUTS,
            current_option=initial_put,
            premium_collected=initial_put['total_premium']
        )
        
        position.history.append({
            'action': 'SELL_PUT',
            'timestamp': datetime.now(),
            'details': initial_put
        })
        
        self.positions[ticker] = position
        logger.info(f"Started wheel on {ticker}: Sold ${initial_put['strike']} put for ${initial_put['premium']:.2f}")
        
        return position
    
    def handle_assignment(self, ticker: str, assignment_price: float) -> WheelPosition:
        """Handle put assignment - stock is assigned"""
        if ticker not in self.positions:
            raise ValueError(f"No position found for {ticker}")
        
        position = self.positions[ticker]
        option = position.current_option
        
        # Calculate effective cost basis
        position.shares = 100
        position.cost_basis = option['strike'] - option['premium']
        position.phase = WheelPhase.HOLDING_STOCK
        position.assignments += 1
        position.current_option = None
        
        position.history.append({
            'action': 'ASSIGNED',
            'timestamp': datetime.now(),
            'shares': 100,
            'strike': option['strike'],
            'effective_cost': position.cost_basis
        })
        
        logger.info(f"{ticker}: Assigned at ${option['strike']}, effective cost basis ${position.cost_basis:.2f}")
        
        return position
    
    def sell_covered_call(self, ticker: str, call_option: Dict) -> WheelPosition:
        """Sell a covered call on held shares"""
        if ticker not in self.positions:
            raise ValueError(f"No position found for {ticker}")
        
        position = self.positions[ticker]
        
        if not position.is_holding_stock:
            raise ValueError(f"{ticker}: No shares held for covered call")
        
        position.phase = WheelPhase.SELLING_CALLS
        position.current_option = call_option
        position.premium_collected += call_option['total_premium']
        
        position.history.append({
            'action': 'SELL_CALL',
            'timestamp': datetime.now(),
            'details': call_option
        })
        
        logger.info(f"{ticker}: Sold ${call_option['strike']} call for ${call_option['premium']:.2f}")
        
        return position
    
    def handle_call_expiry(self, ticker: str, was_exercised: bool,
                          final_price: float) -> WheelPosition:
        """Handle call expiration"""
        if ticker not in self.positions:
            raise ValueError(f"No position found for {ticker}")
        
        position = self.positions[ticker]
        option = position.current_option
        
        if was_exercised:
            # Called away - calculate profit
            profit = (option['strike'] - position.cost_basis) * 100
            profit += option['total_premium']
            
            position.total_profit += profit
            position.shares = 0
            position.phase = WheelPhase.CALLED_AWAY
            position.call_aways += 1
            position.cycles_completed += 1
            position.current_option = None
            
            position.history.append({
                'action': 'CALLED_AWAY',
                'timestamp': datetime.now(),
                'strike': option['strike'],
                'profit': profit
            })
            
            logger.info(f"{ticker}: Called away at ${option['strike']}, profit ${profit:.2f}")
        else:
            # Expired worthless - keep shares
            position.total_profit += option['total_premium']
            position.phase = WheelPhase.HOLDING_STOCK
            position.current_option = None
            
            position.history.append({
                'action': 'CALL_EXPIRED',
                'timestamp': datetime.now(),
                'premium_kept': option['total_premium']
            })
            
            logger.info(f"{ticker}: Call expired, kept ${option['total_premium']:.2f} premium")
        
        return position
    
    def handle_put_expiry(self, ticker: str, was_assigned: bool,
                         final_price: float) -> WheelPosition:
        """Handle put expiration"""
        if ticker not in self.positions:
            raise ValueError(f"No position found for {ticker}")
        
        position = self.positions[ticker]
        option = position.current_option
        
        if was_assigned:
            return self.handle_assignment(ticker, option['strike'])
        else:
            # Expired worthless
            position.total_profit += option['total_premium']
            position.cycles_completed += 1
            position.current_option = None
            
            position.history.append({
                'action': 'PUT_EXPIRED',
                'timestamp': datetime.now(),
                'premium_kept': option['total_premium']
            })
            
            logger.info(f"{ticker}: Put expired, kept ${option['total_premium']:.2f} premium")
        
        return position
    
    def get_next_action(self, ticker: str) -> Dict[str, Any]:
        """Determine next action for a wheel position"""
        if ticker not in self.positions:
            return {'action': 'START_NEW', 'description': 'Start new wheel by selling put'}
        
        position = self.positions[ticker]
        
        if position.phase == WheelPhase.HOLDING_STOCK:
            return {
                'action': 'SELL_CALL',
                'description': f'Sell covered call on {position.shares} shares',
                'cost_basis': position.cost_basis
            }
        elif position.phase == WheelPhase.CALLED_AWAY:
            return {
                'action': 'RESTART',
                'description': 'Shares called away - restart with new put',
                'completed_cycles': position.cycles_completed
            }
        elif position.phase in [WheelPhase.SELLING_PUTS, WheelPhase.SELLING_CALLS]:
            return {
                'action': 'WAIT',
                'description': 'Wait for option expiration',
                'option': position.current_option
            }
        
        return {'action': 'UNKNOWN'}
    
    def get_position_summary(self, ticker: str) -> Dict[str, Any]:
        """Get summary of wheel position"""
        if ticker not in self.positions:
            return {'error': f'No position for {ticker}'}
        
        position = self.positions[ticker]
        
        return {
            'ticker': ticker,
            'phase': position.phase.value,
            'shares': position.shares,
            'cost_basis': position.cost_basis,
            'premium_collected': position.premium_collected,
            'total_profit': position.total_profit,
            'roi': position.roi,
            'cycles_completed': position.cycles_completed,
            'assignments': position.assignments,
            'call_aways': position.call_aways,
            'days_active': (datetime.now() - position.started).days,
            'current_option': position.current_option
        }
    
    def get_all_positions(self) -> pd.DataFrame:
        """Get DataFrame of all wheel positions"""
        if not self.positions:
            return pd.DataFrame()
        
        records = [self.get_position_summary(ticker) for ticker in self.positions]
        return pd.DataFrame(records)


# Singleton instance
_wheel_service = None

def get_wheel_service(criteria: WheelCriteria = None) -> WheelStrategyService:
    global _wheel_service
    if _wheel_service is None:
        _wheel_service = WheelStrategyService(criteria)
    return _wheel_service
