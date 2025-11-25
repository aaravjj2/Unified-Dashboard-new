#!/usr/bin/env python3
"""
Lightweight Picks Pipeline Runner
Provides deterministic, auditable, and resumable runs for weekly/monthly picks.

Usage:
  python tools/picks_run.py --type weekly --mode dryrun
  python tools/picks_run.py --type weekly --mode publish

This script implements the stages described in the design: load, normalize,
enrich, score, select, validate, and persist. All artifacts are written to
`reports/picks/runs/<run_id>/` and a `manifest.json` is saved.
"""
import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Dict, Any, List, Tuple
import logging

import pandas as pd
from financial_dashboard.utils.news_client import fetch_news_for_tickers

logger = logging.getLogger(__name__)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RUNS_DIR = os.path.join(REPO_ROOT, 'reports', 'picks', 'runs')
CANONICAL_INPUT_DIR = os.path.join(REPO_ROOT, 'data', 'picks_input')
PUBLISHED_DIR = os.path.join(REPO_ROOT, 'data', 'picks_published')
os.makedirs(RUNS_DIR, exist_ok=True)
os.makedirs(CANONICAL_INPUT_DIR, exist_ok=True)
os.makedirs(PUBLISHED_DIR, exist_ok=True)


def compute_checksum_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def compute_file_checksum(path: str) -> str:
    with open(path, 'rb') as f:
        return compute_checksum_bytes(f.read())


def git_sha() -> str:
    try:
        out = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO_ROOT)
        return out.decode().strip()
    except Exception:
        return 'local'


def load_canonical_source(run_type: str) -> pd.DataFrame:
    """Load canonical CSV source for run_type.
    Falls back to existing data files if canonical not present.
    """
    fn = os.path.join(CANONICAL_INPUT_DIR, f'{run_type}_source.csv')
    if os.path.exists(fn):
        df = pd.read_csv(fn)
        print(f"Loaded canonical CSV: {fn}")
        return df

    # Fallbacks: data/picks/<file>.csv or outputs/picks_*.csv
    fallback = os.path.join(REPO_ROOT, 'data', 'picks', f'{run_type}_source.csv')
    if os.path.exists(fallback):
        return pd.read_csv(fallback)

    # Last resort: try outputs/market_brief.json detailed
    outp = os.path.join(REPO_ROOT, 'financial_dashboard', 'outputs', 'market_brief.json')
    if os.path.exists(outp):
        j = json.load(open(outp, 'r', encoding='utf-8'))
        records = j.get('detailed', [])
        if records:
            return pd.DataFrame(records)

    return pd.DataFrame()


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if 'ticker' not in df.columns and 'Ticker' in df.columns:
        df = df.rename(columns={'Ticker': 'ticker'})
    if 'ticker' in df.columns:
        df['ticker'] = df['ticker'].astype(str).str.upper().str.strip()
    # normalize numeric columns: try to cast common names
    for col in list(df.columns):
        if col.lower() in ('current_price', 'price', 'close', 'close_price'):
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except Exception:
                pass
    # drop exact duplicates on ticker
    if 'ticker' in df.columns:
        df = df.drop_duplicates(subset=['ticker'])
    df = df.reset_index(drop=True)
    return df


def enrich_with_prices(df: pd.DataFrame, sh_module) -> pd.DataFrame:
    df = df.copy()
    prices = (sh_module.RESULTS_CACHE.get('results') or {}).get('prices', {})
    # If price missing, attempt to call update_cache_with_missing (price_fetcher)
    missing = []
    for t in df.get('ticker', []):
        if t not in prices:
            missing.append(t)
    if missing:
        try:
            from financial_dashboard.utils.price_fetcher import update_cache_with_missing
            updated, fetched = update_cache_with_missing((sh_module.RESULTS_CACHE.get('results') or {}), missing)
            if fetched:
                sh_module.RESULTS_CACHE['results'] = updated
                prices = updated.get('prices', {})
        except Exception:
            pass

    # merge fields
    out = []
    for _, row in df.iterrows():
        rec = row.to_dict()
        t = rec.get('ticker')
        p = prices.get(t) or prices.get(t.upper())
        if p and isinstance(p, dict):
            # common fields
            if 'current_price' in p:
                rec['current_price'] = p.get('current_price')
            elif 'start_price' in p and 'month_start_price' not in rec:
                rec['current_price'] = p.get('start_price')
            if 'month_start_price' in p:
                rec['month_start_price'] = p.get('month_start_price')
            if 'week_start_price' in p:
                rec['week_start_price'] = p.get('week_start_price')
            if 'daily_change' in p:
                rec['daily_change'] = p.get('daily_change')
            if 'profit_loss' in p:
                rec['profit_loss'] = p.get('profit_loss')
            if 'source' in p:
                rec['price_source'] = p.get('source')
        out.append(rec)
    return pd.DataFrame(out)


