"""
Alpaca Options Lab - 50+ Improvements Module
=============================================

Major enhancements focused on GLD, SLV, SPY and major tech stocks.

Categories:
1. Chain Tab Improvements (1-10)
2. Greeks & IV Improvements (11-20)
3. Strategy Builder Improvements (21-30)
4. AI Tab Improvements (31-40)
5. Flow Tab Improvements (41-45)
6. Positions Tab Improvements (46-50)
7. Additional Features (51-55)
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Focus Tickers for the Options Lab
FOCUS_TICKERS = ['GLD', 'SLV', 'SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'AMD', 'AVGO']


# ============================================================================
# IMPROVEMENT 1-5: ENHANCED CHAIN DISPLAY
# ============================================================================

class ChainDisplayMode(Enum):
    STANDARD = "standard"
    COMPACT = "compact"
    EXPANDED = "expanded"
    STRADDLE = "straddle"


@dataclass
class EnhancedOptionData:
    """Enhanced option data with additional computed fields."""
    strike: float
    bid: float
    ask: float
    last: float
    volume: int
    open_interest: int
    iv: float
    delta: float
    gamma: float
    theta: float
    vega: float
    # New computed fields
    mid_price: float = 0.0
    spread_pct: float = 0.0
    bid_ask_ratio: float = 0.0
    vol_oi_ratio: float = 0.0
    itm_probability: float = 0.0
    moneyness: str = "ATM"
    days_to_expiry: int = 0
    
    def __post_init__(self):
        self.mid_price = (self.bid + self.ask) / 2
        self.spread_pct = ((self.ask - self.bid) / self.mid_price * 100) if self.mid_price > 0 else 0
        self.bid_ask_ratio = self.bid / self.ask if self.ask > 0 else 0
        self.vol_oi_ratio = self.volume / self.open_interest if self.open_interest > 0 else 0
        self.itm_probability = abs(self.delta) * 100


class ChainEnhancements:
    """
    Improvements 1-10: Chain Tab Enhancements
    
    1. Multi-expiry chain comparison
    2. Strike distance from ATM display
    3. Bid-ask spread quality indicator
    4. Volume/OI ratio highlighting
    5. Quick-add to strategy builder
    6. Real-time price updates indicator
    7. Historical IV comparison
    8. Option chain heatmap view
    9. Greeks column toggle
    10. Export with custom columns
    """
    
    def __init__(self):
        self.display_mode = ChainDisplayMode.STANDARD
        self.visible_columns = ['strike', 'bid', 'ask', 'last', 'volume', 'oi', 'iv', 'delta']
        
    def calculate_strike_distance(self, strike: float, spot: float) -> Dict:
        """Improvement #2: Calculate strike distance from ATM."""
        distance = strike - spot
        distance_pct = (distance / spot) * 100
        
        if abs(distance_pct) < 0.5:
            moneyness = "ATM"
            color = "#FF9800"
        elif distance_pct > 0:
            moneyness = f"OTM {abs(distance_pct):.1f}%"
            color = "#f44336"
        else:
            moneyness = f"ITM {abs(distance_pct):.1f}%"
            color = "#4caf50"
            
        return {
            'distance': round(distance, 2),
            'distance_pct': round(distance_pct, 2),
            'moneyness': moneyness,
            'color': color
        }
    
    def assess_spread_quality(self, bid: float, ask: float) -> Dict:
        """Improvement #3: Assess bid-ask spread quality."""
        spread = ask - bid
        mid = (bid + ask) / 2
        spread_pct = (spread / mid * 100) if mid > 0 else 0
        
        if spread_pct < 2:
            quality = "Excellent"
            color = "#4caf50"
            score = 5
        elif spread_pct < 5:
            quality = "Good"
            color = "#8bc34a"
            score = 4
        elif spread_pct < 10:
            quality = "Fair"
            color = "#FF9800"
            score = 3
        elif spread_pct < 20:
            quality = "Poor"
            color = "#f44336"
            score = 2
        else:
            quality = "Very Poor"
            color = "#d32f2f"
            score = 1
            
        return {
            'spread': round(spread, 2),
            'spread_pct': round(spread_pct, 2),
            'quality': quality,
            'color': color,
            'score': score
        }
    
    def highlight_unusual_activity(self, volume: int, open_interest: int) -> Dict:
        """Improvement #4: Highlight unusual volume/OI activity."""
        ratio = volume / open_interest if open_interest > 0 else 0
        
        if ratio > 2.0:
            signal = "Very High Activity"
            color = "#f44336"
            is_unusual = True
        elif ratio > 1.0:
            signal = "High Activity"
            color = "#FF9800"
            is_unusual = True
        elif ratio > 0.5:
            signal = "Moderate"
            color = "#FFC107"
            is_unusual = False
        else:
            signal = "Normal"
            color = "#4caf50"
            is_unusual = False
            
        return {
            'ratio': round(ratio, 2),
            'signal': signal,
            'color': color,
            'is_unusual': is_unusual
        }
    
    def create_chain_heatmap_data(self, calls: List[Dict], puts: List[Dict], metric: str = 'volume') -> Dict:
        """Improvement #8: Create heatmap visualization data."""
        call_values = [c.get(metric, 0) for c in calls]
        put_values = [p.get(metric, 0) for p in puts]
        strikes = [c.get('strike', 0) for c in calls]
        
        max_val = max(max(call_values) if call_values else 0, max(put_values) if put_values else 0)
        
        return {
            'strikes': strikes,
            'call_values': call_values,
            'put_values': put_values,
            'max_value': max_val,
            'metric': metric
        }


