import os
import pytest

from financial_dashboard.services.ai_morning_brief import AIMorningBriefService


@pytest.mark.skipif(not os.getenv('FINNHUB_API_KEY'), reason="Finnhub key not configured")
def test_live_morning_brief_generation():
    svc = AIMorningBriefService()
    brief = svc.generate_full_brief(watchlist=['AAPL', 'SPY'])

    # Market overview should contain SPY and QQQ keys (at least SPY present)
    overview_section = next((s for s in brief['sections'] if s['category'] == 'market'), None)
    assert overview_section is not None
    overview = overview_section['content']
    assert 'SPY' in overview and (overview['SPY'].get('price') is not None or 'error' not in overview['SPY'])

    # Key events (news) should be non-empty if Finnhub returns items
    exec_section = next((s for s in brief['sections'] if s['category'] == 'summary'), None)
    assert exec_section is not None
    key_events = exec_section['content'].get('key_events', [])
    # We accept empty news but prefer at least one event
    assert isinstance(key_events, list)
