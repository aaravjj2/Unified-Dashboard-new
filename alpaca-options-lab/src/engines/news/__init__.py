"""
News & Sentiment Engine Package
===============================
Phase 2: Local AI & Sentiment Classification

Provides unified access to multiple news and sentiment data sources:
- Finnhub (sentiment scores, news)
- FinViz (headlines scraping with VADER sentiment classification)
- StockTwits (retail sentiment)
- NewsAPI (macro context)
- Tiingo (backup source)

Phase 2 Additions:
- HeadlineSentimentAnalyzer: VADER/TextBlob-based sentiment classification
- Headlines now include sentiment_label: 'Positive', 'Negative', 'Neutral'
- Filter headlines by sentiment type for UI

Usage:
    from financial_dashboard.engines.news import HybridNewsClient, get_news_client
    
    client = get_news_client()  # Singleton
    sentiment = client.get_retail_sentiment('NVDA')
    
    # Get all headlines with sentiment classification
    headlines = client.get_finviz_headlines('TSLA')
    for h in headlines:
        print(f"{h.sentiment_label}: {h.headline}")
    
    # Filter to only positive headlines
    good_news = client.get_finviz_headlines('NVDA', sentiment_filter='Positive')
"""

from .hybrid_client import (
    HybridNewsClient, 
    SentimentResult, 
    NewsHeadline, 
    HeadlineSentiment,
    HeadlineSentimentAnalyzer,
    get_news_client,
    get_sentiment_analyzer
)

__all__ = [
    'HybridNewsClient', 
    'SentimentResult', 
    'NewsHeadline', 
    'HeadlineSentiment',
    'HeadlineSentimentAnalyzer',
    'get_news_client',
    'get_sentiment_analyzer'
]

