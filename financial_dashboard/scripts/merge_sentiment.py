"""Merge sentiment aggregates into the weekly enrichment parquet.

Reads:
 - data/weekly_enriched.parquet
 - data/weekly_sentiment.parquet
Writes:
 - data/weekly_enriched_with_sentiment.parquet

This is idempotent and safe: it will join on 'ticker' and prefer existing columns
from the enrichment file when present.
"""
import os
import pandas as pd

IN_ENRICH = 'data/weekly_enriched.parquet'
IN_SENT = 'data/weekly_sentiment.parquet'
OUT = 'data/weekly_enriched_with_sentiment.parquet'


def main():
    if not os.path.exists(IN_ENRICH):
        raise SystemExit(f"Missing: {IN_ENRICH}")
    if not os.path.exists(IN_SENT):
        raise SystemExit(f"Missing: {IN_SENT}")
    e = pd.read_parquet(IN_ENRICH)
    s = pd.read_parquet(IN_SENT)
    # prefer existing sentiment columns if present
    merged = e.merge(s, on='ticker', how='left', suffixes=('', '_sent'))
    merged.to_parquet(OUT)
    print('wrote', OUT)


if __name__ == '__main__':
    main()
