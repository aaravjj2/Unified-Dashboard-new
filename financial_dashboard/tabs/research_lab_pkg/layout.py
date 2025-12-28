"""
Research Lab - Layout Module

Creates the UI layout for the Research Lab with 7 subtabs.
All functions are pure - no side effects or network calls at import time.
No modals auto-open on dashboard load.
"""

import logging
from dash import dcc, html
import dash_bootstrap_components as dbc

from . import components
from . import data

logger = logging.getLogger(__name__)


def create_layout():
    """
    Build the Research Lab tab layout with all subtabs.
    
    Returns:
        Dash component tree for the Research Lab interface
    """
    return dbc.Container([
        # Stores for state management (no auto-load)
        dcc.Store(id="rl-config-store", data={}),
        dcc.Store(id="rl-beginner-howto-store", data=None),
        dcc.Store(id="rl-query-store", data={}),
        dcc.Store(id="rl-briefs-store", data=[]),
        dcc.Store(id="rl-selected-brief-id", data=None),
        dcc.Store(id="rl-experiments-store", data=[]),
        dcc.Store(id="rl-rag-answer-id", data=None),
        
        # Alert for notifications (hidden by default)
        dbc.Alert(
            id="rl-alert",
            is_open=False,
            dismissable=True,
            duration=4000,
            className="position-fixed",
            style={"top": "80px", "right": "20px", "zIndex": 9999, "maxWidth": "400px"}
        ),
        
        # Header
        _create_header(),
        
        # Main subtabs
        dbc.Tabs(
            id="rl-main-tabs",
            active_tab="rl-alphasim-tab",
            children=[
                dbc.Tab(
                    label="🔌 AlphaSim Console",
                    tab_id="rl-alphasim-tab",
                    children=[_create_alphasim_tab()]
                ),
                dbc.Tab(
                    label="📊 Research Scan",
                    tab_id="rl-scan-tab",
                    children=[_create_scan_tab()]
                ),
                dbc.Tab(
                    label="📈 Factor & Signal Lab",
                    tab_id="rl-factor-tab",
                    children=[_create_factor_tab()]
                ),
                dbc.Tab(
                    label="🔎 Screen Builder",
                    tab_id="rl-screen-tab",
                    children=[_create_screen_tab()]
                ),
                dbc.Tab(
                    label="🤖 RAG Chat",
                    tab_id="rl-rag-tab",
                    children=[_create_rag_tab()]
                ),
                dbc.Tab(
                    label="📝 Briefs & Notes",
                    tab_id="rl-briefs-tab",
                    children=[_create_briefs_tab()]
                ),
                dbc.Tab(
                    label="🧪 Experiment Tracker",
                    tab_id="rl-exp-tab",
                    children=[_create_experiment_tab()]
                ),
                dbc.Tab(
                    label="⚙️ Diagnostics",
                    tab_id="rl-diag-tab",
                    children=[_create_diagnostics_tab()]
                ),
            ],
            className="mb-4"
        ),
        
        # Modal for brief editing (NOT auto-opened)
        _create_brief_modal(),
        # Download helper for HOWTO modal
        dcc.Download(id='rl-beginner-howto-download-file'),
        # Modal for Beginner HOWTO (populated by callback)
        _create_beginner_howto_modal(),
        
    ], fluid=True, className="px-4 py-3")


