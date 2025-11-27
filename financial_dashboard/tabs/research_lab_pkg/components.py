"""
Research Lab - Components Module

Reusable UI components for the Research Lab interface.
All components are pure functions returning Dash elements.
No side effects or network calls.
"""

from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from typing import List, Dict, Optional, Any


# ============================================================================
# LAYOUT WRAPPERS
# ============================================================================

def tab_shell(tab_id: str, title: str, children, icon: str = "📊"):
    """
    Wrapper for subtab content with error boundary.
    
    Args:
        tab_id: Unique tab identifier
        title: Tab title
        children: Tab content
        icon: Emoji icon for the tab
    
    Returns:
        Wrapped content with error handling
    """
    try:
        return html.Div([
            html.H4([icon, " ", title], className="mb-3 text-light mt-3"),
            html.Div(children, id=f"{tab_id}-content")
        ], id=tab_id)
    except Exception as e:
        return html.Div([
            html.H4([icon, " ", title], className="mb-3 text-light mt-3"),
            error_panel(f"Error rendering tab: {str(e)}")
        ], id=tab_id)


def section_card(title: str, children, id_prefix: str = None):
    """Create a styled card section."""
    card_id = f"{id_prefix}-card" if id_prefix else None
    return dbc.Card([
        dbc.CardHeader(html.H5(title, className="text-light mb-0")),
        dbc.CardBody(children)
    ], className="bg-dark border-secondary mb-3", id=card_id)


# ============================================================================
# STATUS / FEEDBACK COMPONENTS
# ============================================================================

def empty_state(message: str, icon: str = "bi-inbox"):
    """Component shown when no data exists."""
    return html.Div([
        html.I(className=f"bi {icon}", style={'font-size': '3rem', 'opacity': '0.3'}),
        html.P(message, className="text-muted text-center mt-3")
    ], className="text-center p-4")


def error_panel(message: str):
    """Component for displaying errors."""
    return dbc.Alert([
        html.I(className="bi bi-exclamation-triangle me-2"),
        message
    ], color="danger")


def loading_panel(message: str = "Loading..."):
    """Component for loading states."""
    return html.Div([
        dbc.Spinner(size="lg"),
        html.P(message, className="text-muted mt-3")
    ], className="text-center p-4")


def success_alert(message: str):
    """Success alert component."""
    return dbc.Alert([
        html.I(className="bi bi-check-circle me-2"),
        message
    ], color="success", dismissable=True)


def warning_alert(message: str):
    """Warning alert component."""
    return dbc.Alert([
        html.I(className="bi bi-exclamation-circle me-2"),
        message
    ], color="warning", dismissable=True)


# ============================================================================
# BRIEF COMPONENTS
# ============================================================================

def brief_card(brief_id: str, title: str, summary: str, tags: List[str],
               created_at: str, last_updated: str, status: str = "published"):
    """
    Create a brief card for list display.
    
    CRITICAL: No modals auto-open. View only triggers on explicit click.
    """
    status_badge = dbc.Badge(
        status.title(),
        color="success" if status == "published" else "warning",
        className="ms-2"
    )
    
    tag_badges = [
        dbc.Badge(tag, color="secondary", className="me-1")
        for tag in (tags or [])[:3]
    ]
    
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.H6([
                    title,
                    status_badge
                ], className="text-light mb-1"),
                html.Small(summary[:100] + "..." if len(summary) > 100 else summary,
                          className="text-muted d-block mb-2"),
                html.Div(tag_badges, className="mb-2"),
                html.Div([
                    html.Small(f"Created: {created_at}", className="text-muted me-3"),
                    html.Small(f"Updated: {last_updated}", className="text-muted")
                ]),
                dbc.Button(
                    "View",
                    id={"type": "rl-select-brief", "index": brief_id},
                    color="primary",
                    size="sm",
                    className="mt-2"
                )
            ])
        ])
    ], className="bg-dark border-secondary mb-2")


