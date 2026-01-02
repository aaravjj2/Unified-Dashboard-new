"""
Comprehensive tests for Part 2: Triton & Infrastructure.

Tests cover:
- Triton Client (with local fallback)
- MLflow Experiment Tracking
- Model Conversion Utilities
- Integration between components

Run with: pytest test_part2_infrastructure.py -v
"""

import asyncio
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


# Check for onnxscript (required for PyTorch ONNX export in newer versions)
def _check_onnx_export_available():
    """Check if ONNX export works (needs onnxscript)."""
    try:
        import onnxscript
        return True
    except ImportError:
        return False

ONNX_EXPORT_AVAILABLE = _check_onnx_export_available()


# ==================== TRITON CLIENT TESTS ====================

class TestTritonClient:
    """Tests for Triton inference client."""
    
    def test_import(self):
        """Test that triton_client module imports correctly."""
        from financial_dashboard.serving.triton_client import (
            TRITON_AVAILABLE,
            UnifiedInferenceClient,
            LocalInferenceClient,
            InferenceResult,
            ServerHealth,
            get_triton_availability
        )
        assert UnifiedInferenceClient is not None
        assert LocalInferenceClient is not None
    
    def test_inference_result_dataclass(self):
        """Test InferenceResult dataclass."""
        from financial_dashboard.serving.triton_client import InferenceResult
        
        result = InferenceResult(
            prediction=np.array([1.0, 2.0]),
            confidence=np.array([0.9]),
            latency_ms=5.0,
            model_name="test_model",
            model_version="1",
            backend="local"
        )
        
        assert result.prediction.shape == (2,)
        assert result.latency_ms == 5.0
        assert result.backend == "local"
    
    def test_server_health_dataclass(self):
        """Test ServerHealth dataclass."""
        from financial_dashboard.serving.triton_client import ServerHealth
        
        health = ServerHealth(
            is_live=True,
            is_ready=True,
            models_ready={"model1": True, "model2": False},
            latency_ms=1.5
        )
        
        assert health.is_live is True
        assert len(health.models_ready) == 2
    
    @pytest.mark.asyncio
    async def test_local_inference_client_init(self):
        """Test LocalInferenceClient initialization."""
        from financial_dashboard.serving.triton_client import LocalInferenceClient
        
        client = LocalInferenceClient()
        assert await client.connect() is True
    
    @pytest.mark.asyncio
    async def test_local_inference_client_health(self):
        """Test LocalInferenceClient health check."""
        from financial_dashboard.serving.triton_client import LocalInferenceClient
        
        client = LocalInferenceClient()
        await client.connect()
        
        health = await client.health_check()
        assert health.is_live is True
        assert health.is_ready is True
    
    @pytest.mark.asyncio
    async def test_local_inference_client_register_model(self):
        """Test registering models with LocalInferenceClient."""
        from financial_dashboard.serving.triton_client import LocalInferenceClient
        
        client = LocalInferenceClient()
        
        # Create a simple mock model
        class MockModel:
            def predict(self, x):
                return x * 2
        
        client.register_model("mock_model", MockModel())
        
        health = await client.health_check()
        assert "mock_model" in health.models_ready
    
    @pytest.mark.asyncio
    async def test_local_inference_client_predict(self):
        """Test local inference prediction."""
        from financial_dashboard.serving.triton_client import LocalInferenceClient
        
        client = LocalInferenceClient()
        
        class MockModel:
            def predict(self, x):
                return x.mean(axis=-1)
        
        client.register_model("mock_model", MockModel())
        
        inputs = {"data": np.random.randn(10).astype(np.float32)}
        result = await client.predict(inputs, "mock_model")
        
        assert result.prediction is not None
        assert result.backend == "local"
        assert result.latency_ms > 0
    
    @pytest.mark.asyncio
    async def test_unified_client_fallback(self):
        """Test UnifiedInferenceClient falls back to local."""
        from financial_dashboard.serving.triton_client import UnifiedInferenceClient
        
        # Use invalid Triton URL to force fallback
        client = UnifiedInferenceClient(
            triton_url="invalid:9999",
            prefer_triton=False  # Skip Triton
        )
        
        connected = await client.connect()
        assert connected is True
        assert client.backend == "local"
    
    def test_get_triton_availability(self):
        """Test availability check function."""
        from financial_dashboard.serving.triton_client import get_triton_availability
        
        avail = get_triton_availability()
        assert "triton_available" in avail
        assert "grpc_available" in avail
        assert "http_available" in avail
    
    @pytest.mark.asyncio
    async def test_unified_client_close(self):
        """Test UnifiedInferenceClient close."""
        from financial_dashboard.serving.triton_client import UnifiedInferenceClient
        
        client = UnifiedInferenceClient(prefer_triton=False)
        await client.connect()
        await client.close()


