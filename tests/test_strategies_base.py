"""
Unit tests for BaseStrategy abstract base class.

These tests verify that:
1. BaseStrategy cannot be instantiated directly (abstract class)
2. Subclasses must implement required abstract methods
3. The strategy interface is properly defined
"""

import pytest
from abc import ABC
from financial_dashboard.services.options_service.strategies.base_strategy import BaseStrategy


class TestBaseStrategyAbstract:
    """Test that BaseStrategy is truly abstract and cannot be instantiated."""
    
    def test_base_strategy_cannot_be_instantiated(self):
        """BaseStrategy should raise TypeError when instantiated directly."""
        with pytest.raises(TypeError) as exc_info:
            BaseStrategy(name="test", params={})
        
        # Verify the error message indicates missing abstract methods
        assert "abstract" in str(exc_info.value).lower()
    
    def test_base_strategy_is_abc(self):
        """BaseStrategy should be an instance of ABC."""
        assert issubclass(BaseStrategy, ABC)


class TestBaseStrategySubclassRequirements:
    """Test that subclasses must implement all abstract methods."""
    
    def test_subclass_missing_generate_signals_fails(self):
        """Subclass missing generate_signals should raise TypeError."""
        
        class IncompleteStrategy(BaseStrategy):
            """Missing generate_signals implementation."""
            def backtest(self, historical_df):
                return {}
        
        with pytest.raises(TypeError) as exc_info:
            IncompleteStrategy(name="incomplete", params={})
        
        assert "generate_signals" in str(exc_info.value).lower()
    
    def test_subclass_missing_backtest_fails(self):
        """Subclass missing backtest should raise TypeError."""
        
        class IncompleteStrategy(BaseStrategy):
            """Missing backtest implementation."""
            def generate_signals(self, historical_df):
                return []
        
        with pytest.raises(TypeError) as exc_info:
            IncompleteStrategy(name="incomplete", params={})
        
        assert "backtest" in str(exc_info.value).lower()
    
    def test_complete_subclass_instantiates(self):
        """Complete subclass with all methods should instantiate successfully."""
        
        class CompleteStrategy(BaseStrategy):
            """Complete implementation of all abstract methods."""
            
            def generate_signals(self, historical_df):
                return []
            
            def backtest(self, historical_df):
                return {"sharpe_ratio": 1.5}
        
        # Should not raise
        strategy = CompleteStrategy(name="complete", params={"test": True})
        
        assert strategy.name == "complete"
        assert strategy.params == {"test": True}


class TestBaseStrategyInterface:
    """Test the BaseStrategy interface methods."""
    
    def test_strategy_has_to_dict_method(self):
        """BaseStrategy should provide to_dict() for serialization."""
        
        class TestStrategy(BaseStrategy):
            def generate_signals(self, historical_df):
                return []
            def backtest(self, historical_df):
                return {}
        
        strategy = TestStrategy(name="test_strat", params={"param1": "value1"})
        
        # Should have to_dict method
        assert hasattr(strategy, "to_dict")
        
        # Should return dict with name and params
        result = strategy.to_dict()
        assert isinstance(result, dict)
        assert result["name"] == "test_strat"
        assert result["params"] == {"param1": "value1"}
    
    def test_strategy_has_from_dict_classmethod(self):
        """BaseStrategy should provide from_dict() for deserialization."""
        
        class TestStrategy(BaseStrategy):
            def generate_signals(self, historical_df):
                return []
            def backtest(self, historical_df):
                return {}
        
        # Should have from_dict class method
        assert hasattr(TestStrategy, "from_dict")
        
        # Should reconstruct strategy from dict
        config = {"name": "restored", "params": {"key": "val"}}
        strategy = TestStrategy.from_dict(config)
        
        assert strategy.name == "restored"
        assert strategy.params == {"key": "val"}
