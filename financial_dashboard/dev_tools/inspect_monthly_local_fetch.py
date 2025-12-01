import importlib.util
import os
import sys
mp_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tabs', 'monthly_picks.py'))
spec = importlib.util.spec_from_file_location('monthly_picks', mp_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print('Loaded monthly_picks from', mp_path)
df, p = mod._load_picks_df()
print('picks path:', p)
if df is None:
    print('Failed to load picks:', p)
    sys.exit(1)
print('raw rows:', len(df))
try:
    out = mod._fetch_live_prices_for_df(df.copy(), SH=None)
    if 'price_live' in out.columns:
        print('price_live present; sample:')
        print(out[['ticker','price_live']].head(20).to_string())
    else:
        print('price_live not present in fetched output columns:', out.columns.tolist())
except Exception as e:
    import traceback
    traceback.print_exc()
    print('Error during fetch:', e)