# ==================== MLFLOW TRACKER TESTS ====================

class TestMLflowTracker:
    """Tests for MLflow experiment tracking."""
    
    def test_import(self):
        """Test that mlflow_tracker module imports correctly."""
        from financial_dashboard.mlops.mlflow_tracker import (
            MLflowExperimentTracker,
            ModelRegistry,
            LocalTracker,
            ExperimentRun,
            ModelVersion,
            MLFLOW_AVAILABLE,
            get_mlflow_availability
        )
        assert MLflowExperimentTracker is not None
        assert LocalTracker is not None
    
    def test_experiment_run_dataclass(self):
        """Test ExperimentRun dataclass."""
        from financial_dashboard.mlops.mlflow_tracker import ExperimentRun
        
        run = ExperimentRun(
            run_id="test_123",
            experiment_name="test_exp",
            run_name="run_1",
            start_time=datetime.now()
        )
        
        assert run.run_id == "test_123"
        assert run.status == "RUNNING"
        assert run.params == {}
    
    def test_model_version_dataclass(self):
        """Test ModelVersion dataclass."""
        from financial_dashboard.mlops.mlflow_tracker import ModelVersion
        
        version = ModelVersion(
            name="lstm_model",
            version=1,
            stage="Production",
            run_id="run_123",
            created_at=datetime.now()
        )
        
        assert version.name == "lstm_model"
        assert version.stage == "Production"
    
    def test_local_tracker_init(self):
        """Test LocalTracker initialization."""
        from financial_dashboard.mlops.mlflow_tracker import LocalTracker
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = LocalTracker(base_dir=tmpdir)
            assert Path(tmpdir).exists()
    
    def test_local_tracker_start_run(self):
        """Test LocalTracker start_run."""
        from financial_dashboard.mlops.mlflow_tracker import LocalTracker
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = LocalTracker(base_dir=tmpdir)
            run = tracker.start_run("test_exp", "test_run")
            
            assert run is not None
            assert run.experiment_name == "test_exp"
            assert run.run_name == "test_run"
    
    def test_local_tracker_log_params(self):
        """Test LocalTracker param logging."""
        from financial_dashboard.mlops.mlflow_tracker import LocalTracker
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = LocalTracker(base_dir=tmpdir)
            tracker.start_run("test_exp", "test_run")
            
            tracker.log_params({"learning_rate": 0.001, "epochs": 100})
            
            assert tracker.current_run.params["learning_rate"] == 0.001
            assert tracker.current_run.params["epochs"] == 100
    
    def test_local_tracker_log_metrics(self):
        """Test LocalTracker metric logging."""
        from financial_dashboard.mlops.mlflow_tracker import LocalTracker
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = LocalTracker(base_dir=tmpdir)
            tracker.start_run("test_exp", "test_run")
            
            for i in range(5):
                tracker.log_metric("loss", 1.0 / (i + 1))
            
            assert len(tracker.current_run.metrics["loss"]) == 5
            assert tracker.current_run.metrics["loss"][-1] == 0.2
    
    def test_local_tracker_end_run(self):
        """Test LocalTracker end_run saves metadata."""
        from financial_dashboard.mlops.mlflow_tracker import LocalTracker
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = LocalTracker(base_dir=tmpdir)
            run = tracker.start_run("test_exp", "test_run")
            tracker.log_params({"lr": 0.01})
            tracker.log_metric("loss", 0.5)
            
            run_id = run.run_id
            tracker.end_run()
            
            # Check metadata was saved
            meta_path = Path(tmpdir) / "test_exp" / run_id / "run_metadata.json"
            assert meta_path.exists()
            
            with open(meta_path) as f:
                metadata = json.load(f)
            
            assert metadata["status"] == "FINISHED"
            assert metadata["params"]["lr"] == 0.01
    
    def test_local_tracker_list_runs(self):
        """Test LocalTracker list_runs."""
        from financial_dashboard.mlops.mlflow_tracker import LocalTracker
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = LocalTracker(base_dir=tmpdir)
            
            # Create multiple runs
            for i in range(3):
                tracker.start_run("test_exp", f"run_{i}")
                tracker.log_metric("accuracy", 0.8 + i * 0.05)
                tracker.end_run()
            
            runs = tracker.list_runs("test_exp")
            assert len(runs) == 3
    
    def test_mlflow_tracker_context_manager(self):
        """Test MLflowExperimentTracker context manager."""
        from financial_dashboard.mlops.mlflow_tracker import MLflowExperimentTracker
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use local fallback
            tracker = MLflowExperimentTracker(
                experiment_name="test_exp",
                tracking_uri=f"sqlite:///{tmpdir}/test.db"
            )
            
            with tracker.start_run("test_run") as run:
                tracker.log_params({"lr": 0.001})
                tracker.log_metrics({"loss": 0.5, "accuracy": 0.9})
    
    def test_model_registry_local_fallback(self):
        """Test ModelRegistry with local fallback."""
        from financial_dashboard.mlops.mlflow_tracker import (
            MLflowExperimentTracker, ModelRegistry
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = MLflowExperimentTracker(experiment_name="test")
            registry = ModelRegistry(tracker)
            registry._registry_path = Path(tmpdir) / "registry"
            registry._registry_path.mkdir()
            
            # Register model
            version = registry.register_model(
                model_uri="runs:/test_run/model",
                name="test_model",
                description="Test model"
            )
            
            assert version.name == "test_model"
            assert version.version == 1
            assert version.stage == "None"
    
    def test_get_mlflow_availability(self):
        """Test availability check function."""
        from financial_dashboard.mlops.mlflow_tracker import get_mlflow_availability
        
        avail = get_mlflow_availability()
        assert "mlflow_available" in avail
        assert "torch_available" in avail


# ==================== MODEL CONVERTER TESTS ====================

class TestModelConverter:
    """Tests for model conversion utilities."""
    
    def test_import(self):
        """Test that model_converter module imports correctly."""
        from financial_dashboard.serving.model_converter import (
            PyTorchConverter,
            TensorFlowConverter,
            ONNXUtils,
            ModelBenchmark,
            TritonConfigGenerator,
            ConversionResult,
            BenchmarkResult,
            get_conversion_availability
        )
        assert PyTorchConverter is not None
        assert ONNXUtils is not None
    
    def test_conversion_result_dataclass(self):
        """Test ConversionResult dataclass."""
        from financial_dashboard.serving.model_converter import ConversionResult
        
        result = ConversionResult(
            success=True,
            output_path="/path/to/model.onnx",
            source_format="pytorch",
            target_format="onnx",
            input_shapes={"input": [1, 60, 10]},
            output_shapes={"output": [1, 1]},
            file_size_mb=5.5
        )
        
        assert result.success is True
        assert result.file_size_mb == 5.5
    
    def test_benchmark_result_dataclass(self):
        """Test BenchmarkResult dataclass."""
        from financial_dashboard.serving.model_converter import BenchmarkResult
        
        result = BenchmarkResult(
            mean_latency_ms=5.0,
            std_latency_ms=0.5,
            min_latency_ms=4.5,
            max_latency_ms=6.0,
            throughput_per_sec=200.0,
            batch_size=1,
            n_runs=100,
            device="cpu"
        )
        
        assert result.mean_latency_ms == 5.0
        assert result.throughput_per_sec == 200.0
    
    @pytest.mark.skipif(
        not __import__('financial_dashboard.serving.model_converter', fromlist=['TORCH_AVAILABLE']).TORCH_AVAILABLE or
        not ONNX_EXPORT_AVAILABLE,
        reason="PyTorch or onnxscript not available"
    )
    def test_pytorch_to_onnx_simple(self):
        """Test PyTorch to ONNX conversion with simple model."""
        import torch
        import torch.nn as nn
        from financial_dashboard.serving.model_converter import PyTorchConverter
        
        # Simple model
        class SimpleModel(nn.Module):
            def __init__(self):
                super().__init__()
                self.fc = nn.Linear(10, 1)
            
            def forward(self, x):
                return self.fc(x)
        
        model = SimpleModel()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "model.onnx")
            
            result = PyTorchConverter.to_onnx(
                model=model,
                input_shapes={"input": (1, 10)},
                output_path=output_path
            )
            
            assert result.success is True
            assert os.path.exists(output_path)
            assert result.file_size_mb > 0
    
    @pytest.mark.skipif(
        not __import__('financial_dashboard.serving.model_converter', fromlist=['TORCH_AVAILABLE']).TORCH_AVAILABLE,
        reason="PyTorch not available"
    )
    def test_pytorch_to_torchscript(self):
        """Test PyTorch to TorchScript conversion."""
        import torch
        import torch.nn as nn
        from financial_dashboard.serving.model_converter import PyTorchConverter
        
        class SimpleModel(nn.Module):
            def __init__(self):
                super().__init__()
                self.fc = nn.Linear(10, 1)
            
            def forward(self, x):
                return self.fc(x)
        
        model = SimpleModel()
        example_input = torch.randn(1, 10)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "model.pt")
            
            result = PyTorchConverter.to_torchscript(
                model=model,
                output_path=output_path,
                example_input=example_input
            )
            
            assert result.success is True
            assert os.path.exists(output_path)
    
    @pytest.mark.skipif(
        not __import__('financial_dashboard.serving.model_converter', fromlist=['ONNX_AVAILABLE']).ONNX_AVAILABLE or
        not ONNX_EXPORT_AVAILABLE,
        reason="ONNX or onnxscript not available"
    )
    def test_onnx_utils_verify(self):
        """Test ONNX verification utility."""
        import torch
        import torch.nn as nn
        from financial_dashboard.serving.model_converter import PyTorchConverter, ONNXUtils
        
        if not __import__('financial_dashboard.serving.model_converter', fromlist=['TORCH_AVAILABLE']).TORCH_AVAILABLE:
            pytest.skip("PyTorch not available")
        
        class SimpleModel(nn.Module):
            def __init__(self):
                super().__init__()
                self.fc = nn.Linear(10, 1)
            
            def forward(self, x):
                return self.fc(x)
        
        model = SimpleModel()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "model.onnx")
            PyTorchConverter.to_onnx(model, {"input": (1, 10)}, output_path)
            
            is_valid, error = ONNXUtils.verify(output_path)
            assert is_valid is True
            assert error is None
    
    @pytest.mark.skipif(
        not __import__('financial_dashboard.serving.model_converter', fromlist=['ONNX_AVAILABLE']).ONNX_AVAILABLE or
        not ONNX_EXPORT_AVAILABLE,
        reason="ONNX or onnxscript not available"
    )
    def test_onnx_utils_get_metadata(self):
        """Test ONNX metadata extraction."""
        import torch
        import torch.nn as nn
        from financial_dashboard.serving.model_converter import PyTorchConverter, ONNXUtils
        
        if not __import__('financial_dashboard.serving.model_converter', fromlist=['TORCH_AVAILABLE']).TORCH_AVAILABLE:
            pytest.skip("PyTorch not available")
        
        class SimpleModel(nn.Module):
            def __init__(self):
                super().__init__()
                self.fc = nn.Linear(10, 1)
            
            def forward(self, x):
                return self.fc(x)
        
        model = SimpleModel()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "model.onnx")
            PyTorchConverter.to_onnx(model, {"input": (1, 10)}, output_path)
            
            metadata = ONNXUtils.get_metadata(output_path)
            
            assert "inputs" in metadata
            assert "outputs" in metadata
            assert "num_nodes" in metadata
            assert len(metadata["inputs"]) > 0
    
    def test_triton_config_generator(self):
        """Test Triton config generation."""
        from financial_dashboard.serving.model_converter import TritonConfigGenerator
        
        config = TritonConfigGenerator.generate_config(
            model_name="lstm_forecaster",
            platform="onnxruntime_onnx",
            inputs=[
                {"name": "price_sequence", "dtype": "TYPE_FP32", "dims": [60, 10]},
                {"name": "ticker_id", "dtype": "TYPE_INT32", "dims": [1]}
            ],
            outputs=[
                {"name": "price_prediction", "dtype": "TYPE_FP32", "dims": [1]},
                {"name": "confidence", "dtype": "TYPE_FP32", "dims": [1]}
            ],
            max_batch_size=64,
            dynamic_batching=True
        )
        
        assert 'name: "lstm_forecaster"' in config
        assert 'platform: "onnxruntime_onnx"' in config
        assert 'max_batch_size: 64' in config
        assert 'dynamic_batching' in config
    
    def test_triton_config_generator_create_repository(self):
        """Test Triton model repository creation."""
        from financial_dashboard.serving.model_converter import TritonConfigGenerator
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a dummy model file
            model_file = os.path.join(tmpdir, "model.onnx")
            Path(model_file).touch()
            
            config_content = TritonConfigGenerator.generate_config(
                model_name="test_model",
                platform="onnxruntime_onnx",
                inputs=[{"name": "input", "dtype": "TYPE_FP32", "dims": [10]}],
                outputs=[{"name": "output", "dtype": "TYPE_FP32", "dims": [1]}]
            )
            
            repo_path = TritonConfigGenerator.create_model_repository(
                base_path=tmpdir,
                model_name="test_model",
                model_file=model_file,
                config_content=config_content
            )
            
            assert (repo_path / "config.pbtxt").exists()
            assert (repo_path / "1").exists()
    
    @pytest.mark.skipif(
        not __import__('financial_dashboard.serving.model_converter', fromlist=['ONNX_AVAILABLE']).ONNX_AVAILABLE or
        not ONNX_EXPORT_AVAILABLE,
        reason="ONNX or onnxscript not available"
    )
    def test_model_benchmark_onnx(self):
        """Test ONNX model benchmarking."""
        import torch
        import torch.nn as nn
        from financial_dashboard.serving.model_converter import (
            PyTorchConverter, ModelBenchmark
        )
        
        if not __import__('financial_dashboard.serving.model_converter', fromlist=['TORCH_AVAILABLE']).TORCH_AVAILABLE:
            pytest.skip("PyTorch not available")
        
        class SimpleModel(nn.Module):
            def __init__(self):
                super().__init__()
                self.fc = nn.Linear(10, 1)
            
            def forward(self, x):
                return self.fc(x)
        
        model = SimpleModel()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "model.onnx")
            PyTorchConverter.to_onnx(model, {"input": (1, 10)}, output_path)
            
            result = ModelBenchmark.benchmark_onnx(
                onnx_path=output_path,
                input_shapes={"input": (1, 10)},
                n_runs=10,
                warmup_runs=2,
                use_gpu=False
            )
            
            assert result.mean_latency_ms > 0
            assert result.n_runs == 10
            assert result.device in ["CPUExecutionProvider", "CUDAExecutionProvider"]
    
    def test_get_conversion_availability(self):
        """Test availability check function."""
        from financial_dashboard.serving.model_converter import get_conversion_availability
        
        avail = get_conversion_availability()
        assert "pytorch" in avail
        assert "tensorflow" in avail
        assert "onnx" in avail
        assert "tensorrt" in avail


