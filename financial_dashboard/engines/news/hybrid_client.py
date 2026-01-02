"""
Hybrid News Client - Phase 4: Self-Healing Data Layer
======================================================
Combines multiple news and sentiment sources into a unified API.

Features:
- Finnhub sentiment scores (API key required for full access)
- FinViz headline scraping (no key required, fast)
- StockTwits retail sentiment (public API)
- Mock fallback for testing without API keys
- **Phase 2:** VADER-based headline sentiment classification (Good/Bad/Neutral)
- **Phase 4:** Circuit breakers + automatic fallbacks for resilience

Self-Healing Features (Phase 4):
- Circuit Breakers: If API fails 3 times in 1 minute -> Stop for 5 minutes
- Automatic Fallbacks: Finnhub -> StockTwits -> Mock
- Data Degraded Flag: Warns when using fallback/mock data
- Comprehensive logging for API call tracing

Performance targets:
- get_retail_sentiment(): < 1s
- get_finviz_headlines(): < 500ms
- All methods include caching and rate limiting
"""

import os
import sys
import time
import logging
import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Literal
from functools import lru_cache
from enum import Enum
import hashlib

import requests
from bs4 import BeautifulSoup

# Phase 2: Import sentiment analyzers
try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False

try:
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    import nltk
    # Ensure VADER lexicon is downloaded
    try:
        nltk.data.find('sentiment/vader_lexicon.zip')
    except LookupError:
        nltk.download('vader_lexicon', quiet=True)
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False

# Add parent paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from financial_dashboard.config.sentiment import get_sentiment_config, SentimentConfig
except ImportError:
    try:
        from financial_dashboard.config import get_sentiment_config, SentimentConfig
    except ImportError:
        # Fallback if running standalone
        SentimentConfig = None
        def get_sentiment_config():
            return None

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SentimentResult:
    """Result from sentiment analysis."""
    symbol: str
    score: float  # 0.0 (bearish) to 1.0 (bullish), 0.5 = neutral
    label: str    # 'Bullish', 'Bearish', 'Neutral'
    source: str   # 'finnhub', 'stocktwits', 'mock'
    confidence: float = 0.5  # Confidence in the score
    bullish_count: int = 0   # Number of bullish signals
    bearish_count: int = 0   # Number of bearish signals
    timestamp: datetime = field(default_factory=datetime.now)
    is_mock: bool = False
    raw_data: Optional[Dict] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'symbol': self.symbol,
            'score': self.score,
            'label': self.label,
            'source': self.source,
            'confidence': self.confidence,
            'bullish_count': self.bullish_count,
            'bearish_count': self.bearish_count,
            'timestamp': self.timestamp.isoformat(),
            'is_mock': self.is_mock
        }


class HeadlineSentiment(Enum):
    """Sentiment classification for headlines."""
    POSITIVE = "Positive"
    NEGATIVE = "Negative"
    NEUTRAL = "Neutral"


@dataclass
class NewsHeadline:
    """A single news headline with sentiment classification."""
    time: str           # Display time like '10:30AM' or 'Jan-01'
    headline: str       # The headline text
    link: str           # URL to full article
    source: str = ''    # Source name (Bloomberg, Reuters, etc.)
    sentiment: Optional[float] = None  # Sentiment polarity (-1 to 1)
    sentiment_label: str = 'Neutral'   # Phase 2: 'Positive', 'Negative', 'Neutral'
    sentiment_compound: float = 0.0    # Phase 2: VADER compound score
    timestamp: Optional[datetime] = None  # Parsed timestamp if available
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'time': self.time,
            'headline': self.headline,
            'link': self.link,
            'source': self.source,
            'sentiment': self.sentiment,
            'sentiment_label': self.sentiment_label,
            'sentiment_compound': self.sentiment_compound
        }
    
    @property
    def is_positive(self) -> bool:
        return self.sentiment_label == 'Positive'
    
    @property
    def is_negative(self) -> bool:
        return self.sentiment_label == 'Negative'
    
    @property
    def color(self) -> str:
        """Return color code for UI display."""
        if self.sentiment_label == 'Positive':
            return '#00D084'  # Green
        elif self.sentiment_label == 'Negative':
            return '#FF6B6B'  # Red
        return '#FFD93D'      # Yellow (Neutral)


# =============================================================================
# CACHE IMPLEMENTATION
# =============================================================================

class SimpleCache:
    """Simple in-memory cache with TTL."""
    
    def __init__(self, default_ttl: int = 300):
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)
        self._default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            value, expiry = self._cache[key]
            if time.time() < expiry:
                return value
            else:
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        ttl = ttl or self._default_ttl
        self._cache[key] = (value, time.time() + ttl)
    
    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()


# =============================================================================
# CIRCUIT BREAKER (Phase 4: Self-Healing)
# =============================================================================

class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"       # Normal operation
    OPEN = "OPEN"           # Blocking requests (API down)
    HALF_OPEN = "HALF_OPEN" # Testing if API is back


