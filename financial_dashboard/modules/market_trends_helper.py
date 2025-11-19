from datetime import datetime
import json, os
import pandas as pd
import plotly.graph_objects as go

BASE_DIR = os.path.dirname(os.path.dirname(__file__)) if '__file__' in globals() else os.getcwd()
OUTPUT_DIR = os.path.join(BASE_DIR, 'output', 'market_trends')

def run_full_analysis(tickers, period='1y', interval='1d', **kwargs):
    """Defensive wrapper used by the Dash server as a lightweight analysis
    implementation. Tries to call the real pipeline when available, but
    falls back to a deterministic mock payload so background jobs don't fail
    when the pipeline or its outputs are missing.

    Accepts legacy kwargs (options, news, cache_only, etc.) and returns a
    dict with keys: ok, detailed, tidy, prices.
    """
    # Normalize tickers into a list
    try:
        if isinstance(tickers, str):
            tickers = [t.strip() for t in tickers.split(',') if t.strip()]
        elif tickers is None:
            tickers = []
        elif not isinstance(tickers, (list, tuple)):
            try:
                tickers = list(tickers)
            except Exception:
                tickers = [str(tickers)]
    except Exception:
        tickers = []

    # Try to call the compute pipeline if it's available
    try:
        from pipelines.compute_market_trends import compute_and_write
        path = compute_and_write(tickers=tickers)
        if path and os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Normalize/augment pipeline output into the UI-friendly shape
            try:
                mt = _map_pipeline_output_to_market_trend(data)
                # attach unified market_trend for backward-compatible UI consumption
                data.setdefault('market_trend', mt)
            except Exception:
                # best-effort: if mapping fails, just return raw data
                pass
            return data
    except Exception:
        # If any of the pipeline imports or execution fails, fall back to mock
        pass

    # Deterministic mock response so the UI can render during debugging.
    rows = []
    for i, t in enumerate(tickers or []):
        rows.append({
            'ticker': t,
            'composite_score': round(0.5 - (i * 0.01), 3),
            'rank': i + 1,
            'signal': 'NEUTRAL'
        })

    payload = {
        'ok': True,
        'detailed': rows,
        'tidy': rows,
        'prices': {},
        'generated_at': datetime.utcnow().isoformat() + 'Z'
    }
    return payload


def build_price_figure(price_rows, title=None):
    """Build a simple Plotly figure from price data.
    price_rows: either a pandas.DataFrame or a list-of-dicts (records) with a date-like index/column and price columns.
    """
    try:
        if price_rows is None:
            return go.Figure()
        if isinstance(price_rows, list):
            df = pd.DataFrame(price_rows)
        elif hasattr(price_rows, 'to_dict') and hasattr(price_rows, 'columns'):
            df = price_rows.copy()
        else:
            df = pd.DataFrame(price_rows)

        # find a date column or use index
        date_col = None
        for cand in ('Date', 'date', 'Datetime', 'datetime', 'index'):
            if cand in df.columns:
                date_col = cand
                break
        if date_col is None:
            # maybe converted rows have the first column as date
            if df.shape[1] >= 1:
                date_col = df.columns[0]

        if date_col is not None:
            try:
                df[date_col] = pd.to_datetime(df[date_col])
            except Exception:
                pass
            x = df[date_col]
        else:
            x = df.index

        # pick close-like column
        y_col = None
        for cand in ('Close', 'Adj Close', 'Adj_Close', 'close', 'close_price'):
            if cand in df.columns:
                y_col = cand
                break
        if y_col is None:
            # fallback to numeric column besides date
            for c in df.columns:
                if c == date_col:
                    continue
                if pd.api.types.is_numeric_dtype(df[c]):
                    y_col = c
                    break

        fig = go.Figure()
        if y_col is not None:
            fig.add_trace(go.Scatter(x=x, y=df[y_col], mode='lines', name=y_col))
        else:
            # plot the first numeric column found
            for c in df.columns:
                if c == date_col:
                    continue
                if pd.api.types.is_numeric_dtype(df[c]):
                    fig.add_trace(go.Scatter(x=x, y=df[c], mode='lines', name=c))
                    break

        fig.update_layout(title=title or '', xaxis_title='Date', yaxis_title='Price')
        return fig
    except Exception:
        return go.Figure()


def load_cached_results_from_outputs():
    # Try to find the latest JSON in OUTPUT_DIR
    try:
        files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.startswith('regime_pred_') and f.endswith('.json')])
        if not files:
            return None
        latest = files[-1]
        path = os.path.join(OUTPUT_DIR, latest)
        with open(path, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return None


def _clip(x, lo=-1.0, hi=1.0):
    try:
        if x is None:
            return 0.0
        v = float(x)
        if v != v:  # NaN
            return 0.0
        return max(lo, min(hi, v))
    except Exception:
        return 0.0


def _map_pipeline_output_to_market_trend(pipeline_json):
    """Map the older pipeline JSON (regime_pred_*.json) into a UI-friendly
    `market_trend` dict that `tabs/market_trends.py` expects.

    The pipeline `detailed` entries include fields like `r1m`, `ma50_vs200`,
    `composite`, `label`. This function picks the best entry (prefer SPY)
    and produces a dict with keys: composite, label, scores (s_r1m, s_ma50_vs200,
    plus placeholders), generated_at, source.
    """
    if not pipeline_json or not isinstance(pipeline_json, dict):
        return None

    detailed = pipeline_json.get('detailed') or []
    if not detailed:
        return None

    # Prefer SPY if present, else first entry
    chosen = None
    for row in detailed:
        try:
            if str(row.get('ticker', '')).upper() == 'SPY':
                chosen = row
                break
        except Exception:
            continue
    if chosen is None:
        chosen = detailed[0]

    r1m = chosen.get('r1m') if isinstance(chosen.get('r1m'), (int, float)) else 0.0
    ma50_vs200 = chosen.get('ma50_vs200') if isinstance(chosen.get('ma50_vs200'), (int, float)) else 0.0
    composite = chosen.get('composite') if isinstance(chosen.get('composite'), (int, float)) else 0.0
    label = chosen.get('label') or chosen.get('regime') or 'Unknown'

    # Build approximate normalized scores similar in spirit to utils.market_trend
    # but keep them transparent and traceable back to pipeline values.
    try:
        s_r1m = _clip(r1m / 0.05)
    except Exception:
        s_r1m = 0.0
    try:
        s_ma50_vs200 = _clip(ma50_vs200 / 0.05)
    except Exception:
        s_ma50_vs200 = 0.0

    scores = {
        's_r1m': s_r1m,
        's_ma50_vs200': s_ma50_vs200,
        # placeholders for compatibility
        's_r3m': 0.0,
        's_r6m': 0.0,
        's_ma50_slope': 0.0,
        's_vix': 0.0,
        's_breadth': 0.0,
    }

    out = {
        'composite': float(composite),
        'label': label,
        'scores': scores,
        'generated_at': pipeline_json.get('generated_at') or chosen.get('generated_at') or datetime.utcnow().isoformat() + 'Z',
        'source': 'pipeline',
        'raw_row': chosen,
    }
    return out