# ==================== INTEGRATION TESTS ====================

class TestIntegration:
    """Integration tests across Part 2 components."""
    
    @pytest.mark.asyncio
    async def test_tracker_with_inference(self):
        """Test MLflow tracking with inference results."""
        from financial_dashboard.mlops.mlflow_tracker import MLflowExperimentTracker
        from financial_dashboard.serving.triton_client import (
            UnifiedInferenceClient, InferenceResult
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup tracker
            tracker = MLflowExperimentTracker(experiment_name="inference_test")
            
            # Setup client
            client = UnifiedInferenceClient(prefer_triton=False)
            await client.connect()
            
            # Mock model
            class MockModel:
                def predict(self, x):
                    return np.array([x.mean()])
            
            client.register_local_model("mock", MockModel())
            
            with tracker.start_run("inference_run"):
                # Log params
                tracker.log_params({
                    "model_name": "mock",
                    "backend": client.backend
                })
                
                # Run inference
                inputs = {"data": np.random.randn(10).astype(np.float32)}
                result = await client.predict(inputs, "mock")
                
                # Log metrics
                tracker.log_metrics({
                    "latency_ms": result.latency_ms,
                    "prediction": float(result.prediction[0])
                })
            
            await client.close()
    
    @pytest.mark.skipif(
        not __import__('financial_dashboard.serving.model_converter', fromlist=['TORCH_AVAILABLE']).TORCH_AVAILABLE or
        not __import__('financial_dashboard.serving.model_converter', fromlist=['ONNX_AVAILABLE']).ONNX_AVAILABLE or
        not ONNX_EXPORT_AVAILABLE,
        reason="PyTorch, ONNX or onnxscript not available"
    )
    def test_convert_and_benchmark(self):
        """Test model conversion followed by benchmarking."""
        import torch
        import torch.nn as nn
        from financial_dashboard.serving.model_converter import (
            PyTorchConverter, ModelBenchmark
        )
        
        # Use simple MLP instead of LSTM to avoid ONNX runtime slice issues
        class SimpleMLPModel(nn.Module):
            def __init__(self):
                super().__init__()
                self.fc1 = nn.Linear(60 * 10, 64)
                self.relu = nn.ReLU()
                self.fc2 = nn.Linear(64, 32)
                self.fc3 = nn.Linear(32, 1)
            
            def forward(self, x):
                x = x.view(x.size(0), -1)  # Flatten
                x = self.relu(self.fc1(x))
                x = self.relu(self.fc2(x))
                return self.fc3(x)
        
        model = SimpleMLPModel()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Convert
            output_path = os.path.join(tmpdir, "mlp.onnx")
            conv_result = PyTorchConverter.to_onnx(
                model=model,
                input_shapes={"input": (1, 60, 10)},
                output_path=output_path
            )
            
            assert conv_result.success is True
            
            # Benchmark
            bench_result = ModelBenchmark.benchmark_onnx(
                onnx_path=output_path,
                input_shapes={"input": (1, 60, 10)},
                n_runs=5,
                use_gpu=False
            )
            
            assert bench_result.mean_latency_ms > 0
            assert bench_result.throughput_per_sec > 0
    
    def test_full_pipeline_with_triton_config(self):
        """Test full pipeline: convert -> config -> repository."""
        from financial_dashboard.serving.model_converter import (
            TritonConfigGenerator, TORCH_AVAILABLE, ONNX_AVAILABLE
        )
        
        if not TORCH_AVAILABLE or not ONNX_AVAILABLE or not ONNX_EXPORT_AVAILABLE:
            pytest.skip("PyTorch, ONNX or onnxscript not available")
        
        import torch
        import torch.nn as nn
        from financial_dashboard.serving.model_converter import PyTorchConverter
        
        class SimpleModel(nn.Module):
            def __init__(self):
                super().__init__()
                self.fc = nn.Linear(10, 1)
            
            def forward(self, x):
                return self.fc(x)
        
        model = SimpleModel()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Step 1: Convert to ONNX
            onnx_path = os.path.join(tmpdir, "model.onnx")
            conv_result = PyTorchConverter.to_onnx(
                model=model,
                input_shapes={"input": (1, 10)},
                output_path=onnx_path
            )
            assert conv_result.success
            
            # Step 2: Generate Triton config
            config = TritonConfigGenerator.generate_config(
                model_name="simple_model",
                platform="onnxruntime_onnx",
                inputs=[{"name": "input", "dtype": "TYPE_FP32", "dims": [10]}],
                outputs=[{"name": "output", "dtype": "TYPE_FP32", "dims": [1]}],
                max_batch_size=32
            )
            
            # Step 3: Create repository
            repo_path = TritonConfigGenerator.create_model_repository(
                base_path=tmpdir,
                model_name="simple_model",
                model_file=onnx_path,
                config_content=config
            )
            
            # Verify structure
            assert (repo_path / "config.pbtxt").exists()
            assert (repo_path / "1" / "model.onnx").exists()
            
            # Verify config content
            config_content = (repo_path / "config.pbtxt").read_text()
            assert 'name: "simple_model"' in config_content


# ==================== RUN TESTS ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
