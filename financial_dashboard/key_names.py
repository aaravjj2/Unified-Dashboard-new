"""
Centralized canonical key names and helpers for normalizing and matching
feature/column names across the codebase.

This module provides:
- CANONICAL_KEYS: standard names used across code
- ALIASES: mappings from common variants to canonical keys
- normalize_column_name(name): lower/strip normalization
- map_column_to_canonical(col): returns canonical key or None
- find_matching_columns(df_columns, key): returns list of columns matching a canonical key

Usage: from financial_dashboard import key_names as KN
      cols = KN.find_matching_columns(df.columns, 'vix')
"""
import os
import re
import shutil
import subprocess
import logging
from typing import List, Dict, Iterable, Optional

logger = logging.getLogger(__name__)

# Canonical key names used across the project
CANONICAL_KEYS = {
    'vix': 'vix',
    'vix_30d': 'vix_30d',
    'vix_60d': 'vix_60d',
    'tnx': 'tnx',
    'treasury_10y': 'treasury_10y',
    'oil_price': 'oil_price',
    'energy_sector': 'energy_sector',
    'spy_momentum': 'spy_momentum',
    'qqq_momentum': 'qqq_momentum',
    'credit_spreads': 'credit_spreads',
    'momentum': 'momentum',
    'returns_1m': 'returns_1m',
    'returns_1w': 'returns_1w',
    'ticker': 'ticker',
    'sector': 'sector',
}

# Common aliases / variants mapped to canonical keys
ALIASES: Dict[str, str] = {
    # vix variants
    'vix': 'vix',
    'vix30': 'vix_30d',
    'vix_30': 'vix_30d',
    'vix_30d': 'vix_30d',
    'vix60': 'vix_60d',
    'vix_60d': 'vix_60d',
    # treasury / tnx
    'tnx': 'tnx',
    'treasury': 'treasury_10y',
    'treasury_10y': 'treasury_10y',
    '10y': 'treasury_10y',
    # oil
    'oil': 'oil_price',
    'oil_price': 'oil_price',
    'wti': 'oil_price',
    'crude': 'oil_price',
    # momentum / returns
    'momentum': 'momentum',
    'spy_momentum': 'spy_momentum',
    'qqq_momentum': 'qqq_momentum',
    'ret_1m': 'returns_1m',
    'returns_1m': 'returns_1m',
    'ret_1w': 'returns_1w',
    'returns_1w': 'returns_1w',
    # others
    'sector': 'sector',
    'ticker': 'ticker',
}

# Precompile regex patterns for alias lookup convenience
_ALIAS_PATTERNS = {re.compile(rf"\b{re.escape(k)}\b", flags=re.IGNORECASE): v for k, v in ALIASES.items()}


def normalize_column_name(name: str) -> str:
    """Lowercase and strip a column name for normalization."""
    if not isinstance(name, str):
        return ''
    return name.strip().lower()


def map_column_to_canonical(col: str) -> Optional[str]:
    """Try to map a column name to a canonical key using exact alias match
    or substring heuristics. Returns canonical key or None.
    """
    n = normalize_column_name(col)
    if n in ALIASES:
        return ALIASES[n]

    # exact canonical name
    if n in CANONICAL_KEYS:
        return CANONICAL_KEYS[n]

    # substring matching against alias patterns
    for pat, canon in _ALIAS_PATTERNS.items():
        if pat.search(n):
            return canon

    # heuristics: common words
    for word, canon in ALIASES.items():
        if word in n:
            return canon

    return None


def find_matching_columns(columns: Iterable[str], key: str) -> List[str]:
    """Return the list of column names from `columns` that map to canonical `key`.
    Matching uses `map_column_to_canonical`.
    """
    if key not in CANONICAL_KEYS and key not in ALIASES.values():
        # allow passing an alias that maps to canonical
        if key in ALIASES:
            key = ALIASES[key]
    out = []
    for c in columns:
        mapped = map_column_to_canonical(c)
        if mapped == key:
            out.append(c)
    return out


def standardize_df_columns(df):
    """Return a mapping of original column -> canonical key (where found).
    This does not rename the DataFrame; it returns a dict that callers can use
    to rename or align features as needed.
    """
    mapping = {}
    for c in df.columns:
        canon = map_column_to_canonical(c)
        if canon:
            mapping[c] = canon
    return mapping

# Canonical environment key names (preferred names to use everywhere)
ENV_CANONICAL = {
    'FINNHUB_API_KEY_1': 'FINNHUB_API_KEY_1',
    'FINNHUB_API_KEY_2': 'FINNHUB_API_KEY_2',
    'FINNHUB_API_KEY_3': 'FINNHUB_API_KEY_3',
    'ALPACA_API_KEY': 'ALPACA_API_KEY',
    'ALPACA_SECRET_KEY': 'ALPACA_SECRET_KEY',
    'ALPACA_BASE_URL': 'ALPACA_BASE_URL',
    # Backwards-compatibility aliases (APCA_* used in older code)
    'APCA_API_KEY_ID': 'ALPACA_API_KEY',
    'APCA_API_SECRET_KEY': 'ALPACA_SECRET_KEY',
}

