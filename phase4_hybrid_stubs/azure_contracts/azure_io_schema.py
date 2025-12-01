"""
Azure I/O Schema Definitions (Phase 4 - Hybrid Readiness)

Schema definitions for JSON I/O and Parquet files that mirror Azure Blob Storage layouts.
Provides versioned schemas with validation and payload verification.

Core Features:
- Versioned schema registry (supports multiple schema versions)
- JSON and Parquet schema definitions
- Payload validation against schemas
- Azure Blob Storage compatible layouts

Usage:
    >>> schema = load_schema(version="0.1")
    >>> is_valid, errors = validate_payload(payload, schema)
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# ============================================================================
# SCHEMA VERSION ENUMERATION
# ============================================================================

class IOSchemaVersion(str, Enum):
    """Supported I/O schema versions."""
    
    V0_1 = "0.1"  # Initial Phase 4 schema
    V0_2 = "0.2"  # Future enhancement
    LATEST = "0.1"  # Alias for most recent
    
    def __str__(self) -> str:
        return self.value
    
    @classmethod
    def from_string(cls, value: str) -> 'IOSchemaVersion':
        """Convert string to IOSchemaVersion."""
        try:
            return cls(value)
        except ValueError:
            logger.warning(f"Unknown schema version '{value}', using LATEST")
            return cls.LATEST


# ============================================================================
# SCHEMA DEFINITIONS
# ============================================================================

# Schema for ML prediction input (JSON)
SCHEMA_PREDICTION_INPUT_V01 = {
    "schema_version": "0.1",
    "schema_type": "prediction_input",
    "required_fields": [
        "job_uuid",
        "ticker",
        "features",
        "date_range",
        "mode"
    ],
    "optional_fields": [
        "model_type",
        "forecast_horizon",
        "confidence_level",
        "explainability",
        "metadata"
    ],
    "field_specs": {
        "job_uuid": {"type": "string", "pattern": r"^[a-f0-9\-]{36}$"},
        "ticker": {"type": "string", "pattern": r"^[A-Z]{1,5}$"},
        "features": {"type": "object", "min_keys": 1},
        "date_range": {"type": "array", "length": 2, "item_type": "string"},
        "mode": {"type": "string", "enum": ["forecast", "backtest", "risk", "optimization", "shap", "batch"]},
        "model_type": {"type": "string", "enum": ["linear_regression", "random_forest", "gradient_boosting", "xgboost", "lightgbm", "neural_network", "ensemble", "time_series_arima", "time_series_prophet", "custom"]},
        "forecast_horizon": {"type": "string", "enum": ["intraday", "daily", "weekly", "biweekly", "monthly", "quarterly", "annual", "custom"]},
        "confidence_level": {"type": "number", "min": 0.0, "max": 1.0},
        "explainability": {"type": "string", "enum": ["none", "basic", "full"]},
        "metadata": {"type": "object"}
    },
    "description": "Input payload for ML prediction jobs (Azure ML compatible)"
}

# Schema for ML prediction output (JSON)
SCHEMA_PREDICTION_OUTPUT_V01 = {
    "schema_version": "0.1",
    "schema_type": "prediction_output",
    "required_fields": [
        "job_uuid",
        "ticker",
        "predictions",
        "confidence",
        "timestamp",
        "status"
    ],
    "optional_fields": [
        "explainability_blob",
        "model_version",
        "latency_ms",
        "metadata",
        "error_message"
    ],
    "field_specs": {
        "job_uuid": {"type": "string", "pattern": r"^[a-f0-9\-]{36}$"},
        "ticker": {"type": "string", "pattern": r"^[A-Z]{1,5}$"},
        "predictions": {"type": "array", "min_length": 1, "item_type": "number"},
        "confidence": {"type": "array", "min_length": 1, "item_type": "number"},
        "timestamp": {"type": "string", "format": "iso8601"},
        "status": {"type": "string", "enum": ["queued", "running", "completed", "failed", "canceled"]},
        "explainability_blob": {"type": "object"},
        "model_version": {"type": "string"},
        "latency_ms": {"type": "number", "min": 0.0},
        "metadata": {"type": "object"},
        "error_message": {"type": "string"}
    },
    "constraints": [
        {
            "name": "predictions_confidence_length_match",
            "description": "predictions and confidence arrays must have same length",
            "validation": "len(predictions) == len(confidence)"
        },
        {
            "name": "failed_status_requires_error",
            "description": "If status is 'failed', error_message must be present",
            "validation": "status != 'failed' or error_message is not None"
        }
    ],
    "description": "Output payload from ML prediction jobs (Azure ML compatible)"
}

# Schema for SHAP explainability data (JSON)
SCHEMA_SHAP_EXPLAINABILITY_V01 = {
    "schema_version": "0.1",
    "schema_type": "shap_explainability",
    "required_fields": [
        "job_uuid",
        "ticker",
        "shap_values",
        "feature_importance"
    ],
    "optional_fields": [
        "base_value",
        "expected_value",
        "textual_rationale",
        "plot_data"
    ],
    "field_specs": {
        "job_uuid": {"type": "string"},
        "ticker": {"type": "string"},
        "shap_values": {"type": "object", "description": "Dict of feature -> SHAP value"},
        "feature_importance": {"type": "array", "item_type": "object"},
        "base_value": {"type": "number"},
        "expected_value": {"type": "number"},
        "textual_rationale": {"type": "string"},
        "plot_data": {"type": "object"}
    },
    "description": "SHAP explainability data for ML predictions"
}

# Schema for Parquet storage layout (Azure Blob Storage compatible)
SCHEMA_PARQUET_LAYOUT_V01 = {
    "schema_version": "0.1",
    "schema_type": "parquet_layout",
    "description": "Azure Blob Storage compatible Parquet file layout",
    "directory_structure": {
        "predictions": "predictions/{year}/{month}/{day}/predictions_{ticker}_{timestamp}.parquet",
        "shap": "explainability/shap/{year}/{month}/{day}/shap_{ticker}_{timestamp}.parquet",
        "backtest": "backtest/{year}/{month}/{day}/backtest_{ticker}_{timestamp}.parquet",
        "risk": "risk/{year}/{month}/{day}/risk_{ticker}_{timestamp}.parquet"
    },
    "partition_keys": ["year", "month", "day", "ticker"],
    "compression": "snappy",
    "columns": {
        "predictions": [
            {"name": "job_uuid", "type": "string"},
            {"name": "ticker", "type": "string"},
            {"name": "prediction_date", "type": "date"},
            {"name": "predicted_value", "type": "float"},
            {"name": "confidence", "type": "float"},
            {"name": "model_version", "type": "string"},
            {"name": "created_at", "type": "timestamp"}
        ],
        "shap": [
            {"name": "job_uuid", "type": "string"},
            {"name": "ticker", "type": "string"},
            {"name": "feature_name", "type": "string"},
            {"name": "shap_value", "type": "float"},
            {"name": "feature_value", "type": "float"},
            {"name": "created_at", "type": "timestamp"}
        ]
    }
}

# Schema registry mapping
SCHEMA_REGISTRY = {
    "0.1": {
        "prediction_input": SCHEMA_PREDICTION_INPUT_V01,
        "prediction_output": SCHEMA_PREDICTION_OUTPUT_V01,
        "shap_explainability": SCHEMA_SHAP_EXPLAINABILITY_V01,
        "parquet_layout": SCHEMA_PARQUET_LAYOUT_V01
    }
}


# ============================================================================
# SCHEMA LOADING & VALIDATION
# ============================================================================

def load_schema(
    version: str = "0.1",
    schema_type: str = "prediction_input"
) -> Dict[str, Any]:
    """
    Load schema definition from registry.
    
    Args:
        version: Schema version (default: "0.1")
        schema_type: Type of schema to load
            ('prediction_input', 'prediction_output', 'shap_explainability', 'parquet_layout')
    
    Returns:
        Schema definition dictionary
    
    Raises:
        ValueError: If version or schema_type not found
    
    Example:
        >>> schema = load_schema(version="0.1", schema_type="prediction_input")
        >>> print(schema['required_fields'])
    """
    # Normalize version
    version_enum = IOSchemaVersion.from_string(version)
    version_str = str(version_enum)
    
    if version_str not in SCHEMA_REGISTRY:
        raise ValueError(f"Unknown schema version: {version_str}")
    
    version_schemas = SCHEMA_REGISTRY[version_str]
    
    if schema_type not in version_schemas:
        available = list(version_schemas.keys())
        raise ValueError(
            f"Unknown schema type '{schema_type}' for version {version_str}. "
            f"Available: {available}"
        )
    
    schema = version_schemas[schema_type]
    logger.debug(f"Loaded schema: {schema_type} v{version_str}")
    
    return schema


def validate_payload(
    payload: Dict[str, Any],
    schema: Optional[Dict[str, Any]] = None,
    schema_version: str = "0.1",
    schema_type: str = "prediction_input"
) -> Tuple[bool, List[str]]:
    """
    Validate payload against schema.
    
    Args:
        payload: Data payload to validate
        schema: Schema definition (if None, will load from registry)
        schema_version: Schema version to use if schema not provided
        schema_type: Schema type to use if schema not provided
    
    Returns:
        Tuple of (is_valid, error_messages)
    
    Example:
        >>> payload = {'job_uuid': '...', 'ticker': 'AAPL', 'features': {...}, ...}
        >>> is_valid, errors = validate_payload(payload, schema_type='prediction_input')
        >>> if not is_valid:
        ...     print(f"Validation errors: {errors}")
    """
    errors = []
    
    # Load schema if not provided
    if schema is None:
        try:
            schema = load_schema(version=schema_version, schema_type=schema_type)
        except ValueError as e:
            return False, [str(e)]
    
    # Check required fields
    required_fields = schema.get('required_fields', [])
    for field in required_fields:
        if field not in payload:
            errors.append(f"Missing required field: '{field}'")
    
    # Validate field specifications
    field_specs = schema.get('field_specs', {})
    for field_name, field_spec in field_specs.items():
        if field_name not in payload:
            # Skip optional fields
            if field_name not in required_fields:
                continue
            # Already caught by required_fields check
            continue
        
        value = payload[field_name]
        
        # Type validation
        expected_type = field_spec.get('type')
        if expected_type:
            type_valid = _validate_field_type(value, expected_type, field_name)
            if not type_valid[0]:
                errors.append(type_valid[1])
        
        # Enum validation
        if 'enum' in field_spec:
            if value not in field_spec['enum']:
                errors.append(
                    f"Field '{field_name}' value '{value}' not in allowed values: {field_spec['enum']}"
                )
        
        # Numeric range validation
        if expected_type == 'number':
            if 'min' in field_spec and value < field_spec['min']:
                errors.append(f"Field '{field_name}' value {value} < min {field_spec['min']}")
            if 'max' in field_spec and value > field_spec['max']:
                errors.append(f"Field '{field_name}' value {value} > max {field_spec['max']}")
        
        # Array length validation
        if expected_type == 'array':
            if 'length' in field_spec and len(value) != field_spec['length']:
                errors.append(
                    f"Field '{field_name}' array length {len(value)} != expected {field_spec['length']}"
                )
            if 'min_length' in field_spec and len(value) < field_spec['min_length']:
                errors.append(
                    f"Field '{field_name}' array length {len(value)} < min {field_spec['min_length']}"
                )
        
        # Object validation
        if expected_type == 'object':
            if 'min_keys' in field_spec and len(value) < field_spec['min_keys']:
                errors.append(
                    f"Field '{field_name}' object has {len(value)} keys, min required: {field_spec['min_keys']}"
                )
    
    # Custom constraints
    constraints = schema.get('constraints', [])
    for constraint in constraints:
        # Note: Advanced constraint validation would require eval or custom logic
        # For Phase 4, we implement basic checks manually
        if constraint['name'] == 'predictions_confidence_length_match':
            if 'predictions' in payload and 'confidence' in payload:
                if len(payload['predictions']) != len(payload['confidence']):
                    errors.append(constraint['description'])
        
        if constraint['name'] == 'failed_status_requires_error':
            if payload.get('status') == 'failed' and not payload.get('error_message'):
                errors.append(constraint['description'])
    
    is_valid = len(errors) == 0
    
    if is_valid:
        logger.debug(f"Payload validation PASSED for schema {schema.get('schema_type')}")
    else:
        logger.warning(f"Payload validation FAILED with {len(errors)} errors")
    
    return is_valid, errors


def _validate_field_type(
    value: Any,
    expected_type: str,
    field_name: str
) -> Tuple[bool, str]:
    """
    Validate field type.
    
    Args:
        value: Field value
        expected_type: Expected type name ('string', 'number', 'array', 'object', 'boolean')
        field_name: Field name for error messages
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    type_checks = {
        'string': lambda v: isinstance(v, str),
        'number': lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        'integer': lambda v: isinstance(v, int) and not isinstance(v, bool),
        'boolean': lambda v: isinstance(v, bool),
        'array': lambda v: isinstance(v, list),
        'object': lambda v: isinstance(v, dict),
        'null': lambda v: v is None
    }
    
    check = type_checks.get(expected_type)
    if not check:
        return True, ""  # Unknown type, skip check
    
    if not check(value):
        actual_type = type(value).__name__
        return False, f"Field '{field_name}' expected type '{expected_type}', got '{actual_type}'"
    
    return True, ""


