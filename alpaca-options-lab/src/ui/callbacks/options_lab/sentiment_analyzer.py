"""
Sentiment Analyzer
Aggregates sentiment from multiple sources (News, Social, Insider).
"""

import logging
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def get_finnhub_sentiment(ticker: str) -> Dict:
    """Get sentiment from Finnhub."""
    api_key = os.getenv('FINNHUB_API_KEY')
    if not api_key:
        return {'score': 0, 'label': 'Neutral (No Key)'}
        
    try:
        # News sentiment
        url = f"https://finnhub.io/api/v1/news-sentiment?symbol={ticker}&token={api_key}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            sentiment = data.get('sentiment', {})
            bullish = sentiment.get('bullishPercent', 0.5)
            bearish = sentiment.get('bearishPercent', 0.5)
            
            score = bullish - bearish # -1 to 1 roughly
            
            if score > 0.2:
                label = 'Bullish'
            elif score < -0.2:
                label = 'Bearish'
            else:
                label = 'Neutral'
                
            return {'score': score, 'label': label, 'bullish': bullish, 'bearish': bearish}
            
    except Exception as e:
        logger.error(f"Finnhub error: {e}")
        
    return {'score': 0, 'label': 'Neutral'}

def get_insider_sentiment(ticker: str) -> Dict:
    """Get insider sentiment (mock/stub for now)."""
    # In a real app, we'd query SEC API or Finnhub insider endpoint
    return {'score': 0, 'label': 'Neutral', 'recent_trades': 0}

def get_comprehensive_sentiment(ticker: str) -> Dict:
    """Aggregate sentiment from all sources."""
    finnhub = get_finnhub_sentiment(ticker)
    insider = get_insider_sentiment(ticker)
    
    # Simple weighted average
    total_score = finnhub['score'] # + insider['score']
    
    if total_score > 0.2:
        overall = 'Bullish'
    elif total_score < -0.2:
        overall = 'Bearish'
    else:
        overall = 'Neutral'
        
    return {
        'overall': overall,
        'score': total_score,
        'sources': {
            'news': finnhub,
            'insider': insider
        }
    }
