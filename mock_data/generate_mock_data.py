"""
Mock data generator for the Unified Dashboard next phase

This script synthesizes:
- portfolio_{n_days}.csv: daily prices for a set of tickers
- factors_{n_days}.csv: simulated Fama-French-like factors
- strategy_outputs_{n_days}.json: a sample strategy output including equity curve and metrics

Run locally when you want to populate `/mock_data` with realistic, reproducible
mock data. This script is intentionally offline-only and does not require
network access.
"""
import json
from pathlib import Path
import argparse

try:
    import numpy as np
    import pandas as pd
except Exception:
    np = None
    pd = None


def generate(portfolio_tickers=20, days=365, out_dir="."):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    if pd is None or np is None:
        raise RuntimeError("pandas and numpy are required to generate mock data")

    dates = pd.date_range(end=pd.Timestamp.today(), periods=days, freq="D")

    # Generate geometric random walk for prices
    tickers = [f"TCK{str(i).zfill(3)}" for i in range(1, portfolio_tickers + 1)]
    prices = pd.DataFrame(index=dates, columns=tickers, dtype=float)
    for t in tickers:
        # daily returns ~ N(0.0002, 0.02%)
        rets = np.random.normal(loc=0.0003, scale=0.01, size=len(dates))
        prices[t] = 100 * np.cumprod(1 + rets)

    prices_path = out / f"portfolio_{days}d.csv"
    prices.to_csv(prices_path)

    # Factors: market, size, value, momentum
    factors = pd.DataFrame(index=dates)
    factors['market'] = np.random.normal(0.0004, 0.008, size=len(dates))
    factors['size'] = np.random.normal(0, 0.002, size=len(dates))
    factors['value'] = np.random.normal(0, 0.002, size=len(dates))
    factors['momentum'] = np.random.normal(0, 0.0025, size=len(dates))
    factors_path = out / f"factors_{days}d.csv"
    factors.to_csv(factors_path)

    # Strategy outputs: equity curve and metrics
    # Equity curve: simple average of tickers returns compounded with small alpha
    returns = prices.pct_change().fillna(0)
    strategy_returns = returns.mean(axis=1) + 0.0002  # small alpha
    equity = (1 + strategy_returns).cumprod() * 100000

    metrics = {
        "cagr": float(((equity[-1] / equity[0]) ** (365.0 / len(equity)) - 1) if len(equity) > 0 else 0),
        "sharpe": None,
        "max_drawdown": None
    }

    strategy = {
        "equity_curve": equity.round(2).to_dict(),
        "metrics": metrics,
        "weights": {t: round(1.0 / portfolio_tickers, 4) for t in tickers}
    }

    strategy_path = out / f"strategy_outputs_{days}d.json"
    with open(strategy_path, "w") as f:
        json.dump(strategy, f, indent=2)

    return {
        "prices_csv": str(prices_path),
        "factors_csv": str(factors_path),
        "strategy_json": str(strategy_path)
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--tickers", type=int, default=20)
    parser.add_argument("--out", default="./mock_data")
    args = parser.parse_args()
    print("Generating mock data...")
    res = generate(portfolio_tickers=args.tickers, days=args.days, out_dir=args.out)
    print("Generated:")
    for k, v in res.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
