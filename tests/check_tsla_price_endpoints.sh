#!/usr/bin/env bash
# Quick TSLA price endpoint checks for Finnhub and Alpaca
# Usage: FINNHUB_API_KEY=... ALPACA_API_KEY=... ALPACA_SECRET=... ./tests/check_tsla_price_endpoints.sh
set -euo pipefail

FINNHUB_KEY=${FINNHUB_API_KEY:-}
ALPACA_KEY=${ALPACA_API_KEY:-}
ALPACA_SECRET=${ALPACA_SECRET:-}

echo "== TSLA Price Endpoint Quick Check =="

echo "\n-- Finnhub (quote) --"
if [ -z "$FINNHUB_KEY" ]; then
  echo "FINNHUB_API_KEY not set; skipping Finnhub test"
else
  FH_URL="https://finnhub.io/api/v1/quote?symbol=TSLA&token=${FINNHUB_KEY}"
  echo "Curling: $FH_URL"
  curl -sS -w "\nHTTP_CODE:%{http_code}\n" "$FH_URL" | sed -n '1,20p'
fi

echo "\n-- Alpaca (market data - latest) --"
if [ -z "$ALPACA_KEY" ] || [ -z "$ALPACA_SECRET" ]; then
  echo "ALPACA_API_KEY or ALPACA_SECRET not set; skipping Alpaca test"
else
  # Try the paper API first (commonly used in this repo)
  ALPACA_PAPER_URL="https://paper-api.alpaca.markets/v2/stocks/TSLA/quotes/latest"
  echo "Curling Paper API: $ALPACA_PAPER_URL"
  curl -sS -w "\nHTTP_CODE:%{http_code}\n" -H "APCA-API-KEY-ID: ${ALPACA_KEY}" -H "APCA-API-SECRET-KEY: ${ALPACA_SECRET}" "$ALPACA_PAPER_URL" | sed -n '1,30p'

  echo "\n-- Alpaca (data.alpaca.markets) --"
  ALPACA_DATA_URL="https://data.alpaca.markets/v2/stocks/TSLA/quotes/latest"
  echo "Curling Data API: $ALPACA_DATA_URL"
  curl -sS -w "\nHTTP_CODE:%{http_code}\n" -H "APCA-API-KEY-ID: ${ALPACA_KEY}" -H "APCA-API-SECRET-KEY: ${ALPACA_SECRET}" "$ALPACA_DATA_URL" | sed -n '1,30p'
fi

echo "\n-- yfinance fallback check (simple) --"
python3 - <<'PY'
import yfinance as yf
try:
    t=yf.Ticker('TSLA')
    data=t.history(period='1d')
    print(data.tail(1).to_json())
except Exception as e:
    print('yfinance failed:', e)
PY

echo "\n== Done =="
