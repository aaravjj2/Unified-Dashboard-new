"""
Options Trading Service
FastAPI application that orchestrates options trading logic.
Provides endpoints for strategy execution, monitoring, and manual trading.
"""

import os
import yaml
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from keys.env
env_path = Path(__file__).parent / 'keys.env'
load_dotenv(env_path)
print(f"✓ Loaded environment variables from {env_path}")

# Import our custom modules
from utils.finnhub_client import FinnhubClient
from utils.alpaca_trader import AlpacaTrader
from trading.base_broker import BaseBroker, OrderSide, OrderType, OrderStatus
from utils.risk_manager import RiskManager
from utils.alerter import Alerter, AlertSeverity, AlertCategory
from strategies.covered_call_screener import CoveredCallScreener


# Load configuration
config_path = Path(__file__).parent / 'options_config.yaml'
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Initialize FastAPI app
app = FastAPI(
    title="Options Trading Service",
    description="API for automated and manual options trading",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
finnhub_client = FinnhubClient(config=config['api']['finnhub'])
# Use BaseBroker interface for broker-agnostic design
alpaca_trader: BaseBroker = AlpacaTrader(paper_mode=config['api']['alpaca']['paper_mode'])
risk_manager = RiskManager(config=config['risk'])
alerter = Alerter(config=config['alerts'])

# Initialize strategies
strategies = {}
if config['strategies']['covered_call_screener']['enabled']:
    strategies['covered_call'] = CoveredCallScreener(
        config=config['strategies']['covered_call_screener']
    )

# Strategy execution state
strategy_state = {
    'running': False,
    'last_run': None,
    'last_signals': [],
    'total_runs': 0,
    'execution_count': 0,
    'errors': [],
    'positions_opened': 0,
    'positions_closed': 0
}

# Live execution loop control
live_loop_task: Optional[asyncio.Task] = None


# Pydantic models for request/response
class TradeRequest(BaseModel):
    symbol: str
    quantity: int
    side: str  # 'buy' or 'sell'
    order_type: str = 'market'
    limit_price: Optional[float] = None


class StrategyRunRequest(BaseModel):
    strategy_name: str
    symbols: List[str]


class SignalResponse(BaseModel):
    action: str
    symbol: str
    quantity: int
    reason: str
    confidence: Optional[float] = None
    metadata: Optional[Dict] = None


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "options_service"
    }


