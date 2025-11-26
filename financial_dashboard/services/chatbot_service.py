"""
AI Chatbot Service for Financial Dashboard
Provides conversational AI interface with access to market data and analytics.
Uses Mistral-7B-Instruct-v0.2 on GPU for high-quality, local inference.

Run: python -m uvicorn services.chatbot_service:app --host 0.0.0.0 --port 8062
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager
import asyncio
import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'keys.env'))

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
        from gpt4all import GPT4All
        logger.info("📦 Loading Mistral-7B-Instruct model (GPU)...")
        
        # Use local model file
        model_path = "/home/aarav/unified-dashboard/models"
        model_file = "mistral-7b-instruct-v0.2.Q4_K_M.gguf"
        
        # Load model synchronously
        # Using 'cuda' for GPU acceleration if available, otherwise CPU
        app.state.llm = GPT4All(
            model_name=model_file,
            model_path=model_path,
            device='cuda',
            n_threads=8,
            n_ctx=2048
        )
        app.state.llm_available = True
        logger.info("✅ Mistral-7B-Instruct loaded successfully on GPU")
        
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
    version="2.0.0",
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


async def fetch_finnhub_quote(symbol: str, http_client: httpx.AsyncClient) -> Optional[Dict]:
    """Fetch real-time quote from Finnhub"""
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return None
        
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}"
        response = await http_client.get(url, timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            # Finnhub returns c (current), d (change), dp (percent change), h (high), l (low), o (open), pc (prev close)
            if data.get('c', 0) > 0:
                return {
                    'symbol': symbol,
                    'price': data.get('c'),
                    'change': data.get('d'),
                    'change_percent': data.get('dp'),
                    'high': data.get('h'),
                    'low': data.get('l'),
                    'open': data.get('o'),
                    'prev_close': data.get('pc'),
                    'source': 'Finnhub'
                }
    except Exception as e:
        logger.warning(f"Failed to fetch {symbol} from Finnhub: {e}")
    
    return None


async def fetch_alpaca_positions(http_client: httpx.AsyncClient) -> List[Dict]:
    """Fetch open positions from Alpaca"""
    api_key = os.getenv("APCA_API_KEY_ID")
    api_secret = os.getenv("APCA_API_SECRET_KEY")
    base_url = os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")
    
    if not api_key or not api_secret:
        return []
        
    try:
        headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": api_secret
        }
        response = await http_client.get(f"{base_url}/v2/positions", headers=headers, timeout=5.0)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.warning(f"Failed to fetch Alpaca positions: {e}")
        
    return []


async def fetch_stock_price(symbol: str, http_client: httpx.AsyncClient) -> Optional[Dict]:
    """Fetch stock price from Finnhub, then options service, then yfinance fallback"""
    # 1. Try Finnhub first (Primary)
    finnhub_data = await fetch_finnhub_quote(symbol, http_client)
    if finnhub_data:
        return finnhub_data

    # 2. Try options service
    try:
        options_url = os.getenv("OPTIONS_SERVICE_URL", "http://localhost:8060")
        response = await http_client.get(f"{options_url}/quote/{symbol}", timeout=2.0)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    
    # 3. Fallback to yfinance
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
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


async def process_query_llm(query: str, llm, http_client: httpx.AsyncClient) -> ChatResponse:
    """Process query using Mistral LLM with RAG context"""
    sources = []
    context_parts = []
    
    # 1. Extract symbols and fetch market data
    words = query.upper().replace('?', '').replace('.', '').replace(',', '').split()
    exclude_words = {"WHAT", "WHEN", "WHERE", "PRICE", "COST", "ABOUT", "TELL", "SHOW", 
                     "GIVE", "FIND", "HELP", "PLEASE", "THANK", "THANKS", "THE", "AND", 
                     "FOR", "WITH", "FROM", "THAT", "THIS", "HAVE", "DOES", "MEAN", "LIKE",
                     "KNOW", "MUCH", "MORE", "SOME", "MAKE", "GOOD", "BEST", "NEED", "WILL",
                     "WOULD", "COULD", "SHOULD", "THERE", "THEIR", "THEY", "THEM", "THEN",
                     "PORTFOLIO", "POSITION", "HOLDING", "ACCOUNT", "MONEY", "CASH"}
    symbols = [w for w in words if len(w) <= 5 and w.isalpha() and w not in exclude_words]
    
    for symbol in symbols[:3]:
        price_data = await fetch_stock_price(symbol, http_client)
        if price_data:
            change_str = f"{price_data.get('change', 0):+.2f} ({price_data.get('change_percent', 0):+.2f}%)"
            context_parts.append(f"Market Data for {symbol}:\n- Price: ${price_data.get('price', 'N/A')}\n- Change: {change_str}\n- Source: {price_data.get('source', 'Unknown')}")
            sources.append(f"Quote ({symbol})")
            
    # 2. Check for portfolio/position keywords
    if any(k in query.upper() for k in ["PORTFOLIO", "POSITION", "HOLDING", "ACCOUNT"]):
        positions = await fetch_alpaca_positions(http_client)
        if positions:
            pos_str = "Current Portfolio Positions:\n"
            for p in positions:
                symbol = p.get('symbol')
                qty = p.get('qty')
                mv = float(p.get('market_value', 0))
                pl_pct = float(p.get('unrealized_plpc', 0)) * 100
                pos_str += f"- {symbol}: {qty} shares, Value: ${mv:.2f}, P&L: {pl_pct:+.2f}%\n"
            context_parts.append(pos_str)
            sources.append("Alpaca Portfolio")
        else:
            context_parts.append("Portfolio: No open positions found or API unavailable.")

    # 3. Construct Prompt
    current_date = datetime.now().strftime("%B %d, %Y")
    
    system_prompt = f"""You are a professional financial assistant for a trading dashboard.
Current Date: {current_date}

Your Role:
- Analyze market data and provide trading insights.
- Explain financial concepts (Options, Greeks, Technical Analysis).
- Assist with portfolio management.

Guidelines:
- Be concise, accurate, and professional.
- Use the provided Context data to answer questions.
- If context is missing, provide general knowledge but mention you don't have real-time data.
- Format numbers clearly (e.g., $150.25, +1.5%).
"""

    context_str = "\n\n".join(context_parts)
    
    # Mistral Instruction Format: <s>[INST] Instruction [/INST]
    if context_str:
        full_prompt = f"<s>[INST] {system_prompt}\n\nCONTEXT DATA:\n{context_str}\n\nUSER QUESTION:\n{query} [/INST]"
    else:
        full_prompt = f"<s>[INST] {system_prompt}\n\nUSER QUESTION:\n{query} [/INST]"
    
    # 4. Generate
    try:
        # GPT4All generate method
        response_text = llm.generate(
            full_prompt,
            max_tokens=512,
            temp=0.7,
            top_k=40,
            top_p=0.9
        )
        
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
    return ChatResponse(
        response="I'm currently running in fallback mode. Please ensure the AI model is loaded for full capabilities.",
        timestamp=datetime.now().isoformat(),
        sources=["System Fallback"]
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "chatbot_service",
        "model": "Mistral-7B-Instruct-v0.2",
        "timestamp": datetime.now().isoformat(),
        "llm_available": getattr(app.state, 'llm_available', False)
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    """Main chat endpoint"""
    try:
        logger.info(f"Received chat request: {request.message[:50]}...")
        
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
