"""
Phase 7 — Batch Simulation Orchestrator: Portfolio-Wide Parallel Execution
==========================================================================

High-performance batch simulation engine for running multiple scenarios across
portfolio holdings with parallel execution and intelligent caching.

Features:
- Parallel scenario execution (ThreadPoolExecutor/ProcessPoolExecutor)
- Portfolio-wide risk analysis across M scenarios
- Intelligent caching for scenario reuse
- Deterministic reproducibility with seed management
- Performance targets: 10-ticker ≤10s, 50-ticker ≤40s
- Comprehensive batch result aggregation

Author: Agent 1B — Unified Financial Dashboard Team
Version: 1.0 (Phase 7 - Advanced Simulation Orchestration)
Date: October 29, 2025
"""

import json
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from functools import lru_cache
import time
import logging

# Import simulation components
from scenario_engine import (
    ScenarioEngine, ScenarioParameters, ScenarioType, ScenarioDataset,
    StressType, EventType, create_monte_carlo_scenario,
    create_stress_scenario, create_event_scenario
)
from portfolio_simulator import (
    Portfolio, PortfolioLoader, PortfolioSimulator,
    SimulationResult, RiskMetrics
)
from options_risk_simulator import (
    OptionsRiskSimulator, OptionContract, OptionSimulationResult
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# BATCH CONFIGURATION
# ============================================================================

@dataclass
class BatchConfig:
    """Configuration for batch simulation execution"""
    # Portfolio settings
    portfolio_id: str = "batch_portfolio"
    tickers: List[str] = field(default_factory=lambda: ["SPY", "QQQ", "IWM"])
    allocation_per_ticker: float = 10000.0
    
    # Scenario settings
    num_monte_carlo: int = 3  # Number of MC scenarios with different seeds
    include_stress_tests: bool = True
    include_event_driven: bool = True
    num_days: int = 252  # Trading days per scenario
    base_random_seed: int = 42
    
    # Stress test configuration
    stress_types: List[StressType] = field(default_factory=lambda: [
        StressType.VOLATILITY_SPIKE,
        StressType.SECTOR_SHOCK,
        StressType.BLACK_SWAN
    ])
    
    # Event-driven configuration
    event_types: List[EventType] = field(default_factory=lambda: [
        EventType.EARNINGS_BEAT,
        EventType.FED_RATE_HIKE
    ])
    
    # Performance settings
    max_workers: int = 4  # Parallel workers
    use_multiprocessing: bool = False  # True for CPU-intensive, False for I/O
    cache_scenarios: bool = True
    
    # Output settings
    output_dir: str = "outputs/phase7_batch"
    save_individual_results: bool = True
    save_aggregate_reports: bool = True


# ============================================================================
# BATCH RESULT DATA STRUCTURES
# ============================================================================

@dataclass
class ScenarioMetadata:
    """Metadata for a single scenario in batch"""
    scenario_id: str
    scenario_type: str
    random_seed: int
    num_days: int
    tickers: List[str]
    generation_time_ms: float


@dataclass
class BatchSimulationResult:
    """Comprehensive result from batch simulation execution"""
    batch_id: str
    portfolio_id: str
    config: BatchConfig
    
    # Scenario metadata
    scenarios_executed: List[ScenarioMetadata]
    
    # Portfolio simulation results
    portfolio_results: List[SimulationResult]
    
    # Options simulation results (if any)
    options_results: List[OptionSimulationResult]
    
    # Aggregate metrics
    aggregate_metrics: Dict[str, Any]
    
    # Performance metrics
    total_execution_time_ms: float
    scenarios_per_second: float
    cache_hit_rate: float
    
    # Timestamp
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "batch_id": self.batch_id,
            "portfolio_id": self.portfolio_id,
            "timestamp": self.timestamp,
            "config": {
                "tickers": self.config.tickers,
                "num_monte_carlo": self.config.num_monte_carlo,
                "num_days": self.config.num_days,
                "max_workers": self.config.max_workers
            },
            "scenarios_executed": [asdict(s) for s in self.scenarios_executed],
            "portfolio_results": [r.to_dict() for r in self.portfolio_results],
            "options_results": [r.to_dict() for r in self.options_results],
            "aggregate_metrics": self.aggregate_metrics,
            "performance": {
                "total_execution_time_ms": self.total_execution_time_ms,
                "scenarios_per_second": self.scenarios_per_second,
                "cache_hit_rate": self.cache_hit_rate
            }
        }


