"""
Azure Contract Definitions (Phase 4 - Hybrid Readiness)

Defines standard contracts between the dashboard and Azure ML services.
All ML interactions must conform to these contracts for Azure compatibility.

Core Contracts:
- ContractInputSpec: Standardized input for ML jobs
- ContractOutputSpec: Standardized output from ML jobs
- ModelType: Enumeration of supported model types
- ForecastHorizon: Enumeration of forecast time horizons

Usage:
    >>> input_spec = ContractInputSpec(
    ...     ticker='AAPL',
    ...     features={'momentum_20d': 0.05, 'volatility_20d': 0.15},
    ...     date_range=('2025-01-01', '2025-10-29'),
    ...     mode='forecast',
    ...     uuid='job-12345'
    ... )
    >>> json_str = contract_to_json(input_spec)
    >>> is_valid = validate_contract(input_spec)
"""

import json
import uuid as uuid_lib
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, date
from enum import Enum
import hashlib
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# ENUMERATIONS
# ============================================================================

class ModelType(str, Enum):
    """Supported ML model types for Azure ML deployment."""
    
    LINEAR_REGRESSION = "linear_regression"
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    NEURAL_NETWORK = "neural_network"
    ENSEMBLE = "ensemble"
    TIME_SERIES_ARIMA = "time_series_arima"
    TIME_SERIES_PROPHET = "time_series_prophet"
    CUSTOM = "custom"
    
    def __str__(self) -> str:
        return self.value
    
    @classmethod
    def from_string(cls, value: str) -> 'ModelType':
        """Convert string to ModelType enum."""
        try:
            return cls(value.lower())
        except ValueError:
            logger.warning(f"Unknown model type '{value}', defaulting to CUSTOM")
            return cls.CUSTOM


class ForecastHorizon(str, Enum):
    """Supported forecast time horizons."""
    
    INTRADAY = "intraday"  # Hours
    DAILY = "daily"  # 1 day
    WEEKLY = "weekly"  # 5-7 days
    BIWEEKLY = "biweekly"  # 10-14 days
    MONTHLY = "monthly"  # 20-30 days
    QUARTERLY = "quarterly"  # 60-90 days
    ANNUAL = "annual"  # 252 trading days
    CUSTOM = "custom"  # User-defined
    
    def __str__(self) -> str:
        return self.value
    
    @classmethod
    def from_string(cls, value: str) -> 'ForecastHorizon':
        """Convert string to ForecastHorizon enum."""
        try:
            return cls(value.lower())
        except ValueError:
            logger.warning(f"Unknown horizon '{value}', defaulting to CUSTOM")
            return cls.CUSTOM
    
    def to_days(self) -> int:
        """Convert horizon to approximate number of days."""
        mapping = {
            self.INTRADAY: 1,
            self.DAILY: 1,
            self.WEEKLY: 7,
            self.BIWEEKLY: 14,
            self.MONTHLY: 30,
            self.QUARTERLY: 90,
            self.ANNUAL: 252,
            self.CUSTOM: 30  # Default
        }
        return mapping.get(self, 30)


class JobStatus(str, Enum):
    """Azure ML job status enumeration."""
    
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    
    def __str__(self) -> str:
        return self.value


class ExplainabilityLevel(str, Enum):
    """Level of explainability requested for predictions."""
    
    NONE = "none"  # No explainability
    BASIC = "basic"  # Feature importance only
    FULL = "full"  # SHAP values + narratives
    
    def __str__(self) -> str:
        return self.value


# ============================================================================
# INPUT CONTRACT
# ============================================================================

