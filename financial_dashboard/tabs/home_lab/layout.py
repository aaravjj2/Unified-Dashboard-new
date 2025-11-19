"""
Home Lab - Layout Module

Creates the command center dashboard with 5 main sections:
1. System Summary - Lab status and diagnostics
2. Portfolio Snapshot - Quick view of current holdings
3. Performance Insights - Cross-lab metrics summary
4. AI Insights - Automated analysis highlights (future Azure ML)
5. Getting Started - User help and documentation
"""

import logging
from dash_extensions.enrich import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime

from .helpers import (
    get_portfolio_summary,
    get_cross_lab_metrics,
    get_lab_status,
    compute_system_health,
    summarize_insights,
    format_currency,
    format_percentage,
    format_metric_color,
    generate_portfolio_sparkline
)

logger = logging.getLogger(__name__)

# ============================================================================
# SECTION 1: SYSTEM SUMMARY
# ============================================================================

def create_system_summary_section():
    """
    Dashboard overview with lab statuses and system diagnostics.
    """
    lab_statuses = get_lab_status()
    
    status_cards = []
    for lab_key, lab_info in lab_statuses.items():
        card = dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5([
                        html.Span(lab_info['icon'], className="me-2"),
                        lab_info['name']
                    ], className="mb-2"),
                    html.Div([
                        dbc.Badge("✅ Active", color="success", className="me-2"),
                        html.Small(f"Last: {lab_info['last_load']}", className="text-muted", style={'color': '#000000'})
                    ], className="mb-2"),
                    html.P([
                        html.Strong("Data: "),
                        html.Span(lab_info['data_source'], className="small text-muted", style={'color': '#000000'})
                    ], className="mb-0 small")
                ])
            ], className="h-100", style={'borderLeft': '4px solid #28a745'})
        ], md=6, lg=3, className="mb-3")
        status_cards.append(card)
    
    # Compute system health snapshot for display
    try:
        _sys = compute_system_health()
    except Exception as e:
        logger.exception("compute_system_health failed")
        _sys = {'percent': 0, 'issues': ['compute_system_health error'], 'details': {}}

    health_percent = int(_sys.get('percent', 0))
    health_issues = _sys.get('issues', []) or []
    # choose color
    if health_percent >= 90:
        health_color = 'success'
    elif health_percent >= 70:
        health_color = 'warning'
    else:
        health_color = 'danger'

    system_health_children = [
        dbc.Progress(value=health_percent, color=health_color, className="mb-2", style={'height': '20px'}),
        html.Small(f"{health_percent}% - {'All systems operational' if health_percent>=100 else 'Attention required'}", className="text-muted", style={'color': '#000000'})
    ]
    if health_issues:
        system_health_children.append(html.Ul([html.Li(issue) for issue in health_issues], className='mt-2', style={'color': '#000000'}))

    return dbc.Card([
        dbc.CardHeader([
            html.H5([
                html.I(className="bi bi-speedometer2 me-2"),
                "🎯 System Summary"
            ], className="mb-0")
        ]),
        dbc.CardBody([
            # Welcome Banner
            dbc.Alert([
                html.H4("Welcome to Financial Dashboard", className="alert-heading mb-2"),
                html.P([
                    "Version 2.0.0 | ",
                    html.Strong(datetime.now().strftime("%B %d, %Y - %H:%M")),
                    " | All systems operational"
                ], className="mb-0")
            ], color="info", className="mb-4"),
            
            # Lab Status Cards (compact responsive grid)
            html.H6("Lab Status Overview", className="mb-3 fw-bold"),
            # Use bootstrap responsive row-cols to avoid tall stacked cards
            dbc.Row(status_cards, className="lab-status-row row-cols-1 row-cols-sm-2 row-cols-md-4 g-2"),
            
            # Diagnostic Button
            dbc.Row([
                dbc.Col([
                    dbc.Button([
                        html.I(className="bi bi-check-circle me-2"),
                        "Run Full Diagnostic"
                    ], id='home-run-diagnostic-btn', color="primary", outline=True, className="w-100"),
                    html.Div(id='home-diagnostic-result', className="mt-3")
                ], md=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("System Health", className="mb-2"),
                            html.Div(system_health_children)
                        ], className="py-2 px-2")
                    ], className="bg-light")
                ], md=6)
            ])
        ])
    ], className="mb-4")


# ============================================================================
# SECTION 2: PORTFOLIO SNAPSHOT
# ============================================================================

