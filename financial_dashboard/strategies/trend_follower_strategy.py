"""
Trend Follower Strategy - Bull Call Spread Bot

Enters defined-risk bullish positions (Long Call Spreads) when a short-term
moving average crosses above a long-term moving average, indicating momentum
shift to an uptrend.

Strategy Logic:
- Entry: 20-day SMA crosses above 50-day SMA on SPY or QQQ
- Position: Bull Call Spread with 30-60 DTE, 40Δ long / 20Δ short
- Exit: 100% profit target, -50% stop loss, or trend reversal (MA cross down)

Expected Performance:
- Win Rate: 40-50%
- Risk/Reward: Asymmetric (wins are 2x+ larger than losses)
- Market Environment: Excels in sustained uptrends
"""

from strategies.base_strategy import BaseStrategy
import pandas as pd
import numpy as np
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class TrendFollowerStrategy(BaseStrategy):
    """
    Trend Follower: Enters Bull Call Spreads on moving average crossovers.
    
    This strategy uses the classic "Golden Cross" (20 SMA crosses above 50 SMA)
    as a signal that momentum has shifted bullish. It enters defined-risk
    directional positions to capitalize on sustained trends.
    """
    
    def __init__(self,
                 symbols: List[str] = None,
                 short_ma_period: int = 20,
                 long_ma_period: int = 50,
                 min_dte: int = 30,
                 max_dte: int = 60,
                 long_leg_delta: float = 40.0,
                 short_leg_delta: float = 20.0,
                 profit_target_pct: float = 100.0,
                 stop_loss_pct: float = -50.0):
        """
        Initialize the Trend Follower Strategy.
        
        Args:
            symbols: List of symbols to scan (default: SPY, QQQ)
            short_ma_period: Short moving average period (default: 20)
            long_ma_period: Long moving average period (default: 50)
            min_dte: Minimum days to expiration (default: 30)
            max_dte: Maximum days to expiration (default: 60)
            long_leg_delta: Delta for long call leg (default: 40)
            short_leg_delta: Delta for short call leg (default: 20)
            profit_target_pct: Profit target as % of debit (default: 100)
            stop_loss_pct: Stop loss as % of debit (default: -50)
        """
        super().__init__(name="Trend Follower", config={})
        self.symbols = symbols or ['SPY', 'QQQ']
        self.short_ma_period = short_ma_period
        self.long_ma_period = long_ma_period
        self.min_dte = min_dte
        self.max_dte = max_dte
        self.long_leg_delta = long_leg_delta
        self.short_leg_delta = short_leg_delta
        self.profit_target_pct = profit_target_pct
        self.stop_loss_pct = stop_loss_pct
        
        logger.info(f"Trend Follower Strategy initialized: symbols={self.symbols}, "
                   f"MA={self.short_ma_period}/{self.long_ma_period}, "
                   f"DTE={self.min_dte}-{self.max_dte}")
    
    def generate_signals(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate Bull Call Spread signals based on moving average crossover.
        
        Args:
            data: Dictionary containing market data for each symbol.
                  Expected structure:
                  {
                      'SPY': {
                          'quote': {'c': 450.0, ...},
                          'historical_prices': pd.DataFrame with 'close' column,
                          'ma_20': 448.5,
                          'ma_50': 445.0,
                          'ma_crossover': True,  # 20 SMA just crossed above 50 SMA
                          'options_chain': [...],
                      },
                      ...
                  }
        
        Returns:
            List of signal dictionaries, each representing a Bull Call Spread opportunity.
            Signal structure:
            {
                'action': 'OPEN_BULL_CALL_SPREAD',
                'symbol': 'SPY',
                'strategy_type': 'bull_call_spread',
                'legs': [
                    {'type': 'call', 'action': 'buy', 'strike': 445, 'delta': 40},
                    {'type': 'call', 'action': 'sell', 'strike': 455, 'delta': 20}
                ],
                'dte': 45,
                'entry_criteria': {...},
                'exit_rules': {...},
                'expected_debit': 5.50,
                'max_profit': 4.50,
                'risk_reward_ratio': 0.82
            }
        """
        signals = []
        
        for symbol in self.symbols:
            if symbol not in data:
                logger.debug(f"No data available for {symbol}")
                continue
            
            symbol_data = data[symbol]
            
            # Extract required data
            quote = symbol_data.get('quote', {})
            current_price = quote.get('c', 0)
            historical_prices = symbol_data.get('historical_prices')
            options_chain = symbol_data.get('options_chain', [])
            
            # Check for moving average crossover
            crossover_detected = self._check_ma_crossover(symbol, symbol_data, historical_prices)
            
            if not crossover_detected:
                continue
            
            # Check if we have options data
            if not options_chain or current_price <= 0:
                logger.warning(f"{symbol}: Missing options chain or invalid price")
                continue
            
            # Find appropriate strikes for Bull Call Spread
            bull_call_legs = self._construct_bull_call_spread_legs(
                symbol, current_price, options_chain
            )
            
            if not bull_call_legs:
                logger.debug(f"{symbol}: Could not construct Bull Call Spread legs")
                continue
            
            # Calculate expected debit and profit potential
            expected_debit = self._calculate_expected_debit(bull_call_legs)
            spread_width = bull_call_legs[1]['strike'] - bull_call_legs[0]['strike']
            max_profit = spread_width - expected_debit
            
            # Get MA values for documentation
            ma_20 = symbol_data.get('ma_20', 0)
            ma_50 = symbol_data.get('ma_50', 0)
            
            # Create signal
            signal = {
                'action': 'OPEN_BULL_CALL_SPREAD',
                'symbol': symbol,
                'strategy_type': 'bull_call_spread',
                'legs': bull_call_legs,
                'dte': self._get_target_dte(options_chain),
                'entry_criteria': {
                    'ma_20': round(ma_20, 2),
                    'ma_50': round(ma_50, 2),
                    'crossover_confirmed': True,
                    'current_price': current_price,
                    'timestamp': pd.Timestamp.now().isoformat()
                },
                'exit_rules': {
                    'profit_target_pct': self.profit_target_pct,
                    'stop_loss_pct': self.stop_loss_pct,
                    'trend_reversal_exit': True
                },
                'expected_debit': round(expected_debit, 2),
                'max_profit': round(max_profit, 2),
                'max_loss': round(expected_debit, 2),
                'risk_reward_ratio': round(max_profit / expected_debit, 2) if expected_debit > 0 else 0,
                'quantity': 1
            }
            
            signals.append(signal)
            logger.info(f"Generated Bull Call Spread signal for {symbol}: "
                       f"MA Cross {ma_20:.2f}/{ma_50:.2f}, Debit=${expected_debit:.2f}")
        
        return signals
    
    def _check_ma_crossover(self, symbol: str, symbol_data: Dict, 
                             historical_prices: pd.DataFrame) -> bool:
        """
        Check if 20-day SMA has crossed above 50-day SMA.
        
        Args:
            symbol: Symbol being checked
            symbol_data: Symbol data dictionary (may contain pre-calculated MAs)
            historical_prices: DataFrame with historical price data
        
        Returns:
            True if crossover detected, False otherwise
        """
        # Check if crossover flag is already provided
        if 'ma_crossover' in symbol_data:
            crossover = symbol_data['ma_crossover']
            if crossover:
                logger.info(f"{symbol}: MA crossover detected (pre-calculated)")
            return crossover
        
        # Calculate MAs if we have historical data
        if historical_prices is None or len(historical_prices) < self.long_ma_period:
            logger.debug(f"{symbol}: Insufficient historical data for MA calculation")
            return False
        
        try:
            # Calculate moving averages
            prices = historical_prices['close'] if 'close' in historical_prices else historical_prices['Close']
            ma_20 = prices.rolling(window=self.short_ma_period).mean()
            ma_50 = prices.rolling(window=self.long_ma_period).mean()
            
            # Check for crossover (20 SMA crosses above 50 SMA)
            # Today: 20 > 50, Yesterday: 20 <= 50
            if len(ma_20) >= 2 and len(ma_50) >= 2:
                current_20 = ma_20.iloc[-1]
                current_50 = ma_50.iloc[-1]
                prev_20 = ma_20.iloc[-2]
                prev_50 = ma_50.iloc[-2]
                
                crossover = (current_20 > current_50) and (prev_20 <= prev_50)
                
                if crossover:
                    logger.info(f"{symbol}: MA Golden Cross detected - "
                               f"20 SMA ({current_20:.2f}) crossed above 50 SMA ({current_50:.2f})")
                else:
                    logger.debug(f"{symbol}: No crossover - 20 SMA: {current_20:.2f}, 50 SMA: {current_50:.2f}")
                
                return crossover
            
        except Exception as e:
            logger.error(f"Error calculating MA crossover for {symbol}: {e}")
        
        return False
    
    def _construct_bull_call_spread_legs(self, symbol: str, current_price: float,
                                          options_chain: List[Dict]) -> List[Dict[str, Any]]:
        """
        Construct the 2 legs of a Bull Call Spread based on delta targeting.
        
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
                and opt.get('type') == 'call'
            ]
            
            if not target_options:
                return []
            
            # Find long call (40 delta, closer to ATM)
            long_call = self._find_option_by_delta(target_options, self.long_leg_delta)
            if not long_call:
                return []
            
            # Find short call (20 delta, further OTM)
            short_call = self._find_option_by_delta(target_options, self.short_leg_delta)
            if not short_call:
                return []
            
            # Ensure short call is higher strike than long call
            if short_call['strike'] <= long_call['strike']:
                logger.warning(f"{symbol}: Short call strike not higher than long call")
                return []
            
            # Construct legs (order: buy lower strike, sell higher strike)
            legs = [
                {
                    'type': 'call',
                    'action': 'buy',
                    'strike': long_call['strike'],
                    'delta': long_call.get('delta', self.long_leg_delta),
                    'premium': long_call.get('mark', 0)
                },
                {
                    'type': 'call',
                    'action': 'sell',
                    'strike': short_call['strike'],
                    'delta': short_call.get('delta', self.short_leg_delta),
                    'premium': short_call.get('mark', 0)
                }
            ]
            
            return legs
            
        except Exception as e:
            logger.error(f"Error constructing Bull Call Spread legs for {symbol}: {e}")
            return []
    
    def _find_option_by_delta(self, options: List[Dict], target_delta: float) -> Dict[str, Any]:
        """Find call option closest to target delta."""
        if not options:
            return None
        
        # For calls, delta should be positive
        target_delta = abs(target_delta)
        
        # Find option with delta closest to target
        best_option = min(
            options,
            key=lambda x: abs(x.get('delta', 0) - target_delta)
        )
        
        return best_option if best_option else None
    
    def _get_target_dte(self, options_chain: List[Dict]) -> int:
        """Get the target DTE from available options (middle of range)."""
        target_dte = (self.min_dte + self.max_dte) // 2
        return target_dte
    
    def _calculate_expected_debit(self, legs: List[Dict]) -> float:
        """
        Calculate total expected debit paid for Bull Call Spread.
        
        Debit = Long Call Premium - Short Call Premium
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
        Check if position should be exited based on P/L or trend reversal.
        
        Args:
            position: Dictionary containing position details
            current_market_data: Current market data including MAs
        
        Returns:
            Dictionary with exit decision
        """
        pnl_pct = position.get('pnl_pct', 0)
        symbol = position.get('symbol', '')
        
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
        
        # Check for trend reversal (Death Cross)
        if symbol in current_market_data:
            symbol_data = current_market_data[symbol]
            ma_20 = symbol_data.get('ma_20', 0)
            ma_50 = symbol_data.get('ma_50', 0)
            
            if ma_20 > 0 and ma_50 > 0 and ma_20 < ma_50:
                return {
                    'action': 'CLOSE',
                    'reason': f'Trend reversal (Death Cross): 20 SMA ({ma_20:.2f}) < 50 SMA ({ma_50:.2f})'
                }
        
        return {'action': 'HOLD', 'reason': None}


# Export strategy
__all__ = ['TrendFollowerStrategy']
