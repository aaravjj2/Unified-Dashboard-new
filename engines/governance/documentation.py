"""
Documentation & Governance System
Phase 13 - Documentation & Governance (Items 881-940)

Complete implementation of:
- API documentation generator
- User guide generator
- Compliance & audit logging
- Model governance
- Data governance
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union, Type
from enum import Enum
from datetime import datetime, timedelta
import hashlib
import json
import inspect


# =============================================================================
# API DOCUMENTATION (Items 881-900)
# =============================================================================

@dataclass
class ParameterDoc:
    """API parameter documentation."""
    name: str
    type_hint: str
    description: str
    required: bool = True
    default: Any = None
    example: Any = None


@dataclass
class EndpointDoc:
    """API endpoint documentation."""
    path: str
    method: str
    summary: str
    description: str
    parameters: List[ParameterDoc] = field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    deprecated: bool = False
    
    def to_openapi(self) -> Dict[str, Any]:
        """Convert to OpenAPI specification format."""
        operation = {
            "summary": self.summary,
            "description": self.description,
            "tags": self.tags,
            "deprecated": self.deprecated,
            "parameters": [
                {
                    "name": p.name,
                    "in": "query",
                    "required": p.required,
                    "description": p.description,
                    "schema": {"type": p.type_hint}
                }
                for p in self.parameters
            ],
            "responses": {
                str(code): {
                    "description": resp.get("description", ""),
                    "content": {
                        "application/json": {
                            "schema": resp.get("schema", {})
                        }
                    }
                }
                for code, resp in self.responses.items()
            }
        }
        
        if self.request_body:
            operation["requestBody"] = {
                "content": {
                    "application/json": {
                        "schema": self.request_body
                    }
                }
            }
        
        return operation


class APIDocGenerator:
    """Generate API documentation."""
    
    def __init__(self, title: str = "API Documentation", version: str = "1.0.0"):
        self.title = title
        self.version = version
        self.endpoints: List[EndpointDoc] = []
        self.tags: List[Dict[str, str]] = []
    
    def add_endpoint(self, endpoint: EndpointDoc):
        """Add an endpoint to documentation."""
        self.endpoints.append(endpoint)
        for tag in endpoint.tags:
            if not any(t["name"] == tag for t in self.tags):
                self.tags.append({"name": tag, "description": f"{tag} operations"})
    
    def document(self, path: str, method: str = "GET", tags: List[str] = None):
        """Decorator to document a function as an API endpoint."""
        def decorator(func: Callable):
            sig = inspect.signature(func)
            doc = inspect.getdoc(func) or ""
            
            params = []
            for name, param in sig.parameters.items():
                if name == "self":
                    continue
                params.append(ParameterDoc(
                    name=name,
                    type_hint=str(param.annotation) if param.annotation != inspect.Parameter.empty else "any",
                    description=f"Parameter: {name}",
                    required=param.default == inspect.Parameter.empty,
                    default=param.default if param.default != inspect.Parameter.empty else None
                ))
            
            endpoint = EndpointDoc(
                path=path,
                method=method,
                summary=doc.split('\n')[0] if doc else func.__name__,
                description=doc,
                parameters=params,
                tags=tags or [],
                responses={200: {"description": "Success"}}
            )
            
            self.add_endpoint(endpoint)
            return func
        return decorator
    
    def generate_openapi(self) -> Dict[str, Any]:
        """Generate OpenAPI specification."""
        paths = {}
        for endpoint in self.endpoints:
            if endpoint.path not in paths:
                paths[endpoint.path] = {}
            paths[endpoint.path][endpoint.method.lower()] = endpoint.to_openapi()
        
        return {
            "openapi": "3.0.0",
            "info": {
                "title": self.title,
                "version": self.version
            },
            "tags": self.tags,
            "paths": paths
        }
    
    def generate_markdown(self) -> str:
        """Generate Markdown documentation."""
        lines = [f"# {self.title}", f"Version: {self.version}", ""]
        
        # Group by tags
        by_tag: Dict[str, List[EndpointDoc]] = {}
        for endpoint in self.endpoints:
            for tag in endpoint.tags or ["default"]:
                if tag not in by_tag:
                    by_tag[tag] = []
                by_tag[tag].append(endpoint)
        
        for tag, endpoints in by_tag.items():
            lines.append(f"## {tag}")
            lines.append("")
            
            for ep in endpoints:
                lines.append(f"### {ep.method} {ep.path}")
                lines.append("")
                lines.append(f"**{ep.summary}**")
                lines.append("")
                if ep.description:
                    lines.append(ep.description)
                    lines.append("")
                
                if ep.parameters:
                    lines.append("**Parameters:**")
                    lines.append("")
                    lines.append("| Name | Type | Required | Description |")
                    lines.append("|------|------|----------|-------------|")
                    for param in ep.parameters:
                        req = "Yes" if param.required else "No"
                        lines.append(f"| {param.name} | {param.type_hint} | {req} | {param.description} |")
                    lines.append("")
                
                lines.append("---")
                lines.append("")
        
        return "\n".join(lines)


# =============================================================================
# USER GUIDE GENERATOR (Items 901-910)
# =============================================================================

@dataclass
class GuideSection:
    """User guide section."""
    id: str
    title: str
    content: str
    subsections: List['GuideSection'] = field(default_factory=list)
    order: int = 0


class UserGuideGenerator:
    """Generate user guides and tutorials."""
    
    def __init__(self, title: str = "User Guide"):
        self.title = title
        self.sections: List[GuideSection] = []
        self.glossary: Dict[str, str] = {}
    
    def add_section(self, section: GuideSection):
        """Add a section to the guide."""
        self.sections.append(section)
        self.sections.sort(key=lambda s: s.order)
    
    def add_glossary_term(self, term: str, definition: str):
        """Add a glossary term."""
        self.glossary[term] = definition
    
    def generate_markdown(self) -> str:
        """Generate Markdown user guide."""
        lines = [f"# {self.title}", ""]
        
        # Table of contents
        lines.append("## Table of Contents")
        lines.append("")
        for i, section in enumerate(self.sections, 1):
            lines.append(f"{i}. [{section.title}](#{section.id})")
            for j, sub in enumerate(section.subsections, 1):
                lines.append(f"   {i}.{j}. [{sub.title}](#{sub.id})")
        lines.append("")
        
        # Sections
        for section in self.sections:
            lines.append(f"## {section.title} {{#{section.id}}}")
            lines.append("")
            lines.append(section.content)
            lines.append("")
            
            for sub in section.subsections:
                lines.append(f"### {sub.title} {{#{sub.id}}}")
                lines.append("")
                lines.append(sub.content)
                lines.append("")
        
        # Glossary
        if self.glossary:
            lines.append("## Glossary")
            lines.append("")
            for term in sorted(self.glossary.keys()):
                lines.append(f"**{term}**: {self.glossary[term]}")
                lines.append("")
        
        return "\n".join(lines)


# =============================================================================
# AUDIT LOGGING (Items 911-920)
# =============================================================================

class AuditAction(Enum):
    """Audit action types."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    TRADE = "trade"
    CONFIG_CHANGE = "config_change"
    MODEL_DEPLOY = "model_deploy"
    DATA_EXPORT = "data_export"


