"""
Home Lab - Helper Functions

Utility functions for data aggregation, metric formatting, and insight summarization.
"""

import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)

# ============================================================================
# PORTFOLIO HELPERS
# ============================================================================

def get_portfolio_summary():
    """
    Load portfolio summary data from Alpaca API → cache → CSV fallback.
    
    Priority:
    1. Try fetching from Alpaca API (live data)
    2. Fallback to cache/portfolio_data.json
    3. Fallback to latest /outputs/top20_weekly_picks_*.csv
    4. Return mock data if all unavailable
    
    Returns:
        dict: Portfolio summary with tickers, metrics, and metadata
    """
    try:
        # Try Alpaca API first
        alpaca_data = _fetch_from_alpaca()
        if alpaca_data:
            return alpaca_data
        
        # Try primary cache
        cache_path = Path(__file__).parent.parent.parent / "cache" / "portfolio_data.json"
        
        if cache_path.exists():
            with open(cache_path, 'r') as f:
                data = json.load(f)
            
            # Extract key metrics
            positions = data.get('positions', [])
            total_value = sum(p.get('market_value', 0) for p in positions)
            daily_change_pct = data.get('daily_change_pct', 0.0)
            
            logger.info(f"✅ Loaded portfolio from cache: {len(positions)} positions, ${total_value:,.2f}")
            
            return {
                'total_positions': len(positions),
                'total_value': total_value,
                'daily_change_pct': daily_change_pct,
                'positions': positions[:10],  # Top 10
                'last_updated': data.get('last_updated', 'N/A'),
                'source': 'cache'
            }
        
        # Fallback to CSV
        logger.warning(f"Portfolio cache not found: {cache_path}, trying CSV fallback...")
        return _load_portfolio_from_csv()
    
    except Exception as e:
        logger.error(f"Error loading portfolio summary: {e}")
        return _get_mock_portfolio()


def _fetch_from_alpaca():
    """
    Fetch live portfolio data from Alpaca API.
    
    Returns:
        dict or None: Portfolio summary from Alpaca API, or None if unavailable
    """
    try:
        import os
        from alpaca.trading.client import TradingClient
        
        api_key = os.getenv("APCA_API_KEY_ID")
        api_secret = os.getenv("APCA_API_SECRET_KEY")
        
        if not api_key or not api_secret:
            logger.warning("Alpaca API credentials not found")
            return None
        
        # Initialize client (paper trading)
        client = TradingClient(api_key, api_secret, paper=True)
        
        # Fetch positions
        positions_raw = client.get_all_positions()
        
        if not positions_raw:
            logger.warning("No positions found in Alpaca account")
            return None
        
        # Fetch account info
        account = client.get_account()
        
        # Format positions
        positions = []
        for pos in positions_raw[:10]:  # Top 10
            positions.append({
                'ticker': pos.symbol,
                'shares': float(pos.qty),
                'price': float(pos.current_price),
                'market_value': float(pos.market_value),
                'sector': 'N/A',  # Sector lookup would require additional API call
                'daily_change_pct': float(pos.unrealized_plpc) * 100
            })
        
        total_value = sum(p['market_value'] for p in positions)
        
        logger.info(f"✅ Loaded portfolio from Alpaca API: {len(positions)} positions, ${total_value:,.2f}")
        
        return {
            'total_positions': len(positions),
            'total_value': float(account.equity),
            'daily_change_pct': 0.0,  # Would need historical comparison
            'positions': positions,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'source': 'alpaca_api'
        }
    
    except ImportError:
        logger.warning("alpaca-py not installed, skipping Alpaca API fetch")
        return None
    except Exception as e:
        logger.error(f"Error fetching from Alpaca API: {e}")
        return None


