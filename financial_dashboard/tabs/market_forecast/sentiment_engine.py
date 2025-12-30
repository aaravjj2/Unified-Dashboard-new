"""
Sentiment Consensus Engine for Market Forecast Tab
===================================================

Phase 5: Market Intelligence - Sentiment Analysis with FinBERT

Provides multi-source sentiment aggregation using FinBERT transformer model
for financial text classification.

Features:
- FinBERT-powered sentiment classification (positive/negative/neutral)
- Multi-headline aggregation with confidence weighting
- Consensus scoring with bull/bear/neutral thresholds
- Sentiment distribution visualization
- Cached model loading for performance

Phase 5 Requirements:
- PORT=8051
- AZURE_ENABLED=false  
- PHASE5_DETERMINISTIC=1
"""

import logging
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

# Set deterministic mode for Phase 5
DETERMINISTIC_MODE = os.getenv('PHASE5_DETERMINISTIC', '0') == '1'
if DETERMINISTIC_MODE:
    np.random.seed(42)
    logger.info("✅ Phase 5 deterministic mode enabled for Sentiment Engine")

# FinBERT imports with graceful fallback
FINBERT_AVAILABLE = False
try:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
    import torch
    
    if DETERMINISTIC_MODE:
        torch.manual_seed(42)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(42)
    
    FINBERT_AVAILABLE = True
    logger.info("✅ FinBERT (transformers) available for sentiment analysis")
except ImportError as e:
    logger.warning(f"FinBERT not available: {e}. Using fallback sentiment analysis.")


