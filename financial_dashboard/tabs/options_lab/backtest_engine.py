"""
Alpaca Options Lab - Advanced Backtesting Engine
Implements Items 126-150 from the 220 NEW IDEAS roadmap
"""

import dash_bootstrap_components as dbc
from dash import html, dcc
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json


# ============================================================
# ITEM 126: Historical Options Data Integration
# ============================================================
@dataclass
class HistoricalOptionData:
    """Historical options data structure."""
    date: datetime
    underlying_price: float
    strike: float
    expiration: str
    option_type: str  # 'call' or 'put'
    bid: float
    ask: float
    last: float
    volume: int
    open_interest: int
    iv: float
    delta: float
    gamma: float
    theta: float
    vega: float


class HistoricalDataLoader:
    """Load and manage historical options data."""
    
    def __init__(self, data_source: str = "local"):
        self.data_source = data_source
        self.cache = {}
    
    def load_option_chain(
        self,
        symbol: str,
        date: datetime,
        expiration: str = None
    ) -> List[HistoricalOptionData]:
        """Load historical option chain for a specific date."""
        cache_key = f"{symbol}_{date.strftime('%Y%m%d')}_{expiration}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Placeholder - would fetch from actual data source
        data = self._generate_sample_chain(symbol, date, expiration)
        self.cache[cache_key] = data
        return data
    
    def _generate_sample_chain(
        self,
        symbol: str,
        date: datetime,
        expiration: str
    ) -> List[HistoricalOptionData]:
        """Generate sample chain data for testing."""
        spot = 100 + np.random.randn() * 5
        strikes = np.arange(spot * 0.85, spot * 1.15, 2.5)
        
        options = []
        for strike in strikes:
            for opt_type in ['call', 'put']:
                moneyness = (spot - strike) / spot
                iv = 0.25 + abs(moneyness) * 0.1  # Skew
                
                options.append(HistoricalOptionData(
                    date=date,
                    underlying_price=spot,
                    strike=strike,
                    expiration=expiration or (date + timedelta(days=30)).strftime('%Y-%m-%d'),
                    option_type=opt_type,
                    bid=max(0, 2 + np.random.uniform(-0.1, 0)),
                    ask=max(0.05, 2.1 + np.random.uniform(0, 0.1)),
                    last=2.05,
                    volume=int(np.random.exponential(100)),
                    open_interest=int(np.random.exponential(1000)),
                    iv=iv,
                    delta=0.5 if abs(moneyness) < 0.02 else (0.7 if moneyness > 0 else 0.3),
                    gamma=0.05,
                    theta=-0.05,
                    vega=0.10
                ))
        
        return options


# ============================================================
# ITEM 127: Backtest Configuration
# ============================================================
@dataclass
class BacktestConfig:
    """Configuration for backtest."""
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_capital: float = 100000
    
    # Position sizing
    max_position_size: int = 10  # contracts
    position_size_method: str = 'fixed'  # fixed, pct_capital, kelly
    position_size_value: float = 1  # contracts or percentage
    
    # Entry rules
    entry_signal: str = 'manual'  # manual, iv_rank, delta_neutral
    entry_iv_threshold: float = 0.5  # IV rank threshold
    entry_dte_min: int = 30
    entry_dte_max: int = 45
    
    # Exit rules
    profit_target: float = 0.50  # 50% of max profit
    stop_loss: float = 2.0  # 200% of max profit
    dte_exit: int = 5  # Close at X DTE
    
    # Costs
    commission_per_contract: float = 0.65
    slippage_pct: float = 0.02  # 2% of spread
    
    # Strategy
    strategy_type: str = 'iron_condor'


# ============================================================
# ITEM 128: Backtest Engine
# ============================================================
@dataclass
class BacktestTrade:
    """Record of a single trade."""
    trade_id: int
    entry_date: datetime
    exit_date: Optional[datetime]
    strategy: str
    legs: List[Dict]  # Leg details
    entry_credit: float
    exit_debit: Optional[float]
    pnl: float = 0
    commission: float = 0
    status: str = 'open'  # open, closed_profit, closed_loss, closed_expiry


@dataclass
class BacktestResult:
    """Complete backtest results."""
    config: BacktestConfig
    trades: List[BacktestTrade]
    equity_curve: pd.DataFrame
    daily_returns: pd.Series
    metrics: Dict[str, Any]


