"""
BentoML Service for Financial Dashboard ML Models
Provides high-performance model serving with GPU acceleration

Features:
- Forecast Engine (Prophet, ARIMA, LSTM, Ensemble)
- Sentiment Analysis (FinBERT)
- Strategy Prediction
- Volatility Forecasting

Run: bentoml serve serving/bento_service:FinancialMLService
"""

import bentoml
import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ============================================================================
# Request/Response Models
# ============================================================================

class ForecastRequest(BaseModel):
    ticker: str = "AAPL"
    horizon: int = 30
    model: str = "ensemble"


class SentimentRequest(BaseModel):
    texts: List[str]
    ticker: Optional[str] = None


class BacktestRequest(BaseModel):
    tickers: List[str] = ["AAPL"]
    strategy: str = "momentum"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    parameters: Dict[str, Any] = {}


class EmbedRequest(BaseModel):
    texts: List[str]


# ============================================================================
# BentoML Service
# ============================================================================

@bentoml.service(
    name="financial_dashboard_ml",
    resources={"gpu": 1, "memory": "4Gi"},
    traffic={"timeout": 60}
)
class FinancialMLService:
    """Financial Dashboard ML Service with GPU acceleration"""
    
    def __init__(self):
        logger.info("Initializing Financial ML Service...")
        self._forecast_engine = None
        self._sentiment_analyzer = None
        self._embedder = None
    
    @bentoml.api
    async def forecast_price(self, request: ForecastRequest) -> Dict[str, Any]:
        """
        Generate price forecast using AI ensemble
        """
        try:
            from financial_dashboard.models.ai_forecast_engine import AIForecastEngine
            
            if self._forecast_engine is None:
                self._forecast_engine = AIForecastEngine()
            
            result = self._forecast_engine.forecast(
                ticker=request.ticker,
                horizon=request.horizon,
                model=request.model
            )
            
            return {
                "ticker": request.ticker,
                "forecast": result.get("forecast", []),
                "confidence": result.get("confidence", 0.0),
                "model": request.model,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Forecast error: {e}")
            return {"error": str(e), "ticker": request.ticker}
    
    @bentoml.api
    async def analyze_sentiment(self, request: SentimentRequest) -> Dict[str, Any]:
        """
        Analyze sentiment of financial text using FinBERT
        """
        try:
            from financial_dashboard.models.finbert_sentiment import FinBERTSentimentAnalyzer
            
            if self._sentiment_analyzer is None:
                self._sentiment_analyzer = FinBERTSentimentAnalyzer()
            
            results = []
            scores = {"positive": 0, "negative": 0, "neutral": 0}
            
            for text in request.texts:
                sentiment = self._sentiment_analyzer.analyze(text)
                results.append({
                    "text": text[:100] + "..." if len(text) > 100 else text,
                    "sentiment": sentiment.get("label", "neutral"),
                    "score": sentiment.get("score", 0.5)
                })
                label = sentiment.get("label", "neutral")
                scores[label] = scores.get(label, 0) + 1
            
            total = len(results)
            aggregate = {k: v / total for k, v in scores.items()} if total > 0 else {}
            
            return {
                "sentiments": results,
                "aggregate": aggregate,
                "ticker": request.ticker,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Sentiment error: {e}")
            return {"error": str(e)}
    
    @bentoml.api
    async def run_strategy_backtest(self, request: BacktestRequest) -> Dict[str, Any]:
        """
        Run strategy backtest
        """
        try:
            from financial_dashboard.models.backtest_engine import BacktestEngine
            
            engine = BacktestEngine()
            result = engine.run_backtest(
                tickers=request.tickers,
                strategy=request.strategy,
                start_date=request.start_date,
                end_date=request.end_date,
                parameters=request.parameters
            )
            
            return {
                "strategy": request.strategy,
                "tickers": request.tickers,
                "returns": result.get("total_return", 0),
                "sharpe_ratio": result.get("sharpe_ratio", 0),
                "max_drawdown": result.get("max_drawdown", 0),
                "win_rate": result.get("win_rate", 0),
                "num_trades": result.get("num_trades", 0),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Backtest error: {e}")
            return {"error": str(e)}
    
    @bentoml.api
    async def embed_text(self, request: EmbedRequest) -> Dict[str, Any]:
        """
        Generate embeddings for RAG retrieval
        """
        try:
            from financial_dashboard.services.chat.embed import get_embedder
            
            if self._embedder is None:
                self._embedder = get_embedder()
            
            embeddings = self._embedder.embed_batch(request.texts)
            
            return {
                "embeddings": embeddings.tolist(),
                "dim": embeddings.shape[1] if len(embeddings.shape) > 1 else len(embeddings),
                "count": len(request.texts),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return {"error": str(e)}
    
    @bentoml.api
    async def health_check(self) -> Dict[str, Any]:
        """Health check endpoint"""
        import torch
        
        return {
            "status": "healthy",
            "service": "financial_dashboard_ml",
            "gpu_available": torch.cuda.is_available(),
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# Triton-compatible model configs
# ============================================================================

def get_triton_model_config(model_name: str) -> Dict[str, Any]:
    """
    Generate Triton Inference Server model configuration
    
    Triton supports:
    - TensorRT for NVIDIA GPUs
    - ONNX Runtime
    - PyTorch (TorchScript)
    - Ensemble models
    """
    configs = {
        "forecast_ensemble": {
            "name": "forecast_ensemble",
            "platform": "pytorch_libtorch",
            "max_batch_size": 32,
            "input": [
                {"name": "price_history", "data_type": "FP32", "dims": [-1, 60]},  # 60-day history
                {"name": "ticker_id", "data_type": "INT32", "dims": [1]}
            ],
            "output": [
                {"name": "forecast", "data_type": "FP32", "dims": [30]},  # 30-day forecast
                {"name": "confidence", "data_type": "FP32", "dims": [1]}
            ],
            "instance_group": [{"kind": "KIND_GPU", "count": 1}],
            "dynamic_batching": {"max_queue_delay_microseconds": 100000}
        },
        "sentiment_finbert": {
            "name": "sentiment_finbert",
            "platform": "pytorch_libtorch",
            "max_batch_size": 64,
            "input": [
                {"name": "input_ids", "data_type": "INT64", "dims": [-1, 512]},
                {"name": "attention_mask", "data_type": "INT64", "dims": [-1, 512]}
            ],
            "output": [
                {"name": "logits", "data_type": "FP32", "dims": [3]}  # positive, neutral, negative
            ],
            "instance_group": [{"kind": "KIND_GPU", "count": 1}],
            "dynamic_batching": {"max_queue_delay_microseconds": 50000}
        },
        "embeddings": {
            "name": "embeddings",
            "platform": "onnxruntime_onnx",
            "max_batch_size": 128,
            "input": [
                {"name": "input_ids", "data_type": "INT64", "dims": [-1, 256]},
                {"name": "attention_mask", "data_type": "INT64", "dims": [-1, 256]}
            ],
            "output": [
                {"name": "embeddings", "data_type": "FP32", "dims": [384]}
            ],
            "instance_group": [{"kind": "KIND_GPU", "count": 1}],
            "dynamic_batching": {"max_queue_delay_microseconds": 25000}
        }
    }
    
    return configs.get(model_name, {})


if __name__ == "__main__":
    # Print service info
    print("Financial Dashboard ML Service")
    print("=" * 40)
    print("Endpoints:")
    print("  - POST /forecast_price")
    print("  - POST /analyze_sentiment")
    print("  - POST /run_strategy_backtest")
    print("  - POST /embed_text")
    print("  - POST /health_check")
    print("\nRun with: bentoml serve serving/bento_service:svc")