def _create_header():
    """Create the Research Lab header."""
    return html.Div([
        html.H2([
            html.I(className="bi bi-book me-2"),
            "Research Lab"
        ], className="mt-2 mb-1 text-light"),
        html.P(
            "Integrated research platform: scanning, factor analysis, RAG-powered Q&A, and experiment tracking",
            className="text-muted mb-3"
        ),
        # Beginner-friendly accordion (in-app How-To / quickstart)
        # Use a light, padded body so the guide visually matches Attribution Lab
        dbc.Accordion([
            dbc.AccordionItem([
                html.Div(
                    dcc.Markdown(
                        """
**🔬 What This Lab Does:**

The Research Lab is your data exploration workspace for analyzing stocks, ETFs, and market trends before building strategies or making trades. It groups tools into scanning, factor analysis, screening, RAG-powered Q&A, experiment tracking, and briefs.

**🚀 Quick Start (2-minute flow):**
1. Click **AlphaSim Console** → run `TIME_SERIES_DAILY` for a sample ticker (e.g., `AAPL`).
2. Switch to **Research Scan** and run a preset (Momentum / Value) to generate candidates.
3. Open **Factor & Signal Lab** to inspect exposures and build a signal.
4. Save findings as a **Brief** and run a quick preview in **Experiment Tracker**.

**✨ Key Features:**
- AlphaSim Console: Local Alpha Vantage-compatible API for price, indicators, news, and options snapshots.
- Research Scan: Fast universe screening with quick presets and news feed.
- Factor & Signal Lab: Compute factor exposures, correlation heatmaps, and create reusable signals.
- Screen Builder: Save filters as reusable screens and export to weekly picks.
- RAG Chat: Ask questions over indexed research documents and convert answers into briefs.
- Experiment Tracker: Lightweight backtest previews and result snapshots.

**🛠️ Common Workflows:**
- Exploratory: Run scans → shortlist tickers → inspect factor exposures → save brief.
- Signal Dev: Create factor signals → preview performance in Experiment Tracker → export to Strategy Lab.
- Research Ops: Index documents → use RAG Chat to summarize → publish brief.

**⚠️ Troubleshooting & Tips:**
- If AlphaSim shows `Offline`, start the service: `uvicorn financial_dashboard.services.alpha_sim.app:app --port 8065`.
- If news or prices are missing, check API keys in `keys.env` and restart the dashboard.
- Use the **Diagnostics** tab to inspect index health and ingestion logs.

**📖 Full Guide & Examples:**
Click **Open Full Guide** below to read the complete how-to with examples, selectors, and troubleshooting steps.
                        """,
                        style={'color': '#000000', 'fontSize': '14px'}
                    ),
                    style={
                        'backgroundColor': '#f8fafc',
                        'padding': '12px 14px',
                        'borderRadius': '8px',
                        'color': '#000000'
                    }
                ),
                html.Div([
                    dbc.Button(
                        "Open Full Guide",
                        id="rl-beginner-open-howto",
                        color="primary",
                        size="sm",
                        className="mt-3"
                    )
                ], className="mt-2")
            ], title="📚 Beginner's Guide to Research Lab", className="mb-3")
        ], start_collapsed=True, className="mb-4"),
    ], style={
        'backgroundColor': '#2b3035',
        'padding': '15px 20px',
        'borderRadius': '8px',
        'marginBottom': '20px'
    })


# ============================================================================
# SUBTAB LAYOUTS
# ============================================================================

