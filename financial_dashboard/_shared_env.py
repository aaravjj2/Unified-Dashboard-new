"""Shared environment loader for local development.

This module centralizes loading of .env files when running services locally
(not in Docker). Containers should rely on docker-compose to inject env vars.

Usage:
    from _shared_env import load_local_env, get_env
    load_local_env()  # optional: loads .env into os.environ
    key = get_env('ALPACA_API_KEY')
"""
from pathlib import Path
import os
from dotenv import load_dotenv
import subprocess
import shlex

ENV_PATHS = [
    Path('.').resolve() / '.env',
    Path('.').resolve() / '.env.local',
    Path('.').resolve() / 'keys.env'
]

_loaded = False

def load_local_env(env_file: str = None) -> None:
    """Load environment variables from a .env file into the process environment.

    If env_file is provided it will be used, otherwise we try common names.
    This is idempotent and safe to call multiple times.
    """
    global _loaded
    if _loaded:
        return

    if env_file:
        p = Path(env_file)
        if p.exists():
            load_dotenv(p)
            _loaded = True
            return

    for p in ENV_PATHS:
        if p.exists():
            load_dotenv(p)
            _loaded = True
            return


def load_doppler_env(project: str = 'dash', config: str = 'dev') -> bool:
    """Attempt to load secrets from Doppler CLI into the process environment.

    This function requires the `doppler` CLI to be installed and the calling
    user to have access to the specified project/config. It returns True if
    it successfully loaded any environment variables.

    Example usage:
        load_doppler_env(project='dash', config='dev')
    """
    try:
        # Try to download secrets in env format
        cmd = ["doppler", "secrets", "download", "--format", "env", "--project", project, "--config", config]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        out = proc.stdout
        if not out:
            return False

        # Parse lines like KEY=VALUE
        for line in out.splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            # strip potential surrounding quotes
            v = v.strip().strip('\"').strip('\'')
            if k:
                os.environ.setdefault(k, v)
        return True
    except FileNotFoundError:
        # doppler CLI not installed
        return False
    except Exception:
        return False


def get_env(key: str, default=None):
    """Get environment variable, optionally loading local .env first."""
    if not _loaded:
        load_local_env()
        # Try Doppler as an optional secondary loader (non-fatal)
        try:
            load_doppler_env()
        except Exception:
            pass
    return os.getenv(key, default)
