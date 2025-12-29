"""
Proactive AI Advisor
====================
AI that pushes recommendations to users without requiring prompts.
Continuously analyzes market conditions and suggests optimal actions.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import requests
from enum import Enum

logger = logging.getLogger(__name__)


class RecommendationType(Enum):
    """Types of proactive recommendations."""
    OPPORTUNITY = "opportunity"      # New trade opportunity
    ADJUSTMENT = "adjustment"        # Adjust existing position
    CLOSE = "close"                  # Close position
    HEDGE = "hedge"                  # Add hedge
    WARNING = "warning"              # Risk warning
    MARKET_UPDATE = "market_update"  # Market condition change


@dataclass
class ProactiveRecommendation:
    """AI-generated proactive recommendation."""
    rec_id: str
    rec_type: RecommendationType
    ticker: str
    title: str
    summary: str
    detailed_analysis: str
    suggested_action: str
    confidence: float
    urgency: str  # 'low', 'medium', 'high', 'immediate'
    potential_reward: Optional[float]
    potential_risk: Optional[float]
    timestamp: datetime
    expires_at: datetime
    metadata: Dict


class ProactiveAdvisor:
    """
    AI advisor that proactively generates trading recommendations
    without requiring user input.
    """
    
    def __init__(self):
        self.groq_api_key = os.getenv('GROQ_API_KEY')
        self.recommendations: List[ProactiveRecommendation] = []
        self._rec_counter = 0
        
        # Watchlist for proactive monitoring
        self.watchlist = ['SPY', 'QQQ', 'AAPL', 'NVDA', 'TSLA', 'AMZN', 'META', 'GOOGL', 'MSFT']
        
        # Cache for market analysis
        self._market_cache = {}
        self._cache_time = {}
    
    def generate_daily_briefing(self) -> Dict:
        """
        Generate a comprehensive daily market briefing.
        Called automatically each day.
        """
        try:
            from .ai_ml_engine import get_auto_discovery, get_ai_selector
            from .sentiment_analyzer import get_sentiment_analyzer
            
            discovery = get_auto_discovery()
            selector = get_ai_selector()
            sentiment = get_sentiment_analyzer()
            
            briefing = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'market_overview': self._get_market_overview(),
                'top_opportunities': [],
                'sector_analysis': [],
                'risk_events': [],
                'recommendations': []
            }
            
            # Get top opportunities
            opportunities = discovery.get_top_opportunities(5)
            for opp in opportunities:
                sent = sentiment.analyze_ticker(opp.ticker)
                strategy = selector.get_best_strategy(opp.ticker)
                
                briefing['top_opportunities'].append({
                    'ticker': opp.ticker,
                    'iv_rank': opp.iv_rank,
                    'regime': opp.regime.value,
                    'sentiment': sent.overall_sentiment.name,
                    'strategy': strategy.strategy_name if strategy else 'N/A',
                    'confidence': strategy.confidence if strategy else 0
                })
            
            # Generate recommendations
            recs = self._generate_recommendations(opportunities, sentiment)
            briefing['recommendations'] = recs
            
            return briefing
            
        except Exception as e:
            logger.error(f"Daily briefing error: {e}")
            return {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'error': str(e),
                'market_overview': 'Unable to generate briefing',
                'top_opportunities': [],
                'recommendations': []
            }
    
    def _get_market_overview(self) -> Dict:
        """Get current market overview."""
        try:
            import yfinance as yf
            
            indices = {
                'SPY': 'S&P 500',
                'QQQ': 'NASDAQ',
                'IWM': 'Russell 2000',
                'VIX': 'Volatility'
            }
            
            overview = []
            for symbol, name in indices.items():
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period='2d')
                    
                    if len(hist) >= 2:
                        current = hist['Close'].iloc[-1]
                        prev = hist['Close'].iloc[-2]
                        change_pct = ((current - prev) / prev) * 100
                        
                        overview.append({
                            'symbol': symbol,
                            'name': name,
                            'price': round(current, 2),
                            'change_pct': round(change_pct, 2),
                            'direction': 'up' if change_pct > 0 else 'down' if change_pct < 0 else 'flat'
                        })
                except:
                    pass
            
            # Determine market regime
            spy_data = next((o for o in overview if o['symbol'] == 'SPY'), None)
            vix_data = next((o for o in overview if o['symbol'] == 'VIX'), None)
            
            if spy_data and vix_data:
                vix_price = vix_data['price']
                spy_change = spy_data['change_pct']
                
                if vix_price > 25:
                    regime = 'HIGH_VOLATILITY'
                elif vix_price < 15:
                    regime = 'LOW_VOLATILITY'
                elif spy_change > 0.5:
                    regime = 'BULLISH'
                elif spy_change < -0.5:
                    regime = 'BEARISH'
                else:
                    regime = 'NEUTRAL'
            else:
                regime = 'UNKNOWN'
            
            return {
                'indices': overview,
                'regime': regime,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.debug(f"Market overview error: {e}")
            return {'indices': [], 'regime': 'UNKNOWN', 'error': str(e)}
    
    def _generate_recommendations(self, opportunities, sentiment_analyzer) -> List[Dict]:
        """Generate proactive recommendations based on opportunities."""
        recommendations = []
        
        for i, opp in enumerate(opportunities[:3]):
            try:
                sent = sentiment_analyzer.analyze_ticker(opp.ticker)
                
                # Generate recommendation based on market conditions
                rec = {
                    'ticker': opp.ticker,
                    'type': 'OPPORTUNITY',
                    'urgency': 'medium',
                    'confidence': 0.7
                }
                
                # High IV + Neutral/Bearish sentiment = Sell premium
                if opp.iv_rank > 70 and sent.overall_sentiment.value <= 0:
                    rec['strategy'] = 'Iron Condor'
                    rec['rationale'] = f"High IV rank ({opp.iv_rank:.0f}%) with {sent.overall_sentiment.name} sentiment - ideal for premium selling"
                    rec['action'] = f"Sell iron condor on {opp.ticker} to capture elevated premium"
                    rec['confidence'] = 0.75
                
                # High IV + Bullish = Bull Put Spread
                elif opp.iv_rank > 60 and sent.overall_sentiment.value > 0:
                    rec['strategy'] = 'Bull Put Spread'
                    rec['rationale'] = f"Elevated IV ({opp.iv_rank:.0f}%) with bullish sentiment - sell puts for premium"
                    rec['action'] = f"Sell put spread on {opp.ticker}"
                    rec['confidence'] = 0.7
                
                # Low IV + Strong trend = Buy options
                elif opp.iv_rank < 30 and abs(opp.trend_strength) > 0.05:
                    direction = 'bullish' if opp.trend_strength > 0 else 'bearish'
                    rec['strategy'] = 'Long Call' if direction == 'bullish' else 'Long Put'
                    rec['rationale'] = f"Low IV ({opp.iv_rank:.0f}%) with {direction} trend - options are cheap"
                    rec['action'] = f"Buy {rec['strategy'].lower()} on {opp.ticker}"
                    rec['confidence'] = 0.65
                
                else:
                    rec['strategy'] = 'Watch'
                    rec['rationale'] = f"No clear edge - IV rank {opp.iv_rank:.0f}%"
                    rec['action'] = f"Monitor {opp.ticker} for better entry"
                    rec['confidence'] = 0.5
                
                recommendations.append(rec)
                
            except Exception as e:
                logger.debug(f"Recommendation error for {opp.ticker}: {e}")
        
        return recommendations
    
    def get_quick_trade_ideas(self, count: int = 5) -> List[Dict]:
        """
        Get quick AI-generated trade ideas.
        Zero user input required.
        """
        try:
            from .ai_ml_engine import get_auto_discovery, get_ai_selector
            from .sentiment_analyzer import get_sentiment_analyzer
            
            discovery = get_auto_discovery()
            selector = get_ai_selector()
            sentiment_analyzer = get_sentiment_analyzer()
            
            ideas = []
            opportunities = discovery.get_top_opportunities(count * 2)  # Get more to filter
            
            for opp in opportunities:
                try:
                    strategy = selector.get_best_strategy(opp.ticker)
                    sent = sentiment_analyzer.analyze_ticker(opp.ticker)
                    
                    if strategy and strategy.confidence >= 0.5:
                        idea = {
                            'ticker': opp.ticker,
                            'spot_price': round(opp.spot_price, 2),
                            'strategy': strategy.strategy_name,
                            'direction': 'bullish' if strategy.legs[0].action == 'buy' else 'neutral/bearish',
                            'iv_rank': round(opp.iv_rank, 1),
                            'sentiment': sent.overall_sentiment.name,
                            'confidence': round(strategy.confidence * 100, 0),
                            'pop': round(strategy.probability_of_profit * 100, 0),
                            'max_profit': round(strategy.max_profit, 0),
                            'max_loss': round(abs(strategy.max_loss), 0),
                            'risk_reward': round(strategy.risk_reward_ratio, 1),
                            'rationale': strategy.rationale[:100] + '...' if len(strategy.rationale) > 100 else strategy.rationale
                        }
                        ideas.append(idea)
                        
                        if len(ideas) >= count:
                            break
                            
                except Exception as e:
                    logger.debug(f"Trade idea error for {opp.ticker}: {e}")
                    continue
            
            return ideas
            
        except Exception as e:
            logger.error(f"Quick trade ideas error: {e}")
            return []
    
    def get_market_regime_recommendation(self) -> Dict:
        """
        Get strategy recommendations based on current market regime.
        """
        overview = self._get_market_overview()
        regime = overview.get('regime', 'UNKNOWN')
        
        regime_strategies = {
            'HIGH_VOLATILITY': {
                'name': 'High Volatility',
                'description': 'VIX elevated - expect large price swings',
                'preferred_strategies': [
                    {'name': 'Iron Condor', 'reason': 'Capture elevated premium with defined risk'},
                    {'name': 'Short Straddle', 'reason': 'Maximum premium collection if neutral view'},
                    {'name': 'Credit Spreads', 'reason': 'Good premium with limited risk'}
                ],
                'avoid': ['Long calls/puts (expensive)', 'Calendar spreads (vega negative)'],
                'tips': [
                    'Reduce position sizes due to larger moves',
                    'Set wider strikes for iron condors',
                    'Consider shorter DTE to capture quick theta decay'
                ]
            },
            'LOW_VOLATILITY': {
                'name': 'Low Volatility',
                'description': 'VIX suppressed - calm market conditions',
                'preferred_strategies': [
                    {'name': 'Long Straddles', 'reason': 'Options are cheap, betting on volatility expansion'},
                    {'name': 'Calendar Spreads', 'reason': 'Benefit from vega expansion'},
                    {'name': 'Debit Spreads', 'reason': 'Directional plays are affordable'}
                ],
                'avoid': ['Selling premium (low reward)', 'Iron condors (poor risk/reward)'],
                'tips': [
                    'Good time to buy protective puts',
                    'Look for earnings plays',
                    'Consider longer DTE positions'
                ]
            },
            'BULLISH': {
                'name': 'Bullish Market',
                'description': 'Market trending higher',
                'preferred_strategies': [
                    {'name': 'Bull Put Spread', 'reason': 'Collect premium with bullish bias'},
                    {'name': 'Cash Secured Put', 'reason': 'Get paid to buy at lower price'},
                    {'name': 'Call Debit Spread', 'reason': 'Limited risk bullish play'}
                ],
                'avoid': ['Bear call spreads', 'Short calls'],
                'tips': [
                    'Let winners run with trailing stops',
                    'Scale into positions on pullbacks',
                    'Consider covered calls on existing holdings'
                ]
            },
            'BEARISH': {
                'name': 'Bearish Market',
                'description': 'Market trending lower',
                'preferred_strategies': [
                    {'name': 'Bear Call Spread', 'reason': 'Collect premium with bearish bias'},
                    {'name': 'Put Debit Spread', 'reason': 'Limited risk bearish play'},
                    {'name': 'Protective Puts', 'reason': 'Hedge existing long positions'}
                ],
                'avoid': ['Bull put spreads', 'Naked puts'],
                'tips': [
                    'Be patient - dont catch falling knives',
                    'Reduce overall position sizing',
                    'Consider VIX calls as portfolio hedge'
                ]
            },
            'NEUTRAL': {
                'name': 'Neutral/Ranging',
                'description': 'Market moving sideways',
                'preferred_strategies': [
                    {'name': 'Iron Condor', 'reason': 'Profit from lack of movement'},
                    {'name': 'Iron Butterfly', 'reason': 'Maximum theta in tight range'},
                    {'name': 'Short Strangle', 'reason': 'Premium collection with undefined risk'}
                ],
                'avoid': ['Directional trades', 'Long straddles (theta decay)'],
                'tips': [
                    'Focus on high-probability setups',
                    'Use technical levels for strike selection',
                    'Manage winners at 50% profit'
                ]
            }
        }
        
        recommendation = regime_strategies.get(regime, {
            'name': 'Unknown',
            'description': 'Unable to determine market regime',
            'preferred_strategies': [],
            'avoid': [],
            'tips': ['Wait for clearer market conditions']
        })
        
        recommendation['current_regime'] = regime
        recommendation['market_data'] = overview
        
        return recommendation
    
    def get_ai_generated_analysis(self, ticker: str) -> Dict:
        """
        Get comprehensive AI-generated analysis for a ticker.
        Uses GROQ if available, otherwise rule-based analysis.
        """
        if not self.groq_api_key:
            return self._generate_rule_based_analysis(ticker)
        
        try:
            # Gather context
            from .sentiment_analyzer import quick_sentiment
            from .ai_ml_engine import get_ml_predictor, get_ai_selector
            
            sentiment = quick_sentiment(ticker)
            predictor = get_ml_predictor()
            selector = get_ai_selector()
            
            prediction = predictor.predict_price(ticker, 7)
            strategy = selector.get_best_strategy(ticker)
            
            # Build context for GROQ
            context = f"""
