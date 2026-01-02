"""
Iron Condor Auto-Builder Engine

Phase 3: Options Strategy & Analysis
- Item 185: Iron Condor auto-builder with width based on Expected Move
- Item 184: Strategy picker presets (neutral/bull/bear/high IV/low IV)
- Item 176: Max pain calculator per expiry

Author: Phase 3 Options Strategy Implementation
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


# =============================================================================
# EXPECTED MOVE (EM) CALCULATOR
# =============================================================================

class ExpectedMoveCalculator:
    """Calculate Expected Move (EM) for options pricing."""
    
    @staticmethod
    def calculate_em(
        stock_price: float,
        iv: float,  # Annualized IV as decimal (e.g., 0.30 for 30%)
        days_to_expiry: int
    ) -> float:
        """
        Calculate Expected Move using Black-Scholes-based formula.
        
        EM = Stock Price × IV × √(DTE / 365)
        
        Args:
            stock_price: Current stock price
            iv: Implied volatility (annualized, as decimal)
            days_to_expiry: Days to expiration
            
        Returns:
            Expected move in dollars
        """
        if days_to_expiry <= 0:
            return 0.0
        return stock_price * iv * math.sqrt(days_to_expiry / 365)
    
    @staticmethod
    def calculate_em_from_straddle(
        atm_call_price: float,
        atm_put_price: float
    ) -> float:
        """
        Calculate Expected Move from ATM straddle price.
        
        EM ≈ (ATM Call + ATM Put) × 0.85
        
        This is the market's implied expected move.
        """
        return (atm_call_price + atm_put_price) * 0.85
    
    @staticmethod
    def get_1sd_range(
        stock_price: float,
        em: float
    ) -> Tuple[float, float]:
        """Get 1 standard deviation price range (~68% probability)."""
        return (stock_price - em, stock_price + em)
    
    @staticmethod
    def get_2sd_range(
        stock_price: float,
        em: float
    ) -> Tuple[float, float]:
        """Get 2 standard deviation price range (~95% probability)."""
        return (stock_price - 2 * em, stock_price + 2 * em)


# =============================================================================
# IRON CONDOR AUTO-BUILDER
# =============================================================================

class IronCondorBuilder:
    """
    Auto-build Iron Condor spreads based on Expected Move.
    
    An Iron Condor consists of:
    - Short OTM Put (below EM range)
    - Long OTM Put (wing protection)
    - Short OTM Call (above EM range)
    - Long OTM Call (wing protection)
    """
    
    def __init__(self):
        self.em_calculator = ExpectedMoveCalculator()
    
    def build_iron_condor(
        self,
        stock_price: float,
        iv: float,
        days_to_expiry: int,
        wing_width: float = 5.0,  # Width of each wing in dollars
        sd_multiplier: float = 1.0,  # 1.0 = 1SD (~68% POP), 2.0 = 2SD (~95% POP)
        available_strikes: Optional[List[float]] = None
    ) -> Dict:
        """
        Build an Iron Condor with strikes based on Expected Move.
        
        Args:
            stock_price: Current stock price
            iv: Implied volatility (annualized, decimal)
            days_to_expiry: Days to expiration
            wing_width: Width of protective wings in dollars
            sd_multiplier: Standard deviation multiplier for short strikes
            available_strikes: List of available strike prices (optional)
            
        Returns:
            Dictionary with Iron Condor leg details
        """
        # Calculate expected move
        em = self.em_calculator.calculate_em(stock_price, iv, days_to_expiry)
        
        # Calculate target strike levels based on SD
        target_put_short = stock_price - (em * sd_multiplier)
        target_call_short = stock_price + (em * sd_multiplier)
        
        # Snap to available strikes if provided
        if available_strikes:
            put_short_strike = self._find_nearest_strike(target_put_short, available_strikes, prefer='below')
            call_short_strike = self._find_nearest_strike(target_call_short, available_strikes, prefer='above')
            
            # Find wing strikes
            put_long_strike = self._find_strike_below(put_short_strike, wing_width, available_strikes)
            call_long_strike = self._find_strike_above(call_short_strike, wing_width, available_strikes)
        else:
            # Use round numbers
            put_short_strike = self._round_strike(target_put_short, prefer='below')
            call_short_strike = self._round_strike(target_call_short, prefer='above')
            put_long_strike = put_short_strike - wing_width
            call_long_strike = call_short_strike + wing_width
        
        # Calculate probabilities
        put_delta = self._estimate_delta(stock_price, put_short_strike, iv, days_to_expiry, 'put')
        call_delta = self._estimate_delta(stock_price, call_short_strike, iv, days_to_expiry, 'call')
        
        condor = {
            'ticker': 'N/A',
            'stock_price': stock_price,
            'expiry_days': days_to_expiry,
            'iv': iv,
            'expected_move': round(em, 2),
            'sd_multiplier': sd_multiplier,
            
            'legs': {
                'put_long': {
                    'type': 'put',
                    'action': 'buy',
                    'strike': put_long_strike,
                    'quantity': 1
                },
                'put_short': {
                    'type': 'put',
                    'action': 'sell',
                    'strike': put_short_strike,
                    'quantity': 1,
                    'delta': round(put_delta, 3)
                },
                'call_short': {
                    'type': 'call',
                    'action': 'sell',
                    'strike': call_short_strike,
                    'quantity': 1,
                    'delta': round(call_delta, 3)
                },
                'call_long': {
                    'type': 'call',
                    'action': 'buy',
                    'strike': call_long_strike,
                    'quantity': 1
                }
            },
            
            'metrics': {
                'put_spread_width': round(put_short_strike - put_long_strike, 2),
                'call_spread_width': round(call_long_strike - call_short_strike, 2),
                'total_range': round(call_short_strike - put_short_strike, 2),
                'pop_estimate': round((1 - abs(put_delta) - abs(call_delta)) * 100, 1)
            }
        }
        
        return condor
    
    def _find_nearest_strike(
        self,
        target: float,
        strikes: List[float],
        prefer: str = 'nearest'
    ) -> float:
        """Find the nearest available strike to target."""
        if not strikes:
            return self._round_strike(target)
        
        sorted_strikes = sorted(strikes)
        
        if prefer == 'below':
            candidates = [s for s in sorted_strikes if s <= target]
            return max(candidates) if candidates else sorted_strikes[0]
        elif prefer == 'above':
            candidates = [s for s in sorted_strikes if s >= target]
            return min(candidates) if candidates else sorted_strikes[-1]
        else:
            return min(sorted_strikes, key=lambda x: abs(x - target))
    
    def _find_strike_below(
        self,
        reference: float,
        width: float,
        strikes: List[float]
    ) -> float:
        """Find strike approximately 'width' dollars below reference."""
        target = reference - width
        candidates = [s for s in strikes if s < reference]
        if not candidates:
            return reference - width
        return min(candidates, key=lambda x: abs(x - target))
    
    def _find_strike_above(
        self,
        reference: float,
        width: float,
        strikes: List[float]
    ) -> float:
        """Find strike approximately 'width' dollars above reference."""
        target = reference + width
        candidates = [s for s in strikes if s > reference]
        if not candidates:
            return reference + width
        return min(candidates, key=lambda x: abs(x - target))
    
    def _round_strike(self, price: float, prefer: str = 'nearest') -> float:
        """Round to nearest common strike interval."""
        if price < 50:
            interval = 1
        elif price < 200:
            interval = 5
        else:
            interval = 10
        
        if prefer == 'below':
            return math.floor(price / interval) * interval
        elif prefer == 'above':
            return math.ceil(price / interval) * interval
        else:
            return round(price / interval) * interval
    
    def _estimate_delta(
        self,
        stock: float,
        strike: float,
        iv: float,
        dte: int,
        option_type: str
    ) -> float:
        """Estimate option delta using simplified Black-Scholes."""
        if dte <= 0:
            return 0.0
        
        t = dte / 365
        d1 = (math.log(stock / strike) + (0.05 + (iv ** 2) / 2) * t) / (iv * math.sqrt(t))
        
        # Cumulative normal distribution approximation
        def norm_cdf(x):
            return (1 + math.erf(x / math.sqrt(2))) / 2
        
        if option_type == 'call':
            return norm_cdf(d1)
        else:
            return norm_cdf(d1) - 1


# =============================================================================
# STRATEGY PICKER - PRESET STRATEGIES
# =============================================================================

class StrategyPicker:
    """
    Strategy picker with market condition presets.
    
    Presets:
    - Neutral: Iron Condor, Iron Butterfly, Straddle (sell)
    - Bullish: Bull Call Spread, Bull Put Spread, Long Call
    - Bearish: Bear Put Spread, Bear Call Spread, Long Put
    - High IV: Sell premium strategies (IC, credit spreads)
    - Low IV: Buy premium strategies (straddles, strangles)
    """
    
    PRESETS = {
        'neutral': {
            'name': 'Neutral Market',
            'description': 'Range-bound, expecting low volatility',
            'strategies': [
                {'name': 'Iron Condor', 'id': 'iron_condor', 'win_rate': 68},
                {'name': 'Iron Butterfly', 'id': 'iron_butterfly', 'win_rate': 55},
                {'name': 'Short Straddle', 'id': 'short_straddle', 'win_rate': 50},
                {'name': 'Short Strangle', 'id': 'short_strangle', 'win_rate': 65}
            ],
            'icon': '⚖️',
            'color': '#9ca3af'
        },
        'bullish': {
            'name': 'Bullish Market',
            'description': 'Expecting upward price movement',
            'strategies': [
                {'name': 'Bull Call Spread', 'id': 'bull_call_spread', 'win_rate': 55},
                {'name': 'Bull Put Spread', 'id': 'bull_put_spread', 'win_rate': 60},
                {'name': 'Long Call', 'id': 'long_call', 'win_rate': 40},
                {'name': 'Cash-Secured Put', 'id': 'cash_secured_put', 'win_rate': 65}
            ],
            'icon': '📈',
            'color': '#4caf50'
        },
        'bearish': {
            'name': 'Bearish Market',
            'description': 'Expecting downward price movement',
            'strategies': [
                {'name': 'Bear Put Spread', 'id': 'bear_put_spread', 'win_rate': 55},
                {'name': 'Bear Call Spread', 'id': 'bear_call_spread', 'win_rate': 60},
                {'name': 'Long Put', 'id': 'long_put', 'win_rate': 40},
                {'name': 'Covered Call', 'id': 'covered_call', 'win_rate': 70}
            ],
            'icon': '📉',
            'color': '#f44336'
        },
        'high_iv': {
            'name': 'High IV Environment',
            'description': 'IV Rank > 50, sell premium strategies',
            'strategies': [
                {'name': 'Iron Condor (Wide)', 'id': 'iron_condor_wide', 'win_rate': 75},
                {'name': 'Short Strangle', 'id': 'short_strangle', 'win_rate': 68},
                {'name': 'Credit Spreads', 'id': 'credit_spread', 'win_rate': 65},
                {'name': 'Jade Lizard', 'id': 'jade_lizard', 'win_rate': 70}
            ],
            'icon': '🔥',
            'color': '#ff9800'
        },
        'low_iv': {
            'name': 'Low IV Environment',
            'description': 'IV Rank < 30, buy premium strategies',
            'strategies': [
                {'name': 'Long Straddle', 'id': 'long_straddle', 'win_rate': 35},
                {'name': 'Long Strangle', 'id': 'long_strangle', 'win_rate': 30},
                {'name': 'Calendar Spread', 'id': 'calendar_spread', 'win_rate': 55},
                {'name': 'Diagonal Spread', 'id': 'diagonal_spread', 'win_rate': 50}
            ],
            'icon': '❄️',
            'color': '#2196f3'
        }
    }
    
    @classmethod
    def get_preset(cls, preset_name: str) -> Optional[Dict]:
        """Get a preset configuration."""
        return cls.PRESETS.get(preset_name)
    
    @classmethod
    def get_all_presets(cls) -> Dict:
        """Get all presets."""
        return cls.PRESETS
    
    @classmethod
    def recommend_preset(
        cls,
        iv_rank: float,  # 0-100
        trend: str = 'neutral',  # 'bullish', 'bearish', 'neutral'
        vix_level: float = 20
    ) -> str:
        """Recommend a preset based on market conditions."""
        # High IV environments
        if iv_rank > 50 or vix_level > 25:
            return 'high_iv'
        
        # Low IV environments
        if iv_rank < 30 and vix_level < 18:
            return 'low_iv'
        
        # Directional views
        if trend == 'bullish':
            return 'bullish'
        elif trend == 'bearish':
            return 'bearish'
        
        return 'neutral'


# =============================================================================
# MAX PAIN CALCULATOR
# =============================================================================

class MaxPainCalculator:
    """
    Calculate Max Pain price for options expiration.
    
    Max Pain is the strike price where option holders would
    experience the most financial pain (loss).
    """
    
    def calculate_max_pain(
        self,
        chain_data: pd.DataFrame,
        stock_price: float
    ) -> Dict:
        """
        Calculate Max Pain from options chain data.
        
        Args:
            chain_data: DataFrame with columns:
                - strike: Strike price
                - call_oi: Call open interest
                - put_oi: Put open interest
            stock_price: Current stock price
            
        Returns:
            Dictionary with max pain results
        """
        if chain_data.empty:
            return {'max_pain': stock_price, 'pain_by_strike': {}}
        
        strikes = sorted(chain_data['strike'].unique())
        pain_by_strike = {}
        
        for expiry_strike in strikes:
            total_pain = 0
            
            for _, row in chain_data.iterrows():
                strike = row['strike']
                call_oi = row.get('call_oi', 0) or 0
                put_oi = row.get('put_oi', 0) or 0
                
                # If stock expires at expiry_strike:
                # - Calls ITM if strike < expiry_strike
                # - Puts ITM if strike > expiry_strike
                
                # Call pain (loss to call holders)
                if strike < expiry_strike:
                    call_intrinsic = expiry_strike - strike
                    total_pain += call_oi * call_intrinsic * 100
                
                # Put pain (loss to put holders)
                if strike > expiry_strike:
                    put_intrinsic = strike - expiry_strike
                    total_pain += put_oi * put_intrinsic * 100
            
            pain_by_strike[expiry_strike] = total_pain
        
        # Find strike with minimum total pain
        if pain_by_strike:
            max_pain_strike = min(pain_by_strike.keys(), key=lambda x: pain_by_strike[x])
        else:
            max_pain_strike = stock_price
        
        return {
            'max_pain': max_pain_strike,
            'current_price': stock_price,
            'distance_to_max_pain': round(max_pain_strike - stock_price, 2),
            'distance_pct': round((max_pain_strike - stock_price) / stock_price * 100, 2),
            'pain_by_strike': pain_by_strike
        }
    
    def create_max_pain_chart(
        self,
        max_pain_result: Dict,
        ticker: str = ""
    ) -> go.Figure:
        """Create Max Pain visualization chart."""
        pain_data = max_pain_result.get('pain_by_strike', {})
        max_pain = max_pain_result.get('max_pain', 0)
        current = max_pain_result.get('current_price', 0)
        
        if not pain_data:
            fig = go.Figure()
            fig.add_annotation(text="No data available", x=0.5, y=0.5, showarrow=False)
            fig.update_layout(template='plotly_dark')
            return fig
        
        strikes = sorted(pain_data.keys())
        pain_values = [pain_data[s] / 1_000_000 for s in strikes]  # In millions
        
        # Color bars - highlight max pain strike
        colors = ['#f44336' if s == max_pain else '#2196f3' for s in strikes]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=strikes,
            y=pain_values,
            marker_color=colors,
            name='Total Pain'
        ))
        
        # Mark max pain
        fig.add_vline(
            x=max_pain,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Max Pain: ${max_pain:.0f}"
        )
        
        # Mark current price
        fig.add_vline(
            x=current,
            line_dash="dot",
            line_color="yellow",
            annotation_text=f"Current: ${current:.2f}"
        )
        
        fig.update_layout(
            title=f"{ticker} Max Pain Analysis",
            xaxis_title="Strike Price",
            yaxis_title="Total Pain ($M)",
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(22,33,62,0.8)',
            height=400,
            showlegend=False
        )
        
        return fig


# =============================================================================
# POSITION GREEKS ROLLUP
# =============================================================================

class PositionGreeksRollup:
    """
    Roll up Greeks for positions at ticker and portfolio level.
    
    Provides:
    - Per-position Greeks
    - Ticker-level aggregate
    - Portfolio-level aggregate
    - Risk metrics
    """
    
    def __init__(self):
        self.positions = []
    
    def add_position(
        self,
        ticker: str,
        option_type: str,  # 'call' or 'put'
        action: str,  # 'buy' or 'sell'
        quantity: int,
        delta: float,
        gamma: float,
        theta: float,
        vega: float,
        rho: float = 0.0,
        position_id: str = None
    ):
        """Add a position to track."""
        sign = 1 if action == 'buy' else -1
        
        position = {
            'id': position_id or f"{ticker}_{option_type}_{len(self.positions)}",
            'ticker': ticker,
            'type': option_type,
            'action': action,
            'quantity': quantity,
            'sign': sign,
            # Store raw Greeks (will be multiplied by sign and quantity)
            'delta_raw': delta,
            'gamma_raw': gamma,
            'theta_raw': theta,
            'vega_raw': vega,
            'rho_raw': rho,
            # Net Greeks (sign * quantity * greek * 100)
            'delta_net': round(sign * quantity * delta * 100, 2),
            'gamma_net': round(sign * quantity * gamma * 100, 4),
            'theta_net': round(sign * quantity * theta * 100, 2),
            'vega_net': round(sign * quantity * vega * 100, 2),
            'rho_net': round(sign * quantity * rho * 100, 2)
        }
        
        self.positions.append(position)
        return position
    
    def get_ticker_rollup(self, ticker: str) -> Dict:
        """Get aggregated Greeks for a specific ticker."""
        ticker_positions = [p for p in self.positions if p['ticker'] == ticker]
        
        if not ticker_positions:
            return {'ticker': ticker, 'positions': 0}
        
        return {
            'ticker': ticker,
            'positions': len(ticker_positions),
            'delta': round(sum(p['delta_net'] for p in ticker_positions), 2),
            'gamma': round(sum(p['gamma_net'] for p in ticker_positions), 4),
            'theta': round(sum(p['theta_net'] for p in ticker_positions), 2),
            'vega': round(sum(p['vega_net'] for p in ticker_positions), 2),
            'rho': round(sum(p['rho_net'] for p in ticker_positions), 2)
        }
    
    def get_portfolio_rollup(self) -> Dict:
        """Get aggregated Greeks for entire portfolio."""
        if not self.positions:
            return {
                'tickers': 0,
                'positions': 0,
                'delta': 0,
                'gamma': 0,
                'theta': 0,
                'vega': 0,
                'rho': 0
            }
        
        tickers = set(p['ticker'] for p in self.positions)
        
        return {
            'tickers': len(tickers),
            'positions': len(self.positions),
            'delta': round(sum(p['delta_net'] for p in self.positions), 2),
            'gamma': round(sum(p['gamma_net'] for p in self.positions), 4),
            'theta': round(sum(p['theta_net'] for p in self.positions), 2),
            'vega': round(sum(p['vega_net'] for p in self.positions), 2),
            'rho': round(sum(p['rho_net'] for p in self.positions), 2),
            'by_ticker': {t: self.get_ticker_rollup(t) for t in tickers}
        }
    
    def get_risk_summary(self) -> Dict:
        """Get risk summary for portfolio."""
        portfolio = self.get_portfolio_rollup()
        
        return {
            'delta_exposure': portfolio['delta'],
            'delta_neutral': abs(portfolio['delta']) < 50,
            'daily_theta': portfolio['theta'],
            'vega_exposure': portfolio['vega'],
            'gamma_risk': portfolio['gamma'],
            'warnings': self._generate_warnings(portfolio)
        }
    
    def _generate_warnings(self, portfolio: Dict) -> List[str]:
        """Generate risk warnings."""
        warnings = []
        
        if abs(portfolio['delta']) > 500:
            warnings.append(f"⚠️ High delta exposure: {portfolio['delta']}")
        
        if portfolio['theta'] < -50:
            warnings.append(f"⚠️ High daily theta decay: ${portfolio['theta']}/day")
        
        if abs(portfolio['vega']) > 200:
            warnings.append(f"⚠️ High vega exposure: ${portfolio['vega']} per 1% IV")
        
        if portfolio['gamma'] > 10:
            warnings.append(f"⚠️ High positive gamma: {portfolio['gamma']}")
        elif portfolio['gamma'] < -10:
            warnings.append(f"⚠️ High negative gamma: {portfolio['gamma']}")
        
        return warnings
    
    def clear_positions(self):
        """Clear all positions."""
        self.positions = []


# =============================================================================
# SINGLETON INSTANCES
# =============================================================================

_iron_condor_builder = None
_strategy_picker = None
_max_pain_calculator = None
_greeks_rollup = None


def get_iron_condor_builder() -> IronCondorBuilder:
    """Get singleton Iron Condor builder."""
    global _iron_condor_builder
    if _iron_condor_builder is None:
        _iron_condor_builder = IronCondorBuilder()
    return _iron_condor_builder


def get_strategy_picker() -> StrategyPicker:
    """Get singleton Strategy Picker."""
    global _strategy_picker
    if _strategy_picker is None:
        _strategy_picker = StrategyPicker()
    return _strategy_picker


def get_max_pain_calculator() -> MaxPainCalculator:
    """Get singleton Max Pain calculator."""
    global _max_pain_calculator
    if _max_pain_calculator is None:
        _max_pain_calculator = MaxPainCalculator()
    return _max_pain_calculator


def get_greeks_rollup() -> PositionGreeksRollup:
    """Get singleton Greeks rollup tracker."""
    global _greeks_rollup
    if _greeks_rollup is None:
        _greeks_rollup = PositionGreeksRollup()
    return _greeks_rollup
