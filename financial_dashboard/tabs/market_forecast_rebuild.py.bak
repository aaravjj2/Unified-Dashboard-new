"""
Market Forecast Tab - Local-First Rebuild
==========================================

Agent-1B: Complete rebuild with deterministic fixtures, Bento integration,
and zero Azure dependencies by default.

Architecture:
- UI: Three-panel layout (Inputs, Results, Explainability)
- Backend: Bento-first model serving with HTTP adapter
- Persistence: PostgreSQL or JSON fallback
- Deterministic mode: FORECAST_DETERMINISTIC=1

Component IDs (stable):
- Inputs: mf-ticker-input, mf-horizon-select, mf-confidence-select, mf-model-select, mf-run-btn, mf-mode-select
- Results: mf-forecast-chart, mf-forecast-table, mf-forecast-download-btn
- Explain: mf-explain-chart, mf-explain-download-btn
- Status: mf-status-banner, mf-last-run-ts
"""

import logging
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

logger = logging.getLogger(__name__)

# Component IDs (exported for callbacks)
COMPONENT_IDS = {
    # Inputs panel
    'ticker_input': 'mf-ticker-input',
    'horizon_select': 'mf-horizon-select',
    'confidence_select': 'mf-confidence-select',
    'model_select': 'mf-model-select',
    'run_btn': 'mf-run-btn',
    'mode_select': 'mf-mode-select',
    
    # Results panel
    'forecast_chart': 'mf-forecast-chart',
    'forecast_table': 'mf-forecast-table',
    'forecast_download_btn': 'mf-forecast-download-btn',
    
    # Explainability panel
    'explain_chart': 'mf-explain-chart',
    'explain_download_btn': 'mf-explain-download-btn',
    
    # Status/diagnostics
    'status_banner': 'mf-status-banner',
    'last_run_ts': 'mf-last-run-ts',
    
    # Stores
    'forecast_store': 'mf-forecast-store',
    'explain_store': 'mf-explain-store',
}


def create_inputs_panel():
    """
    Panel 1: Inputs - ticker, horizon, confidence, model, run button
    """
    return dbc.Card([
        dbc.CardHeader(html.H5("📊 Forecast Inputs", className="mb-0")),
        dbc.CardBody([
            # Ticker selection
            dbc.Row([
                dbc.Col([
                    html.Label("Ticker", className="small fw-bold"),
                    dcc.Input(
                        id=COMPONENT_IDS['ticker_input'],
                        type="text",
                        placeholder="SPY",
                        value="SPY",
                        className="form-control form-control-sm"
                    )
                ], width=6),
                dbc.Col([
                    html.Label("Horizon", className="small fw-bold"),
                    dcc.Dropdown(
                        id=COMPONENT_IDS['horizon_select'],
                        options=[
                            {'label': '1 Week', 'value': 7},
                            {'label': '1 Month', 'value': 30},
                            {'label': '3 Months', 'value': 90},
                        ],
                        value=30,
                        clearable=False,
                        className="form-select-sm"
                    )
                ], width=6),
            ], className="mb-3"),
            
            # Confidence & Model
            dbc.Row([
                dbc.Col([
                    html.Label("Confidence Level", className="small fw-bold"),
                    dcc.Dropdown(
                        id=COMPONENT_IDS['confidence_select'],
                        options=[
                            {'label': '90%', 'value': 0.90},
                            {'label': '95%', 'value': 0.95},
                            {'label': '99%', 'value': 0.99},
                        ],
                        value=0.95,
                        clearable=False,
                        className="form-select-sm"
                    )
                ], width=6),
                dbc.Col([
                    html.Label("Model Version", className="small fw-bold"),
                    dcc.Dropdown(
                        id=COMPONENT_IDS['model_select'],
                        options=[
                            {'label': 'XGBoost v1.0', 'value': 'xgboost_v1'},
                            {'label': 'LSTM v1.0', 'value': 'lstm_v1'},
                        ],
                        value='xgboost_v1',
                        clearable=False,
                        className="form-select-sm"
                    )
                ], width=6),
            ], className="mb-3"),
            
            # Mode selection (sync/async)
            dbc.Row([
                dbc.Col([
                    html.Label("Execution Mode", className="small fw-bold"),
                    dcc.RadioItems(
                        id=COMPONENT_IDS['mode_select'],
                        options=[
                            {'label': ' Synchronous', 'value': 'sync'},
                            {'label': ' Asynchronous (Job Queue)', 'value': 'async'},
                        ],
                        value='sync',
                        inline=True,
                        className="small"
                    )
                ], width=12),
            ], className="mb-3"),
            
            # Run button
            dbc.Button(
                "▶ Run Forecast",
                id=COMPONENT_IDS['run_btn'],
                color="success",
                size="lg",
                className="w-100"
            ),
        ])
    ], className="h-100")


