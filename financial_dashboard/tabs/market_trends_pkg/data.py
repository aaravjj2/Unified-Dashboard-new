"""Data access and heavy imports for Market Trends.

All heavy imports (network, DB, ML) should live here and be executed only
when a function is called. This prevents import-time side effects.
"""

import os
import json
import time
from typing import List, Dict

CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'outputs')


def load_cached_briefs() -> List[Dict]:
    """Load cached briefs from outputs; perform I/O only when called."""
    path = os.path.join(CACHE_DIR, 'market_brief.json')
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return []


def probe_external_providers(timeout: float = 1.0) -> Dict:
    """Perform lightweight provider probes when explicitly requested."""
    import requests
    probes = {'finnhub': 'https://finnhub.io', 'alpaca': 'https://data.alpaca.markets'}
    out = {}
    for k, url in probes.items():
        try:
            r = requests.get(url, timeout=timeout)
            out[k] = r.status_code
        except Exception:
            out[k] = None
    return out
