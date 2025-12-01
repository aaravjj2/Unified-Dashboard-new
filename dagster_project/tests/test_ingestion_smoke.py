"""Smoke tests for the ingestion pipeline (unit-level)

These tests should be runnable without connecting to external Postgres by mocking
resources or using an in-memory SQLite engine.
"""
import pytest
import pandas as pd


def test_clean_picks_basic():
    from dagster_project.assets.transforms import clean_picks_df
    raw = pd.DataFrame({
        'ticker': ['AAPL', None, 'TSLA'],
        'date': ['2021-01-01', '2021-01-02', None],
        'price': ['150', 'N/A', '700']
    })
    cleaned = clean_picks_df(raw)
    assert 'AAPL' in cleaned['ticker'].values
    assert 'TSLA' not in cleaned['ticker'].values or cleaned['date'].notnull().any()