def create_results_panel():
    """
    Panel 2: Results - forecast chart, table, download
    """
    return dbc.Card([
        dbc.CardHeader([
            html.H5("📈 Forecast Results", className="mb-0 d-inline"),
            dbc.Button(
                "💾 Download",
                id=COMPONENT_IDS['forecast_download_btn'],
                size="sm",
                color="secondary",
                className="float-end"
            )
        ]),
        dbc.CardBody([
            # Forecast chart
            dcc.Loading(
                dcc.Graph(
                    id=COMPONENT_IDS['forecast_chart'],
                    figure=_empty_forecast_chart(),
                    style={'height': '350px'}
                )
            ),
            
            # Forecast summary table
            html.Div(
                id=COMPONENT_IDS['forecast_table'],
                className="mt-3"
            ),
        ])
    ], className="h-100")


def create_explain_panel():
    """
    Panel 3: Explainability - SHAP chart, download
    """
    return dbc.Card([
        dbc.CardHeader([
            html.H5("🔍 Feature Importance", className="mb-0 d-inline"),
            dbc.Button(
                "💾 Download Explain",
                id=COMPONENT_IDS['explain_download_btn'],
                size="sm",
                color="secondary",
                className="float-end"
            )
        ]),
        dbc.CardBody([
            dcc.Loading(
                dcc.Graph(
                    id=COMPONENT_IDS['explain_chart'],
                    figure=_empty_explain_chart(),
                    style={'height': '300px'}
                )
            ),
        ])
    ], className="h-100")


def _empty_forecast_chart():
    """Empty forecast chart placeholder"""
    fig = go.Figure()
    fig.add_annotation(
        text="Run forecast to see predictions",
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=14, color="#6c757d")
    )
    fig.update_layout(
        margin=dict(l=50, r=50, t=50, b=50),
        paper_bgcolor='white',
        plot_bgcolor='white',
    )
    return fig


def _empty_explain_chart():
    """Empty explain chart placeholder"""
    fig = go.Figure()
    fig.add_annotation(
        text="Run forecast to see feature importance",
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=14, color="#6c757d")
    )
    fig.update_layout(
        margin=dict(l=50, r=50, t=50, b=50),
        paper_bgcolor='white',
        plot_bgcolor='white',
    )
    return fig


def layout():
    """
    Main Market Forecast layout - three panels + status banner
    """
    return dbc.Container([
        # Header with status
        dbc.Row([
            dbc.Col([
                html.H3([
                    html.I(className="bi bi-graph-up me-2"),
                    "Market Forecast"
                ], className="mb-1"),
                html.P(
                    "Local-first predictive analytics with explainability",
                    className="text-muted small mb-3"
                )
            ], width=8),
            dbc.Col([
                html.Div(id=COMPONENT_IDS['status_banner'], className="text-end small"),
                html.Div(id=COMPONENT_IDS['last_run_ts'], className="text-end small text-muted")
            ], width=4)
        ]),
        
        # Main panels layout
        dbc.Row([
            # Inputs panel (left)
            dbc.Col([
                create_inputs_panel()
            ], width=3),
            
            # Results panel (center)
            dbc.Col([
                create_results_panel()
            ], width=6),
            
            # Explainability panel (right)
            dbc.Col([
                create_explain_panel()
            ], width=3),
        ], className="mb-4"),
        
        # Hidden stores
        dcc.Store(id=COMPONENT_IDS['forecast_store'], data=None),
        dcc.Store(id=COMPONENT_IDS['explain_store'], data=None),
        # Hidden debug element for Playwright to read store JSON
        html.Div(id='mf-store-debug', style={'display': 'none'}),
        
    ], fluid=True, className="p-4")


