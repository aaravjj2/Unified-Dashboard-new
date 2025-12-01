"""Minimal Alpaca adapter (dry-run safe).

This module does not install the `alpaca-trade-api` package to avoid
mandatory dependencies. If the package is installed, the adapter will use
it; otherwise it will only simulate order submission and log the request.
"""
from typing import Dict, Any
import logging
from .secrets import get_alpaca_credentials

log = logging.getLogger(__name__)


def submit_order(symbol: str, qty: float, side: str = 'buy', type: str = 'market', time_in_force: str = 'day', dry_run: bool = True) -> Dict[str, Any]:
    """Submit an order to Alpaca or simulate it when dry_run=True.

    Returns a dict with the request details and a simulated response.
    """
    key_id, secret, base_url = get_alpaca_credentials()
    payload = {
        'symbol': symbol,
        'qty': qty,
        'side': side,
        'type': type,
        'time_in_force': time_in_force,
    }
    if dry_run or not key_id or not secret:
        log.info('Dry-run order: %s', payload)
        return {'ok': True, 'dry_run': True, 'order': payload}

    # Try to use alpaca-trade-api if available
    try:
        from alpaca_trade_api import REST
        api = REST(key_id, secret, base_url)
        ord = api.submit_order(symbol=symbol, qty=qty, side=side, type=type, time_in_force=time_in_force)
        return {'ok': True, 'dry_run': False, 'order_id': getattr(ord, 'id', None), 'raw': ord}
    except Exception as e:
        log.exception('Failed to submit order')
        return {'ok': False, 'error': str(e), 'order': payload}
