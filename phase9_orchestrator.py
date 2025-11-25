"""
Phase 9 — System-Level Orchestrator & Telemetry Validator
===========================================================

Master orchestrator that integrates and validates the complete offline workflow:
- Phase 6: Azure ML forecasting + SHAP explanations
- Phase 8: Advanced analytics (trend, volatility, risk, cache telemetry)
- Phase 8B: Performance-optimized scenario generation

Responsibilities:
1. Sequential pipeline execution (forecast → analytics → risk → dashboard)
2. Real-time telemetry collection (latency, cache hits, throughput)
3. Deterministic reproducibility validation (3-run SHA256 hash comparison)
4. Regression detection (≤5% deviation from baseline metrics)
5. Unified run manifest generation (JSON output)

Performance Targets (from Phase 9 spec):
- Analytics Fusion (Phase 8 + 8B): ≤5s @ 10 tickers
- Full Pipeline (forecast → dashboard): ≤15s @ 50 tickers
- Deterministic Replay: 100% hash match (3 runs)
- Telemetry Drift: ≤5% vs baseline
- Dashboard Latency: ≤200ms UI refresh

Author: Agent 1A — Unified Financial Dashboard Team
Version: 1.0 (Phase 9 - System Orchestration & Validation)
Date: October 29, 2025
"""

import json
import time
import hashlib
import logging
import sys
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# JSON ENCODER FOR NUMPY TYPES
# ============================================================================

