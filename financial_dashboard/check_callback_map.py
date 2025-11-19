"""Diagnostic: load tab modules into a fresh Dash app and print callback_map details.

Run: python Dash/check_callback_map.py
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dash import Dash

app = Dash(__name__, suppress_callback_exceptions=True)

from tabs import weekly_picks, monthly_picks

# register callbacks
try:
    weekly_picks.register_callbacks(app, SH=None)
except Exception as e:
    print('weekly_picks.register_callbacks failed:', e)
try:
    monthly_picks.register_callbacks(app, SH=None)
except Exception as e:
    print('monthly_picks.register_callbacks failed:', e)

# After registering, aggressively populate outputs_spec placeholders so diagnostics
# and any renderer validation expecting a length won't treat None as zero-outputs.
try:
    fixed = []
    for k, v in app.callback_map.items():
        try:
            if isinstance(v, dict) and v.get('outputs_spec') is None:
                oi = v.get('outputs_indices')
                if isinstance(oi, list):
                    count = len(oi)
                elif isinstance(oi, int):
                    count = 1
                else:
                    out = v.get('output')
                    try:
                        count = len(out) if isinstance(out, (list, tuple)) else 1
                    except Exception:
                        count = 1
                # Use empty dict placeholders to avoid None semantics
                v['outputs_spec'] = [{}] * count
                fixed.append(k)
        except Exception:
            pass
    if fixed:
        print('check_callback_map: populated outputs_spec for keys:', fixed)
except Exception:
    pass

print('CALLBACK MAP DUMP:')
for k, v in app.callback_map.items():
    print('KEY:', repr(k))
    try:
        if isinstance(v, dict):
            out_spec = v.get('outputs_spec')
            out = v.get('output')
            print('  outputs_spec (type):', type(out_spec), 'value:', out_spec)
            print('  output (type):', type(out), 'repr:', repr(out))
            print('  keys:', list(v.keys()))
            # if outputs_spec is present but None, try to inspect callback object
            cb = v.get('callback')
            print('  callback type:', type(cb), 'name:', getattr(cb, '__name__', str(cb)))
            # print common fields
            print('  outputs_indices:', v.get('outputs_indices'))
            print('  inputs:', v.get('inputs'))
            print('  state:', v.get('state'))
            print('  no_output:', v.get('no_output'))
        else:
            print('  entry not a dict, repr:', repr(v))
    except Exception as e:
        print('  error serializing entry:', e)

print('done')