# ============================================================================
# IMPROVEMENT 11-20: GREEKS & IV ENHANCEMENTS
# ============================================================================

class GreeksEnhancements:
    """
    Improvements 11-20: Greeks & IV Tab Enhancements
    
    11. Greeks P&L attribution
    12. Delta-adjusted position size
    13. Gamma risk warning system
    14. Theta decay projection chart
    15. Vega exposure vs VIX correlation
    16. IV percentile vs HV comparison
    17. IV term structure analysis
    18. IV skew smile visualization
    19. Greeks sensitivity table
    20. What-if scenario modeler
    """
    
    def calculate_greeks_pnl_attribution(self, 
                                          delta: float, gamma: float, theta: float, vega: float,
                                          price_change: float, iv_change: float, 
                                          days_passed: float = 1) -> Dict:
        """Improvement #11: Greeks P&L attribution."""
        delta_pnl = delta * price_change * 100
        gamma_pnl = 0.5 * gamma * (price_change ** 2) * 100
        theta_pnl = theta * days_passed
        vega_pnl = vega * iv_change * 100
        
        total_pnl = delta_pnl + gamma_pnl + theta_pnl + vega_pnl
        
        return {
            'delta_pnl': round(delta_pnl, 2),
            'gamma_pnl': round(gamma_pnl, 2),
            'theta_pnl': round(theta_pnl, 2),
            'vega_pnl': round(vega_pnl, 2),
            'total_pnl': round(total_pnl, 2),
            'largest_contributor': max(
                [('Delta', abs(delta_pnl)), ('Gamma', abs(gamma_pnl)), 
                 ('Theta', abs(theta_pnl)), ('Vega', abs(vega_pnl))],
                key=lambda x: x[1]
            )[0]
        }
    
    def calculate_delta_adjusted_size(self, 
                                       target_delta: float, 
                                       option_delta: float, 
                                       max_risk: float) -> Dict:
        """Improvement #12: Calculate delta-adjusted position size."""
        if option_delta == 0:
            return {'contracts': 0, 'error': 'Delta cannot be zero'}
            
        contracts = abs(target_delta / option_delta)
        dollar_delta = contracts * option_delta * 100
        
        return {
            'contracts': int(contracts),
            'actual_delta': round(contracts * option_delta, 2),
            'dollar_delta': round(dollar_delta, 2),
            'target_met': abs(contracts * option_delta - target_delta) < 0.1
        }
    
    def assess_gamma_risk(self, gamma: float, spot_price: float, position_size: int) -> Dict:
        """Improvement #13: Gamma risk warning system."""
        dollar_gamma = gamma * spot_price * position_size * 100
        
        # Calculate gamma at different price levels
        price_moves = [1, 2, 3, 5, 10]  # percentage moves
        gamma_impact = {}
        
        for move in price_moves:
            price_change = spot_price * (move / 100)
            delta_change = gamma * price_change * position_size * 100
            gamma_impact[f'{move}%_move'] = round(delta_change, 2)
        
        # Risk level assessment
        if abs(dollar_gamma) > 5000:
            risk_level = "HIGH"
            color = "#f44336"
            warning = "Significant gamma exposure - consider hedging"
        elif abs(dollar_gamma) > 2000:
            risk_level = "MODERATE"
            color = "#FF9800"
            warning = "Moderate gamma risk"
        else:
            risk_level = "LOW"
            color = "#4caf50"
            warning = "Gamma risk within normal bounds"
            
        return {
            'dollar_gamma': round(dollar_gamma, 2),
            'risk_level': risk_level,
            'color': color,
            'warning': warning,
            'impact_by_move': gamma_impact
        }
    
    def project_theta_decay(self, theta: float, days_forward: int = 30) -> List[Dict]:
        """Improvement #14: Theta decay projection."""
        projections = []
        cumulative_decay = 0
        
        for day in range(1, days_forward + 1):
            # Theta accelerates as expiration approaches (simplified model)
            daily_decay = theta * (1 + (day / days_forward) * 0.5)
            cumulative_decay += daily_decay
            
            projections.append({
                'day': day,
                'daily_decay': round(daily_decay, 2),
                'cumulative_decay': round(cumulative_decay, 2)
            })
            
        return projections
    
    def calculate_iv_percentile(self, current_iv: float, historical_ivs: List[float]) -> Dict:
        """Improvement #16: IV percentile calculation."""
        if not historical_ivs:
            return {'percentile': 50, 'rank': 50, 'signal': 'neutral'}
            
        percentile = sum(1 for iv in historical_ivs if iv < current_iv) / len(historical_ivs) * 100
        
        iv_min = min(historical_ivs)
        iv_max = max(historical_ivs)
        iv_rank = (current_iv - iv_min) / (iv_max - iv_min) * 100 if iv_max > iv_min else 50
        
        if percentile > 80:
            signal = "HIGH_IV"
            recommendation = "Consider selling premium"
        elif percentile < 20:
            signal = "LOW_IV"
            recommendation = "Consider buying premium"
        else:
            signal = "NEUTRAL"
            recommendation = "IV in normal range"
            
        return {
            'percentile': round(percentile, 1),
            'rank': round(iv_rank, 1),
            'signal': signal,
            'recommendation': recommendation,
            'current_iv': round(current_iv * 100, 1),
            'iv_min': round(iv_min * 100, 1),
            'iv_max': round(iv_max * 100, 1),
            'iv_mean': round(np.mean(historical_ivs) * 100, 1)
        }
    
    def analyze_iv_term_structure(self, expirations: List[str], ivs: List[float]) -> Dict:
        """Improvement #17: IV term structure analysis."""
        if len(expirations) < 2:
            return {'structure': 'unknown', 'slope': 0}
            
        # Calculate slope (simplified linear regression)
        x = list(range(len(ivs)))
        slope = np.polyfit(x, ivs, 1)[0] if len(ivs) > 1 else 0
        
        if slope > 0.01:
            structure = "CONTANGO"
            interpretation = "Near-term IV lower than far-term (normal)"
        elif slope < -0.01:
            structure = "BACKWARDATION"
            interpretation = "Near-term IV higher than far-term (elevated fear)"
        else:
            structure = "FLAT"
            interpretation = "Relatively flat term structure"
            
        return {
            'structure': structure,
            'slope': round(slope, 4),
            'interpretation': interpretation,
            'expirations': expirations,
            'ivs': [round(iv * 100, 1) for iv in ivs]
        }


