"""
Trade Journal - Track and analyze options trades

Author: Options Lab Enhancement Phase
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from dataclasses import dataclass, asdict
import json
import os

logger = logging.getLogger(__name__)


@dataclass
class TradeEntry:
    """Single trade entry."""
    id: str
    ticker: str
    strategy: str  # 'long_call', 'iron_condor', etc.
    entry_date: str
    exit_date: Optional[str]
    entry_price: float
    exit_price: Optional[float]
    quantity: int
    pnl: Optional[float]
    pnl_percent: Optional[float]
    status: str  # 'open', 'closed', 'expired'
    legs: List[Dict]
    notes: str
    tags: List[str]
    iv_at_entry: Optional[float]
    iv_at_exit: Optional[float]
    spot_at_entry: float
    spot_at_exit: Optional[float]
    max_drawdown: Optional[float]
    max_profit_seen: Optional[float]
    hold_time_days: Optional[int]
    win: Optional[bool]


class TradeJournal:
    """Track and analyze options trades."""
    
    def __init__(self, storage_path: str = None):
        self.trades: List[TradeEntry] = []
        self.storage_path = storage_path or '/tmp/options_trade_journal.json'
        self._load()
        
    def _load(self):
        """Load trades from storage."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    self.trades = [TradeEntry(**t) for t in data.get('trades', [])]
                logger.info(f"Loaded {len(self.trades)} trades from journal")
            except Exception as e:
                logger.error(f"Error loading journal: {e}")
                self.trades = []
        else:
            # Initialize with sample trades
            self._create_sample_trades()
    
    def _save(self):
        """Save trades to storage."""
        try:
            data = {'trades': [asdict(t) for t in self.trades]}
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.trades)} trades to journal")
        except Exception as e:
            logger.error(f"Error saving journal: {e}")
    
    def _create_sample_trades(self):
        """Create sample trades for demonstration."""
        np.random.seed(42)
        strategies = ['long_call', 'long_put', 'bull_call_spread', 'iron_condor', 
                     'straddle', 'covered_call']
        tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'SPY', 'NVDA', 'AMD', 'META']
        
        for i in range(30):
            strategy = np.random.choice(strategies)
            ticker = np.random.choice(tickers)
            entry_date = datetime.now() - timedelta(days=np.random.randint(1, 180))
            is_closed = np.random.random() > 0.3
            
            entry_price = np.random.uniform(1, 20)
            spot = np.random.uniform(100, 500)
            iv = np.random.uniform(0.2, 0.6)
            
            if is_closed:
                hold_days = np.random.randint(1, 45)
                exit_date = entry_date + timedelta(days=hold_days)
                pnl_pct = np.random.uniform(-0.5, 1.0)
                exit_price = entry_price * (1 + pnl_pct)
                pnl = (exit_price - entry_price) * 100
                win = pnl > 0
                status = 'closed'
                spot_exit = spot * (1 + np.random.uniform(-0.1, 0.1))
                iv_exit = iv * (1 + np.random.uniform(-0.3, 0.3))
            else:
                exit_date = None
                exit_price = None
                pnl = None
                pnl_pct = None
                win = None
                hold_days = (datetime.now() - entry_date).days
                status = 'open'
                spot_exit = None
                iv_exit = None
            
            trade = TradeEntry(
                id=f"T{i+1:04d}",
                ticker=ticker,
                strategy=strategy,
                entry_date=entry_date.strftime('%Y-%m-%d'),
                exit_date=exit_date.strftime('%Y-%m-%d') if exit_date else None,
                entry_price=round(entry_price, 2),
                exit_price=round(exit_price, 2) if exit_price else None,
                quantity=np.random.randint(1, 10),
                pnl=round(pnl, 2) if pnl else None,
                pnl_percent=round(pnl_pct * 100, 2) if pnl_pct else None,
                status=status,
                legs=[],
                notes=f"Sample trade #{i+1}",
                tags=['sample'],
                iv_at_entry=round(iv, 4),
                iv_at_exit=round(iv_exit, 4) if iv_exit else None,
                spot_at_entry=round(spot, 2),
                spot_at_exit=round(spot_exit, 2) if spot_exit else None,
                max_drawdown=round(-np.random.uniform(0, entry_price * 0.5), 2),
                max_profit_seen=round(np.random.uniform(0, entry_price * 0.5), 2),
                hold_time_days=hold_days,
                win=win
            )
            self.trades.append(trade)
    
    def add_trade(self, **kwargs) -> TradeEntry:
        """Add a new trade to the journal."""
        trade_id = f"T{len(self.trades) + 1:04d}"
        
        trade = TradeEntry(
            id=trade_id,
            status='open',
            exit_date=None,
            exit_price=None,
            pnl=None,
            pnl_percent=None,
            max_drawdown=None,
            max_profit_seen=None,
            hold_time_days=None,
            win=None,
            spot_at_exit=None,
            iv_at_exit=None,
            **kwargs
        )
        
        self.trades.append(trade)
        self._save()
        logger.info(f"Added trade {trade_id}")
        return trade
    
    def close_trade(self, trade_id: str, exit_price: float, 
                    spot_at_exit: float = None, iv_at_exit: float = None,
                    notes: str = None) -> Optional[TradeEntry]:
        """Close an open trade."""
        for trade in self.trades:
            if trade.id == trade_id and trade.status == 'open':
                trade.exit_date = datetime.now().strftime('%Y-%m-%d')
                trade.exit_price = round(exit_price, 2)
                trade.pnl = round((exit_price - trade.entry_price) * trade.quantity * 100, 2)
                trade.pnl_percent = round((exit_price - trade.entry_price) / trade.entry_price * 100, 2)
                trade.status = 'closed'
                trade.win = trade.pnl > 0
                trade.spot_at_exit = spot_at_exit
                trade.iv_at_exit = iv_at_exit
                
                if notes:
                    trade.notes += f" | Close: {notes}"
                
                # Calculate hold time
                entry = datetime.strptime(trade.entry_date, '%Y-%m-%d')
                trade.hold_time_days = (datetime.now() - entry).days
                
                self._save()
                logger.info(f"Closed trade {trade_id} with P&L: ${trade.pnl}")
                return trade
        
        return None
    
    def get_open_trades(self) -> List[TradeEntry]:
        """Get all open trades."""
        return [t for t in self.trades if t.status == 'open']
    
    def get_closed_trades(self) -> List[TradeEntry]:
        """Get all closed trades."""
        return [t for t in self.trades if t.status == 'closed']
    
    def get_trades_df(self, status: str = None) -> pd.DataFrame:
        """Get trades as DataFrame."""
        if status:
            trades = [t for t in self.trades if t.status == status]
        else:
            trades = self.trades
        
        return pd.DataFrame([asdict(t) for t in trades])
    
    def get_statistics(self) -> Dict:
        """Calculate trading statistics."""
        closed = self.get_closed_trades()
        
        if not closed:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'max_win': 0,
                'max_loss': 0,
                'avg_hold_time': 0
            }
        
        wins = [t for t in closed if t.win]
        losses = [t for t in closed if not t.win]
        
        total_pnl = sum(t.pnl for t in closed if t.pnl)
        win_pnl = sum(t.pnl for t in wins if t.pnl) if wins else 0
        loss_pnl = sum(abs(t.pnl) for t in losses if t.pnl) if losses else 0
        
        return {
            'total_trades': len(closed),
            'open_trades': len(self.get_open_trades()),
            'win_rate': round(len(wins) / len(closed) * 100, 1) if closed else 0,
            'total_pnl': round(total_pnl, 2),
            'avg_pnl': round(total_pnl / len(closed), 2) if closed else 0,
            'avg_win': round(win_pnl / len(wins), 2) if wins else 0,
            'avg_loss': round(-loss_pnl / len(losses), 2) if losses else 0,
            'profit_factor': round(win_pnl / loss_pnl, 2) if loss_pnl > 0 else float('inf'),
            'max_win': max([t.pnl for t in wins if t.pnl], default=0),
            'max_loss': min([t.pnl for t in losses if t.pnl], default=0),
            'avg_hold_time': round(
                sum(t.hold_time_days for t in closed if t.hold_time_days) / len(closed), 1
            ) if closed else 0
        }
    
    def get_performance_by_strategy(self) -> pd.DataFrame:
        """Get performance breakdown by strategy."""
        closed = self.get_trades_df('closed')
        
        if closed.empty:
            return pd.DataFrame()
        
        return closed.groupby('strategy').agg({
            'pnl': ['count', 'sum', 'mean'],
            'win': 'mean',
            'hold_time_days': 'mean'
        }).round(2).reset_index()
    
    def get_performance_by_ticker(self) -> pd.DataFrame:
        """Get performance breakdown by ticker."""
        closed = self.get_trades_df('closed')
        
        if closed.empty:
            return pd.DataFrame()
        
        return closed.groupby('ticker').agg({
            'pnl': ['count', 'sum', 'mean'],
            'win': 'mean'
        }).round(2).reset_index()


