#!/usr/bin/env python3
"""Re-rank weekly picks deterministically to break ties.

Sort precedence (descending):
 - score (existing)
 - has_headlines (tickers with headlines first)
 - market_cap (higher first)
 - last_price (higher first)
 - ticker (ascending) as final deterministic tie-breaker

Writes: models/weekly_run/{orig_filename}_reranked.csv and updates weekly meta JSON with rerank metadata.
"""
import json
import os
import sys
import time
import argparse
import pandas as pd


def load_headline_presence(headlines_parquet_path):
    if not os.path.exists(headlines_parquet_path):
        return set()
    try:
        df = pd.read_parquet(headlines_parquet_path, columns=["ticker"])
        return set(df["ticker"].astype(str).unique())
    except Exception:
        return set()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--picks", default=None, help='Path to picks CSV. If omitted, auto-discover latest weeklypicks*.csv in models/weekly_run')
    p.add_argument("--headlines", default="data/weekly_headlines_all.parquet")
    p.add_argument("--enriched", default="data/weekly_enriched_with_sentiment.parquet")
    p.add_argument("--meta", default="models/weekly_run/weekly_meta_20250922.json")
    p.add_argument("--out", default=None, help="Output CSV path (defaults to picks_weekly_YYYYMMDD_reranked.csv)")
    args = p.parse_args()

    # Auto-discover picks file if not provided
    if not args.picks:
        candidates = []
        import glob
        base = os.path.join('models', 'weekly_run')
        patterns = [os.path.join(base, 'weeklypicks*.csv'), os.path.join(base, 'picks_weekly_*.csv'), os.path.join(base, 'picks_*.csv')]
        for pat in patterns:
            candidates += glob.glob(pat)
        if not candidates:
            print("No picks files found in models/weekly_run/", file=sys.stderr)
            sys.exit(2)
        args.picks = max(candidates, key=lambda p: os.path.getmtime(p))
        print('Auto-discovered picks file:', args.picks)
    elif not os.path.exists(args.picks):
        print("Picks file not found:", args.picks, file=sys.stderr)
        sys.exit(2)

    picks = pd.read_csv(args.picks)
    # normalize ticker col name
    if "ticker" not in picks.columns:
        # try symbol
        for c in ("symbol", "Symbol"):
            if c in picks.columns:
                picks = picks.rename(columns={c: "ticker"})
                break

    picks["ticker"] = picks["ticker"].astype(str)

    # load headline presence
    headline_set = load_headline_presence(args.headlines)
    picks["has_headlines"] = picks["ticker"].isin(headline_set)

    # try to load market_cap/last_price from enriched features if present
    if os.path.exists(args.enriched):
        try:
            enriched = pd.read_parquet(args.enriched)
            enriched = enriched[[c for c in ("ticker", "market_cap", "last_price") if c in enriched.columns]]
            enriched["ticker"] = enriched["ticker"].astype(str)
            picks = picks.merge(enriched, on="ticker", how="left")
        except Exception:
            picks["market_cap"] = pd.NA
            picks["last_price"] = pd.NA
    else:
        picks["market_cap"] = pd.NA
        picks["last_price"] = pd.NA

    # ensure numeric fields exist, then coerce
    if "market_cap" not in picks.columns:
        picks["market_cap"] = pd.NA
    if "last_price" not in picks.columns:
        picks["last_price"] = pd.NA

    picks["market_cap"] = pd.to_numeric(picks["market_cap"], errors="coerce").fillna(0.0)
    picks["last_price"] = pd.to_numeric(picks["last_price"], errors="coerce").fillna(0.0)

    # define sort keys: score desc, has_headlines desc (True>False), market_cap desc, last_price desc, ticker asc
    picks_sorted = picks.sort_values(by=["score", "has_headlines", "market_cap", "last_price", "ticker"],
                                     ascending=[False, False, False, False, True],
                                     kind="mergesort")

    # recompute rank (1-based)
    picks_sorted = picks_sorted.reset_index(drop=True)
    picks_sorted["rank"] = picks_sorted.index + 1

    out_path = args.out or args.picks.replace(".csv", "_reranked.csv")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    picks_sorted.to_csv(out_path, index=False)

    # update meta JSON if present
    meta = {}
    if args.meta and os.path.exists(args.meta):
        try:
            with open(args.meta) as f:
                meta = json.load(f)
        except Exception:
            meta = {}

    meta_update = {
        "rerank_applied": True,
        "rerank_method": "score desc, has_headlines desc, market_cap desc, last_price desc, ticker asc",
        "rerank_time": int(time.time()),
        "rerank_output": out_path
    }
    meta["rerank"] = meta_update
    if args.meta:
        try:
            with open(args.meta, "w") as f:
                json.dump(meta, f, indent=2)
        except Exception as e:
            print("Failed to write meta:", e, file=sys.stderr)

    print("Wrote reranked picks to:", out_path)
    print("Updated meta:", args.meta)


if __name__ == "__main__":
    main()
