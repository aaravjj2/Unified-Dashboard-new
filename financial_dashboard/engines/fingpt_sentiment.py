#!/usr/bin/env python3
"""
FinGPT-Style Sentiment Engine
=============================
LLM-powered sentiment analysis for financial text.

Inspired by AI4Finance-Foundation/FinGPT, this engine provides:
- News article sentiment analysis
- Earnings call transcript analysis
- Social media sentiment
- Multi-source sentiment fusion

Uses FinBERT for classification and optionally local LLMs for reasoning.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import pandas as pd
import os
import json

logger = logging.getLogger(__name__)


class SentimentLabel(Enum):
    """Sentiment classification labels"""
    SEVERELY_NEGATIVE = -3
    NEGATIVE = -2
    SLIGHTLY_NEGATIVE = -1
    NEUTRAL = 0
    SLIGHTLY_POSITIVE = 1
    POSITIVE = 2
    SEVERELY_POSITIVE = 3


@dataclass
class SentimentResult:
    """Result from sentiment analysis"""
    text: str
    label: SentimentLabel
    score: float  # -1 to 1
    confidence: float  # 0 to 1
    probabilities: Dict[str, float]
    source: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)
    reasoning: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'text': self.text[:200] + '...' if len(self.text) > 200 else self.text,
            'label': self.label.name,
            'label_value': self.label.value,
            'score': self.score,
            'confidence': self.confidence,
            'probabilities': self.probabilities,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'reasoning': self.reasoning
        }


@dataclass
class AggregateSentiment:
    """Aggregated sentiment across multiple sources"""
    ticker: str
    overall_score: float
    overall_label: SentimentLabel
    confidence: float
    num_sources: int
    source_breakdown: Dict[str, float]
    positive_developments: List[str]
    potential_concerns: List[str]
    prediction: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'overall_score': self.overall_score,
            'overall_label': self.overall_label.name,
            'confidence': self.confidence,
            'num_sources': self.num_sources,
            'source_breakdown': self.source_breakdown,
            'positive_developments': self.positive_developments,
            'potential_concerns': self.potential_concerns,
            'prediction': self.prediction,
            'timestamp': self.timestamp.isoformat()
        }


class FinGPTSentimentEngine:
    """
    FinGPT-style sentiment analysis engine.
    
    Combines:
    1. FinBERT for fast sentiment classification
    2. Optional LLM for reasoning and synthesis
    3. Multi-source aggregation
    
    Output format follows FinGPT-Forecaster style:
    [Positive Developments], [Potential Concerns], [Prediction & Analysis]
    """
    
    def __init__(self,
                 use_finbert: bool = True,
                 use_llm: bool = False,
                 llm_endpoint: str = None,
                 finbert_model: str = 'yiyanghkust/finbert-tone'):
        """
        Args:
            use_finbert: Whether to use FinBERT for classification
            use_llm: Whether to use LLM for reasoning
            llm_endpoint: LLM API endpoint (e.g., Ollama)
            finbert_model: FinBERT model name
        """
        self.use_finbert = use_finbert
        self.use_llm = use_llm
        self.llm_endpoint = llm_endpoint or "http://localhost:11434/api/generate"
        self.finbert_model = finbert_model
        
        self._finbert = None
        self._tokenizer = None
        self._device = None
        self._initialized = False
        
    def initialize(self) -> bool:
        """Initialize FinBERT model"""
        if self._initialized:
            return True
            
        if not self.use_finbert:
            self._initialized = True
            return True
            
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            
            logger.info(f"Loading FinBERT: {self.finbert_model}")
            
            self._device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self._tokenizer = AutoTokenizer.from_pretrained(self.finbert_model)
            self._finbert = AutoModelForSequenceClassification.from_pretrained(self.finbert_model)
            self._finbert.to(self._device)
            self._finbert.eval()
            
            self._initialized = True
            logger.info(f"✅ FinGPT Sentiment Engine initialized on {self._device}")
            return True
            
        except ImportError as e:
            logger.warning(f"FinBERT not available: {e}")
            self._initialized = True  # Use fallback
            return True
        except Exception as e:
            logger.error(f"Failed to initialize FinBERT: {e}")
            return False
    
    def analyze_text(self, text: str, source: str = "unknown") -> SentimentResult:
        """
        Analyze sentiment of a single text.
        
        Returns:
            SentimentResult with label, score, confidence
        """
        if not self._initialized:
            if not self.initialize():
                return self._fallback_sentiment(text, source)
        
        if self._finbert is None:
            return self._fallback_sentiment(text, source)
            
        try:
            import torch
            
            # Tokenize
            inputs = self._tokenizer(
                text,
                return_tensors='pt',
                truncation=True,
                max_length=512,
                padding=True
            )
            inputs = {k: v.to(self._device) for k, v in inputs.items()}
            
            # Inference
            with torch.no_grad():
                outputs = self._finbert(**inputs)
                probs = torch.softmax(outputs.logits, dim=-1).cpu().numpy()[0]
            
            # FinBERT: [negative, neutral, positive]
            neg, neu, pos = probs[0], probs[1], probs[2]
            
            # Calculate compound score (-1 to 1)
            score = pos - neg
            
            # Map to 7-class label (FinGPT style)
            label = self._map_score_to_label(score, confidence=max(probs))
            
            # Confidence is max probability
            confidence = float(max(probs))
            
            return SentimentResult(
                text=text,
                label=label,
                score=float(score),
                confidence=confidence,
                probabilities={'negative': float(neg), 'neutral': float(neu), 'positive': float(pos)},
                source=source
            )
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return self._fallback_sentiment(text, source)
    
    def _map_score_to_label(self, score: float, confidence: float) -> SentimentLabel:
        """Map score to 7-class label"""
        if confidence < 0.4:
            return SentimentLabel.NEUTRAL
            
        if score >= 0.6:
            return SentimentLabel.SEVERELY_POSITIVE
        elif score >= 0.3:
            return SentimentLabel.POSITIVE
        elif score >= 0.1:
            return SentimentLabel.SLIGHTLY_POSITIVE
        elif score <= -0.6:
            return SentimentLabel.SEVERELY_NEGATIVE
        elif score <= -0.3:
            return SentimentLabel.NEGATIVE
        elif score <= -0.1:
            return SentimentLabel.SLIGHTLY_NEGATIVE
        else:
            return SentimentLabel.NEUTRAL
    
    def _fallback_sentiment(self, text: str, source: str) -> SentimentResult:
        """Fallback when FinBERT not available - use keyword-based"""
        text_lower = text.lower()
        
        # Simple keyword-based fallback
        positive_words = ['bullish', 'growth', 'profit', 'beat', 'strong', 'upgrade', 
                         'outperform', 'positive', 'surge', 'rally', 'gain']
        negative_words = ['bearish', 'decline', 'loss', 'miss', 'weak', 'downgrade',
                         'underperform', 'negative', 'crash', 'fall', 'drop']
        
        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)
        
        total = pos_count + neg_count
        if total == 0:
            score = 0.0
            confidence = 0.3
        else:
            score = (pos_count - neg_count) / total
            confidence = min(0.5 + total * 0.05, 0.8)
        
        return SentimentResult(
            text=text,
            label=self._map_score_to_label(score, confidence),
            score=score,
            confidence=confidence,
            probabilities={'negative': max(0, -score), 'neutral': 1 - abs(score), 'positive': max(0, score)},
            source=source
        )
    
    def analyze_batch(self, texts: List[str], source: str = "batch") -> List[SentimentResult]:
        """Analyze multiple texts"""
        return [self.analyze_text(text, source) for text in texts]
    
    def aggregate_sentiment(self,
                           ticker: str,
                           news_texts: List[str] = None,
                           social_texts: List[str] = None,
                           earnings_text: str = None) -> AggregateSentiment:
        """
        Aggregate sentiment from multiple sources.
        
        Output follows FinGPT-Forecaster format:
        - Positive Developments
        - Potential Concerns
        - Prediction & Analysis
        """
        all_results: List[SentimentResult] = []
        source_scores: Dict[str, List[float]] = {}
        
        # Analyze news
        if news_texts:
            for text in news_texts:
                result = self.analyze_text(text, "news")
                all_results.append(result)
                source_scores.setdefault("news", []).append(result.score)
        
        # Analyze social media
        if social_texts:
            for text in social_texts:
                result = self.analyze_text(text, "social")
                all_results.append(result)
                source_scores.setdefault("social", []).append(result.score)
        
        # Analyze earnings
        if earnings_text:
            result = self.analyze_text(earnings_text, "earnings")
            all_results.append(result)
            source_scores.setdefault("earnings", []).append(result.score)
        
        if not all_results:
            return AggregateSentiment(
                ticker=ticker,
                overall_score=0.0,
                overall_label=SentimentLabel.NEUTRAL,
                confidence=0.0,
                num_sources=0,
                source_breakdown={},
                positive_developments=[],
                potential_concerns=[],
                prediction="Insufficient data for sentiment analysis"
            )
        
        # Calculate overall score (weighted by confidence)
        total_weight = sum(r.confidence for r in all_results)
        if total_weight > 0:
            overall_score = sum(r.score * r.confidence for r in all_results) / total_weight
            overall_confidence = np.mean([r.confidence for r in all_results])
        else:
            overall_score = 0.0
            overall_confidence = 0.0
        
        # Get source breakdown
        source_breakdown = {
            source: np.mean(scores) for source, scores in source_scores.items()
        }
        
        # Extract positive developments and concerns
        positive_developments = [
            r.text[:100] for r in all_results 
            if r.label.value >= 1 and r.confidence > 0.5
        ][:5]
        
        potential_concerns = [
            r.text[:100] for r in all_results 
            if r.label.value <= -1 and r.confidence > 0.5
        ][:5]
        
        # Generate prediction
        prediction = self._generate_prediction(
            ticker, overall_score, overall_confidence, 
            positive_developments, potential_concerns
        )
        
        return AggregateSentiment(
            ticker=ticker,
            overall_score=overall_score,
            overall_label=self._map_score_to_label(overall_score, overall_confidence),
            confidence=overall_confidence,
            num_sources=len(all_results),
            source_breakdown=source_breakdown,
            positive_developments=positive_developments,
            potential_concerns=potential_concerns,
            prediction=prediction
        )
    
    def _generate_prediction(self,
                            ticker: str,
                            score: float,
                            confidence: float,
                            positives: List[str],
                            concerns: List[str]) -> str:
        """
        Generate FinGPT-style prediction text.
        
        Format: [Analysis] [Prediction] [Confidence level]
        """
        if confidence < 0.3:
            return f"{ticker}: Insufficient confidence for prediction. Mixed signals detected."
        
        # Determine direction
        if score >= 0.3:
            direction = "bullish"
            action = "positive momentum expected"
        elif score <= -0.3:
            direction = "bearish"
            action = "downward pressure anticipated"
        else:
            direction = "neutral"
            action = "sideways movement expected"
        
        # Confidence qualifier
        if confidence >= 0.7:
            conf_text = "High confidence"
        elif confidence >= 0.5:
            conf_text = "Moderate confidence"
        else:
            conf_text = "Low confidence"
        
        # Build prediction
        num_pos = len(positives)
        num_neg = len(concerns)
        
        if num_pos > num_neg * 2:
            outlook = "Significantly more positive than negative sentiment detected."
        elif num_neg > num_pos * 2:
            outlook = "Significantly more negative than positive sentiment detected."
        else:
            outlook = "Mixed sentiment with both positive and negative factors."
        
        return f"{ticker}: {conf_text} {direction} outlook. {action}. {outlook} Score: {score:.2f}"
    
    def get_fingpt_format(self, aggregate: AggregateSentiment) -> Dict:
        """
        Return sentiment in FinGPT-Forecaster output format.
        
        Format:
        {
            "ticker": "AAPL",
            "positive_developments": [...],
            "potential_concerns": [...],
            "prediction_and_analysis": "...",
            "sentiment_score": 0.65,
            "confidence": 0.82
        }
        """
        return {
            "ticker": aggregate.ticker,
            "positive_developments": aggregate.positive_developments,
            "potential_concerns": aggregate.potential_concerns,
            "prediction_and_analysis": aggregate.prediction,
            "sentiment_score": aggregate.overall_score,
            "sentiment_label": aggregate.overall_label.name,
            "confidence": aggregate.confidence,
            "num_sources": aggregate.num_sources,
            "source_breakdown": aggregate.source_breakdown,
            "timestamp": aggregate.timestamp.isoformat()
        }
    
    async def get_llm_reasoning(self, ticker: str, context: str) -> str:
        """
        Use LLM (e.g., Ollama) for deeper reasoning.
        
        This mimics FinGPT's LLM layer for market analysis.
        """
        if not self.use_llm:
            return None
            
        try:
            import aiohttp
            
            prompt = f"""You are a seasoned stock market analyst. Analyze the following information about {ticker}:

{context}

Provide your analysis in this format:
[Positive Developments]: List 2-3 positive factors
[Potential Concerns]: List 2-3 risk factors  
[Prediction & Analysis]: Your prediction with confidence level

Be specific and concise."""

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.llm_endpoint,
                    json={"model": "mistral:7b", "prompt": prompt, "stream": False}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("response", "")
                        
        except Exception as e:
            logger.warning(f"LLM reasoning failed: {e}")
            
        return None
