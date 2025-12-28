"""
Options Lab - Overhauled Layout (v2)
=====================================
Consolidated from 12 subtabs to 5 streamlined tabs:
1. Chain Viewer (kept as requested)
2. Analysis Hub (combines Greeks, IV Analysis, Flow Scanner)
3. Strategy Lab (combines Strategy Builder, Manual Trade, Backtester)
4. AI Recommendations (enhanced with full trade details)
5. Portfolio & Journal

Each subtab now has enhanced detail displays.
"""

import logging
from datetime import datetime, timedelta
from dash import dcc, html
import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)

# Color scheme
COLORS = {
    'background': '#1a1a2e',
    'card': '#16213e',
    'accent': '#0f3460',
    'primary': '#3b82f6',
    'success': '#10b981',
    'warning': '#f59e0b',
    'danger': '#ef4444',
    'text': '#e5e5e5',
}


def _tab_shell(tab_id: str, content_fn, display_name: str = ""):
    """Wrap subtab content in error boundary."""
    try:
        return content_fn()
    except Exception as e:
        logger.error(f"Error creating {tab_id}: {e}")
        return dbc.Alert(
            f"⚠️ Error loading {display_name or tab_id}: {str(e)}",
            color="danger",
            className="m-3"
        )


def create_layout():
    """Create the consolidated Options Lab layout."""
    try:
        return _build_main_layout()
    except Exception as e:
        logger.error(f"Options Lab layout failed: {e}")
        return _error_fallback(e)


def _build_main_layout():
    """Build main Options Lab layout with consolidated tabs."""
    return dbc.Container([
        # Hidden stores for state management
        dcc.Store(id='options-chain-store', storage_type='memory'),
        dcc.Store(id='options-analysis-store', storage_type='memory'),
        dcc.Store(id='ol-ai-recommendations-store', storage_type='memory'),
        dcc.Store(id='ol-portfolio-store', storage_type='memory'),
        
        # Header
        html.Div([
            html.H2([
                html.I(className="bi bi-graph-up-arrow me-2"),
                "Options Lab"
            ], className="mt-3 mb-2 text-white"),
            html.P(
                "Comprehensive options analysis, AI-powered recommendations, and strategy tools",
                className="text-muted mb-3"
            ),
        ]),
        
        # Global Controls
        dbc.Row([
            dbc.Col([
                dbc.Label("Ticker", className="text-white fw-bold"),
                dbc.InputGroup([
                    dbc.Input(
                        id='options-ticker-input',
                        type='text',
                        value='AAPL',
                        placeholder='Enter ticker...',
                        className='bg-dark text-white'
                    ),
                    dbc.Button(
                        html.I(className="bi bi-arrow-repeat"),
                        id='options-refresh-btn',
                        color='primary',
                        outline=True
                    )
                ])
            ], width=3),
            dbc.Col([
                dbc.Label("As of", className="text-white fw-bold"),
                html.Div(id='options-last-updated', className="text-info")
            ], width=3),
            dbc.Col([
                dbc.Label("Current Price", className="text-white fw-bold"),
                html.H4(id='options-spot-price', children="--", className="text-success mb-0")
            ], width=2),
            dbc.Col([
                dbc.Label("IV Rank", className="text-white fw-bold"),
                html.H4(id='options-iv-rank-display', children="--", className="text-warning mb-0")
            ], width=2),
            dbc.Col([
                dbc.Label("IV Percentile", className="text-white fw-bold"),
                html.H4(id='options-iv-pct-display', children="--", className="text-info mb-0")
            ], width=2),
        ], className="mb-4 p-3 bg-dark rounded"),
        
        # Main Tabs (Consolidated from 12 to 5)
        dbc.Tabs(
            id='options-lab-tabs-v2',
            active_tab='chain-viewer',
            children=[
                dbc.Tab(
                    label='📊 Chain Viewer',
                    tab_id='chain-viewer',
                    children=_tab_shell('chain-viewer', _create_chain_viewer_tab, "Chain Viewer")
                ),
                dbc.Tab(
                    label='📈 Analysis Hub',
                    tab_id='analysis-hub',
                    children=_tab_shell('analysis-hub', _create_analysis_hub_tab, "Analysis Hub")
                ),
                dbc.Tab(
                    label='🔧 Strategy Lab',
                    tab_id='strategy-lab-options',
                    children=_tab_shell('strategy-lab-options', _create_strategy_lab_tab, "Strategy Lab")
                ),
                dbc.Tab(
                    label='🤖 AI Recommendations',
                    tab_id='ai-recommendations',
                    children=_tab_shell('ai-recommendations', _create_ai_recommendations_tab, "AI Recommendations")
                ),
                dbc.Tab(
                    label='📋 Portfolio & Journal',
                    tab_id='portfolio-journal',
                    children=_tab_shell('portfolio-journal', _create_portfolio_journal_tab, "Portfolio & Journal")
                ),
            ],
            className="mb-3"
        ),
        
        # Footer
        html.Hr(),
        html.P([
            html.Small("Options Lab v2.0 • Data from Alpaca/yfinance • ", className="text-muted"),
            html.Small(id='ol-footer-timestamp', className="text-muted")
        ], className="text-center")
        
    ], fluid=True, className="p-3")


