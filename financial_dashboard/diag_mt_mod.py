import traceback
from importlib.machinery import SourceFileLoader

import os
proj_root = os.path.abspath(os.path.dirname(__file__))
SH = SourceFileLoader('Dash._shared', os.path.join(proj_root, '_shared.py')).load_module()
print('SH loaded. mt_mod is None?' , SH.mt_mod is None)
if SH.mt_mod is not None:
    print('mt_mod repr:', repr(SH.mt_mod))
    print('attrs:', [a for a in dir(SH.mt_mod) if not a.startswith('_')][:80])
else:
    print('\nAttempting to load Gradio/market_trends.py directly to capture error:')
    import importlib.util
    import os
    path = os.path.join(os.path.dirname(SH.__file__), '..', 'Gradio', 'market_trends.py')
    path = os.path.abspath(path)
    print('Path:', path)
    try:
        spec = importlib.util.spec_from_file_location('gr_market_trends', path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        print('Direct load succeeded; has run_full_analysis?:', hasattr(mod, 'run_full_analysis'))
    except Exception:
        print('Direct import failed with:')
        traceback.print_exc()

print('\nSH load printed messages (if any) may be in the Dash server console logs.')
