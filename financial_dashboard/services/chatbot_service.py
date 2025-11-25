"""
AI Chatbot Service for Financial Dashboard
Provides conversational AI interface with access to market data and analytics.
Uses TinyLlama-1.1B on GPU for fast, local inference.

Run: python -m uvicorn services.chatbot_service:app --host 0.0.0.0 --port 8062
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simple in-memory conversation history
conversation_history: List[Dict] = []


class ChatRequest(BaseModel):
    """Chat message request model"""
    message: str
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    """Chat message response model"""
    response: str
    timestamp: str
    sources: Optional[List[str]] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("🤖 Chatbot Service starting up...")
    
    # Initialize HTTP client for internal service calls
    app.state.http_client = httpx.AsyncClient(timeout=30.0)
    
    # Load LLM
    app.state.llm_available = False
    app.state.llm = None
    
    try:
        from ctransformers import AutoModelForCausalLM
        logger.info("📦 Loading TinyLlama-1.1B model (GPU)...")
        
        # Use a separate thread for model loading to not block startup
        def load_model():
            return AutoModelForCausalLM.from_pretrained(
                "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF",
                model_file="tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
                model_type="llama",
                gpu_layers=50,  # Offload to GPU
                context_length=2048
            )
        
        # We'll load it synchronously here for simplicity in this script, 
        # but in prod you might want to do this differently.
        # Since ctransformers downloads the model, this might take a while on first run.
        app.state.llm = load_model()
        app.state.llm_available = True
        logger.info("✅ LLM model loaded successfully on GPU")
        
    except Exception as e:
        logger.warning(f"⚠️ LLM not available: {e}. Using rule-based chatbot.")
        import traceback
        logger.error(traceback.format_exc())
    
    yield
    
    # Cleanup
    await app.state.http_client.aclose()
    logger.info("🤖 Chatbot Service shutting down...")


app = FastAPI(
    title="AI Chatbot Service",
    description="Conversational AI for financial dashboard",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def fetch_stock_price(symbol: str, http_client: httpx.AsyncClient) -> Optional[Dict]:
    """Fetch stock price from options service or yfinance fallback"""
    # Try options service first
    try:
        options_url = os.getenv("OPTIONS_SERVICE_URL", "http://localhost:8060")
        response = await http_client.get(f"{options_url}/quote/{symbol}", timeout=2.0)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    
    # Fallback to yfinance for real-time data
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Get current price
        current_price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
        
        if current_price:
            return {
                'symbol': symbol,
                'price': current_price,
                'change': info.get('regularMarketChange', 0),
                'change_percent': info.get('regularMarketChangePercent', 0),
                'source': 'yfinance'
            }
    except Exception as e:
        logger.warning(f"Failed to fetch {symbol} price from yfinance: {e}")
    
    return None


# Financial terminology glossary for enhanced chatbot context
FINANCIAL_GLOSSARY = {
    # Options & Volatility
    "IV": "Implied Volatility - market's forecast of likely movement in a security's price",
    "IV Rank": "Implied Volatility Rank - where current IV stands relative to its 52-week range",
    "IV Percentile": "percentage of days in past year when IV was lower than current level",
    "Vega": "option Greek measuring sensitivity to volatility changes",
    "Theta": "option Greek measuring time decay",
    "Delta": "option Greek measuring price sensitivity to underlying",
    "Gamma": "option Greek measuring rate of change of Delta",
    "ATM": "At-The-Money - strike price equal to current stock price",
    "ITM": "In-The-Money - option with intrinsic value",
    "OTM": "Out-of-The-Money - option with no intrinsic value",
    "DTE": "Days To Expiration",
    "IV Surface": "3D visualization of implied volatility across strikes and expirations",
    
    # Trading Strategies
    "Iron Condor": "options strategy selling OTM put and call spreads",
    "Straddle": "buying both call and put at same strike",
    "Strangle": "buying OTM call and put",
    "Butterfly": "limited risk strategy using three strikes",
    "Calendar Spread": "buying and selling options with different expirations",
    "Vertical Spread": "buying and selling options with different strikes, same expiration",
    
    # Market Terms
    "Bull Market": "rising market with optimistic sentiment",
    "Bear Market": "declining market, typically 20%+ drop from highs",
    "Volatility": "statistical measure of price dispersion",
    "Liquidity": "ease of buying/selling without affecting price",
    "Bid-Ask Spread": "difference between highest buy and lowest sell price",
    "Market Maker": "firm providing liquidity by quoting buy/sell prices",
    "VIX": "CBOE Volatility Index - market fear gauge",
    
    # Portfolio & Risk
    "Sharpe Ratio": "risk-adjusted return metric",
    "Beta": "measure of volatility relative to market",
    "Alpha": "excess return above benchmark",
    "Drawdown": "peak-to-trough decline",
    "Portfolio Rebalancing": "realigning asset weights to target allocation",
    "Diversification": "spreading investments to reduce risk",
    
    # Technical Analysis
    "Support": "price level where buying interest prevents further decline",
    "Resistance": "price level where selling interest prevents further rise",
    "Moving Average": "average price over specific time period",
    "RSI": "Relative Strength Index - momentum oscillator (0-100)",
    "MACD": "Moving Average Convergence Divergence - trend indicator",
    "Bollinger Bands": "volatility bands around moving average",
    
    # Common Abbreviations
    "P/E": "Price-to-Earnings ratio",
    "EPS": "Earnings Per Share",
    "ROI": "Return On Investment",
    "YTD": "Year-To-Date",
    "QoQ": "Quarter-over-Quarter",
    "YoY": "Year-over-Year",
    "ATH": "All-Time High",
    "ATL": "All-Time Low",
}



async def process_query_llm(query: str, llm, http_client: httpx.AsyncClient) -> ChatResponse:
    """Process query using LLM with RAG context"""
    sources = []
    context_parts = []
    
    # 1. Simple RAG: Extract symbols and fetch data
    words = query.upper().replace('?', '').replace('.', '').replace(',', '').split()
    # Common stock symbols (exclude common English words to avoid false positives)
    exclude_words = {"WHAT", "WHEN", "WHERE", "PRICE", "COST", "ABOUT", "TELL", "SHOW", 
                     "GIVE", "FIND", "HELP", "PLEASE", "THANK", "THANKS", "THE", "AND", 
                     "FOR", "WITH", "FROM", "THAT", "THIS", "HAVE", "DOES", "MEAN", "LIKE",
                     "KNOW", "MUCH", "MORE", "SOME", "MAKE", "GOOD", "BEST", "NEED", "WILL",
                     "WOULD", "COULD", "SHOULD", "THERE", "THEIR", "THEY", "THEM", "THEN"}
    symbols = [w for w in words if len(w) <= 5 and w.isalpha() and w not in exclude_words]
    
    for symbol in symbols[:3]:  # Limit to 3 symbols to avoid overwhelming context
        price_data = await fetch_stock_price(symbol, http_client)
        if price_data:
            context_parts.append(f"Current price of {symbol}: ${price_data.get('price', 'N/A')}")
            sources.append(f"Real-time Quote ({symbol})")
    
    
    # 2. Construct Enhanced Prompt with current date and financial knowledge
    current_date = datetime.now().strftime("%B %d, %Y")  # e.g., "November 24, 2024"
    system_prompt = f"""You are a knowledgeable financial assistant for a professional trading dashboard.

