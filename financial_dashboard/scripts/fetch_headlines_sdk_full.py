#!/usr/bin/env python3
"""
sequential SDK fetcher for company news and ranking fields

Usage examples:
  # smoke test on 5 tickers, don't write output
  python3 scripts/fetch_headlines_sdk_full.py --sample 5 --no-write

  # run for full universe and write parquet
  python3 scripts/fetch_headlines_sdk_full.py --out data/weekly_headlines_sdk.parquet

This script fetches for each ticker:
  - company_news for the last --days days
  - quote (for last_price)
  - company_profile2 (attempt market_cap)
  - daily candles to compute avg_dollar_vol_3mo and ret_1w

The script uses the Finnhub Python SDK and is intentionally sequential (one ticker at a time)
so it's easy to observe per-ticker results and debug differences vs. a parallel fetcher.
"""

import argparse
import datetime
import time
import os
import sys
from typing import List, Dict, Any

import finnhub
import yfinance as yf
import requests
import logging
import pandas as pd
import importlib

# Try to import alpaca-py (optional). Use importlib to avoid static import errors when
# the package isn't installed. Keep import-safe so script works without alpaca-py.
ALPACA_AVAILABLE = False
AlpacaRESTClient = None
StockBarsRequest = None
AlpacaTimeFrame = None
try:
    _alpaca_rest = importlib.import_module("alpaca_py.rest")
    _alpaca_reqs = importlib.import_module("alpaca_py.requests")
    _alpaca_tf = importlib.import_module("alpaca_py.common.timeframe")
    AlpacaRESTClient = getattr(_alpaca_rest, "RESTClient", None)
    StockBarsRequest = getattr(_alpaca_reqs, "StockBarsRequest", None)
    AlpacaTimeFrame = getattr(_alpaca_tf, "TimeFrame", None)
    if AlpacaRESTClient and StockBarsRequest and AlpacaTimeFrame:
        ALPACA_AVAILABLE = True
except Exception:
    ALPACA_AVAILABLE = False


def _load_keys_env(path: str = "keys.env"):
    """Load simple KEY=VALUE lines from a keys.env file into os.environ.

    This is intentionally minimal: skips comments and blank lines, and does
    not overwrite already-set environment variables.
    """
    try:
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and v and (k not in os.environ):
                    os.environ[k] = v
    except Exception:
        # Don't fail hard if keys.env is malformed; caller will still validate env keys
        return


def read_universe(path: str) -> List[str]:
    # Try to read common CSV variants and find the ticker column
    if not os.path.exists(path):
        raise FileNotFoundError(f"Universe file not found: {path}")
    df = pd.read_csv(path)
    # common column names
    for col in ("SYMBOL", "Symbol", "symbol", "ticker", "Ticker", "TICKER"):
        if col in df.columns:
            return df[col].dropna().astype(str).str.strip().tolist()
    # fallback: first column
    first = df.columns[0]
    return df[first].dropna().astype(str).str.strip().tolist()


def to_unix(dt: datetime.date) -> int:
    return int(datetime.datetime(dt.year, dt.month, dt.day).timestamp())