def _create_alphasim_tab():
    """Create the AlphaSim Console subtab content per research_lab_implementation_plan.md."""
    return html.Div([
        html.H4("🔌 AlphaSim Console", className="text-light mb-3 mt-3"),
        html.P(
            "Run Alpha Vantage-compatible queries against the internal AlphaSim service.",
            className="text-muted mb-3"
        ),
        
        dbc.Row([
            # Left: Query builder
            dbc.Col([
                components.section_card("Query Builder", [
                    dbc.Row([
                        dbc.Col([
                            html.Label("Function", className="text-light"),
                            dcc.Dropdown(
                                id="rl-alphasim-function",
                                options=[
                                    {"label": "TIME_SERIES_DAILY", "value": "TIME_SERIES_DAILY"},
                                    {"label": "TIME_SERIES_INTRADAY", "value": "TIME_SERIES_INTRADAY"},
                                    {"label": "SMA (Simple Moving Average)", "value": "SMA"},
                                    {"label": "EMA (Exponential Moving Average)", "value": "EMA"},
                                    {"label": "RSI (Relative Strength Index)", "value": "RSI"},
                                    {"label": "MACD", "value": "MACD"},
                                    {"label": "NEWS_SENTIMENT", "value": "NEWS_SENTIMENT"},
                                    {"label": "HISTORICAL_OPTIONS", "value": "HISTORICAL_OPTIONS"},
                                ],
                                value="TIME_SERIES_DAILY",
                                className="mb-3"
                            )
                        ], md=6),
                        dbc.Col([
                            html.Label("Symbol", className="text-light"),
                            dbc.Input(
                                id="rl-alphasim-symbol",
                                type="text",
                                value="AAPL",
                                placeholder="Enter ticker symbol",
                                className="bg-dark text-light mb-3"
                            )
                        ], md=6)
                    ]),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Time Period (indicators)", className="text-light"),
                            dbc.Input(
                                id="rl-alphasim-time-period",
                                type="number",
                                value=10,
                                min=1,
                                max=200,
                                className="bg-dark text-light mb-3"
                            )
                        ], md=4),
                        dbc.Col([
                            html.Label("Interval (intraday)", className="text-light"),
                            dcc.Dropdown(
                                id="rl-alphasim-interval",
                                options=[
                                    {"label": "1 min", "value": "1min"},
                                    {"label": "5 min", "value": "5min"},
                                    {"label": "15 min", "value": "15min"},
                                    {"label": "60 min", "value": "60min"},
                                ],
                                value="5min",
                                className="mb-3"
                            )
                        ], md=4),
                        dbc.Col([
                            html.Label("Output Size", className="text-light"),
                            dcc.Dropdown(
                                id="rl-alphasim-outputsize",
                                options=[
                                    {"label": "Compact (100)", "value": "compact"},
                                    {"label": "Full", "value": "full"},
                                ],
                                value="compact",
                                className="mb-3"
                            )
                        ], md=4)
                    ]),
                    html.Div([
                        dbc.Button(
                            [html.I(className="bi bi-play-fill me-1"), "Run Query"],
                            id="rl-alphasim-run-btn",
                            color="primary",
                            className="me-2"
                        ),
                        dbc.Button(
                            [html.I(className="bi bi-clipboard me-1"), "Copy Result"],
                            id="rl-alphasim-copy-btn",
                            color="secondary",
                            outline=True,
                            className="me-2"
                        ),
                        dbc.Button(
                            [html.I(className="bi bi-download me-1"), "Export JSON"],
                            id="rl-alphasim-export-btn",
                            color="secondary",
                            outline=True
                        )
                    ], className="mt-3")
                ], id_prefix="rl-alphasim-query"),
                
                # Recent queries table
                components.section_card("Recent Queries", [
                    html.Div(id="rl-alphasim-recent", children=[
                        components.empty_state("No queries yet", icon="bi-clock-history")
                    ])
                ], id_prefix="rl-alphasim-recent-section")
            ], md=6),
            
            # Right: Response viewer
            dbc.Col([
                components.section_card("Response Viewer", [
                    html.Div([
                        # Status badges
                        html.Div([
                            dbc.Badge("Ready", id="rl-alphasim-status", color="secondary", className="me-2"),
                            dbc.Badge("Cache: --", id="rl-alphasim-cache-badge", color="info", className="me-2"),
                            html.Span(id="rl-alphasim-latency", className="text-muted small")
                        ], className="mb-3"),
                        
                        # JSON response viewer
                        html.Pre(
                            id="rl-alphasim-response",
                            className="bg-dark text-light p-3 rounded",
                            style={
                                "maxHeight": "500px",
                                "overflow": "auto",
                                "fontFamily": "monospace",
                                "fontSize": "12px",
                                "whiteSpace": "pre-wrap"
                            },
                            children='{\n  "status": "ready",\n  "message": "Enter query parameters and click Run"\n}'
                        )
                    ])
                ], id_prefix="rl-alphasim-response-section"),
                
                # Service status card
                components.section_card("Service Status", [
                    html.Div(id="rl-alphasim-service-status", children=[
                        dbc.Row([
                            dbc.Col([
                                html.Div([
                                    html.I(className="bi bi-circle-fill text-secondary me-2", id="rl-alphasim-health-icon"),
                                    html.Span("AlphaSim Service", className="text-light")
                                ]),
                                html.Small("Checking...", id="rl-alphasim-health-text", className="text-muted")
                            ], md=6),
                            dbc.Col([
                                html.Div([
                                    html.I(className="bi bi-database me-2 text-info"),
                                    html.Span("Cache", className="text-light")
                                ]),
                                html.Small("Size: --", id="rl-alphasim-cache-size", className="text-muted")
                            ], md=6)
                        ]),
                        html.Hr(className="border-secondary my-3"),
                        html.Div([
                            dbc.Button(
                                [html.I(className="bi bi-arrow-clockwise me-1"), "Check Health"],
                                id="rl-alphasim-check-health-btn",
                                size="sm",
                                color="secondary",
                                outline=True,
                                className="me-2"
                            ),
                            dbc.Button(
                                [html.I(className="bi bi-bar-chart me-1"), "View Metrics"],
                                id="rl-alphasim-metrics-btn",
                                size="sm",
                                color="secondary",
                                outline=True
                            )
                        ])
                    ])
                ], id_prefix="rl-alphasim-status-section")
            ], md=6)
        ]),
        
        # Store for query history
        dcc.Store(id="rl-alphasim-query-history", data=[]),
        dcc.Store(id="rl-alphasim-last-result", data=None),
        dcc.Download(id="rl-alphasim-download")
    ], id="rl-alphasim-content")


