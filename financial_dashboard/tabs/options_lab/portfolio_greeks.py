"""
Portfolio Greeks Module - Aggregate Greeks across all positions

Author: Options Lab Enhancement Phase
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


class PortfolioGreeks:
    """Calculate and visualize aggregate portfolio Greeks."""
    
    def __init__(self):
        self.positions = []
        
    def calculate_aggregate_greeks(self, positions: List[Dict]) -> Dict:
        """
        Calculate net Greeks across all options positions.
        
        Args:
            positions: List of position dicts with fields:
                - symbol, strike, expiration, type (call/put)
                - quantity (positive=long, negative=short)
                - delta, gamma, theta, vega, rho
                
        Returns:
            Dict with aggregate Greeks and risk metrics
        """
        aggregate = {
            'net_delta': 0,
            'net_gamma': 0,
            'net_theta': 0,
            'net_vega': 0,
            'net_rho': 0,
            'dollar_delta': 0,
            'gamma_risk': 0,
            'theta_decay': 0,
            'vega_exposure': 0,
            'by_underlying': {},
            'by_expiration': {}
        }
        
        if not positions:
            return aggregate
        
        try:
            for pos in positions:
                qty = pos.get('quantity', 0)
                contracts = abs(qty) * 100  # Each contract = 100 shares
                sign = 1 if qty > 0 else -1
                
                # Raw Greeks
                delta = pos.get('delta', 0) * contracts * sign
                gamma = pos.get('gamma', 0) * contracts * sign
                theta = pos.get('theta', 0) * contracts * sign
                vega = pos.get('vega', 0) * contracts * sign
                rho = pos.get('rho', 0) * contracts * sign
                
                aggregate['net_delta'] += delta
                aggregate['net_gamma'] += gamma
                aggregate['net_theta'] += theta
                aggregate['net_vega'] += vega
                aggregate['net_rho'] += rho
                
                # Dollar exposure (delta * spot * 100)
                spot = pos.get('underlying_price', 100)
                aggregate['dollar_delta'] += delta * spot
                
                # Track by underlying
                symbol = pos.get('symbol', 'UNKNOWN')
                if symbol not in aggregate['by_underlying']:
                    aggregate['by_underlying'][symbol] = {
                        'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0
                    }
                aggregate['by_underlying'][symbol]['delta'] += delta
                aggregate['by_underlying'][symbol]['gamma'] += gamma
                aggregate['by_underlying'][symbol]['theta'] += theta
                aggregate['by_underlying'][symbol]['vega'] += vega
                
                # Track by expiration
                exp = pos.get('expiration', 'UNKNOWN')
                if exp not in aggregate['by_expiration']:
                    aggregate['by_expiration'][exp] = {
                        'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0
                    }
                aggregate['by_expiration'][exp]['delta'] += delta
                aggregate['by_expiration'][exp]['gamma'] += gamma
                aggregate['by_expiration'][exp]['theta'] += theta
                aggregate['by_expiration'][exp]['vega'] += vega
            
            # Risk calculations
            aggregate['gamma_risk'] = abs(aggregate['net_gamma']) * 50  # $50 per 1% move
            aggregate['theta_decay'] = aggregate['net_theta']  # Daily decay
            aggregate['vega_exposure'] = aggregate['net_vega'] * 0.01  # Per 1% IV change
            
            # Round values
            for key in ['net_delta', 'net_gamma', 'net_theta', 'net_vega', 'net_rho',
                        'dollar_delta', 'gamma_risk', 'theta_decay', 'vega_exposure']:
                aggregate[key] = round(aggregate[key], 2)
                
        except Exception as e:
            logger.error(f"Aggregate Greeks calculation error: {e}")
            
        return aggregate
    
    def calculate_scenario_pnl(self, positions: List[Dict], 
                                price_changes: List[float], 
                                iv_changes: List[float]) -> pd.DataFrame:
        """
        Calculate P&L matrix for price move vs IV change scenarios.
        
        Args:
            positions: List of position dicts
            price_changes: List of % price changes (e.g., [-10, -5, 0, 5, 10])
            iv_changes: List of % IV changes (e.g., [-20, -10, 0, 10, 20])
            
        Returns:
            DataFrame with P&L for each scenario
        """
        if not positions:
            return pd.DataFrame()
        
        # Calculate aggregate Greeks
        greeks = self.calculate_aggregate_greeks(positions)
        
        # Build P&L matrix
        pnl_matrix = []
        
        for price_pct in price_changes:
            row = []
            for iv_pct in iv_changes:
                # Approximate P&L using Greeks
                # P&L ≈ Delta * ΔS + 0.5 * Gamma * ΔS² + Vega * ΔIV + Theta
                
                delta_pnl = greeks['net_delta'] * price_pct
                gamma_pnl = 0.5 * greeks['net_gamma'] * (price_pct ** 2)
                vega_pnl = greeks['net_vega'] * iv_pct
                theta_pnl = greeks['net_theta']  # 1 day decay
                
                total_pnl = delta_pnl + gamma_pnl + vega_pnl + theta_pnl
                row.append(round(total_pnl, 2))
            
            pnl_matrix.append(row)
        
        df = pd.DataFrame(
            pnl_matrix,
            index=[f"{p:+.0f}%" for p in price_changes],
            columns=[f"IV {iv:+.0f}%" for iv in iv_changes]
        )
        
        return df
    
    def get_risk_score(self, aggregate_greeks: Dict) -> Dict:
        """
        Calculate risk/reward score for the portfolio.
        
        Score 0-100 where:
        - 0-30: Low risk, conservative
        - 30-60: Moderate risk
        - 60-100: High risk, aggressive
        """
        score = 50  # Start neutral
        
        # Delta risk (large directional exposure)
        delta_risk = min(abs(aggregate_greeks.get('net_delta', 0)) / 100, 25)
        score += delta_risk
        
        # Gamma risk (exposure to large moves)
        gamma_risk = min(abs(aggregate_greeks.get('net_gamma', 0)) / 10, 15)
        score += gamma_risk
        
        # Theta (positive theta = selling premium = higher risk)
        theta = aggregate_greeks.get('net_theta', 0)
        if theta > 0:
            score -= min(theta / 50, 10)  # Earning theta = lower risk
        else:
            score += min(abs(theta) / 50, 10)  # Paying theta = higher risk
        
        # Vega (IV exposure)
        vega_risk = min(abs(aggregate_greeks.get('net_vega', 0)) / 50, 10)
        score += vega_risk
        
        score = max(0, min(100, score))
        
        if score < 30:
            interpretation = 'Conservative'
            color = '#4CAF50'
        elif score < 60:
            interpretation = 'Moderate'
            color = '#FFC107'
        else:
            interpretation = 'Aggressive'
            color = '#f44336'
        
        return {
            'score': round(score, 1),
            'interpretation': interpretation,
            'color': color
        }


def create_greeks_dashboard(aggregate: Dict) -> go.Figure:
    """Create portfolio Greeks visualization dashboard."""
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Net Greeks', 'Delta by Underlying', 'Theta Decay', 'Risk Breakdown'),
        specs=[[{"type": "bar"}, {"type": "pie"}],
               [{"type": "indicator"}, {"type": "bar"}]]
    )
    
    # Net Greeks bar chart
    greeks = ['Delta', 'Gamma×10', 'Theta', 'Vega']
    values = [
        aggregate.get('net_delta', 0),
        aggregate.get('net_gamma', 0) * 10,  # Scale gamma for visibility
        aggregate.get('net_theta', 0),
        aggregate.get('net_vega', 0)
    ]
    colors = ['#4CAF50' if v >= 0 else '#f44336' for v in values]
    
    fig.add_trace(
        go.Bar(x=greeks, y=values, marker_color=colors, name='Net Greeks'),
        row=1, col=1
    )
    
    # Delta by underlying pie
    by_underlying = aggregate.get('by_underlying', {})
    if by_underlying:
        labels = list(by_underlying.keys())
        deltas = [abs(v['delta']) for v in by_underlying.values()]
        fig.add_trace(
            go.Pie(labels=labels, values=deltas, hole=0.4),
            row=1, col=2
        )
    
    # Theta decay indicator
    fig.add_trace(
        go.Indicator(
            mode="number+delta",
            value=aggregate.get('net_theta', 0),
            title={'text': "Daily Theta ($)"},
            delta={'reference': 0},
            number={'prefix': "$"}
        ),
        row=2, col=1
    )
    
    # Risk breakdown
    risks = ['Dollar Delta', 'Gamma Risk', 'Vega Exposure']
    risk_values = [
        abs(aggregate.get('dollar_delta', 0)) / 1000,  # In thousands
        aggregate.get('gamma_risk', 0),
        abs(aggregate.get('vega_exposure', 0)) * 100
    ]
    
    fig.add_trace(
        go.Bar(x=risks, y=risk_values, marker_color='#2196F3', name='Risk ($)'),
        row=2, col=2
    )
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.8)',
        height=600,
        showlegend=False,
        title_text="Portfolio Greeks Dashboard"
    )
    
    return fig


def create_scenario_heatmap(pnl_matrix: pd.DataFrame) -> go.Figure:
    """Create P&L scenario heatmap."""
    if pnl_matrix.empty:
        fig = go.Figure()
        fig.add_annotation(text="No scenario data", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template='plotly_dark')
        return fig
    
    fig = go.Figure(data=go.Heatmap(
        z=pnl_matrix.values,
        x=pnl_matrix.columns.tolist(),
        y=pnl_matrix.index.tolist(),
        colorscale='RdYlGn',
        zmid=0,
        text=pnl_matrix.values,
        texttemplate="$%{text:.0f}",
        textfont={"size": 10},
        hovertemplate='Price: %{y}<br>IV: %{x}<br>P&L: $%{z:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title="P&L Scenario Matrix (Price vs IV Change)",
        xaxis_title="IV Change",
        yaxis_title="Price Change",
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        height=400
    )
    
    return fig


def create_greeks_heatmap(chain_data: pd.DataFrame, greek: str = 'delta') -> go.Figure:
    """Create Greeks heatmap by strike and expiration."""
    if chain_data is None or chain_data.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template='plotly_dark')
        return fig
    
    try:
        # Pivot data
        pivot = chain_data.pivot_table(
            values=greek,
            index='strike',
            columns='expiration',
            aggfunc='mean'
        )
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale='RdBu',
            zmid=0,
            hovertemplate='Strike: %{y}<br>Exp: %{x}<br>' + greek.title() + ': %{z:.4f}<extra></extra>'
        ))
        
        fig.update_layout(
            title=f"{greek.title()} Heatmap (Strike × Expiration)",
            xaxis_title="Expiration",
            yaxis_title="Strike",
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            height=500
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"Greeks heatmap error: {e}")
        fig = go.Figure()
        fig.add_annotation(text=f"Error: {e}", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template='plotly_dark')
        return fig


# Singleton instance
_portfolio_greeks = None

def get_portfolio_greeks() -> PortfolioGreeks:
    """Get singleton portfolio Greeks instance."""
    global _portfolio_greeks
    if _portfolio_greeks is None:
        _portfolio_greeks = PortfolioGreeks()
    return _portfolio_greeks