def register_callbacks(app):
    """
    Register Market Forecast callbacks
    
    Callbacks will be implemented in separate file to keep layout clean.
    For now, this is a placeholder that logs registration.
    """
    logger.info("Registering Market Forecast callbacks (rebuild wiring)")

    # Local imports to avoid circular dependencies at module import time
    from dash import Input, Output, State
    from dash.exceptions import PreventUpdate
    import os
    import json
    from datetime import datetime

    try:
        from services.forecast_adapter import ForecastAdapter
    except Exception:
        ForecastAdapter = None

    @app.callback(
        Output(COMPONENT_IDS['forecast_store'], 'data'),
        Output(COMPONENT_IDS['forecast_chart'], 'figure'),
        Output(COMPONENT_IDS['forecast_table'], 'children'),
        Output(COMPONENT_IDS['status_banner'], 'children'),
        Output(COMPONENT_IDS['last_run_ts'], 'children'),
        Output(COMPONENT_IDS['explain_store'], 'data'),
        Input(COMPONENT_IDS['run_btn'], 'n_clicks'),
        State(COMPONENT_IDS['ticker_input'], 'value'),
        State(COMPONENT_IDS['horizon_select'], 'value'),
        State(COMPONENT_IDS['confidence_select'], 'value'),
        State(COMPONENT_IDS['model_select'], 'value'),
        State(COMPONENT_IDS['mode_select'], 'value'),
        prevent_initial_call=True
    )
    def handle_run(n_clicks, ticker_value, horizon, confidence, model, mode):
        """Handle Run Forecast button clicks."""
        if not n_clicks:
            raise PreventUpdate

        # Normalize inputs
        tickers = []
        if isinstance(ticker_value, str) and ticker_value.strip():
            tickers = [t.strip().upper() for t in ticker_value.split(',') if t.strip()]
        if not tickers:
            return None, _empty_forecast_chart(), html.Div("No ticker provided."), "", "", None

        try:
            horizon_int = int(horizon)
        except Exception:
            horizon_int = 30

        try:
            confidence_float = float(confidence)
        except Exception:
            confidence_float = 0.95

        # Prepare adapter
        bento_url = os.getenv('MARKET_FORECAST_URL', os.getenv('MARKET_FORECAST_BENTO_URL', 'http://localhost:5001/predict'))
        deterministic = os.getenv('MARKET_FORECAST_DETERMINISTIC', '0') in ('1', 'true', 'True')

        if ForecastAdapter is None:
            # Adapter missing - return a helpful message
            status = dbc.Alert("Forecast service adapter not available on server.", color="danger")
            return None, _empty_forecast_chart(), html.Div("Adapter missing"), status, datetime.utcnow().isoformat(), None

        adapter = ForecastAdapter(bento_url=bento_url, deterministic=deterministic)

        # Run forecasts for all requested tickers and aggregate results
        all_results = []
        explanations = {}
        series_traces = []
        details_children = []

        for t in tickers:
            fid_t = f"mf-{t}-{int(datetime.utcnow().timestamp())}"
            try:
                if mode == 'async':
                    resp = adapter.queue_forecast(t, horizon_int, confidence_float, model, fid_t)
                    fr = resp.get('result') if isinstance(resp, dict) and resp.get('result') else resp
                else:
                    fr = adapter.run_forecast(t, horizon_int, confidence_float, model, fid_t)

                if fr is None:
                    details_children.append(html.Div(f"{t}: no result"))
                    continue

                all_results.append(fr)

                # extract time series forecast (list) if present
                s = fr.get('forecast') or []
                if s:
                    series_traces.append({'x': list(range(1, len(s) + 1)), 'y': s, 'type': 'line', 'name': t})

                # details block per ticker
                try:
                    meta = {k: fr.get(k) for k in ('ticker', 'horizon', 'confidence', 'forecast_id', 'timestamp')}
                    details_children.append(html.Div([html.H6(f"{t}"), html.Pre(json.dumps(meta, indent=2))]))
                except Exception:
                    details_children.append(html.Div(f"{t}: no details"))

                # explanation if available
                try:
                    expl = adapter.get_explanation(fr.get('forecast_id') or fid_t)
                    if expl:
                        explanations[fr.get('forecast_id') or fid_t] = expl
                except Exception:
                    pass

            except Exception as e:
                logger.exception(f"Error forecasting {t}: {e}")
                details_children.append(html.Div(f"{t}: error - {e}"))

        # Build combined figure
        if series_traces:
            fig = {'data': series_traces, 'layout': {'title': 'Forecasts', 'height': 380, 'yaxis': {'tickformat': '.2%'}}}
        else:
            fig = _empty_forecast_chart()

        # Build details container
        details = html.Div(details_children) if details_children else html.Div("No details available")

        status = dbc.Alert(f"Generated forecasts for {len(all_results)} tickers", color="success", duration=5000)
        ts = datetime.utcnow().isoformat()

        # Return aggregated result and explanations map
        return all_results, fig, details, status, ts, explanations

    # Client-side helper: mirror store data to a hidden div and window for Playwright
    try:
        app.clientside_callback(
            """
            function(store_data) {
                try { window.__mf_forecast_store__ = store_data || null; } catch(e) {}
                return '';
            }
            """,
            Output('mf-store-debug', 'children'),
            Input(COMPONENT_IDS['forecast_store'], 'data')
        )
    except Exception:
        # If clientside callbacks aren't available in this environment, ignore
        logger.exception('Failed to register clientside store mirror')


__all__ = ['layout', 'register_callbacks', 'COMPONENT_IDS']
