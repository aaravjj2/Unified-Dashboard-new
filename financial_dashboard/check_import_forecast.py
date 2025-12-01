import traceback
print('PYTHON', __import__('sys').executable)
try:
    import _shared as SH
    print('Imported Dash._shared OK')
    print('SH attributes:', [a for a in dir(SH) if not a.startswith('_')][:50])
    print('mt_mod present:', hasattr(SH, 'mt_mod'))
    print('start_background_job present:', hasattr(SH, 'start_background_job'))
except Exception as e:
    print('Failed importing Dash._shared:', e)
    traceback.print_exc()

try:
    from tabs import market_forecast as mf
    print('Imported Dash.tabs.market_forecast OK')
    print('has layout:', hasattr(mf, 'layout'))
    print('has register_callbacks:', hasattr(mf, 'register_callbacks'))
except Exception as e:
    print('Failed importing Dash.tabs.market_forecast:', e)
    traceback.print_exc()

# Try file-load fallback similar to dashboard
import importlib.util
import os
base = os.path.dirname(__file__)
mf_path = os.path.join(base, 'tabs', 'market_forecast.py')
try:
    spec = importlib.util.spec_from_file_location('Dash.tabs.market_forecast', mf_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    print('File-loaded market_forecast OK, has layout:', hasattr(mod, 'layout'), 'register_callbacks:', hasattr(mod, 'register_callbacks'))
except Exception as e:
    print('File-load failed for market_forecast:', e)
    traceback.print_exc()
