from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from src.ui.data_connector import connector
from src.ui.components.backtest_viewer import create_backtest_viewer
from src.ui.components.strategy_builder import create_strategy_builder
from src.ui.components.execution_controls import create_execution_controls
from src.ui.components.websocket_connector import connector as ws_connector
import plotly.graph_objects as go

def create_market_state_card():
    """
    Displays Market Regime and Sentiment.
    """
    return dbc.Card([
        dbc.CardHeader("Market State (Phase 3 AI)"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H5("Market Regime", className="card-title"),
                    html.H3("Loading...", id="p3-regime-display", className="text-primary"),
                    html.Small("Confidence: ", className="text-muted"),
                    html.Span("0%", id="p3-regime-confidence")
                ], width=6),
                dbc.Col([
                    html.H5("News Sentiment", className="card-title"),
                    html.H3("Loading...", id="p3-sentiment-display", className="text-info"),
                    html.Small("Score: ", className="text-muted"),
                    html.Span("0.0", id="p3-sentiment-score")
                ], width=6),
            ])
        ])
    ], className="mb-3")

def create_portfolio_metrics_grid():
    """
    Displays Real-time Greeks and P&L.
    """
    return html.Div([
        dbc.Row([
            dbc.Col(create_metric_box("Net P/L", "p3-pl-display", "💰"), width=3),
            dbc.Col(create_metric_box("Portfolio Delta", "p3-delta-display", "Δ"), width=3),
            dbc.Col(create_metric_box("Portfolio Theta", "p3-theta-display", "Θ"), width=3),
            dbc.Col(create_metric_box("Daily Var (95%)", "p3-var-display", "⚠️"), width=3),
        ], className="mb-3")
    ])

def create_metric_box(title, id_name, icon):
    return dbc.Card([
        dbc.CardBody([
            html.H6([icon, " ", title], className="card-subtitle text-muted mb-2"),
            html.H3("...", id=id_name, className="card-text")
        ])
    ])

def create_system_health_bar():
    """
    Displays system component health.
    """
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col(html.Div([html.Span("API: ", className="fw-bold"), html.Span("Checking...", id="p3-health-api")]), width=2),
                dbc.Col(html.Div([html.Span("Database: ", className="fw-bold"), html.Span("Checking...", id="p3-health-db")]), width=2),
                dbc.Col(html.Div([html.Span("Redis: ", className="fw-bold"), html.Span("Checking...", id="p3-health-redis")]), width=2),
                dbc.Col(html.Div([html.Span("ML Engine: ", className="fw-bold"), html.Span("Checking...", id="p3-health-ml")]), width=3),
                dbc.Col(html.Div([html.Span("Last Update: ", className="fw-bold"), html.Span("...", id="p3-last-update")]), width=3),
            ])
        ])
    ], className="mb-3 bg-light")

def create_phase3_dashboard_layout():
    """
    Assembles the full Phase 3 Dashboard.
    """
    return html.Div([
        # Interval for updates (every 2 seconds)
        dcc.Interval(id='p3-dashboard-interval', interval=2000, n_intervals=0),
        
        html.H2("🚀 Phase 3 Production Dashboard", className="mb-4"),
        
        create_system_health_bar(),
        create_market_state_card(),
        create_portfolio_metrics_grid(),
        
        # Backtest Viewer + Strategy Builder + Execution Controls
        dbc.Row([
            dbc.Col(create_backtest_viewer(), width=6),
            dbc.Col(create_strategy_builder(), width=6),
        ], className='mt-3'),
        dbc.Row([
            dbc.Col(create_execution_controls(), width=4),
            dbc.Col(html.Div(id='phase3-websocket-debug', children=[]), width=8),
        ], className='mt-3'),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Active Positions"),
                    dbc.CardBody(html.Div(id="p3-positions-table"))
                ])
            ], width=8),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Recent Orders"),
                    dbc.CardBody(html.Div(id="p3-orders-list"))
                ])
            ], width=4),
        ])
    ], className="p-4")