def create_portfolio_snapshot_section():
    """
    Quick view of current portfolio holdings and performance.
    """
    portfolio_data = get_portfolio_summary()
    
    # Create mini table of top positions
    positions = portfolio_data.get('positions', [])
    table_rows = []
    
    for pos in positions[:10]:
        row = html.Tr([
            html.Td(pos.get('ticker', 'N/A'), className="fw-bold"),
            html.Td(pos.get('sector', 'N/A'), className="small"),
            html.Td(format_currency(pos.get('last_price', 0)), className="text-end"),
            html.Td([
                html.Span(
                    format_percentage(pos.get('daily_change_pct', 0)),
                    className=f"badge bg-{'success' if pos.get('daily_change_pct', 0) > 0 else 'danger'}"
                )
            ], className="text-end")
        ])
        table_rows.append(row)
    
    # Portfolio sparkline
    sparkline_data = generate_portfolio_sparkline()
    sparkline_fig = go.Figure()
    sparkline_fig.add_trace(go.Scatter(
        y=sparkline_data,
        mode='lines',
        fill='tozeroy',
        line=dict(color='#28a745', width=2),
        fillcolor='rgba(40, 167, 69, 0.1)'
    ))
    sparkline_fig.update_layout(
        height=120,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )
    
    return dbc.Card([
        dbc.CardHeader([
            html.H5([
                html.I(className="bi bi-wallet2 me-2"),
                "💼 Portfolio Snapshot"
            ], className="mb-0")
        ]),
        dbc.CardBody([
            # Beginner-friendly overview
            dcc.Markdown("""
**📊 What This Shows:**

A quick view of your current portfolio holdings loaded from the latest Weekly Picks data.

**Key Metrics:**
- **Total Value**: Sum of all position values (price × shares)
- **Daily Change**: Portfolio performance over the last trading day
- **Positions**: Number of tickers currently held

**💡 Tip:** The sparkline shows your portfolio trend over the past 30 days. Green means growth!
            """, className="small mb-3", style={
                'backgroundColor': '#f0f8ff',
                'padding': '15px',
                'borderRadius': '8px',
                'marginBottom': '20px',
                'color': '#000000'
            }),
            
            # Aggregate Metrics Row
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Tooltip(
                                "Total market value of all portfolio positions combined",
                                target="portfolio-total-value",
                                placement="top"
                            ),
                            html.Div([
                                html.Small("Total Value", className="text-muted d-block mb-1", style={'color': '#000000'}),
                                html.H4(format_currency(portfolio_data['total_value']), className="mb-0 text-primary")
                            ], id="portfolio-total-value")
                        ])
                    ], className="bg-light")
                ], md=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Tooltip(
                                "Portfolio return over the last trading day (average of position changes)",
                                target="portfolio-daily-change",
                                placement="top"
                            ),
                            html.Div([
                                html.Small("Daily Change", className="text-muted d-block mb-1", style={'color': '#000000'}),
                                html.H4([
                                    html.Span(
                                        format_percentage(portfolio_data['daily_change_pct']),
                                        className=f"text-{'success' if portfolio_data['daily_change_pct'] > 0 else 'danger'}"
                                    )
                                ], className="mb-0")
                            ], id="portfolio-daily-change")
                        ])
                    ], className="bg-light")
                ], md=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Tooltip(
                                "Total number of unique tickers in your portfolio",
                                target="portfolio-positions-count",
                                placement="top"
                            ),
                            html.Div([
                                html.Small("Positions", className="text-muted d-block mb-1", style={'color': '#000000'}),
                                html.H4(str(portfolio_data['total_positions']), className="mb-0")
                            ], id="portfolio-positions-count")
                        ])
                    ], className="bg-light")
                ], md=4)
            ], className="mb-4"),
            
            # Sparkline Trend
            html.H6("30-Day Portfolio Trend", className="mb-2 fw-bold"),
            dcc.Graph(figure=sparkline_fig, config={'displayModeBar': False}, className="mb-4"),
            
            # Top 10 Holdings Table
            html.H6("Top 10 Holdings", className="mb-3 fw-bold"),
            dbc.Table([
                html.Thead([
                    html.Tr([
                        html.Th("Ticker"),
                        html.Th("Sector"),
                        html.Th("Price", className="text-end"),
                        html.Th("Daily %", className="text-end")
                    ])
                ]),
                html.Tbody(table_rows if table_rows else [
                    html.Tr([html.Td("No positions loaded", colSpan=4, className="text-center text-muted", style={'color': '#000000'})])
                ])
            ], bordered=True, hover=True, size="sm", className="mb-3"),
            
            # Refresh Button
            dbc.Button([
                html.I(className="bi bi-arrow-clockwise me-2"),
                "Refresh Portfolio"
            ], id='home-refresh-portfolio-btn', color="secondary", outline=True, size="sm")
        ])
    ], className="mb-4")


