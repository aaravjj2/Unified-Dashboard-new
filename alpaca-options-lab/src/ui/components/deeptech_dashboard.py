"""
Deep-Tech Stack Dashboard

Integrates all components from the roadmap:
- LOB Visualization (Microstructure)
- TradingView Charts (Interactive Charting)
- Agent Workflow (LangGraph Agents)
- Event Queue Monitor (EDA Architecture)

Reference: Deep-Tech Stack Roadmap
"""
from dash import html, dcc
import dash_bootstrap_components as dbc

# Import all roadmap components
from src.ui.components.lob_visualization import (
    create_lob_visualization_card,
    create_lob_event_feed
)
from src.ui.components.tradingview_chart import (
    create_tradingview_chart_card,
    create_price_alerts_panel,
    create_chart_events_log
)
from src.ui.components.agent_workflow import (
    create_agent_workflow_card,
    create_tool_calls_monitor,
    create_mcp_status_panel,
    create_agent_input_panel,
    create_agent_final_output
)
from src.ui.components.event_queue_monitor import (
    create_event_queue_card,
    create_event_filter_controls,
    create_event_type_legend
)


def create_deeptech_header() -> html.Div:
    """Create the dashboard header"""
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.H2([
                    html.Span("🔬", className="me-2"),
                    "Deep-Tech Stack Dashboard"
                ], className="mb-0"),
                html.Small(
                    "Event-Driven Backtesting | LOB Microstructure | TradingView Charts | Agentic Reasoning",
                    className="text-muted"
                )
            ], width=8),
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button([
                        html.I(className="fas fa-sync me-1"),
                        "Refresh"
                    ], id="deeptech-refresh-btn", color="secondary", size="sm", outline=True),
                    dbc.Button([
                        html.I(className="fas fa-cog me-1"),
                        "Settings"
                    ], id="deeptech-settings-btn", color="secondary", size="sm", outline=True),
                ], className="float-end")
            ], width=4, className="text-end")
        ]),
        html.Hr()
    ], className="mb-4")


def create_system_status_bar() -> dbc.Card:
    """Create system status indicator bar"""
    systems = [
        {"name": "LOB Engine", "status": "online", "latency": "45µs"},
        {"name": "Chart Server", "status": "online", "latency": "12ms"},
        {"name": "Agent System", "status": "online", "latency": "230ms"},
        {"name": "Event Queue", "status": "online", "latency": "1.2µs"},
        {"name": "MCP Servers", "status": "partial", "latency": "N/A"},
    ]
    
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        dbc.Badge(
                            "●",
                            color="success" if s["status"] == "online" else "warning" if s["status"] == "partial" else "danger",
                            className="me-1"
                        ),
                        html.Small(s["name"], className="me-2"),
                        html.Small(s["latency"], className="text-muted")
                    ])
                ], width=True) for s in systems
            ] + [
                dbc.Col([
                    html.Small("Last Update: ", className="text-muted"),
                    html.Small(id="deeptech-last-update", children="--:--:--")
                ], width=2, className="text-end")
            ])
        ], className="py-2")
    ], className="mb-3 bg-dark")


