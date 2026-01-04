"""
Alpaca Options Lab - Strategy Registry

Dynamic strategy registration and instantiation.
Allows adding strategies without modifying core code.

Usage:
    # Register a strategy
    @StrategyRegistry.register("my_strategy")
    class MyStrategy(Strategy):
        ...
    
    # Create strategy instance
    config = StrategyConfig.from_yaml("configs/my_strategy.yaml")
    strategy = StrategyRegistry.create(config, context)
    
    # List available strategies
    strategies = StrategyRegistry.list_available()
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Type, TYPE_CHECKING

from src.utils.logging_config import get_logger
from src.utils.exceptions import StrategyError

if TYPE_CHECKING:
    from src.strategies.base import Strategy, StrategyConfig
    from src.strategies.context import StrategyContext

logger = get_logger(__name__)


class StrategyRegistry:
    """
    Registry for dynamically loading strategies.
    
    Strategies register themselves using the @register decorator.
    The registry maintains a mapping of strategy names to classes.
    
    Features:
    - Decorator-based registration
    - Lazy instantiation
    - Version tracking
    - Strategy metadata
    """
    
    _strategies: Dict[str, Type['Strategy']] = {}
    _metadata: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def register(
        cls, 
        name: str,
        version: str = "1.0.0",
        description: str = "",
        author: str = "",
        tags: Optional[List[str]] = None
    ) -> Callable[[Type['Strategy']], Type['Strategy']]:
        """
        Decorator to register a strategy.
        
        Args:
            name: Unique strategy name
            version: Strategy version
            description: Strategy description
            author: Strategy author
            tags: Categorization tags
            
        Returns:
            Decorator function
            
        Usage:
            @StrategyRegistry.register(
                "iron_condor",
                version="2.0.0",
                description="0DTE Iron Condor strategy",
                tags=["options", "income", "0dte"]
            )
            class IronCondorStrategy(Strategy):
                ...
        """
        def decorator(strategy_class: Type['Strategy']) -> Type['Strategy']:
            if name in cls._strategies:
                logger.warning(
                    "strategy_already_registered",
                    name=name,
                    overwriting=True
                )
            
            cls._strategies[name] = strategy_class
            cls._metadata[name] = {
                'version': version,
                'description': description,
                'author': author,
                'tags': tags or [],
                'class_name': strategy_class.__name__,
            }
            
            logger.info(
                "strategy_registered",
                name=name,
                version=version,
                class_name=strategy_class.__name__
            )
            
            return strategy_class
        
        return decorator
    
    @classmethod
    def create(
        cls, 
        config: 'StrategyConfig', 
        context: 'StrategyContext'
    ) -> 'Strategy':
        """
        Create strategy instance from config.
        
        Args:
            config: Strategy configuration
            context: Execution context
            
        Returns:
            Strategy instance
            
        Raises:
            StrategyError: If strategy not found
        """
        if config.name not in cls._strategies:
            available = cls.list_available()
            raise StrategyError(
                f"Unknown strategy: {config.name}. "
                f"Available: {available}"
            )
        
        strategy_class = cls._strategies[config.name]
        
        try:
            instance = strategy_class(config, context)
            
            logger.info(
                "strategy_created",
                name=config.name,
                enabled=config.enabled,
                allocation=config.capital_allocation
            )
            
            return instance
            
        except Exception as e:
            logger.error(
                "strategy_creation_failed",
                name=config.name,
                error=str(e)
            )
            raise StrategyError(f"Failed to create strategy: {e}")
    
    @classmethod
    def list_available(cls) -> List[str]:
        """
        List all registered strategy names.
        
        Returns:
            List of strategy names
        """
        return list(cls._strategies.keys())
    
    @classmethod
    def get_metadata(cls, name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a strategy.
        
        Args:
            name: Strategy name
            
        Returns:
            Metadata dictionary or None if not found
        """
        return cls._metadata.get(name)
    
    @classmethod
    def get_all_metadata(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get metadata for all strategies.
        
        Returns:
            Dictionary mapping strategy names to metadata
        """
        return cls._metadata.copy()
    
    @classmethod
    def find_by_tag(cls, tag: str) -> List[str]:
        """
        Find strategies by tag.
        
        Args:
            tag: Tag to search for
            
        Returns:
            List of strategy names with the tag
        """
        results = []
        for name, metadata in cls._metadata.items():
            if tag in metadata.get('tags', []):
                results.append(name)
        return results
    
    @classmethod
    def unregister(cls, name: str) -> bool:
        """
        Unregister a strategy.
        
        Args:
            name: Strategy name
            
        Returns:
            True if removed, False if not found
        """
        if name in cls._strategies:
            del cls._strategies[name]
            del cls._metadata[name]
            
            logger.info("strategy_unregistered", name=name)
            return True
        
        return False
    
    @classmethod
    def clear(cls) -> None:
        """
        Clear all registered strategies.
        
        Useful for testing.
        """
        cls._strategies.clear()
        cls._metadata.clear()
        logger.info("strategy_registry_cleared")
    
    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        Check if a strategy is registered.
        
        Args:
            name: Strategy name
            
        Returns:
            True if registered
        """
        return name in cls._strategies
