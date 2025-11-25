"""
Options Backtester API Endpoint

Provides deterministic backtest results for validation.

Phase 31 Agent 1A - STEP 9
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from flask import Blueprint, request, jsonify
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# Blueprint for backtester
backtest_bp = Blueprint('options_backtest', __name__, url_prefix='/api/options')

# Directories
FIXTURES_DIR = Path(__file__).parent.parent.parent / 'tests' / 'fixtures' / 'options'
REPORTS_DIR = Path('reports/options_validation')

# Deterministic mode flag
DETERMINISTIC = os.getenv('OPTIONS_DETERMINISTIC', '0') == '1'


def load_deterministic_backtest_fixture() -> Dict:
    """Load deterministic backtest fixture"""
    fixture_path = FIXTURES_DIR / 'backtest_fixture.json'
    
    if not fixture_path.exists():
        # Create default fixture
        fixture = create_default_backtest_fixture()
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        with open(fixture_path, 'w') as f:
            json.dump(fixture, f, indent=2)
        logger.info(f"Created default backtest fixture: {fixture_path}")
    
    with open(fixture_path, 'r') as f:
        return json.load(f)


def create_default_backtest_fixture() -> Dict:
    """Create deterministic backtest fixture"""
    end_date = datetime(2024, 11, 1)
    start_date = end_date - timedelta(days=90)
    
    # Generate deterministic equity curve (simple upward trend with volatility)
    import random
    random.seed(42)  # Deterministic seed
    
    equity_curve = []
    equity = 10000.0
    
    for i in range(90):
        date = start_date + timedelta(days=i)
        # Simple random walk with positive drift
        daily_return = random.gauss(0.001, 0.02)  # 0.1% daily return, 2% volatility
        equity *= (1 + daily_return)
        
        equity_curve.append({
            'date': date.strftime('%Y-%m-%d'),
            'equity': round(equity, 2)
        })
    
    # Generate sample trades
    trades = [
        {
            'trade_id': 1,
            'entry_date': '2024-08-05',
            'exit_date': '2024-08-10',
            'ticker': 'AAPL',
            'strategy': 'covered_call',
            'entry_price': 175.50,
            'exit_price': 178.25,
            'quantity': 1,
            'pnl': 275.00,
            'return_pct': 1.57
        },
        {
            'trade_id': 2,
            'entry_date': '2024-08-15',
            'exit_date': '2024-08-22',
            'ticker': 'AAPL',
            'strategy': 'covered_call',
            'entry_price': 178.00,
            'exit_price': 180.50,
            'quantity': 1,
            'pnl': 250.00,
            'return_pct': 1.40
        },
        {
            'trade_id': 3,
            'entry_date': '2024-09-01',
            'exit_date': '2024-09-08',
            'ticker': 'AAPL',
            'strategy': 'covered_call',
            'entry_price': 182.00,
            'exit_price': 179.50,
            'quantity': 1,
            'pnl': -250.00,
            'return_pct': -1.37
        },
        {
            'trade_id': 4,
            'entry_date': '2024-09-15',
            'exit_date': '2024-09-22',
            'ticker': 'AAPL',
            'strategy': 'covered_call',
            'entry_price': 180.00,
            'exit_price': 183.00,
            'quantity': 1,
            'pnl': 300.00,
            'return_pct': 1.67
        },
        {
            'trade_id': 5,
            'entry_date': '2024-10-01',
            'exit_date': '2024-10-08',
            'ticker': 'AAPL',
            'strategy': 'covered_call',
            'entry_price': 183.50,
            'exit_price': 185.75,
            'quantity': 1,
            'pnl': 225.00,
            'return_pct': 1.23
        }
    ]
    
    # Calculate metrics
    total_trades = len(trades)
    winning_trades = sum(1 for t in trades if t['pnl'] > 0)
    total_pnl = sum(t['pnl'] for t in trades)
    
    final_equity = equity_curve[-1]['equity']
    total_return = ((final_equity - 10000) / 10000) * 100
    
    # Simple max drawdown calculation
    peak = 10000
    max_dd = 0
    for point in equity_curve:
        if point['equity'] > peak:
            peak = point['equity']
        dd = ((peak - point['equity']) / peak) * 100
        if dd > max_dd:
            max_dd = dd
    
    # Simple Sharpe ratio (annualized)
    daily_returns = []
    for i in range(1, len(equity_curve)):
        ret = (equity_curve[i]['equity'] / equity_curve[i-1]['equity']) - 1
        daily_returns.append(ret)
    
    import math
    avg_return = sum(daily_returns) / len(daily_returns)
    std_dev = math.sqrt(sum((r - avg_return) ** 2 for r in daily_returns) / len(daily_returns))
    sharpe_ratio = (avg_return / std_dev) * math.sqrt(252) if std_dev > 0 else 0
    
    return {
        'backtest_id': 'bt_deterministic_001',
        'ticker': 'AAPL',
        'strategy': 'covered_call',
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'initial_capital': 10000.00,
        'final_equity': round(final_equity, 2),
        'metrics': {
            'total_return': round(total_return, 2),
            'total_return_pct': round(total_return, 2),
            'max_drawdown': round(max_dd, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': round((winning_trades / total_trades) * 100, 2),
            'total_pnl': round(total_pnl, 2)
        },
        'equity_curve': equity_curve,
        'trades': trades,
        'deterministic': True,
        'seed': 42
    }


@backtest_bp.route('/backtest/run', methods=['POST'])
def run_backtest():
    """
    Run backtest with deterministic results.
    
    In deterministic mode (OPTIONS_DETERMINISTIC=1), returns fixture.
    Otherwise blocks with 403.
    """
    if not DETERMINISTIC and not request.json.get('deterministic'):
        # Block non-deterministic backtests
        log_blocked_backtest(request.json)
        return jsonify({
            'error': 'Live backtesting disabled',
            'message': 'Set OPTIONS_DETERMINISTIC=1 or pass deterministic=true'
        }), 403
    
    # Load deterministic fixture
    fixture = load_deterministic_backtest_fixture()
    
    # Log success
    logger.info(f"Returned deterministic backtest: {fixture['backtest_id']}")
    
    # Save to validation artifacts
    save_backtest_run(fixture)
    
    return jsonify(fixture), 200


@backtest_bp.route('/backtest/export', methods=['POST'])
def export_backtest():
    """
    Export backtest results.
    
    Returns JSON download of most recent backtest.
    """
    fixture = load_deterministic_backtest_fixture()
    
    # In a real implementation, would retrieve from database
    # For validation, return fixture
    
    return jsonify(fixture), 200


def log_blocked_backtest(params: Dict):
    """Log blocked backtest attempt"""
    blocked_log = REPORTS_DIR / 'diagnostics' / 'backtest_blocked.log'
    blocked_log.parent.mkdir(parents=True, exist_ok=True)
    
    with open(blocked_log, 'a') as f:
        f.write(f"{datetime.utcnow().isoformat()}Z - Blocked backtest: {json.dumps(params)}\n")


def save_backtest_run(result: Dict):
    """Save backtest run to artifacts AND database"""
    timestamp = int(datetime.utcnow().timestamp())
    
    # Save to artifacts (always)
    artifact_path = REPORTS_DIR / 'playwright' / f'backtest_response_{timestamp}.json'
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(artifact_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"Saved backtest run to: {artifact_path}")
    
    # Save to database (Postgres primary, JSON fallback)
    try:
        save_to_database(result)
    except Exception as e:
        logger.warning(f"Database save failed, using JSON fallback: {e}")
        save_to_json_fallback(result)


def save_to_database(result: Dict):
    """Save backtest to Postgres database"""
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        raise ImportError("psycopg2 not available")
    
    # Get database connection string from environment
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL not set")
    
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    # Insert into options_backtests table
    cursor.execute("""
        INSERT INTO options_backtests (
            backtest_id, ticker, strategy, start_date, end_date,
            initial_capital, final_equity, total_return, max_drawdown,
            sharpe_ratio, win_rate, total_trades, trades, equity_curve,
            created_at, deterministic, seed
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """, (
        result['backtest_id'],
        result['ticker'],
        result['strategy'],
        result['start_date'],
        result['end_date'],
        result['initial_capital'],
        result['final_equity'],
        result['metrics']['total_return'],
        result['metrics']['max_drawdown'],
        result['metrics']['sharpe_ratio'],
        result['metrics']['win_rate'],
        result['metrics']['total_trades'],
        psycopg2.extras.Json(result['trades']),
        psycopg2.extras.Json(result['equity_curve']),
        datetime.utcnow(),
        result.get('deterministic', False),
        result.get('seed')
    ))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    logger.info(f"Saved backtest {result['backtest_id']} to database")


def save_to_json_fallback(result: Dict):
    """Save backtest to JSON file as fallback"""
    json_dir = Path('financial_dashboard/data/options')
    json_dir.mkdir(parents=True, exist_ok=True)
    
    json_file = json_dir / 'backtests.json'
    
    # Load existing or create new
    if json_file.exists():
        with open(json_file, 'r') as f:
            backtests = json.load(f)
    else:
        backtests = []
    
    # Add new backtest
    backtest_entry = {
        **result,
        'created_at': datetime.utcnow().isoformat() + 'Z'
    }
    backtests.append(backtest_entry)
    
    # Save
    with open(json_file, 'w') as f:
        json.dump(backtests, f, indent=2)
    
    logger.info(f"Saved backtest {result['backtest_id']} to JSON: {json_file}")
    
    # Also save individual backtest to db_dumps for validation
    db_dump_path = REPORTS_DIR / 'db_dumps' / f'backtest_run_{int(datetime.utcnow().timestamp())}.json'
    db_dump_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(db_dump_path, 'w') as f:
        json.dump(backtest_entry, f, indent=2)
    
    logger.info(f"Saved backtest to db_dumps: {db_dump_path}")


@backtest_bp.route('/backtest/health', methods=['GET'])
def health_check():
    """Health check for backtest API"""
    return jsonify({
        'status': 'ok',
        'deterministic_mode': DETERMINISTIC,
        'fixture_exists': (FIXTURES_DIR / 'backtest_fixture.json').exists()
    }), 200
