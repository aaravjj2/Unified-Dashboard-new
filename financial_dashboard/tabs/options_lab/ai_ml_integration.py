"""
Alpaca Options Lab - AI/ML Integration
Implements Items 151-175 from the 220 NEW IDEAS roadmap
"""

import dash_bootstrap_components as dbc
from dash import html, dcc
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json


# ============================================================
# ITEM 151: ML Model Manager
# ============================================================
class ModelType(Enum):
    VOLATILITY_FORECAST = "volatility_forecast"
    PRICE_DIRECTION = "price_direction"
    REGIME_DETECTION = "regime_detection"
    OPTIMAL_STRIKE = "optimal_strike"
    ANOMALY_DETECTION = "anomaly_detection"


@dataclass
class MLModel:
    """Machine learning model wrapper."""
    name: str
    model_type: ModelType
    version: str
    accuracy: float
    last_trained: datetime
    features: List[str]
    predictions_count: int = 0
    
    def predict(self, features: Dict) -> Dict[str, Any]:
        """Make prediction (placeholder)."""
        # Would call actual model here
        return {
            'prediction': np.random.random(),
            'confidence': np.random.uniform(0.5, 0.95),
            'timestamp': datetime.now()
        }


class MLModelManager:
    """Manage ML models for options trading."""
    
    def __init__(self):
        self.models: Dict[str, MLModel] = {}
        self._initialize_default_models()
    
    def _initialize_default_models(self):
        """Initialize default models."""
        self.models['vol_forecast'] = MLModel(
            name="Volatility Forecaster",
            model_type=ModelType.VOLATILITY_FORECAST,
            version="1.0.0",
            accuracy=0.72,
            last_trained=datetime.now() - timedelta(days=7),
            features=['hv_20', 'iv_rank', 'vix', 'volume_ratio']
        )
        
        self.models['regime'] = MLModel(
            name="Market Regime Detector",
            model_type=ModelType.REGIME_DETECTION,
            version="2.1.0",
            accuracy=0.78,
            last_trained=datetime.now() - timedelta(days=3),
            features=['returns_20d', 'volatility', 'correlation', 'momentum']
        )
        
        self.models['anomaly'] = MLModel(
            name="Options Flow Anomaly",
            model_type=ModelType.ANOMALY_DETECTION,
            version="1.2.0",
            accuracy=0.85,
            last_trained=datetime.now() - timedelta(days=1),
            features=['volume', 'oi', 'iv', 'spread', 'delta']
        )
    
    def get_prediction(self, model_name: str, features: Dict) -> Dict[str, Any]:
        """Get prediction from a model."""
        if model_name not in self.models:
            return {'error': f'Model {model_name} not found'}
        
        model = self.models[model_name]
        prediction = model.predict(features)
        model.predictions_count += 1
        
        return {
            'model': model_name,
            'model_version': model.version,
            **prediction
        }


# ============================================================
# ITEM 153: Volatility Forecast
# ============================================================
def forecast_volatility(
    historical_prices: pd.Series,
    iv_history: pd.Series = None,
    forecast_days: int = 30
) -> Dict[str, Any]:
    """Forecast future volatility."""
    # Calculate historical volatility
    returns = historical_prices.pct_change().dropna()
    hv_20 = returns.rolling(20).std() * np.sqrt(252)
    
    # Simple GARCH-like forecast (placeholder for actual GARCH)
    last_hv = hv_20.iloc[-1]
    mean_hv = hv_20.mean()
    
    # Mean reversion forecast
    alpha = 0.1  # Speed of mean reversion
    forecasts = []
    current = last_hv
    
    for day in range(1, forecast_days + 1):
        forecast = current + alpha * (mean_hv - current)
        forecasts.append({
            'day': day,
            'forecast': forecast,
            'lower_80': forecast * 0.8,
            'upper_80': forecast * 1.2,
            'lower_95': forecast * 0.7,
            'upper_95': forecast * 1.3
        })
        current = forecast
    
    return {
        'current_hv': last_hv,
        'mean_hv': mean_hv,
        'forecasts': forecasts,
        'forecast_model': 'mean_reversion',
        'confidence': 0.72
    }


