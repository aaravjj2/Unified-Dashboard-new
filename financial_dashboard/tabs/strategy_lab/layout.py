"""
Strategy Lab - Layout Module

MODULAR ARCHITECTURE (Phase 3)
Creates the main Strategy Lab layout with 6 subtabs:
1. Setup - Define trading rules and parameters
2. Backtest - Run simulations on historical data  
3. Execution - Deploy and monitor live strategies
4. Results - Visualize performance metrics
5. Benchmark - Compare against market indices
6. Risk - Analyze risk exposure and VaR

User Experience:
- Beginner-friendly descriptions and tooltips
- Progressive disclosure (collapsible help sections)
- Visual hierarchy with color-coded cards
- Real-time validation feedback
"""

import logging
from dash_extensions.enrich import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Import modular subtabs
from .subtabs import setup, backtest, execution, results, benchmark, risk

logger = logging.getLogger(__name__)

# ============================================================================
# HELPER FUNCTIONS FOR SECTION CREATION
# ============================================================================

def create_strategy_setup_section():
    """
    Section 1: Strategy Setup
    
    Allows users to:
    - Select strategy type (Momentum, Mean Reversion, etc.)
    - Choose tickers/sectors
    - Define entry/exit conditions
    - Set position sizing and risk parameters
    """
    return dbc.Card([
        dbc.CardHeader([
            html.H5([
                html.I(className="bi bi-gear-fill me-2"),
                "📋 Strategy Setup"
            ], className="mb-0"),
        ]),
        dbc.CardBody([
            # User-friendly description
            dcc.Markdown("""
**📊 What This Section Does:**

Define your quantitative trading strategy by selecting:
- **Strategy Type**: Momentum, mean reversion, pairs trading, options spreads
- **Universe**: Specific tickers or market sectors
- **Rules**: Entry/exit conditions based on technical indicators or factor signals

**💡 Beginner Tip:**

Start with a simple momentum strategy (buy when price crosses above moving average).
You can add complexity as you learn!

**🎯 How to Use:**

1. Choose strategy type from dropdown
2. Enter tickers (comma-separated, e.g., AAPL,SPY,MSFT)
3. Define entry condition (e.g., "SMA 20 > SMA 50")
4. Set exit rule (e.g., "Stop Loss -5%")
5. Click "Validate Strategy" to check for errors
            """, className="small mb-3", style={
                'backgroundColor': '#f0f8ff',
                'padding': '15px',
                'borderRadius': '8px',
                'marginBottom': '20px',
                'color': '#000000'
            }),
            
            # Strategy Type Selection
            dbc.Row([
                dbc.Col([
                    html.Label("Strategy Type", className="fw-bold"),
                    dcc.Dropdown(
                        id='sl-strategy-type',
                        options=[
                            {'label': '📈 Momentum (SMA Crossover)', 'value': 'momentum'},
                            {'label': '📉 Mean Reversion (RSI)', 'value': 'mean_reversion'},
                            {'label': '🔀 Pairs Trading (Z-Score)', 'value': 'pairs'},
                            {'label': '� Bollinger Bands (Mean Reversion)', 'value': 'bollinger_bands'},
                            {'label': '📉 MACD (Trend Crossover)', 'value': 'macd'},
                        ],
                        value='momentum',
                        clearable=False,
                        className="mb-3"
                    ),
                ], md=6),
                dbc.Col([
                    html.Label("Universe Selection", className="fw-bold"),
                    dcc.Dropdown(
                        id='sl-universe-type',
                        options=[
                            {'label': 'Specific Tickers', 'value': 'tickers'},
                            {'label': 'S&P 500', 'value': 'sp500'},
                            {'label': 'Technology Sector', 'value': 'tech'},
                            {'label': 'Weekly Picks', 'value': 'weekly'},
                        ],
                        value='tickers',
                        clearable=False,
                        className="mb-3"
                    ),
                ], md=6),
            ]),
            
            # Ticker Input
            dbc.Row([
                dbc.Col([
                    html.Label("Tickers (comma-separated)", className="fw-bold"),
                    dbc.Input(
                        id='sl-tickers-input',
                        placeholder="AAPL,SPY,MSFT,GOOGL",
                        value="AAPL,SPY",
                        type="text",
                        className="mb-3"
                    ),
                ], md=12),
            ]),
            
            # Entry/Exit Conditions
            dbc.Row([
                dbc.Col([
                    html.Label("Entry Condition", className="fw-bold"),
                    dbc.Textarea(
                        id='sl-entry-condition',
                        placeholder="Example: Close > SMA(20) AND RSI < 70",
                        value="Close > SMA(20)",
                        rows=2,
                        className="mb-3"
                    ),
                ], md=6),
                dbc.Col([
                    html.Label("Exit Condition", className="fw-bold"),
                    dbc.Textarea(
                        id='sl-exit-condition',
                        placeholder="Example: Close < SMA(20) OR Stop Loss -5%",
                        value="Close < SMA(20)",
                        rows=2,
                        className="mb-3"
                    ),
                ], md=6),
            ]),
            
            # Position Sizing
            dbc.Row([
                dbc.Col([
                    html.Label("Position Size (%)", className="fw-bold"),
                    dbc.Input(
                        id='sl-position-size',
                        type="number",
                        min=1,
                        max=100,
                        value=10,
                        className="mb-3"
                    ),
                ], md=4),
                dbc.Col([
                    html.Label("Max Positions", className="fw-bold"),
                    dbc.Input(
                        id='sl-max-positions',
                        type="number",
                        min=1,
                        max=20,
                        value=5,
                        className="mb-3"
                    ),
                ], md=4),
                dbc.Col([
                    html.Label("Rebalance Frequency", className="fw-bold"),
                    dcc.Dropdown(
                        id='sl-rebalance-freq',
                        options=[
                            {'label': 'Daily', 'value': 'D'},
                            {'label': 'Weekly', 'value': 'W'},
                            {'label': 'Monthly', 'value': 'M'},
                        ],
                        value='W',
                        clearable=False,
                        className="mb-3"
                    ),
                ], md=4),
            ]),
            
            # Validation Button
            dbc.Row([
                dbc.Col([
                    dbc.Button(
                        [html.I(className="bi bi-check-circle me-2"), "Validate Strategy"],
                        id='sl-validate-btn',
                        color="primary",
                        className="me-2"
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-arrow-repeat me-2"), "Reset to Default"],
                        id='sl-reset-btn',
                        color="secondary",
                        outline=True
                    ),
                ], className="d-flex justify-content-end"),
            ]),
            
            # Validation Result
            html.Div(id='sl-validation-result', className="mt-3"),
        ])
    ], className="mb-4")