def brief_detail_view(brief: Optional[Dict]):
    """Create detailed view of a brief."""
    if not brief:
        return empty_state("Select a brief to view details", icon="bi-file-text")
    
    return html.Div([
        html.H4(brief.get("title", "Untitled"), className="text-light mb-2"),
        html.Div([
            dbc.Badge(tag, color="secondary", className="me-1")
            for tag in brief.get("tags", [])
        ], className="mb-3"),
        
        dbc.Tabs([
            dbc.Tab([
                html.Div([
                    dcc.Markdown(brief.get("body", ""), className="text-light")
                ], className="p-3")
            ], label="Content", tab_id="brief-content"),
            dbc.Tab([
                html.Div([
                    html.P(brief.get("notes", "No notes"), className="text-muted")
                ], className="p-3")
            ], label="Notes", tab_id="brief-notes")
        ], id="rl-brief-detail-tabs", active_tab="brief-content"),
        
        html.Hr(className="border-secondary mt-3"),
        
        html.Div([
            dbc.Button("Edit", id="rl-brief-edit-btn", color="primary", size="sm", className="me-2"),
            dbc.Button("Export", id="rl-brief-export-btn", color="secondary", size="sm", className="me-2"),
            dbc.Button("Delete", id="rl-brief-delete-btn", color="danger", size="sm", outline=True)
        ])
    ])


def empty_brief_list():
    """Component shown when no briefs exist."""
    return empty_state("No briefs found — click New Brief or Load Demo", icon="bi-inbox")


def empty_detail_panel():
    """Component shown when no brief is selected."""
    return empty_state("Select a brief from the list to view details", icon="bi-arrow-left-circle")


# ============================================================================
# SCAN / SEARCH COMPONENTS
# ============================================================================

def ticker_search_input(id_prefix: str = "rl-scan"):
    """Create ticker search input component."""
    return html.Div([
        html.Label("Tickers", htmlFor=f"{id_prefix}-ticker", className="text-light"),
        dbc.InputGroup([
            dbc.Input(
                id=f"{id_prefix}-ticker",
                type="text",
                placeholder="AAPL,MSFT,GOOGL",
                className="bg-dark text-light"
            ),
            dbc.Button(
                [html.I(className="bi bi-search me-1"), "Search"],
                id=f"{id_prefix}-run-btn",
                color="primary"
            )
        ])
    ], className="mb-3")


def news_feed_item(item: Dict):
    """Create a news feed item component."""
    return dbc.Card([
        dbc.CardBody([
            html.H6([
                dbc.Badge(item.get("ticker", ""), color="info", className="me-2"),
                item.get("headline", "")
            ], className="text-light"),
            html.P(item.get("summary", "")[:150] + "...", className="text-muted small mb-1"),
            html.Small([
                html.Span(item.get("source", ""), className="me-2"),
                html.Span(item.get("datetime", "")[:10])
            ], className="text-muted")
        ])
    ], className="bg-dark border-secondary mb-2")


def scan_results_table(results: List[Dict]):
    """Create scan results table."""
    if not results:
        return empty_state("No results. Run a scan to see matches.", icon="bi-table")
    
    return dash_table.DataTable(
        id="rl-scan-results-table",
        columns=[
            {"name": "Symbol", "id": "symbol"},
            {"name": "Score", "id": "score", "type": "numeric", "format": {"specifier": ".3f"}},
            {"name": "Sector", "id": "sector"},
            {"name": "Momentum", "id": "momentum", "type": "numeric", "format": {"specifier": ".3f"}},
            {"name": "Value", "id": "value", "type": "numeric", "format": {"specifier": ".3f"}},
            {"name": "Growth", "id": "growth", "type": "numeric", "format": {"specifier": ".3f"}}
        ],
        data=results,
        style_table={"overflowX": "auto"},
        style_cell={
            "backgroundColor": "#2b3035",
            "color": "#fff",
            "border": "1px solid #444"
        },
        style_header={
            "backgroundColor": "#1a1d20",
            "fontWeight": "bold"
        },
        style_data_conditional=[
            {
                "if": {"filter_query": "{momentum} > 0", "column_id": "momentum"},
                "color": "#00bc8c"
            },
            {
                "if": {"filter_query": "{momentum} < 0", "column_id": "momentum"},
                "color": "#e74c3c"
            },
            {
                "if": {"filter_query": "{value} > 0", "column_id": "value"},
                "color": "#00bc8c"
            },
            {
                "if": {"filter_query": "{value} < 0", "column_id": "value"},
                "color": "#e74c3c"
            },
            {
                "if": {"filter_query": "{growth} > 0", "column_id": "growth"},
                "color": "#00bc8c"
            },
            {
                "if": {"filter_query": "{growth} < 0", "column_id": "growth"},
                "color": "#e74c3c"
            }
        ],
        row_selectable="single",
        page_size=10
    )


