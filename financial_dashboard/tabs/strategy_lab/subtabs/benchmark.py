"""
Strategy Lab - Benchmark Comparison Subtab

Compare strategy performance vs benchmarks with advanced metrics:
- SPY (S&P 500), QQQ (NASDAQ 100), IWM (Russell 2000), VTI (Total Market)
- Alpha, Beta, Information Ratio, Correlation
- Rolling performance analytics
- Relative performance metrics and risk-adjusted returns

Enhanced in Phase 9C+ with:
- Rolling correlation tracking
- Beta calculation (systematic risk)
- Information Ratio (risk-adjusted alpha)
- Tracking error and active share
"""

import logging
from typing import Optional
from dash_extensions.enrich import html, dcc
import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)

# Benchmark metadata for enhanced analysis
BENCHMARK_METADATA = {
    'SPY': {
        'name': 'S&P 500',
        'description': 'Large-cap US stocks (500 companies)',
        'typical_volatility': 0.15,  # 15% annual vol
        'risk_free_proxy': False
    },
    'QQQ': {
        'name': 'NASDAQ 100',
        'description': 'Tech-heavy index (100 largest non-financial)',
        'typical_volatility': 0.20,  # 20% annual vol
        'risk_free_proxy': False
    },
    'IWM': {
        'name': 'Russell 2000',
        'description': 'Small-cap US stocks',
        'typical_volatility': 0.22,  # 22% annual vol
        'risk_free_proxy': False
    },
    'VTI': {
        'name': 'Total US Market',
        'description': 'Entire US stock market',
        'typical_volatility': 0.16,  # 16% annual vol
        'risk_free_proxy': False
    },
}

def layout():
    """
    Enhanced Benchmark Comparison subtab layout with advanced metrics.
    
    Features:
    - Multi-benchmark comparison (SPY, QQQ, IWM, VTI)
    - Alpha, Beta, Information Ratio calculations
    - Rolling correlation and tracking error
    - Risk-adjusted performance metrics
    
    Returns:
        dbc.Container: Benchmark comparison display with enhanced analytics
    """
    return dbc.Container([
        # Description
        dcc.Markdown("""
**📊 Benchmark Comparison:**

Compare your strategy vs market indices to measure skill:
- **SPY (S&P 500)**: Large-cap US stocks benchmark
- **QQQ (NASDAQ 100)**: Tech-heavy benchmark
- **IWM (Russell 2000)**: Small-cap benchmark

**💡 Understanding Alpha:**
- **Positive Alpha**: Your strategy beats the benchmark (good!)
- **Negative Alpha**: Market index would've been better (needs improvement)
- **Beta**: How closely you track the benchmark (1.0 = identical moves)

**🎯 What to Look For:**
- Consistently higher returns than SPY
- Lower drawdowns than benchmark
- Sharpe ratio > benchmark Sharpe
        """, className="small mb-4", style={
            'backgroundColor': '#f5f5ff',
            'padding': '15px',
            'borderRadius': '8px',
            'color': '#000000'
        }),
        
        # Benchmark Selection
        dbc.Row([
            dbc.Col([
                html.Label("Select Benchmark", className="fw-bold"),
                dcc.Dropdown(
                    id='sl-benchmark-selector',
                    options=[
                        {'label': 'S&P 500 (SPY)', 'value': 'SPY'},
                        {'label': 'NASDAQ 100 (QQQ)', 'value': 'QQQ'},
                        {'label': 'Russell 2000 (IWM)', 'value': 'IWM'},
                        {'label': 'Total Market (VTI)', 'value': 'VTI'},
                    ],
                    value='SPY',
                    clearable=False,
                    className="mb-3"
                )
            ], md=6),
        ], className="mb-3"),
        
        # Comparison Metrics (Enhanced)
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Strategy CAGR", className="text-muted mb-1", style={'color': '#000000'}),
                        html.H4(id='sl-strategy-cagr', children="--", className="mb-0 text-success")
                    ])
                ], className="text-center mb-3")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Benchmark CAGR", className="text-muted mb-1", style={'color': '#000000'}),
                        html.H4(id='sl-benchmark-cagr', children="--", className="mb-0")
                    ])
                ], className="text-center mb-3")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Alpha (Excess Return)", className="text-muted mb-1", style={'color': '#000000'}),
                        html.H4(id='sl-alpha-value', children="--", className="mb-0")
                    ])
                ], className="text-center mb-3")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Beta (Market Sensitivity)", className="text-muted mb-1", style={'color': '#000000'}),
                        html.H4(id='sl-beta-value', children="--", className="mb-0", 
                                style={'color': '#000000'})
                    ])
                ], className="text-center mb-3")
            ], md=3),
        ], className="mb-3"),
        
        # Additional Risk Metrics Row
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Information Ratio", className="text-muted mb-1", style={'color': '#000000'}),
                        html.H5(id='sl-information-ratio', children="--", className="mb-0",
                                style={'color': '#000000'})
                    ])
                ], className="text-center mb-3")
            ], md=4),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Tracking Error", className="text-muted mb-1", style={'color': '#000000'}),
                        html.H5(id='sl-tracking-error', children="--", className="mb-0",
                                style={'color': '#000000'})
                    ])
                ], className="text-center mb-3")
            ], md=4),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Correlation", className="text-muted mb-1", style={'color': '#000000'}),
                        html.H5(id='sl-correlation', children="--", className="mb-0",
                                style={'color': '#000000'})
                    ])
                ], className="text-center mb-3")
            ], md=4),
        ], className="mb-4"),
        
        # Cumulative Returns Comparison
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("📈 Cumulative Returns Comparison", className="mb-0")),
                    dbc.CardBody([
                        dcc.Graph(id='sl-benchmark-comparison-chart', config={'displayModeBar': False})
                    ])
                ])
            ], md=12),
        ], className="mb-3"),
        
        # Side-by-Side Metrics
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("📊 Performance Metrics", className="mb-0")),
                    dbc.CardBody([
                        html.Div(id='sl-benchmark-metrics-table')
                    ])
                ])
            ], md=12),
        ], className="mb-3"),
        
        # Strategy vs Benchmark Chart
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("📊 Strategy vs Benchmark", className="mb-0")),
                    dbc.CardBody([
                        dcc.Graph(id='sl-vs-benchmark', config={'displayModeBar': False})
                    ])
                ])
            ], md=12),
        ], className="mb-3"),
        
        # Factor Attribution Chart
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("🎯 Factor Attribution", className="mb-0")),
                    dbc.CardBody([
                        dcc.Graph(id='sl-factor-attribution', config={'displayModeBar': False})
                    ])
                ])
            ], md=12),
        ], className="mb-3"),
        
        # Exposure Breakdown Chart
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("💼 Exposure Breakdown", className="mb-0")),
                    dbc.CardBody([
                        dcc.Graph(id='sl-exposure-breakdown', config={'displayModeBar': False})
                    ])
                ])
            ], md=12),
        ], className="mb-3"),
        
        # Rolling Analytics (New)
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("📈 Rolling 60-Day Correlation", className="mb-0")),
                    dbc.CardBody([
                        dcc.Graph(id='sl-rolling-correlation-chart', config={'displayModeBar': False})
                    ])
                ])
            ], md=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("📊 Rolling 60-Day Beta", className="mb-0")),
                    dbc.CardBody([
                        dcc.Graph(id='sl-rolling-beta-chart', config={'displayModeBar': False})
                    ])
                ])
            ], md=6),
        ], className="mb-3"),
        
    ], fluid=True, className="p-3")


