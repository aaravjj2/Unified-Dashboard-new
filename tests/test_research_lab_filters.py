import pandas as pd
import numpy as np
from financial_dashboard.tabs.research_lab.data_loader import apply_market_filters


def make_df():
    return pd.DataFrame([
        {'ticker': 'A', 'market_cap': 1e12, 'pe_ratio': np.nan, 'beta': np.nan, 'sector': 'Technology', 'dividend_yield': 0.0},
        {'ticker': 'B', 'market_cap': 5e11, 'pe_ratio': 50.0, 'beta': 1.5, 'sector': 'Finance', 'dividend_yield': 0.02},
        {'ticker': 'C', 'market_cap': 1e9, 'pe_ratio': np.nan, 'beta': 2.0, 'sector': 'Unknown', 'dividend_yield': 0.0},
    ])


def test_nan_pe_beta_pass():
    df = make_df()
    # wide ranges should allow NaN pe/beta to pass
    out = apply_market_filters(
        df,
        min_market_cap=0,
        max_market_cap=3e12,
        sectors=None,
        min_pe=0,
        max_pe=1000,
        min_beta=0,
        max_beta=10,
    )
    # all three should pass because NaNs are treated permissively
    assert len(out) == 3


def test_pe_filter_excludes():
    df = make_df()
    # narrow P/E range that excludes ticker B (pe=50)
    out = apply_market_filters(
        df,
        min_market_cap=0,
        max_market_cap=3e12,
        sectors=None,
        min_pe=0,
        max_pe=10,
        min_beta=None,
        max_beta=None,
    )
    # B should be excluded, but A and C have NaN pe and should pass
    tickers = set(out['ticker'].tolist())
    assert 'B' not in tickers
    assert 'A' in tickers and 'C' in tickers
