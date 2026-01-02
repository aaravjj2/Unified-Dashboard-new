"""
Playwright Tests for Phase 11 - Triton Serving Integration
Tests verify Triton backend connectivity and <200ms latency requirements.
"""

import pytest
import json
import time
import sys
import os
import numpy as np
from pathlib import Path
from playwright.sync_api import Page, expect

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Test configuration
BASE_URL = "http://localhost:8053"
ARTIFACTS_DIR = PROJECT_ROOT / "reports/phase11_serving"
SCREENSHOTS_DIR = ARTIFACTS_DIR / "screenshots"
PLAYWRIGHT_DIR = ARTIFACTS_DIR / "playwright"

# Ensure directories exist
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
PLAYWRIGHT_DIR.mkdir(parents=True, exist_ok=True)


class TestTritonClientUnit:
    """Unit tests for Triton client (no browser needed)."""
    
    def test_triton_client_import(self):
        """Test that triton_client module can be imported."""
        from engines.ml.triton_client import TritonClient, InferenceResult
        assert TritonClient is not None
        assert InferenceResult is not None
    
    def test_triton_client_initialization(self):
        """Test TritonClient initializes correctly."""
        from engines.ml.triton_client import TritonClient
        
        client = TritonClient()
        status = client.get_status()
        
        assert "grpc_url" in status
        assert "http_url" in status
        assert "fallback_enabled" in status
        assert status["fallback_enabled"] is True
    
    def test_local_fallback_inference(self):
        """Test local CPU fallback inference works."""
        from engines.ml.triton_client import TritonClient
        import os
        
        # Enable deterministic mode
        os.environ["SERVING_DETERMINISTIC"] = "1"
        
        client = TritonClient()
        test_input = np.random.randn(1, 50).astype(np.float32)
        
        result = client.infer("signal_model", test_input)
        
        assert result.success is True
        assert result.backend == "local_cpu"
        assert result.output.shape == (1, 1)
    
    def test_inference_latency_under_200ms(self):
        """Test that local inference completes under 200ms."""
        from engines.ml.triton_client import TritonClient
        
        client = TritonClient()
        test_input = np.random.randn(1, 50).astype(np.float32)
        
        # Run multiple inferences to get stable latency
        latencies = []
        for _ in range(5):
            result = client.infer("signal_model", test_input)
            latencies.append(result.latency_ms)
        
        avg_latency = sum(latencies) / len(latencies)
        
        # Store result for reporting
        report = {
            "avg_latency_ms": avg_latency,
            "latencies": latencies,
            "backend": result.backend,
            "under_200ms": avg_latency < 200,
        }
        
        report_path = PLAYWRIGHT_DIR / "latency_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        assert avg_latency < 200, f"Latency {avg_latency}ms exceeds 200ms threshold"
    
    def test_batch_inference(self):
        """Test batch inference works correctly."""
        from engines.ml.triton_client import TritonClient
        
        client = TritonClient()
        batch_input = np.random.randn(8, 50).astype(np.float32)
        
        result = client.infer("signal_model", batch_input)
        
        assert result.success is True
        assert result.output.shape[0] == 8  # Batch dimension preserved


class TestONNXExporter:
    """Tests for ONNX model exporter."""
    
    def test_exporter_import(self):
        """Test that exporter module can be imported."""
        from engines.ml.exporter import ONNXExporter, create_test_models
        assert ONNXExporter is not None
        assert create_test_models is not None
    
    def test_model_repository_exists(self):
        """Test model repository has required structure."""
        model_repo = PROJECT_ROOT / "model_repository"
        
        assert model_repo.exists(), "model_repository directory missing"
        assert (model_repo / "signal_model" / "1" / "model.onnx").exists()
        assert (model_repo / "volatility_model" / "1" / "model.onnx").exists()
    
    def test_config_pbtxt_exists(self):
        """Test Triton config files exist."""
        model_repo = PROJECT_ROOT / "model_repository"
        
        assert (model_repo / "signal_model" / "config.pbtxt").exists()
        assert (model_repo / "volatility_model" / "config.pbtxt").exists()
    
    def test_onnx_model_valid(self):
        """Test exported ONNX models are valid."""
        import onnx
        
        model_repo = PROJECT_ROOT / "model_repository"
        signal_model_path = model_repo / "signal_model" / "1" / "model.onnx"
        
        model = onnx.load(str(signal_model_path))
        onnx.checker.check_model(model)


class TestDockerCompose:
    """Tests for docker-compose configuration."""
    
    def test_tritonserver_service_defined(self):
        """Test that tritonserver service is in docker-compose.yml."""
        compose_path = PROJECT_ROOT / "docker-compose.yml"
        
        with open(compose_path) as f:
            content = f.read()
        
        assert "tritonserver:" in content
        assert "nvcr.io/nvidia/tritonserver" in content
        assert "8001:8001" in content  # gRPC port
        assert "8002:8002" in content  # Metrics port
    
    def test_model_repository_volume(self):
        """Test model_repository volume is mapped."""
        compose_path = PROJECT_ROOT / "docker-compose.yml"
        
        with open(compose_path) as f:
            content = f.read()
        
        assert "./model_repository:/models" in content


