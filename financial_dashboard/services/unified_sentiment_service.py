"""
Unified Sentiment Service
=========================
Combines FinGPT, GROQ, and fallback methods for robust sentiment analysis.
Provides market sentiment, news sentiment, and social sentiment.
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger(__name__)

# Try to import FinGPT service
try:
    from financial_dashboard.services.fingpt_sentiment_service import (
        analyze_sentiment_fingpt,
        analyze_sentiment_fallback,
        is_fingpt_available
    )
    FINGPT_IMPORTED = True
except ImportError:
    FINGPT_IMPORTED = False
    logger.warning("FinGPT service not available, using fallback only")


class UnifiedSentimentService:
    """
    Unified sentiment analysis combining multiple sources:
    1. FinGPT (if GPU available) - best for financial text
    2. GROQ API - fast, good general sentiment
    3. Rule-based fallback - always available
    """
    
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_model = "llama-3.3-70b-versatile"
        self.cache = {}  # Simple cache for repeated requests
        self.cache_ttl = 300  # 5 minutes
        
    def _get_cache_key(self, text: str, source: str) -> str:
        """Generate cache key."""
        return f"{source}:{hash(text[:100])}"
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached result is still valid."""
        if key not in self.cache:
            return False
        cached_time = self.cache[key].get("cached_at", 0)
        return (datetime.now().timestamp() - cached_time) < self.cache_ttl
    
    async def analyze_with_groq(self, text: str) -> Dict:
        """
        Analyze sentiment using GROQ API.
        
        Returns:
            Dict with sentiment, score, confidence
        """
        if not self.groq_api_key:
            return self._rule_based_sentiment(text)
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.groq_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.groq_model,
                        "messages": [
                            {
                                "role": "system",
                                "content": """You are a financial sentiment analyzer. Analyze the sentiment of financial text.
Respond ONLY with a JSON object in this exact format:
{"sentiment": "positive|negative|neutral", "score": <float from -1 to 1>, "confidence": <float from 0 to 1>, "key_factors": ["factor1", "factor2"]}"""
                            },
                            {
                                "role": "user",
                                "content": f"Analyze the financial sentiment of this text:\n\n{text}"
                            }
                        ],
                        "temperature": 0.1,
                        "max_tokens": 200
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    # Parse JSON response
                    import json
                    try:
                        result = json.loads(content)
                        result["model"] = "groq-" + self.groq_model
                        result["timestamp"] = datetime.now().isoformat()
                        return result
                    except json.JSONDecodeError:
                        # Extract sentiment from text response
                        return self._parse_text_response(content)
                else:
                    logger.warning(f"GROQ API error: {response.status_code}")
                    return self._rule_based_sentiment(text)
                    
        except Exception as e:
            logger.error(f"GROQ sentiment analysis failed: {e}")
            return self._rule_based_sentiment(text)
    
    def analyze_sync(self, text: str, prefer_local: bool = True) -> Dict:
        """
        Synchronous sentiment analysis.
        
        Args:
            text: Text to analyze
            prefer_local: If True, prefer FinGPT/local; if False, prefer GROQ
            
        Returns:
            Sentiment analysis result
        """
        cache_key = self._get_cache_key(text, "sync")
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        if prefer_local and FINGPT_IMPORTED:
            result = analyze_sentiment_fingpt(text)
        else:
            # Use synchronous rule-based for sync calls
            result = self._rule_based_sentiment(text)
        
        result["cached_at"] = datetime.now().timestamp()
        self.cache[cache_key] = result
        return result
    
    def _rule_based_sentiment(self, text: str) -> Dict:
        """
        Enhanced rule-based sentiment analysis with financial terms.
        """
        text_lower = text.lower()
        
        # Weighted sentiment words (financial domain)
        positive_weights = {
            # Strong positive (weight 2)
            "surge": 2, "soar": 2, "beat expectations": 2, "record high": 2,
            "breakout": 2, "upgrade": 2, "outperform": 2, "strong buy": 2,
            # Moderate positive (weight 1.5)
            "gain": 1.5, "growth": 1.5, "profit": 1.5, "bullish": 1.5,
            "rally": 1.5, "recover": 1.5, "momentum": 1.5,
            # Mild positive (weight 1)
            "rise": 1, "up": 1, "positive": 1, "increase": 1,
            "improve": 1, "buy": 1, "accumulate": 1, "opportunity": 1
        }
        
        negative_weights = {
            # Strong negative (weight 2)
            "crash": 2, "plunge": 2, "miss expectations": 2, "downgrade": 2,
            "bankruptcy": 2, "default": 2, "fraud": 2, "selloff": 2,
            # Moderate negative (weight 1.5)
            "drop": 1.5, "fall": 1.5, "decline": 1.5, "bearish": 1.5,
            "weakness": 1.5, "concern": 1.5, "warning": 1.5,
            # Mild negative (weight 1)
            "down": 1, "loss": 1, "negative": 1, "decrease": 1,
            "sell": 1, "reduce": 1, "risk": 1, "volatility": 1
        }
        
        pos_score = sum(w for term, w in positive_weights.items() if term in text_lower)
        neg_score = sum(w for term, w in negative_weights.items() if term in text_lower)
        
        # Calculate net score
        total = pos_score + neg_score
        if total == 0:
            sentiment = "neutral"
            score = 0.0
            confidence = 0.3
        elif pos_score > neg_score:
            sentiment = "positive"
            score = min((pos_score - neg_score) / max(total, 1), 1.0)
            confidence = min(0.3 + (pos_score * 0.1), 0.7)
        else:
            sentiment = "negative"
            score = max(-(neg_score - pos_score) / max(total, 1), -1.0)
            confidence = min(0.3 + (neg_score * 0.1), 0.7)
        
        return {
            "sentiment": sentiment,
            "score": round(score, 2),
            "confidence": round(confidence, 2),
            "model": "rule-based-enhanced",
            "key_factors": self._extract_key_factors(text_lower, positive_weights, negative_weights),
            "timestamp": datetime.now().isoformat()
        }
    
    def _extract_key_factors(self, text: str, pos_terms: Dict, neg_terms: Dict) -> List[str]:
        """Extract key sentiment factors from text."""
        factors = []
        for term in pos_terms:
            if term in text:
                factors.append(f"📈 {term}")
        for term in neg_terms:
            if term in text:
                factors.append(f"📉 {term}")
        return factors[:5]  # Limit to 5 factors
    
    def _parse_text_response(self, text: str) -> Dict:
        """Parse sentiment from plain text response."""
        text_lower = text.lower()
        
        if "positive" in text_lower or "bullish" in text_lower:
            return {"sentiment": "positive", "score": 0.6, "confidence": 0.6, "model": "groq-parsed"}
        elif "negative" in text_lower or "bearish" in text_lower:
            return {"sentiment": "negative", "score": -0.6, "confidence": 0.6, "model": "groq-parsed"}
        else:
            return {"sentiment": "neutral", "score": 0.0, "confidence": 0.5, "model": "groq-parsed"}
    
    def get_aggregated_sentiment(self, texts: List[str]) -> Dict:
        """
        Get aggregated sentiment from multiple texts.
        
        Args:
            texts: List of texts (news headlines, tweets, etc.)
            
        Returns:
            Aggregated sentiment with breakdown
        """
        if not texts:
            return {
                "overall_sentiment": "neutral",
                "overall_score": 0.0,
                "confidence": 0.0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "analyzed_count": 0
            }
        
        results = [self.analyze_sync(t) for t in texts]
        
        pos_count = sum(1 for r in results if r["sentiment"] == "positive")
        neg_count = sum(1 for r in results if r["sentiment"] == "negative")
        neu_count = sum(1 for r in results if r["sentiment"] == "neutral")
        
        # Weighted score
        total_score = sum(r["score"] * r["confidence"] for r in results)
        total_confidence = sum(r["confidence"] for r in results)
        
        avg_score = total_score / total_confidence if total_confidence > 0 else 0
        
        if avg_score > 0.2:
            overall = "positive"
        elif avg_score < -0.2:
            overall = "negative"
        else:
            overall = "neutral"
        
        return {
            "overall_sentiment": overall,
            "overall_score": round(avg_score, 2),
            "confidence": round(total_confidence / len(results), 2) if results else 0,
            "positive_count": pos_count,
            "negative_count": neg_count,
            "neutral_count": neu_count,
            "analyzed_count": len(texts),
            "sentiment_ratio": f"{pos_count}:{neg_count}:{neu_count}",
            "breakdown": results[:5]  # Return first 5 for display
        }


# Singleton instance
_sentiment_service = None

def get_sentiment_service() -> UnifiedSentimentService:
    """Get singleton sentiment service instance."""
    global _sentiment_service
    if _sentiment_service is None:
        _sentiment_service = UnifiedSentimentService()
    return _sentiment_service


# Convenience functions
def analyze_text_sentiment(text: str) -> Dict:
    """Quick sentiment analysis for a single text."""
    return get_sentiment_service().analyze_sync(text)


def analyze_headlines_sentiment(headlines: List[str]) -> Dict:
    """Analyze aggregated sentiment from news headlines."""
    return get_sentiment_service().get_aggregated_sentiment(headlines)
