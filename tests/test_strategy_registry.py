"""
Test Suite for Dynamic Strategy Registry System.

This module tests the auto-discovery, registration, and runtime loading
of trading strategies without manual imports.

TDD Phase: RED - All tests designed to fail initially.
"""

import pytest
from typing import Dict, List, Any
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import sys

# Import base class first to ensure strategies are discovered
from financial_dashboard.services.options_service.strategies import BaseStrategy

# Import will fail initially - this is expected for TDD RED phase
try:
    from financial_dashboard.services.options_service.strategies.strategy_registry import (
        StrategyRegistry,
        StrategyNotFoundError,
        DuplicateStrategyError
    )
except ImportError:
    # Expected during RED phase
    StrategyRegistry = None
    StrategyNotFoundError = None
    DuplicateStrategyError = None


@pytest.fixture(autouse=True, scope="function")
def ensure_registry_initialized():
    """Ensure registry is initialized before each test and clean up history."""
    if StrategyRegistry is not None:
        # Get or create singleton
        registry = StrategyRegistry.get_instance()
        # Clear instantiation history for clean tests but preserve registered strategies
        if hasattr(registry, '_instantiation_history'):
            registry._instantiation_history.clear()
    yield
    # No cleanup - preserve singleton across tests


class TestStrategyRegistryAutoDiscovery:
    """Test automatic discovery of strategy classes."""
    
    def test_registry_discovers_known_strategies(self):
        """Registry should auto-discover CoveredCallScreener without manual registration."""
        if StrategyRegistry is None:
            pytest.skip("StrategyRegistry not yet implemented")
        
        registry = StrategyRegistry.get_instance()
        strategies = registry.list_strategies()
        
        # Should discover at least CoveredCallScreener
        assert "CoveredCallScreener" in strategies, \
            "Registry should auto-discover CoveredCallScreener"
        assert isinstance(strategies, list), "list_strategies should return list"
        assert len(strategies) >= 1, "Should discover at least one strategy"
    
    def test_registry_returns_strategy_metadata(self):
        """Registry should provide metadata about discovered strategies."""
        if StrategyRegistry is None:
            pytest.skip("StrategyRegistry not yet implemented")
        
        registry = StrategyRegistry()
        metadata = registry.get_strategy_metadata("CoveredCallScreener")
        
        assert isinstance(metadata, dict), "Metadata should be dict"
        assert "name" in metadata, "Should include strategy name"
        assert "class" in metadata, "Should include class reference"
        assert "module" in metadata, "Should include module path"
    
    def test_registry_discovers_strategies_recursively(self):
        """Registry should scan subdirectories for strategy modules."""
        if StrategyRegistry is None:
            pytest.skip("StrategyRegistry not yet implemented")
        
        registry = StrategyRegistry()
        strategies = registry.list_strategies()
        
        # Should discover strategies from strategies/ directory
        assert len(strategies) > 0, "Should discover strategies in directory tree"
    
    def test_registry_excludes_base_strategy_class(self):
        """Registry should not register the abstract BaseStrategy class."""
        if StrategyRegistry is None:
            pytest.skip("StrategyRegistry not yet implemented")
        
        registry = StrategyRegistry()
        strategies = registry.list_strategies()
        
        assert "BaseStrategy" not in strategies, \
            "Should exclude abstract base class from registry"


class TestStrategyRegistryGetOperations:
    """Test retrieval operations from the registry."""
    
    def test_get_strategy_returns_class(self):
        """get_strategy should return the strategy class, not instance."""
        if StrategyRegistry is None:
            pytest.skip("StrategyRegistry not yet implemented")
        
        registry = StrategyRegistry()
        strategy_class = registry.get_strategy("CoveredCallScreener")
        
        assert strategy_class is not None, "Should return strategy class"
        assert isinstance(strategy_class, type), "Should return class, not instance"
        assert issubclass(strategy_class, BaseStrategy), \
            "Returned class should inherit from BaseStrategy"
    
    def test_get_strategy_raises_on_unknown(self):
        """get_strategy should raise StrategyNotFoundError for unknown strategies."""
        if StrategyRegistry is None:
            pytest.skip("StrategyRegistry not yet implemented")
        
        registry = StrategyRegistry()
        
        with pytest.raises(StrategyNotFoundError) as exc_info:
            registry.get_strategy("NonExistentStrategy")
        
        assert "NonExistentStrategy" in str(exc_info.value), \
            "Error message should include strategy name"
    
    def test_get_strategy_case_insensitive(self):
        """get_strategy should handle case-insensitive lookups."""
        if StrategyRegistry is None:
            pytest.skip("StrategyRegistry not yet implemented")
        
        registry = StrategyRegistry()
        
        # Should work with different casing
        strategy1 = registry.get_strategy("CoveredCallScreener")
        strategy2 = registry.get_strategy("coveredcallscreener")
        
        assert strategy1 is strategy2, \
            "Should return same class regardless of case"


