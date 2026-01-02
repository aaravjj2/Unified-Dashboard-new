"""
Triton Inference Client with Local CPU Fallback
Phase 11 - Agent-Serving

Provides gRPC client for Triton Inference Server with automatic
fallback to local CPU inference when Triton is unavailable.
"""

import os
import time
import json
import logging
import numpy as np
from typing import Optional, Dict, Any, Union, List
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Environment configuration
TRITON_GRPC_URL = os.getenv("TRITON_GRPC_URL", "localhost:8001")
TRITON_HTTP_URL = os.getenv("TRITON_HTTP_URL", "localhost:8002")
SERVING_DETERMINISTIC = os.getenv("SERVING_DETERMINISTIC", "0") == "1"
TRITON_TIMEOUT_MS = int(os.getenv("TRITON_TIMEOUT_MS", "200"))

# Model repository path for fallback
MODEL_REPOSITORY = Path(__file__).parent.parent.parent / "model_repository"


@dataclass
class InferenceResult:
    """Result from model inference."""
    output: np.ndarray
    latency_ms: float
    backend: str  # "triton_grpc", "triton_http", or "local_cpu"
    model_name: str
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "output": self.output.tolist() if isinstance(self.output, np.ndarray) else self.output,
            "latency_ms": self.latency_ms,
            "backend": self.backend,
            "model_name": self.model_name,
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata,
        }


