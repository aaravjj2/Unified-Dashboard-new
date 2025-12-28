import os
import importlib
import sys


def test_serving_client_does_not_import_yfinance(monkeypatch):
    """Ensure ServingClient does not import yfinance during initialization when not allowed.

    We simulate environment where ALLOW_YFINANCE_FALLBACK is not set and then import
    ServingClient. If ServingClient imported yfinance at module import or __init__,
    this test would detect it by ensuring 'yfinance' is not in sys.modules.
    """
    # Ensure env var is not set
    monkeypatch.delenv('ALLOW_YFINANCE_FALLBACK', raising=False)

    # Remove yfinance from sys.modules if present to get a clean slate
    if 'yfinance' in sys.modules:
        del sys.modules['yfinance']

    # Import the module under test
    from financial_dashboard.serving import serving_client

    # Now instantiate ServingClient (should not import yfinance)
    sc = serving_client.ServingClient()

    # Assert yfinance not present unless ALLOW_YFINANCE_FALLBACK set
    assert 'yfinance' not in sys.modules, "ServingClient imported yfinance unexpectedly"
