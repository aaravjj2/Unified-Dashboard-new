"""
Strategy Lab - Execute & Configure Subtab (MERGED)

Combined backtest configuration + execution interface:
- Date range & capital settings
- Transaction costs & slippage
- Run button
- Real-time results display
"""

import logging
from dash_extensions.enrich import html, dcc
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def layout():
    """
    Combined execution + configuration subtab layout.
    
    Returns:
        dbc.Container: Backtest configuration + execution controls
    """
    # Default dates - Use confirmed historical dates (not future)
    # End date: Yesterday to avoid any future date issues
    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=365)  # 1 year back from end_date
    
    return dbc.Container([
        # Description
        dcc.Markdown("""
**▶️ Configure & Execute Backtest:**

Set your backtest parameters and run the simulation:
1. **Date Range**: How far back to test (1-5 years recommended)
2. **Capital**: Starting portfolio value
3. **Costs**: Transaction fees and slippage
4. **Run**: Execute backtest and see results immediately

**⚡ Now using REAL backtest engine** (not mock data)
        """, className="small mb-4", style={
            'backgroundColor': '#f0fff4',
            'padding': '15px',
            'borderRadius': '8px',
            'color': '#000000'
        }),
        
        # Configuration Section
        dbc.Card([
            dbc.CardHeader(html.H6("⚙️ Backtest Parameters", className="mb-0")),
            dbc.CardBody([
                # Date Range
                dbc.Row([
                    dbc.Col([
                        html.Label("Start Date", className="fw-bold small"),
                        dcc.DatePickerSingle(
                            id='sl-start-date',
                            date=start_date.strftime('%Y-%m-%d'),
                            display_format='YYYY-MM-DD',
                            className="mb-2"
                        ),
                    ], md=6),
                    dbc.Col([
                        html.Label("End Date", className="fw-bold small"),
                        dcc.DatePickerSingle(
                            id='sl-end-date',
                            date=end_date.strftime('%Y-%m-%d'),
                            display_format='YYYY-MM-DD',
                            className="mb-2"
                        ),
                    ], md=6),
                ], className="mb-3"),
                
                # Capital & Costs
                dbc.Row([
                    dbc.Col([
                        html.Label("Initial Capital ($)", className="fw-bold small"),
                        dcc.Input(
                            id='sl-initial-capital',
                            type='number',
                            value=100000,
                            min=1000,
                            step=1000,
                            style={'width': '100%'},
                            className="mb-2"
                        ),
                    ], md=6),
                    dbc.Col([
                        html.Label("Transaction Cost ($ per trade)", className="fw-bold small"),
                        dcc.Input(
                            id='sl-transaction-cost',
                            type='number',
                            value=0,
                            min=0,
                            step=0.01,
                            style={'width': '100%'},
                            className="mb-2"
                        ),
                    ], md=6),
                ], className="mb-3"),
                
                # Slippage & Position Size
                dbc.Row([
                    dbc.Col([
                        html.Label("Slippage (%)", className="fw-bold small"),
                        dcc.Input(
                            id='sl-slippage',
                            type='number',
                            value=0.1,
                            min=0,
                            max=5,
                            step=0.1,
                            style={'width': '100%'},
                            className="mb-2"
                        ),
                    ], md=6),
                    dbc.Col([
                        html.Label("Position Size (% of capital)", className="fw-bold small"),
                        dcc.Input(
                            id='sl-position-size',
                            type='number',
                            value=10,
                            min=1,
                            max=100,
                            step=1,
                            style={'width': '100%'},
                            className="mb-2"
                        ),
                    ], md=6),
                ], className="mb-3"),
                
                # Max Positions & Random Seed
                dbc.Row([
                    dbc.Col([
                        html.Label("Max Concurrent Positions", className="fw-bold small"),
                        dcc.Input(
                            id='sl-max-positions',
                            type='number',
                            value=5,
                            min=1,
                            max=20,
                            step=1,
                            style={'width': '100%'},
                            className="mb-2"
                        ),
                    ], md=6),
                    dbc.Col([
                        html.Label("Random Seed (for reproducibility)", className="fw-bold small"),
                        dcc.Input(
                            id='sl-random-seed',
                            type='number',
                            value=42,
                            min=0,
                            step=1,
                            placeholder="Leave blank for random",
                            style={'width': '100%'},
                            className="mb-2"
                        ),
                    ], md=6),
                ]),
            ])
        ], className="mb-4"),
        
        # Phase 4: Engine Selection
        dbc.Card([
            dbc.CardHeader(html.H6("🔧 Backtest Engine", className="mb-0")),
            dbc.CardBody([
                dcc.RadioItems(
                    id='sl-engine-select',
                    options=[
                        {
                            'label': html.Div([
                                html.Strong("⚡ VectorBT (Fast)"),
                                html.Br(),
                                html.Small("Vectorized computation, ideal for quick iterations", 
                                         className="text-muted")
                            ], style={'marginLeft': '8px'}),
                            'value': 'vectorbt'
                        },
                        {
                            'label': html.Div([
                                html.Strong("🌊 Nautilus (Realistic)"),
                                html.Br(),
                                html.Small("Event-driven simulation with order book modeling", 
                                         className="text-muted")
                            ], style={'marginLeft': '8px'}),
                            'value': 'nautilus'
                        },
                    ],
                    value='vectorbt',
                    className="mb-3",
                    labelStyle={'display': 'block', 'marginBottom': '12px'}
                ),
                
                # Nautilus-specific options (conditional)
                html.Div(id='sl-nautilus-options', children=[
                    dbc.Alert([
                        html.I(className="bi bi-info-circle me-2"),
                        html.Strong("Nautilus Mode: "),
                        "Event-driven execution with realistic order fills, slippage, and latency simulation. "
                        "Trade logs will show order-by-order execution details."
                    ], color="info", className="mb-0")
                ], style={'display': 'none'}),
            ])
        ], className="mb-4"),
        
        # Execution Controls
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("🚀 Run Backtest", className="mb-3"),
                        
                        # Run Button
                        dbc.Button(
                            [html.I(className="bi bi-play-circle me-2"), "Run Backtest"],
                            id='sl-run-backtest-btn',
                            color='primary',
                            size='lg',
                            className="w-100 mb-3",
                            n_clicks=0
                        ),
                        
                        # Progress Bar
                        html.Div([
                            dbc.Progress(
                                id='sl-backtest-progress',
                                value=0,
                                striped=True,
                                animated=True,
                                className="mb-2"
                            ),
                            html.Div(id='sl-progress-text', className="text-center small", style={'color': '#000000'})
                        ], id='sl-progress-container', style={'display': 'none'}),
                        
                        # Status Messages
                        html.Div(id='sl-execution-status', className="mt-3"),
                        
                        # Cancel Button
                        dbc.Button(
                            [html.I(className="bi bi-x-circle me-2"), "Cancel"],
                            id='sl-cancel-btn',
                            color='danger',
                            outline=True,
                            className="w-100 mt-2",
                            style={'display': 'none'}
                        ),
                        
                        # Divider
                        html.Hr(className="my-3"),
                        
                        # Live Order Section
                        html.H5("💰 Execute Live Order", className="mb-2"),
                        html.P(
                            "Execute a real trade based on backtest results. Requires confirmation.",
                            className="text-muted small mb-3"
                        ),
                        dbc.Button(
                            [html.I(className="bi bi-lightning-charge me-2"), "Execute Live Order"],
                            id='sl-execute-live-btn',
                            color='warning',
                            size='lg',
                            className="w-100",
                            n_clicks=0,
                            disabled=True  # Enabled after backtest completes
                        ),
                        html.Small(
                            "⚠️ LIVE_ORDER_ALLOWED=true - Real money at risk",
                            className="text-danger d-block mt-2 text-center"
                        ),
                    ])
                ])
            ], md=12),
        ], className="mb-3"),
        
        # Real-time Stats (shown during execution)
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("📊 Execution Stats", className="mb-0")),
                    dbc.CardBody([
                        html.Div(id='sl-execution-stats', children=[
                            html.P("No backtest running...", className="text-muted mb-0", style={'color': '#000000'})
                        ])
                    ])
                ], className="mb-3")
            ], md=12),
        ]),
        
    ], fluid=True, className="p-3")


logger.info("✓ Strategy Lab Execution subtab loaded")