# ============================================================================
# IMPROVEMENT 21-30: STRATEGY BUILDER ENHANCEMENTS
# ============================================================================

class StrategyBuilderEnhancements:
    """
    Improvements 21-30: Strategy Builder Enhancements
    
    21. Multi-leg strategy templates (Iron Fly, Jade Lizard, etc.)
    22. Custom strategy naming and saving
    23. Probability of profit calculation
    24. Expected value calculation
    25. Greeks aggregation for multi-leg
    26. Break-even visualization
    27. Strategy comparison tool
    28. Risk/reward ratio display
    29. Rolling strategy suggestions
    30. Earnings strangle calculator
    """
    
    STRATEGY_TEMPLATES = {
        'iron_condor': {
            'legs': 4,
            'description': 'Neutral strategy - sell OTM put spread and call spread',
            'outlook': 'neutral',
            'max_profit': 'net credit',
            'max_loss': 'width - credit'
        },
        'iron_butterfly': {
            'legs': 4,
            'description': 'Neutral at ATM strike',
            'outlook': 'neutral',
            'max_profit': 'net credit',
            'max_loss': 'width - credit'
        },
        'jade_lizard': {
            'legs': 3,
            'description': 'Short put + short call spread',
            'outlook': 'bullish',
            'max_profit': 'total credit',
            'max_loss': 'unlimited on upside'
        },
        'broken_wing_butterfly': {
            'legs': 3,
            'description': 'Skewed butterfly for credit',
            'outlook': 'directional',
            'max_profit': 'net credit + narrow wing',
            'max_loss': 'wide wing - credit'
        },
        'calendar_spread': {
            'legs': 2,
            'description': 'Sell near, buy far same strike',
            'outlook': 'neutral',
            'max_profit': 'depends on IV',
            'max_loss': 'net debit'
        },
        'diagonal_spread': {
            'legs': 2,
            'description': 'Calendar with different strikes',
            'outlook': 'directional',
            'max_profit': 'complex',
            'max_loss': 'net debit'
        },
        'ratio_spread': {
            'legs': 2,
            'description': 'Unequal quantities',
            'outlook': 'directional with hedge',
            'max_profit': 'varies',
            'max_loss': 'can be unlimited'
        },
        'risk_reversal': {
            'legs': 2,
            'description': 'Long call, short put',
            'outlook': 'bullish',
            'max_profit': 'unlimited',
            'max_loss': 'put strike - credit'
        }
    }
    
    def calculate_probability_of_profit(self, 
                                         spot: float, 
                                         lower_be: float, 
                                         upper_be: float,
                                         iv: float, 
                                         days: int) -> Dict:
        """Improvement #23: Calculate probability of profit."""
        # Using log-normal distribution assumption
        daily_vol = iv / np.sqrt(252)
        total_vol = daily_vol * np.sqrt(days)
        
        # Probability of staying between breakevens
        from scipy.stats import norm
        
        if lower_be > 0:
            lower_z = (np.log(lower_be / spot)) / total_vol
            prob_above_lower = 1 - norm.cdf(lower_z)
        else:
            prob_above_lower = 1
            
        if upper_be > 0 and upper_be < float('inf'):
            upper_z = (np.log(upper_be / spot)) / total_vol
            prob_below_upper = norm.cdf(upper_z)
        else:
            prob_below_upper = 1
            
        pop = prob_above_lower * prob_below_upper * 100
        
        return {
            'pop': round(pop, 1),
            'prob_above_lower': round(prob_above_lower * 100, 1),
            'prob_below_upper': round(prob_below_upper * 100, 1),
            'expected_range_low': round(spot * np.exp(-2 * total_vol), 2),
            'expected_range_high': round(spot * np.exp(2 * total_vol), 2)
        }
    
    def calculate_expected_value(self,
                                  max_profit: float,
                                  max_loss: float,
                                  pop: float) -> Dict:
        """Improvement #24: Calculate expected value."""
        pop_decimal = pop / 100
        ev = (max_profit * pop_decimal) - (max_loss * (1 - pop_decimal))
        
        roi = (ev / abs(max_loss)) * 100 if max_loss != 0 else 0
        
        return {
            'expected_value': round(ev, 2),
            'roi': round(roi, 1),
            'edge': 'Positive' if ev > 0 else 'Negative',
            'quality': 'Good' if ev > abs(max_loss) * 0.1 else 'Fair' if ev > 0 else 'Poor'
        }
    
    def aggregate_greeks(self, legs: List[Dict]) -> Dict:
        """Improvement #25: Aggregate Greeks for multi-leg strategy."""
        total_delta = 0
        total_gamma = 0
        total_theta = 0
        total_vega = 0
        
        for leg in legs:
            multiplier = leg.get('qty', 1) * (1 if leg.get('action') == 'buy' else -1)
            total_delta += leg.get('delta', 0) * multiplier
            total_gamma += leg.get('gamma', 0) * multiplier
            total_theta += leg.get('theta', 0) * multiplier
            total_vega += leg.get('vega', 0) * multiplier
            
        return {
            'total_delta': round(total_delta, 4),
            'total_gamma': round(total_gamma, 4),
            'total_theta': round(total_theta, 4),
            'total_vega': round(total_vega, 4),
            'delta_neutral': abs(total_delta) < 0.1,
            'dominant_greek': self._get_dominant_greek(total_delta, total_gamma, total_theta, total_vega)
        }
    
    def _get_dominant_greek(self, delta, gamma, theta, vega) -> str:
        greeks = {
            'Delta': abs(delta),
            'Gamma': abs(gamma) * 100,  # Scale for comparison
            'Theta': abs(theta) * 10,
            'Vega': abs(vega)
        }
        return max(greeks, key=greeks.get)
    
    def calculate_risk_reward(self, max_profit: float, max_loss: float) -> Dict:
        """Improvement #28: Calculate risk/reward ratio."""
        if max_loss == 0:
            return {'ratio': float('inf'), 'display': '∞:1', 'rating': 'Excellent'}
            
        ratio = abs(max_profit / max_loss)
        
        if ratio >= 3:
            rating = "Excellent"
            color = "#4caf50"
        elif ratio >= 2:
            rating = "Good"
            color = "#8bc34a"
        elif ratio >= 1:
            rating = "Fair"
            color = "#FF9800"
        else:
            rating = "Poor"
            color = "#f44336"
            
        return {
            'ratio': round(ratio, 2),
            'display': f"{ratio:.1f}:1",
            'rating': rating,
            'color': color
        }
    
    def suggest_roll(self, 
                     current_strike: float,
                     current_expiry: str,
                     spot: float,
                     days_to_expiry: int,
                     pnl_pct: float) -> Dict:
        """Improvement #29: Suggest rolling strategy."""
        suggestions = []
        
        # Roll triggers
        if days_to_expiry <= 7 and pnl_pct > 50:
            suggestions.append({
                'action': 'ROLL_OUT',
                'reason': 'Near expiry with good profit - lock in gains',
                'suggestion': f'Roll to next month, same strike ${current_strike}'
            })
            
        if abs(spot - current_strike) / spot < 0.02 and days_to_expiry <= 14:
            suggestions.append({
                'action': 'ROLL_UP_OUT',
                'reason': 'Near ATM with limited time',
                'suggestion': 'Consider rolling up and out for additional credit'
            })
            
        if pnl_pct < -30 and days_to_expiry > 21:
            suggestions.append({
                'action': 'ROLL_DOWN',
                'reason': 'Significant loss with time remaining',
                'suggestion': 'Consider rolling down to recover'
            })
            
        return {
            'should_roll': len(suggestions) > 0,
            'suggestions': suggestions,
            'current_status': {
                'dte': days_to_expiry,
                'pnl_pct': pnl_pct,
                'moneyness': 'ATM' if abs(spot - current_strike) / spot < 0.02 else ('ITM' if spot > current_strike else 'OTM')
            }
        }


