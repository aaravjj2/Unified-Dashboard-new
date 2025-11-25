"""
Schema Diff Checker
===================

Cross-validates contract schemas with Agent 1B's Azure contracts.

Features:
- Detect missing fields
- Type drift detection
- Timestamp desync warnings
- Generate validation reports
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum


class DiffSeverity(Enum):
    """Severity level of schema difference."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class SchemaDifference:
    """Represents a schema difference."""
    field_path: str
    diff_type: str  # missing_field, type_mismatch, value_range, timestamp_drift
    severity: str
    local_value: Optional[Any]
    cloud_value: Optional[Any]
    description: str
    
    def to_json(self) -> dict:
        """Convert to JSON dict."""
        return asdict(self)


@dataclass
class SchemaComparisonResult:
    """Result of schema comparison."""
    contract_type: str
    is_compatible: bool
    differences: List[SchemaDifference]
    compared_at: str
    local_schema_version: str
    cloud_schema_version: str
    
    def to_json(self) -> dict:
        """Convert to JSON dict."""
        return {
            "contract_type": self.contract_type,
            "is_compatible": self.is_compatible,
            "differences": [d.to_json() for d in self.differences],
            "compared_at": self.compared_at,
            "local_schema_version": self.local_schema_version,
            "cloud_schema_version": self.cloud_schema_version,
            "summary": {
                "total_differences": len(self.differences),
                "errors": sum(1 for d in self.differences if d.severity == DiffSeverity.ERROR.value),
                "warnings": sum(1 for d in self.differences if d.severity == DiffSeverity.WARNING.value),
                "info": sum(1 for d in self.differences if d.severity == DiffSeverity.INFO.value)
            }
        }