Current date: {current_date}

Your expertise includes:
- Stock market analysis and trading strategies
- Options trading (calls, puts, spreads, Greeks)
- Technical analysis and chart patterns
- Portfolio management and risk assessment
- Market trends and economic indicators

Communication style:
- Be concise and professional
- Use financial terminology appropriately
- Explain complex concepts in simple terms when needed
- Always reference the current date when providing market data
- If you don't have specific data, acknowledge it and provide general guidance

Available dashboard features you can reference:
- Market data and real-time quotes
- Options analysis in Volatility Lab (IV Surface, Signals, Backtesting)
- Market forecasts and predictions
- Portfolio tracking and performance analytics"""
    
    context_str = "\n\n".join(context_parts)
    if context_str:
        prompt = f"<|system|>\n{system_prompt}\n\nContext:\n{context_str}<|end|>\n<|user|>\n{query}<|end|>\n<|assistant|>"
    else:
        prompt = f"<|system|>\n{system_prompt}<|end|>\n<|user|>\n{query}<|end|>\n<|assistant|>"
    
    # 3. Generate
    try:
        response_text = llm(prompt, max_new_tokens=256, temperature=0.7)
        return ChatResponse(
            response=response_text.strip(),
            timestamp=datetime.now().isoformat(),
            sources=sources
        )
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        return await process_query_rule_based(query, http_client)


async def process_query_rule_based(query: str, http_client: httpx.AsyncClient) -> ChatResponse:
    """Fallback rule-based processing"""
    query_lower = query.lower()
    
    if "help" in query_lower:
        return ChatResponse(
            response="I can help you with stock prices, market trends, and portfolio analysis. Try asking 'What is the price of AAPL?'",
            timestamp=datetime.now().isoformat(),
            sources=["System"]
        )
        
    return ChatResponse(
        response="I'm running in rule-based mode. I can answer basic questions, but for advanced analysis, please ensure the LLM is loaded.",
        timestamp=datetime.now().isoformat(),
        sources=["Rule-based Fallback"]
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "chatbot_service",
        "timestamp": datetime.now().isoformat(),
        "llm_available": getattr(app.state, 'llm_available', False)
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    """Main chat endpoint"""
    try:
        logger.info(f"Received chat request: {request.message[:50]}...")
        
        # Process
        if getattr(req.app.state, 'llm_available', False):
            response = await process_query_llm(request.message, req.app.state.llm, req.app.state.http_client)
        else:
            response = await process_query_rule_based(request.message, req.app.state.http_client)
            
        return response
        
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8062, log_level="info")