# Map common alias names to canonical env names
ENV_ALIASES = {
    # Finnhub
    'FINNHUB_API_KEY': 'FINNHUB_API_KEY_1',
    'FINNHUB_API_KEY_1': 'FINNHUB_API_KEY_1',
    'FINNHUB_API_KEY_2': 'FINNHUB_API_KEY_2',
    'FINNHUB2_API_KEY': 'FINNHUB_API_KEY_2',
    'FINNHUB_API_KEY_3': 'FINNHUB_API_KEY_3',
    # Alpaca / APCA
    'ALPACA_API_KEY': 'ALPACA_API_KEY',
    'ALPACA_API_SECRET': 'ALPACA_SECRET_KEY',
    'ALPACA_SECRET_KEY': 'ALPACA_SECRET_KEY',
    'APCA_API_KEY_ID': 'ALPACA_API_KEY',
    'APCA_API_SECRET_KEY': 'ALPACA_SECRET_KEY',
}


def resolve_env_names(name: str) -> list:
    """Return a prioritized list of environment variable names to check for `name`.
    If `name` is already canonical, it will be returned first.
    """
    if not name:
        return []
    name = name.strip()
    out = []
    # if provided name maps directly to a canonical
    if name in ENV_ALIASES:
        out.append(ENV_ALIASES[name])
    # check if canonical mapping exists
    if name in ENV_CANONICAL:
        out.append(ENV_CANONICAL[name])
    # include original and common variants
    out.append(name)

    # unique preserve order
    seen = set()
    res = []
    for n in out:
        if n and n not in seen:
            seen.add(n)
            res.append(n)

    # If we resolved to a canonical name, also include known aliases that map to
    # that canonical key (so callers asking for FINNHUB_API_KEY_1 will still
    # find values stored as FINNHUB_API_KEY in the environment/Doppler).
    canonical = None
    # pick the first canonical-like name we have
    for candidate in res:
        if candidate in ENV_CANONICAL.values() or candidate in ENV_CANONICAL:
            # normalize to canonical value
            canonical = ENV_CANONICAL.get(candidate, candidate)
            break
        if candidate in ENV_ALIASES.values():
            canonical = candidate
            break

    if canonical:
        # add all alias keys that map to this canonical (preserve order, avoid dupes)
        for alias_key, mapped in ENV_ALIASES.items():
            if mapped == canonical and alias_key not in res:
                res.append(alias_key)

    return res


def get_secret(name: str) -> Optional[str]:
    """Get a secret value for `name` by checking environment variables and
    falling back to the Doppler CLI (if available). This centralizes secret
    lookup so code can call `KN.get_secret('FINNHUB_API_KEY_1')` and get a
    consistent result across the project.

    Returns None if no value found.
    """
    for candidate in resolve_env_names(name):
        val = os.environ.get(candidate)
        if val:
            logger.debug('Found env var %s via os.environ', candidate)
            return val
    # Try Doppler CLI fallback (doppler secrets get <name> --plain)
    try:
        if shutil.which('doppler'):
            # allow callers/environment to specify project/config for Doppler
            doppler_project = os.getenv('DOPPLER_PROJECT') or os.getenv('DOPPLER_PROJECT_NAME') or 'dash'
            doppler_config = os.getenv('DOPPLER_CONFIG') or os.getenv('DOPPLER_ENV') or 'dev'

            # try candidate names in order, prefer explicit project/config flags
            for candidate in resolve_env_names(name):
                # first try with explicit project/config flags (more reliable when CLI requires them)
                cmd_with_flags = ['doppler', 'secrets', 'get', candidate, '--plain', '--project', doppler_project, '--config', doppler_config]
                try:
                    proc = subprocess.run(cmd_with_flags, capture_output=True, text=True, timeout=12)
                    if proc.returncode == 0:
                        out = proc.stdout.strip()
                        if out:
                            logger.debug('Found secret %s via doppler (project=%s config=%s)', candidate, doppler_project, doppler_config)
                            return out
                except Exception:
                    pass

                # fallback: try without flags for backwards compatibility
                try:
                    proc = subprocess.run(['doppler', 'secrets', 'get', candidate, '--plain'], capture_output=True, text=True, timeout=10)
                    if proc.returncode == 0:
                        out = proc.stdout.strip()
                        if out:
                            logger.debug('Found secret %s via doppler (no flags)', candidate)
                            return out
                except Exception:
                    continue
    except Exception:
        pass
    return None
