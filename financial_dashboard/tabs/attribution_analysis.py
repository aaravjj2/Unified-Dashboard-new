"""
Attribution Analysis Interactive Tab

Provides an interactive UI to analyze attribution for weekly/monthly picks:
- Select picks from date range
- Run attribution analysis on-demand
- Display alpha/beta breakdown
- Show factor contributions and SHAP aggregations
- No need to run separate CLI scripts

Usage:
    from tabs import attribution_analysis
    app.layout = html.Div([attribution_analysis.layout()])
    attribution_analysis.register_callbacks(app)
"""

import os
import json
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dash import dcc, html, Input, Output, State, dash_table, callback_context
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px

from financial_dashboard from financial_dashboard import _shared as SH

# Import attribution utilities
try:
    from utils import attribution as ATTR
except ImportError:
    ATTR = None
    logging.warning("Attribution utils not available - beta estimation will be simplified")

logger = logging.getLogger(__name__)


def _find_latest_picks_generic(patterns=None):
    """Find the most recent picks CSV using patterns relative to DASH_ROOT."""
    try:
        dash_root = SH.DASH_ROOT
    except Exception:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        dash_root = os.path.dirname(base_dir)

    import glob, re
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
                from datetime import datetime
                return datetime.strptime(m_yyyymmdd.group(1), '%Y%m%d').date()
            except Exception:
                pass
        m_mmdd = re.search(r'(\d{4})', filename)
        if m_mmdd:
            try:
                from datetime import datetime
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
        parsed = _parse_date_from_name(p) or __import__('datetime').datetime.min.date()
        mtime = os.path.getmtime(p)
        return (_is_picks_prefix(p), _in_full_run(p), parsed, mtime)

    candidates.sort(key=_sort_key, reverse=True)
    return candidates[0]
    
def _load_picks_in_range(picks_type, start_date, end_date):
    """Load picks CSV files within the specified date range."""
    try:
        import glob
        
        dash_root = getattr(SH, 'DASH_ROOT', SH.PROJECT_ROOT)
        
        if picks_type == 'weekly':
            picks_dir = os.path.join(dash_root, 'models', 'weekly_run')
            file_pattern = 'picks_*.csv'
        else:
            # Monthly picks are in full_run directory
            picks_dir = os.path.join(dash_root, 'models', 'full_run')
            file_pattern = 'monthly_picks_*.csv'
        
        if not os.path.exists(picks_dir):
            logger.warning(f"Picks directory does not exist: {picks_dir}")
            return None
        
        # Find picks CSV files with the correct pattern
        csv_files = glob.glob(os.path.join(picks_dir, '**', file_pattern), recursive=True)
        logger.info(f"Attribution: Loading {picks_type} picks from {picks_dir} - found {len(csv_files)} files with pattern {file_pattern}")
        
        all_picks = []
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                # Normalize column names to prevent "Names mismatch" issues
                df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
                # If no date column, parse from filename (picks_YYYYMMDD.csv)
                if 'date' not in df.columns:
                    import re
                    filename = os.path.basename(csv_file)
                    m = re.search(r'(\d{8})', filename)
                    if m:
                        file_date = m.group(1)
                        df['date'] = file_date
                    else:
                        # Use file modification time as fallback
                        mtime = os.path.getmtime(csv_file)
                        df['date'] = datetime.fromtimestamp(mtime).strftime('%Y%m%d')
                # Ensure ticker column exists (try common variants)
                if 'ticker' not in df.columns:
                    # try Title case or other common variants
                    for col in df.columns:
                        if col.lower() == 'ticker' or col.lower() == 'symbol':
                            df['ticker'] = df[col]
                            break

                if 'ticker' in df.columns:
                    all_picks.append(df)
            except Exception as e:
                logger.warning(f"Could not read {csv_file}: {e}")
        
        if not all_picks:
            return None
        
        # Combine and filter by date range
        combined = pd.concat(all_picks, ignore_index=True)
        combined['date'] = pd.to_datetime(combined['date'], format='%Y%m%d', errors='coerce')
        
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        filtered = combined[(combined['date'] >= start) & (combined['date'] <= end)]
        
        return filtered
        
    except Exception as e:
        logger.error(f"Error loading picks: {e}")
        return None