class SentimentLabel(Enum):
    """Sentiment classification labels."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass
class SentimentResult:
    """Container for a single sentiment classification result."""
    text: str
    label: SentimentLabel
    confidence: float
    scores: Dict[str, float]  # All class probabilities


@dataclass 
class ConsensusResult:
    """Container for aggregated sentiment consensus."""
    consensus_label: str  # "Bullish", "Bearish", "Neutral"
    consensus_score: float  # -1 to +1
    positive_pct: float
    negative_pct: float
    neutral_pct: float
    avg_confidence: float
    num_headlines: int
    individual_results: List[SentimentResult]


# Sentiment colors for visualization
SENTIMENT_COLORS = {
    SentimentLabel.POSITIVE: '#2ecc71',  # Green
    SentimentLabel.NEGATIVE: '#e74c3c',  # Red  
    SentimentLabel.NEUTRAL: '#95a5a6',   # Gray
    'bullish': '#2ecc71',
    'bearish': '#e74c3c',
    'neutral': '#95a5a6'
}

# Consensus thresholds
BULLISH_THRESHOLD = 0.2   # score > 0.2 = Bullish
BEARISH_THRESHOLD = -0.2  # score < -0.2 = Bearish


class SentimentAnalyzer:
    """
    FinBERT-powered Sentiment Analyzer for financial headlines.
    
    Uses ProsusAI/finbert model for domain-specific sentiment classification
    with confidence-weighted consensus aggregation.
    """
    
    _instance = None
    _model = None
    _tokenizer = None
    _pipeline = None
    
    def __new__(cls):
        """Singleton pattern to avoid reloading model multiple times."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the sentiment analyzer with FinBERT model."""
        if self._pipeline is not None:
            return  # Already initialized
        
        self._load_model()
    
    def _load_model(self) -> None:
        """Load FinBERT model and tokenizer."""
        if not FINBERT_AVAILABLE:
            logger.warning("FinBERT not available, using fallback lexicon-based analysis")
            return
        
        try:
            model_name = "ProsusAI/finbert"
            logger.info(f"Loading FinBERT model: {model_name}")
            
            self._tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(model_name)
            
            # Use CPU for consistency (AZURE_ENABLED=false)
            device = -1  # CPU
            
            self._pipeline = pipeline(
                "sentiment-analysis",
                model=self._model,
                tokenizer=self._tokenizer,
                device=device,
                top_k=None  # Return all class probabilities
            )
            
            logger.info("✅ FinBERT model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load FinBERT: {e}")
            self._pipeline = None
    
    def analyze_text(self, text: str) -> SentimentResult:
        """
        Analyze sentiment of a single text.
        
        Args:
            text: Input text (headline, news snippet, etc.)
            
        Returns:
            SentimentResult with label, confidence, and scores
        """
        if not text or not text.strip():
            return SentimentResult(
                text=text,
                label=SentimentLabel.NEUTRAL,
                confidence=0.0,
                scores={'positive': 0.33, 'negative': 0.33, 'neutral': 0.34}
            )
        
        # Truncate long texts
        text = text[:512].strip()
        
        if self._pipeline is not None:
            return self._analyze_with_finbert(text)
        else:
            return self._analyze_with_fallback(text)
    
    def _analyze_with_finbert(self, text: str) -> SentimentResult:
        """Use FinBERT pipeline for sentiment analysis."""
        try:
            results = self._pipeline(text)
            
            # Parse results - pipeline returns list of dicts
            scores = {}
            for item in results[0] if isinstance(results[0], list) else results:
                label_str = item['label'].lower()
                scores[label_str] = item['score']
            
            # Get dominant label
            max_label = max(scores, key=scores.get)
            confidence = scores[max_label]
            
            label = SentimentLabel(max_label)
            
            return SentimentResult(
                text=text,
                label=label,
                confidence=confidence,
                scores=scores
            )
            
        except Exception as e:
            logger.error(f"FinBERT analysis error: {e}")
            return self._analyze_with_fallback(text)
    
    def _analyze_with_fallback(self, text: str) -> SentimentResult:
        """
        Fallback lexicon-based sentiment analysis.
        
        Uses simple keyword matching for basic sentiment detection.
        """
        text_lower = text.lower()
        
        # Financial sentiment lexicons
        positive_words = {
            'surge', 'soar', 'rally', 'gain', 'rise', 'jump', 'bullish', 'upgrade',
            'outperform', 'beat', 'exceed', 'strong', 'growth', 'profit', 'record',
            'breakthrough', 'innovation', 'optimistic', 'confident', 'boost', 'buy',
            'positive', 'success', 'win', 'good', 'great', 'excellent', 'up', 'high'
        }
        
        negative_words = {
            'drop', 'fall', 'plunge', 'crash', 'decline', 'slump', 'bearish', 'downgrade',
            'underperform', 'miss', 'weak', 'loss', 'fear', 'concern', 'risk', 'warning',
            'sell', 'cut', 'negative', 'fail', 'bad', 'poor', 'down', 'low', 'worst',
            'crisis', 'recession', 'bankruptcy', 'layoff', 'default', 'debt'
        }
        
        # Count sentiment words
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        total = pos_count + neg_count
        
        if total == 0:
            scores = {'positive': 0.33, 'negative': 0.33, 'neutral': 0.34}
            label = SentimentLabel.NEUTRAL
            confidence = 0.5
        else:
            pos_ratio = pos_count / total if total > 0 else 0.33
            neg_ratio = neg_count / total if total > 0 else 0.33
            neu_ratio = 1 - pos_ratio - neg_ratio if pos_ratio + neg_ratio < 1 else 0
            
            scores = {'positive': pos_ratio, 'negative': neg_ratio, 'neutral': max(0, neu_ratio)}
            
            if pos_ratio > neg_ratio and pos_ratio > 0.4:
                label = SentimentLabel.POSITIVE
                confidence = pos_ratio
            elif neg_ratio > pos_ratio and neg_ratio > 0.4:
                label = SentimentLabel.NEGATIVE
                confidence = neg_ratio
            else:
                label = SentimentLabel.NEUTRAL
                confidence = 0.5 + abs(pos_ratio - neg_ratio) * 0.5
        
        return SentimentResult(
            text=text,
            label=label,
            confidence=min(confidence, 0.95),
            scores=scores
        )
    
    def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        """
        Analyze sentiment of multiple texts.
        
        Args:
            texts: List of text strings
            
        Returns:
            List of SentimentResult objects
        """
        return [self.analyze_text(text) for text in texts]
    
    def compute_consensus(self, results: List[SentimentResult]) -> ConsensusResult:
        """
        Compute aggregated sentiment consensus from multiple results.
        
        Uses confidence-weighted averaging with bull/bear thresholds.
        
        Args:
            results: List of SentimentResult objects
            
        Returns:
            ConsensusResult with aggregated metrics
        """
        if not results:
            return ConsensusResult(
                consensus_label="Neutral",
                consensus_score=0.0,
                positive_pct=0.0,
                negative_pct=0.0,
                neutral_pct=100.0,
                avg_confidence=0.0,
                num_headlines=0,
                individual_results=[]
            )
        
        # Count by sentiment
        pos_count = sum(1 for r in results if r.label == SentimentLabel.POSITIVE)
        neg_count = sum(1 for r in results if r.label == SentimentLabel.NEGATIVE)
        neu_count = sum(1 for r in results if r.label == SentimentLabel.NEUTRAL)
        
        total = len(results)
        
        # Percentages
        pos_pct = (pos_count / total) * 100
        neg_pct = (neg_count / total) * 100
        neu_pct = (neu_count / total) * 100
        
        # Confidence-weighted score (-1 to +1)
        weighted_scores = []
        total_weight = 0
        
        for r in results:
            weight = r.confidence
            if r.label == SentimentLabel.POSITIVE:
                score = r.scores.get('positive', 0.5)
            elif r.label == SentimentLabel.NEGATIVE:
                score = -r.scores.get('negative', 0.5)
            else:
                score = 0
            
            weighted_scores.append(score * weight)
            total_weight += weight
        
        consensus_score = sum(weighted_scores) / total_weight if total_weight > 0 else 0
        
        # Determine consensus label
        if consensus_score > BULLISH_THRESHOLD:
            consensus_label = "Bullish"
        elif consensus_score < BEARISH_THRESHOLD:
            consensus_label = "Bearish"
        else:
            consensus_label = "Neutral"
        
        avg_confidence = np.mean([r.confidence for r in results])
        
        return ConsensusResult(
            consensus_label=consensus_label,
            consensus_score=consensus_score,
            positive_pct=pos_pct,
            negative_pct=neg_pct,
            neutral_pct=neu_pct,
            avg_confidence=avg_confidence,
            num_headlines=total,
            individual_results=results
        )


