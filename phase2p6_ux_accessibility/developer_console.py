"""Developer console utilities for debugging and metrics exposure.

Provides simple functions to gather: onboarding state, theme profile, and a basic latency log.
This is intentionally light-weight and filesystem-based for local/offline use.
"""
from __future__ import annotations
import json
from pathlib import Path
from time import perf_counter
from .onboarding_manager import get_progress
from .theme_engine import ThemeEngine

ROOT = Path(__file__).parent
LATENCY_LOG = ROOT / 'docs' / 'ux_latency.log'


def get_onboarding_state() -> dict:
    return get_progress()


def get_loaded_theme(name: str = 'light') -> dict:
    te = ThemeEngine()
    return te.load_theme(name)


def log_latency(item: str, elapsed: float) -> None:
    LATENCY_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LATENCY_LOG, 'a', encoding='utf8') as f:
        f.write(json.dumps({"item": item, "elapsed": elapsed}) + '\n')


def sample_and_log():
    t0 = perf_counter()
    _ = get_onboarding_state()
    t1 = perf_counter()
    log_latency('onboarding_read', round(t1 - t0, 4))


if __name__ == '__main__':
    sample_and_log()
    print('Console ready. Latency log:', LATENCY_LOG)