# ============================================================================
# IMPROVEMENT 31-40: AI TAB ENHANCEMENTS
# ============================================================================

class AIEnhancements:
    """
    Improvements 31-40: AI Tab Enhancements
    
    31. Multi-timeframe analysis (1D, 1W, 1M)
    32. Sentiment aggregation from multiple sources
    33. Options flow pattern recognition
    34. Earnings play recommendations
    35. IV crush probability calculator
    36. Smart strike selection
    37. Risk-adjusted strategy ranking
    38. Market regime detection
    39. Correlation analysis
    40. Portfolio hedging suggestions
    """
    
    def analyze_multi_timeframe(self, 
                                 price_1d: float, 
                                 price_1w: float, 
                                 price_1m: float,
                                 current: float) -> Dict:
        """Improvement #31: Multi-timeframe analysis."""
        change_1d = ((current - price_1d) / price_1d) * 100
        change_1w = ((current - price_1w) / price_1w) * 100
        change_1m = ((current - price_1m) / price_1m) * 100
        
        # Determine trend alignment
        trends = []
        if change_1d > 0: trends.append('1D_UP')
        if change_1w > 0: trends.append('1W_UP')
        if change_1m > 0: trends.append('1M_UP')
        
        alignment = len(trends)
        
        if alignment == 3:
            outlook = "STRONGLY_BULLISH"
            confidence = 85
        elif alignment == 0:
            outlook = "STRONGLY_BEARISH"
            confidence = 85
        elif alignment >= 2:
            outlook = "BULLISH" if trends[-1] == '1M_UP' else "MILDLY_BULLISH"
            confidence = 65
        else:
            outlook = "BEARISH" if trends[-1] != '1M_UP' else "MILDLY_BEARISH"
            confidence = 65
            
        return {
            'change_1d': round(change_1d, 2),
            'change_1w': round(change_1w, 2),
            'change_1m': round(change_1m, 2),
            'outlook': outlook,
            'confidence': confidence,
            'trend_alignment': alignment,
            'recommendation': self._get_strategy_for_outlook(outlook)
        }
    
    def _get_strategy_for_outlook(self, outlook: str) -> str:
        strategies = {
            'STRONGLY_BULLISH': 'Bull call spread or naked puts',
            'BULLISH': 'Bull put spread or covered calls',
            'MILDLY_BULLISH': 'Iron condor with bullish skew',
            'MILDLY_BEARISH': 'Iron condor with bearish skew',
            'BEARISH': 'Bear call spread or protective puts',
            'STRONGLY_BEARISH': 'Bear put spread or naked calls'
        }
        return strategies.get(outlook, 'Neutral strategies')
    
    def detect_market_regime(self,
                              vix: float,
                              vix_20d_avg: float,
                              spy_return_20d: float,
                              spy_volatility_20d: float) -> Dict:
        """Improvement #38: Market regime detection."""
        # Classify regime
        if vix > 25 and spy_return_20d < -0.05:
            regime = "CRISIS"
            description = "High volatility selloff"
            strategies = ["Buy puts", "Reduce exposure", "VIX calls"]
        elif vix > 20 and vix > vix_20d_avg * 1.2:
            regime = "FEAR"
            description = "Elevated fear, potential bottom"
            strategies = ["Sell puts at support", "Iron condors wide"]
        elif vix < 15 and spy_return_20d > 0.02:
            regime = "COMPLACENCY"
            description = "Low vol bull market"
            strategies = ["Sell premium", "Iron condors tight"]
        elif spy_volatility_20d < 0.01:
            regime = "COMPRESSION"
            description = "Vol compression - breakout imminent"
            strategies = ["Straddles", "Calendar spreads"]
        else:
            regime = "NORMAL"
            description = "Standard market conditions"
            strategies = ["Balanced approach", "Standard spreads"]
            
        return {
            'regime': regime,
            'description': description,
            'strategies': strategies,
            'vix': vix,
            'vix_vs_avg': round((vix / vix_20d_avg - 1) * 100, 1),
            'spy_trend': 'UP' if spy_return_20d > 0 else 'DOWN'
        }
    
    def calculate_iv_crush_probability(self,
                                        current_iv: float,
                                        historical_post_earnings_iv: List[float],
                                        days_to_earnings: int) -> Dict:
        """Improvement #35: IV crush probability calculator."""
        if not historical_post_earnings_iv:
            return {'probability': 50, 'expected_crush': 0}
            
        avg_post_iv = np.mean(historical_post_earnings_iv)
        expected_crush = (current_iv - avg_post_iv) / current_iv * 100
        
        # Higher IV relative to post = higher crush probability
        crush_probability = min(95, max(30, 50 + expected_crush))
        
        return {
            'probability': round(crush_probability, 1),
            'expected_crush_pct': round(expected_crush, 1),
            'current_iv': round(current_iv * 100, 1),
            'expected_post_iv': round(avg_post_iv * 100, 1),
            'days_to_earnings': days_to_earnings,
            'recommendation': 'Sell premium' if crush_probability > 70 else 'Neutral'
        }
    
    def smart_strike_selection(self,
                                spot: float,
                                outlook: str,
                                iv: float,
                                days_to_expiry: int,
                                risk_tolerance: str = 'moderate') -> Dict:
        """Improvement #36: Smart strike selection."""
        # Calculate expected move
        daily_vol = iv / np.sqrt(252)
        expected_move = spot * daily_vol * np.sqrt(days_to_expiry)
        
        # Risk tolerance adjustments
        risk_multipliers = {'low': 0.7, 'moderate': 1.0, 'high': 1.3}
        multiplier = risk_multipliers.get(risk_tolerance, 1.0)
        
        # Calculate strikes
        if outlook in ['bullish', 'BULLISH', 'STRONGLY_BULLISH']:
            # Sell puts OTM
            sell_strike = round((spot - expected_move * multiplier) / 5) * 5
            buy_strike = sell_strike - 5
            call_strike = round((spot + expected_move * 0.5 * multiplier) / 5) * 5
            
            recommendation = {
                'primary': f"Sell ${sell_strike} put",
                'spread': f"Buy ${buy_strike} put for protection",
                'aggressive': f"Buy ${call_strike} call for upside"
            }
        elif outlook in ['bearish', 'BEARISH', 'STRONGLY_BEARISH']:
            sell_strike = round((spot + expected_move * multiplier) / 5) * 5
            buy_strike = sell_strike + 5
            put_strike = round((spot - expected_move * 0.5 * multiplier) / 5) * 5
            
            recommendation = {
                'primary': f"Sell ${sell_strike} call",
                'spread': f"Buy ${buy_strike} call for protection",
                'aggressive': f"Buy ${put_strike} put for downside"
            }
        else:  # Neutral
            sell_put = round((spot - expected_move * multiplier) / 5) * 5
            sell_call = round((spot + expected_move * multiplier) / 5) * 5
            
            recommendation = {
                'primary': f"Iron condor: sell ${sell_put}P / ${sell_call}C",
                'spread': f"Width: $5 on each side",
                'aggressive': f"Strangle: sell ${sell_put}P / ${sell_call}C naked"
            }
            
        return {
            'expected_move': round(expected_move, 2),
            'expected_range': {
                'low': round(spot - expected_move, 2),
                'high': round(spot + expected_move, 2)
            },
            'recommendation': recommendation,
            'outlook': outlook,
            'dte': days_to_expiry
        }