# Account endpoints
@app.get("/account")
async def get_account():
    """Get account information."""
    try:
        account = alpaca_trader.get_account_details()
        return {"success": True, "data": account}
    except Exception as e:
        alerter.alert_api_error("Alpaca", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/positions")
async def get_positions():
    """Get all current positions."""
    try:
        positions = alpaca_trader.get_positions()
        return {"success": True, "data": positions}
    except Exception as e:
        alerter.alert_api_error("Alpaca", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/positions/{symbol}")
async def get_position(symbol: str):
    """Get specific position."""
    try:
        position = alpaca_trader.get_position(symbol)
        if position is None:
            raise HTTPException(status_code=404, detail=f"No position found for {symbol}")
        return {"success": True, "data": position}
    except HTTPException:
        raise
    except Exception as e:
        alerter.alert_api_error("Alpaca", str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Market data endpoints
@app.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """Get quote for a symbol."""
    try:
        quote = finnhub_client.get_quote(symbol)
        return {"success": True, "data": quote}
    except Exception as e:
        alerter.alert_api_error("Finnhub", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/options-chain/{symbol}")
async def get_options_chain(symbol: str, expiration: Optional[str] = None):
    """Get options chain for a symbol."""
    try:
        chain = finnhub_client.get_options_chain(symbol, expiration)
        return {"success": True, "data": chain}
    except Exception as e:
        alerter.alert_api_error("Finnhub", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/options-expirations/{symbol}")
async def get_expirations(symbol: str):
    """Get available expiration dates for a symbol."""
    try:
        expirations = finnhub_client.get_options_expirations(symbol)
        return {"success": True, "data": expirations}
    except Exception as e:
        alerter.alert_api_error("Finnhub", str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Trading endpoints
@app.post("/trade")
async def place_trade(trade: TradeRequest):
    """Place a manual trade with risk checks."""
    try:
        # Get current account and positions for risk check
        account = alpaca_trader.get_account_details()
        positions = alpaca_trader.get_positions()
        
        # Estimate trade cost (simplified)
        if trade.order_type == 'limit' and trade.limit_price:
            estimated_cost = trade.quantity * trade.limit_price * 100  # Assuming options
        else:
            # For market orders, would need to fetch current price
            estimated_cost = trade.quantity * 100  # Rough estimate
        
        trade_dict = {
            'symbol': trade.symbol,
            'quantity': trade.quantity,
            'side': trade.side,
            'estimated_cost': estimated_cost
        }
        
        # Risk check
        approved, reason = risk_manager.check_trade_risk(trade_dict, positions, account)
        
        if not approved:
            alerter.alert_risk_breach("Trade rejected", {'trade': trade_dict, 'reason': reason})
            return {"success": False, "error": reason}
        
        # Convert string inputs to enums
        order_side = OrderSide.BUY if trade.side.lower() == 'buy' else OrderSide.SELL
        order_type_map = {
            'market': OrderType.MARKET,
            'limit': OrderType.LIMIT,
            'stop': OrderType.STOP,
            'stop_limit': OrderType.STOP_LIMIT
        }
        order_type_enum = order_type_map.get(trade.order_type.lower(), OrderType.MARKET)
        
        # Place order using BaseBroker interface
        order = alpaca_trader.place_order(
            symbol=trade.symbol,
            quantity=trade.quantity,
            side=order_side,
            order_type=order_type_enum,
            limit_price=trade.limit_price
        )
        
        alerter.alert_trade_executed(order)
        return {"success": True, "data": order}
        
    except Exception as e:
        trade_details = {'symbol': trade.symbol, 'quantity': trade.quantity, 'side': trade.side}
        alerter.alert_trade_failed(trade_details, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orders")
async def get_orders(status: Optional[str] = None):
    """Get all orders."""
    try:
        orders = alpaca_trader.get_orders(status=None)  # Pass None to get all orders
        return {"success": True, "data": orders}
    except Exception as e:
        alerter.alert_api_error("Alpaca", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get specific order status."""
    try:
        order = alpaca_trader.get_order_status(order_id)
        return {"success": True, "data": order}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Strategy endpoints
@app.post("/run-strategy")
async def run_strategy(request: StrategyRunRequest):
    """Run a strategy to generate signals."""
    try:
        strategy_name = request.strategy_name
        symbols = request.symbols
        
        if strategy_name not in strategies:
            raise HTTPException(status_code=404, detail=f"Strategy '{strategy_name}' not found")
        
        strategy = strategies[strategy_name]
        all_signals = []
        
        # Run strategy for each symbol
        for symbol in symbols:
            # Fetch market data
            quote = finnhub_client.get_quote(symbol)
            options_chain = finnhub_client.get_options_chain(symbol)
            
            # Prepare data for strategy
            data = {
                'symbol': symbol,
                'current_price': quote.get('c'),  # Current price
                'volume': quote.get('v', 0),  # Volume
                'options_chain': options_chain
            }
            
            # Generate signals
            signals = strategy.generate_signals(data)
            all_signals.extend(signals)
        
        # Update state
        strategy_state['last_run'] = datetime.now().isoformat()
        strategy_state['last_signals'] = all_signals
        strategy_state['total_runs'] += 1
        
        return {
            "success": True,
            "strategy": strategy_name,
            "signals_generated": len(all_signals),
            "signals": all_signals
        }
        
    except Exception as e:
        alerter.alert_api_error("Strategy Execution", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/strategy-status")
async def get_strategy_status():
    """Get current strategy execution status."""
    return {
        "success": True,
        "data": {
            **strategy_state,
            'available_strategies': list(strategies.keys()),
            'strategies_info': {name: strat.get_status() for name, strat in strategies.items()}
        }
    }


@app.post("/strategy/start")
async def start_strategy():
    """Start automated strategy execution."""
    strategy_state['running'] = True
    alerter.alert_strategy_started("Automated Strategy Loop")
    return {"success": True, "message": "Strategy execution started"}


@app.post("/strategy/stop")
async def stop_strategy():
    """Stop automated strategy execution."""
    strategy_state['running'] = False
    alerter.alert_strategy_stopped("Automated Strategy Loop")
    return {"success": True, "message": "Strategy execution stopped"}


# Live execution loop endpoints (Sprint 4)
@app.post("/api/live/start")
async def start_live_loop(symbols: Optional[List[str]] = None, interval_seconds: int = 300):
    """
    Start the live automated execution loop.
    
    Args:
        symbols: List of symbols to monitor (default: configured watchlist)
        interval_seconds: Seconds between execution cycles (default: 300 = 5 minutes)
    
    Returns:
        Success status and loop info
    """
    global live_loop_task
    
    if live_loop_task and not live_loop_task.done():
        return {"success": False, "error": "Live loop already running"}
    
    # Use configured symbols or provided symbols
    if symbols is None:
        symbols = config.get('watchlist', ['SPY', 'QQQ', 'IWM'])
    
    # Start live loop as background task
    live_loop_task = asyncio.create_task(
        live_execution_loop(symbols, interval_seconds)
    )
    
    strategy_state['running'] = True
    alerter.send_alert(
        f"Live execution loop started: monitoring {len(symbols)} symbols every {interval_seconds}s",
        AlertSeverity.INFO,
        AlertCategory.STRATEGY_STATUS,
        {'symbols': symbols, 'interval': interval_seconds}
    )
    
    return {
        "success": True,
        "message": "Live execution loop started",
        "symbols": symbols,
        "interval_seconds": interval_seconds
    }


@app.post("/api/live/stop")
async def stop_live_loop():
    """
    Stop the live automated execution loop.
    
    Returns:
        Success status
    """
    global live_loop_task
    
    if not live_loop_task or live_loop_task.done():
        return {"success": False, "error": "Live loop not running"}
    
    # Signal loop to stop
    strategy_state['running'] = False
    
    # Wait for graceful shutdown (up to 10 seconds)
    try:
        await asyncio.wait_for(live_loop_task, timeout=10.0)
    except asyncio.TimeoutError:
        live_loop_task.cancel()
    
    alerter.send_alert(
        "Live execution loop stopped",
        AlertSeverity.INFO,
        AlertCategory.STRATEGY_STATUS,
        {'total_runs': strategy_state['total_runs'], 'execution_count': strategy_state['execution_count']}
    )
    
    return {
        "success": True,
        "message": "Live execution loop stopped",
        "stats": {
            'total_runs': strategy_state['total_runs'],
            'execution_count': strategy_state['execution_count'],
            'positions_opened': strategy_state['positions_opened']
        }
    }


@app.get("/api/live/status")
async def get_live_loop_status():
    """
    Get current status of live execution loop.
    
    Returns:
        Loop status and stats
    """
    global live_loop_task
    
    is_running = live_loop_task is not None and not live_loop_task.done()
    
    return {
        "success": True,
        "data": {
            'running': is_running,
            'state': strategy_state,
            'task_alive': live_loop_task is not None
        }
    }


async def live_execution_loop(symbols: List[str], interval_seconds: int):
    """
    Main live execution loop that continuously monitors and trades.
    
    Args:
        symbols: Symbols to monitor
        interval_seconds: Seconds between execution cycles
    """
    print(f"Live execution loop started for {symbols}")
    
    while strategy_state['running']:
        try:
            # Execute one cycle
            await execute_strategy_cycle(symbols)
            
            # Wait for next cycle
            await asyncio.sleep(interval_seconds)
            
        except Exception as e:
            error_msg = f"Error in live execution loop: {str(e)}"
            print(error_msg)
            strategy_state['errors'].append({
                'timestamp': datetime.now().isoformat(),
                'error': error_msg
            })
            alerter.send_alert(
                error_msg,
                AlertSeverity.ERROR,
                AlertCategory.SYSTEM,
                {'exception': str(e)}
            )
            
            # Keep only last 10 errors
            strategy_state['errors'] = strategy_state['errors'][-10:]
            
            # Wait before retry
            await asyncio.sleep(60)
    
    print("Live execution loop stopped")


async def execute_strategy_cycle(symbols: List[str]):
    """
    Execute one cycle of strategy logic for all symbols.
    
    Args:
        symbols: Symbols to analyze
    """
    strategy_state['total_runs'] += 1
    strategy_state['last_run'] = datetime.now().isoformat()
    
    # Get account and positions for risk checks
    account = alpaca_trader.get_account_details()
    current_positions = alpaca_trader.get_positions()
    
    all_signals = []
    
    # Run each enabled strategy
    for strategy_name, strategy in strategies.items():
        if not strategy.enabled:
            continue
        
        try:
            # Generate signals for all symbols
            for symbol in symbols:
                # Fetch market data
                quote = finnhub_client.get_quote(symbol)
                
                # Skip if market data unavailable
                if not quote or 'c' not in quote:
                    continue
                
                options_chain = finnhub_client.get_options_chain(symbol)
                
                # Prepare data for strategy
                data = {
                    'symbol': symbol,
                    'current_price': quote.get('c'),
                    'volume': quote.get('v', 0),
                    'options_chain': options_chain
                }
                
                # Generate signals
                signals = strategy.generate_signals(data)
                all_signals.extend(signals)
        
        except Exception as e:
            print(f"Error running strategy {strategy_name}: {e}")
            continue
    
    # Store signals
    strategy_state['last_signals'] = all_signals
    
    # Execute approved signals
    for signal in all_signals:
        if not strategy.validate_signal(signal):
            continue
        
        try:
            # Estimate cost
            estimated_cost = signal['quantity'] * signal.get('metadata', {}).get('premium', 1.0) * 100
            
            # Risk check
            trade_dict = {
                'symbol': signal['symbol'],
                'quantity': signal['quantity'],
                'side': signal['action'],
                'estimated_cost': estimated_cost
            }
            
            approved, reason = risk_manager.check_trade_risk(trade_dict, current_positions, account)
            
            if not approved:
                print(f"Trade rejected by risk manager: {reason}")
                alerter.send_alert(
                    f"Trade rejected: {reason}",
                    AlertSeverity.WARNING,
                    AlertCategory.RISK_BREACH,
                    {'signal': signal, 'reason': reason}
                )
                continue
            
            # Execute trade
            order_side = OrderSide.BUY if signal['action'] == 'buy' else OrderSide.SELL
            
            order = alpaca_trader.place_order(
                symbol=signal['symbol'],
                quantity=signal['quantity'],
                side=order_side,
                order_type=OrderType.MARKET
            )
            
            strategy_state['execution_count'] += 1
            if signal['action'] == 'buy':
                strategy_state['positions_opened'] += 1
            else:
                strategy_state['positions_closed'] += 1
            
            alerter.send_alert(
                f"Trade executed: {signal['action']} {signal['quantity']} {signal['symbol']}",
                AlertSeverity.INFO,
                AlertCategory.TRADE_EXECUTION,
                {'order': order, 'signal': signal}
            )
            
        except Exception as e:
            error_msg = f"Failed to execute signal {signal['symbol']}: {str(e)}"
            print(error_msg)
            alerter.send_alert(
                error_msg,
                AlertSeverity.ERROR,
                AlertCategory.TRADE_FAILURE,
                {'signal': signal, 'error': str(e)}
            )
            continue


# Risk management endpoints
@app.get("/risk-summary")
async def get_risk_summary():
    """Get current risk metrics."""
    try:
        account = alpaca_trader.get_account_details()
        positions = alpaca_trader.get_positions()
        risk_summary = risk_manager.get_risk_summary(positions, account)
        return {"success": True, "data": risk_summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Alerts endpoints
@app.get("/alerts")
async def get_alerts(limit: int = 50):
    """Get recent alerts."""
    alerts = alerter.get_recent_alerts(limit=limit)
    return {"success": True, "data": alerts}


# Configuration endpoints
@app.get("/config")
async def get_config():
    """Get current configuration (sanitized)."""
    # Remove sensitive data
    safe_config = {
        'strategies': config['strategies'],
        'risk': config['risk'],
        'alerts': {k: v for k, v in config['alerts'].items() if 'enabled' in k or k in ['log_to_file']},
        'service': config['service']
    }
    return {"success": True, "data": safe_config}


# Startup/shutdown events
@app.on_event("startup")
async def startup_event():
    """Actions to perform on service startup."""
    alerter.send_alert(
        "Options Trading Service started",
        AlertSeverity.INFO,
        AlertCategory.SYSTEM,
        {'port': config['service']['port']}
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Actions to perform on service shutdown."""
    alerter.send_alert(
        "Options Trading Service shutting down",
        AlertSeverity.INFO,
        AlertCategory.SYSTEM
    )
    finnhub_client.close()


# Run server
if __name__ == "__main__":
    import uvicorn
    
    host = config['service']['host']
    port = config['service']['port']
    debug = config['service']['debug']
    
    print(f"Starting Options Trading Service on {host}:{port}")
    
    uvicorn.run(
        "options_service:app",
        host=host,
        port=port,
        reload=debug,
        log_level=config['service']['log_level'].lower()
    )
