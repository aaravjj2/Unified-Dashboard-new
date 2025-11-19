"""
Portfolio Tab Smoke Tests

Validates that the Portfolio tab module loads correctly and
has the required structure.
"""

import pytest


class TestPortfolioTabSmoke:
    """Smoke tests for Portfolio tab structure"""
    
    def test_portfolio_tab_imports(self):
        """Test that portfolio_tab module can be imported"""
        from financial_dashboard.tabs import portfolio_tab
        assert portfolio_tab is not None
    
    def test_create_layout_function_exists(self):
        """Test that create_layout function exists"""
        from financial_dashboard.tabs import portfolio_tab
        assert hasattr(portfolio_tab, 'create_layout')
        assert callable(portfolio_tab.create_layout)
    
    def test_layout_returns_tab(self):
        """Test that create_layout returns a Dash Tab component"""
        from financial_dashboard.tabs import portfolio_tab
        import dash_bootstrap_components as dbc
        
        layout = portfolio_tab.create_layout()
        assert isinstance(layout, dbc.Tab)
    
    def test_layout_has_required_pa_components(self):
        """Test that layout contains required pa-* component IDs"""
        from financial_dashboard.tabs import portfolio_tab
        
        layout = portfolio_tab.create_layout()
        layout_str = str(layout)
        
        required_ids = [
            'pa-total-return',
            'pa-sharpe',
            'pa-drawdown',
            'pa-calc-btn',
            'pa-performance-chart',
            'pa-risk-chart'
        ]
        
        for component_id in required_ids:
            assert component_id in layout_str, \
                f"Required component '{component_id}' not found in layout"
    
    def test_register_callbacks_exists(self):
        """Test that register_callbacks function exists"""
        from financial_dashboard.tabs import portfolio_tab
        assert hasattr(portfolio_tab, 'register_callbacks')
        assert callable(portfolio_tab.register_callbacks)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
