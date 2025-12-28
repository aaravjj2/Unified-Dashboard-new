"""
Simple loader for keys.env file in repo root.
Parses KEY=VALUE lines and sets them into os.environ if not already set.
"""
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def load_keys_env(path: str = None) -> dict:
    """Load key/value pairs from keys.env and set them in os.environ.

    Returns dict of loaded keys.
    """
    repo_root = Path(__file__).resolve().parents[2]
    env_path = Path(path) if path else repo_root / 'keys.env'
    loaded = {}

    if not env_path.exists():
        logger.debug(f"keys.env not found at {env_path}")
        return loaded

    try:
        with env_path.open() as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                # Set only if not present to avoid overwriting real env
                if k and (k not in os.environ or os.environ.get(k) == ''):
                    os.environ[k] = v
                    loaded[k] = v
        logger.info(f"Loaded {len(loaded)} keys from {env_path}")
    except Exception as e:
        logger.error(f"Error loading keys.env: {e}")

    return loaded


if __name__ == '__main__':
    print(load_keys_env())
