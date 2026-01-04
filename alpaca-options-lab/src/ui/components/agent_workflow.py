"""
Agent Workflow Visualization Component

Provides visualization for LangGraph-based autonomous agents:
- Supervisor-Worker pattern display
- Agent state visualization
- Reasoning chain display
- Tool call monitoring
- MCP integration status

Reference: Deep-Tech Stack Roadmap Section 5
"""
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class AgentState(Enum):
    """Agent execution states"""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"


class AgentRole(Enum):
    """Agent roles in the system"""
    SUPERVISOR = "supervisor"
    TECHNICAL_ANALYST = "technical_analyst"
    MICROSTRUCTURE = "microstructure"
    OPTIONS_STRATEGIST = "options_strategist"
    FUNDAMENTAL = "fundamental"
    SYNTHESIS = "synthesis"


@dataclass
class ToolCall:
    """Record of a tool invocation"""
    timestamp: datetime
    tool_name: str
    args: Dict
    result: Optional[str] = None
    duration_ms: float = 0
    success: bool = True


@dataclass
class AgentMessage:
    """Message in agent reasoning chain"""
    timestamp: datetime
    role: str  # 'user', 'assistant', 'tool'
    content: str
    agent_name: Optional[str] = None


@dataclass
class AgentNode:
    """Single agent node in the workflow"""
    id: str
    role: AgentRole
    name: str
    state: AgentState = AgentState.IDLE
    current_task: str = ""
    messages: List[AgentMessage] = field(default_factory=list)
    tool_calls: List[ToolCall] = field(default_factory=list)
    last_output: str = ""


@dataclass
class WorkflowState:
    """Complete workflow state"""
    session_id: str
    query: str
    agents: Dict[str, AgentNode] = field(default_factory=dict)
    current_agent: Optional[str] = None
    completed: bool = False
    final_answer: str = ""


def create_mock_workflow_state() -> WorkflowState:
    """Generate mock workflow state for demo"""
    state = WorkflowState(
        session_id="sess_123",
        query="Analyze AAPL for potential gamma squeeze opportunities"
    )
    
    # Create agents
    state.agents = {
        "supervisor": AgentNode(
            id="supervisor",
            role=AgentRole.SUPERVISOR,
            name="Supervisor Agent",
            state=AgentState.THINKING,
            current_task="Routing analysis request to specialists",
            last_output="Initiating multi-agent analysis..."
        ),
        "technical": AgentNode(
            id="technical",
            role=AgentRole.TECHNICAL_ANALYST,
            name="Technical Analyst",
            state=AgentState.COMPLETED,
            current_task="",
            last_output="RSI: 65.2 (Neutral), MACD: Bullish crossover, Support at $175"
        ),
        "microstructure": AgentNode(
            id="microstructure",
            role=AgentRole.MICROSTRUCTURE,
            name="Microstructure Agent",
            state=AgentState.EXECUTING,
            current_task="Analyzing order book imbalance",
            last_output="Processing LOB data..."
        ),
        "options": AgentNode(
            id="options",
            role=AgentRole.OPTIONS_STRATEGIST,
            name="Options Strategist",
            state=AgentState.WAITING,
            current_task="Pending microstructure analysis",
            last_output=""
        ),
        "synthesis": AgentNode(
            id="synthesis",
            role=AgentRole.SYNTHESIS,
            name="Synthesis Agent",
            state=AgentState.IDLE,
            current_task="",
            last_output=""
        )
    }
    
    state.current_agent = "microstructure"
    
    return state


def get_state_color(state: AgentState) -> str:
    """Get color for agent state"""
    colors = {
        AgentState.IDLE: "#6c757d",
        AgentState.THINKING: "#ffc107",
        AgentState.EXECUTING: "#0d6efd",
        AgentState.WAITING: "#17a2b8",
        AgentState.COMPLETED: "#28a745",
        AgentState.ERROR: "#dc3545"
    }
    return colors.get(state, "#6c757d")


def get_state_icon(state: AgentState) -> str:
    """Get icon for agent state"""
    icons = {
        AgentState.IDLE: "⏸️",
        AgentState.THINKING: "🤔",
        AgentState.EXECUTING: "⚡",
        AgentState.WAITING: "⏳",
        AgentState.COMPLETED: "✅",
        AgentState.ERROR: "❌"
    }
    return icons.get(state, "❓")


def create_agent_card(agent: AgentNode, is_active: bool = False) -> dbc.Card:
    """Create a card for a single agent"""
    border_color = "primary" if is_active else "secondary"
    state_color = get_state_color(agent.state)
    
    return dbc.Card([
        dbc.CardHeader([
            html.Span(get_state_icon(agent.state), className="me-2"),
            html.Strong(agent.name),
            dbc.Badge(
                agent.state.value.upper(),
                color="light",
                text_color="dark",
                className="ms-auto",
                style={"backgroundColor": state_color}
            )
        ], className="d-flex align-items-center py-2"),
        dbc.CardBody([
            html.Small(f"Role: {agent.role.value}", className="text-muted d-block mb-2"),
            html.Div([
                html.Strong("Current Task: ", className="text-muted"),
                html.Span(agent.current_task or "None", className="text-info")
            ], className="mb-2") if agent.current_task else None,
            html.Div([
                html.Strong("Output: ", className="text-muted"),
                html.Span(
                    agent.last_output[:100] + "..." if len(agent.last_output) > 100 else agent.last_output,
                    className="text-success"
                )
            ]) if agent.last_output else None
        ], className="py-2")
    ], className=f"mb-2 border-{border_color}", outline=True)


