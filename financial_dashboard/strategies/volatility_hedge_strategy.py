"""
Volatility Hedge Strategy - Bear Put Spread Bot

Enters defined-risk bearish positions (Long Put Spreads) during low volatility
periods to provide portfolio protection against sudden market corrections and
volatility spikes.

Strategy Logic:
- Entry: VIX < 15 on volatility ETFs (VXX, UVXY)
- Position: Bear Put Spread with 30-60 DTE, 60Δ long / 40Δ short
- Exit: 200% profit target, -75% stop loss, or VIX spike exit (VIX > 30)

Expected Performance:
- Win Rate: 30-40% (tail hedge - infrequent wins)
- Risk/Reward: Highly asymmetric (wins are 3-5x larger than losses)
- Market Environment: Profits from sharp volatility expansions and market sell-offs
"""

from strategies.base_strategy import BaseStrategy
import pandas as pd
import numpy as np
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class VolatilityHedgeStrategy(BaseStrategy):
    """
    Volatility Hedge: Enters Bear Put Spreads when VIX is low to hedge against crashes.
    
    This strategy acts as portfolio insurance, establishing protective put spreads
    on volatility ETFs when complacency is high (VIX < 15). These positions are
    designed to pay out significantly during market stress events.
    """
    
    def __init__(self,
                 symbols: List[str] = None,
                 vix_entry_threshold: float = 15.0,
                 vix_exit_spike: float = 30.0,
                 min_dte: int = 30,
                 max_dte: int = 60,
                 long_leg_delta: float = 60.0,
                 short_leg_delta: float = 40.0,
                 profit_target_pct: float = 200.0,
                 stop_loss_pct: float = -75.0):
        """
        Initialize the Volatility Hedge Strategy.
        
        Args:
            symbols: List of volatility ETF symbols (default: VXX, UVXY)
            vix_entry_threshold: Enter positions when VIX below this (default: 15)
            vix_exit_spike: Exit positions when VIX spikes above this (default: 30)
            min_dte: Minimum days to expiration (default: 30)
            max_dte: Maximum days to expiration (default: 60)
            long_leg_delta: Delta for long put leg (default: 60)
            short_leg_delta: Delta for short put leg (default: 40)
            profit_target_pct: Profit target as % of debit (default: 200)
            stop_loss_pct: Stop loss as % of debit (default: -75)
        """
        super().__init__(name="Volatility Hedge", config={})
        self.symbols = symbols or ['VXX', 'UVXY']
        self.vix_entry_threshold = vix_entry_threshold
        self.vix_exit_spike = vix_exit_spike
        self.min_dte = min_dte
        self.max_dte = max_dte
        self.long_leg_delta = long_leg_delta
        self.short_leg_delta = short_leg_delta
        self.profit_target_pct = profit_target_pct
        self.stop_loss_pct = stop_loss_pct
        
        logger.info(f"Volatility Hedge Strategy initialized: symbols={self.symbols}, "
                   f"VIX entry={self.vix_entry_threshold}, VIX exit={self.vix_exit_spike}, "
                   f"DTE={self.min_dte}-{self.max_dte}")
    
    def generate_signals(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate Bear Put Spread signals when VIX is below threshold.
        
        Args:
            data: Dictionary containing market data for volatility symbols.
                  Expected structure:
                  {
                      'VXX': {
                          'quote': {'c': 18.5, ...},
                          'vix_level': 12.5,  # Current VIX index level
                          'options_chain': [...],
                      },
                      'MARKET': {
                          'vix': 12.5  # Can also be provided at market level
                      }
                  }
        
        Returns:
            List of signal dictionaries, each representing a Bear Put Spread opportunity.
            Signal structure:
            {
                'action': 'OPEN_BEAR_PUT_SPREAD',
                'symbol': 'VXX',
                'strategy_type': 'bear_put_spread',
                'legs': [
                    {'type': 'put', 'action': 'buy', 'strike': 19, 'delta': -60},
                    {'type': 'put', 'action': 'sell', 'strike': 17, 'delta': -40}
                ],
                'dte': 45,
                'entry_criteria': {...},
                'exit_rules': {...},
                'expected_debit': 1.20,
                'max_profit': 0.80,
                'risk_reward_ratio': 0.67
            }
        """
        signals = []
        
        # Get current VIX level from data
        vix_level = self._get_vix_level(data)
        
        # Check if VIX is below entry threshold
        if vix_level >= self.vix_entry_threshold:
            logger.debug(f"VIX {vix_level:.2f} >= threshold {self.vix_entry_threshold}, no entry signal")
            return signals
        
        logger.info(f"VIX {vix_level:.2f} < {self.vix_entry_threshold}, scanning for hedge opportunities")
        
        for symbol in self.symbols:
            if symbol not in data:
                logger.debug(f"No data available for {symbol}")
                continue
            
            symbol_data = data[symbol]
            
            # Extract required data
            quote = symbol_data.get('quote', {})
            current_price = quote.get('c', 0)
            options_chain = symbol_data.get('options_chain', [])
            
            # Check if we have options data
            if not options_chain or current_price <= 0:
                logger.warning(f"{symbol}: Missing options chain or invalid price")
                continue
            
            # Find appropriate strikes for Bear Put Spread
            bear_put_legs = self._construct_bear_put_spread_legs(
                symbol, current_price, options_chain
            )
            
            if not bear_put_legs:
                logger.debug(f"{symbol}: Could not construct Bear Put Spread legs")
                continue
            
            # Calculate expected debit and profit potential
            expected_debit = self._calculate_expected_debit(bear_put_legs)
            spread_width = bear_put_legs[0]['strike'] - bear_put_legs[1]['strike']
            max_profit = spread_width - expected_debit
            
            # Create signal
            signal = {
                'action': 'OPEN_BEAR_PUT_SPREAD',
                'symbol': symbol,
                'strategy_type': 'bear_put_spread',
                'legs': bear_put_legs,
                'dte': self._get_target_dte(options_chain),
                'entry_criteria': {
                    'vix_level': round(vix_level, 2),
                    'vix_threshold': self.vix_entry_threshold,
                    'low_volatility_confirmed': True,
                    'current_price': current_price,
                    'timestamp': pd.Timestamp.now().isoformat()
                },
                'exit_rules': {
                    'profit_target_pct': self.profit_target_pct,
                    'stop_loss_pct': self.stop_loss_pct,
                    'vix_spike_exit': self.vix_exit_spike
                },
                'expected_debit': round(expected_debit, 2),
                'max_profit': round(max_profit, 2),
                'max_loss': round(expected_debit, 2),
                'risk_reward_ratio': round(max_profit / expected_debit, 2) if expected_debit > 0 else 0,
                'quantity': 1,
                'notes': 'Portfolio hedge - expect small losses during normal markets, large wins during crashes'
            }
            
            signals.append(signal)
            logger.info(f"Generated Bear Put Spread hedge signal for {symbol}: "
                       f"VIX={vix_level:.2f}, Debit=${expected_debit:.2f}")
        
        return signals
    
    def _get_vix_level(self, data: Dict[str, Any]) -> float:
        """
        Extract current VIX level from market data.
        
        Args:
            data: Market data dictionary
        
        Returns:
            Current VIX level, or 999.0 if not found (to prevent false entries)
        """
        # Check if VIX is provided at market level
        if 'MARKET' in data and 'vix' in data['MARKET']:
            return data['MARKET']['vix']
        
        # Check if VIX is provided in symbol-level data
        for symbol in self.symbols:
            if symbol in data and 'vix_level' in data[symbol]:
                return data[symbol]['vix_level']
        
        # Check if VIX symbol itself is in data
        if 'VIX' in data:
            vix_quote = data['VIX'].get('quote', {})
            if 'c' in vix_quote:
                return vix_quote['c']
        
        logger.warning("VIX level not found in data, returning high value to prevent entry")
        return 999.0  # High value to prevent false entries
    
    def _construct_bear_put_spread_legs(self, symbol: str, current_price: float,
                                         options_chain: List[Dict]) -> List[Dict[str, Any]]:
        """
        Construct the 2 legs of a Bear Put Spread based on delta targeting.
        
        Args:
            symbol: Symbol being traded
            current_price: Current price of underlying
            options_chain: List of available options
        
        Returns:
            List of 2 leg dictionaries or empty list if construction fails
        """
        legs = []
        
        try:
            # Filter options by DTE range
            target_options = [
                opt for opt in options_chain
                if self.min_dte <= opt.get('dte', 0) <= self.max_dte
                and opt.get('type') == 'put'
            ]
            
            if not target_options:
                return []
            
            # Find long put (60 delta, closer to ATM)
            long_put = self._find_option_by_delta(target_options, self.long_leg_delta)
            if not long_put:
                return []
            
            # Find short put (40 delta, further OTM)
            short_put = self._find_option_by_delta(target_options, self.short_leg_delta)
            if not short_put:
                return []
            
            # Ensure long put is higher strike than short put (buying higher, selling lower)
            if long_put['strike'] <= short_put['strike']:
                logger.warning(f"{symbol}: Long put strike not higher than short put")
                return []
            
            # Construct legs (order: buy higher strike, sell lower strike)
            legs = [
                {
                    'type': 'put',
                    'action': 'buy',
                    'strike': long_put['strike'],
                    'delta': long_put.get('delta', -self.long_leg_delta),
                    'premium': long_put.get('mark', 0)
                },
                {
                    'type': 'put',
                    'action': 'sell',
                    'strike': short_put['strike'],
                    'delta': short_put.get('delta', -self.short_leg_delta),
                    'premium': short_put.get('mark', 0)
                }
            ]
            
            return legs
            
        except Exception as e:
            logger.error(f"Error constructing Bear Put Spread legs for {symbol}: {e}")
            return []
    
    def _find_option_by_delta(self, options: List[Dict], target_delta: float) -> Dict[str, Any]:
        """
        Find put option closest to target delta.
        
        Note: Put deltas are negative, but we work with absolute values for comparison.
        """
        if not options:
            return None
        
        # Work with absolute values for comparison
        target_delta_abs = abs(target_delta)
        
        # Find option with delta closest to target (in absolute terms)
        best_option = min(
            options,
            key=lambda x: abs(abs(x.get('delta', 0)) - target_delta_abs)
        )
        
        return best_option if best_option else None
    
    def _get_target_dte(self, options_chain: List[Dict]) -> int:
        """Get the target DTE from available options (middle of range)."""
        target_dte = (self.min_dte + self.max_dte) // 2
        return target_dte
    
    def _calculate_expected_debit(self, legs: List[Dict]) -> float:
        """
        Calculate total expected debit paid for Bear Put Spread.
        
        Debit = Long Put Premium - Short Put Premium
        """
        debit = 0.0
        
        for leg in legs:
            premium = leg.get('premium', 0)
            if leg['action'] == 'buy':
                debit += premium
            elif leg['action'] == 'sell':
                debit -= premium
        
        return debit
    
    def check_exit_conditions(self, position: Dict[str, Any], 
                               current_market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if position should be exited based on P/L or VIX spike.
        
        Args:
            position: Dictionary containing position details
            current_market_data: Current market data including VIX level
        
        Returns:
            Dictionary with exit decision
        """
        pnl_pct = position.get('pnl_pct', 0)
        
        # Check profit target (200% gain - significant volatility event)
        if pnl_pct >= self.profit_target_pct:
            return {
                'action': 'CLOSE',
                'reason': f'Profit target hit ({pnl_pct:.1f}% >= {self.profit_target_pct}%)'
            }
        
        # Check stop loss (-75% - position not performing)
        if pnl_pct <= self.stop_loss_pct:
            return {
                'action': 'CLOSE',
                'reason': f'Stop loss hit ({pnl_pct:.1f}% <= {self.stop_loss_pct}%)'
            }
        
        # Check for VIX spike (volatility expansion reached exit threshold)
        vix_level = self._get_vix_level(current_market_data)
        if vix_level >= self.vix_exit_spike:
            return {
                'action': 'CLOSE',
                'reason': f'VIX spike exit triggered (VIX {vix_level:.2f} >= {self.vix_exit_spike})'
            }
        
        return {'action': 'HOLD', 'reason': None}


# Export strategy
__all__ = ['VolatilityHedgeStrategy']
