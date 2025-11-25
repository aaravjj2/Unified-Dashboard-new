"""
Backtester Service REST API

FastAPI application exposing backtest endpoints:
- POST /api/backtest - Run a new backtest
- GET /api/backtest/{id} - Get backtest results
- GET /health - Service health check
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
import json
import os
from pathlib import Path

from backtester_service.backtester import BacktesterService
from financial_dashboard.services.options_service.strategies.strategy_registry import StrategyNotFoundError

# Initialize FastAPI app
app = FastAPI(
    title="Backtester Service",
    description="Run strategy backtests at scale with MLflow tracking",
    version="0.1.0"
)

# Results storage (simple file-based for now)
RESULTS_DIR = Path("backtester_service/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


class BacktestRequest(BaseModel):
    """Request model for running a backtest."""
    strategy_name: str = Field(..., description="Name of strategy in registry")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    initial_capital: float = Field(10000.0, description="Starting capital")
    params: Dict[str, Any] = Field(default_factory=dict, description="Strategy parameters")
    mlflow_experiment: Optional[str] = Field(None, description="MLflow experiment name")


class BacktestResponse(BaseModel):
    """Response model for backtest results."""
    run_id: str
    status: str
    metrics: Optional[Dict[str, float]] = None
    num_signals: Optional[int] = None
    error: Optional[str] = None


def save_backtest_result(run_id: str, result: Dict[str, Any]):
    """Save backtest result to file."""
    result_file = RESULTS_DIR / f"{run_id}.json"
    with open(result_file, 'w') as f:
        json.dump(result, f, indent=2)


def get_backtest_result(run_id: str) -> Optional[Dict[str, Any]]:
    """Load backtest result from file."""
    result_file = RESULTS_DIR / f"{run_id}.json"
    if result_file.exists():
        with open(result_file, 'r') as f:
            return json.load(f)
    return None


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "backtester",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/backtest", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest):
    """
    Run a backtest for a strategy.
    
    This endpoint executes the backtest synchronously and returns results immediately.
    For long-running backtests, consider using background tasks.
    """
    try:
        # Initialize backtester
        # Note: PriceClient would be injected here in production
        # For now, backtester will use mock/deterministic data
        backtester = BacktesterService(
            price_client=None,  # TODO: Inject real PriceClient
            mlflow_tracking=True,
            mlflow_experiment=request.mlflow_experiment or "backtester-api"
        )
        
        # Run backtest
        result = backtester.run_backtest_by_name(
            strategy_name=request.strategy_name,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            strategy_params=request.params
        )
        
        # Save result
        save_backtest_result(result['run_id'], result)
        
        # Return response
        return BacktestResponse(
            run_id=result['run_id'],
            status=result['status'],
            metrics=result.get('metrics'),
            num_signals=result.get('num_signals')
        )
        
    except StrategyNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Strategy not found: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameters: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/api/backtest/{run_id}", response_model=BacktestResponse)
async def get_backtest_status(run_id: str):
    """
    Get backtest results by run ID.
    
    Returns the status and metrics for a completed or running backtest.
    """
    result = get_backtest_result(run_id)
    
    if result is None:
        raise HTTPException(status_code=404, detail=f"Backtest run {run_id} not found")
    
    return BacktestResponse(
        run_id=result['run_id'],
        status=result['status'],
        metrics=result.get('metrics'),
        num_signals=result.get('num_signals'),
        error=result.get('error')
    )


@app.get("/api/strategies")
async def list_strategies():
    """List all available strategies in the registry."""
    from financial_dashboard.services.options_service.strategies.strategy_registry import StrategyRegistry
    
    registry = StrategyRegistry.get_instance()
    strategies = registry.list_strategies()
    
    # Get metadata for each strategy
    strategy_info = []
    for strategy_name in strategies:
        try:
            metadata = registry.get_strategy_metadata(strategy_name)
            strategy_info.append({
                'name': metadata['name'],
                'module': metadata['module'],
                'description': metadata.get('docstring', '').split('\n')[0] if metadata.get('docstring') else ''
            })
        except Exception:
            # Skip strategies with metadata issues
            continue
    
    return {
        'strategies': strategy_info,
        'count': len(strategy_info)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
