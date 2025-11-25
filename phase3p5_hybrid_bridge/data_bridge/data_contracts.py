"""
Data Contracts for Hybrid Bridge
==================================

Formal schemas for data exchange between offline analytics and Azure stubs.

Contracts defined:
- PortfolioAnalyticsContract: Portfolio metrics, risk factors
- ExplainabilityContract: SHAP values, feature weights
- ForecastContract: Ticker predictions, return distributions

Each contract provides:
- JSON serialization/deserialization
- Schema validation
- SHA256 integrity hashing
"""

import hashlib
import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum


class ContractType(Enum):
    """Enumeration of all supported contract types."""
    PORTFOLIO_ANALYTICS = "portfolio_analytics"
    EXPLAINABILITY = "explainability"
    FORECAST = "forecast"


@dataclass
class PortfolioAnalyticsContract:
    """
    Contract for portfolio analytics data exchange.
    
    Attributes:
        portfolio_id: Unique identifier for the portfolio
        timestamp: ISO 8601 timestamp of analysis
        total_value: Total portfolio value in USD
        annualized_return: Annualized return (decimal, e.g., 0.15 = 15%)
        volatility: Annualized volatility
        sharpe_ratio: Risk-adjusted return metric
        max_drawdown: Maximum drawdown percentage
        beta: Portfolio beta vs benchmark
        alpha: Portfolio alpha vs benchmark
        sector_allocation: Dict mapping sector name to percentage (0-100)
        risk_metrics: Additional risk metrics
        holdings: List of holdings with ticker, shares, value
        benchmark_name: Name of benchmark (e.g., "SPY")
        metadata: Additional metadata
    """
    portfolio_id: str
    timestamp: str
    total_value: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    beta: float
    alpha: float
    sector_allocation: Dict[str, float]
    risk_metrics: Dict[str, float]
    holdings: List[Dict[str, Any]]
    benchmark_name: str = "SPY"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> dict:
        """Convert contract to JSON-serializable dict."""
        return asdict(self)
    
    @classmethod
    def from_json(cls, data: dict) -> 'PortfolioAnalyticsContract':
        """Create contract from JSON dict."""
        return cls(**data)
    
    def validate(self) -> bool:
        """
        Validate contract data integrity.
        
        Returns:
            True if valid, raises ValueError if invalid
        """
        # Required fields
        if not self.portfolio_id:
            raise ValueError("portfolio_id is required")
        
        # Timestamp format
        try:
            datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
        except ValueError as e:
            raise ValueError(f"Invalid timestamp format: {e}")
        
        # Numeric ranges
        if self.total_value < 0:
            raise ValueError("total_value must be non-negative")
        
        if self.volatility < 0:
            raise ValueError("volatility must be non-negative")
        
        if not -1 <= self.max_drawdown <= 0:
            raise ValueError("max_drawdown must be in range [-1, 0]")
        
        # Sector allocation sums to ~100%
        allocation_sum = sum(self.sector_allocation.values())
        if not 99.0 <= allocation_sum <= 101.0:
            raise ValueError(f"sector_allocation must sum to ~100%, got {allocation_sum}")
        
        # Holdings structure
        for holding in self.holdings:
            if 'ticker' not in holding or 'value' not in holding:
                raise ValueError("Each holding must have 'ticker' and 'value'")
        
        return True
    
    def get_hash(self) -> str:
        """
        Compute SHA256 hash of contract for integrity verification.
        
        Returns:
            Hex digest of SHA256 hash
        """
        # Create canonical JSON representation
        canonical = json.dumps(self.to_json(), sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


@dataclass
class ExplainabilityContract:
    """
    Contract for model explainability data.
    
    Attributes:
        prediction_id: Unique identifier for this prediction
        timestamp: ISO 8601 timestamp of prediction
        model_name: Name of the model (e.g., "portfolio_model.pkl")
        input_features: Dict of feature names to values used in prediction
        prediction: Model prediction output
        shap_values: SHAP values for each feature
        feature_importance: Global feature importance scores
        base_value: SHAP base value (expected value)
        explanation_method: Method used (e.g., "SHAP TreeExplainer")
        confidence_interval: Optional confidence bounds [lower, upper]
        metadata: Additional metadata
    """
    prediction_id: str
    timestamp: str
    model_name: str
    input_features: Dict[str, float]
    prediction: Union[float, List[float]]
    shap_values: Dict[str, float]
    feature_importance: Dict[str, float]
    base_value: float
    explanation_method: str = "SHAP TreeExplainer"
    confidence_interval: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> dict:
        """Convert contract to JSON-serializable dict."""
        return asdict(self)
    
    @classmethod
    def from_json(cls, data: dict) -> 'ExplainabilityContract':
        """Create contract from JSON dict."""
        return cls(**data)
    
    def validate(self) -> bool:
        """
        Validate contract data integrity.
        
        Returns:
            True if valid, raises ValueError if invalid
        """
        # Required fields
        if not self.prediction_id:
            raise ValueError("prediction_id is required")
        
        if not self.model_name:
            raise ValueError("model_name is required")
        
        # Timestamp format
        try:
            datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
        except ValueError as e:
            raise ValueError(f"Invalid timestamp format: {e}")
        
        # Feature consistency
        if set(self.shap_values.keys()) != set(self.input_features.keys()):
            raise ValueError("SHAP values must match input features")
        
        # Feature importance values in [0, 1]
        for importance in self.feature_importance.values():
            if not 0 <= importance <= 1:
                raise ValueError("Feature importance must be in range [0, 1]")
        
        # Confidence interval structure
        if self.confidence_interval is not None:
            if len(self.confidence_interval) != 2:
                raise ValueError("confidence_interval must have exactly 2 values [lower, upper]")
            if self.confidence_interval[0] > self.confidence_interval[1]:
                raise ValueError("confidence_interval lower bound must be <= upper bound")
        
        return True
    
    def get_hash(self) -> str:
        """
        Compute SHA256 hash of contract for integrity verification.
        
        Returns:
            Hex digest of SHA256 hash
        """
        canonical = json.dumps(self.to_json(), sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


@dataclass
class ForecastContract:
    """
    Contract for forecast/prediction data.
    
    Attributes:
        forecast_id: Unique identifier for this forecast
        timestamp: ISO 8601 timestamp of forecast generation
        ticker: Stock ticker symbol
        horizon_days: Forecast horizon in days
        expected_return: Expected return (decimal)
        return_distribution: Dict with mean, std, quantiles
        confidence_score: Model confidence (0-1)
        features_used: List of feature names used in forecast
        model_version: Model version identifier
        scenario: Optional scenario name (e.g., "base", "bull", "bear")
        metadata: Additional metadata
    """
    forecast_id: str
    timestamp: str
    ticker: str
    horizon_days: int
    expected_return: float
    return_distribution: Dict[str, float]
    confidence_score: float
    features_used: List[str]
    model_version: str
    scenario: str = "base"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> dict:
        """Convert contract to JSON-serializable dict."""
        return asdict(self)
    
    @classmethod
    def from_json(cls, data: dict) -> 'ForecastContract':
        """Create contract from JSON dict."""
        return cls(**data)
    
    def validate(self) -> bool:
        """
        Validate contract data integrity.
        
        Returns:
            True if valid, raises ValueError if invalid
        """
        # Required fields
        if not self.forecast_id:
            raise ValueError("forecast_id is required")
        
        if not self.ticker:
            raise ValueError("ticker is required")
        
        # Timestamp format
        try:
            datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
        except ValueError as e:
            raise ValueError(f"Invalid timestamp format: {e}")
        
        # Horizon must be positive
        if self.horizon_days <= 0:
            raise ValueError("horizon_days must be positive")
        
        # Confidence score in [0, 1]
        if not 0 <= self.confidence_score <= 1:
            raise ValueError("confidence_score must be in range [0, 1]")
        
        # Return distribution structure
        required_keys = {'mean', 'std'}
        if not required_keys.issubset(self.return_distribution.keys()):
            raise ValueError(f"return_distribution must contain {required_keys}")
        
        if self.return_distribution['std'] < 0:
            raise ValueError("return_distribution std must be non-negative")
        
        return True
    
    def get_hash(self) -> str:
        """
        Compute SHA256 hash of contract for integrity verification.
        
        Returns:
            Hex digest of SHA256 hash
        """
        canonical = json.dumps(self.to_json(), sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


# Utility functions for contract operations

def create_contract(contract_type: ContractType, data: dict) -> Union[PortfolioAnalyticsContract, ExplainabilityContract, ForecastContract]:
    """
    Factory function to create contract from type and data.
    
    Args:
        contract_type: Type of contract to create
        data: Data dict to populate contract
    
    Returns:
        Contract instance
    """
    contract_map = {
        ContractType.PORTFOLIO_ANALYTICS: PortfolioAnalyticsContract,
        ContractType.EXPLAINABILITY: ExplainabilityContract,
        ContractType.FORECAST: ForecastContract,
    }
    
    contract_class = contract_map.get(contract_type)
    if contract_class is None:
        raise ValueError(f"Unknown contract type: {contract_type}")
    
    return contract_class.from_json(data)


def validate_contract(contract_data: dict, contract_type: ContractType) -> bool:
    """
    Validate contract data without creating instance.
    
    Args:
        contract_data: Contract data dict
        contract_type: Expected contract type
    
    Returns:
        True if valid
    
    Raises:
        ValueError if validation fails
    """
    contract = create_contract(contract_type, contract_data)
    return contract.validate()


def get_contract_hash(contract_data: dict, contract_type: ContractType) -> str:
    """
    Compute hash of contract data.
    
    Args:
        contract_data: Contract data dict
        contract_type: Contract type
    
    Returns:
        SHA256 hex digest
    """
    contract = create_contract(contract_type, contract_data)
    return contract.get_hash()


def serialize_contract(contract: Union[PortfolioAnalyticsContract, ExplainabilityContract, ForecastContract]) -> str:
    """
    Serialize contract to JSON string.
    
    Args:
        contract: Contract instance
    
    Returns:
        JSON string
    """
    return json.dumps(contract.to_json(), indent=2)


def deserialize_contract(json_str: str, contract_type: ContractType) -> Union[PortfolioAnalyticsContract, ExplainabilityContract, ForecastContract]:
    """
    Deserialize JSON string to contract.
    
    Args:
        json_str: JSON string
        contract_type: Expected contract type
    
    Returns:
        Contract instance
    """
    data = json.loads(json_str)
    return create_contract(contract_type, data)
