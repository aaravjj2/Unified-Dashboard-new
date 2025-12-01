from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.pipeline.stacker import train_and_predict_stack

BASE = Path(__file__).resolve().parents[1]
BASE_FULL = BASE / 'models' / 'full_run'
features_path = BASE / 'data' / 'features_20250912.csv'
# locate models
lgb_paths = sorted([str(p) for p in BASE_FULL.glob('lightgbm_fold*_20250914.joblib')])
ng_paths = sorted([str(p) for p in BASE_FULL.glob('ngboost_fold*_20250914.joblib')])
oof_lgb = str(BASE_FULL / 'oof_lightgbm_20250914.csv')
oof_ng = str(BASE_FULL / 'oof_ngboost_20250914.csv')

out_dir = str(BASE / 'models' / 'test_run')
stacker_path, picks_path = train_and_predict_stack(str(features_path), lgb_paths, oof_lgb, ng_paths, oof_ng, [], target='ret_1m', out_dir=out_dir, top_k=20)
print('stacker_path', stacker_path)
print('picks_path', picks_path)
import pandas as pd
print('\nPICKS CSV columns:')
print(pd.read_csv(picks_path).columns.tolist())
print('\nPICKS CSV head:')
print(pd.read_csv(picks_path).head().to_csv(index=False))
print('\nSCORED CSV columns:')
scored_files = sorted([p for p in Path(out_dir).glob('scored_full_*.csv')])
if scored_files:
    print(scored_files[-1])
    print(pd.read_csv(scored_files[-1]).columns.tolist())
    print(pd.read_csv(scored_files[-1]).head().to_csv(index=False))
else:
    print('no scored file')