def calculate_beta(strategy_returns, benchmark_returns):
    """
    Calculate beta (systematic risk) using covariance method.
    
    Beta = Cov(Strategy, Benchmark) / Var(Benchmark)
    
    Args:
        strategy_returns: Array-like strategy returns
        benchmark_returns: Array-like benchmark returns
        
    Returns:
        float: Beta coefficient (1.0 = moves with market, >1 = more volatile, <1 = less volatile)
    """
    import numpy as np
    
    if len(strategy_returns) == 0 or len(benchmark_returns) == 0:
        return None
        
    # Ensure equal lengths
    min_len = min(len(strategy_returns), len(benchmark_returns))
    strat = strategy_returns[-min_len:]
    bench = benchmark_returns[-min_len:]
    
    try:
        covariance = np.cov(strat, bench)[0, 1]
        benchmark_variance = np.var(bench)
        
        if benchmark_variance == 0:
            return None
            
        return covariance / benchmark_variance
    except Exception as e:
        logger.error(f"Beta calculation error: {e}")
        return None


def calculate_information_ratio(strategy_returns, benchmark_returns, periods_per_year=252):
    """
    Calculate Information Ratio (IR) - risk-adjusted alpha.
    
    IR = (Strategy Return - Benchmark Return) / Tracking Error
    
    Args:
        strategy_returns: Array-like strategy returns
        benchmark_returns: Array-like benchmark returns
        periods_per_year: Annualization factor (252 for daily, 52 for weekly, 12 for monthly)
        
    Returns:
        float: Information Ratio (higher is better)
    """
    import numpy as np
    
    if len(strategy_returns) == 0 or len(benchmark_returns) == 0:
        return None
        
    # Ensure equal lengths
    min_len = min(len(strategy_returns), len(benchmark_returns))
    strat = strategy_returns[-min_len:]
    bench = benchmark_returns[-min_len:]
    
    try:
        # Excess returns (active returns)
        excess_returns = strat - bench
        
        # Annualized excess return
        avg_excess = np.mean(excess_returns) * periods_per_year
        
        # Tracking error (std dev of excess returns, annualized)
        tracking_error = np.std(excess_returns) * np.sqrt(periods_per_year)
        
        if tracking_error == 0:
            return None
            
        return avg_excess / tracking_error
    except Exception as e:
        logger.error(f"Information Ratio calculation error: {e}")
        return None


def calculate_tracking_error(strategy_returns, benchmark_returns, periods_per_year=252):
    """
    Calculate Tracking Error - volatility of excess returns.
    
    Tracking Error = StdDev(Strategy Return - Benchmark Return) * sqrt(periods_per_year)
    
    Args:
        strategy_returns: Array-like strategy returns
        benchmark_returns: Array-like benchmark returns
        periods_per_year: Annualization factor
        
    Returns:
        float: Annualized tracking error as decimal (e.g., 0.05 = 5%)
    """
    import numpy as np
    
    if len(strategy_returns) == 0 or len(benchmark_returns) == 0:
        return None
        
    min_len = min(len(strategy_returns), len(benchmark_returns))
    strat = strategy_returns[-min_len:]
    bench = benchmark_returns[-min_len:]
    
    try:
        excess_returns = strat - bench
        tracking_error = np.std(excess_returns) * np.sqrt(periods_per_year)
        return tracking_error
    except Exception as e:
        logger.error(f"Tracking Error calculation error: {e}")
        return None


logger.info("✓ Strategy Lab Benchmark subtab loaded (enhanced with Beta, IR, Tracking Error)")

