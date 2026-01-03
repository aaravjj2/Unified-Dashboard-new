"""
Triton Inference Server Client with Graceful Fallback.

This module provides a high-performance inference client that:
- Connects to Triton via gRPC or HTTP
- Falls back to local inference when Triton unavailable
- Supports batch inference with dynamic batching
- Includes health monitoring and metrics

Based on ROADMAP_ULTIMATE.md Part 2: Triton & Infrastructure
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

logger = logging.getLogger(__name__)

# ==================== CONDITIONAL IMPORTS ====================

try:
    import tritonclient.grpc.aio as grpcclient
    from tritonclient.utils import InferenceServerException
    TRITON_GRPC_AVAILABLE = True
except ImportError:
    grpcclient = None
    InferenceServerException = Exception
    TRITON_GRPC_AVAILABLE = False
    logger.info("Triton gRPC client not installed")

try:
    import tritonclient.http as httpclient
    TRITON_HTTP_AVAILABLE = True
except ImportError:
    httpclient = None
    TRITON_HTTP_AVAILABLE = False
    logger.info("Triton HTTP client not installed")

TRITON_AVAILABLE = TRITON_GRPC_AVAILABLE or TRITON_HTTP_AVAILABLE


# ==================== DATA CLASSES ====================

@dataclass
class InferenceResult:
    """Result from model inference."""
    prediction: np.ndarray
    confidence: Optional[np.ndarray] = None
    latency_ms: float = 0.0
    model_name: str = ""
    model_version: str = ""
    backend: str = "unknown"  # 'triton' or 'local'


@dataclass
class ModelMetadata:
    """Model metadata from server."""
    name: str
    version: str
    inputs: List[Dict[str, Any]]
    outputs: List[Dict[str, Any]]
    platform: str = ""
    max_batch_size: int = 0


@dataclass
class ServerHealth:
    """Server health status."""
    is_live: bool = False
    is_ready: bool = False
    models_ready: Dict[str, bool] = field(default_factory=dict)
    latency_ms: float = 0.0


# ==================== BASE CLIENT ====================

class BaseInferenceClient(ABC):
    """Abstract base class for inference clients."""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to server."""
        pass
    
    @abstractmethod
    async def predict(
        self,
        inputs: Dict[str, np.ndarray],
        model_name: str,
        model_version: str = ""
    ) -> InferenceResult:
        """Run inference."""
        pass
    
    @abstractmethod
    async def predict_batch(
        self,
        inputs_list: List[Dict[str, np.ndarray]],
        model_name: str,
        model_version: str = ""
    ) -> List[InferenceResult]:
        """Run batch inference."""
        pass
    
    @abstractmethod
    async def health_check(self) -> ServerHealth:
        """Check server health."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close connection."""
        pass


# ==================== TRITON CLIENT ====================