class TestStrategyRegistryInstantiation:
    """Test strategy instantiation through the registry."""
    
    def test_instantiate_strategy_creates_instance(self):
        """instantiate_strategy should create a configured instance."""
        if StrategyRegistry is None:
            pytest.skip("StrategyRegistry not yet implemented")
        
        registry = StrategyRegistry()
        instance = registry.instantiate_strategy(
            "CoveredCallScreener",
            name="test_strategy",
            params={"ticker": "AAPL"}
        )
        
        assert instance is not None, "Should create instance"
        assert isinstance(instance, BaseStrategy), "Should be BaseStrategy instance"
        assert instance.name == "test_strategy", "Should apply name parameter"
        assert instance.params["ticker"] == "AAPL", "Should apply params"
    
    def test_instantiate_strategy_with_defaults(self):
        """instantiate_strategy should handle default parameters."""
        if StrategyRegistry is None:
            pytest.skip("StrategyRegistry not yet implemented")
        
        registry = StrategyRegistry()
        instance = registry.instantiate_strategy(
            "CoveredCallScreener",
            name="default_test",
            params={}
        )
        
        assert instance is not None, "Should create instance with defaults"
        assert instance.name == "default_test"
        assert isinstance(instance.params, dict)
    
    def test_instantiate_strategy_raises_on_invalid_params(self):
        """instantiate_strategy should raise TypeError for invalid parameters."""
        if StrategyRegistry is None:
            pytest.skip("StrategyRegistry not yet implemented")
        
        registry = StrategyRegistry()
        
        with pytest.raises(TypeError):
            # Missing required 'name' parameter
            registry.instantiate_strategy(
                "CoveredCallScreener",
                params={"ticker": "AAPL"}
            )


class TestStrategyRegistryDuplicates:
    """Test handling of duplicate strategy registrations."""
    
    def test_duplicate_registration_raises_error(self):
        """Attempting to register duplicate strategy should raise DuplicateStrategyError."""
        if StrategyRegistry is None:
            pytest.skip("StrategyRegistry not yet implemented")
        
        registry = StrategyRegistry.get_instance()
        
        # Get an existing strategy class
        from financial_dashboard.services.options_service.strategies import CoveredCallScreener
        
        # Try to register it again manually
        with pytest.raises(DuplicateStrategyError) as exc_info:
            registry.register_strategy("CoveredCallScreener", CoveredCallScreener)
        
        assert "CoveredCallScreener" in str(exc_info.value)


class TestStrategyRegistryMLflowIntegration:
    """Test MLflow experiment tracking integration."""
    
    def test_registry_applies_mlflow_tags(self):
        """Registry should apply MLflow tags when instantiating strategies."""
        if StrategyRegistry is None:
            pytest.skip("StrategyRegistry not yet implemented")
        
        registry = StrategyRegistry.get_instance()
        # Enable mlflow tracking for this test
        original_tracking = registry.mlflow_tracking
        registry.mlflow_tracking = True
        
        try:
            instance = registry.instantiate_strategy(
                "CoveredCallScreener",
                name="mlflow_test",
                params={"ticker": "AAPL"}
            )
            
            # Verify MLflow tags were applied
            assert hasattr(instance, 'params')
            assert 'mlflow_strategy_type' in instance.params
            assert instance.params['mlflow_strategy_type'].lower() == "coveredcallscreener"
            assert 'mlflow_registry_tracking' in instance.params
            assert instance.params['mlflow_registry_tracking'] is True
        finally:
            # Restore original setting
            registry.mlflow_tracking = original_tracking
    
    def test_registry_mlflow_disabled_by_default(self):
        """Registry should not require MLflow by default."""
        if StrategyRegistry is None:
            pytest.skip("StrategyRegistry not yet implemented")
        
        registry = StrategyRegistry.get_instance()
        instance = registry.instantiate_strategy(
            "CoveredCallScreener",
            name="no_mlflow_test",
            params={"ticker": "AAPL"}
        )
        
        assert instance is not None, "Should work without MLflow"
    
    def test_registry_tracks_strategy_lineage(self):
        """Registry should track which strategies were instantiated."""
        if StrategyRegistry is None:
            pytest.skip("StrategyRegistry not yet implemented")
        
        registry = StrategyRegistry.get_instance()
        
        # Clear history to ensure clean test
        registry._instantiation_history.clear()
        
        # Instantiate multiple strategies
        registry.instantiate_strategy(
            "CoveredCallScreener",
            name="test1",
            params={"ticker": "AAPL"}
        )
        
        registry.instantiate_strategy(
            "CoveredCallScreener",
            name="test2",
            params={"ticker": "MSFT"}
        )
        
        # Should track instantiation history
        history = registry.get_instantiation_history()
        assert len(history) == 2, "Should track both instantiations"
        assert history[0]["strategy_name"] == "CoveredCallScreener"