_NEWS_BULLISH_KEYWORDS = {
    'beat', 'beats', 'beats expectations', 'outperform', 'upgrade', 'surge', 'soar',
    'rally', 'gain', 'gains', 'strong', 'record', 'growth', 'positive', 'buy', 'bull',
    'acquisition', 'beat guidance'
}

_NEWS_BEARISH_KEYWORDS = {
    'miss', 'missed', 'downgrade', 'underperform', 'drop', 'decline', 'fall', 'weak',
    'loss', 'losses', 'plummet', 'negative', 'sell', 'warning', 'cut guidance', 'lower guidance', 'recall'
}


def _headline_sentiment_score(headline: str, ticker: str = '') -> Dict[str, Any]:
    if not headline:
        return {'sentiment': 'Neutral', 'score': 0.0}

    text = headline.lower()
    score = 0.0

    for kw in _NEWS_BULLISH_KEYWORDS:
        if kw in text:
            score += 1.0
    for kw in _NEWS_BEARISH_KEYWORDS:
        if kw in text:
            score -= 1.0

    if ticker and ticker.lower() in text:
        if any(kw in text for kw in ['beat', 'beats', 'upgrade', 'surge', 'rally', 'gain']):
            score += 0.25
        if any(kw in text for kw in ['miss', 'missed', 'downgrade', 'drop', 'decline', 'loss']):
            score -= 0.25

    sentiment = 'Neutral'
    if score >= 1.5:
        sentiment = 'Bullish'
    elif score <= -1.5:
        sentiment = 'Bearish'

    return {'sentiment': sentiment, 'score': round(score, 2)}


def _aggregate_news_sentiment(news_items: List[Dict[str, Any]], ticker: str) -> Dict[str, Any]:
    if not news_items:
        return {'sentiment': 'Neutral', 'score': 0.0, 'count': 0}

    scores = []
    summaries = []
    for item in news_items:
        score_data = _headline_sentiment_score(item.get('headline', ''), ticker)
        scores.append(score_data['score'])
        summaries.append({
            'headline': item.get('headline'),
            'source': item.get('source'),
            'sentiment': score_data['sentiment'],
            'score': score_data['score']
        })

    avg_score = sum(scores) / len(scores)
    sentiment = 'Neutral'
    if avg_score >= 1.0:
        sentiment = 'Bullish'
    elif avg_score <= -1.0:
        sentiment = 'Bearish'

    return {
        'sentiment': sentiment,
        'score': round(avg_score, 2),
        'count': len(news_items),
        'headlines': summaries
    }


