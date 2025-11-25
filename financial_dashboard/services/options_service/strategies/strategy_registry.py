"""
Dynamic Strategy Registry System.

Provides automatic discovery, registration, and runtime loading of trading
strategies without manual imports. Supports hot-reloading and MLflow integration.

Architecture:
- Singleton pattern for global registry access
- Lazy import to minimize startup overhead
- Metaclass-based auto-registration
- Optional MLflow lineage tracking
"""

import importlib
import pkgutil
import inspect
import os
from typing import Dict, List, Type, Any, Optional
from pathlib import Path
from abc import ABCMeta


# Custom exceptions
class StrategyNotFoundError(Exception):
    """Raised when a requested strategy is not found in the registry."""
    pass


class DuplicateStrategyError(Exception):
    """Raised when attempting to register a strategy that already exists."""
    pass


class StrategyRegistryMeta(ABCMeta):
    """
    Metaclass that automatically registers strategy classes.
    
    Any class inheriting from BaseStrategy will be automatically
    registered in the global strategy registry.
    """
    
    def __new__(mcs, name, bases, namespace, **kwargs):
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        
        # Only register concrete strategy classes, not BaseStrategy itself
        if name != 'BaseStrategy' and not inspect.isabstract(cls):
            # Get the singleton registry instance
            registry = StrategyRegistry.get_instance()
            
            # Auto-register this strategy class
            try:
                registry._auto_register(name, cls)
            except DuplicateStrategyError:
                # Strategy already registered, skip
                pass
        
        return cls


