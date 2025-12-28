import json
import os
from datetime import datetime
import pandas as pd
import numpy as np



def clip(x, lo, hi):
    try:
        if x is None:
            return 0.0
        return max(lo, min(hi, float(x)))
    except Exception:
        return 0.0


def score_from_returns(r, scale):
    return clip(r / scale, -1.0, 1.0)


# backward-compatible single-purpose trend function kept for callers
def compute_market_trend(
    r1m, r3m, r6m,
    ma50_pct_slope, ma50_vs_ma200,
    vix, vix_mean_252, vix_std_252,
    adv_decl_ratio,
    prev_smoothed=None, ema_alpha=0.3
):
    s_r1m = score_from_returns(r1m, 0.05)
    s_r3m = score_from_returns(r3m, 0.12)
    s_r6m = score_from_returns(r6m, 0.20)
    s_ma50_slope = clip(ma50_pct_slope / 0.02, -1.0, 1.0)
    s_ma50_vs200 = clip(ma50_vs_ma200 / 0.05, -1.0, 1.0)
    try:
        vix_z = (vix - vix_mean_252) / max(1e-9, vix_std_252)
    except Exception:
        vix_z = 0.0
    s_vix = clip(-vix_z / 2.0, -1.0, 1.0)
    s_breadth = clip(adv_decl_ratio / 0.4, -1.0, 1.0)

    weights = {
        'r1m': 0.20, 'r3m': 0.15, 'r6m': 0.10,
        'ma50_slope': 0.15, 'ma50_vs200': 0.15,
        'breadth': 0.15, 'vix': 0.10
    }

    composite = (
        weights['r1m'] * s_r1m +
        weights['r3m'] * s_r3m +
        weights['r6m'] * s_r6m +
        weights['ma50_slope'] * s_ma50_slope +
        weights['ma50_vs200'] * s_ma50_vs200 +
        weights['breadth'] * s_breadth +
        weights['vix'] * s_vix
    )
    composite = float(max(-1.0, min(1.0, composite)))

    if prev_smoothed is None:
        smoothed = composite
    else:
        smoothed = ema_alpha * composite + (1 - ema_alpha) * prev_smoothed

    c = smoothed
    if c >= 0.60:
        label = "Strong Bull"
    elif c >= 0.20:
        label = "Bull"
    elif c > -0.20:
        label = "Neutral"
    elif c > -0.60:
        label = "Bear"
    else:
        label = "Strong Bear"

    return {
        'composite': composite,
        'smoothed': smoothed,
        'label': label,
        'scores': {
            's_r1m': s_r1m, 's_r3m': s_r3m, 's_r6m': s_r6m,
            's_ma50_slope': s_ma50_slope, 's_ma50_vs200': s_ma50_vs200,
            's_vix': s_vix, 's_breadth': s_breadth
        }
    }


DEFAULT_STATE_PATH = os.path.join('cache', 'market_trend_state.json')


