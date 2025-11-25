import importlib.util
import os
import sys
# load module from file path to avoid package import issues
mp_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tabs', 'monthly_picks.py'))
spec = importlib.util.spec_from_file_location('monthly_picks', mp_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print('Loaded monthly_picks from', mp_path)
# Call loader
df, p = mod._load_picks_df()
print('picks path:', p)
if df is None:
    print('Failed to load picks:', p)
    sys.exit(0)
print('raw df rows:', len(df))
# Prepare display df
try:
    d = mod._prepare_display_df(df)
    print('prepared columns:', d.columns.tolist())
    print('sample rows:')
    print(d.head(10).to_string())
except Exception as e:
    import traceback
    traceback.print_exc()
    print('Error during prepare:', e)