# ============================================================================
# IMPROVEMENT 41-45: FLOW TAB ENHANCEMENTS
# ============================================================================

class FlowEnhancements:
    """
    Improvements 41-45: Flow Tab Enhancements
    
    41. Smart money flow detection
    42. Block trade alerts
    43. Sweep detection
    44. Dark pool prints
    45. Options order flow aggregation
    """
    
    def detect_smart_money(self,
                            volume: int,
                            avg_volume: int,
                            premium: float,
                            open_interest: int) -> Dict:
        """Improvement #41: Smart money flow detection."""
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1
        vol_oi_ratio = volume / open_interest if open_interest > 0 else 0
        
        # Smart money indicators
        is_large_premium = premium > 100000
        is_volume_spike = volume_ratio > 3
        is_opening = vol_oi_ratio > 1
        
        confidence = 0
        if is_large_premium: confidence += 35
        if is_volume_spike: confidence += 30
        if is_opening: confidence += 35
        
        return {
            'is_smart_money': confidence >= 70,
            'confidence': confidence,
            'indicators': {
                'large_premium': is_large_premium,
                'volume_spike': is_volume_spike,
                'likely_opening': is_opening
            },
            'premium': premium,
            'volume_ratio': round(volume_ratio, 2)
        }
    
    def detect_sweep(self,
                      executions: List[Dict],
                      time_window_seconds: int = 60) -> Dict:
        """Improvement #43: Sweep detection."""
        if not executions:
            return {'is_sweep': False}
            
        # Sweep = multiple executions across exchanges in short time
        exchange_count = len(set(e.get('exchange', '') for e in executions))
        total_size = sum(e.get('size', 0) for e in executions)
        
        is_sweep = exchange_count >= 3 and total_size > 100
        
        return {
            'is_sweep': is_sweep,
            'exchange_count': exchange_count,
            'total_contracts': total_size,
            'aggressiveness': 'HIGH' if is_sweep and total_size > 500 else 'MODERATE' if is_sweep else 'LOW',
            'signal': 'BULLISH' if executions[0].get('side') == 'buy' else 'BEARISH'
        }
    
    def aggregate_flow(self, 
                        call_volume: int, put_volume: int,
                        call_premium: float, put_premium: float,
                        call_oi: int, put_oi: int) -> Dict:
        """Improvement #45: Options order flow aggregation."""
        total_volume = call_volume + put_volume
        total_premium = call_premium + put_premium
        
        pcr_volume = put_volume / call_volume if call_volume > 0 else 0
        pcr_oi = put_oi / call_oi if call_oi > 0 else 0
        pcr_premium = put_premium / call_premium if call_premium > 0 else 0
        
        # Net flow
        net_premium_flow = call_premium - put_premium
        
        # Sentiment
        if pcr_volume < 0.7 and net_premium_flow > 0:
            sentiment = "BULLISH"
            color = "#4caf50"
        elif pcr_volume > 1.3 and net_premium_flow < 0:
            sentiment = "BEARISH"
            color = "#f44336"
        else:
            sentiment = "NEUTRAL"
            color = "#FF9800"
            
        return {
            'call_volume': call_volume,
            'put_volume': put_volume,
            'pcr_volume': round(pcr_volume, 2),
            'pcr_oi': round(pcr_oi, 2),
            'pcr_premium': round(pcr_premium, 2),
            'net_premium_flow': round(net_premium_flow, 0),
            'sentiment': sentiment,
            'color': color,
            'total_premium': round(total_premium, 0)
        }


