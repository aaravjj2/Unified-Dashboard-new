"""
Azure Stub Clients (Phase 4 - Hybrid Readiness)

Mock clients for Azure ML, Blob Storage, and Monitor services.
Provides async signatures matching real Azure SDK while running locally.

Core Clients:
- AzureMLStubClient: ML prediction and training jobs
- AzureBlobStubClient: Blob storage I/O (reads/writes to local /data/azure_stub_storage/)
- AzureMonitorStubClient: Telemetry and diagnostics logging

All clients mimic async signatures for drop-in replacement when Azure is available.

Usage:
    >>> client = AzureMLStubClient()
    >>> result = await client.submit_job(input_spec)
    >>> print(result.predictions)
"""

import json
import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import time

import numpy as np

from phase4_hybrid_stubs.azure_contracts.azure_contract_definitions import (
    ContractInputSpec,
    ContractOutputSpec,
    JobStatus,
    create_mock_output
)

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Local storage paths (mirrors Azure Blob)
STUB_STORAGE_ROOT = Path(__file__).parent.parent.parent / "data" / "azure_stub_storage"
STUB_LOGS_ROOT = Path(__file__).parent.parent.parent / "data" / "hybrid_logs"

# Ensure directories exist
STUB_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
STUB_LOGS_ROOT.mkdir(parents=True, exist_ok=True)

# Simulation parameters
STUB_LATENCY_MS = {
    'forecast': (200, 500),  # (min, max) milliseconds
    'backtest': (500, 1500),
    'risk': (300, 800),
    'optimization': (1000, 3000),
    'shap': (400, 900),
    'batch': (2000, 5000)
}

STUB_SUCCESS_RATE = 0.95  # 95% success rate for job simulation


# ============================================================================
# AZURE ML STUB CLIENT
# ============================================================================

