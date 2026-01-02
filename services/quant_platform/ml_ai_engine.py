"""
ML/AI Engine - Local Model Integration
Uses Ollama and sklearn for predictions, sentiment, and analysis
"""

import os
import json
import logging
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

# ML imports
try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler, MinMaxScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent.parent / "keys.env"
if env_path.exists():
    load_dotenv(env_path)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:7b")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


# ===== OLLAMA LLM ENGINE =====
class OllamaEngine:
    """Local LLM inference using Ollama"""
    
    def __init__(self, host: str = None, model: str = None):
        self.host = host or OLLAMA_HOST
        self.model = model or OLLAMA_MODEL
        
    def is_available(self) -> bool:
        """Check if Ollama server is running"""
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=5)
            return resp.status_code == 200
        except:
            return False
    
    def list_models(self) -> List[str]:
        """List available models"""
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return [m.get("name", "") for m in data.get("models", [])]
        except:
            pass
        return []
    
    def generate(self, prompt: str, system: str = None, 
                 max_tokens: int = 500, temperature: float = 0.7) -> Optional[str]:
        """Generate text completion"""
        try:
            url = f"{self.host}/api/generate"
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature
                }
            }
            if system:
                payload["system"] = system
                
            resp = requests.post(url, json=payload, timeout=120)
            if resp.status_code == 200:
                return resp.json().get("response", "")
        except Exception as e:
            logger.error(f"Ollama generate error: {e}")
        return None
    
    def chat(self, messages: List[Dict], max_tokens: int = 500) -> Optional[str]:
        """Chat completion"""
        try:
            url = f"{self.host}/api/chat"
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {"num_predict": max_tokens}
            }
            resp = requests.post(url, json=payload, timeout=120)
            if resp.status_code == 200:
                return resp.json().get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
        return None


