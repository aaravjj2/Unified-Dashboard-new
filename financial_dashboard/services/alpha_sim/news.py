"""
AlphaSim News - FinBERT-based sentiment analysis for news aggregation.

Provides NEWS_SENTIMENT endpoint functionality using either:
1. Local FinBERT model (if transformers available)
2. Mock sentiment (fallback for dev/testing)
"""
import os
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import random

from .cache import get_cache, CacheTTL


# Try to import transformers for FinBERT
FINBERT_AVAILABLE = False
_finbert_model = None
_finbert_tokenizer = None

try:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    import torch
    FINBERT_AVAILABLE = True
except ImportError:
    pass


def _load_finbert():
    """Lazy load FinBERT model."""
    global _finbert_model, _finbert_tokenizer
    
    if not FINBERT_AVAILABLE:
        return None, None
    
    if _finbert_model is None:
        try:
            model_name = os.getenv("FINBERT_MODEL", "ProsusAI/finbert")
            _finbert_tokenizer = AutoTokenizer.from_pretrained(model_name)
            _finbert_model = AutoModelForSequenceClassification.from_pretrained(model_name)
            _finbert_model.eval()
        except Exception as e:
            print(f"Error loading FinBERT model: {e}")
            return None, None
    
    return _finbert_model, _finbert_tokenizer


def _score_text_finbert(text: str) -> Dict[str, float]:
    """
    Score a single text using FinBERT.
    
    Returns:
        Dict with 'positive', 'negative', 'neutral' probabilities
    """
    model, tokenizer = _load_finbert()
    
    if model is None or tokenizer is None:
        return _score_text_mock(text)
    
    try:
        import torch
        
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        
        with torch.no_grad():
            outputs = model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)[0]
        
        # FinBERT labels: positive, negative, neutral
        return {
            "positive": float(probs[0]),
            "negative": float(probs[1]),
            "neutral": float(probs[2])
        }
    except Exception as e:
        print(f"FinBERT scoring error: {e}")
        return _score_text_mock(text)


def _score_text_mock(text: str) -> Dict[str, float]:
    """
    Generate deterministic mock sentiment based on text hash.
    Used when FinBERT is unavailable.
    """
    # Create deterministic scores based on text hash
    text_hash = int(hashlib.md5(text.encode()).hexdigest(), 16)
    
    # Generate pseudo-random but deterministic scores
    random.seed(text_hash)
    pos = random.uniform(0.1, 0.9)
    neg = random.uniform(0.1, 0.9 - pos)
    neu = 1.0 - pos - neg
    
    return {
        "positive": pos,
        "negative": neg,
        "neutral": neu
    }