# ============================================================================
# SECTION 3: PERFORMANCE INSIGHTS
# ============================================================================

def create_performance_insights_section():
    """
    Cross-lab metrics summary with visual encoding.
    """
    metrics = get_cross_lab_metrics()
    
    # Create metric cards
    metric_cards = [
        {
            'title': 'Portfolio CAGR',
            'value': format_percentage(metrics.get('attribution', {}).get('cagr', 0)),
            'source': 'Attribution Lab',
            'icon': '📈',
            'tooltip': 'Compound Annual Growth Rate - your portfolio\'s annualized return',
            'threshold': metrics.get('attribution', {}).get('cagr', 0),
            'benchmark': 10.0
        },
        {
            'title': 'Forecast Accuracy',
            'value': format_percentage(metrics.get('volatility', {}).get('forecast_accuracy', 0)),
            'source': 'Volatility Lab',
            'icon': '🎯',
            'tooltip': 'Percentage of price predictions within confidence interval',
            'threshold': metrics.get('volatility', {}).get('forecast_accuracy', 0),
            'benchmark': 70.0
        },
        {
            'title': 'Research Score',
            'value': f"{metrics.get('research', {}).get('research_score', 0):.1f}/10",
            'source': 'Research Lab',
            'icon': '🔬',
            'tooltip': 'Composite score based on factor analysis and experiment results',
            'threshold': metrics.get('research', {}).get('research_score', 0),
            'benchmark': 6.0
        },
        {
            'title': 'Strategy Win Rate',
            'value': format_percentage(metrics.get('strategy', {}).get('win_rate', 0)),
            'source': 'Strategy Lab',
            'icon': '⚡',
            'tooltip': 'Percentage of profitable trades in backtested strategies',
            'threshold': metrics.get('strategy', {}).get('win_rate', 0),
            'benchmark': 50.0
        }
    ]
    
    cards = []
    for metric in metric_cards:
        color = format_metric_color(metric['threshold'], metric['benchmark'], metric['benchmark'] * 0.7)
        
        card = dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dbc.Tooltip(
                        metric['tooltip'],
                        target=f"metric-{metric['title'].replace(' ', '-')}",
                        placement="top"
                    ),
                    html.Div([
                        html.Span(metric['icon'], className="fs-4 me-2"),
                        html.H6(metric['title'], className="d-inline mb-0")
                    ], id=f"metric-{metric['title'].replace(' ', '-')}", className="mb-2"),
                    html.H3(metric['value'], className=f"mb-1 text-{color}"),
                    html.Small(f"from {metric['source']}", className="text-muted", style={'color': '#000000'})
                ])
            ], className="h-100", color=color, outline=True)
        ], md=6, lg=3, className="mb-3")
        cards.append(card)
    
    return dbc.Card([
        dbc.CardHeader([
            html.H5([
                html.I(className="bi bi-graph-up me-2"),
                "📊 Performance Insights"
            ], className="mb-0")
        ]),
        dbc.CardBody([
            dbc.Alert([
                html.Strong("Visual Encoding: "),
                html.Span("Green = Above benchmark | ", className="text-success"),
                html.Span("Yellow = Neutral | ", className="text-warning"),
                html.Span("Red = Below benchmark", className="text-danger")
            ], color="light", className="mb-4"),
            
            dbc.Row(cards),
            
            html.Small([
                "💡 ",
                html.Strong("Tip: "),
                "Metrics are cached locally in ",
                html.Code("/outputs/metrics_cache.json"),
                " and update every 5 minutes"
            ], className="text-muted", style={'color': '#000000'})
        ])
    ], className="mb-4")


# ============================================================================
# SECTION 4: AI INSIGHTS
# ============================================================================

def create_ai_insights_section():
    """
    AI-powered insight summaries (placeholder for Azure ML integration).
    """
    insights = summarize_insights()
    
    insight_items = [
        html.Li(dcc.Markdown(insight, className="mb-2"), className="mb-3")
        for insight in insights
    ]
    
    return dbc.Card([
        dbc.CardHeader([
            html.H5([
                html.I(className="bi bi-robot me-2"),
                "🤖 AI Assistant Insights"
            ], className="mb-0")
        ]),
        dbc.CardBody([
            dbc.Alert([
                html.I(className="bi bi-info-circle me-2"),
                "This section will be powered by Azure ML in future builds. Current insights are rule-based summaries."
            ], color="info", className="mb-4"),
            
            html.H6("System Insights Summary", className="mb-3 fw-bold"),
            html.Ul(insight_items, className="list-unstyled"),
            
            dbc.Card([
                dbc.CardBody([
                    html.Small([
                        "🔮 ",
                        html.Strong("Coming Soon: "),
                        "Natural language queries, predictive alerts, and personalized recommendations powered by Azure OpenAI"
                    ], className="text-muted", style={'color': '#000000'})
                ])
            ], className="bg-light")
        ])
    ], className="mb-4")