def create_backtest_section():
    """
    Section 2: Backtest Execution
    
    Configure and run backtesting simulations:
    - Date range selection
    - Initial capital
    - Transaction costs
    - Slippage assumptions
    """
    return dbc.Card([
        dbc.CardHeader([
            html.H5([
                html.I(className="bi bi-play-circle-fill me-2"),
                "🧪 Backtest Execution"
            ], className="mb-0"),
        ]),
        dbc.CardBody([
            # Description
            dcc.Markdown("""
**📊 What This Section Does:**

Simulate your strategy on historical data to see how it would have performed.

**💡 Key Concepts:**

- **Backtest Period**: How far back to test (more data = more reliable results)
- **Initial Capital**: Starting portfolio value (e.g., $100,000)
- **Transaction Costs**: Realistic fees (0.1% per trade is typical)
- **Slippage**: Price movement between decision and execution (0.05% is conservative)

**🎯 How to Use:**

1. Select backtest date range (at least 1 year recommended)
2. Set initial capital (default: $100,000)
3. Adjust costs for realism (defaults are conservative)
4. Click "Run Backtest" to simulate
            """, className="small mb-3", style={
                'backgroundColor': '#fff5f0',
                'padding': '15px',
                'borderRadius': '8px',
                'marginBottom': '20px',
                'color': '#000000'
            }),
            
            # Date Range
            dbc.Row([
                dbc.Col([
                    html.Label("Backtest Start Date", className="fw-bold"),
                    dcc.DatePickerSingle(
                        id='sl-start-date',
                        date=datetime.now() - timedelta(days=365),
                        display_format='YYYY-MM-DD',
                        className="mb-3"
                    ),
                ], md=6),
                dbc.Col([
                    html.Label("Backtest End Date", className="fw-bold"),
                    dcc.DatePickerSingle(
                        id='sl-end-date',
                        date=datetime.now(),
                        display_format='YYYY-MM-DD',
                        className="mb-3"
                    ),
                ], md=6),
            ]),
            
            # Capital & Costs
            dbc.Row([
                dbc.Col([
                    html.Label("Initial Capital ($)", className="fw-bold"),
                    dbc.Input(
                        id='sl-initial-capital',
                        type="number",
                        min=1000,
                        max=10000000,
                        value=100000,
                        className="mb-3"
                    ),
                ], md=4),
                dbc.Col([
                    html.Label("Transaction Cost (%)", className="fw-bold"),
                    dbc.Input(
                        id='sl-transaction-cost',
                        type="number",
                        min=0,
                        max=5,
                        step=0.01,
                        value=0.1,
                        className="mb-3"
                    ),
                ], md=4),
                dbc.Col([
                    html.Label("Slippage (%)", className="fw-bold"),
                    dbc.Input(
                        id='sl-slippage',
                        type="number",
                        min=0,
                        max=5,
                        step=0.01,
                        value=0.05,
                        className="mb-3"
                    ),
                ], md=4),
            ]),
            
            # Run Button
            dbc.Row([
                dbc.Col([
                    dbc.Button(
                        [html.I(className="bi bi-play-fill me-2"), "Run Backtest"],
                        id='sl-run-backtest-btn',
                        color="success",
                        size="lg",
                        className="w-100"
                    ),
                ]),
            ]),
            
            # Progress/Status
            html.Div(id='sl-backtest-progress', className="mt-3"),
        ])
    ], className="mb-4")