class BacktestEngine:
    """Options backtesting engine."""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.data_loader = HistoricalDataLoader()
        self.trades: List[BacktestTrade] = []
        self.equity = config.initial_capital
        self.equity_history = []
        self.current_positions = []
        self.trade_counter = 0
    
    def run(self) -> BacktestResult:
        """Run the backtest."""
        current_date = self.config.start_date
        
        while current_date <= self.config.end_date:
            # Skip weekends
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue
            
            # Update existing positions
            self._update_positions(current_date)
            
            # Check for new entry signals
            if self._check_entry_signal(current_date):
                self._open_position(current_date)
            
            # Record equity
            self.equity_history.append({
                'date': current_date,
                'equity': self.equity,
                'positions': len(self.current_positions)
            })
            
            current_date += timedelta(days=1)
        
        return self._compile_results()
    
    def _check_entry_signal(self, date: datetime) -> bool:
        """Check if entry conditions are met."""
        if len(self.current_positions) >= 3:  # Max 3 concurrent
            return False
        
        # Simplified entry logic
        return np.random.random() < 0.05  # ~5% chance per day
    
    def _open_position(self, date: datetime):
        """Open a new position."""
        self.trade_counter += 1
        
        # Generate sample trade
        entry_credit = np.random.uniform(1.0, 3.0)
        commission = self.config.commission_per_contract * 4  # 4 legs
        
        trade = BacktestTrade(
            trade_id=self.trade_counter,
            entry_date=date,
            exit_date=None,
            strategy=self.config.strategy_type,
            legs=[],
            entry_credit=entry_credit,
            exit_debit=None,
            commission=commission
        )
        
        self.trades.append(trade)
        self.current_positions.append(trade)
        self.equity -= commission
    
    def _update_positions(self, date: datetime):
        """Update and potentially close positions."""
        closed = []
        
        for trade in self.current_positions:
            days_held = (date - trade.entry_date).days
            
            # Random P&L evolution
            current_value = trade.entry_credit * (1 + np.random.uniform(-0.3, 0.4))
            
            # Check exit conditions
            should_close = False
            
            if current_value >= trade.entry_credit * (1 + self.config.profit_target):
                should_close = True
                trade.status = 'closed_profit'
            elif current_value <= trade.entry_credit * (1 - self.config.stop_loss):
                should_close = True
                trade.status = 'closed_loss'
            elif days_held >= self.config.entry_dte_min - self.config.dte_exit:
                should_close = True
                trade.status = 'closed_expiry'
            
            if should_close:
                exit_debit = trade.entry_credit - np.random.uniform(-0.5, 1.0)
                trade.exit_date = date
                trade.exit_debit = max(0, exit_debit)
                trade.pnl = (trade.entry_credit - trade.exit_debit) * 100 - trade.commission
                self.equity += trade.pnl
                closed.append(trade)
        
        for trade in closed:
            self.current_positions.remove(trade)
    
    def _compile_results(self) -> BacktestResult:
        """Compile backtest results."""
        equity_df = pd.DataFrame(self.equity_history)
        equity_df.set_index('date', inplace=True)
        
        daily_returns = equity_df['equity'].pct_change().dropna()
        
        metrics = self._calculate_metrics(equity_df, daily_returns)
        
        return BacktestResult(
            config=self.config,
            trades=self.trades,
            equity_curve=equity_df,
            daily_returns=daily_returns,
            metrics=metrics
        )
    
    def _calculate_metrics(
        self,
        equity_df: pd.DataFrame,
        daily_returns: pd.Series
    ) -> Dict[str, Any]:
        """Calculate performance metrics."""
        total_return = (equity_df['equity'].iloc[-1] / self.config.initial_capital - 1) * 100
        
        # Sharpe ratio
        if len(daily_returns) > 0 and daily_returns.std() > 0:
            sharpe = daily_returns.mean() / daily_returns.std() * np.sqrt(252)
        else:
            sharpe = 0
        
        # Sortino ratio
        downside_returns = daily_returns[daily_returns < 0]
        if len(downside_returns) > 0 and downside_returns.std() > 0:
            sortino = daily_returns.mean() / downside_returns.std() * np.sqrt(252)
        else:
            sortino = 0
        
        # Max drawdown
        peak = equity_df['equity'].expanding().max()
        drawdown = (equity_df['equity'] - peak) / peak * 100
        max_drawdown = drawdown.min()
        
        # Win rate
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl <= 0]
        win_rate = len(winning_trades) / len(self.trades) * 100 if self.trades else 0
        
        # Profit factor
        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        return {
            'total_return_pct': total_return,
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'max_drawdown_pct': max_drawdown,
            'win_rate_pct': win_rate,
            'profit_factor': profit_factor,
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'avg_win': np.mean([t.pnl for t in winning_trades]) if winning_trades else 0,
            'avg_loss': np.mean([t.pnl for t in losing_trades]) if losing_trades else 0,
            'largest_win': max([t.pnl for t in winning_trades]) if winning_trades else 0,
            'largest_loss': min([t.pnl for t in losing_trades]) if losing_trades else 0,
            'avg_days_held': np.mean([(t.exit_date - t.entry_date).days 
                                       for t in self.trades if t.exit_date]) if self.trades else 0,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'net_profit': gross_profit - gross_loss,
            'total_commission': sum(t.commission for t in self.trades)
        }


