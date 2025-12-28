"""
MISSION A3 ENV HOTFIX - Centralized Environment Loader
Loads and validates API keys from multiple sources with deterministic behavior.

Priority order:
1. Doppler CLI (if available)
2. .env files (keys.env, doppler.env)
3. OS environment variables

Normalizes key variations (e.g., NEWS_API_KEY → NEWSAPI_KEY).
"""
import os
import subprocess
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class EnvironmentLoader:
    """Centralized environment variable loader with validation."""
    
    # Required keys for the application
    REQUIRED_KEYS = [
        'FINNHUB_API_KEY',
        'NEWSAPI_KEY',
        'APCA_API_KEY_ID',  # Alpaca
        'APCA_API_SECRET_KEY',
        'TIINGO_API_KEY'
    ]
    
    # Key name mappings for normalization
    KEY_ALIASES = {
        'NEWS_API_KEY': 'NEWSAPI_KEY',
        'ALPACA_API_KEY': 'APCA_API_KEY_ID',
        'ALPACA_SECRET': 'APCA_API_SECRET_KEY',
        'FINNHUB_KEY': 'FINNHUB_API_KEY',
        'FINNHUB2_API_KEY': 'FINNHUB_API_KEY_2'
    }
    
    def __init__(self):
        self.loaded_keys: Dict[str, str] = {}
        self.missing_keys: List[str] = []
        self.sources: List[str] = []
    
    def load_from_doppler(self) -> bool:
        """
        Attempt to load from Doppler CLI.
        Returns True if successful, False otherwise.
        """
        try:
            result = subprocess.run(
                ["doppler", "secrets", "download", "--format", "env"],
                capture_output=True,
                text=True,
                timeout=10,
                check=True
            )
            
            # Parse env format output
            for line in result.stdout.splitlines():
                if '=' in line and not line.startswith('#'):
                    key, _, value = line.partition('=')
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    
                    if value:
                        os.environ[key] = value
                        self.loaded_keys[key] = value
            
            self.sources.append('doppler')
            logger.info("✅ Loaded environment from Doppler CLI")
            return True
            
        except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.debug(f"Doppler not available: {e}")
            return False
    
    def load_from_dotenv(self, env_files: Optional[List[str]] = None) -> bool:
        """
        Load from .env files in priority order.
        """
        if env_files is None:
            env_files = ['keys.env', 'doppler.env', '.env']
        
        loaded_any = False
        # Determine repository root (two levels up: utils/ -> financial_dashboard/ -> repo)
        repo_root = Path(__file__).resolve().parents[2]

        for env_file in env_files:
            # Try multiple candidate locations: repo root, module dir, and raw path
            candidates = [repo_root / env_file, Path(__file__).resolve().parent.parent / env_file, Path(env_file)]
            found = False
            for cand in candidates:
                try_path = cand if isinstance(cand, Path) else Path(cand)
                if try_path.exists():
                    load_dotenv(try_path, override=False)
                    self.sources.append(f'dotenv:{try_path}')
                    logger.info(f"✅ Loaded dotenv from {try_path}")
                    loaded_any = True
                    found = True
                    break
            if not found:
                logger.debug(f"Dotenv file not found in candidates for '{env_file}': {[str(c) for c in candidates]}")
        
        if not loaded_any:
            logger.warning("⚠️ No .env files found")
        
        return loaded_any
    
    def normalize_keys(self):
        """
        Normalize key names by creating aliases.
        E.g., if NEWS_API_KEY exists but not NEWSAPI_KEY, create NEWSAPI_KEY.
        """
        for alias, canonical in self.KEY_ALIASES.items():
            if os.getenv(alias) and not os.getenv(canonical):
                value = os.getenv(alias)
                if value is not None:
                    os.environ[canonical] = value
                    logger.debug(f"Normalized {alias} → {canonical}")
    
    def validate_required_keys(self, raise_on_missing: bool = True) -> Dict[str, Any]:
        """
        Validate that all required keys are present.
        
        Args:
            raise_on_missing: If True, raise RuntimeError on missing keys
            
        Returns:
            Dict with validation results
        """
        self.missing_keys = []
        present_keys = []
        
        for key in self.REQUIRED_KEYS:
            value = os.getenv(key)
            if not value or value in ('', 'your_key_here', 'CHANGEME'):
                self.missing_keys.append(key)
            else:
                present_keys.append(key)
        
        result = {
            'valid': len(self.missing_keys) == 0,
            'missing_keys': self.missing_keys,
            'present_keys': present_keys,
            # Legacy aliases kept for compatibility with existing tests/logs
            'missing': self.missing_keys,
            'present': present_keys,
            'sources': self.sources
        }
        
        if self.missing_keys:
            msg = f"Missing required API keys: {self.missing_keys}"
            logger.error(f"❌ {msg}")
            
            if raise_on_missing:
                raise RuntimeError(msg)
        else:
            logger.info(f"✅ All {len(present_keys)} required keys present")
        
        return result
    
    def get_provider_status(self) -> Dict[str, bool]:
        """
        Check which API providers are configured.
        """
        return {
            'Finnhub': bool(os.getenv('FINNHUB_API_KEY')),
            'NewsAPI': bool(os.getenv('NEWSAPI_KEY') or os.getenv('NEWS_API_KEY')),
            'Alpaca': bool(os.getenv('APCA_API_KEY_ID') and os.getenv('APCA_API_SECRET_KEY')),
            'Polygon': bool(os.getenv('POLYGON_API_KEY')),
            'Tiingo': bool(os.getenv('TIINGO_API_KEY')),
            'Quandl': bool(os.getenv('QUANDL_API_KEY')),
            'FRED': bool(os.getenv('FRED_API_KEY'))
            ,
            # Groq provider (API key may be present as GROQ_API_KEY)
            'Groq': bool(os.getenv('GROQ_API_KEY') or os.getenv('GROQ_API'))
        }


