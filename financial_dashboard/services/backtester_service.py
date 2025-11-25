"""
Backtesting Service - Sprint 8
Provides backtesting capabilities for trading strategies
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Backtesting Service", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class BacktestRequest(BaseModel):
    strategy: str
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float = 100000.0
    parameters: Optional[Dict] = {}

class BacktestResult(BaseModel):
    strategy: str
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    equity_curve: List[Dict]
    trade_log: List[Dict]

# Backtesting engine
class BacktestEngine:
    """Simple backtesting engine for demonstration"""
    
    def __init__(self):
        self.strategies = {
            "SMA Crossover": self._sma_crossover,
            "RSI Mean Reversion": self._rsi_mean_reversion,
            "Momentum": self._momentum_strategy
        }
    
    def run_backtest(self, request: BacktestRequest) -> BacktestResult:
        """Execute backtest and return results"""
        logger.info(f"Running backtest: {request.strategy} on {request.symbol}")
        
        # Generate synthetic price data for demonstration
        price_data = self._generate_synthetic_data(
            request.symbol,
            request.start_date,
            request.end_date
        )
        
        # Run strategy
        if request.strategy not in self.strategies:
            raise HTTPException(status_code=400, detail=f"Unknown strategy: {request.strategy}")
        
        trades = self.strategies[request.strategy](price_data, request.parameters)
        
        # Calculate performance metrics
        results = self._calculate_metrics(
            trades,
            price_data,
            request.initial_capital
        )
        
        return BacktestResult(
            strategy=request.strategy,
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            **results
        )
    
    def _generate_synthetic_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Generate synthetic OHLCV data for backtesting"""
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        dates = pd.date_range(start, end, freq='D')
        
        # Random walk with drift
        np.random.seed(hash(symbol) % 2**32)
        returns = np.random.normal(0.0005, 0.02, len(dates))
        price = 100 * np.exp(np.cumsum(returns))
        
        df = pd.DataFrame({
            'date': dates,
            'open': price * (1 + np.random.uniform(-0.01, 0.01, len(dates))),
            'high': price * (1 + np.abs(np.random.uniform(0, 0.02, len(dates)))),
            'low': price * (1 - np.abs(np.random.uniform(0, 0.02, len(dates)))),
            'close': price,
            'volume': np.random.uniform(1e6, 5e6, len(dates))
        })
        
        return df
    
    def _sma_crossover(self, df: pd.DataFrame, params: Dict) -> List[Dict]:
        """Simple Moving Average crossover strategy"""
        short_window = params.get('short_window', 20)
        long_window = params.get('long_window', 50)
        
        df['sma_short'] = df['close'].rolling(window=short_window).mean()
        df['sma_long'] = df['close'].rolling(window=long_window).mean()
        
        trades = []
        position = None
        
        for i in range(long_window, len(df)):
            if position is None:
                if df['sma_short'].iloc[i] > df['sma_long'].iloc[i]:
                    position = {
                        'entry_date': df['date'].iloc[i].isoformat(),
                        'entry_price': df['close'].iloc[i],
                        'type': 'long'
                    }
            elif position is not None:
                if df['sma_short'].iloc[i] < df['sma_long'].iloc[i]:
                    trades.append({
                        **position,
                        'exit_date': df['date'].iloc[i].isoformat(),
                        'exit_price': df['close'].iloc[i],
                        'pnl': df['close'].iloc[i] - position['entry_price']
                    })
                    position = None
        
        return trades
    
    def _rsi_mean_reversion(self, df: pd.DataFrame, params: Dict) -> List[Dict]:
        """RSI mean reversion strategy"""
        rsi_period = params.get('rsi_period', 14)
        oversold = params.get('oversold', 30)
        overbought = params.get('overbought', 70)
        
        # Calculate RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        trades = []
        position = None
        
        for i in range(rsi_period + 1, len(df)):
            if position is None and df['rsi'].iloc[i] < oversold:
                position = {
                    'entry_date': df['date'].iloc[i].isoformat(),
                    'entry_price': df['close'].iloc[i],
                    'type': 'long'
                }
            elif position is not None and df['rsi'].iloc[i] > overbought:
                trades.append({
                    **position,
                    'exit_date': df['date'].iloc[i].isoformat(),
                    'exit_price': df['close'].iloc[i],
                    'pnl': df['close'].iloc[i] - position['entry_price']
                })
                position = None
        
        return trades
    
    def _momentum_strategy(self, df: pd.DataFrame, params: Dict) -> List[Dict]:
        """Momentum-based trading strategy"""
        lookback = params.get('lookback', 20)
        threshold = params.get('threshold', 0.02)
        
        df['returns'] = df['close'].pct_change()
        df['momentum'] = df['returns'].rolling(window=lookback).mean()
        
        trades = []
        position = None
        
        for i in range(lookback + 1, len(df)):
            if position is None and df['momentum'].iloc[i] > threshold:
                position = {
                    'entry_date': df['date'].iloc[i].isoformat(),
                    'entry_price': df['close'].iloc[i],
                    'type': 'long'
                }
            elif position is not None and df['momentum'].iloc[i] < -threshold:
                trades.append({
                    **position,
                    'exit_date': df['date'].iloc[i].isoformat(),
                    'exit_price': df['close'].iloc[i],
                    'pnl': df['close'].iloc[i] - position['entry_price']
                })
                position = None
        
        return trades
    
    def _calculate_metrics(self, trades: List[Dict], price_data: pd.DataFrame, initial_capital: float) -> Dict:
        """Calculate backtest performance metrics"""
        if not trades:
            return {
                'final_capital': initial_capital,
                'total_return': 0.0,
                'total_return_pct': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'win_rate': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'equity_curve': [],
                'trade_log': []
            }
        
        # Calculate equity curve
        equity = initial_capital
        equity_curve = [{'date': price_data['date'].iloc[0].isoformat(), 'equity': equity}]
        
        for trade in trades:
            pnl = trade['pnl']
            shares = equity / trade['entry_price']
            equity += pnl * shares
            equity_curve.append({'date': trade['exit_date'], 'equity': equity})
        
        # Calculate metrics
        total_return = equity - initial_capital
        total_return_pct = (total_return / initial_capital) * 100
        
        winning_trades = sum(1 for t in trades if t['pnl'] > 0)
        losing_trades = len(trades) - winning_trades
        win_rate = (winning_trades / len(trades)) * 100 if trades else 0
        
        # Max drawdown
        peak = initial_capital
        max_dd = 0
        for point in equity_curve:
            if point['equity'] > peak:
                peak = point['equity']
            dd = (peak - point['equity']) / peak
            if dd > max_dd:
                max_dd = dd
        
        # Sharpe ratio (simplified)
        returns = [t['pnl'] / t['entry_price'] for t in trades]
        sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if returns and np.std(returns) > 0 else 0
        
        return {
            'final_capital': equity,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'max_drawdown': max_dd * 100,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'total_trades': len(trades),
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'equity_curve': equity_curve,
            'trade_log': trades[:50]  # Limit to first 50 trades
        }