def _create_scan_tab():
    """Create the Research Scan subtab content."""
    return html.Div([
        html.H4("📊 Research Scan", className="text-light mb-3 mt-3"),
        
        dbc.Row([
            # Left panel: Scan controls
            dbc.Col([
                components.section_card("Ticker Search", [
                    components.ticker_search_input("rl-scan"),
                    html.Div([
                        html.Label("Quick Screens:", className="text-muted small"),
                        dbc.ButtonGroup([
                            dbc.Button("Momentum", id="rl-scan-preset-momentum", size="sm", color="secondary", outline=True),
                            dbc.Button("Value", id="rl-scan-preset-value", size="sm", color="secondary", outline=True),
                            dbc.Button("Growth", id="rl-scan-preset-growth", size="sm", color="secondary", outline=True)
                        ], size="sm", className="mt-2")
                    ])
                ], id_prefix="rl-scan-search"),
                
                components.section_card("Scan Results", [
                    html.Div(id="rl-scan-results", children=[
                        components.empty_state("Run a scan to see results", icon="bi-search")
                    ])
                ], id_prefix="rl-scan-results-section")
            ], md=6),
            
            # Right panel: News feed
            dbc.Col([
                components.section_card("News Feed", [
                    html.Div([
                        dbc.Button(
                            [html.I(className="bi bi-arrow-clockwise me-1"), "Refresh"],
                            id="rl-scan-news-refresh",
                            size="sm",
                            color="secondary",
                            outline=True,
                            className="mb-2"
                        )
                    ]),
                    html.Div(id="rl-scan-news", children=[
                        components.empty_state("Enter tickers and search to load news", icon="bi-newspaper")
                    ])
                ], id_prefix="rl-scan-news-section")
            ], md=6)
        ])
    ], id="rl-scan-content")


def _create_factor_tab():
    """Create the Factor & Signal Lab subtab content."""
    return html.Div([
        html.H4("📈 Factor & Signal Lab", className="text-light mb-3 mt-3"),
        
        dbc.Row([
            dbc.Col([
                html.Label("Select Tickers", className="text-light"),
                dcc.Dropdown(
                    id="rl-factor-select",
                    options=[{"label": t, "value": t} for t in data.get_sample_tickers()],
                    value=["AAPL", "MSFT", "NVDA"],
                    multi=True,
                    className="mb-3"
                )
            ], md=8),
            dbc.Col([
                html.Label("Period", className="text-light"),
                dcc.Dropdown(
                    id="rl-factor-period",
                    options=[
                        {"label": "1M", "value": "1M"},
                        {"label": "3M", "value": "3M"},
                        {"label": "6M", "value": "6M"},
                        {"label": "1Y", "value": "1Y"}
                    ],
                    value="3M",
                    className="mb-3"
                )
            ], md=4)
        ]),
        
        dbc.Row([
            dbc.Col([
                components.section_card("Factor Exposures", [
                    html.Div(id="rl-factor-exposures", children=[
                        components.empty_state("Select tickers to view factor exposures", icon="bi-graph-up")
                    ])
                ], id_prefix="rl-factor-exp")
            ], md=6),
            dbc.Col([
                components.section_card("Correlation Heatmap", [
                    html.Div(id="rl-factor-corr", children=[
                        components.factor_heatmap_placeholder("rl-factor-heatmap")
                    ])
                ], id_prefix="rl-factor-corr-section")
            ], md=6)
        ]),
        
        dbc.Row([
            dbc.Col([
                components.section_card("Create Signal", [
                    dbc.Row([
                        dbc.Col([
                            html.Label("Factor", className="text-light"),
                            dcc.Dropdown(
                                id="rl-factor-signal-factor",
                                options=[{"label": f["name"], "value": k} 
                                        for k, f in data.get_factor_definitions().items()],
                                value="momentum",
                                className="mb-2"
                            )
                        ], md=4),
                        dbc.Col([
                            html.Label("Threshold", className="text-light"),
                            dbc.Input(
                                id="rl-factor-signal-threshold",
                                type="number",
                                value=0.5,
                                step=0.1,
                                className="bg-dark text-light mb-2"
                            )
                        ], md=4),
                        dbc.Col([
                            html.Label("Signal Name", className="text-light"),
                            dbc.Input(
                                id="rl-factor-signal-name",
                                type="text",
                                placeholder="My Signal",
                                className="bg-dark text-light mb-2"
                            )
                        ], md=4)
                    ]),
                    dbc.Button(
                        [html.I(className="bi bi-save me-1"), "Save Signal"],
                        id="rl-factor-create-signal",
                        color="primary",
                        className="mt-2"
                    ),
                    html.Div(id="rl-factor-preview", className="mt-3")
                ], id_prefix="rl-factor-create")
            ])
        ], className="mt-3")
    ], id="rl-factor-content")