def create_results_section():
    """
    Section 3: Results & Insights
    
    Display backtest results with:
    - Performance metrics (CAGR, Sharpe, Max DD)
    - Equity curve visualization
    - Strategy vs benchmark comparison
    - Risk exposure breakdown
    - Factor attribution analysis
    """
    return dbc.Card([
        dbc.CardHeader([
            html.H5([
                html.I(className="bi bi-graph-up me-2"),
                "📈 Results & Insights"
            ], className="mb-0"),
        ]),
        dbc.CardBody([
            # Description
            dcc.Markdown("""
**📊 Understanding Your Results:**

After running a backtest, you'll see:

**Performance Metrics:**
- **CAGR**: Annualized return (higher is better, but watch risk!)
- **Sharpe Ratio**: Risk-adjusted return (>1 is good, >2 is excellent)
- **Max Drawdown**: Worst peak-to-trough loss (lower is better)
- **Win Rate**: % of profitable trades

**Charts:**
- **Equity Curve**: Portfolio value over time
- **Benchmark Comparison**: Your strategy vs SPY (S&P 500)
- **Factor Attribution**: What drove performance (market, value, size, etc.)
- **Risk Exposure**: Portfolio allocation breakdown

**💡 Tip**: A good strategy beats the benchmark (SPY) with lower drawdown!
            """, className="small mb-3", style={
                'backgroundColor': '#f0fff0',
                'padding': '15px',
                'borderRadius': '8px',
                'marginBottom': '20px',
                'color': '#000000'
            }),
            
            # Collapsible "What These Metrics Mean" Panel
            dbc.Accordion([
                dbc.AccordionItem([
                    dcc.Markdown("""
### 📘 What These Metrics Mean (Beginner's Guide)

**CAGR (Compound Annual Growth Rate)**
- What it is: The average yearly return, assuming profits are reinvested
- Example: 15% CAGR means your money grows 15% per year on average
- Good target: 10-20% for active strategies, 8-12% for passive
- ⚠️ Watch out: High CAGR with high drawdown = risky!

**Sharpe Ratio**
- What it is: How much return you get per unit of risk taken
- Formula: (Strategy Return - Risk-Free Rate) / Strategy Volatility
- Interpretation:
  - < 1: Not great (too much risk for the return)
  - 1-2: Good (decent risk-adjusted returns)
  - > 2: Excellent (strong risk-adjusted performance)
- 💡 Tip: Compare to SPY's Sharpe (usually 0.8-1.2)

**Max Drawdown**
- What it is: The worst peak-to-valley loss during the backtest
- Example: -25% means at worst, you lost 25% from a previous high
- Why it matters: Shows how much pain you'd endure in bad times
- Good target: <20% for conservative, <30% for aggressive
- ⚠️ Remember: 50% loss requires 100% gain to recover!

**Win Rate**
- What it is: Percentage of trades that were profitable
- Example: 55% = 55 out of 100 trades made money
- Misconception: Higher is NOT always better!
  - A 40% win rate with big winners can beat 60% with small winners
  - Look at "average win" vs "average loss" too
- 💡 Pro tip: Win rate × Avg Win vs Lose rate × Avg Loss = Edge

**Factor Attribution**
- What it is: Breakdown of where returns came from
- Factors:
  - **Market (Beta)**: How much was just "riding the market up"?
  - **Size**: Small cap vs large cap exposure
  - **Value**: Cheap stocks vs expensive stocks
  - **Momentum**: Recent winners vs losers
  - **Residual (Alpha)**: The "skill" part - returns unexplained by factors
- 💡 Goal: Positive alpha (residual) = you're adding value beyond passive indexing

**Equity Curve**
- What it is: Line chart showing portfolio value over time
- What to look for:
  - Smooth upward slope = consistent strategy
  - Jagged/choppy = volatile (higher risk)
  - Flat periods = strategy underperforming
  - Sharp drops = drawdowns (bad times)
- 💡 Compare to benchmark (SPY): Outperform with less volatility = winner!

**Benchmark (SPY) Comparison**
- Why compare to SPY: It's the "do-nothing" alternative (just buy S&P 500)
- Your strategy should:
  - Beat SPY's returns over time, OR
  - Match SPY with lower drawdowns (safer), OR
  - Deliver uncorrelated returns (diversification benefit)
- ⚠️ If you underperform SPY with higher risk → just buy SPY instead!

**Transaction Costs & Slippage**
- Why they matter: Real trading has friction (fees, bid-ask spread)
- Transaction cost: Brokerage fees + SEC fees (~0.1% per trade)
- Slippage: Difference between expected price and actual fill (~0.05%)
- 💡 High-frequency strategies die from costs; swing/position trading less affected

**Risk-Free Rate**
- What it is: Return from "safe" investments (T-bills, savings)
- Current rate: ~5% (as of 2024-2025)
- Why it matters: Your strategy should beat this, or why take risk?
- Used in: Sharpe ratio calculation

---

**🎯 Putting It Together: What Makes a Good Strategy?**

1. **Positive Alpha**: Residual > 0 (you're adding skill, not just riding the market)
2. **Sharpe > 1.5**: Good risk-adjusted returns
3. **CAGR > 12%**: Beats passive investing (SPY ~10% long-term)
4. **Max Drawdown < 25%**: You can stomach the worst times
5. **Smooth Equity Curve**: Consistent, not choppy
6. **Uncorrelated to SPY**: Diversifies your portfolio

Remember: **Backtest performance ≠ Future performance**. Markets change, but good risk-adjusted returns with solid drawdown control usually persist better than pure high returns.
                    """, className="small", style={'fontSize': '0.9rem'})
                ], title="📘 What These Metrics Mean (Click to Expand)", item_id="metrics-explanation"),
            ], start_collapsed=True, className="mb-4"),
            
            # Performance Metrics Cards (with tooltips)
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Tooltip(
                                "Compound Annual Growth Rate: Average yearly return assuming reinvestment. 10-20% is good for active strategies.",
                                target="sl-metric-cagr-container",
                                placement="top"
                            ),
                            html.Div([
                                html.H6("CAGR", className="text-muted mb-1", style={'color': '#000000'}),
                                html.H3(id='sl-metric-cagr', children="--", className="mb-0"),
                                html.Small("Annualized Return", className="text-muted", style={'color': '#000000'})
                            ], id="sl-metric-cagr-container")
                        ])
                    ], color="success", outline=True)
                ], md=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Tooltip(
                                "Sharpe Ratio: Return per unit of risk. >1 is good, >2 is excellent. Compares strategy to risk-free rate.",
                                target="sl-metric-sharpe-container",
                                placement="top"
                            ),
                            html.Div([
                                html.H6("Sharpe Ratio", className="text-muted mb-1", style={'color': '#000000'}),
                                html.H3(id='sl-metric-sharpe', children="--", className="mb-0"),
                                html.Small("Risk-Adjusted Return", className="text-muted", style={'color': '#000000'})
                            ], id="sl-metric-sharpe-container")
                        ])
                    ], color="primary", outline=True)
                ], md=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Tooltip(
                                "Max Drawdown: Worst peak-to-valley loss. <20% is conservative, <30% is aggressive. Remember: 50% loss needs 100% gain to recover!",
                                target="sl-metric-maxdd-container",
                                placement="top"
                            ),
                            html.Div([
                                html.H6("Max Drawdown", className="text-muted mb-1", style={'color': '#000000'}),
                                html.H3(id='sl-metric-maxdd', children="--", className="mb-0"),
                                html.Small("Worst Peak-to-Trough", className="text-muted", style={'color': '#000000'})
                            ], id="sl-metric-maxdd-container")
                        ])
                    ], color="danger", outline=True)
                ], md=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Tooltip(
                                "Win Rate: % of profitable trades. 50%+ is good, but big winners matter more than high win rate. Look at win/loss ratio too.",
                                target="sl-metric-winrate-container",
                                placement="top"
                            ),
                            html.Div([
                                html.H6("Win Rate", className="text-muted mb-1", style={'color': '#000000'}),
                                html.H3(id='sl-metric-winrate', children="--", className="mb-0"),
                                html.Small("% Profitable Trades", className="text-muted", style={'color': '#000000'})
                            ], id="sl-metric-winrate-container")
                        ])
                    ], color="info", outline=True)
                ], md=3),
            ], className="mb-4"),
            
            # Equity Curve Chart
            dbc.Row([
                dbc.Col([
                    html.H6([
                        "Portfolio Equity Curve ",
                        html.I(className="bi bi-info-circle-fill text-muted", id="equity-curve-info", style={'fontSize': '0.9rem', 'cursor': 'pointer', 'color': '#6c757d'})
                    ], className="fw-bold mb-2"),
                    dbc.Tooltip(
                        "Shows portfolio value over time. Smooth upward slope = good. Sharp drops = drawdowns. Compare to benchmark (SPY) below.",
                        target="equity-curve-info",
                        placement="right"
                    ),
                    dcc.Graph(
                        id='sl-equity-curve',
                        figure=_create_placeholder_chart("Run backtest to see equity curve"),
                        config={'displayModeBar': False}
                    )
                ], md=12),
            ], className="mb-4"),
            
            # Strategy vs Benchmark Comparison
            dbc.Row([
                dbc.Col([
                    html.H6([
                        "Strategy vs Benchmark (SPY) ",
                        html.I(className="bi bi-info-circle-fill text-muted", id="benchmark-info", style={'fontSize': '0.9rem', 'cursor': 'pointer', 'color': '#6c757d'})
                    ], className="fw-bold mb-2"),
                    dbc.Tooltip(
                        "Your strategy (blue) vs SPY/S&P 500 (orange). Goal: Outperform with less volatility. If your line is below SPY with more choppiness, just buy SPY!",
                        target="benchmark-info",
                        placement="right"
                    ),
                    dcc.Graph(
                        id='sl-vs-benchmark',
                        figure=_create_placeholder_chart("Run backtest to see comparison"),
                        config={'displayModeBar': False}
                    )
                ], md=12),
            ], className="mb-4"),
            
            # Risk Exposure Breakdown & Factor Attribution
            dbc.Row([
                dbc.Col([
                    html.H6([
                        "Risk Exposure Breakdown ",
                        html.I(className="bi bi-info-circle-fill text-muted", id="exposure-info", style={'fontSize': '0.9rem', 'cursor': 'pointer', 'color': '#6c757d'})
                    ], className="fw-bold mb-2"),
                    dbc.Tooltip(
                        "How your capital is allocated across positions. Diversification is key - don't put all eggs in one basket!",
                        target="exposure-info",
                        placement="right"
                    ),
                    dcc.Graph(
                        id='sl-exposure-breakdown',
                        figure=_create_placeholder_pie("Run backtest to see exposure"),
                        config={'displayModeBar': False}
                    )
                ], md=6),
                dbc.Col([
                    html.H6([
                        "Factor Attribution Analysis ",
                        html.I(className="bi bi-info-circle-fill text-muted", id="factor-info", style={'fontSize': '0.9rem', 'cursor': 'pointer', 'color': '#6c757d'})
                    ], className="fw-bold mb-2"),
                    dbc.Tooltip(
                        "Where did returns come from? Market (beta), Size, Value, Momentum, or Residual (alpha/skill). Positive residual = you're adding value beyond passive indexing!",
                        target="factor-info",
                        placement="right"
                    ),
                    dcc.Graph(
                        id='sl-factor-attribution',
                        figure=_create_placeholder_bar("Run backtest to see factors"),
                        config={'displayModeBar': False}
                    )
                ], md=6),
            ]),
        ])
    ], className="mb-4")


