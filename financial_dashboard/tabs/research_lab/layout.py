"""
Research Lab - Layout Module
Creates the UI layout for research brief management.
"""

import logging
from dash import dcc, html
import dash_bootstrap_components as dbc
from datetime import datetime

logger = logging.getLogger(__name__)


def create_layout():
    """
    Build the Research Lab tab layout with brief list and editor.
    
    Returns:
        Dash component tree for the Research Lab interface
    """
    return dbc.Container([
        # Header
        html.Div([
            html.H2([
                html.I(className="bi bi-book me-2"),
                "Research Lab"
            ], className="mt-3 mb-2"),
            html.P(
                "Create, manage, and analyze research briefs with integrated screening and backtesting",
                className="text-light mb-3"
            ),
        ], style={
            'background-color': '#2b3035',
            'padding': '20px',
            'border-radius': '8px',
            'margin-bottom': '20px'
        }),
        
        # Subtabs for Research Lab with inline content (callback not working due to DashProxy duplicate callback bug)
        dbc.Tabs(
            id='research-lab-tabs',
            active_tab='research-notes',
            children=[
                dbc.Tab(
                    label='📊 Market Scan',
                    tab_id='market-scan',
                    children=[
                        html.H4('Market Scan', className='mb-3 text-light mt-3'),
                        html.Div([
                            html.Label('Tickers', htmlFor='market-scan-tickers', className='text-light'),
                            dcc.Input(id='market-scan-tickers', placeholder='AAPL,MSFT,GOOGL', type='text', className='form-control mb-2'),
                            html.Button('Run', id='market-scan-run-button', className='btn btn-primary')
                        ], className='p-2'),
                        html.Div([
                            html.Button('Analyze Factors', id='factor-analyze-button', className='btn btn-primary mb-2'),
                            html.Div(id='factor-analysis-results-container')
                        ], className='p-2'),
                    # Run button and results for Correlation Explorer
                    html.Div([
                        html.Button('Run Correlation', id='correlation-run-button', className='btn btn-primary mb-2'),
                        html.Div(id='correlation-heatmap')
                    ], className='p-2')
                    ]
                ),
                dbc.Tab(
                    label='📈 Factor Analysis',
                    tab_id='factor-analysis',
                    children=[
                        html.H4('Factor Analysis', className='mb-3 text-light mt-3'),
                        html.Div([
                            dbc.Row([
                                dbc.Col([
                                    html.Label('Select Tickers', className='text-light'),
                                    dcc.Dropdown(
                                        id='factor-analysis-ticker-select',
                                        options=[
                                            {'label': 'AAPL', 'value': 'AAPL'},
                                            {'label': 'MSFT', 'value': 'MSFT'},
                                            {'label': 'GOOGL', 'value': 'GOOGL'},
                                            {'label': 'NVDA', 'value': 'NVDA'}
                                        ],
                                        value=['AAPL', 'MSFT'],
                                        multi=True,
                                        className='mb-3'
                                    )
                                ], width=6),
                                dbc.Col([
                                    html.Label('Time Period', className='text-light'),
                                    dcc.Dropdown(
                                        id='factor-analysis-period-select',
                                        options=[
                                            {'label': '1 Month', 'value': '1M'},
                                            {'label': '3 Months', 'value': '3M'},
                                            {'label': '6 Months', 'value': '6M'},
                                            {'label': '1 Year', 'value': '1Y'}
                                        ],
                                        value='3M',
                                        className='mb-3'
                                    )
                                ], width=6)
                            ]),
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5('Factor Exposures', className='text-light mb-3'),
                                    html.P(
                                        'Factor analysis shows how portfolio holdings relate to common market factors '
                                        'such as momentum, value, growth, and volatility. This helps identify systematic '
                                        'risk exposures and diversification opportunities.',
                                        className='text-muted'
                                    ),
                                    html.Div([
                                        dbc.Table([
                                            html.Thead([
                                                html.Tr([
                                                    html.Th('Factor', className='text-light'),
                                                    html.Th('Exposure', className='text-light'),
                                                    html.Th('Contribution', className='text-light')
                                                ])
                                            ]),
                                            html.Tbody([
                                                html.Tr([
                                                    html.Td('Momentum', className='text-light'),
                                                    html.Td('0.34', className='text-success'),
                                                    html.Td('High', className='text-success')
                                                ]),
                                                html.Tr([
                                                    html.Td('Value', className='text-light'),
                                                    html.Td('-0.12', className='text-danger'),
                                                    html.Td('Low', className='text-muted')
                                                ]),
                                                html.Tr([
                                                    html.Td('Growth', className='text-light'),
                                                    html.Td('0.58', className='text-success'),
                                                    html.Td('Very High', className='text-success')
                                                ]),
                                                html.Tr([
                                                    html.Td('Volatility', className='text-light'),
                                                    html.Td('0.23', className='text-warning'),
                                                    html.Td('Medium', className='text-warning')
                                                ])
                                            ])
                                        ], bordered=True, hover=True, className='mb-3 table-dark')
                                    ])
                                ])
                            ], className='bg-dark border-secondary')
                        ], className='p-2'),
                        html.Div([
                            html.Button('Run Backtest', id='backtest-run-button', className='btn btn-primary mb-2'),
                            html.Div(id='backtest-results-container')
                        ], className='p-2')
                    ]
                ),
                dbc.Tab(
                    label='🔗 Correlation Explorer',
                    tab_id='correlation-explorer',
                    children=[
                        html.H4('Correlation Explorer', className='mb-3 text-light mt-3'),
                        html.Div([
                            dbc.Row([
                                dbc.Col([
                                    html.Label('Asset Universe', className='text-light'),
                                    dcc.Dropdown(
                                        id='correlation-universe-select',
                                        options=[
                                            {'label': 'Tech Stocks', 'value': 'tech'},
                                            {'label': 'Portfolio Holdings', 'value': 'portfolio'},
                                            {'label': 'Market Indices', 'value': 'indices'}
                                        ],
                                        value='tech',
                                        className='mb-3'
                                    )
                                ], width=6),
                                dbc.Col([
                                    html.Label('Correlation Window', className='text-light'),
                                    dcc.Dropdown(
                                        id='correlation-window-select',
                                        options=[
                                            {'label': '30 Days', 'value': 30},
                                            {'label': '60 Days', 'value': 60},
                                            {'label': '90 Days', 'value': 90}
                                        ],
                                        value=60,
                                        className='mb-3'
                                    )
                                ], width=6)
                            ]),
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5('Correlation Matrix', className='text-light mb-3'),
                                    html.P(
                                        'Correlation measures how closely assets move together. '
                                        'Values range from -1 (perfect negative correlation) to +1 (perfect positive correlation). '
                                        'Diversified portfolios benefit from low or negative correlations.',
                                        className='text-muted mb-3'
                                    ),
                                    html.Div([
                                        dbc.Table([
                                            html.Thead([
                                                html.Tr([
                                                    html.Th('', className='text-light'),
                                                    html.Th('AAPL', className='text-light'),
                                                    html.Th('MSFT', className='text-light'),
                                                    html.Th('GOOGL', className='text-light'),
                                                    html.Th('NVDA', className='text-light')
                                                ])
                                            ]),
                                            html.Tbody([
                                                html.Tr([
                                                    html.Td('AAPL', className='text-light fw-bold'),
                                                    html.Td('1.00', className='text-info'),
                                                    html.Td('0.72', className='text-success'),
                                                    html.Td('0.68', className='text-success'),
                                                    html.Td('0.65', className='text-success')
                                                ]),
                                                html.Tr([
                                                    html.Td('MSFT', className='text-light fw-bold'),
                                                    html.Td('0.72', className='text-success'),
                                                    html.Td('1.00', className='text-info'),
                                                    html.Td('0.81', className='text-success'),
                                                    html.Td('0.69', className='text-success')
                                                ]),
                                                html.Tr([
                                                    html.Td('GOOGL', className='text-light fw-bold'),
                                                    html.Td('0.68', className='text-success'),
                                                    html.Td('0.81', className='text-success'),
                                                    html.Td('1.00', className='text-info'),
                                                    html.Td('0.74', className='text-success')
                                                ]),
                                                html.Tr([
                                                    html.Td('NVDA', className='text-light fw-bold'),
                                                    html.Td('0.65', className='text-success'),
                                                    html.Td('0.69', className='text-success'),
                                                    html.Td('0.74', className='text-success'),
                                                    html.Td('1.00', className='text-info')
                                                ])
                                            ])
                                        ], bordered=True, hover=True, className='table-dark')
                                    ])
                                ])
                            ], className='bg-dark border-secondary')
                        ], className='p-2')
                    ]
                ),
                dbc.Tab(
                    label='⚙️ Strategy Backtest',
                    tab_id='strategy-backtest',
                    children=[
                        html.H4('Strategy Backtest', className='mb-3 text-light mt-3'),
                        html.Div([
                            dbc.Row([
                                dbc.Col([
                                    html.Label('Strategy Type', className='text-light'),
                                    dcc.Dropdown(
                                        id='backtest-strategy-select',
                                        options=[
                                            {'label': 'Momentum', 'value': 'momentum'},
                                            {'label': 'Mean Reversion', 'value': 'mean_reversion'},
                                            {'label': 'Breakout', 'value': 'breakout'}
                                        ],
                                        value='momentum',
                                        className='mb-3'
                                    )
                                ], width=4),
                                dbc.Col([
                                    html.Label('Lookback Period', className='text-light'),
                                    dcc.Dropdown(
                                        id='backtest-lookback-select',
                                        options=[
                                            {'label': '20 Days', 'value': 20},
                                            {'label': '50 Days', 'value': 50},
                                            {'label': '100 Days', 'value': 100}
                                        ],
                                        value=50,
                                        className='mb-3'
                                    )
                                ], width=4),
                                dbc.Col([
                                    html.Label('Initial Capital', className='text-light'),
                                    dcc.Input(
                                        id='backtest-capital-input',
                                        type='number',
                                        value=10000,
                                        className='form-control mb-3'
                                    )
                                ], width=4)
                            ]),
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5('Backtest Results', className='text-light mb-3'),
                                    dbc.Row([
                                        dbc.Col([
                                            dbc.Card([
                                                dbc.CardBody([
                                                    html.H6('Total Return', className='text-light'),
                                                    html.H4('23.4%', className='text-success')
                                                ])
                                            ], className='bg-dark border-secondary mb-3')
                                        ], width=3),
                                        dbc.Col([
                                            dbc.Card([
                                                dbc.CardBody([
                                                    html.H6('Sharpe Ratio', className='text-light'),
                                                    html.H4('1.42', className='text-info')
                                                ])
                                            ], className='bg-dark border-secondary mb-3')
                                        ], width=3),
                                        dbc.Col([
                                            dbc.Card([
                                                dbc.CardBody([
                                                    html.H6('Max Drawdown', className='text-light'),
                                                    html.H4('-8.7%', className='text-danger')
                                                ])
                                            ], className='bg-dark border-secondary mb-3')
                                        ], width=3),
                                        dbc.Col([
                                            dbc.Card([
                                                dbc.CardBody([
                                                    html.H6('Win Rate', className='text-light'),
                                                    html.H4('64%', className='text-success')
                                                ])
                                            ], className='bg-dark border-secondary mb-3')
                                        ], width=3)
                                    ]),
                                    html.Hr(className='border-secondary'),
                                    html.P(
                                        'Backtest simulates strategy performance using historical data. '
                                        'Results shown are for the selected strategy type and parameters. '
                                        'Past performance does not guarantee future results.',
                                        className='text-muted small'
                                    )
                                ])
                            ], className='bg-dark border-secondary')
                        ], className='p-2')
                    ]
                ),
                dbc.Tab(
                    label='📝 Research Notes',
                    tab_id='research-notes',
                    children=[create_brief_management_content()]
                ),
            ],
            className='mb-4'
        ),
        
        # Create/Edit Brief Modal
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id="rl-modal-title", children="New Research Brief")),
            dbc.ModalBody([
                dbc.Form([
                    # Title
                    dbc.Row([
                        dbc.Label("Title", width=3),
                        dbc.Col([
                            dbc.Input(
                                id="rl-brief-title-input",
                                type="text",
                                placeholder="Enter brief title",
                                className="mb-3"
                            )
                        ], width=9)
                    ], className="mb-3"),
                    
                    # Tags
                    dbc.Row([
                        dbc.Label("Tags", width=3),
                        dbc.Col([
                            dbc.Input(
                                id="rl-brief-tags-input",
                                type="text",
                                placeholder="momentum, tech, growth (comma-separated)",
                                className="mb-3"
                            )
                        ], width=9)
                    ], className="mb-3"),
                    
                    # Summary
                    dbc.Row([
                        dbc.Label("Summary", width=3),
                        dbc.Col([
                            dbc.Textarea(
                                id="rl-brief-summary-input",
                                placeholder="Brief summary of the research",
                                rows=3,
                                className="mb-3"
                            )
                        ], width=9)
                    ], className="mb-3"),
                    
                    # Body
                    dbc.Row([
                        dbc.Label("Body", width=3),
                        dbc.Col([
                            dbc.Textarea(
                                id="rl-brief-body-input",
                                placeholder="Full research content (markdown supported)",
                                rows=10,
                                className="mb-3"
                            )
                        ], width=9)
                    ], className="mb-3"),
                    
                    # Hidden field for brief ID when editing
                    dcc.Store(id="rl-edit-brief-id", data=None)
                ])
            ]),
            dbc.ModalFooter([
                dbc.Button("Cancel", id="rl-modal-cancel-btn", color="secondary", className="me-2"),
                dbc.Button("Save Brief", id="rl-brief-save-btn", color="primary")
            ])
        ], id="rl-brief-modal", size="xl", is_open=False),
        
        # Hidden stores
        dcc.Store(id="rl-briefs-store", data=[]),
        dcc.Store(id="rl-selected-brief-id", data=None),
        # Polling interval for auto-updates based on market conditions
        dcc.Interval(id='rl-market-poll-interval', interval=60_000, n_intervals=0),
        
        # Alert for status messages
        dbc.Alert(
            id="rl-alert",
            is_open=False,
            duration=4000,
            dismissable=True
        )
        
    ], fluid=True)


