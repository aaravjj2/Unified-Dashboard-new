"""
Local LLM Connector

Provides abstraction for local LLM inference:
- OpenAI (cloud)
- GPT4All (local)
- Ollama (local server)
- Mock (for testing)

Environment variables:
- LLM_PROVIDER: openai|gpt4all|ollama|mock (default: mock)
- OLLAMA_HOST: Ollama server URL (default: http://localhost:11434)
- GPT4ALL_MODEL: GPT4All model name (default: orca-mini-3b-gguf2-q4_0.gguf)
- OpenAI_API_KEY: OpenAI API key
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import hashlib
from pathlib import Path

# Load environment variables for API keys
from dotenv import load_dotenv
_base = Path(__file__).parent.parent
load_dotenv(_base / "keys.env", override=True)
load_dotenv(_base.parent / "doppler.env", override=True)
load_dotenv(_base.parent / "keys.env", override=True)

logger = logging.getLogger(__name__)


class LLMConnector(ABC):
    """Abstract base class for LLM connectors."""
    
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """Generate text from prompt."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the LLM is available."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get connector name."""
        pass


class MockLLMConnector(LLMConnector):
    """
    Mock LLM for testing and fallback.
    
    Generates deterministic responses based on prompt hash.
    """
    
    def __init__(self):
        self._available = True
    
    @property
    def name(self) -> str:
        return "mock"
    
    def is_available(self) -> bool:
        return self._available
    
    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """Generate deterministic mock response."""
        # Extract query from prompt if present
        query = ""
        if "Question:" in prompt:
            parts = prompt.split("Question:")
            if len(parts) > 1:
                query = parts[1].split("\n")[0].strip()[:100]
        elif "Query:" in prompt:
            parts = prompt.split("Query:")
            if len(parts) > 1:
                query = parts[1].split("\n")[0].strip()[:100]
        else:
            query = prompt[:100]
        
        # Generate deterministic response based on query
        seed = int(hashlib.md5(query.encode()).hexdigest()[:8], 16)
        
        responses = [
            f"Based on the provided context, {query.lower()} relates to market momentum factors and sector analysis. The research indicates positive signals in technology stocks with strong momentum characteristics.",
            f"Analyzing the documents for '{query}': The data suggests focusing on factor exposures, particularly momentum and value metrics. Historical analysis shows these factors have predictive power.",
            f"In response to your query about {query.lower()}: The research briefs indicate this topic connects to current market trends and sector rotation patterns. Consider both fundamental and technical indicators.",
            f"The research documents provide insights on {query.lower()}. Key findings include momentum persistence in trending markets and value opportunities in oversold sectors.",
            f"Based on indexed research, {query.lower()} is addressed across multiple documents. The consensus suggests careful analysis of factor exposures and market conditions."
        ]
        
        return responses[seed % len(responses)]


class GPT4AllConnector(LLMConnector):
    """
    GPT4All local LLM connector.
    
    Uses GPT4All Python bindings for local inference.
    """
    
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.getenv("GPT4ALL_MODEL", "orca-mini-3b-gguf2-q4_0.gguf")
        self._model = None
        self._available = None
    
    @property
    def name(self) -> str:
        return "gpt4all"
    
    def is_available(self) -> bool:
        if self._available is None:
            try:
                from gpt4all import GPT4All
                self._available = True
            except ImportError:
                logger.warning("gpt4all package not installed")
                self._available = False
        return self._available
    
    def _load_model(self):
        """Lazy load the GPT4All model."""
        if self._model is None and self.is_available():
            try:
                from gpt4all import GPT4All
                self._model = GPT4All(self.model_name)
                logger.info(f"Loaded GPT4All model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to load GPT4All model: {e}")
                self._available = False
    
    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """Generate text using GPT4All."""
        self._load_model()
        
        if self._model is None:
            raise RuntimeError("GPT4All model not available")
        
        try:
            response = self._model.generate(
                prompt,
                max_tokens=max_tokens,
                temp=temperature
            )
            return response
        except Exception as e:
            logger.error(f"GPT4All generation failed: {e}")
            raise


class OpenAIConnector(LLMConnector):
    """
    OpenAI API connector for cloud LLM inference.
    
    Uses OpenAI's API for generation.
    """
    
    def __init__(self, model: str = "gpt-3.5-turbo"):
        self.model = model
        self._api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OpenAI_API_KEY")
        self._available = None
        self._validated = False
    
    @property
    def name(self) -> str:
        return "openai"
    
    def is_available(self) -> bool:
        if self._available is None:
            # Basic check - key exists and is long enough
            if not self._api_key or len(self._api_key) < 20:
                self._available = False
            else:
                # Don't validate on every check - just verify format
                self._available = self._api_key.startswith("sk-")
        return self._available
    
    def validate_key(self) -> bool:
        """Test if the API key is actually valid."""
        if self._validated:
            return self._available
        
        if not self._api_key:
            self._validated = True
            self._available = False
            return False
        
        try:
            import requests
            response = requests.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=5
            )
            self._available = response.status_code == 200
            self._validated = True
            if not self._available:
                logger.warning(f"OpenAI API key validation failed: {response.status_code}")
        except Exception as e:
            logger.warning(f"OpenAI API key validation error: {e}")
            self._available = False
            self._validated = True
        
        return self._available
    
    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """Generate text using OpenAI API."""
        if not self.is_available():
            raise RuntimeError("OpenAI API key not available")
        
        try:
            import requests
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                logger.warning(f"OpenAI API error: {response.status_code} - {response.text}")
                raise RuntimeError(f"OpenAI API error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise


class OllamaConnector(LLMConnector):
    """
    Ollama local LLM server connector.
    
    Connects to Ollama API for local inference.
    """
    
    def __init__(self, host: Optional[str] = None, model: str = None):
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self._available = None
        self._detected_model = None
        
        # Auto-detect model if not specified
        if model:
            self.model = model
        else:
            # Try to detect available models
            try:
                import requests
                response = requests.get(f"{self.host}/api/tags", timeout=2)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [m.get("name", "") for m in models]
                    
                    # Prefer Mistral models (same as AI chatbot)
                    mistral_models = [m for m in model_names if "mistral" in m.lower()]
                    if mistral_models:
                        self.model = mistral_models[0]
                        self._detected_model = self.model
                        logger.info(f"Auto-detected Ollama model: {self.model}")
                    elif model_names:
                        # Use first available model
                        self.model = model_names[0]
                        self._detected_model = self.model
                        logger.info(f"Auto-detected Ollama model: {self.model}")
                    else:
                        self.model = "llama2"  # Fallback default
                        logger.warning("No Ollama models found, using default: llama2")
                else:
                    self.model = "llama2"
            except Exception as e:
                logger.warning(f"Failed to auto-detect Ollama model: {e}")
                self.model = "llama2"
    
    @property
    def name(self) -> str:
        return "ollama"
    
    def is_available(self) -> bool:
        if self._available is None:
            try:
                import requests
                response = requests.get(f"{self.host}/api/tags", timeout=2)
                self._available = response.status_code == 200
            except Exception:
                self._available = False
        return self._available
    
    def generate(self, prompt: str, max_tokens: int = 150, temperature: float = 0.7) -> str:
        """Generate text using Ollama API."""
        if not self.is_available():
            raise RuntimeError(f"Ollama server not available at {self.host}")
        
        try:
            import requests
            response = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,  # Reduced from 512 to 150 for 3-4x speedup
                        "temperature": temperature
                    }
                },
                timeout=30.0  # Reduced from 60s
            )
            
            if response.status_code == 200:
                return response.json().get("response", "")
            elif response.status_code == 404:
                # Model not found - provide helpful error message
                raise RuntimeError(f"Ollama model '{self.model}' not found. Please pull the model first with: ollama pull {self.model}")
            else:
                raise RuntimeError(f"Ollama API error: {response.status_code} - {response.text[:200]}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama connection failed: {e}")
            raise RuntimeError(f"Ollama connection error: {str(e)}")
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise


def get_llm_connector(provider: Optional[str] = None) -> LLMConnector:
    """
    Get an LLM connector based on provider setting.
    
    Falls back through the chain: OpenAI -> Ollama -> GPT4All -> Mock
    
    Args:
        provider: LLM provider name (openai, gpt4all, ollama, mock)
        
    Returns:
        LLMConnector instance
    """
    provider = provider or os.getenv("LLM_PROVIDER", "auto")  # Default to auto
    
    # In deterministic mode, always use mock
    if os.getenv("RL_DETERMINISTIC", "0") == "1":
        logger.info("Deterministic mode: using mock LLM")
        return MockLLMConnector()
    
    if provider == "openai":
        connector = OpenAIConnector()
        if connector.is_available() and connector.validate_key():
            logger.info("Using OpenAI LLM connector")
            return connector
        logger.warning("OpenAI API key invalid, trying local LLMs...")
        # Fallback to local
        provider = "ollama"
    
    if provider == "ollama":
        connector = OllamaConnector()
        if connector.is_available():
            logger.info("Using Ollama LLM connector")
            return connector
        logger.warning("Ollama not available, trying GPT4All...")
        # Try GPT4All as second option
        gpt4all_connector = GPT4AllConnector()
        if gpt4all_connector.is_available():
            logger.info("Using GPT4All as fallback")
            return gpt4all_connector
        logger.warning("No local LLM available, falling back to mock")
        return MockLLMConnector()
    
    elif provider == "gpt4all":
        connector = GPT4AllConnector()
        if connector.is_available():
            logger.info("Using GPT4All LLM connector")
            return connector
        logger.warning("GPT4All not available, falling back to mock")
        return MockLLMConnector()
    
    elif provider == "mock":
        logger.info("Using mock LLM connector (explicitly requested)")
        return MockLLMConnector()
    
    else:  # auto or unknown
        # Try in order: OpenAI -> Ollama -> GPT4All -> Mock
        openai_connector = OpenAIConnector()
        if openai_connector.is_available() and openai_connector.validate_key():
            logger.info("Auto: Using OpenAI LLM")
            return openai_connector
        
        ollama_connector = OllamaConnector()
        if ollama_connector.is_available():
            logger.info("Auto: Using Ollama LLM")
            return ollama_connector
        
        gpt4all_connector = GPT4AllConnector()
        if gpt4all_connector.is_available():
            logger.info("Auto: Using GPT4All LLM")
            return gpt4all_connector
        
        logger.info("Auto: No LLM available, using mock")
        return MockLLMConnector()


class RAGQueryEngine:
    """
    RAG Query Engine that combines vector search with LLM generation.
    """
    
    # Comprehensive English dictionary to exclude from ticker extraction
    COMMON_ENGLISH_WORDS = {
        # Articles
        "A", "AN", "THE",
        # Pronouns
        "I", "YOU", "HE", "SHE", "IT", "WE", "THEY", "ME", "HIM", "HER", "US", "THEM",
        "MY", "YOUR", "HIS", "ITS", "OUR", "THIS", "THAT", "THESE", "THOSE", "MINE", "YOURS",
        "OURS", "THEIRS", "MYSELF", "YOURSELF", "HIMSELF", "HERSELF", "ITSELF", "OURSELVES",
        # Verbs (common)
        "AM", "IS", "ARE", "WAS", "WERE", "BE", "BEEN", "BEING",
        "HAVE", "HAS", "HAD", "DO", "DOES", "DID", "WILL", "WOULD", "SHALL", "SHOULD",
        "CAN", "COULD", "MAY", "MIGHT", "MUST",
        "GET", "GETS", "GOT", "GOTTEN", "MAKE", "MAKES", "MADE", "GO", "GOES", "WENT", "GONE",
        "TAKE", "TAKES", "TOOK", "TAKEN", "COME", "COMES", "CAME",
        "SEE", "SAW", "SEEN", "KNOW", "KNEW", "KNOWN", "THINK", "THOUGHT",
        "TELL", "TOLD", "GIVE", "GAVE", "GIVEN", "FIND", "FOUND",
        "KEEP", "KEPT", "LET", "LEAVE", "LEFT", "FEEL", "FELT",
        "TRY", "TRIED", "ASK", "ASKED", "NEED", "NEEDED", "SEEM", "SEEMED",
        "HELP", "HELPED", "TALK", "TALKED", "TURN", "TURNED", "START", "STARTED",
        "SHOW", "SHOWED", "SHOWN", "HEAR", "HEARD", "PLAY", "PLAYED",
        "RUN", "RAN", "MOVE", "MOVED", "LIVE", "LIVED", "BELIEVE", "BELIEVED",
        "BRING", "BROUGHT", "HAPPEN", "HAPPENED", "WRITE", "WROTE", "WRITTEN",
        "STAND", "STOOD", "LOSE", "LOST", "PAY", "PAID", "MEET", "MET",
        "INCLUDE", "INCLUDED", "CONTINUE", "CONTINUED", "SET", "LEARN", "LEARNED",
        "CHANGE", "CHANGED", "LEAD", "LED", "UNDERSTAND", "UNDERSTOOD",
        "WATCH", "WATCHED", "FOLLOW", "FOLLOWED", "STOP", "STOPPED",
        "CREATE", "CREATED", "SPEAK", "SPOKE", "SPOKEN", "READ", "ALLOW", "ALLOWED",
        "ADD", "ADDED", "SPEND", "SPENT", "GROW", "GREW", "GROWN",
        "OPEN", "OPENED", "WALK", "WALKED", "WIN", "WON", "OFFER", "OFFERED",
        "REMEMBER", "REMEMBERED", "LOVE", "LOVED", "CONSIDER", "CONSIDERED",
        "APPEAR", "APPEARED", "BUY", "BOUGHT", "WAIT", "WAITED", "SERVE", "SERVED",
        "DIE", "DIED", "SEND", "SENT", "EXPECT", "EXPECTED", "BUILD", "BUILT",
        "STAY", "STAYED", "FALL", "FELL", "FALLEN", "CUT", "REACH", "REACHED",
        "KILL", "KILLED", "REMAIN", "REMAINED", "SUGGEST", "SUGGESTED",
        "RAISE", "RAISED", "PASS", "PASSED", "SELL", "SOLD", "REQUIRE", "REQUIRED",
        "REPORT", "REPORTED", "DECIDE", "DECIDED", "PULL", "PULLED",
        # Prepositions
        "IN", "ON", "AT", "TO", "FOR", "OF", "WITH", "FROM", "BY", "ABOUT",
        "AS", "INTO", "LIKE", "THROUGH", "AFTER", "OVER", "BETWEEN", "OUT", "AGAINST",
        "DURING", "WITHOUT", "BEFORE", "UNDER", "AROUND", "AMONG", "UPON",
        "ACROSS", "OFF", "ABOVE", "TOWARD", "TOWARDS", "BEHIND", "BELOW", "BESIDE",
        "NEAR", "INSIDE", "OUTSIDE", "WITHIN", "ALONG", "PAST", "SINCE", "UNTIL",
        # Conjunctions
        "AND", "OR", "BUT", "SO", "YET", "NOR", "IF", "THAN", "WHEN", "WHERE", "WHY",
        "WHILE", "ALTHOUGH", "THOUGH", "UNLESS", "BECAUSE", "SINCE", "AS", "UNTIL",
        "BEFORE", "AFTER", "WHENEVER", "WHEREVER", "WHETHER",
        # Question words
        "WHAT", "WHEN", "WHERE", "WHY", "WHO", "WHOM", "WHOSE", "WHICH", "HOW",
        # Common adjectives
        "GOOD", "BAD", "BEST", "BETTER", "WORST", "WORSE", "NEW", "OLD", "LAST", "LONG",
        "GREAT", "LITTLE", "OWN", "OTHER", "OLD", "RIGHT", "BIG", "HIGH", "DIFFERENT",
        "SMALL", "LARGE", "NEXT", "EARLY", "YOUNG", "IMPORTANT", "FEW", "PUBLIC",
        "SAME", "ABLE", "FULL", "SURE", "REAL", "LESS", "CERTAIN", "SHORT",
        "SMALL", "CLEAR", "MAJOR", "RECENT", "LATE", "HARD", "LEFT", "LEAST",
        "SIMPLE", "SPECIAL", "STRONG", "PARTICULAR", "SEVERAL", "POPULAR",
        "TRADITIONAL", "FINAL", "PERFECT", "FORWARD", "LOW", "WIDE", "COMMON",
        "POOR", "NATURAL", "SIGNIFICANT", "SIMILAR", "HOT", "DEAD", "CENTRAL",
        "HAPPY", "SERIOUS", "READY", "SIMPLE", "VARIOUS", "DIFFICULT", "LIKELY",
        "RECENT", "MEDICAL", "BLACK", "WHITE", "DARK", "CLOSE", "FINE", "DEEP",
        "PREVIOUS", "BEGINNING", "SOCIAL", "OUTSIDE", "WRONG", "LEGAL", "GENERAL",
        "INTERNATIONAL", "LOCAL", "POLITICAL", "ECONOMIC", "FOREIGN", "NATIONAL",
        # Common adverbs
        "VERY", "JUST", "NOW", "THEN", "HERE", "THERE", "WELL", "ALSO", "ONLY",
        "EVEN", "BACK", "STILL", "ALREADY", "NEVER", "ALWAYS", "OFTEN", "SOMETIMES",
        "USUALLY", "RATHER", "QUITE", "ALMOST", "PROBABLY", "PERHAPS", "MAYBE",
        "HOWEVER", "THEREFORE", "THUS", "HENCE", "INDEED", "INSTEAD", "OTHERWISE",
        "FURTHERMORE", "MOREOVER", "NEVERTHELESS", "NONETHELESS", "ANYWAY",
        "SOMEHOW", "SOMEWHERE", "ELSEWHERE", "TOGETHER", "APART", "ASIDE",
        # Numbers as words
        "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN",
        "ELEVEN", "TWELVE", "THIRTEEN", "FOURTEEN", "FIFTEEN", "TWENTY", "THIRTY",
        "FORTY", "FIFTY", "SIXTY", "SEVENTY", "EIGHTY", "NINETY", "HUNDRED", "THOUSAND",
        "MILLION", "BILLION", "TRILLION", "FIRST", "SECOND", "THIRD", "FOURTH", "FIFTH",
        # Other common words
        "SOME", "ANY", "MANY", "MUCH", "MORE", "MOST", "LESS", "FEW", "ALL", "BOTH",
        "EACH", "EVERY", "OTHER", "ANOTHER", "SUCH", "OWN", "SAME", "NEXT", "LAST", "FIRST",
        "PLEASE", "THANK", "THANKS", "YES", "NO", "OKAY", "OK", "SURE", "SORRY",
        "HELLO", "HI", "HEY", "GOODBYE", "BYE", "WELCOME", "EXCUSE",
        # Action/helper words
        "GIVE", "FIND", "TELL", "SHOW", "HELP", "USE", "USED", "USING", "KNOW", "THINK",
        "NEED", "WANT", "TRY", "ASK", "WORK", "SEEM", "FEEL", "LEAVE", "PUT",
        "MEAN", "KEEP", "LET", "BEGIN", "START", "STOP", "END", "FINISH",
    }
    
    # Comprehensive financial terminology (NOT stock tickers)
    FINANCIAL_TERMS = {
        # Market types & concepts
        "STOCK", "STOCKS", "EQUITY", "EQUITIES", "MARKET", "MARKETS", "EXCHANGE",
        "TRADING", "TRADE", "TRADES", "TRADED", "TRADER", "TRADERS",
        "INVEST", "INVESTMENT", "INVESTMENTS", "INVESTING", "INVESTOR", "INVESTORS",
        "PORTFOLIO", "PORTFOLIOS", "POSITION", "POSITIONS", "HOLDING", "HOLDINGS",
        "ACCOUNT", "ACCOUNTS", "ASSET", "ASSETS", "SECURITY", "SECURITIES",
        # Analysis types
        "ANALYSIS", "FUNDAMENTAL", "TECHNICAL", "QUANTITATIVE", "QUALITATIVE",
        "INDICATOR", "INDICATORS", "SIGNAL", "SIGNALS", "PATTERN", "PATTERNS",
        "TREND", "TRENDS", "TRENDING", "MOMENTUM", "VOLATILITY", "VOLUME",
        "CORRELATION", "COVARIANCE", "REGRESSION", "FACTOR", "FACTORS",
        # Financial metrics
        "PRICE", "PRICES", "VALUE", "VALUES", "VALUATION", "WORTH",
        "RETURN", "RETURNS", "YIELD", "YIELDS", "DIVIDEND", "DIVIDENDS",
        "EARNINGS", "REVENUE", "PROFIT", "PROFITS", "LOSS", "LOSSES",
        "MARGIN", "MARGINS", "RATIO", "RATIOS", "MULTIPLE", "MULTIPLES",
        "GROWTH", "DECLINE", "INCREASE", "DECREASE", "CHANGE", "CHANGES",
        "GAIN", "GAINS", "APPRECIATION", "DEPRECIATION",
        # Market participants
        "BULL", "BULLS", "BULLISH", "BEAR", "BEARS", "BEARISH",
        "BUYER", "BUYERS", "SELLER", "SELLERS", "BIDDER", "BIDDERS",
        "INSTITUTION", "INSTITUTIONAL", "RETAIL", "WHALE", "WHALES",
        "ANALYST", "ANALYSTS", "ADVISOR", "ADVISORS", "BROKER", "BROKERS",
        # Time periods
        "DAY", "DAILY", "WEEK", "WEEKLY", "MONTH", "MONTHLY",
        "QUARTER", "QUARTERLY", "YEAR", "YEARLY", "ANNUAL", "ANNUALLY",
        "PERIOD", "PERIODS", "TERM", "TERMS", "DURATION", "HORIZON",
        "TIMEFRAME", "TIMELINE", "CYCLE", "CYCLES",
        # Orders & execution
        "ORDER", "ORDERS", "BUY", "BUYING", "SELL", "SELLING",
        "BID", "BIDS", "ASK", "ASKS", "SPREAD", "SPREADS",
        "LIMIT", "LIMITS", "STOP", "MARKET", "EXECUTION",
        "FILL", "FILLED", "PARTIAL", "SLIPPAGE",
        # Risk & strategy
        "RISK", "RISKS", "RISKY", "HEDGE", "HEDGING", "DIVERSIFY", "DIVERSIFICATION",
        "ALLOCATION", "REBALANCE", "REBALANCING", "OPTIMIZE", "OPTIMIZATION",
        "STRATEGY", "STRATEGIES", "APPROACH", "APPROACHES", "METHOD", "METHODS",
        "TACTIC", "TACTICS", "TECHNIQUE", "TECHNIQUES", "SYSTEM", "SYSTEMS",
        # Options & derivatives
        "OPTION", "OPTIONS", "CALL", "CALLS", "PUT", "PUTS",
        "STRIKE", "EXPIRATION", "EXPIRY", "PREMIUM", "PREMIUMS",
        "GREEK", "GREEKS", "DELTA", "GAMMA", "THETA", "VEGA", "RHO",
        "IMPLIED", "INTRINSIC", "EXTRINSIC", "MONEYNESS",
        "DERIVATIVE", "DERIVATIVES", "FUTURE", "FUTURES", "FORWARD", "FORWARDS",
        "SWAP", "SWAPS", "CONTRACT", "CONTRACTS",
        # Technical indicators
        "RSI", "MACD", "EMA", "SMA", "BOLLINGER", "STOCHASTIC",
        "FIBONACCI", "PIVOT", "SUPPORT", "RESISTANCE", "BREAKOUT",
        "CHANNEL", "CROSSOVER", "DIVERGENCE", "CONVERGENCE",
        "OVERBOUGHT", "OVERSOLD", "CONSOLIDATION", "ACCUMULATION", "DISTRIBUTION",
        # Sectors & industries
        "SECTOR", "SECTORS", "INDUSTRY", "INDUSTRIES", "SEGMENT", "SEGMENTS",
        "TECHNOLOGY", "TECH", "FINANCE", "FINANCIAL", "HEALTHCARE", "HEALTH",
        "ENERGY", "CONSUMER", "INDUSTRIAL", "MATERIALS", "UTILITIES",
        "TELECOM", "REAL", "ESTATE", "DISCRETIONARY", "STAPLES",
        # Company metrics
        "COMPANY", "COMPANIES", "CORPORATION", "CORP", "INCORPORATED", "INC",
        "ENTERPRISE", "BUSINESS", "FIRM", "ORGANIZATION",
        "CAPITALIZATION", "MARKETCAP", "CAP", "OUTSTANDING", "SHARES",
        "FLOAT", "INSIDER", "INSTITUTIONAL", "OWNERSHIP",
        # Valuation
        "PE", "PB", "PS", "EV", "EBITDA", "FCF", "ROE", "ROA", "ROIC",
        "DEBT", "EQUITY", "LEVERAGE", "SOLVENCY", "LIQUIDITY",
        "BOOK", "TANGIBLE", "INTANGIBLE", "GOODWILL",
        # Market conditions
        "VOLATILE", "STABLE", "LIQUID", "ILLIQUID", "TRENDING", "RANGING",
        "CHOPPY", "CALM", "ACTIVE", "QUIET", "STRONG", "WEAK",
        "OVERBOUGHT", "OVERSOLD", "NEUTRAL", "SIDEWAYS",
        # Economic terms
        "MACRO", "MICRO", "GDP", "INFLATION", "DEFLATION", "RECESSION",
        "EXPANSION", "RECOVERY", "BOOM", "BUST", "CYCLE", "CYCLES",
        "RATE", "RATES", "INTEREST", "FEDERAL", "RESERVE", "FED",
        "MONETARY", "FISCAL", "POLICY", "POLICIES", "ECONOMIC", "ECONOMY",
        # Chart patterns
        "HEAD", "SHOULDERS", "TRIANGLE", "WEDGE", "FLAG", "PENNANT",
        "CUP", "HANDLE", "DOUBLE", "TOP", "BOTTOM", "ASCENDING", "DESCENDING",
        # Common non-ticker words in finance
        "MONEY", "CASH", "DOLLAR", "DOLLARS", "CENT", "CENTS",
        "FUND", "FUNDS", "BOND", "BONDS", "NOTE", "NOTES",
        "INDEX", "INDICES", "BENCHMARK", "COMPOSITE",
        "LIST", "LISTING", "LISTED", "DELISTED",
        "CHART", "CHARTS", "GRAPH", "GRAPHS", "DATA", "DATASET",
        "MOVERS", "GAINERS", "LOSERS", "LEADERS", "LAGGARDS",
        "PICK", "PICKS", "RECOMMENDATION", "RECOMMENDATIONS",
        "WATCHLIST", "SCREENER", "SCANNER", "FILTER", "FILTERS",
    }
    
    
    def __init__(self, llm_connector: Optional[LLMConnector] = None):
        self.llm = llm_connector or get_llm_connector()
        self._pipeline = None
    
    @property
    def pipeline(self):
        """Lazy load ingestion pipeline."""
        if self._pipeline is None:
            from background.research_ingest import get_pipeline
            self._pipeline = get_pipeline()
        return self._pipeline
    
    def query(self, question: str, top_k: int = 5, sources: str = "all") -> Dict[str, Any]:
        """
        Execute a RAG query.
        
        Args:
            question: The question to answer
            top_k: Number of source documents to retrieve
            sources: Source filter (all, briefs, news, docs)
            
        Returns:
            Dict with answer, sources, and metadata
        """
        # Retrieve relevant documents
        search_results = self.pipeline.search(question, top_k=top_k)
        
        # Filter by source type if specified
        if sources and sources != "all":
            search_results = [
                r for r in search_results 
                if self._matches_source_filter(r, sources)
            ]
        
        # Build context from retrieved documents
        context = self._build_context(search_results)
        
        # Generate prompt
        prompt = self._build_prompt(question, context)
        
        # Generate answer
        try:
            # Reduced max_tokens for faster response (150 instead of 512 = 3-4x faster)
            answer = self.llm.generate(prompt, max_tokens=150)
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            answer = f"Unable to generate answer: {str(e)}"
        
        # Create answer ID for tracking
        answer_id = hashlib.md5(f"{question}{answer}".encode()).hexdigest()[:12]
        
        return {
            "answer_id": answer_id,
            "answer": answer,
            "sources": search_results,
            "llm_provider": self.llm.name,
            "top_k": top_k,
            "query": question
        }
    
    def explain(self, answer_id: str) -> Dict[str, Any]:
        """
        Get explanation for a previous answer.
        
        Args:
            answer_id: ID of the answer to explain
            
        Returns:
            Explanation dict
        """
        # In a full implementation, we would store answers and their provenance
        # For now, return a generic explanation
        return {
            "answer_id": answer_id,
            "method": "Vector similarity search + LLM generation",
            "retrieval_method": "FAISS L2 distance",
            "llm_provider": self.llm.name,
            "explanation": "Retrieved top-k documents by vector similarity, "
                          "constructed context window, and generated response using LLM."
        }
    
    def _matches_source_filter(self, result: Dict, source_filter: str) -> bool:
        """Check if result matches source filter."""
        doc = self.pipeline.get_document(result.get("doc_id"))
        if not doc:
            return True
        
        source_type = doc.source_type
        
        if source_filter == "briefs":
            return source_type in ("brief", "text")
        elif source_filter == "news":
            return source_type == "news"
        elif source_filter == "docs":
            return source_type in ("pdf", "url")
        
        return True
    
    def _build_context(self, results: List[Dict]) -> str:
        """Build context string from search results."""
        if not results:
            return "No relevant documents found."
        
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(
                f"[Document {i}: {result.get('title', 'Untitled')}]\n"
                f"{result.get('snippet', '')}\n"
            )
        
        return "\n".join(context_parts)
    
    def _build_prompt(self, question: str, context: str) -> str:
        """Build prompt with financial domain expertise."""
        return f"""You are an expert financial analyst and investment advisor with deep knowledge of:
- Technical Analysis: Chart patterns, indicators (RSI, MACD, Bollinger Bands, Moving Averages)
- Fundamental Analysis: Financial statements, valuation metrics (P/E, P/B, DCF, EV/EBITDA)
- Options Trading: Greeks (Delta, Gamma, Theta, Vega), strategies, implied volatility
- Market Microstructure: Order types, bid-ask spreads, market makers, liquidity
- Risk Management: Portfolio theory, diversification, hedging strategies, position sizing
- Economic Indicators: GDP, inflation, interest rates, Federal Reserve policy
- Trading Strategies: Momentum, mean reversion, pairs trading, statistical arbitrage

Context from research documents:
{context}

Question: {question}

Answer:"""


# Singleton engine
_query_engine = None


def get_query_engine() -> RAGQueryEngine:
    """Get or create the query engine singleton."""
    global _query_engine
    if _query_engine is None:
        _query_engine = RAGQueryEngine()
    return _query_engine