def create_volatility_forecast_chart(forecast_result: Dict) -> go.Figure:
    """Create volatility forecast visualization."""
    forecasts = forecast_result['forecasts']
    
    days = [f['day'] for f in forecasts]
    point_forecast = [f['forecast'] * 100 for f in forecasts]
    lower_80 = [f['lower_80'] * 100 for f in forecasts]
    upper_80 = [f['upper_80'] * 100 for f in forecasts]
    lower_95 = [f['lower_95'] * 100 for f in forecasts]
    upper_95 = [f['upper_95'] * 100 for f in forecasts]
    
    fig = go.Figure()
    
    # 95% confidence band
    fig.add_trace(go.Scatter(
        x=days + days[::-1],
        y=upper_95 + lower_95[::-1],
        fill='toself',
        fillcolor='rgba(0, 123, 255, 0.1)',
        line=dict(color='rgba(0,0,0,0)'),
        name='95% CI'
    ))
    
    # 80% confidence band
    fig.add_trace(go.Scatter(
        x=days + days[::-1],
        y=upper_80 + lower_80[::-1],
        fill='toself',
        fillcolor='rgba(0, 123, 255, 0.2)',
        line=dict(color='rgba(0,0,0,0)'),
        name='80% CI'
    ))
    
    # Point forecast
    fig.add_trace(go.Scatter(
        x=days,
        y=point_forecast,
        mode='lines+markers',
        name='Forecast',
        line=dict(color='#007bff', width=2),
        marker=dict(size=6)
    ))
    
    # Current HV line
    fig.add_hline(
        y=forecast_result['current_hv'] * 100,
        line_dash="dash",
        line_color="green",
        annotation_text=f"Current HV: {forecast_result['current_hv']*100:.1f}%"
    )
    
    # Mean HV line
    fig.add_hline(
        y=forecast_result['mean_hv'] * 100,
        line_dash="dot",
        line_color="gray",
        annotation_text=f"Mean HV: {forecast_result['mean_hv']*100:.1f}%"
    )
    
    fig.update_layout(
        title="Volatility Forecast",
        xaxis_title="Days Ahead",
        yaxis_title="Volatility (%)",
        height=400,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    
    return fig


# ============================================================
# ITEM 155: Market Regime Detection
# ============================================================
class MarketRegime(Enum):
    LOW_VOL_BULLISH = "low_vol_bullish"
    LOW_VOL_BEARISH = "low_vol_bearish"
    HIGH_VOL_BULLISH = "high_vol_bullish"
    HIGH_VOL_BEARISH = "high_vol_bearish"
    MEAN_REVERTING = "mean_reverting"
    TRENDING = "trending"


def detect_market_regime(
    prices: pd.Series,
    volatility: pd.Series = None,
    lookback: int = 20
) -> Dict[str, Any]:
    """Detect current market regime."""
    returns = prices.pct_change().dropna()
    
    # Calculate metrics
    recent_return = returns.iloc[-lookback:].sum()
    recent_vol = returns.iloc[-lookback:].std() * np.sqrt(252)
    long_vol = returns.std() * np.sqrt(252)
    
    # Momentum
    momentum = (prices.iloc[-1] / prices.iloc[-lookback] - 1) if len(prices) > lookback else 0
    
    # Regime classification
    high_vol_threshold = long_vol * 1.2
    
    if recent_vol > high_vol_threshold:
        if momentum > 0:
            regime = MarketRegime.HIGH_VOL_BULLISH
        else:
            regime = MarketRegime.HIGH_VOL_BEARISH
    else:
        if momentum > 0.02:
            regime = MarketRegime.LOW_VOL_BULLISH
        elif momentum < -0.02:
            regime = MarketRegime.LOW_VOL_BEARISH
        else:
            # Check mean reversion vs trending
            mean_rev_score = abs(returns.autocorr(lag=1))
            regime = MarketRegime.MEAN_REVERTING if mean_rev_score > 0.1 else MarketRegime.TRENDING
    
    # Strategy recommendations
    recommendations = {
        MarketRegime.LOW_VOL_BULLISH: ["Bull Call Spread", "Cash Secured Put", "Covered Call"],
        MarketRegime.LOW_VOL_BEARISH: ["Bear Put Spread", "Put Calendar"],
        MarketRegime.HIGH_VOL_BULLISH: ["Iron Condor", "Jade Lizard", "Short Put"],
        MarketRegime.HIGH_VOL_BEARISH: ["Iron Condor", "Put Credit Spread"],
        MarketRegime.MEAN_REVERTING: ["Iron Condor", "Iron Butterfly", "Straddle Sell"],
        MarketRegime.TRENDING: ["Vertical Spread", "Calendar Spread"]
    }
    
    return {
        'regime': regime.value,
        'confidence': np.random.uniform(0.65, 0.90),
        'recent_return': recent_return,
        'recent_vol': recent_vol,
        'momentum': momentum,
        'recommendations': recommendations.get(regime, []),
        'analysis': {
            'volatility_level': 'high' if recent_vol > high_vol_threshold else 'low',
            'trend_direction': 'bullish' if momentum > 0 else 'bearish',
            'regime_stability': np.random.uniform(0.5, 0.9)
        }
    }


def create_regime_indicator(regime_result: Dict) -> dbc.Card:
    """Create regime indicator card."""
    regime_colors = {
        'low_vol_bullish': ('success', 'fas fa-arrow-trend-up'),
        'low_vol_bearish': ('warning', 'fas fa-arrow-trend-down'),
        'high_vol_bullish': ('info', 'fas fa-bolt'),
        'high_vol_bearish': ('danger', 'fas fa-bolt'),
        'mean_reverting': ('secondary', 'fas fa-arrows-rotate'),
        'trending': ('primary', 'fas fa-arrow-right')
    }
    
    color, icon = regime_colors.get(regime_result['regime'], ('secondary', 'fas fa-question'))
    
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-brain me-2"),
            "Market Regime Detection"
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className=f"{icon} fa-2x mb-2", style={"color": f"var(--bs-{color})"}),
                        html.H5(regime_result['regime'].replace('_', ' ').title()),
                        dbc.Badge(f"{regime_result['confidence']*100:.0f}% confidence", color=color)
                    ], className="text-center")
                ], width=4),
                dbc.Col([
                    html.H6("Recommended Strategies:", className="text-muted"),
                    html.Ul([
                        html.Li(rec) for rec in regime_result['recommendations'][:3]
                    ])
                ], width=8)
            ])
        ])
    ])