def create_brief_management_content():
    """Create the brief list and detail panel content for Research Notes subtab."""
    return dbc.Row([
            # Left column: Brief list
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5("Research Briefs", className="mb-0 d-inline"),
                        dbc.Button(
                            [html.I(className="bi bi-plus-circle me-1"), "New Brief"],
                            id="rl-brief-create-btn",
                            color="primary",
                            size="sm",
                            className="float-end"
                        )
                    ]),
                    dbc.CardBody([
                        html.Div(id="rl-brief-list", children=[
                            html.P(
                                "No briefs found — click New Brief or Load Demo",
                                className="text-light text-center p-3"
                            )
                        ])
                    ])
                ], className="mb-3"),
                
                # Quick actions
                dbc.Card([
                    dbc.CardHeader(html.H6("Quick Actions", className="mb-0")),
                    dbc.CardBody([
                        dbc.Button(
                            [html.I(className="bi bi-download me-1"), "Load Demo Brief"],
                            id="rl-load-demo-btn",
                            color="info",
                            size="sm",
                            className="w-100 mb-2"
                        ),
                        dbc.Button(
                            [html.I(className="bi bi-arrow-clockwise me-1"), "Refresh List"],
                            id="rl-refresh-btn",
                            color="secondary",
                            size="sm",
                            className="w-100"
                        )
                    ])
                ])
            ], width=4),
            
            # Right column: Detail view and editor
            dbc.Col([
                html.Div(id="rl-detail-panel", children=[
                        html.Div([
                            html.I(className="bi bi-arrow-left-circle me-2", style={'font-size': '3rem', 'color': '#cbd5e1'}),
                            html.H5("Select a brief from the list to view details", className="text-light mt-3")
                        ], className="text-center p-5")
                    ])
            ], width=8)
        ])