@dataclass
class AuditEntry:
    """Audit log entry."""
    id: str
    timestamp: datetime
    user_id: str
    action: AuditAction
    resource_type: str
    resource_id: str
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    outcome: str = "success"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "action": self.action.value,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "outcome": self.outcome
        }


class AuditLogger:
    """Audit logging system."""
    
    def __init__(self, retention_days: int = 365):
        self.retention_days = retention_days
        self.entries: List[AuditEntry] = []
    
    def log(self, user_id: str, action: AuditAction, resource_type: str, resource_id: str, 
            details: Dict[str, Any] = None, ip_address: str = None, outcome: str = "success") -> AuditEntry:
        """Log an audit event."""
        entry = AuditEntry(
            id=hashlib.md5(f"{datetime.now().isoformat()}_{user_id}_{action.value}".encode()).hexdigest()[:16],
            timestamp=datetime.now(),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            outcome=outcome
        )
        self.entries.append(entry)
        return entry
    
    def query(self, user_id: Optional[str] = None, action: Optional[AuditAction] = None,
              resource_type: Optional[str] = None, start_time: Optional[datetime] = None,
              end_time: Optional[datetime] = None) -> List[AuditEntry]:
        """Query audit logs."""
        results = self.entries
        
        if user_id:
            results = [e for e in results if e.user_id == user_id]
        if action:
            results = [e for e in results if e.action == action]
        if resource_type:
            results = [e for e in results if e.resource_type == resource_type]
        if start_time:
            results = [e for e in results if e.timestamp >= start_time]
        if end_time:
            results = [e for e in results if e.timestamp <= end_time]
        
        return results
    
    def cleanup(self):
        """Remove entries older than retention period."""
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        self.entries = [e for e in self.entries if e.timestamp >= cutoff]


