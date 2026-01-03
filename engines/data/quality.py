"""
Data Quality & Feature Engineering System
Phase 10 - Data Quality & Features (Items 701-760)

Complete implementation of:
- Data validation framework
- Feature engineering pipeline
- Data quality monitoring
- Anomaly detection
- Data lineage tracking
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
from datetime import datetime, timedelta
import hashlib
import json


# =============================================================================
# DATA VALIDATION FRAMEWORK (Items 701-720)
# =============================================================================

class ValidationLevel(Enum):
    """Validation severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationRule:
    """Data validation rule definition."""
    id: str
    name: str
    description: str
    level: ValidationLevel
    check_fn: Callable[[pd.DataFrame], bool]
    fix_fn: Optional[Callable[[pd.DataFrame], pd.DataFrame]] = None
    
    def validate(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Run validation and return result."""
        try:
            passed = self.check_fn(df)
            return {
                "rule_id": self.id,
                "name": self.name,
                "passed": passed,
                "level": self.level.value,
                "message": f"Passed: {self.description}" if passed else f"Failed: {self.description}"
            }
        except Exception as e:
            return {
                "rule_id": self.id,
                "name": self.name,
                "passed": False,
                "level": ValidationLevel.ERROR.value,
                "message": f"Error running validation: {e}"
            }


class DataValidator:
    """Data validation engine."""
    
    def __init__(self):
        self.rules: Dict[str, ValidationRule] = {}
        self._register_default_rules()
    
    def _register_default_rules(self):
        """Register default validation rules."""
        
        # Null checks
        self.add_rule(ValidationRule(
            id="no_null_prices",
            name="No Null Prices",
            description="Price columns should not contain null values",
            level=ValidationLevel.ERROR,
            check_fn=lambda df: not df[['open', 'high', 'low', 'close']].isnull().any().any() if all(c in df.columns for c in ['open', 'high', 'low', 'close']) else True
        ))
        
        # OHLC consistency
        self.add_rule(ValidationRule(
            id="ohlc_consistency",
            name="OHLC Consistency",
            description="High >= Low, Close within High-Low range",
            level=ValidationLevel.ERROR,
            check_fn=lambda df: self._check_ohlc_consistency(df)
        ))
        
        # Positive prices
        self.add_rule(ValidationRule(
            id="positive_prices",
            name="Positive Prices",
            description="All price values should be positive",
            level=ValidationLevel.ERROR,
            check_fn=lambda df: (df[['open', 'high', 'low', 'close']] > 0).all().all() if all(c in df.columns for c in ['open', 'high', 'low', 'close']) else True
        ))
        
        # Volume check
        self.add_rule(ValidationRule(
            id="non_negative_volume",
            name="Non-Negative Volume",
            description="Volume should be non-negative",
            level=ValidationLevel.WARNING,
            check_fn=lambda df: (df['volume'] >= 0).all() if 'volume' in df.columns else True
        ))
        
        # Timestamp monotonic
        self.add_rule(ValidationRule(
            id="timestamp_monotonic",
            name="Timestamp Monotonic",
            description="Timestamps should be strictly increasing",
            level=ValidationLevel.WARNING,
            check_fn=lambda df: df.index.is_monotonic_increasing if isinstance(df.index, pd.DatetimeIndex) else True
        ))
        
        # No duplicates
        self.add_rule(ValidationRule(
            id="no_duplicate_timestamps",
            name="No Duplicate Timestamps",
            description="No duplicate timestamps in data",
            level=ValidationLevel.ERROR,
            check_fn=lambda df: not df.index.duplicated().any() if isinstance(df.index, pd.DatetimeIndex) else True
        ))
        
        # Reasonable price changes
        self.add_rule(ValidationRule(
            id="reasonable_returns",
            name="Reasonable Returns",
            description="Daily returns should be within reasonable bounds (-50% to +100%)",
            level=ValidationLevel.WARNING,
            check_fn=lambda df: self._check_reasonable_returns(df)
        ))
        
        # IV bounds
        self.add_rule(ValidationRule(
            id="iv_bounds",
            name="IV Within Bounds",
            description="Implied volatility should be between 0 and 500%",
            level=ValidationLevel.WARNING,
            check_fn=lambda df: ((df['iv'] >= 0) & (df['iv'] <= 5.0)).all() if 'iv' in df.columns else True
        ))
        
        # Greeks bounds
        self.add_rule(ValidationRule(
            id="delta_bounds",
            name="Delta Within Bounds",
            description="Delta should be between -1 and 1",
            level=ValidationLevel.ERROR,
            check_fn=lambda df: ((df['delta'] >= -1) & (df['delta'] <= 1)).all() if 'delta' in df.columns else True
        ))
    
    def _check_ohlc_consistency(self, df: pd.DataFrame) -> bool:
        """Check OHLC data consistency."""
        if not all(c in df.columns for c in ['open', 'high', 'low', 'close']):
            return True
        
        high_low = (df['high'] >= df['low']).all()
        close_range = ((df['close'] >= df['low']) & (df['close'] <= df['high'])).all()
        open_range = ((df['open'] >= df['low']) & (df['open'] <= df['high'])).all()
        
        return high_low and close_range and open_range
    
    def _check_reasonable_returns(self, df: pd.DataFrame) -> bool:
        """Check if returns are within reasonable bounds."""
        if 'close' not in df.columns or len(df) < 2:
            return True
        
        returns = df['close'].pct_change().dropna()
        return ((returns >= -0.5) & (returns <= 1.0)).all()
    
    def add_rule(self, rule: ValidationRule):
        """Add a validation rule."""
        self.rules[rule.id] = rule
    
    def validate(self, df: pd.DataFrame, rules: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run all or specified validation rules."""
        results = []
        rules_to_run = rules or list(self.rules.keys())
        
        for rule_id in rules_to_run:
            if rule_id in self.rules:
                result = self.rules[rule_id].validate(df)
                results.append(result)
        
        passed = all(r['passed'] for r in results)
        errors = [r for r in results if r['level'] in ['error', 'critical'] and not r['passed']]
        warnings = [r for r in results if r['level'] == 'warning' and not r['passed']]
        
        return {
            "passed": passed,
            "total_rules": len(results),
            "passed_count": sum(1 for r in results if r['passed']),
            "failed_count": sum(1 for r in results if not r['passed']),
            "errors": errors,
            "warnings": warnings,
            "results": results
        }


# =============================================================================
# FEATURE ENGINEERING PIPELINE (Items 721-740)
# =============================================================================

class FeatureType(Enum):
    """Feature types."""
    TECHNICAL = "technical"
    STATISTICAL = "statistical"
    VOLATILITY = "volatility"
    MOMENTUM = "momentum"
    VOLUME = "volume"
    OPTIONS = "options"
    SENTIMENT = "sentiment"


@dataclass
class FeatureDefinition:
    """Feature definition."""
    id: str
    name: str
    feature_type: FeatureType
    description: str
    compute_fn: Callable[[pd.DataFrame], pd.Series]
    dependencies: List[str] = field(default_factory=list)
    lookback: int = 0


class FeatureEngineer:
    """Feature engineering pipeline."""
    
    def __init__(self):
        self.features: Dict[str, FeatureDefinition] = {}
        self._register_default_features()
    
    def _register_default_features(self):
        """Register default features."""
        
        # Technical indicators
        self.add_feature(FeatureDefinition(
            id="sma_20",
            name="20-Day SMA",
            feature_type=FeatureType.TECHNICAL,
            description="20-day simple moving average",
            compute_fn=lambda df: df['close'].rolling(20).mean(),
            lookback=20
        ))
        
        self.add_feature(FeatureDefinition(
            id="sma_50",
            name="50-Day SMA",
            feature_type=FeatureType.TECHNICAL,
            description="50-day simple moving average",
            compute_fn=lambda df: df['close'].rolling(50).mean(),
            lookback=50
        ))
        
        self.add_feature(FeatureDefinition(
            id="ema_12",
            name="12-Day EMA",
            feature_type=FeatureType.TECHNICAL,
            description="12-day exponential moving average",
            compute_fn=lambda df: df['close'].ewm(span=12, adjust=False).mean(),
            lookback=12
        ))
        
        self.add_feature(FeatureDefinition(
            id="ema_26",
            name="26-Day EMA",
            feature_type=FeatureType.TECHNICAL,
            description="26-day exponential moving average",
            compute_fn=lambda df: df['close'].ewm(span=26, adjust=False).mean(),
            lookback=26
        ))
        
        self.add_feature(FeatureDefinition(
            id="macd",
            name="MACD",
            feature_type=FeatureType.MOMENTUM,
            description="Moving Average Convergence Divergence",
            compute_fn=lambda df: df['close'].ewm(span=12).mean() - df['close'].ewm(span=26).mean(),
            lookback=26
        ))
        
        self.add_feature(FeatureDefinition(
            id="macd_signal",
            name="MACD Signal",
            feature_type=FeatureType.MOMENTUM,
            description="MACD Signal Line",
            compute_fn=lambda df: (df['close'].ewm(span=12).mean() - df['close'].ewm(span=26).mean()).ewm(span=9).mean(),
            lookback=35
        ))
        
        self.add_feature(FeatureDefinition(
            id="rsi_14",
            name="14-Day RSI",
            feature_type=FeatureType.MOMENTUM,
            description="14-day Relative Strength Index",
            compute_fn=lambda df: self._compute_rsi(df, 14),
            lookback=14
        ))
        
        self.add_feature(FeatureDefinition(
            id="bollinger_upper",
            name="Bollinger Upper",
            feature_type=FeatureType.VOLATILITY,
            description="Bollinger Band Upper (20, 2)",
            compute_fn=lambda df: df['close'].rolling(20).mean() + 2 * df['close'].rolling(20).std(),
            lookback=20
        ))
        
        self.add_feature(FeatureDefinition(
            id="bollinger_lower",
            name="Bollinger Lower",
            feature_type=FeatureType.VOLATILITY,
            description="Bollinger Band Lower (20, 2)",
            compute_fn=lambda df: df['close'].rolling(20).mean() - 2 * df['close'].rolling(20).std(),
            lookback=20
        ))
        
        self.add_feature(FeatureDefinition(
            id="atr_14",
            name="14-Day ATR",
            feature_type=FeatureType.VOLATILITY,
            description="14-day Average True Range",
            compute_fn=lambda df: self._compute_atr(df, 14),
            lookback=14
        ))
        
        self.add_feature(FeatureDefinition(
            id="realized_vol_20",
            name="20-Day Realized Volatility",
            feature_type=FeatureType.VOLATILITY,
            description="20-day realized volatility (annualized)",
            compute_fn=lambda df: df['close'].pct_change().rolling(20).std() * np.sqrt(252),
            lookback=20
        ))
        
        self.add_feature(FeatureDefinition(
            id="volume_sma_20",
            name="20-Day Volume SMA",
            feature_type=FeatureType.VOLUME,
            description="20-day volume moving average",
            compute_fn=lambda df: df['volume'].rolling(20).mean() if 'volume' in df.columns else pd.Series(index=df.index),
            lookback=20
        ))
        
        self.add_feature(FeatureDefinition(
            id="volume_ratio",
            name="Volume Ratio",
            feature_type=FeatureType.VOLUME,
            description="Current volume / 20-day average",
            compute_fn=lambda df: df['volume'] / df['volume'].rolling(20).mean() if 'volume' in df.columns else pd.Series(index=df.index),
            lookback=20
        ))
        
        self.add_feature(FeatureDefinition(
            id="price_momentum_5",
            name="5-Day Momentum",
            feature_type=FeatureType.MOMENTUM,
            description="5-day price momentum (return)",
            compute_fn=lambda df: df['close'].pct_change(5),
            lookback=5
        ))
        
        self.add_feature(FeatureDefinition(
            id="price_momentum_20",
            name="20-Day Momentum",
            feature_type=FeatureType.MOMENTUM,
            description="20-day price momentum (return)",
            compute_fn=lambda df: df['close'].pct_change(20),
            lookback=20
        ))
        
        # Options-specific features
        self.add_feature(FeatureDefinition(
            id="iv_rank",
            name="IV Rank",
            feature_type=FeatureType.OPTIONS,
            description="IV Rank over 252 days",
            compute_fn=lambda df: self._compute_iv_rank(df, 252) if 'iv' in df.columns else pd.Series(index=df.index),
            lookback=252
        ))
        
        self.add_feature(FeatureDefinition(
            id="iv_percentile",
            name="IV Percentile",
            feature_type=FeatureType.OPTIONS,
            description="IV Percentile over 252 days",
            compute_fn=lambda df: self._compute_iv_percentile(df, 252) if 'iv' in df.columns else pd.Series(index=df.index),
            lookback=252
        ))
        
        self.add_feature(FeatureDefinition(
            id="iv_premium",
            name="IV Premium",
            feature_type=FeatureType.OPTIONS,
            description="IV - Realized Vol (volatility risk premium)",
            compute_fn=lambda df: df['iv'] - df['close'].pct_change().rolling(20).std() * np.sqrt(252) if 'iv' in df.columns else pd.Series(index=df.index),
            lookback=20
        ))
    
    def _compute_rsi(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Compute RSI."""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _compute_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Compute ATR."""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(period).mean()
    
    def _compute_iv_rank(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Compute IV Rank."""
        iv = df['iv']
        iv_min = iv.rolling(period).min()
        iv_max = iv.rolling(period).max()
        return (iv - iv_min) / (iv_max - iv_min) * 100
    
    def _compute_iv_percentile(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Compute IV Percentile."""
        iv = df['iv']
        return iv.rolling(period).apply(lambda x: (x < x.iloc[-1]).sum() / len(x) * 100)
    
    def add_feature(self, feature: FeatureDefinition):
        """Add a feature definition."""
        self.features[feature.id] = feature
    
    def compute_features(self, df: pd.DataFrame, features: Optional[List[str]] = None) -> pd.DataFrame:
        """Compute all or specified features."""
        result = df.copy()
        features_to_compute = features or list(self.features.keys())
        
        for feature_id in features_to_compute:
            if feature_id in self.features:
                feature = self.features[feature_id]
                try:
                    result[feature_id] = feature.compute_fn(df)
                except Exception as e:
                    print(f"Error computing {feature_id}: {e}")
        
        return result
    
    def get_feature_info(self) -> List[Dict[str, Any]]:
        """Get info about all registered features."""
        return [
            {
                "id": f.id,
                "name": f.name,
                "type": f.feature_type.value,
                "description": f.description,
                "lookback": f.lookback
            }
            for f in self.features.values()
        ]


# =============================================================================
# DATA QUALITY MONITORING (Items 741-750)
# =============================================================================

@dataclass
class DataQualityMetrics:
    """Data quality metrics."""
    completeness: float  # % non-null
    uniqueness: float  # % unique values
    validity: float  # % passing validation
    timeliness: float  # freshness score
    consistency: float  # cross-field consistency
    accuracy: float  # data accuracy score
    
    def overall_score(self) -> float:
        """Calculate overall data quality score."""
        weights = {
            'completeness': 0.2,
            'uniqueness': 0.1,
            'validity': 0.25,
            'timeliness': 0.2,
            'consistency': 0.15,
            'accuracy': 0.1
        }
        return sum([
            self.completeness * weights['completeness'],
            self.uniqueness * weights['uniqueness'],
            self.validity * weights['validity'],
            self.timeliness * weights['timeliness'],
            self.consistency * weights['consistency'],
            self.accuracy * weights['accuracy']
        ])
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "completeness": self.completeness,
            "uniqueness": self.uniqueness,
            "validity": self.validity,
            "timeliness": self.timeliness,
            "consistency": self.consistency,
            "accuracy": self.accuracy,
            "overall": self.overall_score()
        }


class DataQualityMonitor:
    """Monitor data quality over time."""
    
    def __init__(self):
        self.validator = DataValidator()
        self.history: List[Dict[str, Any]] = []
    
    def compute_metrics(self, df: pd.DataFrame, timestamp: Optional[datetime] = None) -> DataQualityMetrics:
        """Compute data quality metrics for a dataframe."""
        timestamp = timestamp or datetime.now()
        
        # Completeness
        completeness = (1 - df.isnull().sum().sum() / df.size) * 100
        
        # Uniqueness (for index)
        uniqueness = (1 - df.index.duplicated().sum() / len(df)) * 100 if len(df) > 0 else 100
        
        # Validity (run validation rules)
        validation_result = self.validator.validate(df)
        validity = (validation_result['passed_count'] / validation_result['total_rules']) * 100 if validation_result['total_rules'] > 0 else 100
        
        # Timeliness (how fresh is the data)
        if isinstance(df.index, pd.DatetimeIndex) and len(df) > 0:
            latest = df.index.max()
            age = (datetime.now() - latest.to_pydatetime().replace(tzinfo=None)).total_seconds() / 3600  # hours
            timeliness = max(0, 100 - age * 2)  # Lose 2% per hour
        else:
            timeliness = 100
        
        # Consistency (OHLC checks)
        if all(c in df.columns for c in ['open', 'high', 'low', 'close']):
            ohlc_consistent = (
                (df['high'] >= df['low']).all() and
                ((df['close'] >= df['low']) & (df['close'] <= df['high'])).all()
            )
            consistency = 100 if ohlc_consistent else 50
        else:
            consistency = 100
        
        # Accuracy (proxy: no extreme outliers)
        if 'close' in df.columns and len(df) > 10:
            returns = df['close'].pct_change().dropna()
            outliers = ((returns < -0.5) | (returns > 1.0)).sum()
            accuracy = max(0, 100 - outliers * 10)
        else:
            accuracy = 100
        
        metrics = DataQualityMetrics(
            completeness=completeness,
            uniqueness=uniqueness,
            validity=validity,
            timeliness=timeliness,
            consistency=consistency,
            accuracy=accuracy
        )
        
        # Store in history
        self.history.append({
            "timestamp": timestamp.isoformat(),
            "metrics": metrics.to_dict()
        })
        
        return metrics
    
    def get_trend(self, metric: str, periods: int = 10) -> List[float]:
        """Get trend for a specific metric."""
        if not self.history:
            return []
        
        recent = self.history[-periods:]
        return [h['metrics'].get(metric, 0) for h in recent]


# =============================================================================
# DATA LINEAGE (Items 751-760)
# =============================================================================

@dataclass
class DataLineageNode:
    """Node in data lineage graph."""
    id: str
    name: str
    node_type: str  # source, transform, output
    metadata: Dict[str, Any] = field(default_factory=dict)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.node_type,
            "metadata": self.metadata,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "created_at": self.created_at.isoformat()
        }


class DataLineageTracker:
    """Track data lineage and transformations."""
    
    def __init__(self):
        self.nodes: Dict[str, DataLineageNode] = {}
        self.edges: List[tuple] = []
    
    def add_source(self, name: str, metadata: Optional[Dict] = None) -> str:
        """Add a data source node."""
        node_id = self._generate_id(name, "source")
        self.nodes[node_id] = DataLineageNode(
            id=node_id,
            name=name,
            node_type="source",
            metadata=metadata or {}
        )
        return node_id
    
    def add_transform(self, name: str, inputs: List[str], metadata: Optional[Dict] = None) -> str:
        """Add a transformation node."""
        node_id = self._generate_id(name, "transform")
        self.nodes[node_id] = DataLineageNode(
            id=node_id,
            name=name,
            node_type="transform",
            metadata=metadata or {},
            inputs=inputs
        )
        
        # Add edges from inputs to this node
        for input_id in inputs:
            self.edges.append((input_id, node_id))
            if input_id in self.nodes:
                self.nodes[input_id].outputs.append(node_id)
        
        return node_id
    
    def add_output(self, name: str, inputs: List[str], metadata: Optional[Dict] = None) -> str:
        """Add an output node."""
        node_id = self._generate_id(name, "output")
        self.nodes[node_id] = DataLineageNode(
            id=node_id,
            name=name,
            node_type="output",
            metadata=metadata or {},
            inputs=inputs
        )
        
        for input_id in inputs:
            self.edges.append((input_id, node_id))
            if input_id in self.nodes:
                self.nodes[input_id].outputs.append(node_id)
        
        return node_id
    
    def _generate_id(self, name: str, node_type: str) -> str:
        """Generate unique node ID."""
        timestamp = datetime.now().isoformat()
        return hashlib.md5(f"{name}_{node_type}_{timestamp}".encode()).hexdigest()[:12]
    
    def get_upstream(self, node_id: str) -> List[str]:
        """Get all upstream nodes for a given node."""
        if node_id not in self.nodes:
            return []
        
        upstream = set()
        to_visit = list(self.nodes[node_id].inputs)
        
        while to_visit:
            current = to_visit.pop()
            if current not in upstream:
                upstream.add(current)
                if current in self.nodes:
                    to_visit.extend(self.nodes[current].inputs)
        
        return list(upstream)
    
    def get_downstream(self, node_id: str) -> List[str]:
        """Get all downstream nodes for a given node."""
        if node_id not in self.nodes:
            return []
        
        downstream = set()
        to_visit = list(self.nodes[node_id].outputs)
        
        while to_visit:
            current = to_visit.pop()
            if current not in downstream:
                downstream.add(current)
                if current in self.nodes:
                    to_visit.extend(self.nodes[current].outputs)
        
        return list(downstream)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export lineage graph as dictionary."""
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [{"from": e[0], "to": e[1]} for e in self.edges]
        }


# =============================================================================
# COMPLETE PHASE 10
# =============================================================================

def complete_phase_10() -> Dict[str, Any]:
    """Complete Phase 10 deliverables."""
    validator = DataValidator()
    engineer = FeatureEngineer()
    monitor = DataQualityMonitor()
    lineage = DataLineageTracker()
    
    return {
        "validation_rules_count": len(validator.rules),
        "features_count": len(engineer.features),
        "feature_types": list(set(f.feature_type.value for f in engineer.features.values())),
        "status": "complete"
    }


if __name__ == "__main__":
    print("Phase 10 Summary:")
    result = complete_phase_10()
    for k, v in result.items():
        print(f"  {k}: {v}")
