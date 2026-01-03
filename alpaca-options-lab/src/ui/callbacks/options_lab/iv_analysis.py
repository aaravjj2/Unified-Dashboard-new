"""
IV Analysis Module - Historical IV, Term Structure, Skew Analysis

Author: Options Lab Enhancement Phase
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


class IVAnalyzer:
    """Comprehensive Implied Volatility analysis."""
    
    def __init__(self):
        self.iv_history = {}
        
    def generate_sample_iv_history(self, ticker: str) -> List[float]:
        """Generate sample historical IV data."""
        import random
        
        # Generate 252 days of IV data (random walk)
        iv = 0.30
        history = []
        for _ in range(252):
            change = random.gauss(0, 0.02)
            iv = max(0.1, min(0.8, iv + change))
            history.append(iv)
            
        return history

    def calculate_iv_percentile(self, current_iv: float, historical_ivs: List[float], 
                                 periods: List[int] = [30, 60, 90, 252]) -> Dict:
        """
        Calculate IV percentile rank over various lookback periods.
        
        IV Percentile = % of days IV was lower than current
        """
        if not historical_ivs or len(historical_ivs) < max(periods):
            return {p: None for p in periods}
        
        results = {}
        for period in periods:
            if len(historical_ivs) >= period:
                lookback = historical_ivs[-period:]
                percentile = sum(1 for iv in lookback if iv < current_iv) / period * 100
                results[period] = round(percentile, 1)
            else:
                results[period] = None
        
        return results
    
    def calculate_iv_rank(self, current_iv: float, historical_ivs: List[float],
                          period: int = 252) -> Optional[float]:
        """
        Calculate IV Rank (IVR).
        
        IVR = (Current IV - 52-week Low) / (52-week High - 52-week Low) × 100
        """
        if not historical_ivs or len(historical_ivs) < period:
            return None
        
        lookback = historical_ivs[-period:]
        iv_high = max(lookback)
        iv_low = min(lookback)
        
        if iv_high == iv_low:
            return 50.0  # Neutral if no range
        
        iv_rank = (current_iv - iv_low) / (iv_high - iv_low) * 100
        return round(iv_rank, 1)
    
    def analyze_term_structure(self, chain_data: pd.DataFrame, atm_strike: float) -> Dict:
        """
        Analyze IV term structure across expirations.
        
        Normal: Near-term IV < Long-term IV (Contango)
        Inverted: Near-term IV > Long-term IV (Backwardation)
        """
        if chain_data is None or chain_data.empty:
            return {'structure': [], 'shape': 'unknown'}
        
        try:
            # Filter to ATM options (+/- 5% of ATM strike)
            atm_range = atm_strike * 0.05
            atm_chain = chain_data[
                (chain_data['strike'] >= atm_strike - atm_range) &
                (chain_data['strike'] <= atm_strike + atm_range)
            ]
            
            # Group by expiration
            term_structure = []
            for exp in atm_chain['expiration'].unique():
                exp_data = atm_chain[atm_chain['expiration'] == exp]
                avg_iv = exp_data['impliedVolatility'].mean()
                
                # Calculate DTE
                try:
                    exp_date = pd.to_datetime(exp)
                    dte = (exp_date - datetime.now()).days
                except:
                    dte = 30  # Default
                
                term_structure.append({
                    'expiration': exp,
                    'dte': dte,
                    'iv': round(avg_iv * 100, 2)
                })
            
            # Sort by DTE
            term_structure.sort(key=lambda x: x['dte'])
            
            # Determine shape
            if len(term_structure) >= 2:
                if term_structure[0]['iv'] < term_structure[-1]['iv']:
                    shape = 'contango'
                elif term_structure[0]['iv'] > term_structure[-1]['iv']:
                    shape = 'backwardation'
                else:
                    shape = 'flat'
            else:
                shape = 'insufficient_data'
            
            return {'structure': term_structure, 'shape': shape}
            
        except Exception as e:
            logger.error(f"Term structure analysis error: {e}")
            return {'structure': [], 'shape': 'error'}
    
    def analyze_skew(self, chain_data: pd.DataFrame, spot_price: float,
                     expiration: str = None) -> Dict:
        """
        Analyze IV skew (put/call IV difference).
        
        Positive skew: OTM puts have higher IV than OTM calls (bearish fear)
        Negative skew: OTM calls have higher IV than OTM puts (bullish)
        """
        if chain_data is None or chain_data.empty:
            return {'skew': 0, 'skew_by_strike': {}, 'interpretation': 'unknown'}
        
        try:
            # Filter by expiration if specified
            if expiration:
                chain_data = chain_data[chain_data['expiration'] == expiration]
            
            skew_by_strike = {}
            
            for strike in chain_data['strike'].unique():
                strike_data = chain_data[chain_data['strike'] == strike]
                
                call_iv = strike_data[strike_data['type'] == 'call']['impliedVolatility'].mean()
                put_iv = strike_data[strike_data['type'] == 'put']['impliedVolatility'].mean()
                
                if not pd.isna(call_iv) and not pd.isna(put_iv):
                    # Skew = Put IV - Call IV
                    skew_by_strike[strike] = round((put_iv - call_iv) * 100, 2)
            
            # Calculate average skew for OTM options
            otm_put_strikes = [s for s in skew_by_strike.keys() if s < spot_price * 0.95]
            otm_call_strikes = [s for s in skew_by_strike.keys() if s > spot_price * 1.05]
            
            avg_otm_put_skew = np.mean([skew_by_strike[s] for s in otm_put_strikes]) if otm_put_strikes else 0
            avg_otm_call_skew = np.mean([skew_by_strike[s] for s in otm_call_strikes]) if otm_call_strikes else 0
            
            net_skew = avg_otm_put_skew - avg_otm_call_skew
            
            # Interpretation
            if net_skew > 5:
                interpretation = 'Strong put skew (fear/hedging)'
            elif net_skew > 2:
                interpretation = 'Moderate put skew'
            elif net_skew < -5:
                interpretation = 'Strong call skew (bullish)'
            elif net_skew < -2:
                interpretation = 'Moderate call skew'
            else:
                interpretation = 'Neutral skew'
            
            return {
                'skew': round(net_skew, 2),
                'skew_by_strike': skew_by_strike,
                'interpretation': interpretation,
                'avg_otm_put_skew': round(avg_otm_put_skew, 2),
                'avg_otm_call_skew': round(avg_otm_call_skew, 2)
            }
            
        except Exception as e:
            logger.error(f"Skew analysis error: {e}")
            return {'skew': 0, 'skew_by_strike': {}, 'interpretation': 'error'}
    
    def calculate_earnings_iv_crush(self, pre_earnings_iv: float, 
                                     historical_crush_pct: float = 30) -> Dict:
        """
        Estimate post-earnings IV crush.
        
        Typical crush: 20-50% depending on stock
        """
        expected_post_iv = pre_earnings_iv * (1 - historical_crush_pct / 100)
        
        return {
            'pre_earnings_iv': round(pre_earnings_iv, 2),
            'expected_crush_pct': historical_crush_pct,
            'expected_post_iv': round(expected_post_iv, 2),
            'premium_at_risk_pct': round(historical_crush_pct * 0.7, 1),  # Approximation
            'recommendation': 'Sell premium before earnings' if pre_earnings_iv > 40 else 'Consider buying for directional play'
        }


def create_term_structure_chart(term_data: Dict, ticker: str = "N/A") -> go.Figure:
    """Create IV term structure visualization."""
    structure = term_data.get('structure', [])
    
    if not structure:
        fig = go.Figure()
        fig.add_annotation(text="No term structure data", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template='plotly_dark')
        return fig
    
    dtes = [s['dte'] for s in structure]
    ivs = [s['iv'] for s in structure]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=dtes,
        y=ivs,
        mode='lines+markers',
        line=dict(color='#4CAF50', width=3),
        marker=dict(size=10),
        name='IV Term Structure'
    ))
    
    # Add shape indicator
    shape = term_data.get('shape', 'unknown')
    shape_colors = {
        'contango': '#4CAF50',
        'backwardation': '#f44336',
        'flat': '#FFC107'
    }
    
    fig.update_layout(
        title=f"{ticker} IV Term Structure ({shape.upper()})",
        xaxis_title="Days to Expiration",
        yaxis_title="Implied Volatility (%)",
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.8)',
        height=350
    )
    
    return fig


def create_skew_chart(skew_data: Dict, spot_price: float, ticker: str = "N/A") -> go.Figure:
    """Create IV skew visualization."""
    skew_by_strike = skew_data.get('skew_by_strike', {})
    
    if not skew_by_strike:
        fig = go.Figure()
        fig.add_annotation(text="No skew data", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template='plotly_dark')
        return fig
    
    strikes = sorted(skew_by_strike.keys())
    skews = [skew_by_strike[s] for s in strikes]
    colors = ['#f44336' if s > 0 else '#4CAF50' for s in skews]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=strikes,
        y=skews,
        marker_color=colors,
        name='Put-Call Skew'
    ))
    
    # Spot price line
    fig.add_vline(x=spot_price, line_dash="dash", line_color="yellow",
                  annotation_text=f"Spot: ${spot_price:.2f}")
    
    # Zero line
    fig.add_hline(y=0, line_dash="dot", line_color="white", opacity=0.5)
    
    fig.update_layout(
        title=f"{ticker} IV Skew - {skew_data.get('interpretation', 'N/A')}",
        xaxis_title="Strike",
        yaxis_title="Put IV - Call IV (%)",
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.8)',
        height=350
    )
    
    return fig


def create_iv_percentile_gauge(percentile_data: Dict, current_iv: float) -> go.Figure:
    """Create IV percentile gauge chart."""
    fig = go.Figure()
    
    # Use 252-day percentile for main gauge
    pct_252 = percentile_data.get(252, 50)
    if pct_252 is None:
        pct_252 = 50
    
    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=pct_252,
        title={'text': f"IV Percentile (Current IV: {current_iv:.1f}%)"},
        delta={'reference': 50, 'increasing': {'color': "red"}, 'decreasing': {'color': "green"}},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "#2196F3"},
            'steps': [
                {'range': [0, 20], 'color': '#4CAF50'},   # Low IV
                {'range': [20, 40], 'color': '#8BC34A'},
                {'range': [40, 60], 'color': '#FFC107'},  # Neutral
                {'range': [60, 80], 'color': '#FF9800'},
                {'range': [80, 100], 'color': '#f44336'}  # High IV
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': pct_252
            }
        }
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        height=250
    )
    
    return fig


# Singleton analyzer instance
_iv_analyzer = None

def get_iv_analyzer() -> IVAnalyzer:
    """Get singleton IV analyzer instance."""
    global _iv_analyzer
    if _iv_analyzer is None:
        _iv_analyzer = IVAnalyzer()
    return _iv_analyzer
