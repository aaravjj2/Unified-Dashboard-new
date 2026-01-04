"""
News Sentiment Engine

Real-time news ingestion and NLP sentiment analysis:
- Multiple news source integration
- FinBERT-based sentiment analysis
- Earnings/events impact scoring
- Trading signal generation
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
import hashlib

import numpy as np

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class Sentiment(Enum):
    """Sentiment classification"""
    VERY_BEARISH = -2
    BEARISH = -1
    NEUTRAL = 0
    BULLISH = 1
    VERY_BULLISH = 2


class NewsCategory(Enum):
    """News category classification"""
    EARNINGS = "earnings"
    MACRO = "macro"
    COMPANY = "company"
    SECTOR = "sector"
    ANALYST = "analyst"
    OPTIONS = "options"
    INSIDER = "insider"
    REGULATORY = "regulatory"
    GENERAL = "general"


@dataclass
class NewsArticle:
    """Represents a news article"""
    id: str
    title: str
    summary: str
    source: str
    url: str
    published_at: datetime
    symbols: List[str]
    categories: List[NewsCategory]
    sentiment: Optional[Sentiment] = None
    sentiment_score: float = 0.0
    sentiment_confidence: float = 0.0
    impact_score: float = 0.0
    processed_at: Optional[datetime] = None
    
    def __hash__(self):
        return hash(self.id)


@dataclass
class SentimentSignal:
    """Trading signal based on sentiment"""
    symbol: str
    signal_type: str  # entry, exit, adjustment
    direction: str  # bullish, bearish
    strength: float  # 0-1
    reasoning: str
    articles: List[str]  # Article IDs
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None


class FinBERTSentimentAnalyzer:
    """
    FinBERT-based sentiment analysis for financial text.
    
    Uses the ProsusAI/finbert model for financial sentiment classification.
    Falls back to rule-based analysis if model unavailable.
    """
    
    # Financial sentiment keywords
    BULLISH_KEYWORDS = {
        "strong": 0.3, "surge": 0.5, "beat": 0.4, "exceed": 0.3,
        "growth": 0.3, "upgrade": 0.5, "buy": 0.4, "bullish": 0.6,
        "outperform": 0.4, "rally": 0.4, "gain": 0.3, "positive": 0.3,
        "optimistic": 0.4, "record": 0.3, "breakout": 0.5, "momentum": 0.3,
    }
    
    BEARISH_KEYWORDS = {
        "weak": -0.3, "plunge": -0.5, "miss": -0.4, "below": -0.3,
        "decline": -0.3, "downgrade": -0.5, "sell": -0.4, "bearish": -0.6,
        "underperform": -0.4, "crash": -0.5, "loss": -0.3, "negative": -0.3,
        "pessimistic": -0.4, "concern": -0.3, "warning": -0.4, "risk": -0.2,
    }
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = "cpu"
        self._model_loaded = False
        
    async def load_model(self):
        """Load FinBERT model (lazy loading)"""
        if self._model_loaded:
            return
            
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            import torch
            
            logger.info("loading_finbert_model")
            
            self.tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
            self.model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
            
            # Use GPU if available
            if torch.cuda.is_available():
                self.device = "cuda"
                self.model = self.model.to(self.device)
                
            self.model.eval()
            self._model_loaded = True
            
            logger.info("finbert_model_loaded", device=self.device)
            
        except ImportError:
            logger.warning("transformers_not_installed_using_rule_based")
        except Exception as e:
            logger.error("finbert_load_failed", error=str(e))
            
    async def analyze(self, text: str) -> Tuple[Sentiment, float, float]:
        """
        Analyze sentiment of financial text.
        
        Returns:
            Tuple of (Sentiment, score (-1 to 1), confidence (0 to 1))
        """
        if self._model_loaded and self.model is not None:
            return await self._analyze_with_model(text)
        else:
            return self._analyze_rule_based(text)
            
    async def _analyze_with_model(self, text: str) -> Tuple[Sentiment, float, float]:
        """Analyze using FinBERT model"""
        import torch
        
        # Tokenize
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )
        
        if self.device == "cuda":
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
        # Inference
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)[0]
            
        # FinBERT outputs: [negative, neutral, positive]
        neg_prob = probs[0].item()
        neu_prob = probs[1].item()
        pos_prob = probs[2].item()
        
        # Calculate score and confidence
        score = pos_prob - neg_prob
        confidence = max(neg_prob, neu_prob, pos_prob)
        
        # Map to sentiment
        if score > 0.5:
            sentiment = Sentiment.VERY_BULLISH
        elif score > 0.2:
            sentiment = Sentiment.BULLISH
        elif score < -0.5:
            sentiment = Sentiment.VERY_BEARISH
        elif score < -0.2:
            sentiment = Sentiment.BEARISH
        else:
            sentiment = Sentiment.NEUTRAL
            
        return sentiment, score, confidence
        
    def _analyze_rule_based(self, text: str) -> Tuple[Sentiment, float, float]:
        """Fallback rule-based sentiment analysis"""
        text_lower = text.lower()
        
        score = 0.0
        matches = 0
        
        # Check bullish keywords
        for keyword, weight in self.BULLISH_KEYWORDS.items():
            if keyword in text_lower:
                score += weight
                matches += 1
                
        # Check bearish keywords
        for keyword, weight in self.BEARISH_KEYWORDS.items():
            if keyword in text_lower:
                score += weight
                matches += 1
                
        # Normalize
        if matches > 0:
            score = score / matches
            confidence = min(0.5 + matches * 0.1, 0.9)
        else:
            confidence = 0.3
            
        # Map to sentiment
        if score > 0.4:
            sentiment = Sentiment.VERY_BULLISH
        elif score > 0.15:
            sentiment = Sentiment.BULLISH
        elif score < -0.4:
            sentiment = Sentiment.VERY_BEARISH
        elif score < -0.15:
            sentiment = Sentiment.BEARISH
        else:
            sentiment = Sentiment.NEUTRAL
            
        return sentiment, score, confidence


class NewsAggregator:
    """
    Aggregates news from multiple sources.
    
    Supported sources:
    - Alpaca News API
    - Polygon.io News
    - Benzinga (via API)
    - SEC EDGAR filings
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._sources: Dict[str, bool] = {
            "alpaca": True,
            "polygon": False,
            "benzinga": False,
            "edgar": False,
        }
        
    async def fetch_news(
        self,
        symbols: Optional[List[str]] = None,
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[NewsArticle]:
        """
        Fetch news articles from all enabled sources.
        """
        articles = []
        
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(hours=24)
            
        tasks = []
        
        if self._sources.get("alpaca"):
            tasks.append(self._fetch_alpaca_news(symbols, since, limit))
            
        if self._sources.get("polygon"):
            tasks.append(self._fetch_polygon_news(symbols, since, limit))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                articles.extend(result)
            elif isinstance(result, Exception):
                logger.error("news_fetch_error", error=str(result))
                
        # Deduplicate by title similarity
        articles = self._deduplicate(articles)
        
        return articles
        
    async def _fetch_alpaca_news(
        self,
        symbols: Optional[List[str]],
        since: datetime,
        limit: int,
    ) -> List[NewsArticle]:
        """Fetch news from Alpaca API"""
        try:
            from alpaca.data.historical.news import NewsClient
            from alpaca.data.requests import NewsRequest
            
            # This would use actual Alpaca API
            # For now, return mock data
            return self._generate_mock_news(symbols, limit)
            
        except ImportError:
            logger.warning("alpaca_news_client_not_available")
            return self._generate_mock_news(symbols, limit)
            
    async def _fetch_polygon_news(
        self,
        symbols: Optional[List[str]],
        since: datetime,
        limit: int,
    ) -> List[NewsArticle]:
        """Fetch news from Polygon.io API"""
        # Implementation would use Polygon API
        return []
        
    def _generate_mock_news(
        self,
        symbols: Optional[List[str]],
        limit: int,
    ) -> List[NewsArticle]:
        """Generate mock news for testing"""
        if symbols is None:
            symbols = ["SPY", "QQQ", "AAPL"]
            
        mock_headlines = [
            ("Tech stocks surge on strong earnings outlook", Sentiment.BULLISH),
            ("Fed signals potential rate cuts in 2024", Sentiment.BULLISH),
            ("Market volatility rises amid geopolitical concerns", Sentiment.BEARISH),
            ("Options activity shows bullish sentiment", Sentiment.BULLISH),
            ("Analysts upgrade sector outlook", Sentiment.BULLISH),
            ("Economic data misses expectations", Sentiment.BEARISH),
            ("Institutional investors increase positions", Sentiment.BULLISH),
            ("Trade tensions weigh on markets", Sentiment.BEARISH),
        ]
        
        articles = []
        for i, (headline, sentiment) in enumerate(mock_headlines[:limit]):
            symbol = symbols[i % len(symbols)]
            article_id = hashlib.md5(f"{headline}{i}".encode()).hexdigest()[:12]
            
            articles.append(NewsArticle(
                id=article_id,
                title=f"{symbol}: {headline}",
                summary=f"Full analysis of {headline.lower()}...",
                source="mock",
                url=f"https://news.example.com/{article_id}",
                published_at=datetime.now(timezone.utc) - timedelta(hours=i),
                symbols=[symbol],
                categories=[NewsCategory.GENERAL],
                sentiment=sentiment,
                sentiment_score=0.3 if sentiment == Sentiment.BULLISH else -0.3,
                sentiment_confidence=0.7,
            ))
            
        return articles
        
    def _deduplicate(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Remove duplicate articles based on title similarity"""
        seen_titles = set()
        unique = []
        
        for article in articles:
            # Simple dedup by normalized title
            normalized = re.sub(r'\W+', '', article.title.lower())
            if normalized not in seen_titles:
                seen_titles.add(normalized)
                unique.append(article)
                
        return unique


class NewsSentimentEngine:
    """
    Main sentiment engine that coordinates news aggregation,
    sentiment analysis, and signal generation.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.aggregator = NewsAggregator(config)
        self.analyzer = FinBERTSentimentAnalyzer()
        self.article_cache: Dict[str, NewsArticle] = {}
        self.symbol_sentiment: Dict[str, List[float]] = {}
        self._running = False
        self._task = None
        
        # Configurable thresholds
        self.signal_threshold = self.config.get("signal_threshold", 0.4)
        self.min_articles = self.config.get("min_articles_for_signal", 3)
        self.sentiment_window = self.config.get("sentiment_window_hours", 24)
        
    async def start(self):
        """Start the sentiment engine"""
        logger.info("sentiment_engine_starting")
        await self.analyzer.load_model()
        self._running = True
        self._task = asyncio.create_task(self._processing_loop())
        logger.info("sentiment_engine_started")
        
    async def stop(self):
        """Stop the sentiment engine"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("sentiment_engine_stopped")
        
    async def _processing_loop(self):
        """Main processing loop"""
        while self._running:
            try:
                await self.process_news_batch()
                await asyncio.sleep(60)  # Process every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("sentiment_processing_error", error=str(e))
                await asyncio.sleep(30)
                
    async def process_news_batch(
        self,
        symbols: Optional[List[str]] = None,
    ) -> List[NewsArticle]:
        """
        Fetch and process a batch of news articles.
        """
        articles = await self.aggregator.fetch_news(symbols=symbols)
        
        processed = []
        for article in articles:
            if article.id in self.article_cache:
                processed.append(self.article_cache[article.id])
                continue
                
            # Analyze sentiment if not already done
            if article.sentiment is None:
                text = f"{article.title} {article.summary}"
                sentiment, score, confidence = await self.analyzer.analyze(text)
                article.sentiment = sentiment
                article.sentiment_score = score
                article.sentiment_confidence = confidence
                
            # Calculate impact score
            article.impact_score = self._calculate_impact(article)
            article.processed_at = datetime.now(timezone.utc)
            
            # Cache article
            self.article_cache[article.id] = article
            
            # Update symbol sentiment
            for symbol in article.symbols:
                if symbol not in self.symbol_sentiment:
                    self.symbol_sentiment[symbol] = []
                self.symbol_sentiment[symbol].append(article.sentiment_score)
                
            processed.append(article)
            
        logger.info(
            "news_batch_processed",
            total=len(articles),
            new=len([a for a in processed if a.processed_at]),
        )
        
        return processed
        
    def _calculate_impact(self, article: NewsArticle) -> float:
        """
        Calculate the potential market impact of an article.
        
        Factors:
        - Source credibility
        - Category importance
        - Sentiment strength
        - Recency
        """
        # Base impact from sentiment confidence
        impact = article.sentiment_confidence
        
        # Category multipliers
        category_weights = {
            NewsCategory.EARNINGS: 1.5,
            NewsCategory.MACRO: 1.3,
            NewsCategory.ANALYST: 1.2,
            NewsCategory.OPTIONS: 1.1,
            NewsCategory.INSIDER: 1.4,
            NewsCategory.REGULATORY: 1.3,
        }
        
        for cat in article.categories:
            if cat in category_weights:
                impact *= category_weights[cat]
                
        # Recency decay
        hours_old = (datetime.now(timezone.utc) - article.published_at).seconds / 3600
        recency_factor = max(0.5, 1.0 - hours_old * 0.02)
        impact *= recency_factor
        
        return min(impact, 1.0)
        
    def get_sentiment_signal(self, symbol: str) -> Optional[SentimentSignal]:
        """
        Generate trading signal based on aggregated sentiment.
        """
        if symbol not in self.symbol_sentiment:
            return None
            
        scores = self.symbol_sentiment[symbol]
        if len(scores) < self.min_articles:
            return None
            
        # Calculate aggregate sentiment
        avg_sentiment = np.mean(scores[-20:])  # Last 20 articles
        sentiment_std = np.std(scores[-20:]) if len(scores) >= 2 else 0.5
        
        # Signal strength based on consistency
        strength = abs(avg_sentiment) * (1.0 - min(sentiment_std, 0.5))
        
        if strength < self.signal_threshold:
            return None
            
        # Determine direction
        direction = "bullish" if avg_sentiment > 0 else "bearish"
        
        # Get supporting articles
        relevant_articles = [
            a.id for a in self.article_cache.values()
            if symbol in a.symbols
        ][:5]
        
        return SentimentSignal(
            symbol=symbol,
            signal_type="entry",
            direction=direction,
            strength=strength,
            reasoning=f"Aggregate sentiment {direction} ({avg_sentiment:.2f}) from {len(scores)} articles",
            articles=relevant_articles,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=4),
        )
        
    def get_symbol_sentiment_summary(self, symbol: str) -> Dict:
        """
        Get sentiment summary for a symbol.
        """
        if symbol not in self.symbol_sentiment:
            return {
                "symbol": symbol,
                "sentiment": "neutral",
                "score": 0.0,
                "article_count": 0,
                "trend": "stable",
            }
            
        scores = self.symbol_sentiment[symbol]
        avg_score = np.mean(scores) if scores else 0.0
        recent_avg = np.mean(scores[-5:]) if len(scores) >= 5 else avg_score
        
        # Determine trend
        if len(scores) >= 5:
            older_avg = np.mean(scores[-10:-5]) if len(scores) >= 10 else avg_score
            if recent_avg > older_avg + 0.1:
                trend = "improving"
            elif recent_avg < older_avg - 0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
            
        # Map score to sentiment label
        if avg_score > 0.3:
            sentiment_label = "bullish"
        elif avg_score < -0.3:
            sentiment_label = "bearish"
        else:
            sentiment_label = "neutral"
            
        return {
            "symbol": symbol,
            "sentiment": sentiment_label,
            "score": round(avg_score, 3),
            "article_count": len(scores),
            "trend": trend,
            "recent_score": round(recent_avg, 3),
        }
        
    def get_market_sentiment_overview(self) -> Dict:
        """
        Get overall market sentiment overview.
        """
        all_scores = []
        symbol_sentiments = {}
        
        for symbol, scores in self.symbol_sentiment.items():
            if scores:
                symbol_sentiments[symbol] = np.mean(scores)
                all_scores.extend(scores)
                
        overall = np.mean(all_scores) if all_scores else 0.0
        
        # Count by sentiment
        bullish_count = sum(1 for s in symbol_sentiments.values() if s > 0.2)
        bearish_count = sum(1 for s in symbol_sentiments.values() if s < -0.2)
        neutral_count = len(symbol_sentiments) - bullish_count - bearish_count
        
        return {
            "overall_sentiment": "bullish" if overall > 0.2 else "bearish" if overall < -0.2 else "neutral",
            "overall_score": round(overall, 3),
            "symbols_analyzed": len(symbol_sentiments),
            "bullish_symbols": bullish_count,
            "bearish_symbols": bearish_count,
            "neutral_symbols": neutral_count,
            "total_articles": len(self.article_cache),
            "most_bullish": max(symbol_sentiments.items(), key=lambda x: x[1])[0] if symbol_sentiments else None,
            "most_bearish": min(symbol_sentiments.items(), key=lambda x: x[1])[0] if symbol_sentiments else None,
        }


# Singleton instance
news_sentiment_engine = NewsSentimentEngine()
