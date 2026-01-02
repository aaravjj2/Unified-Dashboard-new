"""
Model Conversion Utilities for Triton Deployment.

This module provides tools to convert models to deployment formats:
- PyTorch -> ONNX
- Keras/TensorFlow -> ONNX
- ONNX -> TensorRT (GPU optimization)
- Benchmarking utilities

Based on ROADMAP_ULTIMATE.md Part 2: Triton & Infrastructure
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)

# ==================== CONDITIONAL IMPORTS ====================

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    nn = None
    TORCH_AVAILABLE = False
    logger.info("PyTorch not available for model conversion")

try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    tf = None
    TF_AVAILABLE = False
    logger.info("TensorFlow not available for model conversion")

try:
    import onnx
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    onnx = None
    ort = None
    ONNX_AVAILABLE = False
    logger.info("ONNX/ONNXRuntime not available")

try:
    import tf2onnx
    TF2ONNX_AVAILABLE = True
except ImportError:
    tf2onnx = None
    TF2ONNX_AVAILABLE = False

try:
    import tensorrt as trt
    TENSORRT_AVAILABLE = True
except ImportError:
    trt = None
    TENSORRT_AVAILABLE = False
    logger.info("TensorRT not available for GPU optimization")


# ==================== DATA CLASSES ====================

@dataclass
class ConversionResult:
    """Result of model conversion."""
    success: bool
    output_path: str
    source_format: str
    target_format: str
    input_shapes: Dict[str, List[int]]
    output_shapes: Dict[str, List[int]]
    file_size_mb: float
    error: Optional[str] = None


@dataclass
class BenchmarkResult:
    """Result of inference benchmark."""
    mean_latency_ms: float
    std_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    throughput_per_sec: float
    batch_size: int
    n_runs: int
    device: str


@dataclass
class TritonModelConfig:
    """Triton model configuration."""
    name: str
    platform: str  # "pytorch_libtorch", "onnxruntime_onnx", "tensorrt_plan"
    max_batch_size: int
    inputs: List[Dict[str, Any]]
    outputs: List[Dict[str, Any]]
    dynamic_batching: bool = True
    instance_groups: List[Dict[str, Any]] = None


# ==================== PYTORCH CONVERSION ====================

class PyTorchConverter:
    """
    Convert PyTorch models to ONNX format.
    
    Example:
        converter = PyTorchConverter()
        result = converter.to_onnx(
            model=my_model,
            input_shapes={"input": (1, 60, 10)},
            output_path="model.onnx"
        )
    """
    
    @staticmethod
    def to_onnx(
        model: "torch.nn.Module",
        input_shapes: Dict[str, Tuple[int, ...]],
        output_path: str,
        input_names: List[str] = None,
        output_names: List[str] = None,
        opset_version: int = 14,
        dynamic_axes: Dict[str, Dict[int, str]] = None
    ) -> ConversionResult:
        """
        Convert PyTorch model to ONNX.
        
        Args:
            model: PyTorch model
            input_shapes: Dict of input name -> shape
            output_path: Path to save ONNX model
            input_names: Optional input names (defaults to dict keys)
            output_names: Optional output names
            opset_version: ONNX opset version
            dynamic_axes: Dynamic axes for variable batch size
        
        Returns:
            ConversionResult with status and metadata
        """
        if not TORCH_AVAILABLE:
            return ConversionResult(
                success=False,
                output_path=output_path,
                source_format="pytorch",
                target_format="onnx",
                input_shapes={},
                output_shapes={},
                file_size_mb=0,
                error="PyTorch not available"
            )
        
        if not ONNX_AVAILABLE:
            return ConversionResult(
                success=False,
                output_path=output_path,
                source_format="pytorch",
                target_format="onnx",
                input_shapes={},
                output_shapes={},
                file_size_mb=0,
                error="ONNX not available"
            )
        
        try:
            model.eval()
            
            # Create dummy inputs
            dummy_inputs = []
            input_names = input_names or list(input_shapes.keys())
            
            for name in input_names:
                shape = input_shapes[name]
                if 'int' in name.lower() or 'id' in name.lower():
                    dummy_inputs.append(torch.randint(0, 100, shape))
                else:
                    dummy_inputs.append(torch.randn(*shape))
            
            # Default dynamic axes for batch dimension
            if dynamic_axes is None:
                dynamic_axes = {name: {0: 'batch_size'} for name in input_names}
            
            # Output names
            output_names = output_names or ['output']
            
            # Export
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            
            torch.onnx.export(
                model,
                tuple(dummy_inputs) if len(dummy_inputs) > 1 else dummy_inputs[0],
                output_path,
                input_names=input_names,
                output_names=output_names,
                dynamic_axes=dynamic_axes,
                opset_version=opset_version,
                do_constant_folding=True
            )
            
            # Verify
            onnx_model = onnx.load(output_path)
            onnx.checker.check_model(onnx_model)
            
            # Get output shapes
            output_shapes = {}
            for output in onnx_model.graph.output:
                dims = [d.dim_value for d in output.type.tensor_type.shape.dim]
                output_shapes[output.name] = dims
            
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            
            logger.info(f"PyTorch -> ONNX conversion successful: {output_path}")
            
            return ConversionResult(
                success=True,
                output_path=output_path,
                source_format="pytorch",
                target_format="onnx",
                input_shapes=input_shapes,
                output_shapes=output_shapes,
                file_size_mb=file_size
            )
            
        except Exception as e:
            logger.error(f"PyTorch -> ONNX conversion failed: {e}")
            return ConversionResult(
                success=False,
                output_path=output_path,
                source_format="pytorch",
                target_format="onnx",
                input_shapes=input_shapes,
                output_shapes={},
                file_size_mb=0,
                error=str(e)
            )
    
    @staticmethod
    def to_torchscript(
        model: "torch.nn.Module",
        output_path: str,
        example_input: "torch.Tensor" = None,
        method: str = "trace"  # "trace" or "script"
    ) -> ConversionResult:
        """
        Convert PyTorch model to TorchScript for C++ deployment.
        
        Args:
            model: PyTorch model
            output_path: Path to save .pt file
            example_input: Example input for tracing
            method: "trace" or "script"
        """
        if not TORCH_AVAILABLE:
            return ConversionResult(
                success=False,
                output_path=output_path,
                source_format="pytorch",
                target_format="torchscript",
                input_shapes={},
                output_shapes={},
                file_size_mb=0,
                error="PyTorch not available"
            )
        
        try:
            model.eval()
            
            if method == "trace":
                if example_input is None:
                    raise ValueError("example_input required for tracing")
                scripted = torch.jit.trace(model, example_input)
            else:
                scripted = torch.jit.script(model)
            
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            scripted.save(output_path)
            
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            
            return ConversionResult(
                success=True,
                output_path=output_path,
                source_format="pytorch",
                target_format="torchscript",
                input_shapes={},
                output_shapes={},
                file_size_mb=file_size
            )
            
        except Exception as e:
            logger.error(f"TorchScript conversion failed: {e}")
            return ConversionResult(
                success=False,
                output_path=output_path,
                source_format="pytorch",
                target_format="torchscript",
                input_shapes={},
                output_shapes={},
                file_size_mb=0,
                error=str(e)
            )


# ==================== TENSORFLOW CONVERSION ====================

class TensorFlowConverter:
    """
    Convert TensorFlow/Keras models to ONNX format.
    """
    
    @staticmethod
    def to_onnx(
        model: "tf.keras.Model",
        output_path: str,
        opset_version: int = 14
    ) -> ConversionResult:
        """
        Convert Keras model to ONNX.
        
        Args:
            model: Keras/TF model
            output_path: Path to save ONNX model
            opset_version: ONNX opset version
        """
        if not TF_AVAILABLE:
            return ConversionResult(
                success=False,
                output_path=output_path,
                source_format="tensorflow",
                target_format="onnx",
                input_shapes={},
                output_shapes={},
                file_size_mb=0,
                error="TensorFlow not available"
            )
        
        if not TF2ONNX_AVAILABLE:
            return ConversionResult(
                success=False,
                output_path=output_path,
                source_format="tensorflow",
                target_format="onnx",
                input_shapes={},
                output_shapes={},
                file_size_mb=0,
                error="tf2onnx not available"
            )
        
        try:
            # Get input spec
            input_shapes = {}
            if hasattr(model, 'input_shape'):
                if isinstance(model.input_shape, list):
                    for i, shape in enumerate(model.input_shape):
                        input_shapes[f"input_{i}"] = list(shape)
                else:
                    input_shapes["input"] = list(model.input_shape)
            
            # Convert
            spec = (tf.TensorSpec(model.input_shape, tf.float32, name="input"),)
            
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            
            model_proto, _ = tf2onnx.convert.from_keras(
                model,
                input_signature=spec,
                opset=opset_version,
                output_path=output_path
            )
            
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            
            # Get output shapes
            output_shapes = {}
            onnx_model = onnx.load(output_path)
            for output in onnx_model.graph.output:
                dims = [d.dim_value for d in output.type.tensor_type.shape.dim]
                output_shapes[output.name] = dims
            
            return ConversionResult(
                success=True,
                output_path=output_path,
                source_format="tensorflow",
                target_format="onnx",
                input_shapes=input_shapes,
                output_shapes=output_shapes,
                file_size_mb=file_size
            )
            
        except Exception as e:
            logger.error(f"TensorFlow -> ONNX conversion failed: {e}")
            return ConversionResult(
                success=False,
                output_path=output_path,
                source_format="tensorflow",
                target_format="onnx",
                input_shapes={},
                output_shapes={},
                file_size_mb=0,
                error=str(e)
            )
    
    @staticmethod
    def to_savedmodel(
        model: "tf.keras.Model",
        output_path: str
    ) -> ConversionResult:
        """Save Keras model as TensorFlow SavedModel."""
        if not TF_AVAILABLE:
            return ConversionResult(
                success=False,
                output_path=output_path,
                source_format="keras",
                target_format="savedmodel",
                input_shapes={},
                output_shapes={},
                file_size_mb=0,
                error="TensorFlow not available"
            )
        
        try:
            os.makedirs(output_path, exist_ok=True)
            model.save(output_path)
            
            # Calculate total size
            total_size = sum(
                f.stat().st_size for f in Path(output_path).rglob('*') if f.is_file()
            ) / (1024 * 1024)
            
            return ConversionResult(
                success=True,
                output_path=output_path,
                source_format="keras",
                target_format="savedmodel",
                input_shapes={},
                output_shapes={},
                file_size_mb=total_size
            )
            
        except Exception as e:
            return ConversionResult(
                success=False,
                output_path=output_path,
                source_format="keras",
                target_format="savedmodel",
                input_shapes={},
                output_shapes={},
                file_size_mb=0,
                error=str(e)
            )


# ==================== TENSORRT OPTIMIZATION ====================

class TensorRTOptimizer:
    """
    Optimize ONNX models with TensorRT for GPU inference.
    """
    
    @staticmethod
    def optimize(
        onnx_path: str,
        output_path: str,
        fp16: bool = True,
        int8: bool = False,
        max_batch_size: int = 64,
        workspace_size_gb: float = 1.0
    ) -> ConversionResult:
        """
        Optimize ONNX model with TensorRT.
        
        Args:
            onnx_path: Path to ONNX model
            output_path: Path to save TensorRT engine
            fp16: Enable FP16 precision
            int8: Enable INT8 quantization
            max_batch_size: Maximum batch size for optimization
            workspace_size_gb: Workspace size in GB
        """
        if not TENSORRT_AVAILABLE:
            return ConversionResult(
                success=False,
                output_path=output_path,
                source_format="onnx",
                target_format="tensorrt",
                input_shapes={},
                output_shapes={},
                file_size_mb=0,
                error="TensorRT not available"
            )
        
        try:
            TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
            
            with trt.Builder(TRT_LOGGER) as builder:
                network_flags = 1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
                
                with builder.create_network(network_flags) as network:
                    with trt.OnnxParser(network, TRT_LOGGER) as parser:
                        # Read ONNX
                        with open(onnx_path, 'rb') as f:
                            if not parser.parse(f.read()):
                                errors = []
                                for i in range(parser.num_errors):
                                    errors.append(str(parser.get_error(i)))
                                return ConversionResult(
                                    success=False,
                                    output_path=output_path,
                                    source_format="onnx",
                                    target_format="tensorrt",
                                    input_shapes={},
                                    output_shapes={},
                                    file_size_mb=0,
                                    error="\n".join(errors)
                                )
                        
                        # Configure
                        config = builder.create_builder_config()
                        config.set_memory_pool_limit(
                            trt.MemoryPoolType.WORKSPACE,
                            int(workspace_size_gb * (1 << 30))
                        )
                        
                        if fp16 and builder.platform_has_fast_fp16:
                            config.set_flag(trt.BuilderFlag.FP16)
                        
                        if int8 and builder.platform_has_fast_int8:
                            config.set_flag(trt.BuilderFlag.INT8)
                        
                        # Optimization profile
                        profile = builder.create_optimization_profile()
                        
                        for i in range(network.num_inputs):
                            inp = network.get_input(i)
                            shape = list(inp.shape)
                            
                            # Replace -1 (dynamic) with actual sizes
                            min_shape = [1 if s == -1 else s for s in shape]
                            opt_shape = [max_batch_size // 2 if s == -1 else s for s in shape]
                            max_shape = [max_batch_size if s == -1 else s for s in shape]
                            
                            profile.set_shape(inp.name, min_shape, opt_shape, max_shape)
                        
                        config.add_optimization_profile(profile)
                        
                        # Build engine
                        engine = builder.build_serialized_network(network, config)
                        
                        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
                        with open(output_path, 'wb') as f:
                            f.write(engine)
                        
                        file_size = os.path.getsize(output_path) / (1024 * 1024)
                        
                        return ConversionResult(
                            success=True,
                            output_path=output_path,
                            source_format="onnx",
                            target_format="tensorrt",
                            input_shapes={},
                            output_shapes={},
                            file_size_mb=file_size
                        )
            
        except Exception as e:
            logger.error(f"TensorRT optimization failed: {e}")
            return ConversionResult(
                success=False,
                output_path=output_path,
                source_format="onnx",
                target_format="tensorrt",
                input_shapes={},
                output_shapes={},
                file_size_mb=0,
                error=str(e)
            )


# ==================== ONNX UTILITIES ====================

class ONNXUtils:
    """Utilities for ONNX models."""
    
    @staticmethod
    def verify(onnx_path: str) -> Tuple[bool, Optional[str]]:
        """
        Verify ONNX model is valid.
        
        Returns:
            (is_valid, error_message)
        """
        if not ONNX_AVAILABLE:
            return False, "ONNX not available"
        
        try:
            model = onnx.load(onnx_path)
            onnx.checker.check_model(model)
            return True, None
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def get_metadata(onnx_path: str) -> Dict[str, Any]:
        """Get ONNX model metadata."""
        if not ONNX_AVAILABLE:
            return {"error": "ONNX not available"}
        
        try:
            model = onnx.load(onnx_path)
            
            inputs = []
            for inp in model.graph.input:
                dims = [d.dim_value if d.dim_value else -1 
                       for d in inp.type.tensor_type.shape.dim]
                inputs.append({
                    "name": inp.name,
                    "shape": dims,
                    "dtype": onnx.TensorProto.DataType.Name(inp.type.tensor_type.elem_type)
                })
            
            outputs = []
            for out in model.graph.output:
                dims = [d.dim_value if d.dim_value else -1
                       for d in out.type.tensor_type.shape.dim]
                outputs.append({
                    "name": out.name,
                    "shape": dims,
                    "dtype": onnx.TensorProto.DataType.Name(out.type.tensor_type.elem_type)
                })
            
            return {
                "ir_version": model.ir_version,
                "opset_version": model.opset_import[0].version if model.opset_import else None,
                "producer_name": model.producer_name,
                "inputs": inputs,
                "outputs": outputs,
                "num_nodes": len(model.graph.node)
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def simplify(onnx_path: str, output_path: str = None) -> ConversionResult:
        """
        Simplify ONNX model (constant folding, etc.).
        
        Requires onnx-simplifier package.
        """
        try:
            from onnxsim import simplify
            
            model = onnx.load(onnx_path)
            simplified, ok = simplify(model)
            
            if not ok:
                return ConversionResult(
                    success=False,
                    output_path=output_path or onnx_path,
                    source_format="onnx",
                    target_format="onnx",
                    input_shapes={},
                    output_shapes={},
                    file_size_mb=0,
                    error="Simplification failed"
                )
            
            output = output_path or onnx_path
            onnx.save(simplified, output)
            
            file_size = os.path.getsize(output) / (1024 * 1024)
            
            return ConversionResult(
                success=True,
                output_path=output,
                source_format="onnx",
                target_format="onnx_simplified",
                input_shapes={},
                output_shapes={},
                file_size_mb=file_size
            )
            
        except ImportError:
            return ConversionResult(
                success=False,
                output_path=output_path or onnx_path,
                source_format="onnx",
                target_format="onnx_simplified",
                input_shapes={},
                output_shapes={},
                file_size_mb=0,
                error="onnx-simplifier not installed"
            )
        except Exception as e:
            return ConversionResult(
                success=False,
                output_path=output_path or onnx_path,
                source_format="onnx",
                target_format="onnx_simplified",
                input_shapes={},
                output_shapes={},
                file_size_mb=0,
                error=str(e)
            )


# ==================== BENCHMARKING ====================

class ModelBenchmark:
    """Benchmark model inference performance."""
    
    @staticmethod
    def benchmark_onnx(
        onnx_path: str,
        input_shapes: Dict[str, Tuple[int, ...]],
        n_runs: int = 100,
        warmup_runs: int = 10,
        use_gpu: bool = True
    ) -> BenchmarkResult:
        """
        Benchmark ONNX model inference.
        
        Args:
            onnx_path: Path to ONNX model
            input_shapes: Dict of input name -> shape
            n_runs: Number of benchmark runs
            warmup_runs: Number of warmup runs
            use_gpu: Use GPU if available
        """
        if not ONNX_AVAILABLE:
            return BenchmarkResult(
                mean_latency_ms=0,
                std_latency_ms=0,
                min_latency_ms=0,
                max_latency_ms=0,
                throughput_per_sec=0,
                batch_size=1,
                n_runs=0,
                device="none"
            )
        
        # Select providers
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if use_gpu else ['CPUExecutionProvider']
        
        try:
            session = ort.InferenceSession(onnx_path, providers=providers)
            device = session.get_providers()[0]
            
            # Create inputs
            inputs = {}
            batch_size = 1
            for name, shape in input_shapes.items():
                batch_size = shape[0] if shape else 1
                if 'int' in name.lower():
                    inputs[name] = np.random.randint(0, 100, shape).astype(np.int32)
                else:
                    inputs[name] = np.random.randn(*shape).astype(np.float32)
            
            # Warmup
            for _ in range(warmup_runs):
                session.run(None, inputs)
            
            # Benchmark
            latencies = []
            for _ in range(n_runs):
                start = time.perf_counter()
                session.run(None, inputs)
                latencies.append((time.perf_counter() - start) * 1000)
            
            latencies = np.array(latencies)
            
            return BenchmarkResult(
                mean_latency_ms=float(np.mean(latencies)),
                std_latency_ms=float(np.std(latencies)),
                min_latency_ms=float(np.min(latencies)),
                max_latency_ms=float(np.max(latencies)),
                throughput_per_sec=1000 / np.mean(latencies) * batch_size,
                batch_size=batch_size,
                n_runs=n_runs,
                device=device
            )
            
        except Exception as e:
            logger.error(f"Benchmark failed: {e}")
            return BenchmarkResult(
                mean_latency_ms=0,
                std_latency_ms=0,
                min_latency_ms=0,
                max_latency_ms=0,
                throughput_per_sec=0,
                batch_size=1,
                n_runs=0,
                device="error"
            )
    
    @staticmethod
    def benchmark_pytorch(
        model: "torch.nn.Module",
        input_shape: Tuple[int, ...],
        n_runs: int = 100,
        warmup_runs: int = 10,
        use_gpu: bool = True
    ) -> BenchmarkResult:
        """Benchmark PyTorch model inference."""
        if not TORCH_AVAILABLE:
            return BenchmarkResult(
                mean_latency_ms=0,
                std_latency_ms=0,
                min_latency_ms=0,
                max_latency_ms=0,
                throughput_per_sec=0,
                batch_size=1,
                n_runs=0,
                device="none"
            )
        
        device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        model = model.to(device)
        model.eval()
        
        batch_size = input_shape[0]
        x = torch.randn(*input_shape).to(device)
        
        # Warmup
        with torch.no_grad():
            for _ in range(warmup_runs):
                model(x)
        
        if device == "cuda":
            torch.cuda.synchronize()
        
        # Benchmark
        latencies = []
        with torch.no_grad():
            for _ in range(n_runs):
                if device == "cuda":
                    torch.cuda.synchronize()
                start = time.perf_counter()
                model(x)
                if device == "cuda":
                    torch.cuda.synchronize()
                latencies.append((time.perf_counter() - start) * 1000)
        
        latencies = np.array(latencies)
        
        return BenchmarkResult(
            mean_latency_ms=float(np.mean(latencies)),
            std_latency_ms=float(np.std(latencies)),
            min_latency_ms=float(np.min(latencies)),
            max_latency_ms=float(np.max(latencies)),
            throughput_per_sec=1000 / np.mean(latencies) * batch_size,
            batch_size=batch_size,
            n_runs=n_runs,
            device=device
        )


# ==================== TRITON CONFIG GENERATOR ====================

class TritonConfigGenerator:
    """Generate Triton model repository configuration."""
    
    @staticmethod
    def generate_config(
        model_name: str,
        platform: str,
        inputs: List[Dict[str, Any]],
        outputs: List[Dict[str, Any]],
        max_batch_size: int = 64,
        dynamic_batching: bool = True
    ) -> str:
        """
        Generate Triton config.pbtxt content.
        
        Args:
            model_name: Name of the model
            platform: Triton platform (onnxruntime_onnx, pytorch_libtorch, etc.)
            inputs: List of input specs
            outputs: List of output specs
            max_batch_size: Maximum batch size
            dynamic_batching: Enable dynamic batching
        
        Returns:
            Config file content as string
        """
        lines = [
            f'name: "{model_name}"',
            f'platform: "{platform}"',
            f'max_batch_size: {max_batch_size}',
            ''
        ]
        
        # Inputs
        for inp in inputs:
            lines.append('input [')
            lines.append('  {')
            lines.append(f'    name: "{inp["name"]}"')
            lines.append(f'    data_type: {inp["dtype"]}')
            dims = ', '.join(str(d) for d in inp["dims"])
            lines.append(f'    dims: [ {dims} ]')
            lines.append('  }')
            lines.append(']')
        
        # Outputs
        for out in outputs:
            lines.append('output [')
            lines.append('  {')
            lines.append(f'    name: "{out["name"]}"')
            lines.append(f'    data_type: {out["dtype"]}')
            dims = ', '.join(str(d) for d in out["dims"])
            lines.append(f'    dims: [ {dims} ]')
            lines.append('  }')
            lines.append(']')
        
        # Dynamic batching
        if dynamic_batching:
            lines.extend([
                '',
                'dynamic_batching {',
                '  preferred_batch_size: [ 8, 16, 32 ]',
                '  max_queue_delay_microseconds: 100000',
                '}'
            ])
        
        # Version policy
        lines.extend([
            '',
            'version_policy: { latest { num_versions: 2 }}'
        ])
        
        return '\n'.join(lines)
    
    @staticmethod
    def create_model_repository(
        base_path: str,
        model_name: str,
        model_file: str,
        config_content: str,
        version: int = 1
    ) -> Path:
        """
        Create a Triton model repository structure.
        
        Structure:
            model_name/
            ├── config.pbtxt
            └── 1/
                └── model.onnx (or model.pt, model.plan)
        """
        repo_path = Path(base_path) / model_name
        version_path = repo_path / str(version)
        version_path.mkdir(parents=True, exist_ok=True)
        
        # Write config
        config_path = repo_path / "config.pbtxt"
        config_path.write_text(config_content)
        
        # Copy model
        src = Path(model_file)
        if src.exists():
            shutil.copy2(src, version_path / src.name)
        
        logger.info(f"Created Triton model repository at {repo_path}")
        return repo_path


# ==================== CONVENIENCE FUNCTIONS ====================

def convert_model(
    model: Any,
    output_path: str,
    input_shapes: Dict[str, Tuple[int, ...]],
    target_format: str = "onnx"
) -> ConversionResult:
    """
    Universal model conversion function.
    
    Detects model type and converts to target format.
    """
    if TORCH_AVAILABLE and isinstance(model, torch.nn.Module):
        if target_format == "onnx":
            return PyTorchConverter.to_onnx(model, input_shapes, output_path)
        elif target_format == "torchscript":
            example = torch.randn(*list(input_shapes.values())[0])
            return PyTorchConverter.to_torchscript(model, output_path, example)
    
    if TF_AVAILABLE and hasattr(model, 'fit'):  # Keras-like
        if target_format == "onnx":
            return TensorFlowConverter.to_onnx(model, output_path)
        elif target_format == "savedmodel":
            return TensorFlowConverter.to_savedmodel(model, output_path)
    
    return ConversionResult(
        success=False,
        output_path=output_path,
        source_format="unknown",
        target_format=target_format,
        input_shapes=input_shapes,
        output_shapes={},
        file_size_mb=0,
        error="Could not detect model type"
    )


def get_conversion_availability() -> Dict[str, bool]:
    """Check what conversion options are available."""
    return {
        "pytorch": TORCH_AVAILABLE,
        "tensorflow": TF_AVAILABLE,
        "onnx": ONNX_AVAILABLE,
        "tf2onnx": TF2ONNX_AVAILABLE,
        "tensorrt": TENSORRT_AVAILABLE
    }


# ==================== MODULE EXPORTS ====================

__all__ = [
    "PyTorchConverter",
    "TensorFlowConverter",
    "TensorRTOptimizer",
    "ONNXUtils",
    "ModelBenchmark",
    "TritonConfigGenerator",
    "ConversionResult",
    "BenchmarkResult",
    "TritonModelConfig",
    "convert_model",
    "get_conversion_availability",
    "TORCH_AVAILABLE",
    "TF_AVAILABLE",
    "ONNX_AVAILABLE",
    "TENSORRT_AVAILABLE"
]