def analyze_headlines(headlines: List[str]) -> ConsensusResult:
    """
    Convenience function to analyze headlines and compute consensus.
    
    Args:
        headlines: List of news headline strings
        
    Returns:
        ConsensusResult with aggregated sentiment
    """
    analyzer = SentimentAnalyzer()
    results = analyzer.analyze_batch(headlines)
    return analyzer.compute_consensus(results)


def get_sample_headlines(ticker: str = "AAPL") -> List[str]:
    """
    Generate sample headlines for testing/demo.
    
    In production, this would fetch from news APIs.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        List of sample headlines
    """
    # Deterministic sample headlines for Phase 5
    np.random.seed(42)
    
    positive_templates = [
        f"{ticker} shares surge after strong earnings beat",
        f"Analysts upgrade {ticker} citing growth potential",
        f"{ticker} announces record quarterly revenue",
        f"Investors bullish on {ticker} expansion plans",
        f"{ticker} stock rallies on product launch success"
    ]
    
    negative_templates = [
        f"{ticker} faces headwinds as competition intensifies",
        f"Concerns rise over {ticker} supply chain issues",
        f"{ticker} misses revenue expectations for Q3",
        f"Analysts warn of {ticker} valuation concerns",
        f"{ticker} stock drops on weak guidance"
    ]
    
    neutral_templates = [
        f"{ticker} maintains position in market",
        f"{ticker} reports mixed quarterly results",
        f"Analysts hold ratings on {ticker} stock",
        f"{ticker} trading volume remains steady",
        f"{ticker} announces routine board changes"
    ]
    
    # Mix headlines (deterministic shuffle)
    all_headlines = positive_templates + negative_templates + neutral_templates
    indices = np.random.permutation(len(all_headlines))
    
    return [all_headlines[i] for i in indices[:10]]


# Module availability check
def is_finbert_available() -> bool:
    """Check if FinBERT model is available."""
    return FINBERT_AVAILABLE


# Export
__all__ = [
    'SentimentAnalyzer',
    'SentimentResult', 
    'ConsensusResult',
    'SentimentLabel',
    'SENTIMENT_COLORS',
    'analyze_headlines',
    'get_sample_headlines',
    'is_finbert_available'
]