def _create_screen_tab():
    """Create the Screen & Universe Builder subtab content."""
    return html.Div([
        html.H4("🔎 Screen & Universe Builder", className="text-light mb-3 mt-3"),
        
        components.section_card("Filter Builder", [
            components.screen_builder_form()
        ], id_prefix="rl-screen-builder"),
        
        dbc.Row([
            dbc.Col([
                components.section_card("Screen Results", [
                    html.Div(id="rl-screen-results", children=[
                        components.empty_state("Configure filters and run screen", icon="bi-funnel")
                    ])
                ], id_prefix="rl-screen-results-section")
            ], md=8),
            dbc.Col([
                components.section_card("Saved Screens", [
                    html.Div(id="rl-screen-saved", children=[
                        components.empty_state("No saved screens yet", icon="bi-bookmark")
                    ]),
                    html.Hr(className="border-secondary"),
                    dbc.Button(
                        [html.I(className="bi bi-upload me-1"), "Export to Picks"],
                        id="rl-screen-export-btn",
                        color="secondary",
                        size="sm",
                        disabled=True
                    )
                ], id_prefix="rl-screen-saved-section")
            ], md=4)
        ], className="mt-3")
    ], id="rl-screen-content")


def _create_rag_tab():
    """Create the RAG Chat & Explain subtab content."""
    return html.Div([
        html.H4("🤖 RAG Chat & Explain", className="text-light mb-3 mt-3"),
        html.P(
            "Ask questions about your research documents. Answers are generated from your indexed content.",
            className="text-muted mb-3"
        ),
        
        dbc.Row([
            dbc.Col([
                components.rag_chat_interface()
            ], md=8),
            dbc.Col([
                components.section_card("Index Info", [
                    html.Div(id="rl-rag-index-info", children=[
                        html.P("Documents indexed: 0", className="text-muted small"),
                        html.P("Last update: Never", className="text-muted small"),
                        dbc.Button(
                            "Go to Diagnostics",
                            id="rl-rag-go-diag",
                            color="link",
                            size="sm"
                        )
                    ])
                ], id_prefix="rl-rag-info"),
                
                components.section_card("Export", [
                    dbc.Button(
                        [html.I(className="bi bi-file-earmark-text me-1"), "Create Brief from Answer"],
                        id="rl-rag-create-brief-btn",
                        color="secondary",
                        size="sm",
                        disabled=True,
                        className="w-100"
                    )
                ], id_prefix="rl-rag-export")
            ], md=4)
        ]),
        
        html.Hr(className="my-4"),
        
        # FinGPT Forecaster Section
        html.H4("📈 FinGPT Forecaster", className="text-light mb-3"),
        html.P(
            "Generate AI-powered stock price movement forecasts using news and fundamentals.",
            className="text-muted mb-3"
        ),
        
        dbc.Row([
            dbc.Col([
                components.section_card("Forecast Settings", [
                    html.Label("Ticker Symbol:", className="text-light"),
                    dbc.Input(
                        id="rl-forecast-ticker",
                        placeholder="e.g., AAPL, NVDA, MSFT",
                        value="AAPL",
                        className="mb-3"
                    ),
                    
                    html.Label("Weeks of News History:", className="text-light"),
                    dcc.Slider(
                        id="rl-forecast-weeks",
                        min=1,
                        max=12,
                        step=1,
                        value=4,
                        marks={1: '1w', 4: '4w', 8: '8w', 12: '12w'},
                        className="mb-3"
                    ),
                    
                    dbc.Checklist(
                        id="rl-forecast-options",
                        options=[
                            {"label": "Include Financials", "value": "financials"}
                        ],
                        value=["financials"],
                        className="mb-3"
                    ),
                    
                    dbc.Button(
                        [html.I(className="bi bi-graph-up-arrow me-1"), "Generate Forecast"],
                        id="rl-forecast-run-btn",
                        color="primary",
                        className="w-100"
                    )
                ], id_prefix="rl-forecast-settings")
            ], md=4),
            
            dbc.Col([
                components.section_card("Forecast Result", [
                    dcc.Loading(
                        html.Div(id="rl-forecast-result", children=[
                            components.empty_state("Click 'Generate Forecast' to see predictions", icon="bi-graph-up")
                        ])
                    )
                ], id_prefix="rl-forecast-result-card")
            ], md=8)
        ]),
        
        dcc.Store(id="rl-forecast-data", data=None)
        
    ], id="rl-rag-content")