def _create_placeholder_chart(message):
    """Create a placeholder line chart with message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=16, color="gray")
    )
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False),
        yaxis=dict(visible=False)
    )
    return fig


def _create_placeholder_pie(message):
    """Create a placeholder pie chart with message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=14, color="gray")
    )
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )
    return fig


def _create_placeholder_bar(message):
    """Create a placeholder bar chart with message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=14, color="gray")
    )
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False),
        yaxis=dict(visible=False)
    )
    return fig


# ============================================================================
# MAIN LAYOUT FUNCTION
# ============================================================================

def layout():
    """
    Creates the Strategy Lab main layout with modular subtabs.
    
    Returns:
        dbc.Container: Complete Strategy Lab layout with 6 subtabs
    """
    logger.info("Creating Strategy Lab layout with 6 modular subtabs...")
    
    return dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.H2([
                    html.I(className="bi bi-lightning-charge-fill me-2"),
                    "⚡ Strategy Lab"
                ], className="mb-2"),
                html.P(
                    "Quantitative trading strategy development, backtesting, and performance attribution",
                    className="text-muted mb-4",
                    style={'color': '#212529'}
                ),
                
                # Overview Card
                dcc.Markdown("""
**🔬 Strategy Lab Overview:**

A comprehensive environment for building and testing quantitative trading strategies.