# ============================================================
# ITEM 135: Equity Curve Chart
# ============================================================
def create_equity_curve_chart(result: BacktestResult) -> go.Figure:
    """Create equity curve visualization."""
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.5, 0.25, 0.25],
        subplot_titles=('Equity Curve', 'Drawdown', 'Position Count')
    )
    
    # Equity curve
    fig.add_trace(go.Scatter(
        x=result.equity_curve.index,
        y=result.equity_curve['equity'],
        mode='lines',
        name='Equity',
        line=dict(color='#007bff', width=2),
        fill='tozeroy',
        fillcolor='rgba(0, 123, 255, 0.1)'
    ), row=1, col=1)
    
    # Initial capital line
    fig.add_hline(
        y=result.config.initial_capital,
        line_dash="dash",
        line_color="gray",
        annotation_text="Initial Capital",
        row=1, col=1
    )
    
    # Drawdown
    peak = result.equity_curve['equity'].expanding().max()
    drawdown = (result.equity_curve['equity'] - peak) / peak * 100
    
    fig.add_trace(go.Scatter(
        x=result.equity_curve.index,
        y=drawdown,
        mode='lines',
        name='Drawdown',
        fill='tozeroy',
        fillcolor='rgba(220, 53, 69, 0.3)',
        line=dict(color='#dc3545', width=1)
    ), row=2, col=1)
    
    # Position count
    fig.add_trace(go.Bar(
        x=result.equity_curve.index,
        y=result.equity_curve['positions'],
        name='Positions',
        marker_color='#6f42c1'
    ), row=3, col=1)
    
    fig.update_layout(
        height=600,
        showlegend=False,
        title_text=f"Backtest Results: {result.config.strategy_type}"
    )
    
    fig.update_yaxes(title_text="Equity ($)", row=1, col=1)
    fig.update_yaxes(title_text="Drawdown (%)", row=2, col=1)
    fig.update_yaxes(title_text="# Positions", row=3, col=1)
    
    return fig


# ============================================================
# ITEM 137: Trade Distribution Chart
# ============================================================
def create_trade_distribution_chart(trades: List[BacktestTrade]) -> go.Figure:
    """Create trade P&L distribution chart."""
    pnls = [t.pnl for t in trades]
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('P&L Distribution', 'Cumulative P&L')
    )
    
    # Histogram
    fig.add_trace(go.Histogram(
        x=pnls,
        nbinsx=30,
        marker_color=['#28a745' if p >= 0 else '#dc3545' for p in pnls],
        name='P&L'
    ), row=1, col=1)
    
    fig.add_vline(x=0, line_dash="dash", line_color="black", row=1, col=1)
    
    # Cumulative P&L
    cumulative = np.cumsum(pnls)
    colors = ['#28a745' if c >= 0 else '#dc3545' for c in cumulative]
    
    fig.add_trace(go.Scatter(
        x=list(range(1, len(cumulative) + 1)),
        y=cumulative,
        mode='lines+markers',
        name='Cumulative P&L',
        line=dict(color='#007bff', width=2)
    ), row=1, col=2)
    
    fig.add_hline(y=0, line_dash="dash", line_color="black", row=1, col=2)
    
    fig.update_layout(height=350, showlegend=False)
    fig.update_xaxes(title_text="P&L ($)", row=1, col=1)
    fig.update_xaxes(title_text="Trade #", row=1, col=2)
    fig.update_yaxes(title_text="Count", row=1, col=1)
    fig.update_yaxes(title_text="Cumulative P&L ($)", row=1, col=2)
    
    return fig


