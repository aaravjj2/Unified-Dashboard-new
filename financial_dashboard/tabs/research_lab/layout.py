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
                className="text-muted mb-3"
            ),
        ], style={
            'background-color': '#2b3035',
            'padding': '20px',
            'border-radius': '8px',
            'margin-bottom': '20px'
        }),
        
        # Main content area
        dbc.Row([
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
                                className="text-muted text-center p-3"
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
                        html.I(className="bi bi-arrow-left-circle me-2", style={'font-size': '3rem'}),
                        html.H5("Select a brief from the list to view details", className="text-muted mt-3")
                    ], className="text-center p-5")
                ])
            ], width=8)
        ]),
        
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
        
        # Alert for status messages
        dbc.Alert(
            id="rl-alert",
            is_open=False,
            duration=4000,
            dismissable=True
        )
        
    ], fluid=True)


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
                html.H6(title, className="card-title mb-2"),
                html.P(
                    summary[:100] + "..." if len(summary) > 100 else summary,
                    className="card-text text-muted small mb-2"
                ),
                html.Div(tags_badges, className="mb-2"),
                html.Small([
                    html.I(className="bi bi-clock me-1"),
                    f"Updated: {last_updated}"
                ], className="text-muted"),
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