**📈 What You Can Do:**
1. **Define Strategies** - Create rule-based or factor-driven trading strategies
2. **Backtest** - Simulate performance on historical data with realistic costs
3. **Execute** - Deploy strategies with real-time monitoring
4. **Analyze Results** - Deep-dive into returns, risk, and factor attribution
5. **Benchmark** - Compare against SPY/QQQ and measure alpha
6. **Risk Management** - Analyze VaR, drawdowns, and portfolio risk

**💡 Quick Start:**
1. Navigate to "Setup" tab to define your strategy
2. Run backtest in "Backtest" tab
3. Review results in "Results" tab
4. Compare against benchmarks in "Benchmark" tab

**🎓 Learn More**: Each tab includes detailed tooltips and explanations.
                """, className="small", style={
                    'backgroundColor': '#f8f9fa',
                    'padding': '15px',
                    'borderRadius': '8px',
                    'marginBottom': '25px',
                    'color': '#212529'
                })
            ])
        ]),
        
        # Modular Subtabs Navigation
        dbc.Tabs([
            dbc.Tab(setup.layout(), label="📋 Setup", tab_id="setup-tab"),
            dbc.Tab(backtest.layout(), label="📊 Backtest", tab_id="backtest-tab"),
            dbc.Tab(execution.layout(), label="▶️ Execute", tab_id="execute-tab"),
            dbc.Tab(results.layout(), label="📈 Results", tab_id="results-tab"),
            dbc.Tab(benchmark.layout(), label="🎯 Benchmark", tab_id="benchmark-tab"),
            dbc.Tab(risk.layout(), label="⚠️ Risk", tab_id="risk-tab"),
        ], id="strategy-lab-tabs", active_tab="setup-tab", className="mb-4"),
        
        # Hidden stores for data management
        dcc.Store(id='sl-strategy-config', data={}),
        dcc.Store(id='sl-backtest-results', data={}),
        dcc.Store(id='sl-validation-status', data={'valid': False, 'errors': []}),
        
    ], fluid=True, className="p-4")