# =============================================================================
# MODEL GOVERNANCE (Items 921-930)
# =============================================================================

class ModelStatus(Enum):
    """Model lifecycle status."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


@dataclass
class ModelCard:
    """Model documentation card (ML model governance)."""
    model_id: str
    name: str
    version: str
    description: str
    status: ModelStatus
    
    # Model details
    model_type: str
    framework: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    
    # Training info
    training_date: datetime
    training_data_description: str
    training_data_size: int
    
    # Performance metrics
    metrics: Dict[str, float]
    
    # Governance
    owner: str
    reviewers: List[str]
    approved_by: Optional[str] = None
    approval_date: Optional[datetime] = None
    
    # Ethical considerations
    intended_use: str
    limitations: List[str] = field(default_factory=list)
    ethical_considerations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "status": self.status.value,
            "model_type": self.model_type,
            "framework": self.framework,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "training_date": self.training_date.isoformat(),
            "training_data_description": self.training_data_description,
            "training_data_size": self.training_data_size,
            "metrics": self.metrics,
            "owner": self.owner,
            "reviewers": self.reviewers,
            "approved_by": self.approved_by,
            "approval_date": self.approval_date.isoformat() if self.approval_date else None,
            "intended_use": self.intended_use,
            "limitations": self.limitations,
            "ethical_considerations": self.ethical_considerations
        }
    
    def to_markdown(self) -> str:
        """Generate model card as Markdown."""
        lines = [
            f"# Model Card: {self.name}",
            "",
            f"**Version:** {self.version}",
            f"**Status:** {self.status.value}",
            f"**Model ID:** {self.model_id}",
            "",
            "## Description",
            self.description,
            "",
            "## Model Details",
            f"- **Type:** {self.model_type}",
            f"- **Framework:** {self.framework}",
            "",
            "## Training Information",
            f"- **Training Date:** {self.training_date.isoformat()}",
            f"- **Data Description:** {self.training_data_description}",
            f"- **Data Size:** {self.training_data_size:,} samples",
            "",
            "## Performance Metrics",
        ]
        
        for metric, value in self.metrics.items():
            lines.append(f"- **{metric}:** {value:.4f}")
        
        lines.extend([
            "",
            "## Intended Use",
            self.intended_use,
            "",
            "## Limitations",
        ])
        
        for limitation in self.limitations:
            lines.append(f"- {limitation}")
        
        lines.extend([
            "",
            "## Ethical Considerations",
        ])
        
        for consideration in self.ethical_considerations:
            lines.append(f"- {consideration}")
        
        lines.extend([
            "",
            "## Governance",
            f"- **Owner:** {self.owner}",
            f"- **Reviewers:** {', '.join(self.reviewers)}",
            f"- **Approved By:** {self.approved_by or 'Pending'}",
            f"- **Approval Date:** {self.approval_date.isoformat() if self.approval_date else 'Pending'}",
        ])
        
        return "\n".join(lines)


class ModelRegistry:
    """Model registry for governance."""
    
    def __init__(self):
        self.models: Dict[str, ModelCard] = {}
        self.audit_logger = AuditLogger()
    
    def register(self, model_card: ModelCard, user_id: str) -> str:
        """Register a new model."""
        self.models[model_card.model_id] = model_card
        self.audit_logger.log(
            user_id=user_id,
            action=AuditAction.CREATE,
            resource_type="model",
            resource_id=model_card.model_id,
            details={"version": model_card.version, "status": model_card.status.value}
        )
        return model_card.model_id
    
    def promote(self, model_id: str, new_status: ModelStatus, user_id: str) -> bool:
        """Promote model to new status."""
        if model_id not in self.models:
            return False
        
        old_status = self.models[model_id].status
        self.models[model_id].status = new_status
        
        self.audit_logger.log(
            user_id=user_id,
            action=AuditAction.UPDATE,
            resource_type="model",
            resource_id=model_id,
            details={"old_status": old_status.value, "new_status": new_status.value}
        )
        return True
    
    def approve(self, model_id: str, approver_id: str) -> bool:
        """Approve a model for production."""
        if model_id not in self.models:
            return False
        
        self.models[model_id].approved_by = approver_id
        self.models[model_id].approval_date = datetime.now()
        
        self.audit_logger.log(
            user_id=approver_id,
            action=AuditAction.UPDATE,
            resource_type="model",
            resource_id=model_id,
            details={"action": "approval"}
        )
        return True
    
    def get_production_models(self) -> List[ModelCard]:
        """Get all production models."""
        return [m for m in self.models.values() if m.status == ModelStatus.PRODUCTION]


# =============================================================================
# DATA GOVERNANCE (Items 931-940)
# =============================================================================

class DataClassification(Enum):
    """Data classification levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


