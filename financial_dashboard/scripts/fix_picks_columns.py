from pathlib import Path
import json
import pandas as pd
BASE = Path(__file__).resolve().parents[1] / 'models' / 'full_run'
# find latest explain json and scored csv
explain_files = sorted(BASE.glob('picks_explain_*.json'))
scored_files = sorted(BASE.glob('scored_full_*.csv'))
if not explain_files or not scored_files:
    print('missing files')
    raise SystemExit(1)
ex = json.loads(explain_files[-1].read_text())
scored = pd.read_csv(scored_files[-1])
# build picks df from scored top_k where ticker in explain items
items = ex.get('items', [])
if not items:
    print('no items in explain')
    raise SystemExit(1)
p_df = pd.DataFrame(items)
# ensure numeric cols
for c in ['lgb_pred','ng_pred','score','pred_sigma','pred_lower_95','pred_upper_95','position_size','position_size_dollars','expected_slippage_pct','model_confidence']:
    if c in p_df.columns:
        p_df[c] = pd.to_numeric(p_df[c], errors='coerce')
# try merge price fields from scored
if 'ticker' in scored.columns:
    price_cols = [c for c in ['open','close','last_price','price_start_of_month','daily_change','avg_dollar_vol'] if c in scored.columns]
    if price_cols:
        scored_small = scored[['ticker'] + price_cols].drop_duplicates('ticker')
        p_df = p_df.merge(scored_small, on='ticker', how='left')
# write picks file
now = explain_files[-1].stem.split('_')[-1]
picks_path = BASE / f'picks_{now}.csv'
p_df.to_csv(picks_path, index=False)
print('Wrote', picks_path)
print('Columns:', p_df.columns.tolist())
print(p_df.head().to_csv(index=False))
