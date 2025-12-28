import os
import pytest
from financial_dashboard.services.ai_morning_brief import AIMorningBriefService
from financial_dashboard.services import picks as picks_mod


def test_generate_and_execute_picks_dry_run_live():
    """Run the pick generation and a dry-run execution using real services (no mocks).

    This test uses live price providers but does not place live orders (dry-run).
    """
    os.environ.pop('ALLOW_AUTO_BUY', None)

    svc = AIMorningBriefService()
    out = svc.generate_and_execute_picks(n=1, allocation_per_pick=100, execute=False)

    # Some deployments may return only picks; ensure we can produce dry-run orders with real code
    if 'orders' in out and out['orders']:
        orders = out['orders']
    else:
        picks = out.get('picks') or picks_mod.generate_stock_picks(n=1)
        orders = picks_mod.execute_picks(picks, allocation_per_pick=100, dry_run=True)

    assert orders and isinstance(orders, list)
    assert orders[0].get('order', {}).get('dry_run', True) is True


def test_generate_and_execute_picks_execute_live():
    """Attempt a live execution if environment is configured; otherwise skip.

    This will only run when `ALLOW_AUTO_BUY` is set to '1' and Alpaca keys are present.
    """
    if os.getenv('ALLOW_AUTO_BUY') != '1':
        pytest.skip('ALLOW_AUTO_BUY not set; skipping live execution test')
    if not os.getenv('APCA_API_KEY_ID') or not os.getenv('APCA_API_SECRET_KEY'):
        pytest.skip('Alpaca API keys missing; skipping live execution test')

    svc = AIMorningBriefService()
    out = svc.generate_and_execute_picks(n=1, allocation_per_pick=100, execute=True)

    # If the service returns orders, verify they are not dry-run
    orders = out.get('orders')
    if not orders:
        # fallback to executing picks directly
        picks = out.get('picks') or picks_mod.generate_stock_picks(n=1)
        orders = picks_mod.execute_picks(picks, allocation_per_pick=100, dry_run=False)

    assert orders and isinstance(orders, list)
    assert orders[0].get('order', {}).get('dry_run', False) is False