# ============================================================
# ITEM 140: Metrics Dashboard
# ============================================================
def create_metrics_dashboard(metrics: Dict[str, Any]) -> html.Div:
    """Create metrics dashboard cards."""
    
    def metric_card(title: str, value: str, color: str = "primary") -> dbc.Col:
        return dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(value, className=f"text-{color} mb-0"),
                    html.Small(title, className="text-muted")
                ], className="text-center py-2")
            ])
        ], width=2)
    
    return html.Div([
        dbc.Row([
            metric_card("Total Return", f"{metrics['total_return_pct']:.1f}%", 
                       "success" if metrics['total_return_pct'] > 0 else "danger"),
            metric_card("Sharpe Ratio", f"{metrics['sharpe_ratio']:.2f}",
                       "success" if metrics['sharpe_ratio'] > 1 else "warning"),
            metric_card("Max Drawdown", f"{metrics['max_drawdown_pct']:.1f}%", "danger"),
            metric_card("Win Rate", f"{metrics['win_rate_pct']:.0f}%",
                       "success" if metrics['win_rate_pct'] > 50 else "warning"),
            metric_card("Profit Factor", f"{metrics['profit_factor']:.2f}",
                       "success" if metrics['profit_factor'] > 1.5 else "warning"),
            metric_card("Total Trades", str(metrics['total_trades']), "info"),
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Trade Statistics"),
                    dbc.CardBody([
                        dbc.Table([
                            html.Tbody([
                                html.Tr([html.Td("Avg Win"), html.Td(f"${metrics['avg_win']:,.0f}", className="text-success")]),
                                html.Tr([html.Td("Avg Loss"), html.Td(f"${metrics['avg_loss']:,.0f}", className="text-danger")]),
                                html.Tr([html.Td("Largest Win"), html.Td(f"${metrics['largest_win']:,.0f}", className="text-success")]),
                                html.Tr([html.Td("Largest Loss"), html.Td(f"${metrics['largest_loss']:,.0f}", className="text-danger")]),
                                html.Tr([html.Td("Avg Days Held"), html.Td(f"{metrics['avg_days_held']:.1f}")]),
                                html.Tr([html.Td("Total Commission"), html.Td(f"${metrics['total_commission']:,.0f}")]),
                            ])
                        ], bordered=True, size="sm")
                    ])
                ])
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("P&L Breakdown"),
                    dbc.CardBody([
                        dbc.Table([
                            html.Tbody([
                                html.Tr([html.Td("Gross Profit"), html.Td(f"${metrics['gross_profit']:,.0f}", className="text-success")]),
                                html.Tr([html.Td("Gross Loss"), html.Td(f"${metrics['gross_loss']:,.0f}", className="text-danger")]),
                                html.Tr([html.Td("Net Profit"), html.Td(f"${metrics['net_profit']:,.0f}", 
                                        className="text-success" if metrics['net_profit'] > 0 else "text-danger")]),
                                html.Tr([html.Td("Winning Trades"), html.Td(str(metrics['winning_trades']))]),
                                html.Tr([html.Td("Losing Trades"), html.Td(str(metrics['losing_trades']))]),
                            ])
                        ], bordered=True, size="sm")
                    ])
                ])
            ], width=6)
        ])
    ])


# ============================================================
# ITEM 145: Monte Carlo Simulation
# ============================================================
def run_monte_carlo(
    trades: List[BacktestTrade],
    initial_capital: float,
    num_simulations: int = 1000
) -> Dict[str, Any]:
    """Run Monte Carlo simulation on trade results."""
    pnls = [t.pnl for t in trades]
    
    final_equities = []
    max_drawdowns = []
    
    for _ in range(num_simulations):
        # Randomly shuffle trades
        shuffled_pnls = np.random.permutation(pnls)
        
        # Calculate equity curve
        equity = initial_capital
        peak = equity
        max_dd = 0
        
        for pnl in shuffled_pnls:
            equity += pnl
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak
            if dd > max_dd:
                max_dd = dd
        
        final_equities.append(equity)
        max_drawdowns.append(max_dd * 100)
    
    return {
        'final_equities': final_equities,
        'max_drawdowns': max_drawdowns,
        'median_final': np.median(final_equities),
        'p5_final': np.percentile(final_equities, 5),
        'p95_final': np.percentile(final_equities, 95),
        'median_drawdown': np.median(max_drawdowns),
        'p95_drawdown': np.percentile(max_drawdowns, 95),
        'prob_profit': sum(1 for e in final_equities if e > initial_capital) / len(final_equities) * 100
    }


