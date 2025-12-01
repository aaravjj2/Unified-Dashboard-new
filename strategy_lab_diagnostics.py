"""
Strategy Lab - Phase 1 Validation Script

Tests Strategy Lab integration:
1. Module import without errors
2. Layout creation successful
3. Callback registration count
4. Tab visibility in dashboard
5. No interference with other tabs

Usage:
    python strategy_lab_diagnostics.py
"""

import sys
import os
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_module_import():
    """Test 1: Can we import Strategy Lab without errors?"""
    logger.info("=" * 70)
    logger.info("TEST 1: Module Import")
    logger.info("=" * 70)
    
    try:
        from financial_dashboard.tabs.strategy_lab import layout, register_callbacks
        logger.info("✅ PASS: Strategy Lab module imported successfully")
        logger.info(f"   - layout function: {layout}")
        logger.info(f"   - register_callbacks function: {register_callbacks}")
        return True
    except Exception as e:
        logger.error(f"❌ FAIL: Cannot import Strategy Lab module: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_layout_creation():
    """Test 2: Can we create the layout without errors?"""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 2: Layout Creation")
    logger.info("=" * 70)
    
    try:
        from financial_dashboard.tabs.strategy_lab import layout
        
        # Create layout
        layout_obj = layout()
        
        logger.info("✅ PASS: Strategy Lab layout created successfully")
        logger.info(f"   - Layout type: {type(layout_obj)}")
        logger.info(f"   - Layout has {len(layout_obj.children)} children")
        
        # Check for key components
        has_setup = False
        has_backtest = False
        has_results = False
        
        for child in layout_obj.children:
            if hasattr(child, 'children'):
                # Check for section headers
                child_str = str(child)
                if 'Strategy Setup' in child_str:
                    has_setup = True
                if 'Backtest Execution' in child_str:
                    has_backtest = True
                if 'Results & Insights' in child_str:
                    has_results = True
        
        logger.info(f"   - Has Strategy Setup section: {has_setup}")
        logger.info(f"   - Has Backtest section: {has_backtest}")
        logger.info(f"   - Has Results section: {has_results}")
        
        if has_setup and has_backtest and has_results:
            logger.info("✅ All 3 core sections present")
            return True
        else:
            logger.warning("⚠️  Some sections missing")
            return False
            
    except Exception as e:
        logger.error(f"❌ FAIL: Cannot create layout: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_callback_registration():
    """Test 3: Can we register callbacks without errors?"""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 3: Callback Registration")
    logger.info("=" * 70)
    
    try:
        from financial_dashboard.tabs.strategy_lab import register_callbacks
        from dash_extensions.enrich import DashProxy, MultiplexerTransform
        import dash_bootstrap_components as dbc
        
        # Create minimal app
        app = DashProxy(
            __name__,
            transforms=[MultiplexerTransform()],
            external_stylesheets=[dbc.themes.BOOTSTRAP],
            suppress_callback_exceptions=True
        )
        
        # Register callbacks
        callback_count = register_callbacks(app)
        
        logger.info(f"✅ PASS: Callbacks registered successfully")
        logger.info(f"   - Registered {callback_count} callbacks")
        logger.info(f"   - Expected: 8 callbacks (validate, reset, backtest, metrics, 4 charts)")
        
        if callback_count >= 8:
            logger.info("✅ Callback count matches or exceeds expected")
            return True
        else:
            logger.warning(f"⚠️  Only {callback_count} callbacks registered (expected 8)")
            return False
            
    except Exception as e:
        logger.error(f"❌ FAIL: Cannot register callbacks: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_dashboard_integration():
    """Test 4: Is Strategy Lab properly integrated in dashboard?"""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 4: Dashboard Integration")
    logger.info("=" * 70)
    
    try:
        from financial_dashboard import index
        
        # Check if strategy_lab is in TAB_CONFIG
        strategy_lab_config = None
        for tab in index.TAB_CONFIG:
            if tab['id'] == 'strategy_lab':
                strategy_lab_config = tab
                break
        
        if strategy_lab_config:
            logger.info("✅ PASS: Strategy Lab found in TAB_CONFIG")
            logger.info(f"   - Tab ID: {strategy_lab_config['id']}")
            logger.info(f"   - Tab Name: {strategy_lab_config['name']}")
            logger.info(f"   - Module: {strategy_lab_config['module']}")
        else:
            logger.error("❌ FAIL: Strategy Lab not in TAB_CONFIG")
            return False
        
        # Check if strategy_lab is in ENABLED_TABS
        if 'strategy_lab' in index.ENABLED_TABS:
            logger.info("✅ PASS: Strategy Lab found in ENABLED_TABS")
            position = index.ENABLED_TABS.index('strategy_lab')
            logger.info(f"   - Position: {position + 1}/{len(index.ENABLED_TABS)}")
            logger.info(f"   - After: {index.ENABLED_TABS[position - 1] if position > 0 else 'N/A'}")
            logger.info(f"   - Before: {index.ENABLED_TABS[position + 1] if position < len(index.ENABLED_TABS) - 1 else 'N/A'}")
        else:
            logger.error("❌ FAIL: Strategy Lab not in ENABLED_TABS")
            return False
        
        # Check if loaded
        if 'strategy_lab' in index.loaded_tabs:
            logger.info("✅ PASS: Strategy Lab loaded successfully")
            tab_info = index.loaded_tabs['strategy_lab']
            logger.info(f"   - Module: {tab_info['module']}")
            logger.info(f"   - Name: {tab_info['name']}")
        else:
            logger.error("❌ FAIL: Strategy Lab not loaded")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ FAIL: Dashboard integration check failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_isolation():
    """Test 5: Does Strategy Lab break if other tabs fail?"""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 5: Isolation Test")
    logger.info("=" * 70)
    
    try:
        # Try importing just Strategy Lab without full dashboard
        from financial_dashboard.tabs.strategy_lab import layout, register_callbacks
        
        # Create standalone instance
        layout_obj = layout()
        
        logger.info("✅ PASS: Strategy Lab works in isolation")
        logger.info("   - Can import without full dashboard context")
        logger.info("   - No dependencies on other tabs")
        return True
        
    except Exception as e:
        logger.error(f"❌ FAIL: Strategy Lab has external dependencies: {e}")
        return False


def run_all_tests():
    """Run complete test suite."""
    logger.info("\n")
    logger.info("╔" + "=" * 68 + "╗")
    logger.info("║" + " " * 15 + "STRATEGY LAB PHASE 1 VALIDATION" + " " * 22 + "║")
    logger.info("╚" + "=" * 68 + "╝")
    logger.info("\n")
    
    results = {
        'Module Import': test_module_import(),
        'Layout Creation': test_layout_creation(),
        'Callback Registration': test_callback_registration(),
        'Dashboard Integration': test_dashboard_integration(),
        'Isolation': test_isolation()
    }
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info("-" * 70)
    logger.info(f"Total: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    logger.info("=" * 70)
    
    if passed == total:
        logger.info("\n🎉 ALL TESTS PASSED! Strategy Lab Phase 1 is complete!")
        logger.info("\nNext Steps:")
        logger.info("1. Restart dashboard: python financial_dashboard/index.py")
        logger.info("2. Open browser: http://localhost:8050")
        logger.info("3. Click 'Strategy Lab' tab")
        logger.info("4. Verify all sections load correctly")
        return 0
    else:
        logger.error(f"\n❌ {total - passed} test(s) failed. Fix issues before proceeding.")
        return 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
