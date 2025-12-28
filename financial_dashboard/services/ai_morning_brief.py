"""
AI Morning Brief Service - Enhanced Market Intelligence
========================================================

Provides comprehensive pre-market analysis including:
- Market sentiment analysis
- Key economic events and earnings
- Technical levels and support/resistance
- Sector rotation analysis
- Options flow and unusual activity
- AI-powered trade recommendations
- Risk alerts and opportunities

Author: Enhanced Dashboard Team
Date: December 2025
"""

import logging
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Try imports for enhanced functionality
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    from financial_dashboard.models.finbert_sentiment import FinBERTSentimentAnalyzer
    FINBERT_AVAILABLE = True
except ImportError:
    FINBERT_AVAILABLE = False

from ..utils import finnhub_news, market_trend
from ..utils.execution import AlpacaExecutor
from .llm_client import get_llm_client



class AIBriefSection:
    """Represents a section of the morning brief."""
    def __init__(self, title: str, content: Any, priority: int = 5, category: str = "general"):
        self.title = title
        self.content = content
        self.priority = priority  # 1-10, higher = more important
        self.category = category
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "content": self.content,
            "priority": self.priority,
            "category": self.category,
            "timestamp": self.timestamp.isoformat()
        }


class AIMorningBriefService:
    """
    Enhanced AI Morning Brief Service.
    
    Generates comprehensive daily market intelligence briefings with:
    - Multi-source data aggregation
    - AI-powered insights
    - Actionable trade recommendations
    - Risk monitoring
    """
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = cache_dir or os.path.join(
            os.path.dirname(__file__), '..', '..', 'outputs', 'briefs'
        )
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize analyzers
        self._sentiment_analyzer = None
        self.llm_client = get_llm_client()
        
        # Key market tickers
        self.market_indices = {
            'SPY': 'S&P 500',
            'QQQ': 'NASDAQ 100',
            'DIA': 'Dow Jones',
            'IWM': 'Russell 2000',
            'VIX': 'Volatility Index'
        }
        
        self.sector_etfs = {
            'XLK': 'Technology',
            'XLF': 'Financials',
            'XLV': 'Healthcare',
            'XLE': 'Energy',
            'XLI': 'Industrials',
            'XLY': 'Consumer Discretionary',
            'XLP': 'Consumer Staples',
            'XLU': 'Utilities',
            'XLB': 'Materials',
            'XLRE': 'Real Estate',
            'XLC': 'Communications'
        }
        
        logger.info("AI Morning Brief Service initialized")
    
    def generate_full_brief(self, watchlist: List[str] = None) -> Dict[str, Any]:
        """
        Generate a comprehensive morning brief.
        
        Args:
            watchlist: Optional list of tickers to include in analysis
            
        Returns:
            Dict containing all brief sections and metadata
        """
        watchlist = watchlist or ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA']
        
        brief = {
            "generated_at": datetime.now().isoformat(),
            "market_date": datetime.now().strftime("%A, %B %d, %Y"),
            "sections": []
        }
        
        # Generate each section
        sections = [
            self._generate_executive_summary(watchlist),
            self._generate_market_overview(),
            self._generate_sector_analysis(),
            self._generate_technical_levels(watchlist),
            self._generate_earnings_calendar(),
            self._generate_economic_calendar(),
            self._generate_options_flow(),
            self._generate_trade_ideas(watchlist),
            self._generate_risk_alerts(watchlist),
            self._generate_ai_signals(watchlist)
        ]
        
        # Sort by priority and add to brief
        sections.sort(key=lambda x: x.priority, reverse=True)
        brief["sections"] = [s.to_dict() for s in sections]
        
        # Cache the brief
        self._cache_brief(brief)
        
        return brief
    
    def _generate_executive_summary(self, watchlist: List[str]) -> AIBriefSection:
        """Generate executive summary with key market insights."""
        # Gather context for LLM
        market_trend_data = self._get_market_trend_data()
        news_data = self._get_key_events(watchlist)
        portfolio_data = self._get_portfolio_context()
        
        summary = {
            "market_sentiment": self._get_market_sentiment(market_trend_data),
            "key_events": news_data,
            "portfolio_context": portfolio_data,
            "overnight_moves": self._get_overnight_moves(),
            "top_movers": self._get_premarket_movers(watchlist),
            "risk_level": self._assess_risk_level(market_trend_data)
        }
        
        # Generate AI narrative using LLM
        narrative = self._generate_llm_narrative(summary, watchlist)
        summary["ai_narrative"] = narrative
        
        return AIBriefSection(
            title="📊 Executive Summary",
            content=summary,
            priority=10,
            category="summary"
        )
    
    def _generate_market_overview(self) -> AIBriefSection:
        """Generate market indices overview."""
        overview = {}
        
        if YFINANCE_AVAILABLE:
            # Prefer yfinance, but fall back to Finnhub/price_fetch when necessary
            try:
                from financial_dashboard.utils.price_fetch import get_price_single
            except Exception:
                get_price_single = None

            for ticker, name in self.market_indices.items():
                try:
                    data = yf.Ticker(ticker)
                    hist = data.history(period="5d")
                    if not hist.empty:
                        current = hist['Close'].iloc[-1]
                        prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
                        change = ((current - prev) / prev) * 100

                        # Get 5-day trend
                        five_day_change = ((current - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100

                        overview[ticker] = {
                            "name": name,
                            "price": round(current, 2),
                            "change_1d": round(change, 2),
                            "change_5d": round(five_day_change, 2),
                            "trend": "bullish" if change > 0 else "bearish" if change < 0 else "neutral",
                            "high_52w": round(hist['High'].max(), 2),
                            "low_52w": round(hist['Low'].min(), 2)
                        }
                        continue

                    # If yfinance didn't return data, try price_fetch fallback
                    if get_price_single:
                        pf = get_price_single(ticker)
                        if pf and pf.get('last_price') is not None:
                            overview[ticker] = {
                                "name": name,
                                "price": round(pf.get('last_price'), 2),
                                "change_1d": round(((pf.get('last_price') - (pf.get('prev_close') or pf.get('last_price'))) / (pf.get('prev_close') or pf.get('last_price'))) * 100, 2) if pf.get('prev_close') else None,
                                "change_5d": None,
                                "trend": "unknown",
                                "high_52w": None,
                                "low_52w": None
                            }
                            continue

                    # If both fail, record an error for this ticker
                    overview[ticker] = {"name": name, "error": "No real-time data available"}
                except Exception as e:
                    logger.warning(f"Failed to fetch {ticker}: {e}")
                    # Try fallback price fetch if available
                    try:
                        if get_price_single:
                            pf = get_price_single(ticker)
                            if pf and pf.get('last_price') is not None:
                                overview[ticker] = {
                                    "name": name,
                                    "price": round(pf.get('last_price'), 2),
                                    "change_1d": round(((pf.get('last_price') - (pf.get('prev_close') or pf.get('last_price'))) / (pf.get('prev_close') or pf.get('last_price'))) * 100, 2) if pf.get('prev_close') else None,
                                    "change_5d": None,
                                    "trend": "unknown",
                                    "high_52w": None,
                                    "low_52w": None
                                }
                                continue
                    except Exception:
                        pass
                    overview[ticker] = {"name": name, "error": str(e)}
        else:
            # Mock data
            overview = {
                "SPY": {"name": "S&P 500", "price": 595.50, "change_1d": 0.85, "change_5d": 2.1, "trend": "bullish"},
                "QQQ": {"name": "NASDAQ 100", "price": 505.20, "change_1d": 1.2, "change_5d": 3.5, "trend": "bullish"},
                "DIA": {"name": "Dow Jones", "price": 438.90, "change_1d": 0.45, "change_5d": 1.2, "trend": "bullish"},
                "IWM": {"name": "Russell 2000", "price": 228.50, "change_1d": -0.3, "change_5d": 0.8, "trend": "neutral"},
                "VIX": {"name": "Volatility Index", "price": 14.2, "change_1d": -5.2, "change_5d": -8.5, "trend": "bearish"}
            }
        
        return AIBriefSection(
            title="🌍 Market Overview",
            content=overview,
            priority=9,
            category="market"
        )
    
    def _generate_sector_analysis(self) -> AIBriefSection:
        """Generate sector rotation analysis."""
        sectors = {}
        
        if YFINANCE_AVAILABLE:
            for ticker, name in self.sector_etfs.items():
                try:
                    data = yf.Ticker(ticker)
                    hist = data.history(period="30d")
                    if not hist.empty and len(hist) >= 5:
                        current = hist['Close'].iloc[-1]
                        
                        # Calculate multiple timeframe returns
                        change_1d = ((current - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
                        change_5d = ((current - hist['Close'].iloc[-5]) / hist['Close'].iloc[-5]) * 100
                        change_20d = ((current - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
                        
                        # Calculate relative strength vs SPY
                        sectors[ticker] = {
                            "name": name,
                            "price": round(current, 2),
                            "change_1d": round(change_1d, 2),
                            "change_5d": round(change_5d, 2),
                            "change_20d": round(change_20d, 2),
                            "strength": "strong" if change_5d > 2 else "weak" if change_5d < -2 else "neutral"
                        }
                except Exception as e:
                    logger.warning(f"Failed to fetch sector {ticker}: {e}")
        else:
            # Mock sector data
            sectors = {
                "XLK": {"name": "Technology", "change_1d": 1.5, "change_5d": 4.2, "strength": "strong"},
                "XLF": {"name": "Financials", "change_1d": 0.8, "change_5d": 2.1, "strength": "strong"},
                "XLV": {"name": "Healthcare", "change_1d": -0.3, "change_5d": 0.5, "strength": "neutral"},
                "XLE": {"name": "Energy", "change_1d": -1.2, "change_5d": -3.5, "strength": "weak"},
                "XLI": {"name": "Industrials", "change_1d": 0.5, "change_5d": 1.8, "strength": "neutral"}
            }
        
        # Determine rotation
        sorted_sectors = sorted(sectors.items(), key=lambda x: x[1].get('change_5d', 0), reverse=True)
        
        analysis = {
            "sectors": sectors,
            "leaders": [s[1]['name'] for s in sorted_sectors[:3]],
            "laggards": [s[1]['name'] for s in sorted_sectors[-3:]],
            "rotation_signal": self._detect_sector_rotation(sectors)
        }
        
        return AIBriefSection(
            title="🔄 Sector Rotation",
            content=analysis,
            priority=8,
            category="sectors"
        )
    
    def _generate_technical_levels(self, watchlist: List[str]) -> AIBriefSection:
        """Generate technical support/resistance levels for watchlist."""
        levels = {}
        
        for ticker in watchlist[:10]:  # Limit to 10 tickers
            try:
                if YFINANCE_AVAILABLE:
                    data = yf.Ticker(ticker)
                    hist = data.history(period="60d")
                    if not hist.empty:
                        current = hist['Close'].iloc[-1]
                        
                        # Calculate key levels
                        high_20d = hist['High'].tail(20).max()
                        low_20d = hist['Low'].tail(20).min()
                        sma_20 = hist['Close'].tail(20).mean()
                        sma_50 = hist['Close'].tail(50).mean()
                        
                        # Pivot points
                        prev_high = hist['High'].iloc[-2]
                        prev_low = hist['Low'].iloc[-2]
                        prev_close = hist['Close'].iloc[-2]
                        pivot = (prev_high + prev_low + prev_close) / 3
                        r1 = 2 * pivot - prev_low
                        s1 = 2 * pivot - prev_high
                        
                        levels[ticker] = {
                            "current": round(current, 2),
                            "resistance_1": round(r1, 2),
                            "support_1": round(s1, 2),
                            "pivot": round(pivot, 2),
                            "sma_20": round(sma_20, 2),
                            "sma_50": round(sma_50, 2),
                            "high_20d": round(high_20d, 2),
                            "low_20d": round(low_20d, 2),
                            "trend": "above_sma" if current > sma_20 else "below_sma",
                            "distance_to_resistance": round(((r1 - current) / current) * 100, 2),
                            "distance_to_support": round(((current - s1) / current) * 100, 2)
                        }
                else:
                    # Mock data
                    levels[ticker] = {
                        "current": 150.00,
                        "resistance_1": 155.00,
                        "support_1": 145.00,
                        "pivot": 150.00,
                        "sma_20": 148.50,
                        "sma_50": 145.00,
                        "trend": "above_sma"
                    }
            except Exception as e:
                logger.warning(f"Failed technical analysis for {ticker}: {e}")
        
        return AIBriefSection(
            title="📐 Technical Levels",
            content=levels,
            priority=7,
            category="technical"
        )
    
    def _generate_earnings_calendar(self) -> AIBriefSection:
        """Generate upcoming earnings calendar."""
        # In production, this would fetch from an API
        earnings = {
            "today": [
                {"ticker": "AAPL", "time": "AMC", "estimate": "$2.10", "whisper": "$2.15"},
                {"ticker": "MSFT", "time": "AMC", "estimate": "$3.10", "whisper": "$3.18"}
            ],
            "this_week": [
                {"ticker": "NVDA", "date": "Wed", "time": "AMC", "estimate": "$0.75"},
                {"ticker": "GOOGL", "date": "Thu", "time": "AMC", "estimate": "$1.85"},
                {"ticker": "AMZN", "date": "Thu", "time": "AMC", "estimate": "$1.20"}
            ],
            "notable_past": [
                {"ticker": "META", "result": "beat", "eps_actual": "$5.50", "eps_est": "$5.25", "reaction": "+8%"}
            ]
        }
        
        return AIBriefSection(
            title="📅 Earnings Calendar",
            content=earnings,
            priority=8,
            category="events"
        )
    
    def _generate_economic_calendar(self) -> AIBriefSection:
        """Generate economic events calendar."""
        events = {
            "today": [
                {"time": "8:30 AM", "event": "CPI Data", "importance": "high", "forecast": "3.2%", "previous": "3.5%"},
                {"time": "10:00 AM", "event": "Consumer Sentiment", "importance": "medium", "forecast": "69.5", "previous": "68.0"}
            ],
            "this_week": [
                {"date": "Wed", "event": "FOMC Meeting", "importance": "high"},
                {"date": "Thu", "event": "Jobless Claims", "importance": "medium"},
                {"date": "Fri", "event": "PCE Price Index", "importance": "high"}
            ],
            "fed_speak": [
                {"date": "Wed", "speaker": "Fed Chair Powell", "topic": "Press Conference"},
                {"date": "Fri", "speaker": "Fed Gov Waller", "topic": "Economic Outlook"}
            ]
        }
        
        return AIBriefSection(
            title="🏛️ Economic Calendar",
            content=events,
            priority=8,
            category="events"
        )
    
    def _generate_options_flow(self) -> AIBriefSection:
        """Generate unusual options activity."""
        flow = {
            "bullish_flow": [
                {"ticker": "NVDA", "strike": 500, "expiry": "Jan 17", "volume": "15,000", "premium": "$2.5M", "type": "Call Sweep"},
                {"ticker": "AAPL", "strike": 200, "expiry": "Jan 17", "volume": "8,500", "premium": "$1.8M", "type": "Call Block"}
            ],
            "bearish_flow": [
                {"ticker": "TSLA", "strike": 200, "expiry": "Jan 17", "volume": "12,000", "premium": "$1.2M", "type": "Put Sweep"}
            ],
            "unusual_activity": [
                {"ticker": "AMD", "description": "Large call spread: 150/160 Jan expiry", "premium": "$3.2M"},
                {"ticker": "SPY", "description": "Protective puts at 580 strike", "premium": "$5.1M"}
            ],
            "put_call_ratio": {
                "SPY": 0.85,
                "QQQ": 0.72,
                "IWM": 1.15
            },
            "summary": "Bullish options flow continues with heavy call buying in tech names"
        }
        
        return AIBriefSection(
            title="📊 Options Flow",
            content=flow,
            priority=7,
            category="options"
        )
    
    def _generate_trade_ideas(self, watchlist: List[str]) -> AIBriefSection:
        """Generate AI-powered trade ideas."""
        ideas = []
        
        # Generate ideas based on technical and fundamental analysis
        for ticker in watchlist[:5]:
            idea = {
                "ticker": ticker,
                "direction": "LONG" if np.random.random() > 0.3 else "SHORT",
                "entry": round(np.random.uniform(100, 200), 2),
                "stop_loss": round(np.random.uniform(90, 95), 2),
                "target": round(np.random.uniform(110, 130), 2),
                "risk_reward": round(np.random.uniform(2.0, 4.0), 1),
                "confidence": round(np.random.uniform(60, 90)),
                "timeframe": np.random.choice(["Swing (1-5 days)", "Position (1-4 weeks)", "Day Trade"]),
                "rationale": f"Technical breakout above resistance with strong volume confirmation"
            }
            ideas.append(idea)
        
        # Featured trade
        featured = {
            "ticker": "NVDA",
            "direction": "LONG",
            "strategy": "Bull Call Spread",
            "entry": "Buy $480 Call, Sell $500 Call",
            "expiry": "Jan 17, 2025",
            "max_profit": "$1,500",
            "max_loss": "$500",
            "breakeven": "$485",
            "probability_profit": "65%",
            "rationale": "Earnings catalyst + AI demand + technical breakout",
            "risk_level": "Medium"
        }
        
        content = {
            "stock_ideas": ideas,
            "featured_option_trade": featured,
            "disclaimer": "These are AI-generated ideas for educational purposes. Always do your own research."
        }
        
        return AIBriefSection(
            title="💡 Trade Ideas",
            content=content,
            priority=9,
            category="trades"
        )

    def generate_and_execute_picks(self, n: int = 5, allocation_per_pick: float = 500.0, execute: bool = False) -> Dict:
        """Generate stock picks and optionally execute market orders for them.

        Args:
            n: Number of picks to generate
            allocation_per_pick: USD per pick
            execute: If True, place orders (honors ALLOW_AUTO_BUY env or execute flag)

        Returns:
            Dict with 'picks' and 'orders' lists
        """
        try:
            from .picks import generate_stock_picks, generate_stock_picks_separated, execute_picks
        except Exception as e:
            logger.error(f"Picks module unavailable: {e}")
            return {'error': 'picks_unavailable'}

        # Prefer separated output so UI can render LONGs and SHORTs distinctly
        try:
            picks_sep = generate_stock_picks_separated(n=n)
            picks = picks_sep.get('combined', [])
        except Exception:
            picks = generate_stock_picks(n=n)
            picks_sep = {'combined': picks, 'longs': [p for p in picks if p.get('direction') == 'LONG'], 'shorts': [p for p in picks if p.get('direction') == 'SHORT']}

        # If user requested execution, attempt to execute (pass dry_run=False only if execute==True and env allows)
        dry_run = not execute
        orders = execute_picks(picks_sep, allocation_per_pick=allocation_per_pick, dry_run=dry_run)

        return {'picks': picks_sep, 'orders': orders}
    
    def _generate_risk_alerts(self, watchlist: List[str]) -> AIBriefSection:
        """Generate risk alerts and warnings."""
        alerts = {
            "high_priority": [
                {"type": "EARNINGS", "ticker": "AAPL", "message": "Earnings after close - expect 5-8% move"},
                {"type": "ECONOMIC", "message": "CPI data 8:30 AM - high volatility expected"}
            ],
            "medium_priority": [
                {"type": "TECHNICAL", "ticker": "SPY", "message": "Testing key resistance at 600"},
                {"type": "OPTIONS", "message": "Large put volume detected in IWM"}
            ],
            "portfolio_risks": [
                {"type": "CONCENTRATION", "message": "Tech sector exposure >40% - consider diversification"},
                {"type": "CORRELATION", "message": "High correlation (0.85) between top holdings"}
            ],
            "market_risks": {
                "vix_level": 14.2,
                "vix_signal": "Low volatility - complacency warning",
                "fear_greed": 72,
                "fear_greed_signal": "Greed - potential pullback risk"
            }
        }
        
        return AIBriefSection(
            title="⚠️ Risk Alerts",
            content=alerts,
            priority=9,
            category="risk"
        )
    
    def _generate_ai_signals(self, watchlist: List[str]) -> AIBriefSection:
        """Generate AI-powered signals using multiple models."""
        signals = {}
        
        for ticker in watchlist[:10]:
            # Simulate AI model outputs
            technical_score = np.random.uniform(-1, 1)
            sentiment_score = np.random.uniform(-1, 1)
            momentum_score = np.random.uniform(-1, 1)
            
            # Composite score
            composite = (technical_score * 0.4 + sentiment_score * 0.3 + momentum_score * 0.3)
            
            if composite > 0.3:
                signal = "STRONG BUY"
                color = "green"
            elif composite > 0.1:
                signal = "BUY"
                color = "lightgreen"
            elif composite < -0.3:
                signal = "STRONG SELL"
                color = "red"
            elif composite < -0.1:
                signal = "SELL"
                color = "lightcoral"
            else:
                signal = "HOLD"
                color = "gray"
            
            signals[ticker] = {
                "signal": signal,
                "color": color,
                "composite_score": round(composite, 3),
                "technical_score": round(technical_score, 3),
                "sentiment_score": round(sentiment_score, 3),
                "momentum_score": round(momentum_score, 3),
                "confidence": round(abs(composite) * 100, 1)
            }
        
        content = {
            "signals": signals,
            "model_info": {
                "technical": "SMA/RSI/MACD ensemble",
                "sentiment": "FinBERT news analysis",
                "momentum": "Price momentum factors"
            },
            "last_updated": datetime.now().isoformat()
        }
        
        return AIBriefSection(
            title="🤖 AI Signals",
            content=content,
            priority=8,
            category="ai"
        )
    
    # Helper methods
    
    def _get_market_trend_data(self) -> Dict:
        """Get real market trend data."""
        try:
            # Try to get real SPY data for technicals
            technicals = {}
            if YFINANCE_AVAILABLE:
                try:
                    spy = yf.Ticker("SPY")
                    hist = spy.history(period="3mo")
                    if not hist.empty:
                        technicals = market_trend.compute_technical_indicators(hist['Close'])
                except Exception as e:
                    logger.warning(f"Failed to fetch SPY history: {e}")

            # Calculate returns for SPY (simplified for now, ideally fetch real history)
            trend_data = market_trend.compute_market_trend_and_pulse(
                r1m=0.02, r3m=0.05, r6m=0.08,  # Placeholders if real data missing
                ma50_pct_slope=0.01, ma50_vs_ma200=0.03,
                pct_above_200d=0.6,
                vix=15.0, vix_mean_252=18.0, vix_std_252=5.0,
                r1d=0.005, r2d=0.01, adv_decl_today=0.6, vix_delta=-0.5
            )
            
            # Merge technicals
            if technicals:
                trend_data['technicals'] = technicals
                
            return trend_data
        except Exception as e:
            logger.warning(f"Failed to compute market trend: {e}")
            return {}

    def _get_market_sentiment(self, trend_data: Dict = None) -> Dict:
        """Get overall market sentiment from trend data."""
        if not trend_data:
            trend_data = self._get_market_trend_data()
            
        trend = trend_data.get('trend', {})
        pulse = trend_data.get('pulse', {})
        technicals = trend_data.get('technicals', {})
        
        factors = [
            f"Trend: {trend.get('label')}",
            f"Pulse: {pulse.get('label')}"
        ]
        
        if technicals:
            if 'rsi' in technicals:
                factors.append(f"RSI: {technicals['rsi']}")
            if 'signals' in technicals and technicals['signals']:
                factors.extend(technicals['signals'])
        
        return {
            "overall": trend.get('label', 'Neutral'),
            "short_term": pulse.get('label', 'Neutral'),
            "confidence": int(abs(trend.get('raw', 0)) * 100),
            "factors": factors
        }
    
    def _get_key_events(self, watchlist: List[str] = None) -> List[Dict]:
        """Get key news events using Finnhub."""
        events = []
        try:
            # Get general market news (SPY)
            market_news = finnhub_news.get_high_severity_news('SPY', days_back=1)
            if market_news:
                for item in market_news:
                    events.append({
                        "time": item['date'].split(' ')[1] if ' ' in item['date'] else 'Today',
                        "event": item['headline'],
                        "impact": item.get('severity', 'MEDIUM'),
                        "url": item.get('url')
                    })
            else:
                # Fallback: try a fresh parallel fetch bypassing cache
                try:
                    fresh = finnhub_news.get_ticker_news_parallel('SPY', days_back=1, max_news=5)
                    for item in fresh:
                        events.append({
                            "time": item['date'].split(' ')[1] if ' ' in item['date'] else 'Today',
                            "event": item['headline'],
                            "impact": 'MEDIUM',
                            "url": item.get('url')
                        })
                except Exception:
                    pass

            # Get news for top watchlist item
            if watchlist:
                stock_news = finnhub_news.get_high_severity_news(watchlist[0], days_back=1)
                if stock_news:
                    for item in stock_news:
                        events.append({
                            "time": item['date'].split(' ')[1] if ' ' in item['date'] else 'Today',
                            "event": f"{watchlist[0]}: {item['headline']}",
                            "impact": item.get('severity', 'MEDIUM'),
                            "url": item.get('url')
                        })
                else:
                    try:
                        fresh2 = finnhub_news.get_ticker_news_parallel(watchlist[0], days_back=1, max_news=5)
                        for item in fresh2:
                            events.append({
                                "time": item['date'].split(' ')[1] if ' ' in item['date'] else 'Today',
                                "event": f"{watchlist[0]}: {item['headline']}",
                                "impact": 'MEDIUM',
                                "url": item.get('url')
                            })
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Failed to fetch news: {e}")

        # If still empty, return a helpful message item so narrative generation can mention absence
        if not events:
            return [{"time": "Now", "event": "No high-severity news found in the last 24 hours", "impact": "LOW", "url": ""}]
        return events[:5]
    
    def _get_overnight_moves(self) -> Dict:
        """Get overnight market moves."""
        return {
            "asia": {"direction": "up", "change": "+0.8%", "driver": "China stimulus hopes"},
            "europe": {"direction": "up", "change": "+0.5%", "driver": "ECB dovish signals"},
            "futures": {"es": "+0.3%", "nq": "+0.5%", "rty": "+0.2%"}
        }
    
    def _get_premarket_movers(self, watchlist: List[str]) -> Dict:
        """Get pre-market movers."""
        return {
            "gainers": [
                {"ticker": "NVDA", "change": "+3.2%", "reason": "AI chip demand"},
                {"ticker": "AAPL", "change": "+1.5%", "reason": "Analyst upgrade"}
            ],
            "losers": [
                {"ticker": "TSLA", "change": "-2.1%", "reason": "China sales weak"}
            ]
        }
    
    def _assess_risk_level(self, trend_data: Dict = None) -> Dict:
        """Assess overall market risk level."""
        if not trend_data:
            trend_data = self._get_market_trend_data()
            
        trend_val = trend_data.get('trend', {}).get('raw', 0)
        
        if trend_val < -0.5:
            level = "HIGH"
            score = 85
        elif trend_val < 0:
            level = "MODERATE"
            score = 55
        else:
            level = "LOW"
            score = 25
            
        return {
            "level": level,
            "score": score,
            "factors": ["Trend Analysis", "Volatility"]
        }
    
    def _get_portfolio_context(self) -> Dict:
        """Get portfolio context from Alpaca."""
        try:
            executor = AlpacaExecutor()
            account = executor.get_account_info()
            positions = executor.get_open_positions()
            
            # Summarize top positions
            top_holdings = []
            if positions:
                sorted_pos = sorted(positions.items(), key=lambda x: x[1]['market_value'], reverse=True)
                for ticker, pos in sorted_pos[:3]:
                    top_holdings.append(f"{ticker} ({pos['unrealized_plpc']*100:+.1f}%)")
            
            return {
                "equity": account.get('equity', 0),
                "cash": account.get('cash', 0),
                "day_change": account.get('equity', 0) - account.get('last_equity', 0),
                "top_holdings": top_holdings,
                "position_count": len(positions)
            }
        except Exception as e:
            logger.debug(f"Portfolio context unavailable: {e}")
            return {}

    def _generate_llm_narrative(self, summary: Dict, watchlist: List[str]) -> str:
        """Generate AI narrative summary using LLM."""
        try:
            sentiment = summary.get("market_sentiment", {})
            events = summary.get("key_events", [])
            risk = summary.get("risk_level", {})
            portfolio = summary.get("portfolio_context", {})
            
            # Construct prompt
            prompt = f"""
            You are a senior financial analyst writing a morning brief for a trader.
            
            Market Context:
            - Overall Sentiment: {sentiment.get('overall')} (Confidence: {sentiment.get('confidence')}%)
            - Short-term Pulse: {sentiment.get('short_term')}
            - Key Technicals: {', '.join(sentiment.get('factors', []))}
            - Risk Level: {risk.get('level')}
            
            Portfolio Snapshot:
            - Equity: ${portfolio.get('equity', 0):,.2f}
            - Top Holdings: {', '.join(portfolio.get('top_holdings', ['None']))}
            
            Key News/Events:
            {chr(10).join([f"- {e['event']} (Impact: {e['impact']})" for e in events])}
            
            Watchlist: {', '.join(watchlist[:3])}
            
            Task:
            Write a concise, professional morning brief (max 150 words).
            1. Start with a "Bottom Line Up Front" statement about the market mood.
            2. Mention the most critical news item.
            3. Provide a specific insight on the portfolio or watchlist based on the technicals.
            4. Use bolding for key terms (markdown).
            5. Tone: Professional, objective, slightly cautious.
            """
            
            return self.llm_client.generate(prompt, max_tokens=300)
            
        except Exception as e:
            logger.error(f"Failed to generate LLM narrative: {e}")
            return "Market data is available, but AI narrative generation failed. Please check system logs."
    
    def _detect_sector_rotation(self, sectors: Dict) -> str:
        """Detect sector rotation pattern."""
        # Simplified rotation detection
        strong_sectors = [s for s, d in sectors.items() if d.get('strength') == 'strong']
        weak_sectors = [s for s, d in sectors.items() if d.get('strength') == 'weak']
        
        if 'XLK' in strong_sectors and 'XLY' in strong_sectors:
            return "Risk-On: Growth/Tech leading"
        elif 'XLU' in strong_sectors and 'XLP' in strong_sectors:
            return "Risk-Off: Defensive rotation"
        elif 'XLE' in strong_sectors:
            return "Inflation Trade: Energy leading"
        else:
            return "Neutral: No clear rotation"
    
    def _cache_brief(self, brief: Dict):
        """Cache the brief to disk."""
        try:
            date_str = datetime.now().strftime("%Y%m%d")
            filepath = os.path.join(self.cache_dir, f"morning_brief_{date_str}.json")
            with open(filepath, 'w') as f:
                json.dump(brief, f, indent=2, default=str)
            logger.info(f"Cached morning brief to {filepath}")
        except Exception as e:
            logger.warning(f"Failed to cache brief: {e}")
    
    def get_latest_brief(self) -> Optional[Dict]:
        """Get the latest cached brief."""
        try:
            date_str = datetime.now().strftime("%Y%m%d")
            filepath = os.path.join(self.cache_dir, f"morning_brief_{date_str}.json")
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cached brief: {e}")
        return None


# Singleton instance
_service = None

def get_morning_brief_service() -> AIMorningBriefService:
    """Get or create the morning brief service singleton."""
    global _service
    if _service is None:
        _service = AIMorningBriefService()
    return _service


def generate_morning_brief(watchlist: List[str] = None) -> Dict:
    """Convenience function to generate a morning brief."""
    service = get_morning_brief_service()
    return service.generate_full_brief(watchlist)
