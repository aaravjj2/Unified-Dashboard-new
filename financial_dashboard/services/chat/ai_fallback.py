"""
AI Chat Fallback - Uses Gemini/OpenAI when local LLM is unavailable

Provides intelligent financial assistant capabilities via cloud APIs
as fallback when gpt4all/local models are not available.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class AIFallbackChat:
    """
    AI Chat fallback using Gemini or OpenAI API
    
    Prioritizes Gemini (free tier), falls back to OpenAI
    """
    
    def __init__(self):
        """Initialize with API keys from environment"""
        from dotenv import load_dotenv
        load_dotenv('keys.env')
        
        self.gemini_key = os.getenv('GEMINI_API_KEY')
        self.openai_key = os.getenv('OpenAI_API_KEY') or os.getenv('OPENAI_API_KEY')
        
        self._gemini_model = None
        self._openai_client = None
        
        self.system_prompt = """You are a helpful AI Financial Assistant for a trading dashboard.
You can help users with:
- Market analysis and trends
- Stock price forecasts and predictions
- Options analysis (IV, Greeks, strategies)
- Portfolio management and optimization
- Trading strategies and backtesting

Be concise but informative. When suggesting actions, format them as:
ACTION: [action_type] | [details]

Current date: {date}"""
        
    def _init_gemini(self) -> bool:
        """Initialize Gemini client"""
        if self._gemini_model is not None:
            return True
            
        if not self.gemini_key:
            return False
            
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_key)
            self._gemini_model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("✅ Gemini AI initialized successfully")
            return True
        except ImportError:
            logger.warning("google-generativeai not installed")
            return False
        except Exception as e:
            logger.warning(f"Gemini init failed: {e}")
            return False
            
    def _init_openai(self) -> bool:
        """Initialize OpenAI client"""
        if self._openai_client is not None:
            return True
            
        if not self.openai_key:
            return False
            
        try:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=self.openai_key)
            logger.info("✅ OpenAI client initialized successfully")
            return True
        except ImportError:
            logger.warning("openai not installed")
            return False
        except Exception as e:
            logger.warning(f"OpenAI init failed: {e}")
            return False
    
    def chat(self, 
             message: str, 
             context: str = None,
             history: List[Dict] = None) -> Dict[str, Any]:
        """
        Send a chat message and get AI response
        
        Args:
            message: User message
            context: Optional context (current tab, data)
            history: Optional conversation history
            
        Returns:
            Dict with response, sources, model info
        """
        # Build context-aware prompt
        system = self.system_prompt.format(date=datetime.now().strftime('%Y-%m-%d'))
        if context:
            system += f"\n\nCurrent context: {context}"
        
        # Try Gemini first (free tier)
        if self._init_gemini():
            try:
                response = self._gemini_chat(message, system, history)
                return response
            except Exception as e:
                logger.warning(f"Gemini chat failed: {e}")
        
        # Fall back to OpenAI
        if self._init_openai():
            try:
                response = self._openai_chat(message, system, history)
                return response
            except Exception as e:
                logger.warning(f"OpenAI chat failed: {e}")
        
        # Ultimate fallback - rule-based
        return self._rule_based_response(message)
    
    def _gemini_chat(self, 
                     message: str, 
                     system: str,
                     history: List[Dict] = None) -> Dict[str, Any]:
        """Chat using Gemini API"""
        # Build chat history for Gemini
        chat = self._gemini_model.start_chat(history=[])
        
        # Send system prompt first
        full_prompt = f"{system}\n\nUser: {message}"
        
        response = chat.send_message(full_prompt)
        
        return {
            'response': response.text,
            'model': 'gemini-1.5-flash',
            'sources': ['Gemini AI'],
            'timestamp': datetime.now().isoformat()
        }
    
    def _openai_chat(self,
                     message: str,
                     system: str,
                     history: List[Dict] = None) -> Dict[str, Any]:
        """Chat using OpenAI API"""
        messages = [
            {"role": "system", "content": system}
        ]
        
        # Add history if provided
        if history:
            for h in history[-5:]:  # Last 5 messages for context
                messages.append({
                    "role": h.get('role', 'user'),
                    "content": h.get('content', '')
                })
        
        messages.append({"role": "user", "content": message})
        
        response = self._openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        
        return {
            'response': response.choices[0].message.content,
            'model': 'gpt-3.5-turbo',
            'sources': ['OpenAI API'],
            'timestamp': datetime.now().isoformat()
        }
    
    def _rule_based_response(self, message: str) -> Dict[str, Any]:
        """Rule-based fallback when no API is available"""
        message_lower = message.lower()
        
        if any(kw in message_lower for kw in ['volatility', 'vol', 'iv']):
            text = """📊 **Volatility Analysis**
            
