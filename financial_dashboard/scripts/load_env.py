"""Utility script to load local `keys.env` into the environment for local runs.

Usage:
    python3 scripts/load_env.py
This will print which keys it loaded. It uses `src.utils.secrets.load_local_env()`.
"""
from src.utils.secrets import load_local_env
import os


def main():
    load_local_env()
    # print a small summary
    keys = ['OPENAI_API_KEY','APCA_API_KEY_ID','APCA_API_SECRET_KEY','TIINGO_API_KEY','FINNHUB_API_KEY','POLYGON_API_KEY']
    for k in keys:
        print(k, '=>', 'SET' if os.environ.get(k) else 'MISSING')


if __name__ == '__main__':
    main()
