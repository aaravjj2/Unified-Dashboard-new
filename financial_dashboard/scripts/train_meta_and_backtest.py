#!/usr/bin/env python3
"""Train a Ridge stacker from OOF predictions, score snapshots, and run a simple walk-forward backtest.

Writes:
- models/STACKER_FOLDER/stacker_ridge_{YYYYMMDD}.joblib
- models/STACKER_FOLDER/scored_full_{YYYYMMDD}.csv  (single `date` column)
- models/STACKER_FOLDER/picks_{YYYYMMDD}.csv
- models/STACKER_FOLDER/backtest_report_{YYYYMMDD}.csv

Usage:
  python3 scripts/train_meta_and_backtest.py --models-dir models/weekly_run_retrain --features data/snapshots_all.parquet --target ret_1m --top-k 20
"""
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
from sklearn.linear_model import RidgeCV


def load_oof(oof_path):
    df = pd.read_csv(oof_path, parse_dates=['date'] if 'date' in pd.read_csv(oof_path, nrows=0).columns else None)
    # normalize column names
    df.columns = [c.strip() for c in df.columns]
    return df


def build_features_from_snapshots(snapshots_path):
    # snapshots_all.parquet expected to contain date and ticker
    df = pd.read_parquet(snapshots_path)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    return df


def train_stacker(oof_df, features_df, target):
    # oof_df expected: ticker, date, oof_pred (and possibly model-specific columns)
    # features_df expected: includes target column
    df = oof_df.copy()
    # ensure date exists
    if 'date' not in df.columns:
        raise SystemExit('OOF dataframe missing date column')
    # merge realized target
    merged = df.merge(features_df[['ticker','date',target]], on=['ticker','date'], how='left')
    merged = merged.dropna(subset=[target])
    X = merged[[c for c in merged.columns if c.startswith('oof') or c == 'oof_pred' or c.endswith('_pred')]].fillna(0.0)
    y = merged[target].values
    if X.shape[0] < 10:
        raise SystemExit('Not enough rows to train stacker')
    # simple RidgeCV
    alphas = [0.1,1.0,10.0]
    model = RidgeCV(alphas=alphas, scoring='neg_mean_squared_error', cv=3)
    model.fit(X, y)
    return model, X.columns.tolist()


def score_all(model, oof_df, features_df, feature_cols):
    # produce scored frame by merging oof predictions onto features snapshots
    # prefer oof_df to provide per-(ticker,date) base preds; if base preds missing, use available features
    scored = features_df.copy()
    # ensure date col
    if 'date' in scored.columns:
        scored['date'] = pd.to_datetime(scored['date'])
    # pivot oof preds if necessary: if oof contains multiple columns per model, keep them
    o = oof_df.copy()
    # rename generic column names to be safe
    if 'oof_pred' in o.columns:
        # keep as-is
        pass
    # merge on ticker+date; if o has only ticker (no date), perform left-join on ticker and keep snapshot date
    if 'date' in o.columns:
        scored = scored.merge(o, on=['ticker','date'], how='left')
    else:
        # When OOF preds lack a date column, merge all available OOF columns on `ticker`.
        # Previous code accidentally dropped non-ticker columns which left only the
        # `ticker` column and resulted in no `oof_pred` being merged (causing a
        # constant stack_pred equal to the intercept). Merge the full oof frame.
        scored = scored.merge(o, on='ticker', how='left')

    # determine stacker input columns
    # Prefer using the original feature names the model was trained with
    stacker_cols = None
    try:
        trained_cols = list(model.feature_names_in_)
    except Exception:
        trained_cols = None

    if trained_cols:
        # build DataFrame with columns in trained order; fill missing with zeros
        import numpy as _np
        available = [c for c in trained_cols if c in scored.columns]
        if available:
            X = scored[available].fillna(0.0).copy()
            # add missing trained cols with zeros
            for c in trained_cols:
                if c not in X.columns:
                    X[c] = 0.0
            # ensure column order matches trained_cols
            X = X[trained_cols]
        else:
            # no overlap — pass zero array with correct shape
            X = _np.zeros((len(scored), len(trained_cols)))
        try:
            preds = model.predict(X)
        except Exception:
            # final fallback: try predict on oof_pred or on zero array
            if 'oof_pred' in scored.columns:
                preds = model.predict(scored[['oof_pred']].fillna(0.0))
            else:
                preds = model.predict(_np.zeros((len(scored), 1)))
        scored['stack_pred'] = preds
    else:
        # older fallback behavior: infer stacker cols from features/columns
        stacker_cols = [c for c in scored.columns if c in feature_cols or c in ('oof_pred',) or c.endswith('_pred')]
        if not stacker_cols:
            # try to infer columns starting with 'oof' or 'pred'
            stacker_cols = [c for c in scored.columns if c.startswith('oof') or c.endswith('_pred')]
        # fill NaNs
        if stacker_cols:
            scored[stacker_cols] = scored[stacker_cols].fillna(0.0)
            scored['stack_pred'] = model.predict(scored[stacker_cols])
        else:
            # last-resort: if 'oof_pred' exists, use it; else zero
            if 'oof_pred' in scored.columns:
                scored['stack_pred'] = scored['oof_pred'].fillna(0.0)
            else:
                scored['stack_pred'] = 0.0
    return scored