class TritonInferenceClient(BaseInferenceClient):
    """
    Async Triton Inference Server client.
    
    Features:
    - gRPC (preferred) or HTTP protocol
    - Dynamic batching support
    - Model ensemble support
    - Health monitoring
    - Graceful error handling
    
    Example:
        client = TritonInferenceClient("localhost:8001")
        await client.connect()
        
        result = await client.predict(
            inputs={"price_sequence": np.random.randn(60, 10).astype(np.float32)},
            model_name="lstm_forecaster"
        )
        print(f"Prediction: {result.prediction}, Latency: {result.latency_ms}ms")
    """
    
    def __init__(
        self,
        url: str = "localhost:8001",
        use_grpc: bool = True,
        timeout: float = 30.0,
        verbose: bool = False
    ):
        self.url = url
        self.use_grpc = use_grpc and TRITON_GRPC_AVAILABLE
        self.timeout = timeout
        self.verbose = verbose
        self._client: Any = None
        self._connected = False
        self._model_metadata_cache: Dict[str, ModelMetadata] = {}
    
    async def connect(self) -> bool:
        """Connect to Triton server."""
        if not TRITON_AVAILABLE:
            logger.warning("Triton client libraries not available")
            return False
        
        try:
            if self.use_grpc:
                self._client = grpcclient.InferenceServerClient(
                    url=self.url,
                    verbose=self.verbose
                )
            else:
                self._client = httpclient.InferenceServerClient(
                    url=self.url,
                    verbose=self.verbose
                )
            
            # Verify connection
            health = await self.health_check()
            if health.is_live and health.is_ready:
                self._connected = True
                logger.info(f"Connected to Triton at {self.url}")
                return True
            else:
                logger.warning(f"Triton at {self.url} not ready")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to Triton: {e}")
            return False
    
    async def health_check(self) -> ServerHealth:
        """Check Triton server health."""
        health = ServerHealth()
        start = time.perf_counter()
        
        try:
            if self.use_grpc and self._client:
                health.is_live = await self._client.is_server_live()
                health.is_ready = await self._client.is_server_ready()
            elif self._client:
                health.is_live = self._client.is_server_live()
                health.is_ready = self._client.is_server_ready()
                
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
        
        health.latency_ms = (time.perf_counter() - start) * 1000
        return health
    
    async def get_model_metadata(self, model_name: str) -> Optional[ModelMetadata]:
        """Get model metadata from server."""
        if model_name in self._model_metadata_cache:
            return self._model_metadata_cache[model_name]
        
        try:
            if self.use_grpc:
                metadata = await self._client.get_model_metadata(model_name)
            else:
                metadata = self._client.get_model_metadata(model_name)
            
            model_meta = ModelMetadata(
                name=metadata.name,
                version=metadata.versions[0] if metadata.versions else "",
                inputs=[{"name": i.name, "shape": list(i.shape), "datatype": i.datatype}
                       for i in metadata.inputs],
                outputs=[{"name": o.name, "shape": list(o.shape), "datatype": o.datatype}
                        for o in metadata.outputs],
                platform=getattr(metadata, 'platform', '')
            )
            self._model_metadata_cache[model_name] = model_meta
            return model_meta
            
        except Exception as e:
            logger.error(f"Failed to get metadata for {model_name}: {e}")
            return None
    
    async def predict(
        self,
        inputs: Dict[str, np.ndarray],
        model_name: str,
        model_version: str = ""
    ) -> InferenceResult:
        """
        Run inference on Triton server.
        
        Args:
            inputs: Dict mapping input names to numpy arrays
            model_name: Name of model in Triton repository
            model_version: Optional specific version
        
        Returns:
            InferenceResult with predictions and metadata
        """
        if not self._connected:
            raise RuntimeError("Not connected to Triton server")
        
        start = time.perf_counter()
        
        try:
            # Build inputs
            triton_inputs = []
            for name, data in inputs.items():
                # Ensure batch dimension
                if data.ndim == 1:
                    data = data.reshape(1, -1)
                elif data.ndim > 1 and data.shape[0] != 1:
                    data = data.reshape(1, *data.shape)
                
                dtype_str = self._numpy_to_triton_dtype(data.dtype)
                
                if self.use_grpc:
                    inp = grpcclient.InferInput(name, list(data.shape), dtype_str)
                    inp.set_data_from_numpy(data)
                else:
                    inp = httpclient.InferInput(name, list(data.shape), dtype_str)
                    inp.set_data_from_numpy(data)
                
                triton_inputs.append(inp)
            
            # Request outputs
            outputs = []
            if self.use_grpc:
                outputs = [grpcclient.InferRequestedOutput("price_prediction")]
                # Try to get confidence if available
                outputs.append(grpcclient.InferRequestedOutput("confidence"))
            else:
                outputs = [httpclient.InferRequestedOutput("price_prediction")]
            
            # Run inference
            if self.use_grpc:
                response = await self._client.infer(
                    model_name=model_name,
                    model_version=model_version,
                    inputs=triton_inputs,
                    outputs=outputs,
                    timeout=self.timeout
                )
            else:
                response = self._client.infer(
                    model_name=model_name,
                    model_version=model_version,
                    inputs=triton_inputs,
                    outputs=outputs
                )
            
            # Extract results
            prediction = response.as_numpy("price_prediction")
            
            try:
                confidence = response.as_numpy("confidence")
            except:
                confidence = None
            
            latency = (time.perf_counter() - start) * 1000
            
            return InferenceResult(
                prediction=prediction,
                confidence=confidence,
                latency_ms=latency,
                model_name=model_name,
                model_version=model_version or "latest",
                backend="triton"
            )
            
        except Exception as e:
            logger.error(f"Inference failed: {e}")
            raise
    
    async def predict_batch(
        self,
        inputs_list: List[Dict[str, np.ndarray]],
        model_name: str,
        model_version: str = ""
    ) -> List[InferenceResult]:
        """Run batch inference - stack inputs and run single inference."""
        if not inputs_list:
            return []
        
        # Stack all inputs
        stacked_inputs = {}
        for key in inputs_list[0].keys():
            arrays = [inp[key] for inp in inputs_list]
            stacked_inputs[key] = np.stack(arrays, axis=0)
        
        # Run inference
        result = await self.predict(stacked_inputs, model_name, model_version)
        
        # Split results back
        batch_size = len(inputs_list)
        results = []
        for i in range(batch_size):
            results.append(InferenceResult(
                prediction=result.prediction[i:i+1],
                confidence=result.confidence[i:i+1] if result.confidence is not None else None,
                latency_ms=result.latency_ms / batch_size,
                model_name=model_name,
                model_version=model_version or "latest",
                backend="triton"
            ))
        
        return results
    
    def _numpy_to_triton_dtype(self, dtype: np.dtype) -> str:
        """Convert numpy dtype to Triton dtype string."""
        dtype_map = {
            np.float32: "FP32",
            np.float64: "FP64",
            np.float16: "FP16",
            np.int32: "INT32",
            np.int64: "INT64",
            np.int16: "INT16",
            np.int8: "INT8",
            np.uint8: "UINT8",
            np.bool_: "BOOL"
        }
        return dtype_map.get(dtype.type, "FP32")
    
    async def close(self) -> None:
        """Close connection."""
        if self._client and self.use_grpc:
            try:
                await self._client.close()
            except:
                pass
        self._connected = False


