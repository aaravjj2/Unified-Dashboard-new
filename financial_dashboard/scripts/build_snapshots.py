"""Build per-date feature snapshots from an existing features CSV.

Produces:
 - data/snapshots_all.parquet  (combined)
 - data/snapshots/YYYYMMDD.parquet (one file per date)

Usage:
  python3 scripts/build_snapshots.py --features data/features_20250912.csv --out data/snapshots
"""
from pathlib import Path
import argparse
import pandas as pd


def main(features, out_dir):
    features = Path(features)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print('Reading features from', features)
    df = pd.read_csv(features, parse_dates=['date'])
    if 'date' not in df.columns:
        raise SystemExit('features file must include a date column')

    # ensure ticker column exists
    if 'ticker' not in df.columns:
        raise SystemExit('features file must include ticker column')

    # write per-date snapshots
    dates = sorted(df['date'].dropna().unique())
    print('Found', len(dates), 'unique dates')
    files = []
    for d in dates:
        day = pd.to_datetime(d)
        sub = df[df['date'] == day]
        if sub.empty:
            continue
        fname = out_dir / f'{day.strftime("%Y%m%d")}.parquet'
        sub.to_parquet(fname, index=False)
        files.append(fname)
    # write combined parquet
    combined = Path(features).parent / 'snapshots_all.parquet'
    print('Writing combined snapshots to', combined)
    df.to_parquet(combined, index=False)
    print('Wrote', len(files), 'per-date files and combined file')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--features', required=True)
    p.add_argument('--out', default='data/snapshots')
    args = p.parse_args()
    main(args.features, args.out)