def _create_chain_viewer_tab():
    """Chain Viewer - Options chain with live prices and quick analysis."""
    return dbc.Container([
        # Stats cards
        dbc.Row([
            dbc.Col([dbc.Card([dbc.CardBody([
                html.H6("ATM IV", className="text-muted mb-2"),
                html.H4(id='chain-atm-iv', children="--", className="text-primary")
            ])])], width=3),
            dbc.Col([dbc.Card([dbc.CardBody([
                html.H6("Total Volume", className="text-muted mb-2"),
                html.H4(id='chain-total-volume', children="--", className="text-info")
            ])])], width=3),
            dbc.Col([dbc.Card([dbc.CardBody([
                html.H6("Total OI", className="text-muted mb-2"),
                html.H4(id='chain-total-oi', children="--", className="text-success")
            ])])], width=3),
            dbc.Col([dbc.Card([dbc.CardBody([
                html.H6("Put/Call Ratio", className="text-muted mb-2"),
                html.H4(id='chain-pcr', children="--", className="text-warning")
            ])])], width=3),
        ], className="mb-3 g-2"),
        
        # Filters
        dbc.Row([
            dbc.Col([
                dbc.Label("Expiration Date", className="fw-bold text-white"),
                dcc.Dropdown(id='chain-expiration-dropdown', placeholder="Select expiration...", className="mb-2")
            ], width=4),
            dbc.Col([
                dbc.Label("Option Type", className="fw-bold text-white"),
                dbc.RadioItems(
                    id='chain-type-radio',
                    options=[
                        {'label': 'Calls', 'value': 'call'},
                        {'label': 'Puts', 'value': 'put'},
                        {'label': 'Both', 'value': 'both'}
                    ],
                    value='both',
                    inline=True,
                    className="text-white"
                )
            ], width=4),
            dbc.Col([
                dbc.Label("Moneyness", className="fw-bold text-white"),
                dbc.RadioItems(
                    id='chain-moneyness-radio',
                    options=[
                        {'label': 'All', 'value': 'all'},
                        {'label': 'ITM', 'value': 'itm'},
                        {'label': 'OTM', 'value': 'otm'}
                    ],
                    value='all',
                    inline=True,
                    className="text-white"
                )
            ], width=4),
        ], className="mb-3 g-2"),
        
        # Chain table
        html.Div(id='chain-table-container', className="mb-3"),
        
        # Quick Forecast for selected contract
        dbc.Card([
            dbc.CardHeader("📈 Quick Forecast - Select a contract above"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Button("🔮 Generate Forecast", id='options-forecast-btn', color="primary", className="me-2"),
                    ], width=12)
                ]),
                html.Div(id='options-forecast-results', className="mt-3"),
            ])
        ], className="mb-3"),
        
        # Export
        dbc.Button("📥 Export Chain", id='chain-export-btn', color="success", size="sm"),
        dcc.Download(id='chain-download'),
        
    ], fluid=True, className="p-3")