To analyze volatility, navigate to the **Volatility Lab** tab where you can:
- View 3D IV surfaces
- Analyze term structure
- Check ATM volatility vs realized vol
- Identify volatility skew patterns

Would you like me to show you the Volatility Lab?"""
        
        elif any(kw in message_lower for kw in ['forecast', 'predict', 'price']):
            text = """📈 **Market Forecast**

Navigate to **Market Forecast** tab for AI-powered predictions:
- Ensemble model combining Prophet, ARIMA, LSTM
- FinBERT sentiment analysis from news
- Technical indicators verification
- Confidence scoring

Which stock would you like to analyze?"""
        
        elif any(kw in message_lower for kw in ['portfolio', 'position', 'holding']):
            text = """💼 **Portfolio Analysis**

Check the **Portfolio** tab for:
- Current positions and P&L
- Factor exposure analysis
- Risk metrics (VaR, Beta, Sharpe)
- Monte Carlo simulations

Would you like to see your portfolio summary?"""
        
        elif any(kw in message_lower for kw in ['option', 'greeks', 'strike']):
            text = """💹 **Options Analysis**

The **Options Lab** provides:
- Real-time options chains
- Greeks calculator
- IV surface visualization
- Strategy simulator

Enter a ticker to load options data!"""
        
        elif any(kw in message_lower for kw in ['buy', 'sell', 'trade', 'order']):
            text = """📝 **Paper Trading**

I can help you place paper trades. Please specify:
- **Ticker symbol** (e.g., AAPL)
- **Action** (buy/sell)
- **Quantity** (number of shares)

Example: "Buy 10 shares of AAPL" """
        
        elif any(kw in message_lower for kw in ['help', 'what can']):
            text = """🤖 **AI Financial Assistant**

I can help you with:
• 📊 **Volatility Analysis** - IV surfaces, skew
• 📈 **Market Forecasts** - AI predictions
• 💼 **Portfolio Management** - positions, risk
• 💹 **Options Analysis** - chains, Greeks
• 📝 **Paper Trading** - simulate trades
• 🔍 **Market Trends** - news, sentiment

Just ask me anything!"""
        
        else:
            text = """I'm your AI Financial Assistant. I can help with:

• Market analysis and forecasts
• Portfolio and position tracking
• Options analysis (IV, Greeks)
• Paper trading simulation
• Technical indicators

What would you like to explore?"""
        
        return {
            'response': text,
            'model': 'rule-based',
            'sources': ['System'],
            'timestamp': datetime.now().isoformat()
        }
    
    def is_available(self) -> bool:
        """Check if any AI backend is available"""
        return self._init_gemini() or self._init_openai()
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of available backends"""
        return {
            'gemini_available': bool(self.gemini_key) and self._init_gemini(),
            'openai_available': bool(self.openai_key) and self._init_openai(),
            'rule_based': True  # Always available
        }


# Global singleton
_fallback_chat: Optional[AIFallbackChat] = None


def get_fallback_chat() -> AIFallbackChat:
    """Get or create fallback chat instance"""
    global _fallback_chat
    if _fallback_chat is None:
        _fallback_chat = AIFallbackChat()
    return _fallback_chat