def create_workflow_diagram(state: WorkflowState) -> go.Figure:
    """Create a visual diagram of the workflow"""
    agents = list(state.agents.values())
    
    # Node positions (supervisor at top, others in a row below, synthesis at bottom)
    positions = {
        "supervisor": (0.5, 1.0),
        "technical": (0.1, 0.6),
        "microstructure": (0.35, 0.6),
        "options": (0.65, 0.6),
        "fundamental": (0.9, 0.6),
        "synthesis": (0.5, 0.2)
    }
    
    fig = go.Figure()
    
    # Draw edges
    edges = [
        ("supervisor", "technical"),
        ("supervisor", "microstructure"),
        ("supervisor", "options"),
        ("technical", "synthesis"),
        ("microstructure", "synthesis"),
        ("options", "synthesis")
    ]
    
    for start, end in edges:
        if start in positions and end in positions:
            x0, y0 = positions[start]
            x1, y1 = positions[end]
            fig.add_trace(go.Scatter(
                x=[x0, x1],
                y=[y0, y1],
                mode='lines',
                line=dict(color='rgba(150,150,150,0.5)', width=2),
                hoverinfo='none',
                showlegend=False
            ))
    
    # Draw nodes
    for agent_id, (x, y) in positions.items():
        if agent_id in state.agents:
            agent = state.agents[agent_id]
            color = get_state_color(agent.state)
            is_active = state.current_agent == agent_id
            
            fig.add_trace(go.Scatter(
                x=[x],
                y=[y],
                mode='markers+text',
                marker=dict(
                    size=40 if is_active else 30,
                    color=color,
                    line=dict(width=3 if is_active else 1, color='white')
                ),
                text=[agent.name.split()[0]],
                textposition='bottom center',
                textfont=dict(size=10, color='white'),
                hovertemplate=(
                    f"<b>{agent.name}</b><br>"
                    f"State: {agent.state.value}<br>"
                    f"Task: {agent.current_task or 'None'}<extra></extra>"
                ),
                showlegend=False
            ))
    
    fig.update_layout(
        title="Agent Workflow Graph",
        template="plotly_dark",
        height=250,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.1, 1.1]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, 1.2]),
        hovermode='closest'
    )
    
    return fig


def create_reasoning_chain_display(state: WorkflowState) -> html.Div:
    """Create display for agent reasoning chain"""
    messages = [
        {"time": "10:30:01", "agent": "Supervisor", "content": "Received query: Analyze AAPL for gamma squeeze", "type": "input"},
        {"time": "10:30:02", "agent": "Supervisor", "content": "Routing to Technical Analyst for price analysis", "type": "routing"},
        {"time": "10:30:05", "agent": "Technical", "content": "Calling get_technical_indicators(AAPL)", "type": "tool"},
        {"time": "10:30:08", "agent": "Technical", "content": "RSI at 65.2, MACD bullish crossover detected", "type": "output"},
        {"time": "10:30:10", "agent": "Supervisor", "content": "Routing to Microstructure Agent", "type": "routing"},
        {"time": "10:30:12", "agent": "Microstructure", "content": "Querying LOB for order book imbalance...", "type": "tool"},
    ]
    
    return html.Div([
        html.Div([
            html.Div([
                html.Small(m["time"], className="text-muted me-2"),
                dbc.Badge(m["agent"], color={
                    "Supervisor": "primary",
                    "Technical": "success",
                    "Microstructure": "info",
                    "Options": "warning"
                }.get(m["agent"], "secondary"), className="me-2"),
                dbc.Badge(m["type"], color="dark", className="me-2"),
                html.Span(m["content"])
            ], className="mb-2 p-2 rounded", style={
                "backgroundColor": "rgba(255,255,255,0.05)"
            })
        for m in messages])
    ], style={"maxHeight": "300px", "overflowY": "auto"})


