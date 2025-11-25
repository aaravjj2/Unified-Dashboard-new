#!/usr/bin/env python3
"""Merge data/embeddings_aggregated.parquet into data/snapshots_all.parquet producing data/snapshots_all_with_emb.parquet"""
import argparse
import pandas as pd


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--snapshots', default='data/snapshots_all.parquet')
    p.add_argument('--emb', default='data/embeddings_aggregated.parquet')
    p.add_argument('--out', default='data/snapshots_all_with_emb.parquet')
    args = p.parse_args()

    snaps = pd.read_parquet(args.snapshots)
    if 'date' in snaps.columns:
        snaps['date'] = pd.to_datetime(snaps['date'])
    emb = pd.read_parquet(args.emb)
    if 'date' in emb.columns:
        emb['date'] = pd.to_datetime(emb['date'])

    merged = snaps.merge(emb, on=['ticker','date'], how='left')
    merged.to_parquet(args.out, index=False)
    print('Wrote merged snapshots with embeddings to', args.out)


if __name__ == '__main__':
    main()
