import importlib.util
import json
import traceback
import sys
import os


def main():
    path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '_shared.py')
    spec = importlib.util.spec_from_file_location('Dash._shared', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    print('Loaded SH from', path)
    mt = getattr(mod, 'mt_mod', None)
    print('mt_mod is None?', mt is None)
    if mt is None:
        # when run as a script, return non-zero to indicate missing module
        # but when imported (e.g. by pytest) we must not exit the interpreter
        sys.exit(1)
    print('module repr:', repr(mt))
    if not hasattr(mt, 'analyze_ticker'):
        print('no analyze_ticker')
        sys.exit(0)
    try:
        res = mt.analyze_ticker('AAPL')
        print('analyze_ticker returned type:', type(res))
        try:
            if isinstance(res, dict):
                keys = list(res.keys())[:20]
                print('keys:', keys)
                short = {k: (res[k] if (isinstance(res[k], (str, int, float, bool, list, dict)) and len(str(res[k]))<300) else str(res[k])[:300]) for k in keys}
                print('preview:', json.dumps(short, default=str, indent=2)[:2000])
            else:
                print('result repr:', str(res)[:1000])
        except Exception:
            print('failed to jsonify result')
    except Exception:
        traceback.print_exc()


if __name__ == '__main__':
    main()
