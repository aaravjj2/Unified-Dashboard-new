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
    app.state.http_client = httpx.AsyncClient(timeout=60.0)
    
    # Load LLM - prefer Ollama for GPU acceleration
    app.state.llm_available = False
    app.state.llm = None
    app.state.llm_backend = None
    
    # Try Ollama first (GPU-accelerated)
    ollama_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    try:
        test_response = await app.state.http_client.get(f"{ollama_url}/api/tags", timeout=5.0)
        if test_response.status_code == 200:
            models = test_response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            
            # Check for Mistral model
            if any("mistral" in m.lower() for m in model_names):
                app.state.llm_backend = "ollama"
                app.state.llm_available = True
                app.state.ollama_model = next(m for m in model_names if "mistral" in m.lower())
                app.state.ollama_url = ollama_url
                logger.info(f"✅ Ollama backend ready with GPU acceleration - Model: {app.state.ollama_model}")
            else:
                logger.warning("Ollama available but no Mistral model found. Falling back...")
    except Exception as e:
        logger.warning(f"Ollama not available: {e}. Trying GPT4All fallback...")
    
    # Fallback to GPT4All if Ollama not available
    if not app.state.llm_available:
        try:
            from gpt4all import GPT4All
            logger.info("📦 Loading Mistral-7B-Instruct model via GPT4All...")
            
            model_path = os.getenv("GPT4ALL_MODEL_PATH", os.path.join(os.path.expanduser("~"), "Unified-Dashboard", "models"))
            model_file = os.getenv("GPT4ALL_MODEL", "mistral-7b-instruct-v0.2.Q4_K_M.gguf")
            model_full_path = os.path.join(model_path, model_file)
            
            if os.path.exists(model_full_path):
                logger.info(f"Model file found at {model_full_path}")
            
            # Try CPU with optimized settings
            app.state.llm = GPT4All(
                model_name=model_file,
                model_path=model_path,
                device='cpu',
                n_threads=8,
                n_ctx=2048
            )
            app.state.llm_available = True
            app.state.llm_backend = "gpt4all"
            logger.info("✅ GPT4All backend ready (CPU)")
        
        except Exception as e:
            logger.error(f"Failed to load GPT4All model: {e}")
    
    if not app.state.llm_available:
        logger.warning("⚠️ No LLM backend available. Using rule-based chatbot.")
    
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


