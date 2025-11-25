"""
Income Generator Strategy - Iron Condor Bot

Systematically sells high-probability Iron Condors on liquid, broad-market ETFs
when implied volatility is elevated. Designed to generate consistent income from
time decay (Theta) in sideways or range-bound markets.

Strategy Logic:
- Entry: IV Rank > 30 on SPY, QQQ, or IWM
- Position: Iron Condor with 45 DTE, 15 Delta strikes on both sides
- Exit: 50% profit target, -100% stop loss, or DTE < 21 days

Expected Performance:
- Win Rate: 70-80%
- Risk/Reward: Small consistent gains with occasional larger losses
- Market Environment: Excels in range-bound markets
"""

from strategies.base_strategy import BaseStrategy
import pandas as pd
import numpy as np
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class IncomeGeneratorStrategy(BaseStrategy):
    """
    Core Income Generator: Sells Iron Condors when IV Rank > 30.
    
    This strategy capitalizes on elevated implied volatility by selling premium
    on both sides of the market, profiting from time decay when the underlying
    stays within a defined range.
    """
    
    def __init__(self, 
                 symbols: List[str] = None,
                 iv_rank_threshold: float = 30.0,
                 target_dte: int = 45,
                 strike_delta: float = 15.0,
                 spread_width: float = 5.0,
                 profit_target_pct: float = 50.0,
                 stop_loss_pct: float = -100.0,
                 time_exit_dte: int = 21):
        """
        Initialize the Income Generator Strategy.
        
        Args:
            symbols: List of symbols to scan (default: SPY, QQQ, IWM)
            iv_rank_threshold: Minimum IV Rank to enter (default: 30)
            target_dte: Target days to expiration (default: 45)
            strike_delta: Delta for short strikes (default: 15)
            spread_width: Width of spreads in dollars (default: 5)
            profit_target_pct: Profit target as % of credit (default: 50)
            stop_loss_pct: Stop loss as % of credit (default: -100)
            time_exit_dte: Exit when DTE drops below this (default: 21)
        """
        super().__init__(name="Income Generator", config={})
        self.symbols = symbols or ['SPY', 'QQQ', 'IWM']
        self.iv_rank_threshold = iv_rank_threshold
        self.target_dte = target_dte
        self.strike_delta = strike_delta
        self.spread_width = spread_width
        self.profit_target_pct = profit_target_pct
        self.stop_loss_pct = stop_loss_pct
        self.time_exit_dte = time_exit_dte
        
        logger.info(f"Income Generator Strategy initialized: symbols={self.symbols}, "
                   f"IV threshold={self.iv_rank_threshold}, DTE={self.target_dte}")
    
    def generate_signals(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate Iron Condor signals based on IV Rank criteria.
        
        Args:
            data: Dictionary containing market data for each symbol.
                  Expected structure:
                  {
                      'SPY': {
                          'quote': {'c': 450.0, ...},
                          'iv_rank': 35.5,
                          'options_chain': [...],
                          'dte_45': True  # Flag indicating 45 DTE options available
                      },
                      ...
                  }
        
        Returns:
            List of signal dictionaries, each representing an Iron Condor opportunity.
            Signal structure:
            {
                'action': 'OPEN_IRON_CONDOR',
                'symbol': 'SPY',
                'strategy_type': 'iron_condor',
                'legs': [
                    {'type': 'call', 'action': 'sell', 'strike': 465, 'delta': 15},
                    {'type': 'call', 'action': 'buy', 'strike': 470, 'delta': 8},
                    {'type': 'put', 'action': 'sell', 'strike': 435, 'delta': -15},
                    {'type': 'put', 'action': 'buy', 'strike': 430, 'delta': -8}
                ],
                'dte': 45,
                'entry_criteria': {...},
                'exit_rules': {...},
                'expected_credit': 2.50,
                'max_risk': 2.50,
                'risk_reward_ratio': 1.0
            }
        """
        signals = []
        
        for symbol in self.symbols:
            if symbol not in data:
                logger.debug(f"No data available for {symbol}")
                continue
            
            symbol_data = data[symbol]
            
            # Extract required data
            iv_rank = symbol_data.get('iv_rank', 0)
            quote = symbol_data.get('quote', {})
            current_price = quote.get('c', 0)
            options_chain = symbol_data.get('options_chain', [])
            
            # Check IV Rank entry condition
            if iv_rank <= self.iv_rank_threshold:
                logger.debug(f"{symbol}: IV Rank {iv_rank:.1f} below threshold "
                           f"{self.iv_rank_threshold}")
                continue
            
            # Check if we have options data
            if not options_chain or current_price <= 0:
                logger.warning(f"{symbol}: Missing options chain or invalid price")
                continue
            
            # Find appropriate strikes for Iron Condor
            iron_condor_legs = self._construct_iron_condor_legs(
                symbol, current_price, options_chain
            )
            
            if not iron_condor_legs:
                logger.debug(f"{symbol}: Could not construct Iron Condor legs")
                continue
            
            # Calculate expected credit and risk
            expected_credit = self._calculate_expected_credit(iron_condor_legs)
            max_risk = self.spread_width - expected_credit
            
            # Create signal
            signal = {
                'action': 'OPEN_IRON_CONDOR',
                'symbol': symbol,
                'strategy_type': 'iron_condor',
                'legs': iron_condor_legs,
                'dte': self.target_dte,
                'entry_criteria': {
                    'iv_rank': iv_rank,
                    'iv_rank_threshold': self.iv_rank_threshold,
                    'current_price': current_price,
                    'timestamp': pd.Timestamp.now().isoformat()
                },
                'exit_rules': {
                    'profit_target_pct': self.profit_target_pct,
                    'stop_loss_pct': self.stop_loss_pct,
                    'time_exit_dte': self.time_exit_dte
                },
                'expected_credit': round(expected_credit, 2),
                'max_risk': round(max_risk, 2),
                'risk_reward_ratio': round(max_risk / expected_credit, 2) if expected_credit > 0 else 0,
                'quantity': 1  # Default to 1 contract
            }
            
            signals.append(signal)
            logger.info(f"Generated Iron Condor signal for {symbol}: "
                       f"IV Rank={iv_rank:.1f}, Expected Credit=${expected_credit:.2f}")
        
        return signals
    
    def _construct_iron_condor_legs(self, symbol: str, current_price: float, 
                                     options_chain: List[Dict]) -> List[Dict[str, Any]]:
        """
        Construct the 4 legs of an Iron Condor based on delta targeting.
        
        Args:
            symbol: Symbol being traded
            current_price: Current price of underlying
            options_chain: List of available options
        
        Returns:
            List of 4 leg dictionaries or empty list if construction fails
        """
        legs = []
        
        try:
            # Filter options by DTE (look for options close to target DTE)
            dte_tolerance = 5  # Accept options within 5 days of target
            target_options = [
                opt for opt in options_chain 
                if abs(opt.get('dte', 0) - self.target_dte) <= dte_tolerance
            ]
            
            if not target_options:
                return []
            
            # Separate calls and puts
            calls = [opt for opt in target_options if opt.get('type') == 'call']
            puts = [opt for opt in target_options if opt.get('type') == 'put']
            
            # Find short call (15 delta, OTM)
            short_call = self._find_option_by_delta(calls, self.strike_delta, 'call')
            if not short_call:
                return []
            
            # Find long call (further OTM, spread_width away)
            long_call_strike = short_call['strike'] + self.spread_width
            long_call = self._find_option_by_strike(calls, long_call_strike, 'call')
            if not long_call:
                return []
            
            # Find short put (15 delta, OTM)
            short_put = self._find_option_by_delta(puts, self.strike_delta, 'put')
            if not short_put:
                return []
            
            # Find long put (further OTM, spread_width away)
            long_put_strike = short_put['strike'] - self.spread_width
            long_put = self._find_option_by_strike(puts, long_put_strike, 'put')
            if not long_put:
                return []
            
            # Construct legs (order: sell call, buy call, sell put, buy put)
            legs = [
                {
                    'type': 'call',
                    'action': 'sell',
                    'strike': short_call['strike'],
                    'delta': short_call.get('delta', self.strike_delta),
                    'premium': short_call.get('mark', 0)
                },
                {
                    'type': 'call',
                    'action': 'buy',
                    'strike': long_call['strike'],
                    'delta': long_call.get('delta', self.strike_delta / 2),
                    'premium': long_call.get('mark', 0)
                },
                {
                    'type': 'put',
                    'action': 'sell',
                    'strike': short_put['strike'],
                    'delta': short_put.get('delta', -self.strike_delta),
                    'premium': short_put.get('mark', 0)
                },
                {
                    'type': 'put',
                    'action': 'buy',
                    'strike': long_put['strike'],
                    'delta': long_put.get('delta', -self.strike_delta / 2),
                    'premium': long_put.get('mark', 0)
                }
            ]
            
            return legs
            
        except Exception as e:
            logger.error(f"Error constructing Iron Condor legs for {symbol}: {e}")
            return []
    
    def _find_option_by_delta(self, options: List[Dict], target_delta: float, 
                               option_type: str) -> Dict[str, Any]:
        """Find option closest to target delta."""
        if not options:
            return None
        
        # For puts, delta is negative
        if option_type == 'put':
            target_delta = -abs(target_delta)
        else:
            target_delta = abs(target_delta)
        
        # Find option with delta closest to target
        best_option = min(
            options, 
            key=lambda x: abs(x.get('delta', 0) - target_delta)
        )
        
        return best_option if best_option else None
    
    def _find_option_by_strike(self, options: List[Dict], target_strike: float,
                                option_type: str) -> Dict[str, Any]:
        """Find option with specific strike price."""
        for opt in options:
            if abs(opt.get('strike', 0) - target_strike) < 0.1:
                return opt
        return None
    
    def _calculate_expected_credit(self, legs: List[Dict]) -> float:
        """
        Calculate total expected credit received from Iron Condor.
        
        Credit = (Short Call Premium + Short Put Premium) - (Long Call Premium + Long Put Premium)
        """
        credit = 0.0
        
        for leg in legs:
            premium = leg.get('premium', 0)
            if leg['action'] == 'sell':
                credit += premium
            elif leg['action'] == 'buy':
                credit -= premium
        
        return credit
    
    def check_exit_conditions(self, position: Dict[str, Any],
                               current_market_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Check if position should be exited based on P/L or time.
        
        Args:
            position: Dictionary containing position details
                {
                    'pnl_pct': 45.0,  # Current P/L as % of credit received
                    'days_to_expiration': 25,
                    'entry_credit': 2.50,
                    'current_value': 1.25
                }
            current_market_data: Optional current market data (not used for Iron Condor)
        
        Returns:
            Dictionary with exit decision:
            {
                'action': 'CLOSE' or 'HOLD',
                'reason': 'Profit target hit' or None
            }
        """
        pnl_pct = position.get('pnl_pct', 0)
        dte = position.get('days_to_expiration') or position.get('dte', 0)
        
        # Check profit target
        if pnl_pct >= self.profit_target_pct:
            return {
                'action': 'CLOSE',
                'reason': f'Profit target hit ({pnl_pct:.1f}% >= {self.profit_target_pct}%)'
            }
        
        # Check stop loss
        if pnl_pct <= self.stop_loss_pct:
            return {
                'action': 'CLOSE',
                'reason': f'Stop loss hit ({pnl_pct:.1f}% <= {self.stop_loss_pct}%)'
            }
        
        # Check time exit
        if dte < self.time_exit_dte:
            return {
                'action': 'CLOSE',
                'reason': f'Time exit (DTE {dte} < {self.time_exit_dte})'
            }
        
        return {'action': 'HOLD', 'reason': None}


# Export strategy
__all__ = ['IncomeGeneratorStrategy']
