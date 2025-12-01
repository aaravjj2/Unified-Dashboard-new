#!/usr/bin/env python3
"""Quick diagnostics: compute per-date correlation (pearson + spearman) between model scores and realized returns.

Usage:
  python3 scripts/quick_diagnostics.py --models-dir models/weekly_run_retrain --features data/snapshots_all.parquet --target ret_1m
"""
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.stats import spearmanr


def run(models_dir, snapshots_path, target):
    mdir = Path(models_dir)
    snap = pd.read_parquet(snapshots_path)
    if 'date' in snap.columns:
        snap['date'] = pd.to_datetime(snap['date'])

    # pick target fallback if requested missing
    if target not in snap.columns:
        for alt in ['ret_21d','ret_1m','ret_3m','ret_5d']:
            if alt in snap.columns:
                print(f"Target '{target}' not found in snapshots; falling back to '{alt}'")
                target = alt
                break
    if target not in snap.columns:
        raise SystemExit('No suitable target column found in snapshots')

    scored_files = sorted(list(mdir.glob('scored_full_*.csv')))
    if not scored_files:
        print('No scored files found in', mdir)
        return
    rows = []
    for f in scored_files:
        df = pd.read_csv(f, parse_dates=['date'] if 'date' in pd.read_csv(f, nrows=0).columns else None)
        # merge realized target
        if 'date' in df.columns and 'ticker' in df.columns and 'date' in snap.columns:
            merged = df.merge(snap[['ticker','date',target]], on=['ticker','date'], how='left')
        elif 'ticker' in df.columns:
            # try merge on ticker only
            if target in snap.columns:
                merged = df.merge(snap[['ticker',target]], on=['ticker'], how='left')
            else:
                print(f'Skipping {f.name}: target {target} missing in snapshots')
                continue
        else:
            print(f'Skipping {f.name}: no ticker/date to join on')
            continue
        # pick column for prediction
        pred_col = None
        for c in ['stack_pred','oof_pred','score','pred']:
            if c in merged.columns:
                pred_col = c
                break
        if pred_col is None:
            # try any numeric pred-like col
            candidates = [c for c in merged.columns if 'pred' in c or 'score' in c]
            pred_col = candidates[0] if candidates else None
        if pred_col is None:
            continue
        # ensure required columns exist
        if pred_col not in merged.columns:
            print(f'Skipping {f.name}: pred column {pred_col} missing after merge')
            continue
        if target not in merged.columns:
            print(f'Skipping {f.name}: target {target} missing after merge')
            continue
        merged = merged.dropna(subset=[pred_col, target])
        if merged.empty:
            print(f'Skipping {f.name}: no rows with both pred and target')
            continue
        # compute correlations per date if date exists
        if 'date' in merged.columns:
            for d, g in merged.groupby('date'):
                if len(g) < 5:
                    continue
                pear = np.corrcoef(g[pred_col], g[target])[0,1]
                spear = spearmanr(g[pred_col], g[target]).correlation
                rows.append({'scored_file': f.name, 'date': d, 'n': len(g), 'pred_col': pred_col, 'pearson': float(pear) if not np.isnan(pear) else None, 'spearman': float(spear) if not np.isnan(spear) else None})
        else:
            pear = np.corrcoef(merged[pred_col], merged[target])[0,1]
            spear = spearmanr(merged[pred_col], merged[target]).correlation
            rows.append({'scored_file': f.name, 'date': None, 'n': len(merged), 'pred_col': pred_col, 'pearson': float(pear) if not np.isnan(pear) else None, 'spearman': float(spear) if not np.isnan(spear) else None})

    out = pd.DataFrame(rows)
    out_path = mdir / 'quick_diagnostics.csv'
    out.to_csv(out_path, index=False)
    print('Wrote diagnostics to', out_path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--models-dir', required=True)
    p.add_argument('--features', required=True)
    p.add_argument('--target', default='ret_1m')
    args = p.parse_args()
    run(args.models_dir, args.features, args.target)


if __name__ == '__main__':
    main()