Ticker: {ticker}
Sentiment: {sentiment['sentiment_label']} (confidence: {sentiment['confidence']}%)
Price Prediction (7d): {prediction.direction if prediction else 'N/A'} with {prediction.probability*100:.0f}% probability
Recommended Strategy: {strategy.strategy_name if strategy else 'N/A'}
Strategy Confidence: {strategy.confidence*100:.0f}% if strategy else 'N/A'
"""
            
            # Call GROQ for analysis
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert options trader. Provide concise, actionable analysis. Keep responses under 200 words."
                    },
                    {
                        "role": "user",
                        "content": f"Analyze {ticker} for options trading based on this data:\n{context}\n\nProvide: 1) Key insight, 2) Recommended trade, 3) Risk to watch"
                    }
                ],
                "max_tokens": 400,
                "temperature": 0.7
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                ai_response = data['choices'][0]['message']['content']
                
                return {
                    'ticker': ticker,
                    'analysis': ai_response,
                    'sentiment': sentiment,
                    'prediction': {
                        'direction': prediction.direction if prediction else 'N/A',
                        'probability': prediction.probability if prediction else 0,
                        'target': prediction.predicted_price if prediction else 0
                    } if prediction else None,
                    'strategy': {
                        'name': strategy.strategy_name if strategy else 'N/A',
                        'confidence': strategy.confidence if strategy else 0
                    } if strategy else None,
                    'source': 'groq_ai',
                    'timestamp': datetime.now().isoformat()
                }
            
            return self._generate_rule_based_analysis(ticker)
            
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            return self._generate_rule_based_analysis(ticker)
    
    def _generate_rule_based_analysis(self, ticker: str) -> Dict:
        """Generate rule-based analysis when AI is unavailable."""
        try:
            from .sentiment_analyzer import quick_sentiment
            from .ai_ml_engine import get_ml_predictor, get_ai_selector
            
            sentiment = quick_sentiment(ticker)
            predictor = get_ml_predictor()
            selector = get_ai_selector()
            
            prediction = predictor.predict_price(ticker, 7)
            strategy = selector.get_best_strategy(ticker)
            
            # Build rule-based analysis
            analysis_parts = []
            
            # Sentiment analysis
            analysis_parts.append(f"**Sentiment:** {sentiment['sentiment_label']}")
            if sentiment['signals']:
                top_signal = sentiment['signals'][0]
                analysis_parts.append(f"  - {top_signal['source']}: {top_signal['summary']}")
            
            # Price prediction
            if prediction:
                analysis_parts.append(f"**7-Day Outlook:** {prediction.direction.title()} ({prediction.probability*100:.0f}% confidence)")
                analysis_parts.append(f"  - Target: ${prediction.predicted_price:.2f}")
            
            # Strategy recommendation
            if strategy:
                analysis_parts.append(f"**Recommended Strategy:** {strategy.strategy_name}")
                analysis_parts.append(f"  - POP: {strategy.probability_of_profit*100:.0f}%")
                analysis_parts.append(f"  - Risk/Reward: {strategy.risk_reward_ratio:.1f}:1")
            
            return {
                'ticker': ticker,
                'analysis': '\n'.join(analysis_parts),
                'sentiment': sentiment,
                'prediction': {
                    'direction': prediction.direction if prediction else 'N/A',
                    'probability': prediction.probability if prediction else 0,
                    'target': prediction.predicted_price if prediction else 0
                } if prediction else None,
                'strategy': {
                    'name': strategy.strategy_name if strategy else 'N/A',
                    'confidence': strategy.confidence if strategy else 0
                } if strategy else None,
                'source': 'rule_based',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'ticker': ticker,
                'analysis': f"Unable to generate analysis: {str(e)}",
                'source': 'error',
                'timestamp': datetime.now().isoformat()
            }


# Singleton instance
_proactive_advisor = None

def get_proactive_advisor() -> ProactiveAdvisor:
    """Get singleton proactive advisor."""
    global _proactive_advisor
    if _proactive_advisor is None:
        _proactive_advisor = ProactiveAdvisor()
    return _proactive_advisor


def get_quick_ideas(count: int = 5) -> List[Dict]:
    """Get quick trade ideas."""
    advisor = get_proactive_advisor()
    return advisor.get_quick_trade_ideas(count)


def get_daily_briefing() -> Dict:
    """Get daily market briefing."""
    advisor = get_proactive_advisor()
    return advisor.generate_daily_briefing()


def get_regime_recommendations() -> Dict:
    """Get market regime-based recommendations."""
    advisor = get_proactive_advisor()
    return advisor.get_market_regime_recommendation()