def attach_news_sentiment(df: pd.DataFrame, params: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    include_news = params.get('include_news', True)
    news_items_per_ticker = params.get('news_items_per_ticker', 3)
    df = df.copy()

    if 'ticker' not in df.columns:
        return df, {'included': False, 'reason': 'ticker_column_missing'}

    if not include_news:
        return df, {'included': False, 'reason': 'disabled'}

    tickers = [t for t in df['ticker'].dropna().unique()]
    if not tickers:
        return df, {'included': True, 'reason': 'no_tickers', 'ticker_summary': {}, 'news_items': {}}

    if 'sentiment_score' not in df.columns:
        df['sentiment_score'] = 0.0
    if 'sentiment_signal' not in df.columns:
        df['sentiment_signal'] = 'Neutral'

    news_meta = {'included': True, 'news_items_count': 0, 'ticker_summary': {}, 'news_items': {}}
    try:
        news_data = fetch_news_for_tickers(tickers, max_per_ticker=news_items_per_ticker)
        total_items = 0
        for ticker in tickers:
            items = news_data.get(ticker, []) or []
            summary = _aggregate_news_sentiment(items, ticker)
            news_meta['ticker_summary'][ticker] = summary
            mask = df['ticker'] == ticker
            df.loc[mask, 'sentiment_score'] = summary['score']
            df.loc[mask, 'sentiment_signal'] = summary['sentiment']
            news_meta['news_items'][ticker] = items
            total_items += len(items)

        news_meta['news_items_count'] = total_items
        news_meta['max_items_per_ticker'] = news_items_per_ticker
        logger.info(f"News sentiment attached for {len(tickers)} tickers ({total_items} headlines)")

    except Exception as e:
        logger.warning(f"Failed to fetch news for sentiment enrichment: {e}")
        news_meta['error'] = str(e)

    return df, news_meta


def deterministic_score(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    # Simple deterministic hybrid score using available fields
    df = df.copy()
    # Ensure numeric columns exist
    for col in ('combined_score', 'momentum_score', 'fundamental_score', 'sentiment_score'):
        if col not in df.columns:
            df[col] = 0.0
    # normalize via rank (higher better) to [0,1]
    for col in ('combined_score', 'momentum_score', 'fundamental_score', 'sentiment_score'):
        df[f'rank_{col}'] = df[col].rank(method='first', pct=True).fillna(0.0)

    w1 = params.get('w1', 0.4)
    w2 = params.get('w2', 0.3)
    w3 = params.get('w3', 0.2)
    w4 = params.get('w4', 0.1)

    df['score'] = (
        w1 * df['rank_combined_score'] +
        w2 * df['rank_momentum_score'] +
        w3 * (1 - df['rank_fundamental_score']) +
        w4 * df['rank_sentiment_score']
    )
    # deterministic tie-breaker: ticker string
    df = df.sort_values(by=['score', 'ticker'], ascending=[False, True])
    df['rank'] = range(1, len(df) + 1)
    return df


def apply_selection(df: pd.DataFrame, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    max_per_sector = params.get('max_per_sector', 3)
    top_n = params.get('top_n', 12)
    selected = []
    sector_count = defaultdict(int)
    for _, row in df.iterrows():
        if len(selected) >= top_n:
            break
        sector = row.get('sector') or row.get('Sector') or 'UNKNOWN'
        if sector_count[sector] >= max_per_sector:
            continue
        # liquidity filter example
        adv = row.get('avg_daily_volume') or row.get('average_volume') or 0
        if adv and adv < params.get('min_avg_volume', 0):
            continue
        selected.append(row.to_dict())
        sector_count[sector] += 1
    return selected


def validate_selected(selected: List[Dict[str, Any]], params: Dict[str, Any]) -> Dict[str, Any]:
    report = {'passed': True, 'errors': []}
    if not selected:
        report['passed'] = False
        report['errors'].append('No picks selected')
        return report
    # Check tickers and prices
    for rec in selected:
        if not rec.get('ticker'):
            report['passed'] = False
            report['errors'].append('Missing ticker in selection')
        price = rec.get('current_price')
        if price is None or not isinstance(price, (int, float)) or price <= 0:
            report['passed'] = False
            report['errors'].append(f"Invalid price for {rec.get('ticker')}: {price}")
    # Diversity check
    sectors = [r.get('sector') or r.get('Sector') or 'UNKNOWN' for r in selected]
    from collections import Counter
    c = Counter(sectors)
    max_share = max(c.values()) / max(1, len(selected))
    if max_share > params.get('max_sector_share', 0.5):
        report['passed'] = False
        report['errors'].append('Sector concentration exceeds threshold')
    return report


def save_artifacts(run_dir: str, artifacts: Dict[str, Any]):
    for name, obj in artifacts.items():
        path = os.path.join(run_dir, name)
        if isinstance(obj, pd.DataFrame):
            obj.to_csv(path, index=False)
        else:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(obj, f, indent=2, default=str)


def persist_picks(run_id: str, selected: List[Dict[str, Any]], run_manifest: Dict[str, Any]):
    # For simplicity, persist to JSON file in PUBLISHED_DIR and to data/picks
    fn = os.path.join(PUBLISHED_DIR, f'selected_picks_{run_id}.json')
    with open(fn, 'w', encoding='utf-8') as f:
        json.dump({'run_id': run_id, 'selected': selected, 'manifest': run_manifest}, f, indent=2, default=str)
    # Also write a canonical published file used by UI
    pub_canonical = os.path.join(REPO_ROOT, 'data', 'picks', f'weekly_picks_published.json')
    os.makedirs(os.path.dirname(pub_canonical), exist_ok=True)
    with open(pub_canonical, 'w', encoding='utf-8') as f:
        json.dump({'run_id': run_id, 'selected': selected}, f, indent=2, default=str)


def run_pipeline(run_type: str, mode: str = 'dryrun', params: Dict[str, Any] = None, seed: str = None):
    params = params or {}
    run_id = str(uuid.uuid4())
    run_dir = os.path.join(RUNS_DIR, run_id)
    os.makedirs(run_dir, exist_ok=True)

    manifest = {
        'run_id': run_id,
        'run_type': run_type,
        'git_sha': git_sha(),
        'params': params,
        'mode': mode,
        'seed': seed or run_id,
        'started_at': datetime.utcnow().isoformat()
    }

    # Stage 1: Load canonical
    df_raw = load_canonical_source(run_type)
    manifest['inputs_count'] = len(df_raw)
    # save input checksum(s)
    inputs_checksum = {}
    try:
        if not df_raw.empty and 'ticker' in df_raw.columns:
            # create a CSV snapshot and checksum
            inp_csv = os.path.join(run_dir, 'normalized_input_snapshot.csv')
            df_raw.to_csv(inp_csv, index=False)
            inputs_checksum['input_csv'] = compute_file_checksum(inp_csv)
    except Exception:
        pass

    # Stage 2: Normalize & Clean
    df_norm = normalize_df(df_raw)
    df_norm.to_csv(os.path.join(run_dir, 'normalized.csv'), index=False)
    inputs_checksum['normalized_csv'] = compute_file_checksum(os.path.join(run_dir, 'normalized.csv'))

    # Stage 3: Enrich with prices
    try:
        import importlib
        sh = importlib.import_module('financial_dashboard._shared')
    except Exception:
        sh = None
    df_enriched = enrich_with_prices(df_norm, sh) if sh is not None else df_norm
    df_enriched, news_meta = attach_news_sentiment(df_enriched, params)
    df_enriched.to_csv(os.path.join(run_dir, 'enriched.csv'), index=False)
    manifest['news'] = news_meta

    # Stage 4: Score deterministically
    df_scored = deterministic_score(df_enriched, params)
    df_scored.to_csv(os.path.join(run_dir, 'scored.csv'), index=False)

    # Stage 5: Filter & Select
    selected = apply_selection(df_scored, params)
    with open(os.path.join(run_dir, 'selected.json'), 'w', encoding='utf-8') as f:
        json.dump(selected, f, indent=2, default=str)

    # Stage 6: Validate
    validation = validate_selected(selected, params)
    with open(os.path.join(run_dir, 'validation.json'), 'w', encoding='utf-8') as f:
        json.dump(validation, f, indent=2, default=str)

    manifest['inputs_checksum'] = inputs_checksum
    manifest['validation'] = validation
    manifest['finished_at'] = datetime.utcnow().isoformat()

    # Save manifest
    with open(os.path.join(run_dir, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, default=str)

    # Archive successful artifacts summary
    artifacts = {
        'normalized.csv': df_norm,
        'enriched.csv': df_enriched,
        'scored.csv': df_scored,
        'selected.json': selected,
        'validation.json': validation,
        'manifest.json': manifest,
        'news_summary.json': news_meta
    }
    save_artifacts(run_dir, artifacts)

    # Dry-run vs publish
    if mode == 'dryrun':
        print(f"Dry-run complete. Artifacts in: {run_dir}")
        return manifest, run_dir
    elif mode == 'publish':
        if not validation.get('passed'):
            print('Validation failed; aborting publish')
            return manifest, run_dir
        persist_picks(run_id, selected, manifest)
        print(f"Published picks for run {run_id}")
        return manifest, run_dir
    else:
        raise ValueError('Unknown mode')


def main():
    parser = argparse.ArgumentParser(description='Picks pipeline runner')
    parser.add_argument('--type', choices=['weekly', 'monthly'], default='weekly')
    parser.add_argument('--mode', choices=['dryrun', 'publish'], default='dryrun')
    parser.add_argument('--seed', default=None)
    parser.add_argument('--top-n', type=int, default=12)
    parser.add_argument('--min-avg-volume', type=int, default=0)
    parser.add_argument('--max-per-sector', type=int, default=3)
    parser.add_argument('--max-sector-share', type=float, default=0.5)
    parser.add_argument('--skip-news', action='store_true', help='Disable Finnhub news enrichment when rerunning picks')
    parser.add_argument('--news-items-per-ticker', type=int, default=3, help='How many news headlines per ticker to fetch')
    args = parser.parse_args()

    params = {
        'top_n': args.top_n,
        'min_avg_volume': args.min_avg_volume,
        'max_per_sector': args.max_per_sector,
        'max_sector_share': args.max_sector_share,
        # scoring weights
        'w1': 0.4, 'w2': 0.3, 'w3': 0.2, 'w4': 0.1,
        'include_news': not args.skip_news,
        'news_items_per_ticker': args.news_items_per_ticker
    }

    manifest, run_dir = run_pipeline(args.type, mode=args.mode, params=params, seed=args.seed)
    print('Run manifest saved to', os.path.join(run_dir, 'manifest.json'))


if __name__ == '__main__':
    main()
