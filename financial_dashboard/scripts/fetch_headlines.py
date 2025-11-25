#!/usr/bin/env python3
"""
Fetch headlines per-ticker using Finnhub (preferred), NewsAPI (fallback) and optionally scrape Yahoo Finance.
Writes a single parquet file with columns: ticker, published_at (pd.Timestamp), source, title, summary, url, fetched_at

Usage examples:
  python3 scripts/fetch_headlines.py --out data/weekly_headlines_sample.parquet --sample 10 --days 7 --use-scrape

This is a resilient, single-threaded, rate-limit-aware fetcher with simple resume behavior.
"""
import argparse
import datetime
import time
import json
import os
from dotenv import dotenv_values
import requests
import pandas as pd
import threading

try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except Exception:
    _HAS_BS4 = False


def load_tickers(tickers_file=None, sample=0):
    if tickers_file and os.path.exists(tickers_file):
        df = pd.read_csv(tickers_file)
        cols = [c for c in df.columns if c.lower() in ('symbol', 'ticker', 'symbol', 'symbols')]
        col = cols[0] if cols else df.columns[0]
        tickers = df[col].astype(str).str.strip().unique().tolist()
    else:
        # fallback to enriched parquet
        p = 'data/weekly_enriched.parquet'
        if not os.path.exists(p):
            raise FileNotFoundError('No tickers file and no data/weekly_enriched.parquet found')
        df = pd.read_parquet(p)
        if 'ticker' in df.columns:
            tickers = df['ticker'].astype(str).str.strip().unique().tolist()
        else:
            tickers = df.iloc[:,0].astype(str).str.strip().unique().tolist()
    if sample and sample > 0:
        return tickers[: sample]
    return tickers


def finnhub_company_news(ticker, api_key, frm, to):
    url = f'https://finnhub.io/api/v1/company-news?symbol={ticker}&from={frm}&to={to}&token={api_key}'
    r = requests.get(url, timeout=15)
    if r.status_code != 200:
        return None, r
    try:
        j = r.json()
    except Exception:
        return None, r
    items = []
    for it in j if isinstance(j, list) else []:
        # finn: headline, datetime (epoch sec), url, source
        pub = None
        if 'datetime' in it and it['datetime']:
            pub = datetime.datetime.utcfromtimestamp(int(it['datetime']))
        if 'datetime' in it and isinstance(it['datetime'], str):
            try:
                pub = pd.to_datetime(it['datetime'])
            except Exception:
                pass
        items.append({'ticker': ticker, 'published_at': pub, 'source': it.get('source'), 'title': it.get('headline'), 'summary': it.get('summary') or None, 'url': it.get('url')})
    return items, r


def newsapi_everything(ticker, api_key, page_size=100):
    url = f'https://newsapi.org/v2/everything?q={ticker}&pageSize={page_size}&apiKey={api_key}'
    r = requests.get(url, timeout=15)
    if r.status_code != 200:
        return None, r
    j = r.json()
    items = []
    for a in j.get('articles', []):
        pub = None
        try:
            pub = pd.to_datetime(a.get('publishedAt'))
        except Exception:
            pass
        items.append({'ticker': ticker, 'published_at': pub, 'source': a.get('source', {}).get('name'), 'title': a.get('title'), 'summary': a.get('description'), 'url': a.get('url')})
    return items, r


def scrape_yahoo(ticker):
    if not _HAS_BS4:
        return None, None
    url = f'https://finance.yahoo.com/quote/{ticker}/news?p={ticker}'
    r = requests.get(url, timeout=15)
    if r.status_code != 200:
        return None, r
    soup = BeautifulSoup(r.text, 'lxml')
    items = []
    # best-effort: find article headline blocks
    # Yahoo uses many different classes; collect <h3> anchors
    for h in soup.find_all('h3'):
        a = h.find('a')
        if not a or not a.text:
            continue
        title = a.text.strip()
        href = a.get('href')
        if href and href.startswith('/'):
            href = 'https://finance.yahoo.com' + href
        # attempt to extract time nearby
        pub = None
        items.append({'ticker': ticker, 'published_at': pub, 'source': 'yahoo', 'title': title, 'summary': None, 'url': href})
    return items, r