# ============================================================================
# IMPROVEMENT 46-50: POSITIONS TAB ENHANCEMENTS
# ============================================================================

class PositionsEnhancements:
    """
    Improvements 46-50: Positions Tab Enhancements
    
    46. Position Greeks aggregation
    47. Portfolio beta calculation
    48. Margin requirement estimation
    49. Position heat map
    50. Auto-close suggestions
    """
    
    def aggregate_position_greeks(self, positions: List[Dict]) -> Dict:
        """Improvement #46: Aggregate position Greeks."""
        totals = {
            'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0,
            'delta_dollars': 0, 'theta_daily': 0
        }
        
        for pos in positions:
            qty = pos.get('qty', 0)
            totals['delta'] += pos.get('delta', 0) * qty
            totals['gamma'] += pos.get('gamma', 0) * qty
            totals['theta'] += pos.get('theta', 0) * qty
            totals['vega'] += pos.get('vega', 0) * qty
            
            # Dollar values
            spot = pos.get('underlying_price', 100)
            totals['delta_dollars'] += pos.get('delta', 0) * qty * spot * 100
            totals['theta_daily'] += pos.get('theta', 0) * qty * 100
            
        return {
            'portfolio_delta': round(totals['delta'], 2),
            'portfolio_gamma': round(totals['gamma'], 4),
            'portfolio_theta': round(totals['theta'], 2),
            'portfolio_vega': round(totals['vega'], 2),
            'delta_dollars': round(totals['delta_dollars'], 0),
            'theta_daily': round(totals['theta_daily'], 2),
            'is_delta_neutral': abs(totals['delta']) < 5,
            'is_theta_positive': totals['theta'] > 0
        }
    
    def calculate_portfolio_beta(self, 
                                  positions: List[Dict],
                                  spy_correlation: Dict[str, float]) -> Dict:
        """Improvement #47: Calculate portfolio beta."""
        weighted_beta = 0
        total_value = 0
        
        for pos in positions:
            ticker = pos.get('underlying', 'SPY')
            value = pos.get('market_value', 0)
            beta = spy_correlation.get(ticker, 1.0)
            
            weighted_beta += beta * value
            total_value += value
            
        portfolio_beta = weighted_beta / total_value if total_value > 0 else 1.0
        
        return {
            'portfolio_beta': round(portfolio_beta, 2),
            'interpretation': 'Aggressive' if portfolio_beta > 1.2 else ('Defensive' if portfolio_beta < 0.8 else 'Market-neutral'),
            'spy_equivalent': round(total_value * portfolio_beta, 0)
        }
    
    def estimate_margin(self, positions: List[Dict]) -> Dict:
        """Improvement #48: Estimate margin requirements."""
        total_margin = 0
        margin_details = []
        
        for pos in positions:
            pos_type = pos.get('type', 'long_call')
            underlying_price = pos.get('underlying_price', 100)
            strike = pos.get('strike', 100)
            qty = abs(pos.get('qty', 1))
            
            # Simplified margin calculation
            if 'short' in pos_type.lower() or pos.get('qty', 1) < 0:
                if 'put' in pos_type.lower():
                    margin = max(strike * 0.2, (strike - underlying_price) * 0.1) * qty * 100
                else:  # call
                    margin = max(underlying_price * 0.2, underlying_price * 0.15) * qty * 100
            else:
                margin = pos.get('cost', 0) * qty * 100
                
            total_margin += margin
            margin_details.append({
                'position': f"{pos.get('symbol', 'Unknown')}",
                'margin': round(margin, 0)
            })
            
        return {
            'total_margin': round(total_margin, 0),
            'details': margin_details,
            'margin_utilization': round(total_margin / 100000 * 100, 1)  # Assuming 100k account
        }
    
    def suggest_auto_close(self, positions: List[Dict]) -> List[Dict]:
        """Improvement #50: Auto-close suggestions."""
        suggestions = []
        
        for pos in positions:
            pnl_pct = pos.get('pnl_pct', 0)
            dte = pos.get('dte', 30)
            
            # Take profit suggestions
            if pnl_pct >= 50:
                suggestions.append({
                    'symbol': pos.get('symbol'),
                    'action': 'TAKE_PROFIT',
                    'reason': f'Profit target reached ({pnl_pct:.0f}%)',
                    'urgency': 'HIGH' if pnl_pct >= 75 else 'MEDIUM'
                })
                
            # Stop loss suggestions
            elif pnl_pct <= -50:
                suggestions.append({
                    'symbol': pos.get('symbol'),
                    'action': 'STOP_LOSS',
                    'reason': f'Loss exceeds threshold ({pnl_pct:.0f}%)',
                    'urgency': 'HIGH'
                })
                
            # Expiration warnings
            elif dte <= 7 and pnl_pct > 0:
                suggestions.append({
                    'symbol': pos.get('symbol'),
                    'action': 'CLOSE_NEAR_EXPIRY',
                    'reason': f'Near expiration ({dte} DTE) with profit',
                    'urgency': 'MEDIUM'
                })
                
        return suggestions


