"""
Options Screener - Find options by criteria

Author: Options Lab Enhancement Phase
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

logger = logging.getLogger(__name__)


# Predefined screener filters
SCREENER_PRESETS = {
    'high_iv_percentile': {
        'name': 'High IV Percentile',
        'description': 'Stocks with IV above 80th percentile',
        'filters': {'iv_percentile_min': 80}
    },
    'low_iv_percentile': {
        'name': 'Low IV Percentile',
        'description': 'Stocks with IV below 20th percentile',
        'filters': {'iv_percentile_max': 20}
    },
    'high_open_interest': {
        'name': 'High Open Interest',
        'description': 'Most liquid options by open interest',
        'filters': {'oi_min': 10000}
    },
    'unusual_volume': {
        'name': 'Unusual Volume',
        'description': 'Volume > 3x avg daily volume',
        'filters': {'volume_vs_oi_min': 1.5}
    },
    'cheap_premium': {
        'name': 'Cheap Premium',
        'description': 'Low cost options (under $2)',
        'filters': {'premium_max': 2.0}
    },
    'high_delta': {
        'name': 'High Delta (Deep ITM)',
        'description': 'Delta > 0.80',
        'filters': {'delta_min': 0.80}
    },
    'low_theta_decay': {
        'name': 'Low Theta Decay',
        'description': 'Lower time decay relative to premium',
        'filters': {'theta_premium_ratio_max': 0.02}
    },
    'earnings_plays': {
        'name': 'Earnings Plays',
        'description': 'Options expiring around earnings',
        'filters': {'near_earnings': True}
    },
    'weekly_options': {
        'name': 'Weekly Options',
        'description': 'Options expiring this week',
        'filters': {'dte_max': 7}
    },
    'leaps': {
        'name': 'LEAPS',
        'description': 'Long-term options (>6 months)',
        'filters': {'dte_min': 180}
    }
}


class OptionsScreener:
    """Screen options based on various criteria."""
    
    def __init__(self):
        self.results = pd.DataFrame()
        self.tickers_screened = []
        
    def generate_sample_data(self, tickers: List[str] = None) -> pd.DataFrame:
        """Generate sample options data for screening."""
        if tickers is None:
            tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 
                      'AMD', 'NFLX', 'SPY', 'QQQ', 'IWM', 'DIS', 'BA', 'JPM']
        
        np.random.seed(42)
        rows = []
        
        for ticker in tickers:
            spot = np.random.uniform(50, 500)
            base_iv = np.random.uniform(0.15, 0.60)
            
            for dte in [7, 14, 30, 45, 60, 90, 180, 365]:
                expiry = datetime.now() + timedelta(days=dte)
                
                for strike_pct in [0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15]:
                    strike = round(spot * strike_pct, 2)
                    
                    for opt_type in ['call', 'put']:
                        # Calculate rough Greeks and premium
                        moneyness = (spot - strike) / spot
                        if opt_type == 'put':
                            moneyness = -moneyness
                        
                        iv = base_iv * (1 + abs(moneyness) * 0.5)  # Skew
                        delta = 0.5 + moneyness * 2 if opt_type == 'call' else -0.5 + moneyness * 2
                        delta = max(-1, min(1, delta))
                        
                        gamma = 0.05 * np.exp(-moneyness**2 * 10)
                        theta = -0.01 * spot * iv / np.sqrt(max(dte, 1))
                        vega = 0.01 * spot * np.sqrt(dte / 365) * 0.5
                        
                        premium = max(0.10, abs(moneyness) * spot * 0.3 + 
                                     iv * spot * np.sqrt(dte / 365) * 0.4)
                        premium = round(premium, 2)
                        
                        oi = int(np.random.exponential(2000))
                        volume = int(oi * np.random.uniform(0.1, 2.0))
                        
                        iv_percentile = int(np.random.uniform(10, 95))
                        iv_rank = round(np.random.uniform(0.1, 0.9), 2)
                        
                        rows.append({
                            'ticker': ticker,
                            'spot': round(spot, 2),
                            'strike': strike,
                            'type': opt_type,
                            'expiry': expiry.strftime('%Y-%m-%d'),
                            'dte': dte,
                            'premium': premium,
                            'bid': round(premium * 0.98, 2),
                            'ask': round(premium * 1.02, 2),
                            'iv': round(iv, 4),
                            'iv_percentile': iv_percentile,
                            'iv_rank': iv_rank,
                            'delta': round(delta, 4),
                            'gamma': round(gamma, 4),
                            'theta': round(theta, 4),
                            'vega': round(vega, 4),
                            'open_interest': oi,
                            'volume': volume,
                            'volume_oi_ratio': round(volume / max(oi, 1), 2),
                            'theta_premium_ratio': round(abs(theta) / max(premium, 0.01), 4),
                            'moneyness': round(moneyness, 4),
                            'near_earnings': np.random.random() > 0.85
                        })
        
        self.results = pd.DataFrame(rows)
        self.tickers_screened = tickers
        return self.results
    
    def screen(self, data: pd.DataFrame = None, **filters) -> pd.DataFrame:
        """
        Screen options with various filters.
        
        Filters:
            ticker: str - specific ticker
            opt_type: str - 'call' or 'put'
            dte_min: int - minimum days to expiration
            dte_max: int - maximum days to expiration
            delta_min: float - minimum absolute delta
            delta_max: float - maximum absolute delta
            iv_min: float - minimum IV
            iv_max: float - maximum IV
            iv_percentile_min: int - minimum IV percentile
            iv_percentile_max: int - maximum IV percentile
            premium_min: float - minimum premium
            premium_max: float - maximum premium
            oi_min: int - minimum open interest
            volume_min: int - minimum volume
            volume_vs_oi_min: float - minimum volume/OI ratio
            theta_premium_ratio_max: float - max theta/premium ratio
            near_earnings: bool - near earnings date
        """
        if data is None:
            if self.results.empty:
                self.generate_sample_data()
            data = self.results.copy()
        
        df = data.copy()
        
        # Apply filters
        if 'ticker' in filters and filters['ticker']:
            df = df[df['ticker'] == filters['ticker']]
        
        if 'opt_type' in filters and filters['opt_type']:
            df = df[df['type'] == filters['opt_type']]
        
        if 'dte_min' in filters:
            df = df[df['dte'] >= filters['dte_min']]
        
        if 'dte_max' in filters:
            df = df[df['dte'] <= filters['dte_max']]
        
        if 'delta_min' in filters:
            df = df[df['delta'].abs() >= filters['delta_min']]
        
        if 'delta_max' in filters:
            df = df[df['delta'].abs() <= filters['delta_max']]
        
        if 'iv_min' in filters:
            df = df[df['iv'] >= filters['iv_min']]
        
        if 'iv_max' in filters:
            df = df[df['iv'] <= filters['iv_max']]
        
        if 'iv_percentile_min' in filters:
            df = df[df['iv_percentile'] >= filters['iv_percentile_min']]
        
        if 'iv_percentile_max' in filters:
            df = df[df['iv_percentile'] <= filters['iv_percentile_max']]
        
        if 'premium_min' in filters:
            df = df[df['premium'] >= filters['premium_min']]
        
        if 'premium_max' in filters:
            df = df[df['premium'] <= filters['premium_max']]
        
        if 'oi_min' in filters:
            df = df[df['open_interest'] >= filters['oi_min']]
        
        if 'volume_min' in filters:
            df = df[df['volume'] >= filters['volume_min']]
        
        if 'volume_vs_oi_min' in filters:
            df = df[df['volume_oi_ratio'] >= filters['volume_vs_oi_min']]
        
        if 'theta_premium_ratio_max' in filters:
            df = df[df['theta_premium_ratio'] <= filters['theta_premium_ratio_max']]
        
        if filters.get('near_earnings'):
            df = df[df['near_earnings'] == True]
        
        return df.reset_index(drop=True)
    
    def apply_preset(self, preset_name: str, data: pd.DataFrame = None) -> pd.DataFrame:
        """Apply a preset screen filter."""
        if preset_name not in SCREENER_PRESETS:
            logger.warning(f"Unknown preset: {preset_name}")
            return pd.DataFrame()
        
        preset = SCREENER_PRESETS[preset_name]
        return self.screen(data, **preset['filters'])
    
    def get_top_by_volume(self, n: int = 20, opt_type: str = None) -> pd.DataFrame:
        """Get top N options by volume."""
        filters = {'volume_min': 1}
        if opt_type:
            filters['opt_type'] = opt_type
        
        df = self.screen(**filters)
        return df.nlargest(n, 'volume')
    
    def get_top_by_open_interest(self, n: int = 20, opt_type: str = None) -> pd.DataFrame:
        """Get top N options by open interest."""
        filters = {'oi_min': 1}
        if opt_type:
            filters['opt_type'] = opt_type
        
        df = self.screen(**filters)
        return df.nlargest(n, 'open_interest')
    
    def get_unusual_activity(self, volume_oi_threshold: float = 1.5) -> pd.DataFrame:
        """Find options with unusual volume vs open interest."""
        return self.screen(volume_vs_oi_min=volume_oi_threshold).sort_values(
            'volume_oi_ratio', ascending=False
        )


def create_screener_results_chart(df: pd.DataFrame, chart_type: str = 'scatter') -> go.Figure:
    """Visualize screener results."""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No results to display", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template='plotly_dark')
        return fig
    
    if chart_type == 'scatter':
        fig = px.scatter(
            df.head(100),
            x='iv',
            y='delta',
            size='volume',
            color='iv_percentile',
            hover_data=['ticker', 'strike', 'type', 'expiry', 'premium'],
            color_continuous_scale='RdYlGn_r',
            title='Screener Results: IV vs Delta'
        )
        
    elif chart_type == 'treemap':
        fig = px.treemap(
            df.head(50),
            path=['ticker', 'type', 'expiry'],
            values='volume',
            color='iv_percentile',
            color_continuous_scale='RdYlGn_r',
            title='Screener Results by Volume'
        )
        
    elif chart_type == 'bar':
        top_vol = df.groupby('ticker')['volume'].sum().nlargest(15).reset_index()
        fig = px.bar(
            top_vol,
            x='ticker',
            y='volume',
            title='Total Option Volume by Ticker',
            color='volume',
            color_continuous_scale='Blues'
        )
    else:
        fig = go.Figure()
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.8)',
        height=450
    )
    
    return fig


def create_iv_heatmap(df: pd.DataFrame) -> go.Figure:
    """Create IV heatmap by ticker and expiration."""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template='plotly_dark')
        return fig
    
    # Pivot to create heatmap data
    pivot = df.pivot_table(
        index='ticker',
        columns='dte',
        values='iv',
        aggfunc='mean'
    )
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index,
        colorscale='RdYlGn_r',
        colorbar=dict(title='IV')
    ))
    
    fig.update_layout(
        title='IV Heatmap: Ticker vs DTE',
        xaxis_title='Days to Expiration',
        yaxis_title='Ticker',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.8)',
        height=450
    )
    
    return fig


def get_screener_presets() -> List[Dict]:
    """Get list of available screener presets."""
    return [
        {
            'id': key,
            'name': val['name'],
            'description': val['description']
        }
        for key, val in SCREENER_PRESETS.items()
    ]


# Singleton instance
_screener = None

def get_options_screener() -> OptionsScreener:
    """Get singleton screener instance."""
    global _screener
    if _screener is None:
        _screener = OptionsScreener()
        _screener.generate_sample_data()
    return _screener