def create_pnl_chart(journal: TradeJournal) -> go.Figure:
    """Create cumulative P&L chart."""
    df = journal.get_trades_df('closed')
    
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No closed trades", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template='plotly_dark')
        return fig
    
    df = df.sort_values('exit_date')
    df['cumulative_pnl'] = df['pnl'].cumsum()
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['exit_date'],
        y=df['cumulative_pnl'],
        mode='lines+markers',
        line=dict(color='#4CAF50', width=2),
        fill='tozeroy',
        fillcolor='rgba(76, 175, 80, 0.2)',
        name='Cumulative P&L'
    ))
    
    # Add individual trades
    colors = ['green' if pnl > 0 else 'red' for pnl in df['pnl']]
    fig.add_trace(go.Bar(
        x=df['exit_date'],
        y=df['pnl'],
        marker_color=colors,
        name='Trade P&L',
        opacity=0.5
    ))
    
    fig.update_layout(
        title='Trading Performance',
        xaxis_title='Date',
        yaxis_title='P&L ($)',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.8)',
        height=400,
        barmode='overlay'
    )
    
    return fig


def create_win_rate_gauge(journal: TradeJournal) -> go.Figure:
    """Create win rate gauge chart."""
    stats = journal.get_statistics()
    win_rate = stats.get('win_rate', 0)
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=win_rate,
        title={'text': "Win Rate (%)"},
        delta={'reference': 50},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "#4CAF50"},
            'steps': [
                {'range': [0, 40], 'color': "rgba(244, 67, 54, 0.3)"},
                {'range': [40, 60], 'color': "rgba(255, 193, 7, 0.3)"},
                {'range': [60, 100], 'color': "rgba(76, 175, 80, 0.3)"}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 2},
                'thickness': 0.75,
                'value': win_rate
            }
        }
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        height=300
    )
    
    return fig


