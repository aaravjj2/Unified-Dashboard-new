#!/usr/bin/env python3
"""
FinBERT Sentiment Analyzer for Market Forecasting

Integrates yiyanghkust/finbert-tone model for financial sentiment analysis
to enhance price predictions with market sentiment signals.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import os
import sys

# Add parent paths for imports
sys.path.insert(0, str(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

logger = logging.getLogger(__name__)

# Model configuration
FINBERT_MODEL = 'yiyanghkust/finbert-tone'
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'cache', 'finbert')


class FinBERTSentimentAnalyzer:
    """
    FinBERT-based sentiment analyzer for financial text.
    Uses yiyanghkust/finbert-tone model for positive/negative/neutral classification.
    """
    
    def __init__(self, model_name: str = FINBERT_MODEL, device: str = None):
        self.model_name = model_name
        self.device = device
        self.model = None
        self.tokenizer = None
        self._initialized = False
        
    def initialize(self) -> bool:
        """Initialize FinBERT model and tokenizer"""
        if self._initialized:
            return True
            
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            
            logger.info(f"Loading FinBERT model: {self.model_name}")
            
            # Determine device
            if self.device is None:
                self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            
            # Load tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()
            
            self._initialized = True
            logger.info(f"✅ FinBERT initialized on {self.device}")
            return True
            
        except ImportError as e:
            logger.error(f"Missing dependencies: {e}")
            logger.error("Install with: pip install transformers torch")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize FinBERT: {e}")
            return False
    
    def analyze_text(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment of a single text.
        
        Returns:
            Dict with keys: negative, neutral, positive, compound
        """
        if not self._initialized:
            if not self.initialize():
                return {'negative': 0.0, 'neutral': 1.0, 'positive': 0.0, 'compound': 0.0}
        
        try:
            import torch
            
            # Tokenize
            inputs = self.tokenizer(
                text, 
                return_tensors='pt', 
                truncation=True, 
                max_length=512,
                padding=True
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Inference
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.softmax(outputs.logits, dim=-1).cpu().numpy()[0]
            
            # FinBERT output: [negative, neutral, positive]
            return {
                'negative': float(probs[0]),
                'neutral': float(probs[1]),
                'positive': float(probs[2]),
                'compound': float(probs[2] - probs[0])  # Range: -1 to 1
            }
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return {'negative': 0.0, 'neutral': 1.0, 'positive': 0.0, 'compound': 0.0}
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of a single text (BentoML-compatible interface).
        
        Returns:
            Dict with keys: label, score (for BentoML compatibility)
        """
        result = self.analyze_text(text)
        
        # Determine dominant label
        scores = {
            'negative': result['negative'],
            'neutral': result['neutral'],
            'positive': result['positive']
        }
        label = max(scores, key=scores.get)
        score = scores[label]
        
        return {
            'label': label,
            'score': score,
            'negative': result['negative'],
            'neutral': result['neutral'],
            'positive': result['positive'],
            'compound': result['compound']
        }
    
    def analyze_batch(self, texts: List[str], batch_size: int = 16) -> List[Dict[str, float]]:
        """
        Analyze sentiment of multiple texts in batches.
        
        Returns:
            List of sentiment dicts
        """
        if not self._initialized:
            if not self.initialize():
                return [{'negative': 0.0, 'neutral': 1.0, 'positive': 0.0, 'compound': 0.0}] * len(texts)
        
        try:
            import torch
            
            results = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                
                # Tokenize batch
                inputs = self.tokenizer(
                    batch,
                    return_tensors='pt',
                    truncation=True,
                    max_length=512,
                    padding=True
                )
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                # Inference
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    probs = torch.softmax(outputs.logits, dim=-1).cpu().numpy()
                
                for p in probs:
                    results.append({
                        'negative': float(p[0]),
                        'neutral': float(p[1]),
                        'positive': float(p[2]),
                        'compound': float(p[2] - p[0])
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Batch sentiment analysis failed: {e}")
            return [{'negative': 0.0, 'neutral': 1.0, 'positive': 0.0, 'compound': 0.0}] * len(texts)
    
    def analyze_headlines(self, headlines_df: pd.DataFrame) -> pd.DataFrame:
        """
        Analyze sentiment for a DataFrame of headlines.
        
        Args:
            headlines_df: DataFrame with 'title' or 'headline' column
            
        Returns:
            DataFrame with sentiment columns added
        """
        # Get text column
        if 'title' in headlines_df.columns:
            texts = headlines_df['title'].fillna('').astype(str).tolist()
        elif 'headline' in headlines_df.columns:
            texts = headlines_df['headline'].fillna('').astype(str).tolist()
        else:
            raise ValueError("DataFrame must have 'title' or 'headline' column")
        
        # Analyze
        sentiments = self.analyze_batch(texts)
        
        # Add to DataFrame
        result = headlines_df.copy()
        result['neg_prob'] = [s['negative'] for s in sentiments]
        result['neu_prob'] = [s['neutral'] for s in sentiments]
        result['pos_prob'] = [s['positive'] for s in sentiments]
        result['compound'] = [s['compound'] for s in sentiments]
        
        return result
    
    def get_ticker_sentiment(self, ticker: str, days: int = 7) -> Dict[str, Any]:
        """
        Get aggregated sentiment for a ticker from various news sources.
        
        Returns:
            Dict with aggregated sentiment metrics
        """
        try:
            # Try to fetch headlines from Finnhub
            headlines = self._fetch_news(ticker, days)
            
            if not headlines:
                return {
                    'ticker': ticker,
                    'sentiment_mean': 0.0,
                    'sentiment_std': 0.0,
                    'sentiment_count': 0,
                    'bullish_ratio': 0.5,
                    'signal': 'neutral',
                    'confidence': 0.0
                }
            
            # Analyze headlines
            sentiments = self.analyze_batch(headlines)
            compounds = [s['compound'] for s in sentiments]
            
            # Aggregate
            mean_sentiment = np.mean(compounds)
            std_sentiment = np.std(compounds) if len(compounds) > 1 else 0.0
            bullish_count = sum(1 for c in compounds if c > 0.1)
            bearish_count = sum(1 for c in compounds if c < -0.1)
            total = len(compounds)
            
            # Determine signal
            if mean_sentiment > 0.15:
                signal = 'bullish'
            elif mean_sentiment < -0.15:
                signal = 'bearish'
            else:
                signal = 'neutral'
            
            confidence = min(abs(mean_sentiment) * 2, 1.0)  # Scale to 0-1
            
            return {
                'ticker': ticker,
                'sentiment_mean': float(mean_sentiment),
                'sentiment_std': float(std_sentiment),
                'sentiment_count': total,
                'bullish_ratio': bullish_count / total if total > 0 else 0.5,
                'bearish_ratio': bearish_count / total if total > 0 else 0.5,
                'signal': signal,
                'confidence': float(confidence)
            }
            
        except Exception as e:
            logger.error(f"Failed to get sentiment for {ticker}: {e}")
            return {
                'ticker': ticker,
                'sentiment_mean': 0.0,
                'sentiment_std': 0.0,
                'sentiment_count': 0,
                'bullish_ratio': 0.5,
                'signal': 'neutral',
                'confidence': 0.0
            }
    
    def _fetch_news(self, ticker: str, days: int = 7) -> List[str]:
        """Fetch news headlines for a ticker from multiple sources"""
        headlines = []
        
        # Source 1: Finnhub Company News API
        try:
            from dotenv import load_dotenv
            load_dotenv('keys.env')
            
            api_key = os.getenv('FINNHUB_API_KEY') or os.getenv('FINNHUB_KEY')
            
            if api_key:
                import requests
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                # Finnhub Company News endpoint
                response = requests.get(
                    "https://finnhub.io/api/v1/company-news",
                    params={
                        "symbol": ticker,
                        "from": start_date.strftime('%Y-%m-%d'),
                        "to": end_date.strftime('%Y-%m-%d'),
                        "token": api_key
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    news = response.json()
                    for article in news[:30]:  # Limit to 30 articles from Finnhub
                        if 'headline' in article and article['headline']:
                            headlines.append(article['headline'])
                    logger.info(f"Finnhub: fetched {len(headlines)} headlines for {ticker}")
                        
        except Exception as e:
            logger.warning(f"Finnhub news fetch failed: {e}")
        
        # Source 2: Finnhub General Market News (for market-wide sentiment)
        if len(headlines) < 10:
            try:
                api_key = os.getenv('FINNHUB_API_KEY') or os.getenv('FINNHUB_KEY')
                if api_key:
                    import requests
                    response = requests.get(
                        "https://finnhub.io/api/v1/news",
                        params={
                            "category": "general",
                            "token": api_key
                        },
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        general_news = response.json()
                        for article in general_news[:20]:
                            if 'headline' in article and article['headline']:
                                # Filter for relevant market news
                                headline = article['headline']
                                if any(kw in headline.lower() for kw in ['stock', 'market', 'trade', 'investor', ticker.lower()]):
                                    headlines.append(headline)
                        logger.info(f"Finnhub general: added {len(headlines)} total headlines")
                                    
            except Exception as e:
                logger.warning(f"Finnhub general news fetch failed: {e}")
        
        # Source 3: yfinance as backup
        if len(headlines) < 10:
            try:
                import yfinance as yf
                stock = yf.Ticker(ticker)
                news = stock.news or []
                
                for article in news[:20]:
                    if 'title' in article:
                        headlines.append(article['title'])
                logger.info(f"yfinance: added news, total {len(headlines)} headlines")
                        
            except Exception as e:
                logger.warning(f"yfinance news fetch failed: {e}")
        
        # Deduplicate headlines while preserving order
        seen = set()
        unique_headlines = []
        for h in headlines:
            h_lower = h.lower()
            if h_lower not in seen:
                seen.add(h_lower)
                unique_headlines.append(h)
        
        logger.info(f"Total unique headlines for {ticker}: {len(unique_headlines)}")
        return unique_headlines[:50]  # Return max 50 unique headlines


# Global instance for caching
_analyzer = None


def get_sentiment_analyzer() -> FinBERTSentimentAnalyzer:
    """Get or create singleton sentiment analyzer"""
    global _analyzer
    if _analyzer is None:
        _analyzer = FinBERTSentimentAnalyzer()
    return _analyzer


def analyze_sentiment(text: str) -> Dict[str, float]:
    """Convenience function for single text analysis"""
    return get_sentiment_analyzer().analyze_text(text)


def get_market_sentiment(ticker: str, days: int = 7) -> Dict[str, Any]:
    """Get market sentiment for a ticker"""
    return get_sentiment_analyzer().get_ticker_sentiment(ticker, days)
