"""
Triton Inference Server Integration
Model export and deployment utilities for NVIDIA Triton

Features:
- Export PyTorch models to TorchScript
- Generate Triton model configs
- Deploy to Triton server
"""

import os
import json
import logging
import torch
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Triton model repository structure:
# model_repository/
#   model_name/
#     config.pbtxt
#     1/
#       model.pt (TorchScript)
#     2/
#       model.pt (newer version)

TRITON_REPO = Path(__file__).parent.parent.parent / "triton_models"


class TritonModelExporter:
    """Export models for Triton Inference Server"""
    
    def __init__(self, repo_path: Path = TRITON_REPO):
        self.repo_path = repo_path
        self.repo_path.mkdir(parents=True, exist_ok=True)
    
    def export_embedding_model(self, model_name: str = "embeddings") -> Path:
        """
        Export sentence-transformer to ONNX for Triton
        
        Returns path to exported model
        """
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer("all-MiniLM-L6-v2")
            
            # Create model directory
            model_dir = self.repo_path / model_name / "1"
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Get underlying transformer module now - ensure variable exists for both export branches
            transformer = model._first_module()
            # Ensure transformer module is on a device (use CUDA if available)
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            try:
                transformer.auto_model.to(device)
            except Exception:
                # best-effort; some transformer wrappers don't expose auto_model
                pass

            # Export to ONNX (prefers ONNX; fallback to TorchScript)
            onnx_path = model_dir / "model.onnx"

            onnx_exported = False
            try:
                import onnx
                from torch.onnx import export as onnx_export

                # Create dummy tensors
                input_ids = torch.zeros(1, 256, dtype=torch.long, device=device)
                attention_mask = torch.ones(1, 256, dtype=torch.long, device=device)

                # Export
                torch.onnx.export(
                    transformer.auto_model,
                    (input_ids, attention_mask),
                    str(onnx_path),
                    input_names=["input_ids", "attention_mask"],
                    output_names=["last_hidden_state"],
                    dynamic_axes={
                        "input_ids": {0: "batch", 1: "seq"},
                        "attention_mask": {0: "batch", 1: "seq"}
                    },
                    opset_version=14
                )
                logger.info(f"Exported embedding model to {onnx_path}")
                onnx_exported = True

            except Exception as e:
                logger.warning(f"ONNX export failed or not available: {e}, using TorchScript")
                ts_path = model_dir / "model.pt"
                # Fallback to TorchScript
                # Create dummy tensors
                input_ids = torch.zeros(1, 256, dtype=torch.long, device=device)
                attention_mask = torch.ones(1, 256, dtype=torch.long, device=device)
                # Wrap transformer.model to return a single tensor (last_hidden_state) to avoid dict outputs
                class EmbeddingWrapper(torch.nn.Module):
                    def __init__(self, auto_model):
                        super().__init__()
                        self.auto_model = auto_model

                    def forward(self, input_ids, attention_mask):
                        outputs = self.auto_model(input_ids=input_ids, attention_mask=attention_mask)
                        last_hidden_state = getattr(outputs, 'last_hidden_state', None)
                        if last_hidden_state is None and isinstance(outputs, dict):
                            last_hidden_state = outputs.get('last_hidden_state')
                        return last_hidden_state

                wrapper = EmbeddingWrapper(transformer.auto_model)
                script = torch.jit.trace(
                    wrapper,
                    (input_ids, attention_mask),
                    strict=False
                )
                script.save(str(ts_path))
                logger.info(f"Exported embedding model (TorchScript) to {ts_path}")
            
            # Write config (platform depends on export type - ONNX vs TorchScript)
            platform = "onnxruntime_onnx" if onnx_exported else "pytorch_libtorch"
            self._write_config(model_name, {
                "name": model_name,
                "platform": platform,
                "max_batch_size": 128,
                "input": [
                    {"name": "input_ids", "data_type": "TYPE_INT64", "dims": [256]},
                    {"name": "attention_mask", "data_type": "TYPE_INT64", "dims": [256]}
                ],
                "output": [
                    {"name": "last_hidden_state", "data_type": "TYPE_FP32", "dims": [256, 384]}
                ],
                "instance_group": [{"kind": "KIND_GPU", "count": 1}]
            })
            
            return model_dir
            
        except Exception as e:
            logger.error(f"Failed to export embedding model: {e}")
            raise
    
    def export_finbert_model(self, model_name: str = "sentiment_finbert") -> Path:
        """Export FinBERT model for Triton"""
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            
            # Load FinBERT
            model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
            model.eval()
            
            # Create model directory
            model_dir = self.repo_path / model_name / "1"
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Export to TorchScript
            ts_path = model_dir / "model.pt"

            # Create dummy inputs
            input_ids = torch.zeros(1, 512, dtype=torch.long)
            attention_mask = torch.ones(1, 512, dtype=torch.long)

            # Wrap the model to return only logits (avoid dict/ModelOutput tracing issues)
            class FinBERTWrapper(torch.nn.Module):
                def __init__(self, model):
                    super().__init__()
                    self.model = model

                def forward(self, input_ids, attention_mask):
                    outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
                    # `outputs` may be a ModelOutput or dict
                    logits = getattr(outputs, 'logits', outputs.get('logits') if isinstance(outputs, dict) else outputs)
                    return logits

            wrapper = FinBERTWrapper(model)

            # Trace and save with strict=False to allow non-tensor constants (if needed)
            with torch.no_grad():
                traced = torch.jit.trace(wrapper, (input_ids, attention_mask), strict=False)
                traced.save(str(ts_path))
            
            logger.info(f"Exported FinBERT to {ts_path}")
            
            # Write config
            self._write_config(model_name, {
                "name": model_name,
                "platform": "pytorch_libtorch",
                "max_batch_size": 64,
                "input": [
                    {"name": "input_ids", "data_type": "TYPE_INT64", "dims": [512]},
                    {"name": "attention_mask", "data_type": "TYPE_INT64", "dims": [512]}
                ],
                "output": [
                    {"name": "logits", "data_type": "TYPE_FP32", "dims": [3]}
                ],
                "instance_group": [{"kind": "KIND_GPU", "count": 1}],
                "dynamic_batching": {"max_queue_delay_microseconds": 50000}
            })
            
            return model_dir
            
        except Exception as e:
            logger.error(f"Failed to export FinBERT: {e}")
            raise
    
    def _write_config(self, model_name: str, config: Dict[str, Any]):
        """Write Triton config.pbtxt file"""
        config_path = self.repo_path / model_name / "config.pbtxt"
        
        pbtxt_lines = []
        pbtxt_lines.append(f'name: "{config["name"]}"')
        pbtxt_lines.append(f'platform: "{config["platform"]}"')
        pbtxt_lines.append(f'max_batch_size: {config["max_batch_size"]}')
        
        for inp in config.get("input", []):
            pbtxt_lines.append("input {")
            pbtxt_lines.append(f'  name: "{inp["name"]}"')
            pbtxt_lines.append(f'  data_type: {inp["data_type"]}')
            dims_str = ", ".join(str(d) for d in inp["dims"])
            pbtxt_lines.append(f'  dims: [ {dims_str} ]')
            pbtxt_lines.append("}")
        
        for out in config.get("output", []):
            pbtxt_lines.append("output {")
            pbtxt_lines.append(f'  name: "{out["name"]}"')
            pbtxt_lines.append(f'  data_type: {out["data_type"]}')
            dims_str = ", ".join(str(d) for d in out["dims"])
            pbtxt_lines.append(f'  dims: [ {dims_str} ]')
            pbtxt_lines.append("}")
        
        for ig in config.get("instance_group", []):
            pbtxt_lines.append("instance_group {")
            pbtxt_lines.append(f'  kind: {ig["kind"]}')
            pbtxt_lines.append(f'  count: {ig["count"]}')
            pbtxt_lines.append("}")
        
        if "dynamic_batching" in config:
            db = config["dynamic_batching"]
            pbtxt_lines.append("dynamic_batching {")
            if "max_queue_delay_microseconds" in db:
                pbtxt_lines.append(f'  max_queue_delay_microseconds: {db["max_queue_delay_microseconds"]}')
            pbtxt_lines.append("}")
        
        with open(config_path, "w") as f:
            f.write("\n".join(pbtxt_lines))
        
        logger.info(f"Wrote config to {config_path}")


