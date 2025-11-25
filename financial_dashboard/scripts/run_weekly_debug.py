"""Debug runner for the weekly fetch-and-trade job.
Prints resolved environment variable names, secret lookups (via KN.get_secret), Doppler availability,
sets logging to DEBUG, and runs the weekly main for a small target (10 tickers) in dry-run mode.

Run under WSL with the project's PYTHONPATH and your venv:
  source /mnt/c/Aarav/fin_env/.venv_local/bin/activate
  PYTHONPATH=/mnt/c/Aarav/fin_env/unified-dashboard python3 financial_dashboard/scripts/run_weekly_debug.py
"""
import logging
import shutil

# ensure imports from package work when PYTHONPATH is set by the shell
from financial_dashboard import key_names as KN
from financial_dashboard.scripts import fetch_and_trade_weekly as ftw

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger('run_weekly_debug')

def show_secrets():
    names = ['FINNHUB_API_KEY_1', 'FINNHUB_API_KEY_2', 'ALPACA_API_KEY', 'ALPACA_SECRET_KEY']
    logger.info('Doppler CLI in PATH: %s', shutil.which('doppler'))
    for n in names:
        resolved = KN.resolve_env_names(n)
        val = KN.get_secret(n)
        logger.info('Secret lookup: name=%s resolved=%s present=%s', n, resolved, bool(val))


def main():
    show_secrets()
    logger.info('Starting fetch_and_trade_weekly (dry-run) for 10 tickers')
    # call the script's main with explicit args to avoid sys.argv surprises
    ftw.main(['--target-count', '10'])

if __name__ == '__main__':
    main()