class CircuitBreaker:
    """
    Circuit breaker for API calls - Phase 4 Self-Healing.
    
    Behavior:
    - CLOSED: Normal operation, track failures
    - If 3 failures in 1 minute -> OPEN (block requests for 5 min)
    - After 5 min -> HALF_OPEN (allow 1 test request)
    - If test succeeds -> CLOSED
    - If test fails -> OPEN (reset timeout)
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        failure_window: int = 60,      # seconds
        recovery_timeout: int = 300,   # seconds (5 min)
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.failure_window = failure_window
        self.recovery_timeout = recovery_timeout
        
        self._state = CircuitBreakerState.CLOSED
        self._failures: List[float] = []  # timestamps of failures
        self._last_failure_time: float = 0
        self._open_time: float = 0
        
    @property
    def state(self) -> CircuitBreakerState:
        """Get current state, handling HALF_OPEN transitions."""
        if self._state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if time.time() - self._open_time >= self.recovery_timeout:
                self._state = CircuitBreakerState.HALF_OPEN
                logger.info(f"🔄 Circuit {self.name}: OPEN -> HALF_OPEN (testing...)")
        return self._state
    
    @property
    def is_available(self) -> bool:
        """Check if circuit allows requests."""
        return self.state in (CircuitBreakerState.CLOSED, CircuitBreakerState.HALF_OPEN)
    
    def record_success(self) -> None:
        """Record successful API call."""
        if self._state == CircuitBreakerState.HALF_OPEN:
            logger.info(f"✅ Circuit {self.name}: HALF_OPEN -> CLOSED (recovered)")
            self._state = CircuitBreakerState.CLOSED
            self._failures.clear()
    
    def record_failure(self) -> None:
        """Record failed API call."""
        now = time.time()
        self._failures.append(now)
        self._last_failure_time = now
        
        # Clean old failures outside the window
        cutoff = now - self.failure_window
        self._failures = [t for t in self._failures if t > cutoff]
        
        logger.warning(f"⚠️ Circuit {self.name}: Failure recorded ({len(self._failures)}/{self.failure_threshold})")
        
        # Check if we need to open the circuit
        if self._state == CircuitBreakerState.HALF_OPEN:
            # Test failed, back to OPEN
            logger.warning(f"🔴 Circuit {self.name}: HALF_OPEN -> OPEN (test failed)")
            self._state = CircuitBreakerState.OPEN
            self._open_time = now
        elif len(self._failures) >= self.failure_threshold:
            # Threshold reached, open circuit
            logger.warning(f"🔴 Circuit {self.name}: CLOSED -> OPEN (threshold reached)")
            self._state = CircuitBreakerState.OPEN
            self._open_time = now
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status for monitoring."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failures_in_window": len(self._failures),
            "failure_threshold": self.failure_threshold,
            "is_available": self.is_available,
            "last_failure": datetime.fromtimestamp(self._last_failure_time).isoformat() if self._last_failure_time else None,
        }


class DataDegradedWarning:
    """
    Tracks when data is degraded (using mock/fallback).
    
    Phase 4: Provides visibility into data quality.
    """
    
    def __init__(self):
        self._degraded_sources: Dict[str, str] = {}  # source -> reason
        self._degraded_since: Dict[str, float] = {}  # source -> timestamp
    
    def mark_degraded(self, source: str, reason: str) -> None:
        """Mark a data source as degraded."""
        if source not in self._degraded_sources:
            logger.warning(f"⚠️ DATA DEGRADED: {source} - {reason}")
            self._degraded_since[source] = time.time()
        self._degraded_sources[source] = reason
    
    def mark_healthy(self, source: str) -> None:
        """Mark a data source as healthy."""
        if source in self._degraded_sources:
            duration = time.time() - self._degraded_since.get(source, 0)
            logger.info(f"✅ DATA RECOVERED: {source} (was degraded for {duration:.1f}s)")
            del self._degraded_sources[source]
            if source in self._degraded_since:
                del self._degraded_since[source]
    
    def is_degraded(self, source: str) -> bool:
        """Check if a source is degraded."""
        return source in self._degraded_sources
    
    def get_degraded_sources(self) -> Dict[str, str]:
        """Get all degraded sources and reasons."""
        return self._degraded_sources.copy()
    
    @property
    def has_degradation(self) -> bool:
        """Check if any source is degraded."""
        return len(self._degraded_sources) > 0


# =============================================================================
# HEADLINE SENTIMENT ANALYZER (Phase 2)
# =============================================================================

class HeadlineSentimentAnalyzer:
    """
    Analyze headline sentiment using VADER (preferred) or TextBlob (fallback).
    
    Phase 2: Local AI - No external API calls required.
    
    Thresholds:
    - Polarity > 0.1 → Positive (Good news, Green)
    - Polarity < -0.1 → Negative (Bad news, Red)
    - Otherwise → Neutral (Yellow)
    """
    
    POSITIVE_THRESHOLD = 0.1
    NEGATIVE_THRESHOLD = -0.1
    
    # Financial-specific sentiment boosters
    POSITIVE_KEYWORDS = {
        'surge', 'soar', 'rally', 'bullish', 'upgrade', 'beat', 'outperform',
        'breakthrough', 'record', 'profit', 'growth', 'gain', 'jump', 'rise',
        'boom', 'strong', 'positive', 'optimistic', 'buy', 'accumulate'
    }
    
    NEGATIVE_KEYWORDS = {
        'crash', 'plunge', 'fall', 'bearish', 'downgrade', 'miss', 'underperform',
        'decline', 'loss', 'drop', 'tumble', 'weak', 'negative', 'sell', 'warning',
        'risk', 'concern', 'fear', 'trouble', 'lawsuit', 'investigation', 'fraud'
    }
    
    def __init__(self):
        """Initialize sentiment analyzer."""
        self._vader = None
        self._use_vader = VADER_AVAILABLE
        
        if VADER_AVAILABLE:
            try:
                self._vader = SentimentIntensityAnalyzer()
                logger.info("📊 HeadlineSentimentAnalyzer: Using VADER")
            except Exception as e:
                logger.warning(f"VADER init failed: {e}, falling back to TextBlob")
                self._use_vader = False
        
        if not self._use_vader and TEXTBLOB_AVAILABLE:
            logger.info("📊 HeadlineSentimentAnalyzer: Using TextBlob")
        elif not self._use_vader:
            logger.warning("📊 HeadlineSentimentAnalyzer: No NLP library, using keyword-based")
    
    def analyze(self, headline: str) -> tuple[float, str, float]:
        """
        Analyze sentiment of a headline.
        
        Args:
            headline: The headline text to analyze
            
        Returns:
            Tuple of (polarity, label, compound_score)
            - polarity: -1.0 to 1.0
            - label: 'Positive', 'Negative', or 'Neutral'
            - compound_score: VADER compound or TextBlob polarity
        """
        if not headline:
            return 0.0, 'Neutral', 0.0
        
        # Clean headline
        clean_text = self._preprocess(headline)
        
        if self._use_vader and self._vader:
            return self._analyze_vader(clean_text)
        elif TEXTBLOB_AVAILABLE:
            return self._analyze_textblob(clean_text)
        else:
            return self._analyze_keywords(clean_text)
    
    def _preprocess(self, text: str) -> str:
        """Clean and preprocess headline text."""
        # Remove URLs
        text = re.sub(r'http\S+|www\.\S+', '', text)
        # Remove special characters but keep important punctuation
        text = re.sub(r'[^\w\s\-\.\!\?]', '', text)
        return text.strip()
    
    def _analyze_vader(self, text: str) -> tuple[float, str, float]:
        """Analyze using VADER."""
        scores = self._vader.polarity_scores(text)
        compound = scores['compound']
        
        # Apply financial keyword boosting
        boost = self._calculate_keyword_boost(text)
        adjusted_compound = max(-1, min(1, compound + boost * 0.2))
        
        label = self._compound_to_label(adjusted_compound)
        return adjusted_compound, label, compound
    
    def _analyze_textblob(self, text: str) -> tuple[float, str, float]:
        """Analyze using TextBlob."""
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # -1 to 1
        
        # Apply financial keyword boosting
        boost = self._calculate_keyword_boost(text)
        adjusted_polarity = max(-1, min(1, polarity + boost * 0.2))
        
        label = self._compound_to_label(adjusted_polarity)
        return adjusted_polarity, label, polarity
    
    def _analyze_keywords(self, text: str) -> tuple[float, str, float]:
        """Fallback keyword-based analysis."""
        text_lower = text.lower()
        words = set(text_lower.split())
        
        pos_count = len(words & self.POSITIVE_KEYWORDS)
        neg_count = len(words & self.NEGATIVE_KEYWORDS)
        
        if pos_count > neg_count:
            score = min(0.5, 0.15 * pos_count)
            return score, 'Positive', score
        elif neg_count > pos_count:
            score = max(-0.5, -0.15 * neg_count)
            return score, 'Negative', score
        else:
            return 0.0, 'Neutral', 0.0
    
    def _calculate_keyword_boost(self, text: str) -> float:
        """Calculate sentiment boost from financial keywords."""
        text_lower = text.lower()
        words = set(text_lower.split())
        
        pos_matches = len(words & self.POSITIVE_KEYWORDS)
        neg_matches = len(words & self.NEGATIVE_KEYWORDS)
        
        return (pos_matches - neg_matches) * 0.1
    
    def _compound_to_label(self, compound: float) -> str:
        """Convert compound score to label."""
        if compound >= self.POSITIVE_THRESHOLD:
            return 'Positive'
        elif compound <= self.NEGATIVE_THRESHOLD:
            return 'Negative'
        return 'Neutral'
    
    def batch_analyze(self, headlines: List[str]) -> List[tuple[float, str, float]]:
        """Analyze multiple headlines efficiently."""
        return [self.analyze(h) for h in headlines]


# Module-level sentiment analyzer instance
_sentiment_analyzer: Optional[HeadlineSentimentAnalyzer] = None


def get_sentiment_analyzer() -> HeadlineSentimentAnalyzer:
    """Get singleton sentiment analyzer."""
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        _sentiment_analyzer = HeadlineSentimentAnalyzer()
    return _sentiment_analyzer


# =============================================================================
# HYBRID NEWS CLIENT
# =============================================================================

class HybridNewsClient:
    """
    Unified client for news and sentiment data from multiple sources.
    
    Implements Ideas #14 (Strike-level news flags), #80 (Sentiment aggregator),
    and #212 (Live option sentiment gauge) from ALPACA_500_NEW_IDEAS.md.
    
    Usage:
        client = HybridNewsClient()
        
        # Get sentiment score (0-1)
        sentiment = client.get_retail_sentiment('NVDA')
        print(f"NVDA Sentiment: {sentiment.score:.2f} ({sentiment.label})")
        
        # Get news headlines
        headlines = client.get_finviz_headlines('TSLA')
        for h in headlines[:5]:
            print(f"{h.time}: {h.headline}")
    """
    
    # FinViz requires user-agent to avoid blocks
    FINVIZ_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }
    
    def __init__(self, config: Optional[SentimentConfig] = None):
        """Initialize the hybrid news client."""
        self.config = config or (get_sentiment_config() if get_sentiment_config else None)
        
        # Load API keys from config or environment
        if self.config:
            self.finnhub_key = self.config.FINNHUB_API_KEY
            self.newsapi_key = self.config.NEWSAPI_KEY
            self.stocktwits_key = self.config.STOCKTWITS_API_KEY
            self.tiingo_key = self.config.TIINGO_API_KEY
        else:
            # Fallback to direct env vars
            self.finnhub_key = os.getenv('FINNHUB_API_KEY')
            self.newsapi_key = os.getenv('NEWSAPI_KEY')
            self.stocktwits_key = os.getenv('STOCKTWITS_API_KEY')
            self.tiingo_key = os.getenv('TIINGO_API_KEY')
        
        # Initialize caches
        self._sentiment_cache = SimpleCache(default_ttl=300)  # 5 min
        self._news_cache = SimpleCache(default_ttl=120)        # 2 min
        
        # Rate limiting
        self._last_request_time: Dict[str, float] = {}
        self._min_request_interval = 0.5  # seconds between requests to same source
        
        # Session for connection pooling
        self._session = requests.Session()
        self._session.headers.update(self.FINVIZ_HEADERS)
        
        # Phase 2: Headline sentiment analyzer
        self._headline_analyzer = get_sentiment_analyzer()
        
        # =====================================================================
        # Phase 4: Self-Healing - Circuit Breakers & Data Degradation Tracking
        # =====================================================================
        self._circuit_breakers = {
            'finnhub': CircuitBreaker('Finnhub', failure_threshold=3, failure_window=60, recovery_timeout=300),
            'finviz': CircuitBreaker('FinViz', failure_threshold=3, failure_window=60, recovery_timeout=300),
            'stocktwits': CircuitBreaker('StockTwits', failure_threshold=3, failure_window=60, recovery_timeout=300),
            'newsapi': CircuitBreaker('NewsAPI', failure_threshold=3, failure_window=60, recovery_timeout=300),
        }
        
        self._data_degraded = DataDegradedWarning()
        
        logger.info(f"🔌 HybridNewsClient initialized (Phase 4: Self-Healing)")
        logger.info(f"   Finnhub: {'✅' if self.finnhub_key else '❌ (using mock)'}")
        logger.info(f"   NewsAPI: {'✅' if self.newsapi_key else '❌'}")
        logger.info(f"   FinViz:  ✅ (no key required)")
        logger.info(f"   VADER:   {'✅' if VADER_AVAILABLE else '❌'}")
        logger.info(f"   TextBlob: {'✅' if TEXTBLOB_AVAILABLE else '❌'}")
        logger.info(f"   Circuit Breakers: ✅ (3 failures/1min -> 5min cooldown)")
    
    def _rate_limit(self, source: str) -> None:
        """Enforce rate limiting between requests."""
        last_time = self._last_request_time.get(source, 0)
        elapsed = time.time() - last_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time[source] = time.time()
    
    # =========================================================================
    # SENTIMENT METHODS
    # =========================================================================
    
    def get_retail_sentiment(self, symbol: str) -> SentimentResult:
        """
        Get retail sentiment score for a symbol.
        
        Tries sources in order:
        1. Finnhub (if API key configured)
        2. StockTwits (public API)
        3. Mock data (fallback)
        
        Args:
            symbol: Stock ticker symbol (e.g., 'NVDA')
            
        Returns:
            SentimentResult with score 0-1 and metadata
        """
        symbol = symbol.upper().strip()
        cache_key = f"sentiment:{symbol}"
        
        # Check cache first
        cached = self._sentiment_cache.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for sentiment:{symbol}")
            return cached
        
        result = None
        
        # Try Finnhub first (most reliable)
        if self.finnhub_key:
            result = self._get_finnhub_sentiment(symbol)
        
        # Fallback to StockTwits
        if result is None:
            result = self._get_stocktwits_sentiment(symbol)
        
        # Final fallback to mock
        if result is None:
            result = self._get_mock_sentiment(symbol)
        
        # Cache and return
        self._sentiment_cache.set(cache_key, result)
        return result
    
    def _get_finnhub_sentiment(self, symbol: str) -> Optional[SentimentResult]:
        """
        Get sentiment from Finnhub API with circuit breaker protection.
        
        Phase 4: If circuit is open, returns None immediately.
        """
        if not self.finnhub_key:
            return None
        
        # Phase 4: Check circuit breaker
        circuit = self._circuit_breakers['finnhub']
        if not circuit.is_available:
            logger.debug(f"Finnhub circuit OPEN for {symbol}, skipping")
            self._data_degraded.mark_degraded('finnhub', 'Circuit breaker open')
            return None
        
        try:
            self._rate_limit('finnhub')
            
            # Finnhub social sentiment endpoint
            url = f"https://finnhub.io/api/v1/stock/social-sentiment"
            params = {
                'symbol': symbol,
                'token': self.finnhub_key
            }
            
            response = self._session.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                # Parse Finnhub response
                reddit_data = data.get('reddit', [])
                twitter_data = data.get('twitter', [])
                
                # Aggregate sentiment
                total_positive = 0
                total_negative = 0
                
                for item in reddit_data + twitter_data:
                    total_positive += item.get('positiveMention', 0)
                    total_negative += item.get('negativeMention', 0)
                
                total = total_positive + total_negative
                if total > 0:
                    score = total_positive / total
                else:
                    score = 0.5  # Neutral if no data
                
                label = self._score_to_label(score)
                
                # Phase 4: Record success
                circuit.record_success()
                self._data_degraded.mark_healthy('finnhub')
                
                return SentimentResult(
                    symbol=symbol,
                    score=score,
                    label=label,
                    source='finnhub',
                    confidence=min(0.9, total / 100),  # More mentions = higher confidence
                    bullish_count=total_positive,
                    bearish_count=total_negative,
                    is_mock=False,
                    raw_data=data
                )
            
            elif response.status_code == 401:
                logger.warning("Finnhub API key invalid or expired")
                circuit.record_failure()
                return None
            
            elif response.status_code == 429:
                logger.warning("Finnhub rate limit reached")
                circuit.record_failure()
                return None
            
            else:
                logger.warning(f"Finnhub unexpected status: {response.status_code}")
                circuit.record_failure()
                return None
            
        except requests.exceptions.Timeout:
            logger.warning(f"Finnhub timeout for {symbol}")
            circuit.record_failure()
            self._data_degraded.mark_degraded('finnhub', 'Timeout')
        except Exception as e:
            logger.error(f"Finnhub error for {symbol}: {e}")
            circuit.record_failure()
            self._data_degraded.mark_degraded('finnhub', str(e))
        
        return None
    
    def _get_stocktwits_sentiment(self, symbol: str) -> Optional[SentimentResult]:
        """Get sentiment from StockTwits public API."""
        try:
            self._rate_limit('stocktwits')
            
            # StockTwits streams endpoint (public)
            url = f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"
            
            response = self._session.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                messages = data.get('messages', [])
                if not messages:
                    return None
                
                # Count bullish/bearish messages
                bullish = 0
                bearish = 0
                
                for msg in messages[:30]:  # Analyze last 30 messages
                    sentiment = msg.get('entities', {}).get('sentiment', {})
                    if sentiment:
                        if sentiment.get('basic') == 'Bullish':
                            bullish += 1
                        elif sentiment.get('basic') == 'Bearish':
                            bearish += 1
                
                total = bullish + bearish
                if total > 0:
                    score = bullish / total
                else:
                    score = 0.5
                
                label = self._score_to_label(score)
                
                return SentimentResult(
                    symbol=symbol,
                    score=score,
                    label=label,
                    source='stocktwits',
                    confidence=min(0.7, total / 20),
                    bullish_count=bullish,
                    bearish_count=bearish,
                    is_mock=False,
                    raw_data={'message_count': len(messages)}
                )
            
        except Exception as e:
            logger.debug(f"StockTwits error for {symbol}: {e}")
        
        return None
    
    def _get_mock_sentiment(self, symbol: str) -> SentimentResult:
        """Generate mock sentiment for testing."""
        # Use symbol hash for consistent mock data
        seed = int(hashlib.md5(symbol.encode()).hexdigest()[:8], 16)
        random.seed(seed + int(time.time() // 3600))  # Change hourly
        
        # Generate realistic-looking mock data
        base_score = random.uniform(0.3, 0.7)
        
        # Add symbol-specific bias
        symbol_bias = {
            'NVDA': 0.15,   # Tech generally bullish
            'TSLA': 0.1,    # Volatile but bullish
            'SPY': 0.05,    # Market neutral
            'GLD': -0.05,   # Counter-cyclical
            'AMD': 0.1,
            'AAPL': 0.08,
        }
        bias = symbol_bias.get(symbol, 0)
        score = max(0.1, min(0.9, base_score + bias))
        
        label = self._score_to_label(score)
        
        return SentimentResult(
            symbol=symbol,
            score=score,
            label=label,
            source='mock',
            confidence=0.5,
            bullish_count=int(score * 100),
            bearish_count=int((1 - score) * 100),
            is_mock=True
        )
    
    @staticmethod
    def _score_to_label(score: float) -> str:
        """Convert numeric score to label."""
        if score >= 0.6:
            return 'Bullish'
        elif score <= 0.4:
            return 'Bearish'
        else:
            return 'Neutral'
    
    # =========================================================================
    # NEWS HEADLINES METHODS
    # =========================================================================
    
    def get_finviz_headlines(self, symbol: str, max_items: int = 20,
                             sentiment_filter: Optional[str] = None) -> List[NewsHeadline]:
        """
        Get news headlines with circuit breaker and automatic fallbacks.
        
        Phase 4: Fallback chain: FinViz -> NewsAPI -> Default "No News"
        
        Args:
            symbol: Stock ticker symbol
            max_items: Maximum headlines to return
            sentiment_filter: Optional filter - 'Positive', 'Negative', 'Neutral', or None for all
            
        Returns:
            List of NewsHeadline objects with sentiment classification
        """
        symbol = symbol.upper().strip()
        cache_key = f"news:{symbol}"
        
        # Check cache
        cached = self._news_cache.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for news:{symbol}")
            filtered = self._filter_by_sentiment(cached, sentiment_filter)
            return filtered[:max_items]
        
        headlines = []
        
        # Phase 4: Try FinViz first (with circuit breaker)
        finviz_circuit = self._circuit_breakers['finviz']
        if finviz_circuit.is_available:
            headlines = self._scrape_finviz_headlines(symbol, max_items)
            if headlines:
                finviz_circuit.record_success()
                self._data_degraded.mark_healthy('finviz')
        else:
            logger.debug(f"FinViz circuit OPEN for {symbol}, trying fallback")
        
        # Phase 4: Fallback to NewsAPI if FinViz failed
        if not headlines and self.newsapi_key:
            newsapi_circuit = self._circuit_breakers['newsapi']
            if newsapi_circuit.is_available:
                logger.info(f"📰 Falling back to NewsAPI for {symbol}")
                headlines = self._get_newsapi_headlines(symbol, max_items)
                if headlines:
                    newsapi_circuit.record_success()
                    self._data_degraded.mark_degraded('finviz', 'Using NewsAPI fallback')
        
        # Phase 4: Final fallback to "No News Available"
        if not headlines:
            logger.warning(f"⚠️ No news sources available for {symbol}")
            self._data_degraded.mark_degraded('news', 'No news sources available')
            headlines = [NewsHeadline(
                time=datetime.now().strftime("%I:%M%p"),
                headline=f"No news available for {symbol}",
                link="",
                source="System",
                sentiment=0.0,
                sentiment_label="Neutral",
                sentiment_compound=0.0
            )]
        
        # Cache results
        self._news_cache.set(cache_key, headlines)
        
        # Apply sentiment filter
        filtered = self._filter_by_sentiment(headlines, sentiment_filter)
        return filtered[:max_items]
    
    def _scrape_finviz_headlines(self, symbol: str, max_items: int = 20) -> List[NewsHeadline]:
        """
        Internal method to scrape FinViz headlines.
        
        Fast and reliable - no API key required.
        Target: < 500ms response time.
        
        Phase 2: Each headline is classified as Positive/Negative/Neutral.
        Phase 4: Includes circuit breaker failure recording.
        """
        headlines = []
        start_time = time.time()
        
        try:
            self._rate_limit('finviz')
            
            url = f"https://finviz.com/quote.ashx?t={symbol}"
            response = self._session.get(url, timeout=3)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find the news table
                news_table = soup.find('table', {'id': 'news-table'})
                
                if news_table:
                    rows = news_table.find_all('tr')
                    current_date = ''
                    
                    for row in rows[:max_items * 2]:  # Get extra in case some are filtered
                        cells = row.find_all('td')
                        if len(cells) >= 2:
                            # First cell has date/time
                            time_cell = cells[0].text.strip()
                            
                            # Parse time - could be "Jan-01" or "10:30AM"
                            if len(time_cell) > 8:  # It's a date
                                current_date = time_cell.split()[0]
                                display_time = time_cell
                            else:
                                display_time = time_cell
                            
                            # Second cell has headline and link
                            link_tag = cells[1].find('a')
                            if link_tag:
                                headline_text = link_tag.text.strip()
                                link_url = link_tag.get('href', '')
                                
                                # Extract source if in parentheses
                                source = ''
                                source_span = cells[1].find('span', class_='news-link-right')
                                if source_span:
                                    source = source_span.text.strip('() ')
                                
                                # Phase 2: Analyze sentiment
                                polarity, label, compound = self._headline_analyzer.analyze(headline_text)
                                
                                headlines.append(NewsHeadline(
                                    time=display_time,
                                    headline=headline_text,
                                    link=link_url,
                                    source=source,
                                    sentiment=polarity,
                                    sentiment_label=label,
                                    sentiment_compound=compound
                                ))
                        
                        if len(headlines) >= max_items * 2:  # Get more for filtering
                            break
            
            elapsed = time.time() - start_time
            logger.debug(f"FinViz scrape for {symbol}: {len(headlines)} headlines in {elapsed:.2f}s")
            
            if elapsed > 0.5:
                logger.warning(f"FinViz scrape exceeded 500ms target: {elapsed:.2f}s")
        
        except requests.exceptions.Timeout:
            logger.warning(f"FinViz timeout for {symbol}")
            self._circuit_breakers['finviz'].record_failure()
            self._data_degraded.mark_degraded('finviz', 'Timeout')
        except Exception as e:
            logger.error(f"FinViz scrape error for {symbol}: {e}")
            self._circuit_breakers['finviz'].record_failure()
            self._data_degraded.mark_degraded('finviz', str(e))
        
        return headlines
    
    def _filter_by_sentiment(self, headlines: List[NewsHeadline], 
                            sentiment_filter: Optional[str]) -> List[NewsHeadline]:
        """Filter headlines by sentiment label."""
        if not sentiment_filter:
            return headlines
        
        sentiment_filter = sentiment_filter.capitalize()
        if sentiment_filter not in ('Positive', 'Negative', 'Neutral'):
            return headlines
        
        return [h for h in headlines if h.sentiment_label == sentiment_filter]
    
    def get_sentiment_summary(self, symbol: str) -> Dict[str, Any]:
        """
        Get sentiment summary for headlines of a symbol.
        
        Returns counts and percentages of positive/negative/neutral headlines.
        """
        headlines = self.get_finviz_headlines(symbol, max_items=30)
        
        total = len(headlines)
        if total == 0:
            return {
                'symbol': symbol,
                'total': 0,
                'positive': 0, 'negative': 0, 'neutral': 0,
                'positive_pct': 0, 'negative_pct': 0, 'neutral_pct': 0,
                'overall_sentiment': 'Neutral',
                'avg_compound': 0.0
            }
        
        positive = sum(1 for h in headlines if h.sentiment_label == 'Positive')
        negative = sum(1 for h in headlines if h.sentiment_label == 'Negative')
        neutral = total - positive - negative
        
        avg_compound = sum(h.sentiment_compound for h in headlines) / total
        
        # Determine overall sentiment
        if positive > negative + 3:
            overall = 'Bullish'
        elif negative > positive + 3:
            overall = 'Bearish'
        else:
            overall = 'Neutral'
        
        return {
            'symbol': symbol,
            'total': total,
            'positive': positive,
            'negative': negative,
            'neutral': neutral,
            'positive_pct': round(positive / total * 100, 1),
            'negative_pct': round(negative / total * 100, 1),
            'neutral_pct': round(neutral / total * 100, 1),
            'overall_sentiment': overall,
            'avg_compound': round(avg_compound, 3)
        }
    
    def get_combined_news(self, symbol: str, max_items: int = 20) -> List[NewsHeadline]:
        """
        Get news from multiple sources combined and deduplicated.
        
        Sources: FinViz (primary), NewsAPI (if configured), Tiingo (backup)
        
        Args:
            symbol: Stock ticker symbol
            max_items: Maximum headlines to return
            
        Returns:
            List of NewsHeadline objects from all sources
        """
        all_headlines = []
        
        # Primary: FinViz
        finviz_news = self.get_finviz_headlines(symbol, max_items)
        all_headlines.extend(finviz_news)
        
        # Secondary: NewsAPI if configured
        if self.newsapi_key:
            newsapi_headlines = self._get_newsapi_headlines(symbol, max_items // 2)
            all_headlines.extend(newsapi_headlines)
        
        # Deduplicate by headline similarity
        seen_headlines = set()
        unique_headlines = []
        
        for h in all_headlines:
            # Simple dedup by first 50 chars of headline
            key = h.headline[:50].lower()
            if key not in seen_headlines:
                seen_headlines.add(key)
                unique_headlines.append(h)
        
        return unique_headlines[:max_items]
    
    def _get_newsapi_headlines(self, symbol: str, max_items: int = 10) -> List[NewsHeadline]:
        """Get headlines from NewsAPI."""
        if not self.newsapi_key:
            return []
        
        try:
            self._rate_limit('newsapi')
            
            # Map symbol to company name for better search
            company_names = {
                'NVDA': 'NVIDIA',
                'TSLA': 'Tesla',
                'AAPL': 'Apple',
                'MSFT': 'Microsoft',
                'AMD': 'AMD',
                'SPY': 'S&P 500',
                'GLD': 'Gold',
            }
            query = company_names.get(symbol, symbol)
            
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': query,
                'apiKey': self.newsapi_key,
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': max_items
            }
            
            response = self._session.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                headlines = []
                
                for article in data.get('articles', []):
                    pub_time = article.get('publishedAt', '')
                    if pub_time:
                        # Parse ISO timestamp to display time
                        try:
                            dt = datetime.fromisoformat(pub_time.replace('Z', '+00:00'))
                            display_time = dt.strftime('%I:%M%p')
                        except:
                            display_time = pub_time[:10]
                    else:
                        display_time = ''
                    
                    headlines.append(NewsHeadline(
                        time=display_time,
                        headline=article.get('title', ''),
                        link=article.get('url', ''),
                        source=article.get('source', {}).get('name', 'NewsAPI')
                    ))
                
                return headlines
        
        except Exception as e:
            logger.debug(f"NewsAPI error for {symbol}: {e}")
        
        return []
    
    # =========================================================================
    # AGGREGATED METHODS
    # =========================================================================
    
    def get_hype_score(self, symbol: str) -> Dict[str, Any]:
        """
        Get a combined "hype score" for display in gauges.
        
        Combines:
        - Sentiment score (0-1)
        - News volume indicator
        - Recent price momentum proxy
        
        Returns dict suitable for DAQ gauge components.
        """
        sentiment = self.get_retail_sentiment(symbol)
        headlines = self.get_finviz_headlines(symbol, max_items=10)
        
        # Calculate hype multiplier based on news volume
        news_count = len(headlines)
        news_multiplier = 1.0 + (news_count / 20)  # Up to 1.5x for high news volume
        
        # Combined hype score
        hype_score = sentiment.score * min(news_multiplier, 1.3)
        hype_score = max(0, min(1, hype_score))  # Clamp to 0-1
        
        return {
            'symbol': symbol,
            'hype_score': hype_score,
            'sentiment_score': sentiment.score,
            'sentiment_label': sentiment.label,
            'sentiment_source': sentiment.source,
            'news_count': news_count,
            'is_mock': sentiment.is_mock,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_multi_symbol_sentiment(self, symbols: List[str]) -> Dict[str, SentimentResult]:
        """
        Get sentiment for multiple symbols efficiently.
        
        Args:
            symbols: List of ticker symbols
            
        Returns:
            Dict mapping symbol to SentimentResult
        """
        results = {}
        for symbol in symbols:
            results[symbol] = self.get_retail_sentiment(symbol)
        return results
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._sentiment_cache.clear()
        self._news_cache.clear()
        logger.info("Cleared news client cache")
    
    # =========================================================================
    # PHASE 4: HEALTH & STATUS METHODS
    # =========================================================================
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status for admin panel.
        
        Returns dict with:
        - api_status: Status of each API (True/False/None)
        - circuit_breakers: State of each circuit breaker
        - degraded_sources: Currently degraded data sources
        - is_healthy: Overall health status
        """
        api_status = {
            'finnhub': self.finnhub_key is not None and self._circuit_breakers['finnhub'].is_available,
            'finviz': self._circuit_breakers['finviz'].is_available,
            'stocktwits': self._circuit_breakers['stocktwits'].is_available,
            'newsapi': self.newsapi_key is not None and self._circuit_breakers['newsapi'].is_available,
            'tiingo': self.tiingo_key is not None,
        }
        
        circuit_statuses = {
            name: cb.get_status() for name, cb in self._circuit_breakers.items()
        }
        
        degraded = self._data_degraded.get_degraded_sources()
        
        # Overall healthy if at least one news source is available
        is_healthy = api_status['finviz'] or api_status['newsapi']
        
        return {
            'api_status': api_status,
            'circuit_breakers': circuit_statuses,
            'degraded_sources': degraded,
            'is_healthy': is_healthy,
            'has_degradation': self._data_degraded.has_degradation,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_api_status_simple(self) -> Dict[str, bool]:
        """Get simple API status (True/False) for health check display."""
        return {
            'Finnhub': bool(self.finnhub_key) and self._circuit_breakers['finnhub'].is_available,
            'FinViz': self._circuit_breakers['finviz'].is_available,
            'StockTwits': self._circuit_breakers['stocktwits'].is_available,
            'NewsAPI': bool(self.newsapi_key) and self._circuit_breakers['newsapi'].is_available,
            'Tiingo': bool(self.tiingo_key),
        }
    
    def reset_circuit_breakers(self) -> None:
        """Reset all circuit breakers to CLOSED state."""
        for name, cb in self._circuit_breakers.items():
            cb._state = CircuitBreakerState.CLOSED
            cb._failures.clear()
            logger.info(f"🔄 Reset circuit breaker: {name}")
        
        # Clear degraded warnings
        self._data_degraded._degraded_sources.clear()
        self._data_degraded._degraded_since.clear()
        logger.info("✅ All circuit breakers reset")


# =============================================================================
# MODULE-LEVEL SINGLETON
# =============================================================================

_client_instance: Optional[HybridNewsClient] = None


def get_news_client() -> HybridNewsClient:
    """Get the singleton news client instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = HybridNewsClient()
    return _client_instance


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == '__main__':
    # Quick test when run directly
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("HybridNewsClient Test")
    print("=" * 60)
    
    client = HybridNewsClient()
    
    test_symbols = ['NVDA', 'TSLA', 'SPY', 'GLD']
    
    for symbol in test_symbols:
        print(f"\n📊 {symbol}")
        print("-" * 40)
        
        # Test sentiment
        sentiment = client.get_retail_sentiment(symbol)
        print(f"  Sentiment: {sentiment.score:.2f} ({sentiment.label}) via {sentiment.source}")
        print(f"  Confidence: {sentiment.confidence:.2f}")
        
        # Test headlines
        headlines = client.get_finviz_headlines(symbol, max_items=3)
        print(f"  Headlines ({len(headlines)}):")
        for h in headlines[:3]:
            print(f"    {h.time}: {h.headline[:60]}...")
        
        # Test hype score
        hype = client.get_hype_score(symbol)
        print(f"  Hype Score: {hype['hype_score']:.2f}")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")

