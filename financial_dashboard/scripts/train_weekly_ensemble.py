"""Trainer scaffold: train LightGBM and NGBoost base models and produce OOF preds for stacking.

Usage (example):
python3 scripts/train_weekly_ensemble.py --features data/weekly_enriched_with_sentiment.parquet --out models/weekly_run

This scaffold focuses on structure: loading features, splitting by date, training base models,
storing models and OOF preds for the stacking layer.
"""
import os
import argparse
import pandas as pd

try:
    import lightgbm as lgb
except Exception:
    lgb = None

try:
    from ngboost import NGBRegressor
except Exception:
    NGBRegressor = None

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit
import joblib


def train_lightgbm(X, y):
    if lgb is None:
        raise RuntimeError('lightgbm not installed')
    params = {'objective': 'regression', 'metric': 'rmse', 'verbosity': -1}
    dtrain = lgb.Dataset(X, y)
    model = lgb.train(params, dtrain, num_boost_round=100)
    return model


def train_ngboost(X, y, n_estimators=200):
    if NGBRegressor is None:
        return None
    model = NGBRegressor(n_estimators=n_estimators)
    model.fit(X, y)
    return model


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--features', required=True)
    p.add_argument('--out', default='models/weekly_run')
    p.add_argument('--target', default='ret_5d', help='Target column to train on (default ret_5d). Falls back to ret_21d or ret_1m if missing')
    p.add_argument('--rf-estimators', type=int, default=50, help='RandomForest n_estimators (default 50)')
    p.add_argument('--ngb-estimators', type=int, default=200, help='NGBoost n_estimators (default 200)')
    args = p.parse_args()

    df = pd.read_parquet(args.features)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    # select target column, with fallbacks
    target = args.target
    if target not in df.columns:
        for alt in ['ret_21d', 'ret_1m', 'ret_3m']:
            if alt in df.columns:
                print(f"Target '{target}' not found; falling back to '{alt}'")
                target = alt
                break
    if target not in df.columns:
        raise SystemExit(f"Target '{args.target}' missing and no fallback found in features")
    df = df.dropna(subset=['ticker'])
    # drop rows with NaN target
    df = df[~df[target].isna()].copy()
    if df.empty:
        raise SystemExit('No rows with non-null ret_5d to train on')
    # preserve identifiers
    ids = df[['ticker']].copy()
    if 'date' in df.columns:
        ids['date'] = df['date']
    # feature columns: drop non-numeric/skipped cols
    drop = ['ticker', 'date']
    candidate = [c for c in df.columns if c not in drop and c != target]
    # keep only numeric feature columns
    numeric_cols = []
    for c in candidate:
        try:
            if pd.api.types.is_numeric_dtype(df[c]):
                numeric_cols.append(c)
        except Exception:
            continue
    if not numeric_cols:
        raise SystemExit('No numeric feature columns found for training')
    X = df[numeric_cols].copy()
    y = df[target].copy()

    tscv = TimeSeriesSplit(n_splits=5)
    oof_preds = pd.Series(index=df.index, dtype=float)
    models = {'lgb': None, 'ngb': None, 'rf': None}

    for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
        Xtr, Xv = X.iloc[train_idx], X.iloc[val_idx]
        ytr, yv = y.iloc[train_idx], y.iloc[val_idx]
        # train lgb
        try:
            if lgb is not None:
                m = train_lightgbm(Xtr, ytr)
                pred = m.predict(Xv)
                oof_preds.iloc[val_idx] = pred
                models['lgb'] = m
        except Exception as e:
            print('lgb fold failed', e)
        # train ngboost
        try:
            if NGBRegressor is not None:
                ng = train_ngboost(Xtr, ytr, n_estimators=args.ngb_estimators)
                pred = ng.predict(Xv)
                # store as additional column
                X.loc[Xv.index, 'ng_oof'] = pred
                models['ngb'] = ng
        except Exception as e:
            print('ngb fold failed', e)
        # fallback rf inside the fold so we can fill OOFs
        try:
            rf = RandomForestRegressor(n_estimators=args.rf_estimators)
            rf.fit(Xtr, ytr)
            pred = rf.predict(Xv)
            X.loc[Xv.index, 'rf_oof'] = pred
            models['rf'] = rf
        except Exception as e:
            print('rf fold failed', e)

    # Save artifacts
    os.makedirs(args.out, exist_ok=True)
    joblib.dump(models['lgb'], os.path.join(args.out, 'weekly_lgb.joblib'))
    joblib.dump(models['ngb'], os.path.join(args.out, 'weekly_ngb.joblib'))
    joblib.dump(models['rf'], os.path.join(args.out, 'weekly_rf.joblib'))
    # ensure OOF preds filled: if some entries are still NaN, fill them using a safe fallback
    try:
        if oof_preds.isna().any():
            # fallback: use RF model predictions on full feature matrix if available
            if models.get('rf') is not None:
                try:
                    fallback = models['rf'].predict(X)
                    # ensure alignment by index
                    fallback_series = pd.Series(fallback, index=oof_preds.index)
                    oof_preds = oof_preds.fillna(fallback_series)
                except Exception:
                    # last resort: fill with mean
                    oof_preds = oof_preds.fillna(oof_preds.mean())
            else:
                oof_preds = oof_preds.fillna(oof_preds.mean())
        # write oof preds for stacking
        oof_df = ids.copy()
        oof_df['oof_pred'] = oof_preds.astype(float)
        oof_df.to_csv(os.path.join(args.out, 'oof_preds.csv'), index=False)
    except Exception:
        # fallback write upstream even if fill attempt fails
        oof_df = ids.copy()
        oof_df['oof_pred'] = oof_preds
        oof_df.to_csv(os.path.join(args.out, 'oof_preds.csv'), index=False)
    print('wrote models and oof preds')


if __name__ == '__main__':
    main()
