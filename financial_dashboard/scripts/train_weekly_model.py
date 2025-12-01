"""Train or warm-start a weekly model using LightGBM if available.

This script is a lightweight implementation: it will attempt to use LightGBM
if installed; otherwise it trains a small RandomForest as a fallback. It
saves the model under `models/weekly_run/` with a date-stamped filename and
updates `models/weekly_run/lightgbm_weekly_latest.joblib` (or rf fallback).
"""
import os
import argparse
import joblib
from datetime import datetime

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT_DIR = os.path.join(BASE, 'models', 'weekly_run')
os.makedirs(OUT_DIR, exist_ok=True)

def train_placeholder(X, y, out_path, warmstart_path=None):
    # Try LightGBM warm-start if available
    try:
        import lightgbm as lgb
        dtrain = lgb.Dataset(X, label=y)
        params = {'objective': 'regression', 'verbose': -1}
        init_model = None
        if warmstart_path and os.path.exists(warmstart_path):
            try:
                init_model = joblib.load(warmstart_path)
            except Exception:
                init_model = None
        if init_model is not None:
            # lgb.train accepts init_model as model object or filename
            model = lgb.train(params, dtrain, num_boost_round=20, init_model=init_model)
        else:
            model = lgb.train(params, dtrain, num_boost_round=50)
        joblib.dump(model, out_path)
        return 'lgb'
    except Exception:
        # fallback to sklearn
        try:
            from sklearn.ensemble import RandomForestRegressor
            model = RandomForestRegressor(n_estimators=50, random_state=42)
            model.fit(X, y)
            joblib.dump(model, out_path)
            return 'rf'
        except Exception:
            # as a last resort, write a placeholder dict
            joblib.dump({'placeholder': True}, out_path)
            return 'placeholder'

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--features', help='CSV or parquet of features', default=None)
    p.add_argument('--out', help='output model path', default=None)
    p.add_argument('--force-retrain', action='store_true', help='Ignore warm-start and retrain from scratch')
    args = p.parse_args(argv)

    # for demo: if features not provided, build tiny synthetic X,y
    warmstart = None
    latest_ptr = os.path.join(OUT_DIR, 'weekly_model_latest.joblib')
    latest_info = None
    if os.path.exists(latest_ptr):
        try:
            latest_info = joblib.load(latest_ptr)
            if isinstance(latest_info, dict) and latest_info.get('path'):
                warmstart = latest_info.get('path')
        except Exception:
            warmstart = None

    feature_cols = None
    if args.features is None:
        import numpy as np
        X = np.random.RandomState(0).randn(100, 5)
        y = (X[:, 0] * 0.5 + X[:, 1] * -0.2) + np.random.RandomState(1).randn(100) * 0.01
        # synthetic feature names
        feature_cols = [f'f{i}' for i in range(X.shape[1])]
    else:
        # try reading a csv or parquet with pandas
        import pandas as pd
        if args.features.endswith('.parquet'):
            df = pd.read_parquet(args.features)
        else:
            df = pd.read_csv(args.features)
        # prefer numeric feature columns (exclude label)
        num_df = df.select_dtypes(include=['number']).copy()
        if 'label' in num_df.columns:
            num_df = num_df.drop(columns=['label'])
        feature_cols = list(num_df.columns[:20])
        X = num_df.iloc[:, :20].fillna(0).values
        # if there is a label column named 'label' use it otherwise synth
        if 'label' in df.columns:
            y = df['label'].fillna(0).values
        else:
            y = df.select_dtypes(include=['number']).iloc[:, 0].fillna(0).values

    date_str = datetime.utcnow().strftime('%Y%m%d')
    out_path = args.out or os.path.join(OUT_DIR, f'weekly_model_{date_str}.joblib')
    # If feature columns changed compared to latest pointer, avoid warm-start
    use_warm = True
    if args.force_retrain:
        use_warm = False
    else:
        try:
            if latest_info and isinstance(latest_info, dict) and latest_info.get('feature_columns'):
                prev_cols = list(latest_info.get('feature_columns'))
                if prev_cols != (feature_cols or []):
                    # columns changed -> retrain from scratch
                    use_warm = False
        except Exception:
            use_warm = True

    kind = train_placeholder(X, y, out_path, warmstart_path=(warmstart if use_warm else None))
    # write a pointer to latest model
    latest = os.path.join(OUT_DIR, 'weekly_model_latest.joblib')
    # write a pointer to latest model including feature column names and dtypes for alignment
    try:
        feature_dtypes = None
        if feature_cols is not None and args.features is not None:
            try:
                import pandas as pd
                if args.features.endswith('.parquet'):
                    df = pd.read_parquet(args.features)
                else:
                    df = pd.read_csv(args.features)
                dtypes = {c: str(df[c].dtype) for c in feature_cols if c in df.columns}
                feature_dtypes = dtypes
            except Exception:
                feature_dtypes = None

        pointer = {
            'path': out_path,
            'kind': kind,
            'feature_columns': feature_cols,
            'feature_dtypes': feature_dtypes,
            'trained_on': date_str
        }
        joblib.dump(pointer, latest)
    except Exception:
        pass
    print('Wrote model:', out_path, 'kind=', kind)

if __name__ == '__main__':
    main()