def create_deeptech_dashboard_layout() -> html.Div:
    """
    Main Deep-Tech Stack Dashboard Layout.
    
    Organized into tabs for each major component:
    1. Microstructure (LOB)
    2. Interactive Charts (TradingView)
    3. Agent Workflow (LangGraph)
    4. Event Architecture (EDA)
    """
    return html.Div([
        # Update interval
        dcc.Interval(id='deeptech-interval', interval=2000, n_intervals=0),
        
        # Header
        create_deeptech_header(),
        
        # System status
        create_system_status_bar(),
        
        # Main tabs
        dbc.Tabs([
            # Tab 1: Overview
            dbc.Tab([
                html.Div([
                    dbc.Row([
                        # Left: Chart
                        dbc.Col([
                            create_tradingview_chart_card()
                        ], width=8),
                        # Right: LOB
                        dbc.Col([
                            create_lob_visualization_card()
                        ], width=4)
                    ], className="mb-3"),
                    dbc.Row([
                        # Agent workflow
                        dbc.Col([
                            create_agent_workflow_card()
                        ], width=8),
                        # Event queue
                        dbc.Col([
                            create_event_queue_card()
                        ], width=4)
                    ])
                ], className="mt-3")
            ], label="📊 Overview", tab_id="tab-overview"),
            
            # Tab 2: Microstructure
            dbc.Tab([
                html.Div([
                    dbc.Row([
                        dbc.Col([
                            create_lob_visualization_card()
                        ], width=8),
                        dbc.Col([
                            create_lob_event_feed(),
                            html.Div(className="mb-3"),
                            dbc.Card([
                                dbc.CardHeader("📈 LOB Analytics"),
                                dbc.CardBody([
                                    html.P("Order Book Imbalance Tracking"),
                                    html.P("Spread Analysis"),
                                    html.P("Market Impact Estimation"),
                                    html.P("Trade Flow Toxicity"),
                                ])
                            ])
                        ], width=4)
                    ])
                ], className="mt-3")
            ], label="📚 LOB Microstructure", tab_id="tab-lob"),
            
            # Tab 3: Interactive Charts
            dbc.Tab([
                html.Div([
                    dbc.Row([
                        dbc.Col([
                            create_tradingview_chart_card()
                        ], width=9),
                        dbc.Col([
                            create_price_alerts_panel(),
                            html.Div(className="mb-3"),
                            create_chart_events_log()
                        ], width=3)
                    ])
                ], className="mt-3")
            ], label="📈 Interactive Charts", tab_id="tab-charts"),
            
            # Tab 4: Agent Workflow
            dbc.Tab([
                html.Div([
                    dbc.Row([
                        dbc.Col([
                            create_agent_input_panel(),
                            html.Div(className="mb-3"),
                            create_agent_workflow_card()
                        ], width=8),
                        dbc.Col([
                            create_mcp_status_panel(),
                            html.Div(className="mb-3"),
                            create_tool_calls_monitor(),
                            html.Div(className="mb-3"),
                            create_agent_final_output()
                        ], width=4)
                    ])
                ], className="mt-3")
            ], label="🤖 Agent Workflow", tab_id="tab-agents"),
            
            # Tab 5: Event Architecture
            dbc.Tab([
                html.Div([
                    create_event_filter_controls(),
                    create_event_type_legend(),
                    create_event_queue_card()
                ], className="mt-3")
            ], label="📨 Event Queue", tab_id="tab-events"),
            
        ], id="deeptech-tabs", active_tab="tab-overview")
    ], id="deeptech-dashboard", className="p-4")


def create_deeptech_mini_view() -> dbc.Card:
    """
    Create a mini view of deep-tech components for embedding in other dashboards.
    """
    return dbc.Card([
        dbc.CardHeader([
            html.Span("🔬 Deep-Tech Quick View", className="fw-bold"),
            dbc.Button(
                "Expand",
                id="deeptech-expand-btn",
                color="link",
                size="sm",
                className="ms-auto"
            )
        ], className="d-flex align-items-center"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H6("LOB Spread", className="text-muted mb-1"),
                    html.H4("$0.02", className="text-success mb-0", id="deeptech-mini-spread")
                ], width=3),
                dbc.Col([
                    html.H6("Imbalance", className="text-muted mb-1"),
                    html.H4("+12%", className="text-info mb-0", id="deeptech-mini-imbalance")
                ], width=3),
                dbc.Col([
                    html.H6("Events/sec", className="text-muted mb-1"),
                    html.H4("342", className="text-warning mb-0", id="deeptech-mini-events")
                ], width=3),
                dbc.Col([
                    html.H6("Agent Status", className="text-muted mb-1"),
                    html.H4("Active", className="text-primary mb-0", id="deeptech-mini-agent")
                ], width=3)
            ])
        ])
    ])
