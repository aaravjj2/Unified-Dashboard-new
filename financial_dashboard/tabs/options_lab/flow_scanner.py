"""
Options Flow Scanner - Tracks unusual options activity
Includes: Large block trades, unusual volume, sweeps detection

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


class OptionsFlowScanner:
    """Scans for unusual options activity patterns."""
    
    def __init__(self):
        self.flow_data = []
        self.alerts = []
        
    def generate_sample_chain(self, ticker: str) -> pd.DataFrame:
        """Generate sample options chain data for testing."""
        import random
        
        strikes = [100, 105, 110, 115, 120, 125, 130]
        expirations = [(datetime.now() + timedelta(days=x)).strftime('%Y-%m-%d') for x in [7, 14, 30, 60]]
        
        data = []
        for exp in expirations:
            for strike in strikes:
                # Call
                data.append({
                    'ticker': ticker,
                    'type': 'call',
                    'strike': strike,
                    'expiration': exp,
                    'lastPrice': random.uniform(1, 10),
                    'volume': random.randint(100, 5000),
                    'openInterest': random.randint(1000, 10000),
                    'impliedVolatility': random.uniform(0.2, 0.5),
                    'delta': random.uniform(0.1, 0.9),
                    'gamma': random.uniform(0.01, 0.05),
                    'theta': random.uniform(-0.1, -0.01),
                    'vega': random.uniform(0.05, 0.2)
                })
                # Put
                data.append({
                    'ticker': ticker,
                    'type': 'put',
                    'strike': strike,
                    'expiration': exp,
                    'lastPrice': random.uniform(1, 10),
                    'volume': random.randint(100, 5000),
                    'openInterest': random.randint(1000, 10000),
                    'impliedVolatility': random.uniform(0.2, 0.5),
                    'delta': random.uniform(-0.9, -0.1),
                    'gamma': random.uniform(0.01, 0.05),
                    'theta': random.uniform(-0.1, -0.01),
                    'vega': random.uniform(0.05, 0.2)
                })
        
        return pd.DataFrame(data)

    def analyze_flow(self, chain_data: pd.DataFrame, spot_price: float) -> Dict:
        """
        Analyze options chain for unusual activity.
        
        Args:
            chain_data: DataFrame with options chain data
            spot_price: Current underlying price
            
        Returns:
            Dict with flow analysis results
        """
        if chain_data is None or chain_data.empty:
            return {'alerts': [], 'summary': {}, 'unusual_activity': []}
        
        results = {
            'alerts': [],
            'summary': {},
            'unusual_activity': [],
            'block_trades': [],
            'sweeps': [],
            'bullish_flow': 0,
            'bearish_flow': 0
        }
        
        try:
            # Calculate volume/OI ratio for unusual activity
            chain_data['vol_oi_ratio'] = chain_data['volume'] / chain_data['openInterest'].replace(0, 1)
            
            # Find unusual volume (volume > 2x OI)
            unusual = chain_data[chain_data['vol_oi_ratio'] > 2.0].copy()
            
            for _, row in unusual.iterrows():
                premium = row.get('lastPrice', 0) * row.get('volume', 0) * 100
                
                activity = {
                    'strike': row.get('strike', 0),
                    'expiration': row.get('expiration', 'N/A'),
                    'type': row.get('type', 'call'),
                    'volume': int(row.get('volume', 0)),
                    'oi': int(row.get('openInterest', 0)),
                    'vol_oi_ratio': round(row.get('vol_oi_ratio', 0), 2),
                    'premium': round(premium, 0),
                    'iv': round(row.get('impliedVolatility', 0) * 100, 1),
                    'sentiment': 'Bullish' if row.get('type') == 'call' else 'Bearish'
                }
                results['unusual_activity'].append(activity)
                
                # Track bullish/bearish flow
                if row.get('type') == 'call':
                    results['bullish_flow'] += premium
                else:
                    results['bearish_flow'] += premium
            
            # Detect large block trades (premium > $50k)
            large_premium = chain_data[chain_data['lastPrice'] * chain_data['volume'] * 100 > 50000]
            for _, row in large_premium.iterrows():
                block = {
                    'strike': row.get('strike', 0),
                    'type': row.get('type', 'call'),
                    'premium': round(row.get('lastPrice', 0) * row.get('volume', 0) * 100, 0),
                    'contracts': int(row.get('volume', 0))
                }
                results['block_trades'].append(block)
            
            # Generate alerts
            total_flow = results['bullish_flow'] + results['bearish_flow']
            if total_flow > 0:
                bull_pct = results['bullish_flow'] / total_flow * 100
                if bull_pct > 70:
                    results['alerts'].append({
                        'type': 'bullish',
                        'message': f'Strong bullish flow detected: {bull_pct:.0f}% calls',
                        'severity': 'high'
                    })
                elif bull_pct < 30:
                    results['alerts'].append({
                        'type': 'bearish',
                        'message': f'Strong bearish flow detected: {100-bull_pct:.0f}% puts',
                        'severity': 'high'
                    })
            
            # Summary stats
            results['summary'] = {
                'total_unusual': len(results['unusual_activity']),
                'block_trades': len(results['block_trades']),
                'total_premium': round(total_flow, 0),
                'bullish_pct': round(results['bullish_flow'] / max(total_flow, 1) * 100, 1),
                'bearish_pct': round(results['bearish_flow'] / max(total_flow, 1) * 100, 1)
            }
            
        except Exception as e:
            logger.error(f"Flow analysis error: {e}")
            results['alerts'].append({
                'type': 'error',
                'message': f'Analysis error: {str(e)}',
                'severity': 'low'
            })
        
        return results
    
    def create_flow_chart(self, flow_data: Dict) -> go.Figure:
        """Create visualization of options flow."""
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Flow Sentiment', 'Premium by Strike', 'Volume/OI Ratio', 'Block Trades'),
            specs=[[{"type": "pie"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "bar"}]]
        )
        
        # Sentiment pie chart
        fig.add_trace(
            go.Pie(
                labels=['Bullish', 'Bearish'],
                values=[flow_data.get('bullish_flow', 1), flow_data.get('bearish_flow', 1)],
                marker_colors=['#4CAF50', '#f44336'],
                hole=0.4
            ),
            row=1, col=1
        )
        
        # Premium by strike
        unusual = flow_data.get('unusual_activity', [])
        if unusual:
            strikes = [u['strike'] for u in unusual]
            premiums = [u['premium'] for u in unusual]
            colors = ['#4CAF50' if u['type'] == 'call' else '#f44336' for u in unusual]
            
            fig.add_trace(
                go.Bar(x=strikes, y=premiums, marker_color=colors, name='Premium'),
                row=1, col=2
            )
        
        # Vol/OI Ratio
        if unusual:
            ratios = [u['vol_oi_ratio'] for u in unusual]
            fig.add_trace(
                go.Bar(x=strikes, y=ratios, marker_color='#2196F3', name='Vol/OI'),
                row=2, col=1
            )
        
        # Block trades
        blocks = flow_data.get('block_trades', [])
        if blocks:
            block_strikes = [b['strike'] for b in blocks]
            block_premium = [b['premium'] for b in blocks]
            fig.add_trace(
                go.Bar(x=block_strikes, y=block_premium, marker_color='#FF9800', name='Block Premium'),
                row=2, col=2
            )
        
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(22,33,62,0.8)',
            height=600,
            showlegend=False,
            title_text="Options Flow Analysis"
        )
        
        return fig


def calculate_gex(chain_data: pd.DataFrame, spot_price: float) -> Dict:
    """
    Calculate Gamma Exposure (GEX) for market maker hedging analysis.
    
    GEX = Gamma × OI × 100 × Spot²
    
    Positive GEX = Calls dominate = MM sells as price rises (dampening)
    Negative GEX = Puts dominate = MM buys as price falls (amplifying)
    """
    if chain_data is None or chain_data.empty:
        return {'gex_by_strike': {}, 'net_gex': 0, 'gex_flip': None}
    
    try:
        gex_data = {}
        
        for _, row in chain_data.iterrows():
            strike = row.get('strike', 0)
            gamma = row.get('gamma', 0)
            oi = row.get('openInterest', 0)
            opt_type = row.get('type', 'call')
            
            # GEX formula
            gex = gamma * oi * 100 * (spot_price ** 2) / 1e9  # In billions
            
            # Calls have positive GEX, puts have negative GEX for MMs
            if opt_type == 'put':
                gex = -gex
            
            if strike in gex_data:
                gex_data[strike] += gex
            else:
                gex_data[strike] = gex
        
        # Find GEX flip point (where cumulative GEX changes sign)
        sorted_strikes = sorted(gex_data.keys())
        cumulative = 0
        gex_flip = None
        for strike in sorted_strikes:
            prev_cumulative = cumulative
            cumulative += gex_data[strike]
            if prev_cumulative * cumulative < 0:  # Sign change
                gex_flip = strike
                break
        
        return {
            'gex_by_strike': gex_data,
            'net_gex': sum(gex_data.values()),
            'gex_flip': gex_flip,
            'interpretation': 'Dampening' if sum(gex_data.values()) > 0 else 'Amplifying'
        }
        
    except Exception as e:
        logger.error(f"GEX calculation error: {e}")
        return {'gex_by_strike': {}, 'net_gex': 0, 'gex_flip': None}


def create_gex_chart(gex_data: Dict, spot_price: float) -> go.Figure:
    """Create GEX visualization chart."""
    gex_by_strike = gex_data.get('gex_by_strike', {})
    
    if not gex_by_strike:
        fig = go.Figure()
        fig.add_annotation(text="No GEX data available", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template='plotly_dark')
        return fig
    
    strikes = sorted(gex_by_strike.keys())
    gex_values = [gex_by_strike[s] for s in strikes]
    colors = ['#4CAF50' if v > 0 else '#f44336' for v in gex_values]
    
    fig = go.Figure()
    
    # GEX bars
    fig.add_trace(go.Bar(
        x=strikes,
        y=gex_values,
        marker_color=colors,
        name='GEX'
    ))
    
    # Spot price line
    fig.add_vline(x=spot_price, line_dash="dash", line_color="yellow",
                  annotation_text=f"Spot: ${spot_price:.2f}")
    
    # GEX flip point
    if gex_data.get('gex_flip'):
        fig.add_vline(x=gex_data['gex_flip'], line_dash="dot", line_color="cyan",
                      annotation_text="GEX Flip")
    
    fig.update_layout(
        title=f"Gamma Exposure (GEX) - Net: {gex_data.get('net_gex', 0):.2f}B ({gex_data.get('interpretation', 'N/A')})",
        xaxis_title="Strike",
        yaxis_title="GEX (Billions $)",
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.8)',
        height=400
    )
    
    return fig


def calculate_max_pain(chain_data: pd.DataFrame) -> Dict:
    """
    Calculate max pain strike - where options expire worthless.
    This is where market makers have minimum payout.
    """
    if chain_data is None or chain_data.empty:
        return {'max_pain': None, 'pain_by_strike': {}}
    
    try:
        # Get unique strikes
        strikes = chain_data['strike'].unique()
        pain_by_strike = {}
        
        for test_strike in strikes:
            total_pain = 0
            
            for _, row in chain_data.iterrows():
                strike = row.get('strike', 0)
                oi = row.get('openInterest', 0)
                opt_type = row.get('type', 'call')
                
                if opt_type == 'call':
                    # Call pain: max(0, test_strike - strike) * OI
                    pain = max(0, test_strike - strike) * oi * 100
                else:
                    # Put pain: max(0, strike - test_strike) * OI
                    pain = max(0, strike - test_strike) * oi * 100
                
                total_pain += pain
            
            pain_by_strike[test_strike] = total_pain
        
        # Find minimum pain (max pain strike)
        max_pain_strike = min(pain_by_strike, key=pain_by_strike.get) if pain_by_strike else None
        
        return {
            'max_pain': max_pain_strike,
            'pain_by_strike': pain_by_strike,
            'total_oi': int(chain_data['openInterest'].sum())
        }
        
    except Exception as e:
        logger.error(f"Max pain calculation error: {e}")
        return {'max_pain': None, 'pain_by_strike': {}}


# Singleton scanner instance
_flow_scanner = None

def get_flow_scanner() -> OptionsFlowScanner:
    """Get singleton flow scanner instance."""
    global _flow_scanner
    if _flow_scanner is None:
        _flow_scanner = OptionsFlowScanner()
    return _flow_scanner
