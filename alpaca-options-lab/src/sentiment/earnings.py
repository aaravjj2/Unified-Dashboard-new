"""
Earnings Calendar & Event Impact Engine

Tracks earnings announcements, economic events, and estimates
impact on options trading strategies.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta, date
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class EventType(Enum):
    """Type of market event"""
    EARNINGS = "earnings"
    DIVIDEND = "dividend"
    SPLIT = "split"
    FOMC = "fomc"
    CPI = "cpi"
    JOBS_REPORT = "jobs_report"
    GDP = "gdp"
    RETAIL_SALES = "retail_sales"
    PMI = "pmi"
    OTHER = "other"


class EventTiming(Enum):
    """When the event occurs relative to market hours"""
    PRE_MARKET = "pre_market"
    DURING_MARKET = "during_market"
    POST_MARKET = "post_market"
    UNKNOWN = "unknown"


@dataclass
class EarningsEvent:
    """Earnings announcement event"""
    symbol: str
    event_date: date
    timing: EventTiming
    fiscal_quarter: str
    fiscal_year: int
    
    # Estimates
    eps_estimate: Optional[float] = None
    revenue_estimate: Optional[float] = None
    
    # Historical
    eps_actual: Optional[float] = None
    revenue_actual: Optional[float] = None
    eps_surprise: Optional[float] = None
    revenue_surprise: Optional[float] = None
    
    # Implied move
    implied_move: Optional[float] = None
    historical_avg_move: Optional[float] = None
    
    # Options data
    straddle_price: Optional[float] = None
    iv_rank: Optional[float] = None
    
    confirmed: bool = False


@dataclass
class EconomicEvent:
    """Economic calendar event"""
    event_type: EventType
    event_date: datetime
    name: str
    importance: str  # low, medium, high
    
    # Forecasts
    forecast: Optional[float] = None
    previous: Optional[float] = None
    actual: Optional[float] = None
    
    # Impact
    market_impact: Optional[str] = None  # bullish, bearish, neutral
    affected_symbols: List[str] = field(default_factory=list)


@dataclass
class EventImpactEstimate:
    """Estimated impact of an event on options"""
    symbol: str
    event: EarningsEvent
    
    # IV impact
    pre_event_iv: float
    expected_post_iv: float
    iv_crush_estimate: float
    
    # Move estimates
    implied_move_1std: float
    implied_move_2std: float
    
    # Strategy recommendations
    recommended_strategies: List[str]
    avoid_strategies: List[str]
    
    # Risk assessment
    risk_score: float  # 1-10
    opportunity_score: float  # 1-10


class EarningsCalendar:
    """
    Manages earnings calendar and provides earnings-related analytics.
    """
    
    def __init__(self):
        self.earnings: Dict[str, List[EarningsEvent]] = {}
        self.economic_events: List[EconomicEvent] = []
        self._last_update: Optional[datetime] = None
        
    async def fetch_earnings_calendar(
        self,
        symbols: Optional[List[str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[EarningsEvent]:
        """
        Fetch earnings calendar from data provider.
        """
        if start_date is None:
            start_date = date.today()
        if end_date is None:
            end_date = start_date + timedelta(days=30)
            
        # Mock data - replace with actual API call
        events = self._generate_mock_earnings(symbols, start_date, end_date)
        
        # Update cache
        for event in events:
            if event.symbol not in self.earnings:
                self.earnings[event.symbol] = []
            self.earnings[event.symbol].append(event)
            
        self._last_update = datetime.now(timezone.utc)
        
        return events
        
    async def fetch_economic_calendar(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[EconomicEvent]:
        """
        Fetch economic calendar events.
        """
        if start_date is None:
            start_date = date.today()
        if end_date is None:
            end_date = start_date + timedelta(days=14)
            
        # Mock data - replace with actual API
        events = self._generate_mock_economic_events(start_date, end_date)
        self.economic_events = events
        
        return events
        
    def _generate_mock_earnings(
        self,
        symbols: Optional[List[str]],
        start_date: date,
        end_date: date,
    ) -> List[EarningsEvent]:
        """Generate mock earnings data"""
        if symbols is None:
            symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA"]
            
        events = []
        for i, symbol in enumerate(symbols):
            event_date = start_date + timedelta(days=(i * 5) % 30)
            if event_date > end_date:
                continue
                
            events.append(EarningsEvent(
                symbol=symbol,
                event_date=event_date,
                timing=EventTiming.POST_MARKET if i % 2 == 0 else EventTiming.PRE_MARKET,
                fiscal_quarter=f"Q{((date.today().month - 1) // 3) + 1}",
                fiscal_year=date.today().year,
                eps_estimate=2.50 + i * 0.1,
                revenue_estimate=50.0 + i * 5.0,
                implied_move=0.05 + i * 0.005,
                historical_avg_move=0.045 + i * 0.003,
                straddle_price=8.50 + i * 0.5,
                iv_rank=65.0 + i * 3,
                confirmed=True,
            ))
            
        return events
        
    def _generate_mock_economic_events(
        self,
        start_date: date,
        end_date: date,
    ) -> List[EconomicEvent]:
        """Generate mock economic events"""
        events = [
            EconomicEvent(
                event_type=EventType.FOMC,
                event_date=datetime.combine(start_date + timedelta(days=5), datetime.min.time()),
                name="FOMC Rate Decision",
                importance="high",
                forecast=5.25,
                previous=5.25,
                affected_symbols=["SPY", "QQQ", "TLT", "GLD"],
            ),
            EconomicEvent(
                event_type=EventType.CPI,
                event_date=datetime.combine(start_date + timedelta(days=10), datetime.min.time()),
                name="CPI (MoM)",
                importance="high",
                forecast=0.3,
                previous=0.4,
                affected_symbols=["SPY", "TLT"],
            ),
            EconomicEvent(
                event_type=EventType.JOBS_REPORT,
                event_date=datetime.combine(start_date + timedelta(days=3), datetime.min.time()),
                name="Non-Farm Payrolls",
                importance="high",
                forecast=180000,
                previous=199000,
                affected_symbols=["SPY", "IWM"],
            ),
        ]
        
        return [e for e in events if start_date <= e.event_date.date() <= end_date]
        
    def get_upcoming_earnings(
        self,
        symbol: str,
        days_ahead: int = 30,
    ) -> Optional[EarningsEvent]:
        """
        Get the next upcoming earnings event for a symbol.
        """
        if symbol not in self.earnings:
            return None
            
        today = date.today()
        cutoff = today + timedelta(days=days_ahead)
        
        for event in sorted(self.earnings[symbol], key=lambda x: x.event_date):
            if today <= event.event_date <= cutoff:
                return event
                
        return None
        
    def get_earnings_this_week(self) -> List[EarningsEvent]:
        """
        Get all earnings events for the current week.
        """
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        events = []
        for symbol_events in self.earnings.values():
            for event in symbol_events:
                if week_start <= event.event_date <= week_end:
                    events.append(event)
                    
        return sorted(events, key=lambda x: x.event_date)
        
    def has_earnings_within(self, symbol: str, days: int) -> bool:
        """
        Check if symbol has earnings within specified days.
        """
        event = self.get_upcoming_earnings(symbol, days)
        return event is not None


class EventImpactAnalyzer:
    """
    Analyzes the impact of events on options strategies.
    """
    
    def __init__(self, calendar: EarningsCalendar):
        self.calendar = calendar
        
        # Historical move data for calibration
        self.historical_moves: Dict[str, List[float]] = {}
        
    def estimate_earnings_impact(
        self,
        symbol: str,
        current_iv: float,
        current_price: float,
    ) -> Optional[EventImpactEstimate]:
        """
        Estimate the impact of upcoming earnings on options.
        """
        event = self.calendar.get_upcoming_earnings(symbol)
        if event is None:
            return None
            
        # Estimate IV crush
        # Typically IV drops 30-50% after earnings
        iv_crush_pct = 0.40  # 40% average crush
        expected_post_iv = current_iv * (1 - iv_crush_pct)
        
        # Calculate implied move from straddle
        if event.implied_move:
            implied_move = event.implied_move
        else:
            # Approximate from IV
            # ATM straddle implies ~0.8 * sigma move
            days_to_event = (event.event_date - date.today()).days
            implied_move = current_iv * np.sqrt(days_to_event / 365) * 0.8
            
        # Strategy recommendations
        if implied_move > event.historical_avg_move * 1.2 if event.historical_avg_move else 0.05:
            # IV seems expensive
            recommended = ["iron_condor", "iron_butterfly", "short_straddle"]
            avoid = ["long_straddle", "long_strangle"]
            opportunity = 7.0
        elif implied_move < event.historical_avg_move * 0.8 if event.historical_avg_move else 0.03:
            # IV seems cheap
            recommended = ["long_straddle", "long_strangle", "calendar_spread"]
            avoid = ["iron_condor", "short_straddle"]
            opportunity = 6.0
        else:
            recommended = ["diagonal_spread", "calendar_spread"]
            avoid = []
            opportunity = 5.0
            
        # Risk score based on historical volatility and IV rank
        risk = min(10, max(1, (event.iv_rank or 50) / 10))
        
        return EventImpactEstimate(
            symbol=symbol,
            event=event,
            pre_event_iv=current_iv,
            expected_post_iv=expected_post_iv,
            iv_crush_estimate=iv_crush_pct,
            implied_move_1std=implied_move,
            implied_move_2std=implied_move * 2,
            recommended_strategies=recommended,
            avoid_strategies=avoid,
            risk_score=risk,
            opportunity_score=opportunity,
        )
        
    def get_event_trade_adjustments(
        self,
        symbol: str,
        current_position_type: str,
    ) -> Dict:
        """
        Get recommended adjustments for positions with upcoming events.
        """
        event = self.calendar.get_upcoming_earnings(symbol)
        if event is None:
            return {"action": "none", "reason": "No upcoming events"}
            
        days_to_event = (event.event_date - date.today()).days
        
        # Position-specific recommendations
        if current_position_type in ["short_put", "put_credit_spread"]:
            if days_to_event <= 7:
                return {
                    "action": "close_or_hedge",
                    "reason": "Short premium vulnerable to earnings gap",
                    "urgency": "high",
                    "alternatives": ["close position", "add long put protection"],
                }
            elif days_to_event <= 14:
                return {
                    "action": "monitor",
                    "reason": "Earnings approaching - consider closing",
                    "urgency": "medium",
                }
                
        elif current_position_type in ["covered_call", "call_credit_spread"]:
            if days_to_event <= 7:
                return {
                    "action": "close_or_adjust",
                    "reason": "Capped upside risk if earnings surprise",
                    "urgency": "medium",
                    "alternatives": ["close position", "roll to wider spread"],
                }
                
        elif current_position_type in ["iron_condor", "iron_butterfly"]:
            if days_to_event <= 3:
                return {
                    "action": "close",
                    "reason": "Binary event risk - close before earnings",
                    "urgency": "high",
                }
            elif days_to_event <= 7:
                return {
                    "action": "hedge_or_close",
                    "reason": "Consider closing before IV crush",
                    "urgency": "medium",
                    "alternatives": ["close for profit", "widen wings"],
                }
                
        return {
            "action": "monitor",
            "reason": f"Earnings in {days_to_event} days",
            "urgency": "low",
        }
        
    def get_earnings_play_opportunities(
        self,
        watchlist: List[str],
    ) -> List[Dict]:
        """
        Find earnings trading opportunities from watchlist.
        """
        opportunities = []
        
        for symbol in watchlist:
            event = self.calendar.get_upcoming_earnings(symbol)
            if event is None:
                continue
                
            days_to_event = (event.event_date - date.today()).days
            
            # Only interested in 3-14 day window
            if not (3 <= days_to_event <= 14):
                continue
                
            # Calculate opportunity score
            iv_rank = event.iv_rank or 50
            implied_move = event.implied_move or 0.05
            historical_move = event.historical_avg_move or 0.04
            
            # High IV rank + implied > historical = good for selling
            if iv_rank > 60 and implied_move > historical_move * 1.1:
                opportunities.append({
                    "symbol": symbol,
                    "event_date": event.event_date.isoformat(),
                    "days_to_event": days_to_event,
                    "opportunity_type": "sell_premium",
                    "strategy": "iron_condor" if days_to_event > 7 else "iron_butterfly",
                    "iv_rank": iv_rank,
                    "implied_move": implied_move,
                    "historical_move": historical_move,
                    "edge": implied_move - historical_move,
                    "score": min(10, iv_rank / 10 + (implied_move / historical_move) * 2),
                })
                
            # Low IV rank + implied < historical = good for buying
            elif iv_rank < 40 and implied_move < historical_move * 0.9:
                opportunities.append({
                    "symbol": symbol,
                    "event_date": event.event_date.isoformat(),
                    "days_to_event": days_to_event,
                    "opportunity_type": "buy_premium",
                    "strategy": "long_straddle" if days_to_event <= 5 else "calendar_spread",
                    "iv_rank": iv_rank,
                    "implied_move": implied_move,
                    "historical_move": historical_move,
                    "edge": historical_move - implied_move,
                    "score": min(10, (100 - iv_rank) / 10 + (historical_move / implied_move) * 2),
                })
                
        return sorted(opportunities, key=lambda x: x["score"], reverse=True)


# Module instances
earnings_calendar = EarningsCalendar()
event_impact_analyzer = EventImpactAnalyzer(earnings_calendar)