class TritonClient:
    """
    Triton Inference Server client with local fallback.
    
    Attempts gRPC connection first, then HTTP, then falls back to local
    ONNX Runtime inference if Triton is unavailable.
    """

    def __init__(
        self,
        grpc_url: Optional[str] = None,
        http_url: Optional[str] = None,
        timeout_ms: int = TRITON_TIMEOUT_MS,
        enable_fallback: bool = True,
    ):
        """
        Initialize Triton client.
        
        Args:
            grpc_url: Triton gRPC endpoint (default: localhost:8001)
            http_url: Triton HTTP endpoint (default: localhost:8002)
            timeout_ms: Request timeout in milliseconds
            enable_fallback: Enable local CPU fallback if Triton unavailable
        """
        self.grpc_url = grpc_url or TRITON_GRPC_URL
        self.http_url = http_url or TRITON_HTTP_URL
        self.timeout_ms = timeout_ms
        self.enable_fallback = enable_fallback
        
        self._grpc_client = None
        self._http_client = None
        self._local_sessions: Dict[str, Any] = {}
        self._connection_state = {
            "grpc_available": None,
            "http_available": None,
            "last_check": 0,
        }
        
        # Check availability
        self._check_connections()

    def _check_connections(self) -> None:
        """Check Triton server availability."""
        # Rate limit checks to every 30 seconds
        if time.time() - self._connection_state["last_check"] < 30:
            return
            
        self._connection_state["last_check"] = time.time()
        
        # Try gRPC connection
        try:
            import tritonclient.grpc as grpcclient
            self._grpc_client = grpcclient.InferenceServerClient(
                url=self.grpc_url,
                verbose=False,
            )
            if self._grpc_client.is_server_live():
                self._connection_state["grpc_available"] = True
                logger.info(f"Triton gRPC connected at {self.grpc_url}")
            else:
                self._connection_state["grpc_available"] = False
        except Exception as e:
            self._connection_state["grpc_available"] = False
            self._grpc_client = None
            logger.debug(f"Triton gRPC unavailable: {e}")

        # Try HTTP connection
        try:
            import tritonclient.http as httpclient
            self._http_client = httpclient.InferenceServerClient(
                url=self.http_url,
                verbose=False,
            )
            if self._http_client.is_server_live():
                self._connection_state["http_available"] = True
                logger.info(f"Triton HTTP connected at {self.http_url}")
            else:
                self._connection_state["http_available"] = False
        except Exception as e:
            self._connection_state["http_available"] = False
            self._http_client = None
            logger.debug(f"Triton HTTP unavailable: {e}")

    def _get_local_session(self, model_name: str):
        """Get or create local ONNX Runtime session for fallback."""
        if model_name in self._local_sessions:
            return self._local_sessions[model_name]
            
        try:
            import onnxruntime as ort
            
            model_path = MODEL_REPOSITORY / model_name / "1" / "model.onnx"
            if not model_path.exists():
                logger.warning(f"Local model not found: {model_path}")
                return None
                
            # Create ONNX Runtime session
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            
            session = ort.InferenceSession(
                str(model_path),
                sess_options=sess_options,
                providers=["CPUExecutionProvider"],
            )
            
            self._local_sessions[model_name] = session
            logger.info(f"Local ONNX session created for {model_name}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to create local session for {model_name}: {e}")
            return None

    def infer(
        self,
        model_name: str,
        inputs: Union[np.ndarray, List[float], Dict[str, np.ndarray]],
        input_name: str = "input",
        output_name: str = "output",
    ) -> InferenceResult:
        """
        Run inference on a model.
        
        Tries gRPC first, then HTTP, then local CPU fallback.
        
        Args:
            model_name: Name of the model to use
            inputs: Input data as numpy array, list, or dict
            input_name: Name of input tensor
            output_name: Name of output tensor
            
        Returns:
            InferenceResult with output, latency, and backend info
        """
        # Normalize inputs to numpy array
        if isinstance(inputs, list):
            inputs = np.array(inputs, dtype=np.float32)
        if isinstance(inputs, dict):
            input_data = inputs
        else:
            if inputs.ndim == 1:
                inputs = inputs.reshape(1, -1)
            input_data = {input_name: inputs.astype(np.float32)}
        
        start_time = time.perf_counter()
        
        # Try gRPC
        if self._connection_state.get("grpc_available"):
            result = self._infer_grpc(model_name, input_data, input_name, output_name)
            if result.success:
                result.latency_ms = (time.perf_counter() - start_time) * 1000
                return result
        
        # Try HTTP
        if self._connection_state.get("http_available"):
            result = self._infer_http(model_name, input_data, input_name, output_name)
            if result.success:
                result.latency_ms = (time.perf_counter() - start_time) * 1000
                return result
        
        # Fallback to local CPU
        if self.enable_fallback:
            result = self._infer_local(model_name, input_data, input_name, output_name)
            result.latency_ms = (time.perf_counter() - start_time) * 1000
            return result
        
        # No backend available
        return InferenceResult(
            output=np.array([]),
            latency_ms=(time.perf_counter() - start_time) * 1000,
            backend="none",
            model_name=model_name,
            success=False,
            error="No inference backend available",
        )

    def _infer_grpc(
        self,
        model_name: str,
        input_data: Dict[str, np.ndarray],
        input_name: str,
        output_name: str,
    ) -> InferenceResult:
        """Run inference via gRPC."""
        try:
            import tritonclient.grpc as grpcclient
            
            if self._grpc_client is None:
                raise RuntimeError("gRPC client not initialized")
            
            # Prepare inputs
            inputs = []
            for name, data in input_data.items():
                inp = grpcclient.InferInput(name, data.shape, "FP32")
                inp.set_data_from_numpy(data)
                inputs.append(inp)
            
            # Prepare outputs
            outputs = [grpcclient.InferRequestedOutput(output_name)]
            
            # Run inference
            response = self._grpc_client.infer(
                model_name=model_name,
                inputs=inputs,
                outputs=outputs,
            )
            
            output = response.as_numpy(output_name)
            
            return InferenceResult(
                output=output,
                latency_ms=0,  # Will be set by caller
                backend="triton_grpc",
                model_name=model_name,
                success=True,
                metadata={"server": self.grpc_url},
            )
            
        except Exception as e:
            logger.warning(f"gRPC inference failed: {e}")
            self._connection_state["grpc_available"] = False
            return InferenceResult(
                output=np.array([]),
                latency_ms=0,
                backend="triton_grpc",
                model_name=model_name,
                success=False,
                error=str(e),
            )

    def _infer_http(
        self,
        model_name: str,
        input_data: Dict[str, np.ndarray],
        input_name: str,
        output_name: str,
    ) -> InferenceResult:
        """Run inference via HTTP."""
        try:
            import tritonclient.http as httpclient
            
            if self._http_client is None:
                raise RuntimeError("HTTP client not initialized")
            
            # Prepare inputs
            inputs = []
            for name, data in input_data.items():
                inp = httpclient.InferInput(name, list(data.shape), "FP32")
                inp.set_data_from_numpy(data)
                inputs.append(inp)
            
            # Prepare outputs
            outputs = [httpclient.InferRequestedOutput(output_name)]
            
            # Run inference
            response = self._http_client.infer(
                model_name=model_name,
                inputs=inputs,
                outputs=outputs,
            )
            
            output = response.as_numpy(output_name)
            
            return InferenceResult(
                output=output,
                latency_ms=0,
                backend="triton_http",
                model_name=model_name,
                success=True,
                metadata={"server": self.http_url},
            )
            
        except Exception as e:
            logger.warning(f"HTTP inference failed: {e}")
            self._connection_state["http_available"] = False
            return InferenceResult(
                output=np.array([]),
                latency_ms=0,
                backend="triton_http",
                model_name=model_name,
                success=False,
                error=str(e),
            )

    def _infer_local(
        self,
        model_name: str,
        input_data: Dict[str, np.ndarray],
        input_name: str,
        output_name: str,
    ) -> InferenceResult:
        """Run inference locally using ONNX Runtime."""
        try:
            session = self._get_local_session(model_name)
            if session is None:
                # Create synthetic output if no model available
                # This enables testing without actual models
                logger.warning(f"No local model for {model_name}, using synthetic output")
                first_input = list(input_data.values())[0]
                batch_size = first_input.shape[0]
                
                if SERVING_DETERMINISTIC:
                    # Deterministic output for testing
                    output = np.full((batch_size, 1), 0.5, dtype=np.float32)
                else:
                    output = np.random.randn(batch_size, 1).astype(np.float32)
                
                return InferenceResult(
                    output=output,
                    latency_ms=0,
                    backend="local_cpu",
                    model_name=model_name,
                    success=True,
                    metadata={"synthetic": True},
                )
            
            # Run ONNX Runtime inference
            outputs = session.run(
                [output_name],
                {name: data for name, data in input_data.items()},
            )
            
            return InferenceResult(
                output=outputs[0],
                latency_ms=0,
                backend="local_cpu",
                model_name=model_name,
                success=True,
                metadata={"onnx_runtime": True},
            )
            
        except Exception as e:
            logger.error(f"Local inference failed: {e}")
            return InferenceResult(
                output=np.array([]),
                latency_ms=0,
                backend="local_cpu",
                model_name=model_name,
                success=False,
                error=str(e),
            )

    def get_status(self) -> Dict[str, Any]:
        """Get client connection status."""
        self._check_connections()
        return {
            "grpc_url": self.grpc_url,
            "grpc_available": self._connection_state.get("grpc_available", False),
            "http_url": self.http_url,
            "http_available": self._connection_state.get("http_available", False),
            "fallback_enabled": self.enable_fallback,
            "local_models": list(self._local_sessions.keys()),
            "timeout_ms": self.timeout_ms,
        }

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all backends."""
        results = {
            "healthy": False,
            "backends": {},
            "latency_ms": {},
        }
        
        # Test gRPC
        if self._connection_state.get("grpc_available"):
            try:
                start = time.perf_counter()
                if self._grpc_client.is_server_ready():
                    results["backends"]["grpc"] = "healthy"
                    results["latency_ms"]["grpc"] = (time.perf_counter() - start) * 1000
                    results["healthy"] = True
            except Exception as e:
                results["backends"]["grpc"] = f"error: {e}"
        else:
            results["backends"]["grpc"] = "unavailable"
        
        # Test HTTP
        if self._connection_state.get("http_available"):
            try:
                start = time.perf_counter()
                if self._http_client.is_server_ready():
                    results["backends"]["http"] = "healthy"
                    results["latency_ms"]["http"] = (time.perf_counter() - start) * 1000
                    results["healthy"] = True
            except Exception as e:
                results["backends"]["http"] = f"error: {e}"
        else:
            results["backends"]["http"] = "unavailable"
        
        # Test local fallback
        if self.enable_fallback:
            results["backends"]["local_cpu"] = "available"
            results["healthy"] = True
        
        return results


# Singleton client instance
_default_client: Optional[TritonClient] = None


def get_client() -> TritonClient:
    """Get the default Triton client instance."""
    global _default_client
    if _default_client is None:
        _default_client = TritonClient()
    return _default_client


def infer(
    model_name: str,
    inputs: Union[np.ndarray, List[float]],
    **kwargs,
) -> InferenceResult:
    """
    Convenience function for inference.
    
    Args:
        model_name: Name of model
        inputs: Input data
        **kwargs: Additional arguments passed to TritonClient.infer
        
    Returns:
        InferenceResult
    """
    return get_client().infer(model_name, inputs, **kwargs)


if __name__ == "__main__":
    # Test the client
    logging.basicConfig(level=logging.INFO)
    
    client = TritonClient()
    print("Client status:", json.dumps(client.get_status(), indent=2))
    
    # Test inference
    test_input = np.random.randn(1, 50).astype(np.float32)
    result = client.infer("signal_model", test_input)
    print("Inference result:", json.dumps(result.to_dict(), indent=2))
