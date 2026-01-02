"""
ONNX Model Exporter for Triton Server
Phase 11 - Agent-Serving

Exports PyTorch and XGBoost models to ONNX format for Triton deployment.
Output structure: model_repository/<model_name>/1/model.onnx
"""

import os
import json
import logging
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Model repository path (relative to project root)
MODEL_REPOSITORY = Path(__file__).parent.parent.parent / "model_repository"


class ONNXExporter:
    """Export ML models to ONNX format for Triton Inference Server."""

    def __init__(self, model_repository: Optional[Path] = None):
        """
        Initialize the ONNX exporter.
        
        Args:
            model_repository: Path to Triton model repository. 
                              Defaults to project's model_repository.
        """
        self.model_repository = model_repository or MODEL_REPOSITORY
        self.model_repository.mkdir(parents=True, exist_ok=True)
        logger.info(f"ONNX Exporter initialized. Model repo: {self.model_repository}")

    def export_pytorch_model(
        self,
        model,
        model_name: str,
        input_shape: Tuple[int, ...] = (1, 50),
        input_dtype: str = "float32",
        output_names: Optional[list] = None,
        dynamic_axes: Optional[Dict[str, Dict[int, str]]] = None,
        opset_version: int = 14,
    ) -> Path:
        """
        Export a PyTorch model to ONNX format.
        
        Args:
            model: PyTorch model (nn.Module)
            model_name: Name for the exported model
            input_shape: Shape of input tensor (batch, features)
            input_dtype: Data type of input
            output_names: Names for output tensors
            dynamic_axes: Dynamic axes specification for variable batch size
            opset_version: ONNX opset version
            
        Returns:
            Path to exported ONNX model
        """
        try:
            import torch
            import torch.onnx
        except ImportError:
            logger.error("PyTorch not installed. Cannot export PyTorch models.")
            raise ImportError("torch required for PyTorch model export")

        # Create model directory structure
        model_dir = self.model_repository / model_name / "1"
        model_dir.mkdir(parents=True, exist_ok=True)
        onnx_path = model_dir / "model.onnx"

        # Prepare model for export
        model.eval()
        
        # Create dummy input
        if input_dtype == "float32":
            dummy_input = torch.randn(*input_shape, dtype=torch.float32)
        elif input_dtype == "float64":
            dummy_input = torch.randn(*input_shape, dtype=torch.float64)
        else:
            dummy_input = torch.randn(*input_shape)

        # Default dynamic axes for batch dimension
        if dynamic_axes is None:
            dynamic_axes = {
                "input": {0: "batch_size"},
                "output": {0: "batch_size"}
            }

        # Export to ONNX
        torch.onnx.export(
            model,
            dummy_input,
            str(onnx_path),
            export_params=True,
            opset_version=opset_version,
            do_constant_folding=True,
            input_names=["input"],
            output_names=output_names or ["output"],
            dynamic_axes=dynamic_axes,
        )

        logger.info(f"PyTorch model exported to {onnx_path}")
        
        # Create config.pbtxt for this model
        self._create_model_config(model_name, input_shape, input_dtype)
        
        return onnx_path

    def export_xgboost_model(
        self,
        model,
        model_name: str,
        n_features: int = 50,
        input_dtype: str = "float32",
    ) -> Path:
        """
        Export an XGBoost model to ONNX format.
        
        Args:
            model: XGBoost model (Booster or sklearn wrapper)
            model_name: Name for the exported model
            n_features: Number of input features
            input_dtype: Data type of input
            
        Returns:
            Path to exported ONNX model
        """
        try:
            from onnxmltools import convert_xgboost
            from onnxmltools.convert.common.data_types import FloatTensorType
        except ImportError:
            logger.error("onnxmltools not installed. Falling back to sklearn conversion.")
            return self._export_xgboost_sklearn(model, model_name, n_features, input_dtype)

        # Create model directory structure
        model_dir = self.model_repository / model_name / "1"
        model_dir.mkdir(parents=True, exist_ok=True)
        onnx_path = model_dir / "model.onnx"

        # Define input type
        if input_dtype == "float32":
            initial_type = [("input", FloatTensorType([None, n_features]))]
        else:
            initial_type = [("input", FloatTensorType([None, n_features]))]

        # Convert to ONNX
        onnx_model = convert_xgboost(model, initial_types=initial_type)
        
        # Save ONNX model
        with open(onnx_path, "wb") as f:
            f.write(onnx_model.SerializeToString())

        logger.info(f"XGBoost model exported to {onnx_path}")
        
        # Create config.pbtxt for this model
        self._create_model_config(model_name, (1, n_features), input_dtype)
        
        return onnx_path

    def _export_xgboost_sklearn(
        self,
        model,
        model_name: str,
        n_features: int,
        input_dtype: str,
    ) -> Path:
        """
        Fallback: Export XGBoost model via sklearn-onnx.
        """
        try:
            from skl2onnx import convert_sklearn
            from skl2onnx.common.data_types import FloatTensorType
        except ImportError:
            logger.error("skl2onnx not installed. Cannot export XGBoost model.")
            raise ImportError("skl2onnx required for XGBoost model export")

        # Create model directory structure
        model_dir = self.model_repository / model_name / "1"
        model_dir.mkdir(parents=True, exist_ok=True)
        onnx_path = model_dir / "model.onnx"

        # Define input type
        initial_type = [("input", FloatTensorType([None, n_features]))]

        # Convert to ONNX
        onnx_model = convert_sklearn(model, initial_types=initial_type)
        
        # Save ONNX model
        with open(onnx_path, "wb") as f:
            f.write(onnx_model.SerializeToString())

        logger.info(f"XGBoost model (via sklearn) exported to {onnx_path}")
        
        # Create config.pbtxt for this model
        self._create_model_config(model_name, (1, n_features), input_dtype)
        
        return onnx_path

    def export_simple_model(
        self,
        model_name: str,
        input_shape: Tuple[int, ...] = (1, 50),
        output_shape: Tuple[int, ...] = (1,),
        input_dtype: str = "float32",
    ) -> Path:
        """
        Create a simple dummy ONNX model for testing Triton integration.
        
        This creates a minimal ONNX model that just passes input through,
        useful for testing the Triton client without real models.
        
        Args:
            model_name: Name for the model
            input_shape: Shape of input tensor
            output_shape: Shape of output tensor
            input_dtype: Data type
            
        Returns:
            Path to exported ONNX model
        """
        try:
            import onnx
            from onnx import helper, TensorProto
        except ImportError:
            logger.error("onnx package not installed")
            raise ImportError("onnx required for model export")

        # Create model directory structure
        model_dir = self.model_repository / model_name / "1"
        model_dir.mkdir(parents=True, exist_ok=True)
        onnx_path = model_dir / "model.onnx"

        # Map dtype string to TensorProto
        dtype_map = {
            "float32": TensorProto.FLOAT,
            "float64": TensorProto.DOUBLE,
            "int32": TensorProto.INT32,
            "int64": TensorProto.INT64,
        }
        tensor_dtype = dtype_map.get(input_dtype, TensorProto.FLOAT)

        # Create a simple identity model that reduces to output shape
        # Input: [batch, 50] -> Output: [batch, 1]
        X = helper.make_tensor_value_info("input", tensor_dtype, [None, input_shape[1]])
        Y = helper.make_tensor_value_info("output", tensor_dtype, [None, output_shape[0] if len(output_shape) > 0 else 1])

        # Create a ReduceMean node to go from [batch, 50] -> [batch, 1]
        reduce_node = helper.make_node(
            "ReduceMean",
            inputs=["input"],
            outputs=["output"],
            axes=[1],
            keepdims=True,
        )

        # Create the graph
        graph_def = helper.make_graph(
            [reduce_node],
            f"{model_name}_graph",
            [X],
            [Y],
        )

        # Create the model
        model_def = helper.make_model(graph_def, producer_name="triton_exporter")
        model_def.opset_import[0].version = 11
        model_def.ir_version = 6  # Compatible with older ONNX Runtime

        # Validate and save
        onnx.checker.check_model(model_def)
        onnx.save(model_def, str(onnx_path))

        logger.info(f"Simple ONNX model exported to {onnx_path}")
        
        # Create config.pbtxt for this model
        self._create_model_config(model_name, input_shape, input_dtype, output_shape)
        
        return onnx_path

    def _create_model_config(
        self,
        model_name: str,
        input_shape: Tuple[int, ...],
        input_dtype: str = "float32",
        output_shape: Tuple[int, ...] = (1,),
    ) -> Path:
        """
        Create Triton model config.pbtxt file.
        
        Args:
            model_name: Name of the model
            input_shape: Shape of input tensor (without batch dim for config)
            input_dtype: Data type string
            output_shape: Shape of output tensor
            
        Returns:
            Path to config file
        """
        model_dir = self.model_repository / model_name
        config_path = model_dir / "config.pbtxt"

        # Map dtype to Triton format
        dtype_triton_map = {
            "float32": "TYPE_FP32",
            "float64": "TYPE_FP64",
            "int32": "TYPE_INT32",
            "int64": "TYPE_INT64",
        }
        triton_dtype = dtype_triton_map.get(input_dtype, "TYPE_FP32")

        # Build config content
        # Note: Triton config dims exclude batch dimension (it's implicit)
        input_dims = input_shape[1] if len(input_shape) > 1 else input_shape[0]
        output_dims = output_shape[0] if len(output_shape) > 0 else 1

        config_content = f'''name: "{model_name}"
platform: "onnxruntime_onnx"
max_batch_size: 64
input [
  {{
    name: "input"
    data_type: {triton_dtype}
    dims: [{input_dims}]
  }}
]
output [
  {{
    name: "output"
    data_type: {triton_dtype}
    dims: [{output_dims}]
  }}
]
instance_group [
  {{
    count: 1
    kind: KIND_CPU
  }}
]
dynamic_batching {{
  preferred_batch_size: [1, 8, 16, 32]
  max_queue_delay_microseconds: 100
}}
'''

        with open(config_path, "w") as f:
            f.write(config_content)

        logger.info(f"Model config created at {config_path}")
        return config_path


def create_test_models():
    """Create test models for Triton validation."""
    exporter = ONNXExporter()
    
    # Create signal model (price history -> signal)
    signal_path = exporter.export_simple_model(
        model_name="signal_model",
        input_shape=(1, 50),
        output_shape=(1,),
        input_dtype="float32",
    )
    
    # Create volatility model
    volatility_path = exporter.export_simple_model(
        model_name="volatility_model",
        input_shape=(1, 50),
        output_shape=(1,),
        input_dtype="float32",
    )
    
    return {
        "signal_model": str(signal_path),
        "volatility_model": str(volatility_path),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    paths = create_test_models()
    print(json.dumps(paths, indent=2))