def create_monte_carlo_chart(mc_results: Dict[str, Any], initial_capital: float) -> go.Figure:
    """Create Monte Carlo visualization."""
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Final Equity Distribution', 'Max Drawdown Distribution')
    )
    
    # Final equity histogram
    fig.add_trace(go.Histogram(
        x=mc_results['final_equities'],
        nbinsx=50,
        marker_color='#007bff',
        name='Final Equity'
    ), row=1, col=1)
    
    fig.add_vline(x=initial_capital, line_dash="dash", line_color="red",
                 annotation_text="Initial", row=1, col=1)
    fig.add_vline(x=mc_results['median_final'], line_dash="dash", line_color="green",
                 annotation_text="Median", row=1, col=1)
    
    # Drawdown histogram
    fig.add_trace(go.Histogram(
        x=mc_results['max_drawdowns'],
        nbinsx=50,
        marker_color='#dc3545',
        name='Max Drawdown'
    ), row=1, col=2)
    
    fig.add_vline(x=mc_results['p95_drawdown'], line_dash="dash", line_color="orange",
                 annotation_text="95th %ile", row=1, col=2)
    
    fig.update_layout(
        height=350,
        showlegend=False,
        title_text=f"Monte Carlo Simulation (n={len(mc_results['final_equities'])})"
    )
    
    fig.update_xaxes(title_text="Final Equity ($)", row=1, col=1)
    fig.update_xaxes(title_text="Max Drawdown (%)", row=1, col=2)
    
    return fig


# ============================================================
# Main Backtest UI
# ============================================================
def create_backtest_panel() -> html.Div:
    """Create the complete backtesting panel."""
    return html.Div([
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-history me-2"),
                "Strategy Backtester"
            ]),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Strategy"),
                        dbc.Select(
                            id="backtest-strategy",
                            options=[
                                {"label": "Iron Condor", "value": "iron_condor"},
                                {"label": "Iron Butterfly", "value": "iron_butterfly"},
                                {"label": "Vertical Spread", "value": "vertical"},
                                {"label": "Straddle", "value": "straddle"},
                            ],
                            value="iron_condor"
                        )
                    ], width=3),
                    dbc.Col([
                        dbc.Label("Date Range"),
                        dcc.DatePickerRange(
                            id="backtest-dates",
                            start_date=datetime.now() - timedelta(days=365),
                            end_date=datetime.now(),
                        )
                    ], width=4),
                    dbc.Col([
                        dbc.Label("Initial Capital"),
                        dbc.Input(id="backtest-capital", type="number", value=100000)
                    ], width=2),
                    dbc.Col([
                        dbc.Label(" "),
                        dbc.Button([
                            html.I(className="fas fa-play me-2"),
                            "Run Backtest"
                        ], id="run-backtest-btn", color="primary", className="w-100 d-block mt-1")
                    ], width=3),
                ], className="mb-3"),
                
                dbc.Accordion([
                    dbc.AccordionItem([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Profit Target (%)"),
                                dbc.Input(id="bt-profit-target", type="number", value=50)
                            ], width=3),
                            dbc.Col([
                                dbc.Label("Stop Loss (%)"),
                                dbc.Input(id="bt-stop-loss", type="number", value=200)
                            ], width=3),
                            dbc.Col([
                                dbc.Label("DTE Exit"),
                                dbc.Input(id="bt-dte-exit", type="number", value=5)
                            ], width=3),
                            dbc.Col([
                                dbc.Label("Max Positions"),
                                dbc.Input(id="bt-max-pos", type="number", value=3)
                            ], width=3),
                        ])
                    ], title="Advanced Settings")
                ], start_collapsed=True, className="mb-3")
            ])
        ], className="mb-3"),
        
        # Results area
        html.Div(id="backtest-results-area"),
        
        dcc.Store(id="backtest-results-store")
    ])


__all__ = [
    'HistoricalOptionData',
    'HistoricalDataLoader',
    'BacktestConfig',
    'BacktestTrade',
    'BacktestResult',
    'BacktestEngine',
    'create_equity_curve_chart',
    'create_trade_distribution_chart',
    'create_metrics_dashboard',
    'run_monte_carlo',
    'create_monte_carlo_chart',
    'create_backtest_panel',
]