def _create_analysis_hub_tab():
    """Analysis Hub - Combines Greeks, IV Analysis, Flow Scanner."""
    return dbc.Container([
        # Sub-navigation
        dbc.Tabs([
            dbc.Tab(label="Greeks Calculator", tab_id="greeks", children=_greeks_panel()),
            dbc.Tab(label="IV Analysis", tab_id="iv-analysis", children=_iv_analysis_panel()),
            dbc.Tab(label="Flow Scanner", tab_id="flow-scanner", children=_flow_scanner_panel()),
            dbc.Tab(label="Vol Surface", tab_id="vol-surface", children=_vol_surface_panel()),
        ], id='analysis-hub-subtabs', active_tab='greeks'),
    ], fluid=True, className="p-3")


def _greeks_panel():
    """Greeks calculator panel."""
    return dbc.Container([
        html.H5("🧮 Greeks Calculator", className="mb-3 text-white"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Strike", className="text-white"),
                dbc.Input(id='greeks-calc-strike', type='number', value=150, step=0.5)
            ], width=2),
            dbc.Col([
                dbc.Label("DTE", className="text-white"),
                dbc.Input(id='greeks-calc-dte', type='number', value=30, min=1, max=365)
            ], width=2),
            dbc.Col([
                dbc.Label("IV (%)", className="text-white"),
                dbc.Input(id='greeks-calc-iv', type='number', value=25, min=1, max=200, step=0.5)
            ], width=2),
            dbc.Col([
                dbc.Label("Type", className="text-white"),
                dcc.Dropdown(id='greeks-calc-type', options=[
                    {'label': 'Call', 'value': 'call'},
                    {'label': 'Put', 'value': 'put'}
                ], value='call')
            ], width=2),
            dbc.Col([
                dbc.Button("Calculate", id='greeks-calc-btn', color="primary", className="mt-4")
            ], width=2),
        ], className="mb-3"),
        html.Div(id='greeks-calc-results', className="mb-3"),
        dbc.Row([
            dbc.Col([dcc.Graph(id='greeks-delta-chart')], width=6),
            dbc.Col([dcc.Graph(id='greeks-gamma-chart')], width=6),
        ]),
        dbc.Row([
            dbc.Col([dcc.Graph(id='greeks-theta-chart')], width=6),
            dbc.Col([dcc.Graph(id='greeks-vega-chart')], width=6),
        ]),
    ], fluid=True)


def _iv_analysis_panel():
    """IV analysis panel."""
    return dbc.Container([
        html.H5("📊 IV Analysis", className="mb-3 text-white"),
        dbc.Row([
            dbc.Col([dbc.Card([dbc.CardBody([
                html.H6("IV Percentile (30D)", className="text-muted"),
                html.H3(id='ol-iv-percentile-30', children="--", className="text-primary")
            ])])], width=3),
            dbc.Col([dbc.Card([dbc.CardBody([
                html.H6("IV Percentile (1Y)", className="text-muted"),
                html.H3(id='ol-iv-percentile-1y', children="--", className="text-info")
            ])])], width=3),
            dbc.Col([dbc.Card([dbc.CardBody([
                html.H6("IV Rank", className="text-muted"),
                html.H3(id='ol-iv-rank', children="--", className="text-warning")
            ])])], width=3),
            dbc.Col([dbc.Card([dbc.CardBody([
                html.H6("Term Structure", className="text-muted"),
                html.H3(id='ol-term-structure', children="--", className="text-success")
            ])])], width=3),
        ], className="mb-3 g-2"),
        dbc.Row([
            dbc.Col([dcc.Graph(id='ol-term-structure-chart')], width=6),
            dbc.Col([dcc.Graph(id='ol-skew-chart')], width=6),
        ]),
        dcc.Graph(id='greeks-iv-smile'),
    ], fluid=True)