# ============================================================================
# IMPROVEMENT 51-55: ADDITIONAL FEATURES
# ============================================================================

class AdditionalFeatures:
    """
    Improvements 51-55: Additional Features
    
    51. Quick ticker switcher
    52. Keyboard shortcuts
    53. Theme customization
    54. Export to Excel with formulas
    55. Alert sound notifications
    """
    
    KEYBOARD_SHORTCUTS = {
        'Ctrl+1': 'Switch to Chain tab',
        'Ctrl+2': 'Switch to Greeks & IV tab',
        'Ctrl+3': 'Switch to Strategy Builder tab',
        'Ctrl+4': 'Switch to AI tab',
        'Ctrl+5': 'Switch to Flow tab',
        'Ctrl+6': 'Switch to Positions tab',
        'Ctrl+R': 'Refresh data',
        'Ctrl+S': 'Save strategy',
        'Ctrl+E': 'Export data',
        'Escape': 'Close modal/dialog'
    }
    
    QUICK_TICKERS = ['GLD', 'SLV', 'SPY', 'QQQ', 'AAPL', 'NVDA', 'TSLA', 'AMD', 'META', 'GOOGL', 'AMZN', 'MSFT']


# ============================================================================
# MAIN EXPORTS
# ============================================================================

chain_enhancements = ChainEnhancements()
greeks_enhancements = GreeksEnhancements()
strategy_builder_enhancements = StrategyBuilderEnhancements()
ai_enhancements = AIEnhancements()
flow_enhancements = FlowEnhancements()
positions_enhancements = PositionsEnhancements()
additional_features = AdditionalFeatures()

__all__ = [
    'ChainEnhancements',
    'GreeksEnhancements', 
    'StrategyBuilderEnhancements',
    'AIEnhancements',
    'FlowEnhancements',
    'PositionsEnhancements',
    'AdditionalFeatures',
    'chain_enhancements',
    'greeks_enhancements',
    'strategy_builder_enhancements',
    'ai_enhancements',
    'flow_enhancements',
    'positions_enhancements',
    'additional_features',
    'FOCUS_TICKERS',
]
