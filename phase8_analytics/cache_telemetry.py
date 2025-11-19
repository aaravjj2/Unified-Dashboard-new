"""
Phase 8 — Cache Telemetry Module
=================================

Collect and analyze cache performance telemetry.

Key Features:
- Hit/miss ratio tracking
- Latency percentile analysis (p50, p90, p99)
- Determinism variance validation (≤1e-6 threshold)
- L1/L2/L3 cache breakdown
- JSON + CSV exports for analysis

Author: Agent 1B — Unified Financial Dashboard Team
Version: 1.0 (Phase 8)
"""

import json
import csv
import hashlib
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class CacheHitMetrics:
    """
    Cache hit/miss metrics.
    
    Attributes:
        total_requests: Total cache requests
        hits: Number of cache hits
        misses: Number of cache misses
        hit_rate: Hit rate (0-1)
        l1_hits: L1 cache hits
        l2_hits: L2 cache hits
        l3_hits: L3 cache hits
    """
    total_requests: int
    hits: int
    misses: int
    hit_rate: float
    l1_hits: int
    l2_hits: int
    l3_hits: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), separators=(',', ':'))


@dataclass
class LatencyMetrics:
    """
    Cache latency metrics.
    
    Attributes:
        p50: 50th percentile latency (ms)
        p90: 90th percentile latency (ms)
        p99: 99th percentile latency (ms)
        mean: Mean latency (ms)
        max: Maximum latency (ms)
        min: Minimum latency (ms)
    """
    p50: float
    p90: float
    p99: float
    mean: float
    max: float
    min: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), separators=(',', ':'))


@dataclass
class DeterminismRecord:
    """
    Determinism variance record for a single cache key.
    
    Attributes:
        cache_key: Cache key
        run1_hash: SHA256 hash of run 1 result
        run2_hash: SHA256 hash of run 2 result
        run3_hash: SHA256 hash of run 3 result
        variance: Maximum variance across runs
        is_deterministic: Whether variance ≤ 1e-6
    """
    cache_key: str
    run1_hash: str
    run2_hash: str
    run3_hash: str
    variance: float
    is_deterministic: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return asdict(self)


@dataclass
class CacheTelemetryReport:
    """
    Complete cache telemetry report.
    
    Attributes:
        report_id: Unique report identifier
        timestamp: Report timestamp
        hit_metrics: Cache hit/miss metrics
        latency_metrics: Latency percentile metrics
        determinism_records: List of determinism records
        metadata: Additional metadata
    """
    report_id: str
    timestamp: str
    hit_metrics: CacheHitMetrics
    latency_metrics: LatencyMetrics
    determinism_records: List[DeterminismRecord]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            'report_id': self.report_id,
            'timestamp': self.timestamp,
            'hit_metrics': self.hit_metrics.to_dict(),
            'latency_metrics': self.latency_metrics.to_dict(),
            'determinism_records': [r.to_dict() for r in self.determinism_records],
            'metadata': self.metadata
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


# =============================================================================
# CACHE TELEMETRY COLLECTOR
# =============================================================================

