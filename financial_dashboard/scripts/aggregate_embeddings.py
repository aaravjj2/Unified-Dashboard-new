#!/usr/bin/env python3
"""Aggregate per-headline embeddings (cache) into per-(ticker,date) embeddings.

Reads: data/weekly_headlines_all.parquet and data/embeddings/ (cache)
Writes: data/embeddings_aggregated.parquet with columns ticker,date,emb_0..emb_k
"""
from pathlib import Path
import argparse
import pandas as pd
import numpy as np


def load_index(idx_path):
    return pd.read_parquet(idx_path)


def load_vec(cache_dir, h):
    import numpy as _np
    fn = Path(cache_dir) / f'{h}.npy'
    if not fn.exists():
        return None
    return _np.load(fn)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--headlines', default='data/weekly_headlines_all.parquet')
    p.add_argument('--emb-dir', default='data/embeddings')
    p.add_argument('--out', default='data/embeddings_aggregated.parquet')
    args = p.parse_args()

    df = pd.read_parquet(args.headlines)
    df = df.rename(columns={c: c.strip() for c in df.columns})
    time_col = 'published_at' if 'published_at' in df.columns else (args.time_col or 'date')
    if 'headline' not in df.columns and 'title' in df.columns:
        df['headline'] = df['title']
    df['headline_text'] = df['headline'].astype(str).str.strip()
    df = df[df['headline_text'].str.len() > 0].copy()
    # compute hash
    import hashlib
    df['h'] = df['headline_text'].apply(lambda s: hashlib.sha1(s.encode('utf-8')).hexdigest())
    # normalize time to date for merging
    if time_col in df.columns:
        df[time_col] = pd.to_datetime(df[time_col])
        df['date'] = df[time_col].dt.normalize()
    else:
        # if no time column, attempt to use a provided date column
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.normalize()
        else:
            raise SystemExit('No time/date column found in headlines parquet')

    idx_path = Path(args.emb_dir) / 'embeddings_index.parquet'
    if not idx_path.exists():
        raise SystemExit('Embeddings index not found: ' + str(idx_path))
    idx = pd.read_parquet(idx_path)
    # ensure we only process headlines present in index/cache
    has_hash = set(idx['hash'].tolist())
    df = df[df['h'].isin(has_hash)]
    if df.empty:
        print('No indexed headlines matched; exiting')
        return

    # group by ticker & date and aggregate embeddings (mean)
    groups = []
    cache_dir = Path(args.emb_dir) / 'cache'
    for (tkr, date), g in df.groupby(['ticker','date']):
        vecs = []
        for h in g['h'].unique():
            v = load_vec(cache_dir, h)
            if v is not None:
                vecs.append(v)
        if not vecs:
            continue
        arr = np.vstack(vecs)
        mean = arr.mean(axis=0)
        rows = {'ticker': tkr, 'date': pd.to_datetime(date)}
        for i, val in enumerate(mean.tolist()):
            rows[f'emb_{i}'] = float(val)
        groups.append(rows)

    out = pd.DataFrame(groups)
    out.to_parquet(args.out, index=False)
    print('Wrote aggregated embeddings to', args.out)


if __name__ == '__main__':
    main()
