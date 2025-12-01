"""
Unit tests for PicksFetcher

Tests data loading, price enrichment, fixtures, and provenance tracking.
"""

import pytest
import os
import json
import tempfile
import pandas as pd
from pathlib import Path
from financial_dashboard.utils.picks_fetcher import (
    PicksFetcher,
    create_deterministic_fixture,
    load_and_enrich_picks
)


@pytest.fixture
def temp_csv_file():
    """Create a temporary CSV file with test picks."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
        f.write("Ticker,Company,Rank,Score\n")
        f.write("AAPL,Apple Inc.,1,95\n")
        f.write("MSFT,Microsoft Corp.,2,90\n")
        f.write("GOOGL,Alphabet Inc.,3,85\n")
        temp_path = f.name
    yield temp_path
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def temp_fixture_file():
    """Create a temporary fixture JSON."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        fixture_data = {
            'pick_type': 'weekly',
            'deterministic': True,
            'data': [
                {'Ticker': 'TSLA', 'Company': 'Tesla Inc.', 'Rank': 1, 'Score': 100},
                {'Ticker': 'NVDA', 'Company': 'NVIDIA Corp.', 'Rank': 2, 'Score': 95}
            ]
        }
        json.dump(fixture_data, f)
        temp_path = f.name
    yield temp_path
    if os.path.exists(temp_path):
        os.remove(temp_path)


def test_picks_fetcher_initialization():
    """Test PicksFetcher initializes correctly."""
    fetcher = PicksFetcher()
    assert fetcher.fixture_path is None
    assert fetcher.price_client is None
    
    fetcher_with_fixture = PicksFetcher(fixture_path='/path/to/fixture.json')
    assert fetcher_with_fixture.fixture_path == '/path/to/fixture.json'


def test_load_from_csv(temp_csv_file):
    """Test loading picks from CSV."""
    fetcher = PicksFetcher()
    df = fetcher.load_from_csv(temp_csv_file)
    
    assert len(df) == 3
    assert 'Ticker' in df.columns
    assert 'Company' in df.columns
    assert df.iloc[0]['Ticker'] == 'AAPL'
    
    # Check provenance columns
    assert '_source' in df.columns
    assert '_source_path' in df.columns
    assert '_loaded_at' in df.columns
    assert df.iloc[0]['_source'] == 'csv'


def test_load_from_csv_required_columns(temp_csv_file):
    """Test CSV validation with required columns."""
    fetcher = PicksFetcher()
    
    # Should succeed with valid columns
    df = fetcher.load_from_csv(temp_csv_file, required_columns=['Ticker', 'Company'])
    assert len(df) == 3
    
    # Should raise ValueError for missing columns
    with pytest.raises(ValueError, match="Missing required columns"):
        fetcher.load_from_csv(temp_csv_file, required_columns=['Ticker', 'NonExistent'])


def test_load_from_csv_not_found():
    """Test loading from non-existent CSV."""
    fetcher = PicksFetcher()
    
    with pytest.raises(FileNotFoundError):
        fetcher.load_from_csv('/nonexistent/file.csv')


def test_load_from_fixture(temp_fixture_file):
    """Test loading from deterministic fixture."""
    fetcher = PicksFetcher(fixture_path=temp_fixture_file)
    df = fetcher.load_from_fixture()
    
    assert len(df) == 2
    assert df.iloc[0]['Ticker'] == 'TSLA'
    assert df.iloc[1]['Ticker'] == 'NVDA'
    
    # Check provenance
    assert df.iloc[0]['_source'] == 'fixture'
    assert df.iloc[0]['_source_path'] == temp_fixture_file


def test_load_from_fixture_with_explicit_path(temp_fixture_file):
    """Test loading fixture with explicit path argument."""
    fetcher = PicksFetcher()
    df = fetcher.load_from_fixture(fixture_path=temp_fixture_file)
    
    assert len(df) == 2
    assert df.iloc[0]['Ticker'] == 'TSLA'


def test_enrich_with_prices_deterministic(temp_csv_file, monkeypatch):
    """Test price enrichment in deterministic mode."""
    # Enable deterministic mode
    monkeypatch.setenv('OPTIONS_DETERMINISTIC', '1')
    
    fetcher = PicksFetcher()
    df = fetcher.load_from_csv(temp_csv_file)
    
    enriched = fetcher.enrich_with_prices(df, ticker_column='Ticker', provenance=True)
    
    # Check price columns exist
    assert 'current_price' in enriched.columns
    assert 'price_source' in enriched.columns
    assert 'price_fetched_at' in enriched.columns
    assert 'price_age_seconds' in enriched.columns
    
    # Check prices were added
    assert enriched['current_price'].notna().all()
    assert enriched['price_source'].iloc[0] == 'deterministic_fixture'