class TritonClient:
    """Client for Triton Inference Server"""
    
    def __init__(self, url: str = "localhost:8000"):
        self.url = url
        self._client = None
    
    def _get_client(self):
        """Get or create Triton client"""
        if self._client is None:
            try:
                import tritonclient.http as httpclient
                self._client = httpclient.InferenceServerClient(url=self.url)
            except ImportError:
                logger.warning("tritonclient not installed")
                return None
        return self._client
    
    def is_server_ready(self) -> bool:
        """Check if Triton server is ready"""
        client = self._get_client()
        if client is None:
            return False
        try:
            return client.is_server_ready()
        except Exception:
            return False
    
    def infer_embeddings(self, texts: List[str]) -> np.ndarray:
        """Get embeddings from Triton"""
        client = self._get_client()
        if client is None:
            raise RuntimeError("Triton client not available")
        
        # Tokenize
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
        encoded = tokenizer(texts, padding="max_length", truncation=True, max_length=256, return_tensors="np")
        
        # Create inference request
        import tritonclient.http as httpclient
        
        inputs = [
            httpclient.InferInput("input_ids", encoded["input_ids"].shape, "INT64"),
            httpclient.InferInput("attention_mask", encoded["attention_mask"].shape, "INT64")
        ]
        inputs[0].set_data_from_numpy(encoded["input_ids"])
        inputs[1].set_data_from_numpy(encoded["attention_mask"])
        
        outputs = [httpclient.InferRequestedOutput("last_hidden_state")]
        
        # Run inference
        result = client.infer("embeddings", inputs, outputs=outputs)
        
        # Get pooled embeddings (mean of last hidden state)
        hidden = result.as_numpy("last_hidden_state")
        embeddings = hidden.mean(axis=1)  # Mean pooling
        
        return embeddings
    
    def infer_sentiment(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Get sentiment predictions from Triton"""
        client = self._get_client()
        if client is None:
            raise RuntimeError("Triton client not available")
        
        from transformers import AutoTokenizer
        import tritonclient.http as httpclient
        
        tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
        encoded = tokenizer(texts, padding="max_length", truncation=True, max_length=512, return_tensors="np")
        
        inputs = [
            httpclient.InferInput("input_ids", encoded["input_ids"].shape, "INT64"),
            httpclient.InferInput("attention_mask", encoded["attention_mask"].shape, "INT64")
        ]
        inputs[0].set_data_from_numpy(encoded["input_ids"])
        inputs[1].set_data_from_numpy(encoded["attention_mask"])
        
        outputs = [httpclient.InferRequestedOutput("logits")]
        
        result = client.infer("sentiment_finbert", inputs, outputs=outputs)
        logits = result.as_numpy("logits")
        
        # Convert to predictions
        labels = ["positive", "negative", "neutral"]
        predictions = []
        for i, logit in enumerate(logits):
            probs = np.exp(logit) / np.sum(np.exp(logit))
            idx = np.argmax(probs)
            predictions.append({
                "text": texts[i][:100],
                "label": labels[idx],
                "score": float(probs[idx]),
                "probs": {l: float(p) for l, p in zip(labels, probs)}
            })
        
        return predictions

    def infer_forecast(self, price_history, ticker_id: int = 0) -> Dict[str, Any]:
        """Get forecast prediction from Triton for a price_history numpy array.

        price_history: np.ndarray with shape (batch, seq_len) or (seq_len,) for batch 1
        ticker_id: optional integer ticker id
        """
        client = self._get_client()
        if client is None:
            raise RuntimeError("Triton client not available")

        import tritonclient.http as httpclient
        # Ensure price_history is a 2D array (batch dim)
        import numpy as np
        ph = np.asarray(price_history)
        if ph.ndim == 1:
            ph = ph.reshape(1, -1)

        inputs = [
            httpclient.InferInput("price_history", ph.shape, "FP32"),
            httpclient.InferInput("ticker_id", (ph.shape[0], 1), "INT32")
        ]
        inputs[0].set_data_from_numpy(ph.astype(np.float32))
        # repeat ticker_id for each batch element
        ticker_ids = np.full((ph.shape[0], 1), ticker_id, dtype=np.int32)
        inputs[1].set_data_from_numpy(ticker_ids)
        outputs = [
            httpclient.InferRequestedOutput("forecast"),
            httpclient.InferRequestedOutput("confidence")
        ]
        result = client.infer("forecast_ensemble", inputs, outputs=outputs)
        forecast = result.as_numpy("forecast")
        confidence = result.as_numpy("confidence")
        return {"forecast": forecast.tolist(), "confidence": confidence.tolist()}


def setup_triton_models():
    """Export all models for Triton"""
    exporter = TritonModelExporter()
    
    print("Exporting models for Triton Inference Server...")
    print("=" * 50)
    
    try:
        path = exporter.export_embedding_model()
        print(f"✅ Embeddings model: {path}")
    except Exception as e:
        print(f"❌ Embeddings model: {e}")
    
    try:
        path = exporter.export_finbert_model()
        print(f"✅ FinBERT model: {path}")
    except Exception as e:
        print(f"❌ FinBERT model: {e}")
    
    print("\nModel repository:", TRITON_REPO)
    print("\nTo start Triton server:")
    print(f"  docker run --gpus all -p8000:8000 -p8001:8001 -p8002:8002 \\")
    print(f"    -v {TRITON_REPO}:/models \\")
    print("    nvcr.io/nvidia/tritonserver:24.01-py3 tritonserver --model-repository=/models")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    setup_triton_models()