# ============================================================================
# SECTION 5: USER HELP
# ============================================================================

def create_user_help_section():
    """
    Getting started guide and inline documentation.
    """
    return dbc.Card([
        dbc.CardHeader([
            html.H5([
                html.I(className="bi bi-question-circle me-2"),
                "📚 Getting Started"
            ], className="mb-0")
        ]),
        dbc.CardBody([
            dbc.Accordion([
                dbc.AccordionItem([
                    dcc.Markdown("""
**What each lab does:**

- **📊 Attribution Lab**: Analyze portfolio performance using factor models (Fama-French, momentum, quality)
- **⚡ Volatility Lab**: Forecast price volatility using GARCH models and implied volatility surfaces
- **🔬 Research Lab**: Run backtests and experiments to validate trading hypotheses
- **⚡ Strategy Lab**: Build and test quantitative trading strategies with realistic cost simulation
- **💹 Options Lab**: Greeks calculations, options strategy builder, and IV rank analysis
                    """, className="small")
                ], title="What does each lab do?"),
                
                dbc.AccordionItem([
                    dcc.Markdown("""
**Importing your portfolio:**

1. Navigate to **Portfolio** tab
2. Use "Import from Alpaca" for live broker data
3. Or manually add positions via "Add Position" button
4. Supported formats: Ticker, shares, cost basis
5. Data auto-syncs with all labs

**Example:**
```python
Ticker: AAPL
Shares: 100
Cost Basis: $150.00
```
                    """, className="small")
                ], title="How do I import my portfolio?"),
                
                dbc.AccordionItem([
                    dcc.Markdown("""
**Metric Calculations:**

- **CAGR**: `(Ending Value / Beginning Value)^(1/years) - 1`
- **Sharpe Ratio**: `(Portfolio Return - Risk-Free Rate) / Portfolio Std Dev`
- **Max Drawdown**: Largest peak-to-trough decline in portfolio value
- **Win Rate**: `Profitable Trades / Total Trades * 100`
- **Forecast Accuracy**: `Predictions within CI / Total Predictions * 100`

All metrics use industry-standard formulas and are documented in code.
                    """, className="small")
                ], title="How are metrics calculated?"),
                
                dbc.AccordionItem([
                    dcc.Markdown("""
**Data Sources:**

| Data Type | Primary Source | Fallback |
|-----------|---------------|----------|
| Stock Prices | yfinance | Alpaca API |
| Options Data | Polygon.io | Local cache |
| Market Indices | Yahoo Finance | Fred API |
| Factor Data | Ken French Library | CSV files |
| News | NewsAPI | Finnhub |

All data is cached locally in `/cache` directory to minimize API calls.
                    """, className="small")
                ], title="What data sources are used?"),
                
            ], start_collapsed=True)
        ])
    ], className="mb-4")


# ============================================================================
# MAIN LAYOUT FUNCTION
# ============================================================================

def layout():
    """
    Creates the Home Lab main layout (command center).
    
    Returns:
        dbc.Container: Complete Home Lab layout with all 5 sections
    """
    logger.info("Creating Home Lab layout...")
    
    return dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.H2([
                    html.I(className="bi bi-house-fill me-2"),
                    "🏠 Command Center"
                ], className="mb-2"),
                html.P(
                    "Your financial analytics dashboard - system overview, portfolio snapshot, and cross-lab insights",
                    className="text-muted mb-4",
                    style={'color': '#000000'}
                )
            ])
        ]),
        
        # Section 1: System Summary
        create_system_summary_section(),
        
        # Section 2: Portfolio Snapshot
        create_portfolio_snapshot_section(),
        
        # Section 3: Performance Insights
        create_performance_insights_section(),
        
        # Section 4: AI Insights
        create_ai_insights_section(),
        
        # Section 5: User Help
        create_user_help_section(),
        
        # Hidden stores for data management
        dcc.Store(id='home-portfolio-data', data={}),
        dcc.Store(id='home-metrics-data', data={}),
        
    ], fluid=True, className="p-4")


logger.info("✓ Home Lab layout module loaded")