def pick_topk(scored_df, date_col, top_k):
    # for the latest date available, pick top_k by stack_pred
    latest = scored_df[scored_df[date_col] == scored_df[date_col].max()].copy()
    top = latest.sort_values('stack_pred', ascending=False).head(top_k)
    return top


def walk_forward_backtest(scored_df, date_col, target_col, top_k):
    # naive backtest: for each date, take top_k by stack_pred and compute mean realized target next period
    df = scored_df.copy()
    if date_col not in df.columns:
        raise SystemExit('Date column missing in scored dataframe')
    dates = sorted(df[date_col].dropna().unique())
    rows = []
    for d in dates:
        sub = df[df[date_col] == d]
        if sub.empty:
            continue
        top = sub.sort_values('stack_pred', ascending=False).head(top_k)
        # realized return is target_col in the snapshot (assumes target is realized for that date in snapshots)
        if target_col not in top.columns:
            continue
        mean_ret = top[target_col].mean()
        rows.append({'date': pd.to_datetime(d), 'mean_ret': mean_ret, 'n': len(top)})
    res = pd.DataFrame(rows)
    if res.empty:
        return res
    res = res.sort_values('date')
    res['cum_ret'] = (1 + res['mean_ret']).cumprod() - 1
    # basic metrics
    total_periods = len(res)
    avg_ret = res['mean_ret'].mean()
    ann_ret = (1 + res['cum_ret'].iloc[-1]) ** (252 / total_periods) - 1 if total_periods > 0 else np.nan
    sharpe = res['mean_ret'].mean() / (res['mean_ret'].std() + 1e-9) * np.sqrt(252) if total_periods > 1 else np.nan
    max_dd = (res['cum_ret'].cummax() - res['cum_ret']).max()
    summary = {'periods': total_periods, 'avg_ret': avg_ret, 'ann_ret': ann_ret, 'sharpe': sharpe, 'max_drawdown': max_dd}
    return res, summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--models-dir', required=True, nargs='+', help='One or more directories containing oof_preds.csv and model artifacts')
    p.add_argument('--features', required=True, help='Path to snapshots_all.parquet')
    p.add_argument('--universe', required=False, help='Optional path to a CSV or TXT file containing tickers (one per line) or a scored CSV with a `ticker` column. If supplied, and the model dir name contains "weekly" (case-insensitive), the pipeline will restrict the candidate universe to these tickers when scoring/picking.')
    p.add_argument('--target', default='ret_1m')
    p.add_argument('--top-k', type=int, default=20)
    p.add_argument('--allow-constant-picks', action='store_true', help='If set, allow writing picks even when stack_pred is effectively constant (for debugging).')
    args = p.parse_args()

    # load snapshots once (shared across model dirs)
    print('Loading snapshots from', args.features)
    feats = pd.read_parquet(args.features)
    if 'date' in feats.columns:
        feats['date'] = pd.to_datetime(feats['date'])

    # load optional universe tickers
    universe_tickers = None
    if getattr(args, 'universe', None):
        u_path = Path(args.universe)
        if u_path.exists():
            try:
                # try read as CSV with ticker column
                tmp = pd.read_csv(u_path, nrows=5)
                if 'ticker' in tmp.columns:
                    uni = pd.read_csv(u_path, usecols=['ticker'])
                    universe_tickers = set(uni['ticker'].astype(str))
                else:
                    # read as one-per-line text file
                    universe_tickers = set(x.strip() for x in open(u_path, 'r') if x.strip())
            except Exception:
                # fallback to plain text read
                try:
                    universe_tickers = set(x.strip() for x in open(u_path, 'r') if x.strip())
                except Exception:
                    universe_tickers = None
        else:
            print('Universe file not found:', u_path)

    # iterate over provided model directories and run the stacker/backtest pipeline per-dir
    for md in args.models_dir:
        models_dir = Path(md)
        print('Processing models-dir:', models_dir)
        if not models_dir.exists():
            print('models-dir not found, skipping:', models_dir)
            continue

        # discover OOF preds: prefer oof_preds.csv, else fall back to common per-model oof files
        oof_path = models_dir / 'oof_preds.csv'
        if oof_path.exists():
            print('Loading OOF preds from', oof_path)
            oof_df = pd.read_csv(oof_path)
        else:
            # attempt to find oof_lightgbm_*.csv and oof_ngboost_*.csv and merge them
            print('oof_preds.csv not found; searching for oof_lightgbm_*.csv / oof_ngboost_*.csv in', models_dir)
            lgbs = sorted(models_dir.glob('oof_lightgbm_*.csv'))
            ngs = sorted(models_dir.glob('oof_ngboost_*.csv'))
            pieces = []
            for pth in lgbs:
                try:
                    d = pd.read_csv(pth)
                    pieces.append(d.rename(columns={c: c.strip() for c in d.columns}))
                except Exception:
                    continue
            for pth in ngs:
                try:
                    d = pd.read_csv(pth)
                    pieces.append(d.rename(columns={c: c.strip() for c in d.columns}))
                except Exception:
                    continue
            if not pieces:
                print('oof_preds.csv not found and no per-model oof files found in', models_dir, '; skipping')
                continue
            # merge pieces on ticker+date where possible
            base = pieces[0]
            for i, other in enumerate(pieces[1:], start=1):
                keys = [k for k in ['ticker', 'date'] if k in base.columns and k in other.columns]
                try:
                    if keys:
                        base = base.merge(other, on=keys, how='outer', suffixes=(None, f'_p{i}'))
                    else:
                        base = pd.concat([base, other.add_suffix(f'_p{i}')], axis=1)
                except Exception:
                    base = pd.concat([base, other.add_suffix(f'_p{i}')], axis=1)
            if 'date' in base.columns:
                try:
                    base['date'] = pd.to_datetime(base['date'])
                except Exception:
                    pass
            pred_cols = [c for c in base.columns if any(k in c.lower() for k in ('oof', 'pred'))]
            num_pred_cols = [c for c in pred_cols if pd.api.types.is_numeric_dtype(base[c])]
            if num_pred_cols:
                base['oof_pred'] = base[num_pred_cols].mean(axis=1)
            oof_df = base

        if 'date' in oof_df.columns:
            oof_df['date'] = pd.to_datetime(oof_df['date'])
        oof_df.columns = [c.strip() for c in oof_df.columns]

        # Train stacker (or load existing) --- if OOF preds do not include date, assume fast-mode and try to load a saved stacker
        model = None
        feat_cols = None
        if 'date' in oof_df.columns:
            print('Training Ridge stacker for', models_dir)
            try:
                model, feat_cols = train_stacker(oof_df, feats, args.target)
            except Exception as e:
                print('Stacker training failed for', models_dir, ':', e)
                continue
        else:
            # look for existing stacker joblib
            joblibs = sorted(models_dir.glob('stacker_ridge_*.joblib'))
            if joblibs:
                import joblib as _jl
                try:
                    model = _jl.load(joblibs[-1])
                    print('Loaded existing stacker from', joblibs[-1])
                    # attempt to get feature names
                    try:
                        feat_cols = list(model.feature_names_in_)
                    except Exception:
                        feat_cols = None
                except Exception as e:
                    print('Failed to load existing stacker:', e)
                    print('Cannot train stacker because OOFs lack date; skipping', models_dir)
                    continue
            else:
                print('No existing stacker found and OOF preds lack date; cannot train. Skipping', models_dir)
                continue
        ts = pd.Timestamp.utcnow().strftime('%Y%m%d')
        out = models_dir
        joblib.dump(model, out / f'stacker_ridge_{ts}.joblib')

        # Score across snapshots and write cleaned scored CSV
        # If an explicit universe of tickers was provided and this is a weekly run, restrict candidates
        feats_for_scoring = feats
        if universe_tickers and 'weekly' in models_dir.name.lower():
            print(f'Applying universe filter for weekly models-dir {models_dir.name}: {len(universe_tickers)} tickers')
            feats_for_scoring = feats[feats['ticker'].astype(str).isin(universe_tickers)].copy()
            if feats_for_scoring.empty:
                print('Warning: universe filter produced empty feature set for', models_dir)
        scored = score_all(model, oof_df, feats_for_scoring, feat_cols)
        # unify date columns: prefer column literally named 'date'; if date_x/date_y exist, choose date_x if equal
        if 'date' not in scored.columns:
            if 'date_x' in scored.columns and 'date_y' in scored.columns:
                # prefer date_x when equal else take date_x
                try:
                    scored['date'] = pd.to_datetime(scored['date_x'].fillna(scored['date_y']))
                except Exception:
                    scored['date'] = pd.to_datetime(scored['date_y'].fillna(scored['date_x']))
            elif 'date_x' in scored.columns:
                scored['date'] = pd.to_datetime(scored['date_x'])
            elif 'date_y' in scored.columns:
                scored['date'] = pd.to_datetime(scored['date_y'])
            else:
                # if no date at all, set to today for scoring snapshot
                scored['date'] = pd.Timestamp.utcnow().normalize()

        # ensure date dtype
        scored['date'] = pd.to_datetime(scored['date'])

        scored_path = out / f'scored_full_{ts}.csv'
        picks_path = out / f'picks_{ts}.csv'
        print('Writing scored CSV:', scored_path)
        scored.to_csv(scored_path, index=False)

        # generate picks for latest date
        print('Selecting top-k picks')
        top = pick_topk(scored, 'date', args.top_k)

        # provenance: add model metadata so dashboard can show which stacker/universe produced picks
        prov = {'model_dir': str(models_dir.name), 'stacker': (out / f'stacker_ridge_{ts}.joblib').name, 'universe': args.universe or '', 'generated_utc': pd.Timestamp.utcnow().isoformat()}
        for k, v in prov.items():
            top[k] = v

        # safety check: if stack_pred has near-zero variance across scored rows, abort unless user overrides
        if 'stack_pred' in scored.columns:
            var = float(scored['stack_pred'].var())
            if var <= 1e-12 and not args.allow_constant_picks:
                print(f'ERROR: stack_pred variance is extremely low ({var}). Refusing to write picks. Use --allow-constant-picks to override.')
                # still write scored CSV for inspection but skip picks
                scored.to_csv(scored_path, index=False)
                print('Wrote scored CSV (no picks).')
                # skip to next model-dir
                continue

        top.to_csv(picks_path, index=False)

        # run naive walk-forward backtest
        print('Running walk-forward backtest')
        try:
            backtest_df, summary = walk_forward_backtest(scored, 'date', args.target, args.top_k)
            report_path = out / f'backtest_report_{ts}.csv'
            backtest_df.to_csv(report_path, index=False)
            # write summary small json-like csv
            summ = pd.DataFrame([summary])
            summ.to_csv(out / f'backtest_summary_{ts}.csv', index=False)
            print('Wrote backtest report and summary')
        except Exception as e:
            print('Backtest failed:', e)

        print('Wrote:', scored_path, picks_path)


if __name__ == '__main__':
    main()
