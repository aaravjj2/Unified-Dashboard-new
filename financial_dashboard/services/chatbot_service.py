"""
AI Chatbot Service for Financial Dashboard
Provides conversational AI interface with access to market data and analytics.

Run: python -m uvicorn services.chatbot_service:app --host 0.0.0.0 --port 8062
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

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
    
    # Try to load a lightweight LLM (optional - fallback to rule-based if unavailable)
    app.state.llm_available = False
    try:
        from ctransformers import AutoModelForCausalLM
        # This would load a small model like TinyLlama or similar
        # For now, we'll use rule-based responses
        logger.info("LLM model initialization skipped - using rule-based responses")
    except Exception as e:
        logger.warning(f"LLM not available: {e}. Using rule-based chatbot.")
    
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
    """Fetch stock price from options service"""
    try:
        options_url = os.getenv("OPTIONS_SERVICE_URL", "http://localhost:8060")
        response = await http_client.get(f"{options_url}/quote/{symbol}", timeout=10.0)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"Error fetching stock price: {e}")
    return None


async def fetch_market_trends(http_client: httpx.AsyncClient) -> Optional[Dict]:
    """Fetch market trends from market trends service"""
    try:
        trends_url = os.getenv("MARKET_TRENDS_URL", "http://localhost:8050")
        response = await http_client.get(f"{trends_url}/api/trends/status", timeout=10.0)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"Error fetching market trends: {e}")
    return None


async def process_query_rule_based(query: str, http_client: httpx.AsyncClient) -> ChatResponse:
    """
    Process user query using rule-based logic and API calls.
    This is a lightweight alternative to LLM-based processing.
    """
    query_lower = query.lower()
    sources = []
    
    # Stock price queries
    if any(word in query_lower for word in ["price", "quote", "cost", "worth"]):
        # Extract potential stock symbols (simplified)
        words = query.upper().split()
        symbols = [w for w in words if len(w) <= 5 and w.isalpha()]
        
        if symbols:
            symbol = symbols[0]
            price_data = await fetch_stock_price(symbol, http_client)
            
            if price_data:
                sources.append(f"Options Service - {symbol} quote")
                return ChatResponse(
                    response=f"The current price of {symbol} is ${price_data.get('price', 'N/A')}. "
                             f"The bid is ${price_data.get('bid', 'N/A')} and ask is ${price_data.get('ask', 'N/A')}.",
                    timestamp=datetime.now().isoformat(),
                    sources=sources
                )
            else:
                return ChatResponse(
                    response=f"I couldn't fetch the price for {symbol} at the moment. Please try again later.",
                    timestamp=datetime.now().isoformat(),
                    sources=sources
                )
    
    # Market trends queries
    if any(word in query_lower for word in ["market", "trend", "sector", "performance"]):
        trends_data = await fetch_market_trends(http_client)
        
        if trends_data:
            sources.append("Market Trends Service")
            return ChatResponse(
                response="Based on current market trends, I can help you analyze sector performance and market movements. "
                         "Would you like to see specific sector analysis or overall market trends?",
                timestamp=datetime.now().isoformat(),
                sources=sources
            )
    
    # Portfolio queries
    if any(word in query_lower for word in ["portfolio", "holdings", "positions"]):
        return ChatResponse(
            response="I can help you with portfolio analysis. You can view your current positions, "
                     "performance metrics, and risk analysis in the Portfolio tab. "
                     "Would you like me to summarize your portfolio performance?",
            timestamp=datetime.now().isoformat(),
            sources=["Portfolio Service"]
        )
    
    # Analysis queries
    if any(word in query_lower for word in ["analyze", "analysis", "study", "research"]):
        return ChatResponse(
            response="I can help you with various analyses including:\n"
                     "• Technical Analysis\n"
                     "• Fundamental Analysis\n"
                     "• Sentiment Analysis\n"
                     "• Risk Analysis\n\n"
                     "Which type of analysis are you interested in?",
            timestamp=datetime.now().isoformat(),
            sources=["Analysis Hub Service"]
        )
    
    # Options queries
    if any(word in query_lower for word in ["option", "options", "call", "put", "strike"]):
        return ChatResponse(
            response="I can help you with options trading strategies. "
                     "Our Options Lab provides real-time options chains, strategy analysis, and automated trading. "
                     "What specific options information do you need?",
            timestamp=datetime.now().isoformat(),
            sources=["Options Service"]
        )
    
    # Default response
    return ChatResponse(
        response="I'm your AI financial assistant! I can help you with:\n\n"
                 "📊 Stock prices and quotes\n"
                 "📈 Market trends and sector analysis\n"
                 "💼 Portfolio management and optimization\n"
                 "🔍 Technical and fundamental analysis\n"
                 "📉 Options trading strategies\n\n"
                 "What would you like to know?",
        timestamp=datetime.now().isoformat(),
        sources=[]
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
    """
    Main chat endpoint - processes user queries and returns AI responses
    """
    try:
        logger.info(f"Received chat request: {request.message[:50]}...")
        
        # Store in conversation history
        conversation_history.append({
            "role": "user",
            "message": request.message,
            "timestamp": datetime.now().isoformat(),
            "session_id": request.session_id
        })
        
        # Process query (using rule-based for now)
        response = await process_query_rule_based(request.message, req.app.state.http_client)
        
        # Store response in history
        conversation_history.append({
            "role": "assistant",
            "message": response.response,
            "timestamp": response.timestamp,
            "session_id": request.session_id
        })
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/history")
async def get_chat_history(session_id: str = "default", limit: int = 50):
    """Retrieve conversation history for a session"""
    session_history = [
        msg for msg in conversation_history
        if msg.get("session_id") == session_id
    ]
    return {
        "session_id": session_id,
        "history": session_history[-limit:],
        "count": len(session_history)
    }


@app.delete("/api/chat/history")
async def clear_chat_history(session_id: str = "default"):
    """Clear conversation history for a session"""
    global conversation_history
    conversation_history = [
        msg for msg in conversation_history
        if msg.get("session_id") != session_id
    ]
    return {"status": "success", "message": f"Cleared history for session {session_id}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8062,
        log_level="info"
    )
