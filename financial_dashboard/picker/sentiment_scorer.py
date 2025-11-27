"""
Sentiment Scorer - Analyze sentiment from multiple sources (simplified MVP).
"""

import logging
from typing import Dict
import random

logger = logging.getLogger(__name__)


class SentimentScorer:
    """Score stocks based on sentiment indicators."""
    
    def __init__(self):
        self.weight = 0.25  # 25% weight in ensemble
    
    def score(self, ticker: str) -> float:
        """
        Calculate sentiment score for a stock (0-100).
        
        Factors (MVP - simplified):
        - Analyst recommendations (40%)
        - Price target vs current (30%)
        - Institutional ownership (30%)
        
        Returns:
            Score 0-100 (higher is better)
        """
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Analyst recommendations (strong buy = best, sell = worst)
            recommendations = stock.recommendations
            analyst_score = 50.0  # Default
            
            if recommendations is not None and not recommendations.empty:
                # Get most recent recommendations
                recent = recommendations.tail(5)
                
                # Count recommendations
                strong_buy = recent['strongBuy'].sum() if 'strongBuy' in recent.columns else 0
                buy = recent['buy'].sum() if 'buy' in recent.columns else 0
                hold = recent['hold'].sum() if 'hold' in recent.columns else 0
                sell = recent['sell'].sum() if 'sell' in recent.columns else 0
                strong_sell = recent['strongSell'].sum() if 'strongSell' in recent.columns else 0
                
                total = strong_buy + buy + hold + sell + strong_sell
                
                if total > 0:
                    # Weighted score (strong buy = 100, buy = 75, hold = 50, sell = 25, strong sell = 0)
                    analyst_score = (
                        (strong_buy * 100 + buy * 75 + hold * 50 + sell * 25 + strong_sell * 0) / total
                    )
            
            # Price target vs current price
            target_price = info.get('targetMeanPrice')
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            
            target_score = 50.0  # Default
            
            if target_price and current_price:
                upside = ((target_price - current_price) / current_price) * 100
                # Map -20% to +40% upside to 0-100 score
                target_score = max(0, min(100, ((upside + 20) / 60) * 100))
            
            # Institutional ownership (higher = better)
            inst_ownership = info.get('heldPercentInstitutions', 0) * 100
            inst_score = min(100, inst_ownership * 1.5)  # Scale 0-70% ownership to 0-100 score
            
            # Weighted average
            total_score = (
                analyst_score * 0.40 +
                target_score * 0.30 +
                inst_score * 0.30
            )
            
            logger.info(f"{ticker} sentiment: {total_score:.1f} (analyst:{analyst_score:.1f}, target:{target_score:.1f}, inst:{inst_score:.1f})")
            
            return round(total_score, 1)
            
        except Exception as e:
            logger.error(f"Sentiment scoring error for {ticker}: {e}")
            return 50.0  # Neutral score on error
    
    def get_details(self, ticker: str) -> Dict:
        """Get detailed sentiment metrics."""
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            info = stock.info
            
            details = {
                'analyst_rating': info.get('recommendationKey', 'N/A'),
                'target_price': info.get('targetMeanPrice', 0),
                'current_price': info.get('currentPrice') or info.get('regularMarketPrice', 0),
                'institutional_ownership': info.get('heldPercentInstitutions', 0) * 100
            }
            
            return details
            
        except:
            return {}