# ==================== LOCAL FALLBACK CLIENT ====================

class LocalInferenceClient(BaseInferenceClient):
    """
    Local inference client for fallback when Triton unavailable.
    
    Uses models directly from financial_dashboard.models package.
    """
    
    def __init__(self):
        self._models: Dict[str, Any] = {}
        self._connected = True
    
    async def connect(self) -> bool:
        """Always returns True for local inference."""
        self._connected = True
        return True
    
    def register_model(self, name: str, model: Any) -> None:
        """Register a local model for inference."""
        self._models[name] = model
        logger.info(f"Registered local model: {name}")
    
    async def predict(
        self,
        inputs: Dict[str, np.ndarray],
        model_name: str,
        model_version: str = ""
    ) -> InferenceResult:
        """Run local inference."""
        start = time.perf_counter()
        
        model = self._models.get(model_name)
        if model is None:
            # Try to lazy-load model
            model = self._load_model(model_name)
            if model:
                self._models[model_name] = model
        
        if model is None:
            raise ValueError(f"Model not found: {model_name}")
        
        try:
            # Get the input array (usually the first/main input)
            input_data = list(inputs.values())[0]
            
            # Call model's predict method
            if hasattr(model, 'predict'):
                prediction = model.predict(input_data)
            elif hasattr(model, '__call__'):
                prediction = model(input_data)
            else:
                raise ValueError(f"Model {model_name} has no predict method")
            
            # Ensure numpy array
            if not isinstance(prediction, np.ndarray):
                prediction = np.array(prediction)
            
            latency = (time.perf_counter() - start) * 1000
            
            return InferenceResult(
                prediction=prediction,
                confidence=None,
                latency_ms=latency,
                model_name=model_name,
                model_version="local",
                backend="local"
            )
            
        except Exception as e:
            logger.error(f"Local inference failed: {e}")
            raise
    
    async def predict_batch(
        self,
        inputs_list: List[Dict[str, np.ndarray]],
        model_name: str,
        model_version: str = ""
    ) -> List[InferenceResult]:
        """Run batch inference locally."""
        results = []
        for inputs in inputs_list:
            result = await self.predict(inputs, model_name, model_version)
            results.append(result)
        return results
    
    async def health_check(self) -> ServerHealth:
        """Local is always healthy."""
        return ServerHealth(
            is_live=True,
            is_ready=True,
            models_ready={name: True for name in self._models},
            latency_ms=0.0
        )
    
    async def close(self) -> None:
        """No-op for local client."""
        pass
    
    def _load_model(self, model_name: str) -> Optional[Any]:
        """Try to load a model by name."""
        try:
            if model_name == "lstm_forecaster":
                from financial_dashboard.models.lstm_forecaster import LSTMForecaster
                return LSTMForecaster()
            elif model_name == "deep_lstm_forecaster":
                from financial_dashboard.models.deep_lstm_forecaster import DeepLSTMForecaster
                return DeepLSTMForecaster()
            elif model_name == "prophet_forecaster":
                from financial_dashboard.models.prophet_forecaster import ProphetForecaster
                return ProphetForecaster()
            elif model_name == "ensemble_forecaster":
                from financial_dashboard.models.ensemble_forecaster import EnsembleForecaster
                return EnsembleForecaster()
        except Exception as e:
            logger.warning(f"Could not load model {model_name}: {e}")
        return None


