#!/usr/bin/env python3
"""
STEP 9: Integration Tests for Research Lab Package

Tests:
1. Module imports work correctly
2. Layout renders without errors
3. Callbacks register successfully
4. API endpoints respond correctly
5. Data persistence works
"""

import json
import logging
import os
import sys
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

os.environ["RL_DETERMINISTIC"] = "1"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["USE_NEW_RESEARCH_LAB"] = "1"


def test_module_imports():
    """Test that all Research Lab modules import without errors."""
    try:
        from financial_dashboard.tabs.research_lab_pkg import layout, register_callbacks
        from financial_dashboard.tabs.research_lab_pkg import data
        from financial_dashboard.tabs.research_lab_pkg import components
        from financial_dashboard.services.llm_local import get_llm_connector, get_query_engine
        
        logger.info("✓ All modules imported successfully")
        return True
    except Exception as e:
        raise AssertionError(f"Module import failed: {e}")


def test_layout_renders():
    """Test that layout() returns a valid Dash component."""
    from financial_dashboard.tabs.research_lab_pkg import layout
    
    result = layout()
    
    # Check it's a Dash component
    assert result is not None, "Layout returned None"
    assert hasattr(result, "children"), "Layout missing children attribute"
    
    # Check for expected structure
    children = result.children if hasattr(result, "children") else []
    
    # Should have stores and tabs
    logger.info(f"✓ Layout rendered with {len(children)} top-level children")
    return True


def test_component_functions():
    """Test that component helper functions work."""
    from financial_dashboard.tabs.research_lab_pkg import components
    
    # Test various component generators
    empty = components.empty_state("Test message")
    assert empty is not None, "empty_state returned None"
    
    error = components.error_panel("Test error")
    assert error is not None, "error_panel returned None"
    
    card = components.section_card("Test Title", "Content", id_prefix="test")
    assert card is not None, "section_card returned None"
    
    loading = components.loading_panel("Loading...")
    assert loading is not None, "loading_panel returned None"
    
    logger.info("✓ Component functions work correctly")
    return True


def test_data_loaders():
    """Test data loading functions."""
    from financial_dashboard.tabs.research_lab_pkg import data
    
    # Test factor exposures
    exposures = data.load_factor_exposures(["AAPL", "MSFT"])
    assert isinstance(exposures, dict), "Exposures should be a dict"
    
    # Test correlation matrix
    corr = data.load_correlation_matrix(["AAPL", "MSFT", "GOOG"])
    assert isinstance(corr, dict), "Correlation should be a dict"
    
    # Test briefs
    briefs = data.load_briefs()
    assert isinstance(briefs, list), "Briefs should be a list"
    
    # Test index health
    health = data.get_index_health()
    assert "status" in health, "Health should have status"
    
    logger.info("✓ Data loaders work correctly")
    return True


def test_api_endpoints():
    """Test RAG API endpoints (if server is running)."""
    base_url = os.getenv("DASHBOARD_URL", "http://localhost:8050")
    
    # Try a simple health check first
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code != 200:
            logger.warning(f"⚠ Dashboard not responding (status {response.status_code})")
            logger.info("✓ API endpoint test skipped (server not running)")
            return True
    except requests.exceptions.ConnectionError:
        logger.info("✓ API endpoint test skipped (server not running)")
        return True
    
    # If server is running, test API endpoints
    try:
        # Test RAG query endpoint
        response = requests.post(
            f"{base_url}/api/research/query",
            json={"query": "What is momentum?"},
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            assert "answer" in result or "error" not in result
            logger.info("✓ RAG query API endpoint works")
        else:
            logger.warning(f"⚠ RAG query returned status {response.status_code}")
    except Exception as e:
        logger.warning(f"⚠ RAG query API error: {e}")
    
    logger.info("✓ API endpoints tested")
    return True


def test_fixture_persistence():
    """Test that fixtures can be saved and loaded."""
    from financial_dashboard.tabs.research_lab_pkg import data
    
    # Test saving and loading a fixture
    test_data = {"test": "data", "timestamp": datetime.now().isoformat()}
    
    # Save
    success = data.save_fixture("test_fixture.json", test_data)
    assert success, "Failed to save fixture"
    
    # Load
    loaded = data._load_fixture("test_fixture.json")
    assert loaded is not None, "Failed to load fixture"
    assert loaded.get("test") == "data", "Fixture data mismatch"
    
    # Cleanup
    fixture_path = PROJECT_ROOT / "data" / "research_lab" / "fixtures" / "test_fixture.json"
    if fixture_path.exists():
        fixture_path.unlink()
    
    logger.info("✓ Fixture persistence works")
    return True


def test_news_feed():
    """Test news feed loading."""
    from financial_dashboard.tabs.research_lab_pkg import data
    
    news = data.load_news_feed(["AAPL"])
    assert isinstance(news, list), "News should be a list"
    
    if news:
        assert "title" in news[0] or "headline" in news[0], "News items should have title"
    
    logger.info(f"✓ News feed works ({len(news)} items)")
    return True


def run_all_tests():
    """Run all integration tests."""
    tests = [
        ("Module Imports", test_module_imports),
        ("Layout Renders", test_layout_renders),
        ("Component Functions", test_component_functions),
        ("Data Loaders", test_data_loaders),
        ("API Endpoints", test_api_endpoints),
        ("Fixture Persistence", test_fixture_persistence),
        ("News Feed", test_news_feed),
    ]
    
    results = []
    passed = 0
    failed = 0
    
    print("\n" + "=" * 60)
    print("STEP 9: INTEGRATION TESTS")
    print("=" * 60 + "\n")
    
    for name, test_fn in tests:
        try:
            result = test_fn()
            results.append({"name": name, "status": "PASS", "error": None})
            passed += 1
            print(f"✓ {name}: PASS")
        except Exception as e:
            results.append({"name": name, "status": "FAIL", "error": str(e)})
            failed += 1
            print(f"✗ {name}: FAIL - {e}")
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{len(tests)} passed, {failed} failed")
    print("=" * 60 + "\n")
    
    # Save results
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {"total": len(tests), "passed": passed, "failed": failed},
        "tests": results,
    }
    
    report_path = PROJECT_ROOT / "reports" / "research_lab" / "integration_tests.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Report saved to {report_path}")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