# ============================================================================
# AZURE BLOB STORAGE PATH UTILITIES
# ============================================================================

def generate_blob_path(
    schema_type: str,
    ticker: str,
    timestamp: Optional[datetime] = None,
    **kwargs
) -> str:
    """
    Generate Azure Blob Storage compatible file path.
    
    Args:
        schema_type: Type of data ('predictions', 'shap', 'backtest', 'risk')
        ticker: Stock symbol
        timestamp: Timestamp for partitioning (default: now)
        **kwargs: Additional path parameters
    
    Returns:
        Blob storage path string
    
    Example:
        >>> path = generate_blob_path('predictions', 'AAPL')
        >>> # Returns: 'predictions/2025/10/29/predictions_AAPL_20251029_143522.parquet'
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    year = timestamp.strftime('%Y')
    month = timestamp.strftime('%m')
    day = timestamp.strftime('%d')
    timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S')
    
    # Load parquet layout schema
    layout_schema = load_schema(version="0.1", schema_type="parquet_layout")
    directory_structure = layout_schema['directory_structure']
    
    if schema_type not in directory_structure:
        raise ValueError(f"Unknown schema_type for blob path: {schema_type}")
    
    template = directory_structure[schema_type]
    
    # Format path
    path = template.format(
        year=year,
        month=month,
        day=day,
        ticker=ticker.upper(),
        timestamp=timestamp_str,
        **kwargs
    )
    
    return path


def parse_blob_path(blob_path: str) -> Dict[str, str]:
    """
    Parse blob storage path to extract metadata.
    
    Args:
        blob_path: Blob storage path string
    
    Returns:
        Dictionary with extracted metadata (year, month, day, ticker, timestamp)
    
    Example:
        >>> metadata = parse_blob_path('predictions/2025/10/29/predictions_AAPL_20251029_143522.parquet')
        >>> print(metadata['ticker'])  # 'AAPL'
    """
    parts = blob_path.split('/')
    
    metadata = {}
    
    # Extract partition keys if present
    if len(parts) >= 4:
        metadata['schema_type'] = parts[0]
        metadata['year'] = parts[1] if parts[1].isdigit() else None
        metadata['month'] = parts[2] if parts[2].isdigit() else None
        metadata['day'] = parts[3] if parts[3].isdigit() else None
    
    # Extract filename metadata
    filename = parts[-1]
    if '_' in filename:
        filename_parts = filename.replace('.parquet', '').split('_')
        if len(filename_parts) >= 3:
            metadata['ticker'] = filename_parts[1]
            metadata['timestamp'] = '_'.join(filename_parts[2:])
    
    return metadata


# ============================================================================
# SCHEMA DOCUMENTATION
# ============================================================================

def generate_schema_docs(output_path: Optional[Path] = None) -> str:
    """
    Generate Markdown documentation for all schemas.
    
    Args:
        output_path: Path to save documentation (None = return as string)
    
    Returns:
        Markdown documentation string
    """
    docs = []
    docs.append("# Azure I/O Schema Documentation\n")
    docs.append(f"**Generated:** {datetime.now().isoformat()}\n")
    docs.append("**Phase:** 4 - Hybrid Readiness\n")
    docs.append("\n---\n")
    
    for version, schemas in SCHEMA_REGISTRY.items():
        docs.append(f"\n## Schema Version {version}\n")
        
        for schema_type, schema in schemas.items():
            docs.append(f"\n### {schema_type}\n")
            docs.append(f"\n**Description:** {schema.get('description', 'N/A')}\n")
            
            # Required fields
            if 'required_fields' in schema:
                docs.append("\n**Required Fields:**\n")
                for field in schema['required_fields']:
                    spec = schema.get('field_specs', {}).get(field, {})
                    field_type = spec.get('type', 'any')
                    docs.append(f"- `{field}` ({field_type})\n")
            
            # Optional fields
            if 'optional_fields' in schema:
                docs.append("\n**Optional Fields:**\n")
                for field in schema['optional_fields']:
                    spec = schema.get('field_specs', {}).get(field, {})
                    field_type = spec.get('type', 'any')
                    docs.append(f"- `{field}` ({field_type})\n")
            
            # Constraints
            if 'constraints' in schema:
                docs.append("\n**Constraints:**\n")
                for constraint in schema['constraints']:
                    docs.append(f"- {constraint['description']}\n")
            
            docs.append("\n")
    
    doc_str = "".join(docs)
    
    if output_path:
        output_path.write_text(doc_str)
        logger.info(f"Schema documentation saved to {output_path}")
    
    return doc_str


logger.info("✓ Azure I/O Schema loaded (Phase 4 - Hybrid Readiness)")