# ==================== UNIFIED CLIENT WITH FALLBACK ====================

class UnifiedInferenceClient:
    """
    Unified inference client with automatic Triton/Local fallback.
    
    Attempts Triton first, falls back to local inference if unavailable.
    
    Example:
        client = UnifiedInferenceClient(triton_url="localhost:8001")
        await client.connect()
        
        result = await client.predict(
            inputs={"price_sequence": data},
            model_name="lstm_forecaster"
        )
        print(f"Backend: {result.backend}, Latency: {result.latency_ms}ms")
    """
    
    def __init__(
        self,
        triton_url: str = "localhost:8001",
        use_grpc: bool = True,
        prefer_triton: bool = True,
        timeout: float = 30.0
    ):
        self.triton_url = triton_url
        self.use_grpc = use_grpc
        self.prefer_triton = prefer_triton
        self.timeout = timeout
        
        self._triton_client: Optional[TritonInferenceClient] = None
        self._local_client = LocalInferenceClient()
        self._active_client: BaseInferenceClient = self._local_client
        self._using_triton = False
    
    async def connect(self) -> bool:
        """
        Connect to best available backend.
        
        Tries Triton first if preferred, falls back to local.
        """
        # Always init local client
        await self._local_client.connect()
        
        if self.prefer_triton and TRITON_AVAILABLE:
            self._triton_client = TritonInferenceClient(
                url=self.triton_url,
                use_grpc=self.use_grpc,
                timeout=self.timeout
            )
            
            if await self._triton_client.connect():
                self._active_client = self._triton_client
                self._using_triton = True
                logger.info("Using Triton inference backend")
                return True
            else:
                logger.info("Triton unavailable, using local inference")
        
        self._active_client = self._local_client
        self._using_triton = False
        logger.info("Using local inference backend")
        return True
    
    async def predict(
        self,
        inputs: Dict[str, np.ndarray],
        model_name: str,
        model_version: str = ""
    ) -> InferenceResult:
        """
        Run inference on active backend.
        
        Falls back to local if Triton fails.
        """
        try:
            return await self._active_client.predict(inputs, model_name, model_version)
        except Exception as e:
            if self._using_triton:
                logger.warning(f"Triton inference failed, falling back to local: {e}")
                return await self._local_client.predict(inputs, model_name, model_version)
            raise
    
    async def predict_batch(
        self,
        inputs_list: List[Dict[str, np.ndarray]],
        model_name: str,
        model_version: str = ""
    ) -> List[InferenceResult]:
        """Run batch inference."""
        try:
            return await self._active_client.predict_batch(inputs_list, model_name, model_version)
        except Exception as e:
            if self._using_triton:
                logger.warning(f"Triton batch inference failed, falling back to local: {e}")
                return await self._local_client.predict_batch(inputs_list, model_name, model_version)
            raise
    
    async def health_check(self) -> ServerHealth:
        """Get health of active backend."""
        return await self._active_client.health_check()
    
    def register_local_model(self, name: str, model: Any) -> None:
        """Register a model for local fallback."""
        self._local_client.register_model(name, model)
    
    @property
    def backend(self) -> str:
        """Return current backend name."""
        return "triton" if self._using_triton else "local"
    
    async def close(self) -> None:
        """Close all connections."""
        if self._triton_client:
            await self._triton_client.close()
        await self._local_client.close()


