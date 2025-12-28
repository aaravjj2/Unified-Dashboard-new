"""
Model Serving Client Wrapper

Provides a simple interface to route inference calls to:
- BentoML service (dev/prod)
- Triton Inference Server (prod GPU)
- Local `ml_runner` or adapter (fallback)

Usage: from financial_dashboard.serving.serving_client import ServingClient

"""

import os
import json
import logging
from typing import Any, Dict, Optional
import requests

logger = logging.getLogger(__name__)


class ServingClient:
    """Unified client to route forecast & ML calls."""

    def __init__(self):
        # Read env config at runtime to allow unit tests to change env vars
        use_bento = os.getenv('USE_BENTO', '0') == '1'
        bento_url = os.getenv('BENTO_URL', 'http://localhost:5001')
        use_triton = os.getenv('USE_TRITON', '0') == '1'
        triton_url = os.getenv('TRITON_URL', 'localhost:8000')

        self.mode = 'local'
        if use_bento:
            self.mode = 'bento'
        if use_triton:
            self.mode = 'triton'

        self.bento_url = bento_url
        # import here to avoid import-time errors
        self._triton_client = None
        if self.mode == 'triton':
            try:
                from financial_dashboard.serving.triton_integration import TritonClient
                self._triton_client = TritonClient(url=triton_url)
            except Exception:
                logger.warning('Triton client not available; falling back to local mode')
                self.mode = 'local'

    def predict_forecast(self, ticker: str, horizon: int, model: str = 'ensemble', confidence: float = 0.95) -> Dict[str, Any]:
        """Call the configured serving backend to return a forecast dict.

        Returns a dict: {"status": "success", "model": model, "source": "bento|triton|local", "forecast": [...]}
        """
        if self.mode == 'bento':
            return self._predict_bento(ticker, horizon, model, confidence)
        if self.mode == 'triton':
            return self._predict_triton(ticker, horizon, model, confidence)
        # Default local
        return self._predict_local(ticker, horizon, model, confidence)

    def analyze_sentiment(self, texts: list, ticker: Optional[str] = None) -> Dict[str, Any]:
        """Analyze sentiment using configured backend."""
        if self.mode == 'bento':
            return self._analyze_bento(texts, ticker)
        if self.mode == 'triton':
            return self._analyze_triton(texts, ticker)
        return self._analyze_local(texts, ticker)

    def embed_texts(self, texts: list) -> Dict[str, Any]:
        """Return embeddings using the configured backend"""
        if self.mode == 'bento':
            return self._embed_bento(texts)
        if self.mode == 'triton':
            return self._embed_triton(texts)
        return self._embed_local(texts)

    def _predict_bento(self, ticker: str, horizon: int, model: str, confidence: float) -> Dict[str, Any]:
        import requests
        try:
            payload = {
                'request': {
                    'ticker': ticker,
                    'horizon': int(horizon),
                    'model': model,
                    'confidence': float(confidence)
                }
            }
            url = f"{self.bento_url}/forecast_price"
            logger.info(f"Calling Bento service @ {url} for {ticker}")
            r = requests.post(url, json=payload, timeout=20)
            r.raise_for_status()
            data = r.json()
            return {"status": "success", "source": "bento", "data": data}
        except Exception as e:
            logger.exception(f"Bento prediction failed: {e}")
            return {"status": "error", "source": "bento", "error": str(e)}

    def _predict_triton(self, ticker: str, horizon: int, model: str, confidence: float) -> Dict[str, Any]:
        try:
            if self._triton_client is None:
                return {"status": "error", "error": "triton client not initialized", "source": "triton"}

            # Triton usage: for forecast, we'll pack a small price history to call an ensemble
            # Adapter is expected to transform inputs accordingly
            # For now, call sentiment and embedding examples as a proof-of-concept
            # In real usage, we'd send a feature matrix with price history
            logger.info(f"Calling Triton server for {ticker}")
            # Attempt to fetch a price history using the unified fetch helper
            try:
                # Lazy import the shared fetcher to avoid importing heavy deps at module load
                from financial_dashboard.utils.price_fetch import fetch_historical_data
                import numpy as np
                from datetime import datetime, timedelta

                # Request a slightly larger window to ensure we can extract 60 points
                end_date = datetime.utcnow().date()
                start_date = end_date - timedelta(days=120)

                df = fetch_historical_data([ticker], start_date=start_date, end_date=end_date, use_alpaca=True)
                # fetch_historical_data returns a DataFrame with tickers as columns
                if df is None or ticker not in df.columns or df[ticker].dropna().empty:
                    raise RuntimeError('no historical data returned')

                closes = df[ticker].dropna().values
                seq_len = 60
                if len(closes) < seq_len:
                    pad_val = float(closes[-1]) if len(closes) else 0.0
                    pad = np.full((seq_len - len(closes),), pad_val)
                    closes = np.concatenate([pad, closes])
                price_hist = closes[-seq_len:].astype('float32').reshape(1, seq_len)
            except Exception as e:
                logger.warning(f"Failed to fetch price history via unified fetcher for Triton forecast: {e}")
                # Optional explicit yfinance fallback controlled by env var
                allow_yf = os.getenv('ALLOW_YFINANCE_FALLBACK', '0') == '1'
                if allow_yf:
                    try:
                        import numpy as np
                        import yfinance as yf
                        hist = yf.Ticker(ticker).history(period='90d', interval='1d', auto_adjust=True)
                        closes = hist['Close'].dropna().values
                        seq_len = 60
                        if len(closes) < seq_len:
                            pad = np.full((seq_len - len(closes),), closes[-1] if len(closes) else 0.0)
                            closes = np.concatenate([pad, closes])
                        price_hist = closes[-seq_len:].astype('float32').reshape(1, seq_len)
                    except Exception as ye:
                        logger.warning(f"yfinance fallback failed for Triton forecast: {ye}")
                        return {"status": "error", "source": "triton", "error": "failed to fetch price history"}
                else:
                    return {"status": "error", "source": "triton", "error": "failed to fetch price history"}

            try:
                payload = self._triton_client.infer_forecast(price_hist, ticker_id=0)
                return {"status": "success", "source": "triton", "data": payload}
            except Exception as e:
                logger.exception(e)
                return {"status": "error", "source": "triton", "error": str(e)}
        except Exception as e:
            logger.exception(e)
            return {"status": "error", "source": "triton", "error": str(e)}

    def _predict_local(self, ticker: str, horizon: int, model: str, confidence: float) -> Dict[str, Any]:
        """Fallback to local model runner (AIForecastEngine or ml_runner)"""
        try:
            # Prefer AIForecastEngine if present
            try:
                from financial_dashboard.models.ai_forecast_engine import AIForecastEngine
                engine = AIForecastEngine()
                result = engine.forecast(ticker=ticker, horizon=horizon, model=model)
                return {"status": "success", "source": "local", "data": result}
            except Exception:
                # fallback: call ml_runner if available
                try:
                    import ml_runner
                    result = ml_runner.predict({'ticker': ticker, 'horizon': horizon, 'model': model})
                    return {"status": "success", "source": "local", "data": result}
                except Exception as e:
                    logger.warning(f"ml_runner not available or failed: {e}")
                    # fallback statistical
                    from financial_dashboard.services.forecast_adapter import TritonModelExporter  # no-op to satisfy circular
                    # This is a best-effort: fallback to empty/stochastic forecast
                    # NOTE: Avoid importing internal private methods to keep modularity.
                    return {"status": "error", "source": "local", "error": "no local model available"}

        except Exception as e:
            logger.exception(e)
            return {"status": "error", "source": "local", "error": str(e)}

    # Sentiment helpers
    def _analyze_bento(self, texts: list, ticker: Optional[str] = None) -> Dict[str, Any]:
        try:
            url = f"{self.bento_url}/analyze_sentiment"
            payload = {"request": {"texts": texts, "ticker": ticker}}
            r = requests.post(url, json=payload, timeout=20)
            r.raise_for_status()
            return {"status": "success", "source": "bento", "data": r.json()}
        except Exception as e:
            logger.exception(e)
            return {"status": "error", "source": "bento", "error": str(e)}

    def _analyze_triton(self, texts: list, ticker: Optional[str] = None) -> Dict[str, Any]:
        try:
            if self._triton_client is None:
                return {"status": "error", "source": "triton", "error": "triton client not available"}
            preds = self._triton_client.infer_sentiment(texts)
            return {"status": "success", "source": "triton", "data": preds}
        except Exception as e:
            logger.exception(e)
            return {"status": "error", "source": "triton", "error": str(e)}

    def _analyze_local(self, texts: list, ticker: Optional[str] = None) -> Dict[str, Any]:
        try:
            # Attempt to call local FinBERT wrapper
            from financial_dashboard.models.finbert_sentiment import FinBERTSentimentAnalyzer
            analyzer = FinBERTSentimentAnalyzer()
            results = [analyzer.analyze(t) for t in texts]
            return {"status": "success", "source": "local", "data": results}
        except Exception as e:
            logger.exception(e)
            return {"status": "error", "source": "local", "error": str(e)}

    # Embedding helpers
    def _embed_bento(self, texts: list) -> Dict[str, Any]:
        try:
            url = f"{self.bento_url}/embed_text"
            payload = {"request": {"texts": texts}}
            r = requests.post(url, json=payload, timeout=30)
            r.raise_for_status()
            return {"status": "success", "source": "bento", "data": r.json()}
        except Exception as e:
            logger.exception(e)
            return {"status": "error", "source": "bento", "error": str(e)}

    def _embed_triton(self, texts: list) -> Dict[str, Any]:
        try:
            if self._triton_client is None:
                return {"status": "error", "source": "triton", "error": "triton client not available"}
            embeddings = self._triton_client.infer_embeddings(texts)
            return {"status": "success", "source": "triton", "data": embeddings.tolist()}
        except Exception as e:
            logger.exception(e)
            return {"status": "error", "source": "triton", "error": str(e)}

    def _embed_local(self, texts: list) -> Dict[str, Any]:
        try:
            from financial_dashboard.services.chat.embed import get_embedder
            embedder = get_embedder()
            embeddings = embedder.embed_batch(texts)
            return {"status": "success", "source": "local", "data": embeddings.tolist()}
        except Exception as e:
            logger.exception(e)
            return {"status": "error", "source": "local", "error": str(e)}