def _flow_scanner_panel():
    """Options flow scanner panel."""
    return dbc.Container([
        html.H5("🔍 Flow Scanner", className="mb-3 text-white"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Min Premium ($K)", className="text-white"),
                dbc.Input(id='ol-flow-min-premium', type='number', value=100, min=10, step=10)
            ], width=3),
            dbc.Col([
                dbc.Label("Vol Threshold (% OI)", className="text-white"),
                dbc.Input(id='ol-flow-vol-threshold', type='number', value=50, min=10, step=10)
            ], width=3),
            dbc.Col([
                dbc.Button("🔍 Scan", id='ol-flow-scan-btn', color="primary", className="mt-4")
            ], width=2),
        ], className="mb-3"),
        html.Div(id='ol-flow-table', className="mb-3"),
        dbc.Row([
            dbc.Col([dcc.Graph(id='ol-gex-chart')], width=6),
            dbc.Col([dcc.Graph(id='ol-max-pain-chart')], width=6),
        ]),
    ], fluid=True)


def _vol_surface_panel():
    """Volatility surface panel."""
    return dbc.Container([
        html.H5("📈 Volatility Surface", className="mb-3 text-white"),
        dbc.Row([
            dbc.Col([
                dcc.Graph(id='vol-surface-3d', style={'height': '500px'})
            ], width=8),
            dbc.Col([
                dbc.Label("Color Scale", className="text-white"),
                dcc.Dropdown(id='surface-colorscale-dropdown', options=[
                    {'label': 'Viridis', 'value': 'Viridis'},
                    {'label': 'Plasma', 'value': 'Plasma'},
                    {'label': 'Jet', 'value': 'Jet'},
                ], value='Viridis'),
                html.Br(),
                dbc.Label("View Angle", className="text-white"),
                dcc.Slider(id='surface-angle-slider', min=0, max=360, step=10, value=45),
            ], width=4),
        ]),
    ], fluid=True)


def _create_strategy_lab_tab():
    """Strategy Lab - Strategy Builder + Manual Trade + Backtester."""
    return dbc.Container([
        dbc.Tabs([
            dbc.Tab(label="Strategy Builder", tab_id="builder", children=_strategy_builder_panel()),
            dbc.Tab(label="Trade Simulator", tab_id="simulator", children=_trade_simulator_panel()),
            dbc.Tab(label="Backtester", tab_id="backtester", children=_backtester_panel()),
        ], id='ol-strategy-subtabs', active_tab='builder'),
    ], fluid=True, className="p-3")


def _strategy_builder_panel():
    """Strategy builder panel."""
    return dbc.Container([
        html.H5("🏗️ Strategy Builder", className="mb-3 text-white"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Template", className="text-white"),
                dcc.Dropdown(id='ol-strategy-template', options=[
                    {'label': '📈 Long Call', 'value': 'long_call'},
                    {'label': '📉 Long Put', 'value': 'long_put'},
                    {'label': '💰 Covered Call', 'value': 'covered_call'},
                    {'label': '🐂 Bull Call Spread', 'value': 'bull_call_spread'},
                    {'label': '🐻 Bear Put Spread', 'value': 'bear_put_spread'},
                    {'label': '🦅 Iron Condor', 'value': 'iron_condor'},
                    {'label': '🎯 Straddle', 'value': 'straddle'},
                    {'label': '⬛ Strangle', 'value': 'strangle'},
                    {'label': '🦋 Butterfly', 'value': 'butterfly'},
                ], value='iron_condor')
            ], width=4),
            dbc.Col([
                dbc.Label("Spot Price", className="text-white"),
                dbc.Input(id='ol-strategy-spot', type='number', value=100, min=1)
            ], width=3),
            dbc.Col([
                dbc.Button("🏗️ Build", id='ol-strategy-build-btn', color="primary", className="mt-4")
            ], width=2),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([html.Div(id='ol-strategy-legs')], width=6),
            dbc.Col([html.Div(id='ol-strategy-metrics')], width=6),
        ], className="mb-3"),
        dcc.Graph(id='ol-payoff-chart'),
    ], fluid=True)