def write_rows(rows, out):
    if not rows:
        return
    df = pd.DataFrame(rows)
    df['fetched_at'] = pd.Timestamp.utcnow()
    # canonicalize published_at
    try:
        df['published_at'] = pd.to_datetime(df['published_at'])
    except Exception:
        pass
    if os.path.exists(out):
        old = pd.read_parquet(out)
        df = pd.concat([old, df], ignore_index=True)
        df = df.drop_duplicates(subset=['ticker', 'title', 'url'], keep='first')
    df.to_parquet(out, index=False)
    print('wrote', out, 'rows', len(df))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--tickers-file', help='CSV of tickers (Symbol/ticker column)', default=None)
    p.add_argument('--sample', type=int, default=0, help='Process only first N tickers (for tests)')
    p.add_argument('--out', default='data/weekly_headlines.parquet')
    p.add_argument('--checkpoint', default='data/fetch_headlines_check.json', help='Path to checkpoint JSON to resume')
    # Default NewsAPI limit is 0 (disabled) to prefer Finnhub only; set >0 to enable NewsAPI fallback
    p.add_argument('--newsapi-daily-limit', type=int, default=0, help='Max NewsAPI calls per run/day (0 to disable)')
    p.add_argument('--days', type=int, default=7, help='How many days back to fetch')
    p.add_argument('--use-scrape', action='store_true', help='Fallback to scraping Yahoo Finance when APIs fail')
    p.add_argument('--sleep', type=float, default=1.0, help='Base seconds between requests (will be adjusted by Finnhub rate limit if provided)')
    p.add_argument('--finnhub-per-minute', type=int, default=60, help='Target Finnhub calls per minute (throttle). If 0, no Finnhub throttling enforced.')
    p.add_argument('--parallel-workers', type=int, default=4, help='Number of parallel worker threads to use for fetching (will be capped by number of available Finnhub API keys).')
    args = p.parse_args()
    args.parallel_workers = 4 # Default to 4 parallel workers

    cfg = dotenv_values('keys.env')
    # support multiple Finnhub keys for parallel fetching
    finnhub_keys = []
    if cfg.get('FINNHUB_API_KEY'):
        finnhub_keys.append(cfg.get('FINNHUB_API_KEY'))
    if cfg.get('FINNHUB2_API_KEY'):
        finnhub_keys.append(cfg.get('FINNHUB2_API_KEY'))

    tickers = load_tickers(args.tickers_file, sample=args.sample)
    print('tickers to process:', len(tickers))

    # load checkpoint
    # Always reset the checkpoint for a fresh weekly run.
    processed = set()
    newsapi_calls = 0
    if os.path.exists(args.checkpoint):
        os.remove(args.checkpoint)
        print("Removed old checkpoint file to ensure a fresh run.")

    frm = (datetime.datetime.utcnow() - datetime.timedelta(days=args.days)).strftime('%Y-%m-%d')
    to = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    # compute an initial per-call sleep target based on requested finnhub-per-minute
    fh_per_min = max(0, int(args.finnhub_per_minute)) if hasattr(args, 'finnhub_per_minute') else 60
    # default per-call sleep (seconds) when using Finnhub to respect per-minute target
    if fh_per_min and fh_per_min > 0:
        finnhub_sleep = max(args.sleep, 60.0 / float(fh_per_min))
    else:
        finnhub_sleep = args.sleep

    # If multiple Finnhub keys are present, run parallel workers that divide
    # the tickers between them. Each worker will persist intermittently using a lock.
    lock = threading.Lock()
    workers = max(1, min(len(finnhub_keys) if finnhub_keys else 1, args.parallel_workers if hasattr(args, 'parallel_workers') else (len(finnhub_keys) or 1)))

    # provide a default parallel-workers arg if not present
    try:
        pw = int(getattr(args, 'parallel_workers', workers))
    except Exception:
        pw = workers

    # Build list of key(s) to use; if fewer keys than workers, keys will be reused
    if finnhub_keys:
        key_list = finnhub_keys
    else:
        key_list = [None]

    # Worker function
    def _worker(ticker_subset, api_key, worker_id=0):
        local_rows = []
        for idx, t in enumerate(ticker_subset, start=1):
            t = t.strip().upper()
            if t in processed:
                continue
            print(f'[W{worker_id} {idx}/{len(ticker_subset)}] {t}')
            got = False
            # finnhub only (we prefer no NewsAPI by default)
            if api_key:
                try:
                    items, resp = finnhub_company_news(t, api_key, frm, to)
                    if items:
                        local_rows.extend(items)
                        got = True
                    # adapt to headers for respectful throttling
                    if resp is not None and 'x-ratelimit-limit' in resp.headers:
                        try:
                            limit = int(resp.headers.get('x-ratelimit-limit', 60))
                        except Exception:
                            limit = 60
                        server_sleep = 60.0 / max(1, limit)
                        time.sleep(max(args.sleep, finnhub_sleep, server_sleep))
                    else:
                        time.sleep(finnhub_sleep)
                except Exception as e:
                    print('finnhub error', e)

            # optional fallback scrape
            if (not got) and args.use_scrape:
                try:
                    items, resp = scrape_yahoo(t)
                    if items:
                        local_rows.extend(items)
                        got = True
                    time.sleep(args.sleep)
                except Exception as e:
                    print('scrape error', e)

            # Periodically flush to disk and update shared checkpoint
            if len(local_rows) >= 25:
                with lock:
                    write_rows(local_rows, args.out)
                    local_rows = []
                    processed.update([t for t in ticker_subset if t])
                    try:
                        ck = {'processed': list(processed), 'newsapi_calls': newsapi_calls, 'last_index': len(processed)}
                        with open(args.checkpoint, 'w') as f:
                            json.dump(ck, f)
                    except Exception as e:
                        print('checkpoint save failed', e)
        # final flush for this worker
        if local_rows:
            with lock:
                write_rows(local_rows, args.out)
                processed.update([t.strip().upper() for t in ticker_subset])
                try:
                    ck = {'processed': list(processed), 'newsapi_calls': newsapi_calls, 'last_index': len(processed)}
                    with open(args.checkpoint, 'w') as f:
                        json.dump(ck, f)
                except Exception as e:
                    print('checkpoint save failed', e)

    # Split tickers evenly across requested parallel workers
    if pw > 1 and len(tickers) > 1:
        parts = [[] for _ in range(pw)]
        for i, tk in enumerate(tickers):
            parts[i % pw].append(tk)
        threads = []
        for wid in range(pw):
            api = key_list[wid % len(key_list)] if key_list else None
            th = threading.Thread(target=_worker, args=(parts[wid], api, wid), daemon=True)
            threads.append(th)
            th.start()
        for th in threads:
            th.join()
    else:
        # single-threaded behavior (uses first key if available)
        api = key_list[0] if key_list else None
        _worker(tickers, api, 0)
    # final checkpoint
    try:
        processed.update([t.strip().upper() for t in tickers])
        ck = {'processed': list(processed), 'newsapi_calls': newsapi_calls, 'last_index': len(tickers)}
        with open(args.checkpoint, 'w') as f:
            json.dump(ck, f)
        print('final checkpoint saved')
    except Exception as e:
        print('final checkpoint save failed', e)


if __name__ == '__main__':
    main()
