"""
Strategy Lab - Main Layout (Modularized with Subtabs)

Refactored from 753-line monolithic file to modular subtab architecture.

5 Subtabs (UPDATED - Merged Backtest Config into Execute):
1. Setup - Strategy configuration
2. Execute & Configure - Backtest parameters + Run (MERGED from Backtest + Execute)
3. Results - Performance metrics
4. Benchmark - Comparison vs SPY/QQQ
5. Risk & Factors - Risk metrics and factor attribution

Author: Autonomous Lead Engineer (Agent v2)
Date: October 28, 2025 | Updated: December 2025 (Phase 18B)
"""

import logging
from dash_extensions.enrich import html, dcc
import dash_bootstrap_components as dbc

# Import subtab layouts (backtest removed - merged into execution)
from .subtabs import setup, execution, results, benchmark, risk

logger = logging.getLogger(__name__)

def layout():
    """
    Creates the modular Strategy Lab main layout with subtab navigation.
    
    Returns:
        dbc.Container: Complete Strategy Lab with 5 subtabs (Backtest merged into Execute)
    """
    logger.info("Creating Strategy Lab layout with 5 modular subtabs (Backtest+Execute merged)...")
    
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
                    className="mb-3",
                    style={'color': '#000000'}
                ),
                
                # Overall Overview (Collapsible)
                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown("""
**🔬 Strategy Lab Overview:**

A comprehensive environment for building and testing quantitative trading strategies.

**📈 What You Can Do:**
1. **Define Strategies** - Create rule-based or factor-driven trading strategies (Momentum, Mean Reversion, Pairs Trading)
2. **Backtest** - Simulate performance on historical data with realistic costs (commissions, slippage)
3. **Analyze Results** - Deep-dive into returns, risk metrics, and factor attribution (Fama-French model)
4. **Compare Benchmarks** - Measure alpha vs SPY, QQQ, or custom benchmarks
5. **Risk Analysis** - Evaluate drawdowns, VaR, factor exposures, and risk-adjusted returns

**💡 Quick Start Guide:**
1. **Setup Tab**: Choose strategy type (start with Momentum SMA Crossover)
2. **Backtest Tab**: Set date range (1-3 years), initial capital ($100k), costs ($0 commissions)
3. **Execute Tab**: Click "Run Backtest" and wait 5-15 seconds
4. **Results Tab**: Review equity curve, CAGR, Sharpe ratio, win rate
5. **Benchmark Tab**: Compare vs SPY to calculate alpha
6. **Risk Tab**: Analyze drawdowns, volatility, and factor exposures

**🎓 Key Concepts:**

- **CAGR (Compound Annual Growth Rate)**: Your average yearly return (aim for >10%)
- **Sharpe Ratio**: Risk-adjusted return (>1.5 is excellent, >2.0 is exceptional)
- **Max Drawdown**: Worst peak-to-trough decline (prefer < -20%)
- **Alpha**: Excess return vs benchmark after adjusting for risk
- **Factor Exposure**: How much Market/Size/Value/Momentum drives your returns

**🎯 Success Criteria for a Good Strategy:**
- ✅ CAGR > 10% (beats inflation + risk-free rate)
- ✅ Sharpe Ratio > 1.5 (good risk-adjusted returns)
- ✅ Max Drawdown < -25% (manageable pain)
- ✅ Win Rate > 55% (more winners than losers)
- ✅ Positive Alpha > 2% (beating the market after risk adjustment)

**⚠️ Important Notes:**
- Backtest results are historical simulations, not guarantees of future performance
- Always account for transaction costs (even $0 commissions have slippage)
- Out-of-sample testing recommended (train on 2020-2022, test on 2023-2024)
- Paper trade before risking real capital

**📚 Learn More:**
- Momentum strategies: Buy assets trending upward (SMA crossovers, price breakouts)
- Mean reversion: Buy oversold assets expecting bounce (RSI < 30, Bollinger Bands)
- Factor investing: Systematic exposure to Size, Value, Momentum, Quality factors
                        """, style={'color': '#000000', 'fontSize': '14px'})
                    ], title="📚 Complete Strategy Lab Guide", className="mb-3")
                ], start_collapsed=True, className="mb-4")
            ])
        ]),
        
        # Subtabs Navigation (MERGED: Backtest Config + Execute into one tab)
        dbc.Tabs([
            dbc.Tab(
                label="📋 Setup",
                tab_id="sl-setup",
                children=[setup.layout()],
                className="sl-tab-setup"
            ),
            dbc.Tab(
                label="▶️ Execute & Configure",
                tab_id="sl-execute",
                children=[execution.layout()],  # Now includes config + execution
                className="sl-tab-execute"
            ),
            dbc.Tab(
                label="📊 Results",
                tab_id="sl-results",
                children=[results.layout()],
                className="sl-tab-results"
            ),
            dbc.Tab(
                label="🎯 Benchmark",
                tab_id="sl-benchmark",
                children=[benchmark.layout()],
                className="sl-tab-benchmark"
            ),
            dbc.Tab(
                label="⚠️ Risk & Factors",
                tab_id="sl-risk",
                children=[risk.layout()],
                className="sl-tab-risk"
            ),
        ], id="strategy-lab-subtabs", active_tab="sl-setup", className="mb-4"),
        
        # Hidden stores for data management (shared across subtabs)
        dcc.Store(id='sl-strategy-config', data={}),
        dcc.Store(id='sl-backtest-results', data={}),
        dcc.Store(id='sl-validation-status', data={'valid': False, 'errors': []}),
        dcc.Store(id='sl-benchmark-data', data={}),
        dcc.Store(id='sl-risk-data', data={}),
        
    ], fluid=True, className="p-4")


logger.info("✓ Strategy Lab modular layout loaded (6 subtabs)")
