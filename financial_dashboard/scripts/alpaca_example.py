"""Example using `src.utils.alpaca` showing dry-run order submission.

This script demonstrates the recommended pattern:
 - load local env (optional)
 - call `submit_order(..., dry_run=True)` to avoid accidental trades
"""
from src.utils.secrets import load_local_env
from src.utils.alpaca import submit_order


def main():
    load_local_env()
    res = submit_order('AAPL', qty=1, side='buy', dry_run=True)
    print('Result:', res)


if __name__ == '__main__':
    main()
