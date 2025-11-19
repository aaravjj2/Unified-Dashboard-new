import json
import traceback
from Dash import _shared as SH
print('SH loaded, mt_mod is None?', SH.mt_mod is None)
mt = SH.mt_mod
if mt is None:
    print('mt_mod is None; exiting')
else:
    print('mt_mod repr:', repr(mt))
    print('has analyze_ticker?', hasattr(mt, 'analyze_ticker'))
    if hasattr(mt, 'analyze_ticker'):
        try:
            res = mt.analyze_ticker('AAPL')
            print('analyze_ticker returned type:', type(res))
            try:
                print('sample keys:', list(res.keys())[:10])
            except Exception:
                pass
            # print small JSON preview
            try:
                print('preview:', json.dumps(res if isinstance(res, dict) else str(res))[:800])
            except Exception:
                print('preview str:', str(res)[:800])
        except Exception:
            print('analyze_ticker raised:')
            traceback.print_exc()
    else:
        print('No analyze_ticker in mt_mod')