def _fetch_news_headlines(symbol: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Fetch news headlines for a symbol.
    
    In production, this would call a news API (e.g., Finnhub, NewsAPI).
    For MVP, we generate synthetic headlines.
    """
    # Generate synthetic but deterministic headlines
    base_headlines = [
        f"{symbol} reports strong quarterly earnings",
        f"Analysts upgrade {symbol} stock to Buy",
        f"{symbol} announces new product line",
        f"Market volatility impacts {symbol} shares",
        f"{symbol} CEO discusses growth strategy",
        f"Institutional investors increase {symbol} holdings",
        f"{symbol} faces regulatory scrutiny",
        f"Tech sector rally lifts {symbol}",
        f"{symbol} expands into new markets",
        f"Competition intensifies for {symbol}",
        f"{symbol} beats revenue expectations",
        f"Supply chain concerns affect {symbol}",
        f"{symbol} partners with major tech company",
        f"Dividend announcement from {symbol}",
        f"{symbol} stock reaches 52-week high",
        f"Insider trading activity at {symbol}",
        f"{symbol} launches sustainability initiative",
        f"Merger rumors surround {symbol}",
        f"{symbol} restructures operations",
        f"Consumer demand drives {symbol} growth",
    ]
    
    # Create deterministic selection based on symbol
    symbol_hash = int(hashlib.md5(symbol.encode()).hexdigest(), 16)
    random.seed(symbol_hash + datetime.utcnow().toordinal())
    
    selected = random.sample(base_headlines, min(limit, len(base_headlines)))
    
    articles = []
    base_time = datetime.utcnow()
    
    for i, headline in enumerate(selected):
        articles.append({
            "title": headline,
            "source": random.choice(["Reuters", "Bloomberg", "CNBC", "WSJ", "MarketWatch"]),
            "published_at": (base_time - timedelta(hours=i * 2)).isoformat(),
            "url": f"https://example.com/news/{symbol.lower()}/{i}"
        })
    
    return articles


def score_articles(
    articles: List[Dict[str, Any]],
    use_finbert: bool = True
) -> List[Dict[str, Any]]:
    """
    Score a list of articles for sentiment.
    
    Args:
        articles: List of article dicts with 'title' key
        use_finbert: Whether to use FinBERT (if available)
    
    Returns:
        Articles with added 'sentiment' scores
    """
    scored = []
    
    for article in articles:
        title = article.get("title", "")
        
        if use_finbert and FINBERT_AVAILABLE:
            scores = _score_text_finbert(title)
        else:
            scores = _score_text_mock(title)
        
        scored_article = article.copy()
        scored_article["sentiment"] = scores
        scored_article["sentiment_label"] = max(scores, key=scores.get)
        scored_article["sentiment_score"] = scores.get("positive", 0) - scores.get("negative", 0)
        scored.append(scored_article)
    
    return scored


def aggregate_sentiment(scored_articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate sentiment scores across articles.
    
    Returns:
        Dict with aggregate_score, positive/neutral/negative counts, etc.
    """
    if not scored_articles:
        return {
            "aggregate_score": 0.0,
            "positive": 0,
            "neutral": 0,
            "negative": 0,
            "articles": 0
        }
    
    pos_count = sum(1 for a in scored_articles if a.get("sentiment_label") == "positive")
    neg_count = sum(1 for a in scored_articles if a.get("sentiment_label") == "negative")
    neu_count = sum(1 for a in scored_articles if a.get("sentiment_label") == "neutral")
    
    # Calculate aggregate score (-1 to 1)
    total_score = sum(a.get("sentiment_score", 0) for a in scored_articles)
    avg_score = total_score / len(scored_articles) if scored_articles else 0.0
    
    return {
        "aggregate_score": round(avg_score, 4),
        "positive": pos_count,
        "neutral": neu_count,
        "negative": neg_count,
        "articles": len(scored_articles)
    }


def fetch_and_score(
    symbol: str,
    limit: int = 20,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Main entry point: fetch news and compute sentiment for a symbol.
    
    Args:
        symbol: Ticker symbol
        limit: Maximum number of articles to fetch
        use_cache: Whether to use caching
    
    Returns:
        AlphaV-compatible NEWS_SENTIMENT response
    """
    cache = get_cache()
    cache_key = f"news_sentiment:{symbol}:{limit}"
    
    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
    
    # Fetch headlines
    articles = _fetch_news_headlines(symbol, limit)
    
    # Score articles
    scored = score_articles(articles)
    
    # Aggregate sentiment
    aggregated = aggregate_sentiment(scored)
    
    # Build AlphaV-compatible response
    result = build_news_sentiment_response(symbol, aggregated, scored)
    
    # Cache result
    if use_cache:
        cache.set(cache_key, result, ttl=CacheTTL.NEWS_SENTIMENT)
    
    return result


def build_news_sentiment_response(
    symbol: str,
    aggregated: Dict[str, Any],
    articles: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Build AlphaV-compatible NEWS_SENTIMENT response.
    """
    from .schema import build_meta_data
    
    response = {
        "Meta Data": build_meta_data(
            "News Sentiment (AlphaSim)",
            symbol,
            extra={"Source": "FinBERT" if FINBERT_AVAILABLE else "Mock"}
        ),
        "Sentiment": aggregated
    }
    
    # Optionally include article-level details
    if articles:
        response["feed"] = [
            {
                "title": a.get("title"),
                "source": a.get("source"),
                "time_published": a.get("published_at"),
                "url": a.get("url"),
                "overall_sentiment_score": round(a.get("sentiment_score", 0), 4),
                "overall_sentiment_label": a.get("sentiment_label"),
                "ticker_sentiment": [
                    {
                        "ticker": symbol,
                        "relevance_score": "1.0",
                        "ticker_sentiment_score": str(round(a.get("sentiment_score", 0), 4)),
                        "ticker_sentiment_label": a.get("sentiment_label")
                    }
                ]
            }
            for a in articles[:10]  # Limit feed to 10 articles
        ]
    
    return response