# Initialize engine
backtest_engine = BacktestEngine()

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "backtester_service",
        "timestamp": datetime.utcnow().isoformat(),
        "strategies_available": list(backtest_engine.strategies.keys())
    }

@app.post("/api/run", response_model=BacktestResult)
async def run_backtest(request: BacktestRequest):
    """Run a backtest with the specified parameters"""
    try:
        result = backtest_engine.run_backtest(request)
        logger.info(f"Backtest completed: {request.strategy} on {request.symbol} - Return: {result.total_return_pct:.2f}%")
        return result
    except Exception as e:
        logger.error(f"Backtest failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/strategies")
async def get_strategies():
    """Get list of available strategies"""
    return {
        "strategies": [
            {
                "name": "SMA Crossover",
                "description": "Simple Moving Average crossover strategy",
                "parameters": {
                    "short_window": {"type": "int", "default": 20, "description": "Short SMA window"},
                    "long_window": {"type": "int", "default": 50, "description": "Long SMA window"}
                }
            },
            {
                "name": "RSI Mean Reversion",
                "description": "RSI-based mean reversion strategy",
                "parameters": {
                    "rsi_period": {"type": "int", "default": 14, "description": "RSI calculation period"},
                    "oversold": {"type": "int", "default": 30, "description": "Oversold threshold"},
                    "overbought": {"type": "int", "default": 70, "description": "Overbought threshold"}
                }
            },
            {
                "name": "Momentum",
                "description": "Momentum-based trading strategy",
                "parameters": {
                    "lookback": {"type": "int", "default": 20, "description": "Momentum lookback period"},
                    "threshold": {"type": "float", "default": 0.02, "description": "Entry threshold"}
                }
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8064)
