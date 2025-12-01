import requests
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root is on sys.path so we can import strategies/
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Local service URL
BASE = "http://localhost:8060"

from strategies.my_covered_call_strategy import CoveredCallStrategy
from strategies.my_cash_secured_put import CashSecuredPutStrategy
from strategies.my_bull_put_spread import BullPutSpreadStrategy


def get_stock_quote(symbol):
    r = requests.get(f"{BASE}/quote/{symbol}")
    r.raise_for_status()
    return r.json()


def get_expirations(symbol):
    r = requests.get(f"{BASE}/expirations/{symbol}")
    r.raise_for_status()
    return r.json().get('expirations', [])


def get_options_chain(symbol, expiration):
    r = requests.get(f"{BASE}/options-chain/{symbol}?expiration={expiration}")
    r.raise_for_status()
    return r.json().get('options', [])


def pretty_print(signals):
    if not signals:
        print("No trade signals generated.")
        return
    for s in signals:
        print(s)


if __name__ == '__main__':
    symbol = 'SPY'
    print("Fetching quote for", symbol)
    quote = get_stock_quote(symbol)
    print("Quote JSON:", quote)
    # Try several common keys for price
    stock_price = None
    for key in ('price', 'current', 'last', 'c', 'close'):
        if key in quote and isinstance(quote.get(key), (int, float)):
            stock_price = quote.get(key)
            break
    print("Resolved Current Price:", stock_price)

    exps = get_expirations(symbol)
    print("Expirations returned:", exps)
    options = []
    if exps:
        # Try expirations in order and pick the first with options
        for e in exps:
            try:
                opts = get_options_chain(symbol, e)
            except Exception as exc:
                print(f"Error fetching options for {e}: {exc}")
                opts = []
            if opts:
                options = opts
                target = e
                break
        if not options:
            # fallback: choose nearest expiration by days to target 30
            target = None
            best_diff = 9999
            for e in exps:
                try:
                    dt = datetime.fromisoformat(e)
                    days = (dt - datetime.now()).days
                    diff = abs(days - 30)
                    if diff < best_diff:
                        best_diff = diff
                        target = e
                except Exception:
                    continue
            print("No options found for any expiration. Falling back to chosen expiration:", target)
            options = get_options_chain(symbol, target)
    else:
        print("No expirations returned by service.")

    # If still no options, create a small synthetic chain for testing
    if not options:
        print("No options available from service for SPY. Generating synthetic options for testing.")
        # build simple synthetic chain around stock_price or common level
        base = stock_price or 450.0
        strikes = [round(base * (1 + x/100), 2) for x in (-2, 0, 2)]
        options = []
        for s in strikes:
            options.append({'type': 'call', 'strike': s, 'expiration': (datetime.now()).date().isoformat(), 'dte': 30, 'volume': 200, 'delta': 0.30 if s > base else 0.20, 'mid': 0.8})
            options.append({'type': 'put', 'strike': s, 'expiration': (datetime.now()).date().isoformat(), 'dte': 30, 'volume': 200, 'delta': 0.20 if s < base else 0.30, 'mid': 0.7})

    print(f"Using expiration: {target if 'target' in locals() else 'synthetic'}")
    print(f"Options used: {len(options)} contracts")

    # instantiate
    cc = CoveredCallStrategy()
    cp = CashSecuredPutStrategy()
    bps = BullPutSpreadStrategy()

    print('\n--- Covered Call ---')
    pretty_print(cc.run(options, stock_price))

    print('\n--- Cash Secured Put ---')
    pretty_print(cp.run(options, stock_price))

    print('\n--- Bull Put Spread ---')
    pretty_print(bps.run(options, stock_price))
