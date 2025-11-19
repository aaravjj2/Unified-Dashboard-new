"""Secrets helper: load dotenv and provide accessors for common API keys.

This module intentionally does not store secrets in the repo. It will load
environment variables (optionally from a local `keys.env` when running
locally) and expose small helper getters for one-line client code.

Usage:
    from src.utils.secrets import load_local_env, get_alpaca_credentials, get_openai_key
    load_local_env()  # optional: loads Dash/keys.env into environment
    key = get_openai_key()
"""
from pathlib import Path
import os
from typing import Optional, Tuple


def load_local_env(env_path: Optional[str] = None) -> None:
    """Load environment variables from a dotenv-style file into os.environ.

    This is a convenience for local development. Do NOT commit secrets.
    If env_path is None, will attempt to load `Dash/keys.env` relative to
    the repository root.
    """
    try:
        from dotenv import load_dotenv
    except Exception:
        # minimal fallback: parse simple KEY=VALUE lines
        if env_path is None:
            env_path = str(Path(__file__).resolve().parents[2] / 'keys.env')
        p = Path(env_path)
        if not p.exists():
            return
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())
        return

    if env_path is None:
        env_path = str(Path(__file__).resolve().parents[2] / 'keys.env')
    load_dotenv(env_path)


def get_openai_key() -> Optional[str]:
    return os.environ.get('OPENAI_API_KEY') or os.environ.get('OpenAI_API_KEY') or os.environ.get('OPENAI_KEY')


def get_alpaca_credentials() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    return (
        os.environ.get('APCA_API_KEY_ID'),
        os.environ.get('APCA_API_SECRET_KEY'),
        os.environ.get('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')
    )


def get_tiingo_key() -> Optional[str]:
    return os.environ.get('TIINGO_API_KEY') or os.environ.get('TIINGO_KEY')


def get_finnhub_key() -> Optional[str]:
    return os.environ.get('FINNHUB_API_KEY') or os.environ.get('FINNHUB_KEY')


def get_polygon_key() -> Optional[str]:
    return os.environ.get('POLYGON_API_KEY') or os.environ.get('POLYGON_KEY')


def get_quandl_key() -> Optional[str]:
    return os.environ.get('QUANDL_API_KEY') or os.environ.get('QUANDL_KEY')


def get_twelvedata_key() -> Optional[str]:
    return os.environ.get('TWELVEDATA_API_KEY') or os.environ.get('TWELVE_DATA_API_KEY')


def get_rapidapi_key() -> Optional[str]:
    return os.environ.get('RAPIDAPI_KEY')


def get_news_api_key() -> Optional[str]:
    return os.environ.get('NEWS_API_KEY')


def suggest_secure_practices() -> str:
    return (
        'Store API keys outside the repository (e.g. use OS env, .env ignored by git, or a secret manager).'
    )