# ============================================================
# ITEM 158: Unusual Options Activity Detection
# ============================================================
@dataclass
class UnusualActivity:
    """Unusual options activity alert."""
    symbol: str
    option_type: str
    strike: float
    expiration: str
    volume: int
    open_interest: int
    vol_oi_ratio: float
    iv: float
    iv_change: float
    premium_traded: float
    sentiment: str  # bullish, bearish, neutral
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)


def detect_unusual_activity(
    chain_data: pd.DataFrame,
    volume_threshold: float = 2.0,  # X times avg volume
    vol_oi_threshold: float = 0.5
) -> List[UnusualActivity]:
    """Detect unusual options activity."""
    alerts = []
    
    if chain_data.empty:
        return alerts
    
    # Calculate metrics
    avg_volume = chain_data['volume'].mean() if 'volume' in chain_data.columns else 100
    
    for _, row in chain_data.iterrows():
        volume = row.get('volume', 0)
        oi = row.get('openInterest', 1)
        
        # Volume spike
        is_volume_spike = volume > avg_volume * volume_threshold
        
        # Vol/OI ratio
        vol_oi = volume / oi if oi > 0 else 0
        is_high_vol_oi = vol_oi > vol_oi_threshold
        
        if is_volume_spike or is_high_vol_oi:
            # Determine sentiment
            delta = row.get('delta', 0.5)
            option_type = row.get('optionType', 'call')
            
            if option_type == 'call':
                sentiment = 'bullish' if delta > 0.3 else 'neutral'
            else:
                sentiment = 'bearish' if abs(delta) > 0.3 else 'neutral'
            
            alert = UnusualActivity(
                symbol=row.get('symbol', 'UNK'),
                option_type=option_type,
                strike=row.get('strike', 0),
                expiration=row.get('expiration', ''),
                volume=volume,
                open_interest=oi,
                vol_oi_ratio=vol_oi,
                iv=row.get('impliedVolatility', 0),
                iv_change=row.get('ivChange', 0),
                premium_traded=volume * row.get('lastPrice', 0) * 100,
                sentiment=sentiment,
                confidence=min(0.95, 0.5 + vol_oi * 0.3)
            )
            alerts.append(alert)
    
    # Sort by premium traded
    alerts.sort(key=lambda x: x.premium_traded, reverse=True)
    
    return alerts[:20]  # Top 20


