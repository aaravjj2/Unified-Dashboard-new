"""Triton Inference Server integration utilities.

This module provides a small, defensive exporter + client wrapper that the
application can use to produce Triton-compatible model repositories and to
call a running Triton HTTP server if available. The code is best-effort and
falls back gracefully when Triton or optional dependencies are missing.

It is intended as a lightweight developer helper (export artifacts) and a
runtime client for environments where an external Triton server is reachable.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

try:
    import torch
    import numpy as np
except Exception:  # pragma: no cover - optional deps
    torch = None  # type: ignore
    np = None  # type: ignore

# Default repository location for exported Triton models
TRITON_REPO = Path(__file__).resolve().parents[2] / "triton_models"


class TritonModelExporter:
    """Create a minimal Triton model repository for a few helper models.

    The exporter will attempt to use Torch/transformers/sentence-transformers
    if available, but will not fail the application if those packages are
    missing. The primary purpose is to create example artifacts for local
    testing and CI where possible.
    """

    def __init__(self, repo_path: Path | None = None) -> None:
        self.repo_path = Path(repo_path or TRITON_REPO)
        self.repo_path.mkdir(parents=True, exist_ok=True)

    def _write_config(self, model_name: str, config_lines: List[str]) -> None:
        model_dir = self.repo_path / model_name
        model_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = model_dir / "config.pbtxt"
        cfg_path.write_text("\n".join(config_lines))
        logger.info("Wrote Triton config %s", cfg_path)

    def export_example_forecast(self, model_name: str = "forecast_ensemble") -> Path:
        """Create a tiny example model folder for the forecast ensemble.

        This will create a placeholder TorchScript file (if PyTorch is present)
        and a simple `config.pbtxt`. The artifact is suitable for local
        developer testing of the ServingClient's file-based fallback.
        """
        model_dir = self.repo_path / model_name / "1"
        model_dir.mkdir(parents=True, exist_ok=True)

        # Create a tiny TorchScript file when torch is available
        if torch is not None:
            try:
                class _Model(torch.nn.Module):
                    def __init__(self):
                        super().__init__()

                    def forward(self, price_history: torch.Tensor, ticker_id: torch.Tensor):
                        # price_history: (batch, seq)
                        # return forecast and confidence of shape (batch, 1)
                        mean = price_history.mean(dim=1, keepdim=True)
                        forecast = mean * 1.0
                        conf = torch.ones_like(forecast) * 0.5
                        return torch.cat([forecast, conf], dim=1)

                m = _Model()
                ts_path = model_dir / "model.pt"
                example = torch.randn(1, 128)
                tid = torch.tensor([[0]], dtype=torch.int32)
                traced = torch.jit.trace(m, (example, tid), strict=False)
                traced.save(str(ts_path))
                logger.info("Wrote example TorchScript model to %s", ts_path)
            except Exception as e:  # pragma: no cover - best-effort
                logger.warning("Failed to write TorchScript example: %s", e)

        # Write a minimal config.pbtxt
        config_lines = [
            f'name: "{model_name}"',
            'platform: "pytorch_libtorch"',
            'max_batch_size: 8',
            'input {',
            '  name: "price_history"',
            '  data_type: TYPE_FP32',
            '  dims: [ -1 ]',
            '}',
            'input {',
            '  name: "ticker_id"',
            '  data_type: TYPE_INT32',
            '  dims: [ 1 ]',
            '}',
            'output {',
            '  name: "forecast"',
            '  data_type: TYPE_FP32',
            '  dims: [ -1 ]',
            '}',
            'output {',
            '  name: "confidence"',
            '  data_type: TYPE_FP32',
            '  dims: [ -1 ]',
            '}',
        ]
        self._write_config(model_name, config_lines)
        return self.repo_path / model_name


class TritonClient:
    """Thin, defensive wrapper around tritonclient.http.InferenceServerClient.

    The wrapper lazily imports `tritonclient` so the application can run even
    when the Triton client library is not installed. Methods raise a clear
    RuntimeError when the client is unavailable.
    """

    def __init__(self, url: str = "localhost:8000") -> None:
        self.url = url
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            try:
                import tritonclient.http as httpclient

                self._httpclient = httpclient
                self._client = httpclient.InferenceServerClient(url=self.url)
            except Exception as exc:  # pragma: no cover - optional dep / runtime
                logger.debug("Triton client unavailable: %s", exc)
                self._client = None
        return self._client

    def is_ready(self) -> bool:
        client = self._ensure_client()
        if client is None:
            return False
        try:
            return client.is_server_ready()
        except Exception:
            return False

    def infer_forecast(self, price_history, ticker_id: int = 0) -> Dict[str, Any]:
        client = self._ensure_client()
        if client is None:
            raise RuntimeError("Triton client not available")

        httpclient = self._httpclient

        ph = np.asarray(price_history, dtype=np.float32)
        if ph.ndim == 1:
            ph = ph.reshape(1, -1)

        inputs = [
            httpclient.InferInput("price_history", ph.shape, "FP32"),
            httpclient.InferInput("ticker_id", (ph.shape[0], 1), "INT32"),
        ]
        inputs[0].set_data_from_numpy(ph)
        import numpy as _np
        ticker_ids = _np.full((ph.shape[0], 1), ticker_id, dtype=_np.int32)
        inputs[1].set_data_from_numpy(ticker_ids)

        outputs = [httpclient.InferRequestedOutput("forecast"), httpclient.InferRequestedOutput("confidence")]

        result = client.infer("forecast_ensemble", inputs, outputs=outputs)
        forecast = result.as_numpy("forecast")
        confidence = result.as_numpy("confidence")
        return {"forecast": forecast.tolist(), "confidence": confidence.tolist()}


def setup_triton_models():
    exporter = TritonModelExporter()
    exporter.export_example_forecast()
    print("Created Triton model repository at:", TRITON_REPO)
    print("To run Triton locally (Docker):")
    print(f"  docker run --rm -p8000:8000 -p8001:8001 -p8002:8002 -v {TRITON_REPO}:/models nvcr.io/nvidia/tritonserver:24.01-py3 tritonserver --model-repository=/models")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    setup_triton_models()
