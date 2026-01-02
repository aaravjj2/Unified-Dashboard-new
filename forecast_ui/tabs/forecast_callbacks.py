"""
ML Forecast Callbacks - Phase 2 Forecast Engine

Wires the forecast UI to the predictor engine:
- Refresh Forecast button triggers new inference
- Updates Signal Gauge, Price Path Chart, Regime Badge
- Updates Smart Hint with strategy recommendation
"""

import logging
from datetime import datetime
from typing import Dict, Any

import dash
from dash import Input, Output, State, callback, html, dcc, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

# Import ML engine
from engines.ml.predictor import (
    get_price_predictor,
    get_vol_predictor,
    get_hint_generator,
    PricePrediction,
    VolatilityPrediction
)

# Import UI components
from forecast_ui.tabs.forecasts import (
    create_signal_gauge,
    create_price_path_chart,
    create_regime_badge,
    create_smart_hint_card
)

logger = logging.getLogger(__name__)


def register_forecast_callbacks(app: dash.Dash):
    """Register all ML Forecast callbacks."""
    
    @app.callback(
        [
            Output('gauge-signal', 'figure'),
            Output('chart-prediction', 'figure'),
            Output('badge-regime', 'children'),
            Output('metric-direction', 'children'),
            Output('metric-direction', 'style'),
            Output('metric-confidence', 'children'),
            Output('metric-change', 'children'),
            Output('metric-change', 'style'),
            Output('smart-hint-container', 'children'),
            Output('vol-current-iv', 'children'),
            Output('vol-forecast-iv', 'children'),
            Output('vol-iv-rank', 'children'),
            Output('vol-regime', 'children'),
            Output('forecast-last-updated', 'children'),
            Output('forecast-data-store', 'data')
        ],
        Input('refresh-forecast-btn', 'n_clicks'),
        [
            State('forecast-ticker-input', 'value'),
            State('forecast-price-input', 'value')
        ],
        prevent_initial_call=False
    )
    def refresh_forecast(n_clicks, ticker, current_price):
        """
        Handle Refresh Forecast button click.
        
        Triggers new inference and updates all UI components:
        - Signal Strength Gauge
        - Predicted Price Path Chart
        - Regime Classification Badge
        - Direction/Confidence/Change metrics
        - Smart Hint Card
        - Volatility metrics
        - Last Updated timestamp
        """
        # Default values
        ticker = ticker or "SPY"
        current_price = float(current_price) if current_price else 450.0
        
        try:
            # Get predictors
            price_predictor = get_price_predictor()
            vol_predictor = get_vol_predictor()
            hint_generator = get_hint_generator()
            
            # Generate predictions
            price_pred = price_predictor.predict(
                ticker=ticker,
                current_price=current_price,
                horizon_days=7
            )
            
            vol_pred = vol_predictor.predict(
                ticker=ticker,
                horizon_days=7
            )
            
            # Generate smart hint
            hint = hint_generator.generate_hint(price_pred, vol_pred)
            
            # Create updated UI components
            gauge_fig = create_signal_gauge(
                signal_strength=price_pred.signal_strength,
                direction=price_pred.direction.value
            )
            
            chart_fig = create_price_path_chart(
                timestamps=price_pred.timestamps,
                price_path=price_pred.price_path,
                current_price=price_pred.current_price,
                target_price=price_pred.target_price,
                ticker=ticker
            )
            
            regime_badge = create_regime_badge(price_pred.regime.value)
            
            # Direction styling
            direction_colors = {
                "BULLISH": "#4caf50",
                "BEARISH": "#f44336",
                "NEUTRAL": "#ff9800"
            }
            direction_color = direction_colors.get(price_pred.direction.value, "#ff9800")
            direction_style = {'color': direction_color, 'fontSize': '18px', 'fontWeight': 'bold'}
            
            # Change styling
            change_color = "#4caf50" if price_pred.change_pct >= 0 else "#f44336"
            change_style = {'color': change_color, 'fontSize': '18px', 'fontWeight': 'bold'}
            
            # Smart hint card
            smart_hint = create_smart_hint_card(hint)
            
            # Timestamp
            last_updated = f"Last Updated: {datetime.now().strftime('%H:%M:%S')}"
            
            # Store data for potential use
            forecast_data = {
                'price_prediction': price_predictor.to_dict(price_pred),
                'vol_prediction': vol_predictor.to_dict(vol_pred),
                'hint': hint
            }
            
            return (
                gauge_fig,
                chart_fig,
                regime_badge,
                price_pred.direction.value,
                direction_style,
                f"{price_pred.confidence:.0f}%",
                f"{price_pred.change_pct:+.1f}%",
                change_style,
                smart_hint,
                f"{vol_pred.current_iv:.1f}%",
                f"{vol_pred.forecast_iv:.1f}%",
                f"{vol_pred.iv_rank:.0f}%",
                vol_pred.vol_regime,
                last_updated,
                forecast_data
            )
            
        except Exception as e:
            logger.error(f"Forecast error: {e}")
            # Return default values on error
            return (
                create_signal_gauge(0, "NEUTRAL"),
                create_price_path_chart(),
                create_regime_badge("CRAB"),
                "ERROR",
                {'color': '#f44336', 'fontSize': '18px', 'fontWeight': 'bold'},
                "0%",
                "0%",
                {'color': '#6b7280', 'fontSize': '18px', 'fontWeight': 'bold'},
                create_smart_hint_card({"recommended_strategy": f"Error: {str(e)[:50]}", "description": "", "icon": "❌", "color": "#f44336", "confidence": 0, "price_direction": "N/A", "vol_regime": "N/A"}),
                "--",
                "--",
                "--",
                "--",
                f"Error at {datetime.now().strftime('%H:%M:%S')}",
                {}
            )