class AzureMLStubClient:
    """
    Mock Azure ML client for local testing.
    
    Simulates:
    - Job submission and tracking
    - Prediction generation
    - SHAP explainability
    - Model versioning
    
    All methods are async to match real Azure ML SDK.
    
    Example:
        >>> client = AzureMLStubClient()
        >>> input_spec = ContractInputSpec(ticker='AAPL', features={...}, ...)
        >>> output = await client.submit_job(input_spec)
        >>> print(output.predictions)
    """
    
    def __init__(self, workspace_name: str = "unified-dashboard-ml-stub"):
        """
        Initialize stub ML client.
        
        Args:
            workspace_name: Mock workspace name
        """
        self.workspace_name = workspace_name
        self.jobs = {}  # job_uuid -> job_data
        self.models = {
            'portfolio-predictor': {'version': '1.0.0', 'status': 'registered'}
        }
        
        logger.info(f"🧪 AzureMLStubClient initialized (workspace={workspace_name})")
    
    async def submit_job(self, input_spec: ContractInputSpec) -> ContractOutputSpec:
        """
        Submit ML job and return predictions.
        
        Args:
            input_spec: Input contract specification
        
        Returns:
            ContractOutputSpec with predictions
        
        Example:
            >>> output = await client.submit_job(input_spec)
        """
        job_uuid = input_spec.uuid
        mode = input_spec.mode
        ticker = input_spec.ticker
        
        logger.info(f"📤 Submitting {mode} job for {ticker} (uuid={job_uuid[:8]}...)")
        
        # Simulate latency
        latency_range = STUB_LATENCY_MS.get(mode, (200, 500))
        latency_ms = np.random.uniform(*latency_range)
        await asyncio.sleep(latency_ms / 1000.0)
        
        # Simulate occasional failures
        if np.random.rand() > STUB_SUCCESS_RATE:
            logger.warning(f"❌ Job {job_uuid[:8]}... simulated failure")
            return ContractOutputSpec(
                job_uuid=job_uuid,
                ticker=ticker,
                predictions=[],
                confidence=[],
                status=JobStatus.FAILED,
                error_message="Simulated random failure for testing",
                latency_ms=latency_ms
            )
        
        # Generate predictions based on mode
        if mode == 'forecast':
            output = self._generate_forecast(input_spec, latency_ms)
        elif mode == 'backtest':
            output = self._generate_backtest(input_spec, latency_ms)
        elif mode == 'risk':
            output = self._generate_risk(input_spec, latency_ms)
        elif mode == 'shap':
            output = self._generate_shap(input_spec, latency_ms)
        else:
            output = create_mock_output(job_uuid, ticker)
            output.latency_ms = latency_ms
        
        # Store job record
        self.jobs[job_uuid] = {
            'input': input_spec.to_dict(),
            'output': output.to_dict(),
            'submitted_at': datetime.now().isoformat(),
            'status': str(output.status)
        }
        
        # Save to local storage
        await self._save_job_output(job_uuid, output)
        
        logger.info(f"✅ Job {job_uuid[:8]}... completed ({latency_ms:.0f}ms)")
        return output
    
    def _generate_forecast(self, input_spec: ContractInputSpec, latency_ms: float) -> ContractOutputSpec:
        """Generate forecast predictions."""
        ticker = input_spec.ticker
        horizon_days = input_spec.forecast_horizon.to_days()
        
        # Deterministic seed based on ticker + features
        seed = int(hashlib.md5(f"{ticker}{json.dumps(input_spec.features, sort_keys=True)}".encode()).hexdigest()[:8], 16)
        np.random.seed(seed)
        
        # Generate predictions with realistic drift
        base_return = np.random.uniform(-0.02, 0.08)
        drift = np.random.uniform(-0.001, 0.001)
        volatility = np.random.uniform(0.01, 0.03)
        
        predictions = []
        confidences = []
        
        for day in range(horizon_days):
            pred = base_return + drift * day + np.random.normal(0, volatility)
            conf = np.random.uniform(0.75, 0.95) * (1 - 0.01 * day)  # Confidence decays with time
            predictions.append(float(pred))
            confidences.append(float(conf))
        
        # Generate SHAP explainability
        shap_blob = self._generate_shap_blob(input_spec)
        
        return ContractOutputSpec(
            job_uuid=input_spec.uuid,
            ticker=ticker,
            predictions=predictions,
            confidence=confidences,
            explainability_blob=shap_blob,
            status=JobStatus.COMPLETED,
            model_version='1.0.0',
            latency_ms=latency_ms,
            metadata={'horizon_days': horizon_days, 'base_return': base_return}
        )
    
    def _generate_backtest(self, input_spec: ContractInputSpec, latency_ms: float) -> ContractOutputSpec:
        """Generate backtest results."""
        ticker = input_spec.ticker
        
        # Simulate backtest performance metrics
        seed = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
        np.random.seed(seed)
        
        num_trades = np.random.randint(20, 100)
        win_rate = np.random.uniform(0.45, 0.65)
        sharpe = np.random.uniform(0.5, 2.5)
        max_drawdown = np.random.uniform(0.10, 0.35)
        
        # Generate trade-level predictions
        predictions = np.random.normal(0.05, 0.08, num_trades).tolist()
        confidences = np.random.uniform(0.70, 0.90, num_trades).tolist()
        
        return ContractOutputSpec(
            job_uuid=input_spec.uuid,
            ticker=ticker,
            predictions=predictions,
            confidence=confidences,
            status=JobStatus.COMPLETED,
            model_version='1.0.0',
            latency_ms=latency_ms,
            metadata={
                'num_trades': num_trades,
                'win_rate': win_rate,
                'sharpe_ratio': sharpe,
                'max_drawdown': max_drawdown
            }
        )
    
    def _generate_risk(self, input_spec: ContractInputSpec, latency_ms: float) -> ContractOutputSpec:
        """Generate risk metrics."""
        ticker = input_spec.ticker
        
        seed = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
        np.random.seed(seed)
        
        # Risk metrics
        var_95 = float(np.random.uniform(0.02, 0.10))
        cvar_95 = float(np.random.uniform(0.03, 0.15))
        volatility = float(np.random.uniform(0.15, 0.35))
        
        return ContractOutputSpec(
            job_uuid=input_spec.uuid,
            ticker=ticker,
            predictions=[var_95, cvar_95, volatility],
            confidence=[0.95, 0.95, 0.90],
            status=JobStatus.COMPLETED,
            model_version='1.0.0',
            latency_ms=latency_ms,
            metadata={
                'var_95': var_95,
                'cvar_95': cvar_95,
                'volatility': volatility,
                'confidence_level': 0.95
            }
        )
    
    def _generate_shap(self, input_spec: ContractInputSpec, latency_ms: float) -> ContractOutputSpec:
        """Generate SHAP explainability data."""
        shap_blob = self._generate_shap_blob(input_spec)
        
        return ContractOutputSpec(
            job_uuid=input_spec.uuid,
            ticker=input_spec.ticker,
            predictions=[0.05],  # Base prediction
            confidence=[0.85],
            explainability_blob=shap_blob,
            status=JobStatus.COMPLETED,
            model_version='1.0.0',
            latency_ms=latency_ms
        )
    
    def _generate_shap_blob(self, input_spec: ContractInputSpec) -> Dict[str, Any]:
        """Generate SHAP values for features."""
        features = input_spec.features
        seed = int(hashlib.md5(input_spec.ticker.encode()).hexdigest()[:8], 16)
        np.random.seed(seed)
        
        shap_values = {}
        feature_importance = []
        
        for feat_name, feat_value in features.items():
            shap_val = float(np.random.normal(0, 0.1))
            shap_values[feat_name] = shap_val
            feature_importance.append({
                'feature': feat_name,
                'shap_value': shap_val,
                'feature_value': feat_value,
                'abs_importance': abs(shap_val)
            })
        
        # Sort by absolute importance
        feature_importance.sort(key=lambda x: x['abs_importance'], reverse=True)
        
        return {
            'shap_values': shap_values,
            'feature_importance': feature_importance[:10],  # Top 10
            'base_value': 0.0,
            'expected_value': 0.05
        }
    
    async def _save_job_output(self, job_uuid: str, output: ContractOutputSpec):
        """Save job output to local storage."""
        output_dir = STUB_STORAGE_ROOT / "jobs"
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / f"{job_uuid}.json"
        output_file.write_text(json.dumps(output.to_dict(), indent=2))
        
        logger.debug(f"💾 Saved job output: {output_file}")
    
    async def get_job_status(self, job_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Get job status and details.
        
        Args:
            job_uuid: Job identifier
        
        Returns:
            Job data dictionary or None if not found
        """
        return self.jobs.get(job_uuid)


# ============================================================================
# AZURE BLOB STUB CLIENT
# ============================================================================

class AzureBlobStubClient:
    """
    Mock Azure Blob Storage client.
    
    Reads/writes to local /data/azure_stub_storage/ directory.
    Mimics Azure Blob SDK async signatures.
    
    Example:
        >>> client = AzureBlobStubClient()
        >>> await client.upload_blob('predictions/AAPL.json', data)
        >>> content = await client.download_blob('predictions/AAPL.json')
    """
    
    def __init__(self, container_name: str = "ml-predictions"):
        """
        Initialize stub blob client.
        
        Args:
            container_name: Mock container name
        """
        self.container_name = container_name
        self.storage_root = STUB_STORAGE_ROOT / container_name
        self.storage_root.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🗄️  AzureBlobStubClient initialized (container={container_name})")
    
    async def upload_blob(self, blob_name: str, data: Any, overwrite: bool = True) -> bool:
        """
        Upload blob to local storage.
        
        Args:
            blob_name: Blob path (e.g., 'predictions/AAPL.json')
            data: Data to upload (str, bytes, or dict)
            overwrite: Whether to overwrite existing blob
        
        Returns:
            True if successful
        """
        blob_path = self.storage_root / blob_name
        blob_path.parent.mkdir(parents=True, exist_ok=True)
        
        if blob_path.exists() and not overwrite:
            logger.warning(f"Blob {blob_name} exists and overwrite=False")
            return False
        
        # Serialize data
        if isinstance(data, dict):
            content = json.dumps(data, indent=2)
        elif isinstance(data, bytes):
            content = data
        else:
            content = str(data)
        
        # Simulate network latency
        await asyncio.sleep(np.random.uniform(0.05, 0.15))
        
        # Write to local file
        if isinstance(content, bytes):
            blob_path.write_bytes(content)
        else:
            blob_path.write_text(content)
        
        logger.debug(f"📤 Uploaded blob: {blob_name} ({len(content)} bytes)")
        return True
    
    async def download_blob(self, blob_name: str) -> Optional[str]:
        """
        Download blob from local storage.
        
        Args:
            blob_name: Blob path
        
        Returns:
            Blob content as string or None if not found
        """
        blob_path = self.storage_root / blob_name
        
        if not blob_path.exists():
            logger.warning(f"Blob {blob_name} not found")
            return None
        
        # Simulate network latency
        await asyncio.sleep(np.random.uniform(0.05, 0.15))
        
        content = blob_path.read_text()
        logger.debug(f"📥 Downloaded blob: {blob_name} ({len(content)} bytes)")
        
        return content
    
    async def list_blobs(self, prefix: Optional[str] = None) -> List[str]:
        """
        List blobs in container.
        
        Args:
            prefix: Blob name prefix filter
        
        Returns:
            List of blob names
        """
        blobs = []
        
        for path in self.storage_root.rglob('*'):
            if path.is_file():
                relative_path = str(path.relative_to(self.storage_root))
                if prefix is None or relative_path.startswith(prefix):
                    blobs.append(relative_path)
        
        logger.debug(f"📋 Listed {len(blobs)} blobs (prefix={prefix})")
        return blobs
    
    async def delete_blob(self, blob_name: str) -> bool:
        """
        Delete blob from storage.
        
        Args:
            blob_name: Blob path
        
        Returns:
            True if deleted, False if not found
        """
        blob_path = self.storage_root / blob_name
        
        if not blob_path.exists():
            return False
        
        blob_path.unlink()
        logger.debug(f"🗑️  Deleted blob: {blob_name}")
        return True


# ============================================================================
# AZURE MONITOR STUB CLIENT
# ============================================================================

class AzureMonitorStubClient:
    """
    Mock Azure Application Insights client.
    
    Logs telemetry events locally to /data/hybrid_logs/telemetry.jsonl.
    Mimics Application Insights schema.
    
    Example:
        >>> client = AzureMonitorStubClient()
        >>> await client.track_event('prediction_completed', {'ticker': 'AAPL', 'latency_ms': 350})
    """
    
    def __init__(self, instrumentation_key: str = "stub-key"):
        """
        Initialize stub monitor client.
        
        Args:
            instrumentation_key: Mock instrumentation key
        """
        self.instrumentation_key = instrumentation_key
        self.telemetry_file = STUB_LOGS_ROOT / "telemetry.jsonl"
        
        logger.info(f"📊 AzureMonitorStubClient initialized (key={instrumentation_key[:8]}...)")
    
    async def track_event(
        self,
        event_name: str,
        properties: Optional[Dict[str, Any]] = None,
        measurements: Optional[Dict[str, float]] = None
    ):
        """
        Track custom event.
        
        Args:
            event_name: Event name
            properties: Event properties (dimensions)
            measurements: Event measurements (metrics)
        """
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'customEvent',
            'event_name': event_name,
            'properties': properties or {},
            'measurements': measurements or {},
            'instrumentation_key': self.instrumentation_key
        }
        
        await self._write_telemetry(event)
        logger.debug(f"📝 Tracked event: {event_name}")
    
    async def track_metric(
        self,
        metric_name: str,
        value: float,
        properties: Optional[Dict[str, Any]] = None
    ):
        """
        Track metric value.
        
        Args:
            metric_name: Metric name
            value: Metric value
            properties: Metric properties
        """
        metric = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'metric',
            'metric_name': metric_name,
            'value': value,
            'properties': properties or {},
            'instrumentation_key': self.instrumentation_key
        }
        
        await self._write_telemetry(metric)
        logger.debug(f"📈 Tracked metric: {metric_name}={value}")
    
    async def track_request(
        self,
        name: str,
        duration_ms: float,
        success: bool,
        response_code: int = 200,
        properties: Optional[Dict[str, Any]] = None
    ):
        """
        Track HTTP request/operation.
        
        Args:
            name: Request name
            duration_ms: Request duration in milliseconds
            success: Whether request succeeded
            response_code: HTTP response code
            properties: Request properties
        """
        request = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'request',
            'name': name,
            'duration_ms': duration_ms,
            'success': success,
            'response_code': response_code,
            'properties': properties or {},
            'instrumentation_key': self.instrumentation_key
        }
        
        await self._write_telemetry(request)
        logger.debug(f"🌐 Tracked request: {name} ({duration_ms:.0f}ms, success={success})")
    
    async def _write_telemetry(self, event: Dict[str, Any]):
        """Append telemetry event to JSONL file."""
        # Simulate network latency
        await asyncio.sleep(0.01)
        
        with self.telemetry_file.open('a') as f:
            f.write(json.dumps(event) + '\n')


# ============================================================================
# SAMPLE DATA GENERATION
# ============================================================================

async def populate_sample_data():
    """Populate stub storage with sample data for testing."""
    logger.info("🌱 Populating sample data in stub storage...")
    
    blob_client = AzureBlobStubClient()
    
    # Sample forecast
    sample_forecast = {
        'ticker': 'AAPL',
        'predictions': [0.05, 0.06, 0.07],
        'confidence': [0.85, 0.82, 0.79],
        'timestamp': datetime.now().isoformat()
    }
    
    await blob_client.upload_blob('sample_forecast.json', sample_forecast)
    
    # Sample SHAP values
    sample_shap = {
        'ticker': 'AAPL',
        'shap_values': {
            'momentum_20d': 0.05,
            'volatility_20d': -0.03,
            'pe_ratio': 0.02
        },
        'feature_importance': [
            {'feature': 'momentum_20d', 'importance': 0.35},
            {'feature': 'volatility_20d', 'importance': 0.28},
            {'feature': 'pe_ratio', 'importance': 0.15}
        ]
    }
    
    await blob_client.upload_blob('mock_shap_values.json', sample_shap)
    
    logger.info("✅ Sample data populated")


logger.info("✓ Azure Stub Clients loaded (Phase 4 - Hybrid Readiness)")
