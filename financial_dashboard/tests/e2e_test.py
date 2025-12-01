import pytest
import sys
import os

# Add the project root to the Python path to allow imports from the parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from _test_playwright import run_test

@pytest.mark.asyncio
async def test_dashboard_flow():
    port = os.environ.get("DASH_PORT", "8050")
    app_url = f"http://127.0.0.1:{port}"
    await run_test(app_url)