class TestStrategyRegistryHotReload:
    """Test hot-reload functionality for development mode."""
    
    def test_registry_supports_refresh(self):
        """Registry should support manual refresh for discovering new strategies."""
        if StrategyRegistry is None:
            pytest.skip("StrategyRegistry not yet implemented")
        
        registry = StrategyRegistry()
        initial_count = len(registry.list_strategies())
        
        # Refresh should re-scan directory
        registry.refresh()
        
        refreshed_count = len(registry.list_strategies())
        assert refreshed_count >= initial_count, \
            "Refresh should maintain or discover new strategies"
    
    def test_registry_auto_reload_mode(self):
        """Registry with auto_reload=True should detect new strategy files."""
        if StrategyRegistry is None:
            pytest.skip("StrategyRegistry not yet implemented")
        
        # This test would require actually creating a new file
        # For now, just verify the registry accepts the parameter
        registry = StrategyRegistry(auto_reload=True)
        assert hasattr(registry, 'auto_reload'), "Should support auto_reload flag"


class TestStrategyRegistrySingleton:
    """Test singleton pattern for global registry access."""
    
    def test_registry_returns_same_instance(self):
        """Multiple calls should return the same registry instance."""
        if StrategyRegistry is None:
            pytest.skip("StrategyRegistry not yet implemented")
        
        registry1 = StrategyRegistry.get_instance()
        registry2 = StrategyRegistry.get_instance()
        
        assert registry1 is registry2, \
            "Should return singleton instance"
    
    def test_registry_singleton_persists_state(self):
        """Singleton registry should maintain state across calls."""
        if StrategyRegistry is None:
            pytest.skip("StrategyRegistry not yet implemented")
        
        registry1 = StrategyRegistry.get_instance()
        strategies1 = registry1.list_strategies()
        
        registry2 = StrategyRegistry.get_instance()
        strategies2 = registry2.list_strategies()
        
        assert strategies1 == strategies2, \
            "Singleton should maintain consistent state"


class TestStrategyRegistryEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_registry_handles_empty_directory(self):
        """Registry should handle scanning empty directories gracefully."""
        if StrategyRegistry is None:
            pytest.skip("StrategyRegistry not yet implemented")
        
        # Create a temporary empty directory
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = StrategyRegistry(search_paths=[tmpdir])
            strategies = registry.list_strategies()
            
            # Should return empty list, not crash
            assert isinstance(strategies, list)
    
    def test_registry_handles_invalid_modules(self):
        """Registry should skip modules with syntax errors gracefully."""
        if StrategyRegistry is None:
            pytest.skip("StrategyRegistry not yet implemented")
        
        registry = StrategyRegistry()
        
        # Should not crash even if there are problematic modules
        strategies = registry.list_strategies()
        assert isinstance(strategies, list)
    
    def test_registry_repr_is_informative(self):
        """Registry should have informative string representation."""
        if StrategyRegistry is None:
            pytest.skip("StrategyRegistry not yet implemented")
        
        registry = StrategyRegistry()
        repr_str = repr(registry)
        
        assert "StrategyRegistry" in repr_str
        assert str(len(registry.list_strategies())) in repr_str
