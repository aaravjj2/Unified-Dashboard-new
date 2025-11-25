import sys
# Ensure the package and its package-relative imports resolve
sys.path.insert(0,'/app/financial_dashboard')
sys.path.insert(0,'/app')
from financial_dashboard.tabs import weekly_picks as WP
import pandas as pd
print('Calling _load_and_enrich_picks()...')
df, err, summary = WP._load_and_enrich_picks()
print('err:', err)
print('summary:', summary)
print('DF columns:', df.columns.tolist())
print(df[['ticker','current_price','week_start_price','profit_loss']].head(10).to_string())