def test_enrich_with_prices_empty_dataframe():
    """Test enrichment handles empty DataFrame gracefully."""
    fetcher = PicksFetcher()
    df = pd.DataFrame()
    
    enriched = fetcher.enrich_with_prices(df)
    assert enriched.empty


def test_enrich_with_prices_missing_ticker_column(temp_csv_file):
    """Test enrichment fails gracefully with missing ticker column."""
    fetcher = PicksFetcher()
    df = fetcher.load_from_csv(temp_csv_file)
    
    # Try enriching with wrong column name
    enriched = fetcher.enrich_with_prices(df, ticker_column='NonExistentColumn')
    
    # Should return original DataFrame without price columns
    assert 'current_price' not in enriched.columns or enriched['current_price'].isna().all()


def test_load_picks_auto_mode(temp_csv_file, temp_fixture_file):
    """Test auto-loading picks with fallback."""
    fetcher = PicksFetcher(fixture_path=temp_fixture_file)
    
    # Auto mode should try DB → CSV → fixture
    df = fetcher.load_picks(source_type='auto', csv_path=temp_csv_file)
    
    # Should load from CSV since it exists
    assert not df.empty
    assert df.iloc[0]['_source'] == 'csv'


def test_load_picks_fixture_mode(temp_fixture_file, monkeypatch):
    """Test explicit fixture loading."""
    monkeypatch.setenv('OPTIONS_DETERMINISTIC', '1')
    
    fetcher = PicksFetcher(fixture_path=temp_fixture_file)
    df = fetcher.load_picks(source_type='fixture')
    
    assert not df.empty
    assert df.iloc[0]['_source'] == 'fixture'


def test_create_deterministic_fixture():
    """Test creating deterministic fixtures."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fixture_path = os.path.join(tmpdir, 'test_fixture.json')
        
        created_path = create_deterministic_fixture(
            output_path=fixture_path,
            pick_type='weekly',
            num_picks=5
        )
        
        assert os.path.exists(created_path)
        
        # Verify fixture content
        with open(created_path, 'r') as f:
            fixture = json.load(f)
        
        assert fixture['pick_type'] == 'weekly'
        assert fixture['deterministic'] is True
        assert len(fixture['data']) == 5
        assert fixture['data'][0]['Ticker'] == 'AAPL'


def test_load_and_enrich_picks_convenience(temp_csv_file, monkeypatch):
    """Test convenience function for loading and enriching."""
    monkeypatch.setenv('OPTIONS_DETERMINISTIC', '1')
    
    df = load_and_enrich_picks(
        pick_type='weekly',
        csv_path=temp_csv_file,
        enrich_prices=True
    )
    
    assert not df.empty
    assert 'current_price' in df.columns
    assert 'Ticker' in df.columns


def test_load_and_enrich_picks_no_enrichment(temp_csv_file):
    """Test convenience function without price enrichment."""
    df = load_and_enrich_picks(
        pick_type='weekly',
        csv_path=temp_csv_file,
        enrich_prices=False
    )
    
    assert not df.empty
    assert 'current_price' not in df.columns


def test_fetcher_thread_safety(temp_csv_file):
    """Test PicksFetcher thread safety."""
    import threading
    
    fetcher = PicksFetcher()
    results = []
    errors = []
    
    def load_thread():
        try:
            df = fetcher.load_from_csv(temp_csv_file)
            results.append(len(df))
        except Exception as e:
            errors.append(e)
    
    # Run 10 concurrent loads
    threads = [threading.Thread(target=load_thread) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    assert len(errors) == 0
    assert all(r == 3 for r in results)  # All should load 3 rows


def test_price_provenance_tracking(temp_csv_file, monkeypatch):
    """Test that price provenance is tracked correctly."""
    monkeypatch.setenv('OPTIONS_DETERMINISTIC', '1')
    
    fetcher = PicksFetcher()
    df = fetcher.load_from_csv(temp_csv_file)
    enriched = fetcher.enrich_with_prices(df, provenance=True)
    
    # Check all provenance fields
    for _, row in enriched.iterrows():
        assert pd.notna(row['current_price'])
        assert row['price_source'] == 'deterministic_fixture'
        assert pd.notna(row['price_fetched_at'])
        assert row['price_age_seconds'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