def create_tool_calls_monitor() -> dbc.Card:
    """Create tool calls monitoring panel"""
    calls = [
        {"time": "10:30:05", "tool": "get_technical_indicators", "status": "success", "duration": "1.2s"},
        {"time": "10:30:08", "tool": "get_options_chain", "status": "success", "duration": "0.8s"},
        {"time": "10:30:12", "tool": "query_lob_snapshot", "status": "running", "duration": "..."},
    ]
    
    return dbc.Card([
        dbc.CardHeader("🔧 Tool Calls Monitor"),
        dbc.CardBody([
            dbc.Table([
                html.Thead(html.Tr([
                    html.Th("Time"),
                    html.Th("Tool"),
                    html.Th("Status"),
                    html.Th("Duration")
                ])),
                html.Tbody([
                    html.Tr([
                        html.Td(html.Small(c["time"])),
                        html.Td(html.Code(c["tool"])),
                        html.Td(dbc.Badge(
                            c["status"],
                            color="success" if c["status"] == "success" else "info"
                        )),
                        html.Td(c["duration"])
                    ]) for c in calls
                ])
            ], bordered=True, hover=True, size="sm", className="mb-0")
        ])
    ])


def create_mcp_status_panel() -> dbc.Card:
    """Create MCP (Model Context Protocol) status panel"""
    servers = [
        {"name": "playwright-mcp", "status": "connected", "tools": ["click", "snapshot", "navigate"]},
        {"name": "filesystem-mcp", "status": "connected", "tools": ["read_file", "write_file"]},
        {"name": "openbb-mcp", "status": "disconnected", "tools": ["get_prices", "get_fundamentals"]},
    ]
    
    return dbc.Card([
        dbc.CardHeader([
            html.Span("🔌 MCP Servers", className="fw-bold"),
            dbc.Badge(f"{sum(1 for s in servers if s['status'] == 'connected')}/{len(servers)}", 
                     color="success", className="ms-2")
        ]),
        dbc.CardBody([
            html.Div([
                html.Div([
                    dbc.Badge(
                        "●",
                        color="success" if s["status"] == "connected" else "danger",
                        className="me-2"
                    ),
                    html.Strong(s["name"]),
                    html.Br(),
                    html.Small(
                        f"Tools: {', '.join(s['tools'][:3])}{'...' if len(s['tools']) > 3 else ''}",
                        className="text-muted"
                    )
                ], className="mb-2 p-2 rounded", style={"backgroundColor": "rgba(255,255,255,0.05)"})
            for s in servers])
        ])
    ])


def create_agent_workflow_card() -> dbc.Card:
    """
    Main agent workflow visualization component.
    """
    state = create_mock_workflow_state()
    
    return dbc.Card([
        dbc.CardHeader([
            html.Span("🤖 Agent Workflow", className="fw-bold"),
            html.Small(" | LangGraph Supervisor-Worker", className="text-muted ms-2"),
            dbc.Badge("ACTIVE", color="success", className="ms-auto", id="agent-workflow-status")
        ], className="d-flex align-items-center"),
        dbc.CardBody([
            # Query display
            dbc.Alert([
                html.Strong("Query: "),
                html.Span(state.query)
            ], color="info", className="mb-3"),
            
            # Workflow diagram
            dcc.Graph(
                id="agent-workflow-diagram",
                figure=create_workflow_diagram(state),
                config={'displayModeBar': False}
            ),
            
            # Agent cards row
            dbc.Row([
                dbc.Col([
                    create_agent_card(state.agents["supervisor"], state.current_agent == "supervisor")
                ], width=4),
                dbc.Col([
                    create_agent_card(state.agents["technical"], state.current_agent == "technical")
                ], width=4),
                dbc.Col([
                    create_agent_card(state.agents["microstructure"], state.current_agent == "microstructure")
                ], width=4),
            ], className="mb-3"),
            
            # Reasoning chain
            dbc.Accordion([
                dbc.AccordionItem([
                    create_reasoning_chain_display(state)
                ], title="📝 Reasoning Chain", item_id="reasoning"),
            ], id="agent-accordion", start_collapsed=True)
        ])
    ])


def create_agent_input_panel() -> dbc.Card:
    """Create panel for sending queries to agents"""
    return dbc.Card([
        dbc.CardHeader("💬 Query Agent System"),
        dbc.CardBody([
            dbc.Textarea(
                id="agent-query-input",
                placeholder="Enter your analysis query...\ne.g., 'Analyze TSLA options for earnings play'",
                rows=3,
                className="mb-2"
            ),
            dbc.Row([
                dbc.Col([
                    dbc.Select(
                        id="agent-mode-select",
                        options=[
                            {"label": "Full Analysis", "value": "full"},
                            {"label": "Technical Only", "value": "technical"},
                            {"label": "Options Focus", "value": "options"},
                            {"label": "Quick Scan", "value": "quick"}
                        ],
                        value="full"
                    )
                ], width=6),
                dbc.Col([
                    dbc.Button(
                        [html.I(className="fas fa-paper-plane me-2"), "Submit Query"],
                        id="agent-submit-btn",
                        color="primary",
                        className="w-100"
                    )
                ], width=6)
            ])
        ])
    ])


def create_agent_final_output() -> dbc.Card:
    """Create panel for displaying final agent output"""
    return dbc.Card([
        dbc.CardHeader("📊 Analysis Results"),
        dbc.CardBody([
            html.Div(id="agent-final-output", children=[
                dbc.Alert("Awaiting query submission...", color="secondary")
            ])
        ])
    ])
