"""
AI Trade Recommendations - Smart trade suggestions based on market conditions

Author: Options Lab Enhancement Phase
Enhanced: Integrated with FinGPT sentiment and advanced options analytics
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import plotly.graph_objects as go

logger = logging.getLogger(__name__)

# Import advanced analytics and sentiment services
try:
    from financial_dashboard.tabs.options_lab.options_analytics import (
        calculate_iv_rank,
        calculate_iv_percentile,
        calculate_max_pain,
        calculate_expected_move,
        calculate_put_call_ratio,
        get_iv_vs_hv_analysis
    )
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False
    logger.warning("Options analytics module not available")

try:
    from financial_dashboard.services.unified_sentiment_service import (
        analyze_text_sentiment,
        analyze_headlines_sentiment
    )
    SENTIMENT_AVAILABLE = True
except ImportError:
    SENTIMENT_AVAILABLE = False
    logger.warning("Sentiment service not available")


# Trade recommendation types
class RecommendationType:
    BULLISH = 'bullish'
    BEARISH = 'bearish'
    NEUTRAL = 'neutral'
    HIGH_IV = 'high_iv'
    LOW_IV = 'low_iv'
    EARNINGS = 'earnings'
    INCOME = 'income'
    PROTECTION = 'protection'


class TradeRecommendation:
    """Single trade recommendation."""
    
    def __init__(self, ticker: str, strategy: str, rationale: str,
                 expected_roi: float, risk_level: str, confidence: float,
                 entry_criteria: Dict, exit_criteria: Dict,
                 recommendation_type: str, time_horizon: str,
                 legs: List[Dict] = None):
        self.ticker = ticker
        self.strategy = strategy
        self.rationale = rationale
        self.expected_roi = expected_roi  # as percentage
        self.risk_level = risk_level  # 'low', 'medium', 'high'
        self.confidence = confidence  # 0-100
        self.entry_criteria = entry_criteria
        self.exit_criteria = exit_criteria
        self.recommendation_type = recommendation_type
        self.time_horizon = time_horizon
        self.legs = legs or []
        self.created_at = datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'strategy': self.strategy,
            'rationale': self.rationale,
            'expected_roi': self.expected_roi,
            'risk_level': self.risk_level,
            'confidence': self.confidence,
            'entry_criteria': self.entry_criteria,
            'exit_criteria': self.exit_criteria,
            'type': self.recommendation_type,
            'time_horizon': self.time_horizon,
            'legs': self.legs,
            'created_at': self.created_at.isoformat()
        }


class AIRecommendationEngine:
    """Generate AI-powered trade recommendations."""
    
    def __init__(self):
        self.recommendations = []
        self.market_conditions = {}
        
    def update_market_conditions(self, conditions: Dict):
        """Update current market conditions for analysis."""
        self.market_conditions = {
            'vix': conditions.get('vix', 20),
            'vix_percentile': conditions.get('vix_percentile', 50),
            'spy_trend': conditions.get('spy_trend', 'neutral'),
            'sector_rotation': conditions.get('sector_rotation', {}),
            'earnings_season': conditions.get('earnings_season', False),
            'fed_meeting_soon': conditions.get('fed_meeting_soon', False),
            'updated_at': datetime.now()
        }
        
    def _get_expiry_date(self, days: int) -> str:
        """Get expiration date string for given days from now."""
        # Find next Friday that is at least 'days' away
        target = datetime.now() + timedelta(days=days)
        days_ahead = 4 - target.weekday()
        if days_ahead < 0:
            days_ahead += 7
        expiry = target + timedelta(days=days_ahead)
        return expiry.strftime('%Y-%m-%d')

    def _days_to_expiry(self, expiry_date: str) -> int:
        from datetime import datetime
        try:
            d = datetime.strptime(expiry_date, '%Y-%m-%d')
            delta = d - datetime.now()
            return max(0, delta.days)
        except Exception:
            return 30

    def _estimate_option_price(self, S: float, K: float, days: int, iv: float, option_type: str = 'call') -> float:
        """Estimate option premium using Black-Scholes formula (approx).
        Falls back to a simple heuristic if scipy is unavailable.
        """
        try:
            from math import log, sqrt, exp
            from scipy.stats import norm
            r = 0.01
            T = max(1e-6, days / 365.0)
            sigma = max(0.01, float(iv))
            d1 = (log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))
            d2 = d1 - sigma * sqrt(T)
            if option_type == 'call':
                price = S * norm.cdf(d1) - K * exp(-r * T) * norm.cdf(d2)
            else:
                price = K * exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
            return max(0.01, float(price))
        except Exception:
            # Simple heuristic fallback
            intrinsic = max(0.0, (S - K) if option_type == 'call' else (K - S))
            time_value = max(0.01, iv * S * (min(days, 90) / 365.0) * 0.7)
            return max(0.01, intrinsic * 0.6 + time_value)

    def analyze_ticker(self, ticker: str, data: Dict) -> List[TradeRecommendation]:
        """Analyze a ticker and generate recommendations."""
        recommendations = []
        
        spot = data.get('spot', 100)
        iv = data.get('iv', 0.3)
        iv_percentile = data.get('iv_percentile', 50)
        iv_rank = data.get('iv_rank', 0.5)
        trend = data.get('trend', 'neutral')  # 'bullish', 'bearish', 'neutral'
        earnings_soon = data.get('earnings_soon', False)
        support = data.get('support', spot * 0.95)
        resistance = data.get('resistance', spot * 1.05)
        # Attempt to fetch a live option chain to improve leg selection and pricing
        chain = None
        try:
            from financial_dashboard.tabs.options_lab.data_loader import fetch_options_chain
            try:
                chain = fetch_options_chain(ticker, use_mock=False, use_alpaca=False)
            except Exception:
                chain = None
        except Exception:
            chain = None

        def _chain_option_price_lookup(leg: Dict, prefer_days: int = 30) -> Optional[float]:
            """If a live chain is available, pick the nearest expiration and strike and return mid price."""
            try:
                if not chain or ('calls' not in chain and 'puts' not in chain):
                    return None
                exps = chain.get('expirations') or []
                if not exps:
                    return None

                # Choose expiration closest to prefer_days
                best_exp = None
                best_diff = 10_000
                for e in exps:
                    try:
                        d = self._days_to_expiry(e)
                        diff = abs(d - prefer_days)
                        if diff < best_diff:
                            best_diff = diff
                            best_exp = e
                    except Exception:
                        continue

                if not best_exp:
                    best_exp = exps[0]

                opt_type = leg.get('type', 'call')
                df = None
                if opt_type == 'call':
                    df = chain.get('calls')
                elif opt_type == 'put':
                    df = chain.get('puts')

                if df is None or (hasattr(df, 'empty') and df.empty):
                    return None

                # Ensure DataFrame
                import pandas as _pd
                if isinstance(df, list):
                    df = _pd.DataFrame(df)

                # Filter by expiration and find closest strike
                if 'expiration' in df.columns:
                    df_exp = df[df['expiration'].astype(str) == str(best_exp)]
                else:
                    df_exp = df

                if df_exp.empty:
                    df_exp = df

                target_strike = float(leg.get('strike', spot))
                if 'strike' in df_exp.columns:
                    df_exp['diff'] = (df_exp['strike'] - target_strike).abs()
                    row = df_exp.loc[df_exp['diff'].idxmin()]
                else:
                    # no strike column available
                    row = None

                if row is not None:
                    bid = float(row.get('bid') or 0)
                    ask = float(row.get('ask') or 0)
                    last = float(row.get('lastPrice') or 0)
                    if bid and ask:
                        return round((bid + ask) / 2.0, 2)
                    if last:
                        return round(last, 2)
            except Exception:
                return None
            return None
        
        # High IV Strategies - Sell premium
        if iv_percentile > 70:
            # Iron Condor for neutral outlook
            expiry = self._get_expiry_date(45)
            rec = TradeRecommendation(
                ticker=ticker,
                strategy='Iron Condor',
                rationale=f"IV Percentile at {iv_percentile}% - historically high. "
                         f"Selling premium when IV is elevated tends to be profitable.",
                expected_roi=15.0,
                risk_level='medium',
                confidence=min(75 + (iv_percentile - 70), 90),
                entry_criteria={
                    'iv_percentile_min': 70,
                    'trend': 'neutral or range-bound',
                    'days_to_expiry': '30-45 DTE'
                },
                exit_criteria={
                    'profit_target': '50% of max profit',
                    'stop_loss': '2x credit received',
                    'time_stop': '21 DTE'
                },
                recommendation_type=RecommendationType.HIGH_IV,
                time_horizon='30-45 days',
                legs=[
                    {'type': 'put', 'action': 'sell', 'strike': round(support * 0.95, 2), 'expiration': expiry, 'estimated_price': round(spot * 0.02, 2)},
                    {'type': 'put', 'action': 'buy', 'strike': round(support * 0.90, 2), 'expiration': expiry, 'estimated_price': round(spot * 0.01, 2)},
                    {'type': 'call', 'action': 'sell', 'strike': round(resistance * 1.05, 2), 'expiration': expiry, 'estimated_price': round(spot * 0.02, 2)},
                    {'type': 'call', 'action': 'buy', 'strike': round(resistance * 1.10, 2), 'expiration': expiry, 'estimated_price': round(spot * 0.01, 2)}
                ]
            )
            # compute option price estimates for legs (prefer live chain prices when available)
            for leg in rec.legs:
                strike = float(leg.get('strike', spot))
                # days until expiry
                days = self._days_to_expiry(leg.get('expiration') or expiry)
                lookup = _chain_option_price_lookup(leg, prefer_days=days)
                if lookup is not None:
                    leg['estimated_price'] = lookup
                    leg['price_source'] = chain.get('source') if chain else 'live'
                else:
                    est = self._estimate_option_price(spot, strike, days, iv, option_type=leg.get('type', 'call'))
                    leg['estimated_price'] = round(est, 2)

            recommendations.append(rec)
            
            # Credit spread based on trend
            if trend == 'bullish':
                expiry = self._get_expiry_date(30)
                rec = TradeRecommendation(
                    ticker=ticker,
                    strategy='Bull Put Spread',
                    rationale=f"Bullish trend with elevated IV ({iv_percentile}%). "
                             f"Sell puts below support at ${support:.2f}.",
                    expected_roi=12.0,
                    risk_level='medium',
                    confidence=70,
                    entry_criteria={
                        'trend': 'bullish',
                        'iv_percentile_min': 60,
                        'price_above': f"${support:.2f} support"
                    },
                    exit_criteria={
                        'profit_target': '50-75% of credit',
                        'stop_loss': '100% of credit',
                        'time_stop': '7 DTE'
                    },
                    recommendation_type=RecommendationType.BULLISH,
                    time_horizon='30-45 days',
                    legs=[
                        {'type': 'put', 'action': 'sell', 'strike': round(support, 2), 'expiration': expiry, 'estimated_price': round(spot * 0.03, 2)},
                        {'type': 'put', 'action': 'buy', 'strike': round(support * 0.95, 2), 'expiration': expiry, 'estimated_price': round(spot * 0.015, 2)}
                    ]
                )
                for leg in rec.legs:
                    strike = float(leg.get('strike', support))
                    days = self._days_to_expiry(leg.get('expiration') or expiry)
                    lookup = _chain_option_price_lookup(leg, prefer_days=days)
                    if lookup is not None:
                        leg['estimated_price'] = lookup
                        leg['price_source'] = chain.get('source') if chain else 'live'
                    else:
                        est = self._estimate_option_price(spot, strike, days, iv, option_type=leg.get('type', 'put'))
                        leg['estimated_price'] = round(est, 2)
                recommendations.append(rec)
                
        # Low IV Strategies - Buy premium
        if iv_percentile < 30:
            if trend == 'bullish':
                expiry = self._get_expiry_date(60)
                rec = TradeRecommendation(
                    ticker=ticker,
                    strategy='Long Call',
                    rationale=f"IV Percentile at {iv_percentile}% - options are cheap. "
                             f"Bullish trend suggests upside potential.",
                    expected_roi=50.0,
                    risk_level='high',
                    confidence=60,
                    entry_criteria={
                        'iv_percentile_max': 30,
                        'trend': 'bullish',
                        'catalyst': 'breakout above resistance'
                    },
                    exit_criteria={
                        'profit_target': '100%+ of premium',
                        'stop_loss': '50% of premium',
                        'time_stop': '21 DTE'
                    },
                    recommendation_type=RecommendationType.LOW_IV,
                    time_horizon='45-60 days',
                    legs=[
                        {'type': 'call', 'action': 'buy', 'strike': round(resistance, 2), 'expiration': expiry, 'estimated_price': round(spot * 0.05, 2)}
                    ]
                )
                recommendations.append(rec)
            
            # Calendar spread
            rec = TradeRecommendation(
                ticker=ticker,
                strategy='Calendar Spread',
                rationale=f"Low IV ({iv_percentile}%) creates opportunity for "
                         f"calendar spreads if IV expansion is expected.",
                expected_roi=25.0,
                risk_level='medium',
                confidence=55,
                entry_criteria={
                    'iv_percentile_max': 30,
                    'iv_term_structure': 'flat or contango',
                    'expected_catalyst': 'earnings or news'
                },
                exit_criteria={
                    'profit_target': '50% of debit',
                    'stop_loss': '75% of debit',
                    'time_stop': 'near expiry -3 DTE'
                },
                recommendation_type=RecommendationType.LOW_IV,
                time_horizon='30-60 days',
                legs=[
                    {'type': 'call', 'action': 'sell', 'strike': spot, 'expiry': 'near'},
                    {'type': 'call', 'action': 'buy', 'strike': spot, 'expiry': 'far'}
                ]
            )
            for leg in rec.legs:
                strike = float(leg.get('strike', resistance))
                days = self._days_to_expiry(leg.get('expiration') or expiry)
                lookup = _chain_option_price_lookup(leg, prefer_days=days)
                if lookup is not None:
                    leg['estimated_price'] = lookup
                    leg['price_source'] = chain.get('source') if chain else 'live'
                else:
                    est = self._estimate_option_price(spot, strike, days, iv, option_type=leg.get('type', 'call'))
                    leg['estimated_price'] = round(est, 2)
            recommendations.append(rec)
        
        # Earnings play
        if earnings_soon:
            # Define short and long expirations for earnings plays
            expiry_short = self._get_expiry_date(7)
            expiry_long = self._get_expiry_date(60)

            # Straddle for unknown direction
            rec = TradeRecommendation(
                ticker=ticker,
                strategy='Long Straddle (Pre-Earnings)',
                rationale="Earnings announcement soon. Historical move "
                         "may exceed implied move, making straddle profitable.",
                expected_roi=30.0,
                risk_level='high',
                confidence=50,
                entry_criteria={
                    'days_to_earnings': '5-10 days',
                    'iv_not_extreme': f"current IV: {iv*100:.1f}%",
                    'historical_surprise': 'history of big moves'
                },
                exit_criteria={
                    'timing': 'close before earnings or same day',
                    'profit_target': '30%+',
                    'max_loss': 'total premium if held through'
                },
                recommendation_type=RecommendationType.NEUTRAL,
                time_horizon='30 days',
                legs=[
                    {'type': 'call', 'action': 'sell', 'strike': round(spot, 2), 'expiration': expiry_short, 'estimated_price': round(spot * 0.02, 2)},
                    {'type': 'call', 'action': 'buy', 'strike': round(spot, 2), 'expiration': expiry_long, 'estimated_price': round(spot * 0.04, 2)}
                ]
            )
            for leg in rec.legs:
                strike = float(leg.get('strike', spot))
                days = self._days_to_expiry(leg.get('expiration') or expiry_short)
                lookup = _chain_option_price_lookup(leg, prefer_days=days)
                if lookup is not None:
                    leg['estimated_price'] = lookup
                    leg['price_source'] = chain.get('source') if chain else 'live'
                else:
                    est = self._estimate_option_price(spot, strike, days, iv, option_type=leg.get('type', 'call'))
                    leg['estimated_price'] = round(est, 2)
            recommendations.append(rec)
        
        # Income strategy - covered call
        # Income Strategy
        expiry = self._get_expiry_date(30)
        rec = TradeRecommendation(
            ticker=ticker,
            strategy='Covered Call (Income)',
            rationale=f"Generate income on existing {ticker} shares by selling "
                     f"OTM calls at {resistance:.2f} resistance.",
            expected_roi=3.0,
            risk_level='low',
            confidence=80,
            entry_criteria={
                'position': f'own 100+ shares of {ticker}',
                'outlook': 'neutral to slightly bullish',
                'willing_to_sell': f'at ${resistance:.2f}'
            },
            exit_criteria={
                'expiration': 'let expire worthless ideally',
                'roll': 'roll if approaching ITM',
                'assignment': 'accept if called away'
            },
            recommendation_type=RecommendationType.INCOME,
            time_horizon='30-45 days',
            legs=[
                {'type': 'stock', 'action': 'hold', 'quantity': 100, 'expiration': 'N/A', 'estimated_price': round(spot, 2)},
                {'type': 'call', 'action': 'sell', 'strike': round(resistance * 1.05, 2), 'expiration': expiry}
            ]
        )
        # Estimate prices for income legs
        for leg in rec.legs:
            if leg.get('type') in ['call', 'put']:
                strike = float(leg.get('strike', resistance))
                days = self._days_to_expiry(leg.get('expiration') or expiry)
                lookup = _chain_option_price_lookup(leg, prefer_days=days)
                if lookup is not None:
                    leg['estimated_price'] = lookup
                    leg['price_source'] = chain.get('source') if chain else 'live'
                else:
                    est = self._estimate_option_price(spot, strike, days, iv, option_type=leg.get('type', 'call'))
                    leg['estimated_price'] = round(est, 2)

        recommendations.append(rec)
        recommendations.append(rec)
        
        return recommendations
    
    def generate_recommendations(self, tickers: List[str] = None,
                                  market_data: Dict = None) -> List[TradeRecommendation]:
        """Generate recommendations for multiple tickers."""
        if tickers is None:
            tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'SPY', 'QQQ', 'NVDA', 'AMD']
        
        if market_data is None:
            # Generate sample data
            np.random.seed(int(datetime.now().timestamp()) % 1000)
            market_data = {}
            
            for ticker in tickers:
                spot = np.random.uniform(50, 500)
                market_data[ticker] = {
                    'spot': spot,
                    'iv': np.random.uniform(0.15, 0.60),
                    'iv_percentile': np.random.randint(10, 90),
                    'iv_rank': np.random.uniform(0.1, 0.9),
                    'trend': np.random.choice(['bullish', 'bearish', 'neutral']),
                    'earnings_soon': np.random.random() > 0.85,
                    'support': spot * np.random.uniform(0.92, 0.98),
                    'resistance': spot * np.random.uniform(1.02, 1.08)
                }
        
        self.recommendations = []
        
        for ticker in tickers:
            if ticker in market_data:
                recs = self.analyze_ticker(ticker, market_data[ticker])
                self.recommendations.extend(recs)
        
        # Sort by confidence
        self.recommendations.sort(key=lambda x: x.confidence, reverse=True)
        
        return self.recommendations
    
    def generate_sentiment_enhanced_recommendations(
        self, 
        tickers: List[str], 
        market_data: Dict,
        news_headlines: Dict[str, List[str]] = None
    ) -> List[TradeRecommendation]:
        """
        Generate recommendations enhanced with sentiment analysis.
        
        Args:
            tickers: List of tickers to analyze
            market_data: Dict of market data per ticker
            news_headlines: Dict of news headlines per ticker
            
        Returns:
            List of sentiment-enhanced recommendations
        """
        if not SENTIMENT_AVAILABLE:
            logger.warning("Sentiment service not available, using standard recommendations")
            return self.generate_recommendations(tickers, market_data)
        
        self.recommendations = []
        
        for ticker in tickers:
            if ticker not in market_data:
                continue
                
            data = market_data[ticker].copy()
            
            # Analyze sentiment for this ticker
            headlines = news_headlines.get(ticker, []) if news_headlines else []
            if headlines:
                sentiment_result = analyze_headlines_sentiment(headlines)
                data['sentiment'] = sentiment_result.get('overall_sentiment', 'neutral')
                data['sentiment_score'] = sentiment_result.get('overall_score', 0)
                data['sentiment_confidence'] = sentiment_result.get('confidence', 0)
                
                # Adjust trend based on sentiment
                if sentiment_result.get('overall_score', 0) > 0.3 and data.get('trend') != 'bearish':
                    data['trend'] = 'bullish'
                elif sentiment_result.get('overall_score', 0) < -0.3 and data.get('trend') != 'bullish':
                    data['trend'] = 'bearish'
            
            recs = self.analyze_ticker(ticker, data)
            
            # Enhance recommendations with sentiment info
            for rec in recs:
                if 'sentiment' in data:
                    rec.rationale += f" [Sentiment: {data['sentiment'].upper()} ({data['sentiment_score']:.2f})]"
                    # Boost confidence if sentiment aligns with recommendation
                    if (rec.recommendation_type == 'bullish' and data['sentiment'] == 'positive') or \
                       (rec.recommendation_type == 'bearish' and data['sentiment'] == 'negative'):
                        rec.confidence = min(rec.confidence + 10, 95)
            
            self.recommendations.extend(recs)
        
        self.recommendations.sort(key=lambda x: x.confidence, reverse=True)
        return self.recommendations
    
    def get_top_recommendations(self, n: int = 5, 
                                 rec_type: str = None) -> List[TradeRecommendation]:
        """Get top N recommendations, optionally filtered by type."""
        recs = self.recommendations
        
        if rec_type:
            recs = [r for r in recs if r.recommendation_type == rec_type]
        
        return recs[:n]


def create_recommendations_summary(recommendations: List[TradeRecommendation]) -> go.Figure:
    """Create visual summary of recommendations."""
    if not recommendations:
        fig = go.Figure()
        fig.add_annotation(text="No recommendations", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template='plotly_dark')
        return fig
    
    df = pd.DataFrame([r.to_dict() for r in recommendations])
    
    # Scatter plot of risk vs reward
    risk_map = {'low': 1, 'medium': 2, 'high': 3}
    df['risk_numeric'] = df['risk_level'].map(risk_map)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['risk_numeric'],
        y=df['expected_roi'],
        mode='markers+text',
        marker=dict(
            size=df['confidence'] / 5,
            color=df['confidence'],
            colorscale='RdYlGn',
            colorbar=dict(title='Confidence'),
            showscale=True
        ),
        text=df['ticker'] + '<br>' + df['strategy'],
        textposition='top center',
        hovertemplate=(
            '<b>%{text}</b><br>'
            'Expected ROI: %{y:.1f}%<br>'
            'Confidence: %{marker.color:.0f}%<br>'
            '<extra></extra>'
        )
    ))
    
    fig.update_layout(
        title='Trade Recommendations: Risk vs Reward',
        xaxis=dict(
            title='Risk Level',
            tickvals=[1, 2, 3],
            ticktext=['Low', 'Medium', 'High']
        ),
        yaxis_title='Expected ROI (%)',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.8)',
        height=400
    )
    
    return fig


def create_recommendation_card(rec: TradeRecommendation) -> Dict:
    """Create UI card data for a recommendation."""
    risk_colors = {'low': '#4CAF50', 'medium': '#FF9800', 'high': '#f44336'}
    # Build human-readable legs summary
    legs_lines = []
    for leg in (rec.legs or []):
        strike = leg.get('strike')
        exp = leg.get('expiration') or leg.get('exp') or leg.get('expiry') or 'N/A'
        price = leg.get('estimated_price') or leg.get('option_price') or leg.get('price')
        price_src = leg.get('price_source')
        try:
            strike_txt = f"{float(strike):.2f}" if strike is not None else 'N/A'
        except Exception:
            strike_txt = str(strike)
        if price is not None:
            try:
                price_txt = f"${float(price):.2f}"
            except Exception:
                price_txt = str(price)
            src_txt = f" ({price_src})" if price_src else ''
            leg_txt = f"{leg.get('action','').capitalize()} {leg.get('type','').upper()} {strike_txt} exp {exp} @ {price_txt}{src_txt}"
        else:
            leg_txt = f"{leg.get('action','').capitalize()} {leg.get('type','').upper()} {strike_txt} exp {exp}"
        legs_lines.append(leg_txt)

    return {
        'ticker': rec.ticker,
        'strategy': rec.strategy,
        'type': rec.recommendation_type,
        'rationale': rec.rationale,
        'expected_roi': f"{rec.expected_roi:.1f}%",
        'risk_level': rec.risk_level,
        'risk_color': risk_colors.get(rec.risk_level, '#999'),
        'confidence': f"{rec.confidence:.0f}%",
        'time_horizon': rec.time_horizon,
        'legs': rec.legs,
        'legs_summary': '\n'.join(legs_lines) if legs_lines else '',
        'entry_criteria': rec.entry_criteria,
        'exit_criteria': rec.exit_criteria
    }


# Singleton instance
_engine = None

def get_recommendation_engine() -> AIRecommendationEngine:
    """Get singleton recommendation engine instance."""
    global _engine
    if _engine is None:
        _engine = AIRecommendationEngine()
    return _engine