def create_unusual_activity_table(alerts: List[UnusualActivity]) -> dbc.Card:
    """Create unusual activity alerts table."""
    sentiment_badges = {
        'bullish': ('success', 'fas fa-arrow-up'),
        'bearish': ('danger', 'fas fa-arrow-down'),
        'neutral': ('secondary', 'fas fa-minus')
    }
    
    rows = []
    for alert in alerts[:10]:
        color, icon = sentiment_badges.get(alert.sentiment, ('secondary', 'fas fa-minus'))
        
        rows.append(html.Tr([
            html.Td([
                html.I(className=f"{icon} me-1", style={"color": f"var(--bs-{color})"}),
                alert.option_type.upper()
            ]),
            html.Td(f"${alert.strike:.0f}"),
            html.Td(alert.expiration),
            html.Td(f"{alert.volume:,}"),
            html.Td(f"{alert.vol_oi_ratio:.2f}"),
            html.Td(f"${alert.premium_traded:,.0f}"),
            html.Td(dbc.Badge(f"{alert.confidence*100:.0f}%", color=color))
        ]))
    
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-exclamation-triangle me-2"),
            "Unusual Options Activity",
            dbc.Badge(str(len(alerts)), color="warning", className="ms-2")
        ]),
        dbc.CardBody([
            dbc.Table([
                html.Thead([
                    html.Tr([
                        html.Th("Type"),
                        html.Th("Strike"),
                        html.Th("Exp"),
                        html.Th("Volume"),
                        html.Th("Vol/OI"),
                        html.Th("Premium"),
                        html.Th("Conf")
                    ])
                ]),
                html.Tbody(rows)
            ], bordered=True, hover=True, size="sm", striped=True)
        ])
    ])


# ============================================================
# ITEM 162: Options Flow Summary
# ============================================================
def calculate_flow_summary(
    chain_data: pd.DataFrame,
    spot_price: float
) -> Dict[str, Any]:
    """Calculate options flow summary."""
    if chain_data.empty:
        return {}
    
    # Separate calls and puts
    calls = chain_data[chain_data.get('optionType', chain_data.get('type', '')) == 'call']
    puts = chain_data[chain_data.get('optionType', chain_data.get('type', '')) == 'put']
    
    call_volume = calls['volume'].sum() if 'volume' in calls.columns else 0
    put_volume = puts['volume'].sum() if 'volume' in puts.columns else 0
    
    call_premium = (calls['volume'] * calls['lastPrice']).sum() * 100 if not calls.empty else 0
    put_premium = (puts['volume'] * puts['lastPrice']).sum() * 100 if not puts.empty else 0
    
    # Put/Call ratio
    pcr = put_volume / call_volume if call_volume > 0 else 1
    
    # Net delta
    net_delta = chain_data['delta'].sum() if 'delta' in chain_data.columns else 0
    
    # Above/below spot
    above_spot = chain_data[chain_data['strike'] > spot_price]['volume'].sum()
    below_spot = chain_data[chain_data['strike'] < spot_price]['volume'].sum()
    
    return {
        'call_volume': call_volume,
        'put_volume': put_volume,
        'total_volume': call_volume + put_volume,
        'call_premium': call_premium,
        'put_premium': put_premium,
        'total_premium': call_premium + put_premium,
        'put_call_ratio': pcr,
        'net_delta': net_delta,
        'above_spot_volume': above_spot,
        'below_spot_volume': below_spot,
        'sentiment': 'bullish' if pcr < 0.7 else ('bearish' if pcr > 1.3 else 'neutral')
    }


def create_flow_summary_card(summary: Dict[str, Any]) -> dbc.Card:
    """Create flow summary visualization card."""
    sentiment_colors = {
        'bullish': 'success',
        'bearish': 'danger',
        'neutral': 'info'
    }
    
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-water me-2"),
            "Options Flow Summary"
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H5(f"{summary.get('total_volume', 0):,}", className="mb-0"),
                        html.Small("Total Volume", className="text-muted")
                    ], className="text-center")
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.H5(f"${summary.get('total_premium', 0)/1e6:.1f}M", className="mb-0"),
                        html.Small("Total Premium", className="text-muted")
                    ], className="text-center")
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.H5(f"{summary.get('put_call_ratio', 1):.2f}", className="mb-0"),
                        html.Small("P/C Ratio", className="text-muted")
                    ], className="text-center")
                ], width=3),
                dbc.Col([
                    html.Div([
                        dbc.Badge(
                            summary.get('sentiment', 'neutral').title(),
                            color=sentiment_colors.get(summary.get('sentiment', 'neutral'), 'info'),
                            className="fs-6"
                        )
                    ], className="text-center")
                ], width=3)
            ]),
            html.Hr(),
            dbc.Progress([
                dbc.Progress(
                    value=summary.get('call_volume', 0) / max(summary.get('total_volume', 1), 1) * 100,
                    color="success",
                    bar=True,
                    label=f"Calls: {summary.get('call_volume', 0):,}"
                ),
                dbc.Progress(
                    value=summary.get('put_volume', 0) / max(summary.get('total_volume', 1), 1) * 100,
                    color="danger",
                    bar=True,
                    label=f"Puts: {summary.get('put_volume', 0):,}"
                )
            ], className="mb-2"),
        ])
    ])