def _trade_simulator_panel():
    """Trade simulator panel."""
    return dbc.Container([
        html.H5("📝 Trade Simulator", className="mb-3 text-white"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Option Type", className="text-white"),
                dcc.Dropdown(id='sim-option-type', options=[
                    {'label': 'Call', 'value': 'call'},
                    {'label': 'Put', 'value': 'put'},
                ], value='call')
            ], width=2),
            dbc.Col([
                dbc.Label("Expiration", className="text-white"),
                dcc.Dropdown(id='sim-expiration-dropdown', options=[], value=None)
            ], width=3),
            dbc.Col([
                dbc.Label("Strike", className="text-white"),
                dcc.Dropdown(id='sim-strike-dropdown', options=[], value=None)
            ], width=3),
            dbc.Col([
                dbc.Label("Qty", className="text-white"),
                dbc.Input(id='sim-quantity-input', type='number', value=1, min=1)
            ], width=2),
            dbc.Col([
                dbc.Button("Calculate", id='sim-calculate-btn', color="primary", className="mt-4")
            ], width=2),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([dbc.Card([dbc.CardBody([
                html.H6("Max Profit", className="text-muted"),
                html.H4(id='sim-max-profit', children="--", className="text-success")
            ])])], width=4),
            dbc.Col([dbc.Card([dbc.CardBody([
                html.H6("Max Loss", className="text-muted"),
                html.H4(id='sim-max-loss', children="--", className="text-danger")
            ])])], width=4),
            dbc.Col([dbc.Card([dbc.CardBody([
                html.H6("Breakeven", className="text-muted"),
                html.H4(id='sim-breakeven', children="--", className="text-warning")
            ])])], width=4),
        ], className="mb-3 g-2"),
        dcc.Graph(id='sim-pnl-chart'),
    ], fluid=True)


def _backtester_panel():
    """Backtester panel."""
    return dbc.Container([
        html.H5("🎯 Strategy Backtester", className="mb-3 text-white"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Strategy", className="text-white"),
                dcc.Dropdown(id='ol-backtest-strategy', options=[
                    {'label': 'Weekly Iron Condor', 'value': 'weekly_ic'},
                    {'label': 'Monthly Covered Call', 'value': 'monthly_cc'},
                    {'label': 'Delta-Neutral Straddle', 'value': 'delta_neutral'},
                ], value='weekly_ic')
            ], width=4),
            dbc.Col([
                dbc.Label("Lookback (days)", className="text-white"),
                dbc.Input(id='ol-backtest-lookback', type='number', value=90, min=30, max=365)
            ], width=3),
            dbc.Col([
                dbc.Label("Capital ($)", className="text-white"),
                dbc.Input(id='ol-backtest-capital', type='number', value=10000, min=1000)
            ], width=3),
            dbc.Col([
                dbc.Button("▶️ Run", id='ol-backtest-run-btn', color="primary", className="mt-4")
            ], width=2),
        ], className="mb-3"),
        html.Div(id='ol-backtest-results', className="mb-3"),
        dcc.Graph(id='ol-backtest-equity-chart'),
    ], fluid=True)


