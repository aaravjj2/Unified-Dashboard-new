"""Small helpers for normalizing portfolio position records for the dashboard.

This module is intentionally lightweight so it can be imported in unit tests without
pulling heavy app dependencies.
"""

def normalize_positions_list(positions):
    """Normalize various incoming position schemas to a list of dicts with canonical keys.

    Ensures keys: symbol, qty, avg_entry_price, current_price, cost_basis, market_value, unrealized_pl, unrealized_plpc
    """
    out = []
    for p in (positions or []):
        if not isinstance(p, dict):
            # try attribute access fallback (use getattr with default to avoid AttributeError)
            try:
                p = {k: getattr(p, k, None) for k in ['symbol', 'ticker', 'sym', 'qty', 'avg_entry_price', 'current_price', 'cost_basis', 'market_value', 'unrealized_pl', 'unrealized_plpc']}
            except Exception:
                continue

        symbol = p.get('symbol') or p.get('ticker') or p.get('sym') or ''
        try:
            qty = float(p.get('qty') or 0)
        except Exception:
            qty = 0.0
        def _tof(key):
            try:
                return float(p.get(key) or 0.0)
            except Exception:
                return 0.0

        avg_entry_price = _tof('avg_entry_price')
        current_price = _tof('current_price')
        cost_basis = _tof('cost_basis')
        market_value = _tof('market_value')
        unrealized_pl = _tof('unrealized_pl')
        unrealized_plpc = _tof('unrealized_plpc')

        out.append({
            'symbol': symbol,
            'qty': qty,
            'avg_entry_price': avg_entry_price,
            'current_price': current_price,
            'cost_basis': cost_basis,
            'market_value': market_value,
            'unrealized_pl': unrealized_pl,
            'unrealized_plpc': unrealized_plpc
        })
    return out
