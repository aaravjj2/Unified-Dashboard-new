"""Inspect monthly and weekly picks and compute derived portfolio analytics pieces."""
from tabs import attribution_analysis as ta
import pandas as pd
import numpy as np

mp = ta._find_latest_picks_generic(patterns=['models/**/picks_*.csv','models/**/monthlypicks*.csv','picks/picks_*.csv'])
from weekly_picks_flask import find_latest_weekly_csv
wp = find_latest_weekly_csv()
print('Monthly path:', mp)
print('Weekly path:', wp)

mdf = ta._load_picks_df(mp)
wdf = ta._load_picks_df(wp)
print('Monthly rows:', None if mdf is None else len(mdf))
print('Weekly rows:', None if wdf is None else len(wdf))

# Sector exposure from monthly picks if available
sector_data = None
try:
    import yfinance as yf
    if mdf is not None:
        sector_map = {}
        for t in mdf['ticker'].astype(str).tolist():
            try:
                info = yf.Ticker(t).info
                sector = info.get('sector') or 'Other'
            except Exception:
                sector = 'Other'
            sector_map[sector] = sector_map.get(sector, 0) + 1
        total = sum(sector_map.values())
        sector_data = {k: v/total for k,v in sector_map.items()}
except Exception as e:
    sector_data = None

print('Sector exposure (sample):', sector_data)

# Factor exposures from monthly picks columns
factors = {}
if mdf is not None:
    if 'r1m' in mdf.columns:
        factors['Momentum'] = mdf['r1m'].mean()
    if 'composite' in mdf.columns:
        factors['Composite'] = mdf['composite'].mean()
    if 'ma50_vs200' in mdf.columns:
        factors['MA50_vs200'] = mdf['ma50_vs200'].mean()
print('Factor exposures (sample):', factors)

# VaR approx using weekly tickers
var_est = None
try:
    if wdf is not None:
        import yfinance as yf
        tickers = wdf['ticker'].astype(str).tolist()
        data = yf.download(' '.join(tickers), period='3mo', interval='1d', progress=False, threads=True, auto_adjust=True)
        vols = {}
        for t in tickers:
            try:
                if len(tickers) == 1:
                    series = data['Close']
                else:
                    if isinstance(data.columns, pd.MultiIndex):
                        series = data['Close'][t].dropna()
                    else:
                        series = data['Close'].dropna()
                ret = series.pct_change().dropna()
                vols[t] = ret.std()
            except Exception:
                vols[t] = 0.0
        var_est = vols
except Exception as e:
    var_est = None
print('VaR vol estimates (sample):', var_est)

# Slippage via weekly_picks_flask.get_live_prices
try:
    from weekly_picks_flask import get_live_prices
    if wdf is not None:
        wk = wdf['ticker'].astype(str).tolist()
        prices = get_live_prices(wk)
        # compute simple bps list
        bps = []
        for t in wk:
            p = prices.get(t, {})
            if p:
                try:
                    cur = float(p.get('current_price',0))
                    start = float(p.get('week_start_price',cur))
                    if start>0:
                        pct = (cur - start)/start*100
                        bps.append(pct*100)
                except Exception:
                    pass
        print('Sample slippage bps summary: mean=', None if len(bps)==0 else sum(bps)/len(bps))
except Exception as e:
    print('Could not compute slippage via live prices:', e)