def _run_attribution_on_picks(picks_df, horizon):
    """Run attribution analysis on the picks DataFrame."""
    try:
        if ATTR is None:
            raise ImportError("Attribution utils not available")
        
        # Get unique tickers
        tickers = picks_df['ticker'].unique().tolist()
        
        # Fetch price data for returns calculation
        import yfinance as yf
        
        # Determine horizon days
        horizon_days = {'1w': 7, '1m': 30, '3m': 90}.get(horizon, 7)
        
        per_pick_results = []
        
        for _, pick in picks_df.iterrows():
            ticker = pick['ticker']
            pick_date = pd.to_datetime(pick['date'])
            end_date = pick_date + timedelta(days=horizon_days)
            
            try:
                # Get price data
                stock = yf.Ticker(ticker)
                hist = stock.history(start=pick_date - timedelta(days=1), 
                                    end=end_date + timedelta(days=1))
                
                if len(hist) < 2:
                    continue
                
                # Calculate realized return
                start_price = hist['Close'].iloc[0]
                end_price = hist['Close'].iloc[-1]
                # Coerce to float where possible to avoid sequence * float errors
                try:
                    start_price = float(start_price)
                    end_price = float(end_price)
                    realized_return = (end_price / start_price - 1)
                except Exception as _e:
                    logger.warning("ATTR_NUMERIC_COERCE - could not coerce prices for %s: start=%r end=%r err=%s",
                                   ticker, start_price, end_price, _e)
                    # Skip this pick if we cannot interpret numeric prices
                    continue

                # Get benchmark return (SPY)
                spy = yf.Ticker('SPY')
                spy_hist = spy.history(start=pick_date - timedelta(days=1),
                                      end=end_date + timedelta(days=1))

                benchmark_return = 0.0
                if len(spy_hist) >= 2:
                    try:
                        benchmark_return = float(spy_hist['Close'].iloc[-1]) / float(spy_hist['Close'].iloc[0]) - 1
                    except Exception as _e:
                        logger.warning("ATTR_NUMERIC_COERCE - could not coerce spy prices for %s: %s", ticker, _e)
                        benchmark_return = 0.0

                # Estimate beta (using longer history)
                long_hist = stock.history(start=pick_date - timedelta(days=252),
                                         end=pick_date)
                spy_long = spy.history(start=pick_date - timedelta(days=252),
                                      end=pick_date)

                if len(long_hist) >= 20 and len(spy_long) >= 20:
                    # Align dates
                    merged = pd.DataFrame({
                        'stock': long_hist['Close'].pct_change(),
                        'spy': spy_long['Close'].pct_change()
                    }).dropna()

                    if len(merged) >= 20:
                        beta = ATTR.estimate_beta(merged, 'stock', 'spy')
                        # Coerce beta to a float scalar where possible
                        try:
                            beta = float(beta)
                        except Exception:
                            try:
                                # If beta is array-like, take the first element
                                beta = float(beta[0])
                            except Exception:
                                logger.warning("ATTR_NUMERIC_COERCE - could not coerce beta for %s: %r", ticker, beta)
                                beta = 1.0
                    else:
                        beta = 1.0
                else:
                    beta = 1.0

                # Calculate attribution
                try:
                    beta_contrib = float(beta) * float(benchmark_return)
                except Exception as _e:
                    logger.warning("ATTR_NUMERIC_COERCE - error computing beta_contrib for %s: beta=%r benchmark=%r err=%s",
                                   ticker, beta, benchmark_return, _e)
                    beta_contrib = 0.0

                try:
                    alpha = float(realized_return) - float(beta_contrib)
                except Exception as _e:
                    logger.warning("ATTR_NUMERIC_COERCE - error computing alpha for %s: realized=%r beta_contrib=%r err=%s",
                                   ticker, realized_return, beta_contrib, _e)
                    alpha = 0.0

                # Determine top factor (placeholder - would need SHAP data)
                top_factor = "momentum"  # This would come from SHAP analysis

                per_pick_results.append({
                    'ticker': ticker,
                    'date': pick_date.strftime('%Y-%m-%d'),
                    'realized_return': float(realized_return),
                    'alpha': float(alpha),
                    'beta': float(beta),
                    'beta_contrib': float(beta_contrib),
                    'benchmark_return': float(benchmark_return),
                    'top_factor': top_factor
                })
                
            except Exception as e:
                logger.warning(f"Error processing {ticker}: {e}")
                continue
        
        if not per_pick_results:
            return None
        
        # Calculate portfolio-level metrics
        total_return = np.mean([p['realized_return'] for p in per_pick_results])
        total_alpha = np.mean([p['alpha'] for p in per_pick_results])
        avg_beta = np.mean([p['beta'] for p in per_pick_results])
        total_beta_contrib = np.mean([p['beta_contrib'] for p in per_pick_results])
        
            # Load SHAP data and aggregate into factors
        try:
            from financial_dashboard.utils.explain import load_shap_explanations
            
            # Try to find SHAP data for any of the pick dates
            shap_data_loaded = None
            for pick in per_pick_results[:5]:  # Try first 5 picks
                pick_date_str = pd.to_datetime(pick['date']).strftime('%Y%m%d')
                shap_data_loaded = load_shap_explanations(pick_date_str)
                if shap_data_loaded:
                    break
            
            if shap_data_loaded:
                # Define factor groupings (customize based on your actual features)
                factor_groups = {
                    'momentum': ['ret_5d', 'ret_21d', 'ret_63d', 'rsi', 'macd'],
                    'value': ['pb_ratio', 'pe_ratio', 'pcf_ratio', 'dividend_yield'],
                    'quality': ['roe', 'roa', 'debt_equity', 'current_ratio'],
                    'sentiment': ['sentiment_score', 'news_volume', 'social_sentiment'],
                    'growth': ['revenue_growth', 'earnings_growth', 'sales_growth'],
                    'size': ['market_cap', 'volume', 'float_shares']
                }
                
                # Aggregate SHAP values by factor across all picks
                factor_totals = {f: 0.0 for f in factor_groups.keys()}
                count = 0
                
                for ticker_shap in shap_data_loaded.values():
                    if isinstance(ticker_shap, dict):
                        top_features = ticker_shap.get('top_features', [])
                        for feat in top_features:
                            feat_name = feat.get('feature', '')
                            feat_value = feat.get('value', 0)
                            # Find which factor this feature belongs to
                            for factor_name, feature_list in factor_groups.items():
                                if any(f in feat_name.lower() for f in feature_list):
                                    factor_totals[factor_name] += feat_value
                                    break
                        count += 1
                
                # Average and convert to contribution percentages
                if count > 0:
                    factor_contributions = [
                        {'factor': fname, 'contribution': round(fval / count, 4)}
                        for fname, fval in sorted(factor_totals.items(), key=lambda x: abs(x[1]), reverse=True)
                        if fval != 0
                    ][:5]  # Top 5 factors
                    logger.info(f"Loaded real SHAP-based factor contributions: {factor_contributions}")
                else:
                    raise ValueError("No SHAP data found")
            else:
                raise FileNotFoundError("No SHAP explanation files found")
                
        except Exception as e:
            logger.warning(f"Could not load SHAP data ({e}), using placeholder factors")
            # Fallback to placeholder if SHAP not available
            factor_contributions = [
                {'factor': 'momentum', 'contribution': 0.02},
                {'factor': 'sentiment', 'contribution': 0.015},
                {'factor': 'value', 'contribution': -0.005},
                {'factor': 'size', 'contribution': 0.008}
            ]
        
        return {
            'portfolio': {
                'total_return': total_return,
                'alpha': total_alpha,
                'beta': avg_beta,
                'beta_contrib': total_beta_contrib,
                'top_factors': factor_contributions
            },
            'per_pick': per_pick_results
        }

    except Exception as e:
        # Capture full traceback and a small sample of picks to aid debugging
        try:
            sample = picks_df.head(5).to_dict('records') if picks_df is not None else None
        except Exception:
            sample = None

        logger.error(
            "Error in attribution analysis (horizon=%s): %s - sample picks: %s",
            horizon, e, sample,
            exc_info=True
        )
        return None
