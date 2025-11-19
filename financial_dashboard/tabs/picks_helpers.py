"""
Picks helpers: small utilities to find the latest picks CSV and load it as a DataFrame.
This is intentionally lightweight and used by multiple tabs to avoid importing large modules.
"""
import os
import glob
import re
from datetime import datetime

import pandas as pd

from financial_dashboard from financial_dashboard import _shared as SH


def _find_latest_picks_generic(patterns=None):
    """Find the most recent picks CSV using patterns relative to DASH_ROOT.

    Returns the path to the most recent candidate or None.
    """
    try:
        dash_root = SH.DASH_ROOT
    except Exception:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        dash_root = os.path.dirname(base_dir)

    if patterns is None:
        patterns = ['models/**/picks_*.csv', 'picks/picks_*.csv', 'models/**/monthlypicks*.csv', 'models/**/weeklypicks*.csv']

    candidates = []
    for pattern in patterns:
        path = os.path.join(dash_root, pattern)
        found = glob.glob(path, recursive=True)
        candidates.extend(found)

    if not candidates:
        return None

    def _parse_date_from_name(path):
        filename = os.path.basename(path)
        m_yyyymmdd = re.search(r'(\d{8})', filename)
        if m_yyyymmdd:
            try:
                return datetime.strptime(m_yyyymmdd.group(1), '%Y%m%d').date()
            except Exception:
                pass
        m_mmdd = re.search(r'(\d{4})', filename)
        if m_mmdd:
            try:
                year = datetime.now().year
                return datetime.strptime(str(year) + m_mmdd.group(1), '%Y%m%d').date()
            except Exception:
                pass
        return None

    def _is_picks_prefix(p):
        return os.path.basename(p).lower().startswith('picks_')

    def _in_full_run(p):
        return ('models' + os.sep + 'full_run') in p or '/full_run/' in p or '\\full_run\\' in p

    def _sort_key(p):
        parsed = _parse_date_from_name(p) or datetime.min.date()
        try:
            mtime = os.path.getmtime(p)
        except Exception:
            mtime = 0
        return (_is_picks_prefix(p), _in_full_run(p), parsed, mtime)

    candidates.sort(key=_sort_key, reverse=True)
    return candidates[0]


def _load_picks_df(path, limit=50):
    """Load picks CSV into pandas DataFrame; normalize column names."""
    try:
        if not path or not os.path.exists(path):
            return None
        df = pd.read_csv(path)
        # Normalize common column names
        cols = [c.strip() for c in df.columns]
        df.columns = cols
        if 'symbol' in df.columns and 'ticker' not in df.columns:
            df = df.rename(columns={'symbol': 'ticker'})
        # also try lowercase variants
        lowered = [c.lower() for c in df.columns]
        if 'ticker' not in lowered and 'symbol' in lowered:
            # find index
            idx = lowered.index('symbol')
            df['ticker'] = df.iloc[:, idx]
        # final check
        if 'ticker' not in df.columns and 'ticker' not in [c.lower() for c in df.columns]:
            return None
        # ensure ticker column normalized
        df['ticker'] = df['ticker'].astype(str).str.strip()
        return df.head(limit)
    except Exception:
        return None