def _create_briefs_tab():
    """Create the Briefs & Notes subtab content."""
    return html.Div([
        html.H4("📝 Briefs & Notes", className="text-light mb-3 mt-3"),
        
        # Control bar
        html.Div([
            dbc.Button(
                [html.I(className="bi bi-plus me-1"), "New Brief"],
                id="rl-brief-create",
                color="primary",
                className="me-2"
            ),
            dbc.Button(
                [html.I(className="bi bi-arrow-clockwise me-1"), "Refresh"],
                id="rl-refresh-btn",
                color="secondary",
                outline=True,
                className="me-2"
            ),
            dbc.Button(
                "Load Demo",
                id="rl-load-demo-btn",
                color="info",
                outline=True,
                size="sm"
            )
        ], className="mb-3"),
        
        dbc.Row([
            # Left: Brief list
            dbc.Col([
                components.section_card("Your Briefs", [
                    html.Div(id="rl-brief-list", children=[
                        components.empty_brief_list()
                    ])
                ], id_prefix="rl-briefs-list")
            ], md=4),
            
            # Right: Detail panel
            dbc.Col([
                components.section_card("Brief Detail", [
                    html.Div(id="rl-brief-view", children=[
                        components.empty_detail_panel()
                    ])
                ], id_prefix="rl-briefs-detail")
            ], md=8)
        ])
    ], id="rl-briefs-content")


def _create_experiment_tab():
    """Create the Experiment Tracker & Backtest Preview subtab content."""
    return html.Div([
        html.H4("🧪 Experiment Tracker", className="text-light mb-3 mt-3"),
        html.P(
            "Run quick backtest previews and track your research experiments.",
            className="text-muted mb-3"
        ),
        
        dbc.Row([
            dbc.Col([
                components.experiment_run_form(),
                
                components.section_card("Preview Results", [
                    html.Div(id="rl-exp-results", children=[
                        components.empty_state("Run an experiment to see preview results", icon="bi-graph-up-arrow")
                    ])
                ], id_prefix="rl-exp-results-section")
            ], md=7),
            
            dbc.Col([
                components.section_card("Recent Experiments", [
                    html.Div(id="rl-exp-list", children=[
                        components.empty_state("No experiments yet", icon="bi-flask")
                    ]),
                    html.Hr(className="border-secondary"),
                    dbc.Button(
                        [html.I(className="bi bi-box-arrow-up-right me-1"), "Send to Strategy Lab"],
                        id="rl-exp-export",
                        color="secondary",
                        size="sm",
                        disabled=True
                    )
                ], id_prefix="rl-exp-list-section")
            ], md=5)
        ])
    ], id="rl-exp-content")