def fetch_for_ticker(client: finnhub.Client, ticker: str, days: int, verbose: bool = False) -> Dict[str, Any]:
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=days)
    out = {
        "ticker": ticker,
        "news_count": 0,
        "news_sample": [],
        "last_price": None,
        "market_cap": None,
        "avg_dollar_vol_3mo": None,
        "ret_1w": None,
    }

    # company news
    try:
        news = client.company_news(ticker, _from=start_date.strftime("%Y-%m-%d"), to=today.strftime("%Y-%m-%d"))
        out["news_count"] = len(news) if news else 0
        if news:
            out["news_sample"] = [n.get("headline") for n in news[:5]]
    except Exception as e:
        if verbose:
            print(f"[WARN] news fetch failed for {ticker}: {e}")

    # debug: do a raw HTTP preflight to inspect headers
    if hasattr(fetch_for_ticker, "debug") and fetch_for_ticker.debug:
        try:
            url = "https://finnhub.io/api/v1/company-news"
            params = {"symbol": ticker, "from": start_date.strftime("%Y-%m-%d"), "to": today.strftime("%Y-%m-%d"), "token": os.environ.get("FINNHUB_API_KEY")}
            r = requests.get(url, params=params, timeout=20)
            logging.info(f"[PRE] news {ticker} status={r.status_code} headers={{'x-ratelimit-limit':r.headers.get('x-ratelimit-limit'), 'x-ratelimit-remaining':r.headers.get('x-ratelimit-remaining')}} len={len(r.content)}")
        except Exception as e:
            logging.info(f"[PRE] news {ticker} preflight failed: {e}")

    # quote -> last_price
    try:
        q = client.quote(ticker)
        # c = current price, pc = previous close
        out["last_price"] = q.get("c") if isinstance(q, dict) else None
    except Exception as e:
        if verbose:
            print(f"[WARN] quote fetch failed for {ticker}: {e}")

    if hasattr(fetch_for_ticker, "debug") and fetch_for_ticker.debug:
        try:
            url = "https://finnhub.io/api/v1/quote"
            params = {"symbol": ticker, "token": os.environ.get("FINNHUB_API_KEY")}
            r = requests.get(url, params=params, timeout=10)
            logging.info(f"[PRE] quote {ticker} status={r.status_code} headers={{'x-ratelimit-limit':r.headers.get('x-ratelimit-limit'), 'x-ratelimit-remaining':r.headers.get('x-ratelimit-remaining')}}")
        except Exception as e:
            logging.info(f"[PRE] quote {ticker} preflight failed: {e}")

    # company profile (attempt market cap)
    try:
        prof = client.company_profile2(symbol=ticker)
        # finnhub often returns marketCapitalization or marketCapitalization
        for k in ("marketCapitalization", "marketCap", "marketCapitalizationUSD"):
            if prof and k in prof:
                out["market_cap"] = prof.get(k)
                break
        # some responses include 'marketCapitalization'
        if out["market_cap"] is None:
            # sometimes 'ipo' or other fields present; keep None if not found
            pass
    except Exception as e:
        if verbose:
            print(f"[WARN] profile fetch failed for {ticker}: {e}")

    if hasattr(fetch_for_ticker, "debug") and fetch_for_ticker.debug:
        try:
            url = "https://finnhub.io/api/v1/stock/profile2"
            params = {"symbol": ticker, "token": os.environ.get("FINNHUB_API_KEY")}
            r = requests.get(url, params=params, timeout=10)
            logging.info(f"[PRE] profile {ticker} status={r.status_code} headers={{'x-ratelimit-limit':r.headers.get('x-ratelimit-limit'), 'x-ratelimit-remaining':r.headers.get('x-ratelimit-remaining')}}")
        except Exception as e:
            logging.info(f"[PRE] profile {ticker} preflight failed: {e}")

    # candles for avg dollar vol 90 days and ret_1w (7 days)
    # By default we prefer yfinance batched downloads for historicals. Finnhub candle
    # calls are optional and only attempted when --use-finnhub-candles is set.
    if getattr(fetch_for_ticker, "use_finnhub_candles", False):
        now_ts = int(time.time())
        # 90 days for 3mo average
        t90 = now_ts - (90 * 24 * 3600)
        t8 = now_ts - (8 * 24 * 3600)
        got_3mo = False
        try:
            c90 = client.stock_candles(ticker, 'D', t90, now_ts)
            if c90 and c90.get('s') == 'ok' and c90.get('c'):
                closes = c90.get('c')
                vols = c90.get('v')
                if closes and vols and len(closes) == len(vols):
                    import numpy as np

                    closes = np.array(closes, dtype=float)
                    vols = np.array(vols, dtype=float)
                    dollar_vol = closes * vols
                    out["avg_dollar_vol_3mo"] = float(dollar_vol.mean())
                    got_3mo = True
        except Exception as e:
            if verbose:
                print(f"[WARN] 3mo candles fetch failed for {ticker}: {e}")

        if hasattr(fetch_for_ticker, "debug") and fetch_for_ticker.debug:
            try:
                url = "https://finnhub.io/api/v1/stock/candle"
                params = {"symbol": ticker, "resolution": "D", "from": t90, "to": now_ts, "token": os.environ.get("FINNHUB_API_KEY")}
                r = requests.get(url, params=params, timeout=15)
                logging.info(f"[PRE] candles3mo {ticker} status={r.status_code} headers={{'x-ratelimit-limit':r.headers.get('x-ratelimit-limit'), 'x-ratelimit-remaining':r.headers.get('x-ratelimit-remaining')}} len={len(r.content)}")
            except Exception as e:
                logging.info(f"[PRE] candles3mo {ticker} preflight failed: {e}")

        try:
            c8 = client.stock_candles(ticker, 'D', t8, now_ts)
            if c8 and c8.get('s') == 'ok' and c8.get('c'):
                closes = c8.get('c')
                if len(closes) >= 2:
                    last = float(closes[-1])
                    prev = float(closes[0])
                    if prev != 0:
                        out["ret_1w"] = (last / prev) - 1.0
        except Exception as e:
            if verbose:
                print(f"[WARN] 1w candles fetch failed for {ticker}: {e}")

        if hasattr(fetch_for_ticker, "debug") and fetch_for_ticker.debug:
            try:
                url = "https://finnhub.io/api/v1/stock/candle"
                params = {"symbol": ticker, "resolution": "D", "from": t8, "to": now_ts, "token": os.environ.get("FINNHUB_API_KEY")}
                r = requests.get(url, params=params, timeout=12)
                logging.info(f"[PRE] candles1w {ticker} status={r.status_code} headers={{'x-ratelimit-limit':r.headers.get('x-ratelimit-limit'), 'x-ratelimit-remaining':r.headers.get('x-ratelimit-remaining')}} len={len(r.content)}")
            except Exception as e:
                logging.info(f"[PRE] candles1w {ticker} preflight failed: {e}")

    if verbose:
        print(f"{ticker}: news={out['news_count']}, last_price={out['last_price']}, market_cap={out['market_cap']}, avg_dollar_vol_3mo={out['avg_dollar_vol_3mo']}, ret_1w={out['ret_1w']}")

    return out


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--tickers-file", default="Weekly ticker list.csv", help="CSV file with tickers (default: Weekly ticker list.csv)")
    p.add_argument("--days", type=int, default=30, help="lookback days for news (default 30)")
    p.add_argument("--sample", type=int, default=0, help="only process first N tickers (smoke test)")
    p.add_argument("--no-write", action="store_true", help="don't write parquet, just print summary")
    p.add_argument("--out", default="data/weekly_headlines_sdk.parquet", help="output parquet path")
    p.add_argument("--sleep", type=float, default=1.0, help="seconds to sleep between tickers (default 1.0)")
    p.add_argument("--verbose", action="store_true", help="verbose per-ticker logs")
    p.add_argument("--debug", action="store_true", help="enable HTTP preflight debug logs")
    p.add_argument("--parallel", type=int, default=1, help="split work into N child processes (default 1)")
    p.add_argument("--use-finnhub-candles", action="store_true", help="attempt to use Finnhub candles for historicals (default: use yfinance fallback)")
    p.add_argument("--yf-batch-size", type=int, default=20, help="batch size for yfinance multi-ticker downloads (default 20)")
    p.add_argument("--yf-sleep", type=float, default=0.1, help="seconds to sleep between yfinance batches (default 0.1)")
    p.add_argument("--use-alpaca", action="store_true", help="use Alpaca (alpaca-py) to fetch historicals in batches before falling back to yfinance")
    p.add_argument("--child-run", action="store_true", help=argparse.SUPPRESS)
    args = p.parse_args(argv)

    # Attempt to load keys.env from repo root so users don't have to export keys manually
    _load_keys_env("keys.env")

    api_key = os.environ.get("FINNHUB_API_KEY") or os.environ.get("FINNHUB")
    if not api_key:
        print("FINNHUB_API_KEY not found in environment. Please set it before running.")
        sys.exit(2)

    client = finnhub.Client(api_key=api_key)

    # set debug flag on the fetch function for preflight logging
    fetch_for_ticker.debug = args.debug
    if args.debug:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    # Set whether to use Finnhub candles; default is False to use yfinance (safer with free plan)
    fetch_for_ticker.use_finnhub_candles = bool(args.use_finnhub_candles)

    # Parallel coordinator: when parallel > 1 and not a child-run, spawn child processes
    if args.parallel and args.parallel > 1 and not args.child_run:
        # load tickers and split into parts
        tickers = read_universe(args.tickers_file)
        if args.sample and args.sample > 0:
            tickers = tickers[: args.sample]
        n = args.parallel
        parts = [tickers[i::n] for i in range(n)]

        # collect keys from environment; fallback duplicates if missing
        env_keys = []
        k1 = os.environ.get("FINNHUB_API_KEY")
        k2 = os.environ.get("FINNHUB2_API_KEY")
        if k1:
            env_keys.append(k1)
        if k2:
            env_keys.append(k2)
        if not env_keys:
            print("No FINNHUB_API_KEY found for parallel run; aborting.")
            sys.exit(2)

        procs = []
        child_outs = []
        script = os.path.abspath(__file__)
        for i in range(n):
            part = parts[i]
            if not part:
                continue
            child_out = args.out + f".part{i}.parquet"
            child_outs.append(child_out)
            # write a small temp tickers file for this part
            tmp_tf = f"/tmp/weekly_tickers_part_{i}.csv"
            pd.DataFrame({"ticker": part}).to_csv(tmp_tf, index=False)
            child_env = os.environ.copy()
            # assign key (rotate through available keys)
            child_env["FINNHUB_API_KEY"] = env_keys[i % len(env_keys)]
            cmd = [sys.executable, script, "--tickers-file", tmp_tf, "--out", child_out, "--sleep", str(args.sleep)]
            if args.use_finnhub_candles:
                cmd.append("--use-finnhub-candles")
            if args.debug:
                cmd.extend(["--debug"]) 
            # child-run flag
            cmd.append("--child-run")
            print(f"Spawning child {i} with {len(part)} tickers using key index {i % len(env_keys)}")
            p = __import__("subprocess").Popen(cmd, env=child_env)
            procs.append((p, tmp_tf, child_out))

        # wait for children
        for p, tmp_tf, child_out in procs:
            p.wait()
            if p.returncode != 0:
                print(f"Child process failed with code {p.returncode}; check its logs and {child_out}")

        # merge part files
        dfs = []
        for child_out in child_outs:
            part_path = child_out
            # child wrote parquet with .parquet extension if not --no-write; our child used --no-write so it wrote CSV? 
            # In our invocation we used --no-write to avoid double-writing; instead children should write parquet. 
            # But to be robust, try common suffixes
            candidates = [part_path, part_path + ".parquet", part_path + ".csv"]
            found = False
            for c in candidates:
                if os.path.exists(c):
                    try:
                        dfs.append(pd.read_parquet(c) if c.endswith('.parquet') else pd.read_csv(c))
                        found = True
                        break
                    except Exception:
                        try:
                            dfs.append(pd.read_csv(c))
                            found = True
                            break
                        except Exception:
                            pass
            if not found:
                print(f"Warning: child output not found for {child_out} (checked {candidates})")

        if dfs:
            outdf = pd.concat(dfs, ignore_index=True)
            # dedupe by ticker
            outdf = outdf.drop_duplicates(subset=["ticker"], keep="last")
            out_dir = os.path.dirname(args.out)
            if out_dir and not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)
            outdf.to_parquet(args.out, index=False)
            print(f"Merged {len(dfs)} parts into {args.out} rows={len(outdf)}")
        else:
            print("No parts found to merge.")

        # cleanup temp files
        for p, tmp_tf, child_out in procs:
            try:
                os.remove(tmp_tf)
            except Exception:
                pass

        return

    tickers = read_universe(args.tickers_file)
    if args.sample and args.sample > 0:
        tickers = tickers[: args.sample]

    print(f"Processing {len(tickers)} tickers (sample={args.sample}) with days={args.days}")

    rows = []
    start = time.time()
    for i, t in enumerate(tickers, start=1):
        try:
            data = fetch_for_ticker(client, t, days=args.days, verbose=args.verbose)
            rows.append(data)
        except Exception as e:
            print(f"[ERROR] unexpected failure for {t}: {e}")
        # sleep to be gentle on rate limits
        time.sleep(args.sleep)
        if i % 50 == 0:
            elapsed = time.time() - start
            print(f"Processed {i}/{len(tickers)} tickers in {elapsed:.1f}s")

    df = pd.DataFrame(rows)
    # normalize/expand news_sample into a string column
    if "news_sample" in df.columns:
        df["news_sample"] = df["news_sample"].apply(lambda x: " || ".join([str(s) for s in x]) if isinstance(x, (list, tuple)) else "")

    # If any historical ranking fields are missing, fill them using batched yfinance downloads.
    # This is the preferred default behaviour (faster and avoids Finnhub candle limitations).
    try:
        missing_mask = df["avg_dollar_vol_3mo"].isna() | df["ret_1w"].isna()
        to_fill = df.loc[missing_mask, "ticker"].dropna().unique().tolist()
    except Exception:
        to_fill = []

    # Optionally try Alpaca first to fill historicals, then fallback to yfinance.
    if len(to_fill) > 0 and args.use_alpaca and ALPACA_AVAILABLE:
        print(f"Filling historicals via Alpaca for up to {len(to_fill)} tickers in batches of {args.yf_batch_size}")
        try:
            apca_key = os.environ.get("APCA_API_KEY_ID") or os.environ.get("APCA_API_KEY")
            apca_secret = os.environ.get("APCA_API_SECRET_KEY") or os.environ.get("APCA_SECRET_KEY")
            apca_base = os.environ.get("APCA_ENDPOINT") or None
            if not apca_key or not apca_secret:
                print("Alpaca keys not found in environment; skipping Alpaca fill")
            else:
                alp_client = AlpacaRESTClient(api_key=apca_key, secret_key=apca_secret)
                from datetime import datetime, timedelta
                start_dt = datetime.now() - timedelta(days=90)
                batches = [to_fill[i : i + args.yf_batch_size] for i in range(0, len(to_fill), args.yf_batch_size)]
                for ib, batch in enumerate(batches, start=1):
                    try:
                        req = StockBarsRequest(symbol_or_symbols=batch, timeframe=AlpacaTimeFrame.Day, start=start_dt)
                        res = alp_client.get_stock_bars(req)
                        data = res.data if hasattr(res, 'data') else {}
                        for tk in batch:
                            try:
                                bars = data.get(tk, [])
                                if not bars:
                                    continue
                                # bars is a list-like of bar objects with .close and .volume
                                closes = [float(b.close) for b in bars]
                                vols = [float(b.volume) for b in bars]
                                if len(closes) == len(vols) and len(closes) > 0:
                                    import numpy as np
                                    dollar_vol = np.array(closes) * np.array(vols)
                                    df.loc[df["ticker"] == tk, "avg_dollar_vol_3mo"] = float(dollar_vol.mean())
                                if len(closes) >= 5:
                                    last = float(closes[-1])
                                    prev = float(closes[-5])
                                    if prev != 0:
                                        df.loc[df["ticker"] == tk, "ret_1w"] = (last / prev) - 1.0
                            except Exception:
                                continue
                    except Exception as e:
                        print(f"[WARN] Alpaca batch {ib}/{len(batches)} failed: {e}")
                    time.sleep(args.yf_sleep)
        except Exception as e:
            print(f"[WARN] Alpaca fill failed overall: {e}")

    if len(to_fill) > 0 and yf is not None:
        print(f"Filling historicals via yfinance for {len(to_fill)} tickers in batches of {args.yf_batch_size}")
        import math
        import numpy as np

        batches = [to_fill[i : i + args.yf_batch_size] for i in range(0, len(to_fill), args.yf_batch_size)]
        for ib, batch in enumerate(batches, start=1):
            try:
                # yfinance.download returns a DataFrame; group_by='ticker' makes it easier to split
                yf_df = yf.download(tickers=batch, period="3mo", interval="1d", group_by='ticker', threads=True, progress=False)
            except Exception as e:
                print(f"[WARN] yfinance batch {ib}/{len(batches)} failed: {e}")
                time.sleep(args.yf_sleep)
                continue

            for tk in batch:
                try:
                    # Extract per-ticker frame; yfinance may return single-level columns for single-ticker
                    if isinstance(yf_df.columns, pd.MultiIndex):
                        if tk in yf_df.columns.levels[0]:
                            sub = yf_df[tk].dropna()
                        else:
                            # try fallback where the top-level is not ticker
                            sub = yf_df.dropna()
                    else:
                        sub = yf_df.dropna()

                    if sub is None or sub.empty:
                        continue

                    # Ensure columns exist
                    if "Close" in sub.columns and "Volume" in sub.columns:
                        closes = sub["Close"].astype(float).values
                        vols = sub["Volume"].astype(float).values
                        if len(closes) == len(vols) and len(closes) > 0:
                            dollar_vol = closes * vols
                            df.loc[df["ticker"] == tk, "avg_dollar_vol_3mo"] = float(np.mean(dollar_vol))
                    # 1w return: approximate using 5 trading days ago
                    if "Close" in sub.columns and len(sub) >= 5:
                        last = float(sub["Close"].astype(float).values[-1])
                        prev = float(sub["Close"].astype(float).values[-5])
                        if prev != 0:
                            df.loc[df["ticker"] == tk, "ret_1w"] = (last / prev) - 1.0
                except Exception:
                    # per-ticker failures shouldn't stop the batch
                    continue

            # be gentle with yfinance
            time.sleep(args.yf_sleep)

    if args.no_write:
        print(df.head(20).to_string(index=False))
        print(f"Total rows: {len(df)}")
        return

    out = args.out
    out_dir = os.path.dirname(out)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    # write parquet
    try:
        df.to_parquet(out, index=False)
        print(f"Wrote {out} rows {len(df)}")
    except Exception as e:
        print(f"Failed to write parquet {out}: {e}")


if __name__ == "__main__":
    main()