# ============================================================================
# FACTOR / CORRELATION COMPONENTS
# ============================================================================

def factor_heatmap_placeholder(id_str: str = "rl-factor-heatmap"):
    """Placeholder for factor correlation heatmap (Plotly graph)."""
    return dcc.Graph(
        id=id_str,
        figure={
            "data": [],
            "layout": {
                "template": "plotly_dark",
                "title": "Factor Correlation Heatmap",
                "paper_bgcolor": "#2b3035",
                "plot_bgcolor": "#2b3035"
            }
        },
        config={"displayModeBar": False}
    )


def factor_exposure_table(exposures: Dict[str, Dict[str, float]]):
    """Create factor exposure table."""
    if not exposures:
        return empty_state("No factor data. Select tickers to analyze.", icon="bi-graph-up")
    
    # Convert to table format
    rows = []
    for ticker, factors in exposures.items():
        row = {"ticker": ticker}
        row.update(factors)
        rows.append(row)
    
    columns = [{"name": "Ticker", "id": "ticker"}]
    if rows:
        factor_cols = [k for k in rows[0].keys() if k != "ticker"]
        columns.extend([{"name": f.title(), "id": f} for f in factor_cols])
    
    return dash_table.DataTable(
        id="rl-factor-table",
        columns=columns,
        data=rows,
        style_table={"overflowX": "auto"},
        style_cell={
            "backgroundColor": "#2b3035",
            "color": "#fff",
            "border": "1px solid #444"
        },
        style_header={
            "backgroundColor": "#1a1d20",
            "fontWeight": "bold"
        },
        style_data_conditional=[
            {
                "if": {"filter_query": "{momentum} > 0"},
                "color": "#28a745"
            },
            {
                "if": {"filter_query": "{momentum} < 0"},
                "color": "#dc3545"
            }
        ]
    )


# ============================================================================
# RAG / CHAT COMPONENTS
# ============================================================================

def rag_chat_interface():
    """Create the RAG chat interface."""
    return html.Div([
        # Query input
        html.Div([
            html.Label("Ask a question about your research documents:", className="text-light mb-2"),
            dbc.InputGroup([
                dbc.Textarea(
                    id="rl-rag-query-input",
                    placeholder="e.g., What are the key momentum signals in tech sector?",
                    rows=2,
                    className="bg-dark text-light"
                ),
            ]),
            html.Div([
                dbc.Button(
                    [html.I(className="bi bi-send me-1"), "Ask"],
                    id="rl-rag-run-btn",
                    color="primary",
                    className="mt-2 me-2"
                ),
                dbc.Button(
                    [html.I(className="bi bi-lightbulb me-1"), "Explain"],
                    id="rl-rag-explain-btn",
                    color="secondary",
                    outline=True,
                    className="mt-2",
                    disabled=True  # Enable after answer
                )
            ])
        ], className="mb-4"),
        
        # Source selection
        html.Div([
            html.Label("Source Filter:", className="text-light"),
            dcc.Dropdown(
                id="rl-rag-source-filter",
                options=[
                    {"label": "All Sources", "value": "all"},
                    {"label": "Research Briefs", "value": "briefs"},
                    {"label": "News", "value": "news"},
                    {"label": "Ingested Docs", "value": "docs"}
                ],
                value="all",
                className="mb-3"
            )
        ]),
        
        # Answer display
        html.Div([
            html.H5("Answer", className="text-light"),
            dcc.Loading(
                html.Div(id="rl-rag-answer", className="p-3 bg-dark rounded"),
                type="circle"
            )
        ], className="mb-4"),
        
        # Sources display
        html.Div([
            html.H5("Sources", className="text-light"),
            html.Div(id="rl-rag-sources", className="mt-2")
        ])
    ])


