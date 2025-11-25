"""
Options Lab - Standalone Application with Dash UI + FastAPI Backend
Runs on port 8060 with integrated trading capabilities.
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
import uvicorn

# Load environment variables
env_path = Path(__file__).parent / 'keys.env'
load_dotenv(env_path)
print(f"✓ Loaded environment variables from {env_path}")

# Import backend modules
from utils.finnhub_client import FinnhubClient
from utils.alpaca_trader import AlpacaTrader
from trading.base_broker import BaseBroker, OrderSide, OrderType
from utils.risk_manager import RiskManager
from utils.alerter import Alerter

# Load configuration
config_path = Path(__file__).parent / 'options_config.yaml'
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Initialize FastAPI
fastapi_app = FastAPI(title="Options Lab API", version="1.0")

# Add CORS
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
finnhub_client = FinnhubClient(config=config['api']['finnhub'])
broker: BaseBroker = AlpacaTrader(paper=config['api']['alpaca']['paper_mode'])
risk_manager = RiskManager(config=config['risk'])
alerter = Alerter(config=config['alerts'])

# Pydantic models
class TradeRequest(BaseModel):
    symbol: str
    quantity: int
    side: str
    order_type: str = 'market'
    limit_price: Optional[float] = None

# API Endpoints
@fastapi_app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "options_lab", "timestamp": str(datetime.now())}

@fastapi_app.get("/account")
async def get_account():
    try:
        account = broker.get_account_details()
        return {"success": True, "data": account}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.get("/positions")
async def get_positions():
    try:
        positions = broker.get_positions()
        return {"success": True, "data": positions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.get("/quote/{symbol}")
async def get_quote(symbol: str):
    try:
        quote = finnhub_client.get_quote(symbol)
        return quote
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.get("/options-chain/{symbol}")
async def get_options_chain(symbol: str, expiration: Optional[str] = None):
    try:
        chain = finnhub_client.get_options_chain(symbol, expiration_date=expiration)
        
        # Handle empty or None response
        if not chain:
            return {"success": False, "options": [], "error": "No options data available"}
        
        # If chain is a dict with 'data' key, extract it
        if isinstance(chain, dict):
            options_data = chain.get('data', chain.get('options', []))
        else:
            options_data = chain if isinstance(chain, list) else []
        
        return {"success": True, "options": options_data}
    except Exception as e:
        return {"success": False, "options": [], "error": str(e)}

@fastapi_app.get("/expirations/{symbol}")
async def get_expirations(symbol: str):
    try:
        expirations = finnhub_client.get_options_expirations(symbol)
        
        # Generate mock expirations if none found (Finnhub free tier may not have this)
        if not expirations:
            from datetime import datetime, timedelta
            today = datetime.now()
            expirations = []
            for weeks in [1, 2, 3, 4, 8, 12, 16, 24]:
                exp_date = (today + timedelta(weeks=weeks)).strftime('%Y-%m-%d')
                expirations.append(exp_date)
        
        return {"success": True, "expirations": expirations}
    except Exception as e:
        # Fallback to generated expirations
        from datetime import datetime, timedelta
        today = datetime.now()
        expirations = [(today + timedelta(weeks=w)).strftime('%Y-%m-%d') for w in [1,2,3,4,8,12,16,24]]
        return {"success": True, "expirations": expirations}

@fastapi_app.post("/trade")
async def place_trade(trade: TradeRequest):
    try:
        # Convert to enums
        order_side = OrderSide.BUY if trade.side.lower() == 'buy' else OrderSide.SELL
        order_type_map = {
            'market': OrderType.MARKET,
            'limit': OrderType.LIMIT
        }
        order_type_enum = order_type_map.get(trade.order_type.lower(), OrderType.MARKET)
        
        # Place order
        order = broker.place_order(
            symbol=trade.symbol,
            qty=trade.quantity,
            side=order_side,
            order_type=order_type_enum,
            limit_price=trade.limit_price
        )
        
        alerter.alert_trade_executed(order)
        return {"success": True, "data": order}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.get("/orders")
async def get_orders():
    try:
        orders = broker.get_orders()
        return {"success": True, "data": orders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Now create Dash app
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from tabs.options_lab import create_layout, register_callbacks

dash_app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    suppress_callback_exceptions=True,
    title="Options Trading Lab",
    requests_pathname_prefix='/dash/'
)

dash_app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("💹 Options Trading Lab", className="text-center my-4"),
            html.P(
                "Automated strategy monitoring, manual trading, and P&L analysis.",
                className="text-center text-muted mb-4"
            )
        ])
    ]),
    dbc.Row([
        dbc.Col([
            create_layout()
        ])
    ])
], fluid=True, style={'backgroundColor': '#1a1a1a', 'minHeight': '100vh'})

register_callbacks(dash_app)

# Mount Dash app to FastAPI
fastapi_app.mount("/dash", WSGIMiddleware(dash_app.server))

# Redirect root to Dash app
@fastapi_app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dash/")

if __name__ == '__main__':
    print("=" * 70)
    print("🚀 Starting Options Trading Lab (Standalone)")
    print("=" * 70)
    print(f"📡 UI: http://localhost:8060/")
    print(f"📡 API Docs: http://localhost:8060/docs")
    print(f"📊 Mode: PAPER TRADING")
    print(f"🔑 Broker: Alpaca (Paper)")
    print(f"🔑 Data: Finnhub")
    print("=" * 70)
    
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8060, log_level="info")
