import os
from financial_dashboard.utils.normalize import normalize_positions_list


def test_normalize_basic_dict_input():
    positions = [
        {'symbol': 'AAPL', 'qty': '10', 'avg_entry_price': '120.5', 'current_price': '130.2'},
        {'ticker': 'MSFT', 'qty': 5, 'avg_entry_price': 200, 'current_price': 210}
    ]

    out = normalize_positions_list(positions)
    assert isinstance(out, list)
    assert len(out) == 2
    assert out[0]['symbol'] == 'AAPL'
    assert out[0]['qty'] == 10.0
    assert out[0]['avg_entry_price'] == 120.5
    assert out[1]['symbol'] == 'MSFT'
    assert out[1]['qty'] == 5.0


def test_normalize_attribute_like_object():
    class P:
        def __init__(self, symbol, qty):
            self.symbol = symbol
            self.qty = qty

    positions = [P('TSLA', '3')]
    out = normalize_positions_list(positions)
    assert len(out) == 1
    assert out[0]['symbol'] == 'TSLA'
    assert out[0]['qty'] == 3.0