# ============================================================================
# SCENARIO CACHE
# ============================================================================

class ScenarioCache:
    """
    Intelligent caching for scenario reuse.
    
    Caches scenarios by (tickers, scenario_type, seed, num_days) tuple.
    """
    
    def __init__(self):
        self.cache: Dict[Tuple, ScenarioDataset] = {}
        self.hits = 0
        self.misses = 0
    
    def _make_key(
        self,
        tickers: List[str],
        scenario_type: str,
        seed: int,
        num_days: int
    ) -> Tuple:
        """Create cache key"""
        return (tuple(sorted(tickers)), scenario_type, seed, num_days)
    
    def get(
        self,
        tickers: List[str],
        scenario_type: str,
        seed: int,
        num_days: int
    ) -> Optional[ScenarioDataset]:
        """Retrieve cached scenario"""
        key = self._make_key(tickers, scenario_type, seed, num_days)
        
        if key in self.cache:
            self.hits += 1
            logger.debug(f"📦 Cache HIT: {scenario_type} seed={seed}")
            return self.cache[key]
        
        self.misses += 1
        logger.debug(f"❌ Cache MISS: {scenario_type} seed={seed}")
        return None
    
    def put(
        self,
        scenario: ScenarioDataset,
        tickers: List[str],
        scenario_type: str,
        seed: int,
        num_days: int
    ) -> None:
        """Store scenario in cache"""
        key = self._make_key(tickers, scenario_type, seed, num_days)
        self.cache[key] = scenario
        logger.debug(f"💾 Cached: {scenario_type} seed={seed}")
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def clear(self) -> None:
        """Clear cache"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0


# ============================================================================
# BATCH ORCHESTRATOR
# ============================================================================

class BatchSimulationOrchestrator:
    """
    High-performance batch simulation orchestrator with parallel execution.
    """
    
    def __init__(self, config: BatchConfig):
        self.config = config
        self.cache = ScenarioCache() if config.cache_scenarios else None
        self.batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create output directory
        self.output_dir = Path(config.output_dir) / self.batch_id
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    # ========================================================================
    # SCENARIO GENERATION
    # ========================================================================
    
    def _generate_scenario(
        self,
        scenario_type: str,
        tickers: List[str],
        random_seed: int,
        stress_type: Optional[StressType] = None,
        event_type: Optional[EventType] = None
    ) -> Tuple[ScenarioDataset, float]:
        """
        Generate single scenario with optional caching.
        
        Returns:
            Tuple of (ScenarioDataset, generation_time_ms)
        """
        # Check cache first
        if self.cache:
            cached = self.cache.get(tickers, scenario_type, random_seed, self.config.num_days)
            if cached:
                return cached, 0.0  # Cache hit, no generation time
        
        # Generate scenario
        start_time = time.time()
        
        if scenario_type == "monte_carlo":
            scenario = create_monte_carlo_scenario(
                tickers=tickers,
                num_simulations=1000,
                num_days=self.config.num_days,
                random_seed=random_seed,
                output_dir=str(self.output_dir / "scenarios")
            )
        elif scenario_type == "stress_test":
            scenario = create_stress_scenario(
                tickers=tickers,
                stress_type=stress_type,
                num_days=self.config.num_days,
                random_seed=random_seed,
                output_dir=str(self.output_dir / "scenarios")
            )
        elif scenario_type == "event_driven":
            scenario = create_event_scenario(
                tickers=tickers,
                event_type=event_type,
                event_day=self.config.num_days // 2,
                num_days=self.config.num_days,
                random_seed=random_seed,
                output_dir=str(self.output_dir / "scenarios")
            )
        else:
            raise ValueError(f"Unknown scenario type: {scenario_type}")
        
        generation_time = (time.time() - start_time) * 1000
        
        # Cache scenario
        if self.cache:
            self.cache.put(scenario, tickers, scenario_type, random_seed, self.config.num_days)
        
        return scenario, generation_time
    
    def generate_all_scenarios(self) -> List[Tuple[ScenarioDataset, ScenarioMetadata]]:
        """
        Generate all scenarios for batch execution.
        
        Returns:
            List of (ScenarioDataset, ScenarioMetadata) tuples
        """
        logger.info(f"🎲 Generating scenarios for {len(self.config.tickers)} tickers")
        
        scenarios = []
        tickers = self.config.tickers
        
        # Monte Carlo scenarios (different seeds)
        for i in range(self.config.num_monte_carlo):
            seed = self.config.base_random_seed + i
            scenario, gen_time = self._generate_scenario(
                "monte_carlo", tickers, seed
            )
            
            metadata = ScenarioMetadata(
                scenario_id=scenario.scenario_id,
                scenario_type="monte_carlo",
                random_seed=seed,
                num_days=self.config.num_days,
                tickers=tickers,
                generation_time_ms=gen_time
            )
            scenarios.append((scenario, metadata))
        
        # Stress test scenarios
        if self.config.include_stress_tests:
            for stress_type in self.config.stress_types:
                seed = self.config.base_random_seed + 100 + len(scenarios)
                scenario, gen_time = self._generate_scenario(
                    "stress_test", tickers, seed, stress_type=stress_type
                )
                
                metadata = ScenarioMetadata(
                    scenario_id=scenario.scenario_id,
                    scenario_type=f"stress_{stress_type.value}",
                    random_seed=seed,
                    num_days=self.config.num_days,
                    tickers=tickers,
                    generation_time_ms=gen_time
                )
                scenarios.append((scenario, metadata))
        
        # Event-driven scenarios
        if self.config.include_event_driven:
            for event_type in self.config.event_types:
                seed = self.config.base_random_seed + 200 + len(scenarios)
                scenario, gen_time = self._generate_scenario(
                    "event_driven", tickers, seed, event_type=event_type
                )
                
                metadata = ScenarioMetadata(
                    scenario_id=scenario.scenario_id,
                    scenario_type=f"event_{event_type.value}",
                    random_seed=seed,
                    num_days=self.config.num_days,
                    tickers=tickers,
                    generation_time_ms=gen_time
                )
                scenarios.append((scenario, metadata))
        
        logger.info(f"✅ Generated {len(scenarios)} scenarios")
        return scenarios
    
    # ========================================================================
    # PORTFOLIO SIMULATION
    # ========================================================================
    
    def _simulate_portfolio_scenario(
        self,
        portfolio: Portfolio,
        scenario: ScenarioDataset,
        metadata: ScenarioMetadata
    ) -> SimulationResult:
        """Simulate single portfolio scenario"""
        simulator = PortfolioSimulator(portfolio)
        result = simulator.apply_scenario(scenario)
        return result
    
    def simulate_portfolio_batch(
        self,
        portfolio: Portfolio,
        scenarios: List[Tuple[ScenarioDataset, ScenarioMetadata]]
    ) -> List[SimulationResult]:
        """
        Simulate portfolio across all scenarios with parallel execution.
        
        Args:
            portfolio: Portfolio to simulate
            scenarios: List of (scenario, metadata) tuples
            
        Returns:
            List of SimulationResult objects
        """
        logger.info(f"💼 Running {len(scenarios)} portfolio simulations")
        
        results = []
        
        if self.config.max_workers > 1:
            # Parallel execution
            executor_class = ProcessPoolExecutor if self.config.use_multiprocessing else ThreadPoolExecutor
            
            with executor_class(max_workers=self.config.max_workers) as executor:
                # Submit all tasks
                futures = {
                    executor.submit(
                        self._simulate_portfolio_scenario,
                        portfolio,
                        scenario,
                        metadata
                    ): (scenario, metadata)
                    for scenario, metadata in scenarios
                }
                
                # Collect results as they complete
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                        logger.debug(f"✅ Completed: {result.scenario_id}")
                    except Exception as e:
                        scenario, metadata = futures[future]
                        logger.error(f"❌ Failed scenario {metadata.scenario_id}: {e}")
        else:
            # Sequential execution
            for scenario, metadata in scenarios:
                try:
                    result = self._simulate_portfolio_scenario(portfolio, scenario, metadata)
                    results.append(result)
                except Exception as e:
                    logger.error(f"❌ Failed scenario {metadata.scenario_id}: {e}")
        
        logger.info(f"✅ Completed {len(results)} portfolio simulations")
        return results
    
    # ========================================================================
    # AGGREGATE METRICS
    # ========================================================================
    
    def compute_aggregate_metrics(
        self,
        portfolio_results: List[SimulationResult]
    ) -> Dict[str, Any]:
        """
        Compute aggregate metrics across all simulations.
        
        Args:
            portfolio_results: List of SimulationResult objects
            
        Returns:
            Dictionary of aggregate metrics
        """
        if not portfolio_results:
            return {}
        
        # Extract metrics
        returns = [r.total_return_pct for r in portfolio_results]
        sharpes = [r.risk_metrics.sharpe_ratio for r in portfolio_results]
        var_95s = [r.risk_metrics.var_95 for r in portfolio_results]
        var_99s = [r.risk_metrics.var_99 for r in portfolio_results]
        max_dds = [r.risk_metrics.max_drawdown for r in portfolio_results]
        
        # Compute statistics
        return {
            "num_scenarios": len(portfolio_results),
            "returns": {
                "mean": float(np.mean(returns)),
                "median": float(np.median(returns)),
                "std": float(np.std(returns)),
                "min": float(np.min(returns)),
                "max": float(np.max(returns)),
                "percentile_5": float(np.percentile(returns, 5)),
                "percentile_25": float(np.percentile(returns, 25)),
                "percentile_75": float(np.percentile(returns, 75)),
                "percentile_95": float(np.percentile(returns, 95))
            },
            "sharpe_ratio": {
                "mean": float(np.mean(sharpes)),
                "median": float(np.median(sharpes)),
                "min": float(np.min(sharpes)),
                "max": float(np.max(sharpes))
            },
            "var_95": {
                "mean": float(np.mean(var_95s)),
                "median": float(np.median(var_95s)),
                "min": float(np.min(var_95s)),
                "max": float(np.max(var_95s))
            },
            "var_99": {
                "mean": float(np.mean(var_99s)),
                "median": float(np.median(var_99s)),
                "min": float(np.min(var_99s)),
                "max": float(np.max(var_99s))
            },
            "max_drawdown": {
                "mean": float(np.mean(max_dds)),
                "median": float(np.median(max_dds)),
                "worst": float(np.min(max_dds))
            },
            "by_scenario_type": self._aggregate_by_scenario_type(portfolio_results)
        }
    
    def _aggregate_by_scenario_type(
        self,
        results: List[SimulationResult]
    ) -> Dict[str, Dict[str, float]]:
        """Aggregate metrics by scenario type"""
        by_type: Dict[str, List[float]] = {}
        
        for result in results:
            scenario_type = result.scenario_type
            if scenario_type not in by_type:
                by_type[scenario_type] = []
            by_type[scenario_type].append(result.total_return_pct)
        
        aggregated = {}
        for scenario_type, returns in by_type.items():
            aggregated[scenario_type] = {
                "count": len(returns),
                "mean_return": float(np.mean(returns)),
                "median_return": float(np.median(returns)),
                "min_return": float(np.min(returns)),
                "max_return": float(np.max(returns))
            }
        
        return aggregated
    
    # ========================================================================
    # MAIN EXECUTION
    # ========================================================================
    
    def execute_batch(self) -> BatchSimulationResult:
        """
        Execute complete batch simulation.
        
        Returns:
            BatchSimulationResult with all results and metrics
        """
        logger.info("=" * 80)
        logger.info(f"🚀 BATCH SIMULATION: {self.batch_id}")
        logger.info("=" * 80)
        logger.info(f"   Portfolio: {len(self.config.tickers)} tickers")
        logger.info(f"   Scenarios: MC={self.config.num_monte_carlo}, "
                   f"Stress={len(self.config.stress_types) if self.config.include_stress_tests else 0}, "
                   f"Events={len(self.config.event_types) if self.config.include_event_driven else 0}")
        logger.info(f"   Workers: {self.config.max_workers}")
        logger.info("=" * 80)
        
        batch_start_time = time.time()
        
        # Step 1: Create portfolio
        logger.info("\n📊 Step 1: Creating portfolio")
        portfolio = PortfolioLoader.create_synthetic(
            tickers=self.config.tickers,
            allocation=self.config.allocation_per_ticker * len(self.config.tickers),
            portfolio_id=self.config.portfolio_id
        )
        
        # Step 2: Generate scenarios
        logger.info("\n🎲 Step 2: Generating scenarios")
        scenarios = self.generate_all_scenarios()
        scenario_metadata = [meta for _, meta in scenarios]
        
        # Step 3: Run portfolio simulations
        logger.info("\n💼 Step 3: Running portfolio simulations")
        portfolio_results = self.simulate_portfolio_batch(portfolio, scenarios)
        
        # Step 4: Compute aggregate metrics
        logger.info("\n📈 Step 4: Computing aggregate metrics")
        aggregate_metrics = self.compute_aggregate_metrics(portfolio_results)
        
        # Calculate performance metrics
        total_time = (time.time() - batch_start_time) * 1000
        scenarios_per_sec = len(scenarios) / (total_time / 1000) if total_time > 0 else 0
        cache_hit_rate = self.cache.hit_rate if self.cache else 0.0
        
        # Create batch result
        batch_result = BatchSimulationResult(
            batch_id=self.batch_id,
            portfolio_id=self.config.portfolio_id,
            config=self.config,
            scenarios_executed=scenario_metadata,
            portfolio_results=portfolio_results,
            options_results=[],  # Will be populated by options batch analysis
            aggregate_metrics=aggregate_metrics,
            total_execution_time_ms=total_time,
            scenarios_per_second=scenarios_per_sec,
            cache_hit_rate=cache_hit_rate
        )
        
        # Save results
        if self.config.save_individual_results:
            self._save_batch_result(batch_result)
        
        # Print summary
        self._print_summary(batch_result)
        
        return batch_result
    
    def _save_batch_result(self, result: BatchSimulationResult) -> None:
        """Save batch result to JSON"""
        filepath = self.output_dir / f"{result.batch_id}_results.json"
        
        with open(filepath, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
        
        logger.info(f"\n💾 Saved batch result: {filepath}")
    
    def _print_summary(self, result: BatchSimulationResult) -> None:
        """Print batch execution summary"""
        logger.info("\n" + "=" * 80)
        logger.info("BATCH EXECUTION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Batch ID: {result.batch_id}")
        logger.info(f"Total Scenarios: {len(result.scenarios_executed)}")
        logger.info(f"Portfolio Simulations: {len(result.portfolio_results)}")
        logger.info(f"Execution Time: {result.total_execution_time_ms/1000:.2f}s")
        logger.info(f"Scenarios/Second: {result.scenarios_per_second:.2f}")
        logger.info(f"Cache Hit Rate: {result.cache_hit_rate:.1%}")
        logger.info("\n📊 Aggregate Metrics:")
        logger.info(f"   Mean Return: {result.aggregate_metrics['returns']['mean']:.2%}")
        logger.info(f"   Median Return: {result.aggregate_metrics['returns']['median']:.2%}")
        logger.info(f"   Mean Sharpe: {result.aggregate_metrics['sharpe_ratio']['mean']:.2f}")
        logger.info(f"   Mean VaR 95%: {result.aggregate_metrics['var_95']['mean']:.2%}")
        logger.info(f"   Worst Drawdown: {result.aggregate_metrics['max_drawdown']['worst']:.2%}")
        logger.info("=" * 80)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_batch_config(
    tickers: List[str],
    num_monte_carlo: int = 3,
    include_stress: bool = True,
    include_events: bool = True,
    max_workers: int = 4
) -> BatchConfig:
    """Quick function to create batch configuration"""
    return BatchConfig(
        tickers=tickers,
        num_monte_carlo=num_monte_carlo,
        include_stress_tests=include_stress,
        include_event_driven=include_events,
        max_workers=max_workers
    )


def run_batch_simulation(
    tickers: List[str],
    num_monte_carlo: int = 3,
    max_workers: int = 4
) -> BatchSimulationResult:
    """
    Quick function to run batch simulation.
    
    Args:
        tickers: List of ticker symbols
        num_monte_carlo: Number of Monte Carlo scenarios
        max_workers: Number of parallel workers
        
    Returns:
        BatchSimulationResult
    """
    config = create_batch_config(tickers, num_monte_carlo, max_workers=max_workers)
    orchestrator = BatchSimulationOrchestrator(config)
    return orchestrator.execute_batch()


# ============================================================================
# MAIN EXECUTION (FOR TESTING)
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("PHASE 7 — BATCH SIMULATION ORCHESTRATOR TEST")
    logger.info("=" * 80)
    
    # Test 1: Small batch (10 tickers)
    logger.info("\n🔬 Test 1: Small Batch (10 tickers)")
    small_tickers = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META"]
    
    small_config = BatchConfig(
        tickers=small_tickers,
        num_monte_carlo=2,
        include_stress_tests=True,
        include_event_driven=True,
        num_days=60,  # Shorter for testing
        max_workers=4,
        cache_scenarios=True
    )
    
    small_orchestrator = BatchSimulationOrchestrator(small_config)
    small_result = small_orchestrator.execute_batch()
    
    # Test 2: Large batch (50 tickers) - performance test
    logger.info("\n🔬 Test 2: Large Batch (50 tickers) - Performance Test")
    large_tickers = [f"TICKER{i:02d}" for i in range(50)]
    
    large_config = BatchConfig(
        tickers=large_tickers,
        num_monte_carlo=2,
        include_stress_tests=False,  # Fewer scenarios for speed
        include_event_driven=False,
        num_days=60,
        max_workers=8,
        cache_scenarios=True
    )
    
    large_orchestrator = BatchSimulationOrchestrator(large_config)
    large_result = large_orchestrator.execute_batch()
    
    # Performance summary
    logger.info("\n" + "=" * 80)
    logger.info("PERFORMANCE SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Small Batch (10 tickers): {small_result.total_execution_time_ms/1000:.2f}s")
    logger.info(f"Large Batch (50 tickers): {large_result.total_execution_time_ms/1000:.2f}s")
    logger.info(f"Small Batch Throughput: {small_result.scenarios_per_second:.2f} scenarios/s")
    logger.info(f"Large Batch Throughput: {large_result.scenarios_per_second:.2f} scenarios/s")
    logger.info("=" * 80)
    
    logger.info("\n✅ ALL BATCH ORCHESTRATOR TESTS COMPLETE")