def _create_diagnostics_tab():
    """Create the Diagnostics & Index Health subtab content."""
    # Get initial health status (lazy, no side effects)
    initial_health = data.get_index_health()
    
    return html.Div([
        html.H4("⚙️ Diagnostics & Index Health", className="text-light mb-3 mt-3"),
        
        html.Div(id="rl-diag-index-stats", children=[
            components.index_health_display(initial_health)
        ]),
        
        components.ingestion_logs_display([]),
        
        components.section_card("RAG Configuration", [
            dbc.Row([
                dbc.Col([
                    html.Label("LLM Provider", className="text-light"),
                    dcc.Dropdown(
                        id="rl-diag-llm-provider",
                        options=[
                            {"label": "Auto (Best Available)", "value": "auto"},
                            {"label": "OpenAI (Cloud - Requires API Key)", "value": "openai"},
                            {"label": "Ollama (Local Server)", "value": "ollama"},
                            {"label": "GPT4All (Local - Recommended)", "value": "gpt4all"},
                            {"label": "Mock (Testing Only)", "value": "mock"}
                        ],
                        value="auto",
                        className="mb-2"
                    )
                ], md=4),
                dbc.Col([
                    html.Label("Embedding Model", className="text-light"),
                    dcc.Dropdown(
                        id="rl-diag-embed-model",
                        options=[
                            {"label": "all-MiniLM-L6-v2 (Default)", "value": "minilm"},
                            {"label": "BAAI/bge-small-en", "value": "bge-small"},
                            {"label": "text-embedding-ada-002", "value": "ada-002"}
                        ],
                        value="minilm",
                        className="mb-2"
                    )
                ], md=4),
                dbc.Col([
                    html.Label("Top-K Results", className="text-light"),
                    dbc.Input(
                        id="rl-diag-topk",
                        type="number",
                        value=5,
                        min=1,
                        max=20,
                        className="bg-dark text-light mb-2"
                    )
                ], md=4)
            ]),
            dbc.Button(
                [html.I(className="bi bi-save me-1"), "Save Config"],
                id="rl-diag-save-config",
                color="primary",
                size="sm",
                className="mt-2"
            )
        ], id_prefix="rl-diag-config")
    ], id="rl-diag-content")


# ============================================================================
# MODAL
# ============================================================================

def _create_brief_modal():
    """
    Create the brief edit modal.
    
    CRITICAL: is_open=False - modal does NOT auto-open on page load.
    Modal only opens on explicit user action (clicking New Brief or Edit button).
    """
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle(id="rl-modal-title", children="New Research Brief")),
        dbc.ModalBody([
            dbc.Form([
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
                ], className="mb-2"),
                
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
                ], className="mb-2"),
                
                dbc.Row([
                    dbc.Label("Summary", width=3),
                    dbc.Col([
                        dbc.Textarea(
                            id="rl-brief-summary-input",
                            placeholder="Brief summary",
                            rows=2,
                            className="mb-3"
                        )
                    ], width=9)
                ], className="mb-2"),
                
                dbc.Row([
                    dbc.Label("Body", width=3),
                    dbc.Col([
                        dbc.Textarea(
                            id="rl-brief-body-input",
                            placeholder="Full content (Markdown supported)",
                            rows=8,
                            className="mb-3"
                        )
                    ], width=9)
                ])
            ])
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancel", id="rl-modal-cancel", color="secondary", className="me-2"),
            dbc.Button("Save", id="rl-modal-save", color="primary")
        ])
    ], id="rl-brief-modal", is_open=False, size="lg")


def _create_beginner_howto_modal():
    """
    Modal that displays the full Research Lab HOWTO content.
    Content is loaded via a callback into the store `rl-beginner-howto-store`.
    """
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Beginner's Guide: Research Lab")),
        dbc.ModalBody([
            dcc.Markdown(id="rl-beginner-howto-md", children="Loading...", style={"color": "#000000"})
        ], style={"maxHeight": "70vh", "overflow": "auto", "backgroundColor": "#ffffff", "padding": "12px"}),
        dbc.ModalFooter([
            dbc.Button("Download .md", id="rl-beginner-howto-download", color="secondary", size="sm", className="me-2"),
            dbc.Button("Close", id="rl-beginner-howto-close", color="secondary")
        ])
    ], id="rl-beginner-howto-modal", is_open=False, size="lg")