class CacheTelemetryCollector:
    """
    Collect and analyze cache performance telemetry.
    
    Workflow:
    1. Track cache hits/misses (L1/L2/L3 breakdown)
    2. Record latency for each request
    3. Validate determinism across multiple runs
    4. Generate telemetry report (JSON + CSV)
    """
    
    def __init__(self,
                 determinism_threshold: float = 1e-6):
        """
        Initialize cache telemetry collector.
        
        Args:
            determinism_threshold: Maximum allowed variance for determinism validation
        """
        self.determinism_threshold = determinism_threshold
        
        # Internal tracking
        self.total_requests = 0
        self.hits = 0
        self.misses = 0
        self.l1_hits = 0
        self.l2_hits = 0
        self.l3_hits = 0
        self.latencies: List[float] = []
        self.determinism_data: Dict[str, List[str]] = defaultdict(list)  # cache_key → [hash1, hash2, hash3]
        
        logger.info(
            f"🔧 CacheTelemetryCollector initialized "
            f"(determinism_threshold={determinism_threshold})"
        )
    
    def record_cache_request(self,
                             cache_key: str,
                             is_hit: bool,
                             cache_level: str,
                             latency_ms: float):
        """
        Record a cache request.
        
        Args:
            cache_key: Cache key
            is_hit: Whether it was a cache hit
            cache_level: Cache level (L1|L2|L3)
            latency_ms: Latency in milliseconds
        """
        self.total_requests += 1
        
        if is_hit:
            self.hits += 1
            
            if cache_level == "L1":
                self.l1_hits += 1
            elif cache_level == "L2":
                self.l2_hits += 1
            elif cache_level == "L3":
                self.l3_hits += 1
        else:
            self.misses += 1
        
        self.latencies.append(latency_ms)
    
    def record_determinism_run(self,
                               cache_key: str,
                               result_data: Any):
        """
        Record a determinism validation run.
        
        Args:
            cache_key: Cache key
            result_data: Result data (will be hashed)
        """
        # Compute hash of result
        if isinstance(result_data, dict):
            result_str = json.dumps(result_data, sort_keys=True, separators=(',', ':'))
        else:
            result_str = str(result_data)
        
        result_hash = hashlib.sha256(result_str.encode()).hexdigest()[:16]
        
        self.determinism_data[cache_key].append(result_hash)
    
    def generate_report(self) -> CacheTelemetryReport:
        """
        Generate cache telemetry report.
        
        Returns:
            CacheTelemetryReport with hit/miss metrics, latency, and determinism validation
        """
        logger.info("📊 Generating cache telemetry report...")
        
        # Compute hit/miss metrics
        hit_rate = self.hits / self.total_requests if self.total_requests > 0 else 0.0
        
        hit_metrics = CacheHitMetrics(
            total_requests=self.total_requests,
            hits=self.hits,
            misses=self.misses,
            hit_rate=hit_rate,
            l1_hits=self.l1_hits,
            l2_hits=self.l2_hits,
            l3_hits=self.l3_hits
        )
        
        # Compute latency metrics
        if self.latencies:
            latency_metrics = LatencyMetrics(
                p50=float(np.percentile(self.latencies, 50)),
                p90=float(np.percentile(self.latencies, 90)),
                p99=float(np.percentile(self.latencies, 99)),
                mean=float(np.mean(self.latencies)),
                max=float(np.max(self.latencies)),
                min=float(np.min(self.latencies))
            )
        else:
            latency_metrics = LatencyMetrics(
                p50=0.0, p90=0.0, p99=0.0, mean=0.0, max=0.0, min=0.0
            )
        
        # Compute determinism records
        determinism_records = []
        
        for cache_key, hashes in self.determinism_data.items():
            if len(hashes) >= 3:
                # Take first 3 runs
                run1_hash = hashes[0]
                run2_hash = hashes[1]
                run3_hash = hashes[2]
                
                # Check if all hashes match (perfect determinism)
                if run1_hash == run2_hash == run3_hash:
                    variance = 0.0
                    is_deterministic = True
                else:
                    # Hashes differ — not deterministic
                    variance = 1.0  # Categorical variance
                    is_deterministic = False
                
                determinism_records.append(DeterminismRecord(
                    cache_key=cache_key,
                    run1_hash=run1_hash,
                    run2_hash=run2_hash,
                    run3_hash=run3_hash,
                    variance=variance,
                    is_deterministic=is_deterministic
                ))
        
        # Create report
        report_id = hashlib.sha256(
            f"{datetime.now(timezone.utc).isoformat()}:{hit_rate}".encode()
        ).hexdigest()[:16]
        
        report = CacheTelemetryReport(
            report_id=report_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            hit_metrics=hit_metrics,
            latency_metrics=latency_metrics,
            determinism_records=determinism_records,
            metadata={
                'total_cache_keys': len(self.determinism_data),
                'deterministic_count': sum(1 for r in determinism_records if r.is_deterministic),
                'non_deterministic_count': sum(1 for r in determinism_records if not r.is_deterministic),
                'determinism_threshold': self.determinism_threshold
            }
        )
        
        logger.info(
            f"✅ Telemetry report generated: "
            f"Hit rate = {hit_rate:.1%}, "
            f"Latency p50 = {latency_metrics.p50:.2f}ms, "
            f"Deterministic = {report.metadata['deterministic_count']}/{report.metadata['total_cache_keys']}"
        )
        
        return report
    
    def reset(self):
        """Reset all telemetry data."""
        self.total_requests = 0
        self.hits = 0
        self.misses = 0
        self.l1_hits = 0
        self.l2_hits = 0
        self.l3_hits = 0
        self.latencies.clear()
        self.determinism_data.clear()
        
        logger.info("🔄 Telemetry collector reset")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def save_telemetry_report(report: CacheTelemetryReport, output_path: str):
    """
    Save telemetry report to JSON file.
    
    Args:
        report: CacheTelemetryReport to save
        output_path: Output file path
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write(report.to_json())
    
    logger.info(f"💾 Telemetry report saved to {output_path}")


def save_determinism_log_csv(determinism_records: List[DeterminismRecord], output_path: str):
    """
    Save determinism records to CSV file.
    
    Args:
        determinism_records: List of DeterminismRecord
        output_path: Output CSV file path
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', newline='') as csvfile:
        fieldnames = ['cache_key', 'run1_hash', 'run2_hash', 'run3_hash', 'variance', 'is_deterministic']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for record in determinism_records:
            writer.writerow(record.to_dict())
    
    logger.info(f"💾 Determinism log saved to {output_path} ({len(determinism_records)} records)")