@dataclass
class DataCatalogEntry:
    """Data catalog entry."""
    dataset_id: str
    name: str
    description: str
    classification: DataClassification
    
    # Schema
    schema: Dict[str, str]
    row_count: int
    
    # Ownership
    owner: str
    steward: str
    
    # Quality
    quality_score: float
    last_quality_check: datetime
    
    # Access
    access_groups: List[str]
    retention_days: int
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "description": self.description,
            "classification": self.classification.value,
            "schema": self.schema,
            "row_count": self.row_count,
            "owner": self.owner,
            "steward": self.steward,
            "quality_score": self.quality_score,
            "last_quality_check": self.last_quality_check.isoformat(),
            "access_groups": self.access_groups,
            "retention_days": self.retention_days,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags
        }


class DataGovernance:
    """Data governance system."""
    
    def __init__(self):
        self.catalog: Dict[str, DataCatalogEntry] = {}
        self.audit_logger = AuditLogger()
    
    def register_dataset(self, entry: DataCatalogEntry, user_id: str) -> str:
        """Register a dataset in the catalog."""
        self.catalog[entry.dataset_id] = entry
        self.audit_logger.log(
            user_id=user_id,
            action=AuditAction.CREATE,
            resource_type="dataset",
            resource_id=entry.dataset_id,
            details={"classification": entry.classification.value}
        )
        return entry.dataset_id
    
    def check_access(self, dataset_id: str, user_groups: List[str]) -> bool:
        """Check if user has access to dataset."""
        if dataset_id not in self.catalog:
            return False
        
        entry = self.catalog[dataset_id]
        return any(g in entry.access_groups for g in user_groups)
    
    def search(self, query: str = None, classification: DataClassification = None,
               tags: List[str] = None) -> List[DataCatalogEntry]:
        """Search the data catalog."""
        results = list(self.catalog.values())
        
        if query:
            query_lower = query.lower()
            results = [e for e in results if 
                      query_lower in e.name.lower() or 
                      query_lower in e.description.lower()]
        
        if classification:
            results = [e for e in results if e.classification == classification]
        
        if tags:
            results = [e for e in results if any(t in e.tags for t in tags)]
        
        return results
    
    def get_retention_report(self) -> Dict[str, Any]:
        """Get data retention compliance report."""
        now = datetime.now()
        
        compliant = []
        non_compliant = []
        
        for entry in self.catalog.values():
            age_days = (now - entry.created_at).days
            if age_days > entry.retention_days:
                non_compliant.append({
                    "dataset_id": entry.dataset_id,
                    "name": entry.name,
                    "age_days": age_days,
                    "retention_days": entry.retention_days,
                    "overdue_days": age_days - entry.retention_days
                })
            else:
                compliant.append(entry.dataset_id)
        
        return {
            "total_datasets": len(self.catalog),
            "compliant": len(compliant),
            "non_compliant": len(non_compliant),
            "non_compliant_details": non_compliant
        }