def create_brief_card(brief_id, title, summary, tags, created_at, last_updated):
    """
    Create a card component for a research brief.
    
    Args:
        brief_id: Unique identifier for the brief
        title: Brief title
        summary: Short summary text
        tags: List of tag strings
        created_at: Creation timestamp
        last_updated: Last update timestamp
        
    Returns:
        Dash component for the brief card
    """
    tags_badges = [
        dbc.Badge(tag.strip(), color="info", className="me-1")
        for tag in (tags if isinstance(tags, list) else tags.split(','))
        if tag.strip()
    ] if tags else []
    
    return html.Div([
        dbc.Card([
                dbc.CardBody([
                html.H6(title, className="card-title mb-2 text-light"),
                html.P(
                    summary[:100] + "..." if len(summary) > 100 else summary,
                    className="card-text text-light small mb-2"
                ),
                html.Div(tags_badges, className="mb-2"),
                html.Small([
                    html.I(className="bi bi-clock me-1"),
                    f"Updated: {last_updated}"
                ], className="text-light"),
                dbc.Button(
                    "View",
                    id={"type": "rl-select-brief", "index": brief_id},
                    color="primary",
                    size="sm",
                    className="mt-2 w-100"
                )
            ])
        ], className="mb-2")
    ])


def create_brief_detail_view(brief):
    """
    Create detailed view of a research brief with action buttons.
    
    Args:
        brief: Dictionary containing brief data
        
    Returns:
        Dash component for the detail view
    """
    if not brief:
        return html.Div([
            html.I(className="bi bi-arrow-left-circle me-2", style={'font-size': '3rem'}),
            html.H5("Select a brief from the list", className="text-muted mt-3")
        ], className="text-center p-5")
    
    tags_badges = [
        dbc.Badge(tag.strip(), color="info", className="me-1")
        for tag in (brief.get('tags', []) if isinstance(brief.get('tags'), list) 
                   else str(brief.get('tags', '')).split(','))
        if tag.strip()
    ]
    
    return dbc.Card([
        dbc.CardHeader([
            html.H4(brief.get('title', 'Untitled'), className="mb-0 d-inline"),
            dbc.ButtonGroup([
                dbc.Button(
                    [html.I(className="bi bi-pencil me-1"), "Edit"],
                    id="rl-brief-edit-btn",
                    color="warning",
                    size="sm"
                ),
                dbc.Button(
                    [html.I(className="bi bi-download me-1"), "Export"],
                    id="rl-brief-export-btn",
                    color="info",
                    size="sm"
                ),
                dbc.Button(
                    [html.I(className="bi bi-trash me-1"), "Delete"],
                    id="rl-brief-delete-btn",
                    color="danger",
                    size="sm"
                )
            ], className="float-end", size="sm")
        ]),
        dbc.CardBody([
            # Tags and metadata
            html.Div([
                html.Div(tags_badges, className="mb-3"),
                html.P([
                    html.Strong("Created: "),
                    brief.get('created_at', 'Unknown'),
                    html.Span(" | ", className="mx-2"),
                    html.Strong("Last Updated: "),
                    brief.get('last_updated', 'Unknown')
                ], className="text-muted small mb-3")
            ]),
            
            # Summary
            html.Div([
                html.H6("Summary", className="mt-3 mb-2"),
                html.P(brief.get('summary', ''), className="mb-3")
            ]),
            
            # Body
            html.Div([
                html.H6("Content", className="mt-3 mb-2"),
                dcc.Markdown(brief.get('body', ''), className="mb-3")
            ]),
            
            # Notes editor
            html.Div([
                html.H6("Notes", className="mt-3 mb-2"),
                dbc.Textarea(
                    id="rl-brief-notes-editor",
                    value=brief.get('notes', ''),
                    placeholder='Enter your research notes here...',
                    rows=6,
                    className="mb-2"
                ),
                dbc.Button(
                    [html.I(className="bi bi-save me-1"), "Save Notes"],
                    id="rl-notes-save-btn",
                    color="success",
                    size="sm"
                )
            ]),
            
            # Screening & Backtest Actions
            html.Hr(className="my-4"),
            html.H6("Analysis Tools", className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Button(
                        [html.I(className="bi bi-search me-1"), "Run Screen"],
                        id="rl-screen-run-btn",
                        color="primary",
                        className="w-100"
                    )
                ], width=6),
                dbc.Col([
                    dbc.Button(
                        [html.I(className="bi bi-bar-chart me-1"), "Backtest Preview"],
                        id="rl-backtest-run-btn",
                        color="primary",
                        className="w-100"
                    )
                ], width=6)
            ]),
            
            # Results panel
            html.Div(id="rl-analysis-results", className="mt-3")
        ])
    ])
