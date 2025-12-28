import pytest
from unittest.mock import patch
from financial_dashboard.services.picks import generate_stock_picks, execute_picks


def test_generate_stock_picks_basic():
    picks = generate_stock_picks(n=4)
    assert isinstance(picks, list)
    assert len(picks) == 4
    assert all('ticker' in p and 'direction' in p for p in picks)


def test_execute_picks_dry_run(monkeypatch):
    picks = [{'ticker': 'AAPL', 'direction': 'LONG'}, {'ticker': 'TSLA', 'direction': 'SHORT'}]

    class FakeExecutor:
        def place_market_order(self, ticker, qty, side, dry_run=True):
            return {'ticker': ticker, 'qty': qty, 'side': side, 'dry_run': dry_run}

    # Monkeypatch the real executor used in picks.execute_picks
    from financial_dashboard.utils import execution as exec_mod
    monkeypatch.setattr(exec_mod, 'AlpacaExecutor', lambda *a, **k: FakeExecutor())

    res = execute_picks(picks, allocation_per_pick=1000, dry_run=True)
    assert len(res) == 2
    for r in res:
        assert r['order']['dry_run'] is True
        assert 'ticker' in r['order']


def test_execute_picks_with_orders(monkeypatch):
    picks = [{'ticker': 'AAPL', 'direction': 'LONG'}]

    # Mock get_price_single so qty computed
    from financial_dashboard.utils import price_fetch as pf_mod
    monkeypatch.setattr(pf_mod, 'get_price_single', lambda t: {'last_price': 100.0})

    class FakeExecutor:
        def place_market_order(self, ticker, qty, side, dry_run=False):
            return {'ticker': ticker, 'qty': qty, 'side': side, 'dry_run': dry_run, 'order_id': 'ord_123'}

    from financial_dashboard.utils import execution as exec_mod
    monkeypatch.setattr(exec_mod, 'AlpacaExecutor', lambda *a, **k: FakeExecutor())

    res = execute_picks(picks, allocation_per_pick=500, dry_run=False)
    assert res[0]['order']['dry_run'] is False
    assert res[0]['order']['order_id'] == 'ord_123'