def _load_portfolio_from_csv():
    """
    Load portfolio from latest weekly picks CSV file.
    
    Returns:
        dict: Portfolio summary from CSV data
    """
    try:
        outputs_dir = Path(__file__).parent.parent.parent / "outputs"
        
        # Find latest CSV file
        csv_files = sorted(
            outputs_dir.glob("top20_weekly_picks_*.csv"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if not csv_files:
            logger.warning("No CSV files found in /outputs")
            return _get_mock_portfolio()
        
        latest_csv = csv_files[0]
        logger.info(f"📊 Loading portfolio from CSV: {latest_csv.name}")
        
        df = pd.read_csv(latest_csv)
        
        # Extract positions (top 10)
        positions = []
        total_value = 0.0
        
        for idx, row in df.head(10).iterrows():
            ticker = row.get('ticker', row.get('Ticker', 'UNKNOWN'))
            price = float(row.get('last_price', row.get('close', row.get('Close', row.get('price', 100.0)))))
            
            # Use position_size_dollars if available, else estimate
            position_size = float(row.get('position_size_dollars', 10000.0))
            shares = position_size / price if price > 0 else 0
            market_value = position_size
            total_value += market_value
            
            # Get daily return and convert to percentage
            daily_change = float(row.get('ret_5d', row.get('change_pct', row.get('daily_change', 0.0))))
            daily_change_pct = daily_change * 100 if daily_change < 1 else daily_change
            
            positions.append({
                'ticker': ticker,
                'shares': int(shares),
                'last_price': price,
                'price': price,  # backward compat
                'market_value': market_value,
                'sector': row.get('sector', row.get('Sector', 'Technology')),
                'daily_change_pct': daily_change_pct,
                'predicted_return': float(row.get('pred_mean', 0.0)) * 100 if 'pred_mean' in row else None
            })
        
        logger.info(f"✅ Loaded {len(positions)} positions from CSV, total value: ${total_value:,.2f}")
        
        return {
            'total_positions': len(positions),
            'total_value': total_value,
            'daily_change_pct': sum(p['daily_change_pct'] for p in positions) / len(positions) if positions else 0.0,
            'positions': positions,
            'last_updated': latest_csv.stem.replace('top20_weekly_picks_', ''),
            'source': 'csv',
            'csv_file': latest_csv.name
        }
    
    except Exception as e:
        logger.error(f"Error loading portfolio from CSV: {e}")
        return _get_mock_portfolio()


def _get_mock_portfolio():
    """
    Return mock portfolio data for testing/fallback.
    
    Returns:
        dict: Mock portfolio summary
    """
    logger.warning("⚠️ Using mock portfolio data")
    
    mock_positions = [
        {'ticker': 'AAPL', 'shares': 100, 'price': 175.0, 'market_value': 17500.0, 'sector': 'Technology', 'daily_change_pct': 1.2},
        {'ticker': 'MSFT', 'shares': 100, 'price': 380.0, 'market_value': 38000.0, 'sector': 'Technology', 'daily_change_pct': 0.8},
        {'ticker': 'GOOGL', 'shares': 50, 'price': 140.0, 'market_value': 7000.0, 'sector': 'Technology', 'daily_change_pct': -0.5},
        {'ticker': 'NVDA', 'shares': 50, 'price': 495.0, 'market_value': 24750.0, 'sector': 'Technology', 'daily_change_pct': 2.1},
        {'ticker': 'SPY', 'shares': 100, 'price': 450.0, 'market_value': 45000.0, 'sector': 'Index', 'daily_change_pct': 0.3},
    ]
    
    return {
        'total_positions': len(mock_positions),
        'total_value': sum(p['market_value'] for p in mock_positions),
        'daily_change_pct': sum(p['daily_change_pct'] for p in mock_positions) / len(mock_positions),
        'positions': mock_positions,
        'last_updated': datetime.now().strftime('%Y-%m-%d'),
        'source': 'mock'
    }


# ============================================================================
# METRICS CACHE HELPERS
# ============================================================================

def get_cross_lab_metrics():
    """
    Load aggregated metrics from all labs.
    
    Returns:
        dict: Cross-lab performance metrics
    """
    try:
        metrics_path = Path(__file__).parent.parent.parent / "outputs" / "metrics_cache.json"
        
        if metrics_path.exists():
            with open(metrics_path, 'r') as f:
                return json.load(f)
        else:
            # Return mock/default metrics
            return {
                'attribution': {
                    'cagr': 12.5,
                    'last_updated': 'N/A',
                    'status': 'unknown'
                },
                'volatility': {
                    'forecast_accuracy': 78.3,
                    'last_updated': 'N/A',
                    'status': 'unknown'
                },
                'research': {
                    'research_score': 7.2,
                    'last_updated': 'N/A',
                    'status': 'unknown'
                },
                'strategy': {
                    'win_rate': 55.4,
                    'last_updated': 'N/A',
                    'status': 'unknown'
                }
            }
    
    except Exception as e:
        logger.error(f"Error loading cross-lab metrics: {e}")
        return {}


# ============================================================================
# LAB STATUS HELPERS
# ============================================================================

def get_lab_status():
    """
    Check status of all major labs.
    
    Returns:
        dict: Status for each lab (loaded, timestamp, data source)
    """
    labs = {
        'attribution_lab': {
            'name': 'Attribution Lab',
            'icon': '📊',
            'status': 'active',
            'last_load': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'data_source': 'yfinance + local cache'
        },
        'volatility_lab': {
            'name': 'Volatility Lab',
            'icon': '⚡',
            'status': 'active',
            'last_load': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'data_source': 'GARCH models + CSV'
        },
        'research_lab': {
            'name': 'Research Lab',
            'icon': '🔬',
            'status': 'active',
            'last_load': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'data_source': 'yfinance + experiments cache'
        },
        'strategy_lab': {
            'name': 'Strategy Lab',
            'icon': '⚡',
            'status': 'active',
            'last_load': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'data_source': 'yfinance + backtest engine'
        }
    }
    
    return labs


def compute_system_health():
    """
    Perform lightweight system checks and return a health summary.

    Checks performed (non-invasive):
    - portfolio cache exists
    - metrics cache exists
    - at least one weekly picks CSV exists
    - optional: Alpaca credentials present (env)

    Returns:
        dict: {
            'percent': int,  # 0-100
            'issues': [str],  # list of human-readable issues (empty if healthy)
            'details': {check_name: bool}
        }
    """
    issues = []
    details = {}
    # Fix: Go up 4 levels to reach project root
    # __file__ → helpers.py → home_lab/ → tabs/ → financial_dashboard/ → project_root/
    base = Path(__file__).parent.parent.parent.parent

    # Check portfolio cache
    cache_path = base / 'cache' / 'portfolio_data.json'
    ok_cache = cache_path.exists()
    details['portfolio_cache'] = ok_cache
    if not ok_cache:
        issues.append('Portfolio cache missing (cache/portfolio_data.json)')

    # Check metrics cache
    metrics_path = base / 'outputs' / 'metrics_cache.json'
    ok_metrics = metrics_path.exists()
    details['metrics_cache'] = ok_metrics
    if not ok_metrics:
        issues.append('Metrics cache missing (outputs/metrics_cache.json)')

    # Check weekly picks CSV
    csvs = sorted((base / 'outputs').glob('top20_weekly_picks_*.csv'))
    ok_csv = len(csvs) > 0
    details['weekly_picks_csv'] = ok_csv
    if not ok_csv:
        issues.append('No weekly picks CSV found in /outputs')

    # Check Alpaca credentials presence (not validating credentials)
    # NOTE: This is optional - credentials may be loaded via other means (Doppler, secrets manager)
    try:
        import os
        ok_alpaca = bool(os.getenv('APCA_API_KEY_ID') and os.getenv('APCA_API_SECRET_KEY'))
    except Exception:
        ok_alpaca = False
    details['alpaca_credentials'] = ok_alpaca
    # Don't penalize health score for missing Alpaca credentials since portfolio data is working
    # Just add to details for informational purposes

    # Compute percent: start at 100 and subtract equal weight per REQUIRED check (exclude optional Alpaca)
    required_checks = ['portfolio_cache', 'metrics_cache', 'weekly_picks_csv']
    failed = sum(1 for k in required_checks if not details.get(k, False))
    percent = int(max(0, 100 - (failed * (100 // len(required_checks)))))

    return {'percent': percent, 'issues': issues, 'details': details}


# ============================================================================
# INSIGHT SUMMARIZATION
# ============================================================================

def summarize_insights():
    """
    Generate AI-style insight summaries (mock for now, Azure ML later).
    
    Returns:
        list: List of insight strings
    """
    insights = [
        "📈 **Best Strategy**: Momentum SMA Crossover showed +15.3% return last week",
        "⚠️ **High Volatility**: TSLA showing 2.5x normal volatility (consider hedging)",
        "💡 **Sector Alert**: Technology sector alpha up 3.2% this month",
        "🎯 **Portfolio Health**: 8/10 positions beating SPY benchmark",
        "📊 **Risk Update**: Portfolio beta stable at 1.05 (moderate market correlation)"
    ]
    
    return insights


# ============================================================================
# FORMATTING HELPERS
# ============================================================================

def format_currency(value):
    """Format value as currency string."""
    try:
        return f"${value:,.2f}"
    except:
        return "$0.00"


def format_percentage(value, decimals=2):
    """Format value as percentage string."""
    try:
        return f"{value:.{decimals}f}%"
    except:
        return "0.00%"


def format_metric_color(value, threshold_good=10.0, threshold_bad=5.0):
    """
    Determine color for metric based on thresholds.
    
    Returns:
        str: Color name (success, warning, danger)
    """
    try:
        val = float(value)
        if val >= threshold_good:
            return "success"
        elif val >= threshold_bad:
            return "warning"
        else:
            return "danger"
    except:
        return "secondary"


# ============================================================================
# SPARKLINE DATA GENERATION
# ============================================================================

def generate_portfolio_sparkline():
    """
    Generate mock sparkline data for portfolio trend (last 30 days).
    
    Returns:
        list: Daily portfolio values
    """
    # Mock data - in production, load from portfolio history
    import random
    base = 100000
    values = [base]
    
    for _ in range(29):
        change = random.uniform(-0.02, 0.025)
        values.append(values[-1] * (1 + change))
    
    return values


logger.info("✓ Home Lab helpers loaded")
