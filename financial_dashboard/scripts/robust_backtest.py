#!/usr/bin/env python3
"""Robust walk-forward backtest and comparison for multiple model run folders.

Outputs a comparison CSV and per-model backtest series.
"""
import argparse
from pathlib import Path
import pandas as pd
import numpy as np


def load_scored(scored_path):
    df = pd.read_csv(scored_path, parse_dates=['date'] if 'date' in pd.read_csv(scored_path, nrows=0).columns else None)
    return df


def align_with_snapshots(scored_df, snapshots_df, target):
    # ensure date dtype
    if 'date' in snapshots_df.columns:
        snapshots_df['date'] = pd.to_datetime(snapshots_df['date'])
    if 'date' in scored_df.columns:
        scored_df['date'] = pd.to_datetime(scored_df['date'])
    # merge on ticker+date when possible
    if 'date' in scored_df.columns and 'date' in snapshots_df.columns:
        merged = scored_df.merge(snapshots_df[['ticker','date',target]], on=['ticker','date'], how='left')
    else:
        merged = scored_df.merge(snapshots_df[['ticker',target]], on=['ticker'], how='left')
    return merged


def compute_backtest(merged, date_col='date', target_col='ret_1m', pred_col='stack_pred', top_k=20, cost_pct=0.0):
    # Build per-period portfolio returns and turnover
    df = merged.copy()
    if date_col not in df.columns:
        # assign today's timestamp for all
        df[date_col] = pd.Timestamp.utcnow().normalize()
    # filter rows with required columns
    df = df.dropna(subset=[pred_col, target_col])
    if df.empty:
        return None, None
    dates = sorted(df[date_col].dropna().unique())
    period_returns = []
    period_dates = []
    period_hit_rates = []
    period_turnovers = []
    prev_set = None
    for d in dates:
        sub = df[df[date_col] == d]
        if sub.empty:
            continue
        top = sub.sort_values(pred_col, ascending=False).head(top_k)
        if top.empty:
            continue
        # realized return is target_col as stored in snapshots (assumed aligned)
        mean_ret = float(np.nanmean(top[target_col].astype(float)))
        # turnover vs prev_set
        curr_set = set(top['ticker'].astype(str).tolist())
        if prev_set is None:
            turnover = 1.0  # assume full turnover at start
        else:
            changed = curr_set.symmetric_difference(prev_set)
            turnover = len(changed) / float(top_k)
        prev_set = curr_set
        # hit rate
        hit = float((top[target_col] > 0).mean())
        # apply simple transaction cost proportional to turnover
        net_ret = mean_ret - (cost_pct * turnover)
        period_returns.append(net_ret)
        period_dates.append(pd.to_datetime(d))
        period_hit_rates.append(hit)
        period_turnovers.append(turnover)

    if not period_returns:
        return None, None

    ret_series = pd.DataFrame({'date': period_dates, 'period_ret': period_returns, 'hit_rate': period_hit_rates, 'turnover': period_turnovers})

    # compute average period length in days
    if len(ret_series) > 1:
        diffs = np.diff(sorted(ret_series['date'].astype('int64') // 10**9))
        # convert seconds to days
        days = np.median(diffs) / (24*3600)
        days_per_period = max(1.0, days)
    else:
        days_per_period = 7.0

    periods_per_year = 365.0 / days_per_period

    # cumulative return
    cum = np.prod(1.0 + np.array(period_returns)) - 1.0
    # annualized return
    ann = (1.0 + cum) ** (periods_per_year / len(period_returns)) - 1.0 if len(period_returns) > 0 else np.nan
    # sharpe
    mean_r = np.mean(period_returns)
    std_r = np.std(period_returns, ddof=1) if len(period_returns) > 1 else 0.0
    sharpe = (mean_r / (std_r + 1e-12)) * np.sqrt(periods_per_year) if std_r > 0 else np.nan
    # max drawdown computed from cumulative time series
    cum_ts = np.cumprod(1.0 + np.array(period_returns)) - 1.0
    peak = np.maximum.accumulate(cum_ts)
    drawdown = peak - cum_ts
    max_dd = float(np.max(drawdown)) if drawdown.size > 0 else 0.0
    # average hit rate and turnover
    avg_hit = float(np.mean(period_hit_rates))
    avg_turn = float(np.mean(period_turnovers))

    metrics = {'periods': len(period_returns), 'cum_return': float(cum), 'annual_return': float(ann), 'sharpe': float(sharpe) if not np.isnan(sharpe) else None, 'max_drawdown': float(max_dd), 'avg_hit_rate': avg_hit, 'avg_turnover': avg_turn, 'days_per_period': days_per_period}

    return ret_series, metrics


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--model-dirs', nargs='+', required=True, help='List of model run directories to compare')
    p.add_argument('--snapshots', required=True)
    p.add_argument('--target', default='ret_1m')
    p.add_argument('--top-k', type=int, default=20)
    p.add_argument('--cost-pct', type=float, default=0.0, help='Transaction cost per turnover unit (fraction)')
    args = p.parse_args()

    snaps = pd.read_parquet(args.snapshots)
    if 'date' in snaps.columns:
        snaps['date'] = pd.to_datetime(snaps['date'])

    results = []
    per_model_series = {}
    for md in args.model_dirs:
        mdp = Path(md)
        # find latest scored file
        scored_files = sorted(list(mdp.glob('scored_full_*.csv')))
        if not scored_files:
            print('No scored file in', md)
            continue
        scored = load_scored(scored_files[-1])
        merged = align_with_snapshots(scored, snaps, args.target)
        # if target missing in merged, try fallbacks
        target = args.target
        if target not in merged.columns:
            for alt in ['ret_21d','ret_1m','ret_3m','ret_5d']:
                if alt in merged.columns:
                    print(f"Target '{target}' not in merged for {md}; falling back to {alt}")
                    target = alt
                    break
        if target not in merged.columns:
            print('No suitable target found for', md)
            continue
        pred_col = 'stack_pred' if 'stack_pred' in merged.columns else ('oof_pred' if 'oof_pred' in merged.columns else None)
        if pred_col is None:
            # try to find a numeric pred-like column
            candidates = [c for c in merged.columns if 'pred' in c or 'score' in c]
            pred_col = candidates[0] if candidates else None
        if pred_col is None:
            print('No prediction column found for', md)
            continue
        series, metrics = compute_backtest(merged, date_col='date', target_col=target, pred_col=pred_col, top_k=args.top_k, cost_pct=args.cost_pct)
        if series is None:
            print('No valid series for', md)
            continue
        results.append({'model_dir': md, **metrics})
        per_model_series[md] = series

    out = pd.DataFrame(results)
    ts = pd.Timestamp.utcnow().strftime('%Y%m%d')
    out_path = Path('models') / f'backtest_comparison_{ts}.csv'
    out.to_csv(out_path, index=False)
    print('Wrote comparison to', out_path)
    # also write per-model series
    for k, s in per_model_series.items():
        fn = Path(k) / f'backtest_series_{ts}.csv'
        s.to_csv(fn, index=False)
        print('Wrote series for', k, 'to', fn)


if __name__ == '__main__':
    main()