# =============================================================================
# COMPLETE PHASE 13
# =============================================================================

def complete_phase_13() -> Dict[str, Any]:
    """Complete Phase 13 deliverables."""
    
    # API Documentation
    api_doc = APIDocGenerator("Options Dashboard API", "2.0.0")
    
    @api_doc.document("/api/options/chain", "GET", ["Options"])
    def get_options_chain(symbol: str, expiration: str = None):
        """Get options chain for a symbol."""
        pass
    
    @api_doc.document("/api/portfolio/positions", "GET", ["Portfolio"])
    def get_positions():
        """Get current portfolio positions."""
        pass
    
    # User Guide
    guide = UserGuideGenerator("Options Trading Dashboard Guide")
    guide.add_section(GuideSection(
        id="getting-started",
        title="Getting Started",
        content="Welcome to the Options Trading Dashboard...",
        order=1
    ))
    guide.add_glossary_term("Delta", "Rate of change of option price with respect to underlying price")
    guide.add_glossary_term("IV", "Implied Volatility - market's forecast of likely movement")
    
    # Model Registry
    registry = ModelRegistry()
    sample_model = ModelCard(
        model_id="vol-pred-001",
        name="Volatility Predictor",
        version="1.0.0",
        description="Predicts 30-day implied volatility",
        status=ModelStatus.PRODUCTION,
        model_type="regression",
        framework="sklearn",
        input_schema={"features": "array[float]"},
        output_schema={"volatility": "float"},
        training_date=datetime.now(),
        training_data_description="Historical options data",
        training_data_size=100000,
        metrics={"mse": 0.02, "r2": 0.85},
        owner="ml-team",
        reviewers=["reviewer1", "reviewer2"],
        intended_use="Production volatility forecasting",
        limitations=["Requires sufficient historical data"]
    )
    registry.register(sample_model, "admin")
    
    # Data Governance
    governance = DataGovernance()
    sample_dataset = DataCatalogEntry(
        dataset_id="options-2024",
        name="Options Data 2024",
        description="Historical options data for 2024",
        classification=DataClassification.INTERNAL,
        schema={"symbol": "string", "strike": "float", "iv": "float"},
        row_count=1000000,
        owner="data-team",
        steward="data-steward",
        quality_score=0.95,
        last_quality_check=datetime.now(),
        access_groups=["trading", "analytics"],
        retention_days=365,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        tags=["options", "trading"]
    )
    governance.register_dataset(sample_dataset, "admin")
    
    return {
        "api_endpoints_documented": len(api_doc.endpoints),
        "guide_sections": len(guide.sections),
        "glossary_terms": len(guide.glossary),
        "registered_models": len(registry.models),
        "catalog_datasets": len(governance.catalog),
        "status": "complete"
    }


if __name__ == "__main__":
    print("Phase 13 Summary:")
    result = complete_phase_13()
    for k, v in result.items():
        print(f"  {k}: {v}")