# ==================== ENSEMBLE CLIENT ====================

class EnsembleInferenceClient:
    """
    Client for model ensemble inference.
    
    Runs multiple models and combines predictions with configurable weights.
    """
    
    def __init__(self, client: UnifiedInferenceClient):
        self.client = client
        self.model_weights: Dict[str, float] = {
            "lstm_forecaster": 0.4,
            "prophet_forecaster": 0.3,
            "arima_forecaster": 0.3
        }
    
    async def predict_ensemble(
        self,
        inputs: Dict[str, np.ndarray],
        models: List[str] = None,
        weights: Dict[str, float] = None
    ) -> Dict[str, Any]:
        """
        Run ensemble prediction across multiple models.
        
        Args:
            inputs: Input data for all models
            models: List of model names to use
            weights: Custom weights for each model
        
        Returns:
            Dict with individual predictions and weighted ensemble
        """
        models = models or list(self.model_weights.keys())
        weights = weights or self.model_weights
        
        results = {}
        successful_models = []
        
        # Run all models
        tasks = []
        for model_name in models:
            tasks.append((model_name, self.client.predict(inputs, model_name)))
        
        for model_name, task in tasks:
            try:
                result = await task
                results[model_name] = {
                    "prediction": float(result.prediction.flatten()[0]),
                    "confidence": float(result.confidence.flatten()[0]) if result.confidence is not None else None,
                    "latency_ms": result.latency_ms,
                    "backend": result.backend
                }
                successful_models.append(model_name)
            except Exception as e:
                logger.warning(f"Model {model_name} failed: {e}")
                results[model_name] = {"error": str(e)}
        
        # Compute weighted ensemble
        if successful_models:
            total_weight = sum(weights.get(m, 1.0) for m in successful_models)
            ensemble_pred = sum(
                results[m]["prediction"] * weights.get(m, 1.0) / total_weight
                for m in successful_models
            )
            results["ensemble"] = {
                "prediction": ensemble_pred,
                "models_used": successful_models,
                "weights": {m: weights.get(m, 1.0) / total_weight for m in successful_models}
            }
        
        return results


# ==================== CONVENIENCE FUNCTIONS ====================

async def create_inference_client(
    triton_url: str = "localhost:8001",
    prefer_triton: bool = True
) -> UnifiedInferenceClient:
    """
    Create and connect a unified inference client.
    
    Example:
        client = await create_inference_client()
        result = await client.predict(inputs, "lstm_forecaster")
    """
    client = UnifiedInferenceClient(
        triton_url=triton_url,
        prefer_triton=prefer_triton
    )
    await client.connect()
    return client


def get_triton_availability() -> Dict[str, bool]:
    """Check what Triton components are available."""
    return {
        "triton_available": TRITON_AVAILABLE,
        "grpc_available": TRITON_GRPC_AVAILABLE,
        "http_available": TRITON_HTTP_AVAILABLE
    }