def _create_ai_recommendations_tab():
    """
    AI Recommendations - ENHANCED with full trade details.
    Shows: strategy, ticker, current price, expiry, strike, option premium,
    entry criteria, exit criteria, and clear action plan.
    """
    return dbc.Container([
        dbc.Alert([
            html.H5("🤖 AI Trade Recommendations", className="alert-heading"),
            html.P([
                "Smart trade suggestions with ",
                html.Strong("complete details"),
                ": current price, expiry, strike, premium, and clear action plans."
            ]),
        ], color="primary", className="mb-3"),
        
        # Filters
        dbc.Row([
            dbc.Col([
                dbc.Label("Filter by Type", className="text-white fw-bold"),
                dcc.Dropdown(
                    id='ol-ai-rec-type',
                    options=[
                        {'label': '🎯 All Recommendations', 'value': ''},
                        {'label': '📈 Bullish', 'value': 'bullish'},
                        {'label': '📉 Bearish', 'value': 'bearish'},
                        {'label': '↔️ Neutral', 'value': 'neutral'},
                        {'label': '🔥 High IV (Sell Premium)', 'value': 'high_iv'},
                        {'label': '❄️ Low IV (Buy Premium)', 'value': 'low_iv'},
                        {'label': '📅 Earnings Plays', 'value': 'earnings'},
                        {'label': '💰 Income', 'value': 'income'},
                    ],
                    value='',
                )
            ], width=4),
            dbc.Col([
                dbc.Label("Tickers", className="text-white fw-bold"),
                dcc.Dropdown(
                    id='ol-ai-rec-tickers',
                    options=[
                        {'label': 'AAPL', 'value': 'AAPL'},
                        {'label': 'MSFT', 'value': 'MSFT'},
                        {'label': 'GOOGL', 'value': 'GOOGL'},
                        {'label': 'TSLA', 'value': 'TSLA'},
                        {'label': 'NVDA', 'value': 'NVDA'},
                        {'label': 'AMD', 'value': 'AMD'},
                        {'label': 'SPY', 'value': 'SPY'},
                        {'label': 'QQQ', 'value': 'QQQ'},
                    ],
                    value=['AAPL', 'MSFT', 'NVDA'],
                    multi=True
                )
            ], width=4),
            dbc.Col([
                dbc.Button("🔄 Generate Recommendations", id='ol-ai-generate-btn', color="success", size="lg", className="mt-4")
            ], width=4),
        ], className="mb-4"),
        
        # Recommendations output - enhanced cards
        html.Div(id='ol-ai-recommendations', className="mb-4"),
        
        # Risk vs Reward chart
        html.H5("Risk vs Reward Overview", className="mb-3 text-white"),
        dcc.Graph(id='ol-ai-chart'),
        
    ], fluid=True, className="p-3")


def _create_portfolio_journal_tab():
    """Portfolio & Journal - Combines Portfolio Greeks + Trade Journal."""
    return dbc.Container([
        dbc.Tabs([
            dbc.Tab(label="Portfolio Greeks", tab_id="portfolio", children=_portfolio_greeks_panel()),
            dbc.Tab(label="Trade Journal", tab_id="journal", children=_trade_journal_panel()),
            dbc.Tab(label="Earnings Calendar", tab_id="earnings", children=_earnings_calendar_panel()),
        ], id='portfolio-journal-subtabs', active_tab='portfolio'),
    ], fluid=True, className="p-3")


