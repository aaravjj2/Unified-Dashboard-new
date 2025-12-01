import pytest
import math


def test_render_table_from_records_handles_nans_and_ids():
    """Call the _render_table_from_records function with synthetic data containing NaN/None and check outputs."""
    import tabs.market_trends as mt

    # Synthetic records with numeric NaN and None text
    records = [
        {'symbol': 'AAPL', 'last_price': 150.25, 'change': None, 'volume': 100000},
        {'symbol': 'MSFT', 'last_price': None, 'change': -1.23, 'volume': float('nan')},
        {'symbol': None, 'last_price': 250.0, 'change': 0.5, 'volume': 50000},
    ]

    container, table = mt._render_table_from_records(records)

    # Container should have the wrapper id
    assert hasattr(container, 'id') and container.id == 'trends-results-table-container'

    # DataTable should have id 'results-table-client'
    assert hasattr(table, 'id') and table.id == 'results-table-client'

    # Ensure data passed to table is cleaned (NaN replaced)
    data = table.data
    assert isinstance(data, list) and len(data) == 3

    # Check replacements: None or nan in text fields become 'N/A' and numeric NaN becomes 0
    # Row 1: change was None -> became 'N/A' or similar
    assert data[0]['change'] != None

    # Row 2: last_price was None -> should not be None; volume was nan -> should be 0
    assert data[1]['last_price'] != None
    # volume nan replaced
    assert data[1]['volume'] == 0 or (isinstance(data[1]['volume'], (int, float)) and not math.isnan(data[1]['volume']))

    # Row 3: symbol None replaced
    assert data[2]['symbol'] is not None