async def fetch_watchlist(http_client: httpx.AsyncClient) -> List[Dict]:
    """Fetch watchlist data"""
    try:
        watchlist_path = os.path.join(os.path.dirname(__file__), "..", "data", "watchlist.json")
        if os.path.exists(watchlist_path):
            with open(watchlist_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load watchlist: {e}")
    return []


async def fetch_weekly_picks(http_client: httpx.AsyncClient) -> List[Dict]:
    """Fetch current weekly stock picks"""
    try:
        picks_dir = os.path.join(os.path.dirname(__file__), "..", "data", "picks")
        if os.path.exists(picks_dir):
            files = sorted([f for f in os.listdir(picks_dir) if f.startswith("weekly_picks")])
            if files:
                with open(os.path.join(picks_dir, files[-1]), 'r') as f:
                    return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load weekly picks: {e}")
    return []


async def fetch_volatility_data(symbol: str, http_client: httpx.AsyncClient) -> Optional[Dict]:
    """Fetch volatility metrics for a symbol"""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1mo")
        
        if not hist.empty:
            # Calculate volatility metrics
            returns = hist['Close'].pct_change().dropna()
            volatility = returns.std() * (252 ** 0.5) * 100  # Annualized
            avg_volume = hist['Volume'].mean()
            
            return {
                'symbol': symbol,
                'volatility': round(volatility, 2),
                'avg_volume': int(avg_volume),
                'price_range': {
                    'high': round(hist['High'].max(), 2),
                    'low': round(hist['Low'].min(), 2)
                }
            }
    except Exception as e:
        logger.warning(f"Failed to fetch volatility for {symbol}: {e}")
    return None


async def fetch_strategy_backtest_summary(http_client: httpx.AsyncClient) -> Optional[Dict]:
    """Fetch recent strategy backtest results"""
    try:
        cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", "cache", "strategy_lab")
        if os.path.exists(cache_dir):
            results = []
            for f in os.listdir(cache_dir):
                if f.endswith(".json") and "backtest" in f.lower():
                    with open(os.path.join(cache_dir, f), 'r') as file:
                        results.append(json.load(file))
            if results:
                return {"recent_backtests": len(results), "available": True}
    except Exception as e:
        logger.warning(f"Failed to fetch backtest summary: {e}")
    return None


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
    
    # 4. Generate - use appropriate backend
    try:
        response_text = ""
        
        # Check if using Ollama backend (GPU-accelerated)
        if hasattr(llm, '__class__') and llm is None:
            # This means we're using Ollama backend (passed as None, use http_client)
            pass  # Will be handled below
        elif llm is not None:
            # GPT4All backend
            response_text = llm.generate(
                full_prompt,
                max_tokens=256,  # Reduced for faster response
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


async def process_query_ollama(query: str, ollama_url: str, model: str, http_client: httpx.AsyncClient) -> ChatResponse:
    """Process query using Ollama (GPU-accelerated)"""
    sources = []
    context_parts = []
    
    # 1. Extract symbols and fetch market data
    words = query.upper().replace('?', '').replace('.', '').replace(',', '').split()
    exclude_words = {"WHAT", "WHEN", "WHERE", "PRICE", "COST", "ABOUT", "TELL", "SHOW", 
                     "GIVE", "FIND", "HELP", "PLEASE", "THANK", "THANKS", "THE", "AND", 
                     "FOR", "WITH", "FROM", "THAT", "THIS", "HAVE", "DOES", "MEAN", "LIKE",
                     "KNOW", "MUCH", "MORE", "SOME", "MAKE", "GOOD", "BEST", "NEED", "WILL",
                     "WOULD", "COULD", "SHOULD", "THERE", "THEIR", "THEY", "THEM", "THEN",
                     "PORTFOLIO", "POSITION", "HOLDING", "ACCOUNT", "MONEY", "CASH",
                     "VOLATILITY", "STRATEGY", "PICKS", "WATCHLIST", "BACKTEST"}
    symbols = [w for w in words if len(w) <= 5 and w.isalpha() and w not in exclude_words]
    
    for symbol in symbols[:3]:
        price_data = await fetch_stock_price(symbol, http_client)
        if price_data:
            change_str = f"{price_data.get('change', 0):+.2f} ({price_data.get('change_percent', 0):+.2f}%)"
            context_parts.append(f"Market Data for {symbol}:\n- Price: ${price_data.get('price', 'N/A')}\n- Change: {change_str}\n- Source: {price_data.get('source', 'Unknown')}")
            sources.append(f"Quote ({symbol})")
        
        # Fetch volatility data if volatility-related query
        if any(k in query.upper() for k in ["VOLATILITY", "VOL", "IV", "VOLATILE"]):
            vol_data = await fetch_volatility_data(symbol, http_client)
            if vol_data:
                context_parts.append(f"Volatility Data for {symbol}:\n- Annualized Volatility: {vol_data['volatility']}%\n- Avg Volume: {vol_data['avg_volume']:,}\n- 30-Day Range: ${vol_data['price_range']['low']} - ${vol_data['price_range']['high']}")
                sources.append(f"Volatility ({symbol})")
            
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
    
    # 3. Check for picks/recommendations keywords
    if any(k in query.upper() for k in ["PICKS", "RECOMMEND", "SUGGESTION", "WHAT TO BUY", "TOP STOCKS"]):
        picks = await fetch_weekly_picks(http_client)
        if picks:
            picks_str = "Weekly Stock Picks:\n"
            for p in picks[:5]:  # Top 5 picks
                picks_str += f"- {p.get('symbol', 'N/A')}: {p.get('reason', 'AI recommended')}\n"
            context_parts.append(picks_str)
            sources.append("Weekly Picks")
    
    # 4. Check for watchlist keywords
    if any(k in query.upper() for k in ["WATCHLIST", "WATCHING", "TRACKED"]):
        watchlist = await fetch_watchlist(http_client)
        if watchlist:
            watch_str = "Watchlist Stocks: " + ", ".join([w.get('symbol', '') for w in watchlist[:10]])
            context_parts.append(watch_str)
            sources.append("Watchlist")
    
    # 5. Check for strategy/backtest keywords
    if any(k in query.upper() for k in ["STRATEGY", "BACKTEST", "MOMENTUM", "MEAN REVERSION"]):
        backtest_info = await fetch_strategy_backtest_summary(http_client)
        if backtest_info:
            context_parts.append(f"Strategy Lab: {backtest_info.get('recent_backtests', 0)} recent backtests available.")
            sources.append("Strategy Lab")

    # 6. Construct Prompt
    current_date = datetime.now().strftime("%B %d, %Y")
    context_str = "\n\n".join(context_parts)
    
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
- Keep responses under 150 words for speed."""

    if context_str:
        full_prompt = f"{system_prompt}\n\nCONTEXT DATA:\n{context_str}\n\nUSER QUESTION: {query}"
    else:
        full_prompt = f"{system_prompt}\n\nUSER QUESTION: {query}"
    
    # 4. Generate via Ollama API
    try:
        payload = {
            "model": model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "num_predict": 200,  # Limit tokens for speed
                "temperature": 0.7,
                "top_k": 40,
                "top_p": 0.9
            }
        }
        
        response = await http_client.post(
            f"{ollama_url}/api/generate",
            json=payload,
            timeout=30.0
        )
        
        if response.status_code == 200:
            data = response.json()
            response_text = data.get("response", "").strip()
            
            # Log performance metrics
            eval_duration = data.get("eval_duration", 0) / 1e9
            eval_count = data.get("eval_count", 0)
            logger.info(f"Ollama response: {eval_count} tokens in {eval_duration:.2f}s")
            
            return ChatResponse(
                response=response_text,
                timestamp=datetime.now().isoformat(),
                sources=sources
            )
        else:
            logger.error(f"Ollama API error: {response.status_code}")
            return await process_query_rule_based(query, http_client)
            
    except Exception as e:
        logger.error(f"Ollama generation failed: {e}")
        return await process_query_rule_based(query, http_client)


async def process_query_rule_based(query: str, http_client: httpx.AsyncClient) -> ChatResponse:
    """Smart rule-based processing with market data and intelligent responses"""
    sources = []
    query_upper = query.upper()
    
    # Extract potential stock symbols
    words = query_upper.replace('?', '').replace('.', '').replace(',', '').split()
    exclude_words = {"WHAT", "WHEN", "WHERE", "PRICE", "COST", "ABOUT", "TELL", "SHOW", 
                     "GIVE", "FIND", "HELP", "PLEASE", "THANK", "THANKS", "THE", "AND", 
                     "FOR", "WITH", "FROM", "THAT", "THIS", "HAVE", "DOES", "MEAN", "LIKE",
                     "KNOW", "MUCH", "MORE", "SOME", "MAKE", "GOOD", "BEST", "NEED", "WILL",
                     "WOULD", "COULD", "SHOULD", "THERE", "THEIR", "THEY", "THEM", "THEN",
                     "PORTFOLIO", "POSITION", "HOLDING", "ACCOUNT", "MONEY", "CASH", "HOW",
                     "CAN", "YOU", "STOCK", "STOCKS", "MARKET", "TODAY", "NOW", "BUY", "SELL"}
    symbols = [w for w in words if len(w) <= 5 and w.isalpha() and w not in exclude_words]
    
    # 1. Stock price queries
    if symbols:
        symbol = symbols[0]
        price_data = await fetch_stock_price(symbol, http_client)
        if price_data:
            price = price_data.get('price', 0)
            change = price_data.get('change', 0)
            change_pct = price_data.get('change_percent', 0)
            direction = "📈 up" if change >= 0 else "📉 down"
            
            response = f"**{symbol}** is currently trading at **${price:.2f}**\n\n"
            response += f"• Change: {change:+.2f} ({change_pct:+.2f}%) - {direction} today\n"
            
            if price_data.get('high') and price_data.get('low'):
                response += f"• Day Range: ${price_data.get('low'):.2f} - ${price_data.get('high'):.2f}\n"
            
            # Add simple analysis
            if change_pct > 3:
                response += "\n💡 *Strong bullish momentum today.*"
            elif change_pct < -3:
                response += "\n⚠️ *Significant selling pressure today.*"
            elif abs(change_pct) < 0.5:
                response += "\n📊 *Trading relatively flat today.*"
            
            sources.append(f"Quote ({symbol})")
            return ChatResponse(response=response, timestamp=datetime.now().isoformat(), sources=sources)
    
    # 2. Portfolio queries
    if any(k in query_upper for k in ["PORTFOLIO", "POSITION", "HOLDING", "ACCOUNT", "MY STOCK"]):
        positions = await fetch_alpaca_positions(http_client)
        if positions:
            total_value = sum(float(p.get('market_value', 0)) for p in positions)
            total_pl = sum(float(p.get('unrealized_pl', 0)) for p in positions)
            
            response = f"📊 **Your Portfolio Summary**\n\n"
            response += f"• Total Value: **${total_value:,.2f}**\n"
            response += f"• Unrealized P/L: **${total_pl:+,.2f}**\n"
            response += f"• Positions: **{len(positions)}**\n\n"
            response += "**Holdings:**\n"
            
            for p in positions[:10]:  # Limit to 10
                symbol = p.get('symbol')
                qty = p.get('qty')
                mv = float(p.get('market_value', 0))
                pl_pct = float(p.get('unrealized_plpc', 0)) * 100
                icon = "🟢" if pl_pct >= 0 else "🔴"
                response += f"{icon} **{symbol}**: {qty} shares @ ${mv:,.2f} ({pl_pct:+.2f}%)\n"
            
            sources.append("Alpaca Portfolio")
            return ChatResponse(response=response, timestamp=datetime.now().isoformat(), sources=sources)
        else:
            return ChatResponse(
                response="📭 No open positions found in your portfolio. Start trading to see your holdings here!",
                timestamp=datetime.now().isoformat(),
                sources=["Alpaca Portfolio"]
            )
    
    # 3. Market overview queries
    if any(k in query_upper for k in ["MARKET", "SPY", "QQQ", "DOW", "NASDAQ", "S&P"]):
        indices = []
        for symbol in ["SPY", "QQQ", "DIA"]:
            data = await fetch_stock_price(symbol, http_client)
            if data:
                indices.append(data)
                sources.append(f"Quote ({symbol})")
        
        if indices:
            response = "📈 **Market Overview**\n\n"
            for idx in indices:
                symbol = idx.get('symbol')
                name = {"SPY": "S&P 500", "QQQ": "Nasdaq 100", "DIA": "Dow Jones"}.get(symbol, symbol)
                price = idx.get('price', 0)
                change_pct = idx.get('change_percent', 0)
                icon = "🟢" if change_pct >= 0 else "🔴"
                response += f"{icon} **{name}** ({symbol}): ${price:.2f} ({change_pct:+.2f}%)\n"
            
            return ChatResponse(response=response, timestamp=datetime.now().isoformat(), sources=sources)
    
    # 4. Options-related queries
    if any(k in query_upper for k in ["OPTION", "CALL", "PUT", "STRIKE", "EXPIR", "GREEK", "DELTA", "GAMMA", "THETA", "VEGA", "IV"]):
        if "DELTA" in query_upper:
            response = "📚 **Delta (Δ)**\n\n"
            response += "Delta measures how much an option's price changes for a $1 move in the underlying.\n\n"
            response += "• **Call Options**: Delta ranges from 0 to 1\n"
            response += "• **Put Options**: Delta ranges from -1 to 0\n"
            response += "• **ATM Options**: Delta ≈ 0.50 (calls) or -0.50 (puts)\n\n"
            response += "💡 *Delta also approximates the probability of expiring ITM.*"
        elif "GAMMA" in query_upper:
            response = "📚 **Gamma (Γ)**\n\n"
            response += "Gamma measures the rate of change in Delta for a $1 move in the underlying.\n\n"
            response += "• Highest for ATM options near expiration\n"
            response += "• Indicates how quickly Delta will change\n"
            response += "• High gamma = higher risk but higher reward potential"
        elif "THETA" in query_upper:
            response = "📚 **Theta (Θ)**\n\n"
            response += "Theta measures time decay - how much value an option loses per day.\n\n"
            response += "• Always negative for long options\n"
            response += "• Accelerates as expiration approaches\n"
            response += "• Theta works in favor of option sellers"
        elif "VEGA" in query_upper:
            response = "📚 **Vega (ν)**\n\n"
            response += "Vega measures sensitivity to implied volatility changes.\n\n"
            response += "• Higher IV = higher option premiums\n"
            response += "• Long options benefit from rising IV\n"
            response += "• Short options benefit from falling IV"
        elif "IV" in query_upper or "IMPLIED" in query_upper:
            response = "📚 **Implied Volatility (IV)**\n\n"
            response += "IV represents the market's expectation of future price movement.\n\n"
            response += "• High IV = expensive options\n"
            response += "• Low IV = cheap options\n"
            response += "• IV Rank compares current IV to historical range\n\n"
            response += "💡 *Check the Options Lab for IV Surface analysis!*"
        else:
            response = "📚 **Options Basics**\n\n"
            response += "Options give the right (not obligation) to buy/sell at a set price.\n\n"
            response += "• **Call**: Right to BUY at strike price\n"
            response += "• **Put**: Right to SELL at strike price\n"
            response += "• **Greeks**: Delta, Gamma, Theta, Vega, Rho\n\n"
            response += "💡 *Ask me about specific Greeks for detailed explanations!*"
        
        sources.append("Options Education")
        return ChatResponse(response=response, timestamp=datetime.now().isoformat(), sources=sources)
    
    # 5. Help / capabilities
    if any(k in query_upper for k in ["HELP", "WHAT CAN", "CAPABILITIES", "FEATURES"]):
        response = "🤖 **I can help you with:**\n\n"
        response += "📈 **Stock Prices** - Ask \"What's AAPL price?\" or \"How is NVDA doing?\"\n\n"
        response += "💼 **Portfolio** - \"Show my portfolio\" or \"What are my positions?\"\n\n"
        response += "📊 **Market Overview** - \"How's the market?\" or \"Show SPY\"\n\n"
        response += "📚 **Options Education** - \"Explain Delta\" or \"What is Theta?\"\n\n"
        response += "💡 **Tips** - Just type a stock symbol like \"TSLA\" for quick quotes!"
        
        sources.append("Help")
        return ChatResponse(response=response, timestamp=datetime.now().isoformat(), sources=sources)
    
    # 6. Greeting
    if any(k in query_upper for k in ["HELLO", "HI", "HEY", "GOOD MORNING", "GOOD AFTERNOON"]):
        response = "👋 Hello! I'm your AI Financial Assistant.\n\n"
        response += "I can help you with stock prices, portfolio analysis, and options education.\n\n"
        response += "Try asking:\n• \"What's AAPL's price?\"\n• \"Show my portfolio\"\n• \"Explain Delta\""
        
        return ChatResponse(response=response, timestamp=datetime.now().isoformat(), sources=["Greeting"])
    
    # 7. Default response
    response = "I can help you with:\n\n"
    response += "• **Stock prices** - Try \"AAPL price\" or just type \"NVDA\"\n"
    response += "• **Portfolio** - Try \"Show my portfolio\"\n"
    response += "• **Market** - Try \"How's the market?\"\n"
    response += "• **Options** - Try \"Explain Delta\" or \"What is IV?\"\n\n"
    response += "💡 *Type 'help' for more options!*"
    
    return ChatResponse(response=response, timestamp=datetime.now().isoformat(), sources=["Help"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    llm_available = getattr(app.state, 'llm_available', False)
    llm_backend = getattr(app.state, 'llm_backend', None)
    
    if llm_backend == "ollama":
        model_name = getattr(app.state, 'ollama_model', 'mistral:7b')
        mode = "Ollama (GPU)"
    elif llm_backend == "gpt4all":
        model_name = "Mistral-7B-Instruct (GPT4All)"
        mode = "GPT4All (CPU)"
    else:
        model_name = "Smart Rule-Based"
        mode = "Active"
    
    return {
        "status": "healthy",
        "service": "chatbot_service",
        "model": model_name,
        "mode": mode,
        "backend": llm_backend or "rule-based",
        "timestamp": datetime.now().isoformat(),
        "llm_available": llm_available,
        "capabilities": ["stock_quotes", "portfolio", "market_overview", "options_education", "rag"]
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    """Main chat endpoint"""
    try:
        logger.info(f"Received chat request: {request.message[:50]}...")
        
        llm_backend = getattr(req.app.state, 'llm_backend', None)
        
        if llm_backend == "ollama":
            # Use Ollama (GPU-accelerated)
            response = await process_query_ollama(
                request.message,
                req.app.state.ollama_url,
                req.app.state.ollama_model,
                req.app.state.http_client
            )
        elif llm_backend == "gpt4all" and getattr(req.app.state, 'llm', None):
            # Use GPT4All
            response = await process_query_llm(request.message, req.app.state.llm, req.app.state.http_client)
        else:
            # Fallback to rule-based
            response = await process_query_rule_based(request.message, req.app.state.http_client)
            
        return response
        
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8062, log_level="info")