def _portfolio_greeks_panel():
    """Portfolio Greeks panel."""
    return dbc.Container([
        html.H5("📉 Portfolio Greeks", className="mb-3 text-white"),
        dbc.Row([
            dbc.Col([dbc.Card([dbc.CardBody([
                html.H6("Net Delta", className="text-muted"),
                html.H4(id='ol-portfolio-delta', children="--", className="text-primary")
            ])])], width=2),
            dbc.Col([dbc.Card([dbc.CardBody([
                html.H6("Net Gamma", className="text-muted"),
                html.H4(id='ol-portfolio-gamma', children="--", className="text-info")
            ])])], width=2),
            dbc.Col([dbc.Card([dbc.CardBody([
                html.H6("Net Theta", className="text-muted"),
                html.H4(id='ol-portfolio-theta', children="--", className="text-success")
            ])])], width=2),
            dbc.Col([dbc.Card([dbc.CardBody([
                html.H6("Net Vega", className="text-muted"),
                html.H4(id='ol-portfolio-vega', children="--", className="text-warning")
            ])])], width=2),
            dbc.Col([dbc.Card([dbc.CardBody([
                html.H6("Risk Score", className="text-muted"),
                html.H4(id='ol-risk-score', children="--", className="text-danger")
            ])])], width=2),
            dbc.Col([
                dbc.Button("🔄 Refresh", id='ol-portfolio-refresh-btn', color="primary", className="mt-2")
            ], width=2),
        ], className="mb-3 g-2"),
        dbc.Row([
            dbc.Col([dcc.Graph(id='ol-greeks-dashboard')], width=6),
            dbc.Col([dcc.Graph(id='ol-greeks-heatmap')], width=6),
        ]),
    ], fluid=True)


def _trade_journal_panel():
    """Trade journal panel."""
    return dbc.Container([
        html.H5("📝 Trade Journal", className="mb-3 text-white"),
        dbc.Row([
            dbc.Col([
                dbc.Button("📝 Add Trade", id='ol-journal-add-btn', color="success", className="me-2"),
                dbc.Button("🔄 Refresh", id='ol-journal-refresh-btn', color="secondary", className="me-2"),
                dbc.Button("📥 Export", id='ol-journal-export-btn', color="info"),
            ], width=12),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([dbc.Card([dbc.CardBody([
                html.H6("Total P&L", className="text-muted"),
                html.H4(id='ol-journal-total-pnl', children="--", className="text-success")
            ])])], width=3),
            dbc.Col([dbc.Card([dbc.CardBody([
                html.H6("Win Rate", className="text-muted"),
                html.H4(id='ol-journal-win-rate', children="--", className="text-info")
            ])])], width=3),
            dbc.Col([dbc.Card([dbc.CardBody([
                html.H6("Profit Factor", className="text-muted"),
                html.H4(id='ol-journal-profit-factor', children="--", className="text-primary")
            ])])], width=3),
            dbc.Col([dbc.Card([dbc.CardBody([
                html.H6("Total Trades", className="text-muted"),
                html.H4(id='ol-journal-total', children="--", className="text-secondary")
            ])])], width=3),
        ], className="mb-3 g-2"),
        dbc.Row([
            dbc.Col([dcc.Graph(id='ol-journal-pnl-chart')], width=8),
            dbc.Col([dcc.Graph(id='ol-journal-gauge')], width=4),
        ]),
        html.Div(id='ol-journal-trades-table', className="mt-3"),
        dcc.Download(id='ol-journal-download'),
    ], fluid=True)


def _earnings_calendar_panel():
    """Earnings calendar panel."""
    return dbc.Container([
        html.H5("📅 Earnings Calendar", className="mb-3 text-white"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Days Ahead", className="text-white"),
                dbc.Input(id='ol-earnings-days', type='number', value=14, min=1, max=60)
            ], width=3),
            dbc.Col([
                dbc.Button("📅 Load", id='ol-earnings-load-btn', color="primary", className="mt-4 me-2"),
                dbc.Button("🔥 High IV", id='ol-earnings-high-iv-btn', color="warning", className="mt-4"),
            ], width=4),
        ], className="mb-3"),
        html.Div(id='ol-earnings-table', className="mb-3"),
        dbc.Row([
            dbc.Col([dcc.Graph(id='ol-earnings-chart')], width=8),
            dbc.Col([dcc.Graph(id='ol-earnings-heatmap')], width=4),
        ]),
    ], fluid=True)


def _error_fallback(error):
    """Error fallback layout."""
    return dbc.Container([
        dbc.Alert([
            html.H4("⚠️ Options Lab Failed to Load", className="alert-heading"),
            html.P(f"Error: {str(error)}"),
        ], color="danger", className="m-5")
    ], fluid=True)