# Global instance
_loader: Optional[EnvironmentLoader] = None


def load_environment(
    raise_on_missing: bool = True,
    force_reload: bool = False
) -> Dict[str, Any]:
    """
    Load and validate environment variables.
    
    This should be called at application startup before instantiating
    any API clients.
    
    Args:
        raise_on_missing: Raise error if required keys are missing
        force_reload: Force reload even if already loaded
        
    Returns:
        Dict with validation status and provider availability
        
    Raises:
        RuntimeError: If required keys are missing and raise_on_missing=True
    """
    global _loader
    
    if _loader is None or force_reload:
        _loader = EnvironmentLoader()
        
        # Load from sources in priority order
        _loader.load_from_doppler()
        _loader.load_from_dotenv()
        
        # Normalize key names
        _loader.normalize_keys()
    
    # Validate
    validation = _loader.validate_required_keys(raise_on_missing=raise_on_missing)
    provider_status = _loader.get_provider_status()
    
    return {
        **validation,
        'providers': provider_status
    }


def get_loader() -> Optional[EnvironmentLoader]:
    """Get the global loader instance."""
    return _loader


def require_keys(*key_names: str):
    """
    Decorator to ensure specific keys are present before function execution.
    
    Usage:
        @require_keys('FINNHUB_API_KEY', 'NEWSAPI_KEY')
        def fetch_data():
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            missing = [k for k in key_names if not os.getenv(k)]
            if missing:
                raise RuntimeError(
                    f"Function {func.__name__} requires keys: {missing}. "
                    "Call load_environment() first."
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


if __name__ == '__main__':
    # CLI test
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("Environment Loader Test")
    print("=" * 60)
    
    try:
        result = load_environment(raise_on_missing=False)
        
        print(f"\n✅ Sources: {', '.join(result['sources'])}")
        print(f"\n✅ Present keys ({len(result['present_keys'])}):")
        for key in result['present_keys']:
            print(f"  - {key}")
        
        if result['missing_keys']:
            print(f"\n❌ Missing keys ({len(result['missing_keys'])}):")
            for key in result['missing_keys']:
                print(f"  - {key}")
        
        print("\n📊 Provider Status:")
        for provider, available in result['providers'].items():
            status = "✅" if available else "❌"
            print(f"  {status} {provider}")
        
        print("\n" + "=" * 60)
        if result['valid']:
            print("✅ ALL REQUIRED KEYS PRESENT")
        else:
            print("❌ SOME KEYS MISSING")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        exit(1)
