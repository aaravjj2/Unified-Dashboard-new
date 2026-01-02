"""
Earnings Calendar - Track earnings dates and expected moves

Author: Options Lab Enhancement Phase
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

logger = logging.getLogger(__name__)


class EarningsEvent:
    """Single earnings event."""
    
    def __init__(self, ticker: str, earnings_date: datetime, timing: str,
                 expected_move: float, historical_moves: List[float],
                 iv_percentile: float = None, options_volume: int = None):
        self.ticker = ticker
        self.earnings_date = earnings_date
        self.timing = timing  # 'BMO' (before market open), 'AMC' (after market close)
        self.expected_move = expected_move  # as percentage
        self.historical_moves = historical_moves  # last 8 quarters
        self.iv_percentile = iv_percentile
        self.options_volume = options_volume
        
    @property
    def days_until(self) -> int:
        return (self.earnings_date - datetime.now()).days
    
    @property
    def avg_historical_move(self) -> float:
        if self.historical_moves:
            return np.mean([abs(m) for m in self.historical_moves])
        return 0
    
    @property
    def straddle_premium_ratio(self) -> float:
        """Ratio of expected move to average historical move."""
        avg = self.avg_historical_move
        if avg > 0:
            return self.expected_move / avg
        return 1.0
    
    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'date': self.earnings_date.strftime('%Y-%m-%d'),
            'timing': self.timing,
            'days_until': self.days_until,
            'expected_move': self.expected_move,
            'avg_historical_move': self.avg_historical_move,
            'historical_moves': self.historical_moves,
            'iv_percentile': self.iv_percentile,
            'options_volume': self.options_volume,
            'straddle_ratio': self.straddle_premium_ratio
        }


class EarningsCalendar:
    """Track and analyze earnings events."""
    
    def __init__(self):
        self.events: List[EarningsEvent] = []
        self._generate_sample_data()
        
    def _generate_sample_data(self):
        """Generate sample earnings calendar data."""
        np.random.seed(42)
        
        tickers = [
            ('AAPL', 'BMO'), ('MSFT', 'AMC'), ('GOOGL', 'AMC'), ('AMZN', 'AMC'),
            ('META', 'AMC'), ('TSLA', 'AMC'), ('NVDA', 'AMC'), ('AMD', 'AMC'),
            ('NFLX', 'AMC'), ('DIS', 'AMC'), ('JPM', 'BMO'), ('BAC', 'BMO'),
            ('WMT', 'BMO'), ('TGT', 'BMO'), ('HD', 'BMO'), ('LOW', 'BMO'),
            ('CRM', 'AMC'), ('ORCL', 'AMC'), ('ADBE', 'AMC'), ('NOW', 'AMC'),
            ('PYPL', 'AMC'), ('SQ', 'AMC'), ('SHOP', 'BMO'), ('COIN', 'AMC'),
            ('SPY', 'N/A'), ('QQQ', 'N/A'), ('IWM', 'N/A')  # ETFs don't have earnings
        ]
        
        base_date = datetime.now()
        
        for ticker, timing in tickers:
            if ticker in ['SPY', 'QQQ', 'IWM']:
                continue  # Skip ETFs
            
            # Random date in next 60 days
            days_ahead = np.random.randint(1, 60)
            earnings_date = base_date + timedelta(days=days_ahead)
            
            # Historical moves (last 8 quarters)
            historical = [np.random.uniform(-15, 15) for _ in range(8)]
            
            # Expected move based on IV
            avg_hist = np.mean([abs(m) for m in historical])
            expected = avg_hist * np.random.uniform(0.8, 1.3)
            
            event = EarningsEvent(
                ticker=ticker,
                earnings_date=earnings_date,
                timing=timing,
                expected_move=round(expected, 2),
                historical_moves=[round(m, 2) for m in historical],
                iv_percentile=np.random.randint(40, 95),
                options_volume=np.random.randint(10000, 500000)
            )
            
            self.events.append(event)
        
        # Sort by date
        self.events.sort(key=lambda x: x.earnings_date)
    
    def get_upcoming(self, days: int = 14) -> List[EarningsEvent]:
        """Get earnings in the next N days."""
        cutoff = datetime.now() + timedelta(days=days)
        return [e for e in self.events if datetime.now() <= e.earnings_date <= cutoff]
    
    def get_by_week(self) -> Dict[str, List[EarningsEvent]]:
        """Group earnings by week."""
        weeks = {}
        
        for event in self.events:
            if event.days_until < 0:
                continue
            
            # Get week start (Monday)
            week_start = event.earnings_date - timedelta(days=event.earnings_date.weekday())
            week_key = week_start.strftime('%Y-%m-%d')
            
            if week_key not in weeks:
                weeks[week_key] = []
            weeks[week_key].append(event)
        
        return weeks
    
    def get_by_ticker(self, ticker: str) -> Optional[EarningsEvent]:
        """Get earnings event for a specific ticker."""
        for event in self.events:
            if event.ticker == ticker:
                return event
        return None
    
    def get_high_iv_opportunities(self, iv_threshold: int = 70) -> List[EarningsEvent]:
        """Find earnings with high IV (good for selling premium)."""
        return [e for e in self.events 
                if e.iv_percentile and e.iv_percentile >= iv_threshold
                and e.days_until >= 0]
    
    def get_underpriced_moves(self, ratio_threshold: float = 1.2) -> List[EarningsEvent]:
        """Find earnings where expected move < historical (potential straddle buys)."""
        return [e for e in self.events 
                if e.straddle_premium_ratio < ratio_threshold
                and e.days_until >= 0 and e.days_until <= 14]
    
    def get_overpriced_moves(self, ratio_threshold: float = 1.3) -> List[EarningsEvent]:
        """Find earnings where expected move > historical (potential straddle sells)."""
        return [e for e in self.events 
                if e.straddle_premium_ratio > ratio_threshold
                and e.days_until >= 0 and e.days_until <= 14]
    
    def get_calendar_df(self) -> pd.DataFrame:
        """Get all events as DataFrame."""
        return pd.DataFrame([e.to_dict() for e in self.events])


def create_earnings_calendar_chart(calendar: EarningsCalendar, days: int = 30) -> go.Figure:
    """Create visual earnings calendar."""
    upcoming = [e for e in calendar.events if 0 <= e.days_until <= days]
    
    if not upcoming:
        fig = go.Figure()
        fig.add_annotation(text="No upcoming earnings", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template='plotly_dark')
        return fig
    
    df = pd.DataFrame([e.to_dict() for e in upcoming])
    df['date'] = pd.to_datetime(df['date'])
    
    # Color by IV percentile
    fig = px.scatter(
        df,
        x='date',
        y='expected_move',
        size='options_volume',
        color='iv_percentile',
        hover_name='ticker',
        hover_data=['timing', 'avg_historical_move', 'straddle_ratio'],
        color_continuous_scale='RdYlGn_r',
        title='Upcoming Earnings Calendar'
    )
    
    # Add ticker labels
    fig.update_traces(
        textposition='top center',
        marker=dict(sizemin=5)
    )
    
    fig.update_layout(
        xaxis_title='Earnings Date',
        yaxis_title='Expected Move (%)',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.8)',
        height=450
    )
    
    return fig


def create_historical_moves_chart(event: EarningsEvent) -> go.Figure:
    """Create chart showing historical earnings moves."""
    if not event or not event.historical_moves:
        fig = go.Figure()
        fig.add_annotation(text="No historical data", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template='plotly_dark')
        return fig
    
    moves = event.historical_moves
    quarters = [f"Q{i+1}" for i in range(len(moves))]
    colors = ['#4CAF50' if m > 0 else '#f44336' for m in moves]
    
    fig = go.Figure()
    
    # Historical bars
    fig.add_trace(go.Bar(
        x=quarters,
        y=moves,
        marker_color=colors,
        name='Historical Move'
    ))
    
    # Expected move line
    fig.add_hline(y=event.expected_move, line_dash="dash", line_color="yellow",
                  annotation_text=f"Expected: ±{event.expected_move:.1f}%")
    fig.add_hline(y=-event.expected_move, line_dash="dash", line_color="yellow")
    
    # Average line
    avg = event.avg_historical_move
    fig.add_hline(y=avg, line_dash="dot", line_color="cyan",
                  annotation_text=f"Avg: ±{avg:.1f}%")
    fig.add_hline(y=-avg, line_dash="dot", line_color="cyan")
    
    fig.update_layout(
        title=f'{event.ticker} Historical Earnings Moves',
        xaxis_title='Quarter',
        yaxis_title='Move (%)',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.8)',
        height=350,
        showlegend=False
    )
    
    return fig


def create_straddle_analysis(event: EarningsEvent) -> Dict:
    """Analyze straddle opportunity for earnings."""
    if not event:
        return {}
    
    ratio = event.straddle_premium_ratio
    
    if ratio < 0.9:
        signal = 'STRONG BUY'
        signal_color = '#4CAF50'
        strategy = 'Long Straddle'
        rationale = f"Expected move ({event.expected_move:.1f}%) is significantly below " \
                   f"historical average ({event.avg_historical_move:.1f}%). Options appear underpriced."
    elif ratio < 1.1:
        signal = 'NEUTRAL'
        signal_color = '#FF9800'
        strategy = 'Avoid or Small Size'
        rationale = f"Expected move roughly matches historical. Fair pricing, no clear edge."
    elif ratio < 1.3:
        signal = 'SELL'
        signal_color = '#f44336'
        strategy = 'Short Straddle / Iron Butterfly'
        rationale = f"Expected move ({event.expected_move:.1f}%) exceeds historical average " \
                   f"({event.avg_historical_move:.1f}%). Options appear overpriced."
    else:
        signal = 'STRONG SELL'
        signal_color = '#f44336'
        strategy = 'Short Straddle / Iron Condor'
        rationale = f"Expected move significantly exceeds historical. " \
                   f"High probability of collecting premium."
    
    return {
        'ticker': event.ticker,
        'earnings_date': event.earnings_date.strftime('%Y-%m-%d'),
        'timing': event.timing,
        'days_until': event.days_until,
        'expected_move': event.expected_move,
        'historical_avg': event.avg_historical_move,
        'straddle_ratio': ratio,
        'signal': signal,
        'signal_color': signal_color,
        'suggested_strategy': strategy,
        'rationale': rationale,
        'iv_percentile': event.iv_percentile
    }


def create_weekly_calendar_view(calendar: EarningsCalendar) -> go.Figure:
    """Create weekly heatmap of earnings."""
    weeks = calendar.get_by_week()
    
    if not weeks:
        fig = go.Figure()
        fig.add_annotation(text="No upcoming earnings", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template='plotly_dark')
        return fig
    
    # Create heatmap data
    data = []
    for week_start, events in list(weeks.items())[:8]:  # Next 8 weeks
        for event in events:
            day = event.earnings_date.weekday()  # 0=Mon, 4=Fri
            data.append({
                'week': week_start,
                'day': day,
                'ticker': event.ticker,
                'expected_move': event.expected_move
            })
    
    df = pd.DataFrame(data)
    
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template='plotly_dark')
        return fig
    
    # Aggregate by week and day
    pivot = df.pivot_table(
        index='week',
        columns='day',
        values='expected_move',
        aggfunc='count'
    ).fillna(0)
    
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=[days[i] for i in pivot.columns],
        y=pivot.index,
        colorscale='Blues',
        colorbar=dict(title='# Earnings')
    ))
    
    fig.update_layout(
        title='Earnings Calendar Heatmap',
        xaxis_title='Day of Week',
        yaxis_title='Week Starting',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.8)',
        height=350
    )
    
    return fig


# Singleton instance
_calendar = None

def get_earnings_calendar() -> EarningsCalendar:
    """Get singleton earnings calendar instance."""
    global _calendar
    if _calendar is None:
        _calendar = EarningsCalendar()
    return _calendar
