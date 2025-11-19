"""Regenerate picks and explainability JSON from an existing full_run artifacts folder.

This script discovers model and OOF files in the given full_run folder and calls
src.pipeline.stacker.train_and_predict_stack(...) with top_k=25 to produce
new picks and explain JSON files alongside existing artifacts.

Run from project root (Dash/) inside the project's venv:
    python scripts/regenerate_picks_from_full_run.py
"""
from pathlib import Path
import sys
import argparse
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pipeline.stacker import train_and_predict_stack
from src.pipeline.data import read_table
from src.pipeline.features import build_features_from_prices
try:
    from src.adapters.marketaux import MarketauxClient
except Exception:
    MarketauxClient = None

BASE = Path(__file__).resolve().parents[1] / 'models' / 'full_run'
print('Using full_run dir:', BASE)

# find features file from pipeline_meta if available
meta_path = BASE / 'pipeline_meta_20250914.json'
features_path = None
if meta_path.exists():
    import json
    meta = json.loads(meta_path.read_text())
    # meta may include paths like '../models/full_run/..' or empty values; validate
    fp = meta.get('features_path', '')
    if fp and fp != '.':
        features_path = Path(fp)

if not features_path or not Path(features_path).exists():
    # fallback to default expected features file inside Dash/data
    features_path = Path(__file__).resolve().parents[1] / 'data' / 'features_20250912.csv'

features_path = Path(features_path)

parser = argparse.ArgumentParser()
parser.add_argument('--use-marketaux', action='store_true', help='Enable Marketaux enrichment calls (requires MARKETAUX_API_KEY in env)')
args = parser.parse_args()

print('Features path:', features_path)

# load features to infer the features list
df = read_table(str(features_path))
# heuristic: exclude known non-feature columns
exclude = {'date','ticker','asset','target','ret_1m'}
features = [c for c in df.columns if c not in exclude and df[c].dtype.kind in 'fi']
print('Using', len(features), 'features')

# find model paths
lgb_paths = sorted([str(p) for p in BASE.glob('lightgbm_fold*_20250914.joblib')])
ng_paths = sorted([str(p) for p in BASE.glob('ngboost_fold*_20250914.joblib')])
oof_lgb = str(BASE / 'oof_lightgbm_20250914.csv')
oof_ng = str(BASE / 'oof_ngboost_20250914.csv')

print('Found LGB models:', lgb_paths)
print('Found NG models:', ng_paths)
# ensure we have a snapshot of ~20 tickers to score: if features file has few rows for latest date,
# build a snapshot from prices_{date}.csv by taking the latest available row per ticker
prices_path = Path(__file__).resolve().parents[1] / 'data' / 'prices_20250912.csv'
if prices_path.exists():
    print('Building features snapshot from prices:', prices_path)
    # create features CSV using build_features_from_prices helper and point to that
    try:
        # if an S&P tickers list exists, filter prices to that universe first
        sp_list = Path(__file__).resolve().parents[1] / 'data' / 'sp500_tickers.txt'
        if sp_list.exists():
            txt = sp_list.read_text().strip()
            tickers = [t.strip().upper() for t in txt.replace('\n',',').split(',') if t.strip()]
            print('Using S&P list with', len(tickers), 'tickers')
            import pandas as _pd
            pdf = _pd.read_csv(prices_path, parse_dates=['date'])
            ppdf = pdf[pdf['ticker'].isin(tickers)]
            tmp_prices = Path(__file__).resolve().parents[1] / 'data' / 'prices_sp500_snapshot.csv'
            ppdf.to_csv(tmp_prices, index=False)
            build_features_from_prices(str(tmp_prices), out_dir=str(Path(__file__).resolve().parents[1] / 'data'))
            features_path = Path(__file__).resolve().parents[1] / 'data' / 'features_20250912.csv'
        else:
            build_features_from_prices(str(prices_path), out_dir=str(Path(__file__).resolve().parents[1] / 'data'))
            features_path = Path(__file__).resolve().parents[1] / 'data' / 'features_20250912.csv'
    except Exception:
        pass

stacker_path, picks_path = train_and_predict_stack(str(features_path), lgb_paths, oof_lgb, ng_paths, oof_ng, features, target='ret_1m', out_dir=str(BASE), top_k=20)
# optional Marketaux enrichment (guarded)
if args.use_marketaux and MarketauxClient is not None:
    try:
        api = MarketauxClient.from_env()
        if api:
            print('Marketaux enabled: enriching picks with news sentiment/score')
            # enrichment is non-blocking and best-effort: attach a simple field to picks JSON/csv
            try:
                import pandas as _pd
                picks_df = _pd.read_csv(picks_path)
                picks_df['marketaux_sentiment'] = None
                # call in small batches to avoid rate limits
                for i, row in picks_df.iterrows():
                    try:
                        info = api.get_sentiment_for_ticker(row['ticker'])
                        picks_df.at[i, 'marketaux_sentiment'] = info.get('sentiment') if isinstance(info, dict) else None
                    except Exception:
                        continue
                picks_df.to_csv(picks_path, index=False)
                print('Enriched picks with Marketaux sentiment')
            except Exception:
                print('Marketaux enrichment failed; continuing')
    except Exception:
        print('Marketaux client initialization failed or API key missing')
print('Wrote:', stacker_path, picks_path)

# Post-process: if we created a prices snapshot, merge price fields into scored/picks for live info
tmp_prices = Path(__file__).resolve().parents[1] / 'data' / 'prices_sp500_snapshot.csv'
if tmp_prices.exists():
    import pandas as _pd
    print('Merging price fields from snapshot into scored/picks')
    prices = _pd.read_csv(tmp_prices, parse_dates=['date'])
    latest_date = prices['date'].max()
    # pick last trading day rows
    latest_prices = prices[prices['date'] == latest_date][['ticker','open','close','adj_close']]
    # load scored if exists
    scored_path = Path(BASE) / f'scored_full_{_pd.Timestamp.utcnow().strftime("%Y%m%d")}.csv'
    # try common names first: check existing scored file(s)
    scored_files = list(Path(BASE).glob('scored_full_*.csv'))
    if scored_files:
        scored = _pd.read_csv(scored_files[-1])
        picks = _pd.read_csv(picks_path)
        # merge last price info
        latest_prices = latest_prices.rename(columns={'adj_close':'last_price'})
        scored = scored.merge(latest_prices[['ticker','open','close','last_price']], on='ticker', how='left')
        picks = picks.merge(latest_prices[['ticker','open','close','last_price']], on='ticker', how='left')
        # compute daily_change and price_start_of_month (approx: take first price in same month from prices snapshot)
        prices['month'] = prices['date'].dt.to_period('M')
        month0 = latest_date.to_period('M')
        first_in_month = prices[prices['month'] == month0].groupby('ticker').first().reset_index()[['ticker','adj_close']].rename(columns={'adj_close':'price_start_of_month'})
        scored = scored.merge(first_in_month, on='ticker', how='left')
        picks = picks.merge(first_in_month, on='ticker', how='left')
        scored['daily_change'] = (scored['close'] - scored['open']) / scored['open']
        picks['daily_change'] = (picks['close'] - picks['open']) / picks['open']
        # reorder and save
        scored.to_csv(scored_files[-1].parent / scored_files[-1].name, index=False)
        picks.to_csv(picks_path, index=False)
        print('Updated scored and picks with price fields')