def rag_source_card(doc_id: str, title: str, snippet: str, score: float):
    """Create a source citation card."""
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.H6(title, className="text-light mb-1"),
                dbc.Badge(f"Score: {score:.2f}", color="info", className="ms-2")
            ], className="d-flex align-items-center mb-2"),
            html.P(snippet[:200] + "..." if len(snippet) > 200 else snippet,
                  className="text-muted small mb-0"),
            html.Small(f"Doc ID: {doc_id}", className="text-muted")
        ])
    ], className="bg-dark border-secondary mb-2")


# ============================================================================
# EXPERIMENT TRACKER COMPONENTS
# ============================================================================

def experiment_card(exp: Dict):
    """Create an experiment summary card."""
    metrics = exp.get("metrics") or {}
    status = exp.get("status", "unknown")
    
    status_color = {
        "completed": "success",
        "running": "info",
        "failed": "danger",
        "pending": "warning"
    }.get(status, "secondary")
    
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.H6(exp.get("name", "Unnamed"), className="text-light mb-0"),
                dbc.Badge(status.title(), color=status_color, className="ms-2")
            ], className="d-flex align-items-center mb-2"),
            
            html.P(f"Strategy: {exp.get('strategy', 'N/A')}", className="text-muted small mb-2"),
            
            dbc.Row([
                dbc.Col([
                    html.Small("Return", className="text-muted d-block"),
                    html.Strong(f"{metrics.get('total_return', 0)*100:.1f}%", 
                               className="text-success" if metrics.get('total_return', 0) > 0 else "text-danger")
                ], width=3) if metrics else None,
                dbc.Col([
                    html.Small("Sharpe", className="text-muted d-block"),
                    html.Strong(f"{metrics.get('sharpe_ratio', 0):.2f}", className="text-info")
                ], width=3) if metrics else None,
                dbc.Col([
                    html.Small("Max DD", className="text-muted d-block"),
                    html.Strong(f"{metrics.get('max_drawdown', 0)*100:.1f}%", className="text-danger")
                ], width=3) if metrics else None,
                dbc.Col([
                    html.Small("Win Rate", className="text-muted d-block"),
                    html.Strong(f"{metrics.get('win_rate', 0)*100:.0f}%", className="text-light")
                ], width=3) if metrics else None
            ]) if metrics else html.P("Metrics pending...", className="text-muted small"),
            
            html.Hr(className="border-secondary my-2"),
            html.Small(f"Created: {exp.get('created_at', 'N/A')}", className="text-muted")
        ])
    ], className="bg-dark border-secondary mb-2")


def experiment_run_form():
    """Create experiment run configuration form."""
    return dbc.Card([
        dbc.CardHeader("Run New Experiment"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Strategy", className="text-light"),
                    dcc.Dropdown(
                        id="rl-exp-strategy",
                        options=[
                            {"label": "Momentum", "value": "momentum"},
                            {"label": "Mean Reversion", "value": "mean_reversion"},
                            {"label": "Breakout", "value": "breakout"}
                        ],
                        value="momentum",
                        className="mb-2"
                    )
                ], width=4),
                dbc.Col([
                    html.Label("Lookback (days)", className="text-light"),
                    dbc.Input(
                        id="rl-exp-lookback",
                        type="number",
                        value=20,
                        min=5,
                        max=200,
                        className="bg-dark text-light mb-2"
                    )
                ], width=4),
                dbc.Col([
                    html.Label("Top N", className="text-light"),
                    dbc.Input(
                        id="rl-exp-topn",
                        type="number",
                        value=5,
                        min=1,
                        max=20,
                        className="bg-dark text-light mb-2"
                    )
                ], width=4)
            ]),
            dbc.Button(
                [html.I(className="bi bi-play me-1"), "Run Preview"],
                id="rl-exp-run-btn",
                color="primary",
                className="mt-2"
            )
        ])
    ], className="bg-dark border-secondary mb-3")


# ============================================================================
# DIAGNOSTICS COMPONENTS
# ============================================================================