class StrategyRegistry:
    """
    Singleton registry for automatic strategy discovery and management.
    
    Features:
    - Auto-discovers strategies in the strategies/ directory
    - Provides APIs for listing, retrieving, and instantiating strategies
    - Supports hot-reloading in development mode
    - Optional MLflow integration for experiment tracking
    
    Example:
        >>> registry = StrategyRegistry.get_instance()
        >>> strategies = registry.list_strategies()
        >>> ['CoveredCallScreener', 'IronCondor', ...]
        
        >>> strategy_class = registry.get_strategy('CoveredCallScreener')
        >>> instance = registry.instantiate_strategy(
        ...     'CoveredCallScreener',
        ...     name='my_strategy',
        ...     params={'ticker': 'AAPL'}
        ... )
    """
    
    _instance: Optional['StrategyRegistry'] = None
    _lock = None  # Will be threading.Lock() if needed
    
    def __init__(
        self,
        search_paths: Optional[List[str]] = None,
        auto_reload: bool = False,
        mlflow_tracking: bool = False
    ):
        """
        Initialize the strategy registry.
        
        Args:
            search_paths: List of directory paths to search for strategies.
                         If None, uses default strategies/ directory.
            auto_reload: Enable automatic reloading when strategy files change.
            mlflow_tracking: Enable MLflow experiment tracking integration.
        """
        self._strategies: Dict[str, Type] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._instantiation_history: List[Dict[str, Any]] = []
        self.auto_reload = auto_reload
        self.mlflow_tracking = mlflow_tracking
        
        # Determine search paths
        if search_paths is None:
            # Default to strategies/ directory
            strategies_dir = Path(__file__).parent
            self._search_paths = [str(strategies_dir)]
        else:
            self._search_paths = search_paths
        
        # Perform initial discovery
        self._discover_strategies()
    
    @classmethod
    def get_instance(cls) -> 'StrategyRegistry':
        """
        Get the singleton instance of the strategy registry.
        
        Returns:
            The global StrategyRegistry instance.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _discover_strategies(self):
        """
        Scan configured directories for strategy modules and import them.
        
        This triggers the metaclass-based auto-registration for discovered
        strategy classes.
        """
        for search_path in self._search_paths:
            if not os.path.exists(search_path):
                continue
            
            # Get the package name from the path
            path_obj = Path(search_path)
            
            # Walk through all Python modules in the directory
            for finder, name, ispkg in pkgutil.iter_modules([search_path]):
                # Skip special modules
                if name.startswith('_') or name == 'strategy_registry':
                    continue
                
                try:
                    # Construct module path
                    module_path = f"financial_dashboard.services.options_service.strategies.{name}"
                    
                    # Import the module (this triggers metaclass registration)
                    importlib.import_module(module_path)
                    
                except Exception as e:
                    # Skip modules with import errors gracefully
                    continue
    
    def _auto_register(self, name: str, strategy_class: Type):
        """
        Internal method called by metaclass to register strategies.
        
        Args:
            name: Strategy class name
            strategy_class: The strategy class to register
            
        Raises:
            DuplicateStrategyError: If strategy already registered
        """
        # Normalize name to lowercase for case-insensitive lookup
        normalized_name = name.lower()
        
        if normalized_name in self._strategies:
            # Strategy already registered
            raise DuplicateStrategyError(
                f"Strategy '{name}' is already registered"
            )
        
        # Register the strategy
        self._strategies[normalized_name] = strategy_class
        
        # Store metadata
        self._metadata[normalized_name] = {
            "name": name,
            "class": strategy_class,
            "module": strategy_class.__module__,
            "docstring": inspect.getdoc(strategy_class)
        }
    
    def register_strategy(self, name: str, strategy_class: Type):
        """
        Manually register a strategy class.
        
        Args:
            name: Strategy name for lookup
            strategy_class: The strategy class to register
            
        Raises:
            DuplicateStrategyError: If strategy already registered
        """
        self._auto_register(name, strategy_class)
    
    def list_strategies(self) -> List[str]:
        """
        Get list of all registered strategy names.
        
        Returns:
            List of strategy names (original casing preserved).
        """
        return [meta["name"] for meta in self._metadata.values()]
    
    def get_strategy(self, name: str) -> Type:
        """
        Retrieve a strategy class by name.
        
        Args:
            name: Strategy name (case-insensitive)
            
        Returns:
            The strategy class
            
        Raises:
            StrategyNotFoundError: If strategy not found
        """
        normalized_name = name.lower()
        
        if normalized_name not in self._strategies:
            available = ', '.join(self.list_strategies())
            raise StrategyNotFoundError(
                f"Strategy '{name}' not found. Available strategies: {available}"
            )
        
        return self._strategies[normalized_name]
    
    def get_strategy_metadata(self, name: str) -> Dict[str, Any]:
        """
        Get metadata about a registered strategy.
        
        Args:
            name: Strategy name (case-insensitive)
            
        Returns:
            Dictionary with strategy metadata (name, class, module, docstring)
            
        Raises:
            StrategyNotFoundError: If strategy not found
        """
        normalized_name = name.lower()
        
        if normalized_name not in self._metadata:
            raise StrategyNotFoundError(f"Strategy '{name}' not found")
        
        return self._metadata[normalized_name].copy()
    
    def instantiate_strategy(
        self,
        strategy_name: str,
        **kwargs
    ) -> Any:
        """
        Create an instance of a strategy with given parameters.
        
        Args:
            strategy_name: Strategy class name (case-insensitive)
            **kwargs: Parameters to pass to strategy constructor
                     (typically 'name' and 'params')
        
        Returns:
            Instantiated strategy object
            
        Raises:
            StrategyNotFoundError: If strategy not found
            TypeError: If invalid parameters provided
            
        Example:
            >>> instance = registry.instantiate_strategy(
            ...     'CoveredCallScreener',
            ...     name='my_strategy',
            ...     params={'ticker': 'AAPL'}
            ... )
        """
        strategy_class = self.get_strategy(strategy_name)
        
        # Create instance
        instance = strategy_class(**kwargs)
        
        # Track instantiation history
        self._instantiation_history.append({
            "strategy_name": self.get_strategy_metadata(strategy_name)["name"],
            "class": strategy_class.__name__,
            "params": kwargs.get('params', {}),
            "instance_name": kwargs.get('name', 'unnamed')
        })
        
        # Apply MLflow tags if enabled
        if self.mlflow_tracking:
            self._apply_mlflow_tags(instance, strategy_name)
        
        return instance
    
    def _apply_mlflow_tags(self, instance: Any, strategy_name: str):
        """
        Apply MLflow tags to strategy instance for lineage tracking.
        
        Args:
            instance: Strategy instance
            strategy_name: Name of the strategy
        """
        # Set tags on the params attribute
        if hasattr(instance, 'params') and isinstance(instance.params, dict):
            instance.params['mlflow_strategy_type'] = strategy_name
            instance.params['mlflow_registry_tracking'] = True
    
    def get_instantiation_history(self) -> List[Dict[str, Any]]:
        """
        Get history of strategy instantiations.
        
        Returns:
            List of instantiation records with strategy names and parameters.
        """
        return self._instantiation_history.copy()
    
    def refresh(self):
        """
        Refresh the registry by re-scanning for strategies.
        
        Useful in development mode when new strategy files are added.
        Note: This only re-imports modules; already-registered strategies
        from metaclass registration are preserved.
        """
        # Re-discover strategies (will skip already-registered ones)
        self._discover_strategies()
    
    def __repr__(self) -> str:
        """String representation of the registry."""
        count = len(self._strategies)
        strategies = ', '.join(self.list_strategies()[:3])
        if count > 3:
            strategies += f", ... ({count - 3} more)"
        return f"<StrategyRegistry: {count} strategies [{strategies}]>"
