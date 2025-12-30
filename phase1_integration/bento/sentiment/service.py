"""
BentoML Sentiment Classification Service

Serves FinBERT/BERT models for financial sentiment analysis.
"""

from __future__ import annotations
import bentoml
import numpy as np
from typing import Dict, List, Any
import logging
import re

logger = logging.getLogger(__name__)


class MockSentimentModel:
    """Mock sentiment model using keyword matching"""
    
    POSITIVE_WORDS = {
        "bullish", "surge", "rally", "gain", "profit", "growth",
        "beat", "upgrade", "outperform", "strong", "buy", "positive"
    }
    NEGATIVE_WORDS = {
        "bearish", "plunge", "crash", "loss", "decline", "weak",
        "miss", "downgrade", "underperform", "sell", "negative", "risk"
    }
    
    def predict(self, texts: List[str]) -> np.ndarray:
        """Return sentiment scores based on keywords"""
        results = []
        for text in texts:
            text_lower = text.lower()
            words = set(re.findall(r'\w+', text_lower))
            
            pos_count = len(words & self.POSITIVE_WORDS)
            neg_count = len(words & self.NEGATIVE_WORDS)
            
            if pos_count > neg_count:
                results.append([0.7, 0.1, 0.2])  # positive, negative, neutral
            elif neg_count > pos_count:
                results.append([0.1, 0.7, 0.2])
            else:
                results.append([0.2, 0.2, 0.6])
        
        return np.array(results)


try:
    model = bentoml.models.get("sentiment:latest").load()
    logger.info("Loaded trained sentiment model")
except Exception:
    model = MockSentimentModel()
    logger.info("Using mock sentiment model")


@bentoml.service(
    name="sentiment",
    resources={"cpu": "1", "memory": "1Gi"},
    traffic={"timeout": 60},
)
class SentimentService:
    """
    BentoML service for financial sentiment analysis.
    
    Endpoints:
        POST /analyze - Single text analysis
        POST /batch_analyze - Batch analysis
        GET /healthz - Health check
    """
    
    def __init__(self):
        self.model = model
        self.labels = ["positive", "negative", "neutral"]
        logger.info("SentimentService initialized")
    
    @bentoml.api
    async def analyze(
        self,
        text: str,
        symbol: str = None,
    ) -> Dict[str, Any]:
        """
        Analyze sentiment of text.
        
        Args:
            text: Text to analyze
            symbol: Optional symbol context
        
        Returns:
            Sentiment classification with scores
        """
        try:
            # Get prediction
            probs = self.model.predict([text])[0]
            
            # Determine sentiment
            sentiment_idx = np.argmax(probs)
            sentiment = self.labels[sentiment_idx]
            confidence = float(probs[sentiment_idx])
            
            return {
                "text": text[:100] + "..." if len(text) > 100 else text,
                "symbol": symbol,
                "sentiment": sentiment,
                "confidence": round(confidence, 4),
                "score_positive": round(float(probs[0]), 4),
                "score_negative": round(float(probs[1]), 4),
                "score_neutral": round(float(probs[2]), 4),
                "model_version": "1.0.0",
            }
        except Exception as e:
            logger.error(f"Sentiment error: {e}")
            return {
                "text": text[:100],
                "sentiment": "neutral",
                "confidence": 0.0,
                "error": str(e),
            }
    
    @bentoml.api
    async def batch_analyze(
        self,
        texts: List[str],
        symbol: str = None,
    ) -> Dict[str, Any]:
        """Analyze multiple texts"""
        results = []
        for text in texts:
            result = await self.analyze(text, symbol)
            results.append(result)
        
        # Aggregate sentiment
        sentiments = [r["sentiment"] for r in results]
        avg_confidence = np.mean([r["confidence"] for r in results])
        
        sentiment_counts = {
            "positive": sentiments.count("positive"),
            "negative": sentiments.count("negative"),
            "neutral": sentiments.count("neutral"),
        }
        
        overall = max(sentiment_counts, key=sentiment_counts.get)
        
        return {
            "results": results,
            "overall_sentiment": overall,
            "avg_confidence": round(float(avg_confidence), 4),
            "sentiment_counts": sentiment_counts,
        }
    
    @bentoml.api
    def healthz(self) -> Dict[str, str]:
        return {"status": "healthy", "service": "sentiment"}
