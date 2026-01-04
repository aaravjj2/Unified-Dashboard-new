"""
Alpaca Options Lab - Strategy Executor

Manages multiple strategies running concurrently with:
- Asyncio-based parallel execution
- Error isolation (one failure doesn't kill others)
- Resource allocation (capital, positions)
- Performance monitoring
- Hot reload support

Usage:
    executor = StrategyExecutor(context)
    
    # Add strategies
    await executor.add_strategy(config1)
    await executor.add_strategy(config2)
    
    # Process market data
    async for event in market_data_stream:
        await executor.process_market_data(event)
    
    # Stop all strategies
    stats = await executor.stop_all()
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

from src.strategies.base import Strategy, StrategyConfig, MarketEvent, FillEvent, Signal
from src.strategies.context import StrategyContext
from src.strategies.registry import StrategyRegistry
from src.utils.logging_config import get_logger
from src.utils.exceptions import StrategyError, CriticalStrategyError

logger = get_logger(__name__)


@dataclass
class StrategyMetrics:
    """Runtime metrics for a strategy."""
    name: str
    signals_generated: int = 0
    signals_executed: int = 0
    signals_rejected: int = 0
    errors: int = 0
    market_events_processed: int = 0
    avg_processing_time_ms: float = 0.0
    last_signal_time: Optional[datetime] = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def record_event_processing(self, duration_ms: float) -> None:
        """Update processing time average."""
        total = self.avg_processing_time_ms * self.market_events_processed
        self.market_events_processed += 1
        self.avg_processing_time_ms = (total + duration_ms) / self.market_events_processed


class StrategyExecutor:
    """
    Manages multiple strategies running concurrently.
    
    Responsibilities:
    - Lifecycle management (start, stop, restart)
    - Market data distribution
    - Signal processing and routing
    - Error isolation and recovery
    - Performance monitoring
    - Capital allocation tracking
    """
    
    def __init__(
        self, 
        context: StrategyContext,
        max_concurrent_events: int = 100
    ):
        """
        Initialize strategy executor.
        
        Args:
            context: Shared strategy context
            max_concurrent_events: Max events to process in parallel
        """
        self.context = context
        self.strategies: Dict[str, Strategy] = {}
        self.metrics: Dict[str, StrategyMetrics] = {}
        self.running = False
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max_concurrent_events)
        self._event_handlers: Dict[str, Callable] = {}
        
        logger.info("strategy_executor_initialized")
    
    # ================================================================
    # Lifecycle Methods
    # ================================================================
    
    async def add_strategy(self, config: StrategyConfig) -> None:
        """
        Add and start a strategy.
        
        Args:
            config: Strategy configuration
            
        Raises:
            StrategyError: If strategy fails to start
        """
        async with self._lock:
            if config.name in self.strategies:
                raise StrategyError(
                    f"Strategy {config.name} already running. "
                    "Use update_strategy() to modify."
                )
            
            # Check total allocation doesn't exceed 100%
            total_allocation = sum(
                s.config.capital_allocation 
                for s in self.strategies.values()
            ) + config.capital_allocation
            
            if total_allocation > 1.0:
                raise StrategyError(
                    f"Total capital allocation would exceed 100%: {total_allocation:.1%}"
                )
            
            try:
                # Create strategy instance
                strategy = StrategyRegistry.create(config, self.context)
                
                # Start strategy
                strategy._start()
                
                # Add to tracking
                self.strategies[config.name] = strategy
                self.metrics[config.name] = StrategyMetrics(name=config.name)
                
                logger.info(
                    "strategy_added",
                    name=config.name,
                    allocation=config.capital_allocation,
                    total_strategies=len(self.strategies)
                )
                
            except Exception as e:
                logger.error(
                    "strategy_add_failed",
                    name=config.name,
                    error=str(e)
                )
                raise
    
    async def remove_strategy(self, name: str) -> Dict[str, Any]:
        """
        Stop and remove a strategy.
        
        Args:
            name: Strategy name
            
        Returns:
            Final strategy statistics
        """
        async with self._lock:
            if name not in self.strategies:
                raise StrategyError(f"Strategy {name} not found")
            
            strategy = self.strategies[name]
            
            try:
                stats = strategy._stop()
            except Exception as e:
                logger.error("strategy_stop_failed", name=name, error=str(e))
                stats = {"error": str(e)}
            
            del self.strategies[name]
            metrics = self.metrics.pop(name, None)
            
            logger.info(
                "strategy_removed",
                name=name,
                signals_generated=metrics.signals_generated if metrics else 0
            )
            
            return {
                "strategy_stats": stats,
                "metrics": metrics.__dict__ if metrics else {}
            }
    
    async def update_strategy(self, config: StrategyConfig) -> None:
        """
        Update a running strategy's configuration.
        
        Supports hot reload without losing state.
        
        Args:
            config: New configuration
        """
        async with self._lock:
            if config.name not in self.strategies:
                raise StrategyError(f"Strategy {config.name} not found")
            
            strategy = self.strategies[config.name]
            old_config = strategy.config
            
            # Update config (preserve state)
            strategy.config = config
            
            logger.info(
                "strategy_updated",
                name=config.name,
                changes={
                    'enabled': (old_config.enabled, config.enabled),
                    'allocation': (old_config.capital_allocation, config.capital_allocation),
                }
            )
    
    async def start(self) -> None:
        """Start the executor."""
        self.running = True
        logger.info("strategy_executor_started", strategies=len(self.strategies))
    
    async def stop_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Stop all strategies and collect final stats.
        
        Returns:
            Dictionary mapping strategy names to final statistics
        """
        self.running = False
        results = {}
        
        for name in list(self.strategies.keys()):
            try:
                results[name] = await self.remove_strategy(name)
            except Exception as e:
                logger.error("strategy_stop_failed", name=name, error=str(e))
                results[name] = {"error": str(e)}
        
        logger.info("strategy_executor_stopped", strategies_stopped=len(results))
        return results
    
    # ================================================================
    # Event Processing
    # ================================================================
    
    async def process_market_data(self, event: MarketEvent) -> List[Signal]:
        """
        Distribute market data to all strategies.
        
        Args:
            event: Market data event
            
        Returns:
            List of generated signals (across all strategies)
        """
        if not self.running:
            return []
        
        all_signals: List[Signal] = []
        tasks = []
        
        for name, strategy in self.strategies.items():
            if not strategy.config.enabled:
                continue
            
            task = asyncio.create_task(
                self._safe_process_event(strategy, event)
            )
            tasks.append((name, task))
        
        # Wait for all strategies to process
        for name, task in tasks:
            try:
                signals = await task
                if signals:
                    all_signals.extend(signals)
                    self.metrics[name].signals_generated += len(signals)
                    self.metrics[name].last_signal_time = datetime.now(timezone.utc)
            except Exception as e:
                logger.error(
                    "strategy_task_failed",
                    strategy=name,
                    error=str(e)
                )
                self.metrics[name].errors += 1
        
        return all_signals
    
    async def _safe_process_event(
        self, 
        strategy: Strategy, 
        event: MarketEvent
    ) -> List[Signal]:
        """
        Process event with error isolation.
        
        If one strategy crashes, others continue running.
        """
        async with self._semaphore:
            start_time = datetime.now(timezone.utc)
            
            try:
                signals = strategy.on_market_data(event)
                
                # Record processing time
                duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                self.metrics[strategy.config.name].record_event_processing(duration_ms)
                
                return signals or []
                
            except CriticalStrategyError as e:
                # Critical error - disable strategy
                logger.exception(
                    "critical_strategy_error",
                    strategy=strategy.config.name,
                    error=str(e)
                )
                strategy.config.enabled = False
                return []
                
            except Exception as e:
                # Non-critical error - log and continue
                logger.exception(
                    "strategy_processing_error",
                    strategy=strategy.config.name,
                    event_symbol=event.symbol,
                    error=str(e)
                )
                return []
    
    async def process_fill(self, fill: FillEvent) -> None:
        """
        Route fill event to appropriate strategy.
        
        Args:
            fill: Fill event
        """
        if fill.strategy not in self.strategies:
            logger.warning(
                "fill_for_unknown_strategy",
                strategy=fill.strategy,
                order_id=fill.order_id
            )
            return
        
        strategy = self.strategies[fill.strategy]
        
        try:
            strategy.on_order_fill(fill)
            self.metrics[fill.strategy].signals_executed += 1
            
            logger.info(
                "fill_processed",
                strategy=fill.strategy,
                order_id=fill.order_id,
                fill_price=fill.fill_price
            )
            
        except Exception as e:
            logger.error(
                "fill_processing_failed",
                strategy=fill.strategy,
                error=str(e)
            )
    
    # ================================================================
    # Monitoring Methods
    # ================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get executor status.
        
        Returns:
            Status dictionary with all strategy metrics
        """
        return {
            "running": self.running,
            "total_strategies": len(self.strategies),
            "enabled_strategies": sum(
                1 for s in self.strategies.values() if s.config.enabled
            ),
            "total_allocation": sum(
                s.config.capital_allocation for s in self.strategies.values()
            ),
            "strategies": {
                name: {
                    "enabled": strategy.config.enabled,
                    "allocation": strategy.config.allocation,
                    "metrics": self.metrics[name].__dict__
                }
                for name, strategy in self.strategies.items()
            }
        }
    
    def get_metrics(self, name: str) -> Optional[StrategyMetrics]:
        """Get metrics for a specific strategy."""
        return self.metrics.get(name)
    
    def get_all_metrics(self) -> Dict[str, StrategyMetrics]:
        """Get metrics for all strategies."""
        return self.metrics.copy()
    
    # ================================================================
    # Utility Methods
    # ================================================================
    
    def is_strategy_enabled(self, name: str) -> bool:
        """Check if strategy is enabled."""
        if name not in self.strategies:
            return False
        return self.strategies[name].config.enabled
    
    def enable_strategy(self, name: str) -> None:
        """Enable a strategy."""
        if name in self.strategies:
            self.strategies[name].config.enabled = True
            logger.info("strategy_enabled", name=name)
    
    def disable_strategy(self, name: str) -> None:
        """Disable a strategy."""
        if name in self.strategies:
            self.strategies[name].config.enabled = False
            logger.info("strategy_disabled", name=name)