def index_health_display(health: Dict):
    """Create index health status display."""
    status = health.get("status", "unknown")
    status_color = {"ok": "success", "empty": "warning", "error": "danger"}.get(status, "secondary")
    
    return dbc.Card([
        dbc.CardHeader([
            html.H5("Vector Index Health", className="mb-0 d-inline"),
            dbc.Badge(status.upper(), color=status_color, className="ms-2")
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Small("Documents", className="text-muted d-block"),
                    html.H4(health.get("doc_count", 0), className="text-light")
                ], width=3),
                dbc.Col([
                    html.Small("Index Size", className="text-muted d-block"),
                    html.H4(f"{health.get('index_size', 0) / 1024:.1f} KB", className="text-light")
                ], width=3),
                dbc.Col([
                    html.Small("Last Updated", className="text-muted d-block"),
                    html.H6(health.get("last_updated", "Never")[:16] if health.get("last_updated") else "Never",
                           className="text-light")
                ], width=3),
                dbc.Col([
                    html.Small("Errors", className="text-muted d-block"),
                    html.H4(len(health.get("errors", [])), 
                           className="text-danger" if health.get("errors") else "text-success")
                ], width=3)
            ]),
            
            html.Hr(className="border-secondary"),
            
            html.Div([
                dbc.Button("Rebuild Index", id="rl-diag-rebuild-btn", color="warning", size="sm", className="me-2"),
                dbc.Button("Refresh Stats", id="rl-diag-refresh-btn", color="secondary", size="sm")
            ])
        ])
    ], className="bg-dark border-secondary")


def ingestion_logs_display(logs: List[str]):
    """Create ingestion logs display."""
    return dbc.Card([
        dbc.CardHeader("Ingestion Logs"),
        dbc.CardBody([
            html.Pre(
                "\n".join(logs[-50:]) if logs else "No recent logs",
                style={
                    "backgroundColor": "#1a1d20",
                    "color": "#98d1ce",
                    "padding": "10px",
                    "borderRadius": "4px",
                    "maxHeight": "300px",
                    "overflow": "auto",
                    "fontSize": "12px"
                },
                id="rl-diag-logs"
            )
        ])
    ], className="bg-dark border-secondary mt-3")


# ============================================================================
# SCREEN BUILDER COMPONENTS
# ============================================================================

def screen_builder_form():
    """Create the screen/universe builder form."""
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.Label("Sector Filter", className="text-light"),
                dcc.Dropdown(
                    id="rl-screen-sector",
                    options=[
                        {"label": "All Sectors", "value": "all"},
                        {"label": "Technology", "value": "tech"},
                        {"label": "Healthcare", "value": "health"},
                        {"label": "Financials", "value": "finance"},
                        {"label": "Consumer", "value": "consumer"},
                        {"label": "Energy", "value": "energy"}
                    ],
                    value="all",
                    className="mb-2"
                )
            ], width=4),
            dbc.Col([
                html.Label("Min Liquidity ($M)", className="text-light"),
                dbc.Input(
                    id="rl-screen-liquidity",
                    type="number",
                    value=10,
                    min=0,
                    className="bg-dark text-light mb-2"
                )
            ], width=4),
            dbc.Col([
                html.Label("Max Volatility (%)", className="text-light"),
                dbc.Input(
                    id="rl-screen-volatility",
                    type="number",
                    value=50,
                    min=0,
                    max=200,
                    className="bg-dark text-light mb-2"
                )
            ], width=4)
        ]),
        dbc.Row([
            dbc.Col([
                html.Label("Momentum Threshold", className="text-light"),
                dcc.Slider(
                    id="rl-screen-momentum",
                    min=-1,
                    max=1,
                    step=0.1,
                    value=0,
                    marks={-1: "-1", 0: "0", 1: "1"},
                    className="mb-2"
                )
            ], width=8),
            dbc.Col([
                dbc.Button(
                    [html.I(className="bi bi-funnel me-1"), "Run Screen"],
                    id="rl-screen-run-btn",
                    color="primary",
                    className="mt-4"
                )
            ], width=4)
        ], className="mt-2")
    ])