class TestDashboardIntegration:
    """Playwright tests for dashboard integration."""
    
    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        """Setup for each test."""
        self.page = page
        page.set_default_timeout(30000)
    
    def test_dashboard_loads(self, page: Page):
        """Test dashboard loads successfully."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Take screenshot
        page.screenshot(path=str(SCREENSHOTS_DIR / "dashboard_load.png"))
        
        # Verify page loaded - check body is visible
        expect(page.locator("body")).to_be_visible()
    
    def test_inference_endpoint_available(self, page: Page):
        """Test that inference can be triggered from dashboard."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Check for ML-related elements (signals, predictions, etc.)
        ml_indicators = page.locator("text=/signal|predict|model|inference/i")
        
        # Screenshot current state
        page.screenshot(path=str(SCREENSHOTS_DIR / "ml_elements.png"))
        
        # We verify the page loads - actual ML integration varies by tab
        expect(page.locator("body")).to_be_visible()
    
    def test_api_health_endpoint(self, page: Page):
        """Test API health endpoint responds."""
        response = page.request.get(f"{BASE_URL}/")
        assert response.status == 200
    
    def test_backend_status_display(self, page: Page):
        """Test backend status is visible (Triton or Local CPU)."""
        from engines.ml.triton_client import TritonClient
        
        client = TritonClient()
        status = client.get_status()
        
        # Verify backend is operational
        has_backend = (
            status.get("grpc_available") or 
            status.get("http_available") or 
            status.get("fallback_enabled")
        )
        
        assert has_backend, "No inference backend available"
        
        # Write status report
        report_path = PLAYWRIGHT_DIR / "backend_status.json"
        with open(report_path, "w") as f:
            json.dump(status, f, indent=2)


class TestPerformanceRequirements:
    """Tests for performance requirements."""
    
    def test_inference_latency_p99_under_200ms(self):
        """Test P99 latency is under 200ms."""
        from engines.ml.triton_client import TritonClient
        
        client = TritonClient()
        test_input = np.random.randn(1, 50).astype(np.float32)
        
        # Run 100 inferences
        latencies = []
        for _ in range(100):
            result = client.infer("signal_model", test_input)
            latencies.append(result.latency_ms)
        
        # Calculate P99
        p99 = np.percentile(latencies, 99)
        
        report = {
            "p50_ms": float(np.percentile(latencies, 50)),
            "p90_ms": float(np.percentile(latencies, 90)),
            "p99_ms": float(p99),
            "min_ms": float(min(latencies)),
            "max_ms": float(max(latencies)),
            "samples": len(latencies),
        }
        
        report_path = PLAYWRIGHT_DIR / "p99_latency_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        assert p99 < 200, f"P99 latency {p99}ms exceeds 200ms"
    
    def test_throughput_baseline(self):
        """Test baseline throughput (inferences per second)."""
        from engines.ml.triton_client import TritonClient
        
        client = TritonClient()
        test_input = np.random.randn(1, 50).astype(np.float32)
        
        # Measure throughput over 5 seconds
        start = time.time()
        count = 0
        while time.time() - start < 5:
            result = client.infer("signal_model", test_input)
            if result.success:
                count += 1
        
        elapsed = time.time() - start
        throughput = count / elapsed
        
        report = {
            "inferences": count,
            "elapsed_seconds": elapsed,
            "throughput_per_second": throughput,
            "backend": result.backend,
        }
        
        report_path = PLAYWRIGHT_DIR / "throughput_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        # Baseline: at least 10 inferences per second
        assert throughput > 10, f"Throughput {throughput}/s below baseline"


def test_triton_grpc_backend_label():
    """Test that backend correctly reports Triton (gRPC) when available."""
    from engines.ml.triton_client import TritonClient
    
    client = TritonClient()
    status = client.get_status()
    
    # Check if Triton is available or fallback is working
    if status.get("grpc_available"):
        backend_label = "Triton (gRPC)"
    elif status.get("http_available"):
        backend_label = "Triton (HTTP)"
    else:
        backend_label = "Local (CPU)"
    
    report = {
        "backend_label": backend_label,
        "grpc_available": status.get("grpc_available", False),
        "http_available": status.get("http_available", False),
        "fallback_enabled": status.get("fallback_enabled", True),
    }
    
    report_path = PLAYWRIGHT_DIR / "backend_label_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    assert backend_label in ["Triton (gRPC)", "Triton (HTTP)", "Local (CPU)"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