# =============================================================================
# MAIN EXECUTION (FOR TESTING)
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
    
    print("=" * 80)
    print("Phase 8 — Cache Telemetry — Standalone Test")
    print("=" * 80)
    
    # Simulate cache requests
    collector = CacheTelemetryCollector(determinism_threshold=1e-6)
    
    # Simulate 100 cache requests
    np.random.seed(42)
    
    for i in range(100):
        cache_key = f"key_{i % 10}"
        is_hit = np.random.rand() > 0.2  # 80% hit rate
        
        if is_hit:
            cache_level = np.random.choice(["L1", "L2", "L3"], p=[0.7, 0.25, 0.05])
            
            if cache_level == "L1":
                latency = np.random.uniform(0.05, 0.15)
            elif cache_level == "L2":
                latency = np.random.uniform(10, 30)
            else:
                latency = np.random.uniform(50, 100)
        else:
            cache_level = None
            latency = np.random.uniform(100, 300)
        
        collector.record_cache_request(cache_key, is_hit, cache_level or "MISS", latency)
    
    # Simulate determinism validation (3 runs for 10 keys)
    for run in range(3):
        for i in range(10):
            cache_key = f"key_{i}"
            
            # Simulate deterministic results for first 8 keys, non-deterministic for last 2
            if i < 8:
                result_data = {'value': i * 100, 'timestamp': '2025-01-01T00:00:00Z'}
            else:
                result_data = {'value': i * 100 + np.random.randint(0, 10), 'timestamp': datetime.now(timezone.utc).isoformat()}
            
            collector.record_determinism_run(cache_key, result_data)
    
    # Generate report
    report = collector.generate_report()
    
    # Print results
    print(f"\n📊 Telemetry Report:")
    print(f"   ID: {report.report_id}")
    print(f"   Timestamp: {report.timestamp}")
    
    print(f"\n📈 Hit/Miss Metrics:")
    print(f"   Total Requests: {report.hit_metrics.total_requests}")
    print(f"   Hits: {report.hit_metrics.hits} ({report.hit_metrics.hit_rate:.1%})")
    print(f"   Misses: {report.hit_metrics.misses}")
    print(f"   L1 Hits: {report.hit_metrics.l1_hits}")
    print(f"   L2 Hits: {report.hit_metrics.l2_hits}")
    print(f"   L3 Hits: {report.hit_metrics.l3_hits}")
    
    print(f"\n⏱️  Latency Metrics:")
    print(f"   p50: {report.latency_metrics.p50:.2f}ms")
    print(f"   p90: {report.latency_metrics.p90:.2f}ms")
    print(f"   p99: {report.latency_metrics.p99:.2f}ms")
    print(f"   Mean: {report.latency_metrics.mean:.2f}ms")
    print(f"   Max: {report.latency_metrics.max:.2f}ms")
    
    print(f"\n🔒 Determinism Validation:")
    print(f"   Total Keys: {report.metadata['total_cache_keys']}")
    print(f"   Deterministic: {report.metadata['deterministic_count']} ({report.metadata['deterministic_count']/report.metadata['total_cache_keys']*100:.1f}%)")
    print(f"   Non-Deterministic: {report.metadata['non_deterministic_count']}")
    
    # Save outputs
    save_telemetry_report(report, "test_artifacts/cache_telemetry_report.json")
    save_determinism_log_csv(report.determinism_records, "test_artifacts/determinism_log.csv")
    
    print(f"\n✅ Cache telemetry collection complete!")
    print(f"   Report saved to test_artifacts/cache_telemetry_report.json")
    print(f"   Determinism log saved to test_artifacts/determinism_log.csv")