def create_strategy_breakdown(journal: TradeJournal) -> go.Figure:
    """Create strategy performance breakdown chart."""
    perf = journal.get_performance_by_strategy()
    
    if perf.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template='plotly_dark')
        return fig
    
    # Flatten multi-level columns
    perf.columns = ['strategy', 'trades', 'total_pnl', 'avg_pnl', 'win_rate', 'avg_hold']
    
    fig = px.bar(
        perf,
        x='strategy',
        y='total_pnl',
        color='win_rate',
        color_continuous_scale='RdYlGn',
        text='trades',
        title='P&L by Strategy',
        hover_data=['avg_pnl', 'win_rate', 'avg_hold']
    )
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.8)',
        height=350
    )
    
    return fig


def create_monthly_pnl(journal: TradeJournal) -> go.Figure:
    """Create monthly P&L heatmap."""
    df = journal.get_trades_df('closed')
    
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template='plotly_dark')
        return fig
    
    df['exit_date'] = pd.to_datetime(df['exit_date'])
    df['month'] = df['exit_date'].dt.month
    df['year'] = df['exit_date'].dt.year
    
    monthly = df.pivot_table(
        index='year', 
        columns='month', 
        values='pnl', 
        aggfunc='sum'
    ).fillna(0)
    
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    fig = go.Figure(data=go.Heatmap(
        z=monthly.values,
        x=[month_names[m-1] for m in monthly.columns],
        y=monthly.index.astype(str),
        colorscale='RdYlGn',
        colorbar=dict(title='P&L ($)')
    ))
    
    fig.update_layout(
        title='Monthly P&L',
        xaxis_title='Month',
        yaxis_title='Year',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.8)',
        height=300
    )
    
    return fig


# Singleton instance
_journal = None

def get_trade_journal() -> TradeJournal:
    """Get singleton trade journal instance."""
    global _journal
    if _journal is None:
        _journal = TradeJournal()
    return _journal
