"""
MISSION A3 ENV HOTFIX - Pytest Configuration
Configures test environment with proper PYTHONPATH and auto-loads environment.
"""
import sys
import os
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Add financial_dashboard to path
sys.path.insert(0, str(project_root / 'financial_dashboard'))

import pytest


@pytest.fixture(scope="session", autouse=True)
def load_environment_for_tests():
    """
    Auto-load environment variables before running any tests.
    This ensures normalization happens before tests check for keys.
    """
    try:
        # Import from utils since we added it to path
        from utils.load_env import load_environment
        result = load_environment(raise_on_missing=False)
        print(f"\n[conftest] Environment loaded: {len(result['present'])} keys present")
        if result['missing']:
            print(f"[conftest] Missing keys: {result['missing']}")
    except ImportError as e:
        print(f"\n[conftest] Could not load environment (RED phase expected): {e}")
    except Exception as e:
        print(f"\n[conftest] Environment loading error: {e}")
