"""
Options Service
===============
FastAPI microservice for options trading operations.

Endpoints:
- GET /health: Service health check
- GET /options/chain/{symbol}: Get options chain for a symbol
- POST /options/scan: Scan for options opportunities
- GET /options/strategies: List available strategies
- POST /options/backtest: Run backtest on a strategy

Usage:
    uvicorn services.options_service:app --host 0.0.0.0 --port 8060
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.finnhub_client import FinnhubClient
from utils.logging_config import setup_logging, log_api_request, log_error_with_context
from strategies.covered_call_screener import CoveredCallScreener
from backtester import Backtester
from trading.base_broker import BaseBroker
from utils.alpaca_trader import AlpacaTrader

# Initialize logging
logger = setup_logging("options_service", log_level="INFO")

# Initialize broker (using Alpaca as default implementation)
# This can be swapped for other brokers implementing BaseBroker interface
broker: Optional[BaseBroker] = None
try:
    broker = AlpacaTrader(paper_mode=True)
    logger.info("Broker initialized successfully")
except Exception as e:
    logger.warning(f"Broker initialization failed: {e}. Some endpoints may be unavailable.")

# Initialize FastAPI app
app = FastAPI(
    title="Options Service",
    description="Microservice for options trading and analysis",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class OptionsChainRequest(BaseModel):
    symbol: str
    expiration_date: Optional[str] = None

class ScanRequest(BaseModel):
    symbols: List[str]
    strategy: str = "covered_call"
    parameters: Optional[Dict[str, Any]] = None

class BacktestRequest(BaseModel):
    strategy: str
    start_date: str
    end_date: str
    tickers: List[str]
    initial_capital: float = 100000.0
    parameters: Optional[Dict[str, Any]] = None


# Health check
@app.get("/health")
async def health_check():
    """Service health check."""
    return {
        "status": "healthy",
        "service": "options_service",
        "timestamp": datetime.now().isoformat()
    }


# Get options chain
@app.get("/options/chain/{symbol}")
async def get_options_chain(symbol: str, expiration_date: Optional[str] = None):
    """
    Get options chain for a symbol.
    
    Args:
        symbol: Stock ticker symbol
        expiration_date: Optional expiration date (YYYY-MM-DD)
    
    Returns:
        Options chain data
    """
    try:
        import time
        start_time = time.time()
        
        with FinnhubClient() as client:
            chain = client.get_options_chain(symbol, expiration_date)
        
        duration = time.time() - start_time
        log_api_request(logger, "GET", f"/options/chain/{symbol}", 200, duration)
        
        return {
            "symbol": symbol,
            "expiration_date": expiration_date,
            "chain": chain
        }
    
    except Exception as e:
        log_error_with_context(logger, e, {"symbol": symbol, "expiration_date": expiration_date})
        raise HTTPException(status_code=500, detail=str(e))


# Scan for options opportunities
@app.post("/options/scan")
async def scan_opportunities(request: ScanRequest):
    """
    Scan for options trading opportunities.
    
    Args:
        request: Scan request with symbols, strategy, and parameters
    
    Returns:
        List of opportunities found
    """
    try:
        import time
        start_time = time.time()
        
        # Initialize strategy
        if request.strategy == "covered_call":
            strategy = CoveredCallScreener(parameters=request.parameters or {})
        else:
            raise HTTPException(status_code=400, detail=f"Unknown strategy: {request.strategy}")
        
        # Scan each symbol
        all_signals = []
        
        with FinnhubClient() as client:
            for symbol in request.symbols:
                try:
                    # Get current price
                    quote = client.get_quote(symbol)
                    current_price = quote.get('c', 0)
                    
                    if not current_price:
                        continue
                    
                    # Get options chain
                    chain = client.get_options_chain(symbol)
                    
                    # Generate signals
                    data = {
                        'symbol': symbol,
                        'current_price': current_price,
                        'options_chain': chain,
                        'iv_rank': 50  # Default, could be calculated
                    }
                    
                    signals = strategy.generate_signals(data)
                    
                    if signals:
                        all_signals.extend(signals)
                
                except Exception as e:
                    logger.warning(f"Error scanning {symbol}: {e}")
                    continue
        
        duration = time.time() - start_time
        log_api_request(logger, "POST", "/options/scan", 200, duration)
        
        return {
            "strategy": request.strategy,
            "symbols_scanned": len(request.symbols),
            "opportunities_found": len(all_signals),
            "signals": all_signals
        }
    
    except Exception as e:
        log_error_with_context(logger, e, {"strategy": request.strategy, "symbols": request.symbols})
        raise HTTPException(status_code=500, detail=str(e))


# List available strategies
@app.get("/options/strategies")
async def list_strategies():
    """
    List available options strategies.
    
    Returns:
        List of available strategies with descriptions
    """
    strategies = [
        {
            "name": "covered_call",
            "description": "Covered call screener - identifies opportunities to sell calls against long stock positions",
            "parameters": {
                "min_premium_pct": "Minimum premium as % of stock price (default: 1.5)",
                "max_dte": "Maximum days to expiration (default: 45)",
                "target_delta": "Target delta for call options (default: 0.30)",
                "min_volume": "Minimum options volume (default: 100)"
            }
        }
    ]
    
    return {"strategies": strategies}


# Run backtest
@app.post("/options/backtest")
async def run_backtest(request: BacktestRequest):
    """
    Run backtest on an options strategy.
    
    Args:
        request: Backtest request with strategy, dates, tickers, and parameters
    
    Returns:
        Backtest results including P&L, Sharpe ratio, etc.
    """
    try:
        import time
        start_time = time.time()
        
        # Initialize strategy
        if request.strategy == "covered_call":
            strategy = CoveredCallScreener(parameters=request.parameters or {})
        else:
            raise HTTPException(status_code=400, detail=f"Unknown strategy: {request.strategy}")
        
        # Initialize backtester
        backtester = Backtester(
            initial_capital=request.initial_capital,
            commission_per_trade=1.0,
            slippage_pct=0.05
        )
        
        # Run backtest
        results = backtester.run(
            strategy=strategy,
            start_date=request.start_date,
            end_date=request.end_date,
            tickers=request.tickers
        )
        
        duration = time.time() - start_time
        log_api_request(logger, "POST", "/options/backtest", 200, duration)
        
        return {
            "strategy": request.strategy,
            "backtest_period": f"{request.start_date} to {request.end_date}",
            "tickers": request.tickers,
            "results": results
        }
    
    except Exception as e:
        log_error_with_context(logger, e, {
            "strategy": request.strategy,
            "start_date": request.start_date,
            "end_date": request.end_date
        })
        raise HTTPException(status_code=500, detail=str(e))


# Get broker account info (Sprint 5)
@app.get("/broker/account")
async def get_broker_account():
    """
    Get broker account information.
    
    Returns:
        Account details including balance, buying power, etc.
    """
    if broker is None:
        raise HTTPException(status_code=503, detail="Broker not available")
    
    try:
        account_info = broker.get_account_details()
        return account_info
    except Exception as e:
        log_error_with_context(logger, e, {})
        raise HTTPException(status_code=500, detail=str(e))


# Get broker positions (Sprint 5)
@app.get("/broker/positions")
async def get_broker_positions():
    """
    Get all broker positions.
    
    Returns:
        List of positions
    """
    if broker is None:
        raise HTTPException(status_code=503, detail="Broker not available")
    
    try:
        positions = broker.get_positions()
        return {"positions": positions}
    except Exception as e:
        log_error_with_context(logger, e, {})
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Options Service on port 8060")
    
    uvicorn.run(
        "services.options_service:app",
        host="0.0.0.0",
        port=8060,
        reload=False,
        log_level="info"
    )
