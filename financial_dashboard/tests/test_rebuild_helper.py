import importlib.util, sys, os

# load the rebuild module directly
path = os.path.join(os.path.dirname(__file__), '..', 'tabs', 'market_trends_rebuild.py')
spec = importlib.util.spec_from_file_location('mtr_rebuild_test', path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Create a fake market_trends_dash with run_full_analysis stub
class FakeMT:
    @staticmethod
    def run_full_analysis(tickers, period='1y', **kwargs):
        # return a tiny deterministic result
        detailed = []
        for i, t in enumerate(tickers):
            detailed.append({'ticker': t, 'score': 100 - i, 'price': 100.0 + i})
        return {'ok': True, 'detailed': detailed, 'tidy': detailed, 'brief_text': 'fake brief', 'prices': {t: [] for t in tickers}}

sys.modules['market_trends_dash'] = FakeMT


def test_run_analysis_helper():
    out = mod.run_analysis_for_test('AAPL,MSFT', period_value='1y', analysis_opts=['options'])
    # out should be a 4-tuple where first entry is a Dash component container
    assert isinstance(out, tuple) and len(out) == 3 or len(out) == 4
    # ensure the sanitized store contains 'detailed'
    store = out[1]
    assert store is not None and 'detailed' in store