def compute_market_trend_and_pulse(
    # Trend inputs
    r1m, r3m, r6m,
    ma50_pct_slope, ma50_vs_ma200,
    pct_above_200d,
    vix, vix_mean_252, vix_std_252,
    # Pulse inputs
    r1d, r2d, adv_decl_today, vix_delta, notable_market_news=False,
    # parameters
    ema_alpha=0.25, state_path=DEFAULT_STATE_PATH, persist_state=True
):
    """Compute both a medium-term Trend (smoothed) and short-term Pulse.

    Returns a dict suitable for writing to outputs/market_trend_*.json
    and a simple persisted state containing the smoothed trend value.
    """
    # --- trend scores ---
    s_r1m = score_from_returns(r1m, 0.05)
    s_r3m = score_from_returns(r3m, 0.12)
    s_r6m = score_from_returns(r6m, 0.20)
    s_ma50_slope = clip(ma50_pct_slope / 0.02, -1, 1)
    s_ma50_vs200 = clip(ma50_vs_ma200 / 0.05, -1, 1)
    s_breadth = clip((pct_above_200d - 0.5) / 0.4, -1, 1)
    try:
        vix_z = (vix - vix_mean_252) / max(1e-9, vix_std_252)
    except Exception:
        vix_z = 0.0
    s_vix = clip(-vix_z / 2.0, -1, 1)

    # weights - change if you want to tune
    w = {
        'r1m': 0.20, 'r3m': 0.15, 'r6m': 0.10,
        'ma50_slope': 0.15, 'ma50_vs200': 0.15, 'breadth': 0.15, 'vix': 0.10
    }

    trend_raw = (
        w['r1m'] * s_r1m + w['r3m'] * s_r3m + w['r6m'] * s_r6m
        + w['ma50_slope'] * s_ma50_slope + w['ma50_vs200'] * s_ma50_vs200
        + w['breadth'] * s_breadth + w['vix'] * s_vix
    )
    trend_raw = float(clip(trend_raw, -1.0, 1.0))

    # --- pulse scores ---
    ps_r1d = clip(r1d / 0.01, -1, 1)
    ps_r2d = clip(r2d / 0.02, -1, 1)
    ps_advdecl = clip(adv_decl_today / 0.5, -1, 1)
    ps_vixdelta = clip(-vix_delta / 0.05, -1, 1)
    ps_news = -1.0 if notable_market_news else 0.0

    pw = {'r1d': 0.40, 'r2d': 0.15, 'advdecl': 0.20, 'vixdelta': 0.15, 'news': 0.10}
    pulse_raw = (
        pw['r1d'] * ps_r1d + pw['r2d'] * ps_r2d + pw['advdecl'] * ps_advdecl
        + pw['vixdelta'] * ps_vixdelta + pw['news'] * ps_news
    )
    pulse_raw = float(clip(pulse_raw, -1.0, 1.0))

    # --- smoothing & hysteresis for trend ---
    prev_smoothed = None
    prev_label = None
    try:
        if os.path.exists(state_path):
            with open(state_path, 'r', encoding='utf-8') as fh:
                st = json.load(fh)
                prev_smoothed = st.get('smoothed')
                prev_label = st.get('label')
    except Exception:
        prev_smoothed = None

    if prev_smoothed is None:
        trend_smoothed = trend_raw
    else:
        trend_smoothed = ema_alpha * trend_raw + (1 - ema_alpha) * prev_smoothed

    def label_from_trend(c):
        if c >= 0.60:
            return 'Strong Bull'
        if c >= 0.20:
            return 'Bull'
        if c > -0.20:
            return 'Neutral'
        if c > -0.60:
            return 'Bear'
        return 'Strong Bear'

    trend_label = label_from_trend(trend_smoothed)

    def label_from_pulse(c):
        if c >= 0.40:
            return 'Daily Strong Bull'
        if c >= 0.15:
            return 'Daily Bull'
        if c > -0.15:
            return 'Daily Neutral'
        if c > -0.40:
            return 'Daily Bear'
        return 'Daily Strong Bear'

    pulse_label = label_from_pulse(pulse_raw)

    out = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'trend': {
            'raw': trend_raw,
            'smoothed': trend_smoothed,
            'label': trend_label,
            'components': {
                's_r1m': s_r1m, 's_r3m': s_r3m, 's_r6m': s_r6m,
                's_ma50_slope': s_ma50_slope, 's_ma50_vs200': s_ma50_vs200,
                's_breadth': s_breadth, 's_vix': s_vix
            }
        },
        'pulse': {
            'raw': pulse_raw,
            'label': pulse_label,
            'components': {
                's_r1d': ps_r1d, 's_r2d': ps_r2d, 's_advdecl': ps_advdecl,
                's_vixdelta': ps_vixdelta, 's_news': ps_news
            }
        }
    }

    if persist_state:
        try:
            state = {'smoothed': trend_smoothed, 'label': trend_label, 'updated': out['timestamp']}
            d = os.path.dirname(state_path) or '.'
            os.makedirs(d, exist_ok=True)
            with open(state_path, 'w', encoding='utf-8') as fh:
                json.dump(state, fh, indent=2)
        except Exception:
            pass

    return out


def compute_technical_indicators(prices: pd.Series) -> dict:
    """
    Compute technical indicators (RSI, MACD, Bollinger Bands) from a price series.
    
    Args:
        prices: pandas Series of prices (time-indexed)
        
    Returns:
        Dictionary of latest indicator values and signals
    """
    if len(prices) < 26:
        return {}
        
    try:
        # RSI (14)
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        # MACD (12, 26, 9)
        exp1 = prices.ewm(span=12, adjust=False).mean()
        exp2 = prices.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal
        
        # Bollinger Bands (20, 2)
        sma20 = prices.rolling(window=20).mean()
        std20 = prices.rolling(window=20).std()
        upper_band = sma20 + (std20 * 2)
        lower_band = sma20 - (std20 * 2)
        
        current_price = prices.iloc[-1]
        
        # Determine signals
        signals = []
        if current_rsi < 30:
            signals.append("Oversold (RSI < 30)")
        elif current_rsi > 70:
            signals.append("Overbought (RSI > 70)")
            
        if macd.iloc[-1] > signal.iloc[-1] and macd.iloc[-2] <= signal.iloc[-2]:
            signals.append("MACD Bullish Crossover")
        elif macd.iloc[-1] < signal.iloc[-1] and macd.iloc[-2] >= signal.iloc[-2]:
            signals.append("MACD Bearish Crossover")
            
        if current_price < lower_band.iloc[-1]:
            signals.append("Price below Lower Bollinger Band")
        elif current_price > upper_band.iloc[-1]:
            signals.append("Price above Upper Bollinger Band")
            
        return {
            "rsi": round(current_rsi, 2),
            "macd": round(macd.iloc[-1], 2),
            "macd_signal": round(signal.iloc[-1], 2),
            "bb_upper": round(upper_band.iloc[-1], 2),
            "bb_lower": round(lower_band.iloc[-1], 2),
            "signals": signals
        }
    except Exception as e:
        print(f"Error computing indicators: {e}")
        return {}
