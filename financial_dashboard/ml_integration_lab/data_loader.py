"""
ML Integration Lab - Data loader stubs

This module provides lightweight stub functions to load or synthesize the
data shapes expected by the ML lab. The functions avoid heavy network calls
and return None or small sample DataFrames by default.

Design contract (module-level):
- All functions return serializable objects (dicts, lists, CSV paths) or
  pandas DataFrames when pandas is available. They must NOT contact live
  APIs.
"""
from typing import Optional

try:
    import pandas as pd
    import numpy as np
except Exception:
    pd = None  # keep module import-safe when pandas is not installed
    np = None


def load_historical_prices(path: Optional[str] = None):
    """Load historical prices (CSV) or return None/sample when not available.

    Args:
        path: Optional path to CSV. If None, returns a small sample DataFrame or None.
    """
    if path is None:
        if pd is None:
            return None
        dates = pd.date_range(end=pd.Timestamp.today(), periods=10, freq="D")
        df = pd.DataFrame({"AAPL": np.linspace(100, 110, len(dates))}, index=dates)
        return df
    else:
        if pd is None:
            raise RuntimeError("pandas required to read CSV")
        return pd.read_csv(path, index_col=0, parse_dates=True)


def load_factor_data(path: Optional[str] = None):
    """Load factor time series (CSV) or return small sample.

    Expected columns: ['date', 'market', 'size', 'value', 'momentum'] or similar.
    """
    if path is None:
        if pd is None:
            return None
        dates = pd.date_range(end=pd.Timestamp.today(), periods=10, freq="D")
        arr = np.random.normal(0, 0.001, size=(len(dates), 4))
        df = pd.DataFrame(arr, index=dates, columns=["market", "size", "value", "momentum"])
        return df
    else:
        if pd is None:
            raise RuntimeError("pandas required to read CSV")
        return pd.read_csv(path, index_col=0, parse_dates=True)


def load_portfolio_holdings(path: Optional[str] = None):
    """Load portfolio holdings or return example dictionary.

    Returns a list/dict of {ticker: weight}.
    """
    if path is None:
        return {"AAPL": 0.1, "MSFT": 0.1, "SPY": 0.8}
    else:
        import json
        with open(path, "r") as f:
            return json.load(f)