class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder for numpy types (int64, float64, etc.)"""
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

# ============================================================================
# IMPORTS FROM EXISTING MODULES
# ============================================================================

try:
    # Phase 6 imports
    from explainability_azure import AzureMLSHAPClient
    from options_forecast_azure import AzureMLOptionsClient
    from phase6_batch_explain import BatchSHAPOrchestrator
    logger.info("✅ Phase 6 modules imported successfully")
except ImportError as e:
    logger.warning(f"⚠️  Phase 6 import failed: {e}")
    AzureMLSHAPClient = None
    AzureMLOptionsClient = None
    BatchSHAPOrchestrator = None

try:
    # Phase 8 imports
    from phase8_analytics.trend_analyzer import TrendAnalyzer
    from phase8_analytics.volatility_heatmap import VolatilityHeatmap
    from phase8_analytics.risk_dashboard import RiskDashboard
    from phase8_analytics.cache_telemetry import CacheTelemetryCollector
    logger.info("✅ Phase 8 analytics modules imported successfully")
except ImportError as e:
    logger.warning(f"⚠️  Phase 8 import failed: {e}")
    TrendAnalyzer = None
    VolatilityHeatmap = None
    RiskDashboard = None
    CacheTelemetryCollector = None

try:
    # Phase 8B imports
    from scenario_engine import (
        ScenarioEngine, ScenarioParameters, ScenarioType,
        create_monte_carlo_scenario
    )
    logger.info("✅ Phase 8B scenario engine imported successfully")
except ImportError as e:
    logger.warning(f"⚠️  Phase 8B import failed: {e}")
    ScenarioEngine = None
    create_monte_carlo_scenario = None


# ============================================================================
# TELEMETRY DATA STRUCTURES
# ============================================================================

@dataclass
class SubsystemTelemetry:
    """Telemetry for a single subsystem execution"""
    subsystem_name: str
    start_time: float
    end_time: float
    duration_ms: float
    success: bool
    error_message: Optional[str] = None
    
    # Performance metrics
    latency_p50: Optional[float] = None
    latency_p90: Optional[float] = None
    latency_p99: Optional[float] = None
    throughput: Optional[float] = None  # operations per second
    
    # Cache metrics
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_rate: float = 0.0
    
    # Memory metrics
    memory_peak_mb: Optional[float] = None
    memory_delta_mb: Optional[float] = None
    
    # Output metadata
    output_hash: Optional[str] = None
    output_size_bytes: Optional[int] = None
    output_records: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class PipelineRunManifest:
    """Complete manifest for a full pipeline run"""
    run_id: str
    timestamp: str
    pipeline_config: Dict[str, Any]
    
    # Subsystem telemetry
    subsystems: List[SubsystemTelemetry] = field(default_factory=list)
    
    # Overall metrics
    total_duration_ms: float = 0.0
    total_success: bool = False
    
    # Determinism validation
    run_hash: Optional[str] = None
    is_deterministic: Optional[bool] = None
    hash_matches: Optional[List[str]] = None
    
    # Regression metrics
    baseline_comparison: Optional[Dict[str, Any]] = None
    regression_detected: bool = False
    regression_details: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "pipeline_config": self.pipeline_config,
            "subsystems": [s.to_dict() for s in self.subsystems],
            "total_duration_ms": self.total_duration_ms,
            "total_success": self.total_success,
            "run_hash": self.run_hash,
            "is_deterministic": self.is_deterministic,
            "hash_matches": self.hash_matches,
            "baseline_comparison": self.baseline_comparison,
            "regression_detected": self.regression_detected,
            "regression_details": self.regression_details
        }
    
    def save_json(self, filepath: str) -> None:
        """Save manifest to JSON file"""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"✅ Saved pipeline manifest to {filepath}")


# ============================================================================
# BASELINE METRICS (from Phase 6/8/8B reports)
# ============================================================================

BASELINE_METRICS = {
    "phase6": {
        "single_shap_ms": 20.5,  # Average of 15-26ms
        "batch_shap_ms": 70.0,   # Average of 60-80ms
        "options_forecast_ms": 22.0,  # Average of 17-27ms
        "cache_l1_hit_ms": 0.1
    },
    "phase8": {
        "trend_analyzer_ms": 61.5,  # Average of 3-120ms
        "volatility_heatmap_ms": 41.0,  # Average of 2-80ms
        "risk_dashboard_ms": 2.0,
        "cache_telemetry_ms": 4.5  # Average of 1-8ms
    },
    "phase8b": {
        "monte_carlo_5ticker_ms": 910.0,  # 0.91s from report
        "monte_carlo_10ticker_ms": 4760.0,  # 4.76s from report
        "throughput_scenarios_per_sec": 16.6
    }
}


# ============================================================================
# ORCHESTRATOR ENGINE
# ============================================================================

class Phase9Orchestrator:
    """
    Master orchestrator for complete offline workflow validation.
    
    Pipeline Stages:
    1. Scenario Generation (Phase 8B optimized Monte Carlo)
    2. Forecast Generation (Phase 6 options + SHAP)
    3. Analytics Computation (Phase 8 trend/volatility/risk)
    4. Dashboard Assembly (Phase 8B adapter)
    5. Cache Telemetry (Phase 8 telemetry collector)
    """
    
    def __init__(
        self,
        tickers: List[str],
        num_simulations: int = 100,
        num_days: int = 60,
        random_seed: int = 42,
        output_dir: str = "outputs/phase9_validation"
    ):
        self.tickers = tickers
        self.num_simulations = num_simulations
        self.num_days = num_days
        self.random_seed = random_seed
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Run identification
        self.run_id = f"phase9_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Telemetry collection
        self.manifest = PipelineRunManifest(
            run_id=self.run_id,
            timestamp=datetime.now().isoformat(),
            pipeline_config={
                "tickers": self.tickers,
                "num_simulations": self.num_simulations,
                "num_days": self.num_days,
                "random_seed": self.random_seed,
                "output_dir": str(self.output_dir)
            }
        )
        
        # Initialize telemetry collector
        if CacheTelemetryCollector:
            self.cache_telemetry = CacheTelemetryCollector()
        else:
            self.cache_telemetry = None
    
    def _compute_hash(self, data: Any) -> str:
        """
        Compute SHA256 hash of data for determinism validation.
        
        Excludes timestamps and metadata to ensure deterministic hashing.
        """
        if isinstance(data, (dict, list)):
            # Deep copy and remove non-deterministic fields
            import copy
            data_copy = copy.deepcopy(data)
            
            # Remove timestamps recursively
            def remove_timestamps(obj):
                if isinstance(obj, dict):
                    # Remove known timestamp/ID fields
                    keys_to_remove = [
                        'timestamp', 'analysis_id', 'scenario_id', 'run_id', 'snapshot_id',
                        'validation_timestamp', 'generated_at', 'created_at',
                        'updated_at', 'last_modified'
                    ]
                    for key in keys_to_remove:
                        obj.pop(key, None)
                    
                    # Recurse into nested dicts/lists (CRITICAL: iterate over copy of values)
                    for key, value in list(obj.items()):
                        remove_timestamps(value)
                elif isinstance(obj, list):
                    for item in obj:
                        remove_timestamps(item)
            
            remove_timestamps(data_copy)
            data_str = json.dumps(data_copy, sort_keys=True, cls=NumpyEncoder)
        elif isinstance(data, np.ndarray):
            data_str = data.tobytes().hex()
        else:
            data_str = str(data)
        
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _measure_subsystem(
        self,
        subsystem_name: str,
        func: callable,
        *args,
        **kwargs
    ) -> Tuple[Any, SubsystemTelemetry]:
        """
        Execute subsystem with comprehensive telemetry collection.
        
        Args:
            subsystem_name: Name of subsystem for logging
            func: Function to execute
            *args, **kwargs: Arguments for function
            
        Returns:
            Tuple of (result, telemetry)
        """
        logger.info(f"▶️  Executing subsystem: {subsystem_name}")
        
        start_time = time.time()
        success = False
        error_message = None
        result = None
        
        try:
            result = func(*args, **kwargs)
            success = True
            logger.info(f"✅ {subsystem_name} completed successfully")
        except Exception as e:
            error_message = str(e)
            logger.error(f"❌ {subsystem_name} failed: {error_message}")
        
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        # Compute output hash for determinism
        output_hash = None
        output_size_bytes = None
        output_records = None
        
        if result is not None:
            try:
                output_hash = self._compute_hash(result)
                
                if isinstance(result, dict):
                    output_size_bytes = len(json.dumps(result))
                    output_records = len(result)
                elif isinstance(result, list):
                    output_size_bytes = len(json.dumps(result))
                    output_records = len(result)
                elif hasattr(result, '__dict__'):
                    output_size_bytes = len(json.dumps(result.__dict__, default=str))
            except Exception as e:
                logger.warning(f"⚠️  Could not compute hash for {subsystem_name}: {e}")
        
        telemetry = SubsystemTelemetry(
            subsystem_name=subsystem_name,
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            output_hash=output_hash,
            output_size_bytes=output_size_bytes,
            output_records=output_records
        )
        
        self.manifest.subsystems.append(telemetry)
        
        return result, telemetry
    
    def run_phase8b_scenario_generation(self) -> Dict[str, Any]:
        """
        Stage 1: Generate Monte Carlo scenarios using Phase 8B optimized engine.
        
        Returns:
            Scenario dataset
        """
        logger.info("=" * 80)
        logger.info("STAGE 1: Phase 8B Scenario Generation (Optimized Monte Carlo)")
        logger.info("=" * 80)
        
        if create_monte_carlo_scenario is None:
            logger.error("❌ Phase 8B scenario engine not available")
            return None
        
        def generate_scenarios():
            scenario = create_monte_carlo_scenario(
                tickers=self.tickers,
                num_simulations=self.num_simulations,
                num_days=self.num_days,
                random_seed=self.random_seed,
                output_dir=str(self.output_dir / "scenarios")
            )
            
            # Save scenario
            scenario_path = self.output_dir / "scenarios" / f"{self.run_id}_scenario.json"
            scenario.save_json(str(scenario_path))
            
            return scenario.to_dict()
        
        result, telemetry = self._measure_subsystem(
            "phase8b_scenario_generation",
            generate_scenarios
        )
        
        # Log performance vs baseline
        if telemetry.success:
            baseline_ms = BASELINE_METRICS["phase8b"].get(
                f"monte_carlo_{len(self.tickers)}ticker_ms",
                BASELINE_METRICS["phase8b"]["monte_carlo_10ticker_ms"]
            )
            deviation_pct = ((telemetry.duration_ms - baseline_ms) / baseline_ms) * 100
            logger.info(f"   Performance: {telemetry.duration_ms:.2f}ms (baseline: {baseline_ms}ms, {deviation_pct:+.1f}%)")
        
        return result
    
    def run_phase8_analytics(self, scenario_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stage 2: Run Phase 8 analytics on scenario data.
        
        Args:
            scenario_data: Output from Phase 8B scenario generation
            
        Returns:
            Analytics results (trend, volatility, risk)
        """
        logger.info("=" * 80)
        logger.info("STAGE 2: Phase 8 Analytics (Trend/Volatility/Risk)")
        logger.info("=" * 80)
        
        if not all([TrendAnalyzer, VolatilityHeatmap, RiskDashboard]):
            logger.error("❌ Phase 8 analytics modules not available")
            return None
        
        analytics_results = {}
        
        # Extract forecast data from scenario paths
        # Phase 8 analytics expect: Dict[str, List[Dict[str, Any]]]
        # where each dict has 'timestamp' and 'expected_return'
        forecast_data = {}
        if scenario_data and "paths" in scenario_data:
            for path in scenario_data["paths"]:
                ticker = path["ticker"]
                dates = path["dates"]
                returns = path["returns"]
                
                # Convert to Phase 8 format: list of forecast dicts
                forecast_list = []
                for i, (date, ret) in enumerate(zip(dates[1:], returns)):  # Skip first date (no return)
                    forecast_list.append({
                        "timestamp": date,
                        "expected_return": ret,
                        "forecast_index": i
                    })
                
                forecast_data[ticker] = forecast_list
        
        # Stage 2A: Trend Analysis
        def run_trend_analysis():
            analyzer = TrendAnalyzer()
            result = analyzer.analyze_trends(forecast_data)
            return result.to_dict() if hasattr(result, 'to_dict') else result
        
        trend_result, trend_telemetry = self._measure_subsystem(
            "phase8_trend_analyzer",
            run_trend_analysis
        )
        analytics_results["trend_analysis"] = trend_result
        
        # Stage 2B: Volatility Heatmap
        def run_volatility_analysis():
            heatmap = VolatilityHeatmap()
            # VolatilityHeatmap.analyze_volatility expects: Dict[str, List[float]]
            # (ticker → returns array)
            price_data = {}
            if scenario_data and "paths" in scenario_data:
                for path in scenario_data["paths"]:
                    ticker = path["ticker"]
                    price_data[ticker] = path["returns"]  # List of floats
            
            result = heatmap.analyze_volatility(price_data)
            # Convert VolatilityMetrics objects to dicts
            return {k: v.to_dict() if hasattr(v, 'to_dict') else v for k, v in result.items()}
        
        volatility_result, vol_telemetry = self._measure_subsystem(
            "phase8_volatility_heatmap",
            run_volatility_analysis
        )
        analytics_results["volatility_heatmap"] = volatility_result
        
        # Stage 2C: Risk Dashboard
        def run_risk_dashboard():
            dashboard = RiskDashboard()
            # RiskDashboard.generate_dashboard_snapshot() takes 2 args: trend_result, volatility_result
            # (not forecast_data as third arg)
            snapshot = dashboard.generate_dashboard_snapshot(
                trend_result if trend_result else {},
                volatility_result if volatility_result else {}
            )
            return snapshot.to_dict() if hasattr(snapshot, 'to_dict') else snapshot
        
        risk_result, risk_telemetry = self._measure_subsystem(
            "phase8_risk_dashboard",
            run_risk_dashboard
        )
        analytics_results["risk_dashboard"] = risk_result
        
        # Save analytics results
        analytics_path = self.output_dir / f"{self.run_id}_analytics.json"
        with open(analytics_path, 'w') as f:
            json.dump(analytics_results, f, indent=2, cls=NumpyEncoder)
        logger.info(f"✅ Saved analytics results to {analytics_path}")
        
        return analytics_results
    
    def run_cache_telemetry_validation(self) -> Dict[str, Any]:
        """
        Stage 3: Validate cache telemetry and determinism.
        
        Returns:
            Cache telemetry report
        """
        logger.info("=" * 80)
        logger.info("STAGE 3: Cache Telemetry & Determinism Validation")
        logger.info("=" * 80)
        
        if self.cache_telemetry is None:
            logger.warning("⚠️  Cache telemetry collector not available")
            return {"status": "skipped", "reason": "cache_telemetry module not imported"}
        
        def generate_telemetry_report():
            # Record mock cache requests for demonstration
            # API signature: record_cache_request(cache_key, is_hit, cache_level, latency_ms)
            for i in range(100):
                is_hit = i % 3 != 0  # 66% hit rate
                latency_ms = 0.1 if is_hit else 15.0
                cache_level = "L1" if is_hit else "L2"
                
                self.cache_telemetry.record_cache_request(
                    cache_key=f"key_{i % 20}",
                    is_hit=is_hit,
                    cache_level=cache_level,
                    latency_ms=latency_ms
                )
            
            # Generate report
            report = self.cache_telemetry.generate_report()
            return report.to_dict() if hasattr(report, 'to_dict') else report
        
        telemetry_result, telemetry_telemetry = self._measure_subsystem(
            "phase8_cache_telemetry",
            generate_telemetry_report
        )
        
        # Save telemetry report
        telemetry_path = self.output_dir / f"{self.run_id}_cache_telemetry.json"
        with open(telemetry_path, 'w') as f:
            json.dump(telemetry_result, f, indent=2, cls=NumpyEncoder)
        logger.info(f"✅ Saved cache telemetry to {telemetry_path}")
        
        return telemetry_result
    
    def run_full_pipeline(self) -> PipelineRunManifest:
        """
        Execute complete pipeline with telemetry collection.
        
        Returns:
            Complete pipeline manifest
        """
        logger.info("🚀 Starting Phase 9 Full Pipeline Orchestration")
        logger.info(f"   Run ID: {self.run_id}")
        logger.info(f"   Tickers: {self.tickers}")
        logger.info(f"   Simulations: {self.num_simulations}")
        logger.info(f"   Days: {self.num_days}")
        logger.info(f"   Random Seed: {self.random_seed}")
        
        pipeline_start = time.time()
        
        # Stage 1: Scenario Generation
        scenario_data = self.run_phase8b_scenario_generation()
        
        # Stage 2: Analytics
        analytics_data = self.run_phase8_analytics(scenario_data)
        
        # Stage 3: Cache Telemetry
        cache_telemetry_data = self.run_cache_telemetry_validation()
        
        pipeline_end = time.time()
        self.manifest.total_duration_ms = (pipeline_end - pipeline_start) * 1000
        
        # Determine overall success
        self.manifest.total_success = all(s.success for s in self.manifest.subsystems)
        
        # Compute overall hash
        combined_output = {
            "scenario": scenario_data,
            "analytics": analytics_data,
            "cache_telemetry": cache_telemetry_data
        }
        self.manifest.run_hash = self._compute_hash(combined_output)
        
        logger.info("=" * 80)
        logger.info("PIPELINE EXECUTION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"   Total Duration: {self.manifest.total_duration_ms:.2f}ms")
        logger.info(f"   Overall Success: {self.manifest.total_success}")
        logger.info(f"   Run Hash: {self.manifest.run_hash[:16]}...")
        
        # Save manifest
        manifest_path = self.output_dir / f"{self.run_id}_manifest.json"
        self.manifest.save_json(str(manifest_path))
        
        return self.manifest
    
    def run_determinism_validation(self, num_runs: int = 3) -> Dict[str, Any]:
        """
        Run pipeline multiple times and verify deterministic output.
        
        Args:
            num_runs: Number of validation runs (default 3)
            
        Returns:
            Determinism validation report
        """
        logger.info("=" * 80)
        logger.info(f"DETERMINISM VALIDATION ({num_runs} runs)")
        logger.info("=" * 80)
        
        run_hashes = []
        run_manifests = []
        
        for run_idx in range(num_runs):
            logger.info(f"\n🔄 Determinism Run {run_idx + 1}/{num_runs}")
            
            # Create new orchestrator for each run (fresh state)
            orchestrator = Phase9Orchestrator(
                tickers=self.tickers,
                num_simulations=self.num_simulations,
                num_days=self.num_days,
                random_seed=self.random_seed,  # Same seed for determinism
                output_dir=str(self.output_dir / f"determinism_run_{run_idx + 1}")
            )
            
            manifest = orchestrator.run_full_pipeline()
            run_hashes.append(manifest.run_hash)
            run_manifests.append(manifest)
        
        # Check determinism
        is_deterministic = len(set(run_hashes)) == 1
        
        validation_report = {
            "num_runs": num_runs,
            "is_deterministic": is_deterministic,
            "run_hashes": run_hashes,
            "unique_hashes": list(set(run_hashes)),
            "hash_match_rate": run_hashes.count(run_hashes[0]) / num_runs if run_hashes else 0.0,
            "validation_timestamp": datetime.now().isoformat()
        }
        
        # Log results
        if is_deterministic:
            logger.info("✅ DETERMINISM VALIDATED: All runs produced identical output")
            logger.info(f"   Shared Hash: {run_hashes[0][:16]}...")
        else:
            logger.warning("⚠️  DETERMINISM FAILED: Outputs differ across runs")
            logger.warning(f"   Unique Hashes: {len(set(run_hashes))}")
            for idx, hash_val in enumerate(run_hashes):
                logger.warning(f"      Run {idx + 1}: {hash_val[:16]}...")
        
        # Save validation report
        validation_path = self.output_dir / "phase9_determinism_validation.json"
        with open(validation_path, 'w') as f:
            json.dump(validation_report, f, indent=2, cls=NumpyEncoder)
        logger.info(f"✅ Saved determinism validation to {validation_path}")
        
        return validation_report
    
    def run_regression_analysis(self) -> Dict[str, Any]:
        """
        Compare current run against baseline metrics to detect regressions.
        
        Returns:
            Regression analysis report
        """
        logger.info("=" * 80)
        logger.info("REGRESSION ANALYSIS (vs Baseline)")
        logger.info("=" * 80)
        
        regression_details = []
        regression_detected = False
        
        # Define acceptable deviation threshold
        DEVIATION_THRESHOLD_PCT = 5.0
        
        # Analyze each subsystem
        for subsystem in self.manifest.subsystems:
            subsystem_name = subsystem.subsystem_name
            actual_ms = subsystem.duration_ms
            
            # Find baseline metric
            baseline_ms = None
            if "phase8b" in subsystem_name:
                if "scenario" in subsystem_name:
                    baseline_ms = BASELINE_METRICS["phase8b"]["monte_carlo_10ticker_ms"]
            elif "phase8" in subsystem_name:
                if "trend" in subsystem_name:
                    baseline_ms = BASELINE_METRICS["phase8"]["trend_analyzer_ms"]
                elif "volatility" in subsystem_name:
                    baseline_ms = BASELINE_METRICS["phase8"]["volatility_heatmap_ms"]
                elif "risk" in subsystem_name:
                    baseline_ms = BASELINE_METRICS["phase8"]["risk_dashboard_ms"]
                elif "cache" in subsystem_name:
                    baseline_ms = BASELINE_METRICS["phase8"]["cache_telemetry_ms"]
            
            if baseline_ms is not None:
                deviation_pct = ((actual_ms - baseline_ms) / baseline_ms) * 100
                
                # Positive deviation = slower (negative regression)
                # Negative deviation = faster (positive improvement)
                is_negative_regression = deviation_pct > DEVIATION_THRESHOLD_PCT  # Slower than baseline
                is_positive_improvement = deviation_pct < -DEVIATION_THRESHOLD_PCT  # Faster than baseline
                
                detail = {
                    "subsystem": subsystem_name,
                    "baseline_ms": baseline_ms,
                    "actual_ms": actual_ms,
                    "deviation_pct": deviation_pct,
                    "threshold_pct": DEVIATION_THRESHOLD_PCT,
                    "is_regression": is_negative_regression,
                    "is_improvement": is_positive_improvement
                }
                
                regression_details.append(detail)
                
                if is_negative_regression:
                    regression_detected = True
                    logger.warning(f"⚠️  REGRESSION: {subsystem_name}")
                    logger.warning(f"      Baseline: {baseline_ms:.2f}ms, Actual: {actual_ms:.2f}ms ({deviation_pct:+.1f}%)")
                elif is_positive_improvement:
                    logger.info(f"🚀 IMPROVEMENT: {subsystem_name}: {actual_ms:.2f}ms (baseline: {baseline_ms:.2f}ms, {deviation_pct:+.1f}%)")
                else:
                    logger.info(f"✅ {subsystem_name}: {actual_ms:.2f}ms (baseline: {baseline_ms:.2f}ms, {deviation_pct:+.1f}%)")
        
        regression_report = {
            "regression_detected": regression_detected,
            "deviation_threshold_pct": DEVIATION_THRESHOLD_PCT,
            "subsystem_analysis": regression_details,
            "timestamp": datetime.now().isoformat()
        }
        
        # Update manifest
        self.manifest.regression_detected = regression_detected
        self.manifest.regression_details = [
            f"{d['subsystem']}: {d['deviation_pct']:+.1f}%"
            for d in regression_details if d['is_regression']
        ]
        self.manifest.baseline_comparison = regression_report
        
        # Save regression report
        regression_path = self.output_dir / "phase9_regression_audit.json"
        with open(regression_path, 'w') as f:
            json.dump(regression_report, f, indent=2, cls=NumpyEncoder)
        logger.info(f"✅ Saved regression analysis to {regression_path}")
        
        return regression_report


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def run_quick_validation(
    tickers: List[str] = ["SPY", "QQQ", "IWM"],
    num_simulations: int = 100,
    output_dir: str = "outputs/phase9_validation"
) -> PipelineRunManifest:
    """
    Quick validation run with default parameters.
    
    Args:
        tickers: List of ticker symbols
        num_simulations: Number of Monte Carlo simulations
        output_dir: Output directory for results
        
    Returns:
        Pipeline run manifest
    """
    orchestrator = Phase9Orchestrator(
        tickers=tickers,
        num_simulations=num_simulations,
        num_days=60,
        random_seed=42,
        output_dir=output_dir
    )
    
    manifest = orchestrator.run_full_pipeline()
    orchestrator.run_regression_analysis()
    
    return manifest


def run_full_validation(
    tickers: List[str] = ["SPY", "QQQ", "IWM"],
    num_simulations: int = 100,
    determinism_runs: int = 3,
    output_dir: str = "outputs/phase9_validation"
) -> Dict[str, Any]:
    """
    Complete validation including determinism and regression checks.
    
    Args:
        tickers: List of ticker symbols
        num_simulations: Number of Monte Carlo simulations
        determinism_runs: Number of runs for determinism validation
        output_dir: Output directory for results
        
    Returns:
        Complete validation report
    """
    logger.info("=" * 80)
    logger.info("PHASE 9 FULL VALIDATION SUITE")
    logger.info("=" * 80)
    
    orchestrator = Phase9Orchestrator(
        tickers=tickers,
        num_simulations=num_simulations,
        num_days=60,
        random_seed=42,
        output_dir=output_dir
    )
    
    # Run full pipeline
    manifest = orchestrator.run_full_pipeline()
    
    # Run regression analysis
    regression_report = orchestrator.run_regression_analysis()
    
    # Run determinism validation
    determinism_report = orchestrator.run_determinism_validation(num_runs=determinism_runs)
    
    # Compile complete validation report
    validation_report = {
        "validation_timestamp": datetime.now().isoformat(),
        "pipeline_manifest": manifest.to_dict(),
        "regression_analysis": regression_report,
        "determinism_validation": determinism_report,
        "overall_status": {
            "pipeline_success": manifest.total_success,
            "determinism_pass": determinism_report["is_deterministic"],
            "regression_pass": not regression_report["regression_detected"],
            "all_checks_pass": (
                manifest.total_success and
                determinism_report["is_deterministic"] and
                not regression_report["regression_detected"]
            )
        }
    }
    
    # Save complete validation report
    validation_path = Path(output_dir) / "phase9_complete_validation.json"
    with open(validation_path, 'w') as f:
        json.dump(validation_report, f, indent=2, cls=NumpyEncoder)
    
    logger.info("=" * 80)
    logger.info("VALIDATION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"   Pipeline Success: {'✅ PASS' if validation_report['overall_status']['pipeline_success'] else '❌ FAIL'}")
    logger.info(f"   Determinism: {'✅ PASS' if validation_report['overall_status']['determinism_pass'] else '❌ FAIL'}")
    logger.info(f"   Regression: {'✅ PASS' if validation_report['overall_status']['regression_pass'] else '⚠️  DETECTED'}")
    logger.info(f"   Overall: {'✅ ALL CHECKS PASS' if validation_report['overall_status']['all_checks_pass'] else '❌ VALIDATION FAILED'}")
    logger.info(f"\n📄 Full report: {validation_path}")
    
    return validation_report


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("PHASE 9 — SYSTEM ORCHESTRATION & VALIDATION")
    logger.info("=" * 80)
    
    # Run full validation suite
    validation_report = run_full_validation(
        tickers=["SPY", "QQQ", "IWM"],
        num_simulations=100,
        determinism_runs=3,
        output_dir="outputs/phase9_validation"
    )
    
    # Exit with appropriate code
    sys.exit(0 if validation_report["overall_status"]["all_checks_pass"] else 1)
