"""
AlphaSim Schema - Response builders for Alpha Vantage-compatible JSON shapes.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd


def build_meta_data(
    information: str,
    symbol: str,
    last_refreshed: Optional[datetime] = None,
    output_size: str = "compact",
    time_zone: str = "UTC",
    extra: Optional[Dict[str, Any]] = None
) -> Dict[str, str]:
    """Build Meta Data block matching Alpha Vantage format."""
    meta = {
        "1. Information": information,
        "2. Symbol": symbol.upper(),
        "3. Last Refreshed": (last_refreshed or datetime.utcnow()).strftime("%Y-%m-%d %H:%M:%S"),
        "4. Output Size": output_size,
        "5. Time Zone": time_zone,
    }
    if extra:
        for i, (k, v) in enumerate(extra.items(), start=6):
            meta[f"{i}. {k}"] = str(v)
    return meta


def build_time_series_daily(
    symbol: str,
    df: pd.DataFrame,
    output_size: str = "compact"
) -> Dict[str, Any]:
    """Build TIME_SERIES_DAILY response from DataFrame with OHLCV columns."""
    if df.empty:
        return {
            "Meta Data": build_meta_data("Daily Prices (AlphaSim)", symbol, output_size=output_size),
            "Time Series (Daily)": {},
            "Note": "No data available for this symbol."
        }
    
    # Ensure we have the right columns
    df = df.copy()
    if 'Date' in df.columns:
        df = df.set_index('Date')
    
    # Limit data based on output_size
    if output_size == "compact":
        df = df.tail(100)
    
    # Build time series dict
    time_series = {}
    for idx, row in df.iterrows():
        date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, 'strftime') else str(idx)
        time_series[date_str] = {
            "1. open": f"{row.get('Open', row.get('open', 0)):.4f}",
            "2. high": f"{row.get('High', row.get('high', 0)):.4f}",
            "3. low": f"{row.get('Low', row.get('low', 0)):.4f}",
            "4. close": f"{row.get('Close', row.get('close', 0)):.4f}",
            "5. volume": str(int(row.get('Volume', row.get('volume', 0)))),
        }
    
    last_date = df.index[-1] if len(df) > 0 else datetime.utcnow()
    
    return {
        "Meta Data": build_meta_data(
            "Daily Prices (AlphaSim)",
            symbol,
            last_refreshed=last_date if hasattr(last_date, 'strftime') else None,
            output_size=output_size
        ),
        "Time Series (Daily)": time_series
    }


def build_sma_response(
    symbol: str,
    sma_series: pd.Series,
    time_period: int,
    series_type: str = "close"
) -> Dict[str, Any]:
    """Build SMA indicator response."""
    if sma_series.empty:
        return {
            "Meta Data": build_meta_data(
                "SMA (AlphaSim)",
                symbol,
                extra={"Indicator": "SMA", "Time Period": time_period, "Series Type": series_type}
            ),
            "Technical Analysis: SMA": {},
            "Note": "No data available for SMA calculation."
        }
    
    tech_analysis = {}
    for idx, val in sma_series.dropna().items():
        date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, 'strftime') else str(idx)
        tech_analysis[date_str] = {"SMA": f"{val:.4f}"}
    
    return {
        "Meta Data": build_meta_data(
            "SMA (AlphaSim)",
            symbol,
            extra={"Indicator": "SMA", "Time Period": time_period, "Series Type": series_type}
        ),
        "Technical Analysis: SMA": tech_analysis
    }


def build_error_response(error_message: str, note: Optional[str] = None) -> Dict[str, str]:
    """Build an error response."""
    resp = {"Error": error_message}
    if note:
        resp["Note"] = note
    return resp


def build_rate_limit_response(retry_after_seconds: int) -> Dict[str, str]:
    """Build 429 rate-limit response."""
    return {
        "Note": f"Thank you for using AlphaSim. The quota for this API key has been exhausted. Please try again in {retry_after_seconds} seconds. If you are an admin, use /admin/reset/{{key}} to reset usage."
    }
