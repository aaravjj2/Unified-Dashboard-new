"""
FinGPT Forecast Service
========================
Provides AI-powered stock price movement predictions using FinGPT-style prompts.
Uses Groq API (fast) with fallback to local analysis.

Based on: FinGPT-Forecaster (https://huggingface.co/FinGPT/fingpt-forecaster_dow30_llama2-7b_lora)
"""

import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger(__name__)

# Groq API settings
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


class ForecastService:
    """AI-powered stock forecast service using FinGPT-style analysis."""
    
    def __init__(self, groq_api_key: Optional[str] = None):
        """Initialize forecast service.
        
        Args:
            groq_api_key: Groq API key (or uses GROQ_API_KEY env var)
        """
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.finnhub_key = os.getenv("FINNHUB_API_KEY")
        
        if not self.groq_api_key:
            logger.warning("No GROQ_API_KEY set - forecasts will use fallback")
    
    async def get_company_profile(self, symbol: str) -> Dict:
        """Fetch company profile from Finnhub."""
        if not self.finnhub_key:
            return {"name": symbol, "industry": "Unknown"}
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://finnhub.io/api/v1/stock/profile2",
                    params={"symbol": symbol, "token": self.finnhub_key},
                    timeout=10.0
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning(f"Failed to fetch profile for {symbol}: {e}")
        
        return {"name": symbol, "industry": "Unknown"}
    
    async def get_recent_news(self, symbol: str, days: int = 7) -> List[Dict]:
        """Fetch recent news from Finnhub."""
        if not self.finnhub_key:
            return []
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://finnhub.io/api/v1/company-news",
                    params={
                        "symbol": symbol,
                        "from": start_date.strftime("%Y-%m-%d"),
                        "to": end_date.strftime("%Y-%m-%d"),
                        "token": self.finnhub_key
                    },
                    timeout=10.0
                )
                if resp.status_code == 200:
                    news = resp.json()
                    # Limit to most recent 10 news items
                    return news[:10]
        except Exception as e:
            logger.warning(f"Failed to fetch news for {symbol}: {e}")
        
        return []
    
    async def get_price_data(self, symbol: str) -> Dict:
        """Fetch recent price data using yfinance."""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1mo")
            
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                prev_week = hist['Close'].iloc[-5] if len(hist) >= 5 else hist['Close'].iloc[0]
                change_pct = ((current - prev_week) / prev_week) * 100
                
                return {
                    "current_price": round(current, 2),
                    "prev_week_price": round(prev_week, 2),
                    "week_change_pct": round(change_pct, 2),
                    "high_52w": round(hist['High'].max(), 2),
                    "low_52w": round(hist['Low'].min(), 2)
                }
        except Exception as e:
            logger.warning(f"Failed to fetch price data for {symbol}: {e}")
        
        return {}
    
    def _build_forecast_prompt(
        self,
        symbol: str,
        profile: Dict,
        news: List[Dict],
        price_data: Dict
    ) -> str:
        """Build FinGPT-style forecast prompt."""
        
        # Company intro
        company_name = profile.get("name", symbol)
        industry = profile.get("finnhubIndustry", profile.get("industry", "Unknown"))
        
        prompt_parts = [
            f"[Company Introduction]:",
            f"{company_name} ({symbol}) operates in the {industry} sector.",
            ""
        ]
        
        # Price context
        if price_data:
            direction = "increased" if price_data.get("week_change_pct", 0) > 0 else "decreased"
            prompt_parts.extend([
                f"[Recent Price Action]:",
                f"Current price: ${price_data.get('current_price', 'N/A')}",
                f"Past week: {direction} by {abs(price_data.get('week_change_pct', 0)):.1f}%",
                ""
            ])
        
        # News context
        if news:
            prompt_parts.append("[Recent News Headlines]:")
            for i, article in enumerate(news[:5], 1):
                headline = article.get("headline", "")[:100]
                prompt_parts.append(f"{i}. {headline}")
            prompt_parts.append("")
        
        # Forecast request
        next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        prompt_parts.extend([
            "[Analysis Request]:",
            f"Based on the information above, analyze {symbol} for the coming week (until {next_week}).",
            "",
            "Provide:",
            "1. **Positive Developments** (2-3 key factors)",
            "2. **Potential Concerns** (2-3 risk factors)",
            "3. **Price Prediction** (up/down/flat with percentage range)",
            "4. **Summary** (1-2 sentences)",
            "",
            "Format your response clearly with these sections."
        ])
        
        return "\n".join(prompt_parts)
    
    async def generate_forecast(self, symbol: str) -> Dict:
        """Generate AI forecast for a stock symbol.
        
        Args:
            symbol: Stock ticker symbol (e.g., AAPL, NVDA)
            
        Returns:
            Dict with forecast analysis
        """
        symbol = symbol.upper().strip()
        
        # Gather context data
        profile = await self.get_company_profile(symbol)
        news = await self.get_recent_news(symbol)
        price_data = await self.get_price_data(symbol)
        
        # Build prompt
        prompt = self._build_forecast_prompt(symbol, profile, news, price_data)
        
        # Check if Groq available
        if not self.groq_api_key:
            return self._fallback_forecast(symbol, price_data, news)
        
        # Call Groq API
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    GROQ_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.groq_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": GROQ_MODEL,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a professional financial analyst providing stock forecasts. Be concise and specific."
                            },
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 500
                    },
                    timeout=30.0
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    analysis = data["choices"][0]["message"]["content"]
                    
                    return {
                        "symbol": symbol,
                        "company": profile.get("name", symbol),
                        "analysis": analysis,
                        "price_data": price_data,
                        "news_count": len(news),
                        "model": GROQ_MODEL,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    logger.error(f"Groq API error: {resp.status_code}")
                    return self._fallback_forecast(symbol, price_data, news)
                    
        except Exception as e:
            logger.error(f"Forecast generation failed: {e}")
            return self._fallback_forecast(symbol, price_data, news)
    
    def _fallback_forecast(
        self,
        symbol: str,
        price_data: Dict,
        news: List[Dict]
    ) -> Dict:
        """Simple rule-based fallback forecast."""
        
        # Analyze price trend
        change = price_data.get("week_change_pct", 0)
        
        if change > 2:
            prediction = "Bullish momentum may continue"
            direction = "UP"
        elif change < -2:
            prediction = "Bearish pressure may persist"
            direction = "DOWN"
        else:
            prediction = "Sideways consolidation expected"
            direction = "FLAT"
        
        # Simple news sentiment
        positive_keywords = ["surge", "beat", "growth", "strong", "upgrade"]
        negative_keywords = ["fall", "miss", "weak", "concern", "downgrade"]
        
        pos_count = sum(
            1 for n in news 
            for kw in positive_keywords 
            if kw in n.get("headline", "").lower()
        )
        neg_count = sum(
            1 for n in news 
            for kw in negative_keywords 
            if kw in n.get("headline", "").lower()
        )
        
        sentiment_note = ""
        if pos_count > neg_count:
            sentiment_note = "News sentiment appears positive."
        elif neg_count > pos_count:
            sentiment_note = "News sentiment appears cautious."
        
        analysis = f"""**Positive Developments:**
- Recent price action shows {abs(change):.1f}% weekly move
- {pos_count} positive news mentions detected

**Potential Concerns:**
- Market volatility remains elevated
- {neg_count} cautionary news mentions

**Price Prediction:** {direction}
{prediction}

**Summary:** {sentiment_note} Based on recent price action, {symbol} may continue its current trend."""
        
        return {
            "symbol": symbol,
            "company": symbol,
            "analysis": analysis,
            "price_data": price_data,
            "news_count": len(news),
            "model": "rule-based-fallback",
            "timestamp": datetime.now().isoformat()
        }


# Module-level instance for easy import
_forecast_service: Optional[ForecastService] = None


def get_forecast_service() -> ForecastService:
    """Get or create forecast service singleton."""
    global _forecast_service
    if _forecast_service is None:
        _forecast_service = ForecastService()
    return _forecast_service


async def generate_stock_forecast(symbol: str) -> Dict:
    """Convenience function to generate a stock forecast.
    
    Args:
        symbol: Stock ticker symbol
        
    Returns:
        Dict with forecast analysis
    """
    service = get_forecast_service()
    return await service.generate_forecast(symbol)