# ===== GROQ API ENGINE (Fallback) =====
class GroqEngine:
    """Groq API for fast LLM inference (fallback)"""
    
    BASE_URL = "https://api.groq.com/openai/v1"
    
    def __init__(self):
        self.api_key = GROQ_API_KEY
        
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def generate(self, prompt: str, model: str = "llama-3.1-8b-instant",
                 max_tokens: int = 500) -> Optional[str]:
        """Generate completion via Groq"""
        if not self.api_key:
            return None
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            }
            resp = requests.post(
                f"{self.BASE_URL}/chat/completions",
                headers=headers, json=payload, timeout=30
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Groq error: {e}")
        return None


# ===== SENTIMENT ANALYZER =====
class SentimentAnalyzer:
    """AI-powered sentiment analysis"""
    
    def __init__(self):
        self.ollama = OllamaEngine()
        self.groq = GroqEngine()
        
    def analyze(self, text: str, use_local: bool = True) -> Dict[str, Any]:
        """Analyze sentiment of text"""
        prompt = f"""Analyze the financial sentiment of this text. Return ONLY valid JSON.

Text: "{text[:1000]}"

JSON Response format:
{{"sentiment": "bullish" or "bearish" or "neutral", "score": float from -1 to 1, "confidence": float from 0 to 1, "key_factors": ["factor1", "factor2"], "market_impact": "high" or "medium" or "low"}}"""

        # Try local first
        if use_local and self.ollama.is_available():
            response = self.ollama.generate(prompt, max_tokens=200)
        elif self.groq.is_available():
            response = self.groq.generate(prompt, max_tokens=200)
        else:
            # Fallback to simple keyword analysis
            return self._keyword_sentiment(text)
        
        if response:
            try:
                import re
                json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except:
                pass
        
        return self._keyword_sentiment(text)
    
    def _keyword_sentiment(self, text: str) -> Dict[str, Any]:
        """Fallback keyword-based sentiment"""
        text_lower = text.lower()
        
        bullish = ["buy", "long", "bullish", "moon", "rocket", "gains", 
                   "profit", "growth", "beat", "upgrade", "positive"]
        bearish = ["sell", "short", "bearish", "crash", "dump", "loss",
                   "decline", "miss", "downgrade", "negative", "warning"]
        
        bull_count = sum(1 for w in bullish if w in text_lower)
        bear_count = sum(1 for w in bearish if w in text_lower)
        
        if bull_count > bear_count:
            sentiment = "bullish"
            score = min(bull_count / 5, 1.0)
        elif bear_count > bull_count:
            sentiment = "bearish"
            score = -min(bear_count / 5, 1.0)
        else:
            sentiment = "neutral"
            score = 0.0
            
        return {
            "sentiment": sentiment,
            "score": score,
            "confidence": 0.5,
            "key_factors": [],
            "market_impact": "medium"
        }
    
    def batch_analyze(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Analyze multiple texts"""
        return [self.analyze(text) for text in texts]


# ===== PRICE PREDICTION ENGINE =====
class PricePredictionEngine:
    """ML-based price prediction"""
    
    def __init__(self):
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        self.model = None
        
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create technical features for ML"""
        features = df.copy()
        
        # Price features
        features['returns'] = features['close'].pct_change()
        features['log_returns'] = np.log(features['close'] / features['close'].shift(1))
        
        # Moving averages
        for window in [5, 10, 20, 50, 200]:
            features[f'sma_{window}'] = features['close'].rolling(window).mean()
            features[f'sma_ratio_{window}'] = features['close'] / features[f'sma_{window}']
        
        # Volatility
        features['volatility_5'] = features['returns'].rolling(5).std()
        features['volatility_20'] = features['returns'].rolling(20).std()
        
        # RSI
        delta = features['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        features['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = features['close'].ewm(span=12).mean()
        ema26 = features['close'].ewm(span=26).mean()
        features['macd'] = ema12 - ema26
        features['macd_signal'] = features['macd'].ewm(span=9).mean()
        
        # Bollinger Bands
        features['bb_middle'] = features['close'].rolling(20).mean()
        features['bb_std'] = features['close'].rolling(20).std()
        features['bb_upper'] = features['bb_middle'] + 2 * features['bb_std']
        features['bb_lower'] = features['bb_middle'] - 2 * features['bb_std']
        features['bb_position'] = (features['close'] - features['bb_lower']) / (features['bb_upper'] - features['bb_lower'])
        
        # Volume features
        if 'volume' in features.columns:
            features['volume_sma'] = features['volume'].rolling(20).mean()
            features['volume_ratio'] = features['volume'] / features['volume_sma']
        
        # Momentum
        features['momentum_5'] = features['close'] / features['close'].shift(5) - 1
        features['momentum_20'] = features['close'] / features['close'].shift(20) - 1
        
        return features.dropna()
    
    def train(self, df: pd.DataFrame, target_days: int = 5) -> Dict[str, float]:
        """Train prediction model"""
        if not SKLEARN_AVAILABLE:
            return {"error": "sklearn not available"}
        
        features = self.create_features(df)
        
        # Create target (future return)
        features['target'] = features['close'].shift(-target_days) / features['close'] - 1
        features = features.dropna()
        
        # Select feature columns
        feature_cols = [c for c in features.columns if c not in 
                       ['open', 'high', 'low', 'close', 'volume', 'target', 'date']]
        
        X = features[feature_cols].values
        y = features['target'].values
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, shuffle=False
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        
        return {
            "mse": float(mean_squared_error(y_test, y_pred)),
            "mae": float(mean_absolute_error(y_test, y_pred)),
            "r2": float(r2_score(y_test, y_pred)),
            "feature_count": len(feature_cols),
            "samples": len(features)
        }
    
    def predict(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Predict future price direction"""
        if not SKLEARN_AVAILABLE or self.model is None:
            return {"error": "Model not trained or sklearn not available"}
        
        features = self.create_features(df)
        
        feature_cols = [c for c in features.columns if c not in 
                       ['open', 'high', 'low', 'close', 'volume', 'target', 'date']]
        
        X = features[feature_cols].iloc[-1:].values
        X_scaled = self.scaler.transform(X)
        
        prediction = self.model.predict(X_scaled)[0]
        
        return {
            "predicted_return": float(prediction),
            "direction": "UP" if prediction > 0 else "DOWN",
            "confidence": min(abs(prediction) * 10, 0.95),
            "current_price": float(df['close'].iloc[-1]),
            "predicted_price": float(df['close'].iloc[-1] * (1 + prediction))
        }


# ===== MARKET REGIME DETECTOR =====
class MarketRegimeDetector:
    """Detect current market regime"""
    
    REGIMES = {
        "BULL_TRENDING": "Strong uptrend with momentum",
        "BEAR_TRENDING": "Strong downtrend with momentum",
        "BULL_VOLATILE": "Upward bias with high volatility",
        "BEAR_VOLATILE": "Downward bias with high volatility",
        "RANGING": "Sideways consolidation",
        "BREAKOUT": "Breaking out of range",
        "BREAKDOWN": "Breaking down from range"
    }
    
    def detect(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect current market regime"""
        if len(df) < 50:
            return {"regime": "UNKNOWN", "confidence": 0}
        
        # Calculate indicators
        close = df['close']
        
        # Trend indicators
        sma20 = close.rolling(20).mean()
        sma50 = close.rolling(50).mean()
        
        # Volatility
        returns = close.pct_change()
        volatility = returns.rolling(20).std().iloc[-1]
        avg_volatility = returns.rolling(100).std().mean()
        
        # Recent performance
        return_5d = (close.iloc[-1] / close.iloc[-5] - 1) if len(close) >= 5 else 0
        return_20d = (close.iloc[-1] / close.iloc[-20] - 1) if len(close) >= 20 else 0
        
        # Current position
        current = close.iloc[-1]
        sma20_current = sma20.iloc[-1]
        sma50_current = sma50.iloc[-1]
        
        # Determine regime
        high_vol = volatility > avg_volatility * 1.5
        bullish = current > sma20_current > sma50_current
        bearish = current < sma20_current < sma50_current
        
        if bullish and not high_vol:
            regime = "BULL_TRENDING"
            confidence = 0.8
        elif bearish and not high_vol:
            regime = "BEAR_TRENDING"
            confidence = 0.8
        elif bullish and high_vol:
            regime = "BULL_VOLATILE"
            confidence = 0.6
        elif bearish and high_vol:
            regime = "BEAR_VOLATILE"
            confidence = 0.6
        elif return_5d > 0.03 and return_20d < 0.02:
            regime = "BREAKOUT"
            confidence = 0.7
        elif return_5d < -0.03 and return_20d > -0.02:
            regime = "BREAKDOWN"
            confidence = 0.7
        else:
            regime = "RANGING"
            confidence = 0.5
            
        return {
            "regime": regime,
            "description": self.REGIMES.get(regime, ""),
            "confidence": confidence,
            "metrics": {
                "volatility": float(volatility),
                "return_5d": float(return_5d),
                "return_20d": float(return_20d),
                "price_vs_sma20": float(current / sma20_current - 1),
                "sma20_vs_sma50": float(sma20_current / sma50_current - 1)
            }
        }


# ===== AI MARKET ANALYST =====
class AIMarketAnalyst:
    """AI-powered market analysis"""
    
    def __init__(self):
        self.ollama = OllamaEngine()
        self.groq = GroqEngine()
        self.sentiment = SentimentAnalyzer()
        self.regime = MarketRegimeDetector()
        
    def analyze_stock(self, symbol: str, price_data: pd.DataFrame,
                      news: List[str] = None) -> Dict[str, Any]:
        """Comprehensive AI analysis of a stock"""
        
        # Detect regime
        regime_info = self.regime.detect(price_data)
        
        # Analyze news sentiment
        news_sentiment = None
        if news:
            sentiments = self.sentiment.batch_analyze(news[:5])
            avg_score = np.mean([s.get('score', 0) for s in sentiments])
            news_sentiment = {
                "average_score": float(avg_score),
                "overall": "bullish" if avg_score > 0.2 else "bearish" if avg_score < -0.2 else "neutral",
                "article_count": len(news)
            }
        
        # Generate AI summary
        prompt = f"""As a financial analyst, provide a brief market analysis for {symbol}.

Current Market Regime: {regime_info['regime']} - {regime_info['description']}
Recent 5-day return: {regime_info['metrics']['return_5d']:.2%}
Recent 20-day return: {regime_info['metrics']['return_20d']:.2%}
Volatility level: {regime_info['metrics']['volatility']:.4f}
{"News sentiment: " + news_sentiment['overall'] if news_sentiment else ""}

Provide:
1. Short-term outlook (1-5 days)
2. Key support/resistance levels to watch
3. Risk assessment
4. Trading recommendation (buy/sell/hold)

Keep response under 200 words."""

        ai_analysis = None
        if self.ollama.is_available():
            ai_analysis = self.ollama.generate(prompt, max_tokens=300)
        elif self.groq.is_available():
            ai_analysis = self.groq.generate(prompt, max_tokens=300)
        
        return {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "regime": regime_info,
            "sentiment": news_sentiment,
            "ai_analysis": ai_analysis,
            "price_metrics": {
                "current": float(price_data['close'].iloc[-1]),
                "high_52w": float(price_data['close'].tail(252).max()) if len(price_data) >= 252 else None,
                "low_52w": float(price_data['close'].tail(252).min()) if len(price_data) >= 252 else None,
            }
        }
    
    def generate_trade_signals(self, symbol: str, price_data: pd.DataFrame) -> Dict[str, Any]:
        """Generate AI-powered trade signals"""
        
        # Calculate basic signals
        close = price_data['close']
        
        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        
        # MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd = (ema12 - ema26).iloc[-1]
        signal_line = (ema12 - ema26).ewm(span=9).mean().iloc[-1]
        
        # Moving average crossover
        sma20 = close.rolling(20).mean().iloc[-1]
        sma50 = close.rolling(50).mean().iloc[-1]
        
        # Generate signals
        signals = []
        
        # RSI signals
        if rsi < 30:
            signals.append({"signal": "BUY", "indicator": "RSI", "reason": f"RSI oversold at {rsi:.1f}", "strength": "strong"})
        elif rsi > 70:
            signals.append({"signal": "SELL", "indicator": "RSI", "reason": f"RSI overbought at {rsi:.1f}", "strength": "strong"})
        
        # MACD signals
        if macd > signal_line and macd > 0:
            signals.append({"signal": "BUY", "indicator": "MACD", "reason": "MACD bullish crossover", "strength": "medium"})
        elif macd < signal_line and macd < 0:
            signals.append({"signal": "SELL", "indicator": "MACD", "reason": "MACD bearish crossover", "strength": "medium"})
        
        # MA signals
        if sma20 > sma50:
            signals.append({"signal": "BUY", "indicator": "MA", "reason": "Golden cross (20 > 50 SMA)", "strength": "strong"})
        else:
            signals.append({"signal": "SELL", "indicator": "MA", "reason": "Death cross (20 < 50 SMA)", "strength": "strong"})
        
        # Overall signal
        buy_signals = len([s for s in signals if s['signal'] == 'BUY'])
        sell_signals = len([s for s in signals if s['signal'] == 'SELL'])
        
        if buy_signals > sell_signals:
            overall = "BUY"
            confidence = buy_signals / len(signals)
        elif sell_signals > buy_signals:
            overall = "SELL"
            confidence = sell_signals / len(signals)
        else:
            overall = "HOLD"
            confidence = 0.5
        
        return {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "overall_signal": overall,
            "confidence": confidence,
            "signals": signals,
            "indicators": {
                "rsi": float(rsi),
                "macd": float(macd),
                "macd_signal": float(signal_line),
                "sma20": float(sma20),
                "sma50": float(sma50)
            }
        }


# ===== UNIFIED ML ENGINE =====
class UnifiedMLEngine:
    """Unified ML/AI engine for all predictions"""
    
    def __init__(self):
        self.ollama = OllamaEngine()
        self.groq = GroqEngine()
        self.sentiment = SentimentAnalyzer()
        self.predictor = PricePredictionEngine()
        self.regime = MarketRegimeDetector()
        self.analyst = AIMarketAnalyst()
        
    def status(self) -> Dict[str, Any]:
        """Get ML engine status"""
        return {
            "ollama_available": self.ollama.is_available(),
            "ollama_model": OLLAMA_MODEL,
            "groq_available": self.groq.is_available(),
            "sklearn_available": SKLEARN_AVAILABLE,
            "available_models": self.ollama.list_models() if self.ollama.is_available() else []
        }


# Export singleton
ml_engine = UnifiedMLEngine()

if __name__ == "__main__":
    print("=" * 60)
    print("ML/AI ENGINE STATUS")
    print("=" * 60)
    
    status = ml_engine.status()
    for key, value in status.items():
        print(f"{key}: {value}")
    
    # Test sentiment
    print("\n" + "=" * 60)
    print("TESTING SENTIMENT ANALYSIS")
    print("=" * 60)
    
    test_text = "Apple stock surges on strong iPhone sales, beating expectations"
    result = ml_engine.sentiment.analyze(test_text)
    print(f"Text: {test_text}")
    print(f"Result: {result}")
    
    print("=" * 60)
