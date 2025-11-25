"""Centralized configuration helper for the project.

Use get_cfg('KEY', default) to fetch environment variables. It will try to
load local .env files when available via _shared_env.load_local_env().
"""
from typing import Any
import os

# Try to reuse existing local loader
try:
    from _shared_env import get_env, load_local_env
    load_local_env()
except Exception:
    def get_env(k: str, d: Any = None):
        return os.getenv(k, d)


def get_cfg(k: str, default=None):
    return get_env(k, default)
