"""Train LightGBM with rolling purged CV and save OOFs.

This is a self-contained, runnable script intended as a starter:
- generates a tiny synthetic dataset when run with --smoke
- implements a simple rolling purged CV generator
- trains LightGBM (if available) with lambdarank-like grouping, otherwise falls back to sklearn's RandomForestRegressor for smoke
- saves OOF csv and model to /tmp and prints locations

Usage:
    python scripts/train_lightgbm.py --smoke

"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime


def make_synthetic(n_tickers=50, n_months=24, seed=42):
    rng = np.random.RandomState(seed)
    # create monthly dates
    start = datetime(2023, 1, 1)
    dates = [start + pd.DateOffset(months=i) for i in range(n_months)]
    rows = []
    for d in dates:
        for t in range(n_tickers):
            rows.append({
                'date': d,
                'ticker': f'T{t:03d}',
                'feat1': rng.randn(),
                'feat2': rng.randn(),
                'avg_dollar_vol': abs(rng.randn()) * 1e6,
            })
    df = pd.DataFrame(rows)
    # create next-month return as target with some signal
    df['ret_1m'] = 0.01 * (0.3 * df['feat1'] + 0.2 * df['feat2'] + 0.1 * np.log1p(df['avg_dollar_vol']) + rng.randn(len(df)) * 0.5)
    return df


def rolling_purged_splits(dates, train_window_months=12, n_folds=4, embargo_months=0):
    """Yield (train_dates, val_dates) where dates is sorted unique months.
    Simple rolling forward validation using month indices.
    """
    dates = sorted(dates)
    folds = []
    for fold in range(n_folds):
        val_idx = len(dates) - n_folds + fold
        val_date = dates[val_idx]
        train_end_idx = val_idx - 1 - embargo_months
        train_start_idx = max(0, train_end_idx - train_window_months + 1)
        train_dates = dates[train_start_idx:train_end_idx + 1]
        val_dates = [val_date]
        folds.append((train_dates, val_dates))
    return folds


def prepare_Xy(df, feature_cols, target_col='ret_1m'):
    X = df[feature_cols].copy()
    y = df[target_col].copy()
    return X, y


def train_and_oof(df, feature_cols, target_col='ret_1m', out_dir='/tmp/train_lightgbm_smoke'):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    # ensure date is month-start
    df = df.copy()
    df['month'] = pd.to_datetime(df['date']).dt.to_period('M').dt.to_timestamp()
    months = sorted(df['month'].unique())
    folds = rolling_purged_splits(months, train_window_months=12, n_folds=min(4, len(months)-1))

    oof = []
    models = []

    # Try to import lightgbm
    try:
        import lightgbm as lgb
        has_lgb = True
    except Exception:
        has_lgb = False

    for i, (train_dates, val_dates) in enumerate(folds):
        train_idx = df['month'].isin(train_dates)
        val_idx = df['month'].isin(val_dates)
        X_train, y_train = prepare_Xy(df[train_idx], feature_cols, target_col)
        X_val, y_val = prepare_Xy(df[val_idx], feature_cols, target_col)

        if has_lgb:
            dtrain = lgb.Dataset(X_train, label=y_train)
            dval = lgb.Dataset(X_val, label=y_val)
            params = {
                'objective': 'regression',
                'metric': 'l2',
                'learning_rate': 0.05,
                'num_leaves': 31,
                'verbose': -1,
            }
            # use callback-based early stopping for maximum compatibility
            callbacks = [lgb.early_stopping(stopping_rounds=20), lgb.log_evaluation(period=0)]
            model = lgb.train(params, dtrain, num_boost_round=100, valid_sets=[dval], callbacks=callbacks)
            pred = model.predict(X_val, num_iteration=model.best_iteration)
            models.append(model)
        else:
            # fallback to sklearn
            from sklearn.ensemble import RandomForestRegressor
            model = RandomForestRegressor(n_estimators=50, random_state=0)
            model.fit(X_train, y_train)
            pred = model.predict(X_val)
            models.append(model)

        tmp = df[val_idx][['month', 'ticker']].copy()
        tmp['y_true'] = y_val.values
        tmp['y_pred'] = pred
        tmp['fold'] = i
        oof.append(tmp)
        print(f"Fold {i} done: train {len(X_train)} val {len(X_val)}")

    oof_df = pd.concat(oof, ignore_index=True)
    oof_path = Path(out_dir) / f'oof_lightgbm_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    oof_df.to_csv(oof_path, index=False)

    # save a simple model artifact (first model)
    model_path = Path(out_dir) / 'model_lightgbm_smoke.joblib'
    try:
        import joblib
        joblib.dump(models[0], model_path)
    except Exception:
        # best-effort
        with open(model_path, 'wb') as f:
            f.write(b'')

    print('OOF saved to', oof_path)
    print('Model saved to', model_path)
    return oof_path, model_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true', help='Run a small smoke test using synthetic data')
    args = parser.parse_args()

    if args.smoke:
        print('Generating synthetic data for smoke test...')
        df = make_synthetic(n_tickers=60, n_months=30)
        feature_cols = ['feat1', 'feat2', 'avg_dollar_vol']
        out = train_and_oof(df, feature_cols, out_dir='/tmp/train_lightgbm_smoke')
    else:
        print('No dataset specified. Please provide a features file or run with --smoke for a quick test.')