@dataclass
class ContractInputSpec:
    """
    Standard input contract for all Azure ML jobs.
    
    This contract ensures consistent I/O across local stubs and real Azure ML.
    
    Attributes:
        ticker: Stock symbol or asset identifier (e.g., 'AAPL', 'SPY')
        features: Dictionary of feature name -> value pairs
        date_range: Tuple of (start_date, end_date) as ISO strings or date objects
        mode: Job type ('forecast', 'backtest', 'risk', 'optimization', 'shap')
        uuid: Unique job identifier (auto-generated if not provided)
        model_type: ML model to use (default: RANDOM_FOREST)
        forecast_horizon: Time horizon for predictions
        confidence_level: Confidence level for predictions (0.0-1.0)
        explainability: Level of explainability requested
        metadata: Additional job metadata (tags, user_id, etc.)
        created_at: Timestamp of contract creation (auto-generated)
    
    Example:
        >>> spec = ContractInputSpec(
        ...     ticker='AAPL',
        ...     features={'momentum_20d': 0.05, 'pe_ratio': 28.5},
        ...     date_range=('2025-01-01', '2025-10-29'),
        ...     mode='forecast'
        ... )
    """
    
    ticker: str
    features: Dict[str, Union[float, int, str]]
    date_range: Tuple[str, str]
    mode: str  # 'forecast', 'backtest', 'risk', 'optimization', 'shap'
    uuid: str = field(default_factory=lambda: str(uuid_lib.uuid4()))
    model_type: ModelType = ModelType.RANDOM_FOREST
    forecast_horizon: ForecastHorizon = ForecastHorizon.MONTHLY
    confidence_level: float = 0.95
    explainability: ExplainabilityLevel = ExplainabilityLevel.BASIC
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def __post_init__(self):
        """Validate and normalize fields after initialization."""
        # Ensure ticker is uppercase
        self.ticker = self.ticker.upper()
        
        # Convert model_type string to enum if needed
        if isinstance(self.model_type, str):
            self.model_type = ModelType.from_string(self.model_type)
        
        # Convert forecast_horizon string to enum if needed
        if isinstance(self.forecast_horizon, str):
            self.forecast_horizon = ForecastHorizon.from_string(self.forecast_horizon)
        
        # Convert explainability string to enum if needed
        if isinstance(self.explainability, str):
            try:
                self.explainability = ExplainabilityLevel(self.explainability.lower())
            except ValueError:
                self.explainability = ExplainabilityLevel.BASIC
        
        # Validate confidence level
        if not 0.0 <= self.confidence_level <= 1.0:
            raise ValueError(f"confidence_level must be in [0, 1], got {self.confidence_level}")
        
        # Validate mode
        valid_modes = ['forecast', 'backtest', 'risk', 'optimization', 'shap', 'batch']
        if self.mode not in valid_modes:
            raise ValueError(f"mode must be one of {valid_modes}, got {self.mode}")
        
        # Validate date_range format
        if len(self.date_range) != 2:
            raise ValueError(f"date_range must be a tuple of (start, end), got {self.date_range}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with enum serialization."""
        data = asdict(self)
        data['model_type'] = str(self.model_type)
        data['forecast_horizon'] = str(self.forecast_horizon)
        data['explainability'] = str(self.explainability)
        return data
    
    def compute_hash(self) -> str:
        """Compute deterministic hash for caching/deduplication."""
        # Use sorted JSON for deterministic hashing
        data = self.to_dict()
        # Remove timestamp and uuid for content-based hashing
        data_copy = {k: v for k, v in data.items() if k not in ['uuid', 'created_at']}
        json_str = json.dumps(data_copy, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()[:16]
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """
        Validate contract integrity.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check required fields are non-empty
            if not self.ticker:
                return False, "ticker cannot be empty"
            
            if not self.features:
                return False, "features dictionary cannot be empty"
            
            # Validate feature values are numeric or string
            for key, value in self.features.items():
                if not isinstance(value, (int, float, str)):
                    return False, f"feature '{key}' has invalid type {type(value)}"
            
            # Validate date range
            try:
                start, end = self.date_range
                datetime.fromisoformat(start.replace('Z', '+00:00'))
                datetime.fromisoformat(end.replace('Z', '+00:00'))
            except (ValueError, TypeError) as e:
                return False, f"Invalid date_range format: {e}"
            
            return True, None
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"


# ============================================================================
# OUTPUT CONTRACT
# ============================================================================

@dataclass
class ContractOutputSpec:
    """
    Standard output contract for all Azure ML jobs.
    
    Attributes:
        job_uuid: Matches input contract uuid
        ticker: Stock symbol (echoed from input)
        predictions: List of predicted values
        confidence: Confidence scores (same length as predictions)
        timestamp: Job completion timestamp
        explainability_blob: JSON blob with SHAP values, feature importance, etc.
        status: Job status (completed, failed, etc.)
        model_version: Version of model used
        latency_ms: Job execution time in milliseconds
        metadata: Additional output metadata
    
    Example:
        >>> output = ContractOutputSpec(
        ...     job_uuid='job-12345',
        ...     ticker='AAPL',
        ...     predictions=[0.05, 0.08, 0.12],
        ...     confidence=[0.85, 0.82, 0.79],
        ...     explainability_blob={'shap_values': {...}, 'feature_importance': [...]}
        ... )
    """
    
    job_uuid: str
    ticker: str
    predictions: List[float]
    confidence: List[float]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    explainability_blob: Optional[Dict[str, Any]] = None
    status: JobStatus = JobStatus.COMPLETED
    model_version: str = "1.0.0"
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """Validate output contract."""
        # Convert status string to enum if needed
        if isinstance(self.status, str):
            try:
                self.status = JobStatus(self.status.lower())
            except ValueError:
                self.status = JobStatus.FAILED
        
        # Validate predictions and confidence have same length
        if len(self.predictions) != len(self.confidence):
            raise ValueError(
                f"predictions and confidence must have same length: "
                f"{len(self.predictions)} != {len(self.confidence)}"
            )
        
        # Ensure ticker is uppercase
        self.ticker = self.ticker.upper()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with enum serialization."""
        data = asdict(self)
        data['status'] = str(self.status)
        return data
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """
        Validate output contract integrity.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check required fields
            if not self.job_uuid:
                return False, "job_uuid cannot be empty"
            
            if not self.ticker:
                return False, "ticker cannot be empty"
            
            if not self.predictions:
                return False, "predictions list cannot be empty"
            
            # Validate confidence values are in [0, 1]
            for i, conf in enumerate(self.confidence):
                if not 0.0 <= conf <= 1.0:
                    return False, f"confidence[{i}] = {conf} is not in [0, 1]"
            
            # If status is FAILED, error_message should be present
            if self.status == JobStatus.FAILED and not self.error_message:
                return False, "error_message required when status=FAILED"
            
            return True, None
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def contract_to_json(
    contract: Union[ContractInputSpec, ContractOutputSpec],
    indent: Optional[int] = 2
) -> str:
    """
    Serialize contract to JSON string.
    
    Args:
        contract: Input or output contract
        indent: JSON indentation (None for compact)
    
    Returns:
        JSON string representation
    
    Example:
        >>> spec = ContractInputSpec(ticker='AAPL', features={}, date_range=('2025-01-01', '2025-12-31'), mode='forecast')
        >>> json_str = contract_to_json(spec)
    """
    try:
        data = contract.to_dict()
        return json.dumps(data, indent=indent, default=str)
    except Exception as e:
        logger.exception(f"Failed to serialize contract: {e}")
        raise


def contract_from_json(
    json_str: str,
    contract_type: str = "input"
) -> Union[ContractInputSpec, ContractOutputSpec]:
    """
    Deserialize JSON string to contract object.
    
    Args:
        json_str: JSON string
        contract_type: 'input' or 'output'
    
    Returns:
        ContractInputSpec or ContractOutputSpec
    
    Example:
        >>> json_str = '{"ticker": "AAPL", ...}'
        >>> spec = contract_from_json(json_str, "input")
    """
    try:
        data = json.loads(json_str)
        
        if contract_type == "input":
            return ContractInputSpec(**data)
        elif contract_type == "output":
            return ContractOutputSpec(**data)
        else:
            raise ValueError(f"Unknown contract_type: {contract_type}")
            
    except Exception as e:
        logger.exception(f"Failed to deserialize contract: {e}")
        raise


def validate_contract(
    contract: Union[ContractInputSpec, ContractOutputSpec]
) -> Tuple[bool, Optional[str]]:
    """
    Validate contract integrity.
    
    Args:
        contract: Input or output contract
    
    Returns:
        Tuple of (is_valid, error_message)
    
    Example:
        >>> spec = ContractInputSpec(ticker='AAPL', features={'momentum': 0.5}, date_range=('2025-01-01', '2025-12-31'), mode='forecast')
        >>> is_valid, error = validate_contract(spec)
        >>> assert is_valid
    """
    return contract.validate()


def create_mock_input(
    ticker: str = "AAPL",
    mode: str = "forecast"
) -> ContractInputSpec:
    """
    Create mock input contract for testing.
    
    Args:
        ticker: Stock symbol
        mode: Job mode
    
    Returns:
        ContractInputSpec with realistic mock data
    """
    return ContractInputSpec(
        ticker=ticker,
        features={
            'momentum_20d': 0.05,
            'volatility_20d': 0.18,
            'sharpe_20d': 1.2,
            'pe_ratio': 28.5,
            'market_cap': 3.2e12,
            'beta': 1.15
        },
        date_range=('2025-01-01', '2025-10-29'),
        mode=mode,
        model_type=ModelType.RANDOM_FOREST,
        forecast_horizon=ForecastHorizon.MONTHLY,
        explainability=ExplainabilityLevel.FULL
    )


def create_mock_output(
    job_uuid: str,
    ticker: str = "AAPL",
    num_predictions: int = 30
) -> ContractOutputSpec:
    """
    Create mock output contract for testing.
    
    Args:
        job_uuid: Job UUID to match
        ticker: Stock symbol
        num_predictions: Number of predictions to generate
    
    Returns:
        ContractOutputSpec with realistic mock data
    """
    import numpy as np
    
    np.random.seed(int(hashlib.md5(job_uuid.encode()).hexdigest()[:8], 16))
    
    predictions = np.random.normal(0.05, 0.03, num_predictions).tolist()
    confidence = np.random.uniform(0.75, 0.95, num_predictions).tolist()
    
    return ContractOutputSpec(
        job_uuid=job_uuid,
        ticker=ticker,
        predictions=predictions,
        confidence=confidence,
        explainability_blob={
            'shap_values': {f'feature_{i}': float(np.random.randn()) for i in range(10)},
            'feature_importance': [
                {'feature': f'feature_{i}', 'importance': float(np.random.rand())}
                for i in range(10)
            ]
        },
        status=JobStatus.COMPLETED,
        latency_ms=350.5
    )


logger.info("✓ Azure Contract Definitions loaded (Phase 4 - Hybrid Readiness)")