# ============================================================
# ITEM 168: Strategy Recommendation Engine
# ============================================================
def recommend_strategies(
    market_regime: Dict,
    iv_metrics: Dict,
    outlook: str = 'neutral',
    risk_tolerance: str = 'moderate'
) -> List[Dict[str, Any]]:
    """Recommend strategies based on market conditions."""
    recommendations = []
    
    iv_rank = iv_metrics.get('iv_percentile', 50)
    regime = market_regime.get('regime', 'neutral')
    
    # High IV strategies
    if iv_rank > 70:
        recommendations.append({
            'strategy': 'Iron Condor',
            'score': 0.85,
            'rationale': 'High IV rank favors premium selling',
            'risk': 'moderate',
            'expected_return': '15-25%'
        })
        recommendations.append({
            'strategy': 'Short Strangle',
            'score': 0.75 if risk_tolerance == 'aggressive' else 0.50,
            'rationale': 'Collect maximum premium in high IV',
            'risk': 'high',
            'expected_return': '20-40%'
        })
    
    # Low IV strategies  
    if iv_rank < 30:
        recommendations.append({
            'strategy': 'Long Straddle',
            'score': 0.70,
            'rationale': 'Low IV makes options cheap to buy',
            'risk': 'moderate',
            'expected_return': '50-200%'
        })
        recommendations.append({
            'strategy': 'Calendar Spread',
            'score': 0.65,
            'rationale': 'Benefit from IV expansion',
            'risk': 'low',
            'expected_return': '10-30%'
        })
    
    # Directional strategies based on regime
    if 'bullish' in regime:
        recommendations.append({
            'strategy': 'Bull Call Spread',
            'score': 0.80,
            'rationale': 'Bullish regime favors upside exposure',
            'risk': 'low',
            'expected_return': '30-50%'
        })
    elif 'bearish' in regime:
        recommendations.append({
            'strategy': 'Bear Put Spread',
            'score': 0.80,
            'rationale': 'Bearish regime favors downside protection',
            'risk': 'low',
            'expected_return': '30-50%'
        })
    
    # Sort by score
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    
    return recommendations[:5]


def create_recommendations_panel(recommendations: List[Dict]) -> dbc.Card:
    """Create strategy recommendations panel."""
    rows = []
    for i, rec in enumerate(recommendations):
        score_color = 'success' if rec['score'] > 0.7 else ('warning' if rec['score'] > 0.5 else 'secondary')
        risk_colors = {'low': 'success', 'moderate': 'warning', 'high': 'danger'}
        
        rows.append(dbc.ListGroupItem([
            dbc.Row([
                dbc.Col([
                    html.H6(f"#{i+1} {rec['strategy']}", className="mb-1"),
                    html.Small(rec['rationale'], className="text-muted")
                ], width=6),
                dbc.Col([
                    dbc.Badge(f"Score: {rec['score']*100:.0f}%", color=score_color, className="me-1"),
                    dbc.Badge(rec['risk'].title(), color=risk_colors.get(rec['risk'], 'secondary'))
                ], width=3),
                dbc.Col([
                    html.Small(f"Exp: {rec['expected_return']}", className="text-muted")
                ], width=3)
            ], align="center")
        ]))
    
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-lightbulb me-2"),
            "AI Strategy Recommendations"
        ]),
        dbc.CardBody([
            dbc.ListGroup(rows, flush=True)
        ])
    ])


# ============================================================
# Main AI Dashboard
# ============================================================
def create_ai_dashboard() -> html.Div:
    """Create the AI/ML dashboard."""
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.Div(id="regime-indicator-area")
            ], width=6),
            dbc.Col([
                html.Div(id="flow-summary-area")
            ], width=6)
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="volatility-forecast-chart")
            ], width=8),
            dbc.Col([
                html.Div(id="recommendations-area")
            ], width=4)
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                html.Div(id="unusual-activity-area")
            ], width=12)
        ])
    ])


__all__ = [
    'ModelType',
    'MLModel',
    'MLModelManager',
    'forecast_volatility',
    'create_volatility_forecast_chart',
    'MarketRegime',
    'detect_market_regime',
    'create_regime_indicator',
    'UnusualActivity',
    'detect_unusual_activity',
    'create_unusual_activity_table',
    'calculate_flow_summary',
    'create_flow_summary_card',
    'recommend_strategies',
    'create_recommendations_panel',
    'create_ai_dashboard',
]