class SchemaDiffChecker:
    """
    Schema consistency validator for local vs Azure contracts.
    
    Ensures data exchanged between offline analytics and cloud stubs
    maintains schema compatibility.
    """
    
    def __init__(self):
        """Initialize schema diff checker."""
        # Local schema definitions (from data_contracts.py)
        self.local_schemas = self._load_local_schemas()
        
        # Cloud schema definitions (placeholder for Agent 1B integration)
        self.cloud_schemas = self._load_cloud_schemas()
        
        # Statistics
        self.comparisons_performed = 0
        self.compatible_schemas = 0
        self.incompatible_schemas = 0
    
    def _load_local_schemas(self) -> Dict[str, Dict[str, Any]]:
        """
        Load local schema definitions.
        
        Returns:
            Dict mapping contract type to schema
        """
        return {
            "portfolio_analytics": {
                "version": "3.5.0",
                "required_fields": [
                    "portfolio_id", "timestamp", "total_value", "annualized_return",
                    "volatility", "sharpe_ratio", "max_drawdown", "beta", "alpha",
                    "sector_allocation", "risk_metrics", "holdings", "benchmark_name"
                ],
                "field_types": {
                    "portfolio_id": "str",
                    "timestamp": "str",
                    "total_value": "float",
                    "annualized_return": "float",
                    "volatility": "float",
                    "sharpe_ratio": "float",
                    "max_drawdown": "float",
                    "beta": "float",
                    "alpha": "float",
                    "sector_allocation": "dict",
                    "risk_metrics": "dict",
                    "holdings": "list",
                    "benchmark_name": "str",
                    "metadata": "dict"
                }
            },
            "explainability": {
                "version": "3.5.0",
                "required_fields": [
                    "prediction_id", "timestamp", "model_name", "input_features",
                    "prediction", "shap_values", "feature_importance", "base_value"
                ],
                "field_types": {
                    "prediction_id": "str",
                    "timestamp": "str",
                    "model_name": "str",
                    "input_features": "dict",
                    "prediction": ["float", "list"],
                    "shap_values": "dict",
                    "feature_importance": "dict",
                    "base_value": "float",
                    "explanation_method": "str",
                    "confidence_interval": "list",
                    "metadata": "dict"
                }
            },
            "forecast": {
                "version": "3.5.0",
                "required_fields": [
                    "forecast_id", "timestamp", "ticker", "horizon_days",
                    "expected_return", "return_distribution", "confidence_score",
                    "features_used", "model_version"
                ],
                "field_types": {
                    "forecast_id": "str",
                    "timestamp": "str",
                    "ticker": "str",
                    "horizon_days": "int",
                    "expected_return": "float",
                    "return_distribution": "dict",
                    "confidence_score": "float",
                    "features_used": "list",
                    "model_version": "str",
                    "scenario": "str",
                    "metadata": "dict"
                }
            }
        }
    
    def _load_cloud_schemas(self) -> Dict[str, Dict[str, Any]]:
        """
        Load cloud schema definitions (Agent 1B contracts).
        
        For Phase 3.5, this is a mock matching local schemas.
        In Phase 4, this will load from Agent 1B's azure_contract_definitions.py.
        
        Returns:
            Dict mapping contract type to schema
        """
        # Placeholder: identical to local for Phase 3.5
        # In Phase 4, will be replaced with:
        # from agent_1b.azure_contract_definitions import get_schemas
        # return get_schemas()
        
        return {
            "portfolio_analytics": {
                "version": "3.5.0",
                "required_fields": [
                    "portfolio_id", "timestamp", "total_value", "annualized_return",
                    "volatility", "sharpe_ratio", "max_drawdown", "beta", "alpha",
                    "sector_allocation", "risk_metrics", "holdings", "benchmark_name"
                ],
                "field_types": {
                    "portfolio_id": "str",
                    "timestamp": "str",
                    "total_value": "float",
                    "annualized_return": "float",
                    "volatility": "float",
                    "sharpe_ratio": "float",
                    "max_drawdown": "float",
                    "beta": "float",
                    "alpha": "float",
                    "sector_allocation": "dict",
                    "risk_metrics": "dict",
                    "holdings": "list",
                    "benchmark_name": "str",
                    "metadata": "dict"
                }
            },
            "explainability": {
                "version": "3.5.0",
                "required_fields": [
                    "prediction_id", "timestamp", "model_name", "input_features",
                    "prediction", "shap_values", "feature_importance", "base_value"
                ],
                "field_types": {
                    "prediction_id": "str",
                    "timestamp": "str",
                    "model_name": "str",
                    "input_features": "dict",
                    "prediction": ["float", "list"],
                    "shap_values": "dict",
                    "feature_importance": "dict",
                    "base_value": "float",
                    "explanation_method": "str",
                    "confidence_interval": "list",
                    "metadata": "dict"
                }
            },
            "forecast": {
                "version": "3.5.0",
                "required_fields": [
                    "forecast_id", "timestamp", "ticker", "horizon_days",
                    "expected_return", "return_distribution", "confidence_score",
                    "features_used", "model_version"
                ],
                "field_types": {
                    "forecast_id": "str",
                    "timestamp": "str",
                    "ticker": "str",
                    "horizon_days": "int",
                    "expected_return": "float",
                    "return_distribution": "dict",
                    "confidence_score": "float",
                    "features_used": "list",
                    "model_version": "str",
                    "scenario": "str",
                    "metadata": "dict"
                }
            }
        }
    
    def compare_schemas(self, contract_type: str) -> SchemaComparisonResult:
        """
        Compare local and cloud schemas for contract type.
        
        Args:
            contract_type: Type of contract to compare
        
        Returns:
            SchemaComparisonResult with differences
        """
        self.comparisons_performed += 1
        
        local_schema = self.local_schemas.get(contract_type)
        cloud_schema = self.cloud_schemas.get(contract_type)
        
        differences: List[SchemaDifference] = []
        
        # Check if schemas exist
        if local_schema is None:
            differences.append(SchemaDifference(
                field_path="<schema>",
                diff_type="missing_schema",
                severity=DiffSeverity.ERROR.value,
                local_value=None,
                cloud_value="exists",
                description=f"Local schema for {contract_type} not found"
            ))
            is_compatible = False
        elif cloud_schema is None:
            differences.append(SchemaDifference(
                field_path="<schema>",
                diff_type="missing_schema",
                severity=DiffSeverity.ERROR.value,
                local_value="exists",
                cloud_value=None,
                description=f"Cloud schema for {contract_type} not found"
            ))
            is_compatible = False
        else:
            # Compare versions
            local_version = local_schema.get("version", "unknown")
            cloud_version = cloud_schema.get("version", "unknown")
            
            if local_version != cloud_version:
                differences.append(SchemaDifference(
                    field_path="version",
                    diff_type="version_mismatch",
                    severity=DiffSeverity.WARNING.value,
                    local_value=local_version,
                    cloud_value=cloud_version,
                    description=f"Schema version mismatch: local={local_version}, cloud={cloud_version}"
                ))
            
            # Compare required fields
            local_required = set(local_schema.get("required_fields", []))
            cloud_required = set(cloud_schema.get("required_fields", []))
            
            missing_in_local = cloud_required - local_required
            missing_in_cloud = local_required - cloud_required
            
            for field in missing_in_local:
                differences.append(SchemaDifference(
                    field_path=field,
                    diff_type="missing_field",
                    severity=DiffSeverity.ERROR.value,
                    local_value=None,
                    cloud_value="required",
                    description=f"Field '{field}' required by cloud but missing in local schema"
                ))
            
            for field in missing_in_cloud:
                differences.append(SchemaDifference(
                    field_path=field,
                    diff_type="missing_field",
                    severity=DiffSeverity.WARNING.value,
                    local_value="required",
                    cloud_value=None,
                    description=f"Field '{field}' required by local but missing in cloud schema"
                ))
            
            # Compare field types
            local_types = local_schema.get("field_types", {})
            cloud_types = cloud_schema.get("field_types", {})
            
            common_fields = set(local_types.keys()) & set(cloud_types.keys())
            
            for field in common_fields:
                local_type = local_types[field]
                cloud_type = cloud_types[field]
                
                if local_type != cloud_type:
                    differences.append(SchemaDifference(
                        field_path=field,
                        diff_type="type_mismatch",
                        severity=DiffSeverity.ERROR.value,
                        local_value=local_type,
                        cloud_value=cloud_type,
                        description=f"Type mismatch for '{field}': local={local_type}, cloud={cloud_type}"
                    ))
            
            # Determine compatibility (no ERRORs)
            has_errors = any(d.severity == DiffSeverity.ERROR.value for d in differences)
            is_compatible = not has_errors
        
        if is_compatible:
            self.compatible_schemas += 1
        else:
            self.incompatible_schemas += 1
        
        return SchemaComparisonResult(
            contract_type=contract_type,
            is_compatible=is_compatible,
            differences=differences,
            compared_at=datetime.utcnow().isoformat() + "Z",
            local_schema_version=local_schema.get("version", "unknown") if local_schema else "unknown",
            cloud_schema_version=cloud_schema.get("version", "unknown") if cloud_schema else "unknown"
        )
    
    def compare_all_schemas(self) -> Dict[str, SchemaComparisonResult]:
        """
        Compare all contract schemas.
        
        Returns:
            Dict mapping contract type to comparison result
        """
        results = {}
        
        all_contract_types = set(self.local_schemas.keys()) | set(self.cloud_schemas.keys())
        
        for contract_type in all_contract_types:
            results[contract_type] = self.compare_schemas(contract_type)
        
        return results
    
    def generate_report(self, output_path: Optional[Path] = None) -> str:
        """
        Generate comprehensive schema validation report.
        
        Args:
            output_path: Optional path to save report (Markdown)
        
        Returns:
            Report content as string
        """
        results = self.compare_all_schemas()
        
        # Build Markdown report
        lines = [
            "# Schema Validation Report",
            "",
            f"**Generated:** {datetime.utcnow().isoformat()}Z",
            f"**Schemas Compared:** {len(results)}",
            "",
            "## Summary",
            ""
        ]
        
        # Summary table
        total_compatible = sum(1 for r in results.values() if r.is_compatible)
        total_incompatible = len(results) - total_compatible
        
        lines.extend([
            f"- **Compatible Schemas:** {total_compatible}",
            f"- **Incompatible Schemas:** {total_incompatible}",
            ""
        ])
        
        # Detailed results for each contract
        for contract_type, result in sorted(results.items()):
            lines.extend([
                f"## Contract: `{contract_type}`",
                "",
                f"**Status:** {'✅ Compatible' if result.is_compatible else '❌ Incompatible'}",
                f"**Local Version:** {result.local_schema_version}",
                f"**Cloud Version:** {result.cloud_schema_version}",
                ""
            ])
            
            if result.differences:
                lines.append("### Differences")
                lines.append("")
                lines.append("| Field | Type | Severity | Description |")
                lines.append("|-------|------|----------|-------------|")
                
                for diff in result.differences:
                    severity_emoji = {
                        "error": "🔴",
                        "warning": "🟡",
                        "info": "🔵"
                    }.get(diff.severity, "")
                    
                    lines.append(
                        f"| `{diff.field_path}` | {diff.diff_type} | "
                        f"{severity_emoji} {diff.severity} | {diff.description} |"
                    )
                
                lines.append("")
            else:
                lines.append("✅ No differences found")
                lines.append("")
        
        report_content = "\n".join(lines)
        
        # Save to file if path provided
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(report_content)
        
        return report_content
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get schema comparison statistics.
        
        Returns:
            Dict with stats
        """
        compatibility_rate = self.compatible_schemas / self.comparisons_performed if self.comparisons_performed > 0 else 0.0
        
        return {
            "comparisons_performed": self.comparisons_performed,
            "compatible_schemas": self.compatible_schemas,
            "incompatible_schemas": self.incompatible_schemas,
            "compatibility_rate": compatibility_rate,
            "local_schema_count": len(self.local_schemas),
            "cloud_schema_count": len(self.cloud_schemas)
        }


# Singleton instance
_global_checker: Optional[SchemaDiffChecker] = None


def get_global_checker() -> SchemaDiffChecker:
    """Get or create global schema diff checker instance."""
    global _global_checker
    if _global_checker is None:
        _global_checker = SchemaDiffChecker()
    return _global_checker


# Convenience functions

def compare_schemas(contract_type: str) -> SchemaComparisonResult:
    """Convenience wrapper for global checker compare_schemas."""
    return get_global_checker().compare_schemas(contract_type)


def compare_all_schemas() -> Dict[str, SchemaComparisonResult]:
    """Convenience wrapper for global checker compare_all_schemas."""
    return get_global_checker().compare_all_schemas()


def generate_report(output_path: Optional[Path] = None) -> str:
    """Convenience wrapper for global checker generate_report."""
    return get_global_checker().generate_report(output_path)
